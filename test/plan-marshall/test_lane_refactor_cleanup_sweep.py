#!/usr/bin/env python3
"""Dependency-sweep verification for the planning-lanes light/deep refactor.

A structural grep-sweep that asserts ZERO orphaned references to every piece of
machinery this plan retired. The sweep walks ``marketplace/``, ``doc/`` (including
``doc/resources/diagrams/**`` SVG text), and ``test/`` and asserts each retired
token's live-reference count is zero. Each retired token gets its own assertion
with a failure message naming the offending file:line so a future orphan is
trivially located.

Retired machinery (clean-slate ``compatibility=breaking`` deletions):

1. ``fast_path_threshold`` — the deleted phase-2-refine first-pass fast-path knob.
2. The Simple/Complex **track-selection classifier** — specifically the
   ``Route by Track`` selection-step marker (the lane decision is the sole
   selector now; ``track`` is derived from the lane).
3. The loose finalize read-paths — the dotted JSON paths and the CLI
   ``get``/``set`` forms for ``finalize_without_asking`` (phase-5-execute),
   ``loop_back_without_asking`` / ``auto_merge_after_ci`` (phase-6-finalize),
   now homed under ``ceremony_policy.automation.*``. The bare knob NAMES survive
   legitimately (prose, log-value displays, the ``ceremony_policy.automation``
   JSON keys); only the loose *read-path* forms and the bare SVG arrow label are
   orphans.

Plus a transitionary-prose assertion over the D14 classification-gate bodies
(which add NO retired tokens — the gate is new machinery): they must carry no
``previously`` / ``replaced by`` / ``migrated from`` markers.

Exclusions: ``.plan/`` (archived plans + this plan's own fixtures) is never on
the walk root, and this sweep file is excluded by name (it carries every retired
token as a string literal).
"""

from __future__ import annotations

import re
from pathlib import Path

from conftest import PROJECT_ROOT

# Roots the sweep walks. ``.plan/`` is deliberately absent — archived plans and
# this plan's own fixtures must not be scanned. ``test/`` is included for the
# tokens that may NEVER appear anywhere (fast_path_threshold, Route by Track);
# the loose-finalize-path checks scope to ``_SOURCE_ROOTS`` (marketplace + doc)
# because absence-asserting tests legitimately carry the loose path as a literal.
_SWEEP_ROOTS = (
    PROJECT_ROOT / 'marketplace',
    PROJECT_ROOT / 'doc',
    PROJECT_ROOT / 'test',
)

# Source + docs only — the surfaces the config-doc-contract and the SVG live on.
# Excludes ``test/`` so a test that asserts a loose path's *absence* (carrying it
# as a string literal) is not itself flagged as the orphan.
_SOURCE_ROOTS = (
    PROJECT_ROOT / 'marketplace',
    PROJECT_ROOT / 'doc',
)

# Text-bearing file suffixes the sweep inspects.
_TEXT_SUFFIXES = {'.md', '.py', '.adoc', '.svg', '.json', '.toon', '.txt'}

# This file (carries every retired token as a literal) is excluded by name.
_SELF_NAME = Path(__file__).name

# Cache directories never carry source.
_SKIP_DIR_PARTS = {'__pycache__', '.git', '.plan', 'node_modules', 'target'}


def _iter_text_files(roots):
    """Yield every text-bearing source file under ``roots`` (excluding self)."""
    for root in roots:
        if not root.is_dir():
            continue
        for path in root.rglob('*'):
            if not path.is_file():
                continue
            if path.suffix not in _TEXT_SUFFIXES:
                continue
            if path.name == _SELF_NAME:
                continue
            if any(part in _SKIP_DIR_PARTS for part in path.parts):
                continue
            yield path


def _grep(pattern: re.Pattern[str], roots=_SWEEP_ROOTS) -> list[str]:
    """Return ``relpath:lineno: line`` hits for ``pattern`` across ``roots``."""
    hits: list[str] = []
    for path in _iter_text_files(roots):
        try:
            text = path.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            if pattern.search(line):
                rel = path.relative_to(PROJECT_ROOT)
                hits.append(f'{rel}:{lineno}: {line.strip()}')
    return hits


