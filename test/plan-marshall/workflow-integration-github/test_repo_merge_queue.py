#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the GitHub `repo merge-queue` probe/enable handlers (deliverable 2).

All fixtures are API-shape-faithful (no live gh). The probe reads the evaluated
branch rules via ``GET /repos/{owner}/{repo}/rules/branches/{branch}`` and maps
each result to the shared eligibility discriminator; enable creates a
``merge_queue`` ruleset via ``POST /repos/{owner}/{repo}/rulesets`` and is
idempotent.
"""

import argparse
import json

import github_ops


def _make_run_gh(*, rules=None, post_rc=0, repo_rc=0, repo_err='', rules_rc=0, rules_err=''):
    """Build a run_gh stub that routes on the gh api endpoint, plus the capture list."""
    captured: list[list[str]] = []

    def stub(args, capture_json=False, timeout=60):
        captured.append(list(args))
        # POST /rulesets (enable path)
        if args[:3] == ['api', '-X', 'POST']:
            if post_rc != 0:
                return post_rc, '', 'HTTP 403 must have admin rights'
            return 0, '{"id": 99, "name": "plan-marshall-merge-queue"}', ''
        # repo metadata → default_branch
        if args == ['api', 'repos/owner/repo']:
            if repo_rc != 0:
                return repo_rc, '', repo_err
            return 0, '{"default_branch": "main"}', ''
        # evaluated branch rules
        if args == ['api', 'repos/owner/repo/rules/branches/main']:
            if rules_rc != 0:
                return rules_rc, '', rules_err
            return 0, json.dumps(rules or []), ''
        return 0, '', ''

    return stub, captured


def _install(monkeypatch, stub):
    monkeypatch.setattr(github_ops, 'check_auth', lambda: (True, ''))
    monkeypatch.setattr(github_ops, 'get_repo_info', lambda: ('owner', 'repo'))
    monkeypatch.setattr(github_ops, 'run_gh', stub)


# ---------------------------------------------------------------------------
# probe — each eligibility discriminator
# ---------------------------------------------------------------------------


def test_probe_configured(monkeypatch):
    stub, _ = _make_run_gh(rules=[{'type': 'merge_queue'}])
    _install(monkeypatch, stub)

    result = github_ops.cmd_repo_merge_queue_probe(argparse.Namespace())
    assert result['status'] == 'success'
    assert result['operation'] == 'repo_merge_queue_probe'
    assert result['provider'] == 'github'
    assert result['branch'] == 'main'
    assert result['eligibility'] == 'eligible_configured'


def test_probe_unconfigured(monkeypatch):
    stub, _ = _make_run_gh(rules=[{'type': 'pull_request'}, {'type': 'required_status_checks'}])
    _install(monkeypatch, stub)

    result = github_ops.cmd_repo_merge_queue_probe(argparse.Namespace())
    assert result['eligibility'] == 'eligible_unconfigured'


def test_probe_ineligible_on_404(monkeypatch):
    stub, _ = _make_run_gh(rules_rc=1, rules_err='HTTP 404 Not Found')
    _install(monkeypatch, stub)

    result = github_ops.cmd_repo_merge_queue_probe(argparse.Namespace())
    assert result['eligibility'] == 'ineligible'


def test_probe_auth_scope_error(monkeypatch):
    stub, _ = _make_run_gh(
        rules_rc=1, rules_err='HTTP 403: Resource not accessible by integration'
    )
    _install(monkeypatch, stub)

    result = github_ops.cmd_repo_merge_queue_probe(argparse.Namespace())
    # Auth-scope failure surfaces the actionable error, never a discriminator.
    assert result['status'] == 'error'
    assert result['operation'] == 'repo_merge_queue_probe'
    message = ' '.join(str(v) for v in result.values()).lower()
    assert 'scope' in message or 'admin' in message or 'permission' in message


def test_probe_default_branch_resolution_failure(monkeypatch):
    stub, _ = _make_run_gh(repo_rc=1, repo_err='HTTP 500 boom')
    _install(monkeypatch, stub)

    result = github_ops.cmd_repo_merge_queue_probe(argparse.Namespace())
    assert result['status'] == 'error'


def test_probe_auth_failure(monkeypatch):
    monkeypatch.setattr(github_ops, 'check_auth', lambda: (False, 'not authed'))
    result = github_ops.cmd_repo_merge_queue_probe(argparse.Namespace())
    assert result['status'] == 'error'


# ---------------------------------------------------------------------------
# enable — idempotent / create ruleset / refuse
# ---------------------------------------------------------------------------


def test_enable_idempotent_when_configured(monkeypatch):
    stub, captured = _make_run_gh(rules=[{'type': 'merge_queue'}])
    _install(monkeypatch, stub)

    result = github_ops.cmd_repo_merge_queue_enable(argparse.Namespace())
    assert result['status'] == 'success'
    assert result['changed'] is False
    assert result['eligibility'] == 'eligible_configured'
    # No POST was issued (idempotent no-op).
    assert not any(c[:3] == ['api', '-X', 'POST'] for c in captured)


def test_enable_creates_ruleset_when_unconfigured(monkeypatch):
    stub, captured = _make_run_gh(rules=[{'type': 'pull_request'}])
    _install(monkeypatch, stub)

    result = github_ops.cmd_repo_merge_queue_enable(argparse.Namespace())
    assert result['status'] == 'success'
    assert result['changed'] is True
    assert result['eligibility'] == 'eligible_configured'
    # A POST to the rulesets endpoint was issued with a JSON body via --input.
    post_calls = [c for c in captured if c[:3] == ['api', '-X', 'POST']]
    assert len(post_calls) == 1
    post = post_calls[0]
    assert post[3] == 'repos/owner/repo/rulesets'
    assert '--input' in post


def test_enable_error_when_post_fails(monkeypatch):
    stub, _ = _make_run_gh(rules=[{'type': 'pull_request'}], post_rc=1)
    _install(monkeypatch, stub)

    result = github_ops.cmd_repo_merge_queue_enable(argparse.Namespace())
    assert result['status'] == 'error'
    assert result['operation'] == 'repo_merge_queue_enable'


def test_enable_refuses_when_ineligible(monkeypatch):
    stub, captured = _make_run_gh(rules_rc=1, rules_err='HTTP 404 Not Found')
    _install(monkeypatch, stub)

    result = github_ops.cmd_repo_merge_queue_enable(argparse.Namespace())
    assert result['status'] == 'error'
    assert result['operation'] == 'repo_merge_queue_enable'
    # No mutation attempted.
    assert not any(c[:3] == ['api', '-X', 'POST'] for c in captured)


def test_enable_auth_failure(monkeypatch):
    monkeypatch.setattr(github_ops, 'check_auth', lambda: (False, 'not authed'))
    result = github_ops.cmd_repo_merge_queue_enable(argparse.Namespace())
    assert result['status'] == 'error'


# ---------------------------------------------------------------------------
# build_merge_queue_ruleset_payload — pure payload contract
# ---------------------------------------------------------------------------


def test_ruleset_payload_targets_branch_with_merge_queue_rule():
    payload = github_ops.build_merge_queue_ruleset_payload('main')
    assert payload['target'] == 'branch'
    assert payload['enforcement'] == 'active'
    assert payload['conditions']['ref_name']['include'] == ['refs/heads/main']
    rule_types = [r.get('type') for r in payload['rules']]
    assert 'merge_queue' in rule_types


def test_github_ops_exposes_repo_merge_queue_handlers():
    assert callable(github_ops.cmd_repo_merge_queue_probe)
    assert callable(github_ops.cmd_repo_merge_queue_enable)
