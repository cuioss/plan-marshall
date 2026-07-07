#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the ci-verify finalize step (lesson-2026-05-18-16-001 deliverable 6).

The step body is the deterministic executor
``marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/ci_verify.py``
(the former dispatched ``workflow/ci-verify.md`` body was retired), with the
contract codified in ``standards/ci-verify.md``. These tests cover the
deterministic, script-anchored parts of the contract:

1. The ``ci_complete_precondition`` ``consume-failures`` mode threads
   ``failing_checks`` and ``wait_outcome`` through without short-
   circuiting (the strict-mode tests in
   ``test_ci_complete_precondition.py`` cover the opposite behaviour).
2. The default manifest composer includes ``ci-verify`` between
   ``create-pr`` and ``automated-review``.
3. The phase-6-finalize required-steps list contains ``ci-verify`` at
   the canonical position.
4. The HEAD_DEPENDENT_STEPS membership for ``ci-verify`` is declared in
   SKILL.md so loop-back commits re-fire the step.
5. The standards file enumerates every taxonomy row.

The LLM-driven per-finding triage dispatches are covered indirectly
via the ``verification-feedback`` tests; this file pins the
structural contract that surrounds them.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Source anchors
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parent.parent.parent
_BUNDLE_ROOT = _REPO_ROOT / 'marketplace' / 'bundles' / 'plan-marshall'
_PRECOND_PATH = (
    _BUNDLE_ROOT
    / 'skills'
    / 'phase-6-finalize'
    / 'scripts'
    / 'ci_complete_precondition.py'
)
_MANIFEST_SCRIPT = (
    _BUNDLE_ROOT
    / 'skills'
    / 'manage-execution-manifest'
    / 'scripts'
    / 'manage-execution-manifest.py'
)
_CI_VERIFY_SCRIPT = (
    _BUNDLE_ROOT
    / 'skills'
    / 'phase-6-finalize'
    / 'scripts'
    / 'ci_verify.py'
)
_STANDARDS_PATH = (
    _BUNDLE_ROOT
    / 'skills'
    / 'phase-6-finalize'
    / 'standards'
    / 'ci-verify.md'
)
_REQUIRED_STEPS_PATH = (
    _BUNDLE_ROOT
    / 'skills'
    / 'phase-6-finalize'
    / 'standards'
    / 'required-steps.md'
)
_SKILL_PATH = (
    _BUNDLE_ROOT / 'skills' / 'phase-6-finalize' / 'SKILL.md'
)


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_precond = _load_module('ci_complete_precondition_test', _PRECOND_PATH)
resolve = _precond.resolve


# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------


class _StubGitHead:
    def __init__(self, sha: str) -> None:
        self.sha = sha

    def __call__(self, _wt: str) -> str:
        return self.sha


class _StubCiWait:
    def __init__(self, envelope: dict) -> None:
        self.envelope = envelope

    def __call__(self, *_args, **_kwargs) -> dict:
        return self.envelope


# ---------------------------------------------------------------------------
# 1. consume-failures mode contract
# ---------------------------------------------------------------------------


def test_consume_failures_mode_returns_wait_failed_with_envelope_intact(plan_context):
    """In ``consume-failures`` mode, a CI failure MUST surface as
    ``wait_failed`` with ``failing_checks`` / ``wait_outcome`` forwarded —
    the same shape ``strict`` mode returns. The dispatcher uses the
    ``mode`` field to decide whether to short-circuit the consumer
    step body.
    """
    plan_id = 'ci-verify-consume-failure'
    result = resolve(
        plan_id=plan_id,
        worktree_path='/tmp/wt',
        pr_number=42,
        ci_wait_runner=_StubCiWait(
            {
                'status': 'success',
                'final_status': 'failure',
                'failing_checks': [
                    {'name': 'lint', 'conclusion': 'FAILURE'},
                ],
                'wait_outcome': 'completed',
            }
        ),
        git_head_resolver=_StubGitHead('abc12345'),
        mode='consume-failures',
    )
    assert result['status'] == 'wait_failed'
    assert result['ci_final_status'] == 'failure'
    assert result['mode'] == 'consume-failures'
    assert [c['name'] for c in result['failing_checks']] == ['lint']
    assert result['wait_outcome'] == 'completed'


