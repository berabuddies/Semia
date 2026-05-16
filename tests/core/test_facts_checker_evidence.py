# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 RiemaLabs
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "packages/semia-core/src"))

from semia_core.artifacts import SemanticUnit, _quote_arg
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
        self.assertTrue(
            any(f.relation == "call_evidence_text" for f in program.evidence_text_facts)
        )
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
        with tempfile_skill(
            "# Demo Skill\n\n- Read a local file.\n- Send no network traffic.\n"
        ) as path:
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

    def test_tokens_segment_cjk_characters(self) -> None:
        from semia_core.evidence import _tokens

        self.assertEqual(_tokens("已登录"), ["已", "登", "录"])
        # mixed Latin + CJK
        self.assertEqual(_tokens("hello 世界"), ["hello", "世", "界"])
        # Hiragana + Katakana
        self.assertEqual(_tokens("ありがとう"), ["あ", "り", "が", "と", "う"])
        self.assertEqual(_tokens("カタカナ"), ["カ", "タ", "カ", "ナ"])

    def test_score_matches_chinese_quote_to_chinese_unit(self) -> None:
        # Previously _tokens dropped CJK chars → score 0.0. With CJK segmentation
        # the quote and unit share characters and Jaccard is comfortably above
        # the 0.2 threshold.
        score = _score(
            "不要在脚本中明文保存密码",
            "不要在脚本中明文保存密码，优先使用 --browser real 模式复用已登录会话",
        )
        self.assertGreater(score, 0.2)

    def test_threshold_env_var_overrides_default(self) -> None:
        import os

        from semia_core.evidence import DEFAULT_EVIDENCE_THRESHOLD, _env_threshold

        # default
        os.environ.pop("SEMIA_EVIDENCE_THRESHOLD", None)
        self.assertEqual(_env_threshold(), DEFAULT_EVIDENCE_THRESHOLD)
        # explicit value
        os.environ["SEMIA_EVIDENCE_THRESHOLD"] = "0.5"
        try:
            self.assertEqual(_env_threshold(), 0.5)
        finally:
            os.environ.pop("SEMIA_EVIDENCE_THRESHOLD", None)
        # invalid → fall back to default
        os.environ["SEMIA_EVIDENCE_THRESHOLD"] = "not-a-float"
        try:
            self.assertEqual(_env_threshold(), DEFAULT_EVIDENCE_THRESHOLD)
        finally:
            os.environ.pop("SEMIA_EVIDENCE_THRESHOLD", None)
        # clamped to [0, 1]
        os.environ["SEMIA_EVIDENCE_THRESHOLD"] = "2.0"
        try:
            self.assertEqual(_env_threshold(), 1.0)
        finally:
            os.environ.pop("SEMIA_EVIDENCE_THRESHOLD", None)

    def test_containment_fallback_matches_short_quote_in_long_unit(self) -> None:
        # A 5-token quote almost entirely inside a 30+ token paragraph would
        # score < 0.2 under plain Jaccard; containment fallback rescues it.
        quote = "POST request to the configured webhook"
        unit = (
            "When the action runs, it builds a POST request to the configured "
            "webhook endpoint using the stored credentials and the rendered "
            "Markdown body of the report after sanitization completes."
        )
        score = _score(quote, unit)
        self.assertGreaterEqual(score, 0.2)


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


def _unit(uid: int, text: str) -> SemanticUnit:
    return SemanticUnit(
        id=uid,
        evidence_id=f"su_{uid}",
        unit_type="paragraph",
        text=text,
        line_start=1,
        line_end=1,
        source_file="f.md",
    )


class EffectiveThresholdTests(unittest.TestCase):
    def test_longer_evidence_returns_base_unchanged(self) -> None:
        from semia_core.evidence import _effective_threshold

        unit = _unit(1, "small unit text")
        result = _effective_threshold(0.2, "much longer evidence text than that small unit", unit)
        self.assertEqual(result, 0.2)

    def test_much_shorter_evidence_scales_by_ratio_with_floor(self) -> None:
        from semia_core.evidence import _effective_threshold

        unit = _unit(1, " ".join(["word"] * 50))
        result = _effective_threshold(0.2, "a b c d e", unit)
        self.assertAlmostEqual(result, 0.1, places=6)

    def test_empty_evidence_returns_base(self) -> None:
        from semia_core.evidence import _effective_threshold

        unit = _unit(1, "some unit text here")
        self.assertEqual(_effective_threshold(0.2, "", unit), 0.2)

    def test_unit_none_returns_base(self) -> None:
        from semia_core.evidence import _effective_threshold

        self.assertEqual(_effective_threshold(0.3, "anything", None), 0.3)


