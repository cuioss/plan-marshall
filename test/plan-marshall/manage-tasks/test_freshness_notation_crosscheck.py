#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the notation cross-check on ``pre-commit-verify-freshness``."""


from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

import _freshness_crosscheck as crosscheck
import file_ops
import pytest
from _freshness_notation_crosscheck_fixtures import (  # noqa: F401 — a fixture is used by NAME, not by reference
    _CURRENT_SHA,
    _NPM,
    _OTHER_SHA,
    _PYPROJECT,
    _build_entry,
    _build_is_necessary,
    _FakeQueryModule,
    _freshness_mod,
    _run,
    _stub_expected,
    _write_ledger,
    _write_status,
    cmd_pre_commit_verify_freshness,
)

from conftest import PROJECT_ROOT


@pytest.fixture(autouse=True)
def _stub_resolver_seam(monkeypatch):
    """Keep worktree-root resolution hermetic (no ``manage-status`` subprocess)."""
    monkeypatch.setattr(
        file_ops, '_query_worktree_path', lambda _plan_id: (True, str(Path.cwd()))
    )


# =============================================================================
# The record names its evidence
# =============================================================================


def test_fresh_record_names_the_matched_row(plan_context, monkeypatch, tmp_path) -> None:
    """Every field a reader needs to find the satisfying row is in the record."""
    _stub_expected(monkeypatch, {_PYPROJECT})
    result = _run(
        plan_context,
        monkeypatch,
        tmp_path,
        [
            _build_entry(worktree_sha=_OTHER_SHA),
            _build_entry(status='error'),
            _build_entry(notation=_PYPROJECT, plan_id='some-other-plan', timestamp_iso='2026-06-11T13:00:00Z'),
        ],
        'crosscheck-audit',
    )

    assert result['status'] == 'fresh', result
    assert result['matched_notation'] == _PYPROJECT
    assert result['matched_entry_index'] == 2
    assert result['matched_plan_id'] == 'some-other-plan'
    assert result['timestamp_iso'] == '2026-06-11T13:00:00Z'
    assert result['expected_notations'] == [_PYPROJECT]


def test_matched_index_addresses_the_parsed_row_not_the_file_line(
    plan_context, monkeypatch, tmp_path
) -> None:
    """``matched_entry_index`` indexes PARSED entries, which malformed lines shift.

    ``read_entries`` skips unparseable lines, so the parsed index and the
    physical line number diverge on a corrupted ledger. The parsed index is the
    one that addresses the row the gate actually read.
    """
    _stub_expected(monkeypatch, {_PYPROJECT})
    plan_dir = plan_context.plan_dir_for('crosscheck-malformed')
    _write_status(plan_dir)
    monkeypatch.setattr(_freshness_mod, 'compute_worktree_sha', lambda _root: _CURRENT_SHA)
    ledger_path = tmp_path / 'change-ledger.jsonl'
    ledger_path.write_text(
        'not json at all\n' + json.dumps(_build_entry(), sort_keys=True) + '\n',
        encoding='utf-8',
    )
    monkeypatch.setattr(_freshness_mod, 'resolve_ledger_path', lambda: ledger_path)

    result = cmd_pre_commit_verify_freshness(Namespace(plan_id='crosscheck-malformed'))

    assert result['status'] == 'fresh', result
    # Physical line 2, parsed entry 0 — the malformed line is not an entry.
    assert result['matched_entry_index'] == 0


# =============================================================================
# The structural-stale case must remain stale
# =============================================================================


