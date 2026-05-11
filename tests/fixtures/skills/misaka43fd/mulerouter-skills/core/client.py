"""HTTP client for MuleRouter API with retry logic and proper headers."""

import time
from dataclasses import dataclass
from typing import Any

import httpx

from .config import Config

# User agent identifying requests from Agent Skills
USER_AGENT = "MuleRouter-AgentSkill/1.0.0"


@dataclass
class APIResponse:
    """Standardized API response wrapper.

    Attributes:
        success: Whether the request was successful
        data: Response data (if successful)
        error: Error message (if failed)
        status_code: HTTP status code
        traceparent: Traceparent header for debugging
    """

    success: bool
    data: dict | None = None
    error: str | None = None
    status_code: int = 0
    traceparent: str | None = None


class APIClient:
    """HTTP client for MuleRouter/MuleRun API.

    Features:
    - Automatic retries with exponential backoff
    - Proper authentication headers
    - Agent Skills identification via User-Agent
    - Timeout handling
    """

    def __init__(self, config: Config) -> None:
        """Initialize API client.

        Args:
            config: Configuration instance with API key and endpoint settings
        """
        self.config = config
        self._client: httpx.Client | None = None

    @property
    def client(self) -> httpx.Client:
        """Lazy-initialize and return HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.config.base_url,
                timeout=httpx.Timeout(self.config.timeout),
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": USER_AGENT,
                    "X-Agent-Skills": "mulerouter",
                },
            )
        return self._client

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> "APIClient":
        """Context manager entry."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self.close()

    def _handle_response(self, response: httpx.Response) -> APIResponse:
        """Handle HTTP response and convert to APIResponse.

        Args:
            response: httpx Response object

        Returns:
            Standardized APIResponse
        """
        traceparent = response.headers.get("traceparent")

        try:
            data = response.json()
        except Exception:
            data = None

        if response.is_success:
            return APIResponse(
                success=True,
                data=data,
                status_code=response.status_code,
                traceparent=traceparent,
            )

        # Extract error message
        error_msg = f"HTTP {response.status_code}"
        if data:
            if "detail" in data:
                error_msg = data["detail"]
            elif "error" in data:
                error_msg = data["error"]
            elif "message" in data:
                error_msg = data["message"]
            elif "task_info" in data and "error" in data["task_info"]:
                err = data["task_info"]["error"]
                error_msg = err.get("detail", err.get("title", str(err)))

        return APIResponse(
            success=False,
            data=data,
            error=error_msg,
            status_code=response.status_code,
            traceparent=traceparent,
        )

    def _should_retry(self, response: httpx.Response) -> bool:
        """Determine if request should be retried.

        Args:
            response: httpx Response object

        Returns:
            True if request should be retried
        """
        # Retry on server errors and rate limiting
        return response.status_code in (429, 500, 502, 503, 504)

    def request(
        self,
        method: str,
        path: str,
        json: dict | None = None,
        params: dict | None = None,
    ) -> APIResponse:
        """Make HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: API path (e.g., /vendors/google/v1/nano-banana-pro/generation)
            json: JSON body for POST requests
            params: Query parameters

        Returns:
            APIResponse with result or error
        """
        last_response: APIResponse | None = None

        for attempt in range(self.config.max_retries + 1):
            try:
                response = self.client.request(
                    method=method,
                    url=path,
                    json=json,
                    params=params,
                )

                if response.is_success or not self._should_retry(response):
                    return self._handle_response(response)

                last_response = self._handle_response(response)

            except httpx.TimeoutException:
                last_response = APIResponse(
                    success=False,
                    error=f"Request timeout after {self.config.timeout}s",
                    status_code=0,
                )
            except httpx.RequestError as e:
                last_response = APIResponse(
                    success=False,
                    error=f"Request error: {e}",
                    status_code=0,
                )

            # Exponential backoff before retry
            if attempt < self.config.max_retries:
                wait_time = 2**attempt
                time.sleep(wait_time)

        return last_response or APIResponse(
            success=False,
            error="Max retries exceeded",
            status_code=0,
        )

    def post(self, path: str, json: dict | None = None) -> APIResponse:
        """Make POST request.

        Args:
            path: API path
            json: JSON body

        Returns:
            APIResponse with result or error
        """
        return self.request("POST", path, json=json)

    def get(self, path: str, params: dict | None = None) -> APIResponse:
        """Make GET request.

        Args:
            path: API path
            params: Query parameters

        Returns:
            APIResponse with result or error
        """
        return self.request("GET", path, params=params)
