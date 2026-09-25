# SPDX-License-Identifier: FSL-1.1-ALv2
"""Behavior-cluster tests carved from test_decision_rules.py: pre."""

#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_decision_rules_fixtures import (
    DEFAULT_PHASE_6_STEPS,
    _compose_ns,
    _restore_footprint_resolver,
    _seed_marshal,
    _stub_footprint,
    cmd_compose,
    extension_base,
    result_phase_6_steps,
)


class TestPreSubmissionSelfReviewSurvivesCompose:
    """No footprint gate subtracts this step; only ``commit_push_disabled`` does.

    The ``pre_submission_self_review_inactive`` pre-filter was VACUOUS — it
    structurally returned ``(candidates, False)`` for every input, so no footprint
    state could ever drop the step — and has been removed outright along with its
    unreachable emitter and its always-``False`` compose-result key. These cases
    pin the surviving behaviour across all three footprint states, so a future
    re-introduction of a footprint gate here fails rather than silently dropping a
    review step the operator never opted out of.
    """

    def test_keeps_step_when_footprint_unresolvable(self, plan_context):
        """Early compose (no worktree yet) is no evidence — the step survives."""
        _seed_marshal(ci_provider=None)
        _stub_footprint(None)

        ns = _compose_ns(plan_id='qg-self-review-unresolvable')
        result = cmd_compose(ns)

        assert result is not None
        assert result['status'] == 'success'
        assert 'pre-submission-self-review' in result_phase_6_steps(result)

    def test_keeps_step_when_footprint_resolvable_and_empty(self, plan_context):
        """A resolvable-but-empty footprint does not drop the step either."""
        _seed_marshal(ci_provider=None)
        _stub_footprint([])

        ns = _compose_ns(plan_id='qg-self-review-empty')
        result = cmd_compose(ns)

        assert result is not None
        assert result['status'] == 'success'
        assert 'pre-submission-self-review' in result_phase_6_steps(result)

    def test_keeps_step_when_footprint_non_empty(self, plan_context):
        _seed_marshal(ci_provider=None)
        _stub_footprint(['marketplace/bundles/x/skills/y/SKILL.md'])

        ns = _compose_ns(plan_id='qg-self-review-active')
        result = cmd_compose(ns)

        assert result is not None
        assert result['status'] == 'success'
        assert 'pre-submission-self-review' in result_phase_6_steps(result)

    def test_commit_and_push_false_strips_self_review(self, plan_context):
        """``commit_push_disabled`` is the ONE gate that still removes the step."""
        _seed_marshal(ci_provider=None)
        _stub_footprint(['some/file.py'])

        ns = _compose_ns(plan_id='qg-self-review-no-push', commit_and_push='false')
        result = cmd_compose(ns)

        assert result is not None
        assert result['status'] == 'success'
        steps = result_phase_6_steps(result)
        assert 'push' not in steps
        assert 'pre-push-quality-gate' not in steps
        assert 'pre-submission-self-review' not in steps

    def test_commit_push_drop_is_reported_per_step(self, plan_context):
        """Every dropped step is named, not just ``push``.

        The former aggregate reporting named only ``push``, so the two push-only
        gates vanished unnamed. Each drop now carries its own ``{step, reason}``
        record with a non-empty reason.

        The candidate CSV is built explicitly to carry all three droppable steps:
        the gate removes the INTERSECTION of its drop set with the candidates, and
        the default candidate list happens to contain only ``push`` — which is
        precisely why an aggregate line looked sufficient for so long.
        """
        _seed_marshal(ci_provider=None)
        _stub_footprint(['some/file.py'])

        candidates = list(DEFAULT_PHASE_6_STEPS)
        for extra in ('pre-push-quality-gate', 'pre-submission-self-review'):
            if extra not in candidates:
                candidates.insert(candidates.index('push'), extra)

        ns = _compose_ns(
            plan_id='qg-self-review-records',
            commit_and_push='false',
            phase_6_steps=','.join(candidates),
        )
        result = cmd_compose(ns)

        assert result is not None
        dropped = result['commit_push_dropped']
        assert {record['step'] for record in dropped} == {
            'push',
            'pre-push-quality-gate',
            'pre-submission-self-review',
        }
        assert all(record['reason'] for record in dropped)

    def test_commit_push_dropped_is_empty_when_pushing(self, plan_context):
        """The complementary direction: nothing is dropped when a push will occur."""
        _seed_marshal(ci_provider=None)
        _stub_footprint(['some/file.py'])

        ns = _compose_ns(plan_id='qg-self-review-pushing', commit_and_push='true')
        result = cmd_compose(ns)

        assert result is not None
        assert result['commit_push_dropped'] == []



