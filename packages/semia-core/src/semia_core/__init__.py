"""Semia core analysis primitives.

This package is intentionally stdlib-only. Agent plugins and CLIs can layer
host-specific orchestration on top without making the deterministic core depend
on a model provider or plugin runtime.
"""

from .artifacts import (
    AuditReport,
    CheckIssue,
    CheckResult,
    DetectorResult,
    EvidenceAlignment,
    EvidenceAlignmentResult,
    Fact,
    FactProgram,
    FileInventoryEntry,
    Finding,
    SemanticUnit,
    SkillSource,
    SourceMapEntry,
    Stage1Bundle,
)
from .checker import check_program
from .evidence import align_evidence_text
from .facts import parse_facts
from .pipeline import align_evidence, check, check_facts, detect, extract_baseline, prepare, render_report, report
from .report import render_markdown_report
from .stage1 import build_stage1_bundle

__all__ = [
    "AuditReport",
    "CheckIssue",
    "CheckResult",
    "DetectorResult",
    "EvidenceAlignment",
    "EvidenceAlignmentResult",
    "Fact",
    "FactProgram",
    "FileInventoryEntry",
    "Finding",
    "SemanticUnit",
    "SkillSource",
    "SourceMapEntry",
    "Stage1Bundle",
    "align_evidence_text",
    "align_evidence",
    "build_stage1_bundle",
    "check",
    "check_facts",
    "check_program",
    "detect",
    "extract_baseline",
    "parse_facts",
    "prepare",
    "render_markdown_report",
    "render_report",
    "report",
]
