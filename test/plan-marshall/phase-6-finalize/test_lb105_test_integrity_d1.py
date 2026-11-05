#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""PLAN-LB-105 D1 — a moved, renamed or split test is not a lost assertion.

The test-integrity check reads a branch as a whole test set rather than one path
at a time, reads its pre-image at the merge base, names a test by an identity
that survives a file move, and grades a plan that runs without a worktree
against the main checkout instead of skipping it.

Every tree-dependent behaviour runs against a REAL temporary git repository; only
the plan-context worktree resolver is substituted.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

import _review_support_attribution as _attr
import _review_support_integrity as _integrity
import review_support

PLAN_ID = 'lb105-test-integrity-d1'

STRONG = 'def test_a():\n    assert 1 == 1\n    assert 2 == 2\n\ndef test_b():\n    assert 3 == 3\n'
SPLIT_LEFT = 'def test_a():\n    assert 1 == 1\n    assert 2 == 2\n'
SPLIT_RIGHT = 'def test_b():\n    assert 3 == 3\n'
JAVA_TEST = (
    'package com.example;\n\n'
    'public class SampleTest {\n'
    '    @Test\n'
    '    public void present() {\n'
    '        Assertions.assertEquals(1, 1);\n'
    '    }\n'
    '}\n'
)


# --- fixture plumbing -----------------------------------------------------------------------


def _outline(criteria: list[str]) -> str:
    body = '\n'.join(f'- {text}' for text in criteria)
    return (
        '# Solution: weakened tests\n\n## Deliverables\n\n### 1. Deliver the change\n\n'
        '**Affected files:**\n- `src/parser.py` (write-new)\n\n'
        f'**Success Criteria:**\n{body}\n'
    )


def _plan(plan_context: Any, criteria: list[str] | None = None, *, use_worktree: bool = False) -> Path:
    plan_dir = Path(plan_context.plan_dir_for(PLAN_ID))
    (plan_dir / 'references.json').write_text(json.dumps({'base_branch': 'main'}), encoding='utf-8')
    (plan_dir / 'solution_outline.md').write_text(_outline(criteria or ['parser accepts input']), encoding='utf-8')
    (plan_dir / 'status.json').write_text(
        json.dumps(
            {
                'title': 'fixture',
                'phases': [],
                'current_phase': '6-finalize',
                'metadata': {'use_worktree': use_worktree},
            }
        ),
        encoding='utf-8',
    )
    return plan_dir


def _verdict(criteria: list[str]) -> dict[str, Any]:
    return {
        'deliverables': [
            {
                'number': 1,
                'verdict': 'met',
                'criteria': [
                    {'criterion': text, 'status': 'met', 'evidence': ['src/parser.py:1']} for text in criteria
                ],
            }
        ],
        'unrequested_changes': [],
        'self_reports': [],
        'files_read': ['src/parser.py'],
    }


def _sealed(tmp_path: Path, criteria: list[str]) -> str:
    path = tmp_path / 'verdict.json'
    path.write_text(json.dumps(_verdict(criteria)), encoding='utf-8')
    assert review_support.run_author_verdict(PLAN_ID, 'functional', str(path))['status'] == 'success'
    return str(path)


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


