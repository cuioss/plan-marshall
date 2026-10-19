#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""PLAN-LB-70 D4 — the deleted-assertion rows reach the validator.

Two behaviours:

* a branch that removes an assertion produces a validator finding, with no prose
  step the author might skip;
* removing one assertion and adding one elsewhere in the same file is still
  reported, by matching per test function (net-count evasion).

The tree-dependent behaviours run against a REAL temporary git repository; only
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

PLAN_ID = 'lb70-weakened-test-d4'

STRONG_TEST = 'def test_a():\n    assert 1 == 1\n    assert 2 == 2\n'
WEAK_TEST = 'def test_a():\n    assert 1 == 1\n'
#: One assertion removed from ``test_a`` and one added to ``test_b``: the FILE
#: total is unchanged, so only a per-function match sees the loss.
BEFORE_NET = 'def test_a():\n    assert 1 == 1\n    assert 2 == 2\n\ndef test_b():\n    assert 3 == 3\n'
AFTER_NET = 'def test_a():\n    assert 1 == 1\n\ndef test_b():\n    assert 3 == 3\n    assert 4 == 4\n'


def _outline(criteria: list[str]) -> str:
    body = '\n'.join(f'- {text}' for text in criteria)
    return (
        '# Solution: weakened tests\n\n## Deliverables\n\n### 1. Deliver the change\n\n'
        '**Affected files:**\n- `src/parser.py` (write-new)\n\n'
        f'**Success Criteria:**\n{body}\n'
    )


def _plan(plan_context: Any, criteria: list[str] | None = None) -> Path:
    plan_dir = Path(plan_context.plan_dir_for(PLAN_ID))
    (plan_dir / 'references.json').write_text(json.dumps({'base_branch': 'main'}), encoding='utf-8')
    (plan_dir / 'solution_outline.md').write_text(_outline(criteria or ['parser accepts input']), encoding='utf-8')
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


# --- D4 (a): a removed assertion produces a validator finding -------------------------------


def test_removed_assertion_reaches_the_validator(plan_context, tmp_path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    _commit(repo, {'test/sample_test.py': STRONG_TEST})
    _git(repo, 'checkout', '--quiet', '-b', 'feature')
    _commit(repo, {'test/sample_test.py': WEAK_TEST})
    monkeypatch.setattr(_integrity, 'resolve_live_worktree', lambda _plan_id: repo)
    monkeypatch.setattr(_attr, 'resolve_live_worktree', lambda _plan_id: None)
    criteria = ['parser accepts input']
    _plan(plan_context, criteria)

    payload = review_support.run_validate(PLAN_ID, 'functional', _sealed(tmp_path, criteria), None)

    finding = next((f for f in payload['findings'] if f['kind'] == 'weakened_test'), None)
    assert finding is not None, payload['findings']
    assert finding['severity'] == 'blocking'
    assert payload['may_close'] is False


def test_unchanged_test_file_yields_no_validator_finding(plan_context, tmp_path, monkeypatch) -> None:
    """The positive control: an untouched test file raises no weakened-test finding."""
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    _commit(repo, {'test/sample_test.py': STRONG_TEST})
    _git(repo, 'checkout', '--quiet', '-b', 'feature')
    _commit(repo, {'src/other.py': 'x\n'})
    monkeypatch.setattr(_integrity, 'resolve_live_worktree', lambda _plan_id: repo)
    monkeypatch.setattr(_attr, 'resolve_live_worktree', lambda _plan_id: None)
    criteria = ['parser accepts input']
    _plan(plan_context, criteria)

    payload = review_support.run_validate(PLAN_ID, 'functional', _sealed(tmp_path, criteria), None)

    assert [f for f in payload['findings'] if f['kind'] == 'weakened_test'] == []
    assert payload['valid'] is True


# --- D4 (b): net-count evasion is still reported --------------------------------------------


def test_net_count_evasion_is_reported(plan_context, tmp_path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    _commit(repo, {'test/sample_test.py': BEFORE_NET})
    _git(repo, 'checkout', '--quiet', '-b', 'feature')
    _commit(repo, {'test/sample_test.py': AFTER_NET})
    monkeypatch.setattr(_integrity, 'resolve_live_worktree', lambda _plan_id: repo)
    _plan(plan_context)

    payload = _integrity.compute_test_integrity(PLAN_ID)

    assert [row['kind'] for row in payload['findings']] == ['assertion_removed'], payload['findings']
    assert payload['findings'][0]['removed_assertions'] == 1
