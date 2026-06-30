#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the init-time semantic sibling-dedup collision gate.

``sibling-collision-check`` scans every active (non-archived) sibling plan and
flags two collision classes against the plan under init:

1. **source-origin match** — the same audit / lesson / issue ``source_id`` backs
   more than one active plan (read from each plan's ``request.md`` header).
2. **file-path overlap** — concrete file paths named in this plan's
   ``request.md`` body intersect a sibling's ``references.json``
   ``affected_files``.

The verb is deterministic and read-only — no LLM dispatch, no writes.

Coverage:
- A same-``source_id`` fan-out is flagged.
- A file-path overlap is flagged (with the overlap count + joined path column).
- A clean plan (unique source, disjoint files) returns empty match lists.
- A description-sourced plan (no ``source_id``) never trips source-origin, even
  against another description-sourced sibling.
- The literal ``source_id`` ``none`` is treated as null.
- The plan under init never matches itself; a lone plan reports zero siblings.
- Worktree-resident siblings are enumerated alongside main-checkout siblings.
- The subcommand wrapper returns a structured error for a missing plan dir.
"""

from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

from conftest import load_script_module

_mod = load_script_module(
    'plan-marshall', 'manage-status', '_cmd_sibling_collision.py', '_cmd_sibling_collision_under_test'
)
run_sibling_collision_check = _mod.run_sibling_collision_check
cmd_sibling_collision = _mod.cmd_sibling_collision


# =============================================================================
# Fixture authoring helpers
# =============================================================================


def _write_status(plan_dir: Path) -> None:
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'status.json').write_text(
        json.dumps({'plan_id': plan_dir.name, 'phases': [], 'metadata': {}}),
        encoding='utf-8',
    )


def _write_request(
    plan_dir: Path,
    *,
    source: str,
    source_id: str | None,
    body: str = '',
) -> None:
    plan_dir.mkdir(parents=True, exist_ok=True)
    source_id_line = f'source_id: {source_id}\n' if source_id is not None else 'source_id: none\n'
    content = (
        f'# Request: {plan_dir.name}\n\n'
        f'source: {source}\n'
        f'{source_id_line}'
        'created: 2026-06-30T00:00:00Z\n\n'
        '## Original Input\n\n'
        f'{body}\n'
    )
    (plan_dir / 'request.md').write_text(content, encoding='utf-8')


def _write_references(plan_dir: Path, *, affected_files: list[str]) -> None:
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'references.json').write_text(
        json.dumps({'base_branch': 'main', 'affected_files': affected_files}),
        encoding='utf-8',
    )


def _ns(plan_id: str) -> Namespace:
    return Namespace(plan_id=plan_id)


# =============================================================================
# Source-origin match (primary)
# =============================================================================


def test_same_source_id_fan_out_flagged(plan_context):
    """Two active plans backed by the same lesson source_id flag a fan-out."""
    self_dir = plan_context.plan_dir_for('sc-self')
    _write_status(self_dir)
    _write_request(self_dir, source='lesson', source_id='2026-06-29-23-002')

    sib_dir = plan_context.plan_dir_for('sc-sibling')
    _write_status(sib_dir)
    _write_request(sib_dir, source='lesson', source_id='2026-06-29-23-002')

    result = run_sibling_collision_check('sc-self')

    assert result['status'] == 'success'
    assert result['collision_detected'] is True
    assert result['source_origin_match_count'] == 1
    match = result['source_origin_matches'][0]
    assert match['plan_id'] == 'sc-sibling'
    assert match['source'] == 'lesson'
    assert match['source_id'] == '2026-06-29-23-002'
    assert result['file_overlap_match_count'] == 0


def test_different_source_id_not_flagged(plan_context):
    """A sibling backed by a different source_id does not trip source-origin."""
    self_dir = plan_context.plan_dir_for('sc-self')
    _write_status(self_dir)
    _write_request(self_dir, source='lesson', source_id='2026-06-29-23-002')

    sib_dir = plan_context.plan_dir_for('sc-other')
    _write_status(sib_dir)
    _write_request(sib_dir, source='lesson', source_id='2026-01-01-00-001')

    result = run_sibling_collision_check('sc-self')

    assert result['collision_detected'] is False
    assert result['source_origin_match_count'] == 0


def test_description_source_never_trips_source_origin(plan_context):
    """Two description-sourced plans (no source_id) never collide on origin."""
    self_dir = plan_context.plan_dir_for('sc-self')
    _write_status(self_dir)
    _write_request(self_dir, source='description', source_id=None)

    sib_dir = plan_context.plan_dir_for('sc-sibling')
    _write_status(sib_dir)
    _write_request(sib_dir, source='description', source_id=None)

    result = run_sibling_collision_check('sc-self')

    assert result['collision_detected'] is False
    assert result['source_origin_match_count'] == 0
    assert result['source_id'] == ''


def test_literal_none_source_id_treated_as_null(plan_context):
    """The literal source_id 'none' is normalized to null and never matches."""
    self_dir = plan_context.plan_dir_for('sc-self')
    _write_status(self_dir)
    _write_request(self_dir, source='issue', source_id='none')

    sib_dir = plan_context.plan_dir_for('sc-sibling')
    _write_status(sib_dir)
    _write_request(sib_dir, source='issue', source_id='none')

    result = run_sibling_collision_check('sc-self')

    assert result['collision_detected'] is False
    assert result['source_origin_match_count'] == 0


# =============================================================================
# File-path overlap (secondary)
# =============================================================================


def test_file_path_overlap_flagged(plan_context):
    """A request-body path intersecting a sibling's affected_files is flagged."""
    self_dir = plan_context.plan_dir_for('sc-self')
    _write_status(self_dir)
    _write_request(
        self_dir,
        source='description',
        source_id=None,
        body='This change touches `marketplace/bundles/plan-marshall/skills/manage-status/scripts/manage-status.py`.',
    )

    sib_dir = plan_context.plan_dir_for('sc-sibling')
    _write_status(sib_dir)
    _write_request(sib_dir, source='description', source_id=None)
    _write_references(
        sib_dir,
        affected_files=[
            'marketplace/bundles/plan-marshall/skills/manage-status/scripts/manage-status.py',
            'test/plan-marshall/manage-status/test_other.py',
        ],
    )

    result = run_sibling_collision_check('sc-self')

    assert result['collision_detected'] is True
    assert result['file_overlap_match_count'] == 1
    match = result['file_overlap_matches'][0]
    assert match['plan_id'] == 'sc-sibling'
    assert match['overlap_count'] == 1
    assert (
        match['overlapping_files']
        == 'marketplace/bundles/plan-marshall/skills/manage-status/scripts/manage-status.py'
    )
    assert result['source_origin_match_count'] == 0


def test_multiple_overlapping_files_joined_with_semicolon(plan_context):
    """Several overlapping paths join with ';' and report the correct count."""
    self_dir = plan_context.plan_dir_for('sc-self')
    _write_status(self_dir)
    _write_request(
        self_dir,
        source='description',
        source_id=None,
        body='Edits `src/alpha/one.py` and `src/beta/two.py` plus unrelated prose.',
    )

    sib_dir = plan_context.plan_dir_for('sc-sibling')
    _write_status(sib_dir)
    _write_request(sib_dir, source='description', source_id=None)
    _write_references(sib_dir, affected_files=['src/alpha/one.py', 'src/beta/two.py', 'src/gamma/three.py'])

    result = run_sibling_collision_check('sc-self')

    match = result['file_overlap_matches'][0]
    assert match['overlap_count'] == 2
    # Deterministic sorted order.
    assert match['overlapping_files'] == 'src/alpha/one.py;src/beta/two.py'


def test_disjoint_files_not_flagged(plan_context):
    """A sibling whose affected_files are disjoint from the request body is clean."""
    self_dir = plan_context.plan_dir_for('sc-self')
    _write_status(self_dir)
    _write_request(
        self_dir,
        source='description',
        source_id=None,
        body='Touches `src/alpha/one.py`.',
    )

    sib_dir = plan_context.plan_dir_for('sc-sibling')
    _write_status(sib_dir)
    _write_request(sib_dir, source='description', source_id=None)
    _write_references(sib_dir, affected_files=['src/unrelated/file.py'])

    result = run_sibling_collision_check('sc-self')

    assert result['collision_detected'] is False
    assert result['file_overlap_match_count'] == 0


# =============================================================================
# Both classes together
# =============================================================================


def test_both_collision_classes_fire(plan_context):
    """A plan colliding on both source_id and a file path populates both lists."""
    self_dir = plan_context.plan_dir_for('sc-self')
    _write_status(self_dir)
    _write_request(
        self_dir,
        source='lesson',
        source_id='2026-06-29-23-002',
        body='Rewrites `a/b/c.py`.',
    )

    sib_dir = plan_context.plan_dir_for('sc-sibling')
    _write_status(sib_dir)
    _write_request(sib_dir, source='lesson', source_id='2026-06-29-23-002')
    _write_references(sib_dir, affected_files=['a/b/c.py'])

    result = run_sibling_collision_check('sc-self')

    assert result['collision_detected'] is True
    assert result['source_origin_match_count'] == 1
    assert result['file_overlap_match_count'] == 1


# =============================================================================
# Clean / no-sibling cases
# =============================================================================


def test_clean_no_collision(plan_context):
    """Unique source and disjoint files yield empty match lists."""
    self_dir = plan_context.plan_dir_for('sc-self')
    _write_status(self_dir)
    _write_request(
        self_dir,
        source='lesson',
        source_id='2026-06-30-00-001',
        body='Touches `unique/path/here.py`.',
    )

    sib_dir = plan_context.plan_dir_for('sc-sibling')
    _write_status(sib_dir)
    _write_request(sib_dir, source='lesson', source_id='2026-01-01-00-009')
    _write_references(sib_dir, affected_files=['other/path.py'])

    result = run_sibling_collision_check('sc-self')

    assert result['collision_detected'] is False
    assert result['source_origin_matches'] == []
    assert result['file_overlap_matches'] == []
    assert result['active_sibling_count'] == 1


def test_self_never_matches_and_lone_plan_reports_zero_siblings(plan_context):
    """A lone plan reports zero active siblings and never matches itself."""
    self_dir = plan_context.plan_dir_for('sc-self')
    _write_status(self_dir)
    _write_request(
        self_dir,
        source='lesson',
        source_id='2026-06-29-23-002',
        body='Touches `a/b/c.py`.',
    )
    _write_references(self_dir, affected_files=['a/b/c.py'])

    result = run_sibling_collision_check('sc-self')

    assert result['active_sibling_count'] == 0
    assert result['collision_detected'] is False


# =============================================================================
# Worktree-resident sibling enumeration
# =============================================================================


def test_worktree_resident_sibling_enumerated(plan_context):
    """A sibling moved into its worktree is scanned alongside main-checkout plans."""
    self_dir = plan_context.plan_dir_for('sc-self')
    _write_status(self_dir)
    _write_request(
        self_dir,
        source='lesson',
        source_id='2026-06-29-23-002',
        body='Touches `a/b/c.py`.',
    )

    # Worktree layout: <base>/worktrees/<wt>/.plan/local/plans/<id>/
    wt_plan_dir = (
        plan_context.fixture_dir
        / 'worktrees'
        / 'sc-wt'
        / '.plan'
        / 'local'
        / 'plans'
        / 'sc-wt'
    )
    _write_status(wt_plan_dir)
    _write_request(wt_plan_dir, source='lesson', source_id='2026-06-29-23-002')
    _write_references(wt_plan_dir, affected_files=['a/b/c.py'])

    result = run_sibling_collision_check('sc-self')

    assert result['active_sibling_count'] == 1
    assert result['collision_detected'] is True
    assert result['source_origin_matches'][0]['plan_id'] == 'sc-wt'
    assert result['file_overlap_matches'][0]['plan_id'] == 'sc-wt'


# =============================================================================
# Subcommand wrapper
# =============================================================================


def test_cmd_returns_error_for_missing_plan(plan_context):
    """The subcommand returns a structured error when the plan dir is absent."""
    result = cmd_sibling_collision(_ns('sc-nonexistent'))

    assert result['status'] == 'error'
    assert result['error'] == 'plan_dir_not_found'
    assert result['plan_id'] == 'sc-nonexistent'


def test_cmd_success_delegates_to_run(plan_context):
    """The subcommand wrapper returns the full collision result for a real plan."""
    self_dir = plan_context.plan_dir_for('sc-self')
    _write_status(self_dir)
    _write_request(self_dir, source='description', source_id=None, body='No paths here.')

    result = cmd_sibling_collision(_ns('sc-self'))

    assert result['status'] == 'success'
    assert result['plan_id'] == 'sc-self'
    assert result['collision_detected'] is False
