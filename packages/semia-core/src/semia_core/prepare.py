# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 RiemaLabs
"""Deterministic skill source loading and semantic unit extraction."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
import re
from pathlib import Path

from .artifacts import FileInventoryEntry, PrepareBundle, SemanticUnit, SkillSource, SourceMapEntry

_FRONT_MATTER_RE = re.compile(r"\A---\s*\n.*?\n---\s*\n", re.DOTALL)
_INLINED_HEADING = "<!-- semia:inlined-source-start -->"
_OLD_INLINED_HEADING = "## [Inlined Source Files]"
_GENERATED_SOURCE = "<generated>"
_MAX_FILE_SIZE_BYTES = 1_000_000
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
    ".semia",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
}
_SKIP_FILES_ALWAYS = frozenset({".DS_Store", ".gitkeep"})
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
    units = extract_semantic_units(source.inlined_text, source_file=_main_source_file(source))
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


def extract_semantic_units(source: str, *, source_file: str = "SKILL.md") -> list[SemanticUnit]:
    """Extract stable semantic units from markdown-like source.

    This deliberately avoids third-party markdown parsers. It is a conservative
    block extractor: headings, list items, blockquotes, table rows, paragraphs,
    and non-empty fenced-code lines become evidence units.
    """

    source = _truncate_before_inlined(source)
    source = _strip_front_matter(source)
    lines = source.splitlines()
    raw_units: list[tuple[str, str, int, int]] = []
    paragraph: list[str] = []
    paragraph_start = 0
    in_fence = False

    def flush_paragraph(end_line: int) -> None:
        nonlocal paragraph, paragraph_start
        text = " ".join(part.strip() for part in paragraph if part.strip()).strip()
        if text:
            raw_units.append(("paragraph", _clean_markdown(text), paragraph_start, end_line))
        paragraph = []
        paragraph_start = 0

    for idx, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            flush_paragraph(idx - 1)
            in_fence = not in_fence
            continue
        if in_fence:
            if stripped:
                raw_units.append(("fenced_code", stripped, idx, idx))
            continue
        if not stripped:
            flush_paragraph(idx - 1)
            continue
        if stripped.startswith("#"):
            flush_paragraph(idx - 1)
            text = stripped.lstrip("#").strip()
            if text:
                raw_units.append(("heading", _clean_markdown(text), idx, idx))
            continue
        if stripped.startswith(">"):
            flush_paragraph(idx - 1)
            text = stripped.lstrip(">").strip()
            if text:
                raw_units.append(("blockquote", _clean_markdown(text), idx, idx))
            continue
        if _is_list_item(stripped):
            flush_paragraph(idx - 1)
            text = re.sub(r"^[-*+]\s+|^\d+[.)]\s+", "", stripped).strip()
            if text:
                raw_units.append(("list_item", _clean_markdown(text), idx, idx))
            continue
        if "|" in stripped and stripped.count("|") >= 2:
            flush_paragraph(idx - 1)
            if not re.fullmatch(r"[:\-\s|]+", stripped):
                raw_units.append(("table_row", _clean_markdown(stripped), idx, idx))
            continue
        if not paragraph:
            paragraph_start = idx
        paragraph.append(stripped)

    flush_paragraph(len(lines))

    units: list[SemanticUnit] = []
    for unit_type, text, line_start, line_end in raw_units:
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
                source_file=source_file,
            )
        )
    return units


def build_reference_text(units: list[SemanticUnit] | tuple[SemanticUnit, ...]) -> str:
    """Return the canonical prepared reference text."""

    return "\n".join(unit.text for unit in units)


def render_evidence_units(units: list[SemanticUnit] | tuple[SemanticUnit, ...]) -> str:
    """Render ``evidence_unit(ev, unit_id).`` facts."""

    lines = [f'evidence_unit("{unit.evidence_id}", {unit.id}).' for unit in units]
    return "\n".join(lines) + ("\n" if lines else "")


def _select_main_path(root: Path) -> Path:
    main_path = root / "SKILL.md"
    if main_path.exists():
        return main_path
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
        dir_names[:] = sorted(
            name for name in dir_names if name not in _SKIP_DIRS_ALWAYS
        )
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
            attributed.append(_AttributedLine(f"### {entry.path}", entry.path, 0))
            attributed.append(_AttributedLine("", entry.path, 0))
            attributed.append(_AttributedLine("```text", entry.path, 0))
            attributed.extend(_text_lines(entry.path, _read_text(root / entry.path).rstrip()))
            attributed.append(_AttributedLine("```", entry.path, 0))
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
    return path.suffix.lower() in _TEXT_EXTENSIONS


def _detect_language(path: Path) -> str:
    return _EXT_TO_LANGUAGE.get(path.suffix.lower(), "unknown")


def _truncate_before_inlined(source: str) -> str:
    candidates = [source.find(_INLINED_HEADING), source.find(_OLD_INLINED_HEADING)]
    candidates = [idx for idx in candidates if idx >= 0]
    if not candidates:
        return source
    idx = min(candidates)
    return source[:idx].rstrip() + "\n"


def _strip_front_matter(source: str) -> str:
    return _FRONT_MATTER_RE.sub("", source, count=1)


def _is_list_item(stripped: str) -> bool:
    return bool(re.match(r"^([-*+]\s+|\d+[.)]\s+)", stripped))


def _clean_markdown(text: str) -> str:
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"[*_`~]", "", text)
    return re.sub(r"\s+", " ", text).strip()
