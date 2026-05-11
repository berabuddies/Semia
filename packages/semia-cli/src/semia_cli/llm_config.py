# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 berabuddies
"""Configuration shared by Semia LLM synthesis modules.

Semia routes synthesis through one of four **providers**:

HTTP wire formats (use ``--base-url`` and the matching ``*_API_KEY``):

- ``responses`` — OpenAI Responses API
  (``POST {OPENAI_BASE_URL}/responses``). Works against any endpoint that
  speaks the protocol: api.openai.com, DeepSeek, OpenRouter, vLLM, etc.
- ``anthropic`` — Anthropic Messages API
  (``POST {ANTHROPIC_BASE_URL}/v1/messages``). Works against
  api.anthropic.com and Anthropic-compatible relays.

Local CLI shell-outs (only ``--model`` is effective; auth is inherited from
the host CLI's config):

- ``codex`` — pipes the prompt into ``codex exec``.
- ``claude`` — pipes the prompt into ``claude --print``.

The **model** is a free-form string (``gpt-5.5``, ``gpt-5.4``,
``gpt-5.3-codex``, ``deepseek-v4``, ``claude-opus-4-7``,
``claude-opus-4-6``, …). Semia does not validate the model name; that is
the endpoint or CLI's job. The default depends on provider — see
:func:`default_model`.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class LlmSynthesisError(RuntimeError):
    """Raised when synthesis cannot produce usable facts."""


class LlmSynthesisConfigError(LlmSynthesisError):
    """Raised when the synthesis cannot start because the environment is
    misconfigured (missing API key, unknown provider, missing CLI binary).

    The retry layer treats this as non-retryable — retrying will not make a
    missing ``OPENAI_API_KEY`` appear.
    """


# Providers fall into two transport classes.
PROVIDER_RESPONSES = "responses"
PROVIDER_ANTHROPIC = "anthropic"
PROVIDER_CODEX = "codex"
PROVIDER_CLAUDE = "claude"

HTTP_PROVIDERS = (PROVIDER_RESPONSES, PROVIDER_ANTHROPIC)
CLI_PROVIDERS = (PROVIDER_CODEX, PROVIDER_CLAUDE)
SUPPORTED_PROVIDERS = HTTP_PROVIDERS + CLI_PROVIDERS

DEFAULT_PROVIDER = PROVIDER_RESPONSES

# Per-provider default model. ``responses`` uses a forward-looking sentinel;
# any provider can be overridden with ``--model`` or ``SEMIA_LLM_MODEL``.
# ``codex`` has no default — when omitted, the host CLI picks.
DEFAULT_MODEL_RESPONSES = "gpt-5.5"
DEFAULT_MODEL_ANTHROPIC = "claude-opus-4-7"
DEFAULT_MODEL_CLAUDE = "claude-opus-4-7"
DEFAULT_MODEL_CODEX: str | None = None

# Top-level default exported for callers that just want "some default".
DEFAULT_MODEL = DEFAULT_MODEL_RESPONSES

# Per-format default base URLs. Only meaningful for HTTP providers; ignored
# for ``codex``/``claude``. Override via env or ``--base-url``.
DEFAULT_RESPONSES_BASE_URL = "https://api.openai.com/v1"
DEFAULT_ANTHROPIC_BASE_URL = "https://api.anthropic.com"

DEFAULT_TIMEOUT_SECONDS = 600
DEFAULT_SYNTHESIS_ITERATIONS = 5
DEFAULT_SYNTHESIS_MAX_RETRIES = 3
DEFAULT_PLATEAU_MIN_IMPROVEMENT = 0.01
DEFAULT_PLATEAU_PATIENCE = 3
DEFAULT_MAX_DOC_BYTES = 2 * 1024 * 1024
DEFAULT_SYNTHESIS_CEILING = 0.9
DEFAULT_SCORE_WEIGHTS = (0.5, 0.3, 0.2)
SYNTHESIZED_FACTS = "synthesized_facts.dl"
SYNTHESIS_METADATA = "synthesis_metadata.json"
_DOTENV_LOADED = False

# Aliases accepted on the CLI / in env for ergonomics.
_PROVIDER_ALIASES = {
    "openai": PROVIDER_RESPONSES,
}

Validator = Callable[[Path, Path], dict[str, Any]]


# Backwards-compat aliases retained so older imports keep working.
DEFAULT_OPENAI_MODEL = DEFAULT_MODEL_RESPONSES
DEFAULT_ANTHROPIC_MODEL = DEFAULT_MODEL_ANTHROPIC


@dataclass(frozen=True)
class SynthesisConfig:
    """Resolved synthesis target.

    ``base_url`` is only consumed by HTTP providers (``responses`` /
    ``anthropic``). CLI providers (``codex`` / ``claude``) ignore it.
    """

    provider: str
    model: str | None
    base_url: str | None = None


@dataclass(frozen=True)
class SynthesisSettings:
    iterations: int
    max_retries: int
    provider_retries: int
    plateau_min_improvement: float
    plateau_patience: int
    max_doc_bytes: int
    ceiling: float
    score_weights: tuple[float, float, float]

    @classmethod
    def from_env(cls) -> SynthesisSettings:
        load_dotenv()
        return cls(
            iterations=_env_int("SEMIA_SYNTHESIS_N_ITERATIONS", DEFAULT_SYNTHESIS_ITERATIONS),
            max_retries=_env_int("SEMIA_SYNTHESIS_MAX_RETRIES", DEFAULT_SYNTHESIS_MAX_RETRIES),
            provider_retries=_env_int("SEMIA_LLM_MAX_RETRIES", 2),
            plateau_min_improvement=_env_float(
                "SEMIA_SYNTHESIS_PLATEAU_MIN_IMPROVEMENT",
                DEFAULT_PLATEAU_MIN_IMPROVEMENT,
            ),
            plateau_patience=_env_int("SEMIA_SYNTHESIS_PLATEAU_PATIENCE", DEFAULT_PLATEAU_PATIENCE),
            max_doc_bytes=_env_int("SEMIA_SYNTHESIS_MAX_DOC_BYTES", DEFAULT_MAX_DOC_BYTES),
            ceiling=_env_float("SEMIA_SYNTHESIS_CEILING", DEFAULT_SYNTHESIS_CEILING),
            score_weights=_env_weights("SEMIA_SYNTHESIS_SCORE_WEIGHTS", DEFAULT_SCORE_WEIGHTS),
        )


def default_provider(value: str | None = None) -> str:
    """Resolve the provider from flag/env/default.

    Precedence: explicit ``value`` > ``SEMIA_LLM_PROVIDER`` env >
    :data:`DEFAULT_PROVIDER`. The alias ``openai`` is accepted as a synonym
    for ``responses``.
    """

    load_dotenv()
    raw = value or os.environ.get("SEMIA_LLM_PROVIDER")
    if not raw:
        return DEFAULT_PROVIDER
    normalized = raw.strip().lower()
    normalized = _PROVIDER_ALIASES.get(normalized, normalized)
    if normalized not in SUPPORTED_PROVIDERS:
        raise LlmSynthesisConfigError(
            f"unknown provider {raw!r}; expected one of {SUPPORTED_PROVIDERS} "
            f"(plus alias {sorted(_PROVIDER_ALIASES)})"
        )
    return normalized


def default_model(value: str | None = None, provider: str | None = None) -> str | None:
    """Resolve the model name.

    Precedence: explicit ``value`` > ``SEMIA_LLM_MODEL`` > provider-specific
    env (``ANTHROPIC_MODEL`` for ``anthropic``/``claude``, ``OPENAI_MODEL``
    for ``responses``) > provider-specific default. The model is free-form:
    any string accepted by the chosen endpoint is valid.

    Returns ``None`` only for ``codex`` when no override is set (codex CLI
    will use its own default).
    """

    load_dotenv()
    configured = value or os.environ.get("SEMIA_LLM_MODEL")
    if configured:
        return configured
    if provider == PROVIDER_RESPONSES:
        return os.environ.get("OPENAI_MODEL") or DEFAULT_MODEL_RESPONSES
    if provider == PROVIDER_ANTHROPIC:
        return os.environ.get("ANTHROPIC_MODEL") or DEFAULT_MODEL_ANTHROPIC
    if provider == PROVIDER_CLAUDE:
        return os.environ.get("ANTHROPIC_MODEL") or DEFAULT_MODEL_CLAUDE
    if provider == PROVIDER_CODEX:
        return DEFAULT_MODEL_CODEX
    return os.environ.get("OPENAI_MODEL") or DEFAULT_MODEL_RESPONSES


def default_base_url(value: str | None = None, provider: str = DEFAULT_PROVIDER) -> str | None:
    """Resolve the base URL for an HTTP provider.

    Returns ``None`` for CLI providers (``codex`` / ``claude``) — they do not
    use a base URL.

    Precedence (HTTP only): explicit ``value`` > provider-specific env
    (``OPENAI_BASE_URL`` for ``responses``, ``ANTHROPIC_BASE_URL`` for
    ``anthropic``) > provider-specific default.
    """

    if provider not in HTTP_PROVIDERS:
        return None
    load_dotenv()
    if value:
        return value.rstrip("/")
    if provider == PROVIDER_ANTHROPIC:
        return (os.environ.get("ANTHROPIC_BASE_URL") or DEFAULT_ANTHROPIC_BASE_URL).rstrip("/")
    return (os.environ.get("OPENAI_BASE_URL") or DEFAULT_RESPONSES_BASE_URL).rstrip("/")


def timeout_seconds() -> int:
    load_dotenv()
    return _env_int("SEMIA_LLM_TIMEOUT", DEFAULT_TIMEOUT_SECONDS)


def load_dotenv(path: Path | None = None) -> None:
    """Load a local .env file once, without overriding exported variables."""

    global _DOTENV_LOADED
    if _DOTENV_LOADED and path is None:
        return
    env_path = path or Path.cwd() / ".env"
    if not env_path.exists():
        return
    if path is None:
        _DOTENV_LOADED = True
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        key, raw_value = line.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue
        os.environ[key] = _parse_dotenv_value(raw_value.strip())


def _reset_dotenv_for_tests() -> None:
    """Reset the once-only .env load latch. Intended for test setup/teardown."""

    global _DOTENV_LOADED
    _DOTENV_LOADED = False


def _parse_dotenv_value(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    return value.replace("\\n", "\n")


def _env_int(name: str, default: int) -> int:
    load_dotenv()
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    load_dotenv()
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_weights(name: str, default: tuple[float, float, float]) -> tuple[float, float, float]:
    """Parse a ``match,support,reference`` triplet of comma-separated floats.

    Falls back to ``default`` on missing or malformed input.
    """

    load_dotenv()
    raw = os.environ.get(name)
    if not raw:
        return default
    parts = [piece.strip() for piece in raw.split(",")]
    if len(parts) != 3:
        return default
    try:
        return (float(parts[0]), float(parts[1]), float(parts[2]))
    except ValueError:
        return default
