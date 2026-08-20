#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``pre-commit-verify-freshness`` subcommand of manage-tasks."""


from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

import file_ops
import pytest
from _pre_commit_verify_freshness_fixtures import (  # noqa: F401 — a fixture is used by NAME, not by reference
    _CURRENT_SHA,
    _RESOLVED_NOTATIONS,
    _build_entry,
    _build_is_necessary,
    _expected_notations_resolve,  # noqa: F401 — a fixture is used by NAME, not by reference
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


def test_killed_row_is_not_reported_as_a_mutation(plan_context, monkeypatch, tmp_path) -> None:
    """The defect in one assertion: a kill is not a mutation and must not read as one."""
    _write_status(plan_context.plan_dir_for('freshness-killed-not-mutated'))
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    ledger_path = _write_ledger(
        tmp_path, [_build_entry(worktree_sha=_CURRENT_SHA, exit_code=-9, status='killed')]
    )
    _stub_ledger_path(monkeypatch, ledger_path)

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-killed-not-mutated'))

    assert result['reason'] == 'build_killed', result
    assert 'mutated' not in result['message'], result
    assert 'do not blind-retry' in result['message'], result


def test_timeout_row_is_not_reported_as_a_failing_build(
    plan_context, monkeypatch, tmp_path
) -> None:
    """A timeout is not a red test — the refusal must not describe one."""
    _write_status(plan_context.plan_dir_for('freshness-timeout-not-red'))
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    ledger_path = _write_ledger(
        tmp_path, [_build_entry(worktree_sha=_CURRENT_SHA, exit_code=0, status='timeout')]
    )
    _stub_ledger_path(monkeypatch, ledger_path)

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-timeout-not-red'))

    assert result['reason'] == 'build_timeout', result
    assert 'TIMED OUT' in result['message'], result
    assert 'Fix the reported failures' not in result['message'], result


def test_control_error_row_still_prescribes_fixing_the_code(
    plan_context, monkeypatch, tmp_path
) -> None:
    """CONTROL: a genuinely failing build still tells the caller to fix the code."""
    _write_status(plan_context.plan_dir_for('freshness-error-remedy'))
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    ledger_path = _write_ledger(
        tmp_path, [_build_entry(worktree_sha=_CURRENT_SHA, exit_code=1, status='error')]
    )
    _stub_ledger_path(monkeypatch, ledger_path)

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-error-remedy'))

    assert result['reason'] == 'build_error', result
    assert 'Fix the reported failures' in result['message'], result
    assert 'do not blind-retry' not in result['message'], result


def test_statusless_row_reports_indeterminate_not_mutation(
    plan_context, monkeypatch, tmp_path
) -> None:
    """A row with no ``status`` was still a build against this tree, not a mutation."""
    _write_status(plan_context.plan_dir_for('freshness-statusless-reason'))
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    ledger_path = _write_ledger(
        tmp_path, [_build_entry(worktree_sha=_CURRENT_SHA, exit_code=0, status=None)]
    )
    _stub_ledger_path(monkeypatch, ledger_path)

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-statusless-reason'))

    assert result['status'] == 'stale', result
    assert result['reason'] == 'build_indeterminate', result
    # A row with no readable status has no status to report. Emitting one would
    # mean inventing it, so the field's ABSENCE is the honest answer here — and
    # `reason` still separates this from the `worktree_mutated` route, which is
    # the distinction that actually changes the caller's remedy.
    assert 'observed_status' not in result, result


def test_undecidable_when_worktree_sha_unresolvable(plan_context, monkeypatch, tmp_path) -> None:
    """ledger query cannot run because the sha is undefined -> conservative fail.

    ``compute_worktree_sha`` returns ``None`` (non-git directory / repo with no
    commit), so no positive freshness proof can be established and the gate fails
    closed BEFORE the ledger is even consulted.
    """
    plan_dir = plan_context.plan_dir_for('freshness-no-sha')
    _write_status(plan_dir)
    _stub_worktree_sha(monkeypatch, None)
    # A fresh-looking ledger exists but must be irrelevant — the sha is undefined.
    ledger_path = _write_ledger(tmp_path, [_build_entry(worktree_sha=_CURRENT_SHA)])
    _stub_ledger_path(monkeypatch, ledger_path)

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-no-sha'))

    assert result['status'] == 'undecidable', result
    assert result['reason'] == 'head_unresolvable'


def test_malformed_ledger_lines_are_skipped(plan_context, monkeypatch, tmp_path) -> None:
    """A ledger with garbage lines around a valid entry still resolves fresh.

    ``read_entries`` tolerates and skips malformed JSONL lines, so a corrupt line
    must not turn a genuine fresh build into a query error.
    """
    plan_dir = plan_context.plan_dir_for('freshness-malformed')
    _write_status(plan_dir)
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    ledger_path = tmp_path / 'change-ledger.jsonl'
    valid = json.dumps(_build_entry(worktree_sha=_CURRENT_SHA), sort_keys=True)
    ledger_path.write_text(
        'not-json-at-all\n' + valid + '\n{ broken json\n', encoding='utf-8'
    )
    _stub_ledger_path(monkeypatch, ledger_path)

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-malformed'))

    assert result['status'] == 'fresh', result


def test_malformed_manifest_is_irrelevant_to_the_gate(
    plan_context, monkeypatch, tmp_path
) -> None:
    """An unparseable manifest cannot affect the gate — it is never parsed."""
    plan_dir = plan_context.plan_dir_for('freshness-nb-bad-manifest')
    _write_status(plan_dir)
    (plan_dir / 'execution.toon').write_text(
        '{ this is not valid toon\n  : : :\n', encoding='utf-8'
    )
    _stub_verdict(monkeypatch, {'decision': 'build'})
    _stub_worktree_sha(monkeypatch, _CURRENT_SHA)
    ledger_path = _write_ledger(tmp_path, [_build_entry(worktree_sha=_CURRENT_SHA)])
    _stub_ledger_path(monkeypatch, ledger_path)

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-nb-bad-manifest'))

    assert result['status'] == 'fresh', result
    assert result['worktree_sha'] == _CURRENT_SHA


# =============================================================================
# Build-necessity short-circuit — the sole build/no-build authority
# =============================================================================
#
# The gate no longer infers build necessity from the manifest's step SHAPE (the
# retired ``documentation_only`` / ``lint_only`` exemptions). It consults the one
# authority COMMAND-FREE — "does anything in this footprint need a build?" — and:
#
#   * ``not_necessary`` -> short-circuit to ``fresh`` BEFORE the ledger scan,
#     forwarding the verdict's OWN ``reason`` verbatim. No ``kind=build`` entry
#     could legally exist for a footprint that needs no build, so demanding one
#     would be an impossible demand rather than a gate.
#   * ``build``         -> fall through to the ledger scan unchanged.
#
# The manifest is written in several cases below purely as a DECOY: whatever its
# step list looks like, it must not move the outcome.


def test_not_necessary_verdict_short_circuits_to_fresh(
    plan_context, monkeypatch, tmp_path
) -> None:
    """A ``not_necessary`` verdict -> fresh, before the ledger is ever consulted.

    Fail-closed boundary values (``None`` sha, missing ledger file) prove the
    short-circuit fires ahead of them: had the gate reached the scan, the ``None``
    sha would have forced ``undecidable / head_unresolvable``.
    """
    plan_dir = plan_context.plan_dir_for('freshness-no-build-needed')
    _write_status(plan_dir)
    _stub_verdict(
        monkeypatch,
        {'decision': 'not_necessary', 'reason': 'plan footprint touches no build_map glob'},
    )
    _stub_worktree_sha(monkeypatch, None)
    _stub_ledger_path(monkeypatch, tmp_path / 'never-written.jsonl')

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='freshness-no-build-needed'))

    assert result['status'] == 'fresh', result
    assert result['plan_id'] == 'freshness-no-build-needed'
    # No ledger fields — the short-circuit returns before the scan.
    assert 'worktree_sha' not in result
    assert 'ledger_path' not in result
