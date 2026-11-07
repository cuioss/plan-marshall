#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""PLAN-LB-118 D2 — an accepted removal is exactly what was accepted.

A count-less declaration decides a removal and never a drop of a surviving test.
The operator close records the rows from the head the finding was VALIDATED at,
keeps every row of a path, and accepts a row without an identity by its explicit
path-level key, so no row is unacceptable by construction.
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

PLAN_ID = 'lb118-accepted-removals-d2'

_lifecycle = load_script_module('plan-marshall', 'manage-status', '_cmd_lifecycle.py', '_lb118_d2_lifecycle')

BEFORE = 'def test_a():\n    assert 1 == 1\n    assert 2 == 2\n\ndef test_b():\n    assert 3 == 3\n'

LOSS_CASES_RULE = (
    'A loss is reported in exactly four cases: the set total drops, a named test disappears from every '
    "after-file, one test's count drops while that test still exists, or a surviving path's own total "
    'drops and no identity accounts for it.'
)
ACCEPTED_KEY_RULE = (
    'Both key the accepted set by what the entry NAMES: a test identity plus its removed count, a '
    "filter's marker set plus the identity of each marked test, or a path-level row kind (mixed "
    'residual / file total / set total) plus its count.'
)


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


def _blocking(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [f for f in payload.get('findings') or [] if f['kind'] == 'weakened_test' and f['severity'] == 'blocking']


def _prepare_close(plan_context: Any, criteria: list[str]) -> Path:
    plan_dir = _plan(plan_context, criteria, write_status=False)
    status = json.loads((plan_dir / 'status.json').read_text(encoding='utf-8'))
    status.setdefault('metadata', {})['use_worktree'] = False
    (plan_dir / 'status.json').write_text(json.dumps(status), encoding='utf-8')
    return plan_dir


def _mark_and_file(repo: Path, plan_context: Any, criteria: list[str], path: str) -> tuple[str, str]:
    """Create the plan, mark the step looped back at head A, and file the finding."""
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
    _prepare_close(plan_context, criteria)
    filed = _findings_core.add_qgate_finding(
        PLAN_ID,
        '6-finalize',
        'qgate',
        'bug',
        f'weakened_test at {path}',
        'a removed assertion [fix_kind correction]',
        rule='functional-review',
    )
    assert filed['status'] == 'success', filed
    return head_a, str(filed['hash_id'])


def _close(head: str, hash_id: str) -> dict[str, Any]:
    closed = _loop_back.cmd_loop_back_close(
        Namespace(
            plan_id=PLAN_ID,
            step=_loop_back.FUNCTIONAL_REVIEW_STEP,
            head=head,
            accept=[hash_id],
            rationale='the test removal is the deliverable',
            waive_refire=[],
        )
    )
    assert closed is not None and closed['status'] == 'success', closed
    return closed


# --- D2 (a): a count-less declaration decides a removal, not a drop ------------------------


def test_a_count_less_declaration_does_not_accept_a_drop_of_a_surviving_test(
    plan_context, tmp_path, monkeypatch
) -> None:
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    _commit(repo, {'test/surviving_test.py': BEFORE})
    _git(repo, 'checkout', '--quiet', '-b', 'feature')
    _commit(repo, {'test/surviving_test.py': 'def test_a():\n    assert 1 == 1\n\ndef test_b():\n    assert 3 == 3\n'})
    monkeypatch.setattr(_integrity, 'resolve_live_worktree', lambda _plan_id: repo)
    monkeypatch.setattr(_attr, 'resolve_live_worktree', lambda _plan_id: None)
    criteria = ['parser accepts input']
    _plan(plan_context, criteria, removals=['test_a'])
    assert _snap.write_snapshot(PLAN_ID)['status'] == 'success'

    payload = review_support.run_validate(PLAN_ID, 'functional', _sealed(tmp_path, criteria), None)

    assert _blocking(payload), payload['findings']


def test_a_count_less_declaration_accepts_a_wholly_removed_test(plan_context, tmp_path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    _commit(repo, {'test/removed_test.py': 'def test_a():\n    assert 1 == 1\n    assert 2 == 2\n'})
    _git(repo, 'checkout', '--quiet', '-b', 'feature')
    _git(repo, 'rm', 'test/removed_test.py')
    _git(repo, 'commit', '--quiet', '-m', 'remove')
    monkeypatch.setattr(_integrity, 'resolve_live_worktree', lambda _plan_id: repo)
    monkeypatch.setattr(_attr, 'resolve_live_worktree', lambda _plan_id: None)
    criteria = ['parser accepts input']
    _plan(plan_context, criteria, removals=['test_a'])
    assert _snap.write_snapshot(PLAN_ID)['status'] == 'success'

    payload = review_support.run_validate(PLAN_ID, 'functional', _sealed(tmp_path, criteria), None)

    assert _blocking(payload) == [], payload['findings']


def test_a_declaration_naming_two_does_not_accept_a_three_assertion_removal(
    plan_context, tmp_path, monkeypatch
) -> None:
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    _commit(repo, {'test/removed_test.py': 'def test_a():\n    assert 1 == 1\n    assert 2 == 2\n    assert 3 == 3\n'})
    _git(repo, 'checkout', '--quiet', '-b', 'feature')
    _git(repo, 'rm', 'test/removed_test.py')
    _git(repo, 'commit', '--quiet', '-m', 'remove')
    monkeypatch.setattr(_integrity, 'resolve_live_worktree', lambda _plan_id: repo)
    monkeypatch.setattr(_attr, 'resolve_live_worktree', lambda _plan_id: None)
    criteria = ['parser accepts input']
    _plan(plan_context, criteria, removals=['test_a: 2'])
    assert _snap.write_snapshot(PLAN_ID)['status'] == 'success'

    payload = review_support.run_validate(PLAN_ID, 'functional', _sealed(tmp_path, criteria), None)

    assert _blocking(payload), payload['findings']


# --- D2 (b): the close reads the validated head, never a later one -------------------------


def test_a_close_at_a_later_head_is_refused_and_the_later_removal_is_not_recorded(
    plan_context, tmp_path, monkeypatch
) -> None:
    """A close whose head differs from the validated one is refused with a named state.

    The review validated head A; the operator tries to close at head B, where test_b
    has since disappeared. Recording rows from A silently would let the close stand
    done at B while B was never graded, so the removal at B would ship unseen. The
    close is refused instead, and the next validation still raises test_b.
    """
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    _commit(repo, {'test/sample_test.py': BEFORE})
    _git(repo, 'checkout', '--quiet', '-b', 'feature')
    # head A: test_a loses one assertion — the finding the operator sees.
    _commit(repo, {'test/sample_test.py': 'def test_a():\n    assert 1 == 1\n\ndef test_b():\n    assert 3 == 3\n'})
    monkeypatch.chdir(repo)
    monkeypatch.setattr(_integrity, 'resolve_live_worktree', lambda _plan_id: repo)
    monkeypatch.setattr(_attr, 'resolve_live_worktree', lambda _plan_id: None)
    criteria = ['parser accepts input']
    head_a, hash_id = _mark_and_file(repo, plan_context, criteria, 'test/sample_test.py')
    # head B: test_b disappears entirely, after the review validated head A.
    _commit(repo, {'test/sample_test.py': 'def test_a():\n    assert 1 == 1\n'}, 'remove test_b later')
    head_b = _git(repo, 'rev-parse', 'HEAD')
    assert head_a != head_b

    closed = _loop_back.cmd_loop_back_close(
        Namespace(
            plan_id=PLAN_ID,
            step=_loop_back.FUNCTIONAL_REVIEW_STEP,
            head=head_b,
            accept=[hash_id],
            rationale='the test removal is the deliverable',
            waive_refire=[],
        )
    )

    assert closed is not None and closed['status'] == 'error', closed
    assert closed['error'] == 'close_head_not_validated', closed

    payload = review_support.run_validate(PLAN_ID, 'functional', _sealed(tmp_path, criteria), None)
    identities = {entry.get('identity') for entry in payload['accepted_removals']}
    assert 'test_b' not in identities, payload['accepted_removals']
    assert _blocking(payload), payload['findings']


# --- D2 (c): every row of a path is kept, not the last -------------------------------------


def test_a_file_with_an_assertion_loss_and_a_skip_marker_records_both(plan_context, tmp_path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    _commit(repo, {'test/sample_test.py': 'def test_a():\n    assert 1 == 1\n    assert 2 == 2\n'})
    _git(repo, 'checkout', '--quiet', '-b', 'feature')
    # One path, two rows: an assertion loss and an added skip marker.
    _commit(repo, {'test/sample_test.py': 'import pytest\n\n@pytest.mark.skip\ndef test_a():\n    assert 1 == 1\n'})
    monkeypatch.chdir(repo)
    monkeypatch.setattr(_integrity, 'resolve_live_worktree', lambda _plan_id: repo)
    monkeypatch.setattr(_attr, 'resolve_live_worktree', lambda _plan_id: None)
    criteria = ['parser accepts input']
    head_a, hash_id = _mark_and_file(repo, plan_context, criteria, 'test/sample_test.py')

    _close(head_a, hash_id)
    # A later fix commit, the same removed set.
    _commit(repo, {'src/other.py': 'x\n'})

    payload = review_support.run_validate(PLAN_ID, 'functional', _sealed(tmp_path, criteria), None)

    assert _blocking(payload) == [], payload['findings']
    assert any(entry.get('identity') == 'test_a' for entry in payload['accepted_removals']), payload[
        'accepted_removals'
    ]


# --- D2 (d): a row without an identity is accepted by path plus count ---------------------


def test_an_identity_less_file_total_row_is_accepted_by_path(plan_context, tmp_path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    _commit(repo, {'src/thing.test.js': 'expect(1).toBe(1);\n'})
    _git(repo, 'checkout', '--quiet', '-b', 'feature')
    _git(repo, 'rm', 'src/thing.test.js')
    _git(repo, 'commit', '--quiet', '-m', 'remove the file')
    monkeypatch.chdir(repo)
    monkeypatch.setattr(_integrity, 'resolve_live_worktree', lambda _plan_id: repo)
    monkeypatch.setattr(_attr, 'resolve_live_worktree', lambda _plan_id: None)
    criteria = ['parser accepts input']
    head_a, hash_id = _mark_and_file(repo, plan_context, criteria, 'src/thing.test.js')

    _close(head_a, hash_id)
    _commit(repo, {'src/other.py': 'x\n'})

    payload = review_support.run_validate(PLAN_ID, 'functional', _sealed(tmp_path, criteria), None)

    assert _blocking(payload) == [], payload['findings']
    assert any(entry.get('path') == 'src/thing.test.js' for entry in payload['accepted_removals']), payload[
        'accepted_removals'
    ]


def test_a_test_filtered_row_is_accepted_by_path(plan_context, tmp_path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    _commit(repo, {'src/thing.test.js': "it('works', () => {\n  expect(1).toBe(1);\n});\n"})
    _git(repo, 'checkout', '--quiet', '-b', 'feature')
    _commit(repo, {'src/thing.test.js': "it.skip('works', () => {\n  expect(1).toBe(1);\n});\n"})
    monkeypatch.chdir(repo)
    monkeypatch.setattr(_integrity, 'resolve_live_worktree', lambda _plan_id: repo)
    monkeypatch.setattr(_attr, 'resolve_live_worktree', lambda _plan_id: None)
    criteria = ['parser accepts input']
    head_a, hash_id = _mark_and_file(repo, plan_context, criteria, 'src/thing.test.js')

    _close(head_a, hash_id)
    _commit(repo, {'src/other.py': 'x\n'})

    payload = review_support.run_validate(PLAN_ID, 'functional', _sealed(tmp_path, criteria), None)

    assert _blocking(payload) == [], payload['findings']
    assert any(
        entry.get('path') == 'src/thing.test.js' and entry.get('kind') == 'test_filtered'
        for entry in payload['accepted_removals']
    ), payload['accepted_removals']


def test_a_set_total_row_is_accepted_by_path(plan_context, tmp_path, monkeypatch) -> None:
    """A set-total row carries no identity; a close accepts it by path plus count."""
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    _commit(
        repo,
        {'test/outer_test.py': 'module_check = True\nassert module_check\n\ndef test_a():\n    assert 1 == 1\n'},
    )
    _git(repo, 'checkout', '--quiet', '-b', 'feature')
    _git(repo, 'rm', 'test/outer_test.py')
    _git(repo, 'commit', '--quiet', '-m', 'remove the file')
    monkeypatch.chdir(repo)
    monkeypatch.setattr(_integrity, 'resolve_live_worktree', lambda _plan_id: repo)
    monkeypatch.setattr(_attr, 'resolve_live_worktree', lambda _plan_id: None)
    criteria = ['parser accepts input']
    head_a, hash_id = _mark_and_file(repo, plan_context, criteria, 'test/outer_test.py')

    _close(head_a, hash_id)
    _commit(repo, {'src/other.py': 'x\n'})

    payload = review_support.run_validate(PLAN_ID, 'functional', _sealed(tmp_path, criteria), None)

    assert _blocking(payload) == [], payload['findings']
    assert any(entry.get('identity') == 'test_a' for entry in payload['accepted_removals']), payload[
        'accepted_removals'
    ]
    assert any(entry.get('path') == 'test/outer_test.py' for entry in payload['accepted_removals']), payload[
        'accepted_removals'
    ]


def test_a_second_skip_marker_on_the_same_path_is_raised_again(plan_context, tmp_path, monkeypatch) -> None:
    """The accepted filter row names its markers; a new marker kind is raised again."""
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    before = (
        "describe('suite', () => {\n"
        "  it('a', () => {\n"
        '    expect(1).toBe(1);\n'
        '  });\n\n'
        "  it('b', () => {\n"
        '    expect(2).toBe(2);\n'
        '  });\n'
        '});\n'
    )
    _commit(repo, {'src/thing.test.js': before})
    _git(repo, 'checkout', '--quiet', '-b', 'feature')
    head_a_text = before.replace("  it('a'", "  it.skip('a'")
    _commit(repo, {'src/thing.test.js': head_a_text})
    monkeypatch.chdir(repo)
    monkeypatch.setattr(_integrity, 'resolve_live_worktree', lambda _plan_id: repo)
    monkeypatch.setattr(_attr, 'resolve_live_worktree', lambda _plan_id: None)
    criteria = ['parser accepts input']
    head_a, hash_id = _mark_and_file(repo, plan_context, criteria, 'src/thing.test.js')

    _close(head_a, hash_id)
    # A new marker KIND on the same path, after the accepted filter row.
    _commit(repo, {'src/thing.test.js': head_a_text.replace("describe('suite'", "describe.skip('suite'")})

    payload = review_support.run_validate(PLAN_ID, 'functional', _sealed(tmp_path, criteria), None)

    assert _blocking(payload), payload['findings']


def test_a_mixed_residual_row_is_accepted_by_path(plan_context, tmp_path, monkeypatch) -> None:
    """A row whose residual no identity explains needs its own path-level acceptance."""
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    _commit(
        repo,
        {'test/residual_test.py': 'assert preamble\ndef test_a():\n    assert 1 == 1\n    assert 2 == 2\n'},
    )
    _git(repo, 'checkout', '--quiet', '-b', 'feature')
    _commit(repo, {'test/residual_test.py': 'def test_a():\n    assert 1 == 1\n'})
    monkeypatch.chdir(repo)
    monkeypatch.setattr(_integrity, 'resolve_live_worktree', lambda _plan_id: repo)
    monkeypatch.setattr(_attr, 'resolve_live_worktree', lambda _plan_id: None)
    criteria = ['parser accepts input']
    head_a, hash_id = _mark_and_file(repo, plan_context, criteria, 'test/residual_test.py')

    _close(head_a, hash_id)
    _commit(repo, {'src/other.py': 'x\n'})

    payload = review_support.run_validate(PLAN_ID, 'functional', _sealed(tmp_path, criteria), None)

    assert _blocking(payload) == [], payload['findings']


def test_a_grown_residual_is_raised_again(plan_context, tmp_path, monkeypatch) -> None:
    """The residual is accepted by its count, so a larger residual is raised again."""
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    _commit(
        repo,
        {'test/residual_test.py': ('assert p1\nassert p2\ndef test_a():\n    assert 1 == 1\n    assert 2 == 2\n')},
    )
    _git(repo, 'checkout', '--quiet', '-b', 'feature')
    # head A: one preamble assertion and one test assertion removed (residual 1).
    _commit(repo, {'test/residual_test.py': 'assert p2\ndef test_a():\n    assert 1 == 1\n'})
    monkeypatch.chdir(repo)
    monkeypatch.setattr(_integrity, 'resolve_live_worktree', lambda _plan_id: repo)
    monkeypatch.setattr(_attr, 'resolve_live_worktree', lambda _plan_id: None)
    criteria = ['parser accepts input']
    head_a, hash_id = _mark_and_file(repo, plan_context, criteria, 'test/residual_test.py')

    _close(head_a, hash_id)
    # head B: the other preamble assertion goes too (residual grows to 2).
    _commit(repo, {'test/residual_test.py': 'def test_a():\n    assert 1 == 1\n'})

    payload = review_support.run_validate(PLAN_ID, 'functional', _sealed(tmp_path, criteria), None)

    assert _blocking(payload), payload['findings']


# --- D2 (e): the three texts state the cases and the key identically -----------------------


def test_the_three_texts_state_the_loss_cases_and_the_key_identically() -> None:
    finalize = get_skill_dir('plan-marshall', 'phase-6-finalize')
    texts = {
        'functional-review.md § 3e': (finalize / 'workflow' / 'functional-review.md').read_text(encoding='utf-8'),
        'review-rubric.md': (finalize / 'standards' / 'review-rubric.md').read_text(encoding='utf-8'),
        '_review_support_integrity.py': (finalize / 'scripts' / '_review_support_integrity.py').read_text(
            encoding='utf-8'
        ),
    }
    for label, text in texts.items():
        assert LOSS_CASES_RULE in text, label
        assert ACCEPTED_KEY_RULE in text, label


# =============================================================================
# D3 — an acceptance covers exactly what was accepted
# =============================================================================


def test_accepting_one_skip_then_skipping_another_raises_a_row(plan_context, tmp_path, monkeypatch) -> None:
    """The accepted filter row names the MARKED TEST, so a later skip is a new row.

    The first close accepts ``it.skip('a')`` only. Adding ``it.skip('b')`` to the same
    file leaves the marker KIND set unchanged, so a kind-only key accepts it silently.
    The row must name the identity of each marked test. Red at 75b5780d0.
    """
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    before = "it('a', () => {\n  expect(1).toBe(1);\n});\n\nit('b', () => {\n  expect(2).toBe(2);\n});\n"
    _commit(repo, {'src/thing.test.js': before})
    _git(repo, 'checkout', '--quiet', '-b', 'feature')
    head_a_text = before.replace("it('a'", "it.skip('a'")
    _commit(repo, {'src/thing.test.js': head_a_text})
    monkeypatch.chdir(repo)
    monkeypatch.setattr(_integrity, 'resolve_live_worktree', lambda _plan_id: repo)
    monkeypatch.setattr(_attr, 'resolve_live_worktree', lambda _plan_id: None)
    criteria = ['parser accepts input']
    head_a, hash_id = _mark_and_file(repo, plan_context, criteria, 'src/thing.test.js')

    _close(head_a, hash_id)
    _commit(repo, {'src/thing.test.js': head_a_text.replace("it('b'", "it.skip('b'")})

    payload = review_support.run_validate(PLAN_ID, 'functional', _sealed(tmp_path, criteria), None)

    assert _blocking(payload), payload['findings']


def _mark_loop_back_and_file(head: str, path: str, marker: str = '') -> str:
    """Mark the review looped back at ``head`` and file a fresh pending finding for ``path``."""
    marked = _loop_back.cmd_mark_step_done(
        Namespace(
            plan_id=PLAN_ID,
            phase='6-finalize',
            step=_loop_back.FUNCTIONAL_REVIEW_STEP,
            outcome='loop_back',
            display_detail='functional review found 1 blocking, 0 advisory',
            head_at_completion=head,
            loop_back_target='6-finalize',
            fact=None,
            force=False,
            no_completion_log=False,
        )
    )
    assert marked is not None and marked['status'] == 'success', marked
    filed = _findings_core.add_qgate_finding(
        PLAN_ID,
        '6-finalize',
        'qgate',
        'bug',
        f'weakened_test at {path}',
        f'a removed assertion [fix_kind correction] {marker}'.strip(),
        rule='functional-review',
    )
    assert filed['status'] in ('success', 'reopened'), filed
    return str(filed['hash_id'])


def test_a_second_filter_close_with_a_different_marker_set_is_recorded(plan_context, tmp_path, monkeypatch) -> None:
    """A second close whose marker set differs is APPENDED, so the row stays accepted.

    The accepted-set key omits ``markers``/``marked_tests`` pre-fix, so the second
    close collides with the first and the newer marker kind is never accepted. Red at
    75b5780d0.
    """
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    before = (
        "describe('suite', () => {\n"
        "  it('a', () => {\n"
        '    expect(1).toBe(1);\n'
        '  });\n\n'
        "  it('b', () => {\n"
        '    expect(2).toBe(2);\n'
        '  });\n'
        '});\n'
    )
    _commit(repo, {'src/thing.test.js': before})
    _git(repo, 'checkout', '--quiet', '-b', 'feature')
    head_a_text = before.replace("  it('a'", "  it.skip('a'")
    _commit(repo, {'src/thing.test.js': head_a_text})
    monkeypatch.chdir(repo)
    monkeypatch.setattr(_integrity, 'resolve_live_worktree', lambda _plan_id: repo)
    monkeypatch.setattr(_attr, 'resolve_live_worktree', lambda _plan_id: None)
    criteria = ['parser accepts input']
    head_a, hash_id = _mark_and_file(repo, plan_context, criteria, 'src/thing.test.js')
    _close(head_a, hash_id)

    head_b_text = head_a_text.replace("describe('suite'", "describe.skip('suite'")
    head_b = _commit(repo, {'src/thing.test.js': head_b_text}, 'skip the suite too')
    second_hash = _mark_loop_back_and_file(head_b, 'src/thing.test.js', 'second round')
    _close(head_b, second_hash)

    recorded = _snap.accepted_test_removals(PLAN_ID)
    filter_entries = [
        entry for entry in recorded if entry.get('path') == 'src/thing.test.js' and entry.get('kind') == 'test_filtered'
    ]
    assert len(filter_entries) == 2, recorded
    assert any('describe.skip' in (entry.get('markers') or []) for entry in filter_entries), recorded

    _commit(repo, {'src/other.py': 'x\n'})
    payload = review_support.run_validate(PLAN_ID, 'functional', _sealed(tmp_path, criteria), None)

    assert payload['status'] == 'success', payload
    assert _blocking(payload) == [], payload['findings']


def test_reseeding_the_same_entry_neither_duplicates_nor_drops_it(plan_context) -> None:
    """Control: the union key is stable across a re-seed."""
    _plan(plan_context)
    entry = {
        'path': 'src/a.test.js',
        'kind': 'test_filtered',
        'markers': ['it.skip'],
        'marked_tests': ['a'],
    }
    assert _snap.record_accepted_removals(PLAN_ID, [entry]) is True
    assert _snap.record_accepted_removals(PLAN_ID, [entry]) is True

    recorded = _snap.accepted_test_removals(PLAN_ID)
    assert len([e for e in recorded if e.get('path') == 'src/a.test.js']) == 1, recorded


def test_an_entry_that_normalizes_to_nothing_is_not_reported_success(plan_context) -> None:
    """The writer reports success only when the entry appended or was already present."""
    _plan(plan_context)

    assert _snap.record_accepted_removals(PLAN_ID, [{'identity': '', 'path': ''}]) is False


# --- D2 (h): a path-level acceptance is typed by row kind ---------------------------------


def test_a_mixed_residual_entry_does_not_accept_a_file_total_row_of_the_same_count(
    plan_context, tmp_path, monkeypatch
) -> None:
    """A mixed-residual acceptance covers the residual, not a file-total row of that count.

    Head A leaves one identity drop plus a one-assertion residual (mixed row); the
    close accepts both. Head B leaves the identity intact and only a module-level
    assertion gone: a one-assertion FILE-TOTAL row. The residual entry must not cover
    it. Red at 75b5780d0.
    """
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    _commit(
        repo,
        {'test/residual_test.py': 'assert m1\nassert m2\ndef test_a():\n    assert 1 == 1\n    assert 2 == 2\n'},
    )
    _git(repo, 'checkout', '--quiet', '-b', 'feature')
    _commit(repo, {'test/residual_test.py': 'assert m1\ndef test_a():\n    assert 1 == 1\n'})
    monkeypatch.chdir(repo)
    monkeypatch.setattr(_integrity, 'resolve_live_worktree', lambda _plan_id: repo)
    monkeypatch.setattr(_attr, 'resolve_live_worktree', lambda _plan_id: None)
    criteria = ['parser accepts input']
    head_a, hash_id = _mark_and_file(repo, plan_context, criteria, 'test/residual_test.py')

    _close(head_a, hash_id)
    _commit(repo, {'test/residual_test.py': 'assert m1\ndef test_a():\n    assert 1 == 1\n    assert 2 == 2\n'})

    payload = review_support.run_validate(PLAN_ID, 'functional', _sealed(tmp_path, criteria), None)

    assert _blocking(payload), payload['findings']


# --- D4: the Branch B escape is pinned -----------------------------------------------------


def test_the_branch_b_escape_sentence_is_pinned() -> None:
    """The pre-marker ``taken_into_account`` escape is stated in Branch B, not only in manage-findings."""
    finalize = get_skill_dir('plan-marshall', 'phase-6-finalize')
    text = (finalize / 'workflow' / 'functional-review.md').read_text(encoding='utf-8')
    branch_b = text.split('### Branch B', 1)[1].split('### Branch C', 1)[0]

    assert '--resolution pending' in branch_b
    assert 'pre-marker' in branch_b or 'Pre-marker' in branch_b
