from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]
CLI_SRC = REPO_ROOT / "packages" / "semia-cli" / "src"
sys.path.insert(0, str(CLI_SRC))

from semia_cli import llm_adapter  # noqa: E402


class LlmAdapterTests(unittest.TestCase):
    def test_defaults_use_openai_gpt_55(self) -> None:
        with mock.patch.dict("os.environ", {}, clear=True):
            provider = llm_adapter.default_provider()
            model = llm_adapter.default_model(provider=provider)

        self.assertEqual(provider, "openai")
        self.assertEqual(model, "gpt-5.5")

    def test_openai_provider_writes_synthesized_facts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            (run_dir / "synthesis_prompt.md").write_text("Emit facts.", encoding="utf-8")
            (run_dir / "prepared_skill.md").write_text("# Demo\n", encoding="utf-8")

            class FakeResponse:
                def __enter__(self):
                    return self

                def __exit__(self, exc_type, exc, traceback):
                    return False

                def read(self) -> bytes:
                    return b'{"output_text": "```datalog\\nskill(\\"demo\\").\\n```"}'

                @property
                def headers(self) -> dict[str, str]:
                    return {"Content-Type": "application/json"}

            with mock.patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}, clear=True):
                with mock.patch("semia_cli.llm_providers.request.urlopen", return_value=FakeResponse()) as urlopen:
                    result = llm_adapter.synthesize_facts(run_dir, provider="openai")

            self.assertEqual(result["status"], "synthesized")
            self.assertEqual(result["provider"], "openai")
            self.assertEqual(result["model"], "gpt-5.5")
            self.assertEqual((run_dir / "synthesized_facts.dl").read_text(encoding="utf-8"), 'skill("demo").\n')
            body = json_body(urlopen.call_args.args[0].data)
            self.assertEqual(body["model"], "gpt-5.5")
            self.assertTrue(body["stream"])
            self.assertIn("Prepared Skill Source", body["input"])

    def test_openai_provider_reads_streamed_response(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            (run_dir / "synthesis_prompt.md").write_text("Emit facts.", encoding="utf-8")
            (run_dir / "prepared_skill.md").write_text("# Demo\n", encoding="utf-8")

            class FakeStream:
                def __init__(self) -> None:
                    self._chunks = iter(
                        [
                            b"event: response.output_text.delta\n",
                            b'data: {"delta":"skill(\\"demo\\")."}\n\n',
                            b"event: response.completed\n",
                            b'data: {"usage":{"input_tokens":1,"output_tokens":1}}\n\n',
                        ]
                    )

                def __enter__(self):
                    return self

                def __exit__(self, exc_type, exc, traceback):
                    return False

                @property
                def headers(self) -> dict[str, str]:
                    return {"Content-Type": "text/event-stream"}

                def read(self, _size: int = -1) -> bytes:
                    return next(self._chunks, b"")

            with mock.patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}, clear=True):
                with mock.patch("semia_cli.llm_providers.request.urlopen", return_value=FakeStream()):
                    result = llm_adapter.synthesize_facts(run_dir, provider="openai")

            self.assertEqual(result["provider"], "openai")
            self.assertEqual((run_dir / "synthesized_facts.dl").read_text(encoding="utf-8"), 'skill("demo").\n')

    def test_claude_default_model_reads_anthropic_model(self) -> None:
        with mock.patch.dict("os.environ", {"ANTHROPIC_MODEL": "sonnet"}, clear=True):
            model = llm_adapter.default_model(provider="claude")

        self.assertEqual(model, "sonnet")

    def test_anthropic_provider_uses_sdk_stream(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            (run_dir / "synthesis_prompt.md").write_text("Emit facts.", encoding="utf-8")
            (run_dir / "prepared_skill.md").write_text("# Demo\n", encoding="utf-8")
            requests: list[dict[str, object]] = []

            class Delta:
                type = "text_delta"
                text = 'skill("demo").\n'

            class Event:
                type = "content_block_delta"
                delta = Delta()

            class Stream:
                def __enter__(self):
                    return iter([Event()])

                def __exit__(self, exc_type, exc, traceback):
                    return False

            class Messages:
                def create(self, **kwargs):
                    requests.append(kwargs)
                    return Stream()

            class AnthropicClient:
                def __init__(self, **kwargs):
                    requests.append({"client": kwargs})
                    self.messages = Messages()

            fake_anthropic = type("FakeAnthropicModule", (), {"Anthropic": AnthropicClient})

            with mock.patch.dict(
                "sys.modules",
                {"anthropic": fake_anthropic},
            ):
                with mock.patch.dict(
                    "os.environ",
                    {"ANTHROPIC_API_KEY": "test-key", "ANTHROPIC_MODEL": "claude-test"},
                    clear=True,
                ):
                    result = llm_adapter.synthesize_facts(run_dir, provider="anthropic")

            self.assertEqual(result["provider"], "anthropic")
            self.assertEqual(result["model"], "claude-test")
            self.assertEqual((run_dir / "synthesized_facts.dl").read_text(encoding="utf-8"), 'skill("demo").\n')
            self.assertEqual(requests[0]["client"]["api_key"], "test-key")  # type: ignore[index]
            self.assertEqual(requests[1]["model"], "claude-test")
            self.assertTrue(requests[1]["stream"])

    def test_codex_provider_writes_synthesized_facts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            (run_dir / "synthesis_prompt.md").write_text("Emit facts.", encoding="utf-8")
            (run_dir / "prepared_skill.md").write_text("# Demo\n", encoding="utf-8")

            def fake_run(cmd, input=None, cwd=None, text=None, capture_output=None, check=None):
                output_path = Path(cmd[cmd.index("--output-last-message") + 1])
                output_path.write_text('```datalog\nskill("demo").\n```\n', encoding="utf-8")
                return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

            with mock.patch("semia_cli.llm_providers.shutil.which", return_value="/bin/codex"):
                with mock.patch("semia_cli.llm_providers.subprocess.run", side_effect=fake_run) as run:
                    result = llm_adapter.synthesize_facts(run_dir, provider="codex", model="test-model")

            self.assertEqual(result["status"], "synthesized")
            self.assertEqual(result["provider"], "codex")
            self.assertEqual(result["model"], "test-model")
            self.assertEqual((run_dir / "synthesized_facts.dl").read_text(encoding="utf-8"), 'skill("demo").\n')
            self.assertIn("--model", run.call_args.args[0])
            self.assertIn("test-model", run.call_args.args[0])

    def test_claude_provider_uses_stdout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            (run_dir / "synthesis_prompt.md").write_text("Emit facts.", encoding="utf-8")
            (run_dir / "prepared_skill.md").write_text("# Demo\n", encoding="utf-8")
            completed = subprocess.CompletedProcess(["claude"], 0, stdout='skill("demo").\n', stderr="")

            with mock.patch.dict("os.environ", {}, clear=True):
                with mock.patch("semia_cli.llm_providers.shutil.which", return_value="/bin/claude"):
                    with mock.patch("semia_cli.llm_providers.subprocess.run", return_value=completed):
                        result = llm_adapter.synthesize_facts(run_dir, provider="claude")

            self.assertEqual(result["provider"], "claude")
            self.assertEqual(result["model"], "provider-default")
            self.assertEqual((run_dir / "synthesized_facts.dl").read_text(encoding="utf-8"), 'skill("demo").\n')

    def test_synthesis_loop_retries_and_writes_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            (run_dir / "synthesis_prompt.md").write_text("Emit facts.", encoding="utf-8")
            (run_dir / "prepared_skill.md").write_text("# Demo\n", encoding="utf-8")
            responses = iter(["not a fact\n", 'skill("demo").\n'])

            def fake_run(cmd, input=None, cwd=None, text=None, capture_output=None, check=None):
                output_path = Path(cmd[cmd.index("--output-last-message") + 1])
                output_path.write_text(next(responses), encoding="utf-8")
                return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

            def validator(_run_dir: Path, facts_path: Path):
                source = facts_path.read_text(encoding="utf-8")
                if "skill(" not in source:
                    return {"program_valid": False, "errors": 1, "warnings": 0}
                return {
                    "program_valid": True,
                    "errors": 0,
                    "warnings": 0,
                    "evidence_match_rate": 1.0,
                    "evidence_support_coverage": 1.0,
                    "reference_unit_coverage": 0.5,
                }

            with mock.patch.dict(
                "os.environ",
                {"SEMIA_SYNTHESIS_N_ITERATIONS": "1", "SEMIA_SYNTHESIS_MAX_RETRIES": "1"},
                clear=True,
            ):
                with mock.patch("semia_cli.llm_providers.shutil.which", return_value="/bin/codex"):
                    with mock.patch("semia_cli.llm_providers.subprocess.run", side_effect=fake_run):
                        result = llm_adapter.synthesize_facts(run_dir, provider="codex", validator=validator)

            self.assertEqual(result["selected_iteration"], 0)
            self.assertEqual(result["score"], 0.5)
            self.assertTrue((run_dir / "synthesis_response_0_0.txt").exists())
            self.assertTrue((run_dir / "synthesis_response_0_1.txt").exists())
            self.assertTrue((run_dir / "synthesized_facts_0.dl").exists())
            metadata = json_body((run_dir / "synthesis_metadata.json").read_bytes())
            self.assertTrue(metadata["completed"])
            self.assertEqual(metadata["selected_iteration"], 0)
            self.assertEqual(metadata["iterations"][0]["attempts"], 2)

    def test_synthesis_loop_applies_incremental_patch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            (run_dir / "synthesis_prompt.md").write_text("Emit facts.", encoding="utf-8")
            (run_dir / "prepared_skill.md").write_text("# Demo\n", encoding="utf-8")
            responses = iter(
                [
                    'skill("demo").\n',
                    'action("act_read", "demo").\n',
                ]
            )

            def fake_run(cmd, input=None, cwd=None, text=None, capture_output=None, check=None):
                output_path = Path(cmd[cmd.index("--output-last-message") + 1])
                output_path.write_text(next(responses), encoding="utf-8")
                return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

            def validator(_run_dir: Path, facts_path: Path):
                source = facts_path.read_text(encoding="utf-8")
                return {
                    "program_valid": True,
                    "errors": 0,
                    "warnings": 0,
                    "evidence_match_rate": 1.0,
                    "evidence_support_coverage": 1.0,
                    "reference_unit_coverage": 0.8 if "action(" in source else 0.4,
                }

            with mock.patch.dict(
                "os.environ",
                {"SEMIA_SYNTHESIS_N_ITERATIONS": "2", "SEMIA_SYNTHESIS_MAX_RETRIES": "0"},
                clear=True,
            ):
                with mock.patch("semia_cli.llm_providers.shutil.which", return_value="/bin/codex"):
                    with mock.patch("semia_cli.llm_providers.subprocess.run", side_effect=fake_run):
                        result = llm_adapter.synthesize_facts(run_dir, provider="codex", validator=validator)

            self.assertEqual(result["selected_iteration"], 1)
            final_source = (run_dir / "synthesized_facts.dl").read_text(encoding="utf-8")
            self.assertIn('skill("demo").', final_source)
            self.assertIn('action("act_read", "demo").', final_source)
            self.assertTrue((run_dir / "synthesis_patch_1_0.dl").exists())
            metadata = json_body((run_dir / "synthesis_metadata.json").read_bytes())
            self.assertEqual(metadata["iterations"][1]["candidate_mode"], "incremental_patch")

def json_body(data: bytes) -> dict[str, object]:
    import json

    return json.loads(data.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
