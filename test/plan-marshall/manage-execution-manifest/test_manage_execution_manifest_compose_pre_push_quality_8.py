# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import (
    Callable,
    _candidate_phase_6_with_pre_push,
    _compose_ns,
    _mem,
    _stub_footprint,
    _write_marshal,
    cmd_compose,
    pytest,
    read_manifest,
)


class TestPrePushQualityGatePreFilter:
    """Activation-driven pre-filter for ``pre-push-quality-gate``.

    Each test asserts BOTH the resulting ``phase_6.steps`` content AND the
    decision-log line presence/absence. The decision-log emitter is patched on
    ``_mem._emit_decision_log`` and entries are captured into a list per test.
    The live plan footprint is injected via ``_stub_footprint`` (which replaces
    ``_mem._resolve_footprint``); the root conftest's autouse
    ``_restore_footprint_seams`` restores both seams after every test so the
    stub never leaks.
    """

    # The emitter no longer composes a reason of its own — it forwards the
    # build-decision verdict's OWN reason text, which varies by which
    # not_necessary branch fired. Tests therefore match the stable prefix and
    # assert the forwarded tail separately (see
    # ``test_omit_line_forwards_the_verdict_reason``). A hardcoded full line here
    # would re-pin the retired invented reason.
    _OMIT_PREFIX = (
        '(plan-marshall:manage-execution-manifest:compose) [STATUS] pre_push_quality_gate_inactive — '
        'dropped pre-push-quality-gate from phase_6.steps: '
    )
    # The counterpart line: an ``unknown`` verdict KEEPS the gate, and the keep is
    # REPORTED rather than passing silently. Without it an operator sees no
    # difference between "the verdict said build" and "the verdict could not be
    # substantiated" — the ADR-009 unknown-state visibility the three-value
    # vocabulary exists to give.
    _KEPT_UNKNOWN_PREFIX = (
        '(plan-marshall:manage-execution-manifest:compose) [STATUS] pre_push_quality_gate_inactive — '
        'kept pre-push-quality-gate on an unknown build verdict: '
    )

    @staticmethod
    def _capture_decision_log() -> tuple[list[tuple[str, str]], Callable[[str, str], None]]:
        """Install a capturing replacement for ``_emit_decision_log``.

        Returns the capture list plus the original function so the caller can
        restore it in a ``finally`` block.
        """
        captured: list[tuple[str, str]] = []
        original = _mem._emit_decision_log

        def _capture(plan_id: str, message: str) -> None:
            captured.append((plan_id, message))

        _mem._emit_decision_log = _capture
        return captured, original

    @classmethod
    def _omit_entries(cls, captured: list[tuple[str, str]]) -> list[tuple[str, str]]:
        return [entry for entry in captured if entry[1].startswith(cls._OMIT_PREFIX)]

    @classmethod
    def _kept_unknown_entries(cls, captured: list[tuple[str, str]]) -> list[tuple[str, str]]:
        return [entry for entry in captured if entry[1].startswith(cls._KEPT_UNKNOWN_PREFIX)]

    def test_unresolvable_and_resolvable_empty_diverge(self, plan_context):
        """The paired opposite: identical marshal, only the footprint state differs.

        Asserting the two outcomes against each other — rather than each in
        isolation — is what fails if a future change re-collapses ``None`` into
        ``[]`` at either of the two symmetric resolver seams.
        """
        _write_marshal(plan_context.fixture_dir, activation_globs=['marketplace/bundles/**/*.py'])

        _stub_footprint(None)
        unresolvable = cmd_compose(
            _compose_ns(
                plan_id='pp-diverge-unresolvable',
                change_type='feature',
                scope_estimate='multi_module',
                affected_files_count=4,
                phase_6_steps=_candidate_phase_6_with_pre_push(),
            )
        )
        _stub_footprint([])
        resolvable_empty = cmd_compose(
            _compose_ns(
                plan_id='pp-diverge-empty',
                change_type='feature',
                scope_estimate='multi_module',
                affected_files_count=4,
                phase_6_steps=_candidate_phase_6_with_pre_push(),
            )
        )

        assert unresolvable is not None and resolvable_empty is not None
        assert unresolvable['build_verdict_decision'] == 'unknown'
        assert resolvable_empty['build_verdict_decision'] == 'not_necessary'
        kept = read_manifest('pp-diverge-unresolvable')
        dropped = read_manifest('pp-diverge-empty')
        assert kept is not None and dropped is not None
        assert 'pre-push-quality-gate' in kept['phase_6']['steps']
        assert 'pre-push-quality-gate' not in dropped['phase_6']['steps']
