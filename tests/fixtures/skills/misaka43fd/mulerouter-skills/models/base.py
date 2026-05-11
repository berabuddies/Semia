"""Base module for model endpoint implementations."""

import argparse
import json
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

# Support both direct execution and package import
_file_dir = Path(__file__).parent
_root_dir = _file_dir.parent

if str(_root_dir) not in sys.path:
    sys.path.insert(0, str(_root_dir))

from core import (
    APIClient,
    ModelEndpoint,
    TaskResult,
    create_and_poll_task,
    enhance_image_param_description,
    load_config,
    process_image_params,
    register_endpoint,
)


class BaseModelEndpoint(ABC):
    """Base class for model endpoint implementations.

    Provides common functionality for:
    - CLI argument parsing
    - Configuration loading
    - Parameter listing
    - Task execution and polling
    """

    @property
    @abstractmethod
    def endpoint_info(self) -> ModelEndpoint:
        """Return the ModelEndpoint registration info."""
        pass

    def get_parser(self) -> argparse.ArgumentParser:
        """Create argument parser for this endpoint.

        Returns:
            Configured ArgumentParser
        """
        info = self.endpoint_info
        parser = argparse.ArgumentParser(
            description=info.description,
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

        # Meta options
        parser.add_argument(
            "--list-params",
            action="store_true",
            help="List supported parameters and exit",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Output results as JSON",
        )

        # Config options
        parser.add_argument("--api-key", help="API key (overrides environment)")
        parser.add_argument(
            "--base-url",
            help="API base URL (overrides environment and site)",
        )
        parser.add_argument(
            "--site",
            choices=["mulerouter", "mulerun"],
            help="API site (overrides environment, ignored if --base-url is set)",
        )

        # Task options
        parser.add_argument(
            "--no-wait",
            action="store_true",
            help="Don't wait for task completion, return task ID immediately",
        )
        parser.add_argument(
            "--poll-interval",
            type=float,
            default=20.0,
            help="Polling interval in seconds (default: 5.0)",
        )
        parser.add_argument(
            "--max-wait",
            type=float,
            default=600.0,
            help="Maximum wait time in seconds (default: 600.0)",
        )
        parser.add_argument(
            "--quiet",
            action="store_true",
            help="Suppress progress output",
        )

        # Add model-specific parameters
        self._add_model_parameters(parser)

        # Allow arbitrary extra parameters for flexibility
        parser.add_argument(
            "--extra",
            type=str,
            action="append",
            metavar="KEY=VALUE",
            help="Additional parameters as key=value pairs",
        )

        return parser

    def _add_model_parameters(self, parser: argparse.ArgumentParser) -> None:
        """Add model-specific parameters to parser.

        Override in subclasses to add custom parameters.

        Args:
            parser: ArgumentParser to add parameters to
        """
        info = self.endpoint_info
        for param in info.parameters:
            arg_name = f"--{param.name.replace('_', '-')}"
            kwargs: dict[str, Any] = {"help": param.description}

            if param.type == "boolean":
                if param.default is True:
                    parser.add_argument(
                        f"--no-{param.name.replace('_', '-')}",
                        dest=param.name,
                        action="store_false",
                        help=f"Disable {param.name}",
                    )
                else:
                    parser.add_argument(
                        arg_name,
                        action="store_true",
                        help=param.description,
                    )
            else:
                if param.type == "integer":
                    kwargs["type"] = int
                elif param.type == "number":
                    kwargs["type"] = float
                elif param.type == "array":
                    # For array types, accept string and parse as JSON later
                    kwargs["type"] = str

                if param.enum:
                    kwargs["choices"] = param.enum
                if param.default is not None:
                    kwargs["default"] = param.default
                # Note: Don't set required=True here - we validate manually in run()
                # This allows --list-params to work without providing required params

                parser.add_argument(arg_name, **kwargs)

    def list_parameters(self, as_json: bool = False) -> str:
        """Get formatted parameter documentation.

        Args:
            as_json: Return as JSON if True

        Returns:
            Formatted parameter documentation
        """
        info = self.endpoint_info
        params = [p.to_dict() for p in info.parameters]

        if as_json:
            return json.dumps(
                {
                    "model_id": info.model_id,
                    "action": info.action,
                    "api_path": info.api_path,
                    "description": info.description,
                    "parameters": params,
                },
                indent=2,
            )

        lines = [
            f"Model: {info.model_id}",
            f"Action: {info.action}",
            f"API Path: {info.api_path}",
            f"Description: {info.description}",
            "",
            "Parameters:",
            "-" * 60,
        ]

        for p in info.parameters:
            req = "(required)" if p.required else "(optional)"
            default = f" [default: {p.default}]" if p.default is not None else ""
            lines.append(f"  --{p.name.replace('_', '-')} {req}{default}")
            lines.append(f"      Type: {p.type}")
            # Enhance image param descriptions with local file path hint
            desc = enhance_image_param_description(p.name, p.description)
            lines.append(f"      {desc}")
            if p.enum:
                lines.append(f"      Choices: {', '.join(str(e) for e in p.enum)}")
            lines.append("")

        return "\n".join(lines)

    def build_request_body(self, args: argparse.Namespace) -> dict:
        """Build request body from parsed arguments.

        Args:
            args: Parsed arguments

        Returns:
            Request body dictionary
        """
        info = self.endpoint_info
        body: dict[str, Any] = {}

        # Add parameters from model definition
        for param in info.parameters:
            value = getattr(args, param.name, None)
            if value is not None:
                # Parse array types as JSON
                if param.type == "array" and isinstance(value, str):
                    try:
                        value = json.loads(value)
                    except json.JSONDecodeError as e:
                        raise ValueError(f"Invalid JSON for parameter '{param.name}': {e}")
                body[param.name] = value

        # Add extra parameters
        if args.extra:
            for extra in args.extra:
                if "=" in extra:
                    key, value = extra.split("=", 1)
                    # Try to parse as JSON for complex types
                    try:
                        body[key] = json.loads(value)
                    except json.JSONDecodeError:
                        body[key] = value

        return body

    def format_result(self, result: TaskResult, as_json: bool = False) -> str:
        """Format task result for output.

        Args:
            result: TaskResult to format
            as_json: Output as JSON if True

        Returns:
            Formatted result string
        """
        if as_json:
            return json.dumps(
                {
                    "task_id": result.task_id,
                    "status": result.status.value,
                    "results": result.results,
                    "error": result.error,
                },
                indent=2,
            )

        lines = [f"Task ID: {result.task_id}", f"Status: {result.status.value}"]

        if result.error:
            lines.append(f"Error: {result.error}")

        if result.results:
            lines.append(f"\nResults ({result.result_key}):")
            for i, url in enumerate(result.results, 1):
                lines.append(f"  {i}. {url}")

        return "\n".join(lines)

    def run(self, args: list[str] | None = None) -> int:
        """Run the endpoint CLI.

        Args:
            args: Command line arguments (defaults to sys.argv[1:])

        Returns:
            Exit code (0 for success, 1 for failure)
        """
        parser = self.get_parser()
        parsed = parser.parse_args(args)

        # Handle --list-params
        if parsed.list_params:
            print(self.list_parameters(as_json=parsed.json))
            return 0

        # Load configuration
        try:
            config = load_config(
                api_key=parsed.api_key,
                site=parsed.site,
                base_url=getattr(parsed, "base_url", None),
            )
        except ValueError as e:
            print(f"Configuration error: {e}", file=sys.stderr)
            return 1

        # Build request body
        body = self.build_request_body(parsed)

        # Convert local file paths to base64 for image parameters
        body = process_image_params(body)

        # Validate required parameters
        info = self.endpoint_info
        for param in info.parameters:
            if param.required and param.name not in body:
                print(f"Error: --{param.name.replace('_', '-')} is required", file=sys.stderr)
                return 1

        # Execute request
        with APIClient(config) as client:
            if parsed.no_wait:
                # Just create task and return ID
                response = client.post(info.api_path, json=body)
                if not response.success:
                    print(f"Error: {response.error}", file=sys.stderr)
                    return 1

                task_id = (response.data or {}).get("task_info", {}).get("id", "")
                if parsed.json:
                    print(json.dumps({"task_id": task_id}))
                else:
                    print(f"Task ID: {task_id}")
                return 0

            # Create and poll task
            result = create_and_poll_task(
                client=client,
                endpoint_path=info.api_path,
                request_body=body,
                result_key=info.result_key,
                interval=parsed.poll_interval,
                max_wait=parsed.max_wait,
                verbose=not parsed.quiet,
            )

            print(self.format_result(result, as_json=parsed.json))

            return 0 if result.results else 1


def create_endpoint_module(endpoint: ModelEndpoint) -> type[BaseModelEndpoint]:
    """Create a model endpoint class from ModelEndpoint definition.

    This is a factory function that creates endpoint classes dynamically.

    Args:
        endpoint: ModelEndpoint definition

    Returns:
        Endpoint class
    """
    # Register with global registry
    register_endpoint(endpoint)

    class GeneratedEndpoint(BaseModelEndpoint):
        @property
        def endpoint_info(self) -> ModelEndpoint:
            return endpoint

    return GeneratedEndpoint
