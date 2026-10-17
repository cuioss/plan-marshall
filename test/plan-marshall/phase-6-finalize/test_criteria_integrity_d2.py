#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""PLAN-LB-52 D2 — what the review grades cannot be weakened on the way.

Five behaviours, each with the nearest input that must NOT produce a finding or a
refusal:

* a branch that DELETES an assertion from an existing test yields a finding;
* a "fails pre-fix" criterion evidenced only by a HEAD run is graded ``unevidenced``;
* a verdict citing a test name absent at the graded head is refused;
* a verify-first record timestamped after the gated commit is refused;
* finalize with an EMPTY bot queue and one unmet Done-when does not exit.

The tree-dependent behaviours run against a REAL temporary git repository; only
the plan-context worktree resolver is substituted.
"""

from __future__ import annotations

import json
import os
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import _criteria_snapshot as _snap
import _review_support_attribution as _attr
import _review_support_integrity as _integrity
import review_support

from conftest import load_script_module

PLAN_ID = 'criteria-integrity-d2'
CRITERIA = ['parser accepts input', 'parser rejects garbage']
_lifecycle = load_script_module('plan-marshall', 'manage-status', '_cmd_lifecycle.py', '_criteria_integrity_lifecycle')


# ---------------------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------------------


def _outline(criteria: list[str]) -> str:
    body = '\n'.join(f'- {text}' for text in criteria)
    return (
        '# Solution: criteria integrity\n\n## Summary\n\nFixture plan.\n\n## Deliverables\n\n'
        f'### 1. Deliver the parser\n\n**Affected files:**\n- `src/parser.py` (write-new)\n\n'
        f'**Success Criteria:**\n{body}\n'
    )


def _plan(plan_context: Any, criteria: list[str] | None = None, *, freeze: bool = False) -> Path:
    plan_dir = Path(plan_context.plan_dir_for(PLAN_ID))
    (plan_dir / 'solution_outline.md').write_text(_outline(criteria or CRITERIA), encoding='utf-8')
    (plan_dir / 'references.json').write_text(json.dumps({'base_branch': 'main'}), encoding='utf-8')
    if freeze:
        _snap.write_snapshot(PLAN_ID)
    return plan_dir


def _verdict(criteria: list[str], statuses: list[str], evidence: list[list[str]]) -> dict[str, Any]:
    return {
        'deliverables': [
            {
                'number': 1,
                'verdict': 'met',
                'criteria': [
                    {'criterion': text, 'status': status, 'evidence': ev}
                    for text, status, ev in zip(criteria, statuses, evidence, strict=True)
                ],
            }
        ],
        'unrequested_changes': [],
        'self_reports': [],
        'files_read': ['src/parser.py'],
    }


def _sealed(plan_context: Any, tmp_path: Path, document: dict[str, Any]) -> str:
    path = tmp_path / 'verdict.json'
    path.write_text(json.dumps(document), encoding='utf-8')
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


def _commit(repo: Path, files: dict[str, str], committer_date: str | None = None) -> str:
    for relative, body in files.items():
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding='utf-8')
        _git(repo, 'add', relative)
    env = None
    if committer_date:
        env = {**os.environ, 'GIT_COMMITTER_DATE': committer_date, 'GIT_AUTHOR_DATE': committer_date}
    subprocess.run(
        ['git', '-C', str(repo), 'commit', '--quiet', '--message', 'commit'],
        capture_output=True,
        text=True,
        check=True,
        env=env,
    )
    return _git(repo, 'rev-parse', 'HEAD')


STRONG_TEST = 'def test_a():\n    assert 1 == 1\n    assert 2 == 2\n'
WEAK_TEST = 'def test_a():\n    assert 1 == 1\n'


# --- D2 (a): a branch deleting an assertion from an existing test yields a finding ---------


def test_branch_deleting_an_assertion_yields_a_finding(tmp_path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    _commit(repo, {'test/sample_test.py': STRONG_TEST})
    _git(repo, 'checkout', '--quiet', '-b', 'feature')
    _commit(repo, {'test/sample_test.py': WEAK_TEST})
    monkeypatch.setattr(_integrity, 'resolve_live_worktree', lambda _plan_id: repo)

    payload = _integrity.compute_test_integrity(PLAN_ID)

    assert [(row['path'], row['kind']) for row in payload['findings']] == [('test/sample_test.py', 'assertion_removed')]
    assert payload['finding_count'] == 1


def test_branch_adding_an_assertion_yields_no_finding(tmp_path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    _commit(repo, {'test/sample_test.py': WEAK_TEST})
    _git(repo, 'checkout', '--quiet', '-b', 'feature')
    _commit(repo, {'test/sample_test.py': STRONG_TEST})
    monkeypatch.setattr(_integrity, 'resolve_live_worktree', lambda _plan_id: repo)

    payload = _integrity.compute_test_integrity(PLAN_ID)

    assert payload['findings'] == []


def test_branch_filtering_a_test_yields_a_finding(tmp_path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    _commit(repo, {'test/sample_test.py': STRONG_TEST})
    _git(repo, 'checkout', '--quiet', '-b', 'feature')
    _commit(
        repo,
        {
            'test/sample_test.py': 'import pytest\n\n@pytest.mark.skip\ndef test_a():\n    assert 1 == 1\n    assert 2 == 2\n'
        },
    )
    monkeypatch.setattr(_integrity, 'resolve_live_worktree', lambda _plan_id: repo)

    payload = _integrity.compute_test_integrity(PLAN_ID)

    assert [row['kind'] for row in payload['findings']] == ['test_filtered']


# --- D2 (b): a pre-fix criterion evidenced only by a HEAD run is unevidenced ---------------


def test_pre_fix_criterion_evidenced_only_by_a_head_run_is_unevidenced(plan_context, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(_attr, 'resolve_live_worktree', lambda _plan_id: None)
    criteria = ['Regression test fails on the pre-fix tree']
    _plan(plan_context, criteria)
    document = _verdict(criteria, ['met'], [['module-tests green at HEAD 2248478b']])

    payload = review_support.run_validate(PLAN_ID, 'functional', _sealed(plan_context, tmp_path, document), None)

    assert payload['rewrites'] == [{'deliverable': 1, 'criterion': 1, 'from': 'met', 'to': 'unevidenced'}]
    assert [(f['kind'], f['severity']) for f in payload['findings']] == [('unevidenced_criterion', 'blocking')]


def test_pre_fix_criterion_evidenced_by_a_green_pre_fix_mention_is_unevidenced(
    plan_context, tmp_path, monkeypatch
) -> None:
    """Naming the pre-fix tree without naming a failure is not a pre-fix run."""
    monkeypatch.setattr(_attr, 'resolve_live_worktree', lambda _plan_id: None)
    criteria = ['Regression test fails on the pre-fix tree']
    _plan(plan_context, criteria)
    document = _verdict(criteria, ['met'], [['the whole suite passes on the pre-fix tree']])

    payload = review_support.run_validate(PLAN_ID, 'functional', _sealed(plan_context, tmp_path, document), None)

    assert payload['rewrites'] == [{'deliverable': 1, 'criterion': 1, 'from': 'met', 'to': 'unevidenced'}]


def test_pre_fix_criterion_evidenced_by_a_head_failure_is_unevidenced(plan_context, tmp_path, monkeypatch) -> None:
    """A failing run at HEAD names the wrong tree: the criterion is about the tree without the fix."""
    monkeypatch.setattr(_attr, 'resolve_live_worktree', lambda _plan_id: None)
    criteria = ['Regression test fails on the pre-fix tree']
    _plan(plan_context, criteria)
    document = _verdict(criteria, ['met'], [['test/sample_test.py::test_a fails at HEAD 2248478b']])

    payload = review_support.run_validate(PLAN_ID, 'functional', _sealed(plan_context, tmp_path, document), None)

    assert payload['rewrites'] == [{'deliverable': 1, 'criterion': 1, 'from': 'met', 'to': 'unevidenced'}]


def test_pre_fix_criterion_evidenced_by_a_pre_fix_run_is_met(plan_context, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(_attr, 'resolve_live_worktree', lambda _plan_id: None)
    criteria = ['Regression test fails on the pre-fix tree']
    _plan(plan_context, criteria)
    document = _verdict(criteria, ['met'], [['test/sample_test.py::test_a fails at 8442a5e33 (recorded log L)']])

    payload = review_support.run_validate(PLAN_ID, 'functional', _sealed(plan_context, tmp_path, document), None)

    assert payload['rewrites'] == []
    assert payload['findings'] == []
    assert payload['facts']['deliverables_met'] == 1


# --- D2 (c): a verdict citing a test name absent at the graded head is refused --------------


def test_verdict_citing_a_test_name_absent_at_the_graded_head_is_refused(plan_context, tmp_path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    monkeypatch.setattr(_attr, 'resolve_live_worktree', lambda _plan_id: repo)
    criteria = ['parser accepts input']
    _plan(plan_context, criteria, freeze=True)
    document = _verdict(criteria, ['met'], [['test/sample_test.py::test_nowhere']])

    payload = review_support.run_validate(PLAN_ID, 'functional', _sealed(plan_context, tmp_path, document), None)

    assert payload['valid'] is False
    assert any('does not exist at the graded head' in error for error in payload['errors'])


def test_verdict_citing_a_test_name_present_at_the_graded_head_is_accepted(plan_context, tmp_path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    _commit(repo, {'test/sample_test.py': 'def test_present():\n    assert 1 == 1\n'})
    monkeypatch.setattr(_attr, 'resolve_live_worktree', lambda _plan_id: repo)
    criteria = ['parser accepts input']
    _plan(plan_context, criteria, freeze=True)
    document = _verdict(criteria, ['met'], [['test/sample_test.py::test_present']])

    payload = review_support.run_validate(PLAN_ID, 'functional', _sealed(plan_context, tmp_path, document), None)

    assert payload['valid'] is True
    assert payload['errors'] == []


def test_verdict_citing_a_class_scoped_test_name_at_the_graded_head_is_accepted(
    plan_context, tmp_path, monkeypatch
) -> None:
    """The ``path::Class.method`` form resolves to the FILE, not to the whole citation."""
    repo = _repo(tmp_path)
    _commit(
        repo,
        {'test/sample_test.py': 'class TestSample:\n    def test_method(self):\n        assert 1 == 1\n'},
    )
    monkeypatch.setattr(_attr, 'resolve_live_worktree', lambda _plan_id: repo)
    criteria = ['parser accepts input']
    _plan(plan_context, criteria, freeze=True)
    document = _verdict(criteria, ['met'], [['test/sample_test.py::TestSample.test_method']])

    payload = review_support.run_validate(PLAN_ID, 'functional', _sealed(plan_context, tmp_path, document), None)

    assert payload['valid'] is True
    assert payload['errors'] == []


def test_evidence_citing_a_path_outside_the_graded_head_is_refused(plan_context, tmp_path, monkeypatch) -> None:
    """A verdict is author text: a ``..`` citation must not be read outside the graded tree."""
    repo = _repo(tmp_path)
    (tmp_path / 'outside.py').write_text('def test_outside():\n    assert 1 == 1\n', encoding='utf-8')
    _commit(repo, {'README.md': 'readme\n'})
    monkeypatch.setattr(_attr, 'resolve_live_worktree', lambda _plan_id: repo)
    criteria = ['parser accepts input']
    _plan(plan_context, criteria, freeze=True)
    document = _verdict(criteria, ['met'], [['../outside.py::test_outside']])

    payload = review_support.run_validate(PLAN_ID, 'functional', _sealed(plan_context, tmp_path, document), None)

    assert payload['valid'] is False
    assert any('does not exist at the graded head' in error for error in payload['errors'])


# --- D2 (d): a verify-first record timestamped after the gated commit is refused ------------


def test_verify_first_record_after_the_gated_commit_is_refused(plan_context, tmp_path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    sha = _commit(repo, {'src/migration.py': 'x\n'}, committer_date='2020-01-01T00:00:00+00:00')
    monkeypatch.setattr(_integrity, 'resolve_live_worktree', lambda _plan_id: repo)
    _plan(plan_context)
    assert _integrity.record_verify_first(PLAN_ID, 'nine-consumer gate', 'read local files only')['status'] == 'success'

    payload = _integrity.check_verify_first(PLAN_ID, 'nine-consumer gate', sha)

    assert (payload['status'], payload['error']) == ('error', 'verify_first_evidence_postdates_commit')
    assert len(payload['postdating']) == 1


def test_verify_first_record_before_the_gated_commit_passes(plan_context, tmp_path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    monkeypatch.setattr(_integrity, 'resolve_live_worktree', lambda _plan_id: repo)
    _plan(plan_context)
    assert (
        _integrity.record_verify_first(PLAN_ID, 'nine-consumer gate', 'checked all 9 consumers')['status'] == 'success'
    )
    future = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    sha = _commit(repo, {'src/migration.py': 'x\n'}, committer_date=future)

    payload = _integrity.check_verify_first(PLAN_ID, 'nine-consumer gate', sha)

    assert payload['status'] == 'success'
    assert payload['records'] == 1


# --- D2 (e): finalize with an empty bot queue and one unmet Done-when does not exit --------


def _finalize(plan_context: Any, tmp_path: Path, monkeypatch: Any, statuses: list[str]) -> dict[str, Any] | None:
    plan_dir = _plan(plan_context, freeze=True)
    verdict_file = plan_dir / 'work' / 'functional-review-verdict.json'
    verdict_file.parent.mkdir(parents=True, exist_ok=True)
    verdict_file.write_text(
        json.dumps(_verdict(CRITERIA, statuses, [['src/parser.py:1'], ['src/parser.py:2']])), encoding='utf-8'
    )
    monkeypatch.setattr(_lifecycle, 'assert_finalize_findings_clean', lambda *_args, **_kwargs: 0)
    monkeypatch.setattr(_lifecycle, 'log_entry', lambda *_args, **_kwargs: None)
    refusal: dict[str, Any] | None = _lifecycle._finalize_findings_refusal(
        PLAN_ID, {'title': 'fixture', 'metadata': {}}
    )
    return refusal


def test_finalize_with_an_empty_bot_queue_and_one_unmet_done_when_does_not_exit(
    plan_context, tmp_path, monkeypatch
) -> None:
    refusal = _finalize(plan_context, tmp_path, monkeypatch, ['met', 'unevidenced'])

    assert refusal is not None
    assert refusal['error'] == 'open_done_when_criteria'
    assert refusal['open_count'] == 1
    assert refusal['open_criteria'][0]['criterion'] == CRITERIA[1]


def test_finalize_with_every_done_when_met_proceeds(plan_context, tmp_path, monkeypatch) -> None:
    assert _finalize(plan_context, tmp_path, monkeypatch, ['met', 'met']) is None
