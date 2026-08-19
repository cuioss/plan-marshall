#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-status.py read + phase verbs + worktree-path resolution."""


import json
from argparse import Namespace
from pathlib import Path

from _manage_status_read_fixtures import SCRIPT_PATH, _query, cmd_create, cmd_get_worktree_path, cmd_set_phase

from conftest import run_script


def test_get_worktree_path_pending_when_not_yet_materialized(plan_context):
    """use_worktree=true but worktree_path empty → worktree_state: pending.

    A plan can opt into worktree mode before the worktree directory has been
    materialized — between init and the worktree-creation step. In that
    pre-materialization window the verb returns the `pending` tri-state
    branch so callers can fall back to the main checkout cwd instead of
    erroring out.
    """
    plan_id = 'wt-resolve-pending'
    # Seed via cmd_create (true) — create persists only {use_worktree: True},
    # which IS the pre-materialization shape: use_worktree=true with no path yet.
    cmd_create(
        Namespace(
            plan_id=plan_id,
            title='Resolve Pending',
            phases='1-init,2-refine',
            force=False,
            use_worktree=True,
        )
    )
    status_path = plan_context.plan_dir_for(plan_id) / 'status.json'
    status = json.loads(status_path.read_text(encoding='utf-8'))
    # Pre-materialization shape: use_worktree=true but no path/branch.
    status['metadata'] = {'use_worktree': True}
    status_path.write_text(json.dumps(status), encoding='utf-8')

    result = cmd_get_worktree_path(Namespace(plan_id=plan_id))
    assert result['status'] == 'success', (
        f'Pre-materialization must succeed (tri-state contract), got '
        f'{result!r}.'
    )
    assert result['use_worktree'] is True
    assert result['worktree_state'] == 'pending', (
        f'Expected worktree_state=pending, got '
        f'{result.get("worktree_state")!r}.'
    )
    assert result['worktree_path'] == ''
    assert result['not_yet_materialized'] is True


def test_cli_get_worktree_path_help(plan_context):
    """get-worktree-path --help must succeed (subparser registration check)."""
    result = run_script(SCRIPT_PATH, 'get-worktree-path', '--help')
    assert result.success, (
        f'get-worktree-path --help failed: {result.stderr!r}. '
        f'Subparser is missing from manage-status.py.'
    )


# =============================================================================
# Test: cmd_get_worktree_path pre-materialization tri-state (extended coverage)
# =============================================================================


