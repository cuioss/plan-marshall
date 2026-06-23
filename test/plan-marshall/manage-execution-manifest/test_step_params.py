#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``step-params get`` / ``step-params set`` verbs of
manage-execution-manifest.py.

These verbs read/write the plan-local per-step param snapshot the composer
writes into the manifest body (``body[phase].step_params``). ``step-params get``
returns the complete param object for a step in a single call; ``step-params
set`` writes a per-plan override that wins over the marshal.json compose-time
default for subsequent reads. Both operate on the persisted manifest, never on
marshal.json.

Covers:
- ``step-params get`` returns the full snapshotted param object in one call.
- ``step-params set`` writes a per-plan override that round-trips through
  ``step-params get`` and wins over the marshal.json compose-time default.
- The absent-step-id / missing-manifest / invalid-phase error paths.
"""

import importlib.util
import json
from argparse import Namespace
from pathlib import Path

# Tier 2 direct imports via importlib (scripts loaded via PYTHONPATH at runtime).
_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-execution-manifest'
    / 'scripts'
)


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    assert spec is not None, f'Failed to load module spec for {filename}'
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


_mem = _load_module('_mem_script', 'manage-execution-manifest.py')
cmd_compose = _mem.cmd_compose
cmd_step_params_get = _mem.cmd_step_params_get
cmd_step_params_set = _mem.cmd_step_params_set
DEFAULT_PHASE_6_STEPS = _mem.DEFAULT_PHASE_6_STEPS
read_manifest = _mem.read_manifest
write_manifest = _mem.write_manifest
get_manifest_path = _mem.get_manifest_path
_denormalize_step_params_for_write = _mem._denormalize_step_params_for_write
_normalize_step_params_block = _mem._normalize_step_params_block

# Quiet down the best-effort decision-log subprocess.
_mem._log_decision = lambda *a, **kw: None  # type: ignore[attr-defined]


# =============================================================================
# Namespace Helpers
# =============================================================================


def _compose_ns(plan_id: str, phase_6_steps: str | None = None) -> Namespace:
    return Namespace(
        plan_id=plan_id,
        change_type='feature',
        track='complex',
        scope_estimate='multi_module',
        recipe_key=None,
        affected_files_count=11,
        phase_5_steps='quality-gate,module-tests',
        phase_6_steps=phase_6_steps if phase_6_steps is not None else ','.join(DEFAULT_PHASE_6_STEPS),
        commit_and_push=None,
    )


def _get_ns(plan_id: str, phase: str, step_id: str) -> Namespace:
    return Namespace(plan_id=plan_id, phase=phase, step_id=step_id)


def _set_ns(plan_id: str, phase: str, step_id: str, param: str, value: str) -> Namespace:
    return Namespace(plan_id=plan_id, phase=phase, step_id=step_id, param=param, value=value)


def _seed_marshal_with_branch_cleanup_params(fixture_dir: Path) -> None:
    """Write a marshal.json whose phase-6-finalize steps map carries nested params."""
    marshal_path = fixture_dir / 'marshal.json'
    data = {
        'plan': {
            'phase-6-finalize': {
                'steps': {
                    'default:commit-push': {},
                    'default:create-pr': {},
                    'default:automated-review': {'review_bot_buffer_seconds': 240},
                    'default:sonar-roundtrip': {
                        'touched_file_cleanup': 'new_code_only',
                        'do_transition': False,
                        'ce_wait_timeout_seconds': 600,
                    },
                    'default:lessons-capture': {},
                    'default:branch-cleanup': {
                        'pr_merge_strategy': 'squash',
                        'final_merge_without_asking': False,
                        'auto_rebase_threshold': 'no_overlap_only',
                    },
                    'default:record-metrics': {},
                    'default:archive-plan': {},
                }
            }
        }
    }
    marshal_path.write_text(json.dumps(data), encoding='utf-8')


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

    result = cmd_step_params_get(_get_ns('sp-get-empty', '6-finalize', 'commit-push'))

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

    set_result = cmd_step_params_set(
        _set_ns('sp-set', '6-finalize', 'branch-cleanup', 'pr_merge_strategy', 'rebase')
    )

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
    cmd_step_params_set(
        _set_ns('sp-override', '6-finalize', 'branch-cleanup', 'pr_merge_strategy', 'merge')
    )

    # the manifest value now wins over the marshal.json default
    after = cmd_step_params_get(_get_ns('sp-override', '6-finalize', 'branch-cleanup'))
    assert after is not None
    assert after['params']['pr_merge_strategy'] == 'merge'


def test_step_params_set_preserves_other_params(plan_context):
    """step-params set writing one param leaves the step's other params untouched."""
    _seed_marshal_with_branch_cleanup_params(plan_context.fixture_dir)
    cmd_compose(_compose_ns('sp-preserve'))

    cmd_step_params_set(
        _set_ns('sp-preserve', '6-finalize', 'branch-cleanup', 'final_merge_without_asking', 'true')
    )

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

    result = cmd_step_params_set(
        _set_ns('sp-int', '6-finalize', 'sonar-roundtrip', 'ce_wait_timeout_seconds', '720')
    )

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

    result = cmd_step_params_set(
        _set_ns('sp-set-bad-phase', '7-bogus', 'branch-cleanup', 'pr_merge_strategy', 'merge')
    )

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


# =============================================================================
# Empty-{} suppression at the manifest write boundary + read-path coercion
# =============================================================================
#
# `_denormalize_step_params_for_write` collapses an ownerless step_params value
# (empty {} or None) to None right before serializing, so the manifest TOON never
# carries a noisy empty {} block. `_normalize_step_params_block` (the read
# boundary) coerces every per-step value that is not a non-empty dict — None, {},
# and the TOON-round-tripped '' — back to {}, so an ownerless step reads back as
# {} no matter which on-disk representation it carries.


