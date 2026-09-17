#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Unit tests for the deterministic ``ci-verify`` finalize-step executor.

The executor at ``scripts/ci_verify.py`` replaces the former dispatched
``workflow/ci-verify.md`` body with a pure-Python taxonomy classifier. These
tests pin the deliverable's Success Criteria via the injectable seams
(``ci_status_runner`` / ``persist_runner`` / ``findings_runner`` /
``mark_done_runner`` / ``git_head_resolver``) — no live CI, no live git, no
live plan state:

* Green CI returns ``done`` with zero LLM dispatch (``mark_done`` called,
  no findings, ``step_marked_done == True``).
* Each failing-check partition files exactly one taxonomy finding; the
  ``ci_no_checks`` finding is filed on ``final_status == none``.
* The required-field guard skips the persist call when any required flag is
  empty — the persist runner is NOT invoked.
* The ``--wait-outcome`` value passed to persist is always in the
  ``{completed, deadline_exceeded}`` enum and is NEVER a copy of
  ``--final-status``.
* One finding per failing check; per-producer signal aggregation dedupes
  the producer strings.

Each test uses a unique ``worktree_path`` (pytest ``tmp_path``) so the
``.plan/temp/`` jobs-file write is isolated.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys

import pytest

# ---------------------------------------------------------------------------
# Module loading — load the executor from source via importlib so the Python
# seams can be injected at the call level without spawning a subprocess.
# ---------------------------------------------------------------------------

from conftest import get_scripts_dir, load_script_module

_SCRIPTS_DIR = get_scripts_dir('plan-marshall', 'phase-6-finalize')


def _load_module(name: str, filename: str):
    return load_script_module('plan-marshall', 'phase-6-finalize', filename, name)


_mod = _load_module('ci_verify', 'ci_verify.py')

# manage-status seams for the D4b force-push regression, which asserts against
# the PERSISTED head_at_completion record rather than a re-run of CI.
from argparse import Namespace


_ci_verify_lifecycle = load_script_module('plan-marshall', 'manage-status', '_cmd_lifecycle.py', '_ci_verify_lifecycle')
_ci_verify_mark_step = load_script_module('plan-marshall', 'manage-status', '_cmd_mark_step.py', '_ci_verify_mark_step')
_ci_verify_status_core = load_script_module(
    'plan-marshall', 'manage-status', '_status_core.py', '_ci_verify_status_core'
)

_cmd_mark_step_done = _ci_verify_mark_step.cmd_mark_step_done
_read_status = _ci_verify_status_core.read_status


def _make_ci_verify_plan(plan_id: str) -> None:
    """Create an isolated plan for a persisted-record assertion."""
    _ci_verify_lifecycle.cmd_create(
        Namespace(
            plan_id=plan_id,
            title='ci-verify HEAD-dependence regression',
            phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
            force=False,
        )
    )


verify = _mod.verify
classify_check = _mod.classify_check
_extract_run_id_from_url = _mod._extract_run_id_from_url
_normalize_check_entry = _mod._normalize_check_entry
_matches_build_profile = _mod._matches_build_profile
_first_missing_required_field = _mod._first_missing_required_field
_resolve_failing_set = _mod._resolve_failing_set


# ---------------------------------------------------------------------------
# Test seams — deterministic stand-ins for each subprocess boundary.
# ---------------------------------------------------------------------------


class _StubCiStatus:
    """Return a canned ``ci checks status`` envelope; record calls."""

    def __init__(self, envelope: dict) -> None:
        self.envelope = envelope
        self.calls: list[tuple] = []

    def __call__(self, plan_id: str, pr_number: int, worktree_path: str) -> dict:
        self.calls.append((plan_id, pr_number, worktree_path))
        return self.envelope


class _StubPersist:
    """Record every persist call's kwargs; return a success envelope."""

    def __init__(self, status: str = 'success') -> None:
        self.status = status
        self.calls: list[dict] = []

    def __call__(self, **kwargs) -> dict:
        self.calls.append(kwargs)
        return {'status': self.status, 'manifest_path': 'artifacts/ci-runs/x/manifest.toon'}


