# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 berabuddies
"""Transport-layer IO for Semia synthesis.

Four providers are supported. The HTTP pair talks raw HTTP (no third-party
SDK); the CLI pair shells out to a locally-installed agent CLI.

HTTP providers honor ``--model``, ``--base-url`` and the matching env-var
auth (``OPENAI_API_KEY`` / ``ANTHROPIC_API_KEY``):

- :data:`~.llm_config.PROVIDER_RESPONSES` — OpenAI Responses API, streamed
  via Server-Sent Events.
- :data:`~.llm_config.PROVIDER_ANTHROPIC` — Anthropic Messages API, also
  streamed via SSE.

CLI providers only honor ``--model``; auth is inherited from the host CLI's
config:

- :data:`~.llm_config.PROVIDER_CODEX` — pipes the prompt into ``codex exec``.
- :data:`~.llm_config.PROVIDER_CLAUDE` — pipes the prompt into
  ``claude --print``.

This layer owns network and subprocess details only. Scoring and candidate
selection live in :mod:`semia_cli.synthesis_loop`.
"""

from __future__ import annotations

import contextlib
import json
import os
import shutil
import subprocess
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib import error, request

from .llm_config import (
    DEFAULT_MODEL_CLAUDE,
    PROVIDER_ANTHROPIC,
    PROVIDER_CLAUDE,
    PROVIDER_CODEX,
    PROVIDER_RESPONSES,
    LlmSynthesisConfigError,
    LlmSynthesisError,
    SynthesisConfig,
    SynthesisSettings,
    default_base_url,
    load_dotenv,
    timeout_seconds,
)


def call_provider(
    root: Path,
    prompt: str,
    config: SynthesisConfig,
    settings: SynthesisSettings,
) -> str:
    """Dispatch ``prompt`` to the configured provider."""

    load_dotenv()
    if config.provider == PROVIDER_RESPONSES:
        base_url = default_base_url(config.base_url, PROVIDER_RESPONSES) or ""
        return _run_with_retries(
            lambda: _run_responses(prompt, config.model, base_url),
            settings.provider_retries,
        )
    if config.provider == PROVIDER_ANTHROPIC:
        base_url = default_base_url(config.base_url, PROVIDER_ANTHROPIC) or ""
        return _run_with_retries(
            lambda: _run_anthropic_messages(prompt, config.model, base_url),
            settings.provider_retries,
        )
    if config.provider == PROVIDER_CODEX:
        return _run_with_retries(
            lambda: _run_codex(root, prompt, config.model),
            settings.provider_retries,
        )
    if config.provider == PROVIDER_CLAUDE:
        return _run_with_retries(
            lambda: _run_claude(root, prompt, config.model or DEFAULT_MODEL_CLAUDE),
            settings.provider_retries,
        )
    raise LlmSynthesisConfigError(f"unsupported synthesis provider: {config.provider!r}")


_FACT_FENCE_TAGS = {"datalog", "souffle", "prolog", "text", "dl", "facts", "sdl"}


def extract_facts(text: str) -> str:
    """Pull a Datalog program out of an LLM response.

    Strategy:
      1. If a fenced block is tagged with a recognized fact language
         (``datalog``, ``souffle``, ``prolog``, ``text``, ``dl``, ``facts``,
         ``sdl``), prefer the first such block.
      2. Otherwise prefer fenced blocks whose body contains lines that look
         like Datalog facts (end in ``.``).
      3. Else fall back to the first non-empty fenced block.
      4. If there are no fences at all, return the stripped text as-is.

    Tag-looking first lines (single token, no period) are dropped from any
    block — so a stray ```bash`` ``` fence does not poison the candidate with a
    literal ``bash`` line.
    """

    stripped = text.strip()
    if "```" not in stripped:
        return stripped

    blocks = stripped.split("```")
    preferred: str | None = None
    factish: str | None = None
    fallback: str | None = None

    for idx in range(1, len(blocks), 2):
        block = blocks[idx]
        lines = block.splitlines()
        if not lines:
            continue
        first = lines[0].strip()
        first_lower = first.lower()
        looks_like_tag = bool(first) and " " not in first and not first.endswith(".")
        body_lines = lines[1:] if looks_like_tag else lines
        body = "\n".join(body_lines).strip()
        if not body:
            continue
        if first_lower in _FACT_FENCE_TAGS and preferred is None:
            preferred = body
            continue
        if factish is None and any(line.rstrip().endswith(".") for line in body.splitlines()):
            factish = body
        if fallback is None:
            fallback = body

    return preferred or factish or fallback or stripped


