# SPDX-License-Identifier: FSL-1.1-ALv2
"""Behavior-cluster tests carved from test_manage_execution_manifest_validate.py: validate."""

#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_validate_fixtures import (
    VALID_STEP_OWNERS,
    Namespace,
    _compose_ns,
    _mem,
    _seed_keyed_map_marshal,
    _validate_ns,
    cmd_compose,
    cmd_validate,
    get_manifest_path,
    validate_step_owner,
)

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



def test_validate_step_owner_is_a_membership_predicate_over_the_schema():
    """validate_step_owner accepts exactly the declared schema values."""
    for owner in VALID_STEP_OWNERS:
        assert validate_step_owner(owner) is True
    for bogus in ('main-owned', 'ORCHESTRATOR-OWNED', 'leaf', '', 'dispatchable'):
        assert validate_step_owner(bogus) is False
