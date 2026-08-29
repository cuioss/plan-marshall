#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Unit tests for the explicit findings-store handle and its state discriminator.

Subject: ``_findings_store_state.resolve_findings_store`` and the per-surface
store-state payload fields it feeds into ``_findings_core``.

The load-bearing property under test is a DISTINCTION, not a value: "this plan
filed nothing" (`missing`, a genuine `status: success` / `total_count: 0`) and
"this plan's directory is not under the root I resolved" (`plan_absent`, a
refusal) used to produce byte-identical payloads. Every test below is therefore
paired — a positive control for the refusal and a matched negative control for
the benign case it must NOT swallow.

The surface roster is DERIVED from the module rather than hand-listed, so a
surface added later cannot silently escape the store-state contract: it lands in
neither declared bucket and fails the partition assertion instead.
"""

import inspect

import pytest

from conftest import load_script_module

_findings_core = load_script_module(
    'plan-marshall', 'manage-findings', '_findings_core.py', '_findings_core'
)
_store_state = load_script_module(
    'plan-marshall', 'manage-findings', '_findings_store_state.py', '_findings_store_state'
)

resolve_findings_store = _store_state.resolve_findings_store
store_state_fields = _store_state.store_state_fields
STORE_RESOLUTIONS = _store_state.STORE_RESOLUTIONS
FINDINGS_STORE_STATES = _store_state.FINDINGS_STORE_STATES
UNREACHED_STORE_STATES = _store_state.UNREACHED_STORE_STATES
FINDINGS_STORE_UNRESOLVED = _store_state.FINDINGS_STORE_UNRESOLVED

QGATE_PERSIST_OK = _findings_core.QGATE_PERSIST_OK

#: The four store-state fields every operation surface must publish.
_STORE_STATE_KEYS = frozenset(
    {'store_resolution', 'store_path', 'findings_store_state', 'unresolved_store'}
)

#: A hash that exists in no store, used to drive the not-found branch of the
#: hash-keyed surfaces. Six hex chars, matching ``HASH_ID_LENGTH``.
_ABSENT_HASH = 'deadbe'


# =============================================================================
# Population derivation — the roster every contract assertion below runs over
# =============================================================================


def _is_path_helper(name: str) -> bool:
    """Return whether ``name`` is one of the module's pure path composers.

    Decided STRUCTURALLY on the name's suffix (``_path`` / ``_dir``) rather than
    by a hand-written exclusion list, so a path helper added later is excluded
    for the same reason the existing ones are. It does not catch the record
    readers ``get_finding`` / ``get_assessment``, which carry neither suffix and
    are genuine operation surfaces.
    """
    return name.endswith(('_path', '_dir'))


def _operation_roster() -> dict[str, object]:
    """Derive every public operation callable defined in ``_findings_core``.

    The population is the module itself: every module-level function DEFINED
    there (``__module__`` guard drops the imported collaborators), minus the
    private helpers (``_`` prefix) and the pure path composers. Nothing is
    enumerated by hand, so a surface added to the module later appears here
    automatically — and then fails the partition assertion below unless it is
    also placed in a bucket.
    """
    return {
        name: fn
        for name, fn in inspect.getmembers(_findings_core, inspect.isfunction)
        if fn.__module__ == _findings_core.__name__
        and not name.startswith('_')
        and not _is_path_helper(name)
    }


def _shape_c_names(roster: dict[str, object]) -> set[str]:
    """The store-CREATING surfaces, derived from the roster by the ``add_`` prefix."""
    return {name for name in roster if name.startswith('add_')}


def _shape_a_names(roster: dict[str, object]) -> set[str]:
    """The read/resolve surfaces: the roster's complement of Shape C."""
    return set(roster) - _shape_c_names(roster)


