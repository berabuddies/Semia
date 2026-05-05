"""Optional Souffle detector runner.

The core package never downloads or bundles Souffle. It first honors
``SEMIA_SOUFFLE_BIN``, then ``PATH``. Missing Souffle is a structured result so
plugins can keep running prepare/synthesize diagnostics on machines without the binary.
"""

from __future__ import annotations

import csv
import os
import shutil
import subprocess
from pathlib import Path

from .artifacts import DetectorResult, Finding


def find_souffle_binary() -> str | None:
    """Return the configured/available Souffle binary, if any."""

    configured = os.environ.get("SEMIA_SOUFFLE_BIN")
    if configured:
        path = Path(configured).expanduser()
        if path.exists() and os.access(path, os.X_OK):
            return str(path)
        return None
    return shutil.which("souffle")


def run_detector(
    facts_path: str | Path,
    output_dir: str | Path,
    *,
    timeout_seconds: int = 120,
) -> DetectorResult:
    """Run Souffle over an already assembled facts/rules file."""

    souffle_bin = find_souffle_binary()
    if souffle_bin is None:
        return DetectorResult(
            status="unavailable",
            message="Souffle binary not found; set SEMIA_SOUFFLE_BIN or install souffle on PATH.",
        )

    facts = Path(facts_path)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    cmd = [souffle_bin, str(facts), "-D", str(out)]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return DetectorResult(status="failed", message=str(exc), output_dir=out)

    if result.returncode != 0:
        return DetectorResult(
            status="failed",
            stdout=result.stdout,
            stderr=result.stderr,
            message=f"Souffle exited with {result.returncode}",
            output_dir=out,
        )

    return DetectorResult(
        status="ok",
        findings=tuple(_read_findings(out)),
        stdout=result.stdout,
        stderr=result.stderr,
        output_dir=out,
    )


def _read_findings(output_dir: Path) -> list[Finding]:
    findings: list[Finding] = []
    for csv_path in sorted(output_dir.glob("label_*.csv")):
        label = csv_path.stem
        with csv_path.open(newline="", encoding="utf-8") as handle:
            reader = csv.reader(handle, delimiter="\t")
            for row in reader:
                findings.append(Finding(label=label, fields=tuple(row)))
    return findings
