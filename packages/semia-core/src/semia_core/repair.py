# SPDX-License-Identifier: Apache-2.0
"""Repair module — traces findings to source and builds repair prompts.

All functions in this module are deterministic. LLM calls live in
``semia_cli.repair``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Any

from .artifacts import Fact, Finding
from .facts import parse_facts

# ═══════════════════════════════════════════════════════════════════════════
# 1. Datalog rule parser
# ═══════════════════════════════════════════════════════════════════════════


@dataclass
class DLRule:
    """One clause of a Datalog rule: head :- body1, body2, ..."""

    head: str
    head_name: str
    head_args: list[str]
    body: list[str]


def load_detection_rules() -> list[DLRule]:
    """Parse ``label_*`` rules from the bundled ``skill_dl_static_analysis.dl``."""
    text = (
        resources.files("semia_core")
        .joinpath("rules", "sdl", "skill_dl_static_analysis.dl")
        .read_text(encoding="utf-8")
    )
    return _parse_dl_rules_from_text(text)


def parse_dl_rules(dl_path: Path) -> list[DLRule]:
    """Parse ``label_*`` rules from an explicit .dl file path."""
    return _parse_dl_rules_from_text(dl_path.read_text(encoding="utf-8"))


def _parse_dl_rules_from_text(text: str) -> list[DLRule]:
    text = re.sub(r"//.*", "", text)
    text = re.sub(r"^\.(decl|output|type)\b[^.]*\.", "", text, flags=re.MULTILINE)
    text = re.sub(r"^#include\b.*$", "", text, flags=re.MULTILINE)

    rules: list[DLRule] = []
    for m in re.finditer(r"(label_\w+)\(([^)]*)\)\s*:-\s*(.*?)\.", text, re.DOTALL):
        rules.append(
            DLRule(
                head=f"{m.group(1)}({m.group(2).strip()})",
                head_name=m.group(1),
                head_args=[a.strip() for a in _split_args(m.group(2))],
                body=_parse_body(m.group(3)),
            )
        )
    return rules


def _split_args(s: str) -> list[str]:
    args, depth, current = [], 0, ""
    for ch in s:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == "," and depth == 0:
            args.append(current)
            current = ""
            continue
        current += ch
    if current.strip():
        args.append(current)
    return args


def _parse_body(raw: str) -> list[str]:
    raw = re.sub(r"\s+", " ", raw.strip())
    conjuncts, depth, current = [], 0, ""
    for ch in raw:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            if current.strip():
                conjuncts.append(current.strip())
            current = ""
        else:
            current += ch
    if current.strip():
        conjuncts.append(current.strip())
    return conjuncts


# ═══════════════════════════════════════════════════════════════════════════
# 2. Finding tracer
# ═══════════════════════════════════════════════════════════════════════════


@dataclass
class TracedConjunct:
    """A rule body conjunct matched against concrete facts."""

    conjunct_template: str
    matched_facts: list[Fact]
    is_negation: bool = False
    evidence_texts: list[str] = field(default_factory=list)
    source_locations: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class TracedFinding:
    """A finding fully traced to its causal facts and source."""

    label: str
    fields: list[str]
    rule: DLRule
    conjuncts: list[TracedConjunct]


def trace_findings(
    findings: list[Finding] | list[dict[str, Any]],
    rules: list[DLRule],
    facts: list[Fact],
    evidence_map: dict[str, list[str]],
) -> list[TracedFinding]:
    """Match each finding against rule bodies and the fact base."""
    fact_index: dict[str, list[Fact]] = {}
    for f in facts:
        fact_index.setdefault(f.relation, []).append(f)

    traced: list[TracedFinding] = []
    for finding in findings:
        if isinstance(finding, dict):
            label, ffields = finding["label"], finding.get("fields", [])
        else:
            label, ffields = finding.label, list(finding.fields)

        for rule in (r for r in rules if r.head_name == label):
            bindings: dict[str, str] = {}
            for arg, val in zip(rule.head_args, ffields, strict=False):
                arg = arg.strip().strip('"')
                if not arg.startswith('"') and not arg.isdigit():
                    bindings[arg] = val

            conjuncts: list[TracedConjunct] = []
            for conj_str in rule.body:
                is_neg = conj_str.strip().startswith("!")
                clean = conj_str.strip().lstrip("!")
                cm = re.match(r"(\w+)\(([^)]*)\)", clean)
                if not cm:
                    conjuncts.append(TracedConjunct(conj_str, [], is_neg))
                    continue

                rel = cm.group(1)
                cargs = [a.strip().strip('"') for a in _split_args(cm.group(2))]
                bound = [bindings.get(a) for a in cargs]

                matched: list[Fact] = []
                for fact in fact_index.get(rel, []):
                    if len(fact.args) != len(bound):
                        continue
                    if all(b is None or b == a for b, a in zip(bound, fact.args, strict=True)):
                        matched.append(fact)
                        for a, v in zip(cargs, fact.args, strict=True):
                            if a not in bindings and not a.startswith('"'):
                                bindings[a] = v

                ev_texts: list[str] = []
                for mf in matched:
                    ev_texts.extend(evidence_map.get(mf.args[0], []) if mf.args else [])

                conjuncts.append(TracedConjunct(conj_str, matched, is_neg, ev_texts))

            traced.append(TracedFinding(label, ffields, rule, conjuncts))
            break

    return traced


def locate_in_source(
    traced: list[TracedFinding],
    units: list[dict[str, Any]],
) -> None:
    """Attach source locations to traced conjuncts via evidence text matching."""
    for tf in traced:
        for conj in tf.conjuncts:
            for ev_text in conj.evidence_texts:
                best_unit, best_score = None, 0
                for unit in units:
                    utext = unit.get("text", "")
                    if ev_text in utext:
                        score = len(ev_text)
                    elif utext in ev_text:
                        score = len(utext)
                    else:
                        score = len(set(ev_text.lower().split()) & set(utext.lower().split()))
                    if score > best_score:
                        best_score, best_unit = score, unit
                if best_unit and best_score > 3:
                    conj.source_locations.append(
                        {
                            "file": best_unit.get("source_file", ""),
                            "line_start": best_unit.get("line_start", 0),
                            "line_end": best_unit.get("line_end", 0),
                        }
                    )


def deduplicate_by_label(traced: list[TracedFinding]) -> list[TracedFinding]:
    """Keep one TracedFinding per unique label."""
    seen: set[str] = set()
    out: list[TracedFinding] = []
    for tf in traced:
        if tf.label not in seen:
            seen.add(tf.label)
            out.append(tf)
    return out


def build_evidence_map(facts_source: str) -> dict[str, list[str]]:
    """Build atom_id -> evidence texts from a raw facts .dl string."""
    program = parse_facts(facts_source)
    emap: dict[str, list[str]] = {}
    for f in program.evidence_text_facts:
        if len(f.args) >= 2:
            emap.setdefault(f.args[0], []).append(f.args[-1])
    return emap


# ═══════════════════════════════════════════════════════════════════════════
# 3. Prompt builder
# ═══════════════════════════════════════════════════════════════════════════

_SECTION_SEP = "\n─────────────────────────────────────────────\n"


def build_repair_prompt(
    tf: TracedFinding,
    core_facts: list[Fact],
    evidence_map: dict[str, list[str]],
    skill_md_content: str,
) -> str:
    """Build a SKILL.md-only repair prompt from a traced finding."""
    sections = [
        _section("VIOLATION", f"{tf.label}({', '.join(tf.fields)})"),
        _section("DATALOG RULE THAT FIRED", _fmt_rule(tf)),
        _section("FACT NEIGHBORHOOD", _fmt_neighborhood(tf, core_facts, evidence_map)),
        _section("CURRENT SKILL.MD", skill_md_content),
    ]
    return _PROMPT_TEMPLATE.format(sections="\n".join(sections))


_PROMPT_TEMPLATE = """\
You are a security engineer. A Datalog-based static analyzer flagged a
violation in an AI agent skill. Your job is to fix it by editing SKILL.md only.