#: How to drive each Shape-A surface with valid arguments. The KEYS are asserted
#: against the derived roster (see
#: ``test_the_invocation_table_covers_exactly_the_shape_a_roster``), so this
#: table cannot silently fall behind the module — it is a driver, never the
#: population.
_SHAPE_A_INVOCATIONS = {
    'query_findings': lambda core, pid: core.query_findings(pid),
    'query_findings_unified': lambda core, pid: core.query_findings_unified(pid),
    'get_finding': lambda core, pid: core.get_finding(pid, _ABSENT_HASH),
    'resolve_finding': lambda core, pid: core.resolve_finding(pid, _ABSENT_HASH, 'fixed'),
    'resolve_findings_by_type': lambda core, pid: core.resolve_findings_by_type(pid, ('bug',), 'fixed'),
    'promote_finding': lambda core, pid: core.promote_finding(pid, _ABSENT_HASH, 'architecture'),
    'mark_finding_responded': lambda core, pid: core.mark_finding_responded(pid, _ABSENT_HASH),
    'query_qgate_findings': lambda core, pid: core.query_qgate_findings(pid, '5-execute'),
    'resolve_qgate_finding': lambda core, pid: core.resolve_qgate_finding(
        pid, '5-execute', _ABSENT_HASH, 'fixed'
    ),
    'resolve_qgate_findings_by_evidence': lambda core, pid: core.resolve_qgate_findings_by_evidence(
        pid, '5-execute', []
    ),
    'clear_qgate_findings': lambda core, pid: core.clear_qgate_findings(pid, '5-execute'),
    'query_assessments': lambda core, pid: core.query_assessments(pid),
    'get_assessment': lambda core, pid: core.get_assessment(pid, _ABSENT_HASH),
    'clear_assessments': lambda core, pid: core.clear_assessments(pid),
}

#: How to drive each Shape-C surface. ``add_qgate_finding_checked`` returns a
#: ``(hash_id, failure)`` tuple rather than a payload dict, which is why the
#: Shape-C assertions read the tuple form for that one member.
_SHAPE_C_INVOCATIONS = {
    'add_finding': lambda core, pid: core.add_finding(pid, 'bug', 'Title', 'Detail'),
    'add_qgate_finding': lambda core, pid: core.add_qgate_finding(
        pid, '5-execute', 'qgate', 'bug', 'Title', 'Detail'
    ),
    'add_qgate_finding_checked': lambda core, pid: core.add_qgate_finding_checked(
        pid, '5-execute', 'qgate', 'bug', 'Checked title', 'Detail'
    ),
    'add_assessment': lambda core, pid: core.add_assessment(pid, 'src/a.py', 'UNCERTAIN', 50),
}


# =============================================================================
# Test: the roster partitions exhaustively
# =============================================================================


def test_the_roster_is_non_empty():
    """A partition assertion over an empty population proves nothing."""
    assert len(_operation_roster()) > 0, 'the derivation found no operation surfaces at all'


def test_the_roster_partitions_exhaustively_and_disjointly_into_14_plus_4():
    """Shape A (14) and Shape C (4) cover the derived roster with no overlap.

    The two counts are asserted alongside the exhaustiveness so a function added
    to the module later fails HERE — landing in neither bucket, or moving the
    total — rather than silently escaping the store-state contract.
    """
    roster = _operation_roster()
    shape_a = _shape_a_names(roster)
    shape_c = _shape_c_names(roster)

    assert shape_a & shape_c == set(), f'buckets overlap: {sorted(shape_a & shape_c)}'
    assert shape_a | shape_c == set(roster), (
        f'buckets do not cover the roster; unbucketed: {sorted(set(roster) - shape_a - shape_c)}'
    )
    assert len(shape_a) == 14, f'expected 14 Shape-A surfaces, got {sorted(shape_a)}'
    assert len(shape_c) == 4, f'expected 4 Shape-C surfaces, got {sorted(shape_c)}'
    assert len(roster) == 18


def test_the_invocation_table_covers_exactly_the_shape_a_roster():
    """The driver table is pinned to the derived population, not vice versa."""
    assert set(_SHAPE_A_INVOCATIONS) == _shape_a_names(_operation_roster())


