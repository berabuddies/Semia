# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 berabuddies
"""Markdown report rendering helpers."""

from __future__ import annotations

from .artifacts import AuditReport, CheckIssue, DetectorResult, EvidenceAlignmentResult


def render_markdown_report(
    report: AuditReport,
    *,
    evidence_by_atom: dict[str, tuple[str, ...]] | None = None,
) -> str:
    """Render a compact plugin-friendly Markdown report.

    The Markdown output is intentionally narrow: only the detector findings
    plus their grounded source quotes. Structural-check, evidence-grounding,
    and diagnostics metrics still live in the JSON/SARIF reports (consumed by
    CI/programmatic tooling), and the LLM-driven recommendation is rendered
    separately via :mod:`semia_cli.recommendation`.
    """

    lines: list[str] = [f"# {report.title}", "", f"Source: `{report.source_id}`", ""]
    if report.detector_result is not None:
        lines.extend(_render_detector_section(report.detector_result, evidence_by_atom or {}))
    if report.notes:
        lines.extend(["## Notes", ""])
        for note in report.notes:
            lines.append(f"- {note}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _render_check_section(issues: tuple[CheckIssue, ...], support: float) -> list[str]:
    lines = ["## Structural Check", ""]
    errors = [issue for issue in issues if issue.severity == "error"]
    warnings = [issue for issue in issues if issue.severity == "warning"]
    lines.append(f"- Errors: {len(errors)}")
    lines.append(f"- Warnings: {len(warnings)}")
    lines.append(f"- Evidence support coverage: {support:.2%}")
    lines.append("")
    for issue in errors + warnings:
        loc = f" line {issue.line}" if issue.line else ""
        lines.append(f"- `{issue.code}`{loc}: {issue.message}")
    lines.append("")
    return lines


def _render_evidence_section(result: EvidenceAlignmentResult) -> list[str]:
    lines = [
        "## Evidence Grounding",
        "",
        f"- Evidence match rate: {result.evidence_match_rate:.2%}",
        f"- Reference unit coverage: {result.reference_unit_coverage:.2%}",
        f"- Grounding score: {result.grounding_score:.2%}",
        "",
    ]
    unmatched = [alignment for alignment in result.alignments if not alignment.matched]
    if unmatched:
        lines.append("Unmatched evidence:")
        for alignment in unmatched[:10]:
            lines.append(
                f"- line {alignment.fact.line}: {alignment.evidence_text!r} ({alignment.score:.2f})"
            )
        lines.append("")
    return lines


def _render_diagnostics_section(diagnostics: dict[str, float] | None) -> list[str]:
    if not diagnostics:
        return []
    bullets: list[str] = []
    ssa = diagnostics.get("ssa_input_availability")
    if ssa is not None:
        bullets.append(f"- SSA input availability: {ssa:.2%}")
    if not bullets:
        return []
    return ["## Quality Diagnostics", "", *bullets, ""]


def _render_detector_section(
    result: DetectorResult, evidence_by_atom: dict[str, tuple[str, ...]]
) -> list[str]:
    lines = ["## Detector", "", f"- Status: `{result.status}`"]
    if result.message:
        lines.append(f"- Message: {result.message}")
    lines.append(f"- Findings: {len(result.findings)}")
    lines.append("")
    for finding in result.findings:
        fields = ", ".join(f"`{field}`" for field in finding.fields)
        suffix = f": {fields}" if fields else ""
        lines.append(f"- `{finding.label}`{suffix}")
        for atom in finding.fields:
            quotes = evidence_by_atom.get(atom, ())
            seen: set[str] = set()
            for quote in quotes:
                if quote in seen:
                    continue
                seen.add(quote)
                lines.append(f"  - `{atom}` evidence: {quote!r}")
    lines.append("")
    return lines
