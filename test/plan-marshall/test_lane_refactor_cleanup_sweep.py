#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
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
3. The dissolved ``ceremony_policy`` block — the ``ceremony_policy`` JSON key,
   its dotted ``ceremony_policy.*`` read-paths, and the retired
   ``ceremony-policy`` CLI verb. The block was dissolved and every gate /
   automation knob distributed back into its owning phase
   (``plan.phase-1-init`` / ``plan.phase-2-refine`` / ``plan.phase-3-outline``
   / ``plan.phase-6-finalize``). The bare knob NAMES survive legitimately
   (prose, log-value displays, the flat ``plan.phase-*`` JSON keys); only the
   ``ceremony_policy`` token and the ``ceremony-policy`` verb are orphans.

Plus a transitionary-prose assertion over the D14 classification-gate bodies
(which add NO retired tokens — the gate is new machinery): they must carry no
``previously`` / ``replaced by`` / ``migrated from`` markers.

Exclusions: ``.plan/`` (archived plans + this plan's own fixtures) is never on
the walk root, this sweep file is excluded by name (it carries every retired
token as a string literal), and ``doc/plans/`` is excluded as the git-tracked
equivalent of the ``.plan/`` carve-out — see :data:`_EXCLUDED_SUBTREES`.
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

# Subtrees excluded by absolute prefix rather than by directory NAME.
#
# ``doc/plans/`` holds plan documents and dated run reports: records of work that
# HAS happened, which must be able to name the machinery a run retired, the guard
# a run tripped, and the token that guard forbids. This is the same carve-out
# ``.plan`` already takes in ``_SKIP_DIR_PARTS`` ("archived plans … must not be
# scanned") — ``doc/plans/`` is simply the git-tracked half of it, and the split
# is an artifact of where the two live, not a difference in kind.
#
# Without this, the sweep forbids a run report from stating why it failed: a
# report documenting a ``ceremony_policy`` hit must quote the token to do so, and
# is then itself the hit. That is not the orphaned-reference class this sweep
# exists to catch — an orphan is a LIVE reference in source or current
# documentation, not a historical record of one.
#
# Excluded by absolute prefix, deliberately, rather than by adding ``plans`` to
# ``_SKIP_DIR_PARTS``: a name-based skip would also silence any directory called
# ``plans`` under ``marketplace/`` or ``test/``, where a retired token IS an
# orphan. ``test_the_plans_exclusion_does_not_reach_the_rest_of_doc`` pins that
# the carve-out stays this narrow.
_EXCLUDED_SUBTREES = (PROJECT_ROOT / 'doc' / 'plans',)


def _in_excluded_subtree(path: Path) -> bool:
    """True when ``path`` lies under one of :data:`_EXCLUDED_SUBTREES`."""
    return any(path.is_relative_to(subtree) for subtree in _EXCLUDED_SUBTREES)


def _iter_text_files(roots):
    """Yield every text-bearing source file under ``roots`` (excluding self).

    The skip-dir test is applied to the path RELATIVE to ``root``. Testing the
    absolute ``path.parts`` makes the whole sweep vacuous whenever the checkout
    itself lives under a directory named like a skip part — which is exactly the
    case for a plan worktree (``.../.plan/local/worktrees/<plan>``), where every
    absolute path carries ``.plan`` as a part and every file would be skipped.
    """
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
            if _in_excluded_subtree(path):
                continue
            if any(part in _SKIP_DIR_PARTS for part in path.relative_to(root).parts):
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
# (0) The doc/plans/ carve-out, and its bounds
# =============================================================================


def test_the_plans_exclusion_is_honoured_by_the_walk():
    """No file under ``doc/plans/`` reaches the sweep.

    Asserted over the real walk rather than over the predicate alone, so a
    predicate that is correct but never consulted still fails here.
    """
    walked = list(_iter_text_files((PROJECT_ROOT / 'doc',)))
    leaked = [str(p.relative_to(PROJECT_ROOT)) for p in walked if _in_excluded_subtree(p)]
    assert not leaked, (
        f'{len(leaked)} file(s) under doc/plans/ reached the sweep despite the '
        f'exclusion:\n  ' + '\n  '.join(leaked[:10])
    )


def test_the_plans_exclusion_does_not_reach_the_rest_of_doc():
    """The carve-out is ``doc/plans/`` ONLY — the rest of ``doc/`` is still swept.

    This is the control on the exclusion above. Widening it to ``doc/`` (or
    skipping by the bare directory name ``plans``, which would also silence a
    ``plans`` directory under ``marketplace/`` or ``test/``) would make every
    assertion in this module vacuous over the documentation surface they exist to
    police, while every one of them still reported green.
    """
    walked = list(_iter_text_files((PROJECT_ROOT / 'doc',)))
    survivors = [p for p in walked if not _in_excluded_subtree(p)]
    assert survivors, (
        'the doc/ walk yielded nothing outside doc/plans/, so every doc-scoped '
        'assertion in this module is vacuous'
    )
    # Named surfaces the config-doc contract lives on: their absence would mean
    # the walk had been narrowed past the point where these assertions bind.
    swept = {p.relative_to(PROJECT_ROOT).parts[1] for p in survivors}
    assert 'user' in swept and 'developer' in swept, (
        f'doc/user and doc/developer must both remain on the walk; swept top-level '
        f'doc subdirectories were {sorted(swept)}'
    )


def test_the_exclusion_is_prefix_based_not_name_based():
    """A ``plans`` directory outside ``doc/`` is NOT excluded.

    Pins the choice of an absolute-prefix test over adding ``plans`` to
    ``_SKIP_DIR_PARTS``: a retired token under ``marketplace/**/plans/`` or
    ``test/**/plans/`` is a live orphan and must still be caught.
    """
    assert not _in_excluded_subtree(PROJECT_ROOT / 'marketplace' / 'plans' / 'x.md')
    assert not _in_excluded_subtree(PROJECT_ROOT / 'test' / 'plans' / 'x.py')
    assert not _in_excluded_subtree(PROJECT_ROOT / 'doc' / 'user' / 'configuration.adoc')
    assert _in_excluded_subtree(PROJECT_ROOT / 'doc' / 'plans' / 'epic' / 'report-01.md')


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
# (3) Dissolved ceremony_policy block (knobs distributed to plan.phase-*)
# =============================================================================


def test_no_ceremony_policy_json_key_or_dotted_paths():
    """The dissolved ``ceremony_policy`` JSON key and its dotted read-paths are gone.

    The block was dissolved and every gate / automation knob distributed back
    into its owning phase. No ``ceremony_policy`` token may survive in source or
    docs — neither the bare JSON key nor any ``ceremony_policy.<section>.<knob>``
    dotted path. The scan is scoped to ``_SOURCE_ROOTS`` (marketplace + doc); the
    dissolution-regression test files legitimately carry the token as a string
    literal and are excluded from this absence-assertion.
    """
    _assert_zero(re.compile(r'ceremony_policy'), 'ceremony_policy', roots=_SOURCE_ROOTS)


def test_no_ceremony_policy_cli_verb():
    """The retired ``ceremony-policy`` manage-config verb is gone from source/docs.

    The verb was retired with the block dissolution; the distributed knobs are
    read/written via the standard ``plan phase-<N> get/set --field <knob>``
    access shape. No ``ceremony-policy get`` / ``ceremony-policy set`` invocation
    form may survive.
    """
    _assert_zero(
        re.compile(r'ceremony-policy (?:get|set)'),
        'ceremony-policy get/set (retired verb)',
        roots=_SOURCE_ROOTS,
    )


def test_finalize_without_asking_svg_label_is_flat_path():
    """The phase-lifecycle.svg arrow label uses the flat plan.phase-6-finalize path.

    The label must read ``plan.phase-6-finalize.finalize_without_asking`` — the
    dissolved ``ceremony_policy.automation.finalize_without_asking`` form is the
    orphan, and the bare ``>finalize_without_asking<`` text-element body is also
    disallowed (it must carry the flat dotted prefix).
    """
    svg = PROJECT_ROOT / 'doc' / 'resources' / 'diagrams' / 'phase-lifecycle.svg'
    if not svg.is_file():
        return
    text = svg.read_text(encoding='utf-8')
    # The dissolved ceremony_policy form must not survive.
    assert 'ceremony_policy' not in text, (
        'phase-lifecycle.svg still references the dissolved ceremony_policy block; '
        'the arrow label must read plan.phase-6-finalize.finalize_without_asking'
    )
    # The bare label as an SVG text-element body (`>finalize_without_asking<`) is
    # the orphan; the flat form `plan.phase-6-finalize.finalize_without_asking`
    # is required.
    bare = re.compile(r'>\s*finalize_without_asking\s*<')
    assert not bare.search(text), (
        'phase-lifecycle.svg still carries the bare finalize_without_asking arrow label; '
        'it must read plan.phase-6-finalize.finalize_without_asking'
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