def _run_with_retries(call: Callable[[], str], max_retries: int) -> str:
    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            return call()
        except LlmSynthesisConfigError:
            # Configuration errors (missing API key, unknown provider, missing
            # CLI binary) will not be fixed by retrying — surface immediately.
            raise
        except LlmSynthesisError as exc:
            last_error = exc
            if attempt >= max_retries:
                break
            time.sleep(min(30, 2**attempt))
    raise last_error or LlmSynthesisError("provider call failed")


# ---------------------------------------------------------------------------
# OpenAI Responses API
# ---------------------------------------------------------------------------


def _run_responses(prompt: str, model: str | None, base_url: str) -> str:
    if not model:
        raise LlmSynthesisConfigError("responses provider requires a model name")
    api_key = _first_env("SEMIA_OPENAI_API_KEY", "OPENAI_API_KEY")
    if not api_key:
        raise LlmSynthesisConfigError("responses provider selected, but OPENAI_API_KEY is not set")
    payload: dict[str, Any] = {
        "model": model,
        "input": prompt,
        "text": {"format": {"type": "text"}},
        "stream": True,
    }
    # Determinism: security tooling should produce repeatable output where
    # the endpoint allows it. Reasoning models that reject ``temperature``
    # can opt out with ``SEMIA_OPENAI_TEMPERATURE=`` (empty string).
    temperature_raw = os.environ.get("SEMIA_OPENAI_TEMPERATURE", "0")
    if temperature_raw != "":
        with contextlib.suppress(ValueError):
            payload["temperature"] = float(temperature_raw)
    req = request.Request(
        f"{base_url}/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout_seconds()) as response:
            return _read_responses_payload(response)
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise LlmSynthesisError(f"OpenAI Responses API failed ({exc.code}): {detail}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise LlmSynthesisError(f"OpenAI Responses API failed: {exc}") from exc


def _read_responses_payload(response: Any) -> str:
    content_type = response.headers.get("Content-Type", "")
    if "text/event-stream" not in content_type:
        return _extract_responses_text(json.loads(response.read().decode("utf-8")))

    text_parts: list[str] = []
    for event_type, data in _iter_sse_events(_iter_response_lines(response)):
        if event_type == "response.output_text.delta":
            payload = json.loads(data)
            delta = payload.get("delta")
            if isinstance(delta, str):
                text_parts.append(delta)
        elif event_type == "response.failed":
            raise LlmSynthesisError(f"OpenAI Responses API failed: {data}")
    content = "".join(text_parts)
    if not content:
        raise LlmSynthesisError("OpenAI response did not include streamed text output")
    return content


def _extract_responses_text(payload: dict[str, Any]) -> str:
    direct = payload.get("output_text")
    if isinstance(direct, str):
        return direct
    pieces: list[str] = []
    for item in payload.get("output", []):
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []):
            if not isinstance(content, dict):
                continue
            text = content.get("text")
            if isinstance(text, str):
                pieces.append(text)
    if pieces:
        return "\n".join(pieces)
    raise LlmSynthesisError("OpenAI response did not include text output")


# ---------------------------------------------------------------------------
# Anthropic Messages API
# ---------------------------------------------------------------------------


def _run_anthropic_messages(prompt: str, model: str | None, base_url: str) -> str:
    if not model:
        raise LlmSynthesisConfigError("anthropic provider requires a model name")
    api_key = _first_env("SEMIA_ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY")
    auth_token = _first_env("SEMIA_ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_AUTH_TOKEN")
    if not api_key and not auth_token:
        raise LlmSynthesisConfigError(
            "anthropic provider selected, but ANTHROPIC_API_KEY "
            "(or ANTHROPIC_AUTH_TOKEN) is not set"
        )
    headers = {
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
        "anthropic-version": os.environ.get("ANTHROPIC_VERSION") or "2023-06-01",
    }
    if api_key:
        headers["x-api-key"] = api_key
    else:
        headers["Authorization"] = f"Bearer {auth_token}"
    payload: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": _env_int("SEMIA_ANTHROPIC_MAX_TOKENS", 16384),
        "stream": True,
        "temperature": 0,
    }
    thinking_budget = _env_int("SEMIA_ANTHROPIC_THINKING_BUDGET", 0)
    if thinking_budget > 0:
        payload["thinking"] = {"type": "enabled", "budget_tokens": thinking_budget}
    req = request.Request(
        f"{base_url}/v1/messages",
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout_seconds()) as response:
            return _read_anthropic_messages_payload(response)
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise LlmSynthesisError(f"Anthropic Messages API failed ({exc.code}): {detail}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise LlmSynthesisError(f"Anthropic Messages API failed: {exc}") from exc


def _read_anthropic_messages_payload(response: Any) -> str:
    content_type = response.headers.get("Content-Type", "")
    if "text/event-stream" not in content_type:
        return _extract_anthropic_text(json.loads(response.read().decode("utf-8")))

    text_parts: list[str] = []
    for event_type, data in _iter_sse_events(_iter_response_lines(response)):
        if event_type == "content_block_delta":
            payload = json.loads(data)
            delta = payload.get("delta") or {}
            if delta.get("type") == "text_delta":
                text = delta.get("text")
                if isinstance(text, str):
                    text_parts.append(text)
        elif event_type == "message_stop":
            break
        elif event_type == "error":
            raise LlmSynthesisError(f"Anthropic Messages API failed: {data}")
    content = "".join(text_parts)
    if not content:
        raise LlmSynthesisError("Anthropic response did not include streamed text output")
    return content


def _extract_anthropic_text(payload: dict[str, Any]) -> str:
    pieces: list[str] = []
    for block in payload.get("content", []):
        if not isinstance(block, dict):
            continue
        if block.get("type") != "text":
            continue
        text = block.get("text")
        if isinstance(text, str):
            pieces.append(text)
    if pieces:
        return "\n".join(pieces)
    raise LlmSynthesisError("Anthropic response did not include text output")


# ---------------------------------------------------------------------------
# Codex CLI (subprocess)
# ---------------------------------------------------------------------------


def _run_codex(root: Path, prompt: str, model: str | None) -> str:
    codex = shutil.which("codex")
    if codex is None:
        raise LlmSynthesisConfigError("codex provider selected, but `codex` was not found on PATH")
    output = root / ".semia_codex_synthesis.txt"
    # If a prior run left this file behind, remove it so a failed codex call
    # cannot make us return the previous run's output.
    output.unlink(missing_ok=True)
    cmd = [
        codex,
        "exec",
        "--skip-git-repo-check",
        "--sandbox",
        "read-only",
        "--cd",
        str(root),
        "--output-last-message",
        str(output),
    ]
    if model:
        cmd.extend(["--model", model])
    cmd.append("-")
    try:
        _run_subprocess(cmd, prompt)
        if not output.exists():
            raise LlmSynthesisError("codex did not write a final synthesis message")
        return output.read_text(encoding="utf-8")
    finally:
        output.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Claude Code CLI (subprocess)
# ---------------------------------------------------------------------------


# Empty string disables every tool in Claude Code's current CLI surface.
# Synthesis runs on hostile skill content; if a future Claude Code release
# changes ``--tools`` parsing so the empty value no longer means "no tools",
# the synthesizer could be steered into invoking tools on attacker-controlled
# input. The runtime test in tests/cli/test_llm_adapter.py pins this command
# shape — keep it green.
_CLAUDE_NO_TOOLS_ARG = ""


def _run_claude(root: Path, prompt: str, model: str | None) -> str:
    claude = shutil.which("claude")
    if claude is None:
        raise LlmSynthesisConfigError(
            "claude provider selected, but `claude` was not found on PATH"
        )
    cmd = [
        claude,
        "--print",
        "--permission-mode",
        "dontAsk",
        "--tools",
        _CLAUDE_NO_TOOLS_ARG,
    ]
    if model:
        cmd.extend(["--model", model])
    # Pass the prompt via stdin: ``--tools`` is variadic and would otherwise
    # consume a trailing positional prompt argument.
    result = _run_subprocess(cmd, prompt, cwd=root, env=_provider_env())
    if not result.stdout.strip():
        detail = result.stderr.strip() or "Claude Code returned an empty synthesis response"
        raise LlmSynthesisError(detail)
    return result.stdout


def _provider_env() -> dict[str, str]:
    """Inherit the parent env and forward SEMIA_*_ aliases to the canonical
    names Claude Code reads. Lets users keep Semia keys distinct from the
    host CLI's keys when they want to.
    """

    env = os.environ.copy()
    aliases = {
        "ANTHROPIC_API_KEY": ("SEMIA_ANTHROPIC_API_KEY",),
        "ANTHROPIC_AUTH_TOKEN": ("SEMIA_ANTHROPIC_AUTH_TOKEN",),
        "ANTHROPIC_BASE_URL": ("SEMIA_ANTHROPIC_BASE_URL",),
        "ANTHROPIC_MODEL": ("SEMIA_ANTHROPIC_MODEL", "SEMIA_LLM_MODEL"),
        "OPENAI_API_KEY": ("SEMIA_OPENAI_API_KEY",),
        "OPENAI_BASE_URL": ("SEMIA_OPENAI_BASE_URL",),
    }
    for target, source_names in aliases.items():
        if env.get(target):
            continue
        for source_name in source_names:
            if env.get(source_name):
                env[target] = env[source_name]
                break
    return env


def _run_subprocess(
    cmd: list[str],
    stdin: str | None,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            cmd,
            input=stdin,
            cwd=str(cwd) if cwd else None,
            env=env,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout_seconds(),
        )
    except subprocess.TimeoutExpired as exc:
        raise LlmSynthesisError(
            f"provider command timed out after {timeout_seconds()} seconds"
        ) from exc
    except OSError as exc:
        raise LlmSynthesisError(str(exc)) from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise LlmSynthesisError(f"provider command failed ({result.returncode}): {detail}")
    return result


# ---------------------------------------------------------------------------
# Shared SSE machinery
# ---------------------------------------------------------------------------


def _iter_response_lines(response: Any):
    buf = bytearray()
    while True:
        chunk = response.read(65536)
        if not chunk:
            break
        buf.extend(chunk)
        start = 0
        while True:
            idx = buf.find(b"\n", start)
            if idx == -1:
                break
            yield buf[start:idx].decode("utf-8", errors="replace").rstrip("\r")
            start = idx + 1
        if start:
            del buf[:start]
    if buf:
        yield buf.decode("utf-8", errors="replace").rstrip("\r")


def _iter_sse_events(lines):
    event_type = ""
    data_lines: list[str] = []
    for line in lines:
        if line.startswith("event:"):
            event_type = line[len("event:") :].strip()
        elif line.startswith("data:"):
            data_lines.append(line[len("data:") :].strip())
        elif line == "":
            if data_lines:
                yield event_type, "\n".join(data_lines)
            event_type = ""
            data_lines = []
    if data_lines:
        yield event_type, "\n".join(data_lines)


def _first_env(*names: str) -> str | None:
    load_dotenv()
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return None


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default
