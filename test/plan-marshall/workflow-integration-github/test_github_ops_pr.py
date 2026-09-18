# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for github_ops.py --head flag routing.

Verifies that branch-aware operations forward the --head value to gh and that
the --pr-number/--head dual-flag validation works as expected.
"""

import argparse

import ci_base
import github_ops
import gitlab_ops
import pytest
from _ci_wait_contract import _ok_auth
from _resolve_project_dir_fixtures import worktree_query_result

from conftest import MARKETPLACE_ROOT

_CORROBORATION_JSON_MARKER = 'mergedAt'
_CORROBORATED_MERGE_PAYLOAD = (
    '{"state": "MERGED", "mergedAt": "2026-01-01T00:00:00Z", "baseRefName": "main", "headRefOid": "abc123"}'
)


def _capture_run_gh():
    """Return a (run_gh_stub, captured_args_list) pair."""
    captured: list[list[str]] = []

    def run_gh_stub(args, capture_json=False, timeout=60):
        captured.append(list(args))
        # Provide a minimal valid response per operation.
        if args[:2] == ['pr', 'create']:
            return 0, 'https://github.com/octo/repo/pull/42', ''
        if args[:2] == ['pr', 'view']:
            if any(_CORROBORATION_JSON_MARKER in str(a) for a in args):
                return 0, _CORROBORATED_MERGE_PAYLOAD, ''
            return 0, '{"number": 42, "url": "https://github.com/octo/repo/pull/42", "state": "OPEN"}', ''
        if args[:2] == ['pr', 'merge']:
            return 0, '', ''
        if args[:2] == ['pr', 'checks']:
            return 0, '[]', ''
        if args[:2] == ['pr', 'update-branch']:
            return 0, '', ''
        return 0, '', ''

    return run_gh_stub, captured


def _install_merge_shaped_stubs(monkeypatch):
    """Install the platform-queue preflight prerequisites for merge-shaped verbs.

    ``cmd_pr_merge`` and ``cmd_pr_auto_merge`` both probe the PR's own base
    branch before acting. Without these stubs the argv-routing tests below would
    stop testing ``--head`` routing and start testing the preflight's
    fail-closed path — the assertions would still be about argv, but the code
    path reaching them would be the wrong one. ``eligible_unconfigured`` is the
    permissive verdict, so routing proceeds unchanged.
    """
    monkeypatch.setattr(github_ops, 'get_repo_info', lambda: ('octo', 'repo'))
    monkeypatch.setattr(
        github_ops,
        'view_pr_data',
        lambda head=None: {
            'status': 'success',
            'operation': 'pr_view',
            'pr_number': 42,
            'state': 'open',
            'head_branch': 'feature/x',
            'base_branch': 'main',
        },
    )
    monkeypatch.setattr(
        github_ops,
        '_probe_merge_queue_state',
        lambda owner, repo, branch: (
            github_ops.MERGE_QUEUE_ELIGIBLE_UNCONFIGURED,
            'no merge_queue rule on branch',
            None,
            None,
        ),
    )


def _prepare_pr_create_body(tmp_path, monkeypatch, body_text='B', plan_id='p'):
    """Seed PLAN_BASE_DIR with a prepared pr-create body scratch file."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    from ci_base import BODY_KIND_PR_CREATE, get_body_path

    path = get_body_path(plan_id, BODY_KIND_PR_CREATE)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body_text, encoding='utf-8')
    return plan_id


_PROVIDERS = (github_ops, gitlab_ops)
_PROVIDER_IDS = ('github', 'gitlab')
_PROVIDER_FIXTURES = {
    github_ops: {
        'no_pr_stderr': 'no pull requests found for branch "feature/x"',
        'success_stdout': '{"number": 42, "url": "https://github.com/octo/repo/pull/42", "state": "OPEN"}',
    },
    gitlab_ops: {
        'no_pr_stderr': 'no merge requests found for branch "feature/x"',
        'success_stdout': '{"iid": 42, "web_url": "https://gitlab.com/octo/repo/-/merge_requests/42", "state": "opened"}',
    },
}


def _stub_pr_view_cli(monkeypatch, provider, *, returncode, stdout, stderr):
    """Stub auth plus the single CLI seam ``view_pr_data`` reaches on *provider*."""
    monkeypatch.setattr(provider, 'check_auth', _ok_auth)
    runner = 'run_gh' if provider is github_ops else 'run_glab'
    monkeypatch.setattr(provider, runner, lambda *_a, **_kw: (returncode, stdout, stderr))


