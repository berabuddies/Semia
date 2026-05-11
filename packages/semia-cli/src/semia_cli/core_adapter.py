# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 RiemaLabs
"""Direct API bindings to semia_core. The CLI delegates here so that test
doubles can monkeypatch a single import surface."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from semia_core import (
    align_evidence as _align_evidence,
    check_facts,
    detect,
    extract_baseline,
    prepare,
    report,
)


class CoreApiError(RuntimeError):
    """Raised when semia_core is not available or its API call fails."""


def check(run_dir: Path, facts_path: Path | None = None) -> Any:
    result = check_facts(run_dir=run_dir, facts_path=facts_path)
    try:
        _align_evidence(run_dir=run_dir, facts_path=facts_path)
    except FileNotFoundError:
        pass
    return result


__all__ = ["CoreApiError", "check", "detect", "extract_baseline", "prepare", "report"]
