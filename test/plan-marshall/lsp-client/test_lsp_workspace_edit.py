#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the pure WorkspaceEdit helpers (D2 footprint/apply/verdict).

These exercise the write side's core logic with no live server: footprint is
captured from the edit itself, edits apply bottom-up, a worsened error set
fails the verdict, and a rollback restores the original bytes.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from conftest import get_script_path

SCRIPT_PATH = get_script_path('plan-marshall', 'lsp-client', 'lsp_client.py')
SCRIPTS_DIR = SCRIPT_PATH.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import _lsp_workspace_edit as we  # noqa: E402


def _text_edit(sl, sc, el, ec, new_text):
    return {'range': {'start': {'line': sl, 'character': sc}, 'end': {'line': el, 'character': ec}}, 'newText': new_text}


# -- URI round-trip -----------------------------------------------------------


def test_uri_path_round_trip(tmp_path):
    p = tmp_path / 'mod.py'
    p.write_text('x = 1\n')
    uri = we.path_to_uri(p)
    assert uri.startswith('file://')
    assert we.uri_to_path(uri) == str(p.resolve())


def test_uri_to_path_passthrough_non_file():
    assert we.uri_to_path('untitled:foo') == 'untitled:foo'


# -- normalize_changes / footprint -------------------------------------------


def test_normalize_document_changes():
    edit = {'documentChanges': [
        {'textDocument': {'uri': 'file:///a.py', 'version': 1}, 'edits': [_text_edit(0, 0, 0, 1, 'X')]},
        {'textDocument': {'uri': 'file:///b.py', 'version': 1}, 'edits': [_text_edit(0, 0, 0, 1, 'Y'), _text_edit(1, 0, 1, 1, 'Z')]},
    ]}
    changes, notes = we.normalize_changes(edit)
    assert set(changes) == {'/a.py', '/b.py'}
    assert len(changes['/b.py']) == 2
    assert notes == []


def test_normalize_legacy_changes():
    edit = {'changes': {'file:///a.py': [_text_edit(0, 0, 0, 1, 'X')]}}
    changes, notes = we.normalize_changes(edit)
    assert list(changes) == ['/a.py']


def test_normalize_reports_resource_operation():
    edit = {'documentChanges': [{'kind': 'rename', 'oldUri': 'file:///a.py', 'newUri': 'file:///b.py'}]}
    changes, notes = we.normalize_changes(edit)
    assert changes == {}
    assert any('rename' in note for note in notes)


def test_capture_footprint_from_edit():
    edit = {'documentChanges': [
        {'textDocument': {'uri': 'file:///b.py'}, 'edits': [_text_edit(0, 0, 0, 1, 'Y')]},
        {'textDocument': {'uri': 'file:///a.py'}, 'edits': [_text_edit(0, 0, 0, 1, 'X'), _text_edit(2, 0, 2, 1, 'W')]},
    ]}
    footprint = we.capture_footprint(edit)
    # Sorted by path; edit_count taken from the edit itself.
    assert footprint == [{'path': '/a.py', 'edit_count': 2}, {'path': '/b.py', 'edit_count': 1}]


def test_capture_footprint_empty_for_empty_edit():
    assert we.capture_footprint({}) == []


# -- apply_text_edits ---------------------------------------------------------


def test_apply_single_edit():
    assert we.apply_text_edits('foo = 1\n', [_text_edit(0, 0, 0, 3, 'bar')]) == 'bar = 1\n'


def test_apply_multiple_edits_bottom_up():
    text = 'a = 1\nb = 2\n'
    edits = [_text_edit(0, 0, 0, 1, 'aa'), _text_edit(1, 0, 1, 1, 'bb')]
    # Order-independent: same result regardless of edit order in the list.
    assert we.apply_text_edits(text, edits) == 'aa = 1\nbb = 2\n'
    assert we.apply_text_edits(text, list(reversed(edits))) == 'aa = 1\nbb = 2\n'


def test_apply_insertion_edit():
    assert we.apply_text_edits('ab\n', [_text_edit(0, 1, 0, 1, 'X')]) == 'aXb\n'