def test_denormalize_collapses_ownerless_step_params_to_none():
    """The write boundary collapses ownerless step_params ({} / None) to None; param-owning steps keep their dict."""
    manifest = {
        'phase_5': {
            'step_params': {
                'quality-gate': {},
                'module-tests': None,
            }
        },
        'phase_6': {
            'step_params': {
                'commit-push': {},
                'branch-cleanup': {'pr_merge_strategy': 'squash'},
            }
        },
    }

    result = _denormalize_step_params_for_write(manifest)

    # ownerless steps collapse to None (serialized as null) — no empty {} block
    assert result['phase_5']['step_params'] == {'quality-gate': None, 'module-tests': None}
    assert result['phase_6']['step_params']['commit-push'] is None
    # param-owning step keeps its nested object
    assert result['phase_6']['step_params']['branch-cleanup'] == {'pr_merge_strategy': 'squash'}
    # the input manifest is never mutated
    assert manifest['phase_5']['step_params']['quality-gate'] == {}


def test_normalize_step_params_block_coerces_all_empty_shapes_to_empty_dict():
    """The read boundary coerces None / {} / '' per-step values back to {}; param-owning steps keep their dict."""
    manifest = {
        'phase_5': {
            'step_params': {
                'quality-gate': None,
                'module-tests': {},
                'coverage': '',
            }
        },
        'phase_6': {
            'step_params': {
                'commit-push': None,
                'branch-cleanup': {'pr_merge_strategy': 'squash'},
            }
        },
    }

    _normalize_step_params_block(manifest)

    # every absent-or-empty representation reads back as the empty dict
    assert manifest['phase_5']['step_params'] == {
        'quality-gate': {},
        'module-tests': {},
        'coverage': {},
    }
    assert manifest['phase_6']['step_params']['commit-push'] == {}
    # the param-owning step keeps its nested object
    assert manifest['phase_6']['step_params']['branch-cleanup'] == {'pr_merge_strategy': 'squash'}


def test_write_manifest_serializes_no_empty_dict_for_ownerless_steps(plan_context):
    """write_manifest never serializes an empty {} block for an ownerless step.

    Reading the raw on-disk TOON proves the ownerless step round-trips through
    the write boundary as null (TOON renders it as the empty string), not a {}
    block, satisfying the no-empty-{} contract end to end.
    """
    manifest = {
        'phase_5': {'step_params': {'quality-gate': {}, 'module-tests': {}}},
        'phase_6': {'step_params': {'commit-push': {}, 'branch-cleanup': {'pr_merge_strategy': 'squash'}}},
    }

    write_manifest('sp-write-no-empty', manifest)

    # the raw serialized manifest carries no empty {} block for ownerless steps
    raw = get_manifest_path('sp-write-no-empty').read_text(encoding='utf-8')
    parsed = _mem.parse_toon(raw)
    # ownerless steps serialized as null (None), not as a {} block
    assert parsed['phase_5']['step_params'].get('quality-gate') is None
    assert parsed['phase_6']['step_params'].get('commit-push') is None
    # param-owning step survived
    assert parsed['phase_6']['step_params']['branch-cleanup'] == {'pr_merge_strategy': 'squash'}


def test_write_then_read_manifest_round_trips_ownerless_step_to_empty_dict(plan_context):
    """An ownerless step written via write_manifest reads back as {} via read_manifest.

    End-to-end suppression+coercion: the write boundary collapses {} to null, and
    the read boundary coerces it back to {}, so the ownerless step is {} on read
    while no empty {} block was ever serialized.
    """
    manifest = {
        'phase_5': {'step_params': {'quality-gate': {}, 'module-tests': {}}},
        'phase_6': {'step_params': {'commit-push': {}, 'branch-cleanup': {'pr_merge_strategy': 'squash'}}},
    }

    write_manifest('sp-round-trip', manifest)
    read_back = read_manifest('sp-round-trip')

    assert read_back is not None
    # ownerless steps read back as the empty dict
    assert read_back['phase_5']['step_params']['quality-gate'] == {}
    assert read_back['phase_5']['step_params']['module-tests'] == {}
    assert read_back['phase_6']['step_params']['commit-push'] == {}
    # param-owning step round-trips unchanged
    assert read_back['phase_6']['step_params']['branch-cleanup'] == {'pr_merge_strategy': 'squash'}


def test_compose_then_read_manifest_ownerless_steps_read_as_empty_dict(plan_context):
    """A composed manifest's ownerless steps read back as {} (no empty {} on disk).

    Exercises the real compose → write → read path: cmd_compose snapshots
    ownerless verify/finalize steps as null, write_manifest serializes no empty
    {}, and read_manifest coerces them back to {}.
    """
    _seed_marshal_with_branch_cleanup_params(plan_context.fixture_dir)
    cmd_compose(_compose_ns('sp-compose-ownerless'))

    # the raw on-disk manifest carries no empty {} block for ownerless steps
    raw = get_manifest_path('sp-compose-ownerless').read_text(encoding='utf-8')
    parsed_raw = _mem.parse_toon(raw)
    phase_6_raw = parsed_raw['phase_6']['step_params']
    # commit-push is ownerless — its on-disk value is null (None), not a {} block
    assert phase_6_raw.get('commit-push') is None

    # the read boundary coerces it back to {}
    read_back = read_manifest('sp-compose-ownerless')
    assert read_back is not None
    assert read_back['phase_6']['step_params']['commit-push'] == {}
    # the param-owning step survives the round-trip
    assert read_back['phase_6']['step_params']['branch-cleanup'] == {
        'pr_merge_strategy': 'squash',
        'final_merge_without_asking': False,
        'auto_rebase_threshold': 'no_overlap_only',
    }
