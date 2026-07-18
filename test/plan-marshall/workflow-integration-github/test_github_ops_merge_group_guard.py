#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the merge_group CI-trigger guard in ``repo merge-queue enable``.

The guard refuses to provision a GitHub merge-queue ruleset on an
``eligible_unconfigured`` repository whose ``.github/workflows`` carry no
``merge_group`` trigger — a footgun that would stall the queue and block every
merge to the default branch. Two surfaces are covered here:

* the pure stdlib scan helper ``_repo_has_merge_group_trigger`` across the three
  canonical GitHub-Actions ``on:`` forms plus the absent / no-directory /
  false-positive cases, driven through ``tmp_path`` ``.github/workflows``
  fixtures; and
* the ``cmd_repo_merge_queue_enable`` branch behaviour — refuse (no
  ``POST /rulesets``) when the trigger is absent, create when it is present, and
  the ``eligible_configured`` reconcile path staying unaffected by the scan.

The existing large ``test_repo_merge_queue.py`` suite is left untouched.
"""

import argparse
import json

import github_ops
import pytest


@pytest.fixture(autouse=True)
def _hermetic_bypass_config(monkeypatch):
    """Neutralise the real marshal.json so bypass resolution is ``(None, [])``.

    Mirrors the fixture in ``test_repo_merge_queue.py``: pinning ``load_config``
    to an empty dict keeps the enable path deterministic (no org-installations
    lookup) regardless of the meta-project's real config.
    """
    import _config_core

    monkeypatch.setattr(_config_core, 'is_initialized', lambda: True)
    monkeypatch.setattr(_config_core, 'load_config', lambda: {})


def _write_workflow(tmp_path, name, content):
    """Create ``<tmp_path>/.github/workflows/<name>`` with ``content``.

    Returns the ``.github/workflows`` directory path for direct helper calls.
    """
    workflows_dir = tmp_path / '.github' / 'workflows'
    workflows_dir.mkdir(parents=True, exist_ok=True)
    (workflows_dir / name).write_text(content, encoding='utf-8')
    return str(workflows_dir)


# ---------------------------------------------------------------------------
# _repo_has_merge_group_trigger — pure stdlib scan across the three on: forms
# ---------------------------------------------------------------------------


def test_helper_detects_single_string_on_form(tmp_path):
    workflows_dir = _write_workflow(
        tmp_path, 'ci.yml', 'name: CI\non: merge_group\njobs:\n  build:\n    runs-on: ubuntu-latest\n'
    )
    assert github_ops._repo_has_merge_group_trigger(workflows_dir) is True


def test_helper_detects_flow_sequence_on_form(tmp_path):
    workflows_dir = _write_workflow(
        tmp_path, 'ci.yml', 'name: CI\non: [push, merge_group]\njobs:\n  build:\n    runs-on: ubuntu-latest\n'
    )
    assert github_ops._repo_has_merge_group_trigger(workflows_dir) is True


def test_helper_detects_block_mapping_on_form(tmp_path):
    workflows_dir = _write_workflow(
        tmp_path,
        'ci.yml',
        'name: CI\non:\n  push:\n    branches: [main]\n  merge_group:\njobs:\n  build:\n    runs-on: ubuntu-latest\n',
    )
    assert github_ops._repo_has_merge_group_trigger(workflows_dir) is True


def test_helper_detects_block_sequence_on_form(tmp_path):
    workflows_dir = _write_workflow(
        tmp_path,
        'ci.yml',
        'name: CI\non:\n  - push\n  - merge_group\njobs:\n  build:\n    runs-on: ubuntu-latest\n',
    )
    assert github_ops._repo_has_merge_group_trigger(workflows_dir) is True


def test_helper_detects_quoted_on_key(tmp_path):
    workflows_dir = _write_workflow(
        tmp_path, 'ci.yml', 'name: CI\n"on": [push, merge_group]\njobs:\n  build: {}\n'
    )
    assert github_ops._repo_has_merge_group_trigger(workflows_dir) is True


def test_helper_scans_yaml_extension_too(tmp_path):
    workflows_dir = _write_workflow(
        tmp_path, 'ci.yaml', 'name: CI\non: merge_group\njobs:\n  build: {}\n'
    )
    assert github_ops._repo_has_merge_group_trigger(workflows_dir) is True


# ---------------------------------------------------------------------------
# _repo_has_merge_group_trigger — absent / no-directory / false-positive cases
# ---------------------------------------------------------------------------


def test_helper_returns_false_when_only_push_pull_request(tmp_path):
    workflows_dir = _write_workflow(
        tmp_path,
        'ci.yml',
        'name: CI\non:\n  push:\n    branches: [main]\n  pull_request:\njobs:\n  build: {}\n',
    )
    assert github_ops._repo_has_merge_group_trigger(workflows_dir) is False


def test_helper_returns_false_when_directory_absent(tmp_path):
    missing = str(tmp_path / '.github' / 'workflows')
    assert github_ops._repo_has_merge_group_trigger(missing) is False


def test_helper_returns_false_when_directory_empty(tmp_path):
    workflows_dir = tmp_path / '.github' / 'workflows'
    workflows_dir.mkdir(parents=True)
    assert github_ops._repo_has_merge_group_trigger(str(workflows_dir)) is False


def test_helper_ignores_non_workflow_extensions(tmp_path):
    workflows_dir = tmp_path / '.github' / 'workflows'
    workflows_dir.mkdir(parents=True)
    # A README that merely mentions merge_group must not count as a trigger.
    (workflows_dir / 'README.md').write_text('on: merge_group everywhere\n', encoding='utf-8')
    assert github_ops._repo_has_merge_group_trigger(str(workflows_dir)) is False


def test_helper_ignores_stray_token_outside_on_block(tmp_path):
    # A job id / env value named merge_group must NOT trip the anchored scan.
    workflows_dir = _write_workflow(
        tmp_path,
        'ci.yml',
        'name: CI\non:\n  push:\n    branches: [main]\njobs:\n  merge_group:\n    runs-on: ubuntu-latest\n',
    )
    assert github_ops._repo_has_merge_group_trigger(workflows_dir) is False


def test_helper_ignores_merge_group_as_nested_branch_name(tmp_path):
    # A branch literally named merge_group under push: branches: is a nested
    # VALUE, not a trigger — the direct-child anchoring must ignore it so the
    # guard does not falsely permit enabling the queue on such a repo.
    workflows_dir = _write_workflow(
        tmp_path,
        'ci.yml',
        'name: CI\non:\n  push:\n    branches:\n      - merge_group\njobs:\n  build: {}\n',
    )
    assert github_ops._repo_has_merge_group_trigger(workflows_dir) is False


def test_helper_ignores_commented_out_trigger(tmp_path):
    workflows_dir = _write_workflow(
        tmp_path,
        'ci.yml',
        'name: CI\non:\n  push:\n  # merge_group:\njobs:\n  build: {}\n',
    )
    assert github_ops._repo_has_merge_group_trigger(workflows_dir) is False


def test_helper_detects_trigger_in_second_file(tmp_path):
    # First file has no trigger; a later file does → overall True.
    _write_workflow(tmp_path, 'a.yml', 'name: A\non:\n  push:\njobs:\n  build: {}\n')
    workflows_dir = _write_workflow(
        tmp_path, 'b.yml', 'name: B\non: merge_group\njobs:\n  build: {}\n'
    )
    assert github_ops._repo_has_merge_group_trigger(workflows_dir) is True


# ---------------------------------------------------------------------------
# enable — refuse / create / configured-path-unaffected
# ---------------------------------------------------------------------------


def _make_run_gh(*, rules, post_rc=0, rulesets=None):
    """run_gh stub routing on the gh api endpoint, plus the capture list.

    Mirrors the shape used by ``test_repo_merge_queue.py`` so the enable path's
    probe → branch → act flow resolves against faithful fixtures.
    """
    captured: list[list[str]] = []

    def stub(args, capture_json=False, timeout=60):
        captured.append(list(args))
        if args[:3] == ['api', '-X', 'POST']:
            if post_rc != 0:
                return post_rc, '', 'HTTP 403 must have admin rights'
            return 0, '{"id": 99, "name": "plan-marshall-merge-queue"}', ''
        if args == ['api', 'repos/owner/repo']:
            return 0, '{"default_branch": "main"}', ''
        if args == ['api', 'repos/owner/repo/rules/branches/main']:
            return 0, json.dumps(rules), ''
        if args == ['api', 'repos/owner/repo/rulesets']:
            return 0, json.dumps(rulesets or []), ''
        return 0, '', ''

    return stub, captured


def _install(monkeypatch, stub):
    monkeypatch.setattr(github_ops, 'check_auth', lambda: (True, ''))
    monkeypatch.setattr(github_ops, 'get_repo_info', lambda: ('owner', 'repo'))
    monkeypatch.setattr(github_ops, 'run_gh', stub)


def test_enable_refuses_unconfigured_without_merge_group_trigger(monkeypatch, tmp_path):
    # Repo is eligible_unconfigured; its workflows carry only push → the guard
    # refuses with a merge_group message and issues NO POST /rulesets.
    _write_workflow(tmp_path, 'ci.yml', 'name: CI\non:\n  push:\n    branches: [main]\njobs:\n  build: {}\n')
    monkeypatch.chdir(tmp_path)
    stub, captured = _make_run_gh(rules=[{'type': 'pull_request'}])
    _install(monkeypatch, stub)

    result = github_ops.cmd_repo_merge_queue_enable(argparse.Namespace())
    assert result['status'] == 'error'
    assert result['operation'] == 'repo_merge_queue_enable'
    message = ' '.join(str(v) for v in result.values())
    assert 'merge_group' in message
    # The footgun guard fires BEFORE any ruleset mutation.
    assert not any(c[:3] == ['api', '-X', 'POST'] for c in captured)


def test_enable_refuses_unconfigured_when_no_workflows_directory(monkeypatch, tmp_path):
    # No .github/workflows at all → still refuse (missing trigger), no POST.
    monkeypatch.chdir(tmp_path)
    stub, captured = _make_run_gh(rules=[{'type': 'pull_request'}])
    _install(monkeypatch, stub)

    result = github_ops.cmd_repo_merge_queue_enable(argparse.Namespace())
    assert result['status'] == 'error'
    assert 'merge_group' in ' '.join(str(v) for v in result.values())
    assert not any(c[:3] == ['api', '-X', 'POST'] for c in captured)


def test_enable_creates_when_merge_group_trigger_present(monkeypatch, tmp_path):
    # Repo is eligible_unconfigured AND a workflow triggers on merge_group → the
    # guard passes and the ruleset is created (existing create behavior preserved).
    _write_workflow(tmp_path, 'ci.yml', 'name: CI\non: [push, merge_group]\njobs:\n  build: {}\n')
    monkeypatch.chdir(tmp_path)
    stub, captured = _make_run_gh(rules=[{'type': 'pull_request'}])
    _install(monkeypatch, stub)

    result = github_ops.cmd_repo_merge_queue_enable(argparse.Namespace())
    assert result['status'] == 'success'
    assert result['changed'] is True
    assert result['eligibility'] == 'eligible_configured'
    post_calls = [c for c in captured if c[:3] == ['api', '-X', 'POST']]
    assert len(post_calls) == 1
    assert post_calls[0][3] == 'repos/owner/repo/rulesets'
    assert '--input' in post_calls[0]


def test_enable_configured_reconcile_unaffected_by_workflow_scan(monkeypatch, tmp_path):
    # eligible_configured path must NOT be gated by the merge_group scan: with no
    # trigger workflow in cwd at all, enable still reaches the reconcile branch
    # and returns the idempotent no_change (never a merge_group refusal).
    monkeypatch.chdir(tmp_path)
    stub, captured = _make_run_gh(rules=[{'type': 'merge_queue'}], rulesets=[])
    _install(monkeypatch, stub)

    result = github_ops.cmd_repo_merge_queue_enable(argparse.Namespace())
    assert result['status'] == 'success'
    assert result['changed'] is False
    assert result['eligibility'] == 'eligible_configured'
    # No refusal message leaked from the guard into the configured path.
    assert 'merge_group' not in result.get('detail', '')
    assert not any(c[:3] == ['api', '-X', 'POST'] for c in captured)
