#!/usr/bin/env python3
"""Tests for the pre_submission_self_review_inactive pre-filter and bot-enforcement guard."""

import importlib.util
import json
from argparse import Namespace
from pathlib import Path

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
_mem._log_decision = lambda *a, **kw: None  # type: ignore[attr-defined]
_mem._log_commit_push_omitted = lambda *a, **kw: None  # type: ignore[attr-defined]
_mem._log_pre_push_quality_gate_omitted = lambda *a, **kw: None  # type: ignore[attr-defined]
_mem._log_pre_submission_self_review_omitted = lambda *a, **kw: None  # type: ignore[attr-defined]
_mem._log_bot_enforcement_guard_fired = lambda *a, **kw: None  # type: ignore[attr-defined]
_mem._log_bot_enforcement_guard_remediated = lambda *a, **kw: None  # type: ignore[attr-defined]


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
    commit_strategy: str | None = None,
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
        commit_strategy=commit_strategy,
    )


def _seed_marshal(ci_provider: str | None = 'github') -> Path:
    """Write a minimal marshal.json at PLAN_BASE_DIR/marshal.json for the test.

    Pre-push-quality-gate activation derives from ``skill_domains.build_map``
    globs (D7/D8), so the seed carries a build_map entry whose ``**/*.py`` glob
    keeps the gate active against a matching footprint.
    """
    from file_ops import get_marshal_path  # type: ignore[import-not-found]

    marshal: dict = {
        'plan': {'phase-6-finalize': {}},
        'skill_domains': {
            'build_map': {
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
    """Pre-filter drops the step when the live footprint is empty; no-op otherwise."""

    def test_drops_step_when_footprint_empty(self, plan_context):
        _seed_marshal(ci_provider=None)
        _stub_footprint([])

        ns = _compose_ns(plan_id='qg-self-review-empty')
        result = cmd_compose(ns)

        assert result is not None
        assert result['status'] == 'success'
        assert result['pre_submission_self_review_omitted'] is True
        assert 'pre-submission-self-review' not in result_phase_6_steps(result)

    def test_keeps_step_when_footprint_non_empty(self, plan_context):
        _seed_marshal(ci_provider=None)
        _stub_footprint(['marketplace/bundles/x/skills/y/SKILL.md'])

        ns = _compose_ns(plan_id='qg-self-review-active')
        result = cmd_compose(ns)

        assert result is not None
        assert result['status'] == 'success'
        assert result['pre_submission_self_review_omitted'] is False
        assert 'pre-submission-self-review' in result_phase_6_steps(result)

    def test_commit_strategy_none_strips_self_review(self, plan_context):
        _seed_marshal(ci_provider=None)
        _stub_footprint(['some/file.py'])

        ns = _compose_ns(plan_id='qg-self-review-no-push', commit_strategy='none')
        result = cmd_compose(ns)

        assert result is not None
        assert result['status'] == 'success'
        assert result['commit_push_omitted'] is True
        steps = result_phase_6_steps(result)
        assert 'commit-push' not in steps
        assert 'pre-push-quality-gate' not in steps
        assert 'pre-submission-self-review' not in steps


# =============================================================================
# Test: Bot-enforcement guard
# =============================================================================


class TestBotEnforcementGuard:
    """Composition-time guard remediates `automated-review` for GitHub/GitLab when missing.

    Lesson 2026-04-28-10-001 converted the guard from assertion to remediation.
    On GitHub/GitLab plans where `automated-review` is dropped (e.g., by a
    pre-filter or future row), the guard appends `default:automated-review`
    back into `phase_6.steps` and emits a `bot-enforcement guard remediated`
    decision-log line; composition continues normally — no error TOON. The
    `bot_enforcement_violation` error branch is retained as a safety net for
    non-remediable violations (currently unreachable).
    """

    def test_remediates_for_github_when_automated_review_missing(self, plan_context):
        _seed_marshal(ci_provider='github')
        _stub_footprint(['some/file.py'])

        # Compose a candidate set that EXCLUDES automated-review.
        phase_6 = ','.join(s for s in DEFAULT_PHASE_6_STEPS if s != 'automated-review')
        ns = _compose_ns(plan_id='qg-bot-github', phase_6_steps=phase_6)
        result = cmd_compose(ns)

        assert result is not None
        assert result['status'] == 'success'
        steps = result_phase_6_steps(result)
        # Guard appends `default:automated-review` (canonical prefixed form).
        bare_step_names = {s[len('default:') :] if s.startswith('default:') else s for s in steps}
        assert 'automated-review' in bare_step_names

    def test_remediates_for_gitlab_when_automated_review_missing(self, plan_context):
        _seed_marshal(ci_provider='gitlab')
        _stub_footprint(['some/file.py'])

        phase_6 = ','.join(s for s in DEFAULT_PHASE_6_STEPS if s != 'automated-review')
        ns = _compose_ns(plan_id='qg-bot-gitlab', phase_6_steps=phase_6)
        result = cmd_compose(ns)

        assert result is not None
        assert result['status'] == 'success'
        steps = result_phase_6_steps(result)
        bare_step_names = {s[len('default:') :] if s.startswith('default:') else s for s in steps}
        assert 'automated-review' in bare_step_names

    def test_no_op_when_automated_review_present(self, plan_context):
        _seed_marshal(ci_provider='github')
        _stub_footprint(['some/file.py'])

        ns = _compose_ns(plan_id='qg-bot-present')
        result = cmd_compose(ns)

        assert result is not None
        assert result['status'] == 'success'
        assert 'automated-review' in result_phase_6_steps(result)

    def test_no_op_for_non_github_non_gitlab(self, plan_context):
        _seed_marshal(ci_provider=None)
        _stub_footprint(['some/file.py'])

        phase_6 = ','.join(s for s in DEFAULT_PHASE_6_STEPS if s != 'automated-review')
        ns = _compose_ns(plan_id='qg-bot-other', phase_6_steps=phase_6)
        result = cmd_compose(ns)

        assert result is not None
        assert result['status'] == 'success'
        # No CI provider configured → guard is a no-op; automated-review
        # stays dropped and no error is raised.
        assert 'automated-review' not in result_phase_6_steps(result)


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
    from file_ops import get_plan_dir  # type: ignore[import-not-found]

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