_CREATE_PR_DOC = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'phase-6-finalize' / 'workflow' / 'create-pr.md'
_GO_ZERO_GH = '0001-01-01T00:00:00Z'
_REUSABLE_LINK = 'https://github.com/octo/repo/actions/runs/123/job/456'
_RUN_ONLY_LINK = 'https://github.com/octo/repo/actions/runs/123'


def test_pr_create_forwards_head_flag(monkeypatch, tmp_path):
    run_gh_stub, captured = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    plan_id = _prepare_pr_create_body(tmp_path, monkeypatch)
    ns = argparse.Namespace(title='T', plan_id=plan_id, slot=None, base=None, draft=False, head='feature/x')
    result = github_ops.cmd_pr_create(ns)

    assert result['status'] == 'success', result
    assert any('--head' in c and 'feature/x' in c for c in captured), captured


def test_pr_create_omits_head_when_unset(monkeypatch, tmp_path):
    run_gh_stub, captured = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    plan_id = _prepare_pr_create_body(tmp_path, monkeypatch)
    ns = argparse.Namespace(title='T', plan_id=plan_id, slot=None, base=None, draft=False, head=None)
    result = github_ops.cmd_pr_create(ns)

    assert result['status'] == 'success', result
    assert not any('--head' in c for c in captured), captured


def test_pr_view_forwards_head_as_positional(monkeypatch):
    run_gh_stub, captured = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ns = argparse.Namespace(head='feature/x')
    result = github_ops.cmd_pr_view(ns)

    assert result['status'] == 'success', result
    pr_view_call = next(c for c in captured if c[:2] == ['pr', 'view'])
    assert pr_view_call[2] == 'feature/x', pr_view_call


def test_pr_view_forwards_pr_number_as_positional(monkeypatch):
    """--pr-number lands in gh's positional selector slot, stringified.

    This is the landing-poll selector: a required merge queue auto-deletes the head
    branch as it merges, so a --head-keyed poll stops resolving at exactly the moment
    `state: merged` becomes observable. The number survives the branch deletion.
    """
    run_gh_stub, captured = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ns = argparse.Namespace(pr_number=1152, head=None)
    result = github_ops.cmd_pr_view(ns)

    assert result['status'] == 'success', result
    pr_view_call = next(c for c in captured if c[:2] == ['pr', 'view'])
    assert pr_view_call[2] == '1152', pr_view_call


def test_pr_view_dual_flag_rejected(monkeypatch):
    """Both selectors together is a structured error, not a silent precedence rule."""
    run_gh_stub, captured = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ns = argparse.Namespace(pr_number=42, head='feature/x')
    result = github_ops.cmd_pr_view(ns)

    assert result['status'] == 'error', result
    assert 'not both' in result['error'], result
    assert captured == [], 'Should not invoke gh when validation fails'


def test_pr_view_omits_positional_when_no_selector(monkeypatch):
    """Neither selector keeps the historical current-cwd-HEAD lookup.

    Adding --pr-number must not have made a selector mandatory: with both omitted the
    positional slot stays empty, so --json is the token immediately after `pr view`.
    """
    run_gh_stub, captured = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ns = argparse.Namespace(pr_number=None, head=None)
    result = github_ops.cmd_pr_view(ns)

    assert result['status'] == 'success', result
    pr_view_call = next(c for c in captured if c[:2] == ['pr', 'view'])
    assert pr_view_call[2] == '--json', pr_view_call


def test_pr_merge_with_head(monkeypatch):
    run_gh_stub, captured = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)
    _install_merge_shaped_stubs(monkeypatch)

    ns = argparse.Namespace(pr_number=None, head='feature/x', strategy='merge', delete_branch=False)
    result = github_ops.cmd_pr_merge(ns)

    assert result['status'] == 'success', result
    merge_call = next(c for c in captured if c[:2] == ['pr', 'merge'])
    assert merge_call[2] == 'feature/x'


def test_pr_merge_with_pr_number(monkeypatch):
    run_gh_stub, captured = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)
    _install_merge_shaped_stubs(monkeypatch)

    ns = argparse.Namespace(pr_number=42, head=None, strategy='merge', delete_branch=False)
    result = github_ops.cmd_pr_merge(ns)

    assert result['status'] == 'success', result
    merge_call = next(c for c in captured if c[:2] == ['pr', 'merge'])
    assert merge_call[2] == '42'


