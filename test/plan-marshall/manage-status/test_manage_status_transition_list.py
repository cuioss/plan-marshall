#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-status.py transition + archive + delete + orphans + loop-back."""


import json
import shutil
from argparse import Namespace

from _manage_status_transition_fixtures import (
    SCRIPT_PATH,
    _seed_finalize_phase_plan,
    _seed_legitimate_plan,
    _seed_worktree_resident_plan,
    cmd_create,
    cmd_list,
    cmd_list_orphans,
    cmd_transition,
)

from conftest import run_script


def test_transition_last_phase_sets_complete(plan_context):
    """cmd_transition must mirror cmd_archive when completing the LAST phase."""
    plan_id = 'transition-last-phase-complete'
    _seed_finalize_phase_plan(plan_id)

    result = cmd_transition(Namespace(plan_id=plan_id, completed='6-finalize'))

    assert result['status'] == 'success'
    assert result.get('message') == 'All phases completed', (
        f'expected terminal message, got {result}'
    )
    assert 'next_phase' not in result, (
        f'cmd_transition on the last phase must not return next_phase: {result}'
    )

    live_status = json.loads((plan_context.plan_dir_for(plan_id) / 'status.json').read_text(encoding='utf-8'))
    assert live_status['current_phase'] == 'complete', (
        f"Expected current_phase='complete' after transition --completed "
        f'6-finalize, got {live_status["current_phase"]!r}. Symmetry '
        f'with cmd_archive regressed: cmd_transition is not setting '
        f'the post-finalize sentinel for the last phase.'
    )
    assert live_status['phases'][-1]['status'] == 'done', (
        f"Expected phases[-1].status='done', got "
        f'{live_status["phases"][-1]["status"]!r}.'
    )


def test_list_discovers_moved_in_worktree_plan(plan_context):
    """Regression: cmd_list surfaces a plan whose dir moved into a worktree.

    The plan directory lives ONLY under the worktree tree (the ADR-002
    move-in removed it from the main plans_dir). A main-only walk returns
    total=0; the fixed cmd_list must discover it via the worktree scan and
    tag it location='worktree'.
    """
    # Remove the fixture's default main-checkout plan so the worktree plan is
    # the only discoverable plan — total must be exactly 1.
    shutil.rmtree(plan_context.plan_dir, ignore_errors=True)
    _seed_worktree_resident_plan(plan_context.fixture_dir, 'moved-in-plan')

    result = cmd_list(Namespace(filter=None))

    assert result['status'] == 'success'
    assert result['total'] == 1, (
        f'cmd_list is blind to the moved-in worktree plan: expected total=1, '
        f"got {result['total']} plans={result['plans']!r}. A regression to the "
        f'main-only plans_dir walk drops every phase-5+ plan whose directory '
        f'moved into its worktree (ADR-002).'
    )
    entry = result['plans'][0]
    assert entry['id'] == 'moved-in-plan'
    assert entry['location'] == 'worktree', (
        f"Moved-in plan must be tagged location='worktree', got "
        f"{entry['location']!r}."
    )
    assert entry['current_phase'] == '5-execute'


def test_list_merges_main_and_worktree_plans_sorted(plan_context):
    """cmd_list merges main-checkout and worktree plans, sorted by id.

    One legitimate plan on the main checkout (location='current') plus one
    moved-in worktree plan (location='worktree') → both returned, deduped,
    and sorted by id.
    """
    shutil.rmtree(plan_context.plan_dir, ignore_errors=True)
    # Main-checkout plan via cmd_create (writes a real status.json under plans_dir).
    cmd_create(
        Namespace(
            plan_id='alpha-on-main',
            title='Main Plan',
            phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
            force=False,
        )
    )
    # Worktree-resident plan whose id sorts AFTER the main plan.
    _seed_worktree_resident_plan(plan_context.fixture_dir, 'zeta-in-worktree')

    result = cmd_list(Namespace(filter=None))

    assert result['status'] == 'success'
    assert result['total'] == 2, (
        f'Expected both the main-checkout and worktree plans, got '
        f"total={result['total']} plans={result['plans']!r}."
    )
    ids = [p['id'] for p in result['plans']]
    assert ids == ['alpha-on-main', 'zeta-in-worktree'], (
        f'Merged plans must be sorted by id regardless of source, got {ids}.'
    )
    by_id = {p['id']: p for p in result['plans']}
    assert by_id['alpha-on-main']['location'] == 'current'
    assert by_id['zeta-in-worktree']['location'] == 'worktree'


