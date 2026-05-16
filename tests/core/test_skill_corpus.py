# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 RiemaLabs
"""Corpus-level smoke tests over the dev_dataset SKILL.md fixtures.

These tests exercise the deterministic prepare pipeline against a snapshot of
~50 real public agent skills. The intent is to catch crashes and silent
behavior regressions in `build_prepare_bundle` and the wider
`prepare -> extract_baseline -> check_facts -> detect` flow — not to assert
specific findings or program validity, which depend on per-skill content.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "packages/semia-core/src"))

from semia_core.prepare import build_prepare_bundle


class SkillCorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixtures_root = Path(__file__).resolve().parents[1] / "fixtures" / "skills"
        cls.skill_dirs = sorted(
            p for p in cls.fixtures_root.rglob("*") if p.is_dir() and (p / "SKILL.md").exists()
        )

    def test_corpus_directory_present(self) -> None:
        self.assertGreater(len(self.skill_dirs), 30, "expected 30+ fixture skill directories")

    def test_every_skill_prepares_without_error(self) -> None:
        """build_prepare_bundle handles every dev-dataset skill without exception."""
        failures: list[str] = []
        for d in self.skill_dirs:
            try:
                bundle = build_prepare_bundle(d)
                if len(bundle.semantic_units) == 0:
                    failures.append(f"{d.relative_to(self.fixtures_root)}: 0 semantic units")
                if not bundle.source.source_hash:
                    failures.append(f"{d.relative_to(self.fixtures_root)}: empty source_hash")
            except Exception as exc:  # noqa: BLE001 - we want every failure mode
                failures.append(f"{d.relative_to(self.fixtures_root)}: {type(exc).__name__}: {exc}")
        self.assertFalse(failures, "\n".join(failures))

    def test_corpus_pipeline_end_to_end_sample(self) -> None:
        """Run prepare -> extract_baseline -> check_facts -> detect on a small sample.

        Uses 5 skills (first by sort order) and verifies the pipeline runs to
        completion without raising, regardless of program_valid outcome.
        """
        from semia_core import check_facts, detect, extract_baseline, prepare

        for d in self.skill_dirs[:5]:
            with tempfile.TemporaryDirectory() as td:
                run_dir = Path(td)
                prepare(d, out_dir=run_dir)
                extract_baseline(run_dir)
                check_facts(run_dir)
                # Detect may report unavailable backend in some envs; just confirm it runs.
                result = detect(run_dir)
                self.assertIn(result["status"], {"ok", "failed", "unavailable"})

    def test_source_hashes_are_deterministic(self) -> None:
        """Running build_prepare_bundle twice yields the same source_hash."""
        for d in self.skill_dirs[:5]:
            b1 = build_prepare_bundle(d)
            b2 = build_prepare_bundle(d)
            self.assertEqual(b1.source.source_hash, b2.source.source_hash, str(d))

    def test_corpus_unit_type_distribution(self) -> None:
        """Print a summary of unit types across the corpus. Always passes;
        runs only when SEMIA_CORPUS_VERBOSE=1 to keep test output small."""
        if os.environ.get("SEMIA_CORPUS_VERBOSE") != "1":
            self.skipTest("set SEMIA_CORPUS_VERBOSE=1 to view distribution")
        from collections import Counter

        counter: Counter = Counter()
        for d in self.skill_dirs:
            try:
                bundle = build_prepare_bundle(d)
                for unit in bundle.semantic_units:
                    counter[unit.unit_type] += 1
            except Exception:
                continue
        for unit_type, count in counter.most_common():
            print(f"  {unit_type}: {count}")


if __name__ == "__main__":
    unittest.main()
