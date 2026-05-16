# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 RiemaLabs
"""Stdlib-only Markdown AST parser for the CommonMark subset Semia consumes.

The parser runs in two passes: a block tokenizer classifies each line, then a
tree builder assembles them into a flat top-level tuple of :class:`MarkdownNode`
values with nested constructs as ``children``. The exported
:func:`flatten_to_semantic_units` walks the tree and emits the per-line tuples
that :mod:`semia_core.prepare` turns into :class:`SemanticUnit` records.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_FRONT_MATTER_RE = re.compile(r"\A---\s*\n.*?\n---\s*\n", re.DOTALL)
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_LIST_ITEM_RE = re.compile(r"^(?P<indent>[ \t]*)(?P<marker>[-*+]|\d+[.)])\s+(?P<body>.*)$")
_FENCE_RE = re.compile(r"^(?P<indent>[ \t]*)(?P<fence>`{3,}|~{3,})\s*(?P<info>[^\s`]*)\s*$")
_FENCE_CLOSE_RE = re.compile(r"^[ \t]*(?P<fence>`{3,}|~{3,})\s*$")
_ATX_RE = re.compile(r"^(?P<hashes>#{1,6})(?:\s+(?P<text>.*?))?\s*#*\s*$")
_SETEXT_RE = re.compile(r"^[ \t]*(?P<bar>=+|-+)\s*$")
_THEMATIC_RE = re.compile(r"^[ \t]*(?:(?:\*\s*){3,}|(?:-\s*){3,}|(?:_\s*){3,})$")
_TABLE_SEPARATOR_RE = re.compile(r"^[ \t]*\|?[\s:\-|]+\|[\s:\-|]*$")
_BLOCKQUOTE_RE = re.compile(r"^[ \t]{0,3}>\s?(?P<rest>.*)$")
_INDENTED_CODE_RE = re.compile(r"^(?: {4}|\t)(?P<rest>.*)$")
_HTML_BLOCK_OPEN_RE = re.compile(r"^<[A-Za-z!/?][^>]*>?\s*$")
_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_INLINE_PUNCT_RE = re.compile(r"[*_`~]")
_WHITESPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class MarkdownNode:
    """One node in the parsed markdown tree."""

    type: str
    text: str
    level: int = 0
    info: str = ""
    line_start: int = 0
    line_end: int = 0
    children: tuple[MarkdownNode, ...] = ()


def parse_markdown(source: str) -> tuple[MarkdownNode, ...]:
    """Return the top-level :class:`MarkdownNode` tuple for ``source``.

    YAML front matter is extracted into ``front_matter_field`` nodes; inline
    HTML comments are stripped. The returned tree is flat at the top level;
    nested constructs appear as ``children`` on their parent node. Line numbers
    on every node reflect the ORIGINAL source position (1-indexed).
    """

    front_matter_nodes, remaining, body_line_offset = _extract_front_matter(source)
    cleaned = _strip_html_comments(remaining)
    lines = cleaned.splitlines()
    body_tree = _build_tree(lines, line_offset=body_line_offset)
    return tuple(front_matter_nodes) + body_tree


def flatten_to_semantic_units(
    tree: tuple[MarkdownNode, ...],
    source_file: str,
) -> list[tuple[str, str, int, int, str]]:
    """Walk ``tree`` and emit ``(unit_type, text, line_start, line_end, source_file)``."""

    out: list[tuple[str, str, int, int, str]] = []
    for node in tree:
        _emit_node(node, source_file, out)
    return out


def parse_markdown_units(
    source: str,
    source_file: str = "",
    line_offset: int = 0,
) -> list[tuple[str, str, int, int]]:
    """Parse markdown and return ``(unit_type, text, line_start, line_end)`` tuples.

    Matches the contract of the other ``parsers.*.parse_*_units`` callables so
    the prepare-step dispatch can route ``### foo.md`` + fenced blocks to the
    markdown parser. Line numbers are 1-indexed against ``source``; the caller
    is responsible for attribution of the ``source_file``.
    """

    tree = parse_markdown(source)
    out: list[tuple[str, str, int, int, str]] = []
    for node in tree:
        _emit_node(node, "", out)
    return [(ut, text, ls, le) for ut, text, ls, le, _ in out]


def _emit_node(
    node: MarkdownNode,
    source_file: str,
    out: list[tuple[str, str, int, int, str]],
) -> None:
    if node.type == "front_matter_field":
        out.append(("front_matter_field", node.text, node.line_start, node.line_end, source_file))
        return
    if node.type == "heading":
        out.append(("heading", node.text, node.line_start, node.line_end, source_file))
        return
    if node.type == "paragraph":
        out.append(("paragraph", node.text, node.line_start, node.line_end, source_file))
        return
    if node.type == "blockquote":
        for child in node.children:
            out.append(("blockquote", child.text, child.line_start, child.line_end, source_file))
        return
    if node.type == "list":
        for child in node.children:
            _emit_node(child, source_file, out)
        return
    if node.type == "list_item":
        if node.text:
            out.append(("list_item", node.text, node.line_start, node.line_end, source_file))
        for child in node.children:
            _emit_node(child, source_file, out)
        return
    if node.type == "table":
        for child in node.children:
            out.append(("table_row", child.text, child.line_start, child.line_end, source_file))
        return
    if node.type == "code_block":
        line_no = node.line_start
        for line in node.text.split("\n"):
            stripped = line.strip()
            if stripped:
                out.append(("fenced_code", stripped, line_no, line_no, source_file))
            line_no += 1
        return
    if node.type == "html_block":
        out.append(("html_block", node.text, node.line_start, node.line_end, source_file))
        return
    if node.type == "thematic_break":
        return


_FRONT_MATTER_KV_RE = re.compile(r"^(?P<key>[A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(?P<value>.*)$")


def _extract_front_matter(source: str) -> tuple[list[MarkdownNode], str, int]:
    """Return ``(front_matter_nodes, remaining_source, body_line_offset)``.

    ``body_line_offset`` is the 1-indexed source line where the content after
    the closing ``---`` begins, so subsequent parsing can preserve original
    line numbers. Each top-level YAML key becomes one ``front_matter_field``
    node whose text is ``"key: value"``.
    """

    match = _FRONT_MATTER_RE.match(source)
    if not match:
        return [], source, 1
    block = match.group(0)
    block_lines = block.split("\n")
    inner_lines: list[str] = []
    for line in block_lines[1:]:
        if line.strip() == "---":
            break
        inner_lines.append(line)
    nodes: list[MarkdownNode] = []
    current_key: str | None = None
    current_value_parts: list[str] = []
    current_start = 0
    current_last_line = 0
    for offset, line in enumerate(inner_lines, start=2):
        stripped = line.rstrip()
        if not stripped:
            if current_key is not None:
                nodes.append(
                    _front_matter_node(
                        current_key, current_value_parts, current_start, current_last_line
                    )
                )
                current_key, current_value_parts = None, []
            continue
        match_kv = _FRONT_MATTER_KV_RE.match(stripped) if line == stripped else None
        if match_kv:
            if current_key is not None:
                nodes.append(
                    _front_matter_node(
                        current_key, current_value_parts, current_start, current_last_line
                    )
                )
            current_key = match_kv.group("key")
            value = match_kv.group("value").strip()
            current_value_parts = [value] if value else []
            current_start = offset
            current_last_line = offset
        else:
            if current_key is not None:
                current_value_parts.append(stripped.strip())
                current_last_line = offset
    if current_key is not None:
        nodes.append(
            _front_matter_node(current_key, current_value_parts, current_start, current_last_line)
        )
    remaining = source[match.end() :]
    body_offset = block.count("\n") + 1
    return nodes, remaining, body_offset


def _front_matter_node(key: str, value_parts: list[str], start: int, end: int) -> MarkdownNode:
    joined = " ".join(part for part in value_parts if part).strip()
    text = f"{key}: {joined}" if joined else f"{key}:"
    return MarkdownNode(
        type="front_matter_field",
        text=text,
        line_start=start,
        line_end=max(start, end),
    )


def _strip_html_comments(source: str) -> str:
    return _HTML_COMMENT_RE.sub("", source)


def _strip_inline_markdown(text: str) -> str:
    text = _LINK_RE.sub(r"\1", text)
    text = _INLINE_PUNCT_RE.sub("", text)
    return _WHITESPACE_RE.sub(" ", text).strip()


def _build_tree(lines: list[str], line_offset: int = 1) -> tuple[MarkdownNode, ...]:
    nodes: list[MarkdownNode] = []
    idx = 0
    n = len(lines)
    while idx < n:
        line = lines[idx]
        stripped = line.strip()

        if not stripped:
            idx += 1
            continue

        fence = _FENCE_RE.match(line)
        if fence is not None:
            node, next_idx = _consume_fence(lines, idx, fence, line_offset)
            nodes.append(node)
            idx = next_idx
            continue

        if _ATX_RE.match(line) is not None:
            node = _consume_atx(line, idx + line_offset)
            if node is not None:
                nodes.append(node)
            idx += 1
            continue

        if _BLOCKQUOTE_RE.match(line) is not None:
            node, next_idx = _consume_blockquote(lines, idx, line_offset)
            nodes.append(node)
            idx = next_idx
            continue

        if _is_table_start(lines, idx):
            node, next_idx = _consume_table(lines, idx, line_offset)
            nodes.append(node)
            idx = next_idx
            continue

        list_match = _LIST_ITEM_RE.match(line)
        if list_match is not None and _is_indent_for_outer_list(list_match):
            outer_indent = len((list_match.group("indent") or "").expandtabs(4))
            node, next_idx = _consume_list(
                lines, idx, indent_width=outer_indent, line_offset=line_offset
            )
            nodes.append(node)
            idx = next_idx if next_idx > idx else idx + 1
            continue

        if _INDENTED_CODE_RE.match(line) is not None:
            node, next_idx = _consume_indented_code(lines, idx, line_offset)
            nodes.append(node)
            idx = next_idx
            continue

        if _is_html_block_start(line):
            node, next_idx = _consume_html_block(lines, idx, line_offset)
            nodes.append(node)
            idx = next_idx
            continue

        if _THEMATIC_RE.match(line) is not None and not _LIST_ITEM_RE.match(line):
            nodes.append(
                MarkdownNode(
                    type="thematic_break",
                    text="",
                    line_start=idx + line_offset,
                    line_end=idx + line_offset,
                )
            )
            idx += 1
            continue

        # Paragraph or setext heading: capture exactly one text line, but if
        # the following line is a setext underline, fold it into a heading.
        if idx + 1 < n and _SETEXT_RE.match(lines[idx + 1]) is not None:
            bar = _SETEXT_RE.match(lines[idx + 1]).group("bar")
            level = 1 if bar.startswith("=") else 2
            text = _strip_inline_markdown(stripped)
            if text:
                nodes.append(
                    MarkdownNode(
                        type="heading",
                        text=text,
                        level=level,
                        line_start=idx + line_offset,
                        line_end=idx + line_offset + 1,
                    )
                )
            idx += 2
            continue

        text = _strip_inline_markdown(stripped)
        if text:
            nodes.append(
                MarkdownNode(
                    type="paragraph",
                    text=text,
                    line_start=idx + line_offset,
                    line_end=idx + line_offset,
                )
            )
        idx += 1

    return tuple(nodes)


def _is_indent_for_outer_list(match: re.Match[str]) -> bool:
    indent = match.group("indent") or ""
    return len(indent.expandtabs(4)) < 4


def _consume_atx(line: str, line_no: int) -> MarkdownNode | None:
    match = _ATX_RE.match(line)
    if match is None:
        return None
    hashes = match.group("hashes")
    raw = match.group("text") or ""
    text = _strip_inline_markdown(raw)
    if not text:
        return None
    return MarkdownNode(
        type="heading",
        text=text,
        level=len(hashes),
        line_start=line_no,
        line_end=line_no,
    )


def _consume_fence(
    lines: list[str],
    idx: int,
    fence_match: re.Match[str],
    line_offset: int = 1,
) -> tuple[MarkdownNode, int]:
    fence_marker = fence_match.group("fence")
    info = fence_match.group("info") or ""
    body: list[str] = []
    j = idx + 1
    closing_line = idx
    fence_char = fence_marker[0]
    fence_len = len(fence_marker)
    while j < len(lines):
        close = _FENCE_CLOSE_RE.match(lines[j])
        if (
            close is not None
            and close.group("fence")[0] == fence_char
            and len(close.group("fence")) >= fence_len
        ):
            closing_line = j
            break
        body.append(lines[j])
        j += 1
    if j >= len(lines):
        closing_line = len(lines) - 1
        next_idx = len(lines)
    else:
        next_idx = j + 1
    return (
        MarkdownNode(
            type="code_block",
            text="\n".join(body),
            info=info,
            line_start=idx + 1 + line_offset,
            line_end=closing_line + line_offset,
        ),
        next_idx,
    )


def _consume_indented_code(
    lines: list[str],
    idx: int,
    line_offset: int = 1,
) -> tuple[MarkdownNode, int]:
    body: list[str] = []
    j = idx
    while j < len(lines):
        match = _INDENTED_CODE_RE.match(lines[j])
        if match is None:
            if lines[j].strip() == "":
                # Allow blanks inside indented code as long as a following
                # line is still indented; otherwise stop.
                lookahead = j + 1
                while lookahead < len(lines) and lines[lookahead].strip() == "":
                    lookahead += 1
                if lookahead < len(lines) and _INDENTED_CODE_RE.match(lines[lookahead]) is not None:
                    body.append("")
                    j += 1
                    continue
            break
        body.append(match.group("rest"))
        j += 1
    return (
        MarkdownNode(
            type="code_block",
            text="\n".join(body),
            info="",
            line_start=idx + line_offset,
            line_end=j + line_offset - 1,
        ),
        j,
    )


def _consume_blockquote(
    lines: list[str],
    idx: int,
    line_offset: int = 1,
) -> tuple[MarkdownNode, int]:
    children: list[MarkdownNode] = []
    j = idx
    while j < len(lines):
        match = _BLOCKQUOTE_RE.match(lines[j])
        if match is None:
            break
        rest = match.group("rest")
        text = _strip_inline_markdown(rest)
        if text:
            children.append(
                MarkdownNode(
                    type="paragraph",
                    text=text,
                    line_start=j + line_offset,
                    line_end=j + line_offset,
                )
            )
        j += 1
    return (
        MarkdownNode(
            type="blockquote",
            text="",
            line_start=idx + line_offset,
            line_end=j + line_offset - 1,
            children=tuple(children),
        ),
        j,
    )


def _is_table_start(lines: list[str], idx: int) -> bool:
    if idx + 1 >= len(lines):
        return False
    head = lines[idx]
    sep = lines[idx + 1]
    if "|" not in head or "|" not in sep:
        return False
    if _TABLE_SEPARATOR_RE.match(sep) is None:
        return False
    return head.count("|") >= 1 and "-" in sep


def _consume_table(
    lines: list[str],
    idx: int,
    line_offset: int = 1,
) -> tuple[MarkdownNode, int]:
    rows: list[MarkdownNode] = []
    header = lines[idx].strip()
    rows.append(
        MarkdownNode(
            type="table_row",
            text=_strip_inline_markdown(header),
            line_start=idx + line_offset,
            line_end=idx + line_offset,
        )
    )
    j = idx + 2
    while j < len(lines):
        line = lines[j]
        stripped = line.strip()
        if not stripped or "|" not in stripped:
            break
        if _TABLE_SEPARATOR_RE.match(line) is not None:
            j += 1
            continue
        rows.append(
            MarkdownNode(
                type="table_row",
                text=_strip_inline_markdown(stripped),
                line_start=j + line_offset,
                line_end=j + line_offset,
            )
        )
        j += 1
    return (
        MarkdownNode(
            type="table",
            text="",
            line_start=idx + line_offset,
            line_end=j + line_offset - 1,
            children=tuple(rows),
        ),
        j,
    )


def _is_html_block_start(line: str) -> bool:
    if not line.startswith("<"):
        return False
    return _HTML_BLOCK_OPEN_RE.match(line) is not None


def _consume_html_block(
    lines: list[str],
    idx: int,
    line_offset: int = 1,
) -> tuple[MarkdownNode, int]:
    body: list[str] = [lines[idx]]
    j = idx + 1
    while j < len(lines):
        line = lines[j]
        if line.strip() == "":
            j += 1
            break
        body.append(line)
        if "</" in line and line.rstrip().endswith(">"):
            j += 1
            break
        j += 1
    return (
        MarkdownNode(
            type="html_block",
            text="\n".join(body),
            line_start=idx + line_offset,
            line_end=j + line_offset - 1,
        ),
        j,
    )


def _consume_list(
    lines: list[str],
    idx: int,
    indent_width: int,
    line_offset: int = 1,
) -> tuple[MarkdownNode, int]:
    items: list[MarkdownNode] = []
    j = idx
    while j < len(lines):
        line = lines[j]
        if not line.strip():
            j += 1
            continue
        match = _LIST_ITEM_RE.match(line)
        if match is None:
            break
        current_indent = len((match.group("indent") or "").expandtabs(4))
        if current_indent != indent_width:
            break
        body = match.group("body")
        item_text = _strip_inline_markdown(body)
        item_start = j + line_offset
        j += 1
        nested_children: list[MarkdownNode] = []
        # Gather nested lines whose indent exceeds the parent indent.
        while j < len(lines):
            next_line = lines[j]
            if not next_line.strip():
                # Tolerate a single blank line between siblings.
                lookahead = j + 1
                while lookahead < len(lines) and lines[lookahead].strip() == "":
                    lookahead += 1
                if lookahead >= len(lines):
                    break
                next_match = _LIST_ITEM_RE.match(lines[lookahead])
                if next_match is None:
                    break
                next_indent = len((next_match.group("indent") or "").expandtabs(4))
                if next_indent <= indent_width:
                    break
                j = lookahead
                continue
            next_match = _LIST_ITEM_RE.match(next_line)
            if next_match is not None:
                next_indent = len((next_match.group("indent") or "").expandtabs(4))
                if next_indent > indent_width:
                    nested_node, j = _consume_list(
                        lines, j, indent_width=next_indent, line_offset=line_offset
                    )
                    nested_children.append(nested_node)
                    continue
                break
            # Non-list-item line: only fold it in if it is indented past the
            # marker (continuation text). Otherwise the list terminates.
            leading = len(next_line) - len(next_line.lstrip())
            if leading > indent_width:
                j += 1
                continue
            break
        items.append(
            MarkdownNode(
                type="list_item",
                text=item_text,
                line_start=item_start,
                line_end=item_start,
                children=tuple(nested_children),
            )
        )
    return (
        MarkdownNode(
            type="list",
            text="",
            line_start=idx + line_offset,
            line_end=j + line_offset - 1,
            children=tuple(items),
        ),
        j,
    )
