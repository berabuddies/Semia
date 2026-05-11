# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 berabuddies
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "packages/semia-core/src"))

from semia_core.pipeline import prepare
from semia_core.prepare import (
    build_prepare_bundle,
    load_skill_source,
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
        heading = next(u for u in bundle.semantic_units if u.unit_type == "heading")
        self.assertEqual(heading.text, "Demo Skill")
        self.assertEqual(heading.source_file, "SKILL.md")
        inventory = {entry.path: entry for entry in bundle.source.file_inventory}
        self.assertEqual(inventory["SKILL.md"].disposition, "inlined")
        self.assertEqual(inventory["scripts/helper.py"].disposition, "inlined_source")
        self.assertEqual(inventory["scripts/helper.py"].language, "python")
        self.assertEqual(inventory["data.bin"].disposition, "excluded")
        self.assertTrue(
            any(
                entry.source_file == "SKILL.md" and entry.source_line_start == 1
                for entry in bundle.source.source_map
            )
        )
        self.assertTrue(
            any(
                entry.source_file == "scripts/helper.py"
                and entry.source_line_start == 1
                and entry.source_line_end == 1
                for entry in bundle.source.source_map
            )
        )
        self.assertIn('evidence_unit("su_0", 0).', bundle.evidence_unit_facts())

    def test_prepare_writes_file_inventory_and_source_map(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            skill_dir = root / "skill"
            out_dir = root / "run"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                "# Demo Skill\n\n- Read a local file.\n", encoding="utf-8"
            )
            (skill_dir / "scripts").mkdir()
            (skill_dir / "scripts" / "helper.py").write_text("print('hello')\n", encoding="utf-8")

            prepare(skill_dir, out_dir=out_dir)

            metadata = json.loads((out_dir / "prepare_metadata.json").read_text(encoding="utf-8"))
            units = json.loads((out_dir / "prepare_units.json").read_text(encoding="utf-8"))

        self.assertIn("file_inventory", metadata["source"])
        self.assertIn("source_map", metadata["source"])
        self.assertIn("file_inventory", units)
        self.assertIn("source_map", units)
        self.assertTrue(
            any(entry["path"] == "SKILL.md" for entry in metadata["source"]["file_inventory"])
        )
        self.assertTrue(
            any(
                entry["source_file"] == "scripts/helper.py"
                for entry in metadata["source"]["source_map"]
            )
        )
        self.assertTrue(
            any(entry["path"] == "scripts/helper.py" for entry in units["file_inventory"])
        )

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
        self.assertEqual(inventory[".github/workflows/lint.yml"].disposition, "inlined_source")
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


class StructuredSourceUnitTests(unittest.TestCase):
    def _bundle(self, files: dict[str, str]):
        return _bundle_for(files)

    def test_python_function_emits_function_and_statement_units(self) -> None:
        bundle = self._bundle(
            {
                "SKILL.md": "# Demo\n",
                "audit.py": "def login(user):\n    a = 1\n    b = 2\n    return a + b\n",
            }
        )
        types = [u.unit_type for u in bundle.semantic_units if u.source_file == "audit.py"]
        self.assertEqual(types.count("py_def"), 1)
        self.assertEqual(types.count("py_statement"), 3)

    def test_python_class_emits_class_and_method_units(self) -> None:
        bundle = self._bundle(
            {
                "SKILL.md": "# Demo\n",
                "foo.py": (
                    "class Foo:\n"
                    "    def m1(self):\n        return 1\n"
                    "    def m2(self, x):\n        return x + 1\n"
                ),
            }
        )
        types = [u.unit_type for u in bundle.semantic_units if u.source_file == "foo.py"]
        self.assertEqual(types.count("py_class_def"), 1)
        self.assertEqual(types.count("py_method_def"), 2)

    def test_python_imports_grouped_into_one_unit(self) -> None:
        bundle = self._bundle(
            {
                "SKILL.md": "# Demo\n",
                "foo.py": (
                    "import os\nimport sys\nfrom pathlib import Path\n\ndef foo():\n    pass\n"
                ),
            }
        )
        py_units = [u for u in bundle.semantic_units if u.source_file == "foo.py"]
        imports = [u for u in py_units if u.unit_type == "py_import_block"]
        funcs = [u for u in py_units if u.unit_type == "py_def"]
        self.assertEqual(len(imports), 1)
        self.assertEqual(len(funcs), 1)
        self.assertIn("from pathlib import Path", imports[0].text)

    def test_python_syntax_error_falls_back_to_fenced_code(self) -> None:
        bundle = self._bundle(
            {
                "SKILL.md": "# Demo\n",
                "broken.py": "def foo(:\n    pass\n",
            }
        )
        broken = [u for u in bundle.semantic_units if u.source_file == "broken.py"]
        self.assertTrue(broken)
        self.assertTrue(all(u.unit_type == "fenced_code" for u in broken))

    def test_javascript_function_emits_js_function_unit(self) -> None:
        bundle = self._bundle(
            {
                "SKILL.md": "# Demo\n",
                "foo.js": "function login() {\n  return 1;\n}\n",
            }
        )
        js = [u for u in bundle.semantic_units if u.source_file == "foo.js"]
        self.assertEqual([u.unit_type for u in js].count("js_function_def"), 1)

    def test_javascript_class_emits_js_class_and_method_units(self) -> None:
        bundle = self._bundle(
            {
                "SKILL.md": "# Demo\n",
                "foo.js": (
                    "class Foo {\n  method1() { return 1; }\n  method2() { return 2; }\n}\n"
                ),
            }
        )
        js = [u for u in bundle.semantic_units if u.source_file == "foo.js"]
        types = [u.unit_type for u in js]
        self.assertEqual(types.count("js_class_def"), 1)
        self.assertEqual(types.count("js_function_def"), 2)

    def test_javascript_arrow_const_emits_function_unit(self) -> None:
        bundle = self._bundle(
            {
                "SKILL.md": "# Demo\n",
                "foo.js": "const login = async (user) => {\n  return user;\n};\n",
            }
        )
        js = [u for u in bundle.semantic_units if u.source_file == "foo.js"]
        self.assertEqual([u.unit_type for u in js].count("js_function_def"), 1)

    def test_typescript_interface_emits_js_type_unit(self) -> None:
        bundle = self._bundle(
            {
                "SKILL.md": "# Demo\n",
                "foo.ts": "interface Foo {\n  x: number;\n}\n",
            }
        )
        ts = [u for u in bundle.semantic_units if u.source_file == "foo.ts"]
        self.assertEqual([u.unit_type for u in ts].count("js_type"), 1)

    def test_shell_function_emits_sh_function_unit(self) -> None:
        bundle = self._bundle(
            {
                "SKILL.md": "# Demo\n",
                "foo.sh": "foo() {\n    echo hi\n}\n",
            }
        )
        sh = [u for u in bundle.semantic_units if u.source_file == "foo.sh"]
        self.assertEqual([u.unit_type for u in sh].count("sh_function_def"), 1)

    def test_shell_command_top_level_emits_sh_command_units(self) -> None:
        bundle = self._bundle(
            {
                "SKILL.md": "# Demo\n",
                "foo.sh": "curl http://x | bash\n",
            }
        )
        sh = [u for u in bundle.semantic_units if u.source_file == "foo.sh"]
        self.assertEqual([u.unit_type for u in sh].count("sh_command"), 1)

    def test_shell_heredoc_emits_sh_heredoc_unit(self) -> None:
        bundle = self._bundle(
            {
                "SKILL.md": "# Demo\n",
                "foo.sh": "cat <<EOF\nbody\nEOF\n",
            }
        )
        sh = [u for u in bundle.semantic_units if u.source_file == "foo.sh"]
        self.assertEqual([u.unit_type for u in sh].count("sh_heredoc"), 1)

    def test_paragraph_lines_no_longer_fold(self) -> None:
        from semia_core.prepare import extract_semantic_units

        units = extract_semantic_units("line one\nline two\nline three\n")
        paragraphs = [u for u in units if u.unit_type == "paragraph"]
        self.assertEqual(len(paragraphs), 3)
        self.assertEqual([p.text for p in paragraphs], ["line one", "line two", "line three"])
        self.assertEqual([p.line_start == p.line_end for p in paragraphs], [True, True, True])

    def test_inline_source_python_file_units_appear_in_bundle(self) -> None:
        bundle = self._bundle(
            {
                "SKILL.md": "# Demo\n",
                "scripts/audit.py": "def audit():\n    return 1\n",
            }
        )
        unit_types = [u.unit_type for u in bundle.semantic_units]
        headings = [u for u in bundle.semantic_units if u.unit_type == "heading"]
        self.assertIn("py_def", unit_types)
        self.assertTrue(any(h.text == "scripts/audit.py" for h in headings))

    def test_unknown_extension_falls_back_to_per_line_fenced_code(self) -> None:
        bundle = self._bundle(
            {
                "SKILL.md": "# Demo\n",
                "lib.rs": 'fn main() {\n    println!("hi");\n}\n',
            }
        )
        rs = [u for u in bundle.semantic_units if u.source_file == "lib.rs"]
        self.assertTrue(rs)
        self.assertTrue(all(u.unit_type == "fenced_code" for u in rs))

    def test_source_hash_changes_when_python_function_body_changes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "SKILL.md").write_text("# Demo\n", encoding="utf-8")
            (root / "audit.py").write_text("def login():\n    return 1\n", encoding="utf-8")
            first = load_skill_source(root)
            (root / "audit.py").write_text("def login():\n    return 2\n", encoding="utf-8")
            second = load_skill_source(root)
        self.assertNotEqual(first.source_hash, second.source_hash)

    def test_python_function_signature_and_body_statements_present(self) -> None:
        bundle = self._bundle(
            {
                "SKILL.md": "# Demo\n",
                "foo.py": "def step():\n    a = 1\n    b = 2\n    return a + b\n",
            }
        )
        py_units = [u for u in bundle.semantic_units if u.source_file == "foo.py"]
        defs = [u for u in py_units if u.unit_type == "py_def"]
        statements = [u for u in py_units if u.unit_type == "py_statement"]
        self.assertEqual(len(defs), 1)
        self.assertIn("def step():", defs[0].text)
        self.assertTrue(any("return a + b" in s.text for s in statements))

    def test_python_imports_after_docstring_grouped_into_block(self) -> None:
        """Imports after a module docstring still get grouped into a py_import_block."""
        source = '"""Module docstring."""\n\nimport os\nimport sys\nfrom pathlib import Path\n\ndef foo():\n    pass\n'
        bundle = self._bundle({"SKILL.md": "# Demo\n", "scripts/m.py": source})
        units = [u for u in bundle.semantic_units if u.unit_type == "py_import_block"]
        self.assertEqual(len(units), 1, [u.unit_type for u in bundle.semantic_units])
        self.assertIn("import os", units[0].text)
        self.assertIn("import sys", units[0].text)
        self.assertIn("from pathlib import Path", units[0].text)

    def test_python_imports_scattered_in_body_grouped_into_one_block(self) -> None:
        """All top-level imports go into ONE py_import_block, even if scattered."""
        source = "import os\n\ndef foo():\n    pass\n\nimport sys\n"
        bundle = self._bundle({"SKILL.md": "# Demo\n", "scripts/m.py": source})
        blocks = [u for u in bundle.semantic_units if u.unit_type == "py_import_block"]
        self.assertEqual(len(blocks), 1)
        self.assertIn("import os", blocks[0].text)
        self.assertIn("import sys", blocks[0].text)

    def test_python_imports_inside_conditional_not_grouped(self) -> None:
        """Imports nested inside `if` blocks are NOT in py_import_block."""
        source = "import os\n\nif True:\n    import json\n"
        bundle = self._bundle({"SKILL.md": "# Demo\n", "scripts/m.py": source})
        blocks = [u for u in bundle.semantic_units if u.unit_type == "py_import_block"]
        self.assertEqual(len(blocks), 1)
        self.assertIn("import os", blocks[0].text)
        self.assertNotIn("import json", blocks[0].text)

    def test_python_no_top_level_imports_no_block_emitted(self) -> None:
        """Files with no top-level imports produce no py_import_block."""
        source = "def foo():\n    import os\n    return os.getcwd()\n"
        bundle = self._bundle({"SKILL.md": "# Demo\n", "scripts/m.py": source})
        blocks = [u for u in bundle.semantic_units if u.unit_type == "py_import_block"]
        self.assertEqual(len(blocks), 0)

    def test_python_import_block_not_duplicated_as_statement(self) -> None:
        """Imports should NOT also appear as py_statement units."""
        source = "import os\n\ndef foo(): pass\n"
        bundle = self._bundle({"SKILL.md": "# Demo\n", "scripts/m.py": source})
        statement_texts = [u.text for u in bundle.semantic_units if u.unit_type == "py_statement"]
        for t in statement_texts:
            self.assertNotIn("import os", t)


