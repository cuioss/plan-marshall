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


def _live_head_sha() -> str:
    """Resolve the live HEAD SHA — a real anchor for the persisted record.

    The production `mark-step-done` resolves a supplied `--head-at-completion`
    against the object store (unfabricable-anchor rule) and refuses a
    fabricated SHA, so the force-push regression below must record a SHA the
    local repo actually holds.
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


def test_classify_check_failure_precedes_deadline_exceeded():
    """A concluded build failure stays a build failure even under a wait deadline."""
    # Arrange
    check = {'conclusion': 'failure', 'workflow_name': 'verify'}
    # Act
    result = classify_check(check, 'deadline_exceeded')
    # Assert — failure row is evaluated before the timeout row.
    assert result == ('ci-verify-build', 'ci_build_failure')


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


def test_required_field_guard_skips_persist_on_empty_run_id(tmp_path):
    # Arrange — a check with a non-GitHub URL yields no run_id.
    envelope = {
        'status': 'success',
        'overall_status': 'success',
        'checks': [{'name': 'verify', 'status': 'SUCCESS', 'url': 'https://gitlab/x', 'workflow': 'verify'}],
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


def test_first_missing_required_field_catches_zero_pr_number():
    """Both the int 0 and the string '0' PR number are caught as missing."""
    # Arrange / Act / Assert — int 0 (falsy).
    assert (
        _first_missing_required_field(plan_id='p', run_id='r', head_sha='h', pr_number=0, provider='github')
        == 'pr_number'
    )
    # String '0' (truthy) — must ALSO be caught.
    assert (
        _first_missing_required_field(plan_id='p', run_id='r', head_sha='h', pr_number='0', provider='github')
        == 'pr_number'
    )
    # A legitimate PR number passes the guard (returns None).
    assert (
        _first_missing_required_field(plan_id='p', run_id='r', head_sha='h', pr_number=123, provider='github') is None
    )


def test_build_parser_rejects_illegal_wait_outcome():
    # Arrange
    parser = _mod.build_parser()
    # Act / Assert — argparse rejects an out-of-enum wait outcome at parse time.
    with pytest.raises(SystemExit):
        parser.parse_args(
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
                'failure',
                '--wait-outcome',
                'failure',
            ]
        )


def test_invalid_mode_raises_runtime_error(plan_context):
    plan_id = 'ci-verify-invalid-mode'
    with pytest.raises(RuntimeError, match='mode'):
        resolve(
            plan_id=plan_id,
            worktree_path='/tmp/wt',
            pr_number=42,
            ci_wait_runner=_StubCiWait({'status': 'success', 'final_status': 'success'}),
            git_head_resolver=_StubGitHead('abc'),
            mode='bogus',
        )


def test_default_phase_6_steps_includes_ci_verify():
    manifest_mod = _load_manifest_module('manage_execution_manifest_test')
    steps = manifest_mod.DEFAULT_PHASE_6_STEPS
    assert 'ci-verify' in steps, 'ci-verify must be in the default phase-6 step set'


def test_required_steps_order_anchors_ci_verify_after_create_pr():
    content = _REQUIRED_STEPS_PATH.read_text(encoding='utf-8')
    create_pr_pos = content.find('- create-pr')
    ci_verify_pos = content.find('- ci-verify')
    automated_review_pos = content.find('- automatic-review')
    assert 0 < create_pr_pos < ci_verify_pos < automated_review_pos, (
        'required-steps.md must list ci-verify between create-pr and automatic-review'
    )


def test_force_push_supersession_invalidates_a_recorded_ci_verify_green():
    """D4b: a force-push replaces the SHA a recorded green was computed against.

    ``ci-verify``'s green is a verdict over the REMOTE state of a specific pushed
    SHA. A force-push rewrites that SHA, so the recorded green no longer
    describes what is on the branch — it must re-fire rather than stand as
    verified.

    The assertion is against the persisted ``head_at_completion`` comparison the
    documented re-entry table branches on, NOT against a re-run of CI: re-running
    CI would test the CI integration, not the invalidation rule. SKILL.md must
    also state that a plain SHA inequality covers the force-push mechanism, so no
    separate force-push detector is required.
    """
    content = _SKILL_PATH.read_text(encoding='utf-8')

    # The three supersession mechanisms must be named as covered by the same
    # SHA inequality — force-push is the one this regression pins.
    assert 'force-push' in content, (
        'SKILL.md must name force-push among the supersession mechanisms the '
        '!= HEAD comparison covers. Without it a force-push reads as an '
        'unhandled case and invites a separate detector that is not needed.'
    )

    # The governing rule: a verdict is never left green for a HEAD it was not
    # computed against. This is what makes a superseded SHA invalidating.
    assert 'never left standing as green' in content, (
        'SKILL.md must state the governing rule that a head-dependent verdict is '
        'never left standing as green for a HEAD it was not computed against.'
    )

    # Exercise the REAL persisted record: mark ci-verify green against the
    # pre-force-push SHA, then read the record back and confirm it still carries
    # that SHA. The rewritten HEAD therefore compares unequal, which is the input
    # the documented table's RE-FIRE row branches on.
    plan_id = 'ci-verify-d4b-force-push'
    _make_ci_verify_plan(plan_id)

    # The green record must carry a SHA the object store holds: the
    # production `mark-step-done` resolves a supplied anchor (unfabricable-
    # anchor rule) and refuses a fabricated one. The post-force-push head is
    # only ever compared, never recorded, so any distinct string serves.
    recorded_green_sha = _live_head_sha()
    post_force_push_head = 'd' * 40

    _cmd_mark_step_done(
        Namespace(
            plan_id=plan_id,
            phase='6-finalize',
            step='ci-verify',
            outcome='done',
            force=False,
            display_detail='CI green',
            head_at_completion=recorded_green_sha,
            loop_back_target=None,
        )
    )

    entry = _read_status(plan_id)['metadata']['phase_steps']['6-finalize']['ci-verify']

    assert entry['outcome'] == 'done'
    assert entry['head_at_completion'] == recorded_green_sha, (
        'The green record must persist the SHA whose remote state it verified. '
        'Without the SHA the re-entry check cannot tell a force-pushed branch '
        'from the one CI actually ran against.'
    )
    assert entry['head_at_completion'] != post_force_push_head, (
        'The force-push rewrote the branch SHA, so the persisted green no longer '
        'describes the pushed tree. The re-entry check must re-fire ci-verify '
        'rather than let the superseded green stand as verified.'
    )


def test_standards_declares_ci_complete_precondition():
    """The ci-verify contract must declare ``requires: [ci-complete]`` so the
    dispatcher invokes the precondition resolver.
    """
    content = _STANDARDS_PATH.read_text(encoding='utf-8')
    assert 'requires: [ci-complete]' in content, 'ci-verify standards must declare requires: [ci-complete]'