# -- apply_workspace_edit + restore ------------------------------------------


def test_apply_and_restore_round_trip(tmp_path):
    a = tmp_path / 'a.py'
    b = tmp_path / 'b.py'
    a.write_text('foo = 1\n')
    b.write_text('bar = 2\n')
    edit = {'documentChanges': [
        {'textDocument': {'uri': we.path_to_uri(a)}, 'edits': [_text_edit(0, 0, 0, 3, 'FOO')]},
        {'textDocument': {'uri': we.path_to_uri(b)}, 'edits': [_text_edit(0, 0, 0, 3, 'BAR')]},
    ]}
    footprint, originals = we.apply_workspace_edit(edit)
    assert {row['path'] for row in footprint} == {str(a.resolve()), str(b.resolve())}
    assert a.read_text() == 'FOO = 1\n'
    assert b.read_text() == 'BAR = 2\n'

    we.restore_files(originals)
    assert a.read_text() == 'foo = 1\n'
    assert b.read_text() == 'bar = 2\n'


def test_apply_rolls_back_every_written_file_when_a_later_one_fails(tmp_path):
    """A malformed TextEdit on the middle file leaves all three byte-identical."""
    originals_text = {'a.py': 'foo = 1\n', 'b.py': 'bar = 2\n', 'c.py': 'baz = 3\n'}
    files = {}
    for name, text in originals_text.items():
        files[name] = tmp_path / name
        files[name].write_text(text)
    edit = {'documentChanges': [
        {'textDocument': {'uri': we.path_to_uri(files['a.py'])}, 'edits': [_text_edit(0, 0, 0, 3, 'AAA')]},
        # No 'range' — the exact shape a server bug produces, raising mid-apply
        # after a.py has already been rewritten.
        {'textDocument': {'uri': we.path_to_uri(files['b.py'])}, 'edits': [{'newText': 'oops'}]},
        {'textDocument': {'uri': we.path_to_uri(files['c.py'])}, 'edits': [_text_edit(0, 0, 0, 3, 'CCC')]},
    ]}

    with pytest.raises(we.WorkspaceApplyError) as raised:
        we.apply_workspace_edit(edit)

    assert raised.value.path == str(files['b.py'].resolve())
    assert raised.value.restore_error is None
    for name, text in originals_text.items():
        assert files[name].read_text() == text


def test_a_write_that_fails_PART_WAY_restores_the_file_it_damaged(tmp_path):
    """The failing file is restored too — it is the one the write already damaged.

    The sibling test above covers a failure that writes nothing (a malformed
    ``TextEdit``, caught in the transform). This one covers the opposite and far
    more dangerous shape: the write itself fails **after** truncating the file —
    ENOSPC, EIO, a full disk mid-refactor. The damaged file must be restored and
    the rollback must not report success over a tree it left modified.

    Pinned because the code once did exactly that: the failing path was dropped
    from the restore set in the handler, so the one file that needed restoring
    was the one that never got restored, ``restore_error`` stayed ``None``, and
    the payload published ``rolled_back: true`` over a truncated file.
    """
    originals_text = {'a.py': 'foo = 1\n', 'b.py': 'bar = 2\n', 'c.py': 'baz = 3\n'}
    files = {}
    for name, text in originals_text.items():
        files[name] = tmp_path / name
        files[name].write_text(text)
    edit = {'documentChanges': [
        {'textDocument': {'uri': we.path_to_uri(files[name])}, 'edits': [_text_edit(0, 0, 0, 3, 'XXX')]}
        for name in originals_text
    ]}

    real_write = Path.write_text
    state = {'failed': False}

    def truncate_then_fail(self, data, *args, **kwargs):
        if self.name == 'b.py' and not state['failed']:
            state['failed'] = True
            real_write(self, '', encoding='utf-8')  # what a partial write leaves behind
            raise OSError(28, 'No space left on device')
        return real_write(self, data, *args, **kwargs)

    Path.write_text = truncate_then_fail
    try:
        with pytest.raises(we.WorkspaceApplyError) as raised:
            we.apply_workspace_edit(edit)
    finally:
        Path.write_text = real_write

    assert raised.value.path == str(files['b.py'].resolve())
    assert raised.value.restore_error is None
    for name, text in originals_text.items():
        assert files[name].read_text() == text, f'{name} was not restored'