class _StubFindings:
    """Record every finding filed; return a success envelope."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def __call__(self, **kwargs) -> dict:
        self.calls.append(kwargs)
        return {'status': 'success'}


class _StubMarkDone:
    """Record every mark-step-done call; return a success envelope."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def __call__(self, **kwargs) -> dict:
        self.calls.append(kwargs)
        return {'status': 'success'}


class _StubGitHead:
    """Deterministic ``git rev-parse HEAD`` substitute."""

    def __init__(self, sha: str) -> None:
        self.sha = sha
        self.calls: list[str] = []

    def __call__(self, worktree_path: str) -> str:
        self.calls.append(worktree_path)
        return self.sha


_HEAD_SHA = 'a' * 40
_PR = 123
_RUN_URL = 'https://github.com/o/r/actions/runs/987654/job/111'


def _green_envelope() -> dict:
    return {
        'status': 'success',
        'operation': 'ci_status',
        'overall_status': 'success',
        'check_count': 1,
        'checks': [
            {
                'name': 'verify',
                'status': 'SUCCESS',
                'result': 'pass',
                'url': _RUN_URL,
                'workflow': 'verify / verify',
            }
        ],
    }


def _make_check(name: str, conclusion: str, workflow: str, url: str = _RUN_URL) -> dict:
    """Build a rich failing-check entry (the threaded-envelope shape)."""
    return {
        'name': name,
        'conclusion': conclusion,
        'workflow_name': workflow,
        'job_name': name,
        'run_url': url,
        'run_id': _extract_run_id_from_url(url),
    }


# ---------------------------------------------------------------------------
# classify_check — pure taxonomy rows.
# ---------------------------------------------------------------------------


_SKILL_DIR = _SCRIPTS_DIR.parent

_STANDARDS_PATH = _SKILL_DIR / 'standards' / 'ci-verify.md'

_REQUIRED_STEPS_PATH = _SKILL_DIR / 'standards' / 'required-steps.md'

_SKILL_PATH = _SKILL_DIR / 'SKILL.md'

_CI_VERIFY_SCRIPT = _SCRIPTS_DIR / 'ci_verify.py'

_precond = _load_module('ci_complete_precondition_test', 'ci_complete_precondition.py')

resolve = _precond.resolve

def _load_manifest_module(name: str):
    """Load the manage-execution-manifest entry script.

    A sibling skill, so the module-local ``_load_module`` (which resolves
    against phase-6-finalize/scripts) cannot serve it — this one addresses the
    script by ``(bundle, skill, file)`` instead.

    Nothing is registered: the callers read only the returned object, and the
    name they pass is a variable, which no static guard can enumerate. Leaving
    it unregistered keeps the loader-contract guard's blind spot from widening.
    """
    return load_script_module(
        'plan-marshall', 'manage-execution-manifest', 'manage-execution-manifest.py', name, register=False
    )

class _StubCiWait:
    """Return a canned ``ci wait`` envelope."""

    def __init__(self, envelope: dict) -> None:
        self.envelope = envelope

    def __call__(self, *_args, **_kwargs) -> dict:
        return self.envelope

@pytest.mark.parametrize(
    ('conclusion', 'workflow', 'wait_outcome', 'expected'),
    [
        ('failure', 'verify / verify', 'completed', ('ci-verify-build', 'ci_build_failure')),
        ('failed', 'quality-gate', 'completed', ('ci-verify-build', 'ci_build_failure')),
        ('failure', 'license/cla', 'completed', ('ci-verify-policy', 'ci_policy_failure')),
        ('failure', 'codeql', 'completed', ('ci-verify-policy', 'ci_policy_failure')),
        ('timed_out', 'verify', 'completed', ('ci-verify-timeout', 'ci_timeout')),
        ('pending', 'verify', 'deadline_exceeded', ('ci-verify-timeout', 'ci_timeout')),
        ('cancelled', 'verify', 'completed', ('ci-verify-cancelled', 'ci_cancelled')),
        ('canceled', 'verify', 'completed', ('ci-verify-cancelled', 'ci_cancelled')),
        ('action_required', 'verify', 'completed', ('ci-verify-action-required', 'ci_action_required')),
        ('stale', 'verify', 'completed', ('ci-verify-stale', 'ci_stale')),
        ('some_unknown', 'verify', 'completed', ('ci-verify-policy', 'ci_policy_failure')),
        # A definitive cancelled/action_required/stale conclusion wins over the
        # run-level deadline_exceeded fallback — it must NOT be misrouted to the
        # timeout producer.
        ('cancelled', 'verify', 'deadline_exceeded', ('ci-verify-cancelled', 'ci_cancelled')),
        ('action_required', 'verify', 'deadline_exceeded', ('ci-verify-action-required', 'ci_action_required')),
        ('stale', 'verify', 'deadline_exceeded', ('ci-verify-stale', 'ci_stale')),
        # A build failure also stays a build failure under a wait deadline.
        ('failure', 'verify / verify', 'deadline_exceeded', ('ci-verify-build', 'ci_build_failure')),
        # Only a non-definitive (still-pending) conclusion falls through to the
        # timeout row under deadline_exceeded.
        ('pending', 'verify', 'deadline_exceeded', ('ci-verify-timeout', 'ci_timeout')),
    ],
)
def test_classify_check_taxonomy_rows(conclusion, workflow, wait_outcome, expected):
    # Arrange
    check = {'conclusion': conclusion, 'workflow_name': workflow}
    # Act
    result = classify_check(check, wait_outcome)
    # Assert
    assert result == expected


