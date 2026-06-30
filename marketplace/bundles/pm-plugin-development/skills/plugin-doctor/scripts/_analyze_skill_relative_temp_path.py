#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Relative-``.plan/temp`` path scanner for the ``skill-relative-temp-path-git-c`` rule.

This module implements a deterministic regex-based static analyzer that
detects a **relative** ``.plan/temp/...`` path token consumed by a
``git -C ... commit -F`` command inside fenced ``bash``/``sh`` blocks in
skill/agent/command markdown files.

The canonical violation example (from the source bug) is:

.. code-block:: text

    git -C {worktree_path} commit -F .plan/temp/{plan_id}-commit-msg.txt

The harness ``Write`` tool resolves a relative ``.plan/temp/...`` path against
the MAIN checkout, while ``git -C {worktree_path}`` resolves the same relative
path against the WORKTREE.  The two legs reference two different files on disk,
so the commit reads a stale (previous deliverable's) or empty message instead
of the one just authored.  The fix is to make BOTH legs reference the same
worktree-ABSOLUTE ``{worktree_path}/.plan/temp/...`` path.

The rule mirrors ``_analyze_tmp_redirect_in_skills.py``:

- pure static analysis (no subprocess execution, no imports of target scripts)
- regex-driven extraction from fenced ``bash``/``sh`` blocks only
- stdlib-only dependencies
- no mutation of any file

Detection
---------
Inside every fenced block whose info-string is ``bash`` or ``sh``, the
analyzer looks for a ``git -C ... commit -F`` command whose ``-F`` argument is
a **relative** ``.plan/temp/...`` path (a token that begins with ``.plan/temp/``
immediately after ``-F``, i.e. with no ``{worktree_path}/`` / absolute / other
prefix).  The worktree-absolute form ``-F {worktree_path}/.plan/temp/...`` does
NOT match because the path token after ``-F`` starts with ``{worktree_path}/``,
not ``.plan/temp/``.

Structural exemptions (mirroring ``tmp-redirect-in-skills``):

1. **Lines outside bash/sh fenced blocks** — only lines inside fenced blocks
   whose info-string is ``bash`` or ``sh`` are scanned.

2. **Comment lines** — lines whose first non-whitespace character is ``#`` are
   skipped.

This analyzer scopes its scan to bash/sh fences (it defines
``_BASH_FENCE_INFO_STRINGS``) and therefore carries NO markdown inline-code
exemption — inside a bash fence a backtick span denotes command substitution,
not a markdown inline-code span (enforced by the
``bash-fence-inline-code-exemption`` reintroduction guard).

Findings have the shape::

    {
        'rule_id': 'skill-relative-temp-path-git-c',
        'type': 'skill_relative_temp_path_git_c',
        'rule': 'analyze_skill_relative_temp_path',
        'file': '<absolute markdown path>',
        'line': <int, 1-based>,
        'severity': 'warning',
        'fixable': False,
        'temp_path': '<the relative .plan/temp/... token>',
        'snippet': '<offending text excerpt>',
        'description': '<short human-readable explanation>',
    }

Public API
----------
- ``analyze_skill_relative_temp_path(marketplace_root)``: entry point — scans
  every ``*.md`` under ``marketplace_root/plan-marshall/{skills,agents,commands}/``.
"""

from __future__ import annotations

import re
from pathlib import Path

from _doctor_shared import Finding  # type: ignore[import-not-found]

RULE_ID = 'skill-relative-temp-path-git-c'
RULE_NAME = 'analyze_skill_relative_temp_path'
FINDING_TYPE = 'skill_relative_temp_path_git_c'

# ---------------------------------------------------------------------------
# Detection patterns
# ---------------------------------------------------------------------------

_FENCE_OPEN_RE = re.compile(r'^\s*```\s*([A-Za-z0-9_+-]*)\s*$')
_FENCE_CLOSE_RE = re.compile(r'^\s*```\s*$')

_BASH_FENCE_INFO_STRINGS = frozenset({'bash', 'sh'})

# Match a ``git -C <something> commit ... -F`` invocation whose ``-F`` argument
# is a RELATIVE ``.plan/temp/...`` path. The path token starts with
# ``.plan/temp/`` immediately after ``-F`` (group 1 captures the path token up
# to the next whitespace). The worktree-absolute form
# ``-F {worktree_path}/.plan/temp/...`` does NOT match because the token after
# ``-F`` then starts with ``{worktree_path}/`` rather than ``.plan/temp/``.
_GIT_COMMIT_RELATIVE_TEMP_RE = re.compile(
    r'git\s+-C\s+\S+.*\bcommit\b.*\s-F\s+(\.plan/temp/\S+)'
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_fence_map(lines: list[str]) -> dict[int, str]:
    """Map 0-based line indices inside any fenced block to the info-string."""
    inside: dict[int, str] = {}
    in_fence = False
    info_string = ''
    for idx, line in enumerate(lines):
        if not in_fence:
            m = _FENCE_OPEN_RE.match(line)
            if m:
                in_fence = True
                info_string = m.group(1).lower()
        else:
            if _FENCE_CLOSE_RE.match(line):
                in_fence = False
                info_string = ''
            else:
                inside[idx] = info_string
    return inside


def _is_comment_line(line: str) -> bool:
    """Return ``True`` if the line is a shell comment (first non-ws char is ``#``)."""
    return line.lstrip().startswith('#')


def _make_finding(
    path: Path,
    line_no: int,
    temp_path: str,
    line: str,
    offset: int,
) -> dict:
    start = max(0, offset - 30)
    end = min(len(line), offset + 50)
    snippet = line[start:end]
    return Finding(
        type=FINDING_TYPE,
        file=str(path),
        line=line_no,
        severity='warning',
        fixable=False,
        rule_id=RULE_ID,
        description=(
            f'Relative ``.plan/temp`` path ``{temp_path}`` consumed by '
            '``git -C ... commit -F`` in skill markdown. The harness ``Write`` '
            'tool resolves a relative ``.plan/temp`` path against the main '
            'checkout while ``git -C {worktree_path}`` resolves it against the '
            'worktree, so a relative-path round-trip references two different '
            'files and the commit may read a stale message. Use the '
            'worktree-absolute ``{worktree_path}/.plan/temp/...`` form on BOTH '
            'the ``Write`` call and the ``git commit -F``.'
        ),
        extra={'rule': RULE_NAME, 'temp_path': temp_path, 'snippet': snippet},
    ).to_dict()


# ---------------------------------------------------------------------------
# File-level scanner
# ---------------------------------------------------------------------------


def _scan_file(path: Path) -> list[dict]:
    """Scan a single markdown file and return all findings."""
    try:
        text = path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError) as exc:
        return [
            Finding(
                type='file_read_error',
                file=str(path),
                line=0,
                severity='error',
                fixable=False,
                rule_id=RULE_ID,
                description=f'Could not read file: {exc}',
                extra={'rule': RULE_NAME, 'temp_path': '', 'snippet': ''},
            ).to_dict()
        ]

    lines = text.splitlines()
    fence_map = _build_fence_map(lines)
    findings: list[dict] = []

    for idx, line in enumerate(lines):
        fence_info = fence_map.get(idx)
        if fence_info not in _BASH_FENCE_INFO_STRINGS:
            continue

        if _is_comment_line(line):
            continue

        for m in _GIT_COMMIT_RELATIVE_TEMP_RE.finditer(line):
            temp_path = m.group(1)
            findings.append(_make_finding(path, idx + 1, temp_path, line, m.start(1)))

    return findings


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def _markdown_targets(marketplace_root: Path) -> list[Path]:
    """Return every ``*.md`` under plan-marshall skills, agents, and commands."""
    targets: list[Path] = []
    bundle = marketplace_root / 'plan-marshall'
    for subdir in ('skills', 'agents', 'commands'):
        root = bundle / subdir
        if root.is_dir():
            targets.extend(sorted(p for p in root.rglob('*.md') if p.is_file()))
    return targets


def analyze_skill_relative_temp_path(marketplace_root: Path) -> list[dict]:
    """Scan plan-marshall skill/agent/command markdown for relative-temp + git -C.

    Walks ``marketplace_root/plan-marshall/{skills,agents,commands}/**/*.md``
    and reports every relative ``.plan/temp/...`` path token consumed by a
    ``git -C ... commit -F`` command inside a fenced ``bash`` or ``sh`` block.

    Parameters
    ----------
    marketplace_root:
        Path to the marketplace root (the directory that contains the
        ``plan-marshall``, ``pm-dev-java``, etc. bundle directories — i.e.
        ``<repo>/marketplace/bundles``).

    Returns
    -------
    list[dict]
        List of finding dicts (empty for a clean tree).
    """
    findings: list[dict] = []
    for md_path in _markdown_targets(marketplace_root):
        findings.extend(_scan_file(md_path))
    return findings
