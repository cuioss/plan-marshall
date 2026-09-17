#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Tests for gitlab_ops.py — ops forwarding and success paths."""

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


def _install_merge_shaped_stubs(monkeypatch):
    """Install the merge-train preflight + corroboration prerequisites.

    ``cmd_pr_merge`` and ``cmd_pr_auto_merge`` now probe the PROJECT's merge-train
    state before acting (merge trains are a per-project flag on GitLab, so the
    probe takes no branch argument), and ``cmd_pr_merge`` corroborates ``merged``
    from a post-merge ``state == 'merged'`` re-read. Without these stubs the
    argv-routing tests below would stop testing ``--head`` resolution and start
    testing the preflight's fail-closed path instead.

    ``eligible_unconfigured`` is the permissive verdict, so routing proceeds
    unchanged.
    """
    monkeypatch.setattr(
        gitlab_ops,
        '_probe_merge_train_state',
        lambda: (
            gitlab_ops.MERGE_QUEUE_ELIGIBLE_UNCONFIGURED,
            'merge_trains_enabled=false',
            None,
        ),
    )
    monkeypatch.setattr(
        gitlab_ops,
        'view_pr_data',
        lambda head=None: {
            'status': 'success',
            'operation': 'pr_view',
            'pr_number': 7,
            'state': 'merged',
            'head_branch': 'feature/x',
            'base_branch': 'main',
        },
    )