def test_extract_run_id_from_url():
    # Arrange / Act / Assert
    assert _extract_run_id_from_url(_RUN_URL) == '987654'
    assert _extract_run_id_from_url('https://gitlab.com/o/r/-/pipelines/5') == ''
    assert _extract_run_id_from_url('') == ''
    assert _extract_run_id_from_url(None) == ''


def test_required_field_guard_skips_persist_on_empty_head_sha(tmp_path):
    # Arrange — head_sha is empty.
    ci = _StubCiStatus(_green_envelope())
    persist = _StubPersist()
    mark_done = _StubMarkDone()

    # Act
    result = verify(
        plan_id='ci-verify-guard',
        pr_number=_PR,
        worktree_path=str(tmp_path),
        provider='github',
        final_status='success',
        wait_outcome='completed',
        head_sha='',
        ci_status_runner=ci,
        persist_runner=persist,
        findings_runner=_StubFindings(),
        mark_done_runner=mark_done,
        git_head_resolver=_StubGitHead('x'),
    )

    # Assert — persist NOT called; reason names the missing field.
    assert result['persisted'] is False
    assert result['persist_skipped_reason'] == 'head_sha'
    assert len(persist.calls) == 0


def test_wait_outcome_deadline_exceeded_is_forwarded(tmp_path):
    # Arrange
    persist = _StubPersist()

    # Act
    verify(
        plan_id='ci-verify-enum-deadline',
        pr_number=_PR,
        worktree_path=str(tmp_path),
        provider='github',
        final_status='timeout',
        wait_outcome='deadline_exceeded',
        head_sha=_HEAD_SHA,
        failing_checks=[_make_check('verify', 'pending', 'verify')],
        ci_status_runner=_StubCiStatus(_green_envelope()),
        persist_runner=persist,
        findings_runner=_StubFindings(),
        mark_done_runner=_StubMarkDone(),
        git_head_resolver=_StubGitHead('x'),
    )

    # Assert
    assert len(persist.calls) == 1
    assert persist.calls[0]['wait_outcome'] == 'deadline_exceeded'


def test_failure_producer_aggregation_dedupes(tmp_path):
    # Arrange — two build failures produce a single build producer entry.
    failing = [
        _make_check('verify', 'failure', 'verify'),
        _make_check('quality-gate', 'failure', 'quality-gate'),
    ]

    # Act
    result = verify(
        plan_id='ci-verify-dedupe',
        pr_number=_PR,
        worktree_path=str(tmp_path),
        provider='github',
        final_status='failure',
        wait_outcome='completed',
        head_sha=_HEAD_SHA,
        failing_checks=failing,
        ci_status_runner=_StubCiStatus(_green_envelope()),
        persist_runner=_StubPersist(),
        findings_runner=_StubFindings(),
        mark_done_runner=_StubMarkDone(),
        git_head_resolver=_StubGitHead('x'),
    )

    # Assert — the build producer appears exactly once.
    assert result['producers'] == ['ci-verify-build']
    assert result['findings_filed'] == 2


