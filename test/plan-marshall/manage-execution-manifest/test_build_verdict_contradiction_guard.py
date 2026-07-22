#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the compose-time build-verdict contradiction assertion.

``check_build_verdict_consistent`` rejects a composed manifest that contradicts
the sole build/no-build authority: a step that can only pass by producing build
evidence, composed while ``build-decision`` has ruled a build ``not_necessary``
for the plan's live footprint. Such a step is a guaranteed false-red — the
evidence it needs can never exist — and its presence means some consumer decided
build necessity from a signal other than the authority (ADR-004 § "Amendment:
``build-decision`` is the sole build/no-build authority").

It is an ASSERTION, not a pre-filter: it narrows nothing and rejects instead.

**The anti-vacuity obligation.** The guard carries a non-empty-footprint
precondition, and that precondition is the whole reason the guard needs careful
tests. ``should_execute_build`` returns ``not_necessary`` for an EMPTY footprint,
and the footprint is structurally empty at early compose (``phase-4-plan`` runs
before ``phase-5-execute`` Step 2.5 materializes the worktree). Without the
precondition the guard would fire on essentially every plan's first compose —
inverted into a permanent false alarm rather than merely vacuous. The
``TestAntiVacuity`` class below therefore pins BOTH directions: the guard is
silent at early compose, AND it is not silent on the real contradiction. A guard
that only ever returns ``None`` would pass the first half alone.
"""

import importlib.util
from pathlib import Path

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


_validation = _load_module('_manifest_validation_for_verdict_guard', '_manifest_validation.py')
check_build_verdict_consistent = _validation.check_build_verdict_consistent

# A representative non-empty footprint. Its CONTENT is irrelevant to the guard —
# the guard consults the verdict, never the paths — so any non-empty list
# exercises the "a real footprint was observed" precondition.
_REAL_FOOTPRINT = ['marketplace/bundles/plan-marshall/skills/foo/scripts/foo.py']

_NOT_NECESSARY = {
    'decision': 'not_necessary',
    'reason': 'plan footprint touches no build_map glob — only non-buildable files changed',
}
_EMPTY_FOOTPRINT_VERDICT = {
    'decision': 'not_necessary',
    'reason': 'plan footprint is empty — no changed files to build',
}
_BUILD = {'decision': 'build'}


# =============================================================================
# The contradiction is rejected
# =============================================================================


class TestContradictionRejected:
    """A build-evidence step composed against a ``not_necessary`` verdict fails."""

    def test_module_tests_step_contradicts_not_necessary(self):
        result = check_build_verdict_consistent(
            ['verify:quality-gate', 'verify:module-tests'], [], _REAL_FOOTPRINT, _NOT_NECESSARY
        )

        assert result is not None
        assert result['phase'] == 'phase_5'
        assert result['step_id'] == 'verify:module-tests'

    def test_coverage_step_contradicts_not_necessary(self):
        result = check_build_verdict_consistent(
            ['verify:coverage'], [], _REAL_FOOTPRINT, _NOT_NECESSARY
        )

        assert result is not None
        assert result['step_id'] == 'verify:coverage'

    def test_bare_verify_alias_contradicts_not_necessary(self):
        """The bare ``verify`` canonical derives role ``module-tests`` — also rejected."""
        result = check_build_verdict_consistent(
            ['verify:verify'], [], _REAL_FOOTPRINT, _NOT_NECESSARY
        )

        assert result is not None
        assert result['step_id'] == 'verify:verify'

    def test_whole_tree_gates_contradict_not_necessary(self):
        """``integration`` / ``e2e`` roles build too, so they are rejected as well."""
        for step in ('verify:integration-tests', 'verify:e2e'):
            result = check_build_verdict_consistent([step], [], _REAL_FOOTPRINT, _NOT_NECESSARY)
            assert result is not None, step
            assert result['step_id'] == step

    def test_default_prefixed_step_is_still_recognized(self):
        """Role derivation canonicalizes, so a ``default:``-prefixed id is not a bypass."""
        result = check_build_verdict_consistent(
            ['default:verify:module-tests'], [], _REAL_FOOTPRINT, _NOT_NECESSARY
        )

        assert result is not None
        assert result['step_id'] == 'default:verify:module-tests'

    def test_phase_6_build_evidence_gate_contradicts_not_necessary(self):
        """``pre-push-quality-gate`` demands a kind=build entry that cannot be stamped."""
        result = check_build_verdict_consistent(
            [], ['push', 'pre-push-quality-gate'], _REAL_FOOTPRINT, _NOT_NECESSARY
        )

        assert result is not None
        assert result['phase'] == 'phase_6'
        assert result['step_id'] == 'pre-push-quality-gate'

    def test_finding_forwards_the_verdict_reason(self):
        """The finding reports the authority's reason, not one the guard invented."""
        result = check_build_verdict_consistent(
            ['verify:module-tests'], [], _REAL_FOOTPRINT, _NOT_NECESSARY
        )

        assert result is not None
        assert result['reason'] == _NOT_NECESSARY['reason']
        assert _NOT_NECESSARY['reason'] in result['message']

    def test_phase_5_is_reported_before_phase_6(self):
        """With offenders in both phases the phase-5 one is returned first."""
        result = check_build_verdict_consistent(
            ['verify:module-tests'],
            ['pre-push-quality-gate'],
            _REAL_FOOTPRINT,
            _NOT_NECESSARY,
        )

        assert result is not None
        assert result['phase'] == 'phase_5'


# =============================================================================
# Consistent manifests pass
# =============================================================================


class TestConsistentManifestsPass:
    """Every non-contradictory combination returns ``None``."""

    def test_not_necessary_with_empty_phase_5_passes(self):
        assert check_build_verdict_consistent([], [], _REAL_FOOTPRINT, _NOT_NECESSARY) is None

    def test_not_necessary_with_only_quality_gate_passes(self):
        """Structural lint runs no build and stamps no ledger entry — consistent.

        This is the discriminator that keeps the guard from over-rejecting: a
        lint-only manifest beside a ``not_necessary`` verdict is a perfectly
        coherent plan, not a contradiction.
        """
        assert (
            check_build_verdict_consistent(
                ['verify:quality-gate'], [], _REAL_FOOTPRINT, _NOT_NECESSARY
            )
            is None
        )

    def test_not_necessary_with_external_steps_passes(self):
        """External (``project:`` / ``bundle:skill``) steps have no role — never rejected."""
        assert (
            check_build_verdict_consistent(
                ['project:verify-step-lint', 'my-bundle:my-step'],
                ['lessons-capture', 'archive-plan'],
                _REAL_FOOTPRINT,
                _NOT_NECESSARY,
            )
            is None
        )

    def test_build_verdict_with_build_steps_passes(self):
        """The ordinary code-plan shape: a build IS necessary, so build steps belong."""
        assert (
            check_build_verdict_consistent(
                ['verify:quality-gate', 'verify:module-tests', 'verify:coverage'],
                ['push', 'pre-push-quality-gate'],
                _REAL_FOOTPRINT,
                _BUILD,
            )
            is None
        )

    def test_absent_verdict_passes(self):
        """An unobtainable verdict is not evidence of a contradiction."""
        assert (
            check_build_verdict_consistent(
                ['verify:module-tests'], [], _REAL_FOOTPRINT, None
            )
            is None
        )

    def test_malformed_verdict_passes(self):
        """A non-dict verdict cannot establish a contradiction either."""
        assert (
            check_build_verdict_consistent(
                ['verify:module-tests'], [], _REAL_FOOTPRINT, 'not-a-dict'
            )
            is None
        )

    def test_non_string_steps_are_skipped(self):
        """A malformed step entry is ignored rather than crashing the compose."""
        assert (
            check_build_verdict_consistent(
                [None, 42, {'step': 'x'}], [None, 7], _REAL_FOOTPRINT, _NOT_NECESSARY
            )
            is None
        )


# =============================================================================
# Anti-vacuity — the guard is silent at early compose AND fires on the real case
# =============================================================================


class TestAntiVacuity:
    """The non-empty-footprint precondition is correct in BOTH directions.

    Testing only that the guard stays quiet at early compose would be satisfied
    by a guard that never fires at all. Each case below is therefore paired with
    its opposite: identical inputs except the one variable under test.
    """

    def test_empty_footprint_at_early_compose_does_not_fire(self):
        """THE anti-vacuity case: early compose composes build steps and must pass.

        This is the exact shape of every code plan's first compose —
        ``phase-4-plan`` composes the full build/verify list before the worktree
        exists, so the footprint is empty and the verdict is ``not_necessary``
        for that reason alone. An unguarded assertion would reject this manifest,
        which is to say it would reject nearly every plan.
        """
        result = check_build_verdict_consistent(
            ['verify:quality-gate', 'verify:module-tests', 'verify:coverage'],
            ['push', 'pre-push-quality-gate'],
            [],  # early compose — the worktree has not been materialized yet
            _EMPTY_FOOTPRINT_VERDICT,
        )

        assert result is None

    def test_same_manifest_with_a_real_footprint_does_fire(self):
        """The paired opposite: only the footprint changes, and now it fires.

        Same steps, same ``not_necessary`` decision — the ONLY difference is that
        a real footprint was observed. This proves the precondition is what
        silences the previous case, rather than the guard being inert.
        """
        result = check_build_verdict_consistent(
            ['verify:quality-gate', 'verify:module-tests', 'verify:coverage'],
            ['push', 'pre-push-quality-gate'],
            _REAL_FOOTPRINT,
            _NOT_NECESSARY,
        )

        assert result is not None
        assert result['step_id'] == 'verify:module-tests'

    def test_empty_footprint_does_not_fire_even_on_a_phase_6_gate(self):
        """The precondition covers the phase-6 arm too, not just phase-5."""
        assert (
            check_build_verdict_consistent(
                [], ['pre-push-quality-gate'], [], _EMPTY_FOOTPRINT_VERDICT
            )
            is None
        )

    def test_paired_opposite_for_the_phase_6_gate(self):
        """Same phase-6 gate, real footprint — fires."""
        result = check_build_verdict_consistent(
            [], ['pre-push-quality-gate'], _REAL_FOOTPRINT, _NOT_NECESSARY
        )

        assert result is not None
        assert result['phase'] == 'phase_6'

    def test_build_verdict_is_what_distinguishes_pass_from_fail(self):
        """Third axis: hold steps and footprint fixed, vary only the decision.

        Together with the footprint pairing above this pins that BOTH inputs are
        live — neither the footprint check nor the decision check is dead code.
        """
        steps = ['verify:module-tests']

        assert check_build_verdict_consistent(steps, [], _REAL_FOOTPRINT, _BUILD) is None
        assert (
            check_build_verdict_consistent(steps, [], _REAL_FOOTPRINT, _NOT_NECESSARY)
            is not None
        )
