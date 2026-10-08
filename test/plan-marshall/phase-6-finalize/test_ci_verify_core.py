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
  no findings). ``step_marked_done`` is read off the mark's own result: ``True``
  when it returned success, ``False`` with ``outcome == green_unrecorded`` when
  it was refused.
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
    """Record every mark-step-done call; return the configured envelope.

    Defaults to a success envelope. Pass ``result`` to stand in for a mark the
    handler refused.
    """

    def __init__(self, result: dict | None = None) -> None:
        self.result = result if result is not None else {'status': 'success'}
        self.calls: list[dict] = []

    def __call__(self, **kwargs) -> dict:
        self.calls.append(kwargs)
        return self.result


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
                    {'name': 'lint', 'conclusion': 'FAILURE'},
                ],
            }
        ),
        git_head_resolver=_StubGitHead('abc'),
        mode='consume-failures',
    )
    # A check has definitively failed beside the lapse, so this is the
    # timeout the executor consumes, not the wait_pending verdict.
    assert result['status'] == 'wait_failed'
    assert result['ci_final_status'] == 'timeout'
    assert result['wait_outcome'] == 'deadline_exceeded'
    assert result['mode'] == 'consume-failures'


# ---------------------------------------------------------------------------
# deadline_exceeded — a still-running check beside a real failure files nothing
# ---------------------------------------------------------------------------


def _verify_deadline(tmp_path, plan_id: str, failing_checks: list[dict] | None, envelope: dict | None = None):
    """Run the executor on a ``deadline_exceeded`` timeout and return (result, findings)."""
    findings = _StubFindings()
    result = verify(
        plan_id=plan_id,
        pr_number=_PR,
        worktree_path=str(tmp_path),
        provider='github',
        final_status='timeout',
        wait_outcome='deadline_exceeded',
        head_sha=_HEAD_SHA,
        failing_checks=failing_checks,
        ci_status_runner=_StubCiStatus(envelope if envelope is not None else _green_envelope()),
        persist_runner=_StubPersist(),
        findings_runner=findings,
        mark_done_runner=_StubMarkDone(),
        git_head_resolver=_StubGitHead('x'),
    )
    return result, findings


def test_deadline_with_one_failed_and_one_running_check_files_one_finding(tmp_path):
    """The running check is dropped: only the check that failed is reported."""
    failing = [
        _make_check('verify', 'FAILURE', 'verify / verify'),
        _make_check('slow-deploy', 'IN_PROGRESS', 'deploy'),
    ]

    result, findings = _verify_deadline(tmp_path, 'ci-verify-deadline-failed-and-running', failing)

    assert result['outcome'] == 'needs_triage'
    assert result['findings_filed'] == 1
    assert result['producers'] == ['ci-verify-build']
    assert len(findings.calls) == 1
    assert findings.calls[0]['title'] == '[ci_build_failure] verify failed'


def test_deadline_with_a_timed_out_conclusion_still_files_ci_timeout(tmp_path):
    """A check whose own conclusion is timed_out is definitive and is kept."""
    failing = [
        _make_check('verify', 'TIMED_OUT', 'verify / verify'),
        _make_check('slow-deploy', 'PENDING', 'deploy'),
    ]

    result, findings = _verify_deadline(tmp_path, 'ci-verify-deadline-timed-out', failing)

    assert result['findings_filed'] == 1
    assert result['producers'] == ['ci-verify-timeout']
    assert [call['title'] for call in findings.calls] == ['[ci_timeout] verify failed']


def test_deadline_with_only_running_checks_files_ci_timeout_for_each(tmp_path):
    """The past-bound case: nothing has failed, so every running check is a ci_timeout."""
    failing = [
        _make_check('build', 'PENDING', 'verify / verify'),
        _make_check('slow-deploy', 'IN_PROGRESS', 'deploy'),
    ]

    result, findings = _verify_deadline(tmp_path, 'ci-verify-deadline-only-running', failing)

    assert result['findings_filed'] == 2
    assert result['producers'] == ['ci-verify-timeout']
    assert [call['title'] for call in findings.calls] == [
        '[ci_timeout] build failed',
        '[ci_timeout] slow-deploy failed',
    ]


