# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 berabuddies
"""Structural checker for SDL core facts and evidence sidecars."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass

from .artifacts import CheckIssue, CheckResult, Fact, FactProgram
from .facts import parse_facts
from .schema import (
    ALLOWED_CALL_CODES,
    ALLOWED_DOC_CLAIMS,
    ALLOWED_EFFECTS,
    ALLOWED_GATES,
    ALLOWED_TRIGGERS,
    ALLOWED_VALUE_KINDS,
    KNOWN_FACT_SCHEMA,
    MECHANICAL_FACT_RELATIONS,
)


@dataclass(frozen=True)
class CheckOptions:
    """Toggles for plugin/CLI consumers with different strictness needs."""

    require_include: bool = False
    require_evidence: bool = True


def check_program(
    source_or_program: str | FactProgram,
    *,
    options: CheckOptions | None = None,
) -> CheckResult:
    """Run the small SDL structural checker."""

    opts = options or CheckOptions()
    program = (
        parse_facts(source_or_program) if isinstance(source_or_program, str) else source_or_program
    )
    issues: list[CheckIssue] = []
    facts_by_rel = _index(program.core_facts)
    all_by_rel = _index(program.all_facts)

    _check_parse_and_schema(program, issues)
    _check_include(program, issues, required=opts.require_include)
    _check_single_skill(facts_by_rel, issues)
    _check_references(facts_by_rel, issues)
    _check_enums(facts_by_rel, issues)
    _check_duplicates(program.all_facts, issues)
    _check_call_graph_connectivity(facts_by_rel, issues)
    _check_value_definitions(facts_by_rel, issues)
    _check_policy_consistency(facts_by_rel, issues)
    _check_annotation_consistency(facts_by_rel, issues)
    support_coverage = _check_typed_evidence(
        program, all_by_rel, issues, required=opts.require_evidence
    )

    program_valid = not any(issue.severity == "error" for issue in issues)
    return CheckResult(
        issues=tuple(issues),
        program_valid=program_valid,
        evidence_support_coverage=support_coverage,
    )


def _index(facts: tuple[Fact, ...]) -> dict[str, list[Fact]]:
    by_rel: dict[str, list[Fact]] = defaultdict(list)
    for fact in facts:
        by_rel[fact.relation].append(fact)
    return by_rel


def _issue(
    issues: list[CheckIssue],
    code: str,
    message: str,
    *,
    fact: Fact | None = None,
    severity: str = "error",
) -> None:
    issues.append(
        CheckIssue(code=code, message=message, line=fact.line if fact else 0, severity=severity)
    )  # type: ignore[arg-type]


def _check_parse_and_schema(program: FactProgram, issues: list[CheckIssue]) -> None:
    for fact in program.unknown_facts:
        if fact.relation == "__parse_error__":
            _issue(issues, "SDL001", fact.args[0], fact=fact)
        else:
            _issue(issues, "SDL002", f"unknown relation {fact.relation!r}", fact=fact)

    for fact in program.all_facts:
        if fact.relation not in KNOWN_FACT_SCHEMA:
            continue
        expected = KNOWN_FACT_SCHEMA[fact.relation]
        if len(fact.args) != expected:
            _issue(
                issues,
                "SDL003",
                f"{fact.relation} expects {expected} args, got {len(fact.args)}",
                fact=fact,
            )


def _check_include(program: FactProgram, issues: list[CheckIssue], *, required: bool) -> None:
    if not required:
        return
    if not any("skill_dl_static_analysis.dl" in include for include in program.includes):
        _issue(issues, "SDL004", "missing #include for skill_dl_static_analysis.dl")


def _check_single_skill(by_rel: dict[str, list[Fact]], issues: list[CheckIssue]) -> None:
    count = len(by_rel.get("skill", []))
    if count != 1:
        _issue(issues, "SDL005", f"expected exactly one skill() fact, found {count}")


def _ids(by_rel: dict[str, list[Fact]], relation: str, idx: int = 0) -> set[str]:
    return {fact.args[idx] for fact in by_rel.get(relation, []) if len(fact.args) > idx}


def _check_references(by_rel: dict[str, list[Fact]], issues: list[CheckIssue]) -> None:
    skills = _ids(by_rel, "skill")
    actions = _ids(by_rel, "action")
    calls = _ids(by_rel, "call")
    values = _declared_values(by_rel)

    for fact in by_rel.get("action", []):
        if len(fact.args) >= 2 and fact.args[1] not in skills:
            _issue(
                issues,
                "SDL010",
                f"action {fact.args[0]!r} references undeclared skill {fact.args[1]!r}",
                fact=fact,
            )
    for relation in ("action_trigger", "action_gate", "action_param"):
        for fact in by_rel.get(relation, []):
            if fact.args and fact.args[0] not in actions:
                _issue(
                    issues,
                    "SDL011",
                    f"{relation} references undeclared action {fact.args[0]!r}",
                    fact=fact,
                )
    for fact in by_rel.get("call", []):
        if len(fact.args) >= 2 and fact.args[1] not in actions:
            _issue(
                issues,
                "SDL012",
                f"call {fact.args[0]!r} references undeclared action {fact.args[1]!r}",
                fact=fact,
            )
    for relation in (
        "call_effect",
        "call_code",
        "call_action",
        "call_action_arg",
        "call_region",
        "call_input",
        "call_output",
        "call_region_untrusted",
        "call_region_sensitive",
        "call_region_secret",
    ):
        for fact in by_rel.get(relation, []):
            if fact.args and fact.args[0] not in calls:
                _issue(
                    issues,
                    "SDL013",
                    f"{relation} references undeclared call {fact.args[0]!r}",
                    fact=fact,
                )
    for relation in ("call_unconditional", "call_conditional"):
        for fact in by_rel.get(relation, []):
            for cid in fact.args[:2]:
                if cid not in calls:
                    _issue(
                        issues,
                        "SDL014",
                        f"{relation} references undeclared call {cid!r}",
                        fact=fact,
                    )
    for fact in by_rel.get("call_action", []):
        if len(fact.args) >= 2 and fact.args[1] not in actions:
            _issue(
                issues,
                "SDL015",
                f"call_action references undeclared action {fact.args[1]!r}",
                fact=fact,
            )
    for fact in by_rel.get("value", []):
        if len(fact.args) >= 2 and fact.args[1] not in actions:
            _issue(
                issues,
                "SDL016",
                f"value {fact.args[0]!r} references undeclared action {fact.args[1]!r}",
                fact=fact,
            )
    for relation in ("value_sensitive_allowed_action", "value_secret_allowed_action"):
        for fact in by_rel.get(relation, []):
            if len(fact.args) >= 1 and fact.args[0] not in values:
                _issue(
                    issues,
                    "SDL017",
                    f"{relation} references undeclared value {fact.args[0]!r}",
                    fact=fact,
                )
            if len(fact.args) >= 2 and fact.args[1] not in actions:
                _issue(
                    issues,
                    "SDL018",
                    f"{relation} references undeclared action {fact.args[1]!r}",
                    fact=fact,
                )


def _check_enums(by_rel: dict[str, list[Fact]], issues: list[CheckIssue]) -> None:
    _check_enum(by_rel, "call_effect", 1, ALLOWED_EFFECTS, "SDL020", issues)
    _check_enum(by_rel, "action_trigger", 1, ALLOWED_TRIGGERS, "SDL021", issues)
    _check_enum(by_rel, "skill_doc_claim", 1, ALLOWED_DOC_CLAIMS, "SDL022", issues)
    _check_enum(by_rel, "value", 2, ALLOWED_VALUE_KINDS, "SDL023", issues)
    _check_enum(by_rel, "call_code", 1, ALLOWED_CALL_CODES, "SDL024", issues)
    _check_enum(by_rel, "action_gate", 1, ALLOWED_GATES, "SDL025", issues)


def _check_enum(
    by_rel: dict[str, list[Fact]],
    relation: str,
    idx: int,
    allowed: frozenset[str],
    code: str,
    issues: list[CheckIssue],
) -> None:
    for fact in by_rel.get(relation, []):
        if len(fact.args) > idx and fact.args[idx] not in allowed:
            _issue(issues, code, f"{relation} has invalid enum {fact.args[idx]!r}", fact=fact)


def _check_duplicates(facts: tuple[Fact, ...], issues: list[CheckIssue]) -> None:
    seen: set[tuple[str, tuple[str, ...]]] = set()
    for fact in facts:
        if fact.relation == "__parse_error__":
            continue
        key = fact.signature
        if key in seen:
            _issue(issues, "SDL030", f"duplicate fact {fact.render()}", fact=fact)
        seen.add(key)


def _check_call_graph_connectivity(by_rel: dict[str, list[Fact]], issues: list[CheckIssue]) -> None:
    action_calls: dict[str, set[str]] = defaultdict(set)
    call_to_action: dict[str, str] = {}
    for fact in by_rel.get("call", []):
        if len(fact.args) >= 2:
            call_to_action[fact.args[0]] = fact.args[1]
            action_calls[fact.args[1]].add(fact.args[0])

    edges: dict[str, set[str]] = defaultdict(set)
    incoming: dict[str, set[str]] = defaultdict(set)
    for relation in ("call_unconditional", "call_conditional"):
        for fact in by_rel.get(relation, []):
            if len(fact.args) >= 2:
                before, after = fact.args[0], fact.args[1]
                edges[before].add(after)
                incoming[after].add(before)
                if (
                    before in call_to_action
                    and after in call_to_action
                    and call_to_action[before] != call_to_action[after]
                ):
                    _issue(
                        issues,
                        "SDL031",
                        f"{relation} crosses action boundary from {before!r} to {after!r}",
                        fact=fact,
                    )

    for action, calls in action_calls.items():
        if len(calls) <= 1:
            continue
        roots = {call for call in calls if not (incoming.get(call, set()) & calls)}
        if not roots:
            _issue(issues, "SDL032", f"action {action!r} has no root call")
            continue
        visited: set[str] = set()
        queue: deque[str] = deque(sorted(roots))
        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            for nxt in sorted(edges.get(current, set()) & calls):
                queue.append(nxt)
        missing = calls - visited
        if missing:
            _issue(
                issues,
                "SDL033",
                f"action {action!r} has unreachable calls: {', '.join(sorted(missing))}",
            )


def _check_value_definitions(by_rel: dict[str, list[Fact]], issues: list[CheckIssue]) -> None:
    values = _declared_values(by_rel)
    explicit_sources = {
        fact.args[2] for fact in by_rel.get("action_param", []) if len(fact.args) >= 3
    }
    allowed = values | explicit_sources
    for relation, indexes in {
        "call_region": (1,),
        "call_input": (1,),
        "call_output": (1,),
        "call_conditional": (2,),
        "call_action_arg": (1, 2),
    }.items():
        for fact in by_rel.get(relation, []):
            for idx in indexes:
                if len(fact.args) > idx and fact.args[idx] not in allowed:
                    _issue(
                        issues,
                        "SDL040",
                        f"{relation} references undeclared value {fact.args[idx]!r}",
                        fact=fact,
                    )


def _check_policy_consistency(by_rel: dict[str, list[Fact]], issues: list[CheckIssue]) -> None:
    value_kinds = {
        fact.args[0]: fact.args[2] for fact in by_rel.get("value", []) if len(fact.args) >= 3
    }
    secret_allowed = _ids(by_rel, "value_secret_allowed_action")
    sensitive_allowed = _ids(by_rel, "value_sensitive_allowed_action")
    for value_id, kind in value_kinds.items():
        if kind == "secret" and value_id not in secret_allowed:
            _issue(
                issues, "SDL050", f"secret value {value_id!r} has no value_secret_allowed_action"
            )
        if kind == "sensitive_local" and value_id not in sensitive_allowed:
            _issue(
                issues,
                "SDL051",
                f"sensitive value {value_id!r} has no value_sensitive_allowed_action",
            )


def _check_annotation_consistency(by_rel: dict[str, list[Fact]], issues: list[CheckIssue]) -> None:
    untrusted = _ids(by_rel, "call_region_untrusted")
    sensitive = _ids(by_rel, "call_region_sensitive")
    secret = _ids(by_rel, "call_region_secret")
    for cid in sorted(untrusted & sensitive):
        _issue(
            issues, "SDL060", f"call {cid!r} has both untrusted and sensitive region annotations"
        )
    for cid in sorted(untrusted & secret):
        _issue(issues, "SDL061", f"call {cid!r} has both untrusted and secret region annotations")


def _check_typed_evidence(
    program: FactProgram,
    all_by_rel: dict[str, list[Fact]],
    issues: list[CheckIssue],
    *,
    required: bool,
) -> float:
    evidence_units = _ids(all_by_rel, "evidence_unit")
    core_keys = {_support_key_for_core(fact) for fact in program.core_facts}
    for fact in program.evidence_facts:
        if (
            fact.args
            and fact.args[-1].startswith("su_")
            and evidence_units
            and fact.args[-1] not in evidence_units
        ):
            _issue(
                issues,
                "EVD010",
                f"{fact.relation} references unknown evidence handle {fact.args[-1]!r}",
                fact=fact,
                severity="warning",
            )

    evidence_keys = _evidence_target_keys(program)
    for fact in program.evidence_text_facts + program.evidence_facts:
        if _support_key_for_evidence(fact) not in core_keys:
            _issue(
                issues,
                "EVD011",
                f"{fact.relation} does not target an existing core fact",
                fact=fact,
                severity="warning",
            )

    for fact in program.core_facts:
        if _support_key_for_core(fact) in evidence_keys:
            continue
        if required and fact.relation not in MECHANICAL_FACT_RELATIONS:
            _issue(
                issues,
                "EVD012",
                f"core fact lacks typed evidence: {fact.render()}",
                fact=fact,
                severity="warning",
            )

    required_facts = sum(
        1 for f in program.core_facts if f.relation not in MECHANICAL_FACT_RELATIONS
    )
    supported = sum(
        1
        for f in program.core_facts
        if f.relation not in MECHANICAL_FACT_RELATIONS and _support_key_for_core(f) in evidence_keys
    )

    return supported / required_facts if required_facts else 1.0


def _evidence_target_keys(program: FactProgram) -> set[tuple[str, tuple[str, ...]]]:
    keys: set[tuple[str, tuple[str, ...]]] = set()
    for fact in program.evidence_text_facts + program.evidence_facts:
        keys.add(_support_key_for_evidence(fact))
    return keys


def _support_key_for_core(fact: Fact) -> tuple[str, tuple[str, ...]]:
    if fact.relation == "skill" and len(fact.args) >= 1:
        return ("skill", fact.args[:1])
    if fact.relation == "action" and len(fact.args) >= 1:
        return ("action", fact.args[:1])
    if fact.relation == "call" and len(fact.args) >= 1:
        return ("call", fact.args[:1])
    if fact.relation == "value" and len(fact.args) >= 2:
        return ("value", fact.args[:2])
    return fact.signature


def _support_key_for_evidence(fact: Fact) -> tuple[str, tuple[str, ...]]:
    relation = fact.relation.removesuffix("_evidence_text").removesuffix("_evidence")
    return (relation, fact.args[:-1])


def _declared_values(by_rel: dict[str, list[Fact]]) -> set[str]:
    return {fact.args[0] for fact in by_rel.get("value", []) if fact.args}


def compute_ssa_input_availability(program: FactProgram) -> float:
    """Fraction of call_input variables sourced from declared values,
    action_param, or an earlier call_output in the same action chain.

    1.0 means every input has a source; lower scores hint at LLM-hallucinated
    variables. Mechanical lint, not a structural error.
    """

    by_rel = _index(program.core_facts)
    action_calls: dict[str, set[str]] = defaultdict(set)
    call_to_action: dict[str, str] = {}
    for f in by_rel.get("call", []):
        if len(f.args) >= 2:
            action_calls[f.args[1]].add(f.args[0])
            call_to_action[f.args[0]] = f.args[1]
    call_outputs: dict[str, set[str]] = defaultdict(set)
    for f in by_rel.get("call_output", []):
        if len(f.args) >= 2:
            call_outputs[f.args[0]].add(f.args[1])
    action_params: dict[str, set[str]] = defaultdict(set)
    for f in by_rel.get("action_param", []):
        if len(f.args) >= 3:
            action_params[f.args[0]].add(f.args[2])
    values_by_action: dict[str, set[str]] = defaultdict(set)
    for f in by_rel.get("value", []):
        if len(f.args) >= 2:
            values_by_action[f.args[1]].add(f.args[0])
    backward: dict[str, set[str]] = defaultdict(set)
    for rel in ("call_unconditional", "call_conditional"):
        for f in by_rel.get(rel, []):
            if len(f.args) >= 2:
                backward[f.args[1]].add(f.args[0])

    total = 0
    available = 0
    for f in by_rel.get("call_input", []):
        if len(f.args) < 2:
            continue
        total += 1
        c, v = f.args[0], f.args[1]
        a = call_to_action.get(c)
        if v in action_params.get(a, set()) or v in values_by_action.get(a, set()):
            available += 1
            continue
        seen: set[str] = set()
        queue = list(backward.get(c, set()))
        found = False
        while queue:
            x = queue.pop()
            if x in seen:
                continue
            seen.add(x)
            if v in call_outputs.get(x, set()):
                found = True
                break
            queue.extend(backward.get(x, set()))
        if found:
            available += 1
    return available / total if total else 1.0
