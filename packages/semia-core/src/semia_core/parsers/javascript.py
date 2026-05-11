# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 berabuddies
"""JavaScript / TypeScript source parser using regex + brace tracking.

Recognizes top-level imports, function/class declarations (including
generators and default exports), arrow-assigned constants, TS interface/type
aliases, JSX expressions, and class fields. Each function/class produces a
SIGNATURE-only unit (``js_function_def`` / ``js_class_def``) plus inner
statements; arrow expressions without block bodies stay one unit. Falls back
to an empty list when the file is non-trivial but yields no declarations, or
when the source looks minified, so the caller can use per-line fenced_code.
"""

from __future__ import annotations

import re

UNIT_TYPE_FUNCTION_DEF = "js_function_def"
UNIT_TYPE_CLASS_DEF = "js_class_def"
UNIT_TYPE_IMPORT_BLOCK = "js_import_block"
UNIT_TYPE_CONST = "js_const"
UNIT_TYPE_TYPE = "js_type"
UNIT_TYPE_STATEMENT = "js_statement"

_IMPORT_RE = re.compile(r"^\s*(?:import|export\s+\*|export\s*\{)\b")
_FUNCTION_NAMED_RE = re.compile(
    r"^\s*(?:export\s+(?:default\s+)?)?(?:async\s+)?function\s*\*?\s*([A-Za-z_$][\w$]*)\s*\("
)
_FUNCTION_ANON_RE = re.compile(r"^\s*export\s+default\s+(?:async\s+)?function\s*\*?\s*\(")
_CLASS_RE = re.compile(
    r"^\s*(?:export\s+(?:default\s+)?)?(?:abstract\s+)?class\s+([A-Za-z_$][\w$]*)\b"
)
_CLASS_ANON_RE = re.compile(r"^\s*export\s+default\s+(?:abstract\s+)?class\b(?!\s+[A-Za-z_$])")
_ARROW_RE = re.compile(
    r"^\s*(?:export\s+(?:default\s+)?)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*(?::\s*[^=]+)?=\s*(?:async\s*)?(?:\([^)]*\)|[A-Za-z_$][\w$]*)\s*=>"
)
_CONST_RE = re.compile(
    r"^\s*(?:export\s+(?:default\s+)?)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*[:=]"
)
_TYPE_RE = re.compile(r"^\s*(?:export\s+(?:default\s+)?)?(?:interface|type)\s+([A-Za-z_$][\w$]*)\b")


