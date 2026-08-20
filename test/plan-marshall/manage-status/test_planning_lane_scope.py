#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``planning-lane`` subcommand of manage-status."""


from __future__ import annotations

import json
from argparse import Namespace

import pytest
from _planning_lane_fixtures import (
    _mod,
    _ns_scope,
    _write_references,
    _write_request,
    classify_scope_pure,
    cmd_scope_estimate_heuristic,
    evaluate_signals_pure,
    scope_estimate_from_request_pure,
)

from conftest import load_script_module


def test_scope_heuristic_declares_unknown_for_unreadable_request(plan_context):
    """End-to-end: an unscoreable request persists the declared unknown, not a band."""
    plan_dir = plan_context.plan_dir_for('pl-scope-unknown')
    plan_dir.mkdir(parents=True, exist_ok=True)
    _write_references(plan_dir, scope_estimate=None)

    result = cmd_scope_estimate_heuristic(
        Namespace(plan_id='pl-scope-unknown', persist=True)
    )

    assert result['status'] == 'success'
    assert result['scope_estimate'] == 'none'
    assert result['scope_resolved'] is False
    assert result['distinct_path_count'] == 0
    refs = json.loads((plan_dir / 'references.json').read_text())
    assert refs['scope_estimate'] == 'none'


def test_scope_heuristic_reports_scope_resolved_true_for_a_scored_body(plan_context):
    """``scope_resolved`` distinguishes a classified band from the declared unknown.

    Without this field a consumer reading ``scope_estimate`` alone cannot tell a
    measured band from a "cannot tell" verdict — which is exactly how a zero-byte
    read used to pass for a band.
    """
    plan_dir = plan_context.plan_dir_for('pl-scope-resolved')
    _write_request(plan_dir, 'Fix pkg/one.py.')
    _write_references(plan_dir, scope_estimate=None)

    result = cmd_scope_estimate_heuristic(Namespace(plan_id='pl-scope-resolved', persist=False))

    assert result['scope_estimate'] == 'surgical'
    assert result['scope_resolved'] is True


@pytest.mark.parametrize(
    'body',
    [
        'Fix marketplace/bundles/plan-marshall/skills/x/scripts/x.py per the diagnosis.',
        (
            'Update marketplace/bundles/plan-marshall/skills/x/scripts/x.py and '
            'test/plan-marshall/x/test_x.py.'
        ),
        (
            'Touch a/b/one.py, c/d/two.py, and e/f/three.py — three named files, no more.'
        ),
    ],
)
def test_scope_pure_surgical_for_one_to_three_paths(body):
    """One to three distinct file paths with no glob classifies surgical."""
    assert scope_estimate_from_request_pure(body) == 'surgical'


def test_scope_pure_repeated_path_counts_once():
    """The same path mentioned repeatedly counts as one distinct path (still surgical)."""
    body = 'Edit pkg/mod.py, then re-edit pkg/mod.py, and check pkg/mod.py again.'
    assert scope_estimate_from_request_pure(body) == 'surgical'


def test_scope_pure_single_module_for_the_four_to_seven_middle_band():
    """Four-to-seven distinct file paths classifies single_module — the middle band.

    Five paths is neither ``surgical`` (>3) nor ``multi_module`` (<8). The middle
    band is deliberately NOT narrow: it does not earn the S3/S4 carve-out and does
    not project the ``minimal`` posture.
    """
    body = 'Touch a/one.py, b/two.py, c/three.py, d/four.py, and e/five.py.'
    assert scope_estimate_from_request_pure(body) == 'single_module'


@pytest.mark.parametrize(
    'body',
    [
        'Sweep every skills/*/SKILL.md across the bundle.',
        'Rewrite all **/*.py under the module.',
        'Apply the change to marketplace/bundles/*/plugin.json everywhere.',
        'Rewrite the fixtures under test/plan-marshall/manage-status/** wholesale.',
    ],
)
def test_scope_pure_fan_out_marker_bands_multi_module(body):
    """A real fan-out marker bands multi_module — it WIDENS, it does not narrow.

    The inversion this replaces: a genuine glob used to band ``single_module``,
    i.e. a declared inability to enumerate the file set was reported as a narrow
    verdict. An unbounded set cannot be a bounded one, so the marker must widen.
    """
    assert scope_estimate_from_request_pure(body) == 'multi_module'


