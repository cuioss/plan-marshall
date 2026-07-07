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
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Module loading — load the executor from source via importlib so the Python
# seams can be injected at the call level without spawning a subprocess.
# ---------------------------------------------------------------------------

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'phase-6-finalize'
    / 'scripts'
)


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_mod = _load_module('ci_verify', 'ci_verify.py')
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


def test_classify_check_failure_precedes_deadline_exceeded():
    """A concluded build failure stays a build failure even under a wait deadline."""
    # Arrange
    check = {'conclusion': 'failure', 'workflow_name': 'verify'}
    # Act
    result = classify_check(check, 'deadline_exceeded')
    # Assert — failure row is evaluated before the timeout row.
    assert result == ('ci-verify-build', 'ci_build_failure')


def test_matches_build_profile_tokens():
    # Arrange / Act / Assert
    assert _matches_build_profile('verify / verify') is True
    assert _matches_build_profile('Quality-Gate') is True
    assert _matches_build_profile('module-tests') is True
    assert _matches_build_profile('coverage') is True
    assert _matches_build_profile('license/cla') is False
    assert _matches_build_profile('') is False


# ---------------------------------------------------------------------------
# run_id derivation.
# ---------------------------------------------------------------------------


def test_extract_run_id_from_url():
    # Arrange / Act / Assert
    assert _extract_run_id_from_url(_RUN_URL) == '987654'
    assert _extract_run_id_from_url('https://gitlab.com/o/r/-/pipelines/5') == ''
    assert _extract_run_id_from_url('') == ''
    assert _extract_run_id_from_url(None) == ''


def test_normalize_check_entry_accepts_compact_shape():
    # Arrange — the compact ``ci checks status`` row shape.
    row = {'name': 'verify', 'status': 'FAILURE', 'url': _RUN_URL, 'workflow': 'verify / verify'}
    # Act
    normalized = _normalize_check_entry(row)
    # Assert
    assert normalized['name'] == 'verify'
    assert normalized['conclusion'] == 'FAILURE'
    assert normalized['workflow_name'] == 'verify / verify'
    assert normalized['run_id'] == '987654'


# ---------------------------------------------------------------------------
# Green partition — zero dispatch, mark-step-done, no findings.
# ---------------------------------------------------------------------------


def test_green_marks_done_no_findings(tmp_path):
    # Arrange
    ci = _StubCiStatus(_green_envelope())
    persist = _StubPersist()
    findings = _StubFindings()
    mark_done = _StubMarkDone()
    git_head = _StubGitHead('deadbeef')

    # Act
    result = verify(
        plan_id='ci-verify-green',
        pr_number=_PR,
        worktree_path=str(tmp_path),
        provider='github',
        final_status='success',
        wait_outcome='completed',
        head_sha=_HEAD_SHA,
        ci_status_runner=ci,
        persist_runner=persist,
        findings_runner=findings,
        mark_done_runner=mark_done,
        git_head_resolver=git_head,
    )

    # Assert
    assert result['outcome'] == 'green'
    assert result['step_marked_done'] is True
    assert result['findings_filed'] == 0
    assert 'producers' not in result
    assert len(mark_done.calls) == 1
    assert mark_done.calls[0]['head_at_completion'] == 'deadbeef'
    assert len(findings.calls) == 0
    # Persist ran (all required fields present) with the run_id from the check URL.
    assert result['run_id'] == '987654'
    assert result['persisted'] is True
    assert len(persist.calls) == 1


# ---------------------------------------------------------------------------
# Required-field guard — empty head_sha skips persist entirely.
# ---------------------------------------------------------------------------


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


