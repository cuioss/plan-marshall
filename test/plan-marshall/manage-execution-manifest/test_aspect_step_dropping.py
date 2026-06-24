#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the request-aspect step-dropping pre-filter.

``_apply_aspect_step_dropping`` is the role-driven, canonical-agnostic pre-filter
that drops build / quality-gate / test canonical-verify steps from the composed
phase-5 verification list when the request aspect (resolved by the
``manage-config aspect-classify`` verb and forwarded via ``--aspect``) is
``analysis`` or ``planning``. The rationale is the inverse of the footprint
pre-filter: an analysis / planning request carries no production / test footprint
to gate, so running (and failing) build / quality-gate / test commands against a
code-free change is pure waste.

The drop is driven entirely by the ``_role_of`` derivation (the same one the
footprint pre-filter uses) and the ``_BUILD_DROPPING_ROLES`` membership table
(``quality-gate`` / ``module-tests`` / ``coverage``) — there is no per-canonical
branch. An ``implementation`` aspect (the classifier's safe sub-threshold
fallback) and an absent aspect are no-ops: every build/verify gate is retained.

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
_BUILD_DROPPING_ROLES = _mem._BUILD_DROPPING_ROLES


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

    def test_build_dropping_roles_are_the_three_build_verify_roles(self):
        assert _BUILD_DROPPING_ROLES == frozenset({'quality-gate', 'module-tests', 'coverage'})


class TestAnalysisPlanningDropsBuildSteps:
    """An analysis / planning aspect drops every build / quality-gate / test step."""

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

    def test_verify_canonical_maps_to_module_tests_role_and_drops(self):
        """``default:verify:verify`` derives the ``module-tests`` role and is dropped."""
        kept, dropped = _apply_aspect_step_dropping(['default:verify:verify'], 'planning', {})
        assert kept == []
        assert dropped == ['default:verify:verify']

    def test_external_and_unknown_steps_survive_under_analysis(self):
        """External (project:/bundle:skill) and unknown-role steps are passed through
        untouched even under an analysis aspect — only build/verify roles drop."""
        steps = [
            'default:verify:quality-gate',
            'project:finalize-step-plugin-doctor',
            'my-bundle:my-verify-step',
            'default:verify:not-a-canonical',
            'default:verify:integration-tests',
            'default:verify:e2e',
        ]
        kept, dropped = _apply_aspect_step_dropping(steps, 'analysis', {})
        assert dropped == ['default:verify:quality-gate']
        assert kept == [
            'project:finalize-step-plugin-doctor',
            'my-bundle:my-verify-step',
            'default:verify:not-a-canonical',
            'default:verify:integration-tests',
            'default:verify:e2e',
        ]


class TestImplementationRetainsAllSteps:
    """An implementation aspect (or absent aspect) retains every build/verify gate."""

    def test_implementation_retains_all_build_steps(self):
        kept, dropped = _apply_aspect_step_dropping(list(_BUILD_STEPS), 'implementation', {})
        assert kept == _BUILD_STEPS
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
