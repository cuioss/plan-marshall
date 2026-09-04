#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the verdict ``pre-commit-verify-freshness`` returns, and its reason.

Fresh requires a matching build entry for the current sha, across resolved
notations and among unrelated entries. Everything else is stale: an empty or
absent ledger, an entry for a different sha, and a build for THIS sha that
failed, timed out, was killed, or carries no status at all. The last three tests
hold the stated reason to the row it was actually read from.

⛔ **The routes exercised here are the ``_stale_reason`` ones only, and they are
not the whole `reason` vocabulary.** Four further routes —
``notation_unrelated``, ``notation_absent``, ``build_scope_narrow`` and
``no_row_both_attributable_and_adequate`` — are produced by the two cross-check
dimensions rather than by ``_stale_reason``, and are covered in
``test_freshness_notation_crosscheck.py``. This file's enumeration is therefore
deliberately PARTIAL over the gate's reasons; a reader who took it for the
complete set would conclude a cross-check refusal cannot happen.
"""


from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import _freshness_crosscheck as crosscheck
import file_ops
import pytest
from _pre_commit_verify_freshness_fixtures import (
    _CURRENT_SHA,
    _OTHER_SHA,
    _RESOLVED_NOTATIONS,
    _build_entry,
    _build_is_necessary,
    _change_entry,
    _expected_notations_resolve,
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


def test_a_pass_publishes_the_coverage_dimension_at_its_honest_value(
    plan_context, monkeypatch, tmp_path
) -> None:
    """The scope dimension reaches the pass payload, and does NOT default to ``covered``.

    This file's rows are notation-shaped: their ``args`` carries no
    ``--command-args``, so the coverage dimension genuinely cannot read them. The
    pass must therefore say ``undetermined`` with a named reason, not stay silent
    and not report ``covered``.

    ⛔ Both halves are the point. A missing ``scope_cross_check`` key would make
    every existing case in this file pass while the dimension was never wired to
    the payload at all; a ``covered`` value would be the permissive default that
    re-opens the false-green — the check would announce it had verified coverage
    it never looked at. Asserting the exact ``undetermined`` value is what
    distinguishes "wired and honest" from either failure.
    """
    plan_dir = plan_context.plan_dir_for('freshness-scope-published')
    _write_status(plan_dir)
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    ledger_path = _write_ledger(tmp_path, [_build_entry(worktree_sha=_CURRENT_SHA)])
    _stub_ledger_path(monkeypatch, ledger_path)

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-scope-published'))

    assert result['status'] == 'fresh', result
    assert result['scope_cross_check'] == crosscheck.UNDETERMINED, result
    assert result['scope_cross_check_reason'] in {
        crosscheck.REASON_SCOPE_UNREADABLE,
        crosscheck.REASON_REQUIRED_COVERAGE_UNKNOWN,
        crosscheck.REASON_VOCABULARY_UNIMPORTABLE,
    }, result
    # ``row_scopes`` is published on the pass path too, so a reader can see what
    # each candidate recorded rather than only the aggregate verdict.
    assert 'row_scopes' in result


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
# The two ``notation_*`` routes and the two coverage routes
# (``build_scope_narrow``, ``no_row_both_attributable_and_adequate``) are NOT
# exercised here: all four come from the cross-check rather than from
# ``_stale_reason``, and live in ``test_freshness_notation_crosscheck.py``.
# =============================================================================

def test_fresh_match_is_tier_agnostic_across_resolved_notations(
    plan_context, monkeypatch, tmp_path
) -> None:
    """A non-pyproject, plan-less (``plan_id=None``) build still satisfies the gate.

    The primary predicate filters on ``kind``, ``status`` and ``worktree_sha``
    and never on ``plan_id`` — so a Maven build from an orchestrator-driven
    global-tier run with ``plan_id=None`` proves freshness exactly as a
    plan-scoped pyproject build does. Tier-agnosticism is what this pins.

    It is NOT notation-agnosticism: the row passes because Maven is in the
    architecture-resolved notation set (the pinned fixture), not because the
    gate ignores notations. A notation OUTSIDE that set is refused —
    ``test_freshness_notation_crosscheck*.py`` pins that half.
    """
    plan_dir = plan_context.plan_dir_for('freshness-agnostic')
    _write_status(plan_dir)
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    ledger_path = _write_ledger(
        tmp_path,
        [
            _build_entry(
                worktree_sha=_CURRENT_SHA,
                notation='plan-marshall:build-maven:maven',
                plan_id=None,
            )
        ],
    )
    _stub_ledger_path(monkeypatch, ledger_path)

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-agnostic'))

    assert result['status'] == 'fresh', result
    assert result['matched_notation'] == 'plan-marshall:build-maven:maven'


def test_fresh_among_mixed_entries(plan_context, monkeypatch, tmp_path) -> None:
    """The matching successful build is found among non-matching noise entries."""
    plan_dir = plan_context.plan_dir_for('freshness-mixed')
    _write_status(plan_dir)
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    ledger_path = _write_ledger(
        tmp_path,
        [
            _change_entry(worktree_sha=_OTHER_SHA),
            _build_entry(worktree_sha=_OTHER_SHA),
            _build_entry(worktree_sha=_CURRENT_SHA, exit_code=1, status='error'),
            _build_entry(worktree_sha=_CURRENT_SHA, exit_code=0, status='timeout'),
            _build_entry(worktree_sha=_CURRENT_SHA, notation='plan-marshall:build-npm:npm'),
        ],
    )
    _stub_ledger_path(monkeypatch, ledger_path)

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-mixed'))

    assert result['status'] == 'fresh', result
    assert result['matched_notation'] == 'plan-marshall:build-npm:npm'


# =============================================================================
# Tests
# =============================================================================

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
# The two ``notation_*`` routes and the two coverage routes
# (``build_scope_narrow``, ``no_row_both_attributable_and_adequate``) are NOT
# exercised here: all four come from the cross-check rather than from
# ``_stale_reason``, and live in ``test_freshness_notation_crosscheck.py``.
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


def test_stale_reason_reads_the_most_recent_matching_row(
    plan_context, monkeypatch, tmp_path
) -> None:
    """Several non-green builds against one tree: the LATEST one is the reason."""
    _write_status(plan_context.plan_dir_for('freshness-latest-row'))
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    ledger_path = _write_ledger(
        tmp_path,
        [
            _build_entry(worktree_sha=_CURRENT_SHA, exit_code=1, status='error'),
            _build_entry(worktree_sha=_CURRENT_SHA, exit_code=-9, status='killed'),
        ],
    )
    _stub_ledger_path(monkeypatch, ledger_path)

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-latest-row'))

    assert result['reason'] == 'build_killed', result