def test_required_field_guard_skips_persist_on_empty_run_id(tmp_path):
    # Arrange — a check with a non-GitHub URL yields no run_id.
    envelope = {
        'status': 'success',
        'overall_status': 'success',
        'checks': [
            {'name': 'verify', 'status': 'SUCCESS', 'url': 'https://gitlab/x', 'workflow': 'verify'}
        ],
    }
    persist = _StubPersist()

    # Act
    result = verify(
        plan_id='ci-verify-guard-runid',
        pr_number=_PR,
        worktree_path=str(tmp_path),
        provider='github',
        final_status='success',
        wait_outcome='completed',
        head_sha=_HEAD_SHA,
        ci_status_runner=_StubCiStatus(envelope),
        persist_runner=persist,
        findings_runner=_StubFindings(),
        mark_done_runner=_StubMarkDone(),
        git_head_resolver=_StubGitHead('x'),
    )

    # Assert
    assert result['run_id'] == ''
    assert result['persisted'] is False
    assert result['persist_skipped_reason'] == 'run_id'
    assert len(persist.calls) == 0


# ---------------------------------------------------------------------------
# --wait-outcome enum constraint — never a copy of --final-status.
# ---------------------------------------------------------------------------


def test_wait_outcome_out_of_enum_clamps_to_completed(tmp_path):
    # Arrange — pass an illegal wait_outcome mirroring a final-status value.
    ci = _StubCiStatus(_green_envelope())
    persist = _StubPersist()

    # Act
    result = verify(
        plan_id='ci-verify-enum',
        pr_number=_PR,
        worktree_path=str(tmp_path),
        provider='github',
        final_status='success',
        wait_outcome='success',  # illegal — must NOT be forwarded verbatim
        head_sha=_HEAD_SHA,
        ci_status_runner=ci,
        persist_runner=persist,
        findings_runner=_StubFindings(),
        mark_done_runner=_StubMarkDone(),
        git_head_resolver=_StubGitHead('x'),
    )

    # Assert — persist received a legal enum value, not the final_status copy.
    assert result['persisted'] is True
    assert len(persist.calls) == 1
    assert persist.calls[0]['wait_outcome'] == 'completed'
    assert persist.calls[0]['wait_outcome'] != persist.calls[0]['final_status']


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


# ---------------------------------------------------------------------------
# No-checks partition — exactly one ci_no_checks finding.
# ---------------------------------------------------------------------------


def test_no_checks_files_single_ci_no_checks_finding(tmp_path):
    # Arrange — an envelope with zero checks.
    envelope = {'status': 'success', 'overall_status': 'none', 'checks': []}
    findings = _StubFindings()
    mark_done = _StubMarkDone()

    # Act
    result = verify(
        plan_id='ci-verify-nochecks',
        pr_number=_PR,
        worktree_path=str(tmp_path),
        provider='github',
        final_status='none',
        wait_outcome='completed',
        head_sha=_HEAD_SHA,
        ci_status_runner=_StubCiStatus(envelope),
        persist_runner=_StubPersist(),
        findings_runner=findings,
        mark_done_runner=mark_done,
        git_head_resolver=_StubGitHead('x'),
    )

    # Assert
    assert result['outcome'] == 'needs_triage'
    assert result['step_marked_done'] is False
    assert result['findings_filed'] == 1
    assert result['producers'] == ['ci-verify-missing']
    assert len(findings.calls) == 1
    assert '[ci_no_checks]' in findings.calls[0]['title']
    # No dispatch and no green mark-done on the red path.
    assert len(mark_done.calls) == 0


# ---------------------------------------------------------------------------
# Failure partition — one finding per failing check; producer aggregation.
# ---------------------------------------------------------------------------


def test_failure_files_one_finding_per_check(tmp_path):
    # Arrange — three failing checks, threaded as rich entries.
    failing = [
        _make_check('verify', 'failure', 'verify / verify'),
        _make_check('module-tests', 'failure', 'module-tests'),
        _make_check('codeql', 'failure', 'codeql'),
    ]
    findings = _StubFindings()

    # Act
    result = verify(
        plan_id='ci-verify-fail-many',
        pr_number=_PR,
        worktree_path=str(tmp_path),
        provider='github',
        final_status='failure',
        wait_outcome='completed',
        head_sha=_HEAD_SHA,
        failing_checks=failing,
        ci_status_runner=_StubCiStatus(_green_envelope()),
        persist_runner=_StubPersist(),
        findings_runner=findings,
        mark_done_runner=_StubMarkDone(),
        git_head_resolver=_StubGitHead('x'),
    )

    # Assert — exactly one finding per failing check.
    assert result['findings_filed'] == 3
    assert len(findings.calls) == 3
    # Two producers: build (verify + module-tests) and policy (codeql), deduped.
    assert set(result['producers']) == {'ci-verify-build', 'ci-verify-policy'}
    assert result['outcome'] == 'needs_triage'
    assert result['step_marked_done'] is False


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


