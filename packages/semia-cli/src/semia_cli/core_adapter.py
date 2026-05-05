"""Thin, defensive imports around the future semia_core API.

The CLI intentionally owns no analysis behavior. It validates command-line
shape, normalizes paths, and delegates all real work into semia_core.
"""

from __future__ import annotations

from collections.abc import Callable
from importlib import import_module
from inspect import Parameter, signature
from pathlib import Path
from typing import Any


class CoreApiError(RuntimeError):
    """Raised when semia_core is missing or does not expose a needed hook."""


def prepare(skill_path: Path, run_dir: Path) -> Any:
    return _call_first(
        (
            ("semia_core", "prepare"),
            ("semia_core.stage1", "prepare"),
            ("semia_core.pipeline", "prepare"),
        ),
        skill_path=skill_path,
        out_dir=run_dir,
        run_dir=run_dir,
    )


def check(run_dir: Path, facts_path: Path | None = None) -> Any:
    result = _call_first(
        (
            ("semia_core", "check_facts"),
            ("semia_core", "check"),
        ),
        run_dir=run_dir,
        facts_path=facts_path,
    )
    _call_optional(
        (
            ("semia_core", "align_evidence"),
            ("semia_core.evidence", "align_evidence"),
        ),
        run_dir=run_dir,
        facts_path=facts_path,
        checked_facts=result,
    )
    return result


def detect(run_dir: Path) -> Any:
    return _call_first(
        (
            ("semia_core", "detect"),
            ("semia_core.detectors", "detect"),
            ("semia_core.pipeline", "detect"),
        ),
        run_dir=run_dir,
    )


def extract_baseline(run_dir: Path) -> Any:
    return _call_first(
        (
            ("semia_core", "extract_baseline"),
            ("semia_core.pipeline", "extract_baseline"),
        ),
        run_dir=run_dir,
    )


def report(run_dir: Path, report_format: str) -> Any:
    return _call_first(
        (
            ("semia_core", "report"),
            ("semia_core", "render_report"),
            ("semia_core.reports", "report"),
            ("semia_core.reports", "render_report"),
        ),
        run_dir=run_dir,
        format=report_format,
        report_format=report_format,
    )


def _call_optional(candidates: tuple[tuple[str, str], ...], **kwargs: Any) -> Any:
    try:
        return _call_first(candidates, **kwargs)
    except CoreApiError:
        return None


def _call_first(candidates: tuple[tuple[str, str], ...], **kwargs: Any) -> Any:
    import_errors: list[str] = []
    seen_modules: set[str] = set()

    for module_name, attr_name in candidates:
        module = _import_module(module_name, import_errors, seen_modules)
        if module is None or not hasattr(module, attr_name):
            continue
        func = getattr(module, attr_name)
        if not callable(func):
            continue
        return _invoke(func, kwargs)

    choices = ", ".join(f"{module}.{attr}" for module, attr in candidates)
    details = f" Import errors: {'; '.join(import_errors)}" if import_errors else ""
    raise CoreApiError(f"semia_core does not expose any supported API: {choices}.{details}")


def _import_module(
    module_name: str, import_errors: list[str], seen_modules: set[str]
) -> Any | None:
    if module_name in seen_modules:
        return None
    seen_modules.add(module_name)
    try:
        return import_module(module_name)
    except ModuleNotFoundError as exc:
        if exc.name == module_name or module_name.startswith(f"{exc.name}."):
            import_errors.append(f"{module_name}: {exc}")
            return None
        raise


def _invoke(func: Callable[..., Any], kwargs: dict[str, Any]) -> Any:
    attempts: tuple[dict[str, Any], ...] = (
        _signature_kwargs(func, kwargs),
        kwargs,
        _without_none(kwargs),
        _with_out_alias(kwargs),
        _format_alias(kwargs),
    )
    last_error: TypeError | None = None
    for attempt in attempts:
        try:
            return func(**attempt)
        except TypeError as exc:
            last_error = exc

    positional = _positional_args(kwargs)
    if positional:
        try:
            return func(*positional)
        except TypeError as exc:
            last_error = exc

    assert last_error is not None
    raise last_error


def _without_none(kwargs: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in kwargs.items() if value is not None}


def _with_out_alias(kwargs: dict[str, Any]) -> dict[str, Any]:
    aliased = _without_none(kwargs)
    if "out_dir" in aliased:
        aliased.pop("run_dir", None)
    return aliased


def _format_alias(kwargs: dict[str, Any]) -> dict[str, Any]:
    aliased = _without_none(kwargs)
    if "format" in aliased:
        aliased.pop("report_format", None)
    return aliased


def _signature_kwargs(func: Callable[..., Any], kwargs: dict[str, Any]) -> dict[str, Any]:
    try:
        parameters = signature(func).parameters
    except (TypeError, ValueError):
        return kwargs

    if any(param.kind is Parameter.VAR_KEYWORD for param in parameters.values()):
        return kwargs

    names = {
        name
        for name, param in parameters.items()
        if param.kind
        in (
            Parameter.POSITIONAL_OR_KEYWORD,
            Parameter.KEYWORD_ONLY,
        )
    }
    filtered = {key: value for key, value in kwargs.items() if key in names}

    if "out_dir" in names and "out_dir" not in filtered and "run_dir" in kwargs:
        filtered["out_dir"] = kwargs["run_dir"]
    if "run_dir" in names and "run_dir" not in filtered and "out_dir" in kwargs:
        filtered["run_dir"] = kwargs["out_dir"]
    if "format" in names and "format" not in filtered and "report_format" in kwargs:
        filtered["format"] = kwargs["report_format"]
    if (
        "report_format" in names
        and "report_format" not in filtered
        and "format" in kwargs
    ):
        filtered["report_format"] = kwargs["format"]

    return _without_none(filtered)


def _positional_args(kwargs: dict[str, Any]) -> tuple[Any, ...]:
    if "skill_path" in kwargs and "out_dir" in kwargs:
        return (kwargs["skill_path"], kwargs["out_dir"])
    if "run_dir" in kwargs and kwargs.get("facts_path") is not None:
        return (kwargs["run_dir"], kwargs["facts_path"])
    if "run_dir" in kwargs and "format" in kwargs:
        return (kwargs["run_dir"], kwargs["format"])
    if "run_dir" in kwargs:
        return (kwargs["run_dir"],)
    return ()
