"""F1 Race Intelligence — Jolpica F1 API Client.

Handles HTTP transport, URL building, parameter serialization, bounded exponential backoff
retries, structural validation of the MRData envelope, and multi-page pagination.
"""

import logging
import time
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple

import httpx

from app.f1.exceptions import (
    F1APIError,
    F1HTTPError,
    F1RateLimitError,
    F1ResponseError,
    F1TimeoutError,
)
from app.f1.types import APIResponse, ClientConfig, PageMetadata

logger = logging.getLogger("f1.jolpica")

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class JolpicaClient:
    """Client for querying the Jolpica F1 (Ergast-compatible) API."""

    def __init__(
        self,
        config: Optional[ClientConfig] = None,
        http_client: Optional[httpx.Client] = None,
        sleep_fn: Callable[[float], None] = time.sleep,
    ):
        """Initialize the Jolpica F1 API client.

        Args:
            config: Optional client configuration dataclass.
            http_client: Optional injected httpx.Client (e.g. for testing with MockTransport).
            sleep_fn: Sleep function for backoff delays (allows mocking out real time delays in tests).
        """
        self.config = config or ClientConfig()
        self._sleep_fn = sleep_fn
        self._owns_http_client = http_client is None
        self._http = http_client or httpx.Client(
            headers=self.config.headers,
            timeout=self.config.timeout,
            follow_redirects=True,
        )

    def close(self) -> None:
        """Close the underlying HTTP client session if owned by this instance."""
        if self._owns_http_client and not self._http.is_closed:
            self._http.close()

    def __enter__(self) -> "JolpicaClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def _build_url(self, endpoint_path: str) -> str:
        """Construct the absolute URL from the base URL and endpoint path, ensuring .json format."""
        clean_base = self.config.base_url.rstrip("/")
        clean_path = endpoint_path.strip("/")

        # Ensure .json extension
        if not clean_path.endswith(".json"):
            clean_path = f"{clean_path}.json"

        return f"{clean_base}/{clean_path}"

    def _calculate_backoff(self, attempt: int, response: Optional[httpx.Response]) -> float:
        """Determine backoff duration, respecting Retry-After header for 429 responses if present."""
        if response is not None and response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            if retry_after is not None:
                try:
                    delay = float(retry_after)
                    return min(max(delay, 0.0), self.config.max_backoff)
                except (ValueError, TypeError):
                    pass

        # Exponential backoff: backoff_factor * 2^(attempt - 1)
        delay = self.config.backoff_factor * (2 ** (attempt - 1))
        return min(delay, self.config.max_backoff)

    def _decode_and_validate(self, response: httpx.Response, endpoint_path: str) -> APIResponse:
        """Decode response body as JSON and validate MRData envelope structure."""
        try:
            payload = response.json()
        except Exception as e:
            logger.error("Failed to decode JSON from endpoint %s: %s", endpoint_path, e)
            raise F1ResponseError(
                f"Malformed JSON response from endpoint '{endpoint_path}': {e}",
                endpoint=endpoint_path,
                raw_payload=response.text[:500] if response.text else None,
            ) from e

        if not isinstance(payload, dict) or "MRData" not in payload:
            logger.error("Response from %s missing top-level 'MRData' envelope", endpoint_path)
            raise F1ResponseError(
                f"Response from '{endpoint_path}' missing top-level 'MRData' envelope.",
                endpoint=endpoint_path,
                raw_payload=str(payload)[:500],
            )

        mr_data = payload["MRData"]
        if not isinstance(mr_data, dict):
            raise F1ResponseError(
                f"Invalid 'MRData' type (expected dict, got {type(mr_data).__name__}) from '{endpoint_path}'.",
                endpoint=endpoint_path,
            )

        # Parse pagination metadata
        try:
            limit = int(mr_data.get("limit", 0))
            offset = int(mr_data.get("offset", 0))
            total = int(mr_data.get("total", 0))
            url = str(mr_data.get("url", ""))
        except (ValueError, TypeError) as e:
            raise F1ResponseError(
                f"Invalid pagination metadata in MRData envelope from '{endpoint_path}': {e}",
                endpoint=endpoint_path,
            ) from e

        # Extract inner domain table (e.g. RaceTable, StandingsTable, CircuitTable)
        reserved_keys = {"xmlns", "series", "url", "limit", "offset", "total"}
        inner_data = {k: v for k, v in mr_data.items() if k not in reserved_keys}

        metadata = PageMetadata(limit=limit, offset=offset, total=total, url=url)
        return APIResponse(metadata=metadata, data=inner_data, raw=mr_data)

    def get_page(
        self,
        endpoint_path: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> APIResponse:
        """Execute a single HTTP GET request with retries and structural response validation.

        Args:
            endpoint_path: Path relative to base URL (e.g. '2025/1/results' or 'circuits.json').
            params: Optional query parameters (e.g. {'limit': 30, 'offset': 0}).

        Returns:
            APIResponse containing parsed metadata and inner resource data.

        Raises:
            F1HTTPError: For non-retryable 4xx errors, or when 5xx retries are exhausted.
            F1RateLimitError: When 429 rate limit retries are exhausted.
            F1TimeoutError: When request timeouts exceed max retries.
            F1ResponseError: When response payload is not valid JSON or lacks MRData.
        """
        url = self._build_url(endpoint_path)
        query_params = {str(k): str(v) for k, v in (params or {}).items()}

        attempt = 0
        last_exception: Optional[Exception] = None
        last_response: Optional[httpx.Response] = None

        while attempt <= self.config.max_retries:
            attempt += 1
            try:
                logger.debug("Requesting %s (attempt %d/%d, params: %s)", url, attempt, self.config.max_retries + 1, query_params)
                response = self._http.get(url, params=query_params)
                last_response = response

                # Non-retryable client errors (400, 401, 403, 404, etc. excluding 429)
                if response.status_code >= 400 and response.status_code not in RETRYABLE_STATUS_CODES:
                    logger.warning("Non-retryable HTTP %d from %s", response.status_code, endpoint_path)
                    raise F1HTTPError(
                        f"HTTP {response.status_code} error requesting '{endpoint_path}'",
                        status_code=response.status_code,
                        response_text=response.text[:500],
                        endpoint=endpoint_path,
                    )

                # Retryable status codes (429, 500, 502, 503, 504)
                if response.status_code in RETRYABLE_STATUS_CODES:
                    if attempt > self.config.max_retries:
                        if response.status_code == 429:
                            raise F1RateLimitError(
                                f"Rate limit exceeded (HTTP 429) on '{endpoint_path}' after {self.config.max_retries} retries.",
                                status_code=429,
                                response_text=response.text[:500],
                                endpoint=endpoint_path,
                            )
                        raise F1HTTPError(
                            f"HTTP {response.status_code} on '{endpoint_path}' after {self.config.max_retries} retries.",
                            status_code=response.status_code,
                            response_text=response.text[:500],
                            endpoint=endpoint_path,
                        )

                    delay = self._calculate_backoff(attempt, response)
                    logger.warning(
                        "HTTP %d from %s, retrying in %.2fs (attempt %d/%d)",
                        response.status_code,
                        endpoint_path,
                        delay,
                        attempt,
                        self.config.max_retries,
                    )
                    self._sleep_fn(delay)
                    continue

                # Successful HTTP 2xx
                response.raise_for_status()
                return self._decode_and_validate(response, endpoint_path)

            except httpx.TimeoutException as e:
                last_exception = e
                if attempt > self.config.max_retries:
                    logger.error("Request to %s timed out after %d retries", endpoint_path, self.config.max_retries)
                    raise F1TimeoutError(
                        f"Request to '{endpoint_path}' timed out after {self.config.max_retries} retries: {e}",
                        endpoint=endpoint_path,
                    ) from e

                delay = self._calculate_backoff(attempt, None)
                logger.warning("Timeout requesting %s, retrying in %.2fs (attempt %d/%d)", endpoint_path, delay, attempt, self.config.max_retries)
                self._sleep_fn(delay)

            except httpx.NetworkError as e:
                last_exception = e
                if attempt > self.config.max_retries:
                    logger.error("Network error connecting to %s after %d retries: %s", endpoint_path, self.config.max_retries, e)
                    raise F1HTTPError(
                        f"Network error on '{endpoint_path}' after {self.config.max_retries} retries: {e}",
                        endpoint=endpoint_path,
                    ) from e

                delay = self._calculate_backoff(attempt, None)
                logger.warning("Network error on %s, retrying in %.2fs (attempt %d/%d): %s", endpoint_path, delay, attempt, self.config.max_retries, e)
                self._sleep_fn(delay)

        # Fallback if loop exited without explicit return or raise
        if last_exception:
            raise F1APIError(f"Request to '{endpoint_path}' failed: {last_exception}") from last_exception
        raise F1APIError(f"Request to '{endpoint_path}' failed after retries.")

    def iter_pages(
        self,
        endpoint_path: str,
        params: Optional[Dict[str, Any]] = None,
        page_limit: int = 100,
    ) -> Generator[APIResponse, None, None]:
        """Generator that yields successive APIResponse pages until all records are retrieved.

        Args:
            endpoint_path: Resource endpoint path.
            params: Base query parameters.
            page_limit: Maximum items requested per page (default: 100).
        """
        offset = 0
        req_params = dict(params or {})
        req_params["limit"] = page_limit

        while True:
            req_params["offset"] = offset
            response = self.get_page(endpoint_path, params=req_params)
            yield response

            total = response.metadata.total
            limit = response.metadata.limit

            # Check termination conditions
            offset += limit
            if offset >= total or limit == 0:
                break

    def get_all_raw_records(
        self,
        endpoint_path: str,
        resource_key: str,
        table_key: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        page_limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Paginate through all pages of an endpoint and extract a flat list of items.

        Args:
            endpoint_path: Resource endpoint path.
            resource_key: Key inside the table holding the record list (e.g. 'Races', 'Circuits', 'PitStops').
            table_key: Optional table name (e.g. 'RaceTable', 'CircuitTable'). Inferred if None.
            params: Optional query parameters.
            page_limit: Page batch limit.

        Returns:
            Aggregated list of raw record dictionaries.
        """
        all_records: List[Dict[str, Any]] = []

        for page in self.iter_pages(endpoint_path, params=params, page_limit=page_limit):
            data = page.data
            if table_key and table_key in data:
                table = data[table_key]
            elif len(data) == 1:
                table = next(iter(data.values()))
            else:
                table = data

            if isinstance(table, dict) and resource_key in table:
                items = table[resource_key]
                if isinstance(items, list):
                    all_records.extend(items)

        return all_records

    # -------------------------------------------------------------------------
    # High-level convenience methods for project data categories
    # -------------------------------------------------------------------------

    def get_seasons(self, limit: int = 100, offset: int = 0) -> APIResponse:
        """Fetch championship seasons list with pagination."""
        return self.get_page("seasons", params={"limit": limit, "offset": offset})

    def get_all_seasons(self) -> List[Dict[str, Any]]:
        """Fetch all historical championship seasons across all pages."""
        return self.get_all_raw_records("seasons", resource_key="Seasons", table_key="SeasonTable")

    def get_circuits(self, limit: int = 100, offset: int = 0) -> APIResponse:
        """Fetch circuits list with pagination."""
        return self.get_page("circuits", params={"limit": limit, "offset": offset})

    def get_all_circuits(self) -> List[Dict[str, Any]]:
        """Fetch all circuits across all pages."""
        return self.get_all_raw_records("circuits", resource_key="Circuits", table_key="CircuitTable")

    def get_constructors(self, limit: int = 100, offset: int = 0) -> APIResponse:
        """Fetch constructors list with pagination."""
        return self.get_page("constructors", params={"limit": limit, "offset": offset})

    def get_all_constructors(self) -> List[Dict[str, Any]]:
        """Fetch all constructors across all pages."""
        return self.get_all_raw_records("constructors", resource_key="Constructors", table_key="ConstructorTable")

    def get_drivers(self, limit: int = 100, offset: int = 0) -> APIResponse:
        """Fetch drivers list with pagination."""
        return self.get_page("drivers", params={"limit": limit, "offset": offset})

    def get_all_drivers(self) -> List[Dict[str, Any]]:
        """Fetch all drivers across all pages."""
        return self.get_all_raw_records("drivers", resource_key="Drivers", table_key="DriverTable")

    def get_races(self, season: int, limit: int = 100, offset: int = 0) -> APIResponse:
        """Fetch schedule and race list for a specific season."""
        return self.get_page(f"{season}", params={"limit": limit, "offset": offset})

    def get_all_races(self, season: int) -> List[Dict[str, Any]]:
        """Fetch all races scheduled for a season across all pages."""
        return self.get_all_raw_records(f"{season}", resource_key="Races", table_key="RaceTable")

    def get_race_results(self, season: int, round_number: int) -> APIResponse:
        """Fetch final race classification results for a Grand Prix round."""
        return self.get_page(f"{season}/{round_number}/results")

    def get_qualifying_results(self, season: int, round_number: int) -> APIResponse:
        """Fetch qualifying session classification results for a Grand Prix round."""
        return self.get_page(f"{season}/{round_number}/qualifying")

    def get_sprint_results(self, season: int, round_number: int) -> APIResponse:
        """Fetch sprint race session classification results for a Grand Prix round."""
        return self.get_page(f"{season}/{round_number}/sprint")

    def get_pit_stops(self, season: int, round_number: int, limit: int = 100, offset: int = 0) -> APIResponse:
        """Fetch pit stop timing records for a Grand Prix round."""
        return self.get_page(f"{season}/{round_number}/pitstops", params={"limit": limit, "offset": offset})

    def get_all_pit_stops(self, season: int, round_number: int, page_limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch all pit stops for a Grand Prix round across all pages."""
        pit_stops: List[Dict[str, Any]] = []
        for page in self.iter_pages(f"{season}/{round_number}/pitstops", page_limit=page_limit):
            race_table = page.data.get("RaceTable", {})
            races = race_table.get("Races", [])
            for race in races:
                if "PitStops" in race:
                    pit_stops.extend(race["PitStops"])
        return pit_stops

    def get_lap_times(
        self,
        season: int,
        round_number: int,
        lap: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> APIResponse:
        """Fetch lap timing records for a Grand Prix round (or specific lap number)."""
        endpoint = f"{season}/{round_number}/laps/{lap}" if lap is not None else f"{season}/{round_number}/laps"
        return self.get_page(endpoint, params={"limit": limit, "offset": offset})

    def get_all_lap_times(self, season: int, round_number: int, page_limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch all lap timing records for a Grand Prix round across all pages."""
        laps: List[Dict[str, Any]] = []
        for page in self.iter_pages(f"{season}/{round_number}/laps", page_limit=page_limit):
            race_table = page.data.get("RaceTable", {})
            races = race_table.get("Races", [])
            for race in races:
                if "Laps" in race:
                    laps.extend(race["Laps"])
        return laps

    def get_driver_standings(self, season: int, round_number: Optional[int] = None) -> APIResponse:
        """Fetch World Drivers' Championship standings for a season (or after a specific round)."""
        endpoint = f"{season}/{round_number}/driverStandings" if round_number is not None else f"{season}/driverStandings"
        return self.get_page(endpoint)

    def get_constructor_standings(self, season: int, round_number: Optional[int] = None) -> APIResponse:
        """Fetch World Constructors' Championship standings for a season (or after a specific round)."""
        endpoint = f"{season}/{round_number}/constructorStandings" if round_number is not None else f"{season}/constructorStandings"
        return self.get_page(endpoint)