class TestGetWorktreePathPreMaterialization:
    """Pin pre-materialization tri-state edge cases for cmd_get_worktree_path.

    Covers the deferred-pending branch of the tri-state contract across the
    three on-disk shapes a plan can take between init and worktree
    materialization:

    - ``metadata = {use_worktree: True}`` (no path key at all)
    - ``metadata = {use_worktree: True, worktree_path: ''}`` (explicit empty)
    - ``metadata = {use_worktree: True, worktree_path: None}`` (null)
    """

    @staticmethod
    def _seed_pre_materialization(plan_dir, plan_id: str, metadata: dict) -> None:
        """Create the plan via cmd_create then overwrite metadata directly.

        cmd_create persists only ``{use_worktree}`` and never seeds a
        worktree_path / worktree_branch, so the specific on-disk shapes under
        test (and the legacy shapes a read must still tolerate) are written
        directly. Direct file write is the canonical pattern (see also
        test_get_worktree_path_pending_when_not_yet_materialized).
        """
        cmd_create(
            Namespace(
                plan_id=plan_id,
                title='Pre-Materialization Edge Case',
                phases='1-init,2-refine',
                force=False,
                use_worktree=False,
            )
        )
        status_path = plan_dir / 'status.json'
        status = json.loads(status_path.read_text(encoding='utf-8'))
        status['metadata'] = metadata
        status_path.write_text(json.dumps(status), encoding='utf-8')

    def test_pending_when_use_worktree_true_and_path_key_absent(self, plan_context):
        """use_worktree=true with NO worktree_path key → pending."""
        plan_id = 'wt-pre-mat-missing-key'
        self._seed_pre_materialization(plan_context.plan_dir_for(plan_id), plan_id, {'use_worktree': True})
        result = cmd_get_worktree_path(Namespace(plan_id=plan_id))
        assert result['status'] == 'success'
        assert result['worktree_state'] == 'pending'
        assert result['worktree_path'] == ''
        assert result['not_yet_materialized'] is True, (
            f'Expected not_yet_materialized=True for shape '
            f'{{use_worktree: True}} (no path key), got '
            f'{result.get("not_yet_materialized")!r}.'
        )

    def test_pending_when_worktree_path_is_explicit_empty_string(self, plan_context):
        """use_worktree=true with worktree_path='' → pending."""
        plan_id = 'wt-pre-mat-empty-string'
        self._seed_pre_materialization(
            plan_context.plan_dir_for(plan_id), plan_id, {'use_worktree': True, 'worktree_path': ''}
        )
        result = cmd_get_worktree_path(Namespace(plan_id=plan_id))
        assert result['status'] == 'success'
        assert result['worktree_state'] == 'pending'
        assert result['worktree_path'] == ''
        assert result['not_yet_materialized'] is True

    def test_pending_when_worktree_path_is_null(self, plan_context):
        """use_worktree=true with worktree_path=None → pending.

        The JSON null shape is a real possibility — manage-status writers
        could leave ``worktree_path: null`` between phases. The tri-state
        verb must treat null the same as missing/empty.
        """
        plan_id = 'wt-pre-mat-null'
        self._seed_pre_materialization(
            plan_context.plan_dir_for(plan_id), plan_id, {'use_worktree': True, 'worktree_path': None}
        )
        result = cmd_get_worktree_path(Namespace(plan_id=plan_id))
        assert result['status'] == 'success'
        assert result['worktree_state'] == 'pending'
        assert result['worktree_path'] == ''
        assert result['not_yet_materialized'] is True

    def test_pending_omits_worktree_branch_when_unset(self, plan_context):
        """Pending state must NOT carry a worktree_branch field when unset.

        The symmetric contract: just as ``disabled`` omits path/branch,
        ``pending`` must omit branch when the metadata has none yet. The
        materialized state is the only one that carries a branch.
        """
        plan_id = 'wt-pre-mat-no-branch'
        self._seed_pre_materialization(plan_context.plan_dir_for(plan_id), plan_id, {'use_worktree': True})
        result = cmd_get_worktree_path(Namespace(plan_id=plan_id))
        assert result['worktree_state'] == 'pending'
        # Branch absence must be explicit, not a leaked empty key.
        assert result.get('worktree_branch', '') == '', (
            f'Pending state leaked a worktree_branch={result.get("worktree_branch")!r}; '
            f'pre-materialization shapes have no branch yet.'
        )

    def test_pending_includes_worktree_branch_when_metadata_has_branch(self, plan_context):
        """Pending state surfaces worktree_branch when the metadata carries one.

        A legacy plan (or any metadata shape that pairs an empty worktree_path
        with a worktree_branch) must still be read tolerantly: the tri-state
        response for the pending case carries the branch through from metadata
        so downstream consumers read it from the same envelope as the
        materialized case. The read verb does not assume the no-sentinel writer
        contract — it reflects whatever metadata is on disk.

        Symmetric counterpart to
        test_pending_omits_worktree_branch_when_unset: when the metadata
        carries a branch, the pending envelope MUST carry it through.
        """
        plan_id = 'wt-pre-mat-with-branch'
        branch = 'feature/pre-mat-branch'
        self._seed_pre_materialization(
            plan_context.plan_dir_for(plan_id),
            plan_id,
            {
                'use_worktree': True,
                'worktree_path': '',
                'worktree_branch': branch,
            },
        )
        result = cmd_get_worktree_path(Namespace(plan_id=plan_id))
        assert result['worktree_state'] == 'pending'
        assert result['not_yet_materialized'] is True
        assert result.get('worktree_branch') == branch, (
            f'Pending state dropped worktree_branch from metadata; '
            f'expected {branch!r}, got {result.get("worktree_branch")!r}.'
        )

    def test_pending_contract_callers_can_branch_on_either_signal(self, plan_context):
        """Tri-state contract: worktree_state and not_yet_materialized agree.

        Callers downstream may branch on EITHER signal — the contract
        guarantees they never disagree. A regression that ships the
        ``pending`` worktree_state without the ``not_yet_materialized``
        flag (or vice versa) would silently break consumers that picked
        the other signal.
        """
        plan_id = 'wt-pre-mat-symmetric-signals'
        self._seed_pre_materialization(plan_context.plan_dir_for(plan_id), plan_id, {'use_worktree': True})
        result = cmd_get_worktree_path(Namespace(plan_id=plan_id))

        is_pending_state = result.get('worktree_state') == 'pending'
        is_not_yet_materialized = result.get('not_yet_materialized') is True
        assert is_pending_state == is_not_yet_materialized, (
            f'Tri-state signals disagree: worktree_state={result.get("worktree_state")!r}, '
            f'not_yet_materialized={result.get("not_yet_materialized")!r}. The two '
            f'signals MUST agree so callers can branch on either one.'
        )


# =============================================================================
# CLI Plumbing Tests (Tier 3 - subprocess)
# =============================================================================


def test_cli_missing_required_args(plan_context):
    """Test that missing required args produces exit code 2 (argparse error)."""
    result = run_script(SCRIPT_PATH, 'create', '--plan-id', 'test-plan')
    # argparse exits with code 2 for missing required args (--title, --phases)
    assert not result.success


def test_cli_help_flag(plan_context):
    """Test that --help produces exit code 0."""
    result = run_script(SCRIPT_PATH, '--help')
    assert result.success


