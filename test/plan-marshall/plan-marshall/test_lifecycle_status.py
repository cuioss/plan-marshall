#!/usr/bin/env python3
"""Tests for lifecycle commands in manage_status.py script.

Tests plan discovery, transitions, archiving, and routing (formerly manage-lifecycle).
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path

from conftest import PlanContext, get_script_path, run_script

# Get script paths
LIFECYCLE_SCRIPT = get_script_path('plan-marshall', 'manage-status', 'manage_status.py')
STATUS_SCRIPT = get_script_path('plan-marshall', 'manage-status', 'manage_status.py')

# Import toon_parser - conftest sets up PYTHONPATH
from toon_parser import parse_toon  # type: ignore[import-not-found]  # noqa: E402


def _create_plan(plan_id: str, title: str, phases: str) -> None:
    """Helper to create a plan using manage-status."""
    result = run_script(
        STATUS_SCRIPT,
        'create',
        '--plan-id',
        plan_id,
        '--title',
        title,
        '--phases',
        phases,
    )
    assert result.success, f'Failed to create plan: {result.stderr}'


# =============================================================================
# Test: Get Routing Context
# =============================================================================


def test_get_routing_context():
    """Test getting routing context combines phase, skill, and progress."""
    with PlanContext(plan_id='routing-plan'):
        _create_plan('routing-plan', 'Routing Test', '1-init,2-refine,3-outline,4-plan,5-execute,6-finalize')
        result = run_script(LIFECYCLE_SCRIPT, 'get-routing-context', '--plan-id', 'routing-plan')
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        # Should have current phase
        assert data['current_phase'] == '1-init'
        # Should have skill routing
        assert data['skill'] == 'plan-init'
        # Should have progress
        assert 'total_phases' in data
        assert 'completed_phases' in data


def test_get_routing_context_after_transition():
    """Test routing context updates after phase transition."""
    with PlanContext(plan_id='transition-routing'):
        _create_plan('transition-routing', 'Transition Test', '1-init,2-refine,3-outline,4-plan,5-execute,6-finalize')
        run_script(LIFECYCLE_SCRIPT, 'transition', '--plan-id', 'transition-routing', '--completed', '1-init')
        result = run_script(LIFECYCLE_SCRIPT, 'get-routing-context', '--plan-id', 'transition-routing')
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['current_phase'] == '2-refine'
        assert data['skill'] == 'request-refine'
        assert data['completed_phases'] == 1


def test_get_routing_context_not_found():
    """Test get-routing-context exits 0 with TOON error for missing plan."""
    with PlanContext():
        result = run_script(LIFECYCLE_SCRIPT, 'get-routing-context', '--plan-id', 'nonexistent')
        assert result.success, 'Should exit 0 with TOON error output'
        assert 'status: error' in result.stdout


# =============================================================================
# Test: List Command
# =============================================================================


def test_list_empty():
    """Test listing when no plans exist."""
    with PlanContext():
        result = run_script(LIFECYCLE_SCRIPT, 'list')
        assert result.success, f'Script failed: {result.stderr}'


def test_list_with_plan():
    """Test listing when a plan exists."""
    with PlanContext(plan_id='list-plan'):
        _create_plan('list-plan', 'List Test', 'init,execute,finalize')
        result = run_script(LIFECYCLE_SCRIPT, 'list')
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['total'] >= 1
        # Find our plan in the list
        plan_ids = [p['id'] for p in data['plans']]
        assert 'list-plan' in plan_ids


def test_list_with_filter():
    """Test listing with phase filter."""
    with PlanContext(plan_id='filter-plan'):
        _create_plan('filter-plan', 'Filter Test', '1-init,2-refine,3-outline')
        # Filter for 1-init phase
        result = run_script(LIFECYCLE_SCRIPT, 'list', '--filter', '1-init')
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        # Should find the plan (it starts at 1-init)
        plan_ids = [p['id'] for p in data['plans']]
        assert 'filter-plan' in plan_ids


def test_list_with_filter_no_match():
    """Test listing with filter that doesn't match."""
    with PlanContext(plan_id='nomatch-plan'):
        _create_plan('nomatch-plan', 'No Match Test', '1-init,2-refine')
        # Filter for a phase the plan isn't at
        result = run_script(LIFECYCLE_SCRIPT, 'list', '--filter', '5-execute')
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        # Should not find the plan
        plan_ids = [p['id'] for p in data['plans']]
        assert 'nomatch-plan' not in plan_ids


