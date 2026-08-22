#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Detector for the ``shim-marker-missing`` rule: unmarked / malformed migration shims.

A migration or back-compat *version shim* is a code path that reads persisted
state/config/data and accommodates a shape an EARLIER version of this tooling
once wrote and the current version no longer writes. The convention
(``pm-plugin-development:plugin-script-architecture`` ->
``standards/shim-marker-convention.md``) requires every shim to declare, at its
definition site, an owner, a version floor, and a removal trigger via a marker::

    # SHIM(B): <one-line description of the old shape>
    # shim-owner: <skill dir name>
    # shim-floor: <the change that retired the old shape>
    # shim-remove-when: <concrete condition under which no old-shape data remains>

This analyzer is the edit-time guard for that convention. It emits two kinds of
finding:

* ``shim_marker_malformed`` — a marker anchor is present but not conforming: the
  category is not ``A``/``B``, the description is empty, or one of the three
  required field lines (``shim-owner`` / ``shim-floor`` / ``shim-remove-when``)
  is missing or empty. Zero false positives by construction — it only fires on a
  comment the author already wrote as a marker.
* ``shim_unmarked`` — a high-precision shim INDICATOR appears in a code comment
  that is NOT covered by a conforming marker in its enclosing function. This is
  the "next shim landed unmarked" guard.

Population — derived, never hand-listed
---------------------------------------
The population is every ``*.py`` under ``marketplace_root/*/skills/*/scripts/`` —
the executable-tooling source tree. Nothing is hardcoded; a script added
tomorrow is scanned the moment it lands. Every finding publishes
``details.population_size`` (scripts scanned), and an EMPTY population over a
non-empty bundles tree emits its own ``reason: empty_population`` finding, so a
clean result can never read as a vacuous pass over an unread population.

Detection — the false-positive boundary is the hard part
--------------------------------------------------------
Prose vocabulary cannot cleanly separate a shim from ordinary defensive code:
"legacy", "written before", "backward compatibility" and "pre-dating" all appear
in BOTH real shims and non-shims (defensive ``None``-handling, CLI/env-var
compatibility, external-system variance, and deliberate breaking refusals of the
old shape). So the indicator set is deliberately NARROW — it favours a false
negative over a false positive (a detector that fires on defensive code is a
regression, not a win). It matches only compound phrases that, in this tree,
occur when DESCRIBING a shim's tolerated old shape and not when describing
defensive code: e.g. ``pre-migration``, ``legacy bare-string``, ``retired ...
knob/key``, ``older format``, ``self-disarming``, ``supports both formats for
backward ...``, ``accepted for backward ...``, ``pre-home-root``, ``Pre-PR#...``.
The narrowness is by design: the marker convention plus human review carry the
recall; this rule is the backstop that keeps the clearest cases from slipping
through unmarked.

The scan reads COMMENT tokens only (via :mod:`tokenize`), never docstrings or
string literals — so this module's own regex phrases (string literals) and any
doc examples (docstrings) are never mistaken for markers or indicators, and the
detector does not flag itself.

Findings have the shape::

    {
        'rule_id': 'shim-marker-missing',
        'type': 'shim_unmarked' | 'shim_marker_malformed',
        'rule': 'analyze_shim_marker',
        'file': '<absolute script path>',
        'line': <int, 1-based>,
        'severity': 'error',
        'fixable': False,
        'details': {'population_size': <int>, ...},
        'snippet': '<matched comment text>',
        'message': '<human-readable description>',
    }

