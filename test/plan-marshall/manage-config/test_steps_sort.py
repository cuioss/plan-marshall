#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the manage-config ``steps-sort`` verb.

The verb physically re-sorts the on-disk ``plan.phase-6-finalize.steps`` keyed-map
into ascending frontmatter ``order`` sequence, REUSING the manifest composer's
single-source ``_sort_steps_by_frontmatter_order`` choke-point. These tests drive
``cmd_steps_sort`` directly (Tier 2) and cover: shuffled→ascending reorder with an
unresolvable key pinned, byte-identical value preservation, idempotence, the
already-sorted no-op, and the phase-5 out-of-scope guarantee.

Deterministic-order cases monkeypatch ``_manifest_validation._resolve_step_order``
(the module global the real ``_sort_steps_by_frontmatter_order`` looks up) so the
expected key order is fixed without depending on the real doc frontmatter. One
real-resolver case exercises the genuine cross-skill reuse end-to-end.
"""

import json
from argparse import Namespace

# conftest.py puts every skill's scripts dir on sys.path (mirroring the executor),
# so these underscore-prefixed sibling / cross-skill modules import bare.
import _cmd_steps_sort
import _manifest_validation
from test_helpers import create_marshal_json

cmd_steps_sort = _cmd_steps_sort.cmd_steps_sort


# Deterministic frontmatter-order table for the monkeypatched resolver. A step id
# absent from the table resolves to ``None`` — the composer helper then pins it at
# its original index (the unresolvable-order fallback the verb inherits).
_FAKE_ORDER = {
    'default:push': 10,
    'default:create-pr': 20,
    'default:ci-verify': 30,
    'default:lessons-capture': 40,
    'default:archive-plan': 50,
}


def _fake_resolve(step_id):
    """Deterministic stand-in for ``_resolve_step_order`` — table lookup, else None."""
    return _FAKE_ORDER.get(step_id)


def _finalize_config(steps: dict) -> dict:
    """Return a minimal marshal.json config carrying ``steps`` under phase-6-finalize."""
    return {
        'skill_domains': {
            'system': {'defaults': ['plan-marshall:persona-plan-marshall-agent'], 'optionals': []},
        },
        'system': {'retention': {'logs_days': 1, 'archived_plans_days': 5, 'temp_on_maintenance': True}},
        'plan': {
            'phase-5-execute': {
                'commit_and_push': True,
                'max_iterations': 5,
                'verification_steps': {
                    'default:verify:quality-gate': {},
                    'default:verify:module-tests': {},
                },
            },
            'phase-6-finalize': {
                'max_iterations': 3,
                'steps': steps,
            },
        },
    }


def _persisted_steps(fixture_dir) -> dict:
    """Read back ``plan.phase-6-finalize.steps`` from the on-disk marshal.json."""
    config = json.loads((fixture_dir / 'marshal.json').read_text())
    steps: dict = config['plan']['phase-6-finalize']['steps']
    return steps


def test_steps_sort_reorders_shuffled_to_ascending_with_unknown_key_pinned(plan_context, monkeypatch):
    """A shuffled map re-sorts to ascending frontmatter order; the unresolvable key is pinned.

    ``plan-marshall:automatic-review`` is an external ``bundle:skill`` step whose
    order resolves to ``None`` — the composer helper pins it at its original index
    (2) while the resolvable ``default:`` steps flow around it in ascending order.
    """
    monkeypatch.setattr(_manifest_validation, '_resolve_step_order', _fake_resolve)

    shuffled = {
        'default:archive-plan': {},                                        # order 50
        'default:push': {},                                                # order 10
        'plan-marshall:automatic-review': {'review_bot_buffer_seconds': 300},  # None -> pinned at index 2
        'default:create-pr': {},                                           # order 20
        'default:ci-verify': {},                                           # order 30
    }
    create_marshal_json(plan_context.fixture_dir, _finalize_config(shuffled))

    result = cmd_steps_sort(Namespace())

    assert result['status'] == 'success'
    assert result['phase'] == 'phase-6-finalize'
    assert result['reordered'] is True

    expected_order = [
        'default:push',
        'default:create-pr',
        'plan-marshall:automatic-review',  # pinned at its original index (2)
        'default:ci-verify',
        'default:archive-plan',
    ]
    assert result['before'] == list(shuffled.keys())
    assert result['after'] == expected_order
    # The pinned unresolvable key stays at index 2.
    assert result['after'][2] == 'plan-marshall:automatic-review'
    # The persisted map matches the returned order.
    assert list(_persisted_steps(plan_context.fixture_dir).keys()) == expected_order


def test_steps_sort_preserves_values_byte_identical(plan_context, monkeypatch):
    """Only key order changes — each step's nested param object survives unchanged."""
    monkeypatch.setattr(_manifest_validation, '_resolve_step_order', _fake_resolve)

    shuffled = {
        'default:ci-verify': {'nested': {'a': 1, 'b': [2, 3]}, 'flag': True},  # order 30
        'default:push': {'reviewers': ['x', 'y']},                            # order 10
        'default:create-pr': {},                                             # order 20
    }
    create_marshal_json(plan_context.fixture_dir, _finalize_config(shuffled))

    result = cmd_steps_sort(Namespace())

    assert result['reordered'] is True
    persisted = _persisted_steps(plan_context.fixture_dir)
    # Sorted key order.
    assert list(persisted.keys()) == ['default:push', 'default:create-pr', 'default:ci-verify']
    # Every per-step value is preserved byte-identically (deep-equal).
    assert persisted['default:push'] == {'reviewers': ['x', 'y']}
    assert persisted['default:create-pr'] == {}
    assert persisted['default:ci-verify'] == {'nested': {'a': 1, 'b': [2, 3]}, 'flag': True}


