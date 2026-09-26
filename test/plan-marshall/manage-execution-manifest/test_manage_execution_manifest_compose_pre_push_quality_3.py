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

    def test_pre_filter_consults_the_authority_command_free(self, plan_context):
        """The pre-filter asks the plan-wide question — it nominates no command.

        "Does this plan need pre-push-quality-gate at all?" is plan-wide. The
        verdict does not vary by command, so passing one (the retired
        ``'quality-gate'`` representative) implies a command-sensitivity that does
        not exist and invites a future reader to pick a different one. This pins
        the actual argument at the authority boundary.
        """
        plan_id = 'pp-command-free'
        _write_marshal(plan_context.fixture_dir, activation_globs=['**/*.py'])
        _stub_footprint(['doc/user/configuration.adoc'])

        import extension_base

        calls: list[tuple] = []
        original_should = extension_base.should_execute_build

        def _record(canonical_command, plan_id_, *args, **kwargs):
            calls.append((canonical_command, plan_id_))
            return original_should(canonical_command, plan_id_, *args, **kwargs)

        extension_base.should_execute_build = _record
        _captured, original = self._capture_decision_log()
        try:
            result = cmd_compose(
                _compose_ns(
                    plan_id=plan_id,
                    change_type='feature',
                    scope_estimate='multi_module',
                    affected_files_count=1,
                    phase_6_steps=_candidate_phase_6_with_pre_push(),
                )
            )
        finally:
            _mem._emit_decision_log = original
            extension_base.should_execute_build = original_should

        assert result is not None and result['pre_push_quality_gate_omitted'] is True
        assert calls, 'the pre-filter never consulted the build-decision authority'
        assert all(command is None for command, _ in calls), calls

    def test_pre_filter_order_independent_of_six_row_matrix(self, plan_context):
        """Pre-filter runs before Row 1/Row 2/Row 7 — observable via decision-log ordering.

        The composer calls (in order):
          1. _apply_commit_push_disabled
          2. _apply_pre_push_quality_gate_inactive
          3. _decide() — which selects a row (Row 1: early_terminate, Row 2:
             recipe, Row 7: default, etc.)
          4. _log_commit_push_omitted (once per dropped step)
          5. _log_pre_push_quality_gate_omitted (on a not_necessary verdict) or
             _log_pre_push_quality_gate_kept_unknown (on an unknown verdict)
          6. _log_decision (always — rule line)

        Even though log emission happens after _decide, the row matrix already
        sees the filtered candidate list, which means the omission line MUST be
        captured before the rule line, and the rule line MUST reflect the
        absence of pre-push-quality-gate from phase_6.steps.

        This test temporarily replaces ``_log_decision`` (which the module-level
        setup stubs out for speed) with a capturing implementation that mirrors
        the production message contract, so the rule-fired line is observable.
        """
        plan_id = 'pp-order'
        # Activation_globs absent → pre-filter fires.
        _write_marshal(plan_context.fixture_dir, include_pre_push_key=False)
        _stub_footprint(['marketplace/bundles/plan-marshall/skills/foo.py'])

        captured: list[tuple[str, str]] = []
        original_emit = _mem._emit_decision_log
        original_log_decision = _mem._log_decision

        def _capture(plan_id_: str, message: str) -> None:
            captured.append((plan_id_, message))

        # Capturing replacement for _log_decision that mirrors the contract
        # in scripts/manage-execution-manifest.py::_log_decision().
        def _log_decision_capture(plan_id_, rule, body):
            phase_5 = body.get('phase_5', {})
            phase_6 = body.get('phase_6', {})
            p5_steps = phase_5.get('verification_steps', [])
            p6_steps = phase_6.get('steps', [])
            early = phase_5.get('early_terminate', False)
            message = (
                f'(plan-marshall:manage-execution-manifest:compose) Rule {rule} fired — '
                f'early_terminate={early}, phase_5.verification_steps={p5_steps}, '
                f'phase_6.steps={p6_steps}'
            )
            _capture(plan_id_, message)

        _mem._emit_decision_log = _capture
        _mem._log_decision = _log_decision_capture
        try:
            # Use a Row 7 (default) shape — feature + multi_module + files.
            result = cmd_compose(
                _compose_ns(
                    plan_id=plan_id,
                    change_type='feature',
                    scope_estimate='multi_module',
                    affected_files_count=10,
                    phase_6_steps=_candidate_phase_6_with_pre_push(),
                )
            )
        finally:
            _mem._emit_decision_log = original_emit
            _mem._log_decision = original_log_decision

        assert result is not None and result['rule_fired'] == 'default'
        assert result['pre_push_quality_gate_omitted'] is True

        # Ordering: omission line precedes rule-fired line.
        messages = [msg for _, msg in captured]
        omit_idx = next(
            (i for i, m in enumerate(messages) if m.startswith(self._OMIT_PREFIX)),
            None,
        )
        rule_idx = next(
            (i for i, m in enumerate(messages) if 'Rule default fired' in m),
            None,
        )
        assert omit_idx is not None, f'omission line missing in {messages!r}'
        assert rule_idx is not None, f'rule line missing in {messages!r}'
        assert omit_idx < rule_idx, (
            f'pre-filter omission line must precede rule line; got omit_idx={omit_idx}, rule_idx={rule_idx}'
        )

        # Rule line reflects filtered phase_6.steps (no pre-push-quality-gate).
        rule_msg = messages[rule_idx]
        assert 'pre-push-quality-gate' not in rule_msg

        # Manifest content also reflects the pre-filter outcome.
        manifest = read_manifest(plan_id)
        assert manifest is not None
        assert 'pre-push-quality-gate' not in manifest['phase_6']['steps']