Public API
----------
- ``enumerate_script_files(marketplace_root)``: the derived population.
- ``analyze_shim_marker(marketplace_root)``: entry point.
"""

from __future__ import annotations

import ast
import io
import re
import tokenize
from pathlib import Path

from _doctor_shared import Finding
from _rule_registry import RuleDescriptor

RULE_ID = 'shim-marker-missing'
RULE_NAME = 'analyze_shim_marker'
UNMARKED_TYPE = 'shim_unmarked'
MALFORMED_TYPE = 'shim_marker_malformed'
EMPTY_POPULATION_TYPE = 'shim_marker_population_empty'
# A member of the derived population that could not be READ. It is counted in
# ``population_size``, so silently returning no findings for it would let the
# published figure claim coverage the scan never obtained — this rule's own
# subject, one level down. Reported rather than skipped.
UNREADABLE_TYPE = 'shim_marker_target_unreadable'

RULE_DESCRIPTOR = RuleDescriptor(
    rule_id=RULE_ID,
    severity='error',
    category='content',
    scope='corpus-relational',
)

# The convention doc that DEFINES this rule. Its presence is the anchor for the
# empty-population guard: a tree that carries the convention but derives zero
# scripts has a broken derivation (the vacuity archetype), whereas a minimal or
# fixture tree that does not carry the convention legitimately has no population
# and is not flagged. Mirrors the 040 analyzer's ext-point-standard anchor.
_CONVENTION_DOC_REL = (
    'pm-plugin-development/skills/plugin-script-architecture/standards/shim-marker-convention.md'
)

# --- Marker grammar -------------------------------------------------------
# A conforming anchor: "# SHIM(A):" or "# SHIM(B):" followed by a non-empty
# description. The three required field lines follow as further comment lines.
_ANCHOR_OK = re.compile(r'^#\s*SHIM\s*\(\s*([AB])\s*\)\s*:\s*(\S.*)$')
# A marker ATTEMPT — a comment whose ``SHIM`` token is immediately followed by
# ``(`` or ``:``. This catches malformed anchors ("# SHIM:", "# SHIM(C):",
# "# SHIM()") that fail _ANCHOR_OK, while never matching prose that merely uses
# the word (e.g. "the SHIM markers are ..." — ``SHIM`` is followed by a space
# and a letter, not ``(`` / ``:``).
_ANCHOR_ATTEMPT = re.compile(r'^#\s*SHIM\s*[:(]')
_FIELD_OWNER = re.compile(r'^#\s*shim-owner\s*:\s*(\S.*)$')
_FIELD_FLOOR = re.compile(r'^#\s*shim-floor\s*:\s*(\S.*)$')
_FIELD_REMOVE = re.compile(r'^#\s*shim-remove-when\s*:\s*(\S.*)$')

# --- Indicator vocabulary -------------------------------------------------
# Narrow, high-precision, case-insensitive. Each phrase, in this tree, occurs
# when describing a shim's tolerated old shape and NOT in the known non-shim
# comment corpus (defensive None-handling, CLI/env compat, external variance,
# breaking refusals). See the module docstring for the false-positive rationale.
#
# Deliberately EXCLUDED, because they also occur in non-shim code and would
# false-positive: a bare retired-key phrase (a write-side guard that REJECTS an
# unknown or retired key is not a shim), and a credentials-dir migration phrase
# (a caller comment that merely triggers a migration is not itself the shim).
# Recall for a self-clearing migration is carried by its own disarm-describing
# phrase in the set below; a permanent tolerate path by the shape phrases.
# Missing a subtle migration is an accepted false negative (precision over
# recall, per the convention). NOTE: this module is itself in the scanned
# population, so its own comments avoid spelling active indicator phrases; those
# live only in the docstring and the regex literals above (both string tokens).
_INDICATORS: tuple[re.Pattern, ...] = (
    re.compile(r'pre-?migration', re.IGNORECASE),
    re.compile(r'legacy[ _]bare-?string', re.IGNORECASE),
    re.compile(r'legacy_string_entry', re.IGNORECASE),
    re.compile(r'legacy list-of-', re.IGNORECASE),
    re.compile(r'self-disarming', re.IGNORECASE),
    re.compile(r'older format\b', re.IGNORECASE),
    re.compile(r'supports both formats for backward', re.IGNORECASE),
    re.compile(r'accepted for backward', re.IGNORECASE),
    re.compile(r'pre-pr#?\s*\d', re.IGNORECASE),
)

# Coverage window for a module-level marker (one sitting above a constant, not
# inside or immediately above a function): it covers a block of comment lines
# below itself and a leading comment block just above itself (a marker is often
# placed at the foot of the block that describes the shim).
_MODULE_COVER_DOWN = 60
_MODULE_COVER_UP = 20
# Gap within which a marker anchor is treated as sitting "immediately above" a
# ``def``, so it covers that whole function span. A conforming marker block is
# 4 lines (the anchor plus three field lines), so a marker placed directly above
# a ``def`` puts that ``def`` 4 lines below the anchor; the gap must therefore be
# at least 4 (5 allows one blank line between the block and the ``def``).
# Otherwise the ``def`` is missed and coverage falls back to a fixed window,
# which can leave an indicator deep in a long function body uncovered.
_ABOVE_DEF_GAP = 5


# ---------------------------------------------------------------------------
# Population derivation
# ---------------------------------------------------------------------------


def enumerate_script_files(marketplace_root: Path) -> list[Path]:
    """Return every ``*.py`` under ``marketplace_root/*/skills/*/scripts/``.

    The population is derived from the tree structure; nothing is hardcoded.
    Returns the paths in sorted order (empty when the tree is absent).
    """
    marketplace_root = Path(marketplace_root)
    if not marketplace_root.is_dir():
        return []
    scripts: list[Path] = []
    for bundle_dir in sorted(marketplace_root.iterdir()):
        if not bundle_dir.is_dir() or bundle_dir.name.startswith('.'):
            continue
        skills_dir = bundle_dir / 'skills'
        if not skills_dir.is_dir():
            continue
        for skill_dir in sorted(skills_dir.iterdir()):
            if not skill_dir.is_dir() or skill_dir.name.startswith('.'):
                continue
            scripts_dir = skill_dir / 'scripts'
            if not scripts_dir.is_dir():
                continue
            scripts.extend(sorted(scripts_dir.rglob('*.py')))
    return scripts


# ---------------------------------------------------------------------------
# Source parsing — comments and function spans
# ---------------------------------------------------------------------------


def _comment_lines(text: str) -> list[tuple[int, str]]:
    """Return ``(1-based line, stripped comment text)`` for every COMMENT token.

    Uses :mod:`tokenize` so a ``#`` inside a string literal is never mistaken
    for a comment. Returns ``[]`` when the source cannot be tokenized (a file
    that will not tokenize cannot be scanned).
    """
    comments: list[tuple[int, str]] = []
    try:
        tokens = tokenize.generate_tokens(io.StringIO(text).readline)
        for tok in tokens:
            if tok.type == tokenize.COMMENT:
                comments.append((tok.start[0], tok.string.strip()))
    except (tokenize.TokenError, IndentationError, SyntaxError, ValueError):
        return []
    return comments


def _function_spans(text: str) -> list[tuple[int, int]]:
    """Return ``(start_line, end_line)`` (1-based, inclusive) for every function.

    Uses :mod:`ast`, so spans are exact (including nested functions). Returns
    ``[]`` when the source will not parse.
    """
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return []
    spans: list[tuple[int, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end = getattr(node, 'end_lineno', None) or node.lineno
            spans.append((node.lineno, end))
    return spans


def _innermost_span(line: int, spans: list[tuple[int, int]]) -> tuple[int, int] | None:
    """Return the smallest function span containing ``line``, or ``None``."""
    best: tuple[int, int] | None = None
    for start, end in spans:
        if start <= line <= end:
            if best is None or (end - start) < (best[1] - best[0]):
                best = (start, end)
    return best


def _marker_cover(anchor_line: int, spans: list[tuple[int, int]]) -> tuple[int, int]:
    """Return the ``(lo, hi)`` line range a marker at ``anchor_line`` covers.

    A marker inside a function covers that function (plus a few lines above, to
    reach a leading comment block just outside the ``def``). A marker sitting
    just above a ``def`` covers that function. Otherwise (a module-level marker
    above a constant) it covers a window above and below itself, since the block
    that describes the shim commonly sits just above the marker.
    """
    enclosing = _innermost_span(anchor_line, spans)
    if enclosing is not None:
        lo = min(enclosing[0], anchor_line) - _ABOVE_DEF_GAP
        return (max(1, lo), enclosing[1])
    # Immediately above a def? Cover that function (and the small gap to it).
    following = [s for s in spans if anchor_line < s[0] <= anchor_line + _ABOVE_DEF_GAP]
    if following:
        target = min(following, key=lambda s: s[0])
        return (max(1, anchor_line - _MODULE_COVER_UP), target[1])
    return (max(1, anchor_line - _MODULE_COVER_UP), anchor_line + _MODULE_COVER_DOWN)


# ---------------------------------------------------------------------------
# Marker-block parsing
# ---------------------------------------------------------------------------


class _Marker:
    """A parsed ``# SHIM`` marker block: its anchor line, validity, and cover."""

    __slots__ = ('anchor_line', 'malformed_reason', 'cover')

    def __init__(self, anchor_line: int, malformed_reason: str | None, cover: tuple[int, int]):
        self.anchor_line = anchor_line
        self.malformed_reason = malformed_reason
        self.cover = cover


