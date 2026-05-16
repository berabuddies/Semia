# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 RiemaLabs
"""Deterministic skill source loading and semantic unit extraction."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path

from .artifacts import FileInventoryEntry, PrepareBundle, SemanticUnit, SkillSource, SourceMapEntry
from .parsers import javascript as js_parser
from .parsers import markdown as md_parser
from .parsers import python as py_parser
from .parsers import shell as sh_parser

_INLINED_HEADING = "<!-- semia:inlined-source-start -->"
_GENERATED_SOURCE = "<generated>"
_MAX_FILE_SIZE_BYTES = 1_000_000
_DEFAULT_MAX_INLINED_BYTES = 4 * 1024 * 1024
# Conventional main-document filenames, in selection priority order. The first
# existing entry on disk wins. Order is deterministic on case-sensitive
# filesystems (Linux); on case-insensitive ones (macOS default, Windows) all
# four refer to the same file, so order is irrelevant. SKILL.md is the
# canonical name; the other three exist because in practice skill authors
# write them by mistake and we should not silently fall through to picking
# README.md.
_SKILL_MAIN_NAMES: tuple[str, ...] = ("SKILL.md", "skill.md", "SKILLS.md", "skills.md")
_TEXT_EXTENSIONS = {
    ".bash",
    ".c",
    ".cc",
    ".cfg",
    ".conf",
    ".cpp",
    ".css",
    ".go",
    ".h",
    ".html",
    ".java",
    ".js",
    ".json",
    ".jsx",
    ".kt",
    ".lua",
    ".md",
    ".mjs",
    ".py",
    ".rb",
    ".rs",
    ".sh",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}
_SKIP_DIRS_ALWAYS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".next",
    ".nuxt",
    ".turbo",
    ".parcel-cache",
    ".semia",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "htmlcov",
    "node_modules",
    "out",
    "target",
    "vendor",
}
# Files that never carry audit signal — package manager lockfiles, repo metadata,
# OS clutter. Lockfiles are pure dependency-resolution metadata; metadata files
# (_meta.json, package.json) are publishing/registry housekeeping. None of them
# describe what the skill DOES.
_SKIP_FILES_ALWAYS = frozenset(
    {
        ".DS_Store",
        ".gitkeep",
        "Cargo.lock",
        "Gemfile.lock",
        "Pipfile.lock",
        "_meta.json",
        "bun.lockb",
        "composer.lock",
        "go.sum",
        "package-lock.json",
        "package.json",
        "pnpm-lock.yaml",
        "poetry.lock",
        "uv.lock",
        "yarn.lock",
    }
)
_EXT_TO_LANGUAGE = {
    ".bash": "shell",
    ".c": "c",
    ".cc": "cpp",
    ".cfg": "config",
    ".conf": "config",
    ".cpp": "cpp",
    ".css": "css",
    ".go": "go",
    ".h": "c",
    ".html": "html",
    ".java": "java",
    ".js": "javascript",
    ".json": "json",
    ".jsx": "javascript",
    ".kt": "kotlin",
    ".lua": "lua",
    ".md": "markdown",
    ".mjs": "javascript",
    ".py": "python",
    ".rb": "ruby",
    ".rs": "rust",
    ".sh": "shell",
    ".toml": "toml",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".txt": "text",
    ".yaml": "yaml",
    ".yml": "yaml",
}


@dataclass(frozen=True)
class _AttributedLine:
    text: str
    source_file: str
    source_line: int


def build_prepare_bundle(path: str | Path, *, source_id: str | None = None) -> PrepareBundle:
    """Load a skill file/directory and return prepared evidence artifacts."""

    source = load_skill_source(path, source_id=source_id)
    units = extract_semantic_units(
        source.inlined_text,
        source_file=_main_source_file(source),
        source_map=source.source_map,
    )
    return PrepareBundle(source=source, semantic_units=tuple(units))


def load_skill_source(path: str | Path, *, source_id: str | None = None) -> SkillSource:
    """Load a skill source as one inlined document with provenance metadata."""

    root = Path(path).resolve()
    if root.is_dir():
        main_path = _select_main_path(root)
        file_inventory = tuple(_build_file_inventory(root, main_path))
        inlined, source_map = _inline_directory(root, main_path, file_inventory)
        files = tuple(entry.path for entry in file_inventory if entry.disposition != "excluded")
        digest = _hash_inventory(root, file_inventory)
        sid = source_id or root.name
    else:
        raw_text = _read_text(root)
        inlined, source_map = _render_enriched(_text_lines(root.name, raw_text))
        sid = source_id or root.stem
        files = (root.name,)
        file_inventory = (
            FileInventoryEntry(
                path=root.name,
                size_bytes=root.stat().st_size,
                line_count=_line_count(raw_text),
                language=_detect_language(root),
                disposition="inlined",
            ),
        )
        digest = _hash_inventory(root.parent, file_inventory)
        main_path = root

    _enforce_inlined_size_cap(inlined)

    return SkillSource(
        source_id=sid,
        root=root if root.is_dir() else root.parent,
        main_path=main_path,
        inlined_text=inlined,
        source_hash=digest,
        files=files,
        file_inventory=file_inventory,
        source_map=source_map,
    )


def _max_inlined_bytes() -> int:
    raw = os.environ.get("SEMIA_PREPARE_MAX_TOTAL_BYTES")
    if raw is None:
        return _DEFAULT_MAX_INLINED_BYTES
    try:
        value = int(raw)
    except ValueError:
        return _DEFAULT_MAX_INLINED_BYTES
    return max(1, value)


def _enforce_inlined_size_cap(inlined: str) -> None:
    cap = _max_inlined_bytes()
    size = len(inlined.encode("utf-8"))
    if size > cap:
        cap_mb = cap / (1024 * 1024)
        actual_mb = size / (1024 * 1024)
        raise ValueError(
            f"prepared skill exceeds maximum allowed size "
            f"({actual_mb:.1f} MB > {cap_mb:.1f} MB); "
            f"raise SEMIA_PREPARE_MAX_TOTAL_BYTES to override"
        )


def extract_semantic_units(
    source: str,
    *,
    source_file: str = "SKILL.md",
    source_map: tuple[SourceMapEntry, ...] = (),
) -> list[SemanticUnit]:
    """Extract stable semantic units from markdown-like source.

    Headings, list items, blockquotes, table rows, and per-line paragraphs
    become units. ATX ``### path.ext`` headings followed by a fenced block are
    routed to language-aware parsers; unknown extensions fall back to per-line
    ``fenced_code`` units. Each unit carries an attributed ``source_file``.
    Markdown unit line numbers are translated via ``source_map`` back to their
    originating source file; code units pass through unchanged.
    """

    tree = md_parser.parse_markdown(source)
    inlined_paths = _inlined_paths_from_source_map(source_map, main_source_file=source_file)
    raw_units = _flatten_tree_with_dispatch(tree, source_file, source_map, inlined_paths)

    units: list[SemanticUnit] = []
    for unit_type, text, line_start, line_end, attributed_file in raw_units:
        if not text:
            continue
        units.append(
            SemanticUnit(
                id=len(units),
                evidence_id=f"su_{len(units)}",
                unit_type=unit_type,
                text=text,
                line_start=line_start,
                line_end=line_end,
                source_file=attributed_file,
            )
        )
    return units


def _translate_unit_lines(
    line_start: int,
    line_end: int,
    source_map: tuple[SourceMapEntry, ...],
    fallback_source_file: str,
) -> tuple[str, int, int]:
    """Translate inlined-doc lines back to (source_file, source_start, source_end).

    Generated content (``source_line_start == 0``) keeps the caller's
    ``fallback_source_file`` and uses line 0 to signal "no real source line".
    """

    start_entry = _find_source_entry(source_map, line_start)
    end_entry = _find_source_entry(source_map, line_end) or start_entry
    if start_entry is None:
        return fallback_source_file, line_start, line_end
    if start_entry.source_line_start == 0:
        return fallback_source_file, 0, 0
    translated_start = start_entry.source_line_start + (
        line_start - start_entry.enriched_line_start
    )
    if end_entry is None or end_entry.source_line_start == 0:
        translated_end = translated_start
    else:
        translated_end = end_entry.source_line_start + (line_end - end_entry.enriched_line_start)
    return start_entry.source_file, translated_start, max(translated_start, translated_end)


def _find_source_entry(
    source_map: tuple[SourceMapEntry, ...], inlined_line: int
) -> SourceMapEntry | None:
    for entry in source_map:
        if entry.enriched_line_start <= inlined_line <= entry.enriched_line_end:
            return entry
    return None


def _flatten_tree_with_dispatch(
    tree: tuple[md_parser.MarkdownNode, ...],
    source_file: str,
    source_map: tuple[SourceMapEntry, ...] = (),
    inlined_paths: frozenset[str] = frozenset(),
) -> list[tuple[str, str, int, int, str]]:
    """Flatten parsed markdown into per-unit tuples and dispatch ``### path``-
    headed code blocks to language parsers. Dispatch always runs when the
    pattern matches (we get structural units regardless of source provenance),
    but the resulting units are attributed to the actual file containing them:
    ``pending_source_file`` when the path is an inlined source file, otherwise
    the parent document (``source_file``).
    """
    # Each entry is (unit_type, text, line_start, line_end, source_file, is_source_relative)
    raw: list[tuple[str, str, int, int, str, bool]] = []
    pending_source_file: str | None = None
    for node in tree:
        if node.type == "heading":
            raw.append(("heading", node.text, node.line_start, node.line_end, source_file, False))
            pending_source_file = node.text if _looks_like_source_path(node.text) else None
            continue
        if node.type == "code_block":
            is_real_inlined = pending_source_file in inlined_paths
            attributed = pending_source_file if is_real_inlined else source_file
            if (
                pending_source_file
                and node.info in {"", "text"}
                and _has_known_parser(pending_source_file)
            ):
                block_units = _dispatch_source_parser(pending_source_file, node.text)
                # Parser line numbers are source-relative only when the block
                # really lives in an inlined file. For markdown tutorials with
                # `### foo.py` headings, the lines belong to the parent
                # document and still need translation via source_map.
                for ut, text, ls, le in block_units:
                    raw.append((ut, text, ls, le, attributed, is_real_inlined))
            else:
                # Fenced-code fallback emits inlined-doc line numbers from the
                # parsed node; source_map translation reconciles them.
                tmp: list[tuple[str, str, int, int, str]] = []
                _emit_fenced_code_from_node(tmp, node, attributed)
                for entry in tmp:
                    raw.append(entry + (False,))
            pending_source_file = None
            continue
        pending_source_file = None
        tmp_emit: list[tuple[str, str, int, int, str]] = []
        md_parser._emit_node(node, source_file, tmp_emit)
        for entry in tmp_emit:
            raw.append(entry + (False,))

    resolved: list[tuple[str, str, int, int, str]] = []
    for ut, text, ls, le, attributed, is_source_relative in raw:
        if not is_source_relative and source_map:
            attributed, ls, le = _translate_unit_lines(ls, le, source_map, attributed)
        resolved.append((ut, text, ls, le, attributed))
    return resolved


def _inlined_paths_from_source_map(
    source_map: tuple[SourceMapEntry, ...],
    *,
    main_source_file: str = "",
) -> frozenset[str]:
    """Return the set of source file paths that source_map attributes content to,
    excluding the main document and synthetic generated sections.

    ``main_source_file`` should be the path passed as ``source_file`` to
    ``extract_semantic_units`` — the actual main document name, which can be
    any of ``_SKILL_MAIN_NAMES`` or a fallback ``README.md``-style file. When
    omitted, no main-doc exclusion is applied (older callers that pre-date
    this generalization).
    """

    excluded = {"", _GENERATED_SOURCE}
    if main_source_file:
        excluded.add(main_source_file)
    paths: set[str] = set()
    for entry in source_map:
        if entry.source_file in excluded:
            continue
        if entry.source_line_start == 0 and entry.source_line_end == 0:
            continue
        paths.add(entry.source_file)
    return frozenset(paths)


def _emit_fenced_code_from_node(
    out: list[tuple[str, str, int, int, str]],
    node: md_parser.MarkdownNode,
    source_file: str,
) -> None:
    line_no = node.line_start
    for line in node.text.split("\n"):
        stripped = line.strip()
        if stripped:
            out.append(("fenced_code", stripped, line_no, line_no, source_file))
        line_no += 1


def _looks_like_source_path(heading_text: str) -> bool:
    if " " in heading_text:
        return False
    if "." not in heading_text:
        return False
    suffix = Path(heading_text).suffix.lower()
    return suffix in _TEXT_EXTENSIONS


def _has_known_parser(path: str) -> bool:
    return _parser_for_path(path) is not None


def _parser_for_path(path: str):
    name = Path(path).name.lower()
    # TypeScript declaration files contribute zero runtime behavior; skip.
    if name.endswith(".d.ts"):
        return None
    ext = Path(path).suffix.lower()
    if ext == ".py":
        return py_parser.parse_python_units
    if ext in {".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx"}:
        return js_parser.parse_javascript_units
    if ext in {".sh", ".bash"}:
        return sh_parser.parse_shell_units
    if ext == ".md":
        return md_parser.parse_markdown_units
    return None


def _dispatch_source_parser(path: str, block_text: str) -> list[tuple[str, str, int, int]]:
    parser = _parser_for_path(path)
    if parser is None:
        return []
    units = parser(block_text, source_file=path)
    if units:
        return units
    return _fallback_fenced_lines(block_text)


def _fallback_fenced_lines(
    block_text: str,
) -> list[tuple[str, str, int, int]]:
    out: list[tuple[str, str, int, int]] = []
    for offset, line in enumerate(block_text.splitlines(), 1):
        stripped = line.strip()
        if stripped:
            out.append(("fenced_code", stripped, offset, offset))
    return out


def _select_main_path(root: Path) -> Path:
    # Build a case-insensitive index of files keyed by lowercased name. We
    # want priority by the canonical SKILL name order, but the returned Path
    # must use the *actual* on-disk case so the comparison in
    # _build_file_inventory (``rel == rel_main``) succeeds uniformly across
    # case-sensitive (Linux) and case-insensitive (macOS/Windows) filesystems
    # — otherwise ``_select_main_path`` may report ``SKILL.md`` while os.walk
    # enumerates ``skill.md`` and the main doc gets dispositioned as an
    # inlined_source instead of the main inlined doc.
    #
    # ``sorted`` makes the choice deterministic when (rare) case-sensitive
    # FS has both e.g. SKILL.md and skill.md as separate files: ASCII order
    # puts uppercase first, so SKILL.md wins via ``setdefault``.
    if not root.is_dir():
        return root
    by_lower: dict[str, Path] = {}
    for entry in sorted(root.iterdir(), key=lambda p: p.name):
        if entry.is_file():
            by_lower.setdefault(entry.name.lower(), entry)
    for name in _SKILL_MAIN_NAMES:
        candidate = by_lower.get(name.lower())
        if candidate is not None:
            return candidate
    markdown_files = sorted(root.glob("*.md"))
    return markdown_files[0] if markdown_files else root


def _build_file_inventory(root: Path, main_path: Path) -> list[FileInventoryEntry]:
    rel_main = _relative_path(root, main_path) if main_path.is_file() else None
    entries: list[FileInventoryEntry] = []
    for rel in _iter_visible_files(root):
        path = root / rel
        size_bytes = path.stat().st_size
        if not _is_supported_text_file(path) or size_bytes > _MAX_FILE_SIZE_BYTES:
            entries.append(
                FileInventoryEntry(
                    path=rel,
                    size_bytes=size_bytes,
                    line_count=0,
                    language=_detect_language(path),
                    disposition="excluded",
                )
            )
            continue

        text = _read_text(path)
        entries.append(
            FileInventoryEntry(
                path=rel,
                size_bytes=size_bytes,
                line_count=_line_count(text),
                language=_detect_language(path),
                disposition="inlined" if rel == rel_main else "inlined_source",
            )
        )
    return entries


def _iter_visible_files(root: Path) -> list[str]:
    paths: list[str] = []
    for current_dir, dir_names, file_names in os.walk(root):
        dir_names[:] = sorted(name for name in dir_names if name not in _SKIP_DIRS_ALWAYS)
        for name in sorted(file_names):
            if name in _SKIP_FILES_ALWAYS:
                continue
            rel = Path(current_dir, name).relative_to(root).as_posix()
            paths.append(rel)
    return paths


def _inline_directory(
    root: Path,
    main_path: Path,
    file_inventory: tuple[FileInventoryEntry, ...],
) -> tuple[str, tuple[SourceMapEntry, ...]]:
    rel_main = _relative_path(root, main_path) if main_path.is_file() else None
    attributed: list[_AttributedLine] = []

    if rel_main is not None:
        attributed.extend(_text_lines(rel_main, _read_text(main_path).rstrip()))

    aux_files = [entry for entry in file_inventory if entry.disposition == "inlined_source"]
    if aux_files:
        attributed.append(_AttributedLine("", _GENERATED_SOURCE, 0))
        attributed.append(_AttributedLine(_INLINED_HEADING, _GENERATED_SOURCE, 0))
        attributed.append(_AttributedLine("", _GENERATED_SOURCE, 0))
        for entry in aux_files:
            # Use a 6-backtick fence so any 3- or 4-backtick code fences inside
            # the inlined content (common in README.md / *.md files) cannot
            # prematurely close the outer wrapper. CommonMark requires the
            # closing fence to have at least as many backticks as the opening.
            attributed.append(_AttributedLine(f"### {entry.path}", entry.path, 0))
            attributed.append(_AttributedLine("", entry.path, 0))
            attributed.append(_AttributedLine("``````text", entry.path, 0))
            attributed.extend(_text_lines(entry.path, _read_text(root / entry.path).rstrip()))
            attributed.append(_AttributedLine("``````", entry.path, 0))
            attributed.append(_AttributedLine("", entry.path, 0))

    return _render_enriched(attributed)


def _text_lines(source_file: str, text: str) -> list[_AttributedLine]:
    return [
        _AttributedLine(text=line, source_file=source_file, source_line=index)
        for index, line in enumerate(text.splitlines(), 1)
    ]


def _render_enriched(
    attributed: list[_AttributedLine],
) -> tuple[str, tuple[SourceMapEntry, ...]]:
    if not attributed:
        return "\n", ()

    # Merge attributed lines into SourceMapEntry runs:
    # (a) consecutive lines with the same source_file and consecutive source_line
    #     numbers form one entry;
    # (b) source_line == 0 marks "<generated>" content that joins only with adjacent
    #     generated lines from the same source_file, never with real-source lines.
    source_map: list[SourceMapEntry] = []
    start = 0
    while start < len(attributed):
        end = start + 1
        while end < len(attributed):
            current = attributed[end]
            previous = attributed[end - 1]
            first = attributed[start]
            if current.source_file != first.source_file:
                break
            if first.source_line == 0:
                if current.source_line != 0:
                    break
            elif current.source_line != previous.source_line + 1:
                break
            end += 1

        source_map.append(
            SourceMapEntry(
                enriched_line_start=start + 1,
                enriched_line_end=end,
                source_file=attributed[start].source_file,
                source_line_start=attributed[start].source_line,
                source_line_end=attributed[end - 1].source_line,
            )
        )
        start = end

    text = "\n".join(line.text for line in attributed) + "\n"
    return text, tuple(source_map)


def _main_source_file(source: SkillSource) -> str:
    for entry in source.file_inventory:
        if entry.disposition == "inlined":
            return entry.path
    if source.main_path.is_file():
        try:
            return source.main_path.relative_to(source.root).as_posix()
        except ValueError:
            return source.main_path.name
    return source.main_path.name


def _relative_path(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.name


def _hash_inventory(root: Path, inventory: tuple[FileInventoryEntry, ...]) -> str:
    hasher = hashlib.sha256()
    for entry in sorted(inventory, key=lambda e: e.path):
        hasher.update(entry.path.encode("utf-8"))
        hasher.update(b"\0")
        hasher.update(entry.disposition.encode("utf-8"))
        hasher.update(b"\0")
        if entry.disposition == "excluded":
            hasher.update(str(entry.size_bytes).encode("utf-8"))
        else:
            hasher.update((root / entry.path).read_bytes())
        hasher.update(b"\0")
    return hasher.hexdigest()


def _read_text(path: Path) -> str:
    data = path.read_bytes()
    return data.decode("utf-8", errors="replace")


def _line_count(text: str) -> int:
    return len(text.splitlines())


def _is_supported_text_file(path: Path) -> bool:
    name = path.name.lower()
    # TypeScript declaration files (*.d.ts) describe types only; no runtime
    # behavior to audit. Exclude even though the .ts extension is supported.
    if name.endswith(".d.ts"):
        return False
    return path.suffix.lower() in _TEXT_EXTENSIONS


def _detect_language(path: Path) -> str:
    return _EXT_TO_LANGUAGE.get(path.suffix.lower(), "unknown")
