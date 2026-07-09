#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Triage-FIX not-done/STOP contract analyzer (build-failing under ``quality-gate``).

The Step 3c FIX action of the consolidated triage workflow (``triage.md``) is
allowed to do exactly two things and then STOP: allocate the fix task in a
NOT-done state (``prepare-add`` → ``commit-add``) and resolve the finding
``fixed`` with a reviewer-ready ``resolution_detail``. Execution, testing, and
commit of the fix are owned by phase-5-execute, which the ``loop_back`` this FIX
raises re-enters. A created not-done task and a completed-but-uncommitted
working-tree change are **mutually-exclusive returns**: triage returns the
not-done task, and the re-entered execute phase produces the committed change.

The structural failure mode is *implement-then-mark-done*: if the FIX body
implements the fix and marks its task done inline, the change is stranded behind
a done task and the ``loop_back`` becomes a no-op — the re-entered execute phase
finds nothing pending to drive, so the fix never reaches a commit on the branch.

This analyzer is the static backstop for that contract. It flags a triage-FIX
surface's FIX action body when EITHER:

- **(a) inline done-marking** — an actual done-marking *call shape*
  (``mark-step-done``, ``--outcome done``, ``--status done``) appears inside the
  FIX body region, i.e. the body marks its fix task done inline; OR
- **(b) missing directive triad** — the FIX body omits any member of the
  required ``not-done`` / ``loop_back`` / ``STOP`` directive triad, so the
  contract that keeps FIX from executing the fix inline is unstated.