def _commit(repo: Path, files: dict[str, str]) -> str:
    for relative, body in files.items():
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding='utf-8')
        _git(repo, 'add', relative)
    subprocess.run(
        ['git', '-C', str(repo), 'commit', '--quiet', '--message', 'commit'],
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


def _rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [row for row in payload.get('findings') or [] if row.get('kind') == 'assertion_removed']


# --- D1: a move, a rename and a split are not losses ----------------------------------------


def test_moved_python_test_yields_no_row(plan_context, tmp_path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    _commit(repo, {'test/sample_test.py': STRONG})
    _git(repo, 'checkout', '--quiet', '-b', 'feature')
    _git(repo, 'mv', 'test/sample_test.py', 'test/renamed_sample_test.py')
    _git(repo, 'commit', '--quiet', '-m', 'move')
    monkeypatch.setattr(_integrity, 'resolve_live_worktree', lambda _plan_id: repo)
    _plan(plan_context)

    payload = _integrity.compute_test_integrity(PLAN_ID)

    assert payload['status'] == 'success', payload
    assert _rows(payload) == [], payload


def test_split_test_file_yields_no_row(plan_context, tmp_path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    _commit(repo, {'test/sample_test.py': STRONG})
    _git(repo, 'checkout', '--quiet', '-b', 'feature')
    _git(repo, 'rm', 'test/sample_test.py')
    _commit(repo, {'test/sample_left_test.py': SPLIT_LEFT, 'test/sample_right_test.py': SPLIT_RIGHT})
    monkeypatch.setattr(_integrity, 'resolve_live_worktree', lambda _plan_id: repo)
    _plan(plan_context)

    payload = _integrity.compute_test_integrity(PLAN_ID)

    assert _rows(payload) == [], payload


def test_moved_java_test_class_yields_no_row(plan_context, tmp_path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    _commit(repo, {'src/test/java/com/example/SampleTest.java': JAVA_TEST})
    _git(repo, 'checkout', '--quiet', '-b', 'feature')
    (repo / 'src/test/java/com/example/moved').mkdir(parents=True, exist_ok=True)
    _git(repo, 'mv', 'src/test/java/com/example/SampleTest.java', 'src/test/java/com/example/moved/SampleTest.java')
    _git(repo, 'commit', '--quiet', '-m', 'move')
    monkeypatch.setattr(_integrity, 'resolve_live_worktree', lambda _plan_id: repo)
    _plan(plan_context)

    payload = _integrity.compute_test_integrity(PLAN_ID)

    assert _rows(payload) == [], payload


# --- D1: the pre-image is the merge base ----------------------------------------------------


def test_mainline_assertion_is_not_a_removal(plan_context, tmp_path, monkeypatch) -> None:
    """An assertion the base branch gained after the branch point is not lost."""
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    _commit(repo, {'test/sample_test.py': STRONG})
    _git(repo, 'checkout', '--quiet', '-b', 'feature')
    _commit(repo, {'src/other.py': 'x\n'})
    # The base branch moves ahead: an assertion is added to a test file the
    # branch never touched, so the base tip and the merge base disagree.
    _git(repo, 'checkout', '--quiet', 'main')
    _commit(
        repo, {'test/sample_test.py': STRONG.replace('    assert 3 == 3\n', '    assert 3 == 3\n    assert 4 == 4\n')}
    )
    _git(repo, 'checkout', '--quiet', 'feature')
    monkeypatch.setattr(_integrity, 'resolve_live_worktree', lambda _plan_id: repo)
    _plan(plan_context)

    payload = _integrity.compute_test_integrity(PLAN_ID)

    assert _rows(payload) == [], payload


def test_assertion_moved_between_methods_is_reported(plan_context, tmp_path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    _commit(
        repo,
        {
            'test/class_test.py': (
                'class TestThing:\n'
                '    def test_one(self):\n'
                '        assert 1 == 1\n'
                '        assert 2 == 2\n\n'
                '    def test_two(self):\n'
                '        assert 3 == 3\n'
            )
        },
    )
    _git(repo, 'checkout', '--quiet', '-b', 'feature')
    _commit(
        repo,
        {
            'test/class_test.py': (
                'class TestThing:\n'
                '    def test_one(self):\n'
                '        assert 1 == 1\n\n'
                '    def test_two(self):\n'
                '        assert 3 == 3\n'
                '        assert 2 == 2\n'
            )
        },
    )
    monkeypatch.setattr(_integrity, 'resolve_live_worktree', lambda _plan_id: repo)
    _plan(plan_context)

    payload = _integrity.compute_test_integrity(PLAN_ID)

    rows = _rows(payload)
    assert rows, payload
    assert 'TestThing::test_one' in rows[0].get('removed_tests', [{}])[0].get('identity', '') or any(
        removed.get('identity') == 'TestThing::test_one' for removed in rows[0].get('removed_tests') or []
    ), rows


def test_async_def_test_losing_an_assertion_is_reported(plan_context, tmp_path, monkeypatch) -> None:
    """A test named by `async def` is a named test: its loss is not masked by a
    sibling that gained the same number of assertions."""
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    _commit(
        repo,
        {
            'test/async_test.py': (
                'async def test_a():\n    assert 1 == 1\n    assert 2 == 2\n\ndef test_b():\n    assert 3 == 3\n'
            )
        },
    )
    _git(repo, 'checkout', '--quiet', '-b', 'feature')
    _commit(
        repo,
        {
            'test/async_test.py': (
                'async def test_a():\n    assert 1 == 1\n\ndef test_b():\n    assert 3 == 3\n    assert 2 == 2\n'
            )
        },
    )
    monkeypatch.setattr(_integrity, 'resolve_live_worktree', lambda _plan_id: repo)
    _plan(plan_context)

    payload = _integrity.compute_test_integrity(PLAN_ID)

    assert _rows(payload), payload


def test_deleted_test_with_assertions_added_elsewhere_in_file_is_reported(plan_context, tmp_path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    _commit(
        repo,
        {
            'test/sample_test.py': (
                'def test_a():\n    assert 1 == 1\n    assert 2 == 2\n\ndef test_b():\n    assert 3 == 3\n'
            )
        },
    )
    _git(repo, 'checkout', '--quiet', '-b', 'feature')
    # test_a is deleted and its two assertions added to test_b: the file count is
    # unchanged.
    _commit(repo, {'test/sample_test.py': 'def test_b():\n    assert 3 == 3\n    assert 1 == 1\n    assert 2 == 2\n'})
    monkeypatch.setattr(_integrity, 'resolve_live_worktree', lambda _plan_id: repo)
    _plan(plan_context)

    payload = _integrity.compute_test_integrity(PLAN_ID)

    assert _rows(payload), payload


# --- D1: a plan without a worktree is graded, not skipped -----------------------------------


def test_no_worktree_plan_is_graded_against_the_main_checkout(plan_context, tmp_path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    _commit(repo, {'test/sample_test.py': STRONG})
    _git(repo, 'checkout', '--quiet', '-b', 'feature')
    _commit(repo, {'test/sample_test.py': STRONG.replace('    assert 2 == 2\n', '')})
    monkeypatch.setattr(_integrity, 'resolve_live_worktree', lambda _plan_id: None)
    monkeypatch.setattr(_attr, 'resolve_live_worktree', lambda _plan_id: None)
    monkeypatch.setattr(_integrity, 'main_checkout_root', lambda: repo, raising=False)
    monkeypatch.setattr(review_support, '_main_checkout_root', lambda: repo)
    criteria = ['parser accepts input']
    _plan(plan_context, criteria, use_worktree=False)

    payload = review_support.run_validate(PLAN_ID, 'functional', _sealed(tmp_path, criteria), None)

    finding = next((f for f in payload['findings'] if f['kind'] == 'weakened_test'), None)
    assert finding is not None, payload['findings']
    assert finding['severity'] == 'blocking'


# --- D1: controls — a genuine loss is still caught -------------------------------------------


def test_wholly_deleted_test_file_is_reported(plan_context, tmp_path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    _commit(repo, {'test/gone_test.py': STRONG})
    _git(repo, 'checkout', '--quiet', '-b', 'feature')
    _git(repo, 'rm', 'test/gone_test.py')
    _git(repo, 'commit', '--quiet', '-m', 'delete')
    monkeypatch.setattr(_integrity, 'resolve_live_worktree', lambda _plan_id: repo)
    _plan(plan_context)

    payload = _integrity.compute_test_integrity(PLAN_ID)

    assert _rows(payload), payload


def test_assertion_removed_from_a_named_test_is_reported(plan_context, tmp_path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    _commit(repo, {'test/sample_test.py': STRONG})
    _git(repo, 'checkout', '--quiet', '-b', 'feature')
    _commit(repo, {'test/sample_test.py': STRONG.replace('    assert 2 == 2\n', '')})
    monkeypatch.setattr(_integrity, 'resolve_live_worktree', lambda _plan_id: repo)
    _plan(plan_context)

    payload = _integrity.compute_test_integrity(PLAN_ID)

    assert _rows(payload), payload


def test_assertion_moved_to_a_new_test_is_reported(plan_context, tmp_path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    _commit(repo, {'test/sample_test.py': 'def test_a():\n    assert 1 == 1\n    assert 2 == 2\n'})
    _git(repo, 'checkout', '--quiet', '-b', 'feature')
    _commit(repo, {'test/sample_test.py': 'def test_a():\n    assert 1 == 1\n\ndef test_new():\n    assert 2 == 2\n'})
    monkeypatch.setattr(_integrity, 'resolve_live_worktree', lambda _plan_id: repo)
    _plan(plan_context)

    payload = _integrity.compute_test_integrity(PLAN_ID)

    assert _rows(payload), payload


def test_added_skip_marker_is_reported_as_test_filtered(plan_context, tmp_path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    _commit(repo, {'test/sample_test.py': 'def test_a():\n    assert 1 == 1\n'})
    _git(repo, 'checkout', '--quiet', '-b', 'feature')
    _commit(repo, {'test/sample_test.py': 'import pytest\n\n@pytest.mark.skip\ndef test_a():\n    assert 1 == 1\n'})
    monkeypatch.setattr(_integrity, 'resolve_live_worktree', lambda _plan_id: repo)
    _plan(plan_context)

    payload = _integrity.compute_test_integrity(PLAN_ID)

    assert [row['kind'] for row in payload['findings']] == ['test_filtered'], payload