def test_the_invocation_table_covers_exactly_the_shape_c_roster():
    """Same pinning for the store-creating surfaces."""
    assert set(_SHAPE_C_INVOCATIONS) == _shape_c_names(_operation_roster())


# =============================================================================
# Test: the four store states
# =============================================================================


def test_present_when_the_plan_directory_and_findings_directory_both_exist(plan_context):
    plan_id = 'store-state-present'
    plan_context.plan_dir_for(plan_id)
    _findings_core.add_finding(plan_id, 'bug', 'Seed', 'Detail')

    store = resolve_findings_store(plan_id)

    assert store.state == 'present'
    assert store.resolution == 'override'
    assert store.path is not None
    assert store.path.is_dir()


def test_missing_when_the_plan_directory_exists_but_filed_nothing(plan_context):
    """The BENIGN zero — the control the refusal must never swallow."""
    plan_id = 'store-state-missing'
    plan_context.plan_dir_for(plan_id)

    store = resolve_findings_store(plan_id)

    assert store.state == 'missing'
    assert store.path is not None
    assert not store.path.exists()


def test_plan_absent_when_the_plan_directory_is_not_under_the_resolved_root(plan_context):
    plan_id = 'store-state-absent'
    assert not (plan_context.plans_dir / plan_id).exists(), 'fixture must not seed this plan'

    store = resolve_findings_store(plan_id)

    assert store.state == 'plan_absent'
    assert str(plan_context.fixture_dir) in store.detail, (
        'the refusal must name the resolved root it looked under'
    )


def test_unknown_returns_rather_than_raises_when_the_root_cannot_be_resolved(monkeypatch):
    """An unresolvable root is RETURNED as a state, never raised.

    A raise is what a caller swallows into a zero; a returned state is what a
    caller has to report. The branch is driven by making the real resolver fail
    the way it fails in production (``RuntimeError``), not by fabricating a
    handle.
    """

    def _unresolvable():
        raise RuntimeError('no .plan/local ancestor of the current working directory')

    monkeypatch.setattr(_store_state, 'get_base_dir', _unresolvable)

    store = resolve_findings_store('store-state-unknown')

    assert store.state == 'unknown'
    assert store.resolution == 'unresolved'
    assert store.path is None
    assert 'store-state-unknown' in store.detail


def test_the_four_states_are_separately_representable(plan_context, monkeypatch):
    """All four states are reachable and pairwise distinct.

    Asserting each one in isolation leaves open that two of them collapse onto
    the same value; this collects the four observed states and asserts the set
    has four members, which is the property the whole plan turns on.
    """
    plan_context.plan_dir_for('four-present')
    _findings_core.add_finding('four-present', 'bug', 'Seed', 'Detail')
    plan_context.plan_dir_for('four-missing')

    observed = {
        resolve_findings_store('four-present').state,
        resolve_findings_store('four-missing').state,
        resolve_findings_store('four-absent').state,
    }

    def _unresolvable():
        raise RuntimeError('unresolvable')

    monkeypatch.setattr(_store_state, 'get_base_dir', _unresolvable)
    observed.add(resolve_findings_store('four-unknown').state)

    assert observed == set(FINDINGS_STORE_STATES)
    assert len(observed) == 4


def test_declared_vocabularies_match_the_states_the_resolver_can_produce():
    """The published sets are the ones the module actually reasons over."""
    assert UNREACHED_STORE_STATES < FINDINGS_STORE_STATES
    assert UNREACHED_STORE_STATES == {'plan_absent', 'unknown'}
    assert 'unresolved' in STORE_RESOLUTIONS


# =============================================================================
# Test: store_state_fields
# =============================================================================


def test_store_state_fields_publishes_exactly_the_four_keys(plan_context):
    plan_context.plan_dir_for('fields-shape')
    fields = store_state_fields(resolve_findings_store('fields-shape'))
    assert set(fields) == _STORE_STATE_KEYS


