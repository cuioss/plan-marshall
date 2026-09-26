# SPDX-License-Identifier: FSL-1.1-ALv2
"""Behavior-cluster tests carved from test_step_params.py: step."""

#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_step_params_fixtures import (
    _compose_ns,
    _get_ns,
    _seed_marshal_with_branch_cleanup_params,
    _set_ns,
    cmd_compose,
    cmd_step_params_get,
    cmd_step_params_set,
)

# =============================================================================
# step-params get
# =============================================================================


def test_step_params_get_returns_complete_param_object(plan_context):
    """step-params get returns the full snapshotted param object for a step in one call."""
    _seed_marshal_with_branch_cleanup_params(plan_context.fixture_dir)
    cmd_compose(_compose_ns('sp-get'))

    result = cmd_step_params_get(_get_ns('sp-get', '6-finalize', 'branch-cleanup'))

    assert result is not None and result['status'] == 'success'
    assert result['phase'] == '6-finalize'
    assert result['step_id'] == 'branch-cleanup'
    # the complete prefix-stripped param object, in a single call
    assert result['params'] == {
        'pr_merge_strategy': 'squash',
        'final_merge_without_asking': False,
        'auto_rebase_threshold': 'no_overlap_only',
    }


def test_step_params_get_returns_empty_for_ownerless_step(plan_context):
    """step-params get returns the empty param object for a step that owns no params."""
    _seed_marshal_with_branch_cleanup_params(plan_context.fixture_dir)
    cmd_compose(_compose_ns('sp-get-empty'))

    result = cmd_step_params_get(_get_ns('sp-get-empty', '6-finalize', 'push'))

    assert result is not None and result['status'] == 'success'
    assert result['params'] == {}


def test_step_params_get_resolves_default_prefixed_step_id(plan_context):
    """step-params get is prefix-agnostic: the ``default:``-prefixed step id
    resolves to the same bare-keyed snapshot entry as the bare id.

    The snapshot is keyed by the bare step id (``_snapshot_step_params`` strips
    the ``default:`` prefix at compose time), so a consumer querying the
    ``default:`` form must resolve to the same entry — otherwise the literal
    lookup raises ``step_not_found`` for a step that IS in the snapshot. This
    locks the prefix-agnostic contract so the literal-lookup bug cannot return.
    """
    _seed_marshal_with_branch_cleanup_params(plan_context.fixture_dir)
    cmd_compose(_compose_ns('sp-get-prefixed'))

    bare = cmd_step_params_get(_get_ns('sp-get-prefixed', '6-finalize', 'branch-cleanup'))
    prefixed = cmd_step_params_get(_get_ns('sp-get-prefixed', '6-finalize', 'default:branch-cleanup'))

    assert bare is not None and bare['status'] == 'success'
    assert prefixed is not None and prefixed['status'] == 'success'
    # the prefixed query resolves to the SAME params object as the bare query
    assert prefixed['params'] == bare['params']
    assert prefixed['params'] == {
        'pr_merge_strategy': 'squash',
        'final_merge_without_asking': False,
        'auto_rebase_threshold': 'no_overlap_only',
    }


def test_step_params_set_resolves_default_prefixed_step_id(plan_context):
    """step-params set is prefix-agnostic: a write via the ``default:``-prefixed
    id targets the same bare-keyed snapshot entry a bare get reads back."""
    _seed_marshal_with_branch_cleanup_params(plan_context.fixture_dir)
    cmd_compose(_compose_ns('sp-set-prefixed'))

    set_result = cmd_step_params_set(
        _set_ns('sp-set-prefixed', '6-finalize', 'default:branch-cleanup', 'pr_merge_strategy', 'rebase')
    )
    assert set_result is not None and set_result['status'] == 'success'

    # the override written via the prefixed id is visible to the bare get
    get_result = cmd_step_params_get(_get_ns('sp-set-prefixed', '6-finalize', 'branch-cleanup'))
    assert get_result is not None and get_result['status'] == 'success'
    assert get_result['params']['pr_merge_strategy'] == 'rebase'


def test_step_params_get_absent_step_id_errors(plan_context):
    """step-params get errors when the step id has no snapshotted params."""
    _seed_marshal_with_branch_cleanup_params(plan_context.fixture_dir)
    cmd_compose(_compose_ns('sp-get-absent'))

    result = cmd_step_params_get(_get_ns('sp-get-absent', '6-finalize', 'default:nonexistent'))

    assert result is not None and result['status'] == 'error'
    assert result['error'] == 'step_not_found'


def test_step_params_get_invalid_phase_errors(plan_context):
    """step-params get errors on a phase outside the record vocabulary."""
    _seed_marshal_with_branch_cleanup_params(plan_context.fixture_dir)
    cmd_compose(_compose_ns('sp-get-bad-phase'))

    result = cmd_step_params_get(_get_ns('sp-get-bad-phase', '7-bogus', 'branch-cleanup'))

    assert result is not None and result['status'] == 'error'
    assert result['error'] == 'invalid_phase'