def test_list_dedupes_plan_present_in_both_main_and_worktree(plan_context):
    """Defensive dedup: a plan present on main AND in a worktree appears once.

    The transient both-present window (before the move-in fully removes the
    main copy) must not double-count. The main-checkout entry wins
    (location='current') because the main scan runs first and records the id.
    """
    shutil.rmtree(plan_context.plan_dir, ignore_errors=True)
    cmd_create(
        Namespace(
            plan_id='dual-present',
            title='Dual Present',
            phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
            force=False,
        )
    )
    # Same id also seeded in a worktree (transient both-present window).
    _seed_worktree_resident_plan(plan_context.fixture_dir, 'dual-present')

    result = cmd_list(Namespace(filter=None))

    assert result['status'] == 'success'
    assert result['total'] == 1, (
        f"Plan present in both sources must appear exactly once, got "
        f"total={result['total']} plans={result['plans']!r}."
    )
    entry = result['plans'][0]
    assert entry['id'] == 'dual-present'
    assert entry['location'] == 'current', (
        f"The main-checkout entry must win dedup (main scan runs first), got "
        f"location={entry['location']!r}."
    )


def test_list_worktree_plan_honours_phase_filter(plan_context):
    """The --filter phase predicate applies to worktree-resident plans too.

    A worktree plan in phase 5-execute is filtered out by --filter 3-outline
    and surfaced by --filter 5-execute — the worktree scan honours the same
    _passes_phase_filter predicate as the main scan.
    """
    shutil.rmtree(plan_context.plan_dir, ignore_errors=True)
    _seed_worktree_resident_plan(
        plan_context.fixture_dir, 'filtered-worktree', current_phase='5-execute'
    )

    excluded = cmd_list(Namespace(filter='3-outline'))
    assert excluded['status'] == 'success'
    assert excluded['total'] == 0, (
        f'Worktree plan in 5-execute must be excluded by --filter 3-outline, '
        f"got {excluded['plans']!r}. The worktree scan must apply the phase "
        f'filter, not just the main scan.'
    )

    included = cmd_list(Namespace(filter='5-execute'))
    assert included['status'] == 'success'
    assert included['total'] == 1
    assert included['plans'][0]['id'] == 'filtered-worktree'


def test_list_cli_surfaces_worktree_plan(plan_context):
    """End-to-end CLI: ``manage-status list`` surfaces the moved-in plan.

    Exercises the full script entry point (argparse → cmd_list → TOON), not
    just the in-process handler, so the subcommand wiring is covered. The
    fixture's PLAN_BASE_DIR is propagated to the subprocess via run_script's
    os.environ.copy(), so the child resolves the same worktree tree.
    """
    shutil.rmtree(plan_context.plan_dir, ignore_errors=True)
    _seed_worktree_resident_plan(plan_context.fixture_dir, 'cli-worktree-plan')

    result = run_script(SCRIPT_PATH, 'list')

    assert result.success, (
        f'list subcommand must be resolvable via the script entry point. '
        f'stderr: {result.stderr}'
    )
    assert 'status: success' in result.stdout
    assert 'cli-worktree-plan' in result.stdout, (
        f'CLI list output missing the moved-in worktree plan: {result.stdout!r}'
    )
    assert 'worktree' in result.stdout


def test_list_orphans_empty_plans_dir(plan_context):
    """(a) Empty plans_dir returns total: 0 and orphans: []."""
    shutil.rmtree(plan_context.plan_dir_for('orphans-empty'))
    shutil.rmtree(plan_context.plan_dir, ignore_errors=True)

    result = cmd_list_orphans(Namespace())

    assert result['status'] == 'success'
    assert result['total'] == 0
    assert result['orphans'] == []


def test_list_orphans_skips_dir_with_status_json(plan_context):
    """(b) Directory present with status.json is NOT listed as an orphan."""
    shutil.rmtree(plan_context.plan_dir_for('orphans-skip-valid'))
    shutil.rmtree(plan_context.plan_dir, ignore_errors=True)
    _seed_legitimate_plan('legit-plan')

    result = cmd_list_orphans(Namespace())

    assert result['status'] == 'success'
    assert result['total'] == 0, (
        f"Legitimate plan with status.json must NOT be reported as orphan, got: {result['orphans']}"
    )
    assert result['orphans'] == []


def test_list_orphans_includes_dir_without_status_json_with_subdirs(plan_context):
    """(c) Directory without status.json but with logs/ or work/ subdirs IS listed."""
    shutil.rmtree(plan_context.plan_dir_for('orphans-with-subdirs'))
    shutil.rmtree(plan_context.plan_dir, ignore_errors=True)

    orphan_dir = plan_context.fixture_dir / 'plans' / 'orphan-with-subdirs'
    orphan_dir.mkdir(parents=True)
    (orphan_dir / 'logs').mkdir()
    (orphan_dir / 'work').mkdir()

    result = cmd_list_orphans(Namespace())

    assert result['status'] == 'success'
    assert result['total'] == 1
    assert len(result['orphans']) == 1
    entry = result['orphans'][0]
    assert entry['id'] == 'orphan-with-subdirs'
    assert entry['path'] == str(orphan_dir)
    assert entry['contents'] == ['logs', 'work']