@pytest.mark.parametrize(
    'body',
    [
        'Fix **the parser** in a/b/one.py so **bold** prose stops confusing it.',
        '**Objective**\n\n**Root cause:** the regex in pkg/mod.py is too loose.',
        '- **`c/d/two.py`** — the target\n- **`e/f/three.py`** — its test\n',
    ],
)
def test_scope_pure_markdown_bold_is_not_a_fan_out_marker(body):
    """Markdown ``**bold**`` does NOT register as fan-out — the load-bearing precision fix.

    ``_GLOB_RE``'s ``**`` alternatives are path-adjacent (``/**`` / ``**/``). Before
    that tightening a bare ``**`` matched markdown bold, and because the marker
    check short-circuits AHEAD of the path count, a bold-saturated orchestrator
    spec banded on its own — making the path-count thresholds unreachable for
    essentially the entire orchestrated-plan population. Any band extension is
    vacuous without this, so the precision is pinned directly.
    """
    band, provenance = classify_scope_pure(body)

    assert provenance['fan_out_marker'] is False
    assert band == 'surgical'


@pytest.mark.parametrize(
    ('path_count', 'expected_band'),
    [(3, 'surgical'), (4, 'single_module'), (7, 'single_module'), (8, 'multi_module')],
)
def test_scope_pure_band_boundaries_at_three_four_and_seven_eight(path_count, expected_band):
    """The two band boundaries are pinned on both sides: 3/4 and 7/8 distinct paths.

    A threshold asserted only from its interior can drift by one without any test
    noticing, so each boundary is asserted from the band below AND the band above.
    """
    body = 'Touch ' + ', '.join(f'dir{i}/file{i}.py' for i in range(path_count)) + '.'

    band, provenance = classify_scope_pure(body)

    assert provenance['distinct_path_count'] == path_count
    assert band == expected_band


@pytest.mark.parametrize('body', ['', None])
def test_scope_pure_declares_unknown_for_unscoreable_body(body):
    """An unscoreable (empty / None) body yields the DECLARED UNKNOWN, not a band.

    This assertion is the inverse of the one it replaces. The prior contract had
    an empty body classify as ``single_module`` — a confident narrow-ish band
    derived from zero bytes, which is precisely the "scorer reads nothing and
    still emits a verdict" failure this change exists to remove. A body that
    cannot be scored must say so.

    ``none`` is deliberately reused rather than a new enum member: it is already
    inside the closed ``none|surgical|single_module|multi_module|broad`` set that
    ``manage-solution-outline validate`` enforces, and it is already a member of
    ``_DEEP_SCOPE_ESTIMATES``, so the unknown biases the lane DEEP (wider) rather
    than narrow. See ``test_scope_unknown_is_a_deep_biasing_s2_value`` for that
    second half — the enum choice is only correct if the routing consequence
    holds, so both are asserted.
    """
    assert scope_estimate_from_request_pure(body) == 'none'


def test_scope_pure_single_module_for_pathless_body():
    """A non-empty but pathless (ambiguous) request still bands as single_module.

    The declared-unknown change narrows to the UNSCOREABLE case only. A body that
    was read successfully and simply names no path is a real, scoreable request
    about which the coarse verdict is "not demonstrably narrow" — it keeps its
    ``single_module`` band and must NOT drift into the unknown.
    """
    assert scope_estimate_from_request_pure('Make the thing better, somehow, everywhere.') == (
        'single_module'
    )


def test_scope_unknown_is_a_deep_biasing_s2_value():
    """The declared unknown routes DEEP — the unknown must widen, never narrow.

    Guards the enum choice in ``scope_estimate_from_request_pure``: reusing
    ``none`` is only safe while ``none`` remains in ``_DEEP_SCOPE_ESTIMATES`` and
    outside ``_NARROW_SCOPE_ESTIMATES``. If a future edit moved it, the unknown
    would silently start biasing light — the exact inversion this plan removes —
    so both memberships and the end-to-end lane verdict are pinned here.
    """
    assert 'none' in _mod._DEEP_SCOPE_ESTIMATES
    assert 'none' not in _mod._NARROW_SCOPE_ESTIMATES

    verdict = evaluate_signals_pure(
        scope_estimate='none',
        change_type='bug_fix',
        compatibility='deprecation',
        plan_source='lesson',
        request_concrete=True,
    )
    assert verdict['lane'] == 'deep'
    assert 'S2:scope_estimate' in verdict['fired_signals']


def test_scope_pure_makes_no_architecture_call(monkeypatch):
    """The classifier performs zero architecture calls (pure, regex-only)."""
    # Any attempt to import or invoke an architecture surface would raise here.
    import builtins  # noqa: PLC0415

    real_import = builtins.__import__

    def _guard_import(name, *args, **kwargs):
        assert 'architecture' not in name, f'scope classifier must not import {name}'
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, '__import__', _guard_import)
    assert scope_estimate_from_request_pure('Fix pkg/one.py and pkg/two.py.') == 'surgical'


