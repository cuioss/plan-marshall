# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_ceremony_finalize_selection_fixtures import (
    _FOOTPRINT,
    _bare,
    _compose_ns,
    _manifest_phase_6_steps,
    _seed_marshal,
    _stub_footprint,
    cmd_compose,
    pytest,
)

# =============================================================================
# Test: adr-propose rides the ceremony transform untouched
#
# adr-propose is NOT a ceremony-gated step — it carries no ceremony_policy gate
# and is never force-dropped or force-added by the ceremony transform. It must
# survive the matrix + ceremony selection across the change-type rows in the
# same way lessons-capture does (its post-run-review sibling).
# =============================================================================


class TestCeremonyFinalizeAdrPropose:
    """adr-propose survives the ceremony transform across change-type rows."""

    @pytest.mark.parametrize(
        'change_type,scope_estimate',
        [
            ('feature', 'multi_module'),
            ('bug_fix', 'surgical'),
            ('tech_debt', 'surgical'),
            ('enhancement', 'single_module'),
        ],
    )
    def test_adr_propose_survives_ceremony_across_change_types(self, plan_context, change_type, scope_estimate):
        _seed_marshal()  # all ceremony gates default to auto
        _stub_footprint(_FOOTPRINT)

        # plan_id rejects underscores; derive a hyphenated slug from the params.
        slug = f'{change_type}-{scope_estimate}'.replace('_', '-')
        result = cmd_compose(
            _compose_ns(
                plan_id=f'ceremony-adr-{slug}',
                change_type=change_type,
                scope_estimate=scope_estimate,
            )
        )

        assert result is not None and result['status'] == 'success'
        bare = _bare(_manifest_phase_6_steps(result))
        # adr-propose is present and rides alongside its post-run-review sibling.
        assert 'adr-propose' in bare
        assert 'lessons-capture' in bare
        # The ceremony transform never touches adr-propose (not a ceremony gate).
        assert 'adr-propose' not in result['ceremony_finalize_forced_in']
        assert 'adr-propose' not in result['ceremony_finalize_forced_out']

    def test_adr_propose_not_force_dropped_when_gates_set_to_never(self, plan_context):
        """Setting every ceremony gate to ``never`` drops only the ceremony
        steps — adr-propose is not a ceremony gate, so it survives."""
        _seed_marshal(finalize_gates={'self_review': 'off', 'qgate': 'off', 'simplify': 'off'})
        _stub_footprint(_FOOTPRINT)

        result = cmd_compose(_compose_ns(plan_id='ceremony-adr-never'))

        assert result is not None and result['status'] == 'success'
        bare = _bare(_manifest_phase_6_steps(result))
        assert 'adr-propose' in bare
        assert 'adr-propose' not in result['ceremony_finalize_forced_out']
