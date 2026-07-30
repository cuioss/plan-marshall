#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the plan-less ``pr create`` path — now the ``NO_PLAN`` sentinel.

``pr create`` takes the PR body from ONE source: the plan-bound body store,
keyed by ``--plan-id`` [+ ``--slot``]. A genuinely plan-less caller (the steward
landing cycle, an ad-hoc invocation outside any plan) passes ``--plan-id
NO_PLAN``: the sentinel resolves to the shared plan-less directory, so the SAME
store serves it.

That is the whole point of this deliverable. The retired ``--body-file`` flag
existed only because a plan-less caller had no plan directory to allocate a body
in; the sentinel removes that gap, so a second plan-less convention is no longer
justified — and a CI abstraction with two plan-less conventions is one that
callers must choose between.

This suite therefore asserts BOTH halves:

- the sentinel path works end-to-end (``--plan-id NO_PLAN`` consumes the body
  from the store and builds the ``gh pr create`` argv from it), and
- ``--body-file`` is REJECTED by the real parser as an unknown argument.

The second half is load-bearing: without it the removal would merely be
un-tested rather than asserted, and a re-introduction of the flag would be
invisible to this suite.

The GitHub provider surface (``check_auth``, ``run_gh``) is monkeypatched so no
network call occurs; the assertion is on the constructed ``gh`` argv and the
handler's validation branches. Provider stubs are set on
``_github_pr.github_ops`` (the module object the handler reaches through at call
time) so the patch lands regardless of module load order.
"""

import argparse

import pytest
from _resolve_project_dir_fixtures import NO_PLAN_SENTINEL

from conftest import load_script_module

_github_pr = load_script_module('plan-marshall', 'workflow-integration-github', '_github_pr.py', '_github_pr')
_ci_base = load_script_module('plan-marshall', 'tools-integration-ci', 'ci_base.py', 'ci_base_pr_create')


def _patch_create(monkeypatch, captured, store_calls):
    """Stub auth + run_gh and record every body-store call.

    ``captured`` receives the ``gh`` argv on each ``run_gh`` call; ``store_calls``
    receives a marker for every body-store helper invocation, so a test can
    assert the store IS reached (the sentinel path) with the plan id it was
    reached with.
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
    """Build a ``pr create`` args namespace with sensible defaults.

    ``body_file`` is deliberately ABSENT from the defaults: the handler no
    longer reads it, and seeding it here would keep a retired field alive in the
    fixture long after the production code stopped knowing about it.
    """
    base = {
        'title': 'A title',
        'plan_id': None,
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


def _pr_create_parser() -> argparse.ArgumentParser:
    """Build the REAL ``pr create`` parser via the production registrar.

    Driving ``add_pr_create_args`` rather than a hand-rolled stand-in is what
    makes the ``--body-file`` rejection below an assertion about the shipped
    argparse surface instead of about a copy of it.
    """
    parser = argparse.ArgumentParser(allow_abbrev=False)
    subparsers = parser.add_subparsers(dest='pr_command', required=True)
    _ci_base.add_pr_create_args(subparsers)
    return parser


# =============================================================================
# The sentinel IS the plan-less path
# =============================================================================


def test_sentinel_builds_argv_from_the_shared_body_store(monkeypatch):
    """``--plan-id NO_PLAN`` consumes the body from the store like any plan.

    The sentinel is not a special case in the handler — it is an ordinary plan
    id that happens to resolve to the shared plan-less directory. Asserting the
    store is reached WITH the sentinel id is what pins that.
    """
    captured: list = []
    store_calls: list = []
    _patch_create(monkeypatch, captured, store_calls)

    result = _github_pr.cmd_pr_create(_make_args(plan_id=NO_PLAN_SENTINEL))

    assert result['status'] == 'success'
    assert len(captured) == 1
    assert _flag_value(captured[0], '--body') == 'STORE body'
    assert ('read', NO_PLAN_SENTINEL) in store_calls
    assert ('delete', NO_PLAN_SENTINEL) in store_calls


def test_sentinel_passes_label_through(monkeypatch):
    """``--label`` still forwards to ``gh pr create`` on the sentinel path."""
    captured: list = []
    store_calls: list = []
    _patch_create(monkeypatch, captured, store_calls)

    result = _github_pr.cmd_pr_create(
        _make_args(plan_id=NO_PLAN_SENTINEL, label=['skip-bot-review'])
    )

    assert result['status'] == 'success'
    labels = [captured[0][i + 1] for i, tok in enumerate(captured[0]) if tok == '--label']
    assert labels == ['skip-bot-review']


def test_sentinel_is_accepted_by_the_real_parser():
    """``--plan-id NO_PLAN`` parses — the sentinel needs no special declaration."""
    args = _pr_create_parser().parse_args(
        ['create', '--title', 'T', '--plan-id', NO_PLAN_SENTINEL]
    )

    assert args.plan_id == NO_PLAN_SENTINEL


# =============================================================================
# The retired second convention is ASSERTED gone, not merely untested
# =============================================================================


def test_body_file_is_rejected_as_an_unknown_argument():
    """``--body-file`` no longer exists on ``pr create``.

    argparse exits 2 for an unrecognized argument. Without this case the flag's
    removal would be invisible here: every other test would pass equally if the
    flag were quietly re-introduced.
    """
    parser = _pr_create_parser()

    with pytest.raises(SystemExit) as exc:
        parser.parse_args(
            ['create', '--title', 'T', '--plan-id', NO_PLAN_SENTINEL, '--body-file', '/tmp/b.md']
        )

    assert exc.value.code == 2


def test_plan_id_is_required_by_the_real_parser():
    """``--plan-id`` is a plain required argument again.

    It was demoted to an optional member of a mutually-exclusive body-source
    group while ``--body-file`` existed. With the second source gone it returns
    to ``required=True``, so omitting it is an argparse rejection rather than a
    handler-level "no body source" error.
    """
    parser = _pr_create_parser()

    with pytest.raises(SystemExit) as exc:
        parser.parse_args(['create', '--title', 'T'])

    assert exc.value.code == 2


def test_missing_plan_id_is_rejected_by_the_handler(monkeypatch):
    """A direct-Namespace caller that bypasses the parser is still refused.

    The parser guarantees ``--plan-id`` for CLI callers, but the handler is also
    invoked directly with a Namespace; it must fail structurally rather than
    raise AttributeError or reach the network.
    """
    captured: list = []
    store_calls: list = []
    _patch_create(monkeypatch, captured, store_calls)

    result = _github_pr.cmd_pr_create(_make_args(plan_id=None))

    assert result['status'] == 'error'
    assert captured == []
    assert store_calls == []
    # ``make_error`` carries the human-readable text under ``error``; read both
    # keys so the assertion is about the message CONTENT, not its envelope slot.
    text = f'{result.get("error", "")} {result.get("message", "")}'
    assert NO_PLAN_SENTINEL in text, (
        'the missing-plan-id error must name the sentinel — it is the route a '
        f'genuinely plan-less caller is supposed to take; got {result!r}'
    )


# =============================================================================
# The plan-bound path is unchanged
# =============================================================================


def test_plan_bound_path_still_consumes_and_deletes_body(monkeypatch):
    """A real plan id behaves exactly as before: consume, then delete on success."""
    captured: list = []
    store_calls: list = []
    _patch_create(monkeypatch, captured, store_calls)

    result = _github_pr.cmd_pr_create(_make_args(plan_id='plan-x'))

    assert result['status'] == 'success'
    assert _flag_value(captured[0], '--body') == 'STORE body'
    assert ('read', 'plan-x') in store_calls
    assert ('delete', 'plan-x') in store_calls


def test_body_is_not_deleted_when_create_fails(monkeypatch):
    """A failed ``gh pr create`` leaves the prepared body in place for a retry.

    The delete is success-only. Pinning it matters because the retired
    ``consumed_from_store`` flag used to guard this call; with the flag gone the
    guard is the early return on failure, and nothing else asserts it.
    """
    captured: list = []
    store_calls: list = []
    _patch_create(monkeypatch, captured, store_calls)
    monkeypatch.setattr(
        _github_pr.github_ops, 'run_gh', lambda gh_args: (1, '', 'boom')
    )

    result = _github_pr.cmd_pr_create(_make_args(plan_id='plan-x'))

    assert result['status'] == 'error'
    assert ('read', 'plan-x') in store_calls
    assert ('delete', 'plan-x') not in store_calls