def _bundle_for(files: dict[str, str]):
    td = tempfile.TemporaryDirectory()
    root = Path(td.name)
    try:
        for rel, content in files.items():
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        return build_prepare_bundle(root)
    finally:
        td.cleanup()


class NonOverlapTests(unittest.TestCase):
    def _bundle_for(self, files: dict[str, str]):
        return _bundle_for(files)

    def test_python_function_signature_is_separate_from_body(self) -> None:
        source = "def login(user, password):\n    user_input = input()\n    os.system(user)\n"
        bundle = self._bundle_for({"SKILL.md": "# Demo\n", "scripts/m.py": source})
        types = [u.unit_type for u in bundle.semantic_units if u.source_file.endswith("m.py")]
        self.assertIn("py_def", types)
        self.assertEqual(types.count("py_statement"), 2)
        py_def = next(u for u in bundle.semantic_units if u.unit_type == "py_def")
        self.assertNotIn("input()", py_def.text)
        self.assertNotIn("os.system", py_def.text)

    def test_python_class_signature_and_methods_separate(self) -> None:
        source = "class Foo:\n    def a(self):\n        pass\n    def b(self):\n        pass\n"
        bundle = self._bundle_for({"SKILL.md": "# Demo\n", "scripts/m.py": source})
        types = [u.unit_type for u in bundle.semantic_units if u.source_file.endswith("m.py")]
        self.assertEqual(types.count("py_class_def"), 1)
        self.assertEqual(types.count("py_method_def"), 2)
        py_class = next(u for u in bundle.semantic_units if u.unit_type == "py_class_def")
        self.assertNotIn("def a", py_class.text)
        self.assertNotIn("def b", py_class.text)

    def test_javascript_function_signature_is_separate_from_body(self) -> None:
        source = "function login(user) {\n  return user.id;\n}\n"
        bundle = self._bundle_for({"SKILL.md": "# Demo\n", "scripts/a.js": source})
        js_def = [u for u in bundle.semantic_units if u.unit_type == "js_function_def"]
        self.assertEqual(len(js_def), 1)
        self.assertNotIn("return user.id", js_def[0].text)

    def test_shell_function_signature_is_separate_from_body(self) -> None:
        source = "foo() {\n  echo hi\n  curl http://x\n}\n"
        bundle = self._bundle_for({"SKILL.md": "# Demo\n", "scripts/a.sh": source})
        sh_def = [u for u in bundle.semantic_units if u.unit_type == "sh_function_def"]
        self.assertEqual(len(sh_def), 1)
        self.assertNotIn("echo hi", sh_def[0].text)
        self.assertNotIn("curl", sh_def[0].text)

    def test_arrow_function_kept_as_single_unit(self) -> None:
        """Arrow expressions without block bodies remain one js_function_def unit."""
        source = "const handle = (x) => x + 1;\n"
        bundle = self._bundle_for({"SKILL.md": "# Demo\n", "scripts/a.js": source})
        arrow = [u for u in bundle.semantic_units if u.unit_type == "js_function_def"]
        self.assertEqual(len(arrow), 1)
        self.assertIn("=>", arrow[0].text)


