# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 RiemaLabs
"""Incremental patch support for behavior-map synthesis."""

from __future__ import annotations

import re

_REPLACE_RE = re.compile(r"^//\s*REPLACE:\s*(.+)$")
_REMOVE_RE = re.compile(r"^//\s*REMOVE:\s*(.+)$")
_RELATION_RE = re.compile(r'^[A-Za-z_]\w*\s*\(')


def parse_incremental_diff(source: str) -> dict[str, object] | None:
    """Parse an incremental Datalog diff block.

    Returns ``None`` when the block looks like a complete replacement or
    contains no usable Datalog content.
    """

    lines = source.splitlines()
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#include"):
            return None
        if stripped.startswith("skill(") and stripped.endswith(")."):
            return None

    additions: list[str] = []
    removals: set[str] = set()
    replacements: dict[str, str] = {}
    has_directive = False

    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()

        replace = _REPLACE_RE.match(stripped)
        if replace:
            has_directive = True
            old_fact = replace.group(1).strip()
            index += 1
            while index < len(lines) and not lines[index].strip():
                index += 1
            if index < len(lines) and _looks_like_fact(lines[index]):
                replacements[old_fact] = lines[index].strip()
            index += 1
            continue

        remove = _REMOVE_RE.match(stripped)
        if remove:
            has_directive = True
            removals.add(remove.group(1).strip())
            index += 1
            continue

        if _is_legal_dl_line(line) and _looks_like_fact(line):
            additions.append(stripped)
        index += 1

    if not has_directive and not additions:
        return None
    return {"add": additions, "remove": removals, "replace": replacements}


def apply_incremental_patch(source: str, diff: dict[str, object]) -> str:
    """Apply add/remove/replace operations to a full Datalog source."""

    removals = set(diff.get("remove", set()))
    replacements = dict(diff.get("replace", {}))
    result: list[str] = []

    for line in source.splitlines():
        if not _is_legal_dl_line(line):
            continue
        stripped = line.strip()
        if stripped in removals:
            removals.discard(stripped)
            continue
        if stripped in replacements:
            result.append(str(replacements.pop(stripped)))
            continue
        result.append(line)

    existing = {line.strip() for line in result}
    additions = [
        str(line).strip()
        for line in diff.get("add", [])
        if str(line).strip() and str(line).strip() not in existing
    ]
    if additions:
        if result and result[-1].strip():
            result.append("")
        result.extend(additions)

    return "\n".join(result).rstrip() + "\n"


def _is_legal_dl_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped or stripped.startswith("//"):
        return True
    if stripped.startswith("#"):
        return bool(
            re.match(
                r"^#\s*(include|define|undef|ifdef|ifndef|endif|else|elif)\b",
                stripped,
            )
        )
    return _looks_like_fact(stripped)


def _looks_like_fact(line: str) -> bool:
    stripped = line.strip()
    if not stripped.endswith("."):
        return False
    if not _RELATION_RE.match(stripped):
        return False
    body = stripped[:-1].rstrip()
    if not body.endswith(")"):
        return False
    open_idx = body.find("(")
    inner = body[open_idx + 1 : -1]
    paren_depth = 0
    in_quote = False
    escaped = False
    for ch in inner:
        if escaped:
            escaped = False
            continue
        if ch == "\\" and in_quote:
            escaped = True
            continue
        if ch == '"':
            in_quote = not in_quote
            continue
        if in_quote:
            continue
        if ch == "(":
            paren_depth += 1
        elif ch == ")":
            paren_depth -= 1
            if paren_depth < 0:
                return False
    return paren_depth == 0 and not in_quote
