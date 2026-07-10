#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Regression tests for ``_github_pr.cmd_pr_create`` ``--label`` passthrough.

The create-pr finalize step applies ``--label skip-bot-review`` when the
enabled_bots set is empty (all reviewer bots disabled for this plan). The
handler forwards every ``--label`` value straight through to ``gh pr create``.
These tests capture the ``gh`` argv the handler constructs and assert the label
passthrough — verbatim, repeatable, and absent when no label is supplied.

The GitHub provider surface (``check_auth``, ``run_gh``) and the body-store
helpers (``read_and_consume_body``, ``delete_consumed_body``) are monkeypatched
so no network call or scratch-body file I/O occurs; the assertion is purely on
the constructed ``gh`` argv. Provider stubs are set on ``_github_pr.github_ops``
(the module object the handler reaches through at call time) so the patch lands
regardless of module load order.
"""

import argparse

from conftest import load_script_module

_github_pr = load_script_module('plan-marshall', 'workflow-integration-github', '_github_pr.py', '_github_pr')


def _patch_create(monkeypatch, captured):
    """Stub auth, body store, and run_gh so ``cmd_pr_create`` builds argv offline.

    ``captured`` receives the ``gh`` argv list on each ``run_gh`` call.
    """
    monkeypatch.setattr(_github_pr.github_ops, 'check_auth', lambda: (True, ''))
    monkeypatch.setattr(_github_pr, 'read_and_consume_body', lambda plan_id, kind, slot: ('PR body text', None))
    monkeypatch.setattr(_github_pr, 'delete_consumed_body', lambda plan_id, kind, slot: None)

    def _fake_run_gh(gh_args):
        captured.append(list(gh_args))
        return 0, 'https://github.com/o/r/pull/42', ''

    monkeypatch.setattr(_github_pr.github_ops, 'run_gh', _fake_run_gh)


def _make_args(**overrides):
    """Build a ``pr create`` args namespace with sensible defaults."""
    base = {
        'title': 'A title',
        'plan_id': 'label-plan',
        'base': 'main',
        'draft': False,
        'head': None,
        'label': None,
        'slot': None,
    }
    base.update(overrides)
    return argparse.Namespace(**base)


def _label_values(gh_args):
    """Return the ordered list of values following each ``--label`` flag."""
    return [gh_args[i + 1] for i, tok in enumerate(gh_args) if tok == '--label' and i + 1 < len(gh_args)]


def test_single_label_passed_through(monkeypatch):
    """A single ``--label`` value reaches ``gh pr create`` verbatim."""
    captured = []
    _patch_create(monkeypatch, captured)

    result = _github_pr.cmd_pr_create(_make_args(label=['skip-bot-review']))

    assert result['status'] == 'success'
    assert len(captured) == 1
    assert _label_values(captured[0]) == ['skip-bot-review']


def test_multiple_labels_passed_through_in_order(monkeypatch):
    """``--label`` is repeatable — every value is forwarded in supplied order."""
    captured = []
    _patch_create(monkeypatch, captured)

    result = _github_pr.cmd_pr_create(_make_args(label=['skip-bot-review', 'automated']))

    assert result['status'] == 'success'
    assert _label_values(captured[0]) == ['skip-bot-review', 'automated']


def test_no_label_omits_flag(monkeypatch):
    """With no ``--label`` supplied, no ``--label`` flag appears in the gh argv."""
    captured = []
    _patch_create(monkeypatch, captured)

    result = _github_pr.cmd_pr_create(_make_args(label=None))

    assert result['status'] == 'success'
    assert '--label' not in captured[0]