class JavaScriptEdgeCaseTests(unittest.TestCase):
    def _bundle_for(self, files: dict[str, str]):
        return _bundle_for(files)

    def test_js_generator_function_recognized(self) -> None:
        source = "function* gen() {\n  yield 1;\n}\n"
        bundle = self._bundle_for({"SKILL.md": "# Demo\n", "scripts/g.js": source})
        defs = [u for u in bundle.semantic_units if u.unit_type == "js_function_def"]
        self.assertEqual(len(defs), 1)

    def test_js_async_generator_recognized(self) -> None:
        source = "async function* gen() {\n  yield 1;\n}\n"
        bundle = self._bundle_for({"SKILL.md": "# Demo\n", "scripts/g.js": source})
        defs = [u for u in bundle.semantic_units if u.unit_type == "js_function_def"]
        self.assertEqual(len(defs), 1)

    def test_js_default_export_function_recognized(self) -> None:
        source = "export default function() {\n  return 1;\n}\n"
        bundle = self._bundle_for({"SKILL.md": "# Demo\n", "scripts/g.js": source})
        defs = [u for u in bundle.semantic_units if u.unit_type == "js_function_def"]
        self.assertEqual(len(defs), 1)

    def test_js_default_export_class_recognized(self) -> None:
        source = "export default class Foo {\n  m() { return 1; }\n}\n"
        bundle = self._bundle_for({"SKILL.md": "# Demo\n", "scripts/g.js": source})
        classes = [u for u in bundle.semantic_units if u.unit_type == "js_class_def"]
        self.assertEqual(len(classes), 1)

    def test_js_class_with_class_fields(self) -> None:
        source = "class Foo {\n  x = 5;\n  method() {\n    return this.x;\n  }\n}\n"
        bundle = self._bundle_for({"SKILL.md": "# Demo\n", "scripts/g.js": source})
        js_units = [u for u in bundle.semantic_units if u.source_file.endswith("g.js")]
        types = [u.unit_type for u in js_units]
        self.assertEqual(types.count("js_class_def"), 1)
        self.assertEqual(types.count("js_function_def"), 1)
        self.assertTrue(any(u.unit_type == "js_statement" and "x = 5" in u.text for u in js_units))

    def test_js_jsx_inside_expression_does_not_break_parsing(self) -> None:
        source = 'const Card = (props) => <div className="card">{props.text}</div>;\n'
        bundle = self._bundle_for({"SKILL.md": "# Demo\n", "scripts/g.jsx": source})
        defs = [u for u in bundle.semantic_units if u.unit_type == "js_function_def"]
        self.assertEqual(len(defs), 1)

    def test_js_minified_falls_back_to_fenced_code(self) -> None:
        source = "var a=1;" * 100 + "\n"
        self.assertGreater(len(source), 500)
        self.assertEqual(len(source.splitlines()), 1)
        bundle = self._bundle_for({"SKILL.md": "# Demo\n", "scripts/min.js": source})
        js_units = [u for u in bundle.semantic_units if u.source_file.endswith("min.js")]
        self.assertTrue(js_units)
        self.assertTrue(all(u.unit_type == "fenced_code" for u in js_units))


class SourceRelativeLineNumberTests(unittest.TestCase):
    def _bundle_for(self, files: dict[str, str]):
        return _bundle_for(files)

    def test_python_function_line_numbers_are_source_relative(self) -> None:
        """A function on line 5 of foo.py has line_start=5, regardless of where the .py is inlined."""
        source = "\n\n\n\ndef foo():\n    pass\n"
        bundle = self._bundle_for(
            {"SKILL.md": "# Demo\n# Demo\n# Demo\n" * 10, "scripts/m.py": source}
        )
        py_def = next(u for u in bundle.semantic_units if u.unit_type == "py_def")
        self.assertEqual(py_def.source_file, "scripts/m.py")
        self.assertEqual(py_def.line_start, 5)

    def test_js_function_line_numbers_are_source_relative(self) -> None:
        source = "\n\n\nfunction foo() {\n  return 1;\n}\n"
        bundle = self._bundle_for({"SKILL.md": "# Demo\n" * 20, "scripts/m.js": source})
        js_def = next(u for u in bundle.semantic_units if u.unit_type == "js_function_def")
        self.assertEqual(js_def.source_file, "scripts/m.js")
        self.assertEqual(js_def.line_start, 4)

    def test_shell_function_line_numbers_are_source_relative(self) -> None:
        source = "\n\nfoo() {\n  echo hi\n}\n"
        bundle = self._bundle_for({"SKILL.md": "# Demo\n" * 20, "scripts/m.sh": source})
        sh_def = next(u for u in bundle.semantic_units if u.unit_type == "sh_function_def")
        self.assertEqual(sh_def.source_file, "scripts/m.sh")
        self.assertEqual(sh_def.line_start, 3)


