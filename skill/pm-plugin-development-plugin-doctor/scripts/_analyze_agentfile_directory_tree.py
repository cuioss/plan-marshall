#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Directory-tree backstop rule for always-on agentfiles.

Implements the ``agentfile-directory-tree-present`` analyze-surfaced rule: a
fenced code block that draws the repository's directory structure with
box-drawing characters (``├──``, ``│``, ``└──``) inside an always-on agentfile
(``CLAUDE.md`` at any nesting level, ``AGENTS.md``) is a specific, high-frequency
instance of inert content. An assistant enumerates the project tree far more
reliably by reading the filesystem than by trusting a hand-maintained drawing
that goes stale the instant a file moves.

The anti-pattern and its remediation (delete the tree; demote to a doc if a
structural overview is genuinely wanted) are defined in the shared rubric
(``plan-marshall:ref-agentfile-hygiene`` ``standards/rubric.md`` § "The
directory-tree anti-pattern"); this rule is the deterministic backstop that
points at the cognitive recipe for judgement-based remediation.

Analyze-surfaced only: runs under ``doctor-marketplace.py analyze`` and is
intentionally absent from ``quality-gate``.

Public API
----------
- ``analyze_agentfile_directory_tree(marketplace_root)``
"""

from __future__ import annotations

from pathlib import Path

from _analyze_agentfile_shared import (
    contains_tree_glyph,
    discover_agentfiles,
    fenced_block_spans,
    read_text_or_none,
    repo_root_from_marketplace_root,
)
from _doctor_shared import Finding  # type: ignore[import-not-found]
from _rule_registry import RuleDescriptor

RULE_ID = 'agentfile-directory-tree-present'
RULE_NAME = 'analyze_agentfile_directory_tree'

# Analyze-surfaced agentfile-hygiene backstop (intentionally not in quality-gate).
RULE_DESCRIPTOR = RuleDescriptor(
    rule_id=RULE_ID,
    severity='warning',
    category='content',
    scope='file-local',
)


def _first_glyph_line(lines: list[str], open_idx: int, close_idx: int) -> int | None:
    """Return the 0-based index of the first tree-glyph line inside a fence.

    Scans the inner lines of the fenced block (exclusive of the fence markers)
    and returns the first index carrying a directory-tree glyph, or ``None``
    when the block has no glyph line.
    """
    for idx in range(open_idx + 1, close_idx):
        if contains_tree_glyph(lines[idx]):
            return idx
    return None


def analyze_agentfile_directory_tree(marketplace_root: str | Path) -> list[dict]:
    """Flag every fenced directory-tree drawing inside an always-on agentfile.

    Walks the repo-root agentfile corpus, scans each agentfile's fenced code
    blocks, and emits one finding per fenced block that contains a directory-tree
    box-drawing glyph, anchored at the block's first glyph line.

    Parameters
    ----------
    marketplace_root:
        The ``bundles/`` marketplace root; agentfile discovery anchors at the
        repo root derived from it.

    Returns
    -------
    list[dict]
        One finding dict per offending fenced block (empty for a clean corpus).
    """
    repo_root = repo_root_from_marketplace_root(marketplace_root)
    findings: list[Finding] = []
    for path in discover_agentfiles(repo_root):
        text = read_text_or_none(path)
        if text is None:
            continue
        lines = text.splitlines()
        for open_idx, close_idx in fenced_block_spans(lines):
            glyph_idx = _first_glyph_line(lines, open_idx, close_idx)
            if glyph_idx is None:
                continue
            findings.append(
                Finding(
                    type=RULE_ID,
                    file=str(path),
                    line=glyph_idx + 1,
                    severity='warning',
                    fixable=False,
                    rule_id=RULE_ID,
                    description=(
                        'Fenced directory-tree drawing in an always-on agentfile '
                        '— delete it (inert content the assistant reads more '
                        'reliably from the filesystem). See rule-catalog.md and '
                        'recipe-agentfile-hygiene.'
                    ),
                    extra={'rule': RULE_NAME, 'snippet': lines[glyph_idx].strip()},
                )
            )
    return [f.to_dict() for f in findings]
