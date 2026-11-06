#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""PLAN-LB-118 D1 — a loss is decided per identity and every row can be decided.

The survival test compares an identity against what the SAME identity carried
before OUTSIDE the deleted or modified path, so a same-named test in another
changed file cannot absorb a loss, and a function moved out of a surviving file is
not a loss. The class scope is not closed by a column-0 comment or a dedented
string, a nested class keeps its full path, and an indented JS skip marker belongs
to its own test.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

import _review_support_integrity as _integrity

PLAN_ID = 'lb118-test-integrity-d1'


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
    import json

    plan_dir = Path(plan_context.plan_dir_for(PLAN_ID))
    (plan_dir / 'references.json').write_text(json.dumps({'base_branch': 'main'}), encoding='utf-8')
    (plan_dir / 'status.json').write_text(
        json.dumps({'title': 'fixture', 'phases': [], 'current_phase': '6-finalize', 'metadata': {}}),
        encoding='utf-8',
    )
    return plan_dir


def _rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [row for row in payload.get('findings') or [] if row.get('kind') == 'assertion_removed']


def _run(repo: Path, plan_context: Any, monkeypatch) -> dict[str, Any]:
    monkeypatch.setattr(_integrity, 'resolve_live_worktree', lambda _plan_id: repo)
    _plan(plan_context)
    return _integrity.compute_test_integrity(PLAN_ID)


# --- D1 (a): a pooled identity in another changed file absorbs nothing ----------------------


def test_deleted_test_pooled_from_another_changed_file_is_still_a_loss(plan_context, tmp_path, monkeypatch) -> None:
    """``test_x`` in a modified file must not absorb ``test_x`` deleted elsewhere."""
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    _commit(
        repo,
        {
            'test/deleted_test.py': 'def test_x():\n    assert 1 == 1\n    assert 2 == 2\n',
            'test/other_test.py': 'def test_x():\n    assert 1 == 1\n    assert 2 == 2\n    assert 3 == 3\n',
        },
    )
    _git(repo, 'checkout', '--quiet', '-b', 'feature')
    _git(repo, 'rm', 'test/deleted_test.py')
    _commit(
        repo,
        {
            # The surviving same-named test gains assertions: the set total barely moves.
            'test/other_test.py': (
                'def test_x():\n    assert 1 == 1\n    assert 2 == 2\n    assert 3 == 3\n    assert 4 == 4\n'
            )
        },
        'remove one',
    )

    payload = _run(repo, plan_context, monkeypatch)

    rows = _rows(payload)
    assert any(row['path'] == 'test/deleted_test.py' for row in rows), payload
    row = next(row for row in rows if row['path'] == 'test/deleted_test.py')
    assert any(entry['identity'] == 'test_x' for entry in row['removed_tests']), row


# --- D1 (b): a function moved out of a surviving file is not a loss ------------------------