def parse_javascript_units(
    source: str,
    source_file: str = "",
) -> list[tuple[str, str, int, int]]:
    """Parse JS/TS source into structured units.

    Returns an empty list when no declarations are detected and the file is
    longer than five lines, or when the input looks minified (single long
    line), so the caller can choose per-line fallback.
    """

    del source_file
    lines = source.splitlines()
    if len(lines) == 1 and len(source) > 500:
        return []
    units: list[tuple[str, str, int, int]] = []

    import_lines: list[int] = []
    in_block_comment = False
    i = 0
    # Walk through leading comments / blank lines until we either find imports
    # or hit a non-import statement. Multi-line imports (TS-style brace lists)
    # naturally span; we keep collecting consecutive lines once import mode
    # opens until brace depth returns to zero and we hit a non-import line.
    pending_import_open = False
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if in_block_comment:
            if "*/" in stripped:
                in_block_comment = False
            i += 1
            continue
        if not stripped:
            i += 1
            if pending_import_open:
                continue
            if not import_lines:
                continue
            break
        if stripped.startswith("/*"):
            if "*/" not in stripped:
                in_block_comment = True
            i += 1
            continue
        if stripped.startswith("//"):
            i += 1
            continue
        if pending_import_open:
            import_lines.append(i)
            if stripped.endswith(";") or stripped.endswith(")"):
                pending_import_open = False
            i += 1
            continue
        if _IMPORT_RE.match(line) or (stripped.startswith("require(") and import_lines):
            import_lines.append(i)
            # Multi-line import keeps consuming until `;` or `)` at top level.
            if not (stripped.endswith(";") or stripped.endswith(")")):
                pending_import_open = True
            i += 1
            continue
        break
    if import_lines:
        start = import_lines[0] + 1
        end = import_lines[-1] + 1
        text = "\n".join(lines[start - 1 : end])
        units.append((UNIT_TYPE_IMPORT_BLOCK, text, start, end))

    line_starts = _build_line_starts(source)
    depth_zero_positions = _scan_top_level_starts(source)

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped or i in set(import_lines):
            i += 1
            continue
        pos = line_starts[i]
        if pos not in depth_zero_positions:
            i += 1
            continue

        m_func = _FUNCTION_NAMED_RE.match(line) or _FUNCTION_ANON_RE.match(line)
        m_class = _CLASS_RE.match(line) or _CLASS_ANON_RE.match(line)
        m_arrow = _ARROW_RE.match(line)
        m_const = _CONST_RE.match(line)
        m_type = _TYPE_RE.match(line)

        if m_func:
            end_idx = _find_block_end(source, line_starts, i)
            sig_end_idx = _find_signature_end(lines, i, end_idx)
            sig_text = "\n".join(lines[i : sig_end_idx + 1])
            units.append((UNIT_TYPE_FUNCTION_DEF, sig_text, i + 1, sig_end_idx + 1))
            _emit_body_statements(units, lines, line_starts, source, sig_end_idx + 1, end_idx)
            i = end_idx + 1
            continue
        if m_class:
            end_idx = _find_block_end(source, line_starts, i)
            sig_end_idx = _find_signature_end(lines, i, end_idx)
            sig_text = "\n".join(lines[i : sig_end_idx + 1])
            units.append((UNIT_TYPE_CLASS_DEF, sig_text, i + 1, sig_end_idx + 1))
            _emit_class_members(units, lines, line_starts, source, sig_end_idx + 1, end_idx)
            i = end_idx + 1
            continue
        if m_arrow:
            end_idx = _find_arrow_end(source, line_starts, i)
            text = "\n".join(lines[i : end_idx + 1])
            units.append((UNIT_TYPE_FUNCTION_DEF, text, i + 1, end_idx + 1))
            i = end_idx + 1
            continue
        if m_type:
            end_idx = _find_statement_end(source, line_starts, i)
            text = "\n".join(lines[i : end_idx + 1])
            units.append((UNIT_TYPE_TYPE, text, i + 1, end_idx + 1))
            i = end_idx + 1
            continue
        if m_const:
            end_idx = _find_statement_end(source, line_starts, i)
            text = "\n".join(lines[i : end_idx + 1])
            units.append((UNIT_TYPE_CONST, text, i + 1, end_idx + 1))
            i = end_idx + 1
            continue
        units.append((UNIT_TYPE_STATEMENT, stripped, i + 1, i + 1))
        i += 1

    # Files yielding ONLY js_statement units may be valid: test files with
    # describe()/it() calls, runtime-only scripts. Only reject when the parser
    # produced literally nothing for a multi-line file (a sign the source is
    # weird enough that per-line fenced_code is more honest).
    if not units and len(lines) > 5:
        return []
    return units


def _has_declarations(units: list[tuple[str, str, int, int]]) -> bool:
    for unit_type, _, _, _ in units:
        if unit_type in {
            UNIT_TYPE_FUNCTION_DEF,
            UNIT_TYPE_CLASS_DEF,
            UNIT_TYPE_CONST,
            UNIT_TYPE_TYPE,
            UNIT_TYPE_IMPORT_BLOCK,
        }:
            return True
    return False


def _build_line_starts(source: str) -> list[int]:
    starts = [0]
    for i, ch in enumerate(source):
        if ch == "\n":
            starts.append(i + 1)
    return starts


