#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for scope_creep_check.py.

Drive ``cmd_check`` directly by inserting the scripts dir on sys.path and
patching the git-diff / finding-emit subprocess helpers. Verifies the four
contract cases from solution_outline.md deliverable 4:

    (a) empty residual           -> no finding
    (b) residual <= threshold    -> no finding
    (c) residual >  threshold    -> finding emitted with correct list
    (d) configurable override    -> threshold flag honoured
"""

from __future__ import annotations

import json
import sys
from argparse import Namespace
from pathlib import Path

import pytest
from conftest import get_script_path  # type: ignore[import-not-found]

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


class _Recorder:
    def __init__(self):
        self.emitted_calls = []

    def emit_ok(self, plan_id, residual, threshold):
        self.emitted_calls.append((plan_id, list(residual), threshold))
        return True


def _patch_diff(monkeypatch, files):
    monkeypatch.setattr(scc, '_git_diff_files', lambda worktree, sha: list(files))


def _patch_resolve(monkeypatch, plan_dir):
    """Patch only the worktree resolver.

    The plan-dir resolution now flows through ``file_ops.get_plan_dir``, which
    honours the ``PLAN_BASE_DIR`` the ``plan_context`` fixture sets. Each test
    passes the matching ``plan_id`` so ``get_plan_dir(plan_id)`` resolves to the
    fixture's ``plan_dir`` with no patching of the resolver itself.
    """
    monkeypatch.setattr(scc, '_resolve_worktree', lambda plan_id: Path.cwd())


def _patch_emit(monkeypatch, recorder):
    monkeypatch.setattr(scc, '_emit_finding', recorder.emit_ok)


# ---------------------------------------------------------------------------
# Contract test cases
# ---------------------------------------------------------------------------


def test_empty_residual_no_finding(plan_with_refs, monkeypatch, capsys):
    """Case (a): all changed files declared -> residual=0, no finding."""
    _patch_diff(monkeypatch, ['src/a.py', 'src/b.py', 'src/c.py'])
    _patch_resolve(monkeypatch, plan_with_refs.plan_dir)
    recorder = _Recorder()
    _patch_emit(monkeypatch, recorder)

    rc = scc.cmd_check(Namespace(plan_id='scope-creep-test', threshold=None))
    out = capsys.readouterr().out

    assert rc == 0
    assert 'residual_count: 0' in out
    assert 'finding_emitted: false' in out
    assert recorder.emitted_calls == []


def test_residual_at_threshold_no_finding(plan_with_refs, monkeypatch, capsys):
    """Case (b): residual count equals threshold -> no finding (must exceed)."""
    # Declared: a, b, c. Add 5 extras → residual=5 == default threshold 5.
    _patch_diff(
        monkeypatch,
        ['src/a.py', 'src/b.py', 'src/c.py']
        + [f'extra/{i}.py' for i in range(5)],
    )
    _patch_resolve(monkeypatch, plan_with_refs.plan_dir)
    recorder = _Recorder()
    _patch_emit(monkeypatch, recorder)

    rc = scc.cmd_check(Namespace(plan_id='scope-creep-test', threshold=None))
    out = capsys.readouterr().out

    assert rc == 0
    assert 'residual_count: 5' in out
    assert 'finding_emitted: false' in out
    assert recorder.emitted_calls == []


def test_residual_over_threshold_emits_finding(plan_with_refs, monkeypatch, capsys):
    """Case (c): residual > threshold -> finding emitted with full residual list."""
    extras = [f'extra/{i}.py' for i in range(6)]
    _patch_diff(monkeypatch, ['src/a.py'] + extras)
    _patch_resolve(monkeypatch, plan_with_refs.plan_dir)
    recorder = _Recorder()
    _patch_emit(monkeypatch, recorder)

    rc = scc.cmd_check(Namespace(plan_id='scope-creep-test', threshold=None))
    out = capsys.readouterr().out

    assert rc == 0
    assert 'residual_count: 6' in out
    assert 'finding_emitted: true' in out
    assert len(recorder.emitted_calls) == 1
    _, residual, threshold = recorder.emitted_calls[0]
    assert sorted(residual) == sorted(extras)
    assert threshold == 5


def test_threshold_override_via_flag(plan_with_refs, monkeypatch, capsys):
    """Case (d): explicit --threshold raises the bar; lower count -> no finding."""
    extras = [f'extra/{i}.py' for i in range(6)]
    _patch_diff(monkeypatch, ['src/a.py'] + extras)
    _patch_resolve(monkeypatch, plan_with_refs.plan_dir)
    recorder = _Recorder()
    _patch_emit(monkeypatch, recorder)

    rc = scc.cmd_check(Namespace(plan_id='scope-creep-test', threshold=10))
    out = capsys.readouterr().out

    assert rc == 0
    assert 'residual_count: 6' in out
    assert 'threshold: 10' in out
    assert 'finding_emitted: false' in out
    assert recorder.emitted_calls == []


def test_plan_dir_resolved_via_plan_base_dir(plan_with_refs, monkeypatch, capsys):
    """Plan dir is resolved via file_ops.get_plan_dir honouring PLAN_BASE_DIR.

    No patching of any plan-dir resolver: the fixture sets PLAN_BASE_DIR so
    ``get_plan_dir('scope-creep-test')`` resolves to the fixture's plan dir,
    where references.json + TASK-001.json already live. A residual over the
    default threshold confirms the resolved dir was read.
    """
    extras = [f'extra/{i}.py' for i in range(6)]
    _patch_diff(monkeypatch, ['src/a.py'] + extras)
    monkeypatch.setattr(scc, '_resolve_worktree', lambda plan_id: Path.cwd())
    recorder = _Recorder()
    _patch_emit(monkeypatch, recorder)

    rc = scc.cmd_check(Namespace(plan_id='scope-creep-test', threshold=None))
    out = capsys.readouterr().out

    assert rc == 0
    assert 'residual_count: 6' in out
    assert 'finding_emitted: true' in out
    assert len(recorder.emitted_calls) == 1


def test_threshold_zero_disables_guard(plan_with_refs, monkeypatch, capsys):
    """Threshold 0 is the explicit disable knob — short-circuit, no diff."""
    # Patch _git_diff_files to raise; if the script touched it, the test fails.
    def _raise(*_a, **_k):
        raise AssertionError('diff should not be invoked when threshold=0')

    monkeypatch.setattr(scc, '_git_diff_files', _raise)
    _patch_resolve(monkeypatch, plan_with_refs.plan_dir)
    recorder = _Recorder()
    _patch_emit(monkeypatch, recorder)

    rc = scc.cmd_check(Namespace(plan_id='scope-creep-test', threshold=0))
    out = capsys.readouterr().out

    assert rc == 0
    assert 'disabled: true' in out
    assert 'finding_emitted: false' in out
    assert recorder.emitted_calls == []
