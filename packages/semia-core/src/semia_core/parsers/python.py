# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 berabuddies
"""Python source parser built on top of stdlib ``ast``.

Top-level imports are grouped into one ``py_import_block`` unit. Each
function/class produces a SIGNATURE-only unit (``py_def`` / ``py_class_def``)
covering just the ``def`` or ``class`` line(s); the body is broken into
``py_statement`` units (or ``py_method_def`` + statements for methods inside
a class). This keeps unit text non-overlapping so every source token belongs
to exactly one unit.

Line numbers are 1-indexed against the source file itself; callers that
inline the source into a larger document remap them via the source map.
"""

from __future__ import annotations

import ast

UNIT_TYPE_DEF = "py_def"
UNIT_TYPE_CLASS_DEF = "py_class_def"
UNIT_TYPE_METHOD_DEF = "py_method_def"
UNIT_TYPE_IMPORT_BLOCK = "py_import_block"
UNIT_TYPE_ASSIGNMENT = "py_assign"
UNIT_TYPE_STATEMENT = "py_statement"
UNIT_TYPE_DECORATOR = "py_decorator"


def parse_python_units(
    source: str,
    source_file: str = "",
) -> list[tuple[str, str, int, int]]:
    """Return ``(unit_type, text, line_start, line_end)`` tuples in document order.

    A ``SyntaxError`` returns an empty list so the caller can fall back to
    per-line ``fenced_code`` units. Line numbers are source-file relative.
    """

    del source_file
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    except ValueError:
        return []

    lines = source.splitlines()
    units: list[tuple[str, str, int, int]] = []

    body = list(tree.body)
    import_nodes = [n for n in body if isinstance(n, ast.Import | ast.ImportFrom)]
    import_node_ids = {id(n) for n in import_nodes}
    if import_nodes:
        start = import_nodes[0].lineno
        end = max(getattr(n, "end_lineno", n.lineno) or n.lineno for n in import_nodes)
        import_texts: list[str] = []
        for n in import_nodes:
            n_start = n.lineno
            n_end = getattr(n, "end_lineno", n.lineno) or n.lineno
            import_texts.append("\n".join(lines[n_start - 1 : n_end]))
        text = "\n".join(import_texts)
        units.append((UNIT_TYPE_IMPORT_BLOCK, text, start, end))

    for node in body:
        if id(node) in import_node_ids:
            continue
        start = node.lineno
        end = getattr(node, "end_lineno", node.lineno) or node.lineno
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            _emit_decorators(units, node, lines)
            _emit_def_with_body(units, node, lines, UNIT_TYPE_DEF)
        elif isinstance(node, ast.ClassDef):
            _emit_decorators(units, node, lines)
            _emit_class_with_methods(units, node, lines)
        elif isinstance(node, ast.Assign | ast.AnnAssign | ast.AugAssign):
            text = "\n".join(lines[start - 1 : end])
            units.append((UNIT_TYPE_ASSIGNMENT, text, start, end))
        else:
            text = "\n".join(lines[start - 1 : end])
            units.append((UNIT_TYPE_STATEMENT, text, start, end))

    return units


def _emit_decorators(
    units: list[tuple[str, str, int, int]],
    node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef,
    lines: list[str],
) -> None:
    for decorator in getattr(node, "decorator_list", ()) or ():
        d_start = decorator.lineno
        d_end = getattr(decorator, "end_lineno", decorator.lineno) or decorator.lineno
        text = "\n".join(lines[d_start - 1 : d_end])
        stripped = text.strip()
        if not stripped:
            continue
        if not stripped.lstrip().startswith("@"):
            stripped = "@" + stripped.lstrip()
        units.append((UNIT_TYPE_DECORATOR, stripped, d_start, d_end))


def _emit_def_with_body(
    units: list[tuple[str, str, int, int]],
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    lines: list[str],
    signature_kind: str,
) -> None:
    sig_start, sig_end = _signature_range(node)
    sig_text = "\n".join(lines[sig_start - 1 : sig_end])
    units.append((signature_kind, sig_text, sig_start, sig_end))
    if _body_inline_with_def(node):
        return
    for stmt in node.body:
        _emit_inner(units, stmt, lines, UNIT_TYPE_STATEMENT)


def _body_inline_with_def(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> bool:
    """Skip body emission when ``def f(): pass``-style single-line bodies share the def line."""
    if not node.body:
        return False
    first = node.body[0]
    return first.lineno <= node.lineno


def _emit_class_with_methods(
    units: list[tuple[str, str, int, int]],
    node: ast.ClassDef,
    lines: list[str],
) -> None:
    sig_start, sig_end = _signature_range(node)
    sig_text = "\n".join(lines[sig_start - 1 : sig_end])
    units.append((UNIT_TYPE_CLASS_DEF, sig_text, sig_start, sig_end))
    for stmt in node.body:
        if isinstance(stmt, ast.FunctionDef | ast.AsyncFunctionDef):
            _emit_decorators(units, stmt, lines)
            _emit_def_with_body(units, stmt, lines, UNIT_TYPE_METHOD_DEF)
        else:
            _emit_inner(units, stmt, lines, UNIT_TYPE_STATEMENT)


def _signature_range(
    node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef,
) -> tuple[int, int]:
    start = node.lineno
    end = getattr(node, "end_lineno", node.lineno) or node.lineno
    if node.body:
        first_body_line = node.body[0].lineno
        sig_end = max(start, first_body_line - 1)
        if sig_end < start:
            sig_end = start
        return start, sig_end
    return start, end


def _emit_inner(
    units: list[tuple[str, str, int, int]],
    stmt: ast.stmt,
    lines: list[str],
    kind: str,
) -> None:
    start = stmt.lineno
    end = getattr(stmt, "end_lineno", stmt.lineno) or stmt.lineno
    text = "\n".join(lines[start - 1 : end])
    if not text.strip():
        return
    units.append((kind, text, start, end))