def test_failure_set_derived_from_status_envelope_when_not_threaded(tmp_path):
    # Arrange — no threaded failing_checks; derive from the status envelope.
    envelope = {
        'status': 'success',
        'overall_status': 'failure',
        'checks': [
            {'name': 'verify', 'status': 'SUCCESS', 'url': _RUN_URL, 'workflow': 'verify'},
            {'name': 'lint', 'status': 'FAILURE', 'url': _RUN_URL, 'workflow': 'lint'},
        ],
    }
    findings = _StubFindings()

    # Act
    result = verify(
        plan_id='ci-verify-derive',
        pr_number=_PR,
        worktree_path=str(tmp_path),
        provider='github',
        final_status='failure',
        wait_outcome='completed',
        head_sha=_HEAD_SHA,
        failing_checks=None,
        ci_status_runner=_StubCiStatus(envelope),
        persist_runner=_StubPersist(),
        findings_runner=findings,
        mark_done_runner=_StubMarkDone(),
        git_head_resolver=_StubGitHead('x'),
    )

    # Assert — only the failing check (lint) produces a finding; the green
    # check is dropped from the failing set.
    assert result['findings_filed'] == 1
    assert result['producers'] == ['ci-verify-policy']


# ---------------------------------------------------------------------------
# Timeout partition — deadline_exceeded routes to the timeout producer.
# ---------------------------------------------------------------------------


def test_timeout_routes_to_timeout_producer(tmp_path):
    # Arrange — a still-pending check under a wait deadline.
    failing = [_make_check('verify', 'pending', 'verify')]
    findings = _StubFindings()

    # Act
    result = verify(
        plan_id='ci-verify-timeout',
        pr_number=_PR,
        worktree_path=str(tmp_path),
        provider='github',
        final_status='timeout',
        wait_outcome='deadline_exceeded',
        head_sha=_HEAD_SHA,
        failing_checks=failing,
        ci_status_runner=_StubCiStatus(_green_envelope()),
        persist_runner=_StubPersist(),
        findings_runner=findings,
        mark_done_runner=_StubMarkDone(),
        git_head_resolver=_StubGitHead('x'),
    )

    # Assert
    assert result['producers'] == ['ci-verify-timeout']
    assert result['findings_filed'] == 1
    assert '[ci_timeout]' in findings.calls[0]['title']


