#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""PLAN-LB-105 D2 — a removal that was decided on is decided once.

The accepted-removal set lives in the plan's status record, keyed by the D1 test
identity plus the number of removed assertions. Its two sources are an outline
deliverable that declares the removals and an operator close that accepts a
``weakened_test`` finding. A removal nobody decided on still blocks at every head.
"""

from __future__ import annotations

import json
import os
import subprocess
from argparse import Namespace
from pathlib import Path
from typing import Any

import _cmd_loop_back as _loop_back
import _criteria_snapshot as _snap
import _findings_core
import _review_support_attribution as _attr
import _review_support_integrity as _integrity
import review_support

from conftest import get_skill_dir, load_script_module

PLAN_ID = 'lb105-accepted-removals-d2'

_status_query = load_script_module('plan-marshall', 'manage-status', '_status_query.py', '_lb105_d2_query')
_lifecycle = load_script_module('plan-marshall', 'manage-status', '_cmd_lifecycle.py', '_lb105_d2_lifecycle')

BEFORE = 'def test_a():\n    assert 1 == 1\n    assert 2 == 2\n\ndef test_b():\n    assert 3 == 3\n'
AFTER_REMOVED = 'def test_b():\n    assert 3 == 3\n'


def _outline(criteria: list[str], removals: list[str] | None = None) -> str:
    body = '\n'.join(f'- {text}' for text in criteria)
    removed = ''
    if removals:
        removed = '**Tests to remove:**\n' + ''.join(f'- `{name}`\n' for name in removals) + '\n'
    return (
        '# Solution: weakened tests\n\n## Deliverables\n\n### 1. Deliver the change\n\n'
        '**Affected files:**\n- `src/parser.py` (write-new)\n\n'
        f'{removed}**Success Criteria:**\n{body}\n'
    )


def _plan(
    plan_context: Any,
    criteria: list[str] | None = None,
    *,
    removals: list[str] | None = None,
    use_worktree: bool = False,
    write_status: bool = True,
) -> Path:
    plan_dir = Path(plan_context.plan_dir_for(PLAN_ID))
    (plan_dir / 'references.json').write_text(json.dumps({'base_branch': 'main'}), encoding='utf-8')
    (plan_dir / 'solution_outline.md').write_text(
        _outline(criteria or ['parser accepts input'], removals), encoding='utf-8'
    )
    if write_status:
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
                    {'criterion': text, 'status': 'met', 'evidence': ['pyproject.toml:1']} for text in criteria
                ],
            }
        ],
        'unrequested_changes': [],
        'self_reports': [],
        'files_read': ['pyproject.toml'],
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


def _removed_repo(tmp_path: Path) -> Path:
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    _commit(repo, {'test/sample_test.py': BEFORE})
    _git(repo, 'checkout', '--quiet', '-b', 'feature')
    _commit(repo, {'test/sample_test.py': AFTER_REMOVED})
    return repo


def _blocking(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [f for f in payload.get('findings') or [] if f['kind'] == 'weakened_test' and f['severity'] == 'blocking']


# --- D2 (a): an operator close decides the removal once --------------------------------------


def test_accepted_removal_at_head_a_is_not_reported_at_head_b(plan_context, tmp_path, monkeypatch) -> None:
    repo = _removed_repo(tmp_path)
    monkeypatch.chdir(repo)
    _lifecycle.cmd_create(
        Namespace(
            plan_id=PLAN_ID,
            title='Accepted removals',
            phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
            force=False,
        )
    )
    head_a = _git(repo, 'rev-parse', 'HEAD')
    marked = _loop_back.cmd_mark_step_done(
        Namespace(
            plan_id=PLAN_ID,
            phase='6-finalize',
            step=_loop_back.FUNCTIONAL_REVIEW_STEP,
            outcome='loop_back',
            display_detail='functional review found 1 blocking, 0 advisory',
            head_at_completion=head_a,
            loop_back_target='6-finalize',
            fact=None,
            force=False,
            no_completion_log=False,
        )
    )
    assert marked is not None and marked['status'] == 'success', marked
    monkeypatch.setattr(_integrity, 'resolve_live_worktree', lambda _plan_id: repo)
    monkeypatch.setattr(_attr, 'resolve_live_worktree', lambda _plan_id: None)
    criteria = ['parser accepts input']
    plan_dir = _plan(plan_context, criteria, write_status=False)
    status = json.loads((plan_dir / 'status.json').read_text(encoding='utf-8'))
    status.setdefault('metadata', {})['use_worktree'] = False
    (plan_dir / 'status.json').write_text(json.dumps(status), encoding='utf-8')
    filed = _findings_core.add_qgate_finding(
        PLAN_ID,
        '6-finalize',
        'qgate',
        'bug',
        'weakened_test at test/sample_test.py',
        'a removed assertion [fix_kind correction]',
        rule='functional-review',
    )
    assert filed['status'] == 'success', filed

    closed = _loop_back.cmd_loop_back_close(
        Namespace(
            plan_id=PLAN_ID,
            step=_loop_back.FUNCTIONAL_REVIEW_STEP,
            head=head_a,
            accept=[filed['hash_id']],
            rationale='the test removal is the deliverable',
            waive_refire=[],
        )
    )

    assert closed is not None and closed['status'] == 'success', closed
    # A later fix commit, the same removed set.
    _commit(repo, {'src/other.py': 'x\n'})
    payload = review_support.run_validate(PLAN_ID, 'functional', _sealed(tmp_path, criteria), None)

    assert _blocking(payload) == [], payload['findings']
    assert {'identity': 'test_a', 'assertions_removed': 2} in payload['accepted_removals'], payload['accepted_removals']


# --- D2 (b): an outline declaration decides the removal --------------------------------------


def test_declared_removal_yields_no_blocking_row(plan_context, tmp_path, monkeypatch) -> None:
    repo = _removed_repo(tmp_path)
    monkeypatch.setattr(_integrity, 'resolve_live_worktree', lambda _plan_id: repo)
    monkeypatch.setattr(_attr, 'resolve_live_worktree', lambda _plan_id: None)
    criteria = ['parser accepts input']
    _plan(plan_context, criteria, removals=['test_a'])
    # The declaration is recorded when the criteria snapshot is frozen — reading
    # the live outline at validation time would be a second acceptance route.
    assert _snap.write_snapshot(PLAN_ID)['status'] == 'success'

    payload = review_support.run_validate(PLAN_ID, 'functional', _sealed(tmp_path, criteria), None)

    assert _blocking(payload) == [], payload['findings']
    assert {'identity': 'test_a', 'assertions_removed': 2} in payload['accepted_removals'], payload['accepted_removals']


# --- D2 controls: a removal nobody decided on still blocks ----------------------------------


def test_a_java_class_removal_is_declared_and_accepted(plan_context, tmp_path, monkeypatch) -> None:
    """A test class whose language has no per-function leg still has an identity.

    The consumer that saw this defect runs Maven, so a file-level-only row must
    still be decidable: the class header gives it an identity, and a declared
    removal of that class suppresses the row.
    """
    repo = _repo(tmp_path)
    java = 'package com.example;\n\npublic class SampleTest {\n    @Test\n    public void present() {\n        Assertions.assertEquals(1, 1);\n    }\n}\n'
    _commit(repo, {'README.md': 'readme\n'})
    _commit(repo, {'src/test/java/com/example/SampleTest.java': java})
    _git(repo, 'checkout', '--quiet', '-b', 'feature')
    _git(repo, 'rm', 'src/test/java/com/example/SampleTest.java')
    _git(repo, 'commit', '--quiet', '-m', 'delete')
    monkeypatch.setattr(_integrity, 'resolve_live_worktree', lambda _plan_id: repo)
    monkeypatch.setattr(_attr, 'resolve_live_worktree', lambda _plan_id: None)
    criteria = ['parser accepts input']
    _plan(plan_context, criteria, removals=['SampleTest'])
    assert _snap.write_snapshot(PLAN_ID)['status'] == 'success'

    payload = review_support.run_validate(PLAN_ID, 'functional', _sealed(tmp_path, criteria), None)

    assert _blocking(payload) == [], payload['findings']
    assert any(entry['identity'] == 'SampleTest' for entry in payload['accepted_removals']), payload[
        'accepted_removals'
    ]


def test_undeclared_removal_is_blocking_at_every_head(plan_context, tmp_path, monkeypatch) -> None:
    repo = _removed_repo(tmp_path)
    monkeypatch.setattr(_integrity, 'resolve_live_worktree', lambda _plan_id: repo)
    monkeypatch.setattr(_attr, 'resolve_live_worktree', lambda _plan_id: None)
    criteria = ['parser accepts input']
    _plan(plan_context, criteria)

    payload = review_support.run_validate(PLAN_ID, 'functional', _sealed(tmp_path, criteria), None)

    assert _blocking(payload), payload['findings']
    assert payload['accepted_removals'] == []


def test_a_second_removed_test_is_raised_even_though_the_first_was_accepted(
    plan_context, tmp_path, monkeypatch
) -> None:
    repo = _removed_repo(tmp_path)
    monkeypatch.setattr(_integrity, 'resolve_live_worktree', lambda _plan_id: repo)
    monkeypatch.setattr(_attr, 'resolve_live_worktree', lambda _plan_id: None)
    criteria = ['parser accepts input']
    _plan(plan_context, criteria, removals=['test_a'])
    # head B removes a second test.
    _commit(repo, {'test/sample_test.py': ''})

    payload = review_support.run_validate(PLAN_ID, 'functional', _sealed(tmp_path, criteria), None)

    blocking = _blocking(payload)
    assert blocking, payload['findings']
    assert any('test_b' in str(finding.get('title', '')) for finding in blocking), blocking


# --- D2 (c): the two documents state the rule identically -----------------------------------


#: The one sentence both documents must carry. Kept as a constant so the test
#: fails when either document is reworded away from it.
DECLARED_REMOVAL_RULE = 'A declared removal is accepted, and an undeclared one blocks until an operator accepts it.'


def test_section_3e_and_the_rubric_state_the_declared_removal_rule_identically() -> None:
    finalize = get_skill_dir('plan-marshall', 'phase-6-finalize')
    section = (finalize / 'workflow' / 'functional-review.md').read_text(encoding='utf-8')
    rubric = (finalize / 'standards' / 'review-rubric.md').read_text(encoding='utf-8')

    assert DECLARED_REMOVAL_RULE in section
    assert DECLARED_REMOVAL_RULE in rubric


# --- D2 (d): the new key is protected -------------------------------------------------------


def test_the_accepted_removal_key_is_protected_and_a_generic_set_is_refused(plan_context) -> None:
    plan_dir = _plan(plan_context)
    assert _snap.ACCEPTED_TEST_REMOVALS_KEY in _snap.PROTECTED_STATUS_METADATA_KEYS

    result = _status_query.cmd_metadata(
        Namespace(
            plan_id=PLAN_ID,
            set=True,
            get=False,
            append=False,
            field=_snap.ACCEPTED_TEST_REMOVALS_KEY,
            value='[]',
        )
    )

    assert result['status'] == 'error'
    assert result['error'] == 'protected_metadata_key'
    metadata = json.loads((plan_dir / 'status.json').read_text(encoding='utf-8')).get('metadata') or {}
    assert _snap.ACCEPTED_TEST_REMOVALS_KEY not in metadata