def test_step_params_get_missing_manifest_returns_none(plan_context, capsys):
    """step-params get on a plan with no composed manifest emits file_not_found."""
    result = cmd_step_params_get(_get_ns('sp-get-no-manifest', '6-finalize', 'branch-cleanup'))

    assert result is None
    captured = capsys.readouterr()
    assert 'file_not_found' in captured.out


# =============================================================================
# step-params set (per-plan override)
# =============================================================================


def test_step_params_set_writes_override_and_round_trips(plan_context):
    """step-params set writes a per-plan override that round-trips through get."""
    _seed_marshal_with_branch_cleanup_params(plan_context.fixture_dir)
    cmd_compose(_compose_ns('sp-set'))

    set_result = cmd_step_params_set(_set_ns('sp-set', '6-finalize', 'branch-cleanup', 'pr_merge_strategy', 'rebase'))

    assert set_result is not None and set_result['status'] == 'success'
    assert set_result['params']['pr_merge_strategy'] == 'rebase'

    # round-trips through step-params get
    get_result = cmd_step_params_get(_get_ns('sp-set', '6-finalize', 'branch-cleanup'))
    assert get_result is not None
    assert get_result['params']['pr_merge_strategy'] == 'rebase'


def test_step_params_set_override_wins_over_marshal_default(plan_context):
    """A step-params set override wins over the marshal.json compose-time default."""
    _seed_marshal_with_branch_cleanup_params(plan_context.fixture_dir)
    cmd_compose(_compose_ns('sp-override'))

    # precondition: the compose-time snapshot carries the marshal default (squash)
    before = cmd_step_params_get(_get_ns('sp-override', '6-finalize', 'branch-cleanup'))
    assert before is not None
    assert before['params']['pr_merge_strategy'] == 'squash'

    # write a per-plan override
    cmd_step_params_set(_set_ns('sp-override', '6-finalize', 'branch-cleanup', 'pr_merge_strategy', 'merge'))

    # the manifest value now wins over the marshal.json default
    after = cmd_step_params_get(_get_ns('sp-override', '6-finalize', 'branch-cleanup'))
    assert after is not None
    assert after['params']['pr_merge_strategy'] == 'merge'


def test_step_params_set_preserves_other_params(plan_context):
    """step-params set writing one param leaves the step's other params untouched."""
    _seed_marshal_with_branch_cleanup_params(plan_context.fixture_dir)
    cmd_compose(_compose_ns('sp-preserve'))

    cmd_step_params_set(_set_ns('sp-preserve', '6-finalize', 'branch-cleanup', 'final_merge_without_asking', 'true'))

    result = cmd_step_params_get(_get_ns('sp-preserve', '6-finalize', 'branch-cleanup'))
    assert result is not None
    # the touched param is coerced (string -> bool)
    assert result['params']['final_merge_without_asking'] is True
    # untouched siblings survive
    assert result['params']['pr_merge_strategy'] == 'squash'
    assert result['params']['auto_rebase_threshold'] == 'no_overlap_only'


def test_step_params_set_coerces_int_value(plan_context):
    """step-params set coerces an integer-literal value to int."""
    _seed_marshal_with_branch_cleanup_params(plan_context.fixture_dir)
    cmd_compose(_compose_ns('sp-int'))

    result = cmd_step_params_set(_set_ns('sp-int', '6-finalize', 'sonar-roundtrip', 'ce_wait_timeout_seconds', '720'))

    assert result is not None and result['status'] == 'success'
    assert result['params']['ce_wait_timeout_seconds'] == 720


def test_step_params_set_absent_step_id_errors(plan_context):
    """step-params set errors when the step id has no snapshotted params."""
    _seed_marshal_with_branch_cleanup_params(plan_context.fixture_dir)
    cmd_compose(_compose_ns('sp-set-absent'))

    result = cmd_step_params_set(
        _set_ns('sp-set-absent', '6-finalize', 'default:nonexistent', 'pr_merge_strategy', 'merge')
    )

    assert result is not None and result['status'] == 'error'
    assert result['error'] == 'step_not_found'


def test_step_params_set_invalid_phase_errors(plan_context):
    """step-params set errors on a phase outside the record vocabulary."""
    _seed_marshal_with_branch_cleanup_params(plan_context.fixture_dir)
    cmd_compose(_compose_ns('sp-set-bad-phase'))

    result = cmd_step_params_set(_set_ns('sp-set-bad-phase', '7-bogus', 'branch-cleanup', 'pr_merge_strategy', 'merge'))

    assert result is not None and result['status'] == 'error'
    assert result['error'] == 'invalid_phase'


def test_step_params_set_missing_manifest_returns_none(plan_context, capsys):
    """step-params set on a plan with no composed manifest emits file_not_found."""
    result = cmd_step_params_set(
        _set_ns('sp-set-no-manifest', '6-finalize', 'branch-cleanup', 'pr_merge_strategy', 'merge')
    )

    assert result is None
    captured = capsys.readouterr()
    assert 'file_not_found' in captured.out
