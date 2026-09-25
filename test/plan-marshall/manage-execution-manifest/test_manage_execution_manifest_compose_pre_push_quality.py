# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import (
    DEFAULT_PHASE_6_STEPS,
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

    def test_omit_when_activation_globs_absent(self, plan_context):
        """Config key missing → step removed and omission line emitted."""
        plan_id = 'pp-globs-absent'
        # marshal.json exists but lacks the pre_push_quality_gate key entirely.
        _write_marshal(plan_context.fixture_dir, include_pre_push_key=False)
        _stub_footprint(['marketplace/bundles/plan-marshall/skills/foo.py'])

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

        assert result is not None and result['status'] == 'success'
        assert result['pre_push_quality_gate_omitted'] is True
        manifest = read_manifest(plan_id)
        assert manifest is not None
        assert 'pre-push-quality-gate' not in manifest['phase_6']['steps']
        # All other DEFAULT_PHASE_6_STEPS preserved.
        for step in DEFAULT_PHASE_6_STEPS:
            assert step in manifest['phase_6']['steps']
        omit_entries = self._omit_entries(captured)
        assert len(omit_entries) == 1
        assert omit_entries[0][0] == plan_id

    def test_omit_when_activation_globs_empty(self, plan_context):
        """activation_globs: [] → same behavior as missing config."""
        plan_id = 'pp-globs-empty'
        _write_marshal(plan_context.fixture_dir, activation_globs=[])
        _stub_footprint(['marketplace/bundles/plan-marshall/skills/foo.py'])

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

        assert result is not None and result['pre_push_quality_gate_omitted'] is True
        manifest = read_manifest(plan_id)
        assert manifest is not None
        assert 'pre-push-quality-gate' not in manifest['phase_6']['steps']
        for step in DEFAULT_PHASE_6_STEPS:
            assert step in manifest['phase_6']['steps']
        assert len(self._omit_entries(captured)) == 1

    # =========================================================================
    # Boundary-normalization cases
    #
    # The activation-failure branches of ``_apply_pre_push_quality_gate_inactive``
    # compare candidate entries against the bare literal
    # ``'pre-push-quality-gate'``. Before boundary normalization landed, a
    # ``default:pre-push-quality-gate`` candidate would silently bypass the
    # filter — the membership check ``'pre-push-quality-gate' in candidates``
    # returned ``False`` even with the prefixed entry in the list, so the gate
    # survived the manifest with the prefix attached.
    #
    # Boundary normalization in ``cmd_compose`` strips the ``default:`` prefix
    # at intake, so the pre-filter sees bare names regardless of how the
    # caller spelled the candidate IDs. These regressions exercise all three
    # activation-failure branches with a fully prefixed input list and assert
    # the gate is dropped + the manifest output is bare.
    # =========================================================================

    def test_omit_when_activation_globs_empty_with_prefixed_input(self, plan_context):
        """Regression — activation_globs=[] drops prefixed pre-push-quality-gate."""
        plan_id = 'pp-prefixed-globs-empty'
        prefixed = [
            'default:pre-push-quality-gate',
            'default:push',
            'default:create-pr',
            'default:archive-plan',
        ]
        _write_marshal(plan_context.fixture_dir, activation_globs=[])
        _stub_footprint(['marketplace/bundles/plan-marshall/skills/foo.py'])

        captured, original = self._capture_decision_log()
        try:
            result = cmd_compose(
                _compose_ns(
                    plan_id=plan_id,
                    change_type='feature',
                    scope_estimate='multi_module',
                    affected_files_count=4,
                    phase_6_steps=','.join(prefixed),
                )
            )
        finally:
            _mem._emit_decision_log = original

        assert result is not None and result['status'] == 'success'
        assert result['pre_push_quality_gate_omitted'] is True

        manifest = read_manifest(plan_id)
        assert manifest is not None
        steps = manifest['phase_6']['steps']

        # Gate dropped despite prefixed input — boundary normalization
        # made the membership check work.
        assert 'pre-push-quality-gate' not in steps
        assert 'default:pre-push-quality-gate' not in steps

        # Output is fully bare.
        assert not any(s.startswith('default:') for s in steps), f'phase_6 leaked `default:`-prefixed entry: {steps!r}'

        # Other steps from the input survive as bare strings.
        for kept in ('push', 'create-pr', 'archive-plan'):
            assert kept in steps

        # Omission line emitted exactly once.
        assert len(self._omit_entries(captured)) == 1
