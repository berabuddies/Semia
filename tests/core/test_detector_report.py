from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "packages/semia-core/src"))

from semia_core.artifacts import AuditReport
from semia_core.checker import check_program
from semia_core.detector import run_detector
from semia_core.pipeline import check, detect, prepare
from semia_core.report import render_markdown_report


class DetectorReportTests(unittest.TestCase):
    def test_detector_reports_unavailable_without_souffle(self) -> None:
        previous = os.environ.get("SEMIA_SOUFFLE_BIN")
        os.environ["SEMIA_SOUFFLE_BIN"] = "/definitely/not/souffle"
        try:
            with tempfile.TemporaryDirectory() as td:
                facts = Path(td) / "facts.dl"
                facts.write_text('skill("demo").\n', encoding="utf-8")
                result = run_detector(facts, Path(td) / "out")
        finally:
            if previous is None:
                os.environ.pop("SEMIA_SOUFFLE_BIN", None)
            else:
                os.environ["SEMIA_SOUFFLE_BIN"] = previous

        self.assertEqual(result.status, "unavailable")

    def test_render_markdown_report(self) -> None:
        check = check_program('skill("demo").\n')
        markdown = render_markdown_report(AuditReport(title="Semia Audit", source_id="demo", check_result=check))

        self.assertIn("# Semia Audit", markdown)
        self.assertIn("Structural Check", markdown)

    @unittest.skipUnless(shutil.which("souffle"), "souffle not installed")
    def test_detector_rules_compile_and_emit_findings(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            skill_dir = root / "skill"
            run_dir = root / "run"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                "# Demo\n\n- Run a command from downloaded content.\n",
                encoding="utf-8",
            )
            prepare(skill_dir, out_dir=run_dir)
            (run_dir / "synthesized_facts.dl").write_text(
                "\n".join(
                    [
                        'skill("demo").',
                        'skill_evidence_text("demo", "Demo").',
                        'action("act", "demo").',
                        'action_evidence_text("act", "Run a command from downloaded content").',
                        'value("v_payload", "act", "untrusted").',
                        'value_evidence_text("v_payload", "act", "downloaded content").',
                        'call("c_exec", "act").',
                        'call_evidence_text("c_exec", "Run a command").',
                        'call_effect("c_exec", "proc_exec").',
                        'call_effect_evidence_text("c_exec", "proc_exec", "Run a command").',
                        'call_input("c_exec", "v_payload").',
                        'call_input_evidence_text("c_exec", "v_payload", "downloaded content").',
                        'call_region_untrusted("c_exec").',
                        'call_region_untrusted_evidence_text("c_exec", "downloaded content").',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            checked = check(run_dir)
            result = detect(run_dir)

        self.assertEqual(checked["errors"], 0)
        self.assertEqual(result["status"], "ok")
        self.assertGreaterEqual(result["findings"], 1)


if __name__ == "__main__":
    unittest.main()
