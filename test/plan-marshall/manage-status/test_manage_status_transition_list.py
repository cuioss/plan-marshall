#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-status.py transition: list across main and worktree, and orphan discovery."""


import shutil
from argparse import Namespace

from _manage_status_transition_fixtures import (
    SCRIPT_PATH,
    _query,
    _seed_legitimate_plan,
    _seed_worktree_resident_plan,
    cmd_create,
    cmd_list,
    cmd_list_orphans,
)

from conftest import run_script


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


def test_list_orphans_returns_multiple_sorted(plan_context):
    """(d) Multiple orphans are all returned, sorted by id."""
    shutil.rmtree(plan_context.plan_dir_for('orphans-many'))
    shutil.rmtree(plan_context.plan_dir, ignore_errors=True)

    plans_dir = plan_context.fixture_dir / 'plans'
    for name in ('zeta-orphan', 'alpha-orphan', 'mid-orphan'):
        d = plans_dir / name
        d.mkdir(parents=True)
        (d / 'stray.txt').write_text('x')

    result = cmd_list_orphans(Namespace())

    assert result['status'] == 'success'
    assert result['total'] == 3
    ids = [o['id'] for o in result['orphans']]
    assert ids == ['alpha-orphan', 'mid-orphan', 'zeta-orphan'], (
        f'orphans must be returned in sorted id order, got {ids}'
    )
    for orphan in result['orphans']:
        assert orphan['contents'] == ['stray.txt']


def test_list_orphans_mixed_eight_orphans_plus_two_legitimate_plans(plan_context):
    """CLI resolvability + filter contract: 8 orphans + 2 legitimate plans → ONLY the 8 orphans returned."""
    shutil.rmtree(plan_context.plan_dir_for('orphans-mixed'))
    shutil.rmtree(plan_context.plan_dir, ignore_errors=True)

    plans_dir = plan_context.fixture_dir / 'plans'
    orphan_names = [f'orphan-{i:02d}' for i in range(8)]
    for name in orphan_names:
        (plans_dir / name).mkdir(parents=True)

    _seed_legitimate_plan('lesson-alpha')
    _seed_legitimate_plan('lesson-beta')

    result = cmd_list_orphans(Namespace())
    assert result['status'] == 'success'
    assert result['total'] == 8, (
        f"Expected exactly 8 orphans (legitimate lesson-* plans must be filtered out), "
        f"got total={result['total']} ids={[o['id'] for o in result['orphans']]}"
    )
    returned_ids = [o['id'] for o in result['orphans']]
    assert returned_ids == sorted(orphan_names), (
        f'Expected sorted orphan ids {sorted(orphan_names)}, got {returned_ids}'
    )
    assert 'lesson-alpha' not in returned_ids
    assert 'lesson-beta' not in returned_ids

    cli_result = run_script(SCRIPT_PATH, 'list-orphans')
    assert cli_result.success, (
        f'list-orphans subcommand must be resolvable via the script entry point. '
        f'stderr: {cli_result.stderr}'
    )
    assert 'status: success' in cli_result.stdout
    for name in orphan_names:
        assert name in cli_result.stdout, f'orphan {name} missing from CLI output'
    assert 'lesson-alpha' not in cli_result.stdout
    assert 'lesson-beta' not in cli_result.stdout


def test_list_orphans_unreadable_dir_emits_sentinel(plan_context, monkeypatch):
    """(1) OSError on iterdir → contents=['<unreadable>'] sentinel."""
    shutil.rmtree(plan_context.plan_dir_for('orphans-unreadable'))
    shutil.rmtree(plan_context.plan_dir, ignore_errors=True)

    orphan_dir = plan_context.fixture_dir / 'plans' / 'unreadable-orphan'
    orphan_dir.mkdir(parents=True)

    from pathlib import Path as _Path

    original_iterdir = _Path.iterdir

    def patched_iterdir(self):
        if self == orphan_dir:
            raise PermissionError('simulated unreadable dir')
        return original_iterdir(self)

    monkeypatch.setattr(_Path, 'iterdir', patched_iterdir)

    result = cmd_list_orphans(Namespace())

    assert result['status'] == 'success'
    assert result['total'] == 1
    entry = result['orphans'][0]
    assert entry['id'] == 'unreadable-orphan'
    assert entry['contents'] == ['<unreadable>'], (
        f'Unreadable orphan must surface ["<unreadable>"] sentinel, got '
        f'{entry["contents"]!r}. An empty list would trigger silent '
        f'deletion under planning.md Step 3b.'
    )


def test_list_orphans_file_at_plans_dir_returns_zero(monkeypatch, tmp_path):
    """(2) Stray FILE at plans_dir path → total=0 cleanly, no exception."""
    stray_file = tmp_path / 'plans'
    stray_file.write_text('this is a file, not a directory\n')

    monkeypatch.setattr(_query, 'get_plans_dir', lambda: stray_file)

    result = cmd_list_orphans(Namespace())

    assert result['status'] == 'success', (
        f'Stray file at plans_dir must yield clean success, got {result!r}. '
        f'Regression: plans_dir.exists() returned True for the file and '
        f'iterdir() raised NotADirectoryError.'
    )
    assert result['total'] == 0
    assert result['orphans'] == []


def test_list_orphans_empty_status_json_not_flagged(plan_context, monkeypatch):
    """(3) Empty ``{}`` status.json must NOT be reported as orphan."""
    shutil.rmtree(plan_context.plan_dir_for('orphans-empty-status'))
    shutil.rmtree(plan_context.plan_dir, ignore_errors=True)

    plans_dir = plan_context.fixture_dir / 'plans'
    plan_dir = plans_dir / 'empty-status-plan'
    plan_dir.mkdir(parents=True)
    (plan_dir / 'status.json').write_text('{}', encoding='utf-8')

    result = cmd_list_orphans(Namespace())

    assert result['status'] == 'success'
    assert result['total'] == 0, (
        f'Empty {{}} status.json must NOT be flagged as orphan (matches '
        f'require_plan_exists file-presence guard), got '
        f'total={result["total"]} orphans={result["orphans"]!r}. '
        f'Regression: the filter is using parsed-truthy `if status:` '
        f'instead of `(plan_dir / "status.json").is_file()`.'
    )
    assert result['orphans'] == []
