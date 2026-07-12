#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the GitHub ``repo label ensure`` handler.

``repo label ensure`` guarantees a repository label exists — create-if-missing
and idempotent. On GitHub it uses ``gh label create {name} --force``: ``--force``
makes the create UPDATE an existing label in place instead of erroring, so a
re-run against an already-present label is a no-op success. These tests capture
the ``gh`` argv the handler constructs and assert:

- the idempotent ``label create ... --force`` form is used (the ``--force`` flag
  IS the create-if-missing / no-op-on-existing mechanism);
- optional ``--color`` / ``--description`` pass through when supplied;
- a genuine ``gh`` failure surfaces as a structured error.

The GitHub provider surface (``check_auth``, ``run_gh``) is monkeypatched so no
network call occurs; provider stubs are set on ``_github_pr.github_ops`` (the
module object the handler reaches through at call time) so the patch lands
regardless of module load order.
"""

import argparse

from conftest import load_script_module

_github_pr = load_script_module('plan-marshall', 'workflow-integration-github', '_github_pr.py', '_github_pr')


def _patch(monkeypatch, captured, *, returncode=0, stderr=''):
    """Stub auth + run_gh; ``captured`` receives the gh argv on each call."""
    monkeypatch.setattr(_github_pr.github_ops, 'check_auth', lambda: (True, ''))

    def _fake_run_gh(gh_args):
        captured.append(list(gh_args))
        return returncode, '', stderr

    monkeypatch.setattr(_github_pr.github_ops, 'run_gh', _fake_run_gh)


def _make_args(**overrides):
    """Build a ``repo label ensure`` args namespace with sensible defaults."""
    base = {'label': 'skip-bot-review', 'color': None, 'description': None}
    base.update(overrides)
    return argparse.Namespace(**base)


def test_ensure_uses_idempotent_force_create(monkeypatch):
    """The handler builds ``gh label create {name} --force`` — the idempotent form."""
    captured: list = []
    _patch(monkeypatch, captured)

    result = _github_pr.cmd_repo_label_ensure(_make_args())

    assert result['status'] == 'success'
    assert result['label'] == 'skip-bot-review'
    assert result['ensured'] is True
    assert captured == [['label', 'create', 'skip-bot-review', '--force']]


def test_ensure_passes_color_and_description(monkeypatch):
    """Optional --color / --description pass through to gh label create."""
    captured: list = []
    _patch(monkeypatch, captured)

    result = _github_pr.cmd_repo_label_ensure(
        _make_args(color='ededed', description='Suppress bot review')
    )

    assert result['status'] == 'success'
    assert captured[0] == [
        'label',
        'create',
        'skip-bot-review',
        '--force',
        '--color',
        'ededed',
        '--description',
        'Suppress bot review',
    ]


def test_ensure_existing_label_is_noop_success(monkeypatch):
    """An already-present label is a no-op success: --force updates in place, gh returns 0.

    The ``--force`` flag makes ``gh label create`` update an existing label
    instead of erroring, so the create-if-missing and no-op-on-existing paths are
    the SAME successful invocation from the handler's perspective.
    """
    captured: list = []
    _patch(monkeypatch, captured, returncode=0)

    result = _github_pr.cmd_repo_label_ensure(_make_args())

    assert result['status'] == 'success'
    assert result['ensured'] is True
    assert '--force' in captured[0]


def test_ensure_reports_failure(monkeypatch):
    """A genuine gh failure surfaces as a structured error, not a success."""
    captured: list = []
    _patch(monkeypatch, captured, returncode=1, stderr='some auth failure')

    result = _github_pr.cmd_repo_label_ensure(_make_args())

    assert result['status'] == 'error'