class MarkdownAstParserTests(unittest.TestCase):
    def _units(self, source: str) -> list:
        from semia_core.prepare import extract_semantic_units

        return extract_semantic_units(source)

    def _nodes(self, source: str):
        from semia_core.parsers.markdown import parse_markdown

        return parse_markdown(source)

    def test_atx_heading_levels_distinct(self) -> None:
        nodes = self._nodes("# h1\n## h2\n### h3\n")
        headings = [n for n in nodes if n.type == "heading"]
        self.assertEqual(len(headings), 3)
        self.assertEqual([h.level for h in headings], [1, 2, 3])
        units = self._units("# h1\n## h2\n### h3\n")
        heading_units = [u for u in units if u.unit_type == "heading"]
        self.assertEqual(len(heading_units), 3)
        self.assertEqual([u.text for u in heading_units], ["h1", "h2", "h3"])

    def test_setext_heading_recognized(self) -> None:
        nodes = self._nodes("Title\n=====\nSub\n-----\n")
        headings = [n for n in nodes if n.type == "heading"]
        self.assertEqual([h.level for h in headings], [1, 2])
        self.assertEqual([h.text for h in headings], ["Title", "Sub"])
        units = self._units("Title\n=====\nSub\n-----\n")
        paragraphs = [u for u in units if u.unit_type == "paragraph"]
        self.assertEqual(paragraphs, [])

    def test_fenced_code_preserves_info_string(self) -> None:
        nodes = self._nodes("```python\ndef foo(): pass\n```\n")
        code_blocks = [n for n in nodes if n.type == "code_block"]
        self.assertEqual(len(code_blocks), 1)
        self.assertEqual(code_blocks[0].info, "python")
        units = self._units("```python\ndef foo(): pass\n```\n")
        self.assertTrue(any(u.unit_type == "fenced_code" for u in units))

    def test_indented_code_block_recognized(self) -> None:
        source = "Paragraph.\n\n    code line 1\n    code line 2\n"
        nodes = self._nodes(source)
        code_blocks = [n for n in nodes if n.type == "code_block"]
        self.assertEqual(len(code_blocks), 1)
        self.assertEqual(code_blocks[0].info, "")
        units = self._units(source)
        fenced = [u for u in units if u.unit_type == "fenced_code"]
        self.assertEqual([u.text for u in fenced], ["code line 1", "code line 2"])

    def test_nested_list_items_each_become_units(self) -> None:
        source = "- top one\n  - nested A\n  - nested B\n- top two\n"
        units = self._units(source)
        list_items = [u for u in units if u.unit_type == "list_item"]
        self.assertEqual(len(list_items), 4)
        self.assertEqual(
            [u.text for u in list_items],
            ["top one", "nested A", "nested B", "top two"],
        )
        line_starts = [u.line_start for u in list_items]
        self.assertEqual(line_starts, [1, 2, 3, 4])

    def test_blockquote_runs_emit_per_line_units(self) -> None:
        units = self._units("> first\n> second\n")
        bq = [u for u in units if u.unit_type == "blockquote"]
        self.assertEqual([u.text for u in bq], ["first", "second"])
        self.assertEqual([u.line_start for u in bq], [1, 2])

    def test_table_with_separator_emits_two_row_units(self) -> None:
        source = "| h1 | h2 |\n| --- | --- |\n| a | b |\n"
        units = self._units(source)
        rows = [u for u in units if u.unit_type == "table_row"]
        self.assertEqual(len(rows), 2)
        self.assertIn("h1", rows[0].text)
        self.assertIn("a", rows[1].text)

    def test_html_block_preserved(self) -> None:
        source = '<div class="warning">\n  watch out\n</div>\n'
        units = self._units(source)
        html_units = [u for u in units if u.unit_type == "html_block"]
        self.assertEqual(len(html_units), 1)
        self.assertIn("watch out", html_units[0].text)
        self.assertIn('<div class="warning">', html_units[0].text)

    def test_html_comments_stripped(self) -> None:
        source = "# Top\n<!-- semia:inlined-source-start -->\n## Inlined\n"
        units = self._units(source)
        headings = [u for u in units if u.unit_type == "heading"]
        self.assertEqual([h.text for h in headings], ["Top", "Inlined"])
        for u in units:
            self.assertNotIn("semia:inlined-source-start", u.text)

    def test_yaml_front_matter_emits_fields_and_keeps_heading(self) -> None:
        source = "---\nname: test\n---\n# Hello\n"
        units = self._units(source)
        headings = [u for u in units if u.unit_type == "heading"]
        self.assertEqual(len(headings), 1)
        self.assertEqual(headings[0].text, "Hello")
        fields = [u for u in units if u.unit_type == "front_matter_field"]
        self.assertEqual([f.text for f in fields], ["name: test"])

    def test_paragraph_lines_remain_unfolded(self) -> None:
        units = self._units("line one\nline two\nline three\n")
        paragraphs = [u for u in units if u.unit_type == "paragraph"]
        self.assertEqual(len(paragraphs), 3)
        self.assertEqual([p.text for p in paragraphs], ["line one", "line two", "line three"])

    def test_thematic_break_not_emitted(self) -> None:
        source = "before\n\n---\n\nafter\n"
        units = self._units(source)
        # No unit should carry the bare hyphen run as text.
        self.assertFalse(any(u.text.strip() == "---" for u in units))
        paragraphs = [u for u in units if u.unit_type == "paragraph"]
        self.assertEqual([p.text for p in paragraphs], ["before", "after"])

    def test_inline_markdown_stripped(self) -> None:
        units = self._units("**bold** [link](http://x) ~~strike~~\n")
        paragraphs = [u for u in units if u.unit_type == "paragraph"]
        self.assertEqual(len(paragraphs), 1)
        self.assertEqual(paragraphs[0].text, "bold link strike")

    def test_setext_in_middle_of_doc(self) -> None:
        source = "Some intro paragraph\nHeading text\n=============\n"
        units = self._units(source)
        paragraphs = [u for u in units if u.unit_type == "paragraph"]
        headings = [u for u in units if u.unit_type == "heading"]
        self.assertEqual(len(paragraphs), 1)
        self.assertEqual(paragraphs[0].text, "Some intro paragraph")
        self.assertEqual(len(headings), 1)
        self.assertEqual(headings[0].text, "Heading text")
        ast_headings = [n for n in self._nodes(source) if n.type == "heading"]
        self.assertEqual(ast_headings[0].level, 1)

    def test_fenced_code_unclosed_treats_remainder_as_block(self) -> None:
        source = "intro\n\n```python\nstill code\nmore code\n"
        units = self._units(source)
        fenced = [u for u in units if u.unit_type == "fenced_code"]
        self.assertEqual([u.text for u in fenced], ["still code", "more code"])

    def test_inlined_source_dispatch_still_routes_to_python_parser(self) -> None:
        from semia_core.artifacts import SourceMapEntry
        from semia_core.prepare import extract_semantic_units

        source = "# Demo\n\n### foo.py\n\n```text\ndef bar():\n    return 1\n```\n"
        # The dispatch only fires when source_map confirms foo.py is an actually-
        # inlined source file (not just a tutorial heading).
        source_map = (
            SourceMapEntry(
                enriched_line_start=6,
                enriched_line_end=7,
                source_file="foo.py",
                source_line_start=1,
                source_line_end=2,
            ),
        )
        units = extract_semantic_units(source, source_map=source_map)
        py_units = [u for u in units if u.source_file == "foo.py"]
        self.assertTrue(py_units)
        self.assertTrue(any(u.unit_type.startswith("py_") for u in py_units))


class FrontMatterTests(unittest.TestCase):
    def _units(self, source: str) -> list:
        from semia_core.prepare import extract_semantic_units

        return extract_semantic_units(source)

    def test_front_matter_emits_one_unit_per_field(self) -> None:
        source = "---\nname: foo\ndescription: bar\n---\n# Title\n"
        units = self._units(source)
        fields = [u for u in units if u.unit_type == "front_matter_field"]
        self.assertEqual([f.text for f in fields], ["name: foo", "description: bar"])
        headings = [u for u in units if u.unit_type == "heading"]
        self.assertEqual(len(headings), 1)

    def test_front_matter_multiline_value_collapses(self) -> None:
        source = "---\ndescription: this is a very\n  long wrapped value\nname: foo\n---\n# T\n"
        units = self._units(source)
        fields = [u for u in units if u.unit_type == "front_matter_field"]
        self.assertEqual(len(fields), 2)
        self.assertEqual(fields[0].text, "description: this is a very long wrapped value")
        self.assertEqual(fields[1].text, "name: foo")

    def test_no_front_matter_no_units_emitted(self) -> None:
        units = self._units("# Hello\n\nplain body.\n")
        fields = [u for u in units if u.unit_type == "front_matter_field"]
        self.assertEqual(fields, [])

    def test_front_matter_line_numbers_are_one_indexed(self) -> None:
        source = "---\nname: foo\ndescription: bar\n---\n# Title\n"
        units = self._units(source)
        fields = [u for u in units if u.unit_type == "front_matter_field"]
        self.assertEqual(fields[0].line_start, 2)
        self.assertEqual(fields[1].line_start, 3)

    def test_front_matter_heading_line_numbers_source_relative(self) -> None:
        source = "---\nname: foo\n---\n# Title\n"
        units = self._units(source)
        heading = next(u for u in units if u.unit_type == "heading")
        self.assertEqual(heading.line_start, 4)


