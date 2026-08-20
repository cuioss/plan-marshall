#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``pre-commit-verify-freshness`` subcommand of manage-tasks.

Scope: that an unresolvable worktree falls back to the current directory.
"""


from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import file_ops
from _pre_commit_verify_freshness_fixtures import (  # noqa: F401 — a fixture is used by NAME, not by reference
    _RESOLVED_NOTATIONS,
    _build_entry,
    _build_is_necessary,
    _capture_worktree_root,
    _expected_notations_resolve,  # noqa: F401 — a fixture is used by NAME, not by reference
    _stub_expected_notations,
    _stub_ledger_path,
    _stub_verdict,
    _write_ledger,
    _write_status,
    cmd_pre_commit_verify_freshness,
)


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
