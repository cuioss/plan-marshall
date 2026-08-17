#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the notation cross-check on ``pre-commit-verify-freshness``.

The gate's primary predicate ("a ``kind=build`` row with ``status == 'success'``
and a matching ``worktree_sha`` exists") asserts a row EXISTS; it never asks
whether the row is evidence of a build THIS project performs. This file pins the
check that closes that gap, in BOTH directions — because a one-directional fix
trades one false signal for its mirror:

* **Refusal direction.** A matching row whose notation the project's
  architecture does not resolve is refused (``stale`` / ``notation_unrelated``).
  Against the pre-change gate the same ledger returned ``fresh`` with no
  indication anything was odd, which is what made the defect undetectable.
* **Acceptance direction.** A project that legitimately builds with several
  notations still passes, including when an unrelated row sits AHEAD of the
  related one in ledger file order — a first-match return would refuse it.

Two further properties are pinned here because losing either would reintroduce
a defect this work exists to close:

* **The record names its evidence.** A ``fresh`` verdict carries the matched
  notation, the matched row's index in the ledger, its ``plan_id`` and its
  timestamp, plus the cross-check verdict and the resolved notation set. A pass
  is auditable rather than a bare assertion.
* **Structural stale verdicts stay stale.** A tree mutated after its last build
  is correctly ``stale``, and nothing here re-stamps or relaxes the sha
  comparison to make it pass. Weakening that would reintroduce the false-green
  class the cross-check exists to close.

