# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 RiemaLabs
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "packages/semia-core/src"))

from semia_core.artifacts import _quote_arg
from semia_core.checker import CheckOptions, check_program, compute_ssa_input_availability
from semia_core.evidence import _score, align_evidence_text
from semia_core.facts import parse_facts
from semia_core.prepare import build_prepare_bundle


VALID_SOURCE = """
#include "skill_dl_static_analysis.dl"
skill("demo").
skill_evidence_text("demo", "Demo Skill").
skill_doc_claim("demo", "no_network").
skill_doc_claim_evidence_text("demo", "no_network", "Send no network traffic").
action("act_read", "demo").
action_evidence_text("act_read", "Read a local file").
action_trigger("act_read", "llm").
action_trigger_evidence_text("act_read", "llm", "Read a local file").
action_gate("act_read", "confirmation_prompt").
action_gate_evidence_text("act_read", "confirmation_prompt", "Read a local file").
action_param("act_read", "path", "v_path").
action_param_evidence_text("act_read", "path", "v_path", "local file path").
value("v_path", "act_read", "param").
value_evidence_text("v_path", "act_read", "local file path").
value("v_body", "act_read", "local").
value_evidence_text("v_body", "act_read", "Read a local file").
call("c_read", "act_read").
call_evidence_text("c_read", "Read a local file").
call_effect("c_read", "fs_read").
call_effect_evidence_text("c_read", "fs_read", "Read a local file").
call_input("c_read", "v_path").
call_input_evidence_text("c_read", "v_path", "local file path").
call_output("c_read", "v_body").
call_output_evidence_text("c_read", "v_body", "Read a local file").
"""


class FactCheckerEvidenceTests(unittest.TestCase):
    def test_parse_facts_splits_core_and_evidence(self) -> None:
        program = parse_facts(VALID_SOURCE + 'call_evidence("c_read", "su_1"). // ok\n')

        self.assertEqual(len(program.includes), 1)
        self.assertTrue(any(f.relation == "call" for f in program.core_facts))
        self.assertTrue(any(f.relation == "call_evidence_text" for f in program.evidence_text_facts))
        self.assertTrue(any(f.relation == "call_evidence" for f in program.evidence_facts))

    def test_checker_accepts_valid_v2_program(self) -> None:
        result = check_program(VALID_SOURCE, options=CheckOptions(require_include=True))

        self.assertTrue(result.program_valid, result.issues)
        self.assertGreater(result.evidence_support_coverage, 0.9)

    def test_checker_reports_core_schema_errors(self) -> None:
        bad = """
skill("demo").
action("act", "missing").
call("c", "act").
call_effect("c", "teleport").
"""
        result = check_program(bad)

        self.assertFalse(result.program_valid)
        codes = {issue.code for issue in result.errors}
        self.assertIn("SDL010", codes)
        self.assertIn("SDL020", codes)

    def test_align_evidence_text_emits_normalized_handles(self) -> None:
        with tempfile_skill("# Demo Skill\n\n- Read a local file.\n- Send no network traffic.\n") as path:
            prepared = build_prepare_bundle(path)
        result = align_evidence_text(VALID_SOURCE, prepared, threshold=0.2)

        self.assertGreater(result.evidence_match_rate, 0.8)
        self.assertTrue(any(f.relation == "call_evidence" for f in result.normalized_facts))
        self.assertTrue(all(f.args[-1].startswith("su_") for f in result.normalized_facts))

    def test_score_short_substring_falls_back_to_jaccard(self) -> None:
        score = _score("a", "abc def")
        self.assertLess(score, 0.75)
        self.assertGreaterEqual(score, 0.0)

    def test_score_longer_substring_keeps_bonus(self) -> None:
        score = _score("hello world", "hello world greetings")
        self.assertGreaterEqual(score, 0.75)

    def test_quote_arg_handles_negative_integers(self) -> None:
        self.assertEqual(_quote_arg("-42"), "-42")
        self.assertEqual(_quote_arg("42"), "42")

    def test_parse_facts_separates_includes_from_directives(self) -> None:
        program = parse_facts('#define FOO bar\n#include "x.dl"\nskill("a").\n')
        self.assertEqual(program.includes, ('#include "x.dl"',))
        self.assertEqual(program.preprocessor_directives, ("#define FOO bar",))

    def test_mechanical_facts_skip_evd012(self) -> None:
        source = """
skill("demo").
skill_evidence_text("demo", "Demo Skill").
action("act", "demo").
action_evidence_text("act", "Read a thing").
call("c1", "act").
call_evidence_text("c1", "Read step 1").
call("c2", "act").
call_evidence_text("c2", "Read step 2").
call_effect("c1", "fs_read").
call_unconditional("c1", "c2").
"""
        result = check_program(source, options=CheckOptions(require_evidence=True))
        codes = {(issue.code, issue.message) for issue in result.warnings}
        self.assertFalse(
            any(code == "EVD012" and "call_unconditional" in msg for code, msg in codes),
            f"mechanical fact emitted EVD012: {codes}",
        )
        self.assertTrue(
            any(code == "EVD012" and "call_effect" in msg for code, msg in codes),
            f"expected EVD012 for missing call_effect evidence: {codes}",
        )

    def test_ssa_input_availability_all_sourced(self) -> None:
        program = parse_facts(
            """
skill("demo").
action("act", "demo").
action_param("act", "path", "v_path").
value("v_path", "act", "param").
value("v_body", "act", "local").
call("c1", "act").
call_input("c1", "v_path").
call_input("c1", "v_body").
"""
        )
        self.assertEqual(compute_ssa_input_availability(program), 1.0)

    def test_ssa_input_availability_hallucinated(self) -> None:
        program = parse_facts(
            """
skill("demo").
action("act", "demo").
call("c_post", "act").
call_input("c_post", "v_hallucinated").
"""
        )
        self.assertLess(compute_ssa_input_availability(program), 1.0)

    def test_ssa_input_availability_bfs_finds_earlier_output(self) -> None:
        program = parse_facts(
            """
skill("demo").
action("act", "demo").
call("c_prev", "act").
call_output("c_prev", "v_x").
call("c_post", "act").
call_unconditional("c_prev", "c_post").
call_input("c_post", "v_x").
"""
        )
        self.assertEqual(compute_ssa_input_availability(program), 1.0)


class tempfile_skill:
    def __init__(self, text: str) -> None:
        self.text = text
        self._td = None
        self.path = None

    def __enter__(self) -> Path:
        import tempfile

        self._td = tempfile.TemporaryDirectory()
        self.path = Path(self._td.name)
        (self.path / "SKILL.md").write_text(self.text, encoding="utf-8")
        return self.path

    def __exit__(self, exc_type, exc, tb) -> None:
        assert self._td is not None
        self._td.cleanup()


if __name__ == "__main__":
    unittest.main()
