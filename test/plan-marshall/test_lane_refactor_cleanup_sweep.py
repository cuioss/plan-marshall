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
token as a string literal), and lane run reports (``doc/plans/**/report-NN.md``)
are excluded as dated records rather than current documentation — the boundary
``CLAUDE.md`` already draws. See :func:`_is_lane_run_report`; everything else
under ``doc/plans/`` stays on the walk.
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

# Lane RUN REPORTS — ``doc/plans/{epic}/{plan-name}/report-NN.md`` — are excluded.
#
# A run report is a dated record of one execution, so it must be able to name the
# machinery a run retired, the guard a run tripped, and the token that guard
# forbids. Without this the sweep forbids a report from stating why it failed: a
# report documenting a ``ceremony_policy`` hit has to quote the token to do so,
# and is then itself the hit. That is not the orphaned-reference class this sweep
# catches — an orphan is a LIVE reference in source or current documentation, not
# a historical record of one.
#
# The boundary is NOT this module's invention. ``CLAUDE.md`` already draws it, in
# the same records-versus-documentation terms, when it exempts a run report from
# the "No timestamps" / "Current state only" standards: "a lane run report
# (doc/plans/{epic}/{plan-name}/report-NN.md) carries a date and an ordinal,
# because it is a dated record of one execution rather than documentation of the
# current state … No other file in doc/plans/ takes this exemption."
#
# So the carve-out is report files ONLY, not the ``doc/plans/`` tree. That tree
# also holds live documentation the sweep must keep policing: ``doc/plans/
# README.md`` (cross-referenced from CLAUDE.md), a README per epic,
# ``doc/plans/_template/plan.md`` (a template that propagates into every new
# plan), and each plan.md itself — all of which CLAUDE.md says "follow the
# standards unchanged". A retired token in any of them is a live orphan.
#
# Matched on the filename under a ``doc/plans/`` ancestor, deliberately, rather
# than by adding ``plans`` to ``_SKIP_DIR_PARTS``: a name-based skip would
# silence any directory called ``plans`` under ``marketplace/`` or ``test/``,
# where a retired token IS an orphan. Four tests below pin this shape: reports
# excluded, everything else under doc/plans still swept, the rest of doc/ still
# swept, and the match anchored to doc/plans rather than to the name
# ``report-NN.md`` anywhere.
_PLANS_ROOT = PROJECT_ROOT / 'doc' / 'plans'
_RUN_REPORT_NAME = re.compile(r'^report-\d+\.md$')


def _is_lane_run_report(path: Path) -> bool:
    """True for a ``doc/plans/**/report-NN.md`` dated run record."""
    return path.is_relative_to(_PLANS_ROOT) and bool(_RUN_REPORT_NAME.match(path.name))


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
            if _is_lane_run_report(path):
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
# (0) The run-report carve-out, and its bounds
# =============================================================================


def test_the_run_report_exclusion_is_honoured_by_the_walk():
    """No ``doc/plans/**/report-NN.md`` reaches the sweep.

    Asserted over the real walk rather than over the predicate alone, so a
    predicate that is correct but never consulted still fails here.
    """
    walked = list(_iter_text_files((PROJECT_ROOT / 'doc',)))
    leaked = [str(p.relative_to(PROJECT_ROOT)) for p in walked if _is_lane_run_report(p)]
    assert not leaked, (
        f'{len(leaked)} lane run report(s) reached the sweep despite the '
        f'exclusion:\n  ' + '\n  '.join(leaked[:10])
    )


def test_the_rest_of_doc_plans_is_still_swept():
    """The carve-out is run reports ONLY — every other file under ``doc/plans/`` is swept.

    This is the control that keeps the exclusion at the boundary ``CLAUDE.md``
    draws. ``doc/plans/`` also holds live documentation — its own README, an
    epic README each, the plan template that propagates into new plans, and each
    plan.md — which CLAUDE.md says "follow the standards unchanged". Widening the
    carve-out from report files to the tree would stop policing all of them while
    every assertion in this module still reported green.
    """
    walked = {p.relative_to(PROJECT_ROOT) for p in _iter_text_files((PROJECT_ROOT / 'doc',))}

    required = [
        Path('doc/plans/README.md'),
        Path('doc/plans/_template/plan.md'),
    ]
    missing = [str(p) for p in required if (PROJECT_ROOT / p).is_file() and p not in walked]
    assert not missing, (
        f'live documentation under doc/plans/ is no longer swept, so a retired '
        f'token in it would go uncaught: {missing}'
    )

    # At least one epic README and one plan.md, located rather than hardcoded, so
    # the control does not decay into two named files.
    assert any(p.name == 'README.md' and p.parent != Path('doc/plans') and 'plans' in p.parts
               for p in walked), 'no per-epic README under doc/plans/ reached the sweep'
    assert any(p.name == 'plan.md' for p in walked), 'no plan.md reached the sweep'


def test_the_rest_of_doc_is_still_swept():
    """``doc/user`` and ``doc/developer`` stay on the walk."""
    walked = list(_iter_text_files((PROJECT_ROOT / 'doc',)))
    swept = {p.relative_to(PROJECT_ROOT).parts[1] for p in walked}
    assert 'user' in swept and 'developer' in swept, (
        f'doc/user and doc/developer must both remain on the walk; swept top-level '
        f'doc subdirectories were {sorted(swept)}'
    )


def test_the_exclusion_is_anchored_to_doc_plans_and_to_the_report_name():
    """Both halves of the match are load-bearing.

    A ``report-NN.md`` OUTSIDE ``doc/plans/`` is not a lane run record and stays
    swept; a non-report file INSIDE ``doc/plans/`` stays swept too. Pins the
    filename+ancestor pair over adding ``plans`` to ``_SKIP_DIR_PARTS``, which
    would also silence a ``plans`` directory under ``marketplace/`` or ``test/``
    where a retired token IS an orphan.
    """
    # Anchored to doc/plans: a report-shaped name elsewhere is still swept.
    assert not _is_lane_run_report(PROJECT_ROOT / 'doc' / 'user' / 'report-01.md')
    assert not _is_lane_run_report(PROJECT_ROOT / 'marketplace' / 'plans' / 'report-01.md')
    # Anchored to the report name: live docs under doc/plans are still swept.
    assert not _is_lane_run_report(PROJECT_ROOT / 'doc' / 'plans' / 'README.md')
    assert not _is_lane_run_report(PROJECT_ROOT / 'doc' / 'plans' / '_template' / 'plan.md')
    assert not _is_lane_run_report(PROJECT_ROOT / 'doc' / 'plans' / 'epic' / 'p' / 'plan.md')
    assert not _is_lane_run_report(PROJECT_ROOT / 'doc' / 'plans' / 'epic' / 'reports.md')
    # And the record itself is excluded.
    assert _is_lane_run_report(PROJECT_ROOT / 'doc' / 'plans' / 'epic' / 'p' / 'report-01.md')
    assert _is_lane_run_report(PROJECT_ROOT / 'doc' / 'plans' / 'epic' / 'p' / 'report-12.md')


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