class SourceRelativeMarkdownTests(unittest.TestCase):
    def _bundle_for(self, files: dict[str, str]):
        return _bundle_for(files)

    def test_markdown_unit_line_numbers_source_relative(self) -> None:
        skill_md = "# Top\n" * 10
        notes_md = "x\n" * 2 + "## Notes Heading\n" + "y\n" * 12
        bundle = self._bundle_for(
            {
                "SKILL.md": skill_md,
                "references/notes.md": notes_md,
            }
        )
        notes_units = [u for u in bundle.semantic_units if u.source_file == "references/notes.md"]
        notes_heading = next(
            u for u in notes_units if u.unit_type == "heading" and "Notes Heading" in u.text
        )
        self.assertEqual(notes_heading.line_start, 3)

    def test_skill_md_units_remain_skill_md_relative(self) -> None:
        bundle = self._bundle_for(
            {
                "SKILL.md": "# A\n# B\n# C\n# D\n# Target\n",
                "scripts/m.py": "def foo(): pass\n",
            }
        )
        target = next(
            u for u in bundle.semantic_units if u.unit_type == "heading" and u.text == "Target"
        )
        self.assertEqual(target.source_file, "SKILL.md")
        self.assertEqual(target.line_start, 5)

    def test_code_unit_line_numbers_unchanged_after_translation(self) -> None:
        source = "\n\n\n\ndef foo():\n    pass\n"
        bundle = self._bundle_for({"SKILL.md": "# Demo\n" * 20, "scripts/m.py": source})
        py_def = next(u for u in bundle.semantic_units if u.unit_type == "py_def")
        self.assertEqual(py_def.source_file, "scripts/m.py")
        self.assertEqual(py_def.line_start, 5)


