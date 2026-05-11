"""Model registry for tracking available models and their capabilities."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class OutputType(Enum):
    """Type of output produced by a model."""

    IMAGE = "image"
    VIDEO = "video"
    TEXT = "text"
    AUDIO = "audio"


class InputType(Enum):
    """Type of input accepted by a model."""

    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"


@dataclass
class ModelParameter:
    """Parameter definition for a model endpoint.

    Attributes:
        name: Parameter name
        type: Parameter type (string, integer, boolean, etc.)
        description: Parameter description
        required: Whether the parameter is required
        default: Default value
        enum: List of allowed values (if applicable)
    """

    name: str
    type: str
    description: str
    required: bool = False
    default: Any = None
    enum: list[Any] | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        result = {
            "name": self.name,
            "type": self.type,
            "description": self.description,
            "required": self.required,
        }
        if self.default is not None:
            result["default"] = self.default
        if self.enum:
            result["enum"] = self.enum
        return result


@dataclass
class ModelEndpoint:
    """Registration info for a model endpoint.

    Attributes:
        model_id: Unique model identifier (e.g., alibaba/wan2.6-t2v)
        action: Endpoint action (e.g., generation, edit)
        provider: Provider name (e.g., alibaba, google)
        model_name: Model name (e.g., wan2.6-t2v)
        description: Human-readable description
        input_types: Types of inputs accepted
        output_type: Type of output produced
        api_path: RESTful API path
        parameters: List of supported parameters
        available_on: List of endpoints where this model is available
        result_key: Key in response containing results (images/videos)
    """

    model_id: str
    action: str
    provider: str
    model_name: str
    description: str
    input_types: list[InputType]
    output_type: OutputType
    api_path: str
    parameters: list[ModelParameter] = field(default_factory=list)
    available_on: list[str] = field(default_factory=lambda: ["mulerouter", "mulerun"])
    result_key: str = "images"

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "model_id": self.model_id,
            "action": self.action,
            "provider": self.provider,
            "model_name": self.model_name,
            "description": self.description,
            "input_types": [t.value for t in self.input_types],
            "output_type": self.output_type.value,
            "api_path": self.api_path,
            "available_on": self.available_on,
            "result_key": self.result_key,
        }


class ModelRegistry:
    """Registry for tracking available models and endpoints.

    This is a singleton that models register themselves with at import time.
    """

    _instance: Optional["ModelRegistry"] = None
    _endpoints: dict[str, ModelEndpoint]

    def __new__(cls) -> "ModelRegistry":
        """Create singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._endpoints = {}
        return cls._instance

    def register(self, endpoint: ModelEndpoint) -> None:
        """Register a model endpoint.

        Args:
            endpoint: ModelEndpoint to register
        """
        key = f"{endpoint.model_id}/{endpoint.action}"
        self._endpoints[key] = endpoint

    def get(self, model_id: str, action: str) -> ModelEndpoint | None:
        """Get a registered endpoint.

        Args:
            model_id: Model identifier
            action: Endpoint action

        Returns:
            ModelEndpoint if found, None otherwise
        """
        key = f"{model_id}/{action}"
        return self._endpoints.get(key)

    def list_all(self) -> list[ModelEndpoint]:
        """List all registered endpoints.

        Returns:
            List of all registered ModelEndpoints
        """
        return list(self._endpoints.values())

    def list_for_endpoint(self, endpoint_name: str) -> list[ModelEndpoint]:
        """List endpoints available on a specific API endpoint.

        Args:
            endpoint_name: 'mulerouter' or 'mulerun'

        Returns:
            List of ModelEndpoints available on that endpoint
        """
        return [e for e in self._endpoints.values() if endpoint_name in e.available_on]

    def list_by_provider(self, provider: str) -> list[ModelEndpoint]:
        """List endpoints for a specific provider.

        Args:
            provider: Provider name (e.g., 'alibaba', 'google')

        Returns:
            List of ModelEndpoints from that provider
        """
        return [e for e in self._endpoints.values() if e.provider == provider]

    def list_by_output_type(self, output_type: OutputType) -> list[ModelEndpoint]:
        """List endpoints by output type.

        Args:
            output_type: Type of output (IMAGE, VIDEO, etc.)

        Returns:
            List of ModelEndpoints producing that output type
        """
        return [e for e in self._endpoints.values() if e.output_type == output_type]

    def get_providers(self) -> list[str]:
        """Get list of unique providers.

        Returns:
            List of provider names
        """
        return sorted(set(e.provider for e in self._endpoints.values()))

    def get_models(self) -> list[str]:
        """Get list of unique model IDs.

        Returns:
            List of model IDs
        """
        return sorted(set(e.model_id for e in self._endpoints.values()))


# Global registry instance
registry = ModelRegistry()


def register_endpoint(endpoint: ModelEndpoint) -> ModelEndpoint:
    """Register an endpoint with the global registry.

    Args:
        endpoint: ModelEndpoint to register

    Returns:
        The registered endpoint (for chaining)
    """
    registry.register(endpoint)
    return endpoint
