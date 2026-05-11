"""Tests for core.registry module."""

import pytest

from core.registry import (
    InputType,
    ModelEndpoint,
    ModelParameter,
    ModelRegistry,
    OutputType,
    register_endpoint,
    registry,
)


@pytest.fixture
def sample_endpoint() -> ModelEndpoint:
    """Create a sample endpoint for testing."""
    return ModelEndpoint(
        model_id="test/test-model",
        action="generation",
        provider="test",
        model_name="test-model",
        description="Test model for unit testing",
        input_types=[InputType.TEXT],
        output_type=OutputType.IMAGE,
        api_path="/vendors/test/v1/test-model/generation",
        result_key="images",
        available_on=["mulerouter"],
        parameters=[
            ModelParameter(
                name="prompt",
                type="string",
                description="Test prompt",
                required=True,
            ),
            ModelParameter(
                name="size",
                type="string",
                description="Output size",
                required=False,
                default="1024x1024",
                enum=["512x512", "1024x1024"],
            ),
        ],
    )


class TestModelParameter:
    """Tests for ModelParameter dataclass."""

    def test_to_dict(self) -> None:
        """Test parameter to_dict conversion."""
        param = ModelParameter(
            name="test_param",
            type="string",
            description="A test parameter",
            required=True,
            default="default_value",
            enum=["a", "b", "c"],
        )

        result = param.to_dict()
        assert result["name"] == "test_param"
        assert result["type"] == "string"
        assert result["description"] == "A test parameter"
        assert result["required"] is True
        assert result["default"] == "default_value"
        assert result["enum"] == ["a", "b", "c"]

    def test_to_dict_minimal(self) -> None:
        """Test parameter to_dict with minimal fields."""
        param = ModelParameter(
            name="simple",
            type="integer",
            description="Simple param",
        )

        result = param.to_dict()
        assert "default" not in result
        assert "enum" not in result


class TestModelEndpoint:
    """Tests for ModelEndpoint dataclass."""

    def test_to_dict(self, sample_endpoint: ModelEndpoint) -> None:
        """Test endpoint to_dict conversion."""
        result = sample_endpoint.to_dict()
        assert result["model_id"] == "test/test-model"
        assert result["action"] == "generation"
        assert result["provider"] == "test"
        assert result["output_type"] == "image"
        assert result["input_types"] == ["text"]
        assert result["api_path"] == "/vendors/test/v1/test-model/generation"


class TestModelRegistry:
    """Tests for ModelRegistry class."""

    def test_singleton(self) -> None:
        """Test registry is a singleton."""
        reg1 = ModelRegistry()
        reg2 = ModelRegistry()
        assert reg1 is reg2

    def test_register_and_get(self, sample_endpoint: ModelEndpoint) -> None:
        """Test registering and retrieving endpoint."""
        reg = ModelRegistry()
        reg.register(sample_endpoint)

        result = reg.get("test/test-model", "generation")
        assert result is sample_endpoint

    def test_get_not_found(self) -> None:
        """Test get returns None for unknown endpoint."""
        reg = ModelRegistry()
        result = reg.get("unknown/model", "unknown")
        assert result is None

    def test_list_all(self, sample_endpoint: ModelEndpoint) -> None:
        """Test list_all returns registered endpoints."""
        reg = ModelRegistry()
        reg.register(sample_endpoint)

        all_endpoints = reg.list_all()
        assert sample_endpoint in all_endpoints

    def test_list_for_endpoint(self, sample_endpoint: ModelEndpoint) -> None:
        """Test filtering by API endpoint."""
        reg = ModelRegistry()
        reg.register(sample_endpoint)

        # Should be found for mulerouter
        mulerouter_endpoints = reg.list_for_endpoint("mulerouter")
        assert sample_endpoint in mulerouter_endpoints

        # Should not be found for mulerun (not in available_on)
        mulerun_endpoints = reg.list_for_endpoint("mulerun")
        assert sample_endpoint not in mulerun_endpoints

    def test_list_by_provider(self, sample_endpoint: ModelEndpoint) -> None:
        """Test filtering by provider."""
        reg = ModelRegistry()
        reg.register(sample_endpoint)

        test_endpoints = reg.list_by_provider("test")
        assert sample_endpoint in test_endpoints

        other_endpoints = reg.list_by_provider("other")
        assert sample_endpoint not in other_endpoints

    def test_list_by_output_type(self, sample_endpoint: ModelEndpoint) -> None:
        """Test filtering by output type."""
        reg = ModelRegistry()
        reg.register(sample_endpoint)

        image_endpoints = reg.list_by_output_type(OutputType.IMAGE)
        assert sample_endpoint in image_endpoints

        video_endpoints = reg.list_by_output_type(OutputType.VIDEO)
        assert sample_endpoint not in video_endpoints


class TestRegisterEndpoint:
    """Tests for register_endpoint function."""

    def test_register_endpoint_function(self, sample_endpoint: ModelEndpoint) -> None:
        """Test register_endpoint helper function."""
        result = register_endpoint(sample_endpoint)
        assert result is sample_endpoint

        # Should be in global registry
        assert registry.get("test/test-model", "generation") is sample_endpoint