# =============================================================================
# Test: Transition Command
# =============================================================================


def test_transition_to_next_phase():
    """Test transitioning to the next phase."""
    with PlanContext(plan_id='transition-plan'):
        _create_plan('transition-plan', 'Transition Test', '1-init,2-refine,3-outline')
        result = run_script(LIFECYCLE_SCRIPT, 'transition', '--plan-id', 'transition-plan', '--completed', '1-init')
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['completed_phase'] == '1-init'
        assert data['next_phase'] == '2-refine'


def test_transition_last_phase():
    """Test transitioning when completing the last phase."""
    with PlanContext(plan_id='last-phase-plan'):
        _create_plan('last-phase-plan', 'Last Phase Test', '1-init,2-finalize')
        # Transition through all phases
        run_script(LIFECYCLE_SCRIPT, 'transition', '--plan-id', 'last-phase-plan', '--completed', '1-init')
        result = run_script(LIFECYCLE_SCRIPT, 'transition', '--plan-id', 'last-phase-plan', '--completed', '2-finalize')
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['completed_phase'] == '2-finalize'
        assert data['message'] == 'All phases completed'
        assert 'next_phase' not in data


def test_transition_invalid_phase():
    """Test transition with invalid phase name."""
    with PlanContext(plan_id='invalid-transition'):
        _create_plan('invalid-transition', 'Invalid Test', '1-init,2-refine')
        result = run_script(
            LIFECYCLE_SCRIPT, 'transition', '--plan-id', 'invalid-transition', '--completed', 'nonexistent'
        )
        assert result.success, 'Expected exit 0 for expected error'
        data = parse_toon(result.stdout)
        assert data['status'] == 'error'
        assert data['error'] == 'invalid_phase'


def test_transition_not_found():
    """Test transition exits 0 with TOON error for non-existent plan."""
    with PlanContext():
        result = run_script(LIFECYCLE_SCRIPT, 'transition', '--plan-id', 'nonexistent', '--completed', '1-init')
        assert result.success, 'Should exit 0 with TOON error output'
        assert 'status: error' in result.stdout


# =============================================================================
# Test: Route Command
# =============================================================================


def test_route_known_phase():
    """Test getting skill for a known phase."""
    with PlanContext():
        result = run_script(LIFECYCLE_SCRIPT, 'route', '--phase', '1-init')
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['phase'] == '1-init'
        assert data['skill'] == 'plan-init'


def test_route_all_phases():
    """Test routing for all standard phases."""
    phases = {
        '1-init': 'plan-init',
        '2-refine': 'request-refine',
        '3-outline': 'solution-outline',
        '4-plan': 'task-plan',
        '5-execute': 'plan-execute',
        '6-finalize': 'plan-finalize',
    }
    with PlanContext():
        for phase, expected_skill in phases.items():
            result = run_script(LIFECYCLE_SCRIPT, 'route', '--phase', phase)
            assert result.success, f'Script failed for {phase}: {result.stderr}'
            data = parse_toon(result.stdout)
            assert data['skill'] == expected_skill, f'Wrong skill for {phase}'


def test_route_unknown_phase():
    """Unknown ``--phase`` is rejected at the argparse boundary.

    The ``add_phase_arg`` builder wires ``choices=PHASES`` and the
    canonical ``parse_args_with_toon_errors`` handler maps the resulting
    argparse error (``argument --phase: invalid choice``) to
    ``status: error / error: invalid_phase`` TOON on stdout — see
    ``input_validation.py`` for the contract.
    """
    with PlanContext():
        result = run_script(LIFECYCLE_SCRIPT, 'route', '--phase', 'unknown-phase')
        assert result.success, 'Expected exit 0 for expected error'
        data = parse_toon(result.stdout)
        assert data['status'] == 'error'
        assert data['error'] == 'invalid_phase'


