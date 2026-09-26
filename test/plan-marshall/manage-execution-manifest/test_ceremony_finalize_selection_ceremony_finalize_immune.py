# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_ceremony_finalize_selection_fixtures import (
    _FOOTPRINT,
    _IMMUNE_FLOOR_STEPS,
    _OPT_OUT_STEPS,
    _bare,
    _compose_ns,
    _lane_dropped_reasons,
    _manifest_phase_6_steps,
    _patch_immune_off_lanes,
    _seed_marshal_lane_overrides,
    _stub_footprint,
    _write_execution_profile,
    cmd_compose,
    pytest,
)


class TestCeremonyFinalizeImmuneOff:
    """A hand-written floor ``off`` is neutralised; an opt-out ``off`` still drops."""

    @pytest.mark.parametrize('posture', ['minimal', 'standard'])
    def test_floor_off_is_immune_kept_with_warning(self, plan_context, monkeypatch, posture):
        _patch_immune_off_lanes(monkeypatch)
        candidates = _IMMUNE_FLOOR_STEPS + _OPT_OUT_STEPS
        # Every step (floor AND opt-out) carries a hand-written lane: off.
        _seed_marshal_lane_overrides(candidates, off_steps=candidates)
        _stub_footprint(_FOOTPRINT)
        plan_id = f'immune-off-{posture}'
        _write_execution_profile(plan_context, plan_id, posture)

        result = cmd_compose(
            _compose_ns(
                plan_id=plan_id,
                change_type='feature',
                scope_estimate='multi_module',
                affected_files_count=5,
                phase_6_steps=','.join(candidates),
            )
        )

        assert result is not None and result['status'] == 'success'
        assert result['execution_profile'] == posture

        # Every mandatory floor step survives despite its hand-written off.
        composed = _bare(_manifest_phase_6_steps(result))
        for step in _IMMUNE_FLOOR_STEPS:
            assert next(iter(_bare([step]))) in composed, f'{step} must survive a floor off'

        # The opt-out peers with off are dropped (never kept), and each drop is
        # recorded with a reason naming the explicit opt-out rather than the
        # posture cutoff — the two are different facts about the same removal.
        lane_dropped = _lane_dropped_reasons(result)
        for step in _OPT_OUT_STEPS:
            assert step in lane_dropped
            assert "'off'" in lane_dropped[step]
            assert next(iter(_bare([step]))) not in composed

        # Each floor step surfaces an immune informational warning.
        warned = {w['step']: w['warning'] for w in result['lane_warnings']}
        for step in _IMMUNE_FLOOR_STEPS:
            assert step in warned
            assert 'immune' in warned[step]

        # The retired "honored-but-warning" drop semantic is gone.
        assert all('honored' not in w['warning'] for w in result['lane_warnings'])
        # An opt-out drop never carries a warning (a clean opt-out).
        for step in _OPT_OUT_STEPS:
            assert step not in warned

    def test_full_posture_is_noop_no_lane_pruning(self, plan_context, monkeypatch):
        """Under ``full`` the lane pass is a no-op — nothing is dropped or warned,
        even with hand-written floor / opt-out offs."""
        _patch_immune_off_lanes(monkeypatch)
        candidates = _IMMUNE_FLOOR_STEPS + _OPT_OUT_STEPS
        _seed_marshal_lane_overrides(candidates, off_steps=candidates)
        _stub_footprint(_FOOTPRINT)
        plan_id = 'immune-off-full'
        _write_execution_profile(plan_context, plan_id, 'full')

        result = cmd_compose(
            _compose_ns(
                plan_id=plan_id,
                change_type='feature',
                scope_estimate='multi_module',
                affected_files_count=5,
                phase_6_steps=','.join(candidates),
            )
        )

        assert result is not None and result['status'] == 'success'
        assert result['execution_profile'] == 'full'
        assert result['lane_dropped'] == []
        assert result['lane_warnings'] == []

    def test_opt_out_off_drop_is_attributable_to_off_under_auto(self, plan_context, monkeypatch):
        """Under ``standard`` an adversarial (tier-standard) step is KEPT without an override
        but DROPPED once a hand-written ``off`` is set — the drop is the off, not the
        posture cutoff."""
        _patch_immune_off_lanes(monkeypatch)
        candidates = [
            'push',
            'create-pr',
            'ci-verify',
            'branch-cleanup',
            'record-metrics',
            'archive-plan',
            'sonar-roundtrip',
        ]

        # Baseline: no override → sonar-roundtrip (tier standard) survives standard posture.
        _seed_marshal_lane_overrides(candidates, off_steps=[])
        _stub_footprint(_FOOTPRINT)
        _write_execution_profile(plan_context, 'immune-off-baseline', 'standard')
        baseline = cmd_compose(
            _compose_ns(
                plan_id='immune-off-baseline',
                change_type='feature',
                scope_estimate='multi_module',
                affected_files_count=5,
                phase_6_steps=','.join(candidates),
            )
        )
        assert baseline is not None and baseline['status'] == 'success'
        assert 'sonar-roundtrip' in _bare(_manifest_phase_6_steps(baseline))
        assert 'sonar-roundtrip' not in _lane_dropped_reasons(baseline)

        # With off → the adversarial step drops cleanly (no warning).
        _seed_marshal_lane_overrides(candidates, off_steps=['sonar-roundtrip'])
        _write_execution_profile(plan_context, 'immune-off-optout', 'standard')
        dropped = cmd_compose(
            _compose_ns(
                plan_id='immune-off-optout',
                change_type='feature',
                scope_estimate='multi_module',
                affected_files_count=5,
                phase_6_steps=','.join(candidates),
            )
        )
        assert dropped is not None and dropped['status'] == 'success'
        reasons = _lane_dropped_reasons(dropped)
        assert 'sonar-roundtrip' in reasons
        # The recorded reason attributes the drop to the explicit off, not the
        # posture — which is exactly what this test's name claims and what the
        # bare-id list could never express.
        assert "'off'" in reasons['sonar-roundtrip']
        assert 'posture cutoff' not in reasons['sonar-roundtrip']
        assert 'sonar-roundtrip' not in _bare(_manifest_phase_6_steps(dropped))
        assert all(w['step'] != 'sonar-roundtrip' for w in dropped['lane_warnings'])