def test_a_function_moved_from_a_surviving_file_yields_no_row(plan_context, tmp_path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    _commit(
        repo,
        {
            'test/source_test.py': 'def test_a():\n    assert 1 == 1\n    assert 2 == 2\n\ndef test_b():\n    assert 3 == 3\n'
        },
    )
    _git(repo, 'checkout', '--quiet', '-b', 'feature')
    _commit(
        repo,
        {
            'test/source_test.py': 'def test_b():\n    assert 3 == 3\n',
            'test/moved_test.py': 'def test_a():\n    assert 1 == 1\n    assert 2 == 2\n',
        },
        'move one function',
    )

    payload = _run(repo, plan_context, monkeypatch)

    assert _rows(payload) == [], payload


# --- D1 (c): the class scope survives a column-0 comment -----------------------------------


def test_a_column_zero_comment_in_a_class_body_keeps_the_method_identities(plan_context, tmp_path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    _commit(
        repo,
        {
            'test/class_test.py': (
                'class TestThing:\n'
                '    def test_one(self):\n'
                '        assert 1 == 1\n\n'
                '    def test_two(self):\n'
                '        assert 2 == 2\n'
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
                '# a comment the branch adds at column zero\n\n'
                '    def test_two(self):\n'
                '        assert 2 == 2\n'
            )
        },
        'add a comment',
    )

    payload = _run(repo, plan_context, monkeypatch)

    assert _rows(payload) == [], payload


# --- D1 (d): nested classes keep their full path -------------------------------------------


def test_nested_classes_of_the_same_name_do_not_collide(plan_context, tmp_path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    _commit(
        repo,
        {
            'test/nested_test.py': (
                'class A:\n'
                '    class Inner:\n'
                '        def m(self):\n'
                '            assert 1 == 1\n\n'
                'class B:\n'
                '    class Inner:\n'
                '        def m(self):\n'
                '            assert 2 == 2\n'
            )
        },
    )
    _git(repo, 'checkout', '--quiet', '-b', 'feature')
    _commit(
        repo,
        {
            'test/nested_test.py': (
                'class A:\n'
                '    class Inner:\n'
                '        def m(self):\n'
                '            assert 1 == 1\n\n'
                'class B:\n'
                '    class Inner:\n'
                '        def m(self):\n'
                '            pass\n'
            )
        },
        'drop one nested assertion',
    )

    payload = _run(repo, plan_context, monkeypatch)

    rows = _rows(payload)
    assert rows, payload
    identities = {entry['identity'] for row in rows for entry in row['removed_tests']}
    assert identities == {'B.Inner::m'}, identities


# --- D1 (e): an indented JS skip marker belongs to its own test ----------------------------

_BEFORE_JS = (
    "describe('suite', () => {\n"
    "  it.skip('already skipped', () => {\n"
    '    expect(1).toBe(1);\n'
    '  });\n\n'
    "  it('target', () => {\n"
    '    expect(2).toBe(2);\n'
    '  });\n'
    '});\n'
)
_AFTER_JS = _BEFORE_JS.replace("it('target'", "it.skip('target'")


def test_an_indented_js_skip_marker_is_attributed_to_its_own_test(plan_context, tmp_path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    _commit(repo, {'src/thing.test.js': _BEFORE_JS})
    _git(repo, 'checkout', '--quiet', '-b', 'feature')
    _commit(repo, {'src/thing.test.js': _AFTER_JS}, 'skip one more')

    payload = _run(repo, plan_context, monkeypatch)

    assert [(row['kind'], row['path']) for row in payload['findings']] == [('test_filtered', 'src/thing.test.js')], (
        payload
    )


def test_class_body_survives_a_dedented_string(plan_context, tmp_path, monkeypatch) -> None:
    """A triple-quoted body whose lines start at column 0 does not close the class."""
    before = 'class TestThing:\n    def test_one(self):\n        assert 1 == 1\n        assert 2 == 2\n'
    after = (
        'class TestThing:\n'
        '    text = """\n'
        'a line that starts at column zero\n'
        '"""\n\n'
        '    def test_one(self):\n'
        '        assert 1 == 1\n'
        '        assert 2 == 2\n'
    )
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    _commit(repo, {'test/string_test.py': before})
    _git(repo, 'checkout', '--quiet', '-b', 'feature')
    _commit(repo, {'test/string_test.py': after}, 'add a dedented string')

    payload = _run(repo, plan_context, monkeypatch)

    assert _rows(payload) == [], payload


# --- D2 (f): a bare name in another file does not prove a move -----------------------------


def test_a_bare_name_in_a_new_file_does_not_absorb_a_modified_files_loss(plan_context, tmp_path, monkeypatch) -> None:
    """An unrelated same-named test in a NEW file cannot absorb a modified file's loss.

    Pre-fix, the survival comparison read a bare name in the after-set as a move: the
    deleted ``test_parse`` had ``carried = 0`` and ``surviving = 2`` from a new file
    whose ``test_parse`` asserts ``True`` twice, so no row was raised. A move is now
    proven only when the deleted identity's assertion CONTENT reappears elsewhere.
    """
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    _commit(
        repo,
        {'test/mod_test.py': 'def test_parse():\n    assert 1 == 1\n    assert 2 == 2\n'},
    )
    _git(repo, 'checkout', '--quiet', '-b', 'feature')
    _commit(
        repo,
        {
            'test/mod_test.py': 'def test_other():\n    assert 3 == 3\n',
            'test/new_test.py': 'def test_parse():\n    assert True\n    assert True\n',
        },
        'remove one test, add an unrelated same-named one',
    )

    payload = _run(repo, plan_context, monkeypatch)

    rows = _rows(payload)
    assert any(row['path'] == 'test/mod_test.py' for row in rows), payload
    row = next(row for row in rows if row['path'] == 'test/mod_test.py')
    assert any(entry['identity'] == 'test_parse' for entry in row['removed_tests']), row


def test_a_function_moved_with_its_assertions_still_yields_no_row(plan_context, tmp_path, monkeypatch) -> None:
    """Control: content-identical move across files is not a loss."""
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    _commit(
        repo,
        {
            'test/source_test.py': 'def test_a():\n    assert 1 == 1\n    assert 2 == 2\n\ndef test_b():\n    assert 3 == 3\n'
        },
    )
    _git(repo, 'checkout', '--quiet', '-b', 'feature')
    _commit(
        repo,
        {
            'test/source_test.py': 'def test_b():\n    assert 3 == 3\n',
            'test/moved_test.py': 'def test_a():\n    assert 1 == 1\n    assert 2 == 2\n',
        },
        'move one function',
    )

    payload = _run(repo, plan_context, monkeypatch)

    assert _rows(payload) == [], payload


# --- D2 (g): the set-total row is attributed to the unexplained loss ------------------------


def test_the_set_total_row_goes_to_the_file_whose_loss_no_identity_explains(
    plan_context, tmp_path, monkeypatch
) -> None:
    """File Q has a small UNEXPLAINED loss; file P has a larger explained drop.

    Both files are deleted. P's test identity explains its whole drop; Q's identity
    row is reported and its module-level assertion is not, so the leftover set-total
    loss belongs to Q. Pre-fix the row went to ``max(positive)`` of the RAW drop — P.
    """
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    _commit(
        repo,
        {
            'test/p_test.py': (
                'def test_p():\n'
                '    assert 1 == 1\n'
                '    assert 2 == 2\n'
                '    assert 3 == 3\n'
                '    assert 4 == 4\n'
                '    assert 5 == 5\n'
            ),
            'test/q_test.py': 'assert module_check\ndef test_q():\n    assert 1 == 1\n    assert 2 == 2\n',
        },
    )
    _git(repo, 'checkout', '--quiet', '-b', 'feature')
    _git(repo, 'rm', 'test/p_test.py', 'test/q_test.py')
    _git(repo, 'commit', '--quiet', '-m', 'remove both')

    payload = _run(repo, plan_context, monkeypatch)

    set_total = [row for row in _rows(payload) if 'changed test set holds' in row['detail']]
    assert set_total, payload
    assert set_total[0]['path'] == 'test/q_test.py', payload