def test_a_rollback_that_cannot_restore_the_damaged_file_says_so(tmp_path):
    """When the restore itself keeps failing, the tree IS modified — and it reports it.

    The honest counterpart to the test above. ``restore_error`` is what turns
    ``rolled_back`` false in the payload, so a caller can tell a clean rollback
    from a tree left partly edited. A swallowed error here is the false-clean
    this whole write path exists to prevent.
    """
    files = {}
    for name, text in (('a.py', 'foo = 1\n'), ('b.py', 'bar = 2\n')):
        files[name] = tmp_path / name
        files[name].write_text(text)
    edit = {'documentChanges': [
        {'textDocument': {'uri': we.path_to_uri(files[name])}, 'edits': [_text_edit(0, 0, 0, 3, 'XXX')]}
        for name in files
    ]}

    real_write = Path.write_text

    def always_fail_on_b(self, data, *args, **kwargs):
        if self.name == 'b.py':
            real_write(self, '', encoding='utf-8')
            raise OSError(28, 'No space left on device')
        return real_write(self, data, *args, **kwargs)

    Path.write_text = always_fail_on_b
    try:
        with pytest.raises(we.WorkspaceApplyError) as raised:
            we.apply_workspace_edit(edit)
    finally:
        Path.write_text = real_write

    assert raised.value.restore_error is not None  # never swallowed
    assert files['a.py'].read_text() == 'foo = 1\n'  # the restorable one still is


# -- diagnostics counting + verdict ------------------------------------------


def test_count_error_diagnostics_counts_only_errors():
    diags = [{'severity': 1}, {'severity': 2}, {'severity': 1}, {'severity': 3}, {}]
    assert we.count_error_diagnostics(diags) == 2


def _error(message, line=0, code='E'):
    return {'severity': 1, 'code': code, 'message': message,
            'range': {'start': {'line': line, 'character': 0}}}


def test_edit_verdict_fails_when_any_file_gained_an_error():
    assert we.edit_verdict({'/a.py': [_error('boom')]}) == 'failed'
    assert we.edit_verdict({'/a.py': [], '/b.py': [_error('boom')]}) == 'failed'


def test_edit_verdict_passes_when_no_file_gained_an_error():
    assert we.edit_verdict({}) == 'success'
    assert we.edit_verdict({'/a.py': [], '/b.py': []}) == 'success'


# -- diagnostic set delta -----------------------------------------------------


def test_delta_sees_a_swapped_error_that_a_count_cannot():
    """[A] -> [B] is one error out, one in: the count is unchanged, the set is not."""
    added, removed = we.diagnostic_delta([_error('A')], [_error('B')])
    assert [diag['message'] for diag in added] == ['B']
    assert [diag['message'] for diag in removed] == ['A']


def test_delta_reports_only_the_new_error_not_the_pre_existing_one():
    added, removed = we.diagnostic_delta([_error('A')], [_error('A'), _error('B', line=4)])
    assert [diag['message'] for diag in added] == ['B']
    assert removed == []


def test_delta_is_a_multiset_so_a_repeated_error_gaining_one_is_visible():
    before = [_error('dup'), _error('dup')]
    after = [_error('dup'), _error('dup'), _error('dup')]
    added, removed = we.diagnostic_delta(before, after)
    assert len(added) == 1
    assert removed == []


def test_delta_ignores_non_error_severities():
    warning = {'severity': 2, 'message': 'style', 'range': {'start': {'line': 0, 'character': 0}}}
    added, removed = we.diagnostic_delta([], [warning])
    assert added == []
    assert removed == []


def test_delta_distinguishes_same_message_at_a_different_line():
    added, _removed = we.diagnostic_delta([_error('A', line=1)], [_error('A', line=1), _error('A', line=9)])
    assert [diag['range']['start']['line'] for diag in added] == [9]
