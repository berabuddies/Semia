# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 RiemaLabs
"""Parser for the Soufflé Datalog subset used by Semia SDL rules.

Supported surface:

- ``#include "<path>"`` directives, resolved relative to the including file.
- ``.decl pred(arg: Type, ...)`` declarations (types are not enforced).
- ``.output pred`` directives (mark a relation as a result to write).
- ``.type Alias <: symbol`` aliases (recorded but unused at runtime).
- Facts: ``pred("a", "b", 3).``
- Rules: ``head(args) :- body.`` with body literals separated by ``,``.
- Body literals: positive ``pred(args)``, negative ``!pred(args)``, equality
  ``x = y`` / disequality ``x != y``, and the builtin ``contains("sub", v)``.
- Disjunction in body: ``(a; b; c)`` — expanded into multiple rules at parse time.
- ``_`` wildcard variables (each occurrence is fresh).
- Line comments ``//`` and block comments ``/* */``.

Out-of-scope (would raise ``ParseError``): aggregators, components, ADT/record
types, functors, ``.input``/``.printsize``, choice domains, lattices, arithmetic.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Term:
    value: str
    is_var: bool

    @classmethod
    def variable(cls, name: str) -> Term:
        return cls(name, True)

    @classmethod
    def constant(cls, value: str) -> Term:
        return cls(value, False)


@dataclass(frozen=True)
class Atom:
    relation: str
    args: tuple[Term, ...]
    negated: bool = False
    kind: str = "rel"


@dataclass(frozen=True)
class Rule:
    head: Atom
    body: tuple[Atom, ...]


@dataclass
class Program:
    decls: dict[str, tuple[str, ...]] = field(default_factory=dict)
    outputs: set[str] = field(default_factory=set)
    facts: dict[str, set[tuple[str, ...]]] = field(default_factory=dict)
    rules: list[Rule] = field(default_factory=list)


class ParseError(ValueError):
    """Raised on malformed or unsupported Datalog input."""


_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_INT_RE = re.compile(r"-?\d+")


def parse_dl_file(path: Path | str) -> Program:
    """Parse a Soufflé-style program rooted at ``path``, expanding ``#include``s."""

    program = Program()
    anon_counter: list[int] = [0]
    _load(Path(path), program, set(), anon_counter)
    return program


def parse_dl_text(text: str, *, base_dir: Path | None = None) -> Program:
    """Parse a Datalog program from a string. ``base_dir`` resolves includes."""

    program = Program()
    anon_counter: list[int] = [0]
    _consume_text(text, base_dir or Path.cwd(), program, set(), anon_counter)
    return program


def _load(path: Path, program: Program, seen: set[Path], anon_counter: list[int]) -> None:
    resolved = path.resolve()
    if resolved in seen:
        return
    seen.add(resolved)
    text = resolved.read_text(encoding="utf-8")
    _consume_text(text, resolved.parent, program, seen, anon_counter)


def _consume_text(
    text: str,
    base_dir: Path,
    program: Program,
    seen: set[Path],
    anon_counter: list[int],
) -> None:
    text = _strip_comments(text)
    body_lines: list[str] = []
    for raw in text.split("\n"):
        line = raw.strip()
        if not line:
            body_lines.append("")
            continue
        if line.startswith("#include"):
            match = re.match(r'^#include\s+"([^"]+)"\s*$', line)
            if not match:
                raise ParseError(f"malformed include directive: {raw!r}")
            _load((base_dir / match.group(1)), program, seen, anon_counter)
            body_lines.append("")
            continue
        if line.startswith("."):
            _parse_directive(line, program)
            body_lines.append("")
            continue
        body_lines.append(raw)

    body = "\n".join(body_lines)
    for stmt in _split_statements(body):
        _parse_statement(stmt, program, anon_counter)


def _parse_directive(line: str, program: Program) -> None:
    if line.startswith(".decl "):
        _parse_decl(line[len(".decl ") :].strip(), program)
        return
    if line.startswith(".output "):
        program.outputs.add(line[len(".output ") :].strip())
        return
    if line.startswith(".type "):
        return
    if line.startswith((".input ", ".printsize ", ".comp ", ".init ", ".pragma ")):
        return
    raise ParseError(f"unsupported directive: {line!r}")


