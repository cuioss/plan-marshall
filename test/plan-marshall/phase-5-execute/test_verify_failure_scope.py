#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for verify_failure_scope.py.

Cover the five contract cases from solution_outline.md deliverable 5:

    (a) all in_scope                   -> exclusively_out_of_scope=False
    (b) all out_of_scope               -> exclusively_out_of_scope=True
    (c) mixed                          -> exclusively_out_of_scope=False
    (d) empty error_paths              -> exclusively_out_of_scope=False, total=0
    (e) missing references.json        -> status=error

The declared scope is now the live plan footprint derived on demand via
``compute_plan_branch_diff`` (the ``compute-footprint`` derivation), not a
seeded ``references.modified_files`` ledger. Tests stub
``_resolve_declared_footprint`` to inject the footprint without standing up a
real git worktree.
"""

from __future__ import annotations

import json
import sys

from conftest import get_script_path

SCRIPT_PATH = get_script_path('plan-marshall', 'phase-5-execute', 'verify_failure_scope.py')
SCRIPTS_DIR = SCRIPT_PATH.parent

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import verify_failure_scope as vfs  # noqa: E402


def _write_refs(plan_dir):
    """Write a minimal references.json so the missing-file guard passes."""
    refs = {'branch': 'feature/test', 'base_branch': 'main'}
    (plan_dir / 'references.json').write_text(json.dumps(refs))


def _stub_footprint(monkeypatch, footprint):
    """Patch the footprint resolver to return the given declared set."""
    monkeypatch.setattr(
        vfs, '_resolve_declared_footprint', lambda plan_dir: set(footprint)
    )


def test_all_in_scope(plan_context, monkeypatch):
    plan_dir = plan_context.plan_dir_for('vfs-all-in')
    _write_refs(plan_dir)
    _stub_footprint(monkeypatch, ['src/a.py', 'src/b.py'])
    result = vfs.classify_failure_scope(
        'vfs-all-in', ['src/a.py', 'src/b.py'], plan_dir=plan_dir
    )
    assert result['status'] == 'success'
    assert result['total'] == 2
    assert result['in_scope_count'] == 2
    assert result['out_of_scope_count'] == 0
    assert result['exclusively_out_of_scope'] is False
    assert result['out_of_scope_paths'] == []


def test_all_out_of_scope(plan_context, monkeypatch):
    plan_dir = plan_context.plan_dir_for('vfs-all-out')
    _write_refs(plan_dir)
    _stub_footprint(monkeypatch, ['src/a.py'])
    result = vfs.classify_failure_scope(
        'vfs-all-out',
        ['foreign/x.py', 'foreign/y.py'],
        plan_dir=plan_dir,
    )
    assert result['status'] == 'success'
    assert result['total'] == 2
    assert result['in_scope_count'] == 0
    assert result['out_of_scope_count'] == 2
    assert result['exclusively_out_of_scope'] is True
    assert sorted(result['out_of_scope_paths']) == ['foreign/x.py', 'foreign/y.py']


def test_mixed_scope(plan_context, monkeypatch):
    plan_dir = plan_context.plan_dir_for('vfs-mixed')
    _write_refs(plan_dir)
    _stub_footprint(monkeypatch, ['src/a.py'])
    result = vfs.classify_failure_scope(
        'vfs-mixed',
        ['src/a.py', 'foreign/x.py'],
        plan_dir=plan_dir,
    )
    assert result['status'] == 'success'
    assert result['total'] == 2
    assert result['in_scope_count'] == 1
    assert result['out_of_scope_count'] == 1
    assert result['exclusively_out_of_scope'] is False
    assert result['out_of_scope_paths'] == ['foreign/x.py']


def test_empty_error_paths(plan_context, monkeypatch):
    plan_dir = plan_context.plan_dir_for('vfs-empty')
    _write_refs(plan_dir)
    _stub_footprint(monkeypatch, ['src/a.py'])
    result = vfs.classify_failure_scope(
        'vfs-empty', [], plan_dir=plan_dir
    )
    assert result['status'] == 'success'
    assert result['total'] == 0
    assert result['in_scope_count'] == 0
    assert result['out_of_scope_count'] == 0
    assert result['exclusively_out_of_scope'] is False
    assert result['out_of_scope_paths'] == []


def test_missing_references_returns_error(tmp_path):
    # Point at an empty plan_dir with no references.json present. The footprint
    # resolver raises FileNotFoundError, which the classifier maps to an error.
    plan_dir = tmp_path / 'missing-plan'
    plan_dir.mkdir()
    result = vfs.classify_failure_scope(
        'vfs-missing', ['src/a.py'], plan_dir=plan_dir
    )
    assert result['status'] == 'error'
    assert result['error'] == 'references_json_missing'


def test_blank_paths_filtered(plan_context, monkeypatch):
    """Whitespace-only or empty error path tokens are dropped before classification."""
    plan_dir = plan_context.plan_dir_for('vfs-blank')
    _write_refs(plan_dir)
    _stub_footprint(monkeypatch, ['src/a.py'])
    result = vfs.classify_failure_scope(
        'vfs-blank', ['  ', '', 'src/a.py'], plan_dir=plan_dir
    )
    assert result['status'] == 'success'
    assert result['total'] == 1
    assert result['in_scope_count'] == 1


def test_plan_dir_resolved_via_plan_base_dir(plan_context, monkeypatch):
    """Without a plan_dir override, the plan dir is resolved via PLAN_BASE_DIR.

    The plan-dir resolution flows through ``file_ops.get_plan_dir``, which
    honours the ``PLAN_BASE_DIR`` the ``plan_context`` fixture sets. Omitting
    the ``plan_dir`` argument forces the script to resolve the dir itself; the
    stubbed footprint resolver confirms the resolved dir was threaded through.
    """
    plan_id = 'vfs-resolve-via-env'
    plan_dir = plan_context.plan_dir_for(plan_id)
    _write_refs(plan_dir)
    _stub_footprint(monkeypatch, ['src/a.py'])
    result = vfs.classify_failure_scope(
        plan_id, ['src/a.py', 'foreign/x.py']
    )
    assert result['status'] == 'success'
    assert result['total'] == 2
    assert result['in_scope_count'] == 1
    assert result['out_of_scope_count'] == 1
    assert result['exclusively_out_of_scope'] is False
    assert result['out_of_scope_paths'] == ['foreign/x.py']


def test_footprint_resolver_reads_references_and_status(plan_context, monkeypatch, tmp_path):
    """End-to-end seam: _resolve_declared_footprint derives via compute_plan_branch_diff.

    Patches the git-derivation primitive so no real worktree is needed, and
    confirms the resolver threads the worktree from status.metadata and the
    base ref from references.json into the derivation.
    """
    plan_dir = plan_context.plan_dir_for('vfs-resolver-seam')
    (plan_dir / 'references.json').write_text(
        json.dumps({'base_branch': 'develop'})
    )
    worktree = tmp_path / 'wt'
    worktree.mkdir()
    (plan_dir / 'status.json').write_text(
        json.dumps({'metadata': {'worktree_path': str(worktree)}})
    )

    captured = {}

    def _fake_diff(wt, base_ref):
        captured['worktree'] = wt
        captured['base_ref'] = base_ref
        return {'src/a.py'}

    monkeypatch.setattr(vfs, 'compute_plan_branch_diff', _fake_diff)

    declared = vfs._resolve_declared_footprint(plan_dir)
    assert declared == {'src/a.py'}
    assert str(captured['worktree']) == str(worktree)
    assert captured['base_ref'] == 'develop'