# =============================================================================
# Test: Archive Command
# =============================================================================


def test_archive_dry_run():
    """Test archive dry run mode."""
    with PlanContext(plan_id='archive-plan'):
        _create_plan('archive-plan', 'Archive Test', '1-init,2-refine')
        result = run_script(LIFECYCLE_SCRIPT, 'archive', '--plan-id', 'archive-plan', '--dry-run')
        assert result.success, f'Script failed: {result.stderr}'
        data = parse_toon(result.stdout)
        assert data['status'] == 'success'
        assert data['dry_run'] is True
        assert 'would_archive_to' in data


def test_archive_not_found():
    """Test archive with non-existent plan."""
    with PlanContext():
        result = run_script(LIFECYCLE_SCRIPT, 'archive', '--plan-id', 'nonexistent')
        assert result.success, 'Expected exit 0 for expected error'
        data = parse_toon(result.stdout)
        assert data['status'] == 'error'
        assert data['error'] == 'not_found'


# =============================================================================
# Helper: Create Git Repo with Changes
# =============================================================================


def _create_git_repo_with_changes(repo_dir: Path, base_branch: str = 'main') -> None:
    """Create a git repo with a base branch and committed changes on a feature branch.

    Structure:
    - main branch: initial commit with README.md
    - feature branch (HEAD): adds src/foo.py and src/bar.py
    """
    env = {
        **os.environ,
        'GIT_AUTHOR_NAME': 'Test',
        'GIT_AUTHOR_EMAIL': 'test@test.com',
        'GIT_COMMITTER_NAME': 'Test',
        'GIT_COMMITTER_EMAIL': 'test@test.com',
    }

    def run(*cmd):
        return subprocess.run(cmd, cwd=repo_dir, capture_output=True, text=True, check=True, env=env)

    run('git', 'init', '-b', base_branch)
    (repo_dir / 'README.md').write_text('# Test')
    run('git', 'add', '.')
    run('git', 'commit', '-m', 'initial')

    run('git', 'checkout', '-b', 'feature/test')
    src_dir = repo_dir / 'src'
    src_dir.mkdir()
    (src_dir / 'foo.py').write_text('# foo')
    (src_dir / 'bar.py').write_text('# bar')
    run('git', 'add', '.')
    run('git', 'commit', '-m', 'add source files')


# =============================================================================
# Test: Modified Files Collection on 5-execute Transition
# =============================================================================


def test_transition_5_execute_collects_modified_files():
    """Completing 5-execute populates modified_files in references.json."""
    with PlanContext(plan_id='modified-files-plan') as ctx:
        # Create plan with phases including 5-execute
        _create_plan(
            'modified-files-plan', 'Modified Files Test', '1-init,2-refine,3-outline,4-plan,5-execute,6-finalize'
        )

        # Advance to 5-execute
        run_script(LIFECYCLE_SCRIPT, 'transition', '--plan-id', 'modified-files-plan', '--completed', '1-init')
        run_script(LIFECYCLE_SCRIPT, 'transition', '--plan-id', 'modified-files-plan', '--completed', '2-refine')
        run_script(LIFECYCLE_SCRIPT, 'transition', '--plan-id', 'modified-files-plan', '--completed', '3-outline')
        run_script(LIFECYCLE_SCRIPT, 'transition', '--plan-id', 'modified-files-plan', '--completed', '4-plan')

        # Create a git repo with changes
        git_repo = Path(tempfile.mkdtemp())
        try:
            _create_git_repo_with_changes(git_repo, base_branch='main')

            # Create references.json with base_branch
            refs_path = ctx.plan_dir / 'references.json'
            refs_path.write_text(json.dumps({'base_branch': 'main'}, indent=2))

            # Transition completing 5-execute (cwd=git repo so git diff works)
            result = run_script(
                LIFECYCLE_SCRIPT,
                'transition',
                '--plan-id',
                'modified-files-plan',
                '--completed',
                '5-execute',
                cwd=git_repo,
            )
            assert result.success, f'Transition failed: {result.stderr}'
            data = parse_toon(result.stdout)
            assert data['status'] == 'success'

            # Verify references.json now has modified_files
            refs = json.loads(refs_path.read_text())
            assert 'modified_files' in refs, 'modified_files should be set'
            assert sorted(refs['modified_files']) == ['src/bar.py', 'src/foo.py']
        finally:
            import shutil

            shutil.rmtree(git_repo, ignore_errors=True)