def test_cli_subcommand_help(plan_context):
    """Test that subcommand --help produces exit code 0."""
    result = run_script(SCRIPT_PATH, 'create', '--help')
    assert result.success


# =============================================================================
# Regression Tests: Not-found conditions exit 0 with TOON error
# =============================================================================


def test_cli_read_not_found_exits_zero(plan_context):
    """Regression: read with missing status.json exits 0 with TOON error output."""
    result = run_script(SCRIPT_PATH, 'read', '--plan-id', 'nonexistent')
    assert result.success, f'Should exit 0, got: {result.stderr}'
    assert 'status: error' in result.stdout
    assert 'file_not_found' in result.stdout


def test_cli_get_routing_context_not_found_exits_zero(plan_context):
    """Regression: get-routing-context with missing status.json exits 0 with TOON error output."""
    result = run_script(SCRIPT_PATH, 'get-routing-context', '--plan-id', 'nonexistent')
    assert result.success, f'Should exit 0, got: {result.stderr}'
    assert 'status: error' in result.stdout
    assert 'file_not_found' in result.stdout


# =============================================================================
# Tests: get alias for read (subprocess / CLI plumbing)
# =============================================================================


class TestCliGetAlias:
    """Subprocess test pinning ``get`` as an alias for the ``read`` subcommand."""

    def test_cli_get_alias_succeeds(self, plan_context):
        """``manage-status get`` succeeds via the CLI for an existing plan."""
        cmd_create(
            Namespace(plan_id='get-alias', title='Get Alias', phases='1-init,2-refine', force=False)
        )

        result = run_script(SCRIPT_PATH, 'get', '--plan-id', 'get-alias')

        assert result.success, f'Script failed: {result.stderr}'
        assert 'status: success' in result.stdout
        assert 'title: Get Alias' in result.stdout

    def test_cli_get_alias_matches_read(self, plan_context):
        """``get`` and ``read`` produce identical payloads for the same plan."""
        cmd_create(
            Namespace(plan_id='get-alias-match', title='Get Alias Match', phases='1-init,2-refine', force=False)
        )

        get_result = run_script(SCRIPT_PATH, 'get', '--plan-id', 'get-alias-match')
        read_result = run_script(SCRIPT_PATH, 'read', '--plan-id', 'get-alias-match')

        assert get_result.returncode == 0
        assert read_result.returncode == 0
        assert get_result.returncode == read_result.returncode
        assert get_result.stdout == read_result.stdout


def test_script_source_uses_canonical_local_plans_path():
    """The script source references .plan/local/plans, not the legacy form.

    Regression guard for the path-consolidation sweep: the module docstring's
    storage line and the ``list-orphans`` help text must spell the plan
    location as ``.plan/local/plans/`` — the legacy bare ``.plan/plans/`` form
    is incorrect since runtime state moved under ``.plan/local``.
    """
    import re

    source = Path(SCRIPT_PATH).read_text(encoding='utf-8')
    assert '.plan/local/plans/' in source
    legacy = re.findall(r'(?<!local/)\.plan/plans/', source)
    assert legacy == [], f'Legacy .plan/plans/ strings remain: {legacy}'


# =============================================================================
# Regression Tests: cmd_set_phase fires the persisted-title-state-write drive seam
# =============================================================================
#
# cmd_set_phase is a current_phase writer, so it fires the shared _surface_drive
# seam (bind + repaint) AFTER write_status. An invalid-phase error returns before
# write_status, so the seam must NOT fire on that path.


def test_cmd_set_phase_fires_drive_seam_after_write(plan_context, monkeypatch):
    """cmd_set_phase fires _surface_drive exactly once (with the plan_id) after the write."""
    cmd_create(
        Namespace(
            plan_id='setphase-drive',
            title='Set Phase Drive',
            phases='1-init,2-refine,3-outline',
            force=False,
        )
    )
    calls = []
    monkeypatch.setattr(_query, '_surface_drive', lambda pid: calls.append(pid))

    result = cmd_set_phase(Namespace(plan_id='setphase-drive', phase='3-outline'))

    assert result['status'] == 'success'
    assert calls == ['setphase-drive'], (
        f'cmd_set_phase must fire the drive seam once with the plan_id, got {calls!r}.'
    )


def test_cmd_set_phase_invalid_does_not_fire_drive_seam(plan_context, monkeypatch):
    """An invalid-phase error returns before write_status — the seam must NOT fire."""
    cmd_create(
        Namespace(plan_id='setphase-invalid-drive', title='Invalid', phases='1-init,2-refine', force=False)
    )
    calls = []
    monkeypatch.setattr(_query, '_surface_drive', lambda pid: calls.append(pid))

    result = cmd_set_phase(Namespace(plan_id='setphase-invalid-drive', phase='nonexistent'))

    assert result['status'] == 'error'
    assert result['error'] == 'invalid_phase'
    assert calls == [], (
        f'The drive seam must not fire when set-phase is rejected before '
        f'write_status, got {calls!r}.'
    )
