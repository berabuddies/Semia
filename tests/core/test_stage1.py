from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "packages/semia-core/src"))

from semia_core.pipeline import prepare
from semia_core.stage1 import build_stage1_bundle, render_evidence_units


class Stage1Tests(unittest.TestCase):
    def test_build_stage1_bundle_includes_inventory_and_source_map(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "SKILL.md").write_text(
                "---\nname: demo\n---\n# Demo Skill\n\n- Read a local file.\n- Send no network traffic.\n",
                encoding="utf-8",
            )
            (root / "scripts").mkdir()
            (root / "scripts" / "helper.py").write_text("print('hello')\n", encoding="utf-8")
            (root / "data.bin").write_bytes(b"\x00\x01")

            bundle = build_stage1_bundle(root, source_id="demo")

        self.assertEqual(bundle.source.source_id, "demo")
        self.assertIn("## [Inlined Source Files]", bundle.source.inlined_text)
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


if __name__ == "__main__":
    unittest.main()
