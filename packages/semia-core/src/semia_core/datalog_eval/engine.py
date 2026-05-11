# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 berabuddies
"""Stratified bottom-up evaluator for the parsed Datalog subset."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

from .parser import Atom, Program, Rule, Term, parse_dl_file


class EvalError(RuntimeError):
    """Raised on stratification or runtime evaluation problems."""


@dataclass
class EvalResult:
    relations: dict[str, set[tuple[str, ...]]] = field(default_factory=dict)
    output_files: dict[str, Path] = field(default_factory=dict)
    strata: tuple[tuple[str, ...], ...] = ()


def run_evaluator(facts_path: Path | str, output_dir: Path | str) -> EvalResult:
    """Parse ``facts_path`` (with rules included) and write Soufflé-shaped CSVs."""

    program = parse_dl_file(facts_path)
    relations = evaluate(program)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    output_files: dict[str, Path] = {}
    for pred in sorted(program.outputs):
        path = out / f"{pred}.csv"
        rows = sorted(relations.get(pred, set()))
        with path.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write("\t".join(row))
                handle.write("\n")
        output_files[pred] = path
    strata = tuple(tuple(sorted(s)) for s in _strata_predicates(program))
    return EvalResult(relations=relations, output_files=output_files, strata=strata)


def evaluate(program: Program) -> dict[str, set[tuple[str, ...]]]:
    """Run stratified semi-naive evaluation; return all derived relations."""

    db: dict[str, set[tuple[str, ...]]] = {pred: set(rows) for pred, rows in program.facts.items()}
    for pred in program.decls:
        db.setdefault(pred, set())

    rules_by_head: dict[str, list[Rule]] = defaultdict(list)
    for rule in program.rules:
        rules_by_head[rule.head.relation].append(rule)

    for stratum in _strata_predicates(program):
        active_rules = [r for pred in stratum for r in rules_by_head.get(pred, [])]
        for pred in stratum:
            db.setdefault(pred, set())
        _evaluate_stratum(active_rules, db)

    return db


def _evaluate_stratum(rules: list[Rule], db: dict[str, set[tuple[str, ...]]]) -> None:
    if not rules:
        return
    while True:
        snapshot: dict[str, set[tuple[str, ...]]] = {
            rel: frozenset(rows) for rel, rows in db.items()
        }
        derived_any = False
        for rule in rules:
            target = db.setdefault(rule.head.relation, set())
            for binding in _match_body(rule.body, snapshot):
                tup = _ground_args(rule.head.args, binding)
                if tup not in target:
                    target.add(tup)
                    derived_any = True
        if not derived_any:
            return


def _match_body(
    body: tuple[Atom, ...],
    db: dict[str, set[tuple[str, ...]]],
) -> Iterator[dict[str, str]]:
    yield from _match(body, 0, {}, db)


def _match(
    body: tuple[Atom, ...],
    idx: int,
    binding: dict[str, str],
    db: dict[str, set[tuple[str, ...]]],
) -> Iterator[dict[str, str]]:
    if idx == len(body):
        yield binding
        return
    atom = body[idx]
    if atom.kind == "builtin":
        yield from _match_builtin(atom, idx, binding, body, db)
        return
    if atom.negated:
        if not _exists_match(atom.args, db.get(atom.relation, set()), binding):
            yield from _match(body, idx + 1, binding, db)
        return

    relation_rows = db.get(atom.relation)
    if not relation_rows:
        return
    for tup in relation_rows:
        new_binding = _try_bind(atom.args, tup, binding)
        if new_binding is None:
            continue
        yield from _match(body, idx + 1, new_binding, db)


def _exists_match(
    args: tuple[Term, ...],
    rows: set[tuple[str, ...]],
    binding: dict[str, str],
) -> bool:
    """Check whether any tuple in ``rows`` is consistent with ``args``.

    Anonymous and unbound variables match anything; bound variables must match
    their binding; constants must match exactly. Used for negative literals.
    """

    for tup in rows:
        if len(args) != len(tup):
            continue
        ok = True
        for term, value in zip(args, tup, strict=False):
            if term.is_var:
                if term.value.startswith("_anon_"):
                    continue
                existing = binding.get(term.value)
                if existing is None or existing == value:
                    continue
                ok = False
                break
            if term.value != value:
                ok = False
                break
        if ok:
            return True
    return False


def _try_bind(
    args: tuple[Term, ...],
    tup: tuple[str, ...],
    binding: dict[str, str],
) -> dict[str, str] | None:
    if len(args) != len(tup):
        return None
    new_binding = dict(binding)
    for term, value in zip(args, tup, strict=False):
        if term.is_var:
            existing = new_binding.get(term.value)
            if existing is None:
                new_binding[term.value] = value
            elif existing != value:
                return None
        else:
            if term.value != value:
                return None
    return new_binding


def _match_builtin(
    atom: Atom,
    idx: int,
    binding: dict[str, str],
    body: tuple[Atom, ...],
    db: dict[str, set[tuple[str, ...]]],
) -> Iterator[dict[str, str]]:
    if atom.relation == "contains":
        sub = _resolve(atom.args[0], binding)
        whole = _resolve(atom.args[1], binding)
        if sub is None or whole is None:
            raise EvalError("contains/2 requires both arguments to be bound")
        if sub in whole:
            yield from _match(body, idx + 1, binding, db)
        return
    if atom.relation in ("eq", "neq"):
        a_val = _resolve(atom.args[0], binding)
        b_val = _resolve(atom.args[1], binding)
        if atom.relation == "eq":
            if a_val is not None and b_val is not None:
                if a_val == b_val:
                    yield from _match(body, idx + 1, binding, db)
                return
            if a_val is None and b_val is not None:
                if not atom.args[0].is_var:
                    return
                new_binding = dict(binding)
                new_binding[atom.args[0].value] = b_val
                yield from _match(body, idx + 1, new_binding, db)
                return
            if b_val is None and a_val is not None:
                if not atom.args[1].is_var:
                    return
                new_binding = dict(binding)
                new_binding[atom.args[1].value] = a_val
                yield from _match(body, idx + 1, new_binding, db)
                return
            raise EvalError("equality between two unbound variables is not supported")
        if a_val is None or b_val is None:
            raise EvalError("disequality requires both arguments to be bound")
        if a_val != b_val:
            yield from _match(body, idx + 1, binding, db)
        return
    raise EvalError(f"unknown builtin: {atom.relation!r}")


def _resolve(term: Term, binding: dict[str, str]) -> str | None:
    if term.is_var:
        return binding.get(term.value)
    return term.value


def _ground_args(
    args: tuple[Term, ...],
    binding: dict[str, str],
    *,
    allow_unbound: bool = True,
) -> tuple[str, ...] | None:
    out: list[str] = []
    for term in args:
        if term.is_var:
            value = binding.get(term.value)
            if value is None:
                if allow_unbound:
                    raise EvalError(f"head variable {term.value!r} unbound after body match")
                return None
            out.append(value)
        else:
            out.append(term.value)
    return tuple(out)


def _strata_predicates(program: Program) -> list[list[str]]:
    """Topologically order predicates into strata; raise on negative cycles."""

    preds: set[str] = set()
    pos_edges: dict[str, set[str]] = defaultdict(set)
    neg_edges: dict[str, set[str]] = defaultdict(set)
    for rule in program.rules:
        head = rule.head.relation
        preds.add(head)
        for atom in rule.body:
            if atom.kind != "rel":
                continue
            preds.add(atom.relation)
            if atom.negated:
                neg_edges[head].add(atom.relation)
            else:
                pos_edges[head].add(atom.relation)
    for pred in program.decls:
        preds.add(pred)
    for pred in program.facts:
        preds.add(pred)

    all_edges: dict[str, set[str]] = defaultdict(set)
    for p in preds:
        all_edges[p] = pos_edges[p] | neg_edges[p]

    sccs = _tarjan_scc(preds, all_edges)
    pred_to_scc = {p: i for i, comp in enumerate(sccs) for p in comp}

    for head, deps in neg_edges.items():
        for q in deps:
            if pred_to_scc.get(head) == pred_to_scc.get(q):
                raise EvalError(f"non-stratifiable negation in cycle involving {head!r} and {q!r}")

    scc_deps: dict[int, set[int]] = defaultdict(set)
    for head, deps in all_edges.items():
        for q in deps:
            if pred_to_scc[head] != pred_to_scc[q]:
                scc_deps[pred_to_scc[head]].add(pred_to_scc[q])

    order = _toposort(range(len(sccs)), scc_deps)
    return [list(sccs[i]) for i in order]


def _tarjan_scc(nodes: set[str], edges: dict[str, set[str]]) -> list[list[str]]:
    # Iterative to avoid recursion limits on large predicate graphs.
    index_counter = 0
    stack: list[str] = []
    on_stack: set[str] = set()
    indices: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    result: list[list[str]] = []

    for start in sorted(nodes):
        if start in indices:
            continue
        indices[start] = index_counter
        lowlinks[start] = index_counter
        index_counter += 1
        stack.append(start)
        on_stack.add(start)
        work: list[tuple[str, Iterator[str]]] = [(start, iter(sorted(edges.get(start, ()))))]

        while work:
            node, it = work[-1]
            try:
                neighbor = next(it)
            except StopIteration:
                if lowlinks[node] == indices[node]:
                    comp: list[str] = []
                    while True:
                        top = stack.pop()
                        on_stack.discard(top)
                        comp.append(top)
                        if top == node:
                            break
                    result.append(comp)
                work.pop()
                if work:
                    parent = work[-1][0]
                    lowlinks[parent] = min(lowlinks[parent], lowlinks[node])
                continue
            if neighbor not in indices:
                indices[neighbor] = index_counter
                lowlinks[neighbor] = index_counter
                index_counter += 1
                stack.append(neighbor)
                on_stack.add(neighbor)
                work.append((neighbor, iter(sorted(edges.get(neighbor, ())))))
            elif neighbor in on_stack:
                lowlinks[node] = min(lowlinks[node], indices[neighbor])

    return result


def _toposort(nodes, deps: dict[int, set[int]]) -> list[int]:
    visited: set[int] = set()
    on_stack: set[int] = set()
    order: list[int] = []
    for start in sorted(nodes):
        if start in visited:
            continue
        work: list[tuple[int, Iterator[int]]] = [(start, iter(sorted(deps.get(start, ()))))]
        on_stack.add(start)
        while work:
            node, it = work[-1]
            try:
                child = next(it)
            except StopIteration:
                visited.add(node)
                on_stack.discard(node)
                order.append(node)
                work.pop()
                continue
            if child in visited:
                continue
            if child in on_stack:
                continue
            on_stack.add(child)
            work.append((child, iter(sorted(deps.get(child, ())))))
    return order


__all__ = ["EvalError", "EvalResult", "evaluate", "run_evaluator"]