def test_jobs_file_written_with_normalized_checks(tmp_path):
    # Arrange
    ci = _StubCiStatus(_green_envelope())

    # Act
    verify(
        plan_id='ci-verify-jobsfile',
        pr_number=_PR,
        worktree_path=str(tmp_path),
        provider='github',
        final_status='success',
        wait_outcome='completed',
        head_sha=_HEAD_SHA,
        ci_status_runner=ci,
        persist_runner=_StubPersist(),
        findings_runner=_StubFindings(),
        mark_done_runner=_StubMarkDone(),
        git_head_resolver=_StubGitHead('x'),
    )

    # Assert — the jobs file exists under .plan/temp with the normalized array.
    jobs_file = tmp_path / '.plan' / 'temp' / 'ci-verify-jobsfile-ci-jobs-987654.json'
    assert jobs_file.is_file()
    # Path.is_file() follows symlinks — assert the materialized path is a real
    # regular file, not a leftover symlink pointing at a valid file.
    assert not jobs_file.is_symlink()
    payload = json.loads(jobs_file.read_text(encoding='utf-8'))
    assert isinstance(payload, list)
    assert payload[0]['workflow_name'] == 'verify / verify'
    assert payload[0]['run_url'] == _RUN_URL


def test_empty_conclusion_is_failing_on_completed_path():
    """An empty/unknown conclusion is NOT passing on the completed path."""
    # Arrange — a check whose conclusion is the empty string.
    normalized = [_normalize_check_entry({'name': 'mystery', 'conclusion': '', 'workflow': 'x'})]

    # Act — completed (non-deadline) path.
    failing = _resolve_failing_set(
        threaded=None,
        normalized_all=normalized,
        final_status='failure',
        wait_outcome='completed',
    )

    # Assert — the empty-conclusion check falls through to the failing set.
    assert len(failing) == 1
    assert failing[0]['name'] == 'mystery'
    # And it classifies to the fail-closed policy row.
    assert classify_check(failing[0], 'completed') == ('ci-verify-policy', 'ci_policy_failure')


def test_build_parser_accepts_run_subcommand():
    # Arrange
    parser = _mod.build_parser()
    # Act
    args = parser.parse_args(
        [
            'run',
            '--plan-id',
            'p',
            '--pr-number',
            '5',
            '--worktree-path',
            '/tmp/wt',
            '--provider',
            'github',
            '--final-status',
            'success',
            '--wait-outcome',
            'completed',
        ]
    )
    # Assert
    assert args.plan_id == 'p'
    assert args.pr_number == 5
    assert args.provider == 'github'
    assert args.final_status == 'success'
    assert args.wait_outcome == 'completed'


def test_strict_mode_default_still_works(plan_context):
    """Backwards compatibility: omitting ``mode`` defaults to strict and
    the return shape is unchanged for existing callers.
    """
    plan_id = 'ci-verify-strict-default'
    result = resolve(
        plan_id=plan_id,
        worktree_path='/tmp/wt',
        pr_number=42,
        ci_wait_runner=_StubCiWait({'status': 'success', 'final_status': 'success'}),
        git_head_resolver=_StubGitHead('abc12345'),
    )
    assert result['status'] == 'wait_succeeded'


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


def test_required_steps_lists_ci_verify():
    content = _REQUIRED_STEPS_PATH.read_text(encoding='utf-8')
    assert '- ci-verify' in content, 'required-steps.md must enumerate ci-verify'


def test_skill_md_consumes_the_derived_fact_and_drops_the_literal():
    """SKILL.md must consume the derived fact and carry no hand-maintained list."""
    content = _SKILL_PATH.read_text(encoding='utf-8')

    assert 'HEAD_DEPENDENT_STEPS' not in content, (
        'SKILL.md still carries the retired HEAD_DEPENDENT_STEPS literal. A '
        'surviving literal is a second source of truth that drifts from the '
        'per-step declarations — the defect this plan removed.'
    )
    assert 'head_dependent: true' in content, (
        'SKILL.md must name the derived head_dependent fact as the source of head-dependence membership.'
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
        assert subtype in content, f'Standards file must enumerate subtype tag {subtype}'


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
        'the persist seam must run before the classification loop so findings can reference persisted per-job log paths'
    )
