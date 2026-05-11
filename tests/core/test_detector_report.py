# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 RiemaLabs
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "packages/semia-core/src"))

from semia_core.artifacts import AuditReport
from semia_core.checker import check_program
from semia_core import detector as detector_module
from semia_core.detector import run_detector
from semia_core.pipeline import (
    ARTIFACT_REPORT_JSON,
    ARTIFACT_SYNTHESIS_ALIGNMENT,
    check,
    detect,
    prepare,
    report,
)
from semia_core.report import render_markdown_report


class DetectorReportTests(unittest.TestCase):
    def test_detector_reports_unavailable_when_souffle_backend_forced(self) -> None:
        previous_bin = os.environ.get("SEMIA_SOUFFLE_BIN")
        previous_backend = os.environ.get("SEMIA_DETECTOR_BACKEND")
        os.environ["SEMIA_SOUFFLE_BIN"] = "/definitely/not/souffle"
        os.environ["SEMIA_DETECTOR_BACKEND"] = "souffle"
        try:
            with tempfile.TemporaryDirectory() as td:
                facts = Path(td) / "facts.dl"
                facts.write_text('skill("demo").\n', encoding="utf-8")
                result = run_detector(facts, Path(td) / "out")
        finally:
            for key, prev in (
                ("SEMIA_SOUFFLE_BIN", previous_bin),
                ("SEMIA_DETECTOR_BACKEND", previous_backend),
            ):
                if prev is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = prev

        self.assertEqual(result.status, "unavailable")
        self.assertEqual(result.backend, "souffle")

    def test_detector_falls_back_to_builtin_when_souffle_missing(self) -> None:
        previous_bin = os.environ.get("SEMIA_SOUFFLE_BIN")
        previous_backend = os.environ.get("SEMIA_DETECTOR_BACKEND")
        os.environ["SEMIA_SOUFFLE_BIN"] = "/definitely/not/souffle"
        os.environ["SEMIA_DETECTOR_BACKEND"] = "auto"
        try:
            with tempfile.TemporaryDirectory() as td:
                facts = Path(td) / "facts.dl"
                facts.write_text('skill("demo").\n', encoding="utf-8")
                result = run_detector(facts, Path(td) / "out")
        finally:
            for key, prev in (
                ("SEMIA_SOUFFLE_BIN", previous_bin),
                ("SEMIA_DETECTOR_BACKEND", previous_backend),
            ):
                if prev is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = prev

        self.assertEqual(result.status, "ok")
        self.assertEqual(result.backend, "builtin")

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

    def test_report_preserves_unmatched_evidence_after_json_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            (run_dir / "prepare_units.json").write_text(
                json.dumps({"source_id": "demo", "units": []}),
                encoding="utf-8",
            )
            alignment_payload = {
                "evidence_match_rate": 0.5,
                "reference_unit_coverage": 0.25,
                "grounding_score": 0.4,
                "alignments": [
                    {
                        "relation": "skill_evidence_text",
                        "args": ["demo", "Some unmatched quote"],
                        "line": 7,
                        "evidence_text": "Some unmatched quote",
                        "evidence_id": None,
                        "unit_id": None,
                        "score": 0.1,
                        "matched": False,
                    },
                    {
                        "relation": "action_evidence_text",
                        "args": ["act_x", "Matched line"],
                        "line": 9,
                        "evidence_text": "Matched line",
                        "evidence_id": "su_1",
                        "unit_id": 1,
                        "score": 0.95,
                        "matched": True,
                    },
                ],
                "normalized_facts": [],
            }
            (run_dir / ARTIFACT_SYNTHESIS_ALIGNMENT).write_text(
                json.dumps(alignment_payload), encoding="utf-8"
            )

            report(run_dir, format="json")
            self.assertTrue((run_dir / ARTIFACT_REPORT_JSON).exists())

            markdown = report(run_dir, format="md")
            self.assertIn("Unmatched evidence:", markdown)
            self.assertIn("Some unmatched quote", markdown)
            self.assertNotIn("Matched line", markdown.split("Unmatched evidence:", 1)[1])

    def test_souffle_subprocess_runs_in_facts_parent_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            facts = run_dir / "detection_input.dl"
            facts.write_text('skill("demo").\n', encoding="utf-8")
            output_dir = run_dir / "out"

            captured: dict[str, object] = {}

            class _FakeCompleted:
                returncode = 0
                stdout = ""
                stderr = ""

            def _fake_run(cmd, **kwargs):
                captured["cmd"] = cmd
                captured["cwd"] = kwargs.get("cwd")
                return _FakeCompleted()

            with mock.patch.object(detector_module, "find_souffle_binary", return_value="/fake/souffle"), \
                    mock.patch.object(detector_module.subprocess, "run", side_effect=_fake_run):
                previous_backend = os.environ.get("SEMIA_DETECTOR_BACKEND")
                os.environ["SEMIA_DETECTOR_BACKEND"] = "souffle"
                try:
                    result = run_detector(facts, output_dir)
                finally:
                    if previous_backend is None:
                        os.environ.pop("SEMIA_DETECTOR_BACKEND", None)
                    else:
                        os.environ["SEMIA_DETECTOR_BACKEND"] = previous_backend

            self.assertEqual(result.status, "ok")
            self.assertEqual(result.backend, "souffle")
            self.assertEqual(captured["cwd"], str(facts.parent))


if __name__ == "__main__":
    unittest.main()