# =============================================================================
# Test: pre_push_quality_gate_inactive pre-filter (build-decision consumer site)
# =============================================================================


class TestPrePushQualityGateInactive:
    """The pre-filter consumes ``extension_base.should_execute_build``'s verdict.

    The build-necessity decision was centralized into
    ``extension_base.should_execute_build`` (Axis-B strip: the four former
    consumer sites no longer each re-derive it). ``_apply_pre_push_quality_gate_inactive``
    is now a thin consumer over the THREE-value verdict vocabulary: it drops
    ``pre-push-quality-gate`` only on the positive ``not_necessary`` answer, and
    KEEPS it on both ``build`` (a real build is needed) and ``unknown`` (no
    evidence either way). The pre-filter imports ``should_execute_build`` from
    ``extension_base`` at call time, so patching it on the ``extension_base``
    module object is what the pre-filter observes. The decision logic itself is
    covered in ``manage-config/test_build_decision.py``; these tests assert only
    the consumer-site wiring.
    """

    def _phase_6_with_pre_push_quality_gate(self) -> str:
        """Default phase-6 steps with ``pre-push-quality-gate`` spliced in.

        ``DEFAULT_PHASE_6_STEPS`` does not carry the gate, so a test that wants
        to exercise the pre-filter must inject it into the candidate set.
        """
        steps = list(DEFAULT_PHASE_6_STEPS)
        steps.insert(steps.index('push'), 'pre-push-quality-gate')
        return ','.join(steps)

    def test_keeps_gate_when_verdict_is_build(self, plan_context, monkeypatch):
        """A ``build`` verdict keeps ``pre-push-quality-gate`` in phase_6.steps."""
        _seed_marshal(ci_provider=None)
        _stub_footprint(['scripts/foo.py'])
        monkeypatch.setattr(
            extension_base,
            'should_execute_build',
            lambda command, plan_id, project_root=None: {
                'decision': 'build',
                'canonical_command': command,
            },
        )

        ns = _compose_ns(
            plan_id='qg-pre-push-build',
            phase_6_steps=self._phase_6_with_pre_push_quality_gate(),
        )
        result = cmd_compose(ns)

        assert result is not None
        assert result['status'] == 'success'
        assert result['pre_push_quality_gate_omitted'] is False
        assert 'pre-push-quality-gate' in result_phase_6_steps(result)

    def test_drops_gate_when_verdict_is_not_necessary(self, plan_context, monkeypatch):
        """A ``not_necessary`` verdict drops ``pre-push-quality-gate``."""
        _seed_marshal(ci_provider=None)
        _stub_footprint(['README.md'])
        monkeypatch.setattr(
            extension_base,
            'should_execute_build',
            lambda command, plan_id, project_root=None: {
                'decision': 'not_necessary',
                'reason': 'plan footprint touches no build_map glob',
                'canonical_command': command,
            },
        )

        ns = _compose_ns(
            plan_id='qg-pre-push-not-necessary',
            phase_6_steps=self._phase_6_with_pre_push_quality_gate(),
        )
        result = cmd_compose(ns)

        assert result is not None
        assert result['status'] == 'success'
        assert result['pre_push_quality_gate_omitted'] is True
        assert 'pre-push-quality-gate' not in result_phase_6_steps(result)

    def test_keeps_gate_when_verdict_is_unknown(self, plan_context, monkeypatch):
        """An ``unknown`` verdict KEEPS the gate — fail toward inclusion.

        The load-bearing regression for Defect B's consumer site. An unresolvable
        footprint is the normal state at phase-4-plan compose; reading it as a
        positive "nothing to build" answer is what silently dropped a quality gate
        the operator never opted out of. ADR-009 (an unsubstantiated verdict must
        not read as a positive one) and ADR-004 (the composer may not re-derive
        build necessity from any other signal) both require the keep.
        """
        _seed_marshal(ci_provider=None)
        _stub_footprint(None)
        monkeypatch.setattr(
            extension_base,
            'should_execute_build',
            lambda command, plan_id, project_root=None: {
                'decision': 'unknown',
                'reason': 'plan footprint unresolvable — no materialized worktree carries evidence of what this plan changed',
                'canonical_command': command,
            },
        )

        ns = _compose_ns(
            plan_id='qg-pre-push-unknown',
            phase_6_steps=self._phase_6_with_pre_push_quality_gate(),
        )
        result = cmd_compose(ns)

        assert result is not None
        assert result['status'] == 'success'
        assert result['pre_push_quality_gate_omitted'] is False
        assert result['build_verdict_decision'] == 'unknown'
        assert 'pre-push-quality-gate' in result_phase_6_steps(result)

    def test_unknown_and_not_necessary_diverge_on_the_same_gate(self, plan_context, monkeypatch):
        """Only the verdict differs, and only ``not_necessary`` drops the gate.

        The paired assertion that pins the consumer reads the decision VALUE
        rather than "anything that is not ``build``" — the shape that would
        collapse ``unknown`` back into a drop.
        """
        _seed_marshal(ci_provider=None)
        _stub_footprint(None)

        def _verdict(decision):
            return lambda command, plan_id, project_root=None: {
                'decision': decision,
                'reason': f'{decision} for test',
                'canonical_command': command,
            }

        monkeypatch.setattr(extension_base, 'should_execute_build', _verdict('unknown'))
        kept = cmd_compose(
            _compose_ns(
                plan_id='qg-pre-push-diverge-unknown',
                phase_6_steps=self._phase_6_with_pre_push_quality_gate(),
            )
        )
        monkeypatch.setattr(extension_base, 'should_execute_build', _verdict('not_necessary'))
        dropped = cmd_compose(
            _compose_ns(
                plan_id='qg-pre-push-diverge-not-necessary',
                phase_6_steps=self._phase_6_with_pre_push_quality_gate(),
            )
        )

        assert 'pre-push-quality-gate' in result_phase_6_steps(kept)
        assert 'pre-push-quality-gate' not in result_phase_6_steps(dropped)

    def test_no_op_when_gate_absent_from_candidates(self, plan_context, monkeypatch):
        """The pre-filter is a no-op (and never calls the decision) when the gate
        is already absent from the candidate set — e.g. already stripped by
        ``commit_and_push=false``."""
        _seed_marshal(ci_provider=None)
        _stub_footprint(['scripts/foo.py'])

        def _should_not_be_called(*_a, **_kw):
            raise AssertionError('should_execute_build must not run when the gate is absent')

        monkeypatch.setattr(extension_base, 'should_execute_build', _should_not_be_called)

        # Default candidate set carries no pre-push-quality-gate.
        ns = _compose_ns(plan_id='qg-pre-push-absent')
        result = cmd_compose(ns)

        assert result is not None
        assert result['status'] == 'success'
        assert result['pre_push_quality_gate_omitted'] is False
        assert 'pre-push-quality-gate' not in result_phase_6_steps(result)