def _scan_top_level_starts(source: str) -> set[int]:
    """Return character offsets where each line begins at brace-depth 0."""

    depth = 0
    in_str: str | None = None
    in_line_comment = False
    in_block_comment = False
    in_template = 0
    jsx_depth = 0
    positions: set[int] = {0}
    i = 0
    n = len(source)
    while i < n:
        ch = source[i]
        nxt = source[i + 1] if i + 1 < n else ""
        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
                if depth == 0 and in_str is None and in_template == 0 and jsx_depth == 0:
                    positions.add(i + 1)
            i += 1
            continue
        if in_block_comment:
            if ch == "*" and nxt == "/":
                in_block_comment = False
                i += 2
                continue
            i += 1
            continue
        if in_str is not None:
            if ch == "\\":
                i += 2
                continue
            if ch == in_str:
                in_str = None
            elif ch == "\n" and depth == 0 and in_template == 0 and jsx_depth == 0:
                positions.add(i + 1)
            i += 1
            continue
        if in_template > 0:
            if ch == "\\":
                i += 2
                continue
            if ch == "`":
                in_template -= 1
                i += 1
                continue
            if ch == "$" and nxt == "{":
                depth += 1
                i += 2
                continue
            if ch == "\n":
                i += 1
                continue
            i += 1
            continue
        if jsx_depth > 0:
            if ch == "<" and nxt == "/":
                jsx_depth -= 1
                i += 2
                continue
            if ch == "/" and nxt == ">":
                jsx_depth -= 1
                i += 2
                continue
            if ch == "<" and i + 1 < n and (nxt.isalpha() or nxt == "_"):
                jsx_depth += 1
                i += 1
                continue
            if ch == "{":
                depth += 1
                i += 1
                continue
            if ch == "}":
                depth = max(0, depth - 1)
                i += 1
                continue
            if ch == "\n":
                i += 1
                continue
            i += 1
            continue
        if ch == "/" and nxt == "/":
            in_line_comment = True
            i += 2
            continue
        if ch == "/" and nxt == "*":
            in_block_comment = True
            i += 2
            continue
        if ch in ('"', "'"):
            in_str = ch
            i += 1
            continue
        if ch == "`":
            in_template += 1
            i += 1
            continue
        if (
            ch == "<"
            and i + 1 < n
            and (nxt.isalpha() or nxt == "_")
            and _looks_like_jsx_open(source, i)
        ):
            jsx_depth += 1
            i += 1
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth = max(0, depth - 1)
        if ch == "\n" and depth == 0:
            positions.add(i + 1)
        i += 1
    return positions


def _looks_like_jsx_open(source: str, i: int) -> bool:
    j = i - 1
    while j >= 0 and source[j] in " \t":
        j -= 1
    if j < 0:
        return True
    prev = source[j]
    return prev in "=(,?:&|{};>" or prev == "\n"


# Characters that can immediately precede a regex literal. Any "operator-ish"
# context (assignment, comparison, opening bracket, control flow boundary)
# lets `/` start a regex; alphanumerics, `)`, `]` make it division. We keep
# the empty string here for "start of source / right after whitespace at
# start of input."
_REGEX_STARTERS = frozenset(list("=(,;:?{[!&|^~<>+-*%") + ["\n", "", "\t", " ", "/"])