@pytest.mark.parametrize('state_seed', ['present', 'missing', 'plan_absent'])
def test_unresolved_store_is_derived_from_the_state(plan_context, state_seed):
    """``unresolved_store`` agrees with the state on every reachable state.

    Derivation is the point: a separately-tracked boolean could disagree with
    the discriminator it summarises, and a caller reading only the boolean would
    then act on a store the state says was never reached.
    """
    plan_id = f'fields-derived-{state_seed.replace("_", "-")}'
    if state_seed != 'plan_absent':
        plan_context.plan_dir_for(plan_id)
    if state_seed == 'present':
        _findings_core.add_finding(plan_id, 'bug', 'Seed', 'Detail')

    store = resolve_findings_store(plan_id)
    fields = store_state_fields(store)

    assert fields['findings_store_state'] == state_seed
    assert fields['unresolved_store'] is (state_seed in UNREACHED_STORE_STATES)


def test_store_path_is_none_exactly_when_unresolved(monkeypatch):
    def _unresolvable():
        raise RuntimeError('unresolvable')

    monkeypatch.setattr(_store_state, 'get_base_dir', _unresolvable)
    fields = store_state_fields(resolve_findings_store('fields-unresolved'))

    assert fields['store_path'] is None
    assert fields['store_resolution'] == 'unresolved'


# =============================================================================
# Test: every Shape-A surface publishes the store-state fields
# =============================================================================


@pytest.mark.parametrize('surface', sorted(_SHAPE_A_INVOCATIONS))
def test_every_shape_a_surface_publishes_the_store_state_fields(plan_context, surface):
    """Run over the DERIVED roster, one parametrisation per surface."""
    plan_id = 'shape-a-fields'
    plan_context.plan_dir_for(plan_id)
    _findings_core.add_finding(plan_id, 'bug', 'Seed', 'Detail')

    result = _SHAPE_A_INVOCATIONS[surface](_findings_core, plan_id)

    assert isinstance(result, dict), f'{surface} returned {type(result)!r}'
    assert _STORE_STATE_KEYS <= set(result), (
        f'{surface} omits {sorted(_STORE_STATE_KEYS - set(result))}'
    )
    assert result['findings_store_state'] == 'present'
    assert result['unresolved_store'] is False


@pytest.mark.parametrize('surface', sorted(_SHAPE_A_INVOCATIONS))
def test_every_shape_a_surface_refuses_an_absent_plan_directory(plan_context, surface):
    """The refusal is uniform across the whole derived Shape-A population."""
    plan_id = 'shape-a-absent'
    assert not (plan_context.plans_dir / plan_id).exists()

    result = _SHAPE_A_INVOCATIONS[surface](_findings_core, plan_id)

    assert result['status'] == 'error', f'{surface} did not refuse'
    assert result['error'] == FINDINGS_STORE_UNRESOLVED
    assert result['findings_store_state'] == 'plan_absent'
    assert result['unresolved_store'] is True


@pytest.mark.parametrize('surface', sorted(_SHAPE_A_INVOCATIONS))
def test_every_shape_a_surface_keeps_the_benign_zero(plan_context, surface):
    """Matched negative control: a resolved-but-empty store still succeeds.

    Without this direction the refusal above is equally consistent with a fix
    that turned EVERY zero into an error — the documented inverse defect.
    """
    plan_id = 'shape-a-benign'
    plan_context.plan_dir_for(plan_id)

    result = _SHAPE_A_INVOCATIONS[surface](_findings_core, plan_id)

    assert result['findings_store_state'] == 'missing'
    assert result['unresolved_store'] is False
    assert result.get('error') != FINDINGS_STORE_UNRESOLVED


def test_query_findings_benign_zero_is_a_genuine_success_with_zero_counts(plan_context):
    """The load-bearing control, stated on the verb the defect was found on."""
    plan_id = 'benign-zero-list'
    plan_context.plan_dir_for(plan_id)

    result = _findings_core.query_findings(plan_id)

    assert result['status'] == 'success'
    assert result['total_count'] == 0
    assert result['findings_store_state'] == 'missing'


