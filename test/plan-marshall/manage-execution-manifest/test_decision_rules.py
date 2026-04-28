#!/usr/bin/env python3
"""Tests for the pre_submission_self_review_inactive pre-filter and bot-enforcement guard."""

import importlib.util
import json
from argparse import Namespace
from pathlib import Path

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
_mem._log_bundle_self_modification = lambda *a, **kw: None  # type: ignore[attr-defined]


# =============================================================================
# Helpers
# =============================================================================


def _phase_6_with_self_review() -> str:
    """Return the comma-separated default phase-6 steps with pre-submission-self-review added."""
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
    """Write a minimal marshal.json at PLAN_BASE_DIR/marshal.json for the test."""
    from file_ops import get_marshal_path  # type: ignore[import-not-found]

    marshal: dict = {
        'plan': {
            'phase-6-finalize': {
                'pre_push_quality_gate': {'activation_globs': ['**/*.py']},
            }
        },
    }
    if ci_provider:
        marshal['ci'] = {'provider': ci_provider}
    marshal_path = get_marshal_path()
    marshal_path.parent.mkdir(parents=True, exist_ok=True)
    marshal_path.write_text(json.dumps(marshal, indent=2))
    return marshal_path


def _seed_references(plan_id: str, modified_files: list[str]) -> None:
    """Write a minimal references.json with the given modified_files for the plan."""
    from file_ops import get_plan_dir  # type: ignore[import-not-found]

    plan_dir = get_plan_dir(plan_id)
    plan_dir.mkdir(parents=True, exist_ok=True)
    refs_path = plan_dir / 'references.json'
    refs_path.write_text(json.dumps({'modified_files': modified_files}, indent=2))


# =============================================================================
# Test: pre_submission_self_review_inactive pre-filter
# =============================================================================


class TestPreSubmissionSelfReviewInactive:
    """Pre-filter drops the step when modified_files is empty; no-op otherwise."""

    def test_drops_step_when_modified_files_empty(self):
        with PlanContext('qg-self-review-empty'):
            _seed_marshal(ci_provider=None)
            _seed_references('qg-self-review-empty', [])

            ns = _compose_ns(plan_id='qg-self-review-empty')
            result = cmd_compose(ns)

            assert result is not None
            assert result['status'] == 'success'
            assert result['pre_submission_self_review_omitted'] is True
            assert 'pre-submission-self-review' not in result_phase_6_steps(result)

    def test_keeps_step_when_modified_files_non_empty(self):
        with PlanContext('qg-self-review-active'):
            _seed_marshal(ci_provider=None)
            _seed_references('qg-self-review-active', ['marketplace/bundles/x/skills/y/SKILL.md'])

            ns = _compose_ns(plan_id='qg-self-review-active')
            result = cmd_compose(ns)

            assert result is not None
            assert result['status'] == 'success'
            assert result['pre_submission_self_review_omitted'] is False
            assert 'pre-submission-self-review' in result_phase_6_steps(result)

    def test_commit_strategy_none_strips_self_review(self):
        with PlanContext('qg-self-review-no-push'):
            _seed_marshal(ci_provider=None)
            _seed_references('qg-self-review-no-push', ['some/file.py'])

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

    def test_remediates_for_github_when_automated_review_missing(self):
        with PlanContext('qg-bot-github'):
            _seed_marshal(ci_provider='github')
            _seed_references('qg-bot-github', ['some/file.py'])

            # Compose a candidate set that EXCLUDES automated-review.
            phase_6 = ','.join(s for s in DEFAULT_PHASE_6_STEPS if s != 'automated-review')
            ns = _compose_ns(plan_id='qg-bot-github', phase_6_steps=phase_6)
            result = cmd_compose(ns)

            assert result is not None
            assert result['status'] == 'success'
            steps = result_phase_6_steps(result)
            # Guard appends `default:automated-review` (canonical prefixed form).
            bare_step_names = {
                s[len('default:'):] if s.startswith('default:') else s
                for s in steps
            }
            assert 'automated-review' in bare_step_names

    def test_remediates_for_gitlab_when_automated_review_missing(self):
        with PlanContext('qg-bot-gitlab'):
            _seed_marshal(ci_provider='gitlab')
            _seed_references('qg-bot-gitlab', ['some/file.py'])

            phase_6 = ','.join(s for s in DEFAULT_PHASE_6_STEPS if s != 'automated-review')
            ns = _compose_ns(plan_id='qg-bot-gitlab', phase_6_steps=phase_6)
            result = cmd_compose(ns)

            assert result is not None
            assert result['status'] == 'success'
            steps = result_phase_6_steps(result)
            bare_step_names = {
                s[len('default:'):] if s.startswith('default:') else s
                for s in steps
            }
            assert 'automated-review' in bare_step_names

    def test_no_op_when_automated_review_present(self):
        with PlanContext('qg-bot-present'):
            _seed_marshal(ci_provider='github')
            _seed_references('qg-bot-present', ['some/file.py'])

            ns = _compose_ns(plan_id='qg-bot-present')
            result = cmd_compose(ns)

            assert result is not None
            assert result['status'] == 'success'
            assert 'automated-review' in result_phase_6_steps(result)

    def test_no_op_for_non_github_non_gitlab(self):
        with PlanContext('qg-bot-other'):
            _seed_marshal(ci_provider=None)
            _seed_references('qg-bot-other', ['some/file.py'])

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
