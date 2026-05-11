"""Tests for core.client module."""

import httpx
import pytest
import respx

from core.client import APIClient, APIResponse
from core.config import Config, Site


@pytest.fixture
def config() -> Config:
    """Create test config."""
    return Config(api_key="test-api-key", site=Site.MULEROUTER)


@pytest.fixture
def client(config: Config) -> APIClient:
    """Create test API client."""
    return APIClient(config)


class TestAPIResponse:
    """Tests for APIResponse dataclass."""

    def test_success_response(self) -> None:
        """Test successful response."""
        response = APIResponse(
            success=True,
            data={"task_info": {"id": "123"}},
            status_code=200,
        )
        assert response.success is True
        assert response.data == {"task_info": {"id": "123"}}
        assert response.error is None

    def test_error_response(self) -> None:
        """Test error response."""
        response = APIResponse(
            success=False,
            error="Not found",
            status_code=404,
        )
        assert response.success is False
        assert response.error == "Not found"


class TestAPIClient:
    """Tests for APIClient class."""

    def test_client_initialization(self, client: APIClient, config: Config) -> None:
        """Test client initialization."""
        assert client.config == config
        assert client._client is None  # Lazy initialization

    def test_client_headers(self, client: APIClient) -> None:
        """Test that client has proper headers."""
        http_client = client.client
        assert "Authorization" in http_client.headers
        assert http_client.headers["Authorization"] == "Bearer test-api-key"
        assert "User-Agent" in http_client.headers
        assert "MuleRouter-AgentSkill" in http_client.headers["User-Agent"]
        assert http_client.headers["X-Agent-Skills"] == "mulerouter"

    def test_client_context_manager(self, config: Config) -> None:
        """Test client context manager."""
        with APIClient(config) as client:
            assert client._client is None
            _ = client.client  # Initialize
            assert client._client is not None
        assert client._client is None

    @respx.mock
    def test_post_success(self, client: APIClient) -> None:
        """Test successful POST request."""
        respx.post("https://api.mulerouter.ai/test").mock(
            return_value=httpx.Response(
                200,
                json={"task_info": {"id": "123", "status": "pending"}},
            )
        )

        response = client.post("/test", json={"prompt": "test"})
        assert response.success is True
        assert response.data["task_info"]["id"] == "123"

    @respx.mock
    def test_get_success(self, client: APIClient) -> None:
        """Test successful GET request."""
        respx.get("https://api.mulerouter.ai/test/123").mock(
            return_value=httpx.Response(
                200,
                json={"task_info": {"id": "123", "status": "completed"}},
            )
        )

        response = client.get("/test/123")
        assert response.success is True
        assert response.data["task_info"]["status"] == "completed"

    @respx.mock
    def test_error_response_handling(self, client: APIClient) -> None:
        """Test error response handling."""
        respx.post("https://api.mulerouter.ai/test").mock(
            return_value=httpx.Response(
                400,
                json={"detail": "Invalid prompt"},
            )
        )

        response = client.post("/test", json={})
        assert response.success is False
        assert response.error == "Invalid prompt"
        assert response.status_code == 400

    @respx.mock
    def test_traceparent_header(self, client: APIClient) -> None:
        """Test traceparent header extraction."""
        respx.get("https://api.mulerouter.ai/test").mock(
            return_value=httpx.Response(
                200,
                json={},
                headers={"traceparent": "00-trace-id-123"},
            )
        )

        response = client.get("/test")
        assert response.traceparent == "00-trace-id-123"