# =============================================================================
# pr_create --head -> --source-branch
# =============================================================================
def _prepare_pr_create_body(tmp_path, monkeypatch, body_text='B', plan_id='p'):
    """Seed PLAN_BASE_DIR with a prepared pr-create body scratch file."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    from ci_base import BODY_KIND_PR_CREATE, get_body_path

    path = get_body_path(plan_id, BODY_KIND_PR_CREATE)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body_text, encoding='utf-8')
    return plan_id


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


def test_pr_create_forwards_head_as_source_branch(monkeypatch, tmp_path):
    run_glab_stub, captured = _capture_run_glab()
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)

    plan_id = _prepare_pr_create_body(tmp_path, monkeypatch)
    ns = argparse.Namespace(title='T', plan_id=plan_id, slot=None, base=None, draft=False, head='feature/x')
    result = gitlab_ops.cmd_pr_create(ns)

    assert result['status'] == 'success', result
    create_call = next(c for c in captured if c[:2] == ['mr', 'create'])
    assert '--source-branch' in create_call
    assert 'feature/x' in create_call


def test_pr_create_omits_source_branch_when_head_unset(monkeypatch, tmp_path):
    run_glab_stub, captured = _capture_run_glab()
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)

    plan_id = _prepare_pr_create_body(tmp_path, monkeypatch)
    ns = argparse.Namespace(title='T', plan_id=plan_id, slot=None, base=None, draft=False, head=None)
    result = gitlab_ops.cmd_pr_create(ns)

    assert result['status'] == 'success', result
    create_call = next(c for c in captured if c[:2] == ['mr', 'create'])
    assert '--source-branch' not in create_call


# =============================================================================
# pr_view --pr-number / --head
#
# ``glab mr view`` accepts an IID, a URL, or a branch name in the SAME positional
# slot, so the two flags are a selector CHOICE, not two code paths — and unlike the
# merge-shaped verbs, no ``mr list --source-branch`` IID lookup is spent, because
# ``mr view`` resolves the branch itself. Each case asserts the CONSTRUCTED ARGV.
# =============================================================================
def test_pr_view_forwards_head(monkeypatch):
    run_glab_stub, captured = _capture_run_glab()
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)

    ns = argparse.Namespace(head='feature/x')
    result = gitlab_ops.cmd_pr_view(ns)

    assert result['status'] == 'success', result
    view_call = next(c for c in captured if c[:2] == ['mr', 'view'])
    assert view_call[2] == 'feature/x', view_call
    assert not any(c[:3] == ['mr', 'list', '--source-branch'] for c in captured), captured


def test_pr_view_forwards_pr_number_as_positional(monkeypatch):
    """--pr-number lands in glab's positional selector slot, stringified.

    This is the landing-poll selector: a required merge train deletes the source
    branch as it merges, so a --head-keyed poll stops resolving at exactly the moment
    the merged state becomes observable. The IID survives the branch deletion.
    """
    run_glab_stub, captured = _capture_run_glab()
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)

    ns = argparse.Namespace(pr_number=1152, head=None)
    result = gitlab_ops.cmd_pr_view(ns)

    assert result['status'] == 'success', result
    view_call = next(c for c in captured if c[:2] == ['mr', 'view'])
    assert view_call[2] == '1152', view_call


def test_pr_view_omits_positional_when_no_selector(monkeypatch):
    """Neither selector keeps the historical current-cwd-HEAD lookup.

    Adding --pr-number must not have made a selector mandatory: with both omitted the
    positional slot stays empty, so --output is the token immediately after `mr view`.
    """
    run_glab_stub, captured = _capture_run_glab()
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)

    ns = argparse.Namespace(pr_number=None, head=None)
    result = gitlab_ops.cmd_pr_view(ns)

    assert result['status'] == 'success', result
    view_call = next(c for c in captured if c[:2] == ['mr', 'view'])
    assert view_call[2] == '--output', view_call


# =============================================================================
# pr_merge --head -> branch->IID lookup
# =============================================================================
def test_pr_merge_with_head_resolves_iid(monkeypatch):
    run_glab_stub, captured = _capture_run_glab(mr_list_iid=7)
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)
    _install_merge_shaped_stubs(monkeypatch)

    ns = argparse.Namespace(pr_number=None, head='feature/x', strategy='merge', delete_branch=False)
    result = gitlab_ops.cmd_pr_merge(ns)

    assert result['status'] == 'success', result
    list_call = next(c for c in captured if c[:3] == ['mr', 'list', '--source-branch'])
    assert 'feature/x' in list_call
    merge_call = next(c for c in captured if c[:2] == ['mr', 'merge'])
    assert merge_call[2] == '7'


def test_pr_merge_with_pr_number_skips_lookup(monkeypatch):
    run_glab_stub, captured = _capture_run_glab()
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)
    _install_merge_shaped_stubs(monkeypatch)

    ns = argparse.Namespace(pr_number=42, head=None, strategy='merge', delete_branch=False)
    result = gitlab_ops.cmd_pr_merge(ns)

    assert result['status'] == 'success', result
    assert not any(c[:3] == ['mr', 'list', '--source-branch'] for c in captured)
    merge_call = next(c for c in captured if c[:2] == ['mr', 'merge'])
    assert merge_call[2] == '42'


# =============================================================================
# pr_auto_merge --head
# =============================================================================
def test_pr_auto_merge_with_head_resolves_iid(monkeypatch):
    run_glab_stub, captured = _capture_run_glab(mr_list_iid=7)
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)
    _install_merge_shaped_stubs(monkeypatch)

    ns = argparse.Namespace(pr_number=None, head='feature/x', strategy='merge')
    result = gitlab_ops.cmd_pr_auto_merge(ns)

    assert result['status'] == 'success', result
    merge_call = next(c for c in captured if c[:2] == ['mr', 'merge'])
    assert merge_call[2] == '7'
    assert '--when-pipeline-succeeds' in merge_call


# =============================================================================
# ci_status --head
# =============================================================================
def test_ci_status_with_head_resolves_iid(monkeypatch):
    run_glab_stub, captured = _capture_run_glab(mr_list_iid=7)
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)

    ns = argparse.Namespace(pr_number=None, head='feature/x')
    result = gitlab_ops.cmd_ci_status(ns)

    assert result['status'] == 'success', result
    list_call = next(c for c in captured if c[:3] == ['mr', 'list', '--source-branch'])
    assert 'feature/x' in list_call
    view_call = next(c for c in captured if c[:2] == ['mr', 'view'])
    assert view_call[2] == '7'


def test_cmd_issue_comment_posts_prepared_body(monkeypatch, tmp_path):
    """cmd_issue_comment posts the prepared body via `glab issue note {iid} --message`."""
    captured: list[list[str]] = []

    def run_glab_stub(args):
        captured.append(list(args))
        return 0, '', ''

    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)

    plan_id = _prepare_issue_comment_body(tmp_path, monkeypatch, body_text='Outline ready')
    ns = argparse.Namespace(issue='42', plan_id=plan_id, slot=None)
    result = gitlab_ops.cmd_issue_comment(ns)

    assert result['status'] == 'success', result
    assert result['operation'] == 'issue_comment'
    assert result['issue_number'] == '42'
    assert captured[-1] == ['issue', 'note', '42', '--message', 'Outline ready']


def test_cmd_issue_comment_deletes_body_on_success(monkeypatch, tmp_path):
    """The prepared scratch body is removed only after a successful post."""
    from ci_base import BODY_KIND_ISSUE_COMMENT, get_body_path

    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(gitlab_ops, 'run_glab', lambda args: (0, '', ''))

    plan_id = _prepare_issue_comment_body(tmp_path, monkeypatch)
    body_path = get_body_path(plan_id, BODY_KIND_ISSUE_COMMENT)
    assert body_path.exists()

    ns = argparse.Namespace(issue='42', plan_id=plan_id, slot=None)
    result = gitlab_ops.cmd_issue_comment(ns)

    assert result['status'] == 'success', result
    assert not body_path.exists()


def test_cmd_issue_prepare_comment_allocates_path(monkeypatch, tmp_path):
    """_cmd_issue_prepare_comment allocates an issue-comment scratch path."""
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    plan_dir = tmp_path / 'plans' / 'p'
    plan_dir.mkdir(parents=True)
    (plan_dir / 'status.json').write_text('{}', encoding='utf-8')

    ns = argparse.Namespace(plan_id='p', slot=None)
    result = gitlab_ops._cmd_issue_prepare_comment(ns)

    assert result['status'] == 'success', result
    assert result['kind'] == 'issue-comment'
    assert result['path'].endswith('issue-comment-default.md')


def test_cmd_issue_comment_normalizes_full_url(monkeypatch, tmp_path):
    """A full GitLab issue URL in --issue is normalized to the IID for `glab issue note` and the return."""
    captured: list[list[str]] = []

    def run_glab_stub(args):
        captured.append(list(args))
        return 0, '', ''

    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)

    plan_id = _prepare_issue_comment_body(tmp_path, monkeypatch, body_text='Outline ready')
    ns = argparse.Namespace(issue='https://gitlab.com/o/r/-/issues/42', plan_id=plan_id, slot=None)
    result = gitlab_ops.cmd_issue_comment(ns)

    assert result['status'] == 'success', result
    assert result['issue_number'] == '42'
    assert captured[-1] == ['issue', 'note', '42', '--message', 'Outline ready']