def test_mutated_worktree_stays_stale_with_its_own_reason(
    plan_context, monkeypatch, tmp_path
) -> None:
    """A tree mutated after its build is still ``worktree_mutated``, not a notation refusal.

    This verdict is structural and CORRECT: the chain verifies and stamps, a
    later commit changes the tree, the gate compares and reports stale. The
    cross-check must not reach it at all — there is no candidate to check — and
    must not relabel it, or the next reader silences a true positive along with
    the false ones.
    """
    _stub_expected(monkeypatch, {_PYPROJECT})
    result = _run(
        plan_context,
        monkeypatch,
        tmp_path,
        [_build_entry(worktree_sha=_OTHER_SHA)],
        'crosscheck-mutated',
    )

    assert result['status'] == 'stale', result
    assert result['reason'] == 'worktree_mutated'
    assert 'notation_cross_check' not in result


def test_failed_build_for_current_sha_keeps_its_build_status_reason(
    plan_context, monkeypatch, tmp_path
) -> None:
    """A red build against the current tree still reports ``build_error``.

    The cross-check runs only on rows that already passed ``status == 'success'``,
    so a failing build's own remedy sentence is never displaced by a notation
    message.
    """
    _stub_expected(monkeypatch, {_PYPROJECT})
    result = _run(
        plan_context,
        monkeypatch,
        tmp_path,
        [_build_entry(status='error')],
        'crosscheck-error',
    )

    assert result['status'] == 'stale', result
    assert result['reason'] == 'build_error'
    assert 'notation_cross_check' not in result


# =============================================================================
# resolve_expected_notations — the three outcomes, directly
# =============================================================================


def test_resolver_reports_a_non_empty_set_with_no_reason(monkeypatch) -> None:
    """A resolver that finds notations returns them with ``reason is None``."""
    monkeypatch.setitem(
        __import__('sys').modules,
        '_cmd_client_query',
        _FakeQueryModule(frozenset({_PYPROJECT})),
    )
    notations, reason = crosscheck.resolve_expected_notations('.')

    assert notations == frozenset({_PYPROJECT})
    assert reason is None


def test_resolver_reports_an_unimportable_resolver_apart_from_a_failing_one(monkeypatch) -> None:
    """An unimportable resolver gets its OWN reason, not the running-failure one.

    Both pass the gate — neither is a refutation — so the distinction buys
    nothing at the gate and everything to a reader asking why the cross-check
    never corroborates anything. An unimportable resolver means THIS CHECK IS
    BROKEN and will report ``unverified`` on every row forever; an un-crawled
    project is a legitimate quiet pass.
    """
    import builtins

    real_import = builtins.__import__

    def _refuse_query_module(name, *args, **kwargs):
        if name == '_cmd_client_query':
            raise ImportError('no module named _cmd_client_query')
        return real_import(name, *args, **kwargs)

    monkeypatch.delitem(__import__('sys').modules, '_cmd_client_query', raising=False)
    monkeypatch.setattr(builtins, '__import__', _refuse_query_module)

    notations, reason = crosscheck.resolve_expected_notations('.')

    assert notations == frozenset()
    assert reason == crosscheck.REASON_RESOLVER_UNIMPORTABLE
    assert reason != crosscheck.REASON_RESOLUTION_FAILED


def test_resolver_reports_an_empty_set_as_an_inability(monkeypatch) -> None:
    """An empty resolution is 'I do not know', carrying its own reason.

    It is NOT returned as a refutation-grade answer: an un-crawled project
    resolves nothing, and treating that as 'this project builds with nothing'
    would refuse every real build row it holds.
    """
    monkeypatch.setitem(
        __import__('sys').modules, '_cmd_client_query', _FakeQueryModule(frozenset())
    )
    notations, reason = crosscheck.resolve_expected_notations('.')

    assert notations == frozenset()
    assert reason == crosscheck.REASON_NO_NOTATIONS_RESOLVED


def test_resolver_reports_a_raising_crawl_as_an_inability(monkeypatch) -> None:
    """A resolver that raises is an inability, never a refutation."""
    monkeypatch.setitem(
        __import__('sys').modules, '_cmd_client_query', _FakeQueryModule(RuntimeError('crawl blew up'))
    )
    notations, reason = crosscheck.resolve_expected_notations('.')

    assert notations == frozenset()
    assert reason == crosscheck.REASON_RESOLUTION_FAILED