def _parse_markers(
    comments: list[tuple[int, str]], spans: list[tuple[int, int]]
) -> list[_Marker]:
    """Parse marker blocks from the comment stream.

    A block begins at an anchor-attempt comment. A conforming block has an
    ``# SHIM(A|B): <desc>`` anchor followed — within the run of consecutive
    comment lines — by non-empty ``shim-owner`` / ``shim-floor`` /
    ``shim-remove-when`` field lines. Anything else is malformed.
    """
    markers: list[_Marker] = []
    for idx, (line, body) in enumerate(comments):
        if not _ANCHOR_ATTEMPT.match(body):
            continue
        cover = _marker_cover(line, spans)
        ok = _ANCHOR_OK.match(body)
        if not ok:
            markers.append(_Marker(line, 'anchor not of form `# SHIM(A|B): <description>`', cover))
            continue
        # Collect the contiguous comment lines belonging to this block: the
        # anchor plus every following comment on consecutive source lines.
        block_bodies: list[str] = []
        cursor_line = line
        for follow_line, follow_body in comments[idx + 1 :]:
            if follow_line != cursor_line + 1:
                break
            # Stop the block at the next anchor attempt (a new marker).
            if _ANCHOR_ATTEMPT.match(follow_body):
                break
            block_bodies.append(follow_body)
            cursor_line = follow_line
        has_owner = any(_FIELD_OWNER.match(b) for b in block_bodies)
        has_floor = any(_FIELD_FLOOR.match(b) for b in block_bodies)
        has_remove = any(_FIELD_REMOVE.match(b) for b in block_bodies)
        missing = [
            name
            for name, present in (
                ('shim-owner', has_owner),
                ('shim-floor', has_floor),
                ('shim-remove-when', has_remove),
            )
            if not present
        ]
        reason = f'marker missing required field(s): {", ".join(missing)}' if missing else None
        markers.append(_Marker(line, reason, cover))
    return markers


