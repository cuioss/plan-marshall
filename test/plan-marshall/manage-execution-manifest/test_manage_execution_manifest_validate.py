#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``validate`` subcommand of manage-execution-manifest.py.

Split from test_manage_execution_manifest.py — tier 2 direct-import tests for
the validate path plus the CLI happy-path roundtrip.
"""

import importlib.util
import json
from argparse import Namespace
from pathlib import Path

from conftest import get_script_path, run_script

# Script path for subprocess (CLI plumbing) tests.
SCRIPT_PATH = get_script_path('plan-marshall', 'manage-execution-manifest', 'manage-execution-manifest.py')

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
cmd_validate = _mem.cmd_validate
cmd_step_params_get = _mem.cmd_step_params_get
get_manifest_path = _mem.get_manifest_path
read_manifest = _mem.read_manifest
DEFAULT_PHASE_5_STEPS = _mem.DEFAULT_PHASE_5_STEPS
DEFAULT_PHASE_6_STEPS = _mem.DEFAULT_PHASE_6_STEPS

# Step-owner schema primitives live in _manifest_core (loaded directly; the
# hyphenated entry does not re-export them). See _manifest_core.py § "Step
# ownership".
_core = _load_module('_mem_core', '_manifest_core.py')
VALID_STEP_OWNERS = _core.VALID_STEP_OWNERS
validate_step_owner = _core.validate_step_owner
owner_of = _core.owner_of
ORCHESTRATOR_OWNED_STEPS = _core.ORCHESTRATOR_OWNED_STEPS

# Quiet down the best-effort decision-log subprocess.
_mem._log_decision = lambda *a, **kw: None  # type: ignore[attr-defined]


# =============================================================================
# Namespace Helpers
# =============================================================================


def _compose_ns(
    plan_id: str = 'test-plan',
    change_type: str = 'feature',
    track: str = 'complex',
    scope_estimate: str = 'multi_module',
    recipe_key: str | None = None,
    affected_files_count: int = 5,
    phase_5_steps: str | None = 'quality-gate,module-tests',
    phase_6_steps: str | None = ','.join(DEFAULT_PHASE_6_STEPS),
    commit_and_push: str | None = None,
) -> Namespace:
    return Namespace(
        plan_id=plan_id,
        change_type=change_type,
        track=track,
        scope_estimate=scope_estimate,
        recipe_key=recipe_key,
        affected_files_count=affected_files_count,
        phase_5_steps=phase_5_steps,
        phase_6_steps=phase_6_steps,
        commit_and_push=commit_and_push,
    )


def _validate_ns(
    plan_id: str = 'test-plan',
    phase_5_steps: str | None = 'quality-gate,module-tests,coverage',
    phase_6_steps: str | None = ','.join(DEFAULT_PHASE_6_STEPS),
) -> Namespace:
    return Namespace(plan_id=plan_id, phase_5_steps=phase_5_steps, phase_6_steps=phase_6_steps)


# =============================================================================
# validate subcommand tests
# =============================================================================


def test_validate_happy_path(plan_context):
    cmd_compose(_compose_ns(plan_id='val-ok'))
    result = cmd_validate(_validate_ns(plan_id='val-ok'))
    assert result is not None and result['status'] == 'success'
    assert result['valid'] is True
    assert result['phase_5_unknown_steps_count'] == 0
    assert result['phase_6_unknown_steps_count'] == 0


def test_validate_succeeds_on_manifest_with_step_params_block(plan_context):
    """validate succeeds against a composed manifest carrying the step_params snapshot.

    The composer now writes a step_params block into both phase sections. validate
    operates on the verification_steps / steps lists and is agnostic to the
    step_params snapshot — its presence must not trip validation.
    """
    cmd_compose(_compose_ns(plan_id='val-step-params'))
    # the composed manifest carries step_params under both phases
    manifest = _mem.read_manifest('val-step-params')
    assert manifest is not None
    assert 'step_params' in manifest['phase_5']
    assert 'step_params' in manifest['phase_6']

    result = cmd_validate(_validate_ns(plan_id='val-step-params'))
    assert result is not None and result['status'] == 'success'
    assert result['valid'] is True


def test_validate_missing_manifest_returns_none(plan_context, capsys):
    result = cmd_validate(_validate_ns(plan_id='val-missing'))
    assert result is None
    captured = capsys.readouterr()
    assert 'file_not_found' in captured.out


def test_validate_unknown_phase_5_step_flagged(plan_context):
    cmd_compose(
        _compose_ns(
            plan_id='val-unknown-p5',
            phase_5_steps='quality-gate,module-tests',
        )
    )
    # Now validate with a candidate set that DOESN'T include module-tests.
    result = cmd_validate(
        _validate_ns(
            plan_id='val-unknown-p5',
            phase_5_steps='quality-gate',
        )
    )
    assert result is not None and result['status'] == 'error'
    assert result['error'] == 'invalid_manifest'
    assert result['phase_5_unknown_steps_count'] == 1
    assert 'module-tests' in result['phase_5_unknown_steps']


def test_validate_without_candidate_sets_skips_step_id_check(plan_context):
    """validate succeeds (status=success) when candidate sets aren't supplied."""
    cmd_compose(_compose_ns(plan_id='val-no-candidates'))
    result = cmd_validate(
        Namespace(
            plan_id='val-no-candidates',
            phase_5_steps=None,
            phase_6_steps=None,
        )
    )
    assert result is not None and result['status'] == 'success'
    assert result['valid'] is True


