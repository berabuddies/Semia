# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 berabuddies
from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[2]
CLI_SRC = REPO_ROOT / "packages" / "semia-cli" / "src"
CORE_SRC = REPO_ROOT / "packages" / "semia-core" / "src"
sys.path.insert(0, str(CORE_SRC))
sys.path.insert(0, str(CLI_SRC))

from semia_cli import repair as repair_module  # noqa: E402


class RepairPipelineTests(unittest.TestCase):
    def test_trace_only_summarizes_findings_without_llm_or_patch_dir(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = self._make_run_dir(Path(td))
            stdout = io.StringIO()

            with mock.patch.object(repair_module, "call_provider") as call_provider:
                result = repair_module.repair(run_dir, trace_only=True, stdout=stdout)

            call_provider.assert_not_called()
            self.assertEqual(result, {"status": "traced", "findings": 1, "labels": 1})
            self.assertIn("label_obfuscation", stdout.getvalue())
            self.assertFalse((run_dir / "patched").exists())

    def test_repair_writes_patched_skill_and_result_summary(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            skill_dir = root / "skill"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                "# Demo\n\nRun encoded payload.\n",
                encoding="utf-8",
            )
            run_dir = self._make_run_dir(root, skill_root=skill_dir)
            stdout = io.StringIO()
            response = json.dumps(
                {
                    "analysis": "The skill runs encoded code. It should refuse that payload.",
                    "conjunct_to_break": 'call_code(c, "encoded_binary")',
                    "fix_strategy": "Replace the encoded-payload instruction with a refusal.",
                    "files": [
                        {
                            "path": "SKILL.md",
                            "action": "edit",
                            "edits": [
                                {
                                    "old": "Run encoded payload.",
                                    "new": "Refuse to run encoded payloads.",
                                }
                            ],
                        }
                    ],
                }
            )

            with mock.patch.object(repair_module, "call_provider", return_value=response) as call:
                result = repair_module.repair(
                    run_dir,
                    provider="codex",
                    model="test-model",
                    trace_only=False,
                    stdout=stdout,
                )

            self.assertEqual(result["status"], "repaired")
            self.assertEqual(result["labels_repaired"], 1)
            self.assertEqual(
                (run_dir / "patched" / "SKILL.md").read_text(encoding="utf-8"),
                "# Demo\n\nRefuse to run encoded payloads.\n",
            )
            self.assertEqual(
                (skill_dir / "SKILL.md").read_text(encoding="utf-8"),
                "# Demo\n\nRun encoded payload.\n",
            )
            summary = json.loads((run_dir / "repair_result.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["repairs"][0]["conjunct"], 'call_code(c, "encoded_binary")')
            prompt = call.call_args.args[1]
            self.assertIn("label_obfuscation(demo, act_1, call_1, encoded_binary)", prompt)
            self.assertIn('Head: label_obfuscation(s, a, c, "encoded_binary")', prompt)

    def _make_run_dir(self, root: Path, *, skill_root: Path | None = None) -> Path:
        run_dir = root / "run"
        run_dir.mkdir()
        (run_dir / "detection_result.json").write_text(
            json.dumps(
                {
                    "findings": [
                        {
                            "label": "label_obfuscation",
                            "fields": ["demo", "act_1", "call_1", "encoded_binary"],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        (run_dir / "synthesized_facts.dl").write_text(
            "\n".join(
                [
                    'skill("demo").',
                    'action("act_1", "demo").',
                    'action_evidence_text("act_1", "Run encoded payload.")',
                    'call("call_1", "act_1").',
                    'call_evidence_text("call_1", "Run encoded payload.")',
                    'call_code("call_1", "encoded_binary").',
                    'call_code_evidence_text("call_1", "encoded_binary", "encoded payload")',
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        if skill_root is not None:
            (run_dir / "prepare_metadata.json").write_text(
                json.dumps({"source": {"root": str(skill_root)}}),
                encoding="utf-8",
            )
        return run_dir


if __name__ == "__main__":
    unittest.main()