def test_deadline_drops_running_checks_from_a_derived_failing_set(tmp_path):
    """The same rule holds when no failing set is threaded in and it is derived."""
    envelope = {
        'status': 'success',
        'checks': [
            {'name': 'verify', 'conclusion': 'failure', 'workflow': 'verify / verify', 'url': _RUN_URL},
            {'name': 'slow-deploy', 'conclusion': 'in_progress', 'workflow': 'deploy', 'url': _RUN_URL},
            {'name': 'unstarted', 'conclusion': '', 'workflow': 'deploy', 'url': _RUN_URL},
            {'name': 'lint', 'conclusion': 'success', 'workflow': 'lint', 'url': _RUN_URL},
        ],
    }

    result, findings = _verify_deadline(tmp_path, 'ci-verify-deadline-derived', None, envelope)

    assert result['findings_filed'] == 1
    assert [call['title'] for call in findings.calls] == ['[ci_build_failure] verify failed']


def test_completed_wait_does_not_drop_anything():
    """Matched control: the rule applies under deadline_exceeded only."""
    threaded = [
        _make_check('verify', 'failure', 'verify / verify'),
        _make_check('slow-deploy', 'pending', 'deploy'),
    ]

    kept = _resolve_failing_set(threaded=threaded, normalized_all=[], final_status='failure', wait_outcome='completed')

    assert [entry['name'] for entry in kept] == ['verify', 'slow-deploy']


def test_resolver_and_executor_agree_on_definitive_failing_conclusions():
    """The pending verdict and the drop rule read one set of conclusions."""
    assert _precond._DEFINITIVE_FAILING_CONCLUSIONS == _mod._DEFINITIVE_FAILING_CONCLUSIONS


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


# ---------------------------------------------------------------------------
# Green path — the mark's own result decides what is reported.
# ---------------------------------------------------------------------------

_CI_VERIFY_PHASE = '6-finalize'
_CI_VERIFY_STEP = 'ci-verify'


