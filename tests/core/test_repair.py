# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 RiemaLabs
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "packages/semia-core/src"))

from semia_core.artifacts import Fact, Finding  # noqa: E402
from semia_core.repair import (  # noqa: E402
    DLRule,
    apply_patch,
    build_evidence_map,
    build_repair_prompt,
    locate_in_source,
    parse_patch_response,
    trace_findings,
)


class RepairCoreTests(unittest.TestCase):
    def test_trace_findings_honors_quoted_body_literals(self) -> None:
        rule = DLRule(
            head="label_dangerous_execution_primitives(s, a, c)",
            head_name="label_dangerous_execution_primitives",
            head_args=["s", "a", "c"],
            body=["call(c, a)", 'call_effect(c, "proc_exec")'],
        )
        facts = [
            Fact("call", ("call_1", "act_1")),
            Fact("call_effect", ("call_1", "net_read")),
            Fact("call_effect", ("call_1", "proc_exec")),
        ]

        traced = trace_findings(
            [
                Finding(
                    label="label_dangerous_execution_primitives",
                    fields=("demo", "act_1", "call_1"),
                )
            ],
            [rule],
            facts,
            {},
        )

        effect_facts = traced[0].conjuncts[1].matched_facts
        self.assertEqual([fact.args for fact in effect_facts], [("call_1", "proc_exec")])

    def test_trace_findings_selects_rule_matching_head_literal(self) -> None:
        rules = [
            DLRule(
                head='label_obfuscation(s, a, c, "obfuscated")',
                head_name="label_obfuscation",
                head_args=["s", "a", "c", '"obfuscated"'],
                body=['call_code(c, "obfuscated")'],
            ),
            DLRule(
                head='label_obfuscation(s, a, c, "encoded_binary")',
                head_name="label_obfuscation",
                head_args=["s", "a", "c", '"encoded_binary"'],
                body=['call_code(c, "encoded_binary")'],
            ),
        ]
        facts = [Fact("call_code", ("call_1", "encoded_binary"))]

        traced = trace_findings(
            [
                {
                    "label": "label_obfuscation",
                    "fields": ["demo", "act_1", "call_1", "encoded_binary"],
                }
            ],
            rules,
            facts,
            {},
        )

        self.assertEqual(traced[0].rule.head, 'label_obfuscation(s, a, c, "encoded_binary")')
        self.assertEqual(traced[0].conjuncts[0].matched_facts, facts)

    def test_build_prompt_includes_evidence_and_source_location(self) -> None:
        rule = DLRule(
            head="label_demo(s, a)",
            head_name="label_demo",
            head_args=["s", "a"],
            body=["action(a, s)"],
        )
        facts = [Fact("action", ("act_1", "demo"))]
        evidence_map = build_evidence_map(
            'action_evidence_text("act_1", "Run sed -i on adapter.ts").\n'
        )
        traced = trace_findings(
            [{"label": "label_demo", "fields": ["demo", "act_1"]}],
            [rule],
            facts,
            evidence_map,
        )
        locate_in_source(
            traced,
            [
                {
                    "text": "Use the tool, then Run sed -i on adapter.ts.",
                    "source_file": "SKILL.md",
                    "line_start": 7,
                    "line_end": 8,
                }
            ],
        )

        prompt = build_repair_prompt(traced[0], facts, evidence_map, "# Demo\n")

        self.assertIn("Run sed -i on adapter.ts", prompt)
        self.assertIn("@ SKILL.md:7-8", prompt)
        self.assertIn("label_demo(demo, act_1)", prompt)

    def test_parse_patch_response_and_apply_patch(self) -> None:
        response = """```json
{"files":[{"path":"SKILL.md","action":"edit","edits":[{"old":"Run payload","new":"Review payload"}]}]}
```"""

        patch = parse_patch_response(response)

        self.assertIsNotNone(patch)
        with tempfile.TemporaryDirectory() as td:
            skill_dir = Path(td)
            skill_path = skill_dir / "SKILL.md"
            skill_path.write_text("Run payload\nRun payload\n", encoding="utf-8")

            applied = apply_patch(patch or {}, skill_dir)

            self.assertEqual(applied, ["EDIT SKILL.md"])
            self.assertEqual(
                skill_path.read_text(encoding="utf-8"), "Review payload\nRun payload\n"
            )


if __name__ == "__main__":
    unittest.main()
