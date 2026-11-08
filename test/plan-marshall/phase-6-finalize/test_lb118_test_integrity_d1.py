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

    assert payload['status'] == 'success', payload
    assert _rows(payload) == [], payload


def test_an_unchanged_moved_file_with_repeated_identities_yields_no_row(plan_context, tmp_path, monkeypatch) -> None:
    """A whole-file move is not a loss, even when the file repeats a test identity."""
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    _commit(repo, {'test/dup_test.py': 'def test_x():\n    assert 1 == 1\n\ndef test_x():\n    assert 2 == 2\n'})
    _git(repo, 'checkout', '--quiet', '-b', 'feature')
    _git(repo, 'mv', 'test/dup_test.py', 'test/dup_moved_test.py')
    _git(repo, 'commit', '--quiet', '-m', 'move the whole file')

    payload = _run(repo, plan_context, monkeypatch)

    assert payload['status'] == 'success', payload
    assert _rows(payload) == [], payload


def test_a_repeated_identity_in_a_deleted_file_is_not_fully_credited_to_one_move(
    plan_context, tmp_path, monkeypatch
) -> None:
    """Two same-named tests in one file: moving the last must not credit the summed count.

    The identity's count is the SUM of both bodies, and a single moved body cannot
    prove that sum. The repeated identity therefore survives nothing and the whole
    loss is reported.
    """
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    _commit(
        repo,
        {
            'test/dup_test.py': 'def test_x():\n    assert 1 == 1\n    assert 2 == 2\n\ndef test_x():\n    assert 3 == 3\n'
        },
    )
    _git(repo, 'checkout', '--quiet', '-b', 'feature')
    _git(repo, 'rm', 'test/dup_test.py')
    _commit(repo, {'test/moved_test.py': 'def test_x():\n    assert 3 == 3\n'}, 'move only the last one')

    payload = _run(repo, plan_context, monkeypatch)

    assert payload['status'] == 'success', payload
    rows = _rows(payload)
    assert any(row['path'] == 'test/dup_test.py' for row in rows), payload
    row = next(row for row in rows if row['path'] == 'test/dup_test.py')
    assert row['removed_assertions'] == 3, row


def test_a_weakened_move_counts_the_excess_lines_not_the_whole_body(plan_context, tmp_path, monkeypatch) -> None:
    """A moved body whose assertion line is already carried elsewhere proves no move.

    ``other_test.py`` carries ``assert 1 == 1`` for the same identity both before and
    after; the deleted file's only moved line is that same one, so the EXCESS is empty
    and the whole two-assertion test is lost. Counting the after body's assertions
    instead would credit one of them.
    """
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    _commit(
        repo,
        {
            'test/source_test.py': 'def test_a():\n    assert 1 == 1\n    assert 2 == 2\n',
            'test/other_test.py': 'def test_a():\n    assert 1 == 1\n',
        },
    )
    _git(repo, 'checkout', '--quiet', '-b', 'feature')
    _git(repo, 'rm', 'test/source_test.py')
    _commit(
        repo,
        {
            'test/other_test.py': 'def test_a():\n    assert 1 == 1\n# changed\n',
            'test/moved_test.py': 'def test_a():\n    assert 1 == 1\n',
        },
        'move the weakened test',
    )

    payload = _run(repo, plan_context, monkeypatch)

    assert payload['status'] == 'success', payload
    rows = [row for row in _rows(payload) if row['path'] == 'test/source_test.py']
    assert rows, payload
    assert rows[0]['removed_assertions'] == 2, rows


def test_a_partial_move_survives_by_its_excess_lines_only(plan_context, tmp_path, monkeypatch) -> None:
    """A weakened move with a NON-empty excess survives by those excess assertions only."""
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    _commit(
        repo,
        {
            'test/source_test.py': 'def test_a():\n    assert 1 == 1\n    assert 2 == 2\n    assert 3 == 3\n',
            'test/other_test.py': 'def test_a():\n    assert 2 == 2\n',
        },
    )
    _git(repo, 'checkout', '--quiet', '-b', 'feature')
    _git(repo, 'rm', 'test/source_test.py')
    _commit(
        repo,
        {
            'test/other_test.py': 'def test_a():\n    assert 2 == 2\n# changed\n',
            'test/moved_test.py': 'def test_a():\n    assert 1 == 1\n    assert 2 == 2\n',
        },
        'move the weakened test',
    )

    payload = _run(repo, plan_context, monkeypatch)

    assert payload['status'] == 'success', payload
    rows = [row for row in _rows(payload) if row['path'] == 'test/source_test.py']
    assert rows, payload
    # excess = {assert 1 == 1}; assert 2 is carried by other_test, assert 3 is lost.
    assert rows[0]['removed_assertions'] == 2, rows


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

    set_total = [row for row in _rows(payload) if row.get('acceptance_kind') == 'set_total']
    assert set_total, payload
    assert set_total[0]['path'] == 'test/q_test.py', payload