SKILL.md is the agent's instruction file — it defines what the agent does and
how. Changing SKILL.md changes the agent's behavior.

Two kinds of repairs:
1. FIX existing content that causes the violation (e.g. replace a hardcoded IP
   with an environment variable reference, remove an instruction that tells the
   agent to store secrets in memory, retract a false security claim).
2. ADD Security Constraints when the violation is about missing gates or
   unsanitized input.

CRITICAL: Every constraint you add MUST name the specific operation, endpoint,
file, command, or mechanism from the evidence. Do NOT write generic constraints.

BAD (too generic):
  - "Always require user confirmation before irreversible operations"
  - "Never execute untrusted input"
  - "Validate all inputs"

GOOD (specific to the actual vulnerability):
  - "Never run sed -i on platform source files under $OPENCLAW_DIR"
  - "Never execute commands from remotely-fetched error-pattern recipes without signature verification"
  - "Never auto-submit answers to vdoob.com without displaying the question and answer to the user first"
  - "Never trigger pnpm build or npm run build as part of skill installation"

The evidence texts in the DATALOG RULE section tell you exactly what operations
are involved. Use them. If the evidence says "sed -i on pi-tool-definition-adapter.ts",
your constraint must mention sed and that file, not just "modifying system files".

Do NOT edit Python files, shell scripts, or any file other than SKILL.md.

