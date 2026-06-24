#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the request-aspect step-dropping pre-filter.

``_apply_aspect_step_dropping`` clears the ENTIRE composed phase-5 verification
list when the request aspect (resolved by the ``manage-config aspect-classify``
verb and forwarded via ``--aspect``) is ``analysis`` or ``planning``. The
rationale is the inverse of the footprint pre-filter: an analysis / planning
request carries no production / test footprint to gate, so running (and failing)
build / quality-gate / test commands against a code-free change is pure waste.

The full-clear (rather than a role-only drop of the build/verify canonicals) is
load-bearing for the phase-5-execute Step 11b contract: Step 11b fires a
``quality-gate`` sweep whenever ``phase_5.verification_steps`` is non-empty. A
role-only filter that left any external (``project:`` / ``bundle:skill``)
``None``-role step in the list would keep it non-empty and re-trigger
``quality-gate`` via Step 11b for an analysis / planning request — exactly the
build the aspect drop exists to prevent. Clearing the full list keeps the
enforcement at the manifest layer where it belongs.

An ``implementation`` aspect (the classifier's safe sub-threshold fallback) and
an absent aspect are no-ops: every step is retained.

These tests drive ``_apply_aspect_step_dropping`` directly via importlib (Tier 2),
mirroring ``test_canonical_verify_inactive.py``. No live worktree, git history,
or footprint resolution is involved — the function is a pure transform over the
step list and the aspect value.
"""

import importlib.util
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


_mem = _load_module('_mem_aspect_step_dropping', 'manage-execution-manifest.py')
_apply_aspect_step_dropping = _mem._apply_aspect_step_dropping
_BUILD_DROPPING_ASPECTS = _mem._BUILD_DROPPING_ASPECTS


# The full build/verify step set an implementation request retains and an
# analysis/planning request drops — one canonical per build-dropping role.
_BUILD_STEPS = [
    'default:verify:quality-gate',
    'default:verify:module-tests',
    'default:verify:coverage',
]


class TestConstants:
    """The membership tables encode the documented contract."""

    def test_build_dropping_aspects_are_analysis_and_planning(self):
        assert _BUILD_DROPPING_ASPECTS == frozenset({'analysis', 'planning'})

    def test_implementation_is_not_a_build_dropping_aspect(self):
        assert 'implementation' not in _BUILD_DROPPING_ASPECTS


class TestAnalysisPlanningClearsEntireList:
    """An analysis / planning aspect clears the ENTIRE phase-5 verification list."""

    def test_analysis_drops_all_build_steps(self):
        kept, dropped = _apply_aspect_step_dropping(list(_BUILD_STEPS), 'analysis', {})
        assert kept == []
        assert dropped == _BUILD_STEPS

    def test_planning_drops_all_build_steps(self):
        kept, dropped = _apply_aspect_step_dropping(list(_BUILD_STEPS), 'planning', {})
        assert kept == []
        assert dropped == _BUILD_STEPS

    def test_bare_canonical_verify_form_is_also_dropped(self):
        """The bare ``verify:{canonical}`` form is dropped identically to the prefixed form."""
        steps = ['verify:quality-gate', 'verify:module-tests']
        kept, dropped = _apply_aspect_step_dropping(steps, 'analysis', {})
        assert kept == []
        assert dropped == steps

    def test_verify_canonical_is_dropped(self):
        """``default:verify:verify`` (the ``module-tests`` role) is dropped."""
        kept, dropped = _apply_aspect_step_dropping(['default:verify:verify'], 'planning', {})
        assert kept == []
        assert dropped == ['default:verify:verify']

    def test_external_none_role_step_does_not_survive_role_drop(self):
        """REGRESSION (CodeRabbit 10709d): an external (project:/bundle:skill) step
        whose derived role is ``None`` must ALSO drop under analysis/planning. A
        role-only filter would leave it in place, keeping the list non-empty and
        re-triggering quality-gate via phase-5 Step 11b. The full-clear path
        ensures the list ends empty even when the only surviving candidate is an
        external None-role step."""
        # The list contains ONLY external/unknown None-role steps — no build/verify
        # canonical to drop via the old role filter. The list must still end empty.
        steps = [
            'project:finalize-step-plugin-doctor',
            'my-bundle:my-verify-step',
            'default:verify:not-a-canonical',
        ]
        kept, dropped = _apply_aspect_step_dropping(steps, 'analysis', {})
        assert kept == []
        assert dropped == steps

    def test_mixed_build_and_external_steps_all_drop_under_analysis(self):
        """A mix of build/verify canonicals, footprint-gated whole-tree canonicals,
        and external None-role steps ALL drop under an analysis aspect — the list
        ends empty regardless of step kind."""
        steps = [
            'default:verify:quality-gate',
            'project:finalize-step-plugin-doctor',
            'my-bundle:my-verify-step',
            'default:verify:not-a-canonical',
            'default:verify:integration-tests',
            'default:verify:e2e',
        ]
        kept, dropped = _apply_aspect_step_dropping(steps, 'analysis', {})
        assert kept == []
        assert dropped == steps

    def test_mixed_steps_all_drop_under_planning(self):
        """Symmetric coverage for the ``planning`` aspect over a mixed list."""
        steps = [
            'default:verify:module-tests',
            'project:finalize-step-plugin-doctor',
            'default:verify:coverage',
        ]
        kept, dropped = _apply_aspect_step_dropping(steps, 'planning', {})
        assert kept == []
        assert dropped == steps


class TestImplementationRetainsAllSteps:
    """An implementation aspect (or absent aspect) retains every step."""

    def test_implementation_retains_all_build_steps(self):
        kept, dropped = _apply_aspect_step_dropping(list(_BUILD_STEPS), 'implementation', {})
        assert kept == _BUILD_STEPS
        assert dropped == []

    def test_implementation_retains_external_none_role_steps(self):
        """An implementation aspect retains external None-role steps untouched —
        the full-clear path is gated strictly on the build-dropping aspects."""
        steps = [
            'default:verify:quality-gate',
            'project:finalize-step-plugin-doctor',
            'my-bundle:my-verify-step',
        ]
        kept, dropped = _apply_aspect_step_dropping(steps, 'implementation', {})
        assert kept == steps
        assert dropped == []

    def test_none_aspect_is_a_noop(self):
        """An absent aspect (``--aspect`` omitted) retains every step."""
        kept, dropped = _apply_aspect_step_dropping(list(_BUILD_STEPS), None, {})
        assert kept == _BUILD_STEPS
        assert dropped == []

    def test_unrecognized_aspect_is_a_noop(self):
        """An aspect value outside the build-dropping set retains every step."""
        kept, dropped = _apply_aspect_step_dropping(list(_BUILD_STEPS), 'unknown-aspect', {})
        assert kept == _BUILD_STEPS
        assert dropped == []

    def test_empty_step_list_is_a_noop_for_every_aspect(self):
        for aspect in ('analysis', 'planning', 'implementation', None):
            kept, dropped = _apply_aspect_step_dropping([], aspect, {})
            assert kept == []
            assert dropped == []