# --- D1 (JVM): a disabled JVM test is decided per METHOD, not per class --------------------

_JAVA_TEST_PATH = 'src/test/java/com/example/FooTest.java'
_JAVA_FOO_TEST = (
    'package com.example;\n\n'
    'import org.junit.jupiter.api.Disabled;\n\n'
    'class FooTest {\n'
    '    void a() {\n'
    '        assertTrue(true);\n'
    '    }\n\n'
    '    void b() {\n'
    '        assertTrue(true);\n'
    '    }\n'
    '}\n'
)


def _java_with_disabled(methods: tuple[str, ...]) -> str:
    """The ``FooTest`` fixture with ``@Disabled`` above each named method."""
    text = _JAVA_FOO_TEST
    for method in methods:
        text = text.replace(f'    void {method}() {{', f'    @Disabled\n    void {method}() {{')
    return text


def _filter_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [row for row in payload.get('findings') or [] if row.get('kind') == 'test_filtered']


def test_a_base_disabled_jvm_method_does_not_mask_a_second_one(plan_context, tmp_path, monkeypatch) -> None:
    """Head A disables ``a()``; head B disables ``b()`` too. Only ``b`` is the new row."""
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    _commit(repo, {_JAVA_TEST_PATH: _java_with_disabled(('a',))})
    _git(repo, 'checkout', '--quiet', '-b', 'feature')
    _commit(repo, {_JAVA_TEST_PATH: _java_with_disabled(('a', 'b'))}, 'disable b as well')

    payload = _run(repo, plan_context, monkeypatch)

    rows = _filter_rows(payload)
    assert len(rows) == 1, payload
    assert rows[0]['marked_tests'] == ['FooTest::b'], rows
    assert rows[0]['pairs'] == [{'test': 'FooTest::b', 'marker': '@Disabled'}], rows


def test_only_the_named_jvm_method_is_reported(plan_context, tmp_path, monkeypatch) -> None:
    """Control: one branch-added ``@Disabled`` names exactly its own method."""
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    _commit(repo, {_JAVA_TEST_PATH: _JAVA_FOO_TEST})
    _git(repo, 'checkout', '--quiet', '-b', 'feature')
    _commit(repo, {_JAVA_TEST_PATH: _java_with_disabled(('a',))}, 'disable a')

    payload = _run(repo, plan_context, monkeypatch)

    rows = _filter_rows(payload)
    assert len(rows) == 1, payload
    assert rows[0]['marked_tests'] == ['FooTest::a'], rows


def test_both_jvm_methods_added_after_the_base_are_paired_separately(plan_context, tmp_path, monkeypatch) -> None:
    """Two methods disabled by the branch carry TWO pairs, not one class-level marker set."""
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    _commit(repo, {_JAVA_TEST_PATH: _JAVA_FOO_TEST})
    _git(repo, 'checkout', '--quiet', '-b', 'feature')
    _commit(repo, {_JAVA_TEST_PATH: _java_with_disabled(('a', 'b'))}, 'disable both')

    payload = _run(repo, plan_context, monkeypatch)

    rows = _filter_rows(payload)
    assert len(rows) == 1, payload
    assert rows[0]['pairs'] == [
        {'test': 'FooTest::a', 'marker': '@Disabled'},
        {'test': 'FooTest::b', 'marker': '@Disabled'},
    ], rows


def test_a_class_level_annotation_belongs_to_the_class_not_its_first_method(
    plan_context, tmp_path, monkeypatch
) -> None:
    """``@Disabled`` above ``class FooTest`` is the class's marker, never ``a()``'s."""
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    base = _JAVA_FOO_TEST
    _commit(repo, {_JAVA_TEST_PATH: base})
    _git(repo, 'checkout', '--quiet', '-b', 'feature')
    _commit(repo, {_JAVA_TEST_PATH: base.replace('class FooTest {', '@Disabled\nclass FooTest {')}, 'disable the class')

    payload = _run(repo, plan_context, monkeypatch)

    rows = _filter_rows(payload)
    assert len(rows) == 1, payload
    assert rows[0]['marked_tests'] == ['FooTest'], rows


def test_a_python_call_line_is_not_a_jvm_method_identity(plan_context, tmp_path, monkeypatch) -> None:
    """``assert is_valid(cfg)`` has a JVM header's shape but is part of ``test_a``.

    The JVM arm is scoped by file suffix. Applied to every file it would read the
    call as a method named ``is_valid``, splitting ``test_a``'s span and reporting a
    false loss for an ADDITION.
    """
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    _commit(repo, {'test/plain_test.py': 'def test_a():\n    assert 1 == 1\n    assert 3 == 3\n'})
    _git(repo, 'checkout', '--quiet', '-b', 'feature')
    _commit(
        repo,
        {'test/plain_test.py': 'def test_a():\n    assert 1 == 1\n    assert is_valid(cfg)\n    assert 3 == 3\n'},
        'add a call-shaped assertion',
    )

    payload = _run(repo, plan_context, monkeypatch)

    assert _rows(payload) == [], payload


