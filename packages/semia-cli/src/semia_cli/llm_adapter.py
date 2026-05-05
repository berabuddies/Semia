"""Stable public facade for Semia LLM synthesis."""

from __future__ import annotations

from .llm_config import (
    DEFAULT_OPENAI_MODEL,
    LlmSynthesisError,
    SynthesisConfig,
    SynthesisSettings,
    default_model,
    default_provider,
)
from .synthesis_loop import synthesize_facts

__all__ = [
    "DEFAULT_OPENAI_MODEL",
    "LlmSynthesisError",
    "SynthesisConfig",
    "SynthesisSettings",
    "default_model",
    "default_provider",
    "synthesize_facts",
]