def test_validate_unknown_phase_6_step_flagged(plan_context):
    """validate flags phase_6 steps not present in the candidate set."""
    cmd_compose(
        _compose_ns(
            plan_id='val-unknown-p6',
            # Default phase_6 candidate set; manifest will contain
            # the full DEFAULT_PHASE_6_STEPS list.
        )
    )
    result = cmd_validate(
        Namespace(
            plan_id='val-unknown-p6',
            phase_5_steps=None,
            # Restrict allowed phase_6 steps to a tiny subset; everything
            # else in the manifest becomes "unknown".
            phase_6_steps='push',
        )
    )
    assert result is not None and result['status'] == 'error'
    assert result['error'] == 'invalid_manifest'
    assert result['phase_6_unknown_steps_count'] >= 1
    # All non-push DEFAULT_PHASE_6_STEPS entries should be flagged.
    assert 'create-pr' in result['phase_6_unknown_steps']


def test_validate_detects_corrupt_manifest_version(plan_context):
    """validate flags a manifest_version mismatch from a tampered file."""
    cmd_compose(_compose_ns(plan_id='val-bad-version'))
    # Tamper with the on-disk manifest to flip the version.
    path = get_manifest_path('val-bad-version')
    text = path.read_text(encoding='utf-8')
    # TOON top-level scalar replacement: serialize_toon emits
    # `manifest_version: 1` — flip the literal.
    path.write_text(text.replace('manifest_version: 1', 'manifest_version: 99'), encoding='utf-8')

    result = cmd_validate(_validate_ns(plan_id='val-bad-version'))
    assert result is not None and result['status'] == 'error'
    assert result['error'] == 'invalid_manifest'
    assert 'manifest_version mismatch' in result['message']


def test_validate_detects_plan_id_mismatch(plan_context):
    """validate flags a plan_id mismatch from a tampered file."""
    cmd_compose(_compose_ns(plan_id='val-bad-pid'))
    path = get_manifest_path('val-bad-pid')
    text = path.read_text(encoding='utf-8')
    path.write_text(text.replace('plan_id: val-bad-pid', 'plan_id: other-plan'), encoding='utf-8')

    result = cmd_validate(_validate_ns(plan_id='val-bad-pid'))
    assert result is not None and result['status'] == 'error'
    assert result['error'] == 'invalid_manifest'
    assert 'plan_id mismatch' in result['message']


# =============================================================================
# Keyed-map marshal.json -> DICT manifest step_params snapshot bridge
# =============================================================================
#
# marshal.json persists `verification_steps` / `steps` in the canonical keyed-map
# form (`{}` for config-less steps). The composer reads that keyed map through
# `_read_marshal_phase_step_map` and snapshots the per-step params into the
# manifest as an id-keyed DICT (`body[phase].step_params`) — the plan-local
# override surface that `step-params get/set` resolve against. These tests lock
# that bridge: a keyed-map marshal.json composes to a DICT manifest snapshot, the
# params survive, validate succeeds against it, and `step-params get` resolves the
# DICT snapshot.


def _seed_keyed_map_marshal(fixture_dir: Path) -> None:
    """Write a marshal.json whose phase-6-finalize steps are the canonical keyed map.

    Config-less steps map to {}; param-bearing steps carry their nested param
    object — the on-disk serial form every config write verb persists.
    """
    marshal_path = fixture_dir / 'marshal.json'
    data = {
        'plan': {
            'phase-6-finalize': {
                'steps': {
                    'default:push': {},
                    'default:create-pr': {},
                    'plan-marshall:automatic-review': {'review_bot_buffer_seconds': 240},
                    'default:sonar-roundtrip': {},
                    'default:lessons-capture': {},
                    'default:branch-cleanup': {
                        'pr_merge_strategy': 'squash',
                        'final_merge_without_asking': False,
                    },
                    'default:record-metrics': {},
                    'default:archive-plan': {},
                }
            }
        }
    }
    marshal_path.write_text(json.dumps(data), encoding='utf-8')