def test_a_kotlin_class_header_is_scope_not_a_method(plan_context, tmp_path, monkeypatch) -> None:
    """``class FooTest() {`` is a class, so its method is ``FooTest::a`` — not a bare ``a``.

    The JVM method arm's shape also fits the class line; consuming it as a method left
    every method unqualified, so a deleted ``A::a`` and an unrelated new ``B::a`` with
    the same body were credited as a move.
    """
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    kotlin = 'class FooTest() {\n    fun a() {\n        assertTrue(true)\n    }\n}\n'
    _commit(repo, {'src/test/kotlin/FooTest.kt': kotlin})
    _git(repo, 'checkout', '--quiet', '-b', 'feature')
    _git(repo, 'rm', 'src/test/kotlin/FooTest.kt')
    _commit(
        repo,
        {'src/test/kotlin/BarTest.kt': 'class BarTest() {\n    fun a() {\n        assertTrue(true)\n    }\n}\n'},
        'add an unrelated same-named method in another class',
    )

    payload = _run(repo, plan_context, monkeypatch)

    rows = _rows(payload)
    assert any(row['path'] == 'src/test/kotlin/FooTest.kt' for row in rows), payload
    row = next(row for row in rows if row['path'] == 'src/test/kotlin/FooTest.kt')
    assert any(entry['identity'] == 'FooTest::a' for entry in row['removed_tests']), row


def test_a_moved_pre_image_parses_the_added_file_with_its_own_path() -> None:
    """The added file's path decides the JVM arm, not the last pre-image key."""
    java = 'class FooTest {\n    void a() {\n        assertTrue(true);\n    }\n}\n'
    before = {
        'src/FooTest.java': java,
        'test/x_test.py': 'def test_x():\n    assert 1 == 1\n',
    }
    added = 'src/moved/FooTest.java'
    after = {added: 'class FooTest {\n    @Disabled\n    void a() {\n        assertTrue(true);\n    }\n}\n'}

    pre = _integrity._moved_pre_image(after[added], before, after, added)

    assert pre == java


def test_a_kotlin_statement_is_not_a_jvm_method_identity() -> None:
    """Semicolon-free Kotlin statements are not methods, despite the header shape."""
    text = (
        'class FooTest() {\n'
        '    fun a() {\n'
        '        assertTrue(true)\n'
        '        return helper(1)\n'
        '        throw IllegalStateException("x")\n'
        '    }\n'
        '}\n'
    )

    identities = [name for _, name in _integrity._identity_spans(text, 'src/FooTest.kt')]

    assert identities == ['FooTest::a'], identities


def test_an_anonymous_class_initializer_is_not_a_method_identity() -> None:
    """``return new Bar() {`` has the JVM header shape but is not a method."""
    text = 'class FooTest {\n    void b() {\n        return new Bar() {\n        };\n    }\n}\n'

    identities = [name for _, name in _integrity._identity_spans(text, 'src/test/java/FooTest.java')]

    assert identities == ['FooTest::b'], identities


def test_a_js_identity_is_qualified_by_its_enclosing_describe(plan_context, tmp_path, monkeypatch) -> None:
    """A deleted ``A::renders`` is not credited by an unrelated new ``B::renders``.

    The move proof keys on the identity name plus the assertion-line text, so an
    unqualified ``renders`` on both sides credits the loss. The enclosing ``describe``
    is part of the identity, so the two suites are different tests.
    """
    repo = _repo(tmp_path)
    _commit(repo, {'README.md': 'readme\n'})
    _commit(
        repo,
        {'src/a.test.js': "describe('A', () => {\n  it('renders', () => {\n    expect(1).toBe(1);\n  });\n});\n"},
    )
    _git(repo, 'checkout', '--quiet', '-b', 'feature')
    _git(repo, 'rm', 'src/a.test.js')
    _commit(
        repo,
        {'src/b.test.js': "describe('B', () => {\n  it('renders', () => {\n    expect(1).toBe(1);\n  });\n});\n"},
        'add an unrelated same-named test',
    )

    payload = _run(repo, plan_context, monkeypatch)

    rows = _rows(payload)
    assert any(row['path'] == 'src/a.test.js' for row in rows), payload
    row = next(row for row in rows if row['path'] == 'src/a.test.js')
    assert any(entry['identity'] == 'A::renders' for entry in row['removed_tests']), row