def _skip_lexical(source: str, i: int, prev_significant: str) -> int | None:
    """Skip one string / comment / regex / template literal token starting at ``i``.

    Returns the index just past the token, or ``None`` if ``source[i]`` is not
    the opener of any such token. Template literals consume their ``${...}``
    interpolations recursively so that braces inside template expressions
    cannot leak into the caller's brace depth.
    """

    n = len(source)
    if i >= n:
        return None
    ch = source[i]
    nxt = source[i + 1] if i + 1 < n else ""
    if ch == "/" and nxt == "/":
        j = i + 2
        while j < n and source[j] != "\n":
            j += 1
        return j
    if ch == "/" and nxt == "*":
        j = i + 2
        while j + 1 < n and not (source[j] == "*" and source[j + 1] == "/"):
            j += 1
        return min(j + 2, n)
    if ch in ('"', "'"):
        j = i + 1
        while j < n:
            c = source[j]
            if c == "\\" and j + 1 < n:
                j += 2
                continue
            if c == ch:
                return j + 1
            if c == "\n":
                return j + 1
            j += 1
        return n
    if ch == "`":
        j = i + 1
        while j < n:
            c = source[j]
            if c == "\\" and j + 1 < n:
                j += 2
                continue
            if c == "`":
                return j + 1
            if c == "$" and j + 1 < n and source[j + 1] == "{":
                expr_depth = 1
                k = j + 2
                expr_prev = "("
                while k < n and expr_depth > 0:
                    sub = _skip_lexical(source, k, expr_prev)
                    if sub is not None:
                        k = sub
                        continue
                    cc = source[k]
                    if cc == "{":
                        expr_depth += 1
                    elif cc == "}":
                        expr_depth -= 1
                        if expr_depth == 0:
                            k += 1
                            break
                    if not cc.isspace():
                        expr_prev = cc
                    k += 1
                j = k
                continue
            j += 1
        return n
    if ch == "/" and prev_significant in _REGEX_STARTERS:
        j = i + 1
        in_class = False
        while j < n:
            c = source[j]
            if c == "\\" and j + 1 < n:
                j += 2
                continue
            if c == "[":
                in_class = True
            elif c == "]":
                in_class = False
            elif c == "/" and not in_class:
                j += 1
                while j < n and source[j].isalpha():
                    j += 1
                return j
            elif c == "\n":
                return j
            j += 1
        return n
    return None


def _find_block_end(source: str, line_starts: list[int], from_line: int) -> int:
    start_pos = line_starts[from_line]
    first_brace = source.find("{", start_pos)
    if first_brace == -1:
        return from_line
    return _balance_braces(source, line_starts, first_brace)


def _find_block_end_from(source: str, line_starts: list[int], start_brace_pos: int) -> int:
    return _balance_braces(source, line_starts, start_brace_pos)


def _balance_braces(source: str, line_starts: list[int], brace_pos: int) -> int:
    """Walk forward from ``brace_pos``, returning the line of the matching ``}``.

    Strings, comments, regex literals, and template literals (with nested
    ``${...}`` expressions) are skipped via :func:`_skip_lexical` so they
    cannot perturb brace depth.
    """

    n = len(source)
    depth = 0
    i = brace_pos
    prev_significant = "("
    while i < n:
        sub = _skip_lexical(source, i, prev_significant)
        if sub is not None:
            i = sub
            continue
        ch = source[i]
        if ch == "{":
            depth += 1
            prev_significant = "{"
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return _offset_to_line(line_starts, i)
            prev_significant = "}"
        elif not ch.isspace():
            prev_significant = ch
        i += 1
    return len(line_starts) - 1


def _find_signature_end(lines: list[str], from_line: int, block_end: int) -> int:
    """Return the line index where the signature ends (line containing the opening ``{``)."""

    for idx in range(from_line, min(block_end + 1, len(lines))):
        if "{" in lines[idx]:
            return idx
    return from_line


def _find_arrow_end(source: str, line_starts: list[int], from_line: int) -> int:
    """Find end of an arrow expression: either the closing brace of its body block or the terminating ``;``/newline."""

    start_pos = line_starts[from_line]
    arrow_pos = source.find("=>", start_pos)
    if arrow_pos == -1:
        return _find_statement_end(source, line_starts, from_line)
    j = arrow_pos + 2
    n = len(source)
    while j < n and source[j] in " \t":
        j += 1
    if j < n and source[j] == "{":
        return _find_block_end_from(source, line_starts, j)
    return _find_statement_end(source, line_starts, from_line)


