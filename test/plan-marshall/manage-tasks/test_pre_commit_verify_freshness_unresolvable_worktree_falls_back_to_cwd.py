#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``pre-commit-verify-freshness`` subcommand of manage-tasks."""


from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import file_ops
import pytest
from _pre_commit_verify_freshness_fixtures import (
    _RESOLVED_NOTATIONS,
    _build_entry,
    _capture_worktree_root,
    _stub_expected_notations,
    _stub_ledger_path,
    _stub_verdict,
    _write_ledger,
    _write_status,
    cmd_pre_commit_verify_freshness,
)
from _resolve_project_dir_fixtures import (
    worktree_query_result,
)

# =============================================================================
# Fixture builders
# =============================================================================

@pytest.fixture(autouse=True)
def _stub_resolver_seam(monkeypatch):
    """Stub the ONE resolver seam so no case shells out to ``manage-status``.

    The gate resolves its worktree root through ``resolve_plan_context``, whose
    only external touch point is ``file_ops._query_worktree_path``. Stubbing
    that seam (rather than the gate's own resolution) keeps the real delegation
    chain executing while making every case hermetic and subprocess-free.
    """
    monkeypatch.setattr(
        file_ops,
        '_query_worktree_path',
        lambda _plan_id: worktree_query_result(True, str(Path.cwd())),
    )


@pytest.fixture(autouse=True)
def _build_is_necessary(monkeypatch):
    """Default every case to a ``build`` verdict so the ledger scan is reached.

    A ``build`` verdict is the pass-through: the gate falls straight to the ledger
    scan, which is what the bulk of this file exercises. Cases that exercise the
    short-circuit override this with an explicit ``_stub_verdict`` call.
    """
    _stub_verdict(monkeypatch, {'decision': 'build'})


@pytest.fixture(autouse=True)
def _expected_notations_resolve(monkeypatch):
    """Pin the notation cross-check's resolved set for every case in this file.

    The real resolver runs the live architecture crawl against the checkout,
    which would make every case here depend on the working tree AND pay for a
    crawl per test. Pinning the set to the notations this file's fixtures use
    isolates the gate's own logic from the resolver's; the resolver's own
    behaviour — including what it does when resolution fails — is covered in
    ``test_freshness_notation_crosscheck*.py``.
    """
    _stub_expected_notations(monkeypatch, _RESOLVED_NOTATIONS)


# =============================================================================
# Resolver-migration contract
# =============================================================================

def test_unresolvable_worktree_falls_back_to_cwd(
    plan_context, monkeypatch, tmp_path
) -> None:
    """An unresolvable worktree degrades to cwd rather than aborting the gate.

    The fallback is deliberate and predates the migration: a plan whose worktree
    metadata is unusable must still receive a freshness VERDICT (which will fail
    closed on the ledger scan), never an exception that skips the gate entirely.
    """
    plan_dir = plan_context.plan_dir_for('freshness-unresolvable')
    _write_status(plan_dir)
    seen = _capture_worktree_root(monkeypatch)
    _stub_ledger_path(monkeypatch, _write_ledger(tmp_path, [_build_entry()]))

    def _raise(_plan_id):
        raise file_ops.WorktreeResolutionError('deliberately unresolvable')

    monkeypatch.setattr(file_ops, '_query_worktree_path', _raise)

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-unresolvable'))

    assert seen == [Path.cwd()]
    assert result['status'] in ('fresh', 'stale', 'undecidable')
