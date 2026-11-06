#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""PLAN-LB-118 D4 — the evidence root and the git calls fail closed.

A no-worktree plan is graded only when the main checkout carries the plan's work —
not on the base branch, not dirty. A git timeout is a named state, not a traceback;
a failed ``git show`` is not "the file did not exist"; non-ASCII paths are read
literally; and a missing merge base is reported by name instead of falling back to
the base tip.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

import _review_support_integrity as _integrity
import pytest

PLAN_ID = 'lb118-integrity-evidence-root-d4'


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(['git', '-C', str(repo), *args], capture_output=True, text=True, check=True).stdout.strip()


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / 'repo'
    repo.mkdir()
    for args in (('init', '--quiet'), ('symbolic-ref', 'HEAD', 'refs/heads/main')):
        _git(repo, *args)
    for key, value in (('user.email', 't@example.invalid'), ('user.name', 'T'), ('commit.gpgsign', 'false')):
        _git(repo, 'config', key, value)
    return repo


def _commit(repo: Path, files: dict[str, str], message: str = 'commit') -> str:
    for relative, body in files.items():
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding='utf-8')
        _git(repo, 'add', relative)
    subprocess.run(
        ['git', '-C', str(repo), 'commit', '--quiet', '--message', message],
        capture_output=True,
        text=True,
        check=True,
        env={
            **os.environ,
            'GIT_COMMITTER_DATE': '2020-01-01T00:00:00+00:00',
            'GIT_AUTHOR_DATE': '2020-01-01T00:00:00+00:00',
        },
    )
    return _git(repo, 'rev-parse', 'HEAD')


def _plan(plan_context: Any) -> Path:
    plan_dir = Path(plan_context.plan_dir_for(PLAN_ID))
    (plan_dir / 'references.json').write_text(json.dumps({'base_branch': 'main'}), encoding='utf-8')
    (plan_dir / 'status.json').write_text(
        json.dumps(
            {
                'title': 'fixture',
                'phases': [],
                'current_phase': '6-finalize',
                'metadata': {'use_worktree': False},
            }
        ),
        encoding='utf-8',
    )
    return plan_dir


def _rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [row for row in payload.get('findings') or [] if row.get('kind') == 'assertion_removed']