def _assert_zero(pattern: re.Pattern[str], token_label: str, roots=_SWEEP_ROOTS) -> None:
    """Fail with a file:line list when ``pattern`` matches anywhere in ``roots``."""
    hits = _grep(pattern, roots)
    assert not hits, (
        f'Orphaned reference to retired token {token_label!r} '
        f'({len(hits)} hit(s)):\n  ' + '\n  '.join(hits)
    )


# =============================================================================
# (1) fast_path_threshold
# =============================================================================


def test_no_fast_path_threshold_references():
    """The retired fast_path_threshold knob leaves zero references."""
    _assert_zero(re.compile(r'fast_path_threshold'), 'fast_path_threshold')


# =============================================================================
# (2) Simple/Complex track-selection classifier — "Route by Track"
# =============================================================================


def test_no_route_by_track_classifier_marker():
    """The retired track-selection step marker 'Route by Track' is gone (lane subsumes it)."""
    _assert_zero(re.compile(r'Route by Track'), 'Route by Track (track-selection classifier)')


# =============================================================================
# (3) Loose finalize read-paths (now ceremony_policy.automation.*)
# =============================================================================


def test_no_loose_finalize_json_paths():
    """The loose dotted JSON read-paths for the three finalize knobs are gone."""
    for dotted in (
        r'plan\.phase-5-execute\.finalize_without_asking',
        r'plan\.phase-6-finalize\.loop_back_without_asking',
        r'plan\.phase-6-finalize\.auto_merge_after_ci',
    ):
        _assert_zero(re.compile(dotted), dotted.replace('\\', ''), roots=_SOURCE_ROOTS)


def test_no_loose_finalize_cli_read_paths():
    """The loose CLI get/set --field forms for the three finalize knobs are gone."""
    patterns = {
        'phase-5-execute (get|set) --field finalize_without_asking': re.compile(
            r'phase-5-execute (?:get|set)[^\n]*--field finalize_without_asking'
        ),
        'phase-6-finalize (get|set) --field loop_back_without_asking': re.compile(
            r'phase-6-finalize (?:get|set)[^\n]*--field loop_back_without_asking'
        ),
        'phase-6-finalize (get|set) --field auto_merge_after_ci': re.compile(
            r'phase-6-finalize (?:get|set)[^\n]*--field auto_merge_after_ci'
        ),
    }
    for label, pattern in patterns.items():
        _assert_zero(pattern, label, roots=_SOURCE_ROOTS)


def test_finalize_without_asking_svg_label_is_prefixed():
    """The phase-lifecycle.svg arrow label uses the migrated ceremony_policy path, not the bare knob."""
    svg = PROJECT_ROOT / 'doc' / 'resources' / 'diagrams' / 'phase-lifecycle.svg'
    if not svg.is_file():
        return
    text = svg.read_text(encoding='utf-8')
    # The bare label as an SVG text-element body (`>finalize_without_asking<`) is
    # the orphan; the migrated form `ceremony_policy.automation.finalize_without_asking`
    # is allowed.
    bare = re.compile(r'>\s*finalize_without_asking\s*<')
    assert not bare.search(text), (
        'phase-lifecycle.svg still carries the bare finalize_without_asking arrow label; '
        'it must read ceremony_policy.automation.finalize_without_asking'
    )


# =============================================================================
# (4) No transitionary prose in the D14 classification-gate bodies
# =============================================================================

_TRANSITIONARY = re.compile(
    r'\b(previously|replaced by|migrated from|formerly|carved from|used to be|deleted in)\b',
    re.IGNORECASE,
)

_D14_BODIES = (
    'marketplace/bundles/plan-marshall/skills/manage-status/scripts/manage-status.py',
    'marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_classification_validate.py',
    'marketplace/bundles/plan-marshall/skills/manage-status/SKILL.md',
    'marketplace/bundles/plan-marshall/skills/phase-1-init/SKILL.md',
)


def test_no_transitionary_prose_in_classification_gate_bodies():
    """The D14 classification-gate bodies introduce no transitionary-prose markers."""
    offenders: list[str] = []
    for rel in _D14_BODIES:
        path = PROJECT_ROOT / rel
        if not path.is_file():
            continue
        for lineno, line in enumerate(path.read_text(encoding='utf-8').splitlines(), start=1):
            if _TRANSITIONARY.search(line):
                offenders.append(f'{rel}:{lineno}: {line.strip()}')
    assert not offenders, (
        'Transitionary prose introduced in a D14 classification-gate body:\n  '
        + '\n  '.join(offenders)
    )
