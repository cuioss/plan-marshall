# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import (
    _compose_ns,
    _mem,
    cmd_compose,
    read_manifest,
)

# =============================================================================
# build_verdict_contradiction — the post-matrix assertion's wiring into compose
#
# The assertion itself is unit-tested in
# ``test_build_verdict_contradiction_guard.py``; these cases pin that the
# composer actually CONSULTS it on the final step lists and converts a finding
# into a fail-loud compose that writes no manifest — the same shape the
# ``unresolvable_step`` / ``non_canonical_step`` siblings use.
# =============================================================================


class TestBuildVerdictContradictionWiring:
    """``cmd_compose`` rejects a manifest that contradicts the build verdict."""

    @staticmethod
    def _stub_verdict_inputs(footprint: list[str], verdict: dict | None) -> tuple:
        """Pin both assertion inputs; returns the originals for restoration."""
        original_footprint = _mem._resolve_footprint
        original_verdict = _mem._command_free_build_verdict
        _mem._resolve_footprint = lambda plan_id: list(footprint)
        _mem._command_free_build_verdict = lambda plan_id: verdict
        return original_footprint, original_verdict

    @staticmethod
    def _restore(originals: tuple) -> None:
        _mem._resolve_footprint, _mem._command_free_build_verdict = originals

    def test_compose_fails_loud_on_a_contradiction(self, plan_context):
        """A not_necessary verdict over a real footprint + a composed build step → error."""
        plan_id = 'verdict-contradiction'
        originals = self._stub_verdict_inputs(
            ['marketplace/bundles/plan-marshall/skills/foo/scripts/foo.py'],
            {'decision': 'not_necessary', 'reason': 'plan footprint touches no build_map glob'},
        )
        try:
            result = cmd_compose(
                _compose_ns(
                    plan_id=plan_id,
                    change_type='feature',
                    scope_estimate='multi_module',
                    affected_files_count=3,
                    phase_5_steps='verify:quality-gate,verify:module-tests',
                )
            )
        finally:
            self._restore(originals)

        assert result is not None
        assert result['status'] == 'error'
        assert result['error'] == 'build_verdict_contradiction'
        assert result['phase'] == 'phase_5'
        assert result['step_id'] == 'verify:module-tests'
        # The verdict's own reason is forwarded, not an invented one.
        assert result['reason'] == 'plan footprint touches no build_map glob'

    def test_failed_assertion_writes_no_manifest(self, plan_context):
        """Like its sibling gates, the assertion returns BEFORE write_manifest.

        A partial manifest persisted by a rejected compose would be read as
        authoritative by phase-5, so the fail-loud path must leave no artifact.
        """
        plan_id = 'verdict-contradiction-no-write'
        originals = self._stub_verdict_inputs(
            ['scripts/foo.py'],
            {'decision': 'not_necessary', 'reason': 'plan footprint touches no build_map glob'},
        )
        try:
            result = cmd_compose(
                _compose_ns(
                    plan_id=plan_id,
                    change_type='feature',
                    scope_estimate='multi_module',
                    affected_files_count=3,
                    phase_5_steps='verify:quality-gate,verify:module-tests',
                )
            )
        finally:
            self._restore(originals)

        assert result is not None and result['status'] == 'error'
        assert read_manifest(plan_id) is None

    def test_compose_succeeds_when_the_verdict_agrees(self, plan_context):
        """A ``build`` verdict over the same inputs composes normally."""
        plan_id = 'verdict-consistent'
        originals = self._stub_verdict_inputs(['scripts/foo.py'], {'decision': 'build'})
        try:
            result = cmd_compose(
                _compose_ns(
                    plan_id=plan_id,
                    change_type='feature',
                    scope_estimate='multi_module',
                    affected_files_count=3,
                    phase_5_steps='verify:quality-gate,verify:module-tests',
                )
            )
        finally:
            self._restore(originals)

        assert result is not None and result['status'] == 'success'
        assert read_manifest(plan_id) is not None

    def test_early_compose_with_an_empty_footprint_composes_normally(self, plan_context):
        """Anti-vacuity at the WIRING level: the ordinary first compose must succeed.

        This is the case that would break every plan if the composer consulted
        the assertion without its non-empty-footprint precondition: at
        phase-4-plan time the footprint is empty, the verdict is therefore
        ``not_necessary``, and the composed list is the full build/verify set.
        """
        plan_id = 'verdict-early-compose'
        originals = self._stub_verdict_inputs(
            [],  # early compose — worktree not yet materialized
            {'decision': 'not_necessary', 'reason': 'plan footprint is empty — no changed files to build'},
        )
        try:
            result = cmd_compose(
                _compose_ns(
                    plan_id=plan_id,
                    change_type='feature',
                    scope_estimate='multi_module',
                    affected_files_count=3,
                    phase_5_steps='verify:quality-gate,verify:module-tests,verify:coverage',
                )
            )
        finally:
            self._restore(originals)

        assert result is not None and result['status'] == 'success'
        manifest = read_manifest(plan_id)
        assert manifest is not None
        assert 'verify:module-tests' in manifest['phase_5']['verification_steps']

    def test_unobtainable_verdict_composes_normally(self, plan_context):
        """A ``None`` verdict cannot prove a contradiction, so compose proceeds."""
        plan_id = 'verdict-unobtainable'
        originals = self._stub_verdict_inputs(['scripts/foo.py'], None)
        try:
            result = cmd_compose(
                _compose_ns(
                    plan_id=plan_id,
                    change_type='feature',
                    scope_estimate='multi_module',
                    affected_files_count=3,
                    phase_5_steps='verify:quality-gate,verify:module-tests',
                )
            )
        finally:
            self._restore(originals)

        assert result is not None and result['status'] == 'success'
