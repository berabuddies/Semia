# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 RiemaLabs
"""Shell script parser using regex + brace tracking for functions.

Distinguishes top-of-file setup blocks (``source`` / ``.`` / ``export``
lines), function signatures in either ``foo() { ... }`` or
``function foo { ... }`` form (whose bodies are split into ``sh_command``
units), here-doc blocks, and lone command lines.
"""

from __future__ import annotations

import re

UNIT_TYPE_FUNCTION_DEF = "sh_function_def"
UNIT_TYPE_HEREDOC = "sh_heredoc"
UNIT_TYPE_COMMAND = "sh_command"
UNIT_TYPE_SETUP_BLOCK = "sh_setup_block"

_FUNC_PAREN_RE = re.compile(r"^\s*([A-Za-z_][\w]*)\s*\(\s*\)\s*\{")
_FUNC_KW_RE = re.compile(r"^\s*function\s+([A-Za-z_][\w]*)\s*(?:\(\s*\))?\s*\{")
_HEREDOC_RE = re.compile(r"<<[-]?\s*['\"]?([A-Za-z_][\w]*)['\"]?")
_SETUP_RE = re.compile(r"^\s*(?:source\s+|\.\s+|export\s+[A-Z_][\w]*=|[A-Z_][\w]*=)")


def parse_shell_units(
    source: str,
    source_file: str = "",
) -> list[tuple[str, str, int, int]]:
    del source_file
    lines = source.splitlines()
    units: list[tuple[str, str, int, int]] = []

    setup_indices: list[int] = []
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if not stripped or stripped.startswith("#"):
            if not setup_indices:
                i += 1
                continue
            break
        if _SETUP_RE.match(lines[i]):
            setup_indices.append(i)
            i += 1
            continue
        break
    if setup_indices:
        start = setup_indices[0] + 1
        end = setup_indices[-1] + 1
        text = "\n".join(lines[start - 1 : end])
        units.append((UNIT_TYPE_SETUP_BLOCK, text, start, end))

    i = 0
    while i < len(lines):
        if i in set(setup_indices):
            i += 1
            continue
        line = lines[i]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue

        m_func = _FUNC_PAREN_RE.match(line) or _FUNC_KW_RE.match(line)
        if m_func:
            end_idx = _find_brace_end(lines, i)
            units.append((UNIT_TYPE_FUNCTION_DEF, line, i + 1, i + 1))
            _emit_body_commands(units, lines, i + 1, end_idx)
            i = end_idx + 1
            continue

        m_heredoc = _HEREDOC_RE.search(line)
        if m_heredoc:
            marker = m_heredoc.group(1)
            end_idx = _find_heredoc_end(lines, i + 1, marker)
            text = "\n".join(lines[i : end_idx + 1])
            units.append((UNIT_TYPE_HEREDOC, text, i + 1, end_idx + 1))
            i = end_idx + 1
            continue

        units.append((UNIT_TYPE_COMMAND, stripped, i + 1, i + 1))
        i += 1

    return units


def _emit_body_commands(
    units: list[tuple[str, str, int, int]],
    lines: list[str],
    start: int,
    end_idx: int,
) -> None:
    j = start
    while j < end_idx:
        body_line = lines[j].strip()
        if not body_line or body_line.startswith("#") or body_line == "}":
            j += 1
            continue
        m_inner_heredoc = _HEREDOC_RE.search(lines[j])
        if m_inner_heredoc:
            marker = m_inner_heredoc.group(1)
            inner_end = _find_heredoc_end(lines, j + 1, marker)
            if inner_end > end_idx - 1:
                inner_end = end_idx - 1
            heredoc_text = "\n".join(lines[j : inner_end + 1])
            units.append((UNIT_TYPE_HEREDOC, heredoc_text, j + 1, inner_end + 1))
            j = inner_end + 1
            continue
        units.append((UNIT_TYPE_COMMAND, body_line, j + 1, j + 1))
        j += 1


_WORD_BOUNDARY_FOR_COMMENT = frozenset({"", " ", "\t", ";", "&", "|", "(", ")"})


def _find_brace_end(lines: list[str], from_line: int) -> int:
    """Find the line of the ``}`` that balances the first ``{`` at-or-after ``from_line``.

    Tracks string and comment state so braces inside ``"..."``, ``'...'``, or
    after a word-initial ``#`` (outside a string) do not affect depth.
    Single-quoted strings in shell do not interpret ``\\``; double-quoted
    strings honor ``\\\\`` and ``\\"``. A ``#`` is only treated as a comment
    when it stands at a word boundary — preceded by whitespace or one of
    ``;&|()`` — so ``$#`` (positional-arg count) and ``foo#bar`` are not
    swallowed. Here-doc bodies are NOT tracked — callers detect here-docs
    separately and route into :func:`_find_heredoc_end`.
    """

    depth = 0
    seen = False
    in_str: str | None = None
    escaped = False
    for idx in range(from_line, len(lines)):
        line = lines[idx]
        prev_ch = ""  # treat start-of-line as a word boundary
        for ch in line:
            if escaped:
                escaped = False
                prev_ch = ch
                continue
            if in_str == '"':
                if ch == "\\":
                    escaped = True
                    continue
                if ch == '"':
                    in_str = None
                prev_ch = ch
                continue
            if in_str == "'":
                if ch == "'":
                    in_str = None
                prev_ch = ch
                continue
            if ch == "#" and prev_ch in _WORD_BOUNDARY_FOR_COMMENT:
                break  # comment runs to end-of-line
            if ch in ('"', "'"):
                in_str = ch
                prev_ch = ch
                continue
            if ch == "{":
                depth += 1
                seen = True
            elif ch == "}":
                depth -= 1
                if seen and depth == 0:
                    return idx
            prev_ch = ch
        # newline closes any in-line comment; string state persists across
        # newlines for multi-line quoted commands.
    return len(lines) - 1


def _find_heredoc_end(lines: list[str], from_line: int, marker: str) -> int:
    for idx in range(from_line, len(lines)):
        if lines[idx].strip() == marker:
            return idx
    return len(lines) - 1
