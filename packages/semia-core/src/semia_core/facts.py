# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 RiemaLabs
"""Souffle-style SDL fact parser."""

from __future__ import annotations

import re

from .artifacts import Fact, FactProgram
from .schema import CORE_SCHEMA, EVIDENCE_SCHEMA, EVIDENCE_TEXT_SCHEMA, EVIDENCE_UNIT_SCHEMA

_RELATION_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class FactParseError(ValueError):
    """Raised when strict parsing encounters an invalid SDL line."""


def parse_facts(source: str, *, strict: bool = False) -> FactProgram:
    """Parse SDL facts and split core facts from evidence sidecars."""

    includes: list[str] = []
    directives: list[str] = []
    core: list[Fact] = []
    evidence_text: list[Fact] = []
    evidence: list[Fact] = []
    evidence_units: list[Fact] = []
    unknown: list[Fact] = []
    for lineno, line in enumerate(source.splitlines(), 1):
        stripped = _strip_comment(line).strip()
        if not stripped:
            continue
        if stripped.startswith("#include"):
            includes.append(stripped)
            continue
        if stripped.startswith("#"):
            directives.append(stripped)
            continue
        try:
            fact = parse_fact_line(stripped, line=lineno)
        except FactParseError as exc:
            if strict:
                raise
            unknown.append(Fact("__parse_error__", (str(exc),), lineno, line))
            continue
        if fact.relation in CORE_SCHEMA:
            core.append(fact)
        elif fact.relation in EVIDENCE_TEXT_SCHEMA:
            evidence_text.append(fact)
        elif fact.relation in EVIDENCE_SCHEMA:
            evidence.append(fact)
        elif fact.relation in EVIDENCE_UNIT_SCHEMA:
            evidence_units.append(fact)
        else:
            unknown.append(fact)

    return FactProgram(
        source=source,
        includes=tuple(includes),
        core_facts=tuple(core),
        evidence_text_facts=tuple(evidence_text),
        evidence_facts=tuple(evidence),
        evidence_unit_facts=tuple(evidence_units),
        unknown_facts=tuple(unknown),
        preprocessor_directives=tuple(directives),
    )


def parse_fact_line(line_text: str, *, line: int = 0) -> Fact:
    raw = line_text
    if not line_text.endswith("."):
        raise FactParseError("fact must end with '.'")
    body = line_text[:-1].strip()
    open_idx = body.find("(")
    if open_idx <= 0 or not body.endswith(")"):
        raise FactParseError("fact must have relation(args) shape")
    relation = body[:open_idx].strip()
    if not _RELATION_RE.match(relation):
        raise FactParseError(f"invalid relation name {relation!r}")
    arg_source = body[open_idx + 1 : -1].strip()
    args = tuple(_parse_args(arg_source))
    return Fact(relation=relation, args=args, line=line, raw=raw)


def _parse_args(arg_source: str) -> list[str]:
    if not arg_source:
        return []
    args: list[str] = []
    current: list[str] = []
    in_quote = False
    escaped = False
    for ch in arg_source:
        if escaped:
            current.append(ch)
            escaped = False
            continue
        if ch == "\\" and in_quote:
            escaped = True
            continue
        if ch == '"':
            in_quote = not in_quote
            continue
        if ch == "," and not in_quote:
            args.append("".join(current).strip())
            current = []
            continue
        current.append(ch)
    if in_quote:
        raise FactParseError("unterminated quoted string")
    args.append("".join(current).strip())
    return args


def _strip_comment(line: str) -> str:
    in_quote = False
    escaped = False
    i = 0
    while i < len(line):
        ch = line[i]
        if escaped:
            escaped = False
            i += 1
            continue
        if ch == "\\" and in_quote:
            escaped = True
            i += 1
            continue
        if ch == '"':
            in_quote = not in_quote
            i += 1
            continue
        if not in_quote and line.startswith("//", i):
            return line[:i]
        i += 1
    return line
