"""Dataclass contracts shared by Semia core steps."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal


def _plain(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, list):
        return [_plain(v) for v in value]
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    return value


@dataclass(frozen=True)
class SkillSource:
    """A deterministic skill source bundle loaded from a file or directory."""

    source_id: str
    root: Path
    main_path: Path
    inlined_text: str
    source_hash: str
    files: tuple[str, ...] = ()
    file_inventory: tuple[FileInventoryEntry, ...] = ()
    source_map: tuple[SourceMapEntry, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return _plain(asdict(self))


@dataclass(frozen=True)
class FileInventoryEntry:
    """One file observed while preparing a skill source."""

    path: str
    size_bytes: int
    line_count: int
    language: str
    disposition: Literal["excluded", "inlined", "inlined_source"]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SourceMapEntry:
    """Maps inlined output lines back to the originating file and lines."""

    enriched_line_start: int
    enriched_line_end: int
    source_file: str
    source_line_start: int
    source_line_end: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SemanticUnit:
    """A prepared reference unit with a stable local evidence handle."""

    id: int
    evidence_id: str
    unit_type: str
    text: str
    line_start: int
    line_end: int
    source_file: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Stage1Bundle:
    """Prepared artifact contract consumed by agent synthesis workflows."""

    source: SkillSource
    semantic_units: tuple[SemanticUnit, ...]

    @property
    def reference_text(self) -> str:
        return "\n".join(unit.text for unit in self.semantic_units)

    def evidence_unit_facts(self) -> str:
        lines = [
            f'evidence_unit("{unit.evidence_id}", {unit.id}).'
            for unit in self.semantic_units
        ]
        return "\n".join(lines) + ("\n" if lines else "")

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source.to_dict(),
            "total_units": len(self.semantic_units),
            "semantic_units": [unit.to_dict() for unit in self.semantic_units],
        }


@dataclass(frozen=True, order=True)
class Fact:
    """One parsed Souffle-style fact."""

    relation: str
    args: tuple[str, ...]
    line: int = 0
    raw: str = ""

    @property
    def signature(self) -> tuple[str, tuple[str, ...]]:
        return (self.relation, self.args)

    def render(self) -> str:
        rendered_args = ", ".join(_quote_arg(arg) for arg in self.args)
        return f"{self.relation}({rendered_args})."


@dataclass(frozen=True)
class FactProgram:
    """Parsed SDL candidate split into detector core and evidence sidecars."""

    source: str
    includes: tuple[str, ...]
    core_facts: tuple[Fact, ...]
    evidence_text_facts: tuple[Fact, ...]
    evidence_facts: tuple[Fact, ...]
    evidence_unit_facts: tuple[Fact, ...]
    unknown_facts: tuple[Fact, ...]

    @property
    def all_facts(self) -> tuple[Fact, ...]:
        return (
            self.core_facts
            + self.evidence_text_facts
            + self.evidence_facts
            + self.evidence_unit_facts
            + self.unknown_facts
        )

    def core_source(self, *, include_directives: bool = True) -> str:
        lines: list[str] = []
        if include_directives:
            lines.extend(self.includes)
        lines.extend(fact.render() for fact in self.core_facts)
        return "\n".join(lines) + ("\n" if lines else "")


@dataclass(frozen=True)
class CheckIssue:
    """A checker diagnostic."""

    code: str
    message: str
    line: int = 0
    severity: Literal["error", "warning"] = "error"


@dataclass(frozen=True)
class CheckResult:
    """Structural and evidence-sidecar validation result."""

    issues: tuple[CheckIssue, ...]
    program_valid: bool
    evidence_support_coverage: float = 0.0

    @property
    def errors(self) -> tuple[CheckIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "error")

    @property
    def warnings(self) -> tuple[CheckIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "warning")


@dataclass(frozen=True)
class EvidenceAlignment:
    """Best prepared unit match for one raw evidence-text fact."""

    fact: Fact
    evidence_text: str
    evidence_id: str | None
    score: float
    matched: bool
    unit_id: int | None = None

    def normalized_fact(self) -> Fact | None:
        if not self.matched or self.evidence_id is None:
            return None
        relation = self.fact.relation.removesuffix("_text")
        args = self.fact.args[:-1] + (self.evidence_id,)
        return Fact(relation=relation, args=args, line=self.fact.line)


@dataclass(frozen=True)
class EvidenceAlignmentResult:
    """Evidence alignment output and grounding summary metrics."""

    alignments: tuple[EvidenceAlignment, ...]
    normalized_facts: tuple[Fact, ...]
    evidence_match_rate: float
    reference_unit_coverage: float
    grounding_score: float


@dataclass(frozen=True)
class Finding:
    """One detector/report finding."""

    label: str
    fields: tuple[str, ...] = ()
    severity: str = "warning"
    message: str = ""


@dataclass(frozen=True)
class DetectorResult:
    """Result from the optional Souffle-backed detector runner."""

    status: Literal["ok", "unavailable", "failed"]
    findings: tuple[Finding, ...] = ()
    stdout: str = ""
    stderr: str = ""
    message: str = ""
    output_dir: Path | None = None


@dataclass(frozen=True)
class AuditReport:
    """Small report model shared by plugins and future CLI wrappers."""

    title: str
    source_id: str
    check_result: CheckResult | None = None
    evidence_result: EvidenceAlignmentResult | None = None
    detector_result: DetectorResult | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)


def _quote_arg(arg: str) -> str:
    if arg.isdigit():
        return arg
    escaped = arg.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'
