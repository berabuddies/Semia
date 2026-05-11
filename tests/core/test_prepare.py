# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 RiemaLabs
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "packages/semia-core/src"))

from semia_core.pipeline import prepare
from semia_core.prepare import (
    _truncate_before_inlined,
    build_prepare_bundle,
    load_skill_source,
    render_evidence_units,
)


class PrepareTests(unittest.TestCase):
    def test_build_prepare_bundle_includes_inventory_and_source_map(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "SKILL.md").write_text(
                "---\nname: demo\n---\n# Demo Skill\n\n- Read a local file.\n- Send no network traffic.\n",
                encoding="utf-8",
            )
            (root / "scripts").mkdir()
            (root / "scripts" / "helper.py").write_text("print('hello')\n", encoding="utf-8")
            (root / "data.bin").write_bytes(b"\x00\x01")

            bundle = build_prepare_bundle(root, source_id="demo")

        self.assertEqual(bundle.source.source_id, "demo")
        self.assertIn("<!-- semia:inlined-source-start -->", bundle.source.inlined_text)
        self.assertGreaterEqual(len(bundle.semantic_units), 3)
        self.assertEqual(bundle.semantic_units[0].evidence_id, "su_0")
        self.assertEqual(bundle.semantic_units[0].text, "Demo Skill")
        self.assertEqual(bundle.semantic_units[0].source_file, "SKILL.md")
        inventory = {entry.path: entry for entry in bundle.source.file_inventory}
        self.assertEqual(inventory["SKILL.md"].disposition, "inlined")
        self.assertEqual(inventory["scripts/helper.py"].disposition, "inlined_source")
        self.assertEqual(inventory["scripts/helper.py"].language, "python")
        self.assertEqual(inventory["data.bin"].disposition, "excluded")
        self.assertTrue(any(entry.source_file == "SKILL.md" and entry.source_line_start == 1 for entry in bundle.source.source_map))
        self.assertTrue(
            any(
                entry.source_file == "scripts/helper.py"
                and entry.source_line_start == 1
                and entry.source_line_end == 1
                for entry in bundle.source.source_map
            )
        )
        self.assertIn('evidence_unit("su_0", 0).', render_evidence_units(bundle.semantic_units))

    def test_prepare_writes_file_inventory_and_source_map(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            skill_dir = root / "skill"
            out_dir = root / "run"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text("# Demo Skill\n\n- Read a local file.\n", encoding="utf-8")
            (skill_dir / "scripts").mkdir()
            (skill_dir / "scripts" / "helper.py").write_text("print('hello')\n", encoding="utf-8")

            prepare(skill_dir, out_dir=out_dir)

            metadata = json.loads((out_dir / "prepare_metadata.json").read_text(encoding="utf-8"))
            units = json.loads((out_dir / "prepare_units.json").read_text(encoding="utf-8"))

        self.assertIn("file_inventory", metadata["source"])
        self.assertIn("source_map", metadata["source"])
        self.assertIn("file_inventory", units)
        self.assertIn("source_map", units)
        self.assertTrue(any(entry["path"] == "SKILL.md" for entry in metadata["source"]["file_inventory"]))
        self.assertTrue(any(entry["source_file"] == "scripts/helper.py" for entry in metadata["source"]["source_map"]))
        self.assertTrue(any(entry["path"] == "scripts/helper.py" for entry in units["file_inventory"]))

    def test_dotfile_env_appears_in_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "SKILL.md").write_text("# Demo\n", encoding="utf-8")
            (root / ".env").write_text("SECRET=abc\n", encoding="utf-8")

            source = load_skill_source(root)

        inventory = {entry.path: entry for entry in source.file_inventory}
        self.assertIn(".env", inventory)
        # `.env` has no extension supported in the text allowlist, so it is recorded
        # but excluded from inlining. The key behavior change is that it is no
        # longer hidden from the inventory entirely.
        self.assertEqual(inventory[".env"].disposition, "excluded")

    def test_github_workflow_yaml_is_inlined(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "SKILL.md").write_text("# Demo\n", encoding="utf-8")
            workflows = root / ".github" / "workflows"
            workflows.mkdir(parents=True)
            (workflows / "lint.yml").write_text("name: lint\non: push\n", encoding="utf-8")

            source = load_skill_source(root)

        inventory = {entry.path: entry for entry in source.file_inventory}
        self.assertIn(".github/workflows/lint.yml", inventory)
        self.assertEqual(
            inventory[".github/workflows/lint.yml"].disposition, "inlined_source"
        )
        self.assertIn("name: lint", source.inlined_text)

    def test_skip_dirs_always_are_pruned(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "SKILL.md").write_text("# Demo\n", encoding="utf-8")
            (root / "node_modules").mkdir()
            (root / "node_modules" / "pkg.js").write_text("// trash\n", encoding="utf-8")
            (root / ".git").mkdir()
            (root / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
            (root / "dist").mkdir()
            (root / "dist" / "bundle.js").write_text("// build output\n", encoding="utf-8")

            source = load_skill_source(root)

        paths = {entry.path for entry in source.file_inventory}
        self.assertNotIn("node_modules/pkg.js", paths)
        self.assertNotIn(".git/HEAD", paths)
        self.assertNotIn("dist/bundle.js", paths)

    def test_source_hash_changes_when_env_file_changes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "SKILL.md").write_text("# Demo\n", encoding="utf-8")
            (root / ".env").write_text("SECRET=abc\n", encoding="utf-8")

            first = load_skill_source(root)
            (root / ".env").write_text("SECRET=abcdef\n", encoding="utf-8")
            second = load_skill_source(root)

        self.assertNotEqual(first.source_hash, second.source_hash)

    def test_oversized_supported_file_is_excluded(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "SKILL.md").write_text("# Demo\n", encoding="utf-8")
            (root / "huge.py").write_bytes(b"x" * (1_000_001))

            source = load_skill_source(root)

        inventory = {entry.path: entry for entry in source.file_inventory}
        self.assertEqual(inventory["huge.py"].disposition, "excluded")

    def test_truncate_recognizes_new_sentinel(self) -> None:
        body = "# Heading\n\nbody text\n"
        text = body + "<!-- semia:inlined-source-start -->\n\n### foo.py\n```text\nprint(1)\n```\n"
        truncated = _truncate_before_inlined(text)
        self.assertEqual(truncated, body)

    def test_truncate_recognizes_old_sentinel_for_backcompat(self) -> None:
        body = "# Heading\n\nbody text\n"
        text = body + "## [Inlined Source Files]\n\n### foo.py\n"
        truncated = _truncate_before_inlined(text)
        self.assertEqual(truncated, body)

    def test_truncate_picks_first_sentinel_when_both_present(self) -> None:
        prefix = "# Heading\n\nintro\n"
        middle_old = "## [Inlined Source Files] mention in prose\n\n"
        suffix_new = "<!-- semia:inlined-source-start -->\n\n### foo.py\n"
        text = prefix + middle_old + suffix_new
        truncated = _truncate_before_inlined(text)
        self.assertEqual(truncated, prefix)


if __name__ == "__main__":
    unittest.main()
