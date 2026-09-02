"""Unit tests for the Jolpica F1 API Client using native httpx.MockTransport."""

import json
from typing import List, Tuple

import httpx
import pytest

from app.f1.client import JolpicaClient
from app.f1.exceptions import (
    F1APIError,
    F1HTTPError,
    F1RateLimitError,
    F1ResponseError,
    F1TimeoutError,
)
from app.f1.types import ClientConfig
from tests.f1.fixtures import (
    SAMPLE_CIRCUITS_PAYLOAD,
    SAMPLE_CONSTRUCTOR_STANDINGS_PAYLOAD,
    SAMPLE_DRIVER_STANDINGS_PAYLOAD,
    SAMPLE_LAPS_PAGE_1,
    SAMPLE_LAPS_PAGE_2,
    SAMPLE_PITSTOPS_PAGE_1,
    SAMPLE_PITSTOPS_PAGE_2,
    SAMPLE_QUALIFYING_PAYLOAD,
    SAMPLE_RACE_RESULTS_PAYLOAD,
    SAMPLE_SPRINT_PAYLOAD,
)


def _make_client(handler, max_retries=3, backoff_factor=0.01) -> Tuple[JolpicaClient, List[float]]:
    """Helper to create a JolpicaClient with a mock transport and recorded sleep durations."""
    sleeps: List[float] = []

    def record_sleep(d: float):
        sleeps.append(d)

    config = ClientConfig(
        base_url="https://api.jolpi.ca/ergast/f1",
        timeout=5.0,
        max_retries=max_retries,
        backoff_factor=backoff_factor,
        max_backoff=5.0,
    )
    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(headers=config.headers, transport=transport)
    client = JolpicaClient(config=config, http_client=http_client, sleep_fn=record_sleep)
    return client, sleeps


# -----------------------------------------------------------------------------
# Test 1 & 2: Successful request and JSON response decoding
# -----------------------------------------------------------------------------

def test_successful_request_and_decoding():
    """Test 1 & 2: Successful GET request correctly decodes JSON and populates APIResponse."""
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/ergast/f1/2024/1/results.json"
        assert request.headers.get("Accept") == "application/json"
        return httpx.Response(200, json=SAMPLE_RACE_RESULTS_PAYLOAD)

    client, sleeps = _make_client(handler)
    response = client.get_race_results(2024, 1)

    assert response.metadata.limit == 30
    assert response.metadata.offset == 0
    assert response.metadata.total == 2
    assert "RaceTable" in response.data
    assert len(response.data["RaceTable"]["Races"]) == 1
    assert len(sleeps) == 0


# -----------------------------------------------------------------------------
# Test 3: Malformed JSON
# -----------------------------------------------------------------------------

def test_malformed_json_response():
    """Test 3: Non-JSON response text raises F1ResponseError with raw payload snippet."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html><body>502 Bad Gateway</body></html>", headers={"content-type": "text/html"})

    client, _ = _make_client(handler)
    with pytest.raises(F1ResponseError) as exc_info:
        client.get_page("2024/1/results")

    assert "Malformed JSON" in str(exc_info.value)
    assert exc_info.value.endpoint == "2024/1/results"
    assert "502 Bad Gateway" in str(exc_info.value.raw_payload)


# -----------------------------------------------------------------------------
# Test 4: Unexpected response structure
# -----------------------------------------------------------------------------

def test_missing_mrdata_envelope():
    """Test 4: Response JSON missing 'MRData' envelope raises F1ResponseError."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": {"items": []}})

    client, _ = _make_client(handler)
    with pytest.raises(F1ResponseError) as exc_info:
        client.get_page("circuits")

    assert "missing top-level 'MRData'" in str(exc_info.value)


