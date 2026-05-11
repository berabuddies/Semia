# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 RiemaLabs
from __future__ import annotations

import io
import importlib
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CLI_SRC = REPO_ROOT / "packages" / "semia-cli" / "src"
CORE_SRC = REPO_ROOT / "packages" / "semia-core" / "src"
sys.path.insert(0, str(CORE_SRC))
sys.path.insert(0, str(CLI_SRC))

from semia_cli.main import main  # noqa: E402

main_module = importlib.import_module("semia_cli.main")
core_adapter_module = importlib.import_module("semia_cli.core_adapter")


class SemiaCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self._old_synthesize_facts = main_module.llm_adapter.synthesize_facts
        self._old_prepare = core_adapter_module.prepare
        self._old_check = core_adapter_module.check
        self._old_detect = core_adapter_module.detect
        self._old_extract_baseline = core_adapter_module.extract_baseline
        self._old_report = core_adapter_module.report
        self.calls: list[tuple[str, dict[str, object]]] = []

        def prepare(skill_path: Path, run_dir: Path) -> dict[str, object]:
            kwargs: dict[str, object] = {"skill_path": skill_path, "out_dir": run_dir}
            self.calls.append(("prepare", kwargs))
            run_dir.mkdir(parents=True, exist_ok=True)
            return {"status": "prepared", "run_dir": run_dir}

        def check(run_dir: Path, facts_path: Path | None = None) -> dict[str, object]:
            self.calls.append(("check_facts", {"run_dir": run_dir, "facts_path": facts_path}))
            self.calls.append(("align_evidence", {"run_dir": run_dir, "facts_path": facts_path}))
            return {"status": "checked"}

        def detect(run_dir: Path) -> dict[str, object]:
            self.calls.append(("detect", {"run_dir": run_dir}))
            return {"status": "detected"}

        def extract_baseline(run_dir: Path) -> dict[str, object]:
            self.calls.append(("extract_baseline", {"run_dir": run_dir}))
            (run_dir / "synthesized_facts.dl").write_text('skill("s").\n', encoding="utf-8")
            return {"status": "baseline_synthesized"}

        def report(run_dir: Path, format: str) -> object:
            self.calls.append(("report", {"run_dir": run_dir, "format": format}))
            if format == "sarif":
                return {"version": "2.1.0"}
            return "# Semia Report"

        def synthesize_facts(
            run_dir: Path,
            *,
            provider: str | None = None,
            model: str | None = None,
            validator=None,
        ) -> dict[str, object]:
            self.calls.append(
                (
                    "synthesize_facts",
                    {"run_dir": run_dir, "provider": provider, "model": model, "validator": validator},
                )
            )
            (run_dir / "synthesized_facts.dl").write_text('skill("s").\n', encoding="utf-8")
            return {"status": "synthesized", "provider": provider or "openai", "model": model or "provider-default"}

        core_adapter_module.prepare = prepare
        core_adapter_module.check = check
        core_adapter_module.detect = detect
        core_adapter_module.extract_baseline = extract_baseline
        core_adapter_module.report = report
        main_module.llm_adapter.synthesize_facts = synthesize_facts

    def tearDown(self) -> None:
        main_module.llm_adapter.synthesize_facts = self._old_synthesize_facts
        core_adapter_module.prepare = self._old_prepare
        core_adapter_module.check = self._old_check
        core_adapter_module.detect = self._old_detect
        core_adapter_module.extract_baseline = self._old_extract_baseline
        core_adapter_module.report = self._old_report

    def test_prepare_delegates_to_core(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_path = Path(tmp) / "some-skill"
            skill_path.mkdir()
            run_dir = Path(tmp) / "run"

            code, out, err = self._run(["prepare", str(skill_path), "--out", str(run_dir)])

            self.assertEqual(code, 0, err)
            self.assertIn('"status": "prepared"', out)
            self.assertEqual(self.calls[0][0], "prepare")
            self.assertEqual(self.calls[0][1]["skill_path"], skill_path.resolve())
            self.assertEqual(self.calls[0][1]["out_dir"], run_dir.resolve())

    def test_synthesize_uses_default_run_dir_and_aligns_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            run_dir.mkdir()

            code, out, err = self._run(["synthesize", str(run_dir)])

            self.assertEqual(code, 0, err)
            self.assertIn('"status": "checked"', out)
            self.assertEqual([call[0] for call in self.calls], ["synthesize_facts", "check_facts", "align_evidence"])
            self.assertEqual(self.calls[1][1]["facts_path"], run_dir.resolve() / "synthesized_facts.dl")

    def test_synthesize_accepts_explicit_facts_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            run_dir.mkdir()
            facts_path = Path(tmp) / "facts.dl"
            facts_path.write_text('skill("s").\n', encoding="utf-8")

            code, _out, err = self._run(
                ["synthesize", str(run_dir), "--facts", str(facts_path)]
            )

            self.assertEqual(code, 0, err)
            self.assertEqual([call[0] for call in self.calls], ["check_facts", "align_evidence"])
            self.assertEqual(self.calls[0][1]["facts_path"], run_dir.resolve() / "synthesized_facts.dl")
            self.assertTrue((run_dir.resolve() / "synthesized_facts.dl").exists())

    def test_synthesize_with_existing_default_facts_recalls_llm(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            run_dir.mkdir()
            facts_path = run_dir / "synthesized_facts.dl"
            facts_path.write_text('skill("s").\n', encoding="utf-8")

            code, out, err = self._run(["synthesize", str(run_dir)])

            self.assertEqual(code, 0, err)
            self.assertIn('"status": "checked"', out)
            self.assertEqual(
                [call[0] for call in self.calls],
                ["synthesize_facts", "check_facts", "align_evidence"],
            )

    def test_synthesize_skips_llm_when_facts_point_at_default_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            run_dir.mkdir()
            facts_path = run_dir / "synthesized_facts.dl"
            facts_path.write_text('skill("s").\n', encoding="utf-8")

            code, _out, err = self._run(
                ["synthesize", str(run_dir), "--facts", str(facts_path)]
            )

            self.assertEqual(code, 0, err)
            self.assertEqual([call[0] for call in self.calls], ["check_facts", "align_evidence"])

    def test_detect_and_report_delegate_to_core(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            run_dir.mkdir()

            detect_code, detect_out, detect_err = self._run(["detect", str(run_dir)])
            report_code, report_out, report_err = self._run(
                ["report", str(run_dir), "--format", "md"]
            )

            self.assertEqual(detect_code, 0, detect_err)
            self.assertIn('"status": "detected"', detect_out)
            self.assertEqual(report_code, 0, report_err)
            self.assertEqual(report_out.strip(), "# Semia Report")
            self.assertEqual([call[0] for call in self.calls], ["detect", "report"])
            self.assertEqual(self.calls[1][1]["format"], "md")

    def test_report_supports_sarif(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            run_dir.mkdir()

            code, out, err = self._run(["report", str(run_dir), "--format", "sarif"])

            self.assertEqual(code, 0, err)
            self.assertIn('"version": "2.1.0"', out)
            self.assertEqual(self.calls[0][1]["format"], "sarif")

    def test_scan_runs_full_audit_with_llm_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_path = Path(tmp) / "some-skill"
            skill_path.mkdir()
            run_dir = Path(tmp) / "run"

            code, out, err = self._run(["scan", str(skill_path), "--out", str(run_dir)])

            self.assertEqual(code, 0, err)
            self.assertEqual(
                [call[0] for call in self.calls],
                ["prepare", "synthesize_facts", "check_facts", "align_evidence", "detect", "report"],
            )
            self.assertIn("running synthesize with provider `openai`", out)
            self.assertIn("# Semia Report", out)

    def test_scan_accepts_anthropic_provider(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_path = Path(tmp) / "some-skill"
            skill_path.mkdir()
            run_dir = Path(tmp) / "run"

            code, out, err = self._run(
                [
                    "scan",
                    str(skill_path),
                    "--out",
                    str(run_dir),
                    "--provider",
                    "anthropic",
                    "--model",
                    "claude-test",
                ]
            )

            self.assertEqual(code, 0, err)
            synthesize_call = self.calls[1][1]
            self.assertEqual(synthesize_call["provider"], "anthropic")
            self.assertEqual(synthesize_call["model"], "claude-test")
            self.assertIn("provider `anthropic`", out)

    def test_scan_offline_baseline_is_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_path = Path(tmp) / "some-skill"
            skill_path.mkdir()
            run_dir = Path(tmp) / "run"

            code, out, err = self._run(["scan", str(skill_path), "--out", str(run_dir), "--offline-baseline"])

            self.assertEqual(code, 0, err)
            self.assertEqual(
                [call[0] for call in self.calls],
                ["prepare", "extract_baseline", "check_facts", "align_evidence", "detect", "report"],
            )
            self.assertIn("conservative offline baseline map", out)
            self.assertIn("# Semia Report", out)

    def test_scan_prepare_only_prints_agent_guidance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_path = Path(tmp) / "some-skill"
            skill_path.mkdir()
            run_dir = Path(tmp) / "run"

            code, out, err = self._run(["scan", str(skill_path), "--out", str(run_dir), "--prepare-only"])

            self.assertEqual(code, 0, err)
            self.assertEqual([call[0] for call in self.calls], ["prepare"])
            self.assertIn("current agent session", out)
            self.assertIn("synthesized_facts.dl", out)
            self.assertIn("semia synthesize", out)

    def test_scan_with_facts_runs_deterministic_tail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_path = Path(tmp) / "some-skill"
            skill_path.mkdir()
            run_dir = Path(tmp) / "run"
            facts_path = Path(tmp) / "facts.dl"
            facts_path.write_text('skill("s").\n', encoding="utf-8")

            code, out, err = self._run(
                [
                    "scan",
                    str(skill_path),
                    "--out",
                    str(run_dir),
                    "--facts",
                    str(facts_path),
                ]
            )

            self.assertEqual(code, 0, err)
            self.assertEqual(
                [call[0] for call in self.calls],
                ["prepare", "check_facts", "align_evidence", "detect", "report"],
            )
            self.assertTrue((run_dir / "synthesized_facts.dl").exists())
            self.assertIn("Copied synthesized facts", out)
            self.assertIn("# Semia Report", out)

    def test_version_flag_prints_package_version(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        old_stdout, old_stderr = sys.stdout, sys.stderr
        try:
            sys.stdout = stdout
            sys.stderr = stderr
            with self.assertRaises(SystemExit) as ctx:
                main(["--version"])
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
        self.assertEqual(ctx.exception.code, 0)
        self.assertIn("semia ", stdout.getvalue())

    def _run(self, argv: list[str]) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        argv_with_streams = list(argv)
        parser_streams = {"_stdout": stdout, "_stderr": stderr}
        return _run_with_streams(argv_with_streams, parser_streams)


def _run_with_streams(
    argv: list[str], streams: dict[str, io.StringIO]
) -> tuple[int, str, str]:
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    try:
        sys.stdout = streams["_stdout"]
        sys.stderr = streams["_stderr"]
        code = main(argv)
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
    return code, streams["_stdout"].getvalue(), streams["_stderr"].getvalue()


if __name__ == "__main__":
    unittest.main()
