"""F1 Race Intelligence — Jolpica API client exceptions."""

from typing import Optional


class F1APIError(Exception):
    """Base exception for all Jolpica F1 API client errors."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class F1HTTPError(F1APIError):
    """Raised when an HTTP error occurs (e.g., 4xx, 5xx after retries are exhausted)."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_text: Optional[str] = None,
        endpoint: Optional[str] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text
        self.endpoint = endpoint


class F1RateLimitError(F1HTTPError):
    """Raised when the rate limit (HTTP 429) is encountered and retries are exhausted."""

    def __init__(
        self,
        message: str,
        status_code: int = 429,
        response_text: Optional[str] = None,
        endpoint: Optional[str] = None,
        retry_after: Optional[float] = None,
    ):
        super().__init__(
            message=message,
            status_code=status_code,
            response_text=response_text,
            endpoint=endpoint,
        )
        self.retry_after = retry_after


class F1TimeoutError(F1APIError):
    """Raised when an HTTP request times out and retries are exhausted."""

    def __init__(self, message: str, endpoint: Optional[str] = None):
        super().__init__(message)
        self.endpoint = endpoint


class F1ResponseError(F1APIError):
    """Raised when the API response is malformed JSON or lacks the expected MRData envelope."""

    def __init__(
        self,
        message: str,
        endpoint: Optional[str] = None,
        raw_payload: Optional[str] = None,
    ):
        super().__init__(message)
        self.endpoint = endpoint
        self.raw_payload = raw_payload
