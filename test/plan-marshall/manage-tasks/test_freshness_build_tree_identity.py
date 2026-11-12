#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The freshness gate matches a build row on the TREE it describes, not its hash.

A `worktree_sha` match proves the CONTENT of two trees agreed at hash time. It
does not prove the build ran in THIS tree: two checkouts of the same content hash
identically, so a row written against another root used to read as a green for
the wrong tree. The recorder now names the root it hashed and the tree hash it
captured before the build ran, and these cases pin what the gate does with that
record:

* a row hashed against another root is refused as `worktree_root_mismatch`,
  naming both roots and the row, never as an unexplained `stale`;
* a row whose dispatch hash differs from its completion hash is refused as
  `worktree_rewritten_by_build` — the build rewrote the tree it was building
  (or an edit slipped in underneath it), and the remedy is to commit the rewrite
  and re-run;
* a row that records neither field is read as today, with no mismatch claim: the
  fields were added after rows already existed, and failing closed on history is
  not the same as failing closed on evidence;
* a field that IS present but unreadable never matches, and
* the pre-existing `_stale_reason` routes keep their own reasons — the new
  discrimination must not hijack them.
"""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import file_ops
import pytest
from _pre_commit_verify_freshness_fixtures import (
    _CURRENT_SHA,
    _build_entry,
    _build_is_necessary,
    _expected_notations_resolve,
    _stub_ledger_path,
    _stub_worktree_sha,
    _write_ledger,
    _write_status,
    cmd_pre_commit_verify_freshness,
)
from _resolve_project_dir_fixtures import worktree_query_result

#: The root the gate resolves for the plan under test.
_GATE_ROOT = '/tmp/freshness-tree-identity/gate-worktree'

#: Another checkout, standing in for the main checkout a mis-dispatched build ran in.
_OTHER_ROOT = '/tmp/freshness-tree-identity/main-checkout'

_PLAN_ID = 'freshness-tree-identity'


@pytest.fixture(autouse=True)
def _stub_resolver_seam(monkeypatch):
    """Pin the ONE resolver seam so the gate's root is ``_GATE_ROOT``.

    Stubbing ``file_ops._query_worktree_path`` (rather than the gate's own
    resolution) keeps the real delegation chain executing, so the root the gate
    compares against is the one production would read.
    """
    monkeypatch.setattr(
        file_ops,
        '_query_worktree_path',
        lambda _plan_id: worktree_query_result(True, _GATE_ROOT),
    )


def _run_gate(plan_context, monkeypatch, tmp_path: Path, row: dict | list[dict]) -> dict:
    """Drive the gate over a ledger holding ``row`` (or a list of rows)."""
    rows = row if isinstance(row, list) else [row]
    _write_status(plan_context.plan_dir_for(_PLAN_ID))
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    _stub_ledger_path(monkeypatch, _write_ledger(tmp_path, rows))
    return cmd_pre_commit_verify_freshness(Namespace(plan_id=_PLAN_ID))


def _row(**extra) -> dict:
    """A successful row at the current sha that is green by the primary predicate."""
    entry = _build_entry(worktree_sha=_CURRENT_SHA)
    entry.update(extra)
    return entry


# =============================================================================
# The root the row was hashed against
# =============================================================================


def test_a_row_hashed_against_another_root_is_a_root_mismatch(plan_context, monkeypatch, tmp_path) -> None:
    """A green for another tree is refused AS another tree, naming both roots."""
    result = _run_gate(plan_context, monkeypatch, tmp_path, _row(worktree_root=_OTHER_ROOT))

    assert result['status'] == 'stale', result
    assert result['reason'] == 'worktree_root_mismatch', result
    assert _OTHER_ROOT in result['message'], 'the refusal must name the root the row recorded'
    assert _GATE_ROOT in result['message'], 'the refusal must name the root the gate hashes'
    refused = result['refused_rows']
    assert [row['worktree_root'] for row in refused] == [_OTHER_ROOT]
    assert [row['reason'] for row in refused] == ['worktree_root_mismatch']


def test_a_row_recording_the_gate_root_reads_fresh(plan_context, monkeypatch, tmp_path) -> None:
    """The same row, hashed against this tree, is evidence for this tree."""
    result = _run_gate(plan_context, monkeypatch, tmp_path, _row(worktree_root=_GATE_ROOT))

    assert result['status'] == 'fresh', result
    assert Path(result['worktree_root']).resolve() == Path(_GATE_ROOT).resolve()


def test_a_trailing_separator_is_not_a_different_tree(plan_context, monkeypatch, tmp_path) -> None:
    """Roots are compared after resolution, not byte-for-byte."""
    result = _run_gate(plan_context, monkeypatch, tmp_path, _row(worktree_root=_GATE_ROOT + '/'))

    assert result['status'] == 'fresh', result


def test_a_row_without_a_recorded_root_is_read_as_before(plan_context, monkeypatch, tmp_path) -> None:
    """A row written before the field existed carries no mismatch claim.

    This is the recorded decision for already-recorded rows: the field was added
    to a ledger that already held rows, so its absence is read as today. The
    case is a control — it would also pass on a gate that ignored the field
    entirely, which is why the mismatch case above exists beside it.
    """
    result = _run_gate(plan_context, monkeypatch, tmp_path, _row())

    assert result['status'] == 'fresh', result


def test_an_unreadable_recorded_root_never_matches(plan_context, monkeypatch, tmp_path) -> None:
    """A present-but-unreadable root fails closed rather than reading as this tree."""
    result = _run_gate(plan_context, monkeypatch, tmp_path, _row(worktree_root=17))

    assert result['status'] == 'stale', result
    assert result['reason'] == 'worktree_root_unreadable', result


# =============================================================================
# The two hashes — a build that changed the tree under itself
# =============================================================================


def test_a_row_whose_dispatch_hash_differs_names_the_rewrite(plan_context, monkeypatch, tmp_path) -> None:
    """A rewriting build is disclosed as the rewrite, with its remedy."""
    row = _row(worktree_root=_GATE_ROOT, worktree_sha_at_dispatch='0' * 64)

    result = _run_gate(plan_context, monkeypatch, tmp_path, row)

    assert result['status'] == 'stale', result
    assert result['reason'] == 'worktree_rewritten_by_build', result
    assert 'Commit the rewrite and re-run' in result['message'], result['message']
    assert [entry['reason'] for entry in result['refused_rows']] == ['worktree_rewritten_by_build']


def test_equal_dispatch_and_completion_hashes_read_fresh(plan_context, monkeypatch, tmp_path) -> None:
    """A build that changed nothing records both hashes equal and reads fresh."""
    result = _run_gate(
        plan_context,
        monkeypatch,
        tmp_path,
        _row(worktree_root=_GATE_ROOT, worktree_sha_at_dispatch=_CURRENT_SHA),
    )

    assert result['status'] == 'fresh', result


def test_a_row_without_a_dispatch_hash_matches_on_its_completion_hash(plan_context, monkeypatch, tmp_path) -> None:
    """The recorded decision: an already-recorded row matches on its completion hash."""
    result = _run_gate(plan_context, monkeypatch, tmp_path, _row(worktree_root=_GATE_ROOT))

    assert result['status'] == 'fresh', result


def test_an_unreadable_dispatch_hash_never_matches(plan_context, monkeypatch, tmp_path) -> None:
    """A present-but-unreadable dispatch hash cannot be shown stable across the build."""
    result = _run_gate(
        plan_context,
        monkeypatch,
        tmp_path,
        _row(worktree_root=_GATE_ROOT, worktree_sha_at_dispatch=[]),
    )

    assert result['status'] == 'stale', result
    assert result['reason'] == 'worktree_dispatch_hash_unreadable', result


def test_a_root_mismatch_wins_over_a_rewrite(plan_context, monkeypatch, tmp_path) -> None:
    """The headline names the more fundamental fact: the row is about another tree."""
    row = _row(worktree_root=_OTHER_ROOT, worktree_sha_at_dispatch='0' * 64)

    result = _run_gate(plan_context, monkeypatch, tmp_path, row)

    assert result['reason'] == 'worktree_root_mismatch', result


def test_a_rerun_on_the_committed_tree_clears_the_rewrite_verdict(
    plan_context, monkeypatch, tmp_path
) -> None:
    """A rewrite refusal is CLEARABLE: commit the rewrite, re-run, read fresh.

    The refusal names a remedy — commit the rewrite and re-run — so the gate must
    credit that re-run. Both rows are in the ledger at once here, which is the
    real shape: the ledger is append-only, so clearing a verdict never removes
    the row that caused it.
    """
    rewritten = _row(worktree_root=_GATE_ROOT, worktree_sha_at_dispatch='0' * 64)
    rerun = _row(worktree_root=_GATE_ROOT, worktree_sha_at_dispatch=_CURRENT_SHA)

    result = _run_gate(plan_context, monkeypatch, tmp_path, [rewritten, rerun])

    assert result['status'] == 'fresh', result


# =============================================================================
# Control — the pre-existing routes keep their own reasons
# =============================================================================


def test_a_pre_existing_stale_route_keeps_its_own_reason(plan_context, monkeypatch, tmp_path) -> None:
    """A ledger with no row for this sha is still `worktree_mutated`.

    The tree-identity discrimination only speaks about rows that MATCHED the
    primary predicate; a ledger that matches nothing must keep the cause the
    ledger actually shows.
    """
    row = _build_entry(worktree_sha='f' * 64)

    result = _run_gate(plan_context, monkeypatch, tmp_path, row)

    assert result['status'] == 'stale', result
    assert result['reason'] == 'worktree_mutated', result
    assert 'refused_rows' not in result
