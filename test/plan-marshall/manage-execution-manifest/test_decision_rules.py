#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the manage-execution-manifest pre-filters and finalize selection.

Covers:

- ``pre_push_quality_gate_inactive`` — re-pointed onto the centralized
  build-decision API (``extension_base.should_execute_build``). The pre-filter
  keeps ``pre-push-quality-gate`` only when the build-decision verdict is
  ``build``; a ``not_necessary`` verdict drops it. The decision logic itself is
  exhaustively covered in ``manage-config/test_build_decision.py``; here we
  assert the consumer-site wiring (verdict → keep/drop).
- ``pre_submission_self_review_inactive`` — footprint-gated.
- The absence of any bot-enforcement guard: ``automatic-review`` is governed
  purely by its configured candidacy / ``lane`` — compose never force-adds nor
  re-orders it.
- The task-queue-aware ``early_terminate`` predicate.
"""

import importlib.util
import json
from argparse import Namespace
from pathlib import Path

import extension_base
import pytest

from conftest import PlanContext

# =============================================================================
# Module loading (script has hyphens in filename → load via importlib)
# =============================================================================

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-execution-manifest'
    / 'scripts'
)


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    assert spec is not None, f'Failed to load module spec for {filename}'
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


_mem = _load_module('_mem_script_decision_rules', 'manage-execution-manifest.py')
cmd_compose = _mem.cmd_compose
read_manifest = _mem.read_manifest
DEFAULT_PHASE_6_STEPS = _mem.DEFAULT_PHASE_6_STEPS

# Silence the best-effort decision-log subprocess in tests.
_mem._log_decision = lambda *a, **kw: None
_mem._log_commit_push_omitted = lambda *a, **kw: None
_mem._log_pre_push_quality_gate_omitted = lambda *a, **kw: None
_mem._log_pre_submission_self_review_omitted = lambda *a, **kw: None

# =============================================================================
# Helpers
# =============================================================================


def _phase_6_with_self_review() -> str:
    """Return the comma-separated default phase-6-finalize steps with pre-submission-self-review added."""
    steps = list(DEFAULT_PHASE_6_STEPS) + ['pre-submission-self-review']
    return ','.join(steps)


def _compose_ns(
    plan_id: str = 'test-plan',
    change_type: str = 'feature',
    track: str = 'complex',
    scope_estimate: str = 'multi_module',
    recipe_key: str | None = None,
    affected_files_count: int = 5,
    phase_5_steps: str | None = 'quality-gate,module-tests',
    phase_6_steps: str | None = None,
    commit_and_push: str | None = None,
) -> Namespace:
    return Namespace(
        plan_id=plan_id,
        change_type=change_type,
        track=track,
        scope_estimate=scope_estimate,
        recipe_key=recipe_key,
        affected_files_count=affected_files_count,
        phase_5_steps=phase_5_steps,
        phase_6_steps=phase_6_steps if phase_6_steps is not None else _phase_6_with_self_review(),
        commit_and_push=commit_and_push,
    )


def _seed_marshal(ci_provider: str | None = 'github') -> Path:
    """Write a minimal marshal.json at PLAN_BASE_DIR/marshal.json for the test.

    Pre-push-quality-gate activation derives from ``build.map``
    globs (D7/D8), so the seed carries a build_map entry whose ``**/*.py`` glob
    keeps the gate active against a matching footprint.
    """
    from file_ops import get_marshal_path

    marshal: dict = {
        'plan': {'phase-6-finalize': {}},
        'build': {
            'map': {
                'python': [
                    {'glob': '**/*.py', 'role': 'production', 'build_class': 'compile'},
                ],
            },
        },
    }
    if ci_provider:
        marshal['providers'] = [
            {'skill_name': f'plan-marshall:workflow-integration-{ci_provider}', 'category': 'ci'}
        ]
    marshal_path = get_marshal_path()
    marshal_path.parent.mkdir(parents=True, exist_ok=True)
    marshal_path.write_text(json.dumps(marshal, indent=2))
    return marshal_path


def _stub_footprint(footprint: list[str]) -> None:
    """Stub ``_resolve_footprint`` so the activation pre-filter sees the given set.

    The ``pre_submission_self_review_inactive`` pre-filter now derives the live
    plan footprint on demand via ``compute_plan_branch_diff`` rather than reading
    a seeded ``references.modified_files`` ledger. Tests inject the footprint by
    replacing the module-level resolver; the autouse fixture on
    ``TestPreSubmissionSelfReviewInactive`` restores the original after each test.
    """
    _mem._resolve_footprint = lambda plan_id: list(footprint)


