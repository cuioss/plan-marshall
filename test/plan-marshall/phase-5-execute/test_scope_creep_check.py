#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for scope_creep_check.py.

Drive ``cmd_check`` directly by inserting the scripts dir on sys.path and
patching the git-diff helper. Verifies the four residual/threshold contract
cases from solution_outline.md deliverable 4:

    (a) empty residual           -> no finding
    (b) residual <= threshold    -> no finding
    (c) residual >  threshold    -> finding persisted with correct list
    (d) configurable override    -> threshold flag honoured

plus the persist-outcome contract: the stub sits at the ``add_qgate_finding``
seam (NOT over ``_emit_finding`` wholesale), so every test exercises the real
``_emit_finding`` body and the stub can return each of the four real status
values — ``success``, ``deduplicated``, ``reopened`` and ``error``. Stubbing
``_emit_finding`` itself is what hid the original defect: the function and its
argv were never executed by any test.
"""

from __future__ import annotations

import json
import sys
from argparse import Namespace
from pathlib import Path

import file_ops
import pytest
from _resolve_project_dir_fixtures import (
    CANONICAL_PLAN_ID,
    CANONICAL_WORKTREE,
    MAIN_CHECKOUT_ROOT,
    NO_PLAN_SENTINEL,
    patch_main_checkout_root,
    patch_query_worktree_path,
)
from conftest import get_script_path

SCRIPT_PATH = get_script_path('plan-marshall', 'phase-5-execute', 'scope_creep_check.py')
SCRIPTS_DIR = SCRIPT_PATH.parent

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import scope_creep_check as scc  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def plan_with_refs(plan_context):
    """Plan context pre-populated with references.json and one TASK file."""
    plan_dir = plan_context.plan_dir_for('scope-creep-test')
    refs = {
        'plan_creation_sha': 'deadbeef',
        'affected_files': [
            'src/a.py',
            'src/b.py',
        ],
    }
    (plan_dir / 'references.json').write_text(json.dumps(refs))
    task = {
        'number': 1,
        'steps': [{'number': 1, 'target': 'src/c.py'}],
    }
    (plan_dir / 'TASK-001.json').write_text(json.dumps(task))
    plan_context.plan_dir = plan_dir
    yield plan_context


# ---------------------------------------------------------------------------
# Patches
# ---------------------------------------------------------------------------


class _PersistStub:
    """Stub at the ``add_qgate_finding`` seam — the real persist boundary.

    Records the keyword arguments the production ``_emit_finding`` body builds
    and returns the configured primitive outcome, so a test can express any of
    the four real status values without stubbing ``_emit_finding`` itself.
    """

    def __init__(self, status: str = 'success', message: str = ''):
        self.status = status
        self.message = message
        self.calls: list[dict] = []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        if self.status == 'error':
            return {'status': 'error', 'message': self.message}
        return {'status': self.status, 'hash_id': 'abc123', 'phase': kwargs.get('phase')}


def _patch_diff(monkeypatch, files):
    monkeypatch.setattr(scc, '_git_diff_files', lambda worktree, sha: list(files))


def _patch_resolve(monkeypatch, plan_dir):
    """Stub the RESOLVER seam, not ``scc._resolve_worktree``.

    ``_resolve_worktree`` no longer shells out — it delegates to
    ``file_ops.resolve_plan_context``, whose only external touch point is
    ``file_ops._query_worktree_path``. Stubbing that one seam leaves the real
    ``_resolve_worktree`` body (and the whole delegation chain beneath it)
    executing, which is exactly what the migration must keep covered. Stubbing
    ``_resolve_worktree`` itself would hide a regression back to a hand-rolled
    re-derivation, since the replaced function would never run.

    The plan-dir resolution flows separately through ``file_ops.get_plan_dir``,
    which honours the ``PLAN_BASE_DIR`` the ``plan_context`` fixture sets, so no
    plan-dir patching is needed.
    """
    monkeypatch.setattr(
        file_ops, '_query_worktree_path', lambda plan_id: (True, str(Path.cwd()))
    )


def _patch_persist(monkeypatch, stub):
    """Stub the persist primitive, leaving the real ``_emit_finding`` in place."""
    monkeypatch.setattr(scc, 'add_qgate_finding', stub)


# ---------------------------------------------------------------------------
# Contract test cases
# ---------------------------------------------------------------------------


def test_empty_residual_no_finding(plan_with_refs, monkeypatch, capsys):
    """Case (a): all changed files declared -> residual=0, no finding."""
    _patch_diff(monkeypatch, ['src/a.py', 'src/b.py', 'src/c.py'])
    _patch_resolve(monkeypatch, plan_with_refs.plan_dir)
    stub = _PersistStub()
    _patch_persist(monkeypatch, stub)

    rc = scc.cmd_check(Namespace(plan_id='scope-creep-test', threshold=None))
    out = capsys.readouterr().out

    assert rc == 0
    assert 'residual_count: 0' in out
    assert 'finding_emitted: false' in out
    assert stub.calls == []


def test_residual_at_threshold_no_finding(plan_with_refs, monkeypatch, capsys):
    """Case (b): residual count equals threshold -> no finding (must exceed)."""
    # Declared: a, b, c. Add 5 extras → residual=5 == default threshold 5.
    _patch_diff(
        monkeypatch,
        ['src/a.py', 'src/b.py', 'src/c.py']
        + [f'extra/{i}.py' for i in range(5)],
    )
    _patch_resolve(monkeypatch, plan_with_refs.plan_dir)
    stub = _PersistStub()
    _patch_persist(monkeypatch, stub)

    rc = scc.cmd_check(Namespace(plan_id='scope-creep-test', threshold=None))
    out = capsys.readouterr().out

    assert rc == 0
    assert 'residual_count: 5' in out
    assert 'finding_emitted: false' in out
    assert stub.calls == []


def test_residual_over_threshold_emits_finding(plan_with_refs, monkeypatch, capsys):
    """Case (c): residual > threshold -> finding persisted with full residual list."""
    extras = [f'extra/{i}.py' for i in range(6)]
    _patch_diff(monkeypatch, ['src/a.py'] + extras)
    _patch_resolve(monkeypatch, plan_with_refs.plan_dir)
    stub = _PersistStub()
    _patch_persist(monkeypatch, stub)

    rc = scc.cmd_check(Namespace(plan_id='scope-creep-test', threshold=None))
    out = capsys.readouterr().out

    assert rc == 0
    assert 'residual_count: 6' in out
    assert 'finding_emitted: true' in out
    assert len(stub.calls) == 1
    call = stub.calls[0]
    # The real _emit_finding body ran: named arguments, no argv, and the
    # finding type is still the (deliberately un-taxonomised) scope_creep_warning.
    assert call['plan_id'] == 'scope-creep-test'
    assert call['phase'] == '5-execute'
    assert call['source'] == 'qgate'
    assert call['finding_type'] == 'scope_creep_warning'
    assert call['severity'] == 'warning'
    assert 'threshold=5' in call['detail']
    for extra in extras:
        assert extra in call['title']


def test_threshold_override_via_flag(plan_with_refs, monkeypatch, capsys):
    """Case (d): explicit --threshold raises the bar; lower count -> no finding."""
    extras = [f'extra/{i}.py' for i in range(6)]
    _patch_diff(monkeypatch, ['src/a.py'] + extras)
    _patch_resolve(monkeypatch, plan_with_refs.plan_dir)
    stub = _PersistStub()
    _patch_persist(monkeypatch, stub)

    rc = scc.cmd_check(Namespace(plan_id='scope-creep-test', threshold=10))
    out = capsys.readouterr().out

    assert rc == 0
    assert 'residual_count: 6' in out
    assert 'threshold: 10' in out
    assert 'finding_emitted: false' in out
    assert stub.calls == []


def test_plan_dir_resolved_via_plan_base_dir(plan_with_refs, monkeypatch, capsys):
    """Plan dir is resolved via file_ops.get_plan_dir honouring PLAN_BASE_DIR.

    No patching of any plan-dir resolver: the fixture sets PLAN_BASE_DIR so
    ``get_plan_dir('scope-creep-test')`` resolves to the fixture's plan dir,
    where references.json + TASK-001.json already live. A residual over the
    default threshold confirms the resolved dir was read.
    """
    extras = [f'extra/{i}.py' for i in range(6)]
    _patch_diff(monkeypatch, ['src/a.py'] + extras)
    _patch_resolve(monkeypatch, plan_with_refs.plan_dir)
    stub = _PersistStub()
    _patch_persist(monkeypatch, stub)

    rc = scc.cmd_check(Namespace(plan_id='scope-creep-test', threshold=None))
    out = capsys.readouterr().out

    assert rc == 0
    assert 'residual_count: 6' in out
    assert 'finding_emitted: true' in out
    assert len(stub.calls) == 1


def test_threshold_zero_disables_guard(plan_with_refs, monkeypatch, capsys):
    """Threshold 0 is the explicit disable knob — short-circuit, no diff."""
    # Patch _git_diff_files to raise; if the script touched it, the test fails.
    def _raise(*_a, **_k):
        raise AssertionError('diff should not be invoked when threshold=0')

    monkeypatch.setattr(scc, '_git_diff_files', _raise)
    _patch_resolve(monkeypatch, plan_with_refs.plan_dir)
    stub = _PersistStub()
    _patch_persist(monkeypatch, stub)

    rc = scc.cmd_check(Namespace(plan_id='scope-creep-test', threshold=0))
    out = capsys.readouterr().out

    assert rc == 0
    assert 'disabled: true' in out
    assert 'finding_emitted: false' in out
    assert stub.calls == []


# ---------------------------------------------------------------------------
# Persist-outcome contract
# ---------------------------------------------------------------------------


def _over_threshold(monkeypatch, plan_with_refs):
    """Seed a residual above the default threshold so a persist is attempted."""
    extras = [f'extra/{i}.py' for i in range(6)]
    _patch_diff(monkeypatch, ['src/a.py'] + extras)
    _patch_resolve(monkeypatch, plan_with_refs.plan_dir)
    return extras


def test_rejected_persist_fails_loud(plan_with_refs, monkeypatch, capsys):
    """A REJECTED persist yields status: error, a non-zero rc, and the content inline.

    ``finding_emitted: false`` alongside ``status: success`` is no longer
    reachable on a rejection — that shape was indistinguishable from "no creep".
    """
    extras = _over_threshold(monkeypatch, plan_with_refs)
    stub = _PersistStub(
        status='error',
        message='Invalid finding type: scope_creep_warning. Must be one of (...)',
    )
    _patch_persist(monkeypatch, stub)

    rc = scc.cmd_check(Namespace(plan_id='scope-creep-test', threshold=None))
    out = capsys.readouterr().out

    assert rc == 1
    assert 'status: error' in out
    assert 'error: finding_persist_failed' in out
    assert 'Invalid finding type: scope_creep_warning' in out
    # The rejected finding's own content travels inline.
    assert 'finding_title: Scope creep detected' in out
    assert 'threshold=5' in out
    assert 'residual_count: 6' in out
    for extra in extras:
        assert extra in out
    # The success shape must NOT also be printed.
    assert 'status: success' not in out
    assert 'finding_emitted: true' not in out


@pytest.mark.parametrize('benign_status', ['success', 'deduplicated', 'reopened'])
def test_in_store_outcomes_are_benign(plan_with_refs, monkeypatch, capsys, benign_status):
    """All three in-store outcomes leave the run green — they never read as a rejection.

    ``deduplicated`` and ``reopened`` mean the finding IS in the store, so they
    must not collapse onto the ``error`` branch.
    """
    _over_threshold(monkeypatch, plan_with_refs)
    stub = _PersistStub(status=benign_status)
    _patch_persist(monkeypatch, stub)

    rc = scc.cmd_check(Namespace(plan_id='scope-creep-test', threshold=None))
    out = capsys.readouterr().out

    assert rc == 0
    assert 'status: success' in out
    assert 'finding_emitted: true' in out
    assert 'finding_persist_failed' not in out


# ---------------------------------------------------------------------------
# Resolver-migration contract
# ---------------------------------------------------------------------------
#
# ``_resolve_worktree`` KEEPS its name after the migration — it is the helper
# that applies this script's cwd fallback — but its BODY must now delegate to
# ``file_ops.resolve_plan_context`` instead of shelling out to
# ``manage-status get-worktree-path`` and hand-parsing the TOON.


def test_resolve_worktree_routes_through_the_resolver():
    """The real ``_resolve_worktree`` body reaches the single resolver seam."""
    with patch_query_worktree_path(True) as mock:
        resolved = scc._resolve_worktree(CANONICAL_PLAN_ID)

    assert resolved == Path(CANONICAL_WORKTREE)
    assert mock.call_count == 1, (
        '_resolve_worktree did not reach file_ops._query_worktree_path exactly '
        f'once (call_count={mock.call_count}) — it is bypassing the resolver.'
    )


def test_resolve_worktree_accepts_the_no_plan_sentinel():
    """``NO_PLAN`` resolves to the main checkout without shelling out."""
    with patch_query_worktree_path(True) as mock, patch_main_checkout_root():
        resolved = scc._resolve_worktree(NO_PLAN_SENTINEL)

    assert resolved == Path(MAIN_CHECKOUT_ROOT)
    assert mock.call_count == 0, 'the sentinel must never reach get-worktree-path'


def test_resolve_worktree_falls_back_to_cwd_when_resolution_fails(monkeypatch):
    """An unresolvable plan degrades to cwd rather than aborting the check.

    Scope-creep classification is advisory: a plan whose worktree cannot be
    resolved must still produce a verdict, so the non-fatal fallback that
    predated the migration is preserved deliberately.
    """

    def _raise(_plan_id):
        raise file_ops.WorktreeResolutionError('deliberately unresolvable')

    monkeypatch.setattr(file_ops, '_query_worktree_path', _raise)

    assert scc._resolve_worktree('never-resolves') == Path.cwd()
