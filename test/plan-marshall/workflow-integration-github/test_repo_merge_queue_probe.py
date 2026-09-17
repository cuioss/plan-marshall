# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the GitHub `repo merge-queue` probe/enable handlers.

All fixtures are API-shape-faithful (no live gh). The probe reads the evaluated
branch rules via ``GET /repos/{owner}/{repo}/rules/branches/{branch}`` and maps
each result to the shared eligibility discriminator; enable creates a
``merge_queue`` ruleset via ``POST /repos/{owner}/{repo}/rulesets`` and is
idempotent.
"""

import argparse
import json

import github_ops
import pytest


@pytest.fixture(autouse=True)
def _hermetic_bypass_config(monkeypatch):
    """Neutralise the real marshal.json for every test.

    ``_read_merge_queue_bypass_config`` reads ``merge_queue.bypass_app_id`` /
    ``merge_queue.bypass_app_slugs`` from the live config via the lazy
    ``_config_core`` seam. Pinning ``load_config`` to an empty dict makes the
    default resolution ``(None, [])`` regardless of the meta-project's real
    config, so the existing enable/probe tests stay deterministic. Tests that
    exercise config-driven resolution override this by patching
    ``github_ops._read_merge_queue_bypass_config`` (behaviour) or
    ``_config_core.load_config`` (reader unit).
    """
    import _config_core

    monkeypatch.setattr(_config_core, 'is_initialized', lambda: True)
    monkeypatch.setattr(_config_core, 'load_config', lambda: {})


def _make_run_gh(*, rules=None, post_rc=0, repo_rc=0, repo_err='', rules_rc=0, rules_err='', rulesets=None):
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
        # repo rulesets list (enable-configured reconcile path)
        if args == ['api', 'repos/owner/repo/rulesets']:
            return 0, json.dumps(rulesets or []), ''
        return 0, '', ''

    return stub, captured


def _install(monkeypatch, stub):
    monkeypatch.setattr(github_ops, 'check_auth', lambda: (True, ''))
    monkeypatch.setattr(github_ops, 'get_repo_info', lambda: ('owner', 'repo'))
    monkeypatch.setattr(github_ops, 'run_gh', stub)


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
    stub, _ = _make_run_gh(rules_rc=1, rules_err='HTTP 403: Resource not accessible by integration')
    _install(monkeypatch, stub)

    result = github_ops.cmd_repo_merge_queue_probe(argparse.Namespace())
    # Auth-scope failure surfaces the actionable error, never a discriminator.
    assert result['status'] == 'error'
    assert result['operation'] == 'repo_merge_queue_probe'
    message = ' '.join(str(v) for v in result.values()).lower()
    assert 'scope' in message or 'admin' in message or 'permission' in message


def test_probe_generic_api_error_is_error_not_ineligible(monkeypatch):
    # A non-404, non-auth gh failure (transient HTTP 500) must surface as a real
    # error result — NOT be folded into the 'ineligible' discriminator, which
    # would wrongly tell the operator the platform lacks the feature.
    stub, _ = _make_run_gh(rules_rc=1, rules_err='HTTP 500 Internal Server Error')
    _install(monkeypatch, stub)

    result = github_ops.cmd_repo_merge_queue_probe(argparse.Namespace())
    assert result['status'] == 'error'
    assert result['operation'] == 'repo_merge_queue_probe'
    assert result.get('eligibility') != 'ineligible'


def test_probe_unparseable_rules_is_error_not_ineligible(monkeypatch):
    # A malformed (non-JSON) rules response is an API/transport anomaly, not a
    # feature-availability verdict — it must surface as an error, not ineligible.
    def stub(args, capture_json=False, timeout=60):
        if args == ['api', 'repos/owner/repo']:
            return 0, '{"default_branch": "main"}', ''
        if args == ['api', 'repos/owner/repo/rules/branches/main']:
            return 0, 'not-json{', ''
        return 0, '', ''

    _install(monkeypatch, stub)

    result = github_ops.cmd_repo_merge_queue_probe(argparse.Namespace())
    assert result['status'] == 'error'
    assert result.get('eligibility') != 'ineligible'


def test_probe_non_list_rules_is_error_not_ineligible(monkeypatch):
    # A well-formed but non-list rules response is an unexpected API shape, not a
    # feature-availability verdict — it must surface as an error, not ineligible.
    def stub(args, capture_json=False, timeout=60):
        if args == ['api', 'repos/owner/repo']:
            return 0, '{"default_branch": "main"}', ''
        if args == ['api', 'repos/owner/repo/rules/branches/main']:
            return 0, '{"unexpected": "object"}', ''
        return 0, '', ''

    _install(monkeypatch, stub)

    result = github_ops.cmd_repo_merge_queue_probe(argparse.Namespace())
    assert result['status'] == 'error'
    assert result.get('eligibility') != 'ineligible'


def test_probe_default_branch_resolution_failure(monkeypatch):
    stub, _ = _make_run_gh(repo_rc=1, repo_err='HTTP 500 boom')
    _install(monkeypatch, stub)

    result = github_ops.cmd_repo_merge_queue_probe(argparse.Namespace())
    assert result['status'] == 'error'


def test_probe_auth_failure(monkeypatch):
    monkeypatch.setattr(github_ops, 'check_auth', lambda: (False, 'not authed'))
    result = github_ops.cmd_repo_merge_queue_probe(argparse.Namespace())
    assert result['status'] == 'error'


def test_enable_refuses_when_ineligible(monkeypatch):
    stub, captured = _make_run_gh(rules_rc=1, rules_err='HTTP 404 Not Found')
    _install(monkeypatch, stub)

    result = github_ops.cmd_repo_merge_queue_enable(argparse.Namespace())
    assert result['status'] == 'error'
    assert result['operation'] == 'repo_merge_queue_enable'
    # No mutation attempted.
    assert not any(c[:3] == ['api', '-X', 'POST'] for c in captured)


def test_probe_surfaces_merge_method_when_configured(monkeypatch):
    stub, _ = _make_run_gh(rules=[{'type': 'merge_queue', 'parameters': {'merge_method': 'SQUASH'}}])
    _install(monkeypatch, stub)

    result = github_ops.cmd_repo_merge_queue_probe(argparse.Namespace())
    assert result['status'] == 'success'
    assert result['eligibility'] == 'eligible_configured'
    assert result['merge_method'] == 'SQUASH'


def test_probe_omits_merge_method_when_unconfigured(monkeypatch):
    stub, _ = _make_run_gh(rules=[{'type': 'pull_request'}])
    _install(monkeypatch, stub)

    result = github_ops.cmd_repo_merge_queue_probe(argparse.Namespace())
    assert result['eligibility'] == 'eligible_unconfigured'
    assert 'merge_method' not in result


def test_probe_omits_merge_method_when_parameter_absent(monkeypatch):
    # A configured rule without parameters (or a malformed merge_method) yields
    # no merge_method key rather than a None value.
    stub, _ = _make_run_gh(rules=[{'type': 'merge_queue'}])
    _install(monkeypatch, stub)

    result = github_ops.cmd_repo_merge_queue_probe(argparse.Namespace())
    assert result['eligibility'] == 'eligible_configured'
    assert 'merge_method' not in result


def test_probe_reports_externally_managed_for_foreign_ruleset(monkeypatch):
    stub, captured = _make_run_gh(
        rules=[{'type': 'merge_queue'}],
        rulesets=[{'id': 7, 'name': 'org-owned-merge-queue'}],
    )
    _install(monkeypatch, stub)

    result = github_ops.cmd_repo_merge_queue_probe(argparse.Namespace())

    assert result['eligibility'] == 'eligible_configured'
    assert result['externally_managed'] is True
    assert [c for c in captured if c[:2] == ['api', '-X']] == []


def test_probe_omits_externally_managed_when_unconfigured(monkeypatch):
    # The field is absent — never False — on any non-configured discriminator.
    stub, _ = _make_run_gh(rules=[{'type': 'pull_request'}])
    _install(monkeypatch, stub)

    result = github_ops.cmd_repo_merge_queue_probe(argparse.Namespace())
    assert result['eligibility'] == 'eligible_unconfigured'
    assert 'externally_managed' not in result