The resolver seam (``resolve_expected_notations``) is stubbed in the gate-level
cases so no case runs the live architecture crawl; the resolver's own
three-outcome contract is exercised directly against
``_freshness_crosscheck``.
"""

from __future__ import annotations

import importlib.util
import json
from argparse import Namespace
from pathlib import Path

import _freshness_crosscheck as crosscheck
import file_ops
import pytest

from conftest import PROJECT_ROOT

_SCRIPTS_DIR = (
    PROJECT_ROOT
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-tasks'
    / 'scripts'
)


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


_freshness_mod = _load_module(
    '_cmd_pre_commit_verify_freshness_crosscheck_under_test',
    '_cmd_pre_commit_verify_freshness.py',
)
cmd_pre_commit_verify_freshness = _freshness_mod.cmd_pre_commit_verify_freshness

_CURRENT_SHA = 'a' * 64
_OTHER_SHA = 'b' * 64

_PYPROJECT = 'plan-marshall:build-pyproject:pyproject_build'
_MAVEN = 'plan-marshall:build-maven:maven'
_NPM = 'plan-marshall:build-npm:npm'
_GRADLE = 'plan-marshall:build-gradle:gradle'


# =============================================================================
# Fixture builders
# =============================================================================


def _build_entry(
    *,
    worktree_sha: str | None = _CURRENT_SHA,
    status: str | None = 'success',
    notation: str | None = _PYPROJECT,
    plan_id: str | None = 'crosscheck-test',
    timestamp_iso: str = '2026-06-11T12:00:00Z',
) -> dict:
    """Construct a ``kind=build`` ledger row.

    ``notation=None`` omits the key entirely, modelling a row no dispatch
    boundary could have written (``build_record`` requires the field), which is
    the shape a hand-appended or test-authored row most easily takes.
    """
    entry: dict = {
        'kind': 'build',
        'plan_id': plan_id,
        'args': 'run',
        'exit_code': 0,
        'worktree_sha': worktree_sha,
        'log_file': None,
        'timestamp_iso': timestamp_iso,
    }
    if notation is not None:
        entry['notation'] = notation
    if status is not None:
        entry['status'] = status
    return entry


def _write_ledger(tmp_path: Path, entries: list[dict]) -> Path:
    ledger_path = tmp_path / 'change-ledger.jsonl'
    ledger_path.write_text(
        ''.join(json.dumps(entry, sort_keys=True) + '\n' for entry in entries),
        encoding='utf-8',
    )
    return ledger_path


def _write_status(plan_dir: Path) -> None:
    (plan_dir / 'status.json').write_text(
        json.dumps({'plan_id': plan_dir.name, 'metadata': {'worktree_path': ''}}),
        encoding='utf-8',
    )


def _stub_expected(monkeypatch, notations, reason=None) -> None:
    """Pin what the architecture resolves, without running the live crawl."""
    monkeypatch.setattr(
        crosscheck,
        'resolve_expected_notations',
        lambda _project_dir: (frozenset(notations), reason),
    )


def _run(plan_context, monkeypatch, tmp_path, entries, plan_id) -> dict:
    """Drive the real gate handler against a temp ledger and a pinned sha."""
    plan_dir = plan_context.plan_dir_for(plan_id)
    _write_status(plan_dir)
    monkeypatch.setattr(_freshness_mod, 'compute_worktree_sha', lambda _root: _CURRENT_SHA)
    ledger_path = _write_ledger(tmp_path, entries)
    monkeypatch.setattr(_freshness_mod, 'resolve_ledger_path', lambda: ledger_path)
    result: dict = cmd_pre_commit_verify_freshness(Namespace(plan_id=plan_id))
    return result


@pytest.fixture(autouse=True)
def _stub_resolver_seam(monkeypatch):
    """Keep worktree-root resolution hermetic (no ``manage-status`` subprocess)."""
    monkeypatch.setattr(
        file_ops, '_query_worktree_path', lambda _plan_id: (True, str(Path.cwd()))
    )


@pytest.fixture(autouse=True)
def _build_is_necessary(monkeypatch):
    """Reach the ledger scan on every case; the short-circuit has its own file."""
    monkeypatch.setattr(_freshness_mod, '_build_necessity_verdict', lambda _plan_id: {'decision': 'build'})


# =============================================================================
# Refusal direction — unrelated evidence no longer passes
# =============================================================================


def test_unrelated_notation_is_refused(plan_context, monkeypatch, tmp_path) -> None:
    """The founding defect: the ONLY candidate names a build this project never runs.

    Against the pre-change gate this exact ledger returned ``fresh`` — the scan
    filtered on ``kind``/``status``/``worktree_sha`` and never looked at the
    notation, so an npm row proved freshness for a Python-only project. The
    verdict happened to be right on the run that surfaced it; the evidence did
    not support it, and nothing in the output said so.
    """
    _stub_expected(monkeypatch, {_PYPROJECT})
    result = _run(
        plan_context,
        monkeypatch,
        tmp_path,
        [_build_entry(notation=_NPM)],
        'crosscheck-unrelated',
    )

    assert result['status'] == 'stale', result
    assert result['reason'] == crosscheck.REASON_NOTATION_UNRELATED
    assert result['notation_cross_check'] == crosscheck.REFUTED
    assert result['expected_notations'] == [_PYPROJECT]
    assert result['candidate_notations'] == [_NPM]
    assert _NPM in result['message']


def test_row_without_a_notation_is_refused(plan_context, monkeypatch, tmp_path) -> None:
    """A matching row carrying no notation cannot corroborate anything.

    ``_ledger_core.build_record`` makes ``notation`` a required argument, so a
    row without one was not written by the dispatch boundary. It is named apart
    from ``notation_unrelated`` because the remedy differs: this one says the
    ledger has been written to by something other than a build.
    """
    _stub_expected(monkeypatch, {_PYPROJECT})
    result = _run(
        plan_context,
        monkeypatch,
        tmp_path,
        [_build_entry(notation=None)],
        'crosscheck-no-notation',
    )

    assert result['status'] == 'stale', result
    assert result['reason'] == crosscheck.REASON_NOTATION_ABSENT
    assert result['candidate_notations'] == []


def test_every_candidate_unrelated_is_refused(plan_context, monkeypatch, tmp_path) -> None:
    """Several matching rows, none of them resolvable — still a refusal."""
    _stub_expected(monkeypatch, {_PYPROJECT})
    result = _run(
        plan_context,
        monkeypatch,
        tmp_path,
        [_build_entry(notation=_NPM), _build_entry(notation=_GRADLE)],
        'crosscheck-all-unrelated',
    )

    assert result['status'] == 'stale', result
    assert result['reason'] == crosscheck.REASON_NOTATION_UNRELATED
    assert result['candidate_notations'] == sorted([_GRADLE, _NPM])


# =============================================================================
# Acceptance direction — legitimate evidence is not refused
# =============================================================================


def test_multi_notation_project_still_passes(plan_context, monkeypatch, tmp_path) -> None:
    """A project resolving several notations passes on any one of them.

    The mirror-image failure of the refusal above: an over-strict check that
    admits only one 'blessed' notation would refuse a polyglot project's real
    build evidence.
    """
    _stub_expected(monkeypatch, {_PYPROJECT, _MAVEN, _NPM})
    result = _run(
        plan_context,
        monkeypatch,
        tmp_path,
        [_build_entry(notation=_MAVEN)],
        'crosscheck-multi',
    )

    assert result['status'] == 'fresh', result
    assert result['notation_cross_check'] == crosscheck.CORROBORATED
    assert result['matched_notation'] == _MAVEN


def test_related_row_behind_an_unrelated_one_still_passes(
    plan_context, monkeypatch, tmp_path
) -> None:
    """A corroborated candidate is found even when an unrelated row precedes it.

    This is why the scan collects every candidate instead of returning on the
    first match: file order is write order, so a polluted row written before a
    real build would otherwise decide the verdict for the whole ledger.
    """
    _stub_expected(monkeypatch, {_PYPROJECT})
    result = _run(
        plan_context,
        monkeypatch,
        tmp_path,
        [_build_entry(notation=_NPM), _build_entry(notation=_PYPROJECT)],
        'crosscheck-behind',
    )

    assert result['status'] == 'fresh', result
    assert result['notation_cross_check'] == crosscheck.CORROBORATED
    assert result['matched_notation'] == _PYPROJECT
    assert result['matched_entry_index'] == 1


def test_unresolvable_architecture_passes_with_the_inability_recorded(
    plan_context, monkeypatch, tmp_path
) -> None:
    """Resolution failure passes the gate, but never silently.

    An inability to resolve is the ABSENCE of knowledge, not a refutation:
    failing closed here would block every legitimate transition in a tree whose
    architecture has not been discovered. The pass is therefore permitted and
    the inability is stated in the record, so 'passed uncross-checked' stays
    distinguishable from 'passed cross-checked'.
    """
    _stub_expected(monkeypatch, set(), reason=crosscheck.REASON_RESOLUTION_FAILED)
    result = _run(
        plan_context,
        monkeypatch,
        tmp_path,
        [_build_entry(notation=_NPM)],
        'crosscheck-unresolvable',
    )

    assert result['status'] == 'fresh', result
    assert result['notation_cross_check'] == crosscheck.UNVERIFIED
    assert result['notation_cross_check_reason'] == crosscheck.REASON_RESOLUTION_FAILED
    assert result['expected_notations'] == []


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


class _FakeQueryModule:
    """Stand-in for ``_cmd_client_query`` exposing only the one function used.

    The cross-check imports ``resolve_project_build_notations`` in-function, so
    substituting the module in ``sys.modules`` exercises the real import path
    (including its failure branch) without running the architecture crawl.
    """

    def __init__(self, outcome) -> None:
        self._outcome = outcome

    def resolve_project_build_notations(self, project_dir: str = '.'):
        del project_dir
        if isinstance(self._outcome, Exception):
            raise self._outcome
        return self._outcome