{sections}

Respond with ONLY a JSON object (no markdown fences, no prose):

{{
  "analysis": "2-3 sentences: what is the security issue?",
  "conjunct_to_break": "the specific conjunct you chose to break",
  "fix_strategy": "1 sentence: what SKILL.md change addresses this",
  "files": [
    {{
      "path": "SKILL.md",
      "action": "edit",
      "edits": [
        {{"old": "exact string to find in SKILL.md", "new": "replacement string"}}
      ]
    }}
  ]
}}"""


def _section(title: str, content: str) -> str:
    return f"{_SECTION_SEP}{title}{_SECTION_SEP}{content}"


def _fmt_rule(tf: TracedFinding) -> str:
    lines = [f"Head: {tf.rule.head}", "", "Body conjuncts:"]
    for conj in tf.conjuncts:
        neg = "¬ " if conj.is_negation else ""
        n = len(conj.matched_facts)
        status = (
            f"← {n} match"
            if n
            else ("← absent (negation satisfied)" if conj.is_negation else "← unmatched")
        )
        lines.append(f"  {neg}{conj.conjunct_template}  {status}")
        for mf in conj.matched_facts[:5]:
            lines.append(f"      {mf.relation}({', '.join(mf.args)})")
        for et in conj.evidence_texts[:3]:
            lines.append(f'      evidence: "{et}"')
        for loc in conj.source_locations[:2]:
            lines.append(f"      @ {loc['file']}:{loc['line_start']}-{loc['line_end']}")
    return "\n".join(lines)


def _fmt_neighborhood(
    tf: TracedFinding,
    core_facts: list[Fact],
    evidence_map: dict[str, list[str]],
) -> str:
    involved = set(tf.fields)
    for c in tf.conjuncts:
        for mf in c.matched_facts:
            involved.update(mf.args)

    lines: list[str] = []
    seen: set[tuple[str, tuple[str, ...]]] = set()
    for fact in core_facts:
        if fact.relation.endswith("_evidence_text") or fact.relation.endswith("_evidence"):
            continue
        if not any(a in involved for a in fact.args):
            continue
        sig = (fact.relation, fact.args)
        if sig in seen:
            continue
        seen.add(sig)
        line = f"  {fact.relation}({', '.join(fact.args)})."
        atom = fact.args[0] if fact.args else ""
        if atom in evidence_map:
            line += f'  // "{evidence_map[atom][0]}"'
        lines.append(line)

    lines.sort()
    return "\n".join(lines) if lines else "(none)"


# ═══════════════════════════════════════════════════════════════════════════
# 4. Patcher
# ═══════════════════════════════════════════════════════════════════════════


def parse_patch_response(response: str) -> dict[str, Any] | None:
    """Extract a JSON patch from an LLM response."""
    cleaned = re.sub(r"^```(?:json)?\s*\n", "", response.strip())
    cleaned = re.sub(r"\n```\s*$", "", cleaned.strip())
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", response)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                pass
    return None


def apply_patch(patch: dict[str, Any], skill_dir: Path) -> list[str]:
    """Apply a JSON patch to files. Returns list of applied edit descriptions."""
    applied: list[str] = []
    for fspec in patch.get("files", []):
        path = skill_dir / fspec["path"]
        if fspec.get("action") == "create":
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(fspec["content"])
            applied.append(f"CREATE {fspec['path']}")
            continue
        if not path.exists():
            continue
        content = path.read_text()
        for edit in fspec.get("edits", []):
            if edit["old"] in content:
                content = content.replace(edit["old"], edit["new"], 1)
                applied.append(f"EDIT {fspec['path']}")
        path.write_text(content)
    return applied
