# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 RiemaLabs
"""Parsers that turn a skill source (markdown + inlined code files) into
structured semantic units.

Each language module exposes a ``parse_*_units(source, source_file)`` callable
returning ``(unit_type, text, line_start, line_end)`` tuples with line numbers
1-indexed against the original source file. The markdown module exposes
``parse_markdown`` and ``flatten_to_semantic_units`` instead.
"""

from __future__ import annotations

from . import javascript, markdown, python, shell

__all__ = ["javascript", "markdown", "python", "shell"]