# =============================================================================
# Test: pre_submission_self_review_inactive pre-filter
# =============================================================================


@pytest.fixture(autouse=True)
def _restore_footprint_resolver():
    """Restore ``_resolve_footprint`` after any test that stubbed it.

    ``_stub_footprint`` replaces the module-level resolver in-place; this
    module-scoped autouse fixture snapshots and restores it so a stub installed
    by one test never leaks into the next.
    """
    original = _mem._resolve_footprint
    yield
    _mem._resolve_footprint = original


class TestPreSubmissionSelfReviewInactive:
    """Pre-filter keeps the step through compose (self-gates at run time); commit_and_push=false strips it upstream."""

    def test_keeps_step_when_footprint_empty(self, plan_context):
        # An empty compose-time footprint (phase-4-plan, before the worktree is
        # materialised) is NOT evidence the step is inactive — it only means the
        # worktree is not yet materialised. The step survives compose and
        # self-gates at run time (mirroring _apply_canonical_verify_inactive's
        # compose-time safety), so it is KEPT and reports omitted=False.
        _seed_marshal(ci_provider=None)
        _stub_footprint([])

        ns = _compose_ns(plan_id='qg-self-review-empty')
        result = cmd_compose(ns)

        assert result is not None
        assert result['status'] == 'success'
        assert result['pre_submission_self_review_omitted'] is False
        assert 'pre-submission-self-review' in result_phase_6_steps(result)

    def test_keeps_step_when_footprint_non_empty(self, plan_context):
        _seed_marshal(ci_provider=None)
        _stub_footprint(['marketplace/bundles/x/skills/y/SKILL.md'])

        ns = _compose_ns(plan_id='qg-self-review-active')
        result = cmd_compose(ns)

        assert result is not None
        assert result['status'] == 'success'
        assert result['pre_submission_self_review_omitted'] is False
        assert 'pre-submission-self-review' in result_phase_6_steps(result)

    def test_commit_and_push_false_strips_self_review(self, plan_context):
        _seed_marshal(ci_provider=None)
        _stub_footprint(['some/file.py'])

        ns = _compose_ns(plan_id='qg-self-review-no-push', commit_and_push='false')
        result = cmd_compose(ns)

        assert result is not None
        assert result['status'] == 'success'
        assert result['commit_push_omitted'] is True
        steps = result_phase_6_steps(result)
        assert 'push' not in steps
        assert 'pre-push-quality-gate' not in steps
        assert 'pre-submission-self-review' not in steps


# =============================================================================
# Test: pre_push_quality_gate_inactive pre-filter (build-decision consumer site)
# =============================================================================


