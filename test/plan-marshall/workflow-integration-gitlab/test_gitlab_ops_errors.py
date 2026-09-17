#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Tests for gitlab_ops.py — failure envelopes, validation errors, and output guards."""

from __future__ import annotations

import argparse
import gitlab_ops
from _ci_wait_contract import _ok_auth
from _resolve_project_dir_fixtures import worktree_query_result


def _capture_run_glab(*, mr_list_iid: int = 7):
    """Return a (run_glab_stub, captured_args_list) pair.

    ``mr_list_iid`` controls what the ``glab mr list --source-branch ...`` lookup returns.
    Set to ``None`` to simulate a zero-match result.
    """
    captured: list[list[str]] = []

    def run_glab_stub(args):
        captured.append(list(args))
        if args[:3] == ['mr', 'list', '--source-branch']:
            if mr_list_iid is None:
                return 0, '[]', ''
            return 0, f'[{{"iid": {mr_list_iid}, "title": "T"}}]', ''
        if args[:2] == ['mr', 'create']:
            return 0, 'https://gitlab.com/octo/repo/-/merge_requests/42', ''
        if args[:2] == ['mr', 'view']:
            return 0, '{"iid": 7, "state": "opened", "title": "T", "pipeline": {"id": 99, "status": "success"}}', ''
        if args[:2] == ['mr', 'merge']:
            return 0, '', ''
        if args[:2] == ['ci', 'view']:
            return 0, '{"jobs": []}', ''
        return 0, '', ''

    return run_glab_stub, captured


# =============================================================================
# issue comment
# =============================================================================
def _prepare_issue_comment_body(tmp_path, monkeypatch, body_text='Milestone reached', plan_id='p'):
    """Seed PLAN_BASE_DIR with a prepared issue-comment body scratch file."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    from ci_base import BODY_KIND_ISSUE_COMMENT, get_body_path

    path = get_body_path(plan_id, BODY_KIND_ISSUE_COMMENT)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body_text, encoding='utf-8')
    return plan_id


def test_pr_view_dual_flag_rejected(monkeypatch):
    """Both selectors together is a structured error, not a silent precedence rule."""
    run_glab_stub, captured = _capture_run_glab()
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)

    ns = argparse.Namespace(pr_number=42, head='feature/x')
    result = gitlab_ops.cmd_pr_view(ns)

    assert result['status'] == 'error', result
    assert 'not both' in result['error'], result
    assert captured == [], 'Should not invoke glab when validation fails'


def test_pr_merge_dual_flag_rejected(monkeypatch):
    run_glab_stub, captured = _capture_run_glab()
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)

    ns = argparse.Namespace(pr_number=42, head='feature/x', strategy='merge', delete_branch=False)
    result = gitlab_ops.cmd_pr_merge(ns)

    assert result['status'] == 'error'
    assert 'exactly one' in result['error']
    assert captured == [], 'Should not invoke glab when validation fails'


def test_pr_merge_zero_match_rejected(monkeypatch):
    run_glab_stub, captured = _capture_run_glab(mr_list_iid=None)
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)

    ns = argparse.Namespace(pr_number=None, head='feature/x', strategy='merge', delete_branch=False)
    result = gitlab_ops.cmd_pr_merge(ns)

    assert result['status'] == 'error'
    assert 'no MR found' in result['error']


def test_pr_auto_merge_dual_flag_rejected(monkeypatch):
    run_glab_stub, _ = _capture_run_glab()
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)

    ns = argparse.Namespace(pr_number=42, head='feature/x', strategy='merge')
    result = gitlab_ops.cmd_pr_auto_merge(ns)

    assert result['status'] == 'error'
    assert 'exactly one' in result['error']


def test_ci_status_dual_flag_rejected(monkeypatch):
    run_glab_stub, _ = _capture_run_glab()
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)

    ns = argparse.Namespace(pr_number=42, head='feature/x')
    result = gitlab_ops.cmd_ci_status(ns)

    assert result['status'] == 'error'
    assert 'exactly one' in result['error']


def test_cmd_issue_comment_body_not_prepared(monkeypatch, tmp_path):
    """A missing prepared body yields a body_not_prepared error, no glab call."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    captured: list[list[str]] = []

    def run_glab_stub(args):
        captured.append(list(args))
        return 0, '', ''

    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)

    ns = argparse.Namespace(issue='42', plan_id='p', slot=None)
    result = gitlab_ops.cmd_issue_comment(ns)

    assert result['status'] == 'error', result
    assert result['operation'] == 'issue_comment'
    assert captured == []


