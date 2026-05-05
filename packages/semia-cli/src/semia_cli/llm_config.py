"""Configuration shared by Semia LLM synthesis modules."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
import os
from pathlib import Path
from typing import Any


class LlmSynthesisError(RuntimeError):
    """Raised when synthesis cannot produce usable facts."""


DEFAULT_OPENAI_MODEL = "gpt-5.5"
DEFAULT_TIMEOUT_SECONDS = 600
DEFAULT_SYNTHESIS_ITERATIONS = 5
DEFAULT_SYNTHESIS_MAX_RETRIES = 3
DEFAULT_PLATEAU_MIN_IMPROVEMENT = 0.01
DEFAULT_PLATEAU_PATIENCE = 3
DEFAULT_MAX_DOC_BYTES = 2 * 1024 * 1024
SYNTHESIZED_FACTS = "synthesized_facts.dl"
SYNTHESIS_METADATA = "synthesis_metadata.json"

Validator = Callable[[Path, Path], dict[str, Any]]


@dataclass(frozen=True)
class SynthesisConfig:
    provider: str
    model: str | None = None


@dataclass(frozen=True)
class SynthesisSettings:
    iterations: int
    max_retries: int
    provider_retries: int
    plateau_min_improvement: float
    plateau_patience: int
    max_doc_bytes: int

    @classmethod
    def from_env(cls) -> "SynthesisSettings":
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
        )

    def single_pass(self) -> "SynthesisSettings":
        return replace(self, iterations=min(self.iterations, 1), max_retries=0)


def default_provider(value: str | None = None) -> str:
    return value or os.environ.get("SEMIA_LLM_PROVIDER") or "openai"


def default_model(value: str | None = None, provider: str | None = None) -> str | None:
    configured = value or os.environ.get("SEMIA_LLM_MODEL")
    if configured:
        return configured
    if provider == "openai":
        return DEFAULT_OPENAI_MODEL
    if provider in {"anthropic", "claude"}:
        return os.environ.get("ANTHROPIC_MODEL") or os.environ.get("ANTHROPIC_DEFAULT_SONNET_MODEL")
    return None


def timeout_seconds() -> int:
    return _env_int("SEMIA_LLM_TIMEOUT", DEFAULT_TIMEOUT_SECONDS)


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    return default if raw is None else int(raw)


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    return default if raw is None else float(raw)
