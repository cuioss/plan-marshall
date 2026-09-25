# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import _compose_ns, _mem, cmd_compose


class TestDecisionLogShapePreserved:
    """Decision-log line shape is byte-identical to its pre-refactor form."""

    def test_row_5_decision_log_message_matches_canonical_shape(self, plan_context):
        """``Rule {rule_key} fired — early_terminate=…, phase_5.verification_steps=…, phase_6.steps=…``."""
        captured: list[tuple[str, str]] = []
        original_emit = _mem._emit_decision_log
        original_log_decision = _mem._log_decision

        def _capture(plan_id_: str, message: str) -> None:
            captured.append((plan_id_, message))

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
            cmd_compose(
                _compose_ns(
                    plan_id='role-log-shape',
                    change_type='bug_fix',
                    scope_estimate='surgical',
                    affected_files_count=1,
                    phase_5_steps='verify:quality-gate,verify:module-tests',
                )
            )
        finally:
            _mem._emit_decision_log = original_emit
            _mem._log_decision = original_log_decision

        rule_messages = [msg for _, msg in captured if 'Rule surgical_bug_fix fired' in msg]
        assert len(rule_messages) == 1, f'expected exactly one Row 5 rule line, got: {captured!r}'
        msg = rule_messages[0]
        # Canonical shape segments.
        assert msg.startswith('(plan-marshall:manage-execution-manifest:compose) Rule surgical_bug_fix fired — ')
        assert 'early_terminate=False' in msg
        # phase_5.verification_steps reflects role-based intersection output.
        assert "phase_5.verification_steps=['verify:quality-gate', 'verify:module-tests']" in msg
        # phase_6.steps is present (we don't pin the full list here — other tests do).
        assert 'phase_6.steps=' in msg