def test_cmd_issue_comment_api_failure_keeps_body(monkeypatch, tmp_path):
    """A non-zero glab exit returns an error and leaves the scratch body in place."""
    from ci_base import BODY_KIND_ISSUE_COMMENT, get_body_path

    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(gitlab_ops, 'run_glab', lambda args: (1, '', 'glab: not found'))

    plan_id = _prepare_issue_comment_body(tmp_path, monkeypatch)
    body_path = get_body_path(plan_id, BODY_KIND_ISSUE_COMMENT)

    ns = argparse.Namespace(issue='42', plan_id=plan_id, slot=None)
    result = gitlab_ops.cmd_issue_comment(ns)

    assert result['status'] == 'error', result
    assert body_path.exists()


def test_cmd_issue_comment_auth_failure(monkeypatch, tmp_path):
    """An auth failure short-circuits before any glab call."""
    captured: list[list[str]] = []

    def run_glab_stub(args):
        captured.append(list(args))
        return 0, '', ''

    monkeypatch.setattr(gitlab_ops, 'check_auth', lambda: (False, 'not logged in'))
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)

    ns = argparse.Namespace(issue='42', plan_id='p', slot=None)
    result = gitlab_ops.cmd_issue_comment(ns)

    assert result['status'] == 'error', result
    assert captured == []


def test_format_jobs_toon_clamps_runaway_aggregate(monkeypatch, capsys):
    """Defense-in-depth: if compute_total_elapsed somehow returns a runaway
    value, format_checks_toon clamps to the caller-supplied ceiling and warns.

    We patch compute_total_elapsed to simulate the exact pre-fix bug
    (63.9 billion seconds) and verify the clamp engages.
    """
    monkeypatch.setattr(gitlab_ops, 'compute_total_elapsed', lambda values, now: 63_870_000_000)

    jobs = [
        {
            'name': 'unit-tests',
            'status': 'success',
            'started_at': '2025-01-15T11:55:00+00:00',
            'finished_at': '2025-01-15T11:58:00+00:00',
            'web_url': 'https://gitlab.test/1',
            'stage': 'test',
        },
    ]

    # ci_status path: duration_ceiling=0 → clamp substitutes 0.
    rows, total_elapsed = gitlab_ops.format_checks_toon(jobs, duration_ceiling=0)
    assert total_elapsed == 0, f'Expected runaway aggregate to clamp to 0, got {total_elapsed}'
    captured = capsys.readouterr()
    assert 'out of range' in captured.err, 'Expected stderr warning when clamp engages'

    # ci_wait path: duration_ceiling=42 → clamp substitutes 42.
    _, total_elapsed_wait = gitlab_ops.format_checks_toon(jobs, duration_ceiling=42)
    assert total_elapsed_wait == 42


def test_gitlab_main_emits_mutually_exclusive_error_on_both_flags(monkeypatch, capsys):
    """gitlab_ops.main() with both --plan-id and --project-dir → mutually_exclusive_args."""
    monkeypatch.setattr(
        'sys.argv',
        [
            'gitlab_ops.py',
            '--plan-id',
            'task-routing-canonical',
            '--project-dir',
            '/tmp/explicit',
            'pr',
            'view',
        ],
    )
    import pytest as _pytest

    with _pytest.raises(SystemExit) as exc_info:
        gitlab_ops.main()
    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert 'mutually_exclusive_args' in captured.out


def test_gitlab_main_project_dir_only_keeps_legacy_path(monkeypatch):
    """Pre-existing --project-dir-only callers must continue working."""
    from ci_base import get_default_cwd

    monkeypatch.setattr(
        'sys.argv',
        [
            'gitlab_ops.py',
            '--project-dir',
            '/tmp/wt-gitlab-explicit',
            '--help',
        ],
    )
    import pytest as _pytest

    with _pytest.raises(SystemExit):
        gitlab_ops.main()
    assert get_default_cwd() == '/tmp/wt-gitlab-explicit'