def test_transition_non_execute_does_not_collect_modified_files():
    """Completing a phase other than 5-execute does NOT populate modified_files."""
    with PlanContext(plan_id='no-modified-plan') as ctx:
        _create_plan('no-modified-plan', 'No Modified Test', '1-init,2-refine,3-outline')

        # Create references.json with base_branch
        refs_path = ctx.plan_dir / 'references.json'
        refs_path.write_text(json.dumps({'base_branch': 'main'}, indent=2))

        # Create a git repo (so git is available if it were called)
        git_repo = Path(tempfile.mkdtemp())
        try:
            _create_git_repo_with_changes(git_repo, base_branch='main')

            # Transition completing 1-init (not 5-execute)
            result = run_script(
                LIFECYCLE_SCRIPT, 'transition', '--plan-id', 'no-modified-plan', '--completed', '1-init', cwd=git_repo
            )
            assert result.success, f'Transition failed: {result.stderr}'

            # Verify references.json does NOT have modified_files
            refs = json.loads(refs_path.read_text())
            assert 'modified_files' not in refs, 'modified_files should NOT be set for non-5-execute'
        finally:
            import shutil

            shutil.rmtree(git_repo, ignore_errors=True)


def test_transition_5_execute_uses_worktree_path():
    """Completing 5-execute with worktree_path uses git -C for the diff."""
    with PlanContext(plan_id='worktree-modified-plan') as ctx:
        _create_plan(
            'worktree-modified-plan', 'Worktree Modified Test', '1-init,2-refine,3-outline,4-plan,5-execute,6-finalize'
        )

        # Advance to 5-execute
        run_script(LIFECYCLE_SCRIPT, 'transition', '--plan-id', 'worktree-modified-plan', '--completed', '1-init')
        run_script(LIFECYCLE_SCRIPT, 'transition', '--plan-id', 'worktree-modified-plan', '--completed', '2-refine')
        run_script(LIFECYCLE_SCRIPT, 'transition', '--plan-id', 'worktree-modified-plan', '--completed', '3-outline')
        run_script(LIFECYCLE_SCRIPT, 'transition', '--plan-id', 'worktree-modified-plan', '--completed', '4-plan')

        # Create a git repo at a separate location (simulating a worktree)
        worktree_repo = Path(tempfile.mkdtemp())
        try:
            _create_git_repo_with_changes(worktree_repo, base_branch='main')

            # Set worktree_path in status metadata
            status_path = ctx.plan_dir / 'status.json'
            status = json.loads(status_path.read_text())
            status['metadata'] = {'worktree_path': str(worktree_repo)}
            status_path.write_text(json.dumps(status, indent=2))

            # Create references.json with base_branch
            refs_path = ctx.plan_dir / 'references.json'
            refs_path.write_text(json.dumps({'base_branch': 'main'}, indent=2))

            # Transition from a cwd that is NOT the git repo
            # (worktree_path should be used via git -C)
            result = run_script(
                LIFECYCLE_SCRIPT, 'transition', '--plan-id', 'worktree-modified-plan', '--completed', '5-execute'
            )
            assert result.success, f'Transition failed: {result.stderr}'

            # Verify references.json has modified_files via worktree path
            refs = json.loads(refs_path.read_text())
            assert 'modified_files' in refs, 'modified_files should be set via worktree path'
            assert sorted(refs['modified_files']) == ['src/bar.py', 'src/foo.py']
        finally:
            import shutil

            shutil.rmtree(worktree_repo, ignore_errors=True)