def test_invalid_pagination_metadata_types():
    """Test 4b: Non-integer pagination strings in MRData raise F1ResponseError."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"MRData": {"limit": "invalid_num", "offset": "0", "total": "10"}})

    client, _ = _make_client(handler)
    with pytest.raises(F1ResponseError) as exc_info:
        client.get_page("circuits")

    assert "Invalid pagination metadata" in str(exc_info.value)


# -----------------------------------------------------------------------------
# Test 5: 404 / Non-retryable HTTP error
# -----------------------------------------------------------------------------

def test_non_retryable_404_error():
    """Test 5: HTTP 404 error raises F1HTTPError immediately without retrying."""
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(404, text="Resource Not Found")

    client, sleeps = _make_client(handler, max_retries=3)
    with pytest.raises(F1HTTPError) as exc_info:
        client.get_page("non_existent_endpoint")

    assert exc_info.value.status_code == 404
    assert attempts == 1  # Did NOT retry
    assert len(sleeps) == 0


def test_non_retryable_400_error():
    """Test 5b: HTTP 400 Bad Request raises F1HTTPError immediately."""
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(400, text="Bad Request")

    client, sleeps = _make_client(handler)
    with pytest.raises(F1HTTPError) as exc_info:
        client.get_page("invalid_query")

    assert exc_info.value.status_code == 400
    assert attempts == 1


# -----------------------------------------------------------------------------
# Test 6: 429 Retry behavior & backoff
# -----------------------------------------------------------------------------

def test_rate_limit_429_success_after_retry():
    """Test 6: HTTP 429 is retried and succeeds on subsequent attempt."""
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            return httpx.Response(429, text="Too Many Requests")
        return httpx.Response(200, json=SAMPLE_RACE_RESULTS_PAYLOAD)

    client, sleeps = _make_client(handler, max_retries=3, backoff_factor=0.1)
    response = client.get_race_results(2024, 1)

    assert response.metadata.total == 2
    assert attempts == 3
    assert len(sleeps) == 2


# -----------------------------------------------------------------------------
# Test 7: 500 / 503 Transient error retries
# -----------------------------------------------------------------------------

def test_transient_500_503_retry_and_recovery():
    """Test 7: HTTP 500 and 503 errors are retried and succeed on 3rd attempt."""
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(500, text="Internal Server Error")
        if attempts == 2:
            return httpx.Response(503, text="Service Unavailable")
        return httpx.Response(200, json=SAMPLE_RACE_RESULTS_PAYLOAD)

    client, sleeps = _make_client(handler, max_retries=3)
    response = client.get_race_results(2024, 1)

    assert response.metadata.total == 2
    assert attempts == 3
    assert len(sleeps) == 2


# -----------------------------------------------------------------------------
# Test 8: Retry limit respected
# -----------------------------------------------------------------------------

def test_retry_limit_exhausted_for_500():
    """Test 8: HTTP 500 fails and raises F1HTTPError after max_retries attempts."""
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(500, text="Persistent Internal Server Error")

    client, sleeps = _make_client(handler, max_retries=2)
    with pytest.raises(F1HTTPError) as exc_info:
        client.get_page("2024/1/results")

    assert exc_info.value.status_code == 500
    assert attempts == 3  # initial attempt + 2 retries
    assert len(sleeps) == 2


def test_retry_limit_exhausted_for_429():
    """Test 8b: Persistent HTTP 429 raises F1RateLimitError after retries exhausted."""
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(429, text="Rate Limited")

    client, sleeps = _make_client(handler, max_retries=2)
    with pytest.raises(F1RateLimitError) as exc_info:
        client.get_page("2024/1/results")

    assert exc_info.value.status_code == 429
    assert attempts == 3
    assert len(sleeps) == 2


# -----------------------------------------------------------------------------
# Test 9: Timeout handling
# -----------------------------------------------------------------------------

def test_timeout_retry_and_exhaustion():
    """Test 9: Request timeouts are retried and eventually raise F1TimeoutError."""
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        raise httpx.ReadTimeout("Connection read timed out")

    client, sleeps = _make_client(handler, max_retries=2)
    with pytest.raises(F1TimeoutError) as exc_info:
        client.get_page("2024/1/results")

    assert "timed out after 2 retries" in str(exc_info.value)
    assert attempts == 3
    assert len(sleeps) == 2


# -----------------------------------------------------------------------------
# Test 10: Pagination across multiple pages
# -----------------------------------------------------------------------------

def test_pagination_iter_pages_and_get_all_records():
    """Test 10: Multi-page endpoints are seamlessly iterated with correct offset progression."""
    requests_made: List[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        offset = request.url.params.get("offset", "0")
        requests_made.append(offset)
        if offset == "0":
            return httpx.Response(200, json=SAMPLE_PITSTOPS_PAGE_1)
        elif offset == "2":
            return httpx.Response(200, json=SAMPLE_PITSTOPS_PAGE_2)
        return httpx.Response(400, text="Unexpected offset")

    client, _ = _make_client(handler)

    # 1. Test iter_pages generator
    pages = list(client.iter_pages("2024/1/pitstops", page_limit=2))
    assert len(pages) == 2
    assert pages[0].metadata.offset == 0
    assert pages[1].metadata.offset == 2
    assert requests_made == ["0", "2"]

    # 2. Test get_all_pit_stops aggregation
    requests_made.clear()
    pit_stops = client.get_all_pit_stops(2024, 1, page_limit=2)
    assert len(pit_stops) == 3
    assert [ps["driverId"] for ps in pit_stops] == ["sainz", "leclerc", "norris"]


# -----------------------------------------------------------------------------
# Test 11: Single-page endpoint behavior
# -----------------------------------------------------------------------------

def test_single_page_endpoint():
    """Test 11: Single-page response stops pagination immediately when total <= limit."""
    requests_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests_count
        requests_count += 1
        return httpx.Response(200, json=SAMPLE_CIRCUITS_PAYLOAD)

    client, _ = _make_client(handler)
    circuits = client.get_all_circuits()

    assert len(circuits) == 1
    assert circuits[0]["circuitId"] == "albert_park"
    assert requests_count == 1


# -----------------------------------------------------------------------------
# Test 12: Retry-After header handling
# -----------------------------------------------------------------------------

def test_retry_after_header_handling():
    """Test 12: Client honors Retry-After header duration on HTTP 429."""
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(429, headers={"Retry-After": "2.5"}, text="Rate Limit")
        return httpx.Response(200, json=SAMPLE_RACE_RESULTS_PAYLOAD)

    client, sleeps = _make_client(handler, max_retries=2)
    response = client.get_race_results(2024, 1)

    assert response.metadata.total == 2
    assert len(sleeps) == 1
    assert sleeps[0] == 2.5


# -----------------------------------------------------------------------------
# Test 13: Convenience methods coverage
# -----------------------------------------------------------------------------

def test_convenience_methods():
    """Test 13: Verify high-level methods construct proper endpoint URLs."""
    urls_hit: List[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        urls_hit.append(request.url.path)
        path = request.url.path
        if "qualifying" in path:
            return httpx.Response(200, json=SAMPLE_QUALIFYING_PAYLOAD)
        elif "sprint" in path:
            return httpx.Response(200, json=SAMPLE_SPRINT_PAYLOAD)
        elif "driverStandings" in path:
            return httpx.Response(200, json=SAMPLE_DRIVER_STANDINGS_PAYLOAD)
        elif "constructorStandings" in path:
            return httpx.Response(200, json=SAMPLE_CONSTRUCTOR_STANDINGS_PAYLOAD)
        elif "laps" in path:
            offset = request.url.params.get("offset", "0")
            if offset == "0":
                return httpx.Response(200, json=SAMPLE_LAPS_PAGE_1)
            return httpx.Response(200, json=SAMPLE_LAPS_PAGE_2)
        return httpx.Response(200, json=SAMPLE_RACE_RESULTS_PAYLOAD)

    client, _ = _make_client(handler)

    # Qualifying
    q_res = client.get_qualifying_results(2024, 1)
    assert q_res.metadata.total == 1
    assert "/ergast/f1/2024/1/qualifying.json" in urls_hit

    # Sprint
    s_res = client.get_sprint_results(2024, 5)
    assert s_res.metadata.total == 1
    assert "/ergast/f1/2024/5/sprint.json" in urls_hit

    # Driver standings
    ds_res = client.get_driver_standings(2024)
    assert ds_res.metadata.total == 1
    assert "/ergast/f1/2024/driverStandings.json" in urls_hit

    # Constructor standings with specific round
    cs_res = client.get_constructor_standings(2024, 1)
    assert cs_res.metadata.total == 1
    assert "/ergast/f1/2024/1/constructorStandings.json" in urls_hit

    # Laps all pages
    laps = client.get_all_lap_times(2024, 1, page_limit=2)
    assert len(laps) == 2


# -----------------------------------------------------------------------------
# Test 14: Context manager lifecycle
# -----------------------------------------------------------------------------

def test_context_manager():
    """Test 14: JolpicaClient supports context manager protocol and closes HTTP session."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=SAMPLE_RACE_RESULTS_PAYLOAD)

    with JolpicaClient(http_client=httpx.Client(transport=httpx.MockTransport(handler))) as client:
        res = client.get_race_results(2024, 1)
        assert res.metadata.total == 2
