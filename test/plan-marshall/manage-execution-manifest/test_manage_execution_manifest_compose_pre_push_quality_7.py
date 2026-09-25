# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
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
    ``_mem._resolve_footprint``); the autouse fixture below restores the original
    resolver after every test so the stub never leaks.
    """

    @pytest.fixture(autouse=True)
    def _restore_footprint_resolver(self):
        import extension_base

        original = _mem._resolve_footprint
        original_plan_footprint = extension_base._resolve_plan_footprint
        yield
        _mem._resolve_footprint = original
        extension_base._resolve_plan_footprint = original_plan_footprint

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

    def test_keep_when_footprint_unresolvable(self, plan_context):
        """UNRESOLVABLE footprint → ``unknown`` verdict → step KEPT, keep reported.

        The direct Defect B regression at the compose seam. A resolvable-but-empty
        footprint (``test_omit_when_modified_files_empty`` above) is a positive
        "nothing changed" observation and legitimately drops the gate; an
        UNRESOLVABLE footprint — the normal state at phase-4-plan, before the
        worktree is materialised — is no evidence at all and must not. Collapsing
        the two is what silently dropped a quality gate nobody opted out of.
        """
        plan_id = 'pp-unresolvable'
        _write_marshal(plan_context.fixture_dir, activation_globs=['marketplace/bundles/**/*.py'])
        _stub_footprint(None)

        captured, original = self._capture_decision_log()
        try:
            result = cmd_compose(
                _compose_ns(
                    plan_id=plan_id,
                    change_type='feature',
                    scope_estimate='multi_module',
                    affected_files_count=4,
                    phase_6_steps=_candidate_phase_6_with_pre_push(),
                )
            )
        finally:
            _mem._emit_decision_log = original

        assert result is not None and result['pre_push_quality_gate_omitted'] is False
        assert result['build_verdict_decision'] == 'unknown'
        manifest = read_manifest(plan_id)
        assert manifest is not None
        assert 'pre-push-quality-gate' in manifest['phase_6']['steps']
        # The gate is kept, and the keep is REPORTED — not silent.
        assert self._omit_entries(captured) == []
        kept_entries = self._kept_unknown_entries(captured)
        assert len(kept_entries) == 1
        assert kept_entries[0][0] == plan_id
        # The line forwards the verdict's own reason, not an invented one.
        assert kept_entries[0][1][len(self._KEPT_UNKNOWN_PREFIX) :]