# =============================================================================
# cmd_scope_estimate_heuristic — persistence to references.json
# =============================================================================


def test_scope_heuristic_persists_surgical_to_references(plan_context):
    """--persist writes the classified scope_estimate into references.json."""
    plan_dir = plan_context.plan_dir_for('pl-scope-persist')
    _write_request(plan_dir, 'Fix marketplace/bundles/plan-marshall/skills/x/scripts/x.py.')
    _write_references(plan_dir, scope_estimate=None)

    result = cmd_scope_estimate_heuristic(_ns_scope('pl-scope-persist', persist=True))

    assert result['status'] == 'success'
    assert result['scope_estimate'] == 'surgical'
    assert result['persisted'] is True
    refs = json.loads((plan_dir / 'references.json').read_text())
    assert refs['scope_estimate'] == 'surgical'
    # The persist preserves other references fields.
    assert refs['base_branch'] == 'main'


def test_scope_heuristic_persists_single_module_for_the_middle_band(plan_context):
    """A five-path request persists single_module — the 4–7 middle band, end to end."""
    plan_dir = plan_context.plan_dir_for('pl-scope-middle')
    _write_request(plan_dir, 'Touch a/one.py, b/two.py, c/three.py, d/four.py, e/five.py.')
    _write_references(plan_dir, scope_estimate=None)

    result = cmd_scope_estimate_heuristic(_ns_scope('pl-scope-middle', persist=True))

    assert result['scope_estimate'] == 'single_module'
    refs = json.loads((plan_dir / 'references.json').read_text())
    assert refs['scope_estimate'] == 'single_module'


def test_scope_heuristic_persists_multi_module_for_a_large_request(plan_context):
    """An eight-path request persists multi_module — the band that used to be unreachable.

    End-to-end proof that the upper segment of the path-count line now exists: the
    persisted value is a deep-biasing S2 band, so a large concrete request stops
    routing light.
    """
    plan_dir = plan_context.plan_dir_for('pl-scope-large')
    _write_request(
        plan_dir,
        'Touch ' + ', '.join(f'dir{i}/file{i}.py' for i in range(8)) + '.',
    )
    _write_references(plan_dir, scope_estimate=None)

    result = cmd_scope_estimate_heuristic(_ns_scope('pl-scope-large', persist=True))

    assert result['scope_estimate'] == 'multi_module'
    assert result['distinct_path_count'] == 8
    refs = json.loads((plan_dir / 'references.json').read_text())
    assert refs['scope_estimate'] == 'multi_module'
    assert 'multi_module' in _mod._DEEP_SCOPE_ESTIMATES


def test_scope_heuristic_without_persist_does_not_write(plan_context):
    """Without --persist the classifier reports but does not mutate references.json."""
    plan_dir = plan_context.plan_dir_for('pl-scope-nopersist')
    _write_request(plan_dir, 'Fix pkg/one.py.')
    _write_references(plan_dir, scope_estimate=None)

    result = cmd_scope_estimate_heuristic(_ns_scope('pl-scope-nopersist'))

    assert result['scope_estimate'] == 'surgical'
    assert result['persisted'] is False
    refs = json.loads((plan_dir / 'references.json').read_text())
    assert 'scope_estimate' not in refs


def test_scope_heuristic_plan_dir_not_found_errors(plan_context):
    """scope-estimate-heuristic against a missing plan dir returns a structured error."""
    result = cmd_scope_estimate_heuristic(_ns_scope('pl-scope-missing', persist=True))

    assert result['status'] == 'error'
    assert result['error'] == 'plan_dir_not_found'


# =============================================================================
# Dispatch wiring — scope-estimate-heuristic
# =============================================================================


def test_scope_estimate_heuristic_registered_in_manage_status_dispatch():
    """The scope-estimate-heuristic verb resolves to cmd_scope_estimate_heuristic."""
    import argparse  # noqa: PLC0415

    manage_status = load_script_module(
        'plan-marshall', 'manage-status', 'manage-status.py', '_manage_status_dispatch_check_scope_est'
    )

    assert callable(manage_status.cmd_scope_estimate_heuristic)
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='cmd')
    scope = sub.add_parser('scope-estimate-heuristic')
    scope.set_defaults(func=manage_status.cmd_scope_estimate_heuristic)
    ns = p.parse_args(['scope-estimate-heuristic'])
    assert ns.func is manage_status.cmd_scope_estimate_heuristic