def test_strict_mode_default_still_works(plan_context):
    """Backwards compatibility: omitting ``mode`` defaults to strict and
    the return shape is unchanged for existing callers.
    """
    plan_id = 'ci-verify-strict-default'
    result = resolve(
        plan_id=plan_id,
        worktree_path='/tmp/wt',
        pr_number=42,
        ci_wait_runner=_StubCiWait(
            {'status': 'success', 'final_status': 'success'}
        ),
        git_head_resolver=_StubGitHead('abc12345'),
    )
    assert result['status'] == 'wait_succeeded'
    # ``mode`` is not surfaced on success returns — only on wait_failed.


def test_invalid_mode_raises_runtime_error(plan_context):
    plan_id = 'ci-verify-invalid-mode'
    try:
        resolve(
            plan_id=plan_id,
            worktree_path='/tmp/wt',
            pr_number=42,
            ci_wait_runner=_StubCiWait({'status': 'success', 'final_status': 'success'}),
            git_head_resolver=_StubGitHead('abc'),
            mode='bogus',
        )
    except RuntimeError as exc:
        assert 'mode' in str(exc)
    else:
        raise AssertionError('Expected RuntimeError for invalid mode')


def test_no_checks_returns_distinct_status_in_consume_failures_mode(plan_context):
    plan_id = 'ci-verify-no-checks-consume'
    result = resolve(
        plan_id=plan_id,
        worktree_path='/tmp/wt',
        pr_number=42,
        ci_wait_runner=_StubCiWait(
            {
                'status': 'success',
                'final_status': 'none',
                'failing_checks': [],
                'wait_outcome': 'completed',
            }
        ),
        git_head_resolver=_StubGitHead('abc'),
        mode='consume-failures',
    )
    assert result['ci_final_status'] == 'no_checks'
    assert result['mode'] == 'consume-failures'


def test_timeout_returns_deadline_exceeded_in_consume_failures_mode(plan_context):
    plan_id = 'ci-verify-timeout-consume'
    result = resolve(
        plan_id=plan_id,
        worktree_path='/tmp/wt',
        pr_number=42,
        ci_wait_runner=_StubCiWait(
            {
                'status': 'error',
                'error': 'Timeout waiting for CI',
                'last_status': 'pending',
                'wait_outcome': 'deadline_exceeded',
                'failing_checks': [
                    {'name': 'slow-deploy', 'conclusion': 'PENDING'},
                ],
            }
        ),
        git_head_resolver=_StubGitHead('abc'),
        mode='consume-failures',
    )
    assert result['status'] == 'wait_failed'
    assert result['ci_final_status'] == 'timeout'
    assert result['wait_outcome'] == 'deadline_exceeded'
    assert result['mode'] == 'consume-failures'


# ---------------------------------------------------------------------------
# 2. Default manifest composer includes ci-verify in the right position
# ---------------------------------------------------------------------------


def test_default_phase_6_steps_includes_ci_verify():
    manifest_mod = _load_module('manage_execution_manifest_test', _MANIFEST_SCRIPT)
    steps = manifest_mod.DEFAULT_PHASE_6_STEPS
    assert 'ci-verify' in steps, 'ci-verify must be in the default phase-6 step set'


def test_ci_verify_positioned_between_create_pr_and_automated_review():
    manifest_mod = _load_module('manage_execution_manifest_test2', _MANIFEST_SCRIPT)
    steps = list(manifest_mod.DEFAULT_PHASE_6_STEPS)
    create_pr_idx = steps.index('create-pr')
    ci_verify_idx = steps.index('ci-verify')
    automated_review_idx = steps.index('automated-review')
    assert create_pr_idx < ci_verify_idx < automated_review_idx, (
        f'ci-verify must sit between create-pr ({create_pr_idx}) and '
        f'automated-review ({automated_review_idx}); got ci-verify at '
        f'{ci_verify_idx}'
    )


# ---------------------------------------------------------------------------
# 3. required-steps.md anchors ci-verify
# ---------------------------------------------------------------------------


def test_required_steps_lists_ci_verify():
    content = _REQUIRED_STEPS_PATH.read_text(encoding='utf-8')
    assert '- ci-verify' in content, 'required-steps.md must enumerate ci-verify'


