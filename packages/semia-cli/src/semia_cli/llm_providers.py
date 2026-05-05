"""Provider IO for Semia synthesis.

The provider layer owns network/subprocess details. It deliberately avoids any
Semia scoring or candidate-selection logic.
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import contextmanager
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from typing import Any
from urllib import error, request

from .llm_config import (
    DEFAULT_OPENAI_MODEL,
    LlmSynthesisError,
    SynthesisConfig,
    SynthesisSettings,
    timeout_seconds,
)


def call_provider(root: Path, prompt: str, config: SynthesisConfig, settings: SynthesisSettings) -> str:
    if config.provider == "openai":
        return _run_with_retries(
            lambda: _run_openai(prompt, config.model or DEFAULT_OPENAI_MODEL),
            settings.provider_retries,
        )
    if config.provider == "anthropic":
        return _run_with_retries(
            lambda: _run_anthropic(prompt, config.model),
            settings.provider_retries,
        )
    if config.provider == "codex":
        return _run_with_retries(
            lambda: _run_codex(root, prompt, config.model),
            settings.provider_retries,
        )
    if config.provider == "claude":
        return _run_with_retries(
            lambda: _run_claude(root, prompt, config.model),
            settings.provider_retries,
        )
    raise LlmSynthesisError(f"unsupported synthesis provider: {config.provider}")


def extract_facts(text: str) -> str:
    stripped = text.strip()
    if "```" not in stripped:
        return stripped
    blocks = stripped.split("```")
    for idx in range(1, len(blocks), 2):
        block = blocks[idx].strip()
        lines = block.splitlines()
        if lines and lines[0].strip().lower() in {"datalog", "souffle", "prolog", "text"}:
            lines = lines[1:]
        candidate = "\n".join(lines).strip()
        if candidate:
            return candidate
    return stripped


def _run_with_retries(call: Callable[[], str], max_retries: int) -> str:
    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            return call()
        except LlmSynthesisError as exc:
            last_error = exc
            if attempt >= max_retries:
                break
            time.sleep(min(30, 2**attempt))
    raise last_error or LlmSynthesisError("provider call failed")


def _run_openai(prompt: str, model: str) -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise LlmSynthesisError("openai provider selected, but OPENAI_API_KEY is not set")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    payload = {
        "model": model,
        "input": prompt,
        "text": {"format": {"type": "text"}},
        "stream": True,
    }
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
            return _read_openai_response(response)
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise LlmSynthesisError(f"OpenAI Responses API failed ({exc.code}): {detail}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise LlmSynthesisError(f"OpenAI Responses API failed: {exc}") from exc


def _read_openai_response(response: Any) -> str:
    content_type = response.headers.get("Content-Type", "")
    if "text/event-stream" not in content_type:
        return _extract_openai_text(json.loads(response.read().decode("utf-8")))

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


def _extract_openai_text(payload: dict[str, Any]) -> str:
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


def _run_anthropic(prompt: str, model: str | None) -> str:
    try:
        import anthropic  # type: ignore[import-not-found]
    except ImportError as exc:
        raise LlmSynthesisError(
            "anthropic provider selected, but the `anthropic` Python SDK is not installed"
        ) from exc

    resolved_model = model or _anthropic_default_model()
    if not resolved_model:
        raise LlmSynthesisError(
            "anthropic provider selected, but no model is configured; set --model, "
            "SEMIA_LLM_MODEL, ANTHROPIC_MODEL, or ANTHROPIC_DEFAULT_SONNET_MODEL"
        )

    kwargs: dict[str, Any] = {}
    base_url = _first_env("SEMIA_ANTHROPIC_BASE_URL", "ANTHROPIC_BASE_URL")
    if base_url:
        kwargs["base_url"] = base_url
    api_key = _first_env("SEMIA_ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY")
    auth_token = _first_env("SEMIA_ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_AUTH_TOKEN")
    if api_key:
        kwargs["api_key"] = api_key
    elif auth_token:
        kwargs["auth_token"] = auth_token
    kwargs["timeout"] = timeout_seconds()
    kwargs["max_retries"] = _env_int("SEMIA_LLM_MAX_RETRIES", 2)

    client = anthropic.Anthropic(**kwargs)
    request_payload: dict[str, Any] = {
        "model": resolved_model,
        "max_tokens": _env_int("SEMIA_ANTHROPIC_MAX_TOKENS", 16384),
        "temperature": 0,
        "messages": [{"role": "user", "content": prompt}],
        "stream": True,
    }
    thinking_budget = _env_int("SEMIA_ANTHROPIC_THINKING_BUDGET", 0)
    if thinking_budget > 0:
        request_payload["thinking"] = {"type": "enabled", "budget_tokens": thinking_budget}

    try:
        stream = client.messages.create(**request_payload)
        return _read_anthropic_stream(stream)
    except Exception as exc:
        raise LlmSynthesisError(f"Anthropic Messages API failed: {exc}") from exc


def _read_anthropic_stream(stream: Any) -> str:
    text_parts: list[str] = []
    with _maybe_context(stream) as events:
        for event in events:
            event_type = _get_attr(event, "type")
            if event_type == "content_block_delta":
                delta = _get_attr(event, "delta")
                if _get_attr(delta, "type") == "text_delta":
                    text = _get_attr(delta, "text")
                    if isinstance(text, str):
                        text_parts.append(text)
            elif event_type == "message_delta":
                continue
            elif event_type == "message_stop":
                break
            elif isinstance(event, dict):
                delta = event.get("delta")
                if event.get("type") == "content_block_delta" and isinstance(delta, dict):
                    text = delta.get("text")
                    if isinstance(text, str):
                        text_parts.append(text)
    content = "".join(text_parts)
    if not content:
        raise LlmSynthesisError("Anthropic response did not include streamed text output")
    return content


@contextmanager
def _maybe_context(value: Any):
    if hasattr(value, "__enter__") and hasattr(value, "__exit__"):
        with value as entered:
            yield entered
    else:
        yield value


def _get_attr(value: Any, name: str) -> Any:
    if isinstance(value, dict):
        return value.get(name)
    return getattr(value, name, None)


def _anthropic_default_model() -> str | None:
    return (
        _first_env("SEMIA_ANTHROPIC_MODEL", "ANTHROPIC_MODEL", "ANTHROPIC_DEFAULT_SONNET_MODEL")
        or None
    )


def _first_env(*names: str) -> str | None:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return None


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    return default if raw is None else int(raw)


def _run_codex(root: Path, prompt: str, model: str | None) -> str:
    codex = shutil.which("codex")
    if codex is None:
        raise LlmSynthesisError("codex provider selected, but `codex` was not found on PATH")
    output = root / ".semia_codex_synthesis.txt"
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
    _run_subprocess(cmd, prompt)
    if not output.exists():
        raise LlmSynthesisError("codex did not write a final synthesis message")
    return output.read_text(encoding="utf-8")


def _run_claude(root: Path, prompt: str, model: str | None) -> str:
    claude = shutil.which("claude")
    if claude is None:
        raise LlmSynthesisError("claude provider selected, but `claude` was not found on PATH")
    cmd = [
        claude,
        "--print",
        "--permission-mode",
        "dontAsk",
        "--tools",
        "",
    ]
    if model:
        cmd.extend(["--model", model])
    cmd.append(prompt)
    return _run_subprocess(cmd, None, cwd=root).stdout


def _run_subprocess(cmd: list[str], stdin: str | None, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            cmd,
            input=stdin,
            cwd=str(cwd) if cwd else None,
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        raise LlmSynthesisError(str(exc)) from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise LlmSynthesisError(f"provider command failed ({result.returncode}): {detail}")
    return result
