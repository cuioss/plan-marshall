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


# ---------------------------------------------------------------------------
# build_merge_queue_ruleset_payload — bypass_actors threading
# ---------------------------------------------------------------------------


def test_payload_omits_bypass_actors_without_ids():
    # No ids (default) and explicit empty list both preserve today's behavior.
    assert 'bypass_actors' not in github_ops.build_merge_queue_ruleset_payload('main')
    assert 'bypass_actors' not in github_ops.build_merge_queue_ruleset_payload('main', [])


def test_payload_weaves_bypass_actors_when_ids_supplied():
    payload = github_ops.build_merge_queue_ruleset_payload('main', [12345, 678])
    actors = payload['bypass_actors']
    assert [a['actor_id'] for a in actors] == [12345, 678]
    for actor in actors:
        assert actor['actor_type'] == 'Integration'
        assert actor['bypass_mode'] == 'always'
    # The merge_queue rule is still present and unchanged.
    assert 'merge_queue' in [r.get('type') for r in payload['rules']]


# ---------------------------------------------------------------------------
# _read_merge_queue_bypass_config — defensive config reader
# ---------------------------------------------------------------------------


def test_config_reader_reads_both_knobs(monkeypatch):
    import _config_core

    monkeypatch.setattr(
        _config_core,
        'load_config',
        lambda: {'merge_queue': {'bypass_app_id': 4242, 'bypass_app_slugs': ['release-bot', 'other']}},
    )
    app_id, slugs = github_ops._read_merge_queue_bypass_config()
    assert app_id == 4242
    assert slugs == ['release-bot', 'other']


def test_config_reader_absent_block_yields_empty(monkeypatch):
    import _config_core

    monkeypatch.setattr(_config_core, 'load_config', lambda: {'plan': {}})
    assert github_ops._read_merge_queue_bypass_config() == (None, [])


def test_config_reader_rejects_bool_and_malformed_slugs(monkeypatch):
    import _config_core

    # bool is an int subclass — must NOT be read as an id; non-str slugs dropped.
    monkeypatch.setattr(
        _config_core,
        'load_config',
        lambda: {'merge_queue': {'bypass_app_id': True, 'bypass_app_slugs': ['ok', 5, '']}},
    )
    app_id, slugs = github_ops._read_merge_queue_bypass_config()
    assert app_id is None
    assert slugs == ['ok']


def test_config_reader_never_raises_on_load_error(monkeypatch):
    import _config_core

    def _boom():
        raise RuntimeError('no git root')

    monkeypatch.setattr(_config_core, 'load_config', _boom)
    assert github_ops._read_merge_queue_bypass_config() == (None, [])


# ---------------------------------------------------------------------------
# enable — bypass-actor resolution (config-first, org-list fallback, self-heal)
# ---------------------------------------------------------------------------


def _make_enable_stubs(
    *,
    rules,
    installations=None,
    installations_rc=0,
    rulesets_list=None,
    ruleset_detail=None,
):
    """Build (run_gh_stub, body_stub, captured, bodies) for the enable path.

    ``run_gh`` answers the read endpoints (repo metadata, branch rules, org
    installations, ruleset list/detail); ``_gh_api_json_body`` captures every
    POST/PUT payload so the woven bypass_actors are introspectable (the real
    helper writes the body to an unlinked temp file).
    """
    captured: list[list[str]] = []
    bodies: list[tuple[str, str, dict]] = []

    def run_gh_stub(args, capture_json=False, timeout=60):
        captured.append(list(args))
        if args == ['api', 'repos/owner/repo']:
            return 0, '{"default_branch": "main"}', ''
        if args == ['api', 'repos/owner/repo/rules/branches/main']:
            return 0, json.dumps(rules), ''
        if args == ['api', 'orgs/owner/installations']:
            if installations_rc != 0:
                return installations_rc, '', 'HTTP 403 must have admin rights'
            return 0, json.dumps({'installations': installations or []}), ''
        if args == ['api', 'repos/owner/repo/rulesets']:
            return 0, json.dumps(rulesets_list or []), ''
        if len(args) == 2 and args[0] == 'api' and args[1].startswith('repos/owner/repo/rulesets/'):
            return 0, json.dumps(ruleset_detail or {}), ''
        return 0, '', ''

    def body_stub(method, endpoint, payload):
        bodies.append((method, endpoint, payload))
        return 0, '{"id": 99}', ''

    return run_gh_stub, body_stub, captured, bodies


def _install_enable(monkeypatch, run_gh_stub, body_stub):
    monkeypatch.setattr(github_ops, 'check_auth', lambda: (True, ''))
    monkeypatch.setattr(github_ops, 'get_repo_info', lambda: ('owner', 'repo'))
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)
    monkeypatch.setattr(github_ops, '_gh_api_json_body', body_stub)


def test_enable_config_only_weaves_actor_without_orgs_call(monkeypatch):
    run_gh_stub, body_stub, captured, bodies = _make_enable_stubs(rules=[{'type': 'pull_request'}])
    _install_enable(monkeypatch, run_gh_stub, body_stub)
    monkeypatch.setattr(github_ops, '_read_merge_queue_bypass_config', lambda: (12345, []))

    result = github_ops.cmd_repo_merge_queue_enable(argparse.Namespace())
    assert result['status'] == 'success'
    assert result['changed'] is True
    # POST body carries the config-resolved bypass actor.
    posts = [b for b in bodies if b[0] == 'POST']
    assert len(posts) == 1
    payload = posts[0][2]
    assert [a['actor_id'] for a in payload['bypass_actors']] == [12345]
    # Config-only path issues NO org-installations lookup.
    assert not any(c == ['api', 'orgs/owner/installations'] for c in captured)


