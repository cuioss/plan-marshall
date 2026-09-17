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

def test_matches_build_profile_tokens():
    # Arrange / Act / Assert
    assert _matches_build_profile('verify / verify') is True
    assert _matches_build_profile('Quality-Gate') is True
    assert _matches_build_profile('module-tests') is True
    assert _matches_build_profile('coverage') is True
    assert _matches_build_profile('license/cla') is False
    assert _matches_build_profile('') is False


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


def test_ci_verify_positioned_between_create_pr_and_automated_review():
    manifest_mod = _load_manifest_module('manage_execution_manifest_test2')
    steps = list(manifest_mod.DEFAULT_PHASE_6_STEPS)
    create_pr_idx = steps.index('create-pr')
    ci_verify_idx = steps.index('ci-verify')
    automated_review_idx = steps.index('automatic-review')
    assert create_pr_idx < ci_verify_idx < automated_review_idx, (
        f'ci-verify must sit between create-pr ({create_pr_idx}) and '
        f'automatic-review ({automated_review_idx}); got ci-verify at '
        f'{ci_verify_idx}'
    )


def test_ci_verify_declares_head_dependent_frontmatter_fact():
    """Membership is declared on ci-verify's own doc, not listed in SKILL.md.

    This replaces the former assertion against the hand-maintained
    ``HEAD_DEPENDENT_STEPS`` literal. Reading the declaration off the step's own
    authoritative doc is what makes the set derived: a step that IS
    head-dependent can no longer be head-dependent-in-fact but absent-from-the-list.
    """
    content = _STANDARDS_PATH.read_text(encoding='utf-8')
    assert re.search(r'^head_dependent:\s*true\s*$', content, re.MULTILINE), (
        'standards/ci-verify.md must declare head_dependent: true in frontmatter '
        'so loop-back commits re-fire the step against the new HEAD. The fact IS '
        'the membership declaration — there is no list to be added to.'
    )


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
        assert producer in content, f'Standards file must enumerate producer string {producer}'


def test_standards_references_consume_failures_mode():
    """The ci-verify contract documents the ``consume-failures`` precondition
    mode so future readers understand the contract.
    """
    content = _STANDARDS_PATH.read_text(encoding='utf-8')
    assert 'consume-failures' in content, 'ci-verify standards must document the consume-failures precondition mode'
