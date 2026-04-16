#!/usr/bin/env python3
"""Tests for github_ops.py --head flag routing.

Verifies that branch-aware operations forward the --head value to gh and that
the --pr-number/--head dual-flag validation works as expected.
"""

import argparse

import github_ops  # type: ignore[import-not-found]


def _ok_auth():
    return True, ''


def _capture_run_gh():
    """Return a (run_gh_stub, captured_args_list) pair."""
    captured: list[list[str]] = []

    def run_gh_stub(args, capture_json=False, timeout=60):
        captured.append(list(args))
        # Provide a minimal valid response per operation.
        if args[:2] == ['pr', 'create']:
            return 0, 'https://github.com/octo/repo/pull/42', ''
        if args[:2] == ['pr', 'view']:
            return 0, '{"number": 42, "url": "https://github.com/octo/repo/pull/42", "state": "OPEN"}', ''
        if args[:2] == ['pr', 'merge']:
            return 0, '', ''
        if args[:2] == ['pr', 'checks']:
            return 0, '[]', ''
        if args[:2] == ['pr', 'update-branch']:
            return 0, '', ''
        return 0, '', ''

    return run_gh_stub, captured


# =============================================================================
# pr_create --head
# =============================================================================


def _prepare_pr_create_body(tmp_path, monkeypatch, body_text='B', plan_id='p'):
    """Seed PLAN_BASE_DIR with a prepared pr-create body scratch file."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    from ci_base import BODY_KIND_PR_CREATE, get_body_path  # type: ignore[import-not-found]
    path = get_body_path(plan_id, BODY_KIND_PR_CREATE)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body_text, encoding='utf-8')
    return plan_id


def test_pr_create_forwards_head_flag(monkeypatch, tmp_path):
    run_gh_stub, captured = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    plan_id = _prepare_pr_create_body(tmp_path, monkeypatch)
    ns = argparse.Namespace(
        title='T', plan_id=plan_id, slot=None, base=None, draft=False, head='feature/x'
    )
    result = github_ops.cmd_pr_create(ns)

    assert result['status'] == 'success', result
    assert any('--head' in c and 'feature/x' in c for c in captured), captured


def test_pr_create_omits_head_when_unset(monkeypatch, tmp_path):
    run_gh_stub, captured = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    plan_id = _prepare_pr_create_body(tmp_path, monkeypatch)
    ns = argparse.Namespace(
        title='T', plan_id=plan_id, slot=None, base=None, draft=False, head=None
    )
    result = github_ops.cmd_pr_create(ns)

    assert result['status'] == 'success', result
    assert not any('--head' in c for c in captured), captured


# =============================================================================
# pr_view --head
# =============================================================================


def test_pr_view_forwards_head_as_positional(monkeypatch):
    run_gh_stub, captured = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ns = argparse.Namespace(head='feature/x')
    result = github_ops.cmd_pr_view(ns)

    assert result['status'] == 'success', result
    pr_view_call = next(c for c in captured if c[:2] == ['pr', 'view'])
    assert 'feature/x' in pr_view_call, pr_view_call


# =============================================================================
# pr_merge --head / --pr-number
# =============================================================================


def test_pr_merge_with_head(monkeypatch):
    run_gh_stub, captured = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ns = argparse.Namespace(
        pr_number=None, head='feature/x', strategy='merge', delete_branch=False
    )
    result = github_ops.cmd_pr_merge(ns)

    assert result['status'] == 'success', result
    merge_call = next(c for c in captured if c[:2] == ['pr', 'merge'])
    assert merge_call[2] == 'feature/x'


def test_pr_merge_with_pr_number(monkeypatch):
    run_gh_stub, captured = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ns = argparse.Namespace(pr_number=42, head=None, strategy='merge', delete_branch=False)
    result = github_ops.cmd_pr_merge(ns)

    assert result['status'] == 'success', result
    merge_call = next(c for c in captured if c[:2] == ['pr', 'merge'])
    assert merge_call[2] == '42'


def test_pr_merge_dual_flag_rejected(monkeypatch):
    run_gh_stub, captured = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ns = argparse.Namespace(
        pr_number=42, head='feature/x', strategy='merge', delete_branch=False
    )
    result = github_ops.cmd_pr_merge(ns)

    assert result['status'] == 'error'
    assert 'exactly one' in result['error']
    assert captured == [], 'Should not invoke gh when validation fails'


def test_pr_merge_neither_flag_rejected(monkeypatch):
    run_gh_stub, captured = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ns = argparse.Namespace(pr_number=None, head=None, strategy='merge', delete_branch=False)
    result = github_ops.cmd_pr_merge(ns)

    assert result['status'] == 'error'
    assert 'either' in result['error']


# =============================================================================
# pr_auto_merge --head
# =============================================================================


def test_pr_auto_merge_with_head(monkeypatch):
    run_gh_stub, captured = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ns = argparse.Namespace(pr_number=None, head='feature/x', strategy='merge')
    result = github_ops.cmd_pr_auto_merge(ns)

    assert result['status'] == 'success', result
    merge_call = next(c for c in captured if c[:2] == ['pr', 'merge'])
    assert merge_call[2] == 'feature/x'
    assert '--auto' in merge_call


def test_pr_auto_merge_dual_flag_rejected(monkeypatch):
    run_gh_stub, _ = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ns = argparse.Namespace(pr_number=42, head='feature/x', strategy='merge')
    result = github_ops.cmd_pr_auto_merge(ns)

    assert result['status'] == 'error'
    assert 'exactly one' in result['error']


# =============================================================================
# pr_update_branch --head / --pr-number
# =============================================================================


def test_pr_update_branch_with_head(monkeypatch):
    run_gh_stub, captured = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ns = argparse.Namespace(pr_number=None, head='feature/x')
    result = github_ops.cmd_pr_update_branch(ns)

    assert result['status'] == 'success', result
    update_call = next(c for c in captured if c[:2] == ['pr', 'update-branch'])
    assert update_call[2] == 'feature/x'


def test_pr_update_branch_with_pr_number(monkeypatch):
    run_gh_stub, captured = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ns = argparse.Namespace(pr_number=42, head=None)
    result = github_ops.cmd_pr_update_branch(ns)

    assert result['status'] == 'success', result
    update_call = next(c for c in captured if c[:2] == ['pr', 'update-branch'])
    assert update_call[2] == '42'


def test_pr_update_branch_dual_flag_rejected(monkeypatch):
    run_gh_stub, captured = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ns = argparse.Namespace(pr_number=42, head='feature/x')
    result = github_ops.cmd_pr_update_branch(ns)

    assert result['status'] == 'error'
    assert 'exactly one' in result['error']
    assert captured == [], 'Should not invoke gh when validation fails'


def test_pr_update_branch_neither_flag_rejected(monkeypatch):
    run_gh_stub, captured = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ns = argparse.Namespace(pr_number=None, head=None)
    result = github_ops.cmd_pr_update_branch(ns)

    assert result['status'] == 'error'
    assert 'either' in result['error']


def test_pr_update_branch_gh_failure(monkeypatch):
    """When gh returns non-zero, the handler should return an error result."""

    def failing_run_gh(args, capture_json=False, timeout=60):
        if args[:2] == ['pr', 'update-branch']:
            return 1, '', 'merge conflict'
        return 0, '', ''

    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', failing_run_gh)

    ns = argparse.Namespace(pr_number=42, head=None)
    result = github_ops.cmd_pr_update_branch(ns)

    assert result['status'] == 'error'
    assert 'Failed to update branch' in result['error']


def test_pr_update_branch_auth_failure(monkeypatch):
    """When auth fails, the handler should return an error result."""
    monkeypatch.setattr(github_ops, 'check_auth', lambda: (False, 'not logged in'))
    monkeypatch.setattr(github_ops, 'run_gh', _capture_run_gh()[0])

    ns = argparse.Namespace(pr_number=42, head=None)
    result = github_ops.cmd_pr_update_branch(ns)

    assert result['status'] == 'error'
    assert 'not logged in' in result['error']


# =============================================================================
# ci_status --head
# =============================================================================


def test_ci_status_with_head(monkeypatch):
    run_gh_stub, captured = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ns = argparse.Namespace(pr_number=None, head='feature/x')
    result = github_ops.cmd_ci_status(ns)

    assert result['status'] == 'success', result
    checks_call = next(c for c in captured if c[:2] == ['pr', 'checks'])
    assert checks_call[2] == 'feature/x'


def test_ci_status_dual_flag_rejected(monkeypatch):
    run_gh_stub, _ = _capture_run_gh()
    monkeypatch.setattr(github_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(github_ops, 'run_gh', run_gh_stub)

    ns = argparse.Namespace(pr_number=42, head='feature/x')
    result = github_ops.cmd_ci_status(ns)

    assert result['status'] == 'error'
    assert 'exactly one' in result['error']


# =============================================================================
# --project-dir pre-parse plumbing (cwd forwarding)
# =============================================================================


def test_main_project_dir_sets_default_cwd(tmp_path, monkeypatch, capsys):
    """github_ops.main() strips --project-dir from argv and installs it as the
    process-global default cwd used by ci_base.run_cli."""
    import sys

    import ci_base  # type: ignore[import-not-found]

    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    monkeypatch.setattr(ci_base, '_DEFAULT_CWD', None, raising=False)

    worktree = str(tmp_path / 'worktree')
    monkeypatch.setattr(
        sys,
        'argv',
        [
            'github_ops.py',
            '--project-dir',
            worktree,
            'pr',
            'prepare-body',
            '--plan-id',
            'test-plan',
        ],
    )

    rc = github_ops.main()
    assert rc == 0
    # Default cwd was installed before argparse ran.
    assert ci_base.get_default_cwd() == worktree
    # argv was stripped so argparse never saw --project-dir.
    assert '--project-dir' not in sys.argv
    # prepare-body emitted a success TOON payload.
    out = capsys.readouterr().out
    assert 'status' in out and 'success' in out


def test_main_project_dir_equals_form(tmp_path, monkeypatch, capsys):
    """The --project-dir=PATH form is also honoured by github_ops.main()."""
    import sys

    import ci_base  # type: ignore[import-not-found]

    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    monkeypatch.setattr(ci_base, '_DEFAULT_CWD', None, raising=False)

    worktree = str(tmp_path / 'wt2')
    monkeypatch.setattr(
        sys,
        'argv',
        [
            'github_ops.py',
            f'--project-dir={worktree}',
            'pr',
            'prepare-body',
            '--plan-id',
            'eq-plan',
        ],
    )

    rc = github_ops.main()
    assert rc == 0
    assert ci_base.get_default_cwd() == worktree
    capsys.readouterr()  # drain


def test_main_without_project_dir_leaves_cwd_untouched(tmp_path, monkeypatch):
    """Omitting --project-dir must not mutate the process-global default cwd."""
    import sys

    import ci_base  # type: ignore[import-not-found]

    sentinel = str(tmp_path / 'sentinel')
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    monkeypatch.setattr(ci_base, '_DEFAULT_CWD', sentinel, raising=False)

    monkeypatch.setattr(
        sys,
        'argv',
        [
            'github_ops.py',
            'pr',
            'prepare-body',
            '--plan-id',
            'noflag',
        ],
    )

    rc = github_ops.main()
    assert rc == 0
    # Unchanged sentinel — pre-parse did not clobber an existing default.
    assert ci_base.get_default_cwd() == sentinel
