#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``pre-commit-verify-freshness`` subcommand of manage-tasks.

The subcommand answers a single deterministic question — "does the unified
change-ledger contain a ``kind=build`` entry with ``status == 'success'`` whose
``worktree_sha`` equals the CURRENT working-tree currency hash?" — and returns
one of three statuses (``fresh``, ``stale``, ``undecidable``) for the
orchestrator to consume as a fail-closed gate. Matching on ``status`` rather
than ``exit_code`` is load-bearing: the build wrapper exits 0 on timeout, so an
exit-code predicate would launder a build that never finished into a false
``fresh`` (regression covered below). See
``marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md`` §
"Pre-Commit Verify Freshness" for the contract.

Before that question is asked at all, the gate consults the single build/no-build
authority (``extension_base.should_execute_build``, the ``manage-config
build-decision`` verb) COMMAND-FREE. A ``not_necessary`` verdict means no
``kind=build`` entry could ever legally exist for this footprint, so the gate
short-circuits to ``fresh`` carrying the verdict's OWN ``reason`` verbatim. The
gate derives no build-necessity signal of its own — it neither reads the
manifest's step shapes nor owns an exemption vocabulary. See ADR-004 §
"Amendment: ``build-decision`` is the sole build/no-build authority".

The freshness primitive is the change-ledger lookup, NOT a file-mtime heuristic.
Tests stub the three module-level boundary functions the command uses:

- ``compute_worktree_sha`` — the working-tree currency hash. Stubbed to a
  deterministic literal so the lookup match is exercised without standing up a
  real git worktree. Returning ``None`` exercises the ``head_unresolvable``
  fail-closed path.
- ``resolve_ledger_path`` — the tracked-config-dir ledger location. Stubbed to a
  temp JSONL file so the test controls the ledger entries directly.
- ``_build_necessity_verdict`` — the command-free consult of the sole authority.
  An autouse fixture pins it to ``build`` so every ledger-scan case reaches the
  scan; the build-necessity cases override it explicitly.

Together they make the gate's three-way decision (``fresh`` / ``stale`` /
``undecidable``) deterministic and isolated from git, the real ledger, and the
live project footprint.
"""


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
    CANONICAL_WORKTREE,
    MAIN_CHECKOUT_ROOT,
    NO_PLAN_SENTINEL,
    patch_main_checkout_root,
    patch_query_worktree_path,
    worktree_query_result,
)


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
    ``test_freshness_notation_crosscheck.py``.
    """
    _stub_expected_notations(monkeypatch, _RESOLVED_NOTATIONS)


def test_worktree_root_routes_through_the_resolver(
    plan_context, monkeypatch, tmp_path
) -> None:
    """The root reaches the single ``get-worktree-path`` seam, exactly once."""
    plan_dir = plan_context.plan_dir_for('freshness-routing')
    _write_status(plan_dir)
    seen = _capture_worktree_root(monkeypatch)
    _stub_ledger_path(monkeypatch, _write_ledger(tmp_path, [_build_entry()]))

    with patch_query_worktree_path(True) as mock:
        cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-routing'))

    assert seen == [Path(CANONICAL_WORKTREE)]
    assert mock.call_count == 1, (
        'the freshness gate did not reach the single resolver seam exactly once '
        f'(call_count={mock.call_count})'
    )


def test_worktree_root_ignores_status_metadata(
    plan_context, monkeypatch, tmp_path
) -> None:
    """A ``status.metadata.worktree_path`` decoy must NOT steer the resolution.

    The retired implementation read exactly this field. Seeding it with a path
    the resolver does not return proves the hand-read is gone: if the decoy ever
    wins again, the resolver has been bypassed.
    """
    plan_dir = plan_context.plan_dir_for('freshness-decoy')
    decoy = tmp_path / 'decoy-worktree'
    decoy.mkdir()
    _write_status(plan_dir, worktree_path=str(decoy))
    seen = _capture_worktree_root(monkeypatch)
    _stub_ledger_path(monkeypatch, _write_ledger(tmp_path, [_build_entry()]))

    with patch_query_worktree_path(True):
        cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-decoy'))

    assert seen == [Path(CANONICAL_WORKTREE)], (
        'the gate followed status.metadata.worktree_path instead of the resolver'
    )


def test_no_plan_sentinel_resolves_to_the_main_checkout(
    plan_context, monkeypatch, tmp_path
) -> None:
    """``NO_PLAN`` resolves to the main checkout without shelling out."""
    plan_context.plan_dir_for(NO_PLAN_SENTINEL)
    seen = _capture_worktree_root(monkeypatch)
    _stub_ledger_path(monkeypatch, _write_ledger(tmp_path, [_build_entry()]))

    with patch_query_worktree_path(True) as mock, patch_main_checkout_root():
        cmd_pre_commit_verify_freshness(Namespace(plan_id=NO_PLAN_SENTINEL))

    assert seen == [Path(MAIN_CHECKOUT_ROOT)]
    assert mock.call_count == 0, 'the sentinel must never reach get-worktree-path'


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
