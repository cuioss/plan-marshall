#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared detection helpers for the agentfile-hygiene plugin-doctor rules.

Two backstop rules consume these helpers:

- ``agentfile-line-count-over-budget`` (``_analyze_agentfile_line_budget.py``)
- ``agentfile-directory-tree-present`` (``_analyze_agentfile_directory_tree.py``)

Both rules are the fast deterministic half of the agentfile context-hygiene
capability; the cognitive half is ``plan-marshall:recipe-agentfile-hygiene``.
Both halves consume the single normative rubric in
``plan-marshall:ref-agentfile-hygiene`` ``standards/rubric.md`` — the line
budget and the directory-tree anti-pattern are defined there, not here.

The helpers are pure (no subprocess, no mutation, stdlib-only) and operate on
the repository-root agentfile corpus rather than the marketplace bundle tree:
an *always-on agentfile* is any ``CLAUDE.md`` at any nesting level plus any
``AGENTS.md`` (the OpenAI / OpenCode spec name). Discovery anchors at the repo
root and prunes generated / vendored / planning-scratch directories, mirroring
the ``recipe-agentfile-hygiene`` discovery exclusions so the deterministic
backstop and the cognitive sweep see the same corpus.
"""

from __future__ import annotations

import os
from pathlib import Path

# Always-on agentfile basenames (Claude Code ``CLAUDE.md`` + OpenAI/OpenCode
# spec ``AGENTS.md``).
AGENTFILE_NAMES = ('CLAUDE.md', 'AGENTS.md')

# Directories whose agentfiles are generated, vendored, or planning-scratch and
# are therefore NOT the project's own always-on instructions. Mirrors the
# ``recipe-agentfile-hygiene`` Step-1 discovery exclusions.
_EXCLUDED_DIR_NAMES = frozenset({'.plan', '.git', 'node_modules', 'target'})

# Box-drawing glyphs that mark a hand-drawn directory tree. Source: the rubric's
# directory-tree anti-pattern section, which names these three glyphs verbatim.
_TREE_GLYPHS = ('├──', '└──', '│')


def repo_root_from_marketplace_root(marketplace_root: str | Path) -> Path:
    """Return the repository root given the ``bundles/`` marketplace root.

    ``find_marketplace_root`` resolves to ``<repo>/marketplace/bundles``, so the
    repository root is two levels up. Agentfile discovery anchors at the repo
    root (not the bundle tree), so callers translate the marketplace root they
    already hold into the repo root through this single helper.
    """
    return Path(marketplace_root).resolve().parent.parent


def discover_agentfiles(root: str | Path) -> list[Path]:
    """Return every always-on agentfile under ``root`` with excluded dirs pruned.

    Walks ``root`` collecting files named ``CLAUDE.md`` or ``AGENTS.md``,
    pruning any directory in ``_EXCLUDED_DIR_NAMES`` so the walk never descends
    into generated / vendored / planning-scratch trees. Returns absolute
    ``Path`` objects sorted for deterministic ordering. A non-directory ``root``
    yields an empty list (fail-soft).
    """
    root_path = Path(root)
    if not root_path.is_dir():
        return []
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root_path):
        # Prune excluded directories in place so os.walk does not descend.
        dirnames[:] = [d for d in dirnames if d not in _EXCLUDED_DIR_NAMES]
        for name in filenames:
            if name in AGENTFILE_NAMES:
                found.append((Path(dirpath) / name).resolve())
    return sorted(found)


def read_text_or_none(path: str | Path) -> str | None:
    """Read a file as UTF-8, returning ``None`` on any read error (fail-soft)."""
    try:
        return Path(path).read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return None


def count_lines(text: str) -> int:
    """Return the number of lines in ``text`` (newline-delimited)."""
    if not text:
        return 0
    return len(text.splitlines())


def _fence_run(stripped: str) -> tuple[str, int]:
    """Return ``(fence_char, run_length)`` for a line's leading fence run.

    A fence run is at least three identical ```` ` ```` or ``~`` characters at
    the start of the (left-stripped) line. Returns ``('', 0)`` when the line is
    not a fence line.
    """
    for ch in ('`', '~'):
        if stripped.startswith(ch * 3):
            return ch, len(stripped) - len(stripped.lstrip(ch))
    return '', 0


def fenced_block_spans(lines: list[str]) -> list[tuple[int, int]]:
    """Return ``(open_idx, close_idx)`` 0-based inclusive ranges of fenced blocks.

    Tracks ```` ``` ```` and ``~~~`` fences per CommonMark closing-fence rules.
    ``open_idx`` is the opening-fence line index and ``close_idx`` is the
    closing-fence line index. An unterminated fence extends to the final line.

    A closing fence must use the same fence character as the opening fence, be at
    least as long as it, and carry no info string (only fence characters plus
    optional trailing whitespace). This means an info-string-bearing fence line
    such as ```` ```python ```` nested inside a block is content, not a close, and
    a ``~~~`` line inside a ```` ``` ```` block likewise does not close it.
    """
    spans: list[tuple[int, int]] = []
    open_idx: int | None = None
    fence_char = ''
    fence_len = 0
    for idx, line in enumerate(lines):
        stripped = line.lstrip()
        ch, run = _fence_run(stripped)
        if open_idx is None:
            if ch:
                open_idx, fence_char, fence_len = idx, ch, run
        elif ch == fence_char and run >= fence_len and stripped.rstrip() == ch * run:
            spans.append((open_idx, idx))
            open_idx = None
            fence_char = ''
            fence_len = 0
    if open_idx is not None:
        spans.append((open_idx, len(lines) - 1))
    return spans


def contains_tree_glyph(text: str) -> bool:
    """Return True if ``text`` contains any directory-tree box-drawing glyph."""
    return any(glyph in text for glyph in _TREE_GLYPHS)
