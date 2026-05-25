#!/usr/bin/env python3
# ruff: noqa: I001, E402
"""Tests for verify_failure_scope.py.

Cover the five contract cases from solution_outline.md deliverable 7:

    (a) all in_scope                   -> exclusively_out_of_scope=False
    (b) all out_of_scope               -> exclusively_out_of_scope=True
    (c) mixed                          -> exclusively_out_of_scope=False
    (d) empty error_paths              -> exclusively_out_of_scope=False, total=0
    (e) missing references.json        -> status=error
"""

from __future__ import annotations

import json
import sys

from conftest import PlanContext, get_script_path  # type: ignore[import-not-found]

SCRIPT_PATH = get_script_path('plan-marshall', 'phase-5-execute', 'verify_failure_scope.py')
SCRIPTS_DIR = SCRIPT_PATH.parent

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import verify_failure_scope as vfs  # noqa: E402


def _write_refs(plan_dir, modified_files):
    refs = {'modified_files': list(modified_files)}
    (plan_dir / 'references.json').write_text(json.dumps(refs))


def test_all_in_scope():
    with PlanContext(plan_id='vfs-all-in') as ctx:
        assert ctx.plan_dir is not None
        _write_refs(ctx.plan_dir, ['src/a.py', 'src/b.py'])
        result = vfs.classify_failure_scope(
            'vfs-all-in', ['src/a.py', 'src/b.py'], plan_dir=ctx.plan_dir
        )
        assert result['status'] == 'success'
        assert result['total'] == 2
        assert result['in_scope_count'] == 2
        assert result['out_of_scope_count'] == 0
        assert result['exclusively_out_of_scope'] is False
        assert result['out_of_scope_paths'] == []


def test_all_out_of_scope():
    with PlanContext(plan_id='vfs-all-out') as ctx:
        assert ctx.plan_dir is not None
        _write_refs(ctx.plan_dir, ['src/a.py'])
        result = vfs.classify_failure_scope(
            'vfs-all-out',
            ['foreign/x.py', 'foreign/y.py'],
            plan_dir=ctx.plan_dir,
        )
        assert result['status'] == 'success'
        assert result['total'] == 2
        assert result['in_scope_count'] == 0
        assert result['out_of_scope_count'] == 2
        assert result['exclusively_out_of_scope'] is True
        assert sorted(result['out_of_scope_paths']) == ['foreign/x.py', 'foreign/y.py']


def test_mixed_scope():
    with PlanContext(plan_id='vfs-mixed') as ctx:
        assert ctx.plan_dir is not None
        _write_refs(ctx.plan_dir, ['src/a.py'])
        result = vfs.classify_failure_scope(
            'vfs-mixed',
            ['src/a.py', 'foreign/x.py'],
            plan_dir=ctx.plan_dir,
        )
        assert result['status'] == 'success'
        assert result['total'] == 2
        assert result['in_scope_count'] == 1
        assert result['out_of_scope_count'] == 1
        assert result['exclusively_out_of_scope'] is False
        assert result['out_of_scope_paths'] == ['foreign/x.py']


def test_empty_error_paths():
    with PlanContext(plan_id='vfs-empty') as ctx:
        assert ctx.plan_dir is not None
        _write_refs(ctx.plan_dir, ['src/a.py'])
        result = vfs.classify_failure_scope(
            'vfs-empty', [], plan_dir=ctx.plan_dir
        )
        assert result['status'] == 'success'
        assert result['total'] == 0
        assert result['in_scope_count'] == 0
        assert result['out_of_scope_count'] == 0
        assert result['exclusively_out_of_scope'] is False
        assert result['out_of_scope_paths'] == []


def test_missing_references_returns_error(tmp_path):
    # Point at an empty plan_dir with no references.json present.
    plan_dir = tmp_path / 'missing-plan'
    plan_dir.mkdir()
    result = vfs.classify_failure_scope(
        'vfs-missing', ['src/a.py'], plan_dir=plan_dir
    )
    assert result['status'] == 'error'
    assert result['error'] == 'references_json_missing'


def test_blank_paths_filtered():
    """Whitespace-only or empty error path tokens are dropped before classification."""
    with PlanContext(plan_id='vfs-blank') as ctx:
        assert ctx.plan_dir is not None
        _write_refs(ctx.plan_dir, ['src/a.py'])
        result = vfs.classify_failure_scope(
            'vfs-blank', ['  ', '', 'src/a.py'], plan_dir=ctx.plan_dir
        )
        assert result['status'] == 'success'
        assert result['total'] == 1
        assert result['in_scope_count'] == 1
