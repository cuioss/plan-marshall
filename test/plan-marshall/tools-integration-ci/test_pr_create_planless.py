#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the plan-less ``pr create --body-file`` body source.

``pr create`` takes the PR body from exactly ONE of two mutually-exclusive
sources: the plan-bound body store (``--plan-id`` [+ ``--slot``]) or an explicit
``--body-file PATH`` (the steward landing-cycle path with no plan directory).
These tests exercise the GitHub ``cmd_pr_create`` handler and assert:

- ``--body-file`` reads the body directly from the file and builds the ``gh pr
  create`` argv with that content — no plan dir, and the body store is never
  touched (``read_and_consume_body`` / ``delete_consumed_body`` are not called);
- ``--label`` still passes through on the plan-less path;
- supplying NEITHER or BOTH body sources is rejected before any network call.

The GitHub provider surface (``check_auth``, ``run_gh``) is monkeypatched so no
network call occurs; the assertion is on the constructed ``gh`` argv and the
handler's validation branches. Provider stubs are set on
``_github_pr.github_ops`` (the module object the handler reaches through at call
time) so the patch lands regardless of module load order.
"""

import argparse

from conftest import load_script_module

_github_pr = load_script_module('plan-marshall', 'workflow-integration-github', '_github_pr.py', '_github_pr')


def _patch_create(monkeypatch, captured, store_calls):
    """Stub auth + run_gh; track body-store calls so we can assert they are unused.

    ``captured`` receives the ``gh`` argv on each ``run_gh`` call; ``store_calls``
    receives a marker string for every body-store helper invocation.
    """
    monkeypatch.setattr(_github_pr.github_ops, 'check_auth', lambda: (True, ''))

    def _fake_read_and_consume(plan_id, kind, slot):
        store_calls.append(('read', plan_id))
        return 'STORE body', None

    def _fake_delete(plan_id, kind, slot):
        store_calls.append(('delete', plan_id))

    monkeypatch.setattr(_github_pr, 'read_and_consume_body', _fake_read_and_consume)
    monkeypatch.setattr(_github_pr, 'delete_consumed_body', _fake_delete)

    def _fake_run_gh(gh_args):
        captured.append(list(gh_args))
        return 0, 'https://github.com/o/r/pull/42', ''

    monkeypatch.setattr(_github_pr.github_ops, 'run_gh', _fake_run_gh)


def _make_args(**overrides):
    """Build a ``pr create`` args namespace with sensible defaults (both body sources absent)."""
    base = {
        'title': 'A title',
        'plan_id': None,
        'body_file': None,
        'base': 'main',
        'draft': False,
        'head': None,
        'label': None,
        'slot': None,
    }
    base.update(overrides)
    return argparse.Namespace(**base)


def _flag_value(gh_args, flag):
    """Return the value following ``flag`` in the gh argv, or None when absent."""
    for i, tok in enumerate(gh_args):
        if tok == flag and i + 1 < len(gh_args):
            return gh_args[i + 1]
    return None


def test_body_file_builds_argv_from_file_with_no_plan_dir(tmp_path, monkeypatch):
    """--body-file reads the body directly and the body store is never touched."""
    captured: list = []
    store_calls: list = []
    _patch_create(monkeypatch, captured, store_calls)

    body_path = tmp_path / 'pr-body.md'
    body_path.write_text('Plan-less PR body from steward', encoding='utf-8')

    result = _github_pr.cmd_pr_create(_make_args(body_file=str(body_path)))

    assert result['status'] == 'success'
    assert len(captured) == 1
    # The gh argv carries the file's content verbatim as the --body value.
    assert _flag_value(captured[0], '--body') == 'Plan-less PR body from steward'
    # No plan-bound body-store interaction on the plan-less path.
    assert store_calls == []


def test_body_file_passes_label_through(tmp_path, monkeypatch):
    """--label still forwards to gh pr create on the plan-less --body-file path."""
    captured: list = []
    store_calls: list = []
    _patch_create(monkeypatch, captured, store_calls)

    body_path = tmp_path / 'pr-body.md'
    body_path.write_text('body', encoding='utf-8')

    result = _github_pr.cmd_pr_create(
        _make_args(body_file=str(body_path), label=['skip-bot-review'])
    )

    assert result['status'] == 'success'
    labels = [captured[0][i + 1] for i, tok in enumerate(captured[0]) if tok == '--label']
    assert labels == ['skip-bot-review']


def test_empty_body_file_is_rejected(tmp_path, monkeypatch):
    """An empty --body-file is a fail-loud error and no gh call is made."""
    captured: list = []
    store_calls: list = []
    _patch_create(monkeypatch, captured, store_calls)

    body_path = tmp_path / 'empty.md'
    body_path.write_text('   \n', encoding='utf-8')

    result = _github_pr.cmd_pr_create(_make_args(body_file=str(body_path)))

    assert result['status'] == 'error'
    assert captured == []


def test_missing_body_file_is_rejected(tmp_path, monkeypatch):
    """A --body-file pointing at a nonexistent path is a fail-loud error."""
    captured: list = []
    store_calls: list = []
    _patch_create(monkeypatch, captured, store_calls)

    result = _github_pr.cmd_pr_create(_make_args(body_file=str(tmp_path / 'nope.md')))

    assert result['status'] == 'error'
    assert captured == []


def test_no_body_source_is_rejected(monkeypatch):
    """Supplying neither --plan-id nor --body-file is rejected before any gh call."""
    captured: list = []
    store_calls: list = []
    _patch_create(monkeypatch, captured, store_calls)

    result = _github_pr.cmd_pr_create(_make_args(plan_id=None, body_file=None))

    assert result['status'] == 'error'
    assert captured == []
    assert store_calls == []


def test_both_body_sources_is_rejected(tmp_path, monkeypatch):
    """Supplying BOTH --plan-id and --body-file is rejected (mutually exclusive)."""
    captured: list = []
    store_calls: list = []
    _patch_create(monkeypatch, captured, store_calls)

    body_path = tmp_path / 'pr-body.md'
    body_path.write_text('body', encoding='utf-8')

    result = _github_pr.cmd_pr_create(
        _make_args(plan_id='some-plan', body_file=str(body_path))
    )

    assert result['status'] == 'error'
    assert captured == []
    assert store_calls == []


def test_plan_bound_path_still_consumes_and_deletes_body(monkeypatch):
    """The existing plan-bound (--plan-id) path is unchanged: it consumes + deletes the scratch body."""
    captured: list = []
    store_calls: list = []
    _patch_create(monkeypatch, captured, store_calls)

    result = _github_pr.cmd_pr_create(_make_args(plan_id='plan-x'))

    assert result['status'] == 'success'
    assert _flag_value(captured[0], '--body') == 'STORE body'
    # The plan-bound path reads then deletes the scratch body.
    assert ('read', 'plan-x') in store_calls
    assert ('delete', 'plan-x') in store_calls