# ---------------------------------------------------------------------------
# Jobs-file capture — always written, including the green path.
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Fail-closed hardening (PR #849 review) — status_fn error short-circuit,
# malformed-checks guard, empty-conclusion fail-closed, '0' PR-number catch.
# ---------------------------------------------------------------------------


def test_status_fn_error_envelope_short_circuits_to_empty_checks(tmp_path):
    """A status_fn error envelope yields an empty checks set, not a crash.

    The green/red partition still runs off the threaded inputs; the error
    envelope's missing 'checks' key is never read as if it were zero checks.
    """
    # Arrange — status_fn returns a synthetic error dict (its own boundary).
    ci = _StubCiStatus({'status': 'error', 'error': 'subprocess failed: boom'})
    findings = _StubFindings()

    # Act — a threaded failing check drives the failure partition.
    result = verify(
        plan_id='ci-verify-status-error',
        pr_number=_PR,
        worktree_path=str(tmp_path),
        provider='github',
        final_status='failure',
        wait_outcome='completed',
        head_sha=_HEAD_SHA,
        failing_checks=[_make_check('verify', 'failure', 'verify')],
        ci_status_runner=ci,
        persist_runner=_StubPersist(),
        findings_runner=findings,
        mark_done_runner=_StubMarkDone(),
        git_head_resolver=_StubGitHead('x'),
    )

    # Assert — the error envelope did not crash; the threaded check classified.
    assert result['status'] == 'success'
    assert result['findings_filed'] == 1
    assert result['producers'] == ['ci-verify-build']
    # run_id is empty because the error envelope carried no usable checks.
    assert result['run_id'] == ''


def test_malformed_checks_structure_returns_structured_error(tmp_path):
    """A non-dict element in checks[] surfaces as status:error, not a traceback."""
    # Arrange — a corrupt checks array carrying a bare string element.
    envelope = {'status': 'success', 'overall_status': 'failure', 'checks': ['not-a-dict']}

    # Act
    result = verify(
        plan_id='ci-verify-malformed',
        pr_number=_PR,
        worktree_path=str(tmp_path),
        provider='github',
        final_status='failure',
        wait_outcome='completed',
        head_sha=_HEAD_SHA,
        ci_status_runner=_StubCiStatus(envelope),
        persist_runner=_StubPersist(),
        findings_runner=_StubFindings(),
        mark_done_runner=_StubMarkDone(),
        git_head_resolver=_StubGitHead('x'),
    )

    # Assert
    assert result['status'] == 'error'
    assert 'Malformed checks structure' in result['error']
    assert result['plan_id'] == 'ci-verify-malformed'


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


def test_first_missing_required_field_catches_zero_pr_number():
    """Both the int 0 and the string '0' PR number are caught as missing."""
    # Arrange / Act / Assert — int 0 (falsy).
    assert (
        _first_missing_required_field(
            plan_id='p', run_id='r', head_sha='h', pr_number=0, provider='github'
        )
        == 'pr_number'
    )
    # String '0' (truthy) — must ALSO be caught.
    assert (
        _first_missing_required_field(
            plan_id='p', run_id='r', head_sha='h', pr_number='0', provider='github'
        )
        == 'pr_number'
    )
    # A legitimate PR number passes the guard (returns None).
    assert (
        _first_missing_required_field(
            plan_id='p', run_id='r', head_sha='h', pr_number=123, provider='github'
        )
        is None
    )


def test_persist_non_success_marks_not_persisted(tmp_path):
    """A persist runner returning non-success sets persisted False + reason."""
    # Arrange — persist returns a failure envelope.
    persist = _StubPersist(status='error')

    # Act
    result = verify(
        plan_id='ci-verify-persist-fail',
        pr_number=_PR,
        worktree_path=str(tmp_path),
        provider='github',
        final_status='success',
        wait_outcome='completed',
        head_sha=_HEAD_SHA,
        ci_status_runner=_StubCiStatus(_green_envelope()),
        persist_runner=persist,
        findings_runner=_StubFindings(),
        mark_done_runner=_StubMarkDone(),
        git_head_resolver=_StubGitHead('x'),
    )

    # Assert
    assert result['persisted'] is False
    assert result['persist_skipped_reason'] == 'persist_failed'


# ---------------------------------------------------------------------------
# CLI surface — the run subcommand parses the required argument set.
# ---------------------------------------------------------------------------


def test_build_parser_accepts_run_subcommand():
    # Arrange
    parser = _mod.build_parser()
    # Act
    args = parser.parse_args(
        [
            'run',
            '--plan-id', 'p',
            '--pr-number', '5',
            '--worktree-path', '/tmp/wt',
            '--provider', 'github',
            '--final-status', 'success',
            '--wait-outcome', 'completed',
        ]
    )
    # Assert
    assert args.plan_id == 'p'
    assert args.pr_number == 5
    assert args.provider == 'github'
    assert args.final_status == 'success'
    assert args.wait_outcome == 'completed'


def test_build_parser_rejects_illegal_wait_outcome():
    # Arrange
    parser = _mod.build_parser()
    # Act / Assert — argparse rejects an out-of-enum wait outcome at parse time.
    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                'run',
                '--plan-id', 'p',
                '--pr-number', '5',
                '--worktree-path', '/tmp/wt',
                '--provider', 'github',
                '--final-status', 'failure',
                '--wait-outcome', 'failure',
            ]
        )
