"""F1 Race Intelligence — Jolpica API client types and configuration data structures."""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class ClientConfig:
    """Configuration settings for the Jolpica API client."""

    base_url: str = "https://api.jolpi.ca/ergast/f1"
    timeout: float = 15.0
    max_retries: int = 3
    backoff_factor: float = 0.5
    max_backoff: float = 10.0
    headers: Dict[str, str] = field(
        default_factory=lambda: {
            "Accept": "application/json",
            "User-Agent": "F1-Race-Intelligence/0.1.0",
        }
    )


@dataclass(frozen=True)
class PageMetadata:
    """Metadata extracted from the top-level MRData envelope."""

    limit: int
    offset: int
    total: int
    url: str


@dataclass(frozen=True)
class APIResponse:
    """Standardized client response containing metadata and decoded resource payload."""

    metadata: PageMetadata
    data: Dict[str, Any]
    raw: Dict[str, Any]