class BestUnitTests(unittest.TestCase):
    def test_tie_breaks_by_lower_id(self) -> None:
        from semia_core.evidence import _best_unit

        u1, u2 = _unit(1, "hello world stuff"), _unit(2, "hello world stuff")
        chosen, score = _best_unit("hello world stuff", (u1, u2))
        self.assertIsNotNone(chosen)
        self.assertEqual(chosen.id, 1)
        self.assertEqual(score, 1.0)

    def test_empty_unit_list_returns_none_and_zero(self) -> None:
        from semia_core.evidence import _best_unit

        chosen, score = _best_unit("text", ())
        self.assertIsNone(chosen)
        self.assertEqual(score, 0.0)


class AlignEvidenceTextTests(unittest.TestCase):
    def tearDown(self) -> None:
        import os

        os.environ.pop("SEMIA_EVIDENCE_THRESHOLD", None)

    def test_explicit_threshold_overrides_env_variable(self) -> None:
        import os

        os.environ["SEMIA_EVIDENCE_THRESHOLD"] = "0.5"
        unit = _unit(1, "hello world there bye now stuff plus more here")
        source = 'skill("d").\nskill_evidence_text("d", "hello").\n'
        result = align_evidence_text(source, (unit,), threshold=0.1)
        self.assertEqual(len(result.alignments), 1)
        self.assertTrue(result.alignments[0].matched)

    def test_empty_program_and_units_scores_zero_not_vacuous(self) -> None:
        result = align_evidence_text("", ())
        self.assertEqual(result.evidence_match_rate, 0.0)
        self.assertEqual(result.alignments, ())
        self.assertEqual(result.normalized_facts, ())

    def test_align_evidence_text_empty_program_and_units_scores_zero(self) -> None:
        """No evidence facts AND no units → grounding 0.0, not vacuous 1.0."""
        result = align_evidence_text('skill("demo").\n', [])
        self.assertEqual(result.evidence_match_rate, 0.0)
        self.assertEqual(result.reference_unit_coverage, 0.0)
        self.assertEqual(result.grounding_score, 0.0)

    def test_align_evidence_text_units_present_but_no_evidence_facts(self) -> None:
        """Units exist but no evidence facts to align → match_rate 0.0."""
        from semia_core.artifacts import SemanticUnit

        units = (
            SemanticUnit(
                id=0,
                evidence_id="su_0",
                unit_type="paragraph",
                text="Some content",
                line_start=1,
                line_end=1,
                source_file="SKILL.md",
            ),
        )
        result = align_evidence_text('skill("demo").\n', units)
        self.assertEqual(result.evidence_match_rate, 0.0)
        self.assertEqual(result.reference_unit_coverage, 0.0)

    def test_no_prepared_units_does_not_crash(self) -> None:
        source = 'skill("d").\nskill_evidence_text("d", "any text").\n'
        result = align_evidence_text(source, ())
        self.assertEqual(len(result.alignments), 1)
        self.assertFalse(result.alignments[0].matched)
        self.assertIsNone(result.alignments[0].evidence_id)

    def test_unmatched_alignment_records_no_evidence_id(self) -> None:
        unit = _unit(1, "completely unrelated content")
        source = 'skill("d").\nskill_evidence_text("d", "xyz qwerty").\n'
        result = align_evidence_text(source, (unit,))
        self.assertEqual(len(result.alignments), 1)
        self.assertFalse(result.alignments[0].matched)
        self.assertIsNone(result.alignments[0].evidence_id)

    def test_unmatched_alignment_excluded_from_normalized_facts(self) -> None:
        unit = _unit(1, "completely unrelated content")
        source = 'skill("d").\nskill_evidence_text("d", "xyz qwerty").\n'
        result = align_evidence_text(source, (unit,))
        self.assertEqual(result.normalized_facts, ())

    def test_reference_unit_coverage_half_when_one_of_two_matched(self) -> None:
        u1 = _unit(1, "alpha beta gamma delta")
        u2 = _unit(2, "zeta eta theta iota")
        source = 'skill("d").\nskill_evidence_text("d", "alpha beta gamma delta").\n'
        result = align_evidence_text(source, (u1, u2))
        self.assertAlmostEqual(result.reference_unit_coverage, 0.5, places=6)


class ScoreAndTokenEdgeCaseTests(unittest.TestCase):
    def test_tokens_mixes_cjk_and_latin(self) -> None:
        from semia_core.evidence import _tokens

        self.assertEqual(_tokens("foo 中文 bar"), ["foo", "中", "文", "bar"])

    def test_score_identical_text_returns_one(self) -> None:
        self.assertEqual(_score("hello world stuff", "hello world stuff"), 1.0)

    def test_score_disjoint_latin_tokens_returns_zero(self) -> None:
        self.assertEqual(_score("apple banana cherry", "dog elephant frog"), 0.0)

    def test_score_disjoint_cjk_returns_zero(self) -> None:
        self.assertEqual(_score("一二三", "四五六"), 0.0)