def _live_head_sha() -> str:
    """Resolve the live HEAD SHA — a real anchor for the persisted record.

    The production ``mark-step-done`` resolves a supplied
    ``--head-at-completion`` against the object store and refuses a fabricated
    SHA, so a test that drives the real handler must supply one the local repo
    actually holds.
    """
    import subprocess

    proc = subprocess.run(
        ['git', 'rev-parse', 'HEAD'],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert proc.returncode == 0, f'Cannot resolve a real HEAD SHA: {proc.stderr.strip()}'
    sha = proc.stdout.strip()
    assert sha
    return sha


def _mark_ci_verify(plan_id: str, outcome: str, detail: str, head: str | None = None) -> dict:
    """Record ``outcome`` on ci-verify through the real mark-step-done handler."""
    result: dict | None = _cmd_mark_step_done(
        Namespace(
            plan_id=plan_id,
            phase=_CI_VERIFY_PHASE,
            step=_CI_VERIFY_STEP,
            outcome=outcome,
            force=False,
            display_detail=detail,
            head_at_completion=head,
            loop_back_target='6-finalize' if outcome == 'loop_back' else None,
        )
    )
    assert result is not None, 'mark-step-done found no status file for the plan'
    return result


def _real_mark_done_runner(*, plan_id: str, display_detail: str, head_at_completion: str, worktree_path: str) -> dict:
    """Route the executor's green mark through the real handler, not a stub."""
    return _mark_ci_verify(plan_id, 'done', display_detail, head_at_completion)


def _stored_ci_verify_entry(plan_id: str) -> dict:
    entry: dict = _read_status(plan_id)['metadata']['phase_steps'][_CI_VERIFY_PHASE][_CI_VERIFY_STEP]
    return entry


def test_refused_mark_reports_green_unrecorded(tmp_path):
    """A green CI verdict whose mark was refused is not reported as recorded."""
    # Arrange — the mark seam returns the handler's conflict refusal.
    refusal_message = 'Step ci-verify already marked as skipped - use --force to overwrite with done'
    mark_done = _StubMarkDone({'status': 'error', 'error': 'conflict', 'message': refusal_message})
    findings = _StubFindings()

    # Act
    result = verify(
        plan_id='ci-verify-refused-mark',
        pr_number=_PR,
        worktree_path=str(tmp_path),
        provider='github',
        final_status='success',
        wait_outcome='completed',
        head_sha=_HEAD_SHA,
        ci_status_runner=_StubCiStatus(_green_envelope()),
        persist_runner=_StubPersist(),
        findings_runner=findings,
        mark_done_runner=mark_done,
        git_head_resolver=_StubGitHead('deadbeef'),
    )

    # Assert — the mark WAS attempted, and its refusal is what gets reported.
    assert len(mark_done.calls) == 1
    assert result['status'] == 'success'
    assert result['final_status'] == 'success'
    assert result['outcome'] == 'green_unrecorded'
    assert result['step_marked_done'] is False
    assert result['step_mark_error'] == 'conflict'
    assert result['step_mark_message'] == refusal_message
    # A refused mark is not a red CI run: nothing is filed and nothing routes to triage.
    assert result['findings_filed'] == 0
    assert 'producers' not in result
    assert len(findings.calls) == 0


def test_recorded_mark_carries_no_mark_error_fields(tmp_path):
    """The refusal fields ride ``green_unrecorded`` alone, never a recorded green."""
    # Arrange / Act
    result = verify(
        plan_id='ci-verify-recorded-mark',
        pr_number=_PR,
        worktree_path=str(tmp_path),
        provider='github',
        final_status='success',
        wait_outcome='completed',
        head_sha=_HEAD_SHA,
        ci_status_runner=_StubCiStatus(_green_envelope()),
        persist_runner=_StubPersist(),
        findings_runner=_StubFindings(),
        mark_done_runner=_StubMarkDone(),
        git_head_resolver=_StubGitHead('deadbeef'),
    )

    # Assert
    assert result['outcome'] == 'green'
    assert result['step_marked_done'] is True
    assert 'step_mark_error' not in result
    assert 'step_mark_message' not in result


def test_green_run_records_done_over_a_stored_loop_back(tmp_path):
    """End to end: a stored ``loop_back`` record reads ``done`` after a green run.

    The mark is driven through the real ``mark-step-done`` handler against a real
    status file, so ``step_marked_done`` is checked against the record itself
    rather than against a stub's say-so.
    """
    # Arrange — ci-verify looped back on an earlier red run.
    plan_id = 'ci-verify-loop-back-to-done'
    _make_ci_verify_plan(plan_id)
    _mark_ci_verify(plan_id, 'loop_back', 'CI red, fix pushed')
    assert _stored_ci_verify_entry(plan_id)['outcome'] == 'loop_back'
    live_head = _live_head_sha()

    # Act — the re-fired step sees green CI.
    result = verify(
        plan_id=plan_id,
        pr_number=_PR,
        worktree_path=str(tmp_path),
        provider='github',
        final_status='success',
        wait_outcome='completed',
        head_sha=_HEAD_SHA,
        ci_status_runner=_StubCiStatus(_green_envelope()),
        persist_runner=_StubPersist(),
        findings_runner=_StubFindings(),
        mark_done_runner=_real_mark_done_runner,
        git_head_resolver=_StubGitHead(live_head),
    )

    # Assert — the reported write and the stored record agree.
    assert result['outcome'] == 'green'
    assert result['step_marked_done'] is True
    assert 'step_mark_error' not in result

    entry = _stored_ci_verify_entry(plan_id)
    assert entry['outcome'] == 'done'
    assert entry['head_at_completion'] == live_head
    assert entry['firing_count'] == 2
    assert entry['prior_firings'] == [{'outcome': 'loop_back', 'loop_back_target': '6-finalize'}]


def test_refused_real_mark_leaves_the_stored_record_untouched(tmp_path):
    """End to end, negative control: a real refusal is reported and writes nothing."""
    # Arrange — ci-verify is recorded `skipped`; `skipped` to `done` is a conflict.
    plan_id = 'ci-verify-skipped-refuses-done'
    _make_ci_verify_plan(plan_id)
    _mark_ci_verify(plan_id, 'skipped', 'no PR to verify')
    stored_before = json.dumps(_stored_ci_verify_entry(plan_id), sort_keys=True)

    # Act
    result = verify(
        plan_id=plan_id,
        pr_number=_PR,
        worktree_path=str(tmp_path),
        provider='github',
        final_status='success',
        wait_outcome='completed',
        head_sha=_HEAD_SHA,
        ci_status_runner=_StubCiStatus(_green_envelope()),
        persist_runner=_StubPersist(),
        findings_runner=_StubFindings(),
        mark_done_runner=_real_mark_done_runner,
        git_head_resolver=_StubGitHead(_live_head_sha()),
    )

    # Assert — the handler's own error and message surface verbatim.
    assert result['outcome'] == 'green_unrecorded'
    assert result['step_marked_done'] is False
    assert result['step_mark_error'] == 'conflict'
    assert 'already marked as' in result['step_mark_message']
    assert json.dumps(_stored_ci_verify_entry(plan_id), sort_keys=True) == stored_before
