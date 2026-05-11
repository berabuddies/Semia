# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 berabuddies
"""Stable public facade for Semia LLM synthesis."""

from __future__ import annotations

from .llm_config import (
    DEFAULT_ANTHROPIC_BASE_URL,
    DEFAULT_MODEL,
    DEFAULT_MODEL_ANTHROPIC,
    DEFAULT_MODEL_CLAUDE,
    DEFAULT_MODEL_CODEX,
    DEFAULT_MODEL_RESPONSES,
    DEFAULT_OPENAI_MODEL,
    DEFAULT_PROVIDER,
    DEFAULT_RESPONSES_BASE_URL,
    HTTP_PROVIDERS,
    PROVIDER_ANTHROPIC,
    PROVIDER_CLAUDE,
    PROVIDER_CODEX,
    PROVIDER_RESPONSES,
    SUPPORTED_PROVIDERS,
    LlmSynthesisConfigError,
    LlmSynthesisError,
    SynthesisConfig,
    SynthesisSettings,
    default_base_url,
    default_model,
    default_provider,
)
from .synthesis_loop import synthesize_facts

__all__ = [
    "DEFAULT_ANTHROPIC_BASE_URL",
    "DEFAULT_MODEL",
    "DEFAULT_MODEL_ANTHROPIC",
    "DEFAULT_MODEL_CLAUDE",
    "DEFAULT_MODEL_CODEX",
    "DEFAULT_MODEL_RESPONSES",
    "DEFAULT_OPENAI_MODEL",
    "DEFAULT_PROVIDER",
    "DEFAULT_RESPONSES_BASE_URL",
    "HTTP_PROVIDERS",
    "LlmSynthesisConfigError",
    "LlmSynthesisError",
    "PROVIDER_ANTHROPIC",
    "PROVIDER_CLAUDE",
    "PROVIDER_CODEX",
    "PROVIDER_RESPONSES",
    "SUPPORTED_PROVIDERS",
    "SynthesisConfig",
    "SynthesisSettings",
    "default_base_url",
    "default_model",
    "default_provider",
    "synthesize_facts",
]
