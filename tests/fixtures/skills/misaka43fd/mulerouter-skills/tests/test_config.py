"""Tests for core.config module."""

import os
from unittest.mock import patch

import pytest

from core.config import Config, Site, get_config_help, load_config


class TestConfig:
    """Tests for Config dataclass."""

    def test_config_mulerouter_site(self) -> None:
        """Test Config with mulerouter site."""
        config = Config(api_key="test-key", site=Site.MULEROUTER)
        assert config.base_url == "https://api.mulerouter.ai"
        assert config.api_key == "test-key"
        assert config.site == Site.MULEROUTER

    def test_config_mulerun_site(self) -> None:
        """Test Config with mulerun site."""
        config = Config(api_key="test-key", site=Site.MULERUN)
        assert config.base_url == "https://api.mulerun.com"
        assert config.site == Site.MULERUN

    def test_config_explicit_base_url(self) -> None:
        """Test Config with explicit base_url (takes priority over site)."""
        config = Config(api_key="test-key", base_url="https://custom.api.com")
        assert config.base_url == "https://custom.api.com"
        assert config.site is None

    def test_config_base_url_overrides_site(self) -> None:
        """Test that explicit base_url overrides site."""
        config = Config(api_key="test-key", site=Site.MULEROUTER, base_url="https://custom.api.com")
        assert config.base_url == "https://custom.api.com"

    def test_config_defaults(self) -> None:
        """Test Config default values."""
        config = Config(api_key="test-key", site=Site.MULEROUTER)
        assert config.timeout == 120.0
        assert config.max_retries == 3

    def test_config_missing_both_site_and_base_url(self) -> None:
        """Test Config raises error when both site and base_url are missing."""
        with pytest.raises(ValueError, match="Either base_url or site must be provided"):
            Config(api_key="test-key")


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_config_explicit_api_key(self) -> None:
        """Test loading config with explicit API key."""
        config = load_config(api_key="explicit-key", site="mulerouter")
        assert config.api_key == "explicit-key"

    def test_load_config_from_env(self) -> None:
        """Test loading config from environment variables."""
        with patch.dict(
            os.environ,
            {"MULEROUTER_API_KEY": "env-key", "MULEROUTER_SITE": "mulerouter"},
            clear=True,
        ):
            config = load_config()
            assert config.api_key == "env-key"
            assert config.site == Site.MULEROUTER

    def test_load_config_explicit_site(self) -> None:
        """Test loading config with explicit site."""
        config = load_config(api_key="key", site="mulerun")
        assert config.site == Site.MULERUN

    def test_load_config_env_site(self) -> None:
        """Test loading config from MULEROUTER_SITE env var."""
        with patch.dict(
            os.environ,
            {"MULEROUTER_API_KEY": "key", "MULEROUTER_SITE": "mulerun"},
            clear=True,
        ):
            config = load_config()
            assert config.site == Site.MULERUN

    def test_load_config_explicit_base_url(self) -> None:
        """Test loading config with explicit base_url."""
        config = load_config(api_key="key", base_url="https://custom.api.com")
        assert config.base_url == "https://custom.api.com"
        assert config.site is None

    def test_load_config_env_base_url(self) -> None:
        """Test loading config from MULEROUTER_BASE_URL env var."""
        with patch.dict(
            os.environ,
            {"MULEROUTER_API_KEY": "key", "MULEROUTER_BASE_URL": "https://custom.api.com"},
            clear=True,
        ):
            config = load_config()
            assert config.base_url == "https://custom.api.com"
            assert config.site is None

    def test_load_config_base_url_priority_over_site(self) -> None:
        """Test that MULEROUTER_BASE_URL takes priority over MULEROUTER_SITE."""
        with patch.dict(
            os.environ,
            {
                "MULEROUTER_API_KEY": "key",
                "MULEROUTER_BASE_URL": "https://custom.api.com",
                "MULEROUTER_SITE": "mulerun",
            },
            clear=True,
        ):
            config = load_config()
            assert config.base_url == "https://custom.api.com"
            # site should be None because base_url takes priority
            assert config.site is None

    def test_load_config_missing_api_key(self) -> None:
        """Test that missing API key raises ValueError."""
        with (
            patch.dict(os.environ, {"MULEROUTER_SITE": "mulerouter"}, clear=True),
            pytest.raises(ValueError, match="API key not found"),
        ):
            load_config()

    def test_load_config_missing_both_site_and_base_url(self) -> None:
        """Test that missing both site and base_url raises ValueError."""
        with (
            patch.dict(os.environ, {"MULEROUTER_API_KEY": "key"}, clear=True),
            pytest.raises(ValueError, match="Configuration not specified"),
        ):
            load_config()

    def test_load_config_invalid_site(self) -> None:
        """Test that invalid site raises ValueError."""
        with pytest.raises(ValueError, match="Invalid site"):
            load_config(api_key="key", site="invalid")


class TestGetConfigHelp:
    """Tests for get_config_help function."""

    def test_get_config_help_content(self) -> None:
        """Test that config help contains expected content."""
        help_text = get_config_help()
        assert "MULEROUTER_API_KEY" in help_text
        assert "MULEROUTER_SITE" in help_text
        assert "MULEROUTER_BASE_URL" in help_text
        assert ".env" in help_text
