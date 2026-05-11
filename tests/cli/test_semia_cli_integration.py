# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 RiemaLabs
from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "packages" / "semia-core" / "src"))
sys.path.insert(0, str(REPO_ROOT / "packages" / "semia-cli" / "src"))

from semia_cli.main import main  # noqa: E402


VALID_FACTS = """\
skill("demo-skill").
skill_evidence_text("demo-skill", "Demo Skill").
skill_doc_claim("demo-skill", "no_network").
skill_doc_claim_evidence_text("demo-skill", "no_network", "Send no network traffic").
action("act_read", "demo-skill").
action_evidence_text("act_read", "Read a local file path").
call("call_read", "act_read").
call_evidence_text("call_read", "Read a local file path").
call_effect("call_read", "fs_read").
call_effect_evidence_text("call_read", "fs_read", "Read a local file path").
value("v_path", "act_read", "local").
value_evidence_text("v_path", "act_read", "Read a local file path").
call_input("call_read", "v_path").
call_input_evidence_text("call_read", "v_path", "Read a local file path").
"""


class SemiaCliIntegrationTests(unittest.TestCase):
    def test_scan_offline_baseline_runs_end_to_end(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            skill = base / "demo-skill"
            skill.mkdir()
            (skill / "SKILL.md").write_text(
                "# Demo Skill\n\n- Send no network traffic.\n- Read a local file path.\n",
                encoding="utf-8",
            )
            run_dir = base / "run"

            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = main(["scan", str(skill), "--out", str(run_dir), "--offline-baseline"])

            self.assertEqual(code, 0, stderr.getvalue())
            self.assertTrue((run_dir / "prepared_skill.md").exists())
            self.assertTrue((run_dir / "synthesized_facts.dl").exists())
            self.assertTrue((run_dir / "synthesis_check.json").exists())
            self.assertTrue((run_dir / "detection_result.json").exists())
            self.assertTrue((run_dir / "report.md").exists())
            self.assertIn("conservative offline baseline map", stdout.getvalue())

    def test_scan_with_facts_uses_real_core(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            skill = base / "demo-skill"
            skill.mkdir()
            (skill / "SKILL.md").write_text(
                "# Demo Skill\n\n- Send no network traffic.\n- Read a local file path.\n",
                encoding="utf-8",
            )
            facts = base / "facts.dl"
            facts.write_text(VALID_FACTS, encoding="utf-8")
            run_dir = base / "run"

            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = main(["scan", str(skill), "--out", str(run_dir), "--facts", str(facts)])

            self.assertEqual(code, 0, stderr.getvalue())
            self.assertTrue((run_dir / "prepared_skill.md").exists())
            self.assertTrue((run_dir / "synthesis_check.json").exists())
            self.assertTrue((run_dir / "synthesized_facts_normalized.dl").exists())
            self.assertTrue((run_dir / "detection_result.json").exists())
            self.assertTrue((run_dir / "report.md").exists())
            self.assertIn("# Semia Audit Report", stdout.getvalue())

            sarif_stdout = io.StringIO()
            sarif_stderr = io.StringIO()
            with contextlib.redirect_stdout(sarif_stdout), contextlib.redirect_stderr(sarif_stderr):
                sarif_code = main(["report", str(run_dir), "--format", "sarif"])

            self.assertEqual(sarif_code, 0, sarif_stderr.getvalue())
            self.assertTrue((run_dir / "report.sarif.json").exists())
            self.assertIn('"version": "2.1.0"', sarif_stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