def test_steps_sort_is_idempotent(plan_context, monkeypatch):
    """A second run over an already-sorted map is a no-op (reordered: false, zero diff)."""
    monkeypatch.setattr(_manifest_validation, '_resolve_step_order', _fake_resolve)

    shuffled = {
        'default:archive-plan': {},  # 50
        'default:push': {},          # 10
        'default:create-pr': {},     # 20
    }
    create_marshal_json(plan_context.fixture_dir, _finalize_config(shuffled))

    first = cmd_steps_sort(Namespace())
    assert first['reordered'] is True

    # Capture the on-disk bytes after the first (mutating) run.
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    bytes_after_first = marshal_path.read_bytes()

    second = cmd_steps_sort(Namespace())
    assert second['reordered'] is False
    assert second['before'] == second['after']
    # Idempotent: the second run wrote nothing — the file is byte-stable.
    assert marshal_path.read_bytes() == bytes_after_first


def test_steps_sort_already_sorted_is_noop(plan_context, monkeypatch):
    """An already-ascending map yields reordered: false and leaves marshal.json byte-stable."""
    monkeypatch.setattr(_manifest_validation, '_resolve_step_order', _fake_resolve)

    already_sorted = {
        'default:push': {},        # 10
        'default:create-pr': {},   # 20
        'default:ci-verify': {},   # 30
    }
    create_marshal_json(plan_context.fixture_dir, _finalize_config(already_sorted))

    marshal_path = plan_context.fixture_dir / 'marshal.json'
    bytes_before = marshal_path.read_bytes()

    result = cmd_steps_sort(Namespace())

    assert result['reordered'] is False
    assert result['before'] == list(already_sorted.keys())
    assert result['after'] == list(already_sorted.keys())
    # No write on a no-op run.
    assert marshal_path.read_bytes() == bytes_before


def test_steps_sort_does_not_touch_phase_5_verification_steps(plan_context, monkeypatch):
    """steps-sort is scoped to phase-6-finalize; phase-5 verification_steps is untouched."""
    monkeypatch.setattr(_manifest_validation, '_resolve_step_order', _fake_resolve)

    shuffled = {
        'default:create-pr': {},  # 20
        'default:push': {},       # 10
    }
    create_marshal_json(plan_context.fixture_dir, _finalize_config(shuffled))
    phase5_before = json.loads((plan_context.fixture_dir / 'marshal.json').read_text())[
        'plan'
    ]['phase-5-execute']['verification_steps']

    cmd_steps_sort(Namespace())

    phase5_after = json.loads((plan_context.fixture_dir / 'marshal.json').read_text())[
        'plan'
    ]['phase-5-execute']['verification_steps']
    assert phase5_after == phase5_before