# =============================================================================
# Test: the narrowed write set
# =============================================================================


def _seed_cross_store(plan_context, plan_id: str):
    """Seed one plan finding, one Q-Gate finding and one assessment.

    Returns ``(plan_hash, qgate_hash, assessment_hash)``.
    """
    plan_context.plan_dir_for(plan_id)
    plan_hash = _findings_core.add_finding(plan_id, 'bug', 'Plan finding', 'Detail')['hash_id']
    qgate_hash = _findings_core.add_qgate_finding(
        plan_id, '5-execute', 'qgate', 'bug', 'Q-Gate finding', 'Detail'
    )['hash_id']
    assessment_hash = _findings_core.add_assessment(plan_id, 'src/a.py', 'UNCERTAIN', 50)['hash_id']
    return plan_hash, qgate_hash, assessment_hash


@pytest.mark.parametrize('verb', ['resolve_finding', 'promote_finding', 'mark_finding_responded'])
@pytest.mark.parametrize('sibling', ['qgate', 'assessment'])
def test_plan_findings_write_verbs_leave_a_sibling_store_byte_identical(
    plan_context, verb, sibling
):
    """A Q-Gate / assessment hash is identified and refused, never written.

    The assertion is on the FILE BYTES, not on the returned payload: a verb that
    reported an error after already stamping the record would satisfy a
    payload-only check while leaving the cross-store write it exists to prevent.
    """
    plan_id = f'narrow-write-{verb.replace("_", "-")}-{sibling}'
    _plan_hash, qgate_hash, assessment_hash = _seed_cross_store(plan_context, plan_id)

    store = resolve_findings_store(plan_id)
    assert store.path is not None
    if sibling == 'qgate':
        target_path = store.path / 'qgate-5-execute.jsonl'
        target_hash = qgate_hash
        expected_verb_hint = 'qgate resolve --phase 5-execute'
    else:
        target_path = store.path / 'assessments.jsonl'
        target_hash = assessment_hash
        expected_verb_hint = 'assessment get'

    before = target_path.read_bytes()

    if verb == 'resolve_finding':
        result = _findings_core.resolve_finding(plan_id, target_hash, 'fixed')
    elif verb == 'promote_finding':
        result = _findings_core.promote_finding(plan_id, target_hash, 'architecture')
    else:
        result = _findings_core.mark_finding_responded(plan_id, target_hash)

    assert result['status'] == 'error'
    assert result['error'] == 'finding_in_other_store'
    assert result['use_verb'] == expected_verb_hint
    assert target_path.read_bytes() == before, f'{verb} mutated the {sibling} store'


@pytest.mark.parametrize('verb', ['resolve_finding', 'promote_finding', 'mark_finding_responded'])
def test_plan_findings_write_verbs_still_write_a_genuine_plan_finding(plan_context, verb):
    """Matched negative control: the narrowing does not reject legitimate writes."""
    plan_id = f'narrow-write-ok-{verb.replace("_", "-")}'
    plan_hash, _qgate_hash, _assessment_hash = _seed_cross_store(plan_context, plan_id)

    store = resolve_findings_store(plan_id)
    assert store.path is not None
    bug_path = store.path / 'bug.jsonl'
    before = bug_path.read_bytes()

    if verb == 'resolve_finding':
        result = _findings_core.resolve_finding(plan_id, plan_hash, 'fixed')
    elif verb == 'promote_finding':
        result = _findings_core.promote_finding(plan_id, plan_hash, 'architecture')
    else:
        result = _findings_core.mark_finding_responded(plan_id, plan_hash)

    assert result['status'] == 'success', result
    assert bug_path.read_bytes() != before, f'{verb} reported success without writing'