def _parse_decl(rest: str, program: Program) -> None:
    open_idx = rest.find("(")
    close_idx = rest.rfind(")")
    if open_idx <= 0 or close_idx < open_idx:
        raise ParseError(f"malformed .decl: {rest!r}")
    name = rest[:open_idx].strip()
    inside = rest[open_idx + 1 : close_idx].strip()
    arg_names: list[str] = []
    if inside:
        for chunk in _split_top_level(inside, ","):
            piece = chunk.strip()
            if ":" in piece:
                piece = piece.split(":", 1)[0].strip()
            arg_names.append(piece)
    program.decls[name] = tuple(arg_names)


def _strip_comments(text: str) -> str:
    out: list[str] = []
    i = 0
    n = len(text)
    in_quote = False
    while i < n:
        ch = text[i]
        if in_quote:
            if ch == "\\" and i + 1 < n:
                out.append(text[i : i + 2])
                i += 2
                continue
            if ch == '"':
                in_quote = False
            out.append(ch)
            i += 1
            continue
        if ch == '"':
            in_quote = True
            out.append(ch)
            i += 1
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "/":
            while i < n and text[i] != "\n":
                i += 1
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "*":
            i += 2
            while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                if text[i] == "\n":
                    out.append("\n")
                i += 1
            i = min(i + 2, n)
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _split_statements(text: str) -> list[str]:
    statements: list[str] = []
    cur: list[str] = []
    paren = 0
    in_quote = False
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if in_quote:
            if ch == "\\" and i + 1 < n:
                cur.append(text[i : i + 2])
                i += 2
                continue
            if ch == '"':
                in_quote = False
            cur.append(ch)
            i += 1
            continue
        if ch == '"':
            in_quote = True
            cur.append(ch)
            i += 1
            continue
        if ch == "(":
            paren += 1
            cur.append(ch)
            i += 1
            continue
        if ch == ")":
            paren -= 1
            cur.append(ch)
            i += 1
            continue
        if ch == "." and paren == 0:
            stmt = "".join(cur).strip()
            if stmt:
                statements.append(stmt)
            cur = []
            i += 1
            continue
        cur.append(ch)
        i += 1
    leftover = "".join(cur).strip()
    if leftover:
        raise ParseError(f"unterminated statement: {leftover!r}")
    return statements


def _fresh_anon(anon_counter: list[int]) -> str:
    anon_counter[0] += 1
    return f"_anon_{anon_counter[0]}"


def _parse_statement(stmt: str, program: Program, anon_counter: list[int]) -> None:
    arrow = _find_arrow(stmt)
    if arrow < 0:
        atom = _parse_atom(stmt, anon_counter)
        if any(arg.is_var for arg in atom.args):
            raise ParseError(f"fact has unbound variables: {stmt!r}")
        program.facts.setdefault(atom.relation, set()).add(tuple(arg.value for arg in atom.args))
        return
    head_text = stmt[:arrow].strip()
    body_text = stmt[arrow + 2 :].strip()
    head = _parse_atom(head_text, anon_counter)
    if head.negated or head.kind != "rel":
        raise ParseError(f"rule head must be a positive relation: {head_text!r}")
    for body_tuple in _expand_disjunctions(body_text, anon_counter):
        program.rules.append(Rule(head=head, body=body_tuple))


def _find_arrow(stmt: str) -> int:
    in_quote = False
    paren = 0
    i = 0
    n = len(stmt)
    while i < n - 1:
        ch = stmt[i]
        if in_quote:
            if ch == "\\":
                i += 2
                continue
            if ch == '"':
                in_quote = False
            i += 1
            continue
        if ch == '"':
            in_quote = True
            i += 1
            continue
        if ch == "(":
            paren += 1
            i += 1
            continue
        if ch == ")":
            paren -= 1
            i += 1
            continue
        if paren == 0 and ch == ":" and stmt[i + 1] == "-":
            return i
        i += 1
    return -1


def _expand_disjunctions(body_text: str, anon_counter: list[int]) -> list[tuple[Atom, ...]]:
    """Return a list of body conjunctions, one per disjunctive choice."""

    chunks = _split_top_level(body_text, ",")
    options_per_chunk: list[list[Atom]] = []
    for chunk in chunks:
        piece = chunk.strip()
        if piece.startswith("(") and piece.endswith(")") and _is_disjunction(piece):
            inner = piece[1:-1]
            disjuncts = [
                _parse_body_atom(p.strip(), anon_counter) for p in _split_top_level(inner, ";")
            ]
            options_per_chunk.append(disjuncts)
        else:
            options_per_chunk.append([_parse_body_atom(piece, anon_counter)])

    result: list[tuple[Atom, ...]] = [()]
    for options in options_per_chunk:
        new_result: list[tuple[Atom, ...]] = []
        for prefix in result:
            for opt in options:
                new_result.append(prefix + (opt,))
        result = new_result
    return result