# ---------------------------------------------------------------------------
# File scanner
# ---------------------------------------------------------------------------


def _scan_file(path: Path, population_size: int) -> list[dict]:
    """Scan one script for malformed markers and unmarked shim indicators.

    An unreadable member is REPORTED, never skipped. It was enumerated into the
    population and is counted in ``population_size``, so returning ``[]`` for it
    made the published figure assert coverage over a file whose bytes were never
    read — exactly the vacuity this rule exists to detect, committed by the rule
    itself.
    """
    try:
        text = path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError) as exc:
        return [
            _finding(
                UNREADABLE_TYPE,
                path,
                0,
                population_size,
                snippet='',
                message=(
                    f'This script is in the derived shim-marker population but could '
                    f'not be read ({type(exc).__name__}), so it was NOT scanned. It is '
                    f'counted in population_size, so the coverage figure would '
                    f'otherwise overstate what was examined.'
                ),
                reason='unreadable_target',
            )
        ]
    if 'SHIM' not in text and not _text_has_indicator(text):
        return []

    comments = _comment_lines(text)
    if not comments:
        return []
    spans = _function_spans(text)
    markers = _parse_markers(comments, spans)

    findings: list[dict] = []

    for marker in markers:
        if marker.malformed_reason is not None:
            findings.append(
                _finding(
                    MALFORMED_TYPE,
                    path,
                    marker.anchor_line,
                    population_size,
                    snippet='',
                    message=(
                        f'Malformed shim marker: {marker.malformed_reason}. A shim marker '
                        f'must be `# SHIM(A|B): <description>` followed by non-empty '
                        f'`# shim-owner:`, `# shim-floor:`, and `# shim-remove-when:` lines. '
                        f'See shim-marker-convention.md.'
                    ),
                )
            )

    covers = [m.cover for m in markers if m.malformed_reason is None]
    for line, body in comments:
        matched = next((ind.search(body) for ind in _INDICATORS if ind.search(body)), None)
        if matched is None:
            continue
        if any(lo <= line <= hi for lo, hi in covers):
            continue
        findings.append(
            _finding(
                UNMARKED_TYPE,
                path,
                line,
                population_size,
                snippet=body[:120],
                message=(
                    f'Comment reads as a migration/back-compat shim '
                    f'(`{matched.group(0)}`) but the enclosing code carries no '
                    f'`# SHIM(A|B):` marker declaring an owner, version floor, and '
                    f'removal trigger. Add a conforming marker, or — if this is '
                    f'ordinary defensive/CLI/external handling, not a version shim — '
                    f'reword the comment. See shim-marker-convention.md.'
                ),
            )
        )
    return findings