def test_steps_sort_absent_map_is_noop(plan_context):
    """A phase-6-finalize section without a persisted steps map is a clean no-op."""
    config = _finalize_config({})
    del config['plan']['phase-6-finalize']['steps']
    create_marshal_json(plan_context.fixture_dir, config)

    result = cmd_steps_sort(Namespace())

    assert result['status'] == 'success'
    assert result['reordered'] is False
    assert result['before'] == []
    assert result['after'] == []


def test_steps_sort_real_resolver_produces_ascending_order(plan_context):
    """End-to-end with the REAL composer resolver: the result is ascending frontmatter order.

    Exercises the genuine cross-skill reuse (no monkeypatch): the real
    ``_resolve_step_order`` reads the actual phase-6 step-doc frontmatter, and the
    resolvable subsequence of the sorted output is non-decreasing —
    ``_check_ascending_order`` returns ``None``. The default fixture's
    ``plan-marshall:automatic-review`` external step resolves to ``None`` and is
    pinned; the ascending check skips it.
    """
    # The default create_marshal_json config carries a realistic phase-6 step map.
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_steps_sort(Namespace())

    assert result['status'] == 'success'
    assert result['phase'] == 'phase-6-finalize'
    # The sorted output's resolvable subsequence is non-decreasing per the real
    # resolver — None means "no inversion".
    assert _manifest_validation._check_ascending_order(result['after']) is None
    # The persisted map matches the returned order.
    assert list(_persisted_steps(plan_context.fixture_dir).keys()) == result['after']


def test_steps_sort_real_resolver_places_architecture_refresh_before_push_preserving_lane(plan_context):
    """D3 real-resolver: steps-sort re-materializes the mutation-settling reorder.

    Uses the GENUINE ``_resolve_step_order`` (no monkeypatch) so the actual
    phase-6 step-doc frontmatter drives the sort: ``default:architecture-refresh``
    (order 9) and ``default:finalize-step-security-audit`` (order 9) sort into the
    pre-push settle band BEFORE ``default:push`` (order 10), while the WAIT steps
    (``ci-verify`` / ``sonar-roundtrip``, order > 10) sort after it. Each step's
    ``lane`` value is preserved byte-identically (steps-sort reorders keys only),
    and a second run is a zero-diff no-op (idempotent under the steward invariant).
    """
    # Scrambled input: push and the wait steps ahead of the settle steps.
    scrambled = {
        'default:push': {'lane': 'minimal'},  # order 10 — the single push barrier
        'default:ci-verify': {'lane': 'minimal'},  # wait (> 10)
        'default:sonar-roundtrip': {'lane': 'full'},  # wait (> 10)
        'default:architecture-refresh': {'lane': 'minimal'},  # settle (order 9) — D3 move
        'default:finalize-step-security-audit': {'lane': 'full'},  # settle (order 9)
    }
    create_marshal_json(plan_context.fixture_dir, _finalize_config(scrambled))

    result = cmd_steps_sort(Namespace())

    assert result['status'] == 'success'
    assert result['reordered'] is True
    after = result['after']
    push_idx = after.index('default:push')
    # Settle steps (order < 10) sort before the single push.
    assert after.index('default:architecture-refresh') < push_idx
    assert after.index('default:finalize-step-security-audit') < push_idx
    # WAIT steps (order > 10) sort after the push.
    for wait in ('default:ci-verify', 'default:sonar-roundtrip'):
        assert after.index(wait) > push_idx

    # Each per-step value (including the lane) is preserved byte-identically.
    persisted = _persisted_steps(plan_context.fixture_dir)
    assert persisted['default:architecture-refresh'] == {'lane': 'minimal'}
    assert persisted['default:finalize-step-security-audit'] == {'lane': 'full'}
    assert persisted['default:push'] == {'lane': 'minimal'}
    assert persisted['default:ci-verify'] == {'lane': 'minimal'}
    assert persisted['default:sonar-roundtrip'] == {'lane': 'full'}

    # Idempotent: a second run over the re-materialized map is a zero-diff no-op.
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    bytes_after_first = marshal_path.read_bytes()
    second = cmd_steps_sort(Namespace())
    assert second['reordered'] is False
    assert second['before'] == second['after']
    assert marshal_path.read_bytes() == bytes_after_first