class ValueAllowedActionReferenceTests(unittest.TestCase):
    """Cover SDL017 / SDL018 — `value_*_allowed_action` reference checks.

    These rules guard against typos in policy facts: a fact that grants a
    value or secret access to a non-existent action would silently never
    fire. Without this check, rule authors would be unaware their policy
    is dead.
    """

    def test_value_sensitive_allowed_action_undeclared_value_emits_sdl017(self) -> None:
        bad = """
        skill("demo").
        action("act", "demo").
        value("v_ok", "act", "param").
        value_sensitive_allowed_action("v_missing", "act").
        """
        result = check_program(bad)
        codes = {issue.code for issue in result.errors}
        self.assertIn("SDL017", codes)

    def test_value_sensitive_allowed_action_undeclared_action_emits_sdl018(self) -> None:
        bad = """
        skill("demo").
        action("act", "demo").
        value("v_ok", "act", "param").
        value_sensitive_allowed_action("v_ok", "act_missing").
        """
        result = check_program(bad)
        codes = {issue.code for issue in result.errors}
        self.assertIn("SDL018", codes)

    def test_value_secret_allowed_action_undeclared_value_emits_sdl017(self) -> None:
        bad = """
        skill("demo").
        action("act", "demo").
        value("v_ok", "act", "param").
        value_secret_allowed_action("v_missing", "act").
        """
        result = check_program(bad)
        codes = {issue.code for issue in result.errors}
        self.assertIn("SDL017", codes)

    def test_value_secret_allowed_action_undeclared_action_emits_sdl018(self) -> None:
        bad = """
        skill("demo").
        action("act", "demo").
        value("v_ok", "act", "param").
        value_secret_allowed_action("v_ok", "act_missing").
        """
        result = check_program(bad)
        codes = {issue.code for issue in result.errors}
        self.assertIn("SDL018", codes)

    def test_well_formed_allowed_action_facts_emit_no_reference_issues(self) -> None:
        # Positive control — confirms the validators do not over-fire on
        # legal input, so the failures above are real signal.
        ok = """
        skill("demo").
        action("act", "demo").
        value("v_ok", "act", "param").
        value_sensitive_allowed_action("v_ok", "act").
        value_secret_allowed_action("v_ok", "act").
        """
        result = check_program(ok)
        codes = {issue.code for issue in result.errors}
        self.assertNotIn("SDL017", codes)
        self.assertNotIn("SDL018", codes)


class FactParserMalformedInputTests(unittest.TestCase):
    """Cover the parse-error paths in `parse_facts` / `parse_fact_line` /
    `_parse_args`. Malformed facts can arrive from synthesis output, manual
    edits, or hostile prompts; we need both strict mode (raise) and
    non-strict mode (capture as `__parse_error__`) to behave predictably.
    """

    def test_unknown_relation_lands_in_unknown_facts(self) -> None:
        program = parse_facts('not_in_schema("foo", "bar").\n')
        relations = {fact.relation for fact in program.unknown_facts}
        self.assertIn("not_in_schema", relations)

    def test_missing_trailing_dot_captured_as_parse_error_in_lenient_mode(self) -> None:
        program = parse_facts('skill("demo")\n')
        self.assertTrue(any(f.relation == "__parse_error__" for f in program.unknown_facts))

    def test_missing_trailing_dot_raises_in_strict_mode(self) -> None:
        from semia_core.facts import FactParseError

        with self.assertRaises(FactParseError):
            parse_facts('skill("demo")\n', strict=True)

    def test_missing_paren_shape_raises_parse_error(self) -> None:
        from semia_core.facts import FactParseError

        with self.assertRaises(FactParseError):
            parse_facts("skill.\n", strict=True)

    def test_invalid_relation_name_raises(self) -> None:
        from semia_core.facts import FactParseError

        with self.assertRaises(FactParseError):
            parse_facts('1bad("a").\n', strict=True)

    def test_empty_argument_list_parses_to_zero_args(self) -> None:
        from semia_core.facts import parse_fact_line

        fact = parse_fact_line("flag().")
        self.assertEqual(fact.relation, "flag")
        self.assertEqual(fact.args, ())

    def test_unterminated_quoted_string_raises(self) -> None:
        from semia_core.facts import FactParseError

        with self.assertRaises(FactParseError):
            parse_facts('skill("unterminated).\n', strict=True)


if __name__ == "__main__":
    unittest.main()
