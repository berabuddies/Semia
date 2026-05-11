# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 RiemaLabs
"""Tests for the built-in pure-Python Datalog evaluator."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "packages/semia-core/src"))

from semia_core.datalog_eval import ParseError, parse_dl_file, run_evaluator
from semia_core.datalog_eval.engine import EvalError, evaluate
from semia_core.datalog_eval.parser import Program


REPO_ROOT = Path(__file__).resolve().parents[2]
RULES_DIR = REPO_ROOT / "packages/semia-core/src/semia_core/rules/sdl"

# Two scenarios with hand-checked expected findings, used both for the
# built-in evaluator and (when Soufflé is present) cross-validation.
SCENARIOS: tuple[tuple[str, str], ...] = (
    (
        "minimal_proc_exec_untrusted",
        """
        skill("demo").
        action("act", "demo").
        value("v_payload", "act", "untrusted").
        call("c_exec", "act").
        call_effect("c_exec", "proc_exec").
        call_input("c_exec", "v_payload").
        call_region_untrusted("c_exec").
        """,
    ),
    (
        "rich_recursion_contains_disjunction",
        """
        skill("sk").
        skill_doc_claim("sk", "read_only").
        action("a1", "sk").
        action_param("a1", "api_key", "v_param").
        action_trigger("a1", "on_install").

        value("v_param", "a1", "param").
        value("v_inter", "a1", "untrusted").
        value("v_target", "a1", "untrusted").
        value("v_secret_local", "a1", "secret").

        call("c_fetch", "a1").
        call_effect("c_fetch", "net_read").
        call_region_untrusted("c_fetch").
        call_output("c_fetch", "v_inter").

        call("c_run", "a1").
        call_effect("c_run", "proc_exec").
        call_input("c_run", "v_target").
        call_unconditional("c_fetch", "c_run").
        call_code("c_run", "obfuscated").

        call("c_egress", "a1").
        call_effect("c_egress", "net_write").
        call_region_untrusted("c_egress").
        call_input("c_egress", "v_secret_local").

        call("c_creds", "a1").
        call_effect("c_creds", "fs_read").
        call_region_secret("c_creds").
        """,
    ),
)


def _stage_run_dir(tmp_root: Path, scenario_facts: str) -> Path:
    rules_dst = tmp_root / "rules" / "sdl"
    rules_dst.mkdir(parents=True)
    for name in ("skill_description_lang.dl", "skill_dl_static_analysis.dl"):
        (rules_dst / name).write_text(
            (RULES_DIR / name).read_text(encoding="utf-8"), encoding="utf-8"
        )
    facts_path = tmp_root / "detection_input.dl"
    header = '#include "rules/sdl/skill_dl_static_analysis.dl"\n\n'
    facts_path.write_text(header + scenario_facts.strip() + "\n", encoding="utf-8")
    return facts_path


def _read_relation_csvs(out_dir: Path) -> dict[str, list[tuple[str, ...]]]:
    relations: dict[str, list[tuple[str, ...]]] = {}
    for csv_path in sorted(out_dir.glob("*.csv")):
        text = csv_path.read_text(encoding="utf-8").strip()
        rows = [tuple(line.split("\t")) for line in text.split("\n")] if text else []
        relations[csv_path.stem] = sorted(rows)
    return relations


class ParserTests(unittest.TestCase):
    def test_rejects_unsupported_directive(self) -> None:
        with self.assertRaises(ParseError):
            parse_dl_file(self._write_temp(".aggregate foo\n"))

    def test_parses_decl_output_facts_and_rules(self) -> None:
        path = self._write_temp(
            """
            .decl edge(a: symbol, b: symbol)
            .decl path(a: symbol, b: symbol)
            .output path

            edge("x", "y").
            edge("y", "z").
            path(a, b) :- edge(a, b).
            path(a, c) :- edge(a, b), path(b, c).
            """
        )
        program = parse_dl_file(path)
        self.assertIn("edge", program.decls)
        self.assertIn("path", program.outputs)
        self.assertEqual(program.facts["edge"], {("x", "y"), ("y", "z")})
        self.assertEqual(len(program.rules), 2)

    def test_disjunction_expands_to_multiple_rules(self) -> None:
        path = self._write_temp(
            """
            .decl r(x: symbol)
            .output r
            r(x) :- s(x), (t(x); u(x)).
            """
        )
        program = parse_dl_file(path)
        self.assertEqual(len(program.rules), 2)

    def test_anonymous_variable_names_reset_per_parse(self) -> None:
        path = self._write_temp(
            """
            .decl edge(a: symbol, b: symbol)
            .decl root(a: symbol)
            .output root
            edge("a", "b").
            root(x) :- edge(x, _), !edge(_, x).
            """
        )

        def _anon_names(program: Program) -> list[str]:
            names: list[str] = []
            for rule in program.rules:
                for atom in rule.body:
                    for term in atom.args:
                        if term.is_var and term.value.startswith("_anon_"):
                            names.append(term.value)
            return names

        first = parse_dl_file(path)
        second = parse_dl_file(path)
        first_names = _anon_names(first)
        second_names = _anon_names(second)
        self.assertEqual(first_names, second_names)
        self.assertTrue(first_names, "expected anon variables to be present")
        self.assertEqual(min(first_names), "_anon_1")

    def _write_temp(self, body: str) -> Path:
        tmp = Path(tempfile.mkdtemp())
        path = tmp / "p.dl"
        path.write_text(body, encoding="utf-8")
        self.addCleanup(shutil.rmtree, tmp)
        return path


class StratificationTests(unittest.TestCase):
    def test_negative_cycle_rejected(self) -> None:
        path = Path(tempfile.mkdtemp()) / "p.dl"
        self.addCleanup(shutil.rmtree, path.parent)
        path.write_text(
            """
            .decl a(x: symbol)
            .decl b(x: symbol)
            a(x) :- !b(x), seed(x).
            b(x) :- !a(x), seed(x).
            seed("z").
            """,
            encoding="utf-8",
        )
        program = parse_dl_file(path)
        with self.assertRaises(EvalError):
            evaluate(program)

    def test_deep_predicate_chain_does_not_recurse(self) -> None:
        chain_len = 2000
        src = "\n".join(
            f'.decl p_{i}(x: symbol)\np_{i}("x") :- p_{i + 1}("x").'
            for i in range(chain_len)
        ) + f'\n.decl p_{chain_len}(x: symbol)\n.output p_0\np_{chain_len}("x").\n'
        path = Path(tempfile.mkdtemp()) / "chain.dl"
        self.addCleanup(shutil.rmtree, path.parent)
        path.write_text(src, encoding="utf-8")

        original_limit = sys.getrecursionlimit()
        sys.setrecursionlimit(900)
        self.addCleanup(sys.setrecursionlimit, original_limit)

        program = parse_dl_file(path)
        relations = evaluate(program)
        self.assertEqual(relations["p_0"], {("x",)})
        self.assertEqual(relations[f"p_{chain_len}"], {("x",)})


class EvaluatorTests(unittest.TestCase):
    def test_transitive_closure(self) -> None:
        path = Path(tempfile.mkdtemp()) / "p.dl"
        self.addCleanup(shutil.rmtree, path.parent)
        path.write_text(
            """
            .decl edge(a: symbol, b: symbol)
            .decl path(a: symbol, b: symbol)
            .output path
            edge("x", "y").
            edge("y", "z").
            edge("z", "w").
            path(a, b) :- edge(a, b).
            path(a, c) :- edge(a, b), path(b, c).
            """,
            encoding="utf-8",
        )
        with tempfile.TemporaryDirectory() as out:
            run_evaluator(path, out)
            csv_text = (Path(out) / "path.csv").read_text(encoding="utf-8").strip()
            rows = sorted(csv_text.split("\n"))
        self.assertEqual(
            rows,
            sorted(["x\ty", "y\tz", "z\tw", "x\tz", "y\tw", "x\tw"]),
        )

    def test_anonymous_wildcard_in_negation(self) -> None:
        path = Path(tempfile.mkdtemp()) / "p.dl"
        self.addCleanup(shutil.rmtree, path.parent)
        path.write_text(
            """
            .decl edge(a: symbol, b: symbol)
            .decl root(a: symbol)
            .output root
            edge("a", "b").
            edge("b", "c").
            root(x) :- edge(x, _), !edge(_, x).
            """,
            encoding="utf-8",
        )
        with tempfile.TemporaryDirectory() as out:
            run_evaluator(path, out)
            text = (Path(out) / "root.csv").read_text(encoding="utf-8").strip()
        self.assertEqual(text, "a")

    def test_contains_builtin(self) -> None:
        path = Path(tempfile.mkdtemp()) / "p.dl"
        self.addCleanup(shutil.rmtree, path.parent)
        path.write_text(
            """
            .decl param(name: symbol)
            .decl secret_param(name: symbol)
            .output secret_param
            param("user_token").
            param("display_name").
            secret_param(n) :- param(n), (contains("token", n); contains("password", n)).
            """,
            encoding="utf-8",
        )
        with tempfile.TemporaryDirectory() as out:
            run_evaluator(path, out)
            text = (Path(out) / "secret_param.csv").read_text(encoding="utf-8").strip()
        self.assertEqual(text, "user_token")


class SDLRulesEndToEndTests(unittest.TestCase):
    def test_minimal_scenario_produces_expected_labels(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            facts = _stage_run_dir(Path(td), SCENARIOS[0][1])
            out = Path(td) / "out"
            run_evaluator(facts, out)
            relations = _read_relation_csvs(out)
        self.assertEqual(
            relations["label_dangerous_execution_primitives"],
            [("demo", "act", "c_exec")],
        )
        self.assertEqual(
            relations["label_ungated_irreversible_operation"],
            [("demo", "act", "c_exec")],
        )
        self.assertEqual(
            relations["label_unsanitized_context_ingestion"],
            [("demo", "act", "c_exec", "v_payload")],
        )

    def test_rich_scenario_produces_expected_labels(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            facts = _stage_run_dir(Path(td), SCENARIOS[1][1])
            out = Path(td) / "out"
            run_evaluator(facts, out)
            relations = _read_relation_csvs(out)
        self.assertEqual(
            relations["label_behavior_claim_contradiction"],
            [("sk", "a1", "c_egress", "read_only", "net_write")],
        )
        self.assertEqual(
            relations["label_obfuscation"],
            [("sk", "a1", "c_run", "obfuscated")],
        )
        self.assertEqual(len(relations["label_implicit_egress_channels"]), 2)
        self.assertEqual(len(relations["label_unsanitized_context_ingestion"]), 3)
        self.assertEqual(len(relations["label_unverifiable_dependency_source"]), 1)

    @unittest.skipUnless(shutil.which("souffle"), "souffle not installed")
    def test_builtin_matches_souffle_on_all_scenarios(self) -> None:
        for name, body in SCENARIOS:
            with self.subTest(scenario=name):
                with tempfile.TemporaryDirectory() as td_a, tempfile.TemporaryDirectory() as td_b:
                    fa = _stage_run_dir(Path(td_a), body)
                    fb = _stage_run_dir(Path(td_b), body)
                    out_a = Path(td_a) / "out"
                    out_b = Path(td_b) / "out"
                    out_b.mkdir()
                    run_evaluator(fa, out_a)
                    subprocess.run(
                        [shutil.which("souffle"), str(fb), "-D", str(out_b)],
                        check=True,
                        capture_output=True,
                    )
                    builtin = _read_relation_csvs(out_a)
                    souffle = _read_relation_csvs(out_b)
                self.assertEqual(
                    set(builtin.keys()),
                    set(souffle.keys()),
                    msg=f"output relation set differs for scenario {name}",
                )
                for key in builtin:
                    self.assertEqual(
                        builtin[key],
                        souffle[key],
                        msg=f"relation {key} differs for scenario {name}",
                    )


if __name__ == "__main__":
    unittest.main()