def test_pr_merge_dual_flag_rejected(monkeypatch):
    run_gh_stub, captured = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ns = argparse.Namespace(pr_number=42, head='feature/x', strategy='merge', delete_branch=False)
    result = github_ops.cmd_pr_merge(ns)

    assert result['status'] == 'error'
    assert 'exactly one' in result['error']
    assert captured == [], 'Should not invoke gh when validation fails'


def test_pr_merge_neither_flag_rejected(monkeypatch):
    run_gh_stub, captured = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ns = argparse.Namespace(pr_number=None, head=None, strategy='merge', delete_branch=False)
    result = github_ops.cmd_pr_merge(ns)

    assert result['status'] == 'error'
    assert 'either' in result['error']


def test_pr_auto_merge_with_head(monkeypatch):
    run_gh_stub, captured = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)
    _install_merge_shaped_stubs(monkeypatch)

    ns = argparse.Namespace(pr_number=None, head='feature/x', strategy='merge')
    result = github_ops.cmd_pr_auto_merge(ns)

    assert result['status'] == 'success', result
    merge_call = next(c for c in captured if c[:2] == ['pr', 'merge'])
    assert merge_call[2] == 'feature/x'
    assert '--auto' in merge_call


def test_pr_auto_merge_dual_flag_rejected(monkeypatch):
    run_gh_stub, _ = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ns = argparse.Namespace(pr_number=42, head='feature/x', strategy='merge')
    result = github_ops.cmd_pr_auto_merge(ns)

    assert result['status'] == 'error'
    assert 'exactly one' in result['error']


def test_pr_update_branch_with_head(monkeypatch):
    run_gh_stub, captured = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ns = argparse.Namespace(pr_number=None, head='feature/x')
    result = github_ops.cmd_pr_update_branch(ns)

    assert result['status'] == 'success', result
    update_call = next(c for c in captured if c[:2] == ['pr', 'update-branch'])
    assert update_call[2] == 'feature/x'


def test_pr_update_branch_with_pr_number(monkeypatch):
    run_gh_stub, captured = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ns = argparse.Namespace(pr_number=42, head=None)
    result = github_ops.cmd_pr_update_branch(ns)

    assert result['status'] == 'success', result
    update_call = next(c for c in captured if c[:2] == ['pr', 'update-branch'])
    assert update_call[2] == '42'


def test_pr_update_branch_dual_flag_rejected(monkeypatch):
    run_gh_stub, captured = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ns = argparse.Namespace(pr_number=42, head='feature/x')
    result = github_ops.cmd_pr_update_branch(ns)

    assert result['status'] == 'error'
    assert 'exactly one' in result['error']
    assert captured == [], 'Should not invoke gh when validation fails'


def test_pr_update_branch_neither_flag_rejected(monkeypatch):
    run_gh_stub, captured = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ns = argparse.Namespace(pr_number=None, head=None)
    result = github_ops.cmd_pr_update_branch(ns)

    assert result['status'] == 'error'
    assert 'either' in result['error']


def test_pr_update_branch_gh_failure(monkeypatch):
    """When gh returns non-zero, the handler should return an error result."""

    def failing_run_gh(args, capture_json=False, timeout=60):
        if args[:2] == ['pr', 'update-branch']:
            return 1, '', 'merge conflict'
        return 0, '', ''

    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', failing_run_gh)

    ns = argparse.Namespace(pr_number=42, head=None)
    result = github_ops.cmd_pr_update_branch(ns)

    assert result['status'] == 'error'
    assert 'Failed to update branch' in result['error']


def test_pr_update_branch_auth_failure(monkeypatch):
    """When auth fails, the handler should return an error result."""
    monkeypatch.setattr(github_ops, 'check_auth', lambda: (False, 'not logged in'))
    monkeypatch.setattr(github_ops, 'run_gh', _capture_run_gh()[0])

    ns = argparse.Namespace(pr_number=42, head=None)
    result = github_ops.cmd_pr_update_branch(ns)

    assert result['status'] == 'error'
    assert 'not logged in' in result['error']


def test_the_four_pr_view_causes_are_distinct_members_of_one_vocabulary():
    """The shared vocabulary is closed and its four members are distinct.

    Asserted before the arms below because each of them compares against one of
    these constants: two constants that collapsed to the same string would make
    a wrong-cause return satisfy the assertion for the right one.
    """
    causes = (
        ci_base.PR_VIEW_CAUSE_AUTH_FAILED,
        ci_base.PR_VIEW_CAUSE_NO_PR,
        ci_base.PR_VIEW_CAUSE_PROVIDER_FAILED,
        ci_base.PR_VIEW_CAUSE_MALFORMED_RESPONSE,
    )
    assert len(set(causes)) == len(causes), f'Cause constants collapsed: {causes}'
    assert set(causes) == set(ci_base.PR_VIEW_CAUSES)
    assert ci_base.PR_VIEW_CAUSE_SAFE_TO_CREATE == ci_base.PR_VIEW_CAUSE_NO_PR


