"""Argparse entry point for the Semia CLI MVP."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any, TextIO

from . import core_adapter
from . import llm_adapter
from .core_adapter import CoreApiError
from .llm_adapter import LlmSynthesisError

SYNTHESIZED_FACTS = "synthesized_facts.dl"


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    stdout = getattr(args, "_stdout", sys.stdout)
    stderr = getattr(args, "_stderr", sys.stderr)

    try:
        args.handler(args, stdout)
    except CoreApiError as exc:
        print(f"semia: {exc}", file=stderr)
        return 2
    except FileNotFoundError as exc:
        print(f"semia: {exc}", file=stderr)
        return 2
    except LlmSynthesisError as exc:
        print(f"semia: {exc}", file=stderr)
        return 2
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="semia",
        description="Semia Skill Behavior Mapping audit CLI.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare_parser = subparsers.add_parser(
        "prepare",
        help="prepare a Semia run directory from a skill source",
    )
    prepare_parser.add_argument("skill_path", type=Path)
    prepare_parser.add_argument("--out", dest="run_dir", required=True, type=Path)
    prepare_parser.set_defaults(handler=_prepare)

    synthesize_parser = subparsers.add_parser(
        "synthesize",
        help="build and validate the skill behavior map",
    )
    synthesize_parser.add_argument("run_dir", type=Path)
    synthesize_parser.add_argument("--facts", dest="facts_path", type=Path)
    _add_llm_options(synthesize_parser)
    synthesize_parser.set_defaults(handler=_synthesize)

    detect_parser = subparsers.add_parser(
        "detect",
        help="run deterministic Semia detectors for a prepared run",
    )
    detect_parser.add_argument("run_dir", type=Path)
    detect_parser.set_defaults(handler=_detect)

    report_parser = subparsers.add_parser(
        "report",
        help="render a Semia audit report",
    )
    report_parser.add_argument("run_dir", type=Path)
    report_parser.add_argument("--format", choices=("md", "json", "sarif"), required=True)
    report_parser.set_defaults(handler=_report)

    scan_parser = subparsers.add_parser(
        "scan",
        help="prepare, synthesize, detect, and render a report",
    )
    scan_parser.add_argument("skill_path", type=Path)
    scan_parser.add_argument("--out", dest="run_dir", required=True, type=Path)
    scan_parser.add_argument(
        "--facts",
        dest="facts_path",
        type=Path,
        help="existing synthesized facts to copy into the run before detect/report",
    )
    _add_llm_options(scan_parser)
    scan_parser.add_argument(
        "--offline-baseline",
        action="store_true",
        help="use a conservative non-LLM fallback instead of calling synthesize",
    )
    scan_parser.add_argument(
        "--prepare-only",
        action="store_true",
        help="stop after prepare and print synthesis guidance",
    )
    scan_parser.set_defaults(handler=_scan)

    return parser


def _prepare(args: argparse.Namespace, stdout: TextIO) -> None:
    skill_path = _existing_path(args.skill_path, "skill_path")
    run_dir = args.run_dir.resolve()
    result = core_adapter.prepare(skill_path, run_dir)
    _print_result(stdout, result, fallback=f"Prepared Semia run at {run_dir}")


def _synthesize(args: argparse.Namespace, stdout: TextIO) -> None:
    run_dir = _existing_path(args.run_dir, "run_dir")
    facts_path = args.facts_path.resolve() if args.facts_path else None
    if facts_path is not None and not facts_path.exists():
        raise FileNotFoundError(f"facts file does not exist: {facts_path}")
    if facts_path is None and (run_dir / SYNTHESIZED_FACTS).exists():
        facts_path = run_dir / SYNTHESIZED_FACTS
    elif facts_path is None:
        result = llm_adapter.synthesize_facts(run_dir, provider=args.provider, model=args.model, validator=core_adapter.check)
        _print_result(stdout, result, fallback=f"Synthesized behavior map for {run_dir}")
        facts_path = run_dir / SYNTHESIZED_FACTS
    result = core_adapter.check(run_dir, facts_path)
    _print_result(stdout, result, fallback=f"Synthesized behavior map for {run_dir}")


def _detect(args: argparse.Namespace, stdout: TextIO) -> None:
    run_dir = _existing_path(args.run_dir, "run_dir")
    result = core_adapter.detect(run_dir)
    _print_result(stdout, result, fallback=f"Ran detectors for {run_dir}")


def _report(args: argparse.Namespace, stdout: TextIO) -> None:
    run_dir = _existing_path(args.run_dir, "run_dir")
    result = core_adapter.report(run_dir, args.format)
    _print_result(stdout, result, fallback=f"Rendered {args.format} report for {run_dir}")


def _scan(args: argparse.Namespace, stdout: TextIO) -> None:
    skill_path = _existing_path(args.skill_path, "skill_path")
    run_dir = args.run_dir.resolve()
    result = core_adapter.prepare(skill_path, run_dir)
    _print_result(stdout, result, fallback=f"Prepared Semia run at {run_dir}")
    if args.prepare_only:
        print("", file=stdout)
        print("Next step: use your current agent session to synthesize the behavior map.", file=stdout)
        print(f"Write the synthesized facts into: {run_dir / SYNTHESIZED_FACTS}", file=stdout)
        print(f"Then run: semia synthesize {run_dir}", file=stdout)
        print(f"Then run: semia detect {run_dir}", file=stdout)
        print(f"Then run: semia report {run_dir} --format md", file=stdout)
        return
    if args.facts_path is not None:
        facts_path = _existing_path(args.facts_path, "facts_path")
        target = run_dir / SYNTHESIZED_FACTS
        if facts_path != target:
            shutil.copyfile(facts_path, target)
        print("", file=stdout)
        print(f"Copied synthesized facts into: {target}", file=stdout)
    elif not (run_dir / SYNTHESIZED_FACTS).exists():
        print("", file=stdout)
        if args.offline_baseline:
            print("No synthesized facts supplied; using a conservative offline baseline map.", file=stdout)
            _print_result(stdout, core_adapter.extract_baseline(run_dir), fallback=f"Wrote baseline behavior map for {run_dir}")
        else:
            provider = llm_adapter.default_provider(args.provider)
            model = llm_adapter.default_model(args.model, provider)
            print(f"No synthesized facts supplied; running synthesize with provider `{provider}`.", file=stdout)
            if model:
                print(f"Using model `{model}`.", file=stdout)
            else:
                print("Using the provider's configured default model.", file=stdout)
            _print_result(stdout, llm_adapter.synthesize_facts(run_dir, provider=provider, model=model, validator=core_adapter.check), fallback=f"Synthesized behavior map for {run_dir}")

    _print_result(stdout, core_adapter.check(run_dir, run_dir / SYNTHESIZED_FACTS), fallback=f"Validated synthesized facts for {run_dir}")
    _print_result(stdout, core_adapter.detect(run_dir), fallback=f"Ran detectors for {run_dir}")
    report = core_adapter.report(run_dir, "md")
    if isinstance(report, str):
        print(report, file=stdout)
    else:
        _print_result(stdout, report, fallback=f"Rendered report for {run_dir}")


def _existing_path(path: Path, label: str) -> Path:
    resolved = path.resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"{label} does not exist: {resolved}")
    return resolved


def _add_llm_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--provider",
        choices=("openai", "anthropic", "codex", "claude"),
        help="LLM provider for synthesize; default: SEMIA_LLM_PROVIDER or openai",
    )
    parser.add_argument(
        "--model",
        help="model name passed to the provider; default: SEMIA_LLM_MODEL or gpt-5.5 for openai",
    )


def _print_result(stdout: TextIO, result: Any, fallback: str) -> None:
    if result is None:
        print(fallback, file=stdout)
    elif isinstance(result, str):
        print(result, file=stdout)
    elif isinstance(result, bytes):
        print(result.decode("utf-8"), file=stdout)
    else:
        print(json.dumps(_jsonable(result), indent=2, sort_keys=True), file=stdout)


def _jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if hasattr(value, "__dict__"):
        return _jsonable(vars(value))
    return value