# =============================================================================
# cross_check_candidates preconditions
# =============================================================================


def test_an_empty_candidate_list_is_a_precondition_violation() -> None:
    """Zero candidates has no honest verdict, so it fails fast rather than guessing.

    Both answers the code could otherwise reach are wrong: ``refuted`` would
    assert "no row carries a notation" about zero rows, and ``unverified`` would
    hand the caller a ``chosen`` position addressing nothing. The caller routes
    the no-candidate case to ``stale`` before reaching here, so arriving with an
    empty list is a programming error and is reported as one.
    """
    with pytest.raises(ValueError, match='at least one candidate'):
        crosscheck.cross_check_candidates([], '.')


def test_the_chosen_position_indexes_the_list_it_was_given(monkeypatch) -> None:
    """``chosen`` is a position, not the row object — the caller maps it back itself.

    Returning the dict instead would force the caller to recover the row's ledger
    index by ``id()``, which is sound only while this function returns one of the
    very objects it was handed — not a property its signature promises.

    The resolver is pinned so a failure here is attributable to the position
    contract and not to the live architecture; the real path has its own case.
    """
    _stub_expected(monkeypatch, {_PYPROJECT})
    outcome = crosscheck.cross_check_candidates(
        [_build_entry(notation=_NPM), _build_entry(notation=_PYPROJECT)],
        '/nonexistent-project-dir',
    )
    assert outcome['chosen'] == 1
    assert 'entry' not in outcome


# =============================================================================
# Positive control: the WHOLE real path, no seam stubbed
# =============================================================================


def test_the_real_resolution_path_refuses_and_corroborates_against_this_repository(
    plan_context, monkeypatch, tmp_path
) -> None:
    """Anti-vacuity for every case above: the unstubbed check still discriminates.

    Every other gate case here pins ``resolve_expected_notations``. If the real
    resolver could not be imported at runtime, or resolved nothing against a real
    tree, the cross-check would collapse to a permanent ``unverified`` pass — and
    all of those cases would stay green, because none of them uses it. This one
    drives the gate with NO seam stubbed but the ledger and the sha, so an import
    path or a crawl that stopped working is a test failure rather than a silent
    no-op.

    Both directions are asserted in one case on purpose: a refusal alone would
    also be produced by a resolver that resolves the empty set and (wrongly)
    treated it as a refutation, so the corroboration is what proves the set was
    really populated.
    """
    monkeypatch.setattr(
        file_ops, '_query_worktree_path', lambda _plan_id: (True, str(PROJECT_ROOT))
    )
    plan_dir = plan_context.plan_dir_for('crosscheck-live')
    _write_status(plan_dir)
    monkeypatch.setattr(_freshness_mod, 'compute_worktree_sha', lambda _root: _CURRENT_SHA)

    unrelated = _write_ledger(tmp_path, [_build_entry(notation=_NPM)])
    monkeypatch.setattr(_freshness_mod, 'resolve_ledger_path', lambda: unrelated)
    refused = cmd_pre_commit_verify_freshness(Namespace(plan_id='crosscheck-live'))

    related = tmp_path / 'related.jsonl'
    related.write_text(
        json.dumps(_build_entry(notation=_PYPROJECT), sort_keys=True) + '\n', encoding='utf-8'
    )
    monkeypatch.setattr(_freshness_mod, 'resolve_ledger_path', lambda: related)
    permitted = cmd_pre_commit_verify_freshness(Namespace(plan_id='crosscheck-live'))

    assert refused['status'] == 'stale', refused
    assert refused['reason'] == crosscheck.REASON_NOTATION_UNRELATED
    assert permitted['status'] == 'fresh', permitted
    assert permitted['notation_cross_check'] == crosscheck.CORROBORATED
    assert _PYPROJECT in permitted['expected_notations']