def test_compose_from_keyed_map_marshal_snapshots_dict_step_params(plan_context):
    """A keyed-map marshal.json composes to a DICT (id-keyed) manifest step_params snapshot.

    The composer reads the keyed-map steps and writes the per-step params into the
    manifest as an id-keyed DICT. This locks the "manifest snapshot stays a DICT"
    contract.
    """
    _seed_keyed_map_marshal(plan_context.fixture_dir)
    cmd_compose(_compose_ns(plan_id='val-keyed-snapshot'))

    manifest = read_manifest('val-keyed-snapshot')
    assert manifest is not None
    snapshot = manifest['phase_6']['step_params']
    # The manifest snapshot is an id-keyed DICT.
    assert isinstance(snapshot, dict)
    # The param-bearing step's params survive (snapshot is keyed by the bare step
    # id — the default: prefix is stripped).
    assert snapshot['branch-cleanup'] == {
        'pr_merge_strategy': 'squash',
        'final_merge_without_asking': False,
    }
    # A config-less step reads back as the empty dict (no params).
    assert snapshot['push'] == {}


def test_validate_succeeds_against_keyed_map_sourced_manifest(plan_context):
    """validate succeeds against a manifest composed from keyed-map marshal.json.

    validate operates on the bare-name step lists and the DICT step_params
    snapshot; sourcing the manifest from the keyed-map marshal.json must not trip
    validation.
    """
    _seed_keyed_map_marshal(plan_context.fixture_dir)
    cmd_compose(_compose_ns(plan_id='val-keyed-validate'))

    result = cmd_validate(
        _validate_ns(
            plan_id='val-keyed-validate',
            phase_5_steps=None,
            phase_6_steps=None,
        )
    )
    assert result is not None and result['status'] == 'success'
    assert result['valid'] is True


def test_step_params_get_resolves_dict_snapshot_from_keyed_map_marshal(plan_context):
    """step-params get resolves against the DICT manifest snapshot sourced from keyed-map marshal.

    The snapshot is the id-keyed DICT the composer wrote from the keyed-map
    marshal.json; `step-params get` returns the full param object for a step in a
    single call, resolving the bare-keyed DICT entry.
    """
    _seed_keyed_map_marshal(plan_context.fixture_dir)
    cmd_compose(_compose_ns(plan_id='val-keyed-sp-get'))

    result = cmd_step_params_get(
        Namespace(plan_id='val-keyed-sp-get', phase='6-finalize', step_id='branch-cleanup')
    )

    assert result is not None and result['status'] == 'success'
    assert result['params'] == {
        'pr_merge_strategy': 'squash',
        'final_merge_without_asking': False,
    }


# =============================================================================
# CLI plumbing (subprocess) tests for validate
# =============================================================================


def test_cli_validate_happy_path(plan_context):
    """validate via CLI returns status=success TOON."""
    compose = run_script(
        SCRIPT_PATH,
        'compose',
        '--plan-id',
        'cli-val-ok',
        '--change-type',
        'feature',
        '--track',
        'complex',
        '--scope-estimate',
        'multi_module',
    )
    assert compose.success

    result = run_script(
        SCRIPT_PATH,
        'validate',
        '--plan-id',
        'cli-val-ok',
        '--phase-5-steps',
        ','.join(DEFAULT_PHASE_5_STEPS),
        '--phase-6-steps',
        ','.join(DEFAULT_PHASE_6_STEPS),
    )
    assert result.success
    data = result.toon()
    assert data['status'] == 'success'
    # TOON parser may coerce booleans — accept both shapes defensively.
    assert data['valid'] in (True, 'true', 1)


# =============================================================================
# Per-step owner schema field (orchestrator-owned | leaf-dispatchable)
# =============================================================================


def test_step_owner_schema_vocabulary_is_closed():
    """The owner schema vocabulary is the closed two-value tuple."""
    assert VALID_STEP_OWNERS == ('orchestrator-owned', 'leaf-dispatchable')


def test_validate_step_owner_is_a_membership_predicate_over_the_schema():
    """validate_step_owner accepts exactly the declared schema values."""
    for owner in VALID_STEP_OWNERS:
        assert validate_step_owner(owner) is True
    for bogus in ('main-owned', 'ORCHESTRATOR-OWNED', 'leaf', '', 'dispatchable'):
        assert validate_step_owner(bogus) is False


def test_owner_of_yields_a_schema_valid_owner_for_every_step():
    """owner_of always returns a value that passes the schema validator.

    Schema-integrity invariant: the classifier never emits an owner outside the
    declared vocabulary, for both registry and non-registry steps.
    """
    for step in (
        *ORCHESTRATOR_OWNED_STEPS,
        'push',
        'create-pr',
        'ci-verify',
        'verify:quality-gate',
        'project:finalize-step-plugin-doctor',
        'default:finalize-step-simplify',
    ):
        assert validate_step_owner(owner_of(step)) is True


def test_orchestrator_owned_registry_steps_all_resolve_orchestrator_owned():
    """Every registry member classifies as orchestrator-owned (schema field consistency)."""
    for step in ORCHESTRATOR_OWNED_STEPS:
        assert owner_of(step) == 'orchestrator-owned', step