def test_a_no_worktree_plan_on_the_base_branch_does_not_pass(plan_context, tmp_path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    _plan(plan_context)
    monkeypatch.setattr(_integrity, 'resolve_live_worktree', lambda _plan_id: None)
    monkeypatch.setattr(_integrity, 'main_checkout_root', lambda: repo)

    payload = _integrity.compute_test_integrity(PLAN_ID)

    assert payload['status'] == 'error', payload
    assert payload['error'] == 'evidence_root_unresolved', payload
    assert 'main_checkout_on_base_branch' in payload['message'], payload


def test_a_no_worktree_plan_on_the_base_branch_with_an_origin_does_not_pass(
    plan_context, tmp_path, monkeypatch
) -> None:
    """The guard compares commits: ``resolve_base_ref`` returns ``origin/main`` here."""
    repo = _repo(tmp_path)
    head = _commit(repo, {'README.md': 'readme\n'})
    _git(repo, 'remote', 'add', 'origin', str(repo))
    _git(repo, 'update-ref', 'refs/remotes/origin/main', head)
    _plan(plan_context)
    monkeypatch.setattr(_integrity, 'resolve_live_worktree', lambda _plan_id: None)
    monkeypatch.setattr(_integrity, 'main_checkout_root', lambda: repo)

    payload = _integrity.compute_test_integrity(PLAN_ID)

    assert payload['status'] == 'error', payload
    assert payload['error'] == 'evidence_root_unresolved', payload
    assert 'main_checkout_on_base_branch' in payload['message'], payload


def test_a_dirty_no_worktree_checkout_does_not_pass(plan_context, tmp_path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    _git(repo, 'checkout', '--quiet', '-b', 'feature')
    # Commit branch work first, so HEAD is not the base tip and the dirty guard is
    # the one that fires.
    _commit(repo, {'test/sample_test.py': 'def test_a():\n    assert 1 == 1\n'}, 'branch work')
    (repo / 'README.md').write_text('uncommitted\n', encoding='utf-8')
    _plan(plan_context)
    monkeypatch.setattr(_integrity, 'resolve_live_worktree', lambda _plan_id: None)
    monkeypatch.setattr(_integrity, 'main_checkout_root', lambda: repo)

    payload = _integrity.compute_test_integrity(PLAN_ID)

    assert payload['status'] == 'error', payload
    assert payload['error'] == 'evidence_root_unresolved', payload
    assert 'main_checkout_dirty' in payload['message'], payload


def test_a_git_timeout_is_a_named_state(plan_context, tmp_path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    _commit(repo, {'test/sample_test.py': 'def test_a():\n    assert 1 == 1\n'})
    _git(repo, 'checkout', '--quiet', '-b', 'feature')
    _commit(repo, {'test/sample_test.py': 'def test_a():\n    pass\n'})
    _plan(plan_context)
    monkeypatch.setattr(_integrity, 'resolve_live_worktree', lambda _plan_id: repo)
    # The timeout fixture sits at the module's one git seam: every helper funnels
    # through ``_git``, which turns a TimeoutExpired into ``_GitFailure``.
    monkeypatch.setattr(_integrity, '_git', lambda *_args, **_kwargs: _raise_git_timeout())

    payload = _integrity.compute_test_integrity(PLAN_ID)

    assert payload['status'] == 'error', payload
    assert payload['error'] == 'test_integrity_not_run', payload


def _raise_git_timeout() -> None:
    raise _integrity._GitFailure('git timed out')


def test_a_non_ascii_deleted_test_path_is_read(plan_context, tmp_path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    _commit(repo, {'test/\u00fcmlaut_test.py': 'def test_a():\n    assert 1 == 1\n    assert 2 == 2\n'})
    _git(repo, 'checkout', '--quiet', '-b', 'feature')
    _git(repo, 'rm', 'test/\u00fcmlaut_test.py')
    _git(repo, 'commit', '--quiet', '-m', 'delete')
    _plan(plan_context)
    monkeypatch.setattr(_integrity, 'resolve_live_worktree', lambda _plan_id: repo)

    payload = _integrity.compute_test_integrity(PLAN_ID)

    assert payload['status'] == 'success', payload
    assert any(row['path'] == 'test/\u00fcmlaut_test.py' for row in _rows(payload)), payload


def test_a_missing_merge_base_is_reported_by_name(plan_context, tmp_path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    _commit(repo, {'test/sample_test.py': 'def test_a():\n    assert 1 == 1\n'})
    _git(repo, 'checkout', '--quiet', '-b', 'feature')
    _commit(repo, {'test/sample_test.py': 'def test_a():\n    pass\n'})
    _plan(plan_context)
    monkeypatch.setattr(_integrity, 'resolve_live_worktree', lambda _plan_id: repo)
    monkeypatch.setattr(_integrity, 'merge_base', lambda *_args, **_kwargs: None)

    payload = _integrity.compute_test_integrity(PLAN_ID)

    assert payload['status'] == 'error', payload
    assert payload['error'] == 'merge_base_unresolved', payload


def test_an_unreadable_git_status_is_a_named_state(plan_context, tmp_path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    _plan(plan_context)
    monkeypatch.setattr(_integrity, 'resolve_live_worktree', lambda _plan_id: None)
    monkeypatch.setattr(_integrity, 'main_checkout_root', lambda: repo)
    monkeypatch.setattr(_integrity, '_rev_parse', lambda _root, ref: 'a' if ref == 'HEAD' else 'b')
    failed = subprocess.CompletedProcess(args=['git'], returncode=128, stdout='', stderr='fatal: not a repo')
    monkeypatch.setattr(_integrity, '_git', lambda *_args, **_kwargs: failed)

    payload = _integrity.compute_test_integrity(PLAN_ID)

    assert payload['status'] == 'error', payload
    assert payload['error'] == 'test_integrity_not_run', payload


def test_an_unrelated_history_reports_the_missing_merge_base(plan_context, tmp_path, monkeypatch) -> None:
    """A branch with no common ancestor names the merge base, not the diff."""
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    _git(repo, 'checkout', '--quiet', '--orphan', 'feature')
    _commit(repo, {'test/sample_test.py': 'def test_a():\n    assert 1 == 1\n'}, 'orphan root')
    _plan(plan_context)
    monkeypatch.setattr(_integrity, 'resolve_live_worktree', lambda _plan_id: repo)

    payload = _integrity.compute_test_integrity(PLAN_ID)

    assert payload['status'] == 'error', payload
    assert payload['error'] == 'merge_base_unresolved', payload


def test_the_git_seam_translates_a_timeout(monkeypatch) -> None:
    def _timeout(*_args, **_kwargs):
        raise subprocess.TimeoutExpired(cmd='git', timeout=60)

    monkeypatch.setattr(_integrity.subprocess, 'run', _timeout)

    with pytest.raises(_integrity._GitFailure):
        _integrity._git(Path('.'), ['status'])


def test_a_failed_git_show_is_not_read_as_absent(monkeypatch) -> None:
    failed = subprocess.CompletedProcess(args=['git'], returncode=128, stdout='', stderr='fatal: bad object HEAD:x')
    monkeypatch.setattr(_integrity, '_git', lambda *_args, **_kwargs: failed)

    with pytest.raises(_integrity._GitFailure):
        _integrity._show(Path('.'), 'HEAD', 'x')


def test_a_missing_path_at_rev_reads_as_absent(monkeypatch) -> None:
    missing = subprocess.CompletedProcess(
        args=['git'],
        returncode=128,
        stdout='',
        stderr="fatal: path 'x' does not exist in 'HEAD'",
    )
    monkeypatch.setattr(_integrity, '_git', lambda *_args, **_kwargs: missing)

    assert _integrity._show(Path('.'), 'HEAD', 'x') is None