def _is_disjunction(piece: str) -> bool:
    inner = piece[1:-1]
    parts = _split_top_level(inner, ";")
    return len(parts) > 1


def _split_top_level(text: str, sep: str) -> list[str]:
    parts: list[str] = []
    cur: list[str] = []
    paren = 0
    in_quote = False
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if in_quote:
            if ch == "\\" and i + 1 < n:
                cur.append(text[i : i + 2])
                i += 2
                continue
            if ch == '"':
                in_quote = False
            cur.append(ch)
            i += 1
            continue
        if ch == '"':
            in_quote = True
            cur.append(ch)
            i += 1
            continue
        if ch == "(":
            paren += 1
            cur.append(ch)
            i += 1
            continue
        if ch == ")":
            paren -= 1
            cur.append(ch)
            i += 1
            continue
        if ch == sep and paren == 0:
            parts.append("".join(cur))
            cur = []
            i += 1
            continue
        cur.append(ch)
        i += 1
    parts.append("".join(cur))
    return parts


def _parse_body_atom(text: str, anon_counter: list[int]) -> Atom:
    piece = text.strip()
    if not piece:
        raise ParseError("empty body literal")

    negated = False
    if piece.startswith("!"):
        negated = True
        piece = piece[1:].strip()

    if "(" in piece and piece.endswith(")"):
        atom = _parse_atom(piece, anon_counter)
        if atom.relation == "contains":
            if negated:
                raise ParseError("negation not supported on builtins")
            return Atom(
                relation="contains",
                args=atom.args,
                negated=False,
                kind="builtin",
            )
        return Atom(relation=atom.relation, args=atom.args, negated=negated, kind="rel")

    if "!=" in piece:
        return _parse_eq_constraint(piece, "!=", "neq", negated, anon_counter)
    if "=" in piece:
        return _parse_eq_constraint(piece, "=", "eq", negated, anon_counter)

    raise ParseError(f"unrecognized body literal: {text!r}")


def _parse_eq_constraint(
    piece: str, op: str, kind: str, negated: bool, anon_counter: list[int]
) -> Atom:
    if negated:
        raise ParseError(
            f"explicit negation on {op} not supported; use {'=' if op == '!=' else '!='}"
        )
    left, right = piece.split(op, 1)
    left_term = _parse_term(left.strip(), anon_counter)
    right_term = _parse_term(right.strip(), anon_counter)
    return Atom(relation=kind, args=(left_term, right_term), negated=False, kind="builtin")


def _parse_atom(text: str, anon_counter: list[int]) -> Atom:
    piece = text.strip()
    negated = False
    if piece.startswith("!"):
        negated = True
        piece = piece[1:].strip()
    open_idx = piece.find("(")
    close_idx = piece.rfind(")")
    if open_idx <= 0 or close_idx != len(piece) - 1:
        raise ParseError(f"malformed atom: {text!r}")
    relation = piece[:open_idx].strip()
    if not _IDENT_RE.fullmatch(relation):
        raise ParseError(f"invalid relation name {relation!r}")
    inside = piece[open_idx + 1 : close_idx]
    args = tuple(_parse_term(part.strip(), anon_counter) for part in _split_top_level(inside, ","))
    return Atom(relation=relation, args=args, negated=negated, kind="rel")


def _parse_term(text: str, anon_counter: list[int]) -> Term:
    piece = text.strip()
    if not piece:
        raise ParseError("empty term")
    if piece == "_":
        return Term.variable(_fresh_anon(anon_counter))
    if piece.startswith('"') and piece.endswith('"') and len(piece) >= 2:
        return Term.constant(_unescape_string(piece[1:-1]))
    if _INT_RE.fullmatch(piece):
        return Term.constant(piece)
    if _IDENT_RE.fullmatch(piece):
        return Term.variable(piece)
    raise ParseError(f"unrecognized term: {text!r}")


def _unescape_string(value: str) -> str:
    out: list[str] = []
    i = 0
    n = len(value)
    while i < n:
        ch = value[i]
        if ch == "\\" and i + 1 < n:
            nxt = value[i + 1]
            out.append({"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\"}.get(nxt, nxt))
            i += 2
            continue
        out.append(ch)
        i += 1
    return "".join(out)