class PrepareSizeCapTests(unittest.TestCase):
    def test_prepare_rejects_skill_above_size_cap(self) -> None:
        """A skill whose inlined source exceeds 4 MB raises a clear error."""
        with tempfile.TemporaryDirectory() as td:
            d = Path(td) / "skill"
            d.mkdir()
            (d / "SKILL.md").write_text("# Big skill\n", encoding="utf-8")
            chunk = "x" * (900 * 1024)
            for i in range(6):
                (d / f"chunk_{i}.py").write_text(chunk, encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                build_prepare_bundle(d)
            self.assertIn("4", str(ctx.exception))

    def test_prepare_size_cap_env_var_override(self) -> None:
        """SEMIA_PREPARE_MAX_TOTAL_BYTES raises the cap."""
        import os

        with tempfile.TemporaryDirectory() as td:
            d = Path(td) / "skill"
            d.mkdir()
            (d / "SKILL.md").write_text("# Big\n", encoding="utf-8")
            (d / "med.py").write_text("x" * (500 * 1024), encoding="utf-8")
            bundle = build_prepare_bundle(d)
            self.assertGreater(len(bundle.semantic_units), 0)
            os.environ["SEMIA_PREPARE_MAX_TOTAL_BYTES"] = str(100 * 1024)
            try:
                with self.assertRaises(ValueError):
                    build_prepare_bundle(d)
            finally:
                os.environ.pop("SEMIA_PREPARE_MAX_TOTAL_BYTES", None)


class PythonDecoratorTests(unittest.TestCase):
    def _bundle_for(self, files: dict[str, str]):
        return _bundle_for(files)

    def test_python_decorator_emitted_as_separate_unit(self) -> None:
        source = "@cached\ndef foo():\n    return 42\n"
        bundle = self._bundle_for({"SKILL.md": "# d\n", "m.py": source})
        types = [u.unit_type for u in bundle.semantic_units if u.source_file == "m.py"]
        self.assertIn("py_decorator", types)
        self.assertIn("py_def", types)
        dec = next(u for u in bundle.semantic_units if u.unit_type == "py_decorator")
        self.assertEqual(dec.text, "@cached")
        self.assertEqual(dec.line_start, 1)

    def test_python_decorator_with_call_args_emitted_intact(self) -> None:
        source = '@app.route("/login", methods=["POST"])\ndef login():\n    pass\n'
        bundle = self._bundle_for({"SKILL.md": "# d\n", "m.py": source})
        dec = next(u for u in bundle.semantic_units if u.unit_type == "py_decorator")
        self.assertIn("@app.route", dec.text)
        self.assertIn('"/login"', dec.text)

    def test_python_multiple_decorators_each_emit_unit(self) -> None:
        source = "@a\n@b\n@c\ndef foo():\n    pass\n"
        bundle = self._bundle_for({"SKILL.md": "# d\n", "m.py": source})
        decs = [u for u in bundle.semantic_units if u.unit_type == "py_decorator"]
        self.assertEqual(len(decs), 3)
        self.assertEqual([d.text for d in decs], ["@a", "@b", "@c"])

    def test_python_class_decorator_emitted(self) -> None:
        source = "@dataclass\nclass Foo:\n    pass\n"
        bundle = self._bundle_for({"SKILL.md": "# d\n", "m.py": source})
        self.assertTrue(
            any(
                u.unit_type == "py_decorator" and u.text == "@dataclass"
                for u in bundle.semantic_units
            )
        )

    def test_python_single_line_def_no_duplicate_unit(self) -> None:
        source = "def foo(): pass\n"
        bundle = self._bundle_for({"SKILL.md": "# d\n", "m.py": source})
        units = [u for u in bundle.semantic_units if u.source_file == "m.py"]
        py_def = [u for u in units if u.unit_type == "py_def"]
        py_stmt = [u for u in units if u.unit_type == "py_statement"]
        self.assertEqual(len(py_def), 1)
        self.assertEqual(len(py_stmt), 0)


class JavaScriptImportEdgeCaseTests(unittest.TestCase):
    def _bundle_for(self, files: dict[str, str]):
        return _bundle_for(files)

    def test_js_block_comment_unterminated_swallowed_until_close(self) -> None:
        source = (
            "/* multi\nline block comment */\nimport x from 'a';\nfunction go() { return 1; }\n"
        )
        bundle = self._bundle_for({"SKILL.md": "# d\n", "s.js": source})
        js = [u for u in bundle.semantic_units if u.source_file == "s.js"]
        types = [u.unit_type for u in js]
        self.assertIn("js_import_block", types)
        self.assertIn("js_function_def", types)

    def test_js_line_comment_in_leading_imports(self) -> None:
        source = "// preamble comment\nimport a from 'a';\nfunction go() { return 1; }\n"
        bundle = self._bundle_for({"SKILL.md": "# d\n", "s.js": source})
        types = [u.unit_type for u in bundle.semantic_units if u.source_file == "s.js"]
        self.assertIn("js_import_block", types)

    def test_js_multiline_import_with_trailing_paren(self) -> None:
        source = "import {\n  a,\n  b\n} from 'mod';\nfunction go() { return 1; }\n"
        bundle = self._bundle_for({"SKILL.md": "# d\n", "s.js": source})
        imports = [u for u in bundle.semantic_units if u.unit_type == "js_import_block"]
        self.assertEqual(len(imports), 1)
        self.assertIn("from 'mod'", imports[0].text)

    def test_js_blank_line_terminates_import_collection(self) -> None:
        source = "import a from 'a';\n\nfunction go() { return 1; }\n"
        bundle = self._bundle_for({"SKILL.md": "# d\n", "s.js": source})
        types = [u.unit_type for u in bundle.semantic_units if u.source_file == "s.js"]
        self.assertIn("js_import_block", types)
        self.assertIn("js_function_def", types)

    def test_js_blank_line_inside_multiline_import_continues(self) -> None:
        source = "import {\n  a,\n\n  b\n} from 'mod';\n"
        bundle = self._bundle_for({"SKILL.md": "# d\n", "s.js": source})
        imports = [u for u in bundle.semantic_units if u.unit_type == "js_import_block"]
        self.assertEqual(len(imports), 1)


class JavaScriptScanEdgeCaseTests(unittest.TestCase):
    def _bundle_for(self, files: dict[str, str]):
        return _bundle_for(files)

    def test_js_jsx_self_closing_tag(self) -> None:
        source = "const X = () => <img src='a' />;\n"
        bundle = self._bundle_for({"SKILL.md": "# d\n", "s.jsx": source})
        defs = [u for u in bundle.semantic_units if u.unit_type == "js_function_def"]
        self.assertEqual(len(defs), 1)

    def test_js_jsx_nested_tags(self) -> None:
        source = "const Page = () => (\n  <div>\n    <span>hi</span>\n  </div>\n);\n"
        bundle = self._bundle_for({"SKILL.md": "# d\n", "p.jsx": source})
        defs = [u for u in bundle.semantic_units if u.unit_type == "js_function_def"]
        self.assertEqual(len(defs), 1)

    def test_js_jsx_inside_expression_braces(self) -> None:
        source = "function Card() {\n  return <div>{value}</div>;\n}\n"
        bundle = self._bundle_for({"SKILL.md": "# d\n", "c.jsx": source})
        defs = [u for u in bundle.semantic_units if u.unit_type == "js_function_def"]
        self.assertEqual(len(defs), 1)

    def test_js_string_with_embedded_newline_in_template(self) -> None:
        source = "function go() {\n  return `line1\nline2`;\n}\n"
        bundle = self._bundle_for({"SKILL.md": "# d\n", "s.js": source})
        defs = [u for u in bundle.semantic_units if u.unit_type == "js_function_def"]
        self.assertEqual(len(defs), 1)

    def test_js_string_continued_across_newline_with_escape(self) -> None:
        source = "var s = 'line\\\ncontinued';\nfunction go() { return 1; }\n"
        bundle = self._bundle_for({"SKILL.md": "# d\n", "s.js": source})
        defs = [u for u in bundle.semantic_units if u.unit_type == "js_function_def"]
        self.assertEqual(len(defs), 1)

    def test_js_jsx_at_start_of_file_no_prev_char(self) -> None:
        from semia_core.parsers.javascript import _looks_like_jsx_open

        self.assertTrue(_looks_like_jsx_open("<div>", 0))

    def test_js_function_without_brace_returns_caller_line(self) -> None:
        from semia_core.parsers.javascript import _build_line_starts, _find_block_end

        src = "function broken()\n"
        ls = _build_line_starts(src)
        self.assertEqual(_find_block_end(src, ls, 0), 0)

    def test_js_signature_end_no_opening_brace_returns_from_line(self) -> None:
        from semia_core.parsers.javascript import _find_signature_end

        result = _find_signature_end(["function broken()", "  body"], 0, 1)
        self.assertEqual(result, 0)

    def test_js_arrow_no_arrow_falls_back_to_statement_end(self) -> None:
        from semia_core.parsers.javascript import _build_line_starts, _find_arrow_end

        src = "const a = 1;\n"
        ls = _build_line_starts(src)
        self.assertEqual(_find_arrow_end(src, ls, 0), 0)

    def test_js_block_end_from_string_escape_and_runaway(self) -> None:
        from semia_core.parsers.javascript import _build_line_starts, _find_block_end_from

        src = "{ s = 'a\\\nb'; "
        ls = _build_line_starts(src)
        self.assertEqual(_find_block_end_from(src, ls, 0), len(ls) - 1)

    def test_js_block_end_from_balanced_string_then_close(self) -> None:
        from semia_core.parsers.javascript import _build_line_starts, _find_block_end_from

        src = "{ s = 'hi'; }\n"
        ls = _build_line_starts(src)
        self.assertEqual(_find_block_end_from(src, ls, 0), 0)

    def test_js_class_member_unknown_line_advances(self) -> None:
        source = "class Foo {\n  someRandomToken;\n  method() { return 1; }\n}\n"
        bundle = self._bundle_for({"SKILL.md": "# d\n", "c.js": source})
        js = [u for u in bundle.semantic_units if u.source_file == "c.js"]
        funcs = [u for u in js if u.unit_type == "js_function_def"]
        self.assertEqual(len(funcs), 1)

    def test_js_blank_only_long_file_returns_empty(self) -> None:
        from semia_core.parsers.javascript import parse_javascript_units

        source = "\n" * 10
        result = parse_javascript_units(source, source_file="x.js")
        self.assertEqual(result, [])

    def test_js_unterminated_string_with_newline_in_scanner(self) -> None:
        from semia_core.parsers.javascript import _scan_top_level_starts

        src = 'var s = "hello\nworld";\nfunction go() {}\n'
        positions = _scan_top_level_starts(src)
        self.assertIn(15, positions)

    def test_js_has_declarations_recognizes_function_unit(self) -> None:
        from semia_core.parsers.javascript import _has_declarations

        self.assertTrue(_has_declarations([("js_function_def", "f", 1, 1)]))
        self.assertFalse(_has_declarations([("js_statement", "x", 1, 1)]))


class MarkdownParserEdgeCaseTests(unittest.TestCase):
    def _units(self, source: str) -> list:
        from semia_core.prepare import extract_semantic_units

        return extract_semantic_units(source)

    def test_atx_heading_with_no_text_skipped(self) -> None:
        units = self._units("# \nbody\n")
        headings = [u for u in units if u.unit_type == "heading"]
        self.assertEqual(headings, [])

    def test_indented_code_with_multiple_blanks_then_more_code(self) -> None:
        source = "Para.\n\n    line one\n\n\n    line two\n"
        units = self._units(source)
        fenced = [u for u in units if u.unit_type == "fenced_code"]
        self.assertEqual([u.text for u in fenced], ["line one", "line two"])

    def test_table_head_without_pipe_not_table(self) -> None:
        source = "header\n| --- |\n"
        units = self._units(source)
        rows = [u for u in units if u.unit_type == "table_row"]
        self.assertEqual(rows, [])

    def test_table_separator_malformed_not_table(self) -> None:
        source = "| h1 | h2 |\n| ab | cd |\n"
        units = self._units(source)
        rows = [u for u in units if u.unit_type == "table_row"]
        self.assertEqual(rows, [])

    def test_table_with_internal_separator_skipped(self) -> None:
        source = "| h1 | h2 |\n| --- | --- |\n| a | b |\n| --- | --- |\n| c | d |\n"
        units = self._units(source)
        rows = [u for u in units if u.unit_type == "table_row"]
        self.assertEqual(len(rows), 3)

    def test_html_block_terminated_by_blank_line(self) -> None:
        source = "<div>\nbody line\n\nafter\n"
        units = self._units(source)
        html_units = [u for u in units if u.unit_type == "html_block"]
        self.assertEqual(len(html_units), 1)
        self.assertIn("body line", html_units[0].text)

    def test_list_followed_by_trailing_blank_lines_eof(self) -> None:
        source = "- one\n- two\n\n\n"
        units = self._units(source)
        items = [u for u in units if u.unit_type == "list_item"]
        self.assertEqual([u.text for u in items], ["one", "two"])

    def test_list_with_blank_line_then_nested_item(self) -> None:
        source = "- top\n\n  - nested\n- next\n"
        units = self._units(source)
        items = [u for u in units if u.unit_type == "list_item"]
        self.assertEqual([u.text for u in items], ["top", "nested", "next"])

    def test_flatten_to_semantic_units_returns_tuples(self) -> None:
        from semia_core.parsers.markdown import flatten_to_semantic_units, parse_markdown

        tree = parse_markdown("# Hi\n\npara\n")
        flat = flatten_to_semantic_units(tree, "foo.md")
        self.assertTrue(any(t[0] == "heading" and t[4] == "foo.md" for t in flat))
        self.assertTrue(any(t[0] == "paragraph" for t in flat))


class PythonParserEdgeCaseTests(unittest.TestCase):
    def _bundle_for(self, files: dict[str, str]):
        return _bundle_for(files)

    def test_python_null_byte_source_returns_empty(self) -> None:
        from semia_core.parsers.python import parse_python_units

        units = parse_python_units("x = 1\n\x00\n", source_file="m.py")
        self.assertEqual(units, [])

    def test_python_decorator_without_at_prefix_via_parens(self) -> None:
        source = "@(\n    deco\n)\ndef foo():\n    pass\n"
        bundle = self._bundle_for({"SKILL.md": "# d\n", "m.py": source})
        decs = [u for u in bundle.semantic_units if u.unit_type == "py_decorator"]
        self.assertEqual(len(decs), 1)
        self.assertTrue(decs[0].text.startswith("@"))

    def test_python_signature_range_no_body_returns_full_range(self) -> None:
        import ast

        from semia_core.parsers.python import _signature_range

        tree = ast.parse("def foo(): pass\n")
        func = tree.body[0]
        func.body = []
        start, end = _signature_range(func)
        self.assertEqual(start, 1)
        self.assertEqual(end, 1)

    def test_python_body_inline_with_def_empty_body(self) -> None:
        import ast

        from semia_core.parsers.python import _body_inline_with_def

        tree = ast.parse("def foo():\n    pass\n")
        func = tree.body[0]
        func.body = []
        self.assertFalse(_body_inline_with_def(func))

    def test_python_emit_decorators_skips_whitespace_only(self) -> None:
        import ast

        from semia_core.parsers.python import _emit_decorators

        tree = ast.parse("@a\ndef foo():\n    pass\n")
        func = tree.body[0]
        units: list = []
        _emit_decorators(units, func, ["", ""])
        self.assertEqual(units, [])

    def test_python_emit_inner_skips_empty_text(self) -> None:
        import ast

        from semia_core.parsers.python import _emit_inner

        tree = ast.parse("def foo():\n    pass\n")
        stmt = tree.body[0].body[0]
        units: list = []
        _emit_inner(units, stmt, ["", ""], "py_statement")
        self.assertEqual(units, [])


class ShellParserEdgeCaseTests(unittest.TestCase):
    def _bundle_for(self, files: dict[str, str]):
        return _bundle_for(files)

    def test_shell_setup_block_emitted_then_blank_breaks(self) -> None:
        source = "export PATH=/usr/bin\nMY_VAR=1\n\necho hi\n"
        bundle = self._bundle_for({"SKILL.md": "# d\n", "s.sh": source})
        sh = [u for u in bundle.semantic_units if u.source_file == "s.sh"]
        types = [u.unit_type for u in sh]
        self.assertIn("sh_setup_block", types)
        self.assertIn("sh_command", types)

    def test_shell_setup_block_source_line(self) -> None:
        source = "source ./env.sh\n. ./other.sh\necho hi\n"
        bundle = self._bundle_for({"SKILL.md": "# d\n", "s.sh": source})
        setup = [u for u in bundle.semantic_units if u.unit_type == "sh_setup_block"]
        self.assertEqual(len(setup), 1)
        self.assertIn("source", setup[0].text)

    def test_shell_function_inner_heredoc_clamped_to_body(self) -> None:
        source = "go() {\n  cat <<EOF\n  body\n}\nEOF\n"
        bundle = self._bundle_for({"SKILL.md": "# d\n", "s.sh": source})
        sh = [u for u in bundle.semantic_units if u.source_file == "s.sh"]
        types = [u.unit_type for u in sh]
        self.assertIn("sh_function_def", types)
        self.assertIn("sh_heredoc", types)

    def test_shell_brace_end_unterminated_returns_last_line(self) -> None:
        from semia_core.parsers.shell import _find_brace_end

        lines = ["foo() {", "  echo hi"]
        self.assertEqual(_find_brace_end(lines, 0), len(lines) - 1)

    def test_shell_heredoc_unterminated_returns_last_line(self) -> None:
        from semia_core.parsers.shell import _find_heredoc_end

        lines = ["body", "more body"]
        self.assertEqual(_find_heredoc_end(lines, 0, "EOF"), len(lines) - 1)


class PrepareEdgeCaseTests(unittest.TestCase):
    def test_max_inlined_bytes_invalid_env_falls_back_to_default(self) -> None:
        import os

        from semia_core.prepare import _DEFAULT_MAX_INLINED_BYTES, _max_inlined_bytes

        prior = os.environ.get("SEMIA_PREPARE_MAX_TOTAL_BYTES")
        os.environ["SEMIA_PREPARE_MAX_TOTAL_BYTES"] = "not-a-number"
        try:
            self.assertEqual(_max_inlined_bytes(), _DEFAULT_MAX_INLINED_BYTES)
        finally:
            if prior is None:
                os.environ.pop("SEMIA_PREPARE_MAX_TOTAL_BYTES", None)
            else:
                os.environ["SEMIA_PREPARE_MAX_TOTAL_BYTES"] = prior

    def test_looks_like_source_path_spaces_rejected(self) -> None:
        from semia_core.prepare import _looks_like_source_path

        self.assertFalse(_looks_like_source_path("file with spaces.py"))

    def test_looks_like_source_path_no_dot_rejected(self) -> None:
        from semia_core.prepare import _looks_like_source_path

        self.assertFalse(_looks_like_source_path("README"))

    def test_looks_like_source_path_unknown_extension_rejected(self) -> None:
        from semia_core.prepare import _looks_like_source_path

        self.assertFalse(_looks_like_source_path("foo.xyz"))

    def test_parser_for_path_d_ts_returns_none(self) -> None:
        from semia_core.prepare import _parser_for_path

        self.assertIsNone(_parser_for_path("types/foo.d.ts"))

    def test_parser_for_path_unknown_extension_returns_none(self) -> None:
        from semia_core.prepare import _parser_for_path

        self.assertIsNone(_parser_for_path("foo.xyz"))

    def test_dispatch_source_parser_unknown_returns_empty(self) -> None:
        from semia_core.prepare import _dispatch_source_parser

        self.assertEqual(_dispatch_source_parser("x.xyz", "body\n"), [])

    def test_dispatch_source_parser_fallback_when_parser_empty(self) -> None:
        from semia_core.prepare import _dispatch_source_parser

        out = _dispatch_source_parser("x.py", "@@@ definitely not python\n")
        self.assertTrue(out)
        self.assertTrue(all(u[0] == "fenced_code" for u in out))

    def test_render_enriched_empty_input(self) -> None:
        from semia_core.prepare import _render_enriched

        text, mapping = _render_enriched([])
        self.assertEqual(text, "\n")
        self.assertEqual(mapping, ())

    def test_select_main_path_falls_back_to_first_md(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "z_other.md").write_text("# z\n", encoding="utf-8")
            (root / "a_first.md").write_text("# a\n", encoding="utf-8")
            from semia_core.prepare import _select_main_path

            main = _select_main_path(root)
            self.assertEqual(main.name, "a_first.md")

    def test_select_main_path_no_markdown_returns_root(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "data.bin").write_bytes(b"\x00")
            from semia_core.prepare import _select_main_path

            self.assertEqual(_select_main_path(root), root)

    def test_select_main_path_accepts_lowercase_skill_md(self) -> None:
        """``skill.md`` is a common author typo; treat it like the canonical
        ``SKILL.md`` so we don't silently fall through to a README."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "skill.md").write_text("# Demo\n", encoding="utf-8")
            (root / "README.md").write_text("# readme\n", encoding="utf-8")
            from semia_core.prepare import _select_main_path

            self.assertEqual(_select_main_path(root).name, "skill.md")

    def test_select_main_path_accepts_skills_md_plural(self) -> None:
        """``SKILLS.md`` (plural) is another common typo."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "SKILLS.md").write_text("# Demo\n", encoding="utf-8")
            (root / "README.md").write_text("# readme\n", encoding="utf-8")
            from semia_core.prepare import _select_main_path

            self.assertEqual(_select_main_path(root).name, "SKILLS.md")

    def test_select_main_path_accepts_lowercase_skills_md(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "skills.md").write_text("# Demo\n", encoding="utf-8")
            (root / "README.md").write_text("# readme\n", encoding="utf-8")
            from semia_core.prepare import _select_main_path

            self.assertEqual(_select_main_path(root).name, "skills.md")

    def test_select_main_path_prefers_skill_md_over_skills_md(self) -> None:
        """When both SKILL.md and SKILLS.md exist (they are FS-distinct files
        on every filesystem we support, including case-insensitive APFS),
        the canonical singular SKILL.md must win. Uses SKILLS.md instead of
        skill.md as the loser because skill.md aliases SKILL.md on
        case-insensitive filesystems and produces only one on-disk file."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "SKILLS.md").write_text("# SKILLS\n", encoding="utf-8")
            (root / "SKILL.md").write_text("# SKILL\n", encoding="utf-8")
            from semia_core.prepare import _select_main_path

            self.assertEqual(_select_main_path(root).name, "SKILL.md")

    def test_select_main_path_returns_actual_on_disk_case(self) -> None:
        """On case-insensitive filesystems (macOS APFS, Windows NTFS default),
        the user may write ``skill.md`` while the priority list mentions
        ``SKILL.md`` first. The selector must return the on-disk-actual name
        so downstream comparisons against ``os.walk`` results succeed."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "skill.md").write_text("# Demo\n", encoding="utf-8")
            from semia_core.prepare import _select_main_path

            picked = _select_main_path(root)
            # The actual on-disk name appears in iterdir; the picked Path
            # must match one of them byte-for-byte.
            on_disk = {entry.name for entry in root.iterdir()}
            self.assertIn(picked.name, on_disk)

    def test_skill_md_naming_variants_are_treated_as_main(self) -> None:
        """End-to-end: prepare with skill.md (lowercase) must produce inventory
        showing it as the main inlined doc and not as an inlined_source."""
        for variant in ("skill.md", "SKILLS.md", "skills.md"):
            with tempfile.TemporaryDirectory() as td:
                root = Path(td)
                (root / variant).write_text("# Demo\n\n- Read a local file.\n", encoding="utf-8")
                (root / "helper.py").write_text("print('hi')\n", encoding="utf-8")
                bundle = build_prepare_bundle(root)
                inventory = {
                    entry.path: entry.disposition for entry in bundle.source.file_inventory
                }
                self.assertEqual(inventory[variant], "inlined", variant)
                self.assertEqual(inventory["helper.py"], "inlined_source", variant)
                # helper.py should appear in semantic units attributed to its
                # own path — the main-doc exclusion in _inlined_paths_from_source_map
                # must use the actual main name, not the hardcoded "SKILL.md".
                sources = {unit.source_file for unit in bundle.semantic_units}
                self.assertIn("helper.py", sources, variant)

    def test_relative_path_outside_root_returns_name(self) -> None:
        from semia_core.prepare import _relative_path

        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "a"
            root.mkdir()
            other = Path(td) / "b" / "c.txt"
            other.parent.mkdir()
            other.write_text("hi", encoding="utf-8")
            self.assertEqual(_relative_path(root, other), "c.txt")

    def test_is_supported_text_file_rejects_d_ts(self) -> None:
        from semia_core.prepare import _is_supported_text_file

        self.assertFalse(_is_supported_text_file(Path("types/foo.d.ts")))
        self.assertTrue(_is_supported_text_file(Path("regular.ts")))

    def test_main_source_file_handles_no_inlined_disposition(self) -> None:
        from semia_core.artifacts import FileInventoryEntry, SkillSource
        from semia_core.prepare import _main_source_file

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            main_path = root / "README.md"
            main_path.write_text("# r\n", encoding="utf-8")
            inventory = (
                FileInventoryEntry(
                    path="README.md",
                    size_bytes=4,
                    line_count=1,
                    language="markdown",
                    disposition="inlined_source",
                ),
            )
            src = SkillSource(
                source_id="x",
                root=root,
                main_path=main_path,
                inlined_text="",
                source_hash="",
                files=(),
                file_inventory=inventory,
                source_map=(),
            )
            self.assertEqual(_main_source_file(src), "README.md")

    def test_main_source_file_main_path_outside_root(self) -> None:
        from semia_core.artifacts import SkillSource
        from semia_core.prepare import _main_source_file

        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "skill"
            root.mkdir()
            outside = Path(td) / "elsewhere.md"
            outside.write_text("# x\n", encoding="utf-8")
            src = SkillSource(
                source_id="x",
                root=root,
                main_path=outside,
                inlined_text="",
                source_hash="",
                files=(),
                file_inventory=(),
                source_map=(),
            )
            self.assertEqual(_main_source_file(src), "elsewhere.md")

    def test_main_source_file_main_path_missing_returns_name(self) -> None:
        from semia_core.artifacts import SkillSource
        from semia_core.prepare import _main_source_file

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            absent = root / "ghost.md"
            src = SkillSource(
                source_id="x",
                root=root,
                main_path=absent,
                inlined_text="",
                source_hash="",
                files=(),
                file_inventory=(),
                source_map=(),
            )
            self.assertEqual(_main_source_file(src), "ghost.md")

    def test_extract_semantic_units_skips_empty_text(self) -> None:
        from semia_core.artifacts import SourceMapEntry
        from semia_core.prepare import extract_semantic_units

        source = "Real para\n"
        source_map = (
            SourceMapEntry(
                enriched_line_start=1,
                enriched_line_end=1,
                source_file="foo.py",
                source_line_start=0,
                source_line_end=0,
            ),
        )
        units = extract_semantic_units(source, source_map=source_map)
        self.assertTrue(units)


if __name__ == "__main__":
    unittest.main()
