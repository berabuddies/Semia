from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "packages/semia-core/src"))

from semia_core.checker import CheckOptions, check_program
from semia_core.evidence import align_evidence_text
from semia_core.facts import parse_facts
from semia_core.stage1 import build_stage1_bundle


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
            stage1 = build_stage1_bundle(path)
        result = align_evidence_text(VALID_SOURCE, stage1, threshold=0.2)

        self.assertGreater(result.evidence_match_rate, 0.8)
        self.assertTrue(any(f.relation == "call_evidence" for f in result.normalized_facts))
        self.assertTrue(all(f.args[-1].startswith("su_") for f in result.normalized_facts))


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
