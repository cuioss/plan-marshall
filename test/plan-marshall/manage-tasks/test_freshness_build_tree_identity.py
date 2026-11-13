#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The freshness gate matches a build row on the TREE it describes, not its hash.

A `worktree_sha` match proves the CONTENT of two trees agreed at hash time. It
does not prove the build ran in THIS tree: two checkouts of the same content hash
identically, so a row written against another root is a green for the wrong tree
unless the gate compares the roots. The recorder names the root it hashed and the
tree hash it captured before the build ran, and these cases pin what the gate
does with that record:

* a row hashed against another root is refused as `worktree_root_mismatch`,
  naming both roots and the row, never as an unexplained `stale`;
* a row whose dispatch hash differs from its completion hash is refused as
  `worktree_rewritten_by_build` — the build rewrote the tree it was building
  (or an edit slipped in underneath it), and the remedy is to commit the rewrite
  and re-run;
* a row carrying no such KEY is read on its completion hash with no mismatch
  claim: that absence is the legacy shape, and it is not the same as evidence;
* a key that IS present but unreadable — an explicit `null` included — never
  matches, and
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
    verdict: dict = cmd_pre_commit_verify_freshness(Namespace(plan_id=_PLAN_ID))
    return verdict


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


def test_a_root_the_filesystem_refuses_is_a_refusal_not_a_crash(plan_context, monkeypatch, tmp_path) -> None:
    """An embedded NUL cannot become a path — the gate must refuse, never raise.

    A ledger row is untrusted input: JSON can carry ``"a\\u0000b"`` as a string,
    and ``Path.resolve()`` raises ``ValueError`` for it. A gate whose whole job
    is to fail closed must answer `stale`, not a traceback — and the route must
    be the unreadable one, because nothing was hashed against a string that is
    not a path at all.
    """
    result = _run_gate(plan_context, monkeypatch, tmp_path, _row(worktree_root='a\x00b'))

    assert result['status'] == 'stale', result
    assert result['reason'] == 'worktree_root_unreadable', result


def test_a_build_row_that_recorded_no_tree_is_named_as_unrecorded(plan_context, monkeypatch, tmp_path) -> None:
    """This plan's own row with no hash gets its own cause, not 'the tree was mutated'.

    Telling a caller to "re-dispatch a build" reproduces the same unrecorded row,
    so the refusal names the resolution instead.
    """
    result = _run_gate(
        plan_context,
        monkeypatch,
        tmp_path,
        _build_entry(plan_id=_PLAN_ID, worktree_sha=None),
    )

    assert result['status'] == 'stale', result
    assert result['reason'] == 'build_tree_unrecorded', result
    assert result['observed_status'] == 'success', (
        "the newest row's own status is published on this route, and it is that row's "
        'status — not a verdict about this sha'
    )
    assert 're-running' in result['message'].lower(), result['message']


def test_another_plans_unrecorded_row_does_not_relabel_this_plans_mutation(plan_context, monkeypatch, tmp_path) -> None:
    """Attribution is by plan: the ledger is shared by every plan in the repository.

    An unrecorded row carries no root to compare, so another plan's unrecorded
    build must not turn this plan's changed tree into a resolution fault.
    """
    other_plan_unrecorded = _build_entry(plan_id='some-other-plan', worktree_sha=None)

    result = _run_gate(plan_context, monkeypatch, tmp_path, other_plan_unrecorded)

    assert result['status'] == 'stale', result
    assert result['reason'] == 'worktree_mutated', result


def test_an_explicit_null_dispatch_hash_never_matches(plan_context, monkeypatch, tmp_path) -> None:
    """A row that PRESENTS the key with ``null`` is refused, not read as legacy.

    The current writer always writes both keys and writes ``null`` for a fact it
    could not establish, so an explicit null means "this build could not capture
    its tree" — the one case where a mid-build rewrite is invisible. Admitting it
    would let exactly that build pass as fresh.
    """
    result = _run_gate(
        plan_context,
        monkeypatch,
        tmp_path,
        _row(worktree_root=_GATE_ROOT, worktree_sha_at_dispatch=None),
    )

    assert result['status'] == 'stale', result
    assert result['reason'] == 'worktree_dispatch_hash_unreadable', result


def test_an_explicit_null_root_never_matches(plan_context, monkeypatch, tmp_path) -> None:
    """The same rule for the root: a presented ``null`` is unreadable, not legacy."""
    result = _run_gate(plan_context, monkeypatch, tmp_path, _row(worktree_root=None))

    assert result['status'] == 'stale', result
    assert result['reason'] == 'worktree_root_unreadable', result


def test_a_routing_seam_row_is_not_read_as_a_failed_capture(plan_context, monkeypatch, tmp_path) -> None:
    """CONTROL: the seam's deliberately hash-less row keeps the mutation answer.

    `_append_gate_build_row` writes ``worktree_sha=None`` on purpose (resolving the
    hash there would run git after the build). Reading that omission as a failed
    capture would send an operator to repair a resolution that works.
    """
    seam_row = _build_entry(plan_id=_PLAN_ID, worktree_sha=None)
    seam_row['outcome'] = {'route': 'in_process'}

    result = _run_gate(plan_context, monkeypatch, tmp_path, seam_row)

    assert result['status'] == 'stale', result
    assert result['reason'] == 'worktree_mutated', result


def test_an_old_unrecorded_row_does_not_hide_a_later_mutation(plan_context, monkeypatch, tmp_path) -> None:
    """CONTROL: the unrecorded route is scoped to the NEWEST build row.

    The ledger is one shared, append-only, never-rewritten file per repository, so
    an unscoped "any row is unrecorded" would relabel every later mutation for
    ever — and would name a resolution fault where the current build recorded its
    tree perfectly well.
    """
    stale_unrecorded = _build_entry(plan_id=_PLAN_ID, worktree_sha=None)
    later_mutation = _build_entry(plan_id=_PLAN_ID, worktree_sha='f' * 64)

    result = _run_gate(plan_context, monkeypatch, tmp_path, [stale_unrecorded, later_mutation])

    assert result['status'] == 'stale', result
    assert result['reason'] == 'worktree_mutated', result


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


def test_a_rerun_on_the_committed_tree_clears_the_rewrite_verdict(plan_context, monkeypatch, tmp_path) -> None:
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
