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
            self.assertIn("# Semia Report", stdout.getvalue())

            sarif_stdout = io.StringIO()
            sarif_stderr = io.StringIO()
            with contextlib.redirect_stdout(sarif_stdout), contextlib.redirect_stderr(sarif_stderr):
                sarif_code = main(["report", str(run_dir), "--format", "sarif"])

            self.assertEqual(sarif_code, 0, sarif_stderr.getvalue())
            self.assertTrue((run_dir / "report.sarif.json").exists())
            self.assertIn('"version": "2.1.0"', sarif_stdout.getvalue())

    def test_synthesize_with_host_metadata_records_manifest(self) -> None:
        import json

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

            stdout, stderr = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = main(
                    [
                        "scan",
                        str(skill),
                        "--out",
                        str(run_dir),
                        "--facts",
                        str(facts),
                        "--host-session-id",
                        "sess-42",
                        "--host-model",
                        "claude-opus-4-7",
                    ]
                )
            self.assertEqual(code, 0, stderr.getvalue())

            manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["host_synthesis"]["session_id"], "sess-42")
            self.assertEqual(manifest["host_synthesis"]["model"], "claude-opus-4-7")
            self.assertIn("prepared_skill_sha256", manifest)
            self.assertIn("synthesized_facts_sha256", manifest)
            self.assertIn("hostile_input_nonce", manifest)

    def test_synthesis_status_subcommand_reports_scores(self) -> None:
        import json

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

            with (
                contextlib.redirect_stdout(io.StringIO()),
                contextlib.redirect_stderr(io.StringIO()),
            ):
                main(["scan", str(skill), "--out", str(run_dir), "--facts", str(facts)])

            stdout, stderr = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = main(["synthesis-status", str(run_dir)])
            self.assertEqual(code, 0, stderr.getvalue())
            payload = json.loads(stdout.getvalue())
            self.assertIn("scores", payload)
            self.assertIn("composite", payload["scores"])
            self.assertIn("stop_criteria", payload)
            self.assertEqual(payload["stop_criteria"]["ceiling_score"], 0.9)
            self.assertIsInstance(payload["suggestions"], list)

    def test_synthesis_status_respects_env_overrides(self) -> None:
        """SEMIA_SYNTHESIS_CEILING / SEMIA_SYNTHESIS_SCORE_WEIGHTS env overrides
        must flow into synthesis-status output. Regression for the bug where
        the subcommand reported hardcoded defaults while the synthesis loop used
        env-driven settings."""
        import json
        import os

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

            with (
                contextlib.redirect_stdout(io.StringIO()),
                contextlib.redirect_stderr(io.StringIO()),
            ):
                main(["scan", str(skill), "--out", str(run_dir), "--facts", str(facts)])

            prev_ceiling = os.environ.get("SEMIA_SYNTHESIS_CEILING")
            prev_weights = os.environ.get("SEMIA_SYNTHESIS_SCORE_WEIGHTS")
            os.environ["SEMIA_SYNTHESIS_CEILING"] = "0.7"
            os.environ["SEMIA_SYNTHESIS_SCORE_WEIGHTS"] = "0.4,0.4,0.2"
            try:
                stdout, stderr = io.StringIO(), io.StringIO()
                with (
                    contextlib.redirect_stdout(stdout),
                    contextlib.redirect_stderr(stderr),
                ):
                    code = main(["synthesis-status", str(run_dir)])
                self.assertEqual(code, 0, stderr.getvalue())
                payload = json.loads(stdout.getvalue())
                self.assertEqual(payload["stop_criteria"]["ceiling_score"], 0.7)
                self.assertEqual(payload["scores"]["weights"], [0.4, 0.4, 0.2])
            finally:
                if prev_ceiling is None:
                    os.environ.pop("SEMIA_SYNTHESIS_CEILING", None)
                else:
                    os.environ["SEMIA_SYNTHESIS_CEILING"] = prev_ceiling
                if prev_weights is None:
                    os.environ.pop("SEMIA_SYNTHESIS_SCORE_WEIGHTS", None)
                else:
                    os.environ["SEMIA_SYNTHESIS_SCORE_WEIGHTS"] = prev_weights

    def test_synthesize_apply_patch_runs_deterministically(self) -> None:
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

            with (
                contextlib.redirect_stdout(io.StringIO()),
                contextlib.redirect_stderr(io.StringIO()),
            ):
                main(["scan", str(skill), "--out", str(run_dir), "--facts", str(facts)])

            patch = base / "patch.dl"
            patch.write_text(
                'skill_doc_claim("demo-skill", "read_only").\n'
                'skill_doc_claim_evidence_text("demo-skill", "read_only", '
                '"Read a local file path").\n',
                encoding="utf-8",
            )

            stdout, stderr = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = main(["synthesize", str(run_dir), "--apply-patch", str(patch)])
            self.assertEqual(code, 0, stderr.getvalue())
            facts_text = (run_dir / "synthesized_facts.dl").read_text(encoding="utf-8")
            self.assertIn('skill_doc_claim("demo-skill", "read_only").', facts_text)

    def test_synthesize_evidence_taint_threshold_rejects_hallucinated_quotes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            skill = base / "demo-skill"
            skill.mkdir()
            (skill / "SKILL.md").write_text(
                "# Demo Skill\n\n- Read a local file.\n",
                encoding="utf-8",
            )
            facts = base / "facts.dl"
            facts.write_text(
                'skill("demo-skill").\n'
                'skill_evidence_text("demo-skill", "Demo Skill").\n'
                'action("a", "demo-skill").\n'
                'action_evidence_text("a", "ZZZ_NOT_IN_SKILL_AT_ALL_xqxq").\n',
                encoding="utf-8",
            )
            run_dir = base / "run"

            stdout, stderr = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = main(
                    [
                        "scan",
                        str(skill),
                        "--out",
                        str(run_dir),
                        "--facts",
                        str(facts),
                        "--evidence-taint-threshold",
                        "0.9",
                    ]
                )
            # scan continues through detect/report even when check fails; the
            # check output must show program_valid=false with EVD020.
            self.assertEqual(code, 0, stderr.getvalue())
            import json

            check_payload = json.loads(
                (run_dir / "synthesis_check.json").read_text(encoding="utf-8")
            )
            self.assertFalse(check_payload["program_valid"])
            self.assertIn("EVD020", {issue["code"] for issue in check_payload["errors"]})


if __name__ == "__main__":
    unittest.main()
