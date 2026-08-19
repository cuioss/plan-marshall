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
    _CURRENT_SHA,
    _OTHER_SHA,
    _RESOLVED_NOTATIONS,
    _build_entry,
    _change_entry,
    _stub_expected_notations,
    _stub_ledger_path,
    _stub_verdict,
    _stub_worktree_sha,
    _write_ledger,
    _write_status,
    cmd_pre_commit_verify_freshness,
)
from _resolve_project_dir_fixtures import (
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


# =============================================================================
# Tests
# =============================================================================


def test_fresh_when_matching_build_entry_present(plan_context, monkeypatch, tmp_path) -> None:
    """status: fresh — ledger has a successful build for the current sha."""
    plan_dir = plan_context.plan_dir_for('freshness-fresh')
    _write_status(plan_dir)
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    ledger_path = _write_ledger(tmp_path, [_build_entry(worktree_sha=_CURRENT_SHA)])
    _stub_ledger_path(monkeypatch, ledger_path)

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-fresh'))

    assert result['status'] == 'fresh', result
    assert result['plan_id'] == 'freshness-fresh'
    assert result['worktree_sha'] == _CURRENT_SHA
    assert result['matched_notation'] == 'plan-marshall:build-pyproject:pyproject_build'


def test_stale_when_ledger_empty(plan_context, monkeypatch, tmp_path) -> None:
    """ledger empty -> fail closed (undecidable / no_registry)."""
    plan_dir = plan_context.plan_dir_for('freshness-empty')
    _write_status(plan_dir)
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    ledger_path = _write_ledger(tmp_path, [])
    _stub_ledger_path(monkeypatch, ledger_path)

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-empty'))

    assert result['status'] == 'undecidable', result
    assert result['reason'] == 'no_registry'
    assert result['worktree_sha'] == _CURRENT_SHA
    assert 'ledger_path' in result


def test_stale_when_ledger_absent(plan_context, monkeypatch, tmp_path) -> None:
    """ledger file missing entirely -> fail closed (undecidable / no_registry)."""
    plan_dir = plan_context.plan_dir_for('freshness-no-file')
    _write_status(plan_dir)
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    # Point at a path that was never written.
    _stub_ledger_path(monkeypatch, tmp_path / 'never-written.jsonl')

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-no-file'))

    assert result['status'] == 'undecidable', result
    assert result['reason'] == 'no_registry'


def test_stale_when_build_entry_for_different_sha(plan_context, monkeypatch, tmp_path) -> None:
    """ledger has a successful build but for a DIFFERENT sha -> stale (fail)."""
    plan_dir = plan_context.plan_dir_for('freshness-diff-sha')
    _write_status(plan_dir)
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    # Successful build, wrong worktree_sha — the worktree mutated since the build.
    ledger_path = _write_ledger(tmp_path, [_build_entry(worktree_sha=_OTHER_SHA)])
    _stub_ledger_path(monkeypatch, ledger_path)

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-diff-sha'))

    assert result['status'] == 'stale', result
    assert result['worktree_sha'] == _CURRENT_SHA


def test_stale_when_only_failed_build_for_current_sha(plan_context, monkeypatch, tmp_path) -> None:
    """A build entry matches the sha but ``status != success`` -> stale (fail closed)."""
    plan_dir = plan_context.plan_dir_for('freshness-failed-build')
    _write_status(plan_dir)
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    ledger_path = _write_ledger(
        tmp_path, [_build_entry(worktree_sha=_CURRENT_SHA, exit_code=1, status='error')]
    )
    _stub_ledger_path(monkeypatch, ledger_path)

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-failed-build'))

    assert result['status'] == 'stale', result


def test_stale_when_timeout_build_exits_zero_for_current_sha(
    plan_context, monkeypatch, tmp_path
) -> None:
    """THE false-fresh regression: ``exit_code: 0`` + ``status: timeout`` -> stale.

    The build wrapper exits 0 on timeout (the outcome is modeled in its stdout
    TOON, not the exit code). Before the ``status`` predicate, this row proved
    freshness — a build that never finished laundered into a false ``fresh``.
    The gate must now report ``stale`` for it despite the matching sha and the
    zero exit code.
    """
    plan_dir = plan_context.plan_dir_for('freshness-timeout-build')
    _write_status(plan_dir)
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    ledger_path = _write_ledger(
        tmp_path,
        [_build_entry(worktree_sha=_CURRENT_SHA, exit_code=0, status='timeout')],
    )
    _stub_ledger_path(monkeypatch, ledger_path)

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-timeout-build'))

    assert result['status'] == 'stale', result


def test_stale_when_killed_build_matches_sha(plan_context, monkeypatch, tmp_path) -> None:
    """A ``status: killed`` row (signal-terminated child) must not prove freshness."""
    plan_dir = plan_context.plan_dir_for('freshness-killed-build')
    _write_status(plan_dir)
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    ledger_path = _write_ledger(
        tmp_path,
        [_build_entry(worktree_sha=_CURRENT_SHA, exit_code=-9, status='killed')],
    )
    _stub_ledger_path(monkeypatch, ledger_path)

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-killed-build'))

    assert result['status'] == 'stale', result


def test_stale_when_row_lacks_status_key(plan_context, monkeypatch, tmp_path) -> None:
    """A pre-change row without a ``status`` key never matches (fail-closed)."""
    plan_dir = plan_context.plan_dir_for('freshness-statusless-row')
    _write_status(plan_dir)
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    ledger_path = _write_ledger(
        tmp_path,
        [_build_entry(worktree_sha=_CURRENT_SHA, exit_code=0, status=None)],
    )
    _stub_ledger_path(monkeypatch, ledger_path)

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-statusless-row'))

    assert result['status'] == 'stale', result


def test_stale_when_only_change_entry_matches_sha(plan_context, monkeypatch, tmp_path) -> None:
    """A ``kind=change`` entry for the current sha must NOT satisfy the gate."""
    plan_dir = plan_context.plan_dir_for('freshness-change-only')
    _write_status(plan_dir)
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    ledger_path = _write_ledger(tmp_path, [_change_entry(worktree_sha=_CURRENT_SHA)])
    _stub_ledger_path(monkeypatch, ledger_path)

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-change-only'))

    assert result['status'] == 'stale', result


# =============================================================================
# The ``stale`` REASON — a distinct remedy per route
#
# The gate's pass/fail behaviour is identical on every route below (only
# ``fresh`` ever permits), so these cases pin the half that differs: what the
# refusal SAYS. The historical single message asserted "the worktree has been
# mutated since the last observed build ... re-dispatch a build before
# retrying" on every one of them — a cause the gate never established, and a
# remedy that is exactly the blind retry a ``killed`` build forbids.
#
# The two ``notation_*`` routes are NOT exercised here: they come from the
# cross-check rather than from ``_stale_reason``, and live in
# ``test_freshness_notation_crosscheck.py``.
# =============================================================================


@pytest.mark.parametrize(
    ('row_status', 'expected_reason'),
    [
        ('error', 'build_error'),
        ('timeout', 'build_timeout'),
        ('killed', 'build_killed'),
        ('unknown', 'build_indeterminate'),
        # A status outside the vocabulary resolves to indeterminate rather than
        # being folded into a neighbour — an unresolvable case is its own answer.
        ('some-future-status', 'build_indeterminate'),
    ],
)
def test_stale_reason_names_the_observed_build_status(
    plan_context, monkeypatch, tmp_path, row_status, expected_reason
) -> None:
    """A build WAS observed against this tree — the refusal must say which kind."""
    plan_id = f'freshness-reason-{row_status}'
    _write_status(plan_context.plan_dir_for(plan_id))
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    ledger_path = _write_ledger(
        tmp_path, [_build_entry(worktree_sha=_CURRENT_SHA, exit_code=-1, status=row_status)]
    )
    _stub_ledger_path(monkeypatch, ledger_path)

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id=plan_id))

    assert result['status'] == 'stale', result
    assert result['reason'] == expected_reason, result
    assert result['observed_status'] == row_status, result


def test_stale_reason_is_mutation_only_when_no_row_carries_the_sha(
    plan_context, monkeypatch, tmp_path
) -> None:
    """CONTROL: a genuinely-mutated tree still reports the mutation reason."""
    _write_status(plan_context.plan_dir_for('freshness-reason-mutated'))
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    ledger_path = _write_ledger(tmp_path, [_build_entry(worktree_sha=_OTHER_SHA)])
    _stub_ledger_path(monkeypatch, ledger_path)

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-reason-mutated'))

    assert result['status'] == 'stale', result
    assert result['reason'] == 'worktree_mutated', result
    # No row was observed for this sha, so there is no status to report.
    assert 'observed_status' not in result, result
    assert 'mutated' in result['message']