class TestPrePushQualityGateInactive:
    """The pre-filter consumes ``extension_base.should_execute_build``'s verdict.

    The build-necessity decision was centralized into
    ``extension_base.should_execute_build`` (Axis-B strip: the four former
    consumer sites no longer each re-derive it). ``_apply_pre_push_quality_gate_inactive``
    is now a thin consumer — it keeps ``pre-push-quality-gate`` iff the verdict
    is ``build`` and drops it on any ``not_necessary`` verdict. The pre-filter
    imports ``should_execute_build`` from ``extension_base`` at call time, so
    patching it on the ``extension_base`` module object is what the pre-filter
    observes. The decision logic itself is covered in
    ``manage-config/test_build_decision.py``; these tests assert only the
    consumer-site wiring.
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


# =============================================================================
# Test: no bot-enforcement guard — automatic-review governed by candidacy/lane
# =============================================================================


class TestNoBotEnforcementGuard:
    """The bot-enforcement guard (and its placement-validator twin) are removed.

    ``automatic-review`` is governed purely by its configured candidacy / ``lane``
    — compose never force-adds it back on GitHub/GitLab plans and never emits a
    ``bot_enforcement_violation`` error. Its presence tracks the candidate list and
    the lane resolution exactly.
    """

    def test_no_bot_enforcement_symbols_survive(self):
        """No bot-enforcement guard / placement-validator symbol remains on the module."""
        for symbol in (
            '_apply_bot_enforcement_guard',
            '_bot_enforcement_insert_index',
            '_validate_automatic_review_placement',
            '_log_bot_enforcement_guard_fired',
            '_log_bot_enforcement_guard_remediated',
            '_log_bot_enforcement_placement_violation',
        ):
            assert not hasattr(_mem, symbol), f'{symbol} must be deleted with the bot-enforcement guard'

    def test_github_plan_does_not_force_add_dropped_automatic_review(self, plan_context):
        _seed_marshal(ci_provider='github')
        _stub_footprint(['some/file.py'])

        # Candidate set EXCLUDES automatic-review; with no guard it stays absent.
        phase_6 = ','.join(s for s in DEFAULT_PHASE_6_STEPS if s != 'automatic-review')
        ns = _compose_ns(plan_id='qg-bot-github', phase_6_steps=phase_6)
        result = cmd_compose(ns)

        assert result is not None
        assert result['status'] == 'success'
        assert result.get('error') != 'bot_enforcement_violation'
        assert 'automatic-review' not in result_phase_6_steps(result)

    def test_gitlab_plan_does_not_force_add_dropped_automatic_review(self, plan_context):
        _seed_marshal(ci_provider='gitlab')
        _stub_footprint(['some/file.py'])

        phase_6 = ','.join(s for s in DEFAULT_PHASE_6_STEPS if s != 'automatic-review')
        ns = _compose_ns(plan_id='qg-bot-gitlab', phase_6_steps=phase_6)
        result = cmd_compose(ns)

        assert result is not None
        assert result['status'] == 'success'
        assert result.get('error') != 'bot_enforcement_violation'
        assert 'automatic-review' not in result_phase_6_steps(result)

    def test_present_when_in_candidates(self, plan_context):
        _seed_marshal(ci_provider='github')
        _stub_footprint(['some/file.py'])

        # multi_module feature keeps automatic-review (present in default candidates).
        ns = _compose_ns(plan_id='qg-bot-present')
        result = cmd_compose(ns)

        assert result is not None
        assert result['status'] == 'success'
        assert 'automatic-review' in result_phase_6_steps(result)

    def test_absent_for_non_ci_plan_stays_absent(self, plan_context):
        _seed_marshal(ci_provider=None)
        _stub_footprint(['some/file.py'])

        phase_6 = ','.join(s for s in DEFAULT_PHASE_6_STEPS if s != 'automatic-review')
        ns = _compose_ns(plan_id='qg-bot-other', phase_6_steps=phase_6)
        result = cmd_compose(ns)

        assert result is not None
        assert result['status'] == 'success'
        assert 'automatic-review' not in result_phase_6_steps(result)


# =============================================================================
# Helpers — read manifest after a successful compose
# =============================================================================


def result_phase_6_steps(result: dict) -> list[str]:
    """Read the persisted manifest after a successful compose and return phase_6.steps."""
    plan_id = result['plan_id']
    manifest = read_manifest(plan_id)
    assert manifest is not None
    return list(manifest.get('phase_6', {}).get('steps', []))


# =============================================================================
# Test: task-queue-aware early_terminate predicate (lesson 2026-05-24-17-001)
# =============================================================================


def _seed_task_file(plan_id: str, task_number: int, status: str) -> None:
    """Write a minimal TASK-{NNN}.json with the given status under the plan's tasks/ dir.

    Used to exercise the composer's task-queue read: Rule 1's
    ``early_terminate`` predicate now ANDs the existing
    ``affected_files_count==0`` condition with "no pending or in-progress task
    on disk". A test that seeds at least one pending task forces the
    short-circuit to fall through to Rule 7 (default).
    """
    from file_ops import get_plan_dir

    tasks_dir = get_plan_dir(plan_id) / 'tasks'
    tasks_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        'number': task_number,
        'title': f'stub task {task_number}',
        'status': status,
        'steps': [],
    }
    (tasks_dir / f'TASK-{task_number:03d}.json').write_text(json.dumps(payload, indent=2))


class TestEarlyTerminateTaskQueueGuard:
    """Rule 1 (early_terminate_analysis) now requires the task queue to be empty.

    Lesson ``2026-05-24-17-001``: an analysis-only plan that produces zero
    affected files but still queues at least one deliverable task must NOT
    short-circuit phase-5 before TASK-001 runs. The composer reads
    ``tasks/TASK-*.json`` directly and ANDs the existing
    ``affected_files_count==0`` condition with "no pending or in-progress
    task". Genuine no-op plans (no task files on disk) preserve the prior
    early-terminate behaviour.
    """

    def test_early_terminate_when_task_queue_empty(self):
        """Case (i): analysis + affected_files=0 + task_queue empty → early_terminate=True."""
        with PlanContext('et-queue-empty'):
            # No tasks/TASK-*.json seeded — queue is empty.
            ns = _compose_ns(
                plan_id='et-queue-empty',
                change_type='analysis',
                scope_estimate='none',
                affected_files_count=0,
            )
            result = cmd_compose(ns)
            assert result is not None
            assert result['rule_fired'] == 'early_terminate_analysis'
            assert result['phase_5']['early_terminate'] is True

    def test_falls_through_to_default_when_task_queue_non_empty(self):
        """Case (ii): analysis + affected_files=0 + task_queue pending → Rule 7 default."""
        with PlanContext('et-queue-pending'):
            _seed_task_file('et-queue-pending', task_number=1, status='pending')
            ns = _compose_ns(
                plan_id='et-queue-pending',
                change_type='analysis',
                scope_estimate='none',
                affected_files_count=0,
            )
            result = cmd_compose(ns)
            assert result is not None
            assert result['rule_fired'] == 'default'
            assert result['phase_5']['early_terminate'] is False

    def test_rule_label_preserved_for_genuine_early_terminate(self):
        """Case (iii): the ``early_terminate_analysis`` rule label still appears for case (i)."""
        with PlanContext('et-queue-label'):
            ns = _compose_ns(
                plan_id='et-queue-label',
                change_type='analysis',
                scope_estimate='none',
                affected_files_count=0,
            )
            result = cmd_compose(ns)
            assert result is not None
            assert result['rule_fired'] == 'early_terminate_analysis'

    def test_falls_through_when_task_queue_in_progress(self):
        """An in_progress task also blocks the short-circuit (symmetric to pending)."""
        with PlanContext('et-queue-inprogress'):
            _seed_task_file('et-queue-inprogress', task_number=1, status='in_progress')
            ns = _compose_ns(
                plan_id='et-queue-inprogress',
                change_type='analysis',
                scope_estimate='none',
                affected_files_count=0,
            )
            result = cmd_compose(ns)
            assert result is not None
            assert result['rule_fired'] == 'default'
            assert result['phase_5']['early_terminate'] is False

    def test_done_tasks_do_not_block_short_circuit(self):
        """A queue containing ONLY done tasks does NOT block early_terminate."""
        with PlanContext('et-queue-done'):
            _seed_task_file('et-queue-done', task_number=1, status='done')
            ns = _compose_ns(
                plan_id='et-queue-done',
                change_type='analysis',
                scope_estimate='none',
                affected_files_count=0,
            )
            result = cmd_compose(ns)
            assert result is not None
            assert result['rule_fired'] == 'early_terminate_analysis'
            assert result['phase_5']['early_terminate'] is True


# =============================================================================
# Test: security_audit_inactive pre-filter (direct helper unit coverage)
#
# ``_apply_security_audit_inactive`` is the symmetric peer of
# ``_apply_simplify_inactive``: it drops ``finalize-step-security-audit`` from
# the phase-6 candidate list unless BOTH
# ``change_type ∈ {feature, bug_fix, tech_debt, enhancement}`` AND
# ``affected_files_count > 0``. These tests exercise the helper directly (no
# compose round-trip) so the gate's truth table and the no-op-when-absent
# contract are pinned at the unit boundary. See standards/decision-rules.md
# § Pre-Filter: security_audit_inactive.
# =============================================================================


_apply_security_audit_inactive = _mem._apply_security_audit_inactive


class TestSecurityAuditInactivePreFilter:
    """Direct unit coverage of the ``security_audit_inactive`` pre-filter helper."""

    @pytest.mark.parametrize(
        'change_type,affected_files_count,expect_present,expect_fired',
        [
            # Gate passes: code-touching change types with files > 0 → kept.
            ('feature', 5, True, False),
            ('bug_fix', 1, True, False),
            ('tech_debt', 3, True, False),
            ('enhancement', 5, True, False),
            # Gate fails on change_type → dropped.
            ('analysis', 5, False, True),
            ('verification', 5, False, True),
            # Gate fails on zero affected files (even for a code-touching type).
            ('feature', 0, False, True),
            ('tech_debt', 0, False, True),
            ('enhancement', 0, False, True),
        ],
    )
    def test_gate_truth_table(
        self, change_type, affected_files_count, expect_present, expect_fired
    ):
        candidates = ['finalize-step-security-audit', 'push', 'archive-plan']
        filtered, fired = _apply_security_audit_inactive(
            candidates, change_type, affected_files_count
        )
        assert fired is expect_fired
        assert ('finalize-step-security-audit' in filtered) is expect_present
        # Non-target candidates are never disturbed.
        assert 'push' in filtered
        assert 'archive-plan' in filtered

    def test_no_op_when_step_absent_from_candidates(self):
        # The step is not in the candidate set → the pre-filter is a no-op even
        # when the gate would otherwise fail (returns the list unchanged, fired=False).
        candidates = ['push', 'archive-plan']
        filtered, fired = _apply_security_audit_inactive(candidates, 'analysis', 0)
        assert fired is False
        assert filtered == candidates

    def test_returns_new_list_on_drop_not_mutating_input(self):
        # The drop branch must not mutate the caller's candidate list in place.
        candidates = ['finalize-step-security-audit', 'push']
        filtered, fired = _apply_security_audit_inactive(candidates, 'analysis', 2)
        assert fired is True
        assert 'finalize-step-security-audit' not in filtered
        # Input list is untouched.
        assert candidates == ['finalize-step-security-audit', 'push']


# =============================================================================
# Test: unresolved_ask_provider_drop pre-filter (D6, direct helper coverage)
#
# ``_apply_unresolved_ask_provider_drop`` drops an UNRESOLVED ``lane:ask`` infra
# element (automatic-review / sonar-roundtrip) from the phase-6 candidate list
# when its provider is absent. The seed lane for both elements is ``ask``; a
# steward answer overwrites the override to off/auto/full, so an effective tier
# still equal to ``ask`` at compose is the unresolved case. These tests exercise
# the pure helper directly (no compose round-trip) so the full truth table and
# the no-op contracts are pinned at the unit boundary. See
# standards/decision-rules.md § Pre-Filter: unresolved_ask_provider_drop.
# =============================================================================


_apply_unresolved_ask_provider_drop = _mem._apply_unresolved_ask_provider_drop
_read_sonar_provider = _mem._read_sonar_provider


def _override_map(ar_lane: str | None = None, sr_lane: str | None = None) -> dict[str, dict]:
    """Build a marshal-style phase-6 step map with per-element lane overrides.

    Keys mirror the seeded marshal shape: ``plan-marshall:automatic-review`` and
    ``default:sonar-roundtrip`` (the D1 seed keys). Only elements with a non-None
    lane are included.
    """
    m: dict[str, dict] = {}
    if ar_lane is not None:
        m['plan-marshall:automatic-review'] = {'lane': ar_lane}
    if sr_lane is not None:
        m['default:sonar-roundtrip'] = {'lane': sr_lane}
    return m


class TestUnresolvedAskProviderDropPreFilter:
    """Direct unit coverage of the D6 unresolved-ask provider-drop pre-filter."""

    @pytest.mark.parametrize(
        'ar_lane,ci_provider,expect_present',
        [
            ('ask', None, False),      # unresolved ask + no CI provider → DROP
            ('ask', 'github', True),   # unresolved ask + CI provider → keep
            ('ask', 'gitlab', True),   # provider identity is irrelevant — any non-None keeps
            ('auto', None, True),      # resolved auto (steward answered) → keep even w/o provider
            ('full', None, True),      # resolved full → keep even w/o provider
            ('off', None, True),       # off is resolved; the later lane pass drops it, not this one
        ],
    )
    def test_automatic_review_truth_table(self, ar_lane, ci_provider, expect_present):
        candidates = ['plan-marshall:automatic-review', 'push', 'archive-plan']
        kept, dropped = _apply_unresolved_ask_provider_drop(
            candidates, _override_map(ar_lane=ar_lane), ci_provider, None
        )
        assert ('plan-marshall:automatic-review' in kept) is expect_present
        assert ('plan-marshall:automatic-review' in dropped) is (not expect_present)
        # Non-infra candidates are never disturbed.
        assert 'push' in kept and 'archive-plan' in kept

    @pytest.mark.parametrize(
        'sr_lane,sonar_provider,expect_present',
        [
            ('ask', None, False),      # unresolved ask + no Sonar provider → DROP
            ('ask', 'sonar', True),    # unresolved ask + Sonar provider → keep
            ('auto', None, True),      # resolved auto → keep even w/o provider
            ('full', None, True),      # resolved full → keep even w/o provider
            ('off', None, True),       # off is resolved; dropped later by the lane pass, not here
        ],
    )
    def test_sonar_roundtrip_truth_table(self, sr_lane, sonar_provider, expect_present):
        # The candidate list is boundary-normalized in compose (``default:`` is
        # stripped), so the helper is given the bare ``sonar-roundtrip`` form.
        candidates = ['sonar-roundtrip', 'push']
        kept, dropped = _apply_unresolved_ask_provider_drop(
            candidates, _override_map(sr_lane=sr_lane), None, sonar_provider
        )
        assert ('sonar-roundtrip' in kept) is expect_present
        assert ('sonar-roundtrip' in dropped) is (not expect_present)
        assert 'push' in kept

    def test_both_unresolved_no_providers_drop_both(self):
        candidates = ['plan-marshall:automatic-review', 'sonar-roundtrip', 'push']
        kept, dropped = _apply_unresolved_ask_provider_drop(
            candidates, _override_map(ar_lane='ask', sr_lane='ask'), None, None
        )
        assert kept == ['push']
        assert set(dropped) == {'plan-marshall:automatic-review', 'sonar-roundtrip'}

    def test_provider_isolation_ci_present_sonar_absent(self):
        # A configured CI provider keeps automatic-review; an absent Sonar
        # provider still drops an unresolved sonar-roundtrip. The two elements
        # are keyed to distinct providers.
        candidates = ['plan-marshall:automatic-review', 'sonar-roundtrip']
        kept, dropped = _apply_unresolved_ask_provider_drop(
            candidates, _override_map(ar_lane='ask', sr_lane='ask'), 'github', None
        )
        assert kept == ['plan-marshall:automatic-review']
        assert dropped == ['sonar-roundtrip']

    def test_no_override_keeps_infra_elements(self):
        # No marshal override at all (e.g. CSV-fallback, marshal_map None/empty):
        # the effective tier is undeterminable, not ``ask``, so nothing is dropped
        # (conservative keep).
        candidates = ['plan-marshall:automatic-review', 'sonar-roundtrip']
        for override_map in ({}, None):
            kept, dropped = _apply_unresolved_ask_provider_drop(candidates, override_map, None, None)
            assert dropped == []
            assert kept == candidates

    def test_non_infra_elements_pass_through_untouched(self):
        candidates = ['push', 'archive-plan', 'finalize-step-simplify']
        kept, dropped = _apply_unresolved_ask_provider_drop(
            candidates, _override_map(ar_lane='ask'), None, None
        )
        assert kept == candidates
        assert dropped == []

    def test_does_not_mutate_input_list(self):
        candidates = ['plan-marshall:automatic-review', 'push']
        _apply_unresolved_ask_provider_drop(
            candidates, _override_map(ar_lane='ask'), None, None
        )
        assert candidates == ['plan-marshall:automatic-review', 'push']


class TestReadSonarProvider:
    """``_read_sonar_provider`` resolves the Sonar provider from marshal.json."""

    def _seed_providers(self, providers: list[dict]) -> None:
        from file_ops import get_marshal_path

        marshal = {'plan': {'phase-6-finalize': {}}, 'providers': providers}
        marshal_path = get_marshal_path()
        marshal_path.parent.mkdir(parents=True, exist_ok=True)
        marshal_path.write_text(json.dumps(marshal, indent=2))

    def test_returns_sonar_when_declared(self, plan_context):
        self._seed_providers(
            [{'skill_name': 'plan-marshall:workflow-integration-sonar', 'category': 'sonar'}]
        )
        assert _read_sonar_provider() == 'sonar'

    def test_returns_sonar_regardless_of_category(self, plan_context):
        # The reader keys on skill_name, not category, so a differently-categorized
        # Sonar entry still resolves.
        self._seed_providers(
            [{'skill_name': 'plan-marshall:workflow-integration-sonar', 'category': 'quality'}]
        )
        assert _read_sonar_provider() == 'sonar'

    def test_none_when_no_sonar_provider(self, plan_context):
        self._seed_providers(
            [{'skill_name': 'plan-marshall:workflow-integration-github', 'category': 'ci'}]
        )
        assert _read_sonar_provider() is None

    def test_none_when_providers_absent(self, plan_context):
        from file_ops import get_marshal_path

        marshal_path = get_marshal_path()
        marshal_path.parent.mkdir(parents=True, exist_ok=True)
        marshal_path.write_text(json.dumps({'plan': {'phase-6-finalize': {}}}, indent=2))
        assert _read_sonar_provider() is None