def _find_statement_end(source: str, line_starts: list[int], from_line: int) -> int:
    depth = 0
    i = line_starts[from_line]
    n = len(source)
    prev_significant = "\n"
    while i < n:
        sub = _skip_lexical(source, i, prev_significant)
        if sub is not None:
            i = sub
            continue
        ch = source[i]
        if ch == "{" or ch == "(" or ch == "[":
            depth += 1
            prev_significant = ch
        elif ch == "}" or ch == ")" or ch == "]":
            depth -= 1
            prev_significant = ch
        elif (ch == ";" or ch == "\n") and depth <= 0:
            return _offset_to_line(line_starts, i)
        elif not ch.isspace():
            prev_significant = ch
        i += 1
    return len(line_starts) - 1


def _offset_to_line(line_starts: list[int], offset: int) -> int:
    lo, hi = 0, len(line_starts) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if line_starts[mid] <= offset:
            lo = mid
        else:
            hi = mid - 1
    return lo


_METHOD_RE = re.compile(
    r"^\s*(?:static\s+|async\s+|get\s+|set\s+|public\s+|private\s+|protected\s+|\*\s*)*"
    r"([A-Za-z_$][\w$]*|\*\s*[A-Za-z_$][\w$]*)\s*\([^)]*\)\s*\{"
)
_CLASS_FIELD_RE = re.compile(
    r"^\s*(?:static\s+|public\s+|private\s+|protected\s+|readonly\s+)*"
    r"([A-Za-z_$#][\w$]*)\s*(?::\s*[^=;]+)?\s*=\s*[^=]"
)


def _emit_class_members(
    units: list[tuple[str, str, int, int]],
    lines: list[str],
    line_starts: list[int],
    source: str,
    start: int,
    end: int,
) -> None:
    i = start
    while i < end:
        line = lines[i] if i < len(lines) else ""
        stripped = line.strip()
        if not stripped or stripped.startswith("//"):
            i += 1
            continue
        if _METHOD_RE.match(line) and not _FUNCTION_NAMED_RE.match(line):
            block_end = _find_block_end(source, line_starts, i)
            block_end = min(block_end, end)
            sig_end_idx = _find_signature_end(lines, i, block_end)
            sig_text = "\n".join(lines[i : sig_end_idx + 1])
            units.append((UNIT_TYPE_FUNCTION_DEF, sig_text, i + 1, sig_end_idx + 1))
            _emit_body_statements(units, lines, line_starts, source, sig_end_idx + 1, block_end)
            i = block_end + 1
            continue
        if _CLASS_FIELD_RE.match(line):
            stmt_end = _find_statement_end(source, line_starts, i)
            stmt_end = min(stmt_end, end - 1)
            text = "\n".join(lines[i : stmt_end + 1])
            units.append((UNIT_TYPE_STATEMENT, text, i + 1, stmt_end + 1))
            i = stmt_end + 1
            continue
        i += 1


def _emit_body_statements(
    units: list[tuple[str, str, int, int]],
    lines: list[str],
    line_starts: list[int],
    source: str,
    start: int,
    block_end: int,
) -> None:
    """Emit ``js_statement`` units for body lines between ``start`` and just before the closing brace."""

    i = start
    inner_end = block_end - 1
    while i <= inner_end:
        line = lines[i] if i < len(lines) else ""
        stripped = line.strip()
        if not stripped or stripped.startswith("//") or stripped == "}":
            i += 1
            continue
        stmt_end = _find_statement_end(source, line_starts, i)
        if stmt_end > inner_end:
            stmt_end = inner_end
        text = "\n".join(lines[i : stmt_end + 1]).strip("\n")
        if text.strip():
            units.append((UNIT_TYPE_STATEMENT, text, i + 1, stmt_end + 1))
        i = stmt_end + 1