def test_enable_org_list_fallback_matches_app_slug(monkeypatch):
    run_gh_stub, body_stub, captured, bodies = _make_enable_stubs(
        rules=[{'type': 'pull_request'}],
        installations=[
            {'app_slug': 'unrelated', 'app_id': 1},
            {'app_slug': 'release-bot', 'app_id': 777},
        ],
    )
    _install_enable(monkeypatch, run_gh_stub, body_stub)
    monkeypatch.setattr(github_ops, '_read_merge_queue_bypass_config', lambda: (None, ['release-bot']))

    result = github_ops.cmd_repo_merge_queue_enable(argparse.Namespace())
    assert result['status'] == 'success'
    payload = [b for b in bodies if b[0] == 'POST'][0][2]
    assert [a['actor_id'] for a in payload['bypass_actors']] == [777]
    assert any(c == ['api', 'orgs/owner/installations'] for c in captured)


def test_enable_org_list_no_match_leaves_payload_unchanged(monkeypatch):
    run_gh_stub, body_stub, _captured, bodies = _make_enable_stubs(
        rules=[{'type': 'pull_request'}],
        installations=[{'app_slug': 'unrelated', 'app_id': 1}],
    )
    _install_enable(monkeypatch, run_gh_stub, body_stub)
    monkeypatch.setattr(github_ops, '_read_merge_queue_bypass_config', lambda: (None, ['release-bot']))

    result = github_ops.cmd_repo_merge_queue_enable(argparse.Namespace())
    assert result['status'] == 'success'
    payload = [b for b in bodies if b[0] == 'POST'][0][2]
    assert 'bypass_actors' not in payload


def test_enable_org_list_precondition_failure_is_graceful(monkeypatch):
    run_gh_stub, body_stub, _captured, bodies = _make_enable_stubs(
        rules=[{'type': 'pull_request'}],
        installations_rc=1,
    )
    _install_enable(monkeypatch, run_gh_stub, body_stub)
    monkeypatch.setattr(github_ops, '_read_merge_queue_bypass_config', lambda: (None, ['release-bot']))

    result = github_ops.cmd_repo_merge_queue_enable(argparse.Namespace())
    # A non-zero /orgs exit (admin:org scope / non-org ownership) degrades to []
    # — enable still succeeds and the ruleset is created without bypass_actors.
    assert result['status'] == 'success'
    payload = [b for b in bodies if b[0] == 'POST'][0][2]
    assert 'bypass_actors' not in payload


def test_enable_self_heal_patches_missing_actor(monkeypatch):
    run_gh_stub, body_stub, _captured, bodies = _make_enable_stubs(
        rules=[{'type': 'merge_queue'}],
        rulesets_list=[{'id': 5, 'name': 'plan-marshall-merge-queue'}],
        ruleset_detail={'id': 5, 'name': 'plan-marshall-merge-queue', 'bypass_actors': []},
    )
    _install_enable(monkeypatch, run_gh_stub, body_stub)
    monkeypatch.setattr(github_ops, '_read_merge_queue_bypass_config', lambda: (999, []))

    result = github_ops.cmd_repo_merge_queue_enable(argparse.Namespace())
    assert result['status'] == 'success'
    assert result['changed'] is True
    puts = [b for b in bodies if b[0] == 'PUT']
    assert len(puts) == 1
    method, endpoint, payload = puts[0]
    assert endpoint == 'repos/owner/repo/rulesets/5'
    assert [a['actor_id'] for a in payload['bypass_actors']] == [999]


def test_enable_self_heal_noop_when_actor_present(monkeypatch):
    run_gh_stub, body_stub, _captured, bodies = _make_enable_stubs(
        rules=[{'type': 'merge_queue'}],
        rulesets_list=[{'id': 5, 'name': 'plan-marshall-merge-queue'}],
        ruleset_detail={
            'id': 5,
            'name': 'plan-marshall-merge-queue',
            'bypass_actors': [{'actor_id': 999, 'actor_type': 'Integration', 'bypass_mode': 'always'}],
        },
    )
    _install_enable(monkeypatch, run_gh_stub, body_stub)
    monkeypatch.setattr(github_ops, '_read_merge_queue_bypass_config', lambda: (999, []))

    result = github_ops.cmd_repo_merge_queue_enable(argparse.Namespace())
    assert result['status'] == 'success'
    assert result['changed'] is False
    assert not any(b[0] == 'PUT' for b in bodies)


def test_enable_self_heal_noop_when_no_id_resolved(monkeypatch):
    run_gh_stub, body_stub, captured, bodies = _make_enable_stubs(rules=[{'type': 'merge_queue'}])
    _install_enable(monkeypatch, run_gh_stub, body_stub)
    monkeypatch.setattr(github_ops, '_read_merge_queue_bypass_config', lambda: (None, []))

    result = github_ops.cmd_repo_merge_queue_enable(argparse.Namespace())
    assert result['status'] == 'success'
    assert result['changed'] is False
    # No id resolved → self-heal never fetches the ruleset and issues no PUT.
    assert not any(c == ['api', 'repos/owner/repo/rulesets'] for c in captured)
    assert not any(b[0] == 'PUT' for b in bodies)