Deliberately narrow detection
-----------------------------
Detection matches the SITED directive tokens, never the placeholder/wildcard
forms docs use when merely DESCRIBING the contract. In particular, the inline
done-marking condition (a) matches only unambiguous done-marking *call shapes* —
NOT prose "mark ... done". Prose is deliberately excluded because the contract
ITSELF requires the FIX body to describe the failure mode in prose ("... marking
its task done inline strands the change ..."), and a naive prose match would flag
the very doc that correctly states the contract. The finding-resolution calls the
FIX body legitimately makes (``manage-findings resolve --resolution fixed``,
``prepare-add`` / ``commit-add``) resolve the FINDING or allocate the task
not-done — they are never done-marking call shapes and are never matched.

Pattern alignment
-----------------
Mirrors ``_analyze_triage_read_surface.py``: pure static regex analysis,
stdlib-only, no target-script imports, no file mutation. Builds uniform
:class:`Finding` objects and exposes a module-level ``RULE_DESCRIPTOR`` collected
by the central registry.

Triage-FIX surface
------------------
A file is a triage-FIX surface when its basename is ``triage.md`` (the
consolidated triage workflow doc that carries the Step 3c FIX action body) AND it
contains a FIX action body region whose defining signature — a fix-task
allocation call (``prepare-add`` / ``commit-add``) — is present. Requiring the
allocation signature pins the scan to the actual disposition-FIX action, so an
unrelated ``triage.md`` that merely mentions a FIX bullet without the Step 3c
allocation flow is never scanned.

Public API
----------
- ``analyze_triage_fix_not_done_surface(marketplace_root)``: entry point — scans
  every triage-FIX surface under the bundles root and returns a finding per
  offending FIX body (empty list for a clean tree).
"""

from __future__ import annotations

import re
from pathlib import Path

from _doctor_shared import Finding
from _rule_registry import RuleDescriptor

RULE_ID = 'triage-fix-not-done-contract'
RULE_NAME = 'analyze_triage_fix_not_done_surface'
FINDING_TYPE = 'triage_fix_not_done_contract'

RULE_DESCRIPTOR = RuleDescriptor(
    rule_id=RULE_ID,
    severity='error',
    category='safety',
    scope='file-local',
)

# The consolidated triage workflow doc, identified by basename.
_TRIAGE_DOC_BASENAME = 'triage.md'

# The FIX action bullet that opens the Step 3c FIX action body. Matches the
# literal ``- **FIX**`` marker at the head of a top-level list item; the
# ``-here anyway`` variant (``**FIX-here anyway**``) never matches the exact
# ``**FIX**`` token.
_FIX_BULLET_RE = re.compile(r'^-\s+\*\*FIX\*\*')

# A subsequent top-level action bullet (``- **SUPPRESS**`` / ``- **ACCEPT**`` /
# ``- **AskUserQuestion**``) or a section heading ends the FIX body region.
_TOP_LEVEL_BULLET_RE = re.compile(r'^-\s+\*\*')
_HEADING_RE = re.compile(r'^#{1,6}\s')

# The fix-task allocation signature that defines the Step 3c FIX action. Its
# presence in the region confirms the FIX bullet is the disposition-FIX action
# (allocate not-done task) rather than an unrelated FIX mention.
_ALLOCATION_RE = re.compile(r'\b(?:prepare-add|commit-add)\b')

# Inline done-marking CALL SHAPES — an actual done-marking directive, not prose.
# These are unambiguous: they only appear when the FIX body instructs marking
# the fix task (or its step) done inline. Prose "mark ... done" is deliberately
# NOT matched (see module docstring).
_INLINE_DONE_CALL_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r'mark-step-done'),
    re.compile(r'--outcome\s+done'),
    re.compile(r'--status\s+done'),
)

# The required directive triad tokens. Each token is matched in its SITED form.
# ``STOP`` is matched case-sensitively (uppercase) so an incidental lowercase
# "stop" never satisfies the token; ``not-done`` / ``loop_back`` tolerate the
# common separator spellings.
_NOT_DONE_RE = re.compile(r'not[-\s]?done', re.IGNORECASE)
_LOOP_BACK_RE = re.compile(r'loop[_\s-]?back', re.IGNORECASE)
_STOP_RE = re.compile(r'\bSTOP\b')


def _is_triage_fix_doc(path: Path) -> bool:
    """Return True when ``path`` is the consolidated triage workflow doc by basename."""
    return path.name == _TRIAGE_DOC_BASENAME


def _find_fix_region(lines: list[str]) -> tuple[int, int] | None:
    """Return the ``[start, end)`` line-index span of the Step 3c FIX action body.

    The region opens at the ``- **FIX**`` bullet and closes at the next
    top-level action bullet, the next section heading, or end-of-file. Returns
    ``None`` when no FIX bullet is present, or when the region lacks the
    fix-task allocation signature (``prepare-add`` / ``commit-add``) that
    identifies the disposition-FIX action — so unrelated FIX mentions are not
    treated as the contract-bearing body.
    """
    start = None
    for index, line in enumerate(lines):
        if _FIX_BULLET_RE.match(line):
            start = index
            break
    if start is None:
        return None

    end = len(lines)
    for index in range(start + 1, len(lines)):
        line = lines[index]
        if _TOP_LEVEL_BULLET_RE.match(line) or _HEADING_RE.match(line):
            end = index
            break

    region_text = '\n'.join(lines[start:end])
    if not _ALLOCATION_RE.search(region_text):
        return None
    return start, end


def _inline_done_line(line: str) -> bool:
    """Return True when ``line`` carries an inline done-marking call shape."""
    return any(pattern.search(line) for pattern in _INLINE_DONE_CALL_PATTERNS)


def _has_triad(region_text: str) -> bool:
    """Return True when the FIX body carries the full not-done/loop_back/STOP triad."""
    return bool(
        _NOT_DONE_RE.search(region_text)
        and _LOOP_BACK_RE.search(region_text)
        and _STOP_RE.search(region_text)
    )


def _scan_file(path: Path) -> list[Finding]:
    """Scan one triage-FIX doc and emit findings for an offending FIX action body."""
    try:
        text = path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return []

    lines = text.splitlines()
    region = _find_fix_region(lines)
    if region is None:
        return []
    start, end = region
    region_lines = lines[start:end]
    region_text = '\n'.join(region_lines)

    findings: list[Finding] = []

    # (a) inline done-marking — one finding per offending line.
    for offset, line in enumerate(region_lines):
        if not _inline_done_line(line):
            continue
        findings.append(
            Finding(
                type=FINDING_TYPE,
                file=str(path),
                line=start + offset + 1,
                severity='error',
                fixable=False,
                rule_id=RULE_ID,
                description=(
                    'triage Step 3c FIX action body marks its fix task done inline '
                    '(a mark-step-done / --outcome done / --status done call shape) — '
                    'FIX MUST allocate the fix task not-done and STOP; execution and '
                    'commit are owned by phase-5-execute, re-entered by the loop_back '
                    'this FIX raises. Marking the task done inline strands the change '
                    'behind a done task and makes the loop_back a no-op. See the '
                    'Not-done / STOP contract in triage.md Step 3c.'
                ),
                extra={'rule': RULE_NAME, 'snippet': line.strip()[:120]},
            )
        )

    # (b) missing directive triad — one finding anchored at the FIX bullet.
    if not _has_triad(region_text):
        findings.append(
            Finding(
                type=FINDING_TYPE,
                file=str(path),
                line=start + 1,
                severity='error',
                fixable=False,
                rule_id=RULE_ID,
                description=(
                    'triage Step 3c FIX action body omits the required not-done / '
                    'loop_back / STOP directive triad — the contract that keeps FIX '
                    'from executing the fix inline is unstated and unenforceable. Add '
                    'the Not-done / STOP contract stating that FIX allocates the fix '
                    'task not-done, resolves the finding fixed, then STOPS (never '
                    'implement/test/mark-done inline; execution and commit are owned '
                    'by phase-5-execute re-entered by the loop_back).'
                ),
                extra={'rule': RULE_NAME},
            )
        )

    return findings


def analyze_triage_fix_not_done_surface(marketplace_root: Path) -> list[dict]:
    """Flag every triage-FIX surface under ``marketplace_root`` that violates the contract.

    ``marketplace_root`` is the bundles root (the directory that contains
    ``plan-marshall``, ``pm-plugin-development``, etc.). Walks every ``triage.md``
    file, keeps the triage-FIX surfaces (see module docstring), and returns a
    finding per offending FIX action body — one per inline-done line and/or one
    for a missing directive triad. Returns an empty list when the tree is absent;
    unreadable files are skipped silently.
    """
    marketplace_root = Path(marketplace_root)
    if not marketplace_root.is_dir():
        return []

    findings: list[Finding] = []
    for md_path in sorted(marketplace_root.rglob('*.md')):
        if not _is_triage_fix_doc(md_path):
            continue
        findings.extend(_scan_file(md_path))
    return [f.to_dict() for f in findings]