def test_required_steps_order_anchors_ci_verify_after_create_pr():
    content = _REQUIRED_STEPS_PATH.read_text(encoding='utf-8')
    create_pr_pos = content.find('- create-pr')
    ci_verify_pos = content.find('- ci-verify')
    automated_review_pos = content.find('- automated-review')
    assert (
        0 < create_pr_pos < ci_verify_pos < automated_review_pos
    ), 'required-steps.md must list ci-verify between create-pr and automated-review'


# ---------------------------------------------------------------------------
# 4. SKILL.md HEAD_DEPENDENT_STEPS includes ci-verify
# ---------------------------------------------------------------------------


def test_skill_md_declares_ci_verify_head_dependent():
    content = _SKILL_PATH.read_text(encoding='utf-8')
    # The HEAD_DEPENDENT_STEPS literal MUST name ci-verify.
    pattern = r'HEAD_DEPENDENT_STEPS\s*=\s*\{[^}]*"ci-verify"[^}]*\}'
    assert re.search(pattern, content), (
        'SKILL.md HEAD_DEPENDENT_STEPS must include "ci-verify" so loop-'
        'back commits re-fire the step against the new HEAD'
    )


# ---------------------------------------------------------------------------
# 5. Standards file enumerates every taxonomy producer string
# ---------------------------------------------------------------------------


def test_standards_enumerates_all_seven_producer_strings():
    content = _STANDARDS_PATH.read_text(encoding='utf-8')
    expected_producers = (
        'ci-verify-build',
        'ci-verify-policy',
        'ci-verify-timeout',
        'ci-verify-cancelled',
        'ci-verify-action-required',
        'ci-verify-stale',
        'ci-verify-missing',
    )
    for producer in expected_producers:
        assert producer in content, (
            f'Standards file must enumerate producer string {producer}'
        )


def test_standards_enumerates_all_seven_subtype_tags():
    content = _STANDARDS_PATH.read_text(encoding='utf-8')
    expected_subtypes = (
        'ci_build_failure',
        'ci_policy_failure',
        'ci_timeout',
        'ci_cancelled',
        'ci_action_required',
        'ci_stale',
        'ci_no_checks',
    )
    for subtype in expected_subtypes:
        assert subtype in content, (
            f'Standards file must enumerate subtype tag {subtype}'
        )


# ---------------------------------------------------------------------------
# 6. ci-verify contract declares the required precondition mode
#
# The former ``workflow/ci-verify.md`` dispatched body was retired: the
# execution logic now lives in the deterministic ``scripts/ci_verify.py``
# executor and the contract is codified in ``standards/ci-verify.md``. These
# tests assert the same guarantees against those new homes.
# ---------------------------------------------------------------------------


def test_standards_declares_ci_complete_precondition():
    """The ci-verify contract must declare ``requires: [ci-complete]`` so the
    dispatcher invokes the precondition resolver.
    """
    content = _STANDARDS_PATH.read_text(encoding='utf-8')
    assert 'requires: [ci-complete]' in content, (
        'ci-verify standards must declare requires: [ci-complete]'
    )


def test_standards_references_consume_failures_mode():
    """The ci-verify contract documents the ``consume-failures`` precondition
    mode so future readers understand the contract.
    """
    content = _STANDARDS_PATH.read_text(encoding='utf-8')
    assert 'consume-failures' in content, (
        'ci-verify standards must document the consume-failures '
        'precondition mode'
    )


def test_executor_persists_artifacts_before_classification():
    """The deterministic executor must invoke the ``manage-ci-artifacts``
    persist seam BEFORE the taxonomy classification loop so findings can
    reference per-job log paths.
    """
    content = _CI_VERIFY_SCRIPT.read_text(encoding='utf-8')
    # Anchor against the persist call site (``persist_fn(``) and the
    # classification CALL site (``classify_check(check, wait_outcome)``) —
    # NOT the ``def classify_check(check: dict, ...)`` definition, which is
    # declared earlier in the module — so the ordering check reflects the
    # executor's control flow, not source declaration order.
    persist_pos = content.find('persist_fn(')
    classify_pos = content.find('classify_check(check, wait_outcome)')
    assert persist_pos != -1, 'executor must call the persist seam'
    assert classify_pos != -1, 'executor must call classify_check on each check'
    assert persist_pos < classify_pos, (
        'the persist seam must run before the classification loop so findings '
        'can reference persisted per-job log paths'
    )