def test_a_hash_in_no_store_at_all_is_a_plain_not_found(plan_context):
    """The distinguishing message fires only when the hash is genuinely elsewhere."""
    plan_id = 'narrow-write-nowhere'
    _seed_cross_store(plan_context, plan_id)

    result = _findings_core.get_finding(plan_id, _ABSENT_HASH)

    assert result['status'] == 'error'
    assert result.get('error') != 'finding_in_other_store'
    assert _ABSENT_HASH in result['message']


# =============================================================================
# Test: the Shape-C add guard
# =============================================================================


@pytest.mark.parametrize('surface', sorted(_SHAPE_C_INVOCATIONS))
def test_shape_c_surfaces_refuse_an_absent_plan_directory(plan_context, surface):
    plan_id = f'shape-c-absent-{surface.replace("_", "-")}'
    assert not (plan_context.plans_dir / plan_id).exists()

    result = _SHAPE_C_INVOCATIONS[surface](_findings_core, plan_id)

    if surface == 'add_qgate_finding_checked':
        hash_id, failure = result
        assert hash_id is None
        assert failure is not None
        assert FINDINGS_STORE_UNRESOLVED not in QGATE_PERSIST_OK
    else:
        assert result['status'] == 'error', f'{surface} did not refuse'
        assert result['error'] == FINDINGS_STORE_UNRESOLVED
        assert result['findings_store_state'] == 'plan_absent'


@pytest.mark.parametrize('surface', sorted(_SHAPE_C_INVOCATIONS))
def test_shape_c_surfaces_create_nothing_on_disk_when_they_refuse(plan_context, surface):
    """The positive control asserts on the FILESYSTEM, not on the payload.

    A guard that returns an error but still lets ``ensure_parent_dir`` mkdir the
    chain would pass a payload-only assertion while leaving exactly the phantom
    store this plan exists to prevent. The probe is taken after the refused call
    against the resolved root.
    """
    plan_id = f'shape-c-probe-{surface.replace("_", "-")}'
    plan_dir = plan_context.plans_dir / plan_id
    assert not plan_dir.exists()

    _SHAPE_C_INVOCATIONS[surface](_findings_core, plan_id)

    assert not plan_dir.exists(), f'{surface} manufactured {plan_dir} while refusing'


@pytest.mark.parametrize('surface', sorted(_SHAPE_C_INVOCATIONS))
def test_shape_c_surfaces_still_create_the_findings_file_for_a_real_plan(plan_context, surface):
    """Matched negative control: a real plan's FIRST finding still lands.

    This is what proves the guard keys on the PLAN directory and not on
    ``artifacts/findings/`` — a guard keyed on the latter would refuse here, and
    would break every plan's first-ever finding.
    """
    plan_id = f'shape-c-first-{surface.replace("_", "-")}'
    plan_dir = plan_context.plan_dir_for(plan_id)
    findings_dir = plan_dir / 'artifacts' / 'findings'
    assert not findings_dir.exists(), 'the negative control must start with no findings directory'

    result = _SHAPE_C_INVOCATIONS[surface](_findings_core, plan_id)

    if surface == 'add_qgate_finding_checked':
        hash_id, failure = result
        assert failure is None, failure
        assert hash_id is not None
    else:
        assert result['status'] in QGATE_PERSIST_OK, result
    assert findings_dir.is_dir(), f'{surface} did not create the findings directory'


def test_add_qgate_finding_refusal_is_outside_the_persist_ok_partition(plan_context):
    """The refusal reaches every ``QGATE_PERSIST_OK`` caller through its own path.

    ``add_qgate_finding``'s four-valued contract is what its callers branch on,
    so the new refusal must land OUTSIDE the in-store partition rather than
    introduce a fifth value those callers do not know.
    """
    plan_id = 'qgate-refusal-partition'
    assert not (plan_context.plans_dir / plan_id).exists()

    result = _findings_core.add_qgate_finding(
        plan_id, '5-execute', 'qgate', 'bug', 'Title', 'Detail'
    )

    assert result['status'] == 'error'
    assert result['status'] not in QGATE_PERSIST_OK
