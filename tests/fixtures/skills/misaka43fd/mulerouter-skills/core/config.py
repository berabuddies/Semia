"""Configuration management for MuleRouter skill."""

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from dotenv import load_dotenv


class Site(Enum):
    """Supported API sites."""

    MULEROUTER = "mulerouter"
    MULERUN = "mulerun"


@dataclass
class Config:
    """Configuration for MuleRouter API client.

    Attributes:
        api_key: API key for authentication
        site: API site (mulerouter or mulerun), used when base_url is not set
        base_url: Base URL for the API (explicit or auto-derived from site)
        timeout: Request timeout in seconds
        max_retries: Maximum number of retries for failed requests
    """

    api_key: str
    site: Site | None = None
    base_url: str = ""
    timeout: float = 120.0
    max_retries: int = 3

    def __post_init__(self) -> None:
        """Set base_url based on site if not explicitly provided."""
        if not self.base_url:
            if self.site == Site.MULEROUTER:
                self.base_url = "https://api.mulerouter.ai"
            elif self.site == Site.MULERUN:
                self.base_url = "https://api.mulerun.com"
            else:
                raise ValueError(
                    "Either base_url or site must be provided."
                )


def load_env_file(env_file: Path | None = None) -> None:
    """Load .env file if it exists.

    Args:
        env_file: Path to .env file (defaults to current directory)
    """
    if env_file:
        load_dotenv(env_file)
    else:
        env_path = Path(".env")
        if env_path.exists():
            load_dotenv(env_path)


def get_site_from_env() -> Site | None:
    """Get site from environment variable.

    Returns:
        Site enum if MULEROUTER_SITE is set, None otherwise
    """
    site_str = os.getenv("MULEROUTER_SITE")
    if not site_str:
        return None
    try:
        return Site(site_str.lower())
    except ValueError:
        return None


def load_config(
    api_key: str | None = None,
    site: str | None = None,
    base_url: str | None = None,
    env_file: Path | None = None,
) -> Config:
    """Load configuration from environment or parameters.

    Priority: explicit parameters > environment variables > .env file
    For base_url vs site: MULEROUTER_BASE_URL > MULEROUTER_SITE

    Args:
        api_key: Explicit API key (overrides environment)
        site: Explicit site name (overrides environment)
        base_url: Explicit base URL (overrides environment and site)
        env_file: Path to .env file (defaults to current directory)

    Returns:
        Configured Config instance

    Raises:
        ValueError: If API key is not found, or neither base_url nor site is provided
    """
    # Load .env file if it exists
    load_env_file(env_file)

    # Resolve base_url first (highest priority)
    resolved_base_url = base_url or os.getenv("MULEROUTER_BASE_URL")

    # Resolve site (only used if base_url is not set)
    resolved_site: Site | None = None
    if not resolved_base_url:
        site_str = site or os.getenv("MULEROUTER_SITE")
        if not site_str:
            raise ValueError(
                "Configuration not specified. Please set either:\n"
                "  - MULEROUTER_BASE_URL environment variable, or\n"
                "  - MULEROUTER_SITE environment variable to 'mulerouter' or 'mulerun'\n"
                "You can also provide --base-url or --site arguments."
            )

        try:
            resolved_site = Site(site_str.lower())
        except ValueError as err:
            raise ValueError(
                f"Invalid site: {site_str}. Must be 'mulerouter' or 'mulerun'."
            ) from err

    # Resolve API key
    resolved_api_key = api_key or os.getenv("MULEROUTER_API_KEY")
    if not resolved_api_key:
        raise ValueError(
            "API key not found. Please set MULEROUTER_API_KEY environment variable, "
            "or provide it via --api-key argument."
        )

    return Config(
        api_key=resolved_api_key,
        site=resolved_site,
        base_url=resolved_base_url or "",
    )


def get_config_help() -> str:
    """Get help text for configuration."""
    return """
Configuration Options:
---------------------
Environment Variables (Required):
  MULEROUTER_API_KEY    API key for authentication (required)

  One of the following (MULEROUTER_BASE_URL takes priority):
  MULEROUTER_BASE_URL   Custom API base URL (e.g., https://api.example.com)
  MULEROUTER_SITE       API site: 'mulerouter' or 'mulerun'

.env File:
  Create a .env file in the current directory with the above variables.

  Example .env (using site):
    MULEROUTER_SITE=mulerun
    MULEROUTER_API_KEY=your-api-key-here

  Example .env (using custom base URL):
    MULEROUTER_BASE_URL=https://api.custom.example.com
    MULEROUTER_API_KEY=your-api-key-here

Command Line:
  --api-key KEY         Override API key
  --base-url URL        Override base URL (takes priority over --site)
  --site SITE           Override site (mulerouter/mulerun)
"""
