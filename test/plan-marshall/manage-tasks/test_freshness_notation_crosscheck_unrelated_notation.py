#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the notation cross-check on ``pre-commit-verify-freshness``."""


from __future__ import annotations

from pathlib import Path

import _freshness_crosscheck as crosscheck
import file_ops
import pytest
from _freshness_notation_crosscheck_fixtures import (
    _GRADLE,
    _MAVEN,
    _NPM,
    _PYPROJECT,
    _build_entry,
    _freshness_mod,
    _run,
    _stub_expected,
)

# =============================================================================
# Fixture builders
# =============================================================================

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
