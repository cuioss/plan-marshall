# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_decision_rules_fixtures import (
    _RETROSPECTIVE,
    _apply_scope_gated_finalize,
    _compose_ns,
    _lane_map,
    _restore_footprint_resolver,
    _stub_footprint,
    cmd_compose,
    json,
    pytest,
    result_phase_6_steps,
)


class TestScopeGatedFinalizeDeclaredLaneImmunity:
    """``_apply_scope_gated_finalize`` honours an explicit lane declaration."""

    def test_single_module_drops_retrospective_without_declaration(self):
        candidates = [_RETROSPECTIVE, 'push', 'archive-plan']
        kept, dropped, immune = _apply_scope_gated_finalize(candidates, 'single_module', None)
        assert _RETROSPECTIVE not in kept
        assert dropped == [_RETROSPECTIVE]
        assert immune == []
        assert kept == ['push', 'archive-plan']

    def test_single_module_keeps_retrospective_with_declared_lane(self):
        # The regression: an operator's ``lane: minimal`` on plan-retrospective
        # must survive a single_module compose. Before declared-lane immunity the
        # step was dropped here and — having no ceremony re-add path — its
        # declared lane was never reachable.
        candidates = [_RETROSPECTIVE, 'push']
        kept, dropped, immune = _apply_scope_gated_finalize(
            candidates, 'single_module', _lane_map(_RETROSPECTIVE, 'minimal')
        )
        assert _RETROSPECTIVE in kept
        assert dropped == []
        assert immune == [_RETROSPECTIVE]

    def test_surgical_keeps_every_declared_step_and_drops_the_rest(self):
        candidates = [_RETROSPECTIVE, 'pre-submission-self-review', 'project:finalize-step-plugin-doctor', 'push']
        kept, dropped, immune = _apply_scope_gated_finalize(
            candidates, 'surgical', _lane_map('pre-submission-self-review', 'minimal')
        )
        assert 'pre-submission-self-review' in kept
        assert immune == ['pre-submission-self-review']
        assert set(dropped) == {_RETROSPECTIVE, 'project:finalize-step-plugin-doctor'}
        assert 'push' in kept

    def test_auto_declaration_does_not_confer_immunity(self):
        # ``auto`` is the defer value, so the implicit gate still drops.
        candidates = [_RETROSPECTIVE, 'push']
        kept, dropped, immune = _apply_scope_gated_finalize(
            candidates, 'single_module', _lane_map(_RETROSPECTIVE, 'standard')
        )
        assert _RETROSPECTIVE not in kept
        assert dropped == [_RETROSPECTIVE]
        assert immune == []

    @pytest.mark.parametrize('scope_estimate', ['none', 'multi_module', 'broad'])
    def test_non_scope_gated_estimates_never_subtract(self, scope_estimate):
        candidates = [_RETROSPECTIVE, 'push']
        kept, dropped, immune = _apply_scope_gated_finalize(candidates, scope_estimate, None)
        assert kept == candidates
        assert dropped == []
        assert immune == []

    def test_immune_step_keeps_its_list_position(self):
        candidates = ['push', _RETROSPECTIVE, 'archive-plan']
        kept, _dropped, _immune = _apply_scope_gated_finalize(
            candidates, 'single_module', _lane_map(_RETROSPECTIVE, 'full')
        )
        assert kept == ['push', _RETROSPECTIVE, 'archive-plan']

    def test_does_not_mutate_input_list(self):
        candidates = [_RETROSPECTIVE, 'push']
        _apply_scope_gated_finalize(candidates, 'single_module', None)
        assert candidates == [_RETROSPECTIVE, 'push']



class TestScopeGatedFinalizeImmunityThroughCompose:
    """End-to-end: the immunity survives a real ``single_module`` compose."""

    def test_declared_lane_keeps_retrospective_in_composed_manifest(self, plan_context):
        from file_ops import get_marshal_path

        marshal = {
            'plan': {
                'phase-6-finalize': {
                    'steps': {
                        'default:push': {},
                        'default:branch-cleanup': {},
                        'plan-marshall:plan-retrospective': {'lane': 'minimal'},
                        'default:archive-plan': {},
                    }
                }
            },
            'build': {'map': {'python': [{'glob': '**/*.py', 'role': 'production', 'build_class': 'compile'}]}},
        }
        marshal_path = get_marshal_path()
        marshal_path.parent.mkdir(parents=True, exist_ok=True)
        marshal_path.write_text(json.dumps(marshal, indent=2))
        _stub_footprint(['some/file.py'])

        result = cmd_compose(_compose_ns(plan_id='sg-immune-compose', scope_estimate='single_module'))

        assert result is not None
        assert result['status'] == 'success'
        assert result['scope_gated_finalize_dropped'] == []
        assert result['scope_gated_finalize_immune'] == [_RETROSPECTIVE]
        assert _RETROSPECTIVE in result_phase_6_steps(result)

    def test_undeclared_retrospective_is_still_dropped_by_compose(self, plan_context):
        from file_ops import get_marshal_path

        marshal = {
            'plan': {
                'phase-6-finalize': {
                    'steps': {
                        'default:push': {},
                        'default:branch-cleanup': {},
                        'plan-marshall:plan-retrospective': {},
                        'default:archive-plan': {},
                    }
                }
            },
            'build': {'map': {'python': [{'glob': '**/*.py', 'role': 'production', 'build_class': 'compile'}]}},
        }
        marshal_path = get_marshal_path()
        marshal_path.parent.mkdir(parents=True, exist_ok=True)
        marshal_path.write_text(json.dumps(marshal, indent=2))
        _stub_footprint(['some/file.py'])

        result = cmd_compose(_compose_ns(plan_id='sg-nodecl-compose', scope_estimate='single_module'))

        assert result is not None
        assert result['status'] == 'success'
        assert result['scope_gated_finalize_dropped'] == [_RETROSPECTIVE]
        assert result['scope_gated_finalize_immune'] == []
        assert _RETROSPECTIVE not in result_phase_6_steps(result)
