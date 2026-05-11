"""List available models from the registry.

Usage:
    python scripts/list_models.py [--provider PROVIDER] [--output-type TYPE] [--json]

Note: Models are automatically filtered based on MULEROUTER_SITE environment variable.
"""

import argparse
import importlib.util
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
_script_dir = Path(__file__).parent
_root_dir = _script_dir.parent
_models_dir = _root_dir / "models"
sys.path.insert(0, str(_root_dir))

from core import OutputType, get_site_from_env, load_env_file, registry


def _import_provider_models() -> None:
    """Import all provider model packages to register endpoints."""
    providers = ["alibaba", "google", "midjourney", "openai"]

    for provider in providers:
        provider_dir = _models_dir / provider
        init_file = provider_dir / "__init__.py"

        if not init_file.exists():
            continue

        spec = importlib.util.spec_from_file_location(
            f"models.{provider}",
            init_file,
        )
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)


# Import all models to ensure they're registered
_import_provider_models()


def list_models(
    site: str | None = None,
    provider: str | None = None,
    output_type: str | None = None,
) -> list[dict]:
    """List available models with optional filtering.

    Args:
        site: Filter by API site (mulerouter/mulerun)
        provider: Filter by provider (alibaba/google)
        output_type: Filter by output type (image/video/text)

    Returns:
        List of model endpoint dictionaries
    """
    endpoints = registry.list_all()

    # Apply filters
    if site:
        endpoints = [e for e in endpoints if site in e.available_on]

    if provider:
        endpoints = [e for e in endpoints if e.provider == provider]

    if output_type:
        try:
            ot = OutputType(output_type)
            endpoints = [e for e in endpoints if e.output_type == ot]
        except ValueError:
            pass

    return [e.to_dict() for e in endpoints]


def format_models_text(models: list[dict], site: str | None = None) -> str:
    """Format models as human-readable text.

    Args:
        models: List of model dictionaries
        site: Current site for display

    Returns:
        Formatted text output
    """
    if not models:
        return "No models found."

    header = "Available Models"
    if site:
        header += f" ({site})"

    lines = [
        header,
        "=" * 60,
    ]

    # Group by provider
    by_provider: dict[str, list[dict]] = {}
    for m in models:
        provider = m["provider"]
        if provider not in by_provider:
            by_provider[provider] = []
        by_provider[provider].append(m)

    for provider, provider_models in sorted(by_provider.items()):
        lines.append(f"\n[{provider.upper()}]")
        lines.append("-" * 40)

        for m in sorted(provider_models, key=lambda x: (x["model_id"], x["action"])):
            lines.append(f"\n  {m['model_id']}/{m['action']}")
            lines.append(f"    Description: {m['description']}")
            lines.append(f"    Output: {m['output_type']}")

    lines.append("")
    lines.append(f"Total: {len(models)} endpoint(s)")

    return "\n".join(lines)


def main() -> int:
    """CLI entry point."""
    # Load environment first
    load_env_file()

    parser = argparse.ArgumentParser(
        description="List available MuleRouter models",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--provider",
        help="Filter by provider (e.g., alibaba, google)",
    )
    parser.add_argument(
        "--output-type",
        choices=["image", "video", "text", "audio"],
        help="Filter by output type",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    parser.add_argument(
        "--providers",
        action="store_true",
        help="List available providers only",
    )

    args = parser.parse_args()

    # Get site from environment
    site_enum = get_site_from_env()
    site = site_enum.value if site_enum else None

    if not site:
        print(
            "Warning: MULEROUTER_SITE not set. Showing all models.\n"
            "Set MULEROUTER_SITE=mulerouter or MULEROUTER_SITE=mulerun to filter.\n",
            file=sys.stderr,
        )

    # If providers flag, just list providers
    if args.providers:
        providers = registry.get_providers()
        if args.json:
            print(json.dumps({"providers": providers}, indent=2))
        else:
            print("Available Providers:")
            for p in providers:
                print(f"  - {p}")
        return 0

    # List models (filtered by site if set)
    models = list_models(
        site=site,
        provider=args.provider,
        output_type=args.output_type,
    )

    if args.json:
        print(json.dumps({"models": models, "site": site}, indent=2))
    else:
        print(format_models_text(models, site))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