@pytest.mark.parametrize('provider', _PROVIDERS, ids=_PROVIDER_IDS)
def test_pr_view_auth_failure_carries_the_auth_cause(monkeypatch, provider):
    monkeypatch.setattr(provider, 'check_auth', lambda: (False, 'not logged in'))

    result = provider.view_pr_data()

    assert result['status'] == 'error'
    assert result['error_cause'] == ci_base.PR_VIEW_CAUSE_AUTH_FAILED
    # The human message is unchanged — the cause is ADDITIVE, not a rewording.
    assert 'not logged in' in result['error']


@pytest.mark.parametrize('provider', _PROVIDERS, ids=_PROVIDER_IDS)
def test_pr_view_genuine_absence_carries_the_no_pr_cause(monkeypatch, provider):
    """The one cause a caller may act on: the provider positively said "none"."""
    _stub_pr_view_cli(
        monkeypatch,
        provider,
        returncode=1,
        stdout='',
        stderr=_PROVIDER_FIXTURES[provider]['no_pr_stderr'],
    )

    result = provider.view_pr_data()

    assert result['status'] == 'error'
    assert result['error_cause'] == ci_base.PR_VIEW_CAUSE_NO_PR


@pytest.mark.parametrize('provider', _PROVIDERS, ids=_PROVIDER_IDS)
@pytest.mark.parametrize(
    'stderr',
    [
        'dial tcp: lookup api.host: no such host',
        'HTTP 403: Resource not accessible by integration',
        'error connecting to api.host',
        '',
    ],
    ids=['network', 'permission', 'transient', 'silent'],
)
def test_pr_view_unreadable_failure_is_never_a_no_pr_verdict(monkeypatch, provider, stderr):
    """FAIL-CLOSED: an unreadable non-zero exit leaves the question UNANSWERED.

    This is the duplicate-PR defect itself. Each stderr here is a real failure on
    a branch that may well have an open PR; resolving any of them to
    ``no_pr_found`` is what licenses `create-pr` to open a second one. The empty
    stderr arm matters most — it is the case with no evidence at all, and the one
    a permissive default would silently wave through.
    """
    _stub_pr_view_cli(monkeypatch, provider, returncode=1, stdout='', stderr=stderr)

    result = provider.view_pr_data()

    assert result['status'] == 'error'
    assert result['error_cause'] == ci_base.PR_VIEW_CAUSE_PROVIDER_FAILED
    assert result['error_cause'] != ci_base.PR_VIEW_CAUSE_SAFE_TO_CREATE


@pytest.mark.parametrize('provider', _PROVIDERS, ids=_PROVIDER_IDS)
def test_pr_view_unparseable_response_carries_the_malformed_cause(monkeypatch, provider):
    _stub_pr_view_cli(monkeypatch, provider, returncode=0, stdout='not-json', stderr='')

    result = provider.view_pr_data()

    assert result['status'] == 'error'
    assert result['error_cause'] == ci_base.PR_VIEW_CAUSE_MALFORMED_RESPONSE


@pytest.mark.parametrize('provider', _PROVIDERS, ids=_PROVIDER_IDS)
def test_pr_view_success_is_unchanged_and_carries_no_cause(monkeypatch, provider):
    """Matched control: the success envelope did not move.

    The discriminator is additive, so a success return must gain no
    ``error_cause`` and keep its ``status`` and payload. Without this arm a
    change that stamped a cause onto every return — success included — would
    satisfy every assertion above.
    """
    _stub_pr_view_cli(
        monkeypatch,
        provider,
        returncode=0,
        stdout=_PROVIDER_FIXTURES[provider]['success_stdout'],
        stderr='',
    )

    result = provider.view_pr_data()

    assert result['status'] == 'success', result
    assert 'error_cause' not in result
    assert result['pr_number'] == 42


def test_ci_status_dual_flag_rejected(monkeypatch):
    run_gh_stub, _ = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ns = argparse.Namespace(pr_number=42, head='feature/x')
    result = github_ops.cmd_ci_status(ns)

    assert result['status'] == 'error'
    assert 'exactly one' in result['error']