def _text_has_indicator(text: str) -> bool:
    """Cheap pre-filter: does the raw text contain any indicator at all?"""
    return any(ind.search(text) for ind in _INDICATORS)


def _finding(
    finding_type: str,
    path: Path,
    line: int,
    population_size: int,
    *,
    snippet: str,
    message: str,
    reason: str | None = None,
) -> dict:
    """Build one finding dict via the shared :class:`Finding` record."""
    details: dict = {'population_size': population_size}
    if reason is not None:
        details['reason'] = reason
    return Finding(
        type=finding_type,
        file=str(path),
        line=line,
        severity='error',
        fixable=False,
        rule_id=RULE_ID,
        details=details,
        extra={'rule': RULE_NAME, 'snippet': snippet, 'message': message},
    ).to_dict()


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def analyze_shim_marker(marketplace_root: Path) -> list[dict]:
    """Scan the script population for unmarked / malformed migration shims.

    Derives the population (:func:`enumerate_script_files`), scans each script's
    comments, and returns finding dicts. Every finding publishes the
    ``population_size`` examined; an EMPTY population over a non-empty bundles
    tree emits its own finding so a clean result can never read as a vacuous
    pass over an unread population.

    A CLEAN run carries no findings and therefore no ``population_size`` — which
    is the only state a passing gate is ever in. Callers that need the figure on
    a clean run take :func:`analyze_shim_marker_with_population` instead.
    """
    return analyze_shim_marker_with_population(marketplace_root)[0]


def analyze_shim_marker_with_population(marketplace_root: Path) -> tuple[list[dict], int]:
    """Return ``(findings, population_size)`` from a single derivation.

    The runner publishes the examined population in its rule summaries, and it
    must not re-derive the roster to get the number: a second walk is a second
    chance to disagree with the one the findings were actually produced from.
    """
    marketplace_root = Path(marketplace_root)
    population = enumerate_script_files(marketplace_root)
    population_size = len(population)

    if population_size == 0:
        # Anti-vacuity guard: zero scripts is a finding ONLY when this tree
        # actually carries the convention (the standard doc exists), which means
        # scripts are expected — a broken derivation, the archetype this epic is
        # named for. A minimal or fixture tree without the convention doc
        # legitimately has no population and is not flagged.
        if (marketplace_root / _CONVENTION_DOC_REL).is_file():
            return [
                _finding(
                    EMPTY_POPULATION_TYPE,
                    marketplace_root,
                    0,
                    0,
                    snippet='',
                    message=(
                        'The shim-marker scan derived an EMPTY script population over a '
                        'tree that defines the convention — the sweep would be vacuous. '
                        'Expected *.py under bundles/*/skills/*/scripts/. See '
                        'shim-marker-convention.md.'
                    ),
                    reason='empty_population',
                )
            ], 0
        return [], 0

    findings: list[dict] = []
    for script in population:
        findings.extend(_scan_file(script, population_size))
    return findings, population_size
