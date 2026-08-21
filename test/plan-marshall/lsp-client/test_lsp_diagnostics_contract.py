#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""The diagnostics answer contract, driven against a fake server subprocess.

These are CI-portable: they need no language server on ``PATH``, because the
server *is* the fixture — spawned as a subprocess and driven over the real
:class:`StdioTransport`, so the framing, the reader thread and the publish
counter are all under test rather than stubbed past.

Each one pins a way the shipped code used to answer confidently without an
answer:

* the post-edit re-diagnose settling for the **pre-edit** verdict, so a defective
  edit was compared against its own earlier state and reported ``success``;
* a server that never publishes being byte-identical, in every payload field, to
  a server that examined the file and called it clean;
* the verdict summing error **counts** across the footprint, so an error swapped
  for a different one — or moved between two files — netted zero and landed;
* the failure payload listing the whole post-edit set as ``new_diagnostics``,
  presenting pre-existing errors as newly introduced.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from conftest import get_script_path

SCRIPT_PATH = get_script_path('plan-marshall', 'lsp-client', 'lsp_client.py')
SCRIPTS_DIR = SCRIPT_PATH.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import lsp_client as client  # noqa: E402
from _fake_lsp_server import write_fake_server  # noqa: E402
from _lsp_jsonrpc import LspSession, StdioTransport  # noqa: E402
from _lsp_workspace_edit import path_to_uri  # noqa: E402

# Spelled as literals rather than imported from the module under test: a guard
# that takes its expectation from the code it guards agrees with that code by
# construction, including when both are wrong.
STATE_OK = 'ok'
STATE_UNKNOWN = 'unknown'
REASON_UNAVAILABLE = 'diagnostics_unavailable'
REASON_UNANSWERED = 'diagnostics_unanswered'
REASON_WORSENED = 'diagnostics_worsened'

# Short waits keep the suite quick; the contract under test is the *ordering* of
# publishes against the settle window, not its duration.
SETTLE = 0.3
TIMEOUT = 6.0


def _error(message: str, line: int = 0) -> dict[str, Any]:
    return {'severity': 1, 'code': 'E1', 'message': message,
            'range': {'start': {'line': line, 'character': 0}, 'end': {'line': line, 'character': 3}}}


def _rename_edit(*targets: Path) -> dict[str, Any]:
    """A WorkspaceEdit replacing the first three characters of each target."""
    return {'documentChanges': [
        {
            'textDocument': {'uri': path_to_uri(target), 'version': 2},
            'edits': [{'range': {'start': {'line': 0, 'character': 0}, 'end': {'line': 0, 'character': 3}},
                       'newText': 'bar'}],
        }
        for target in targets
    ]}


def _session(tmp_path: Path, config: dict[str, Any], timeout: float = TIMEOUT) -> LspSession:
    command = write_fake_server(tmp_path, config)
    transport = StdioTransport(command, cwd=str(tmp_path))
    session = LspSession(transport, str(tmp_path), diagnostics_settle=SETTLE, diagnostics_timeout=timeout)
    session.initialize()
    return session


def _module(tmp_path: Path, name: str) -> Path:
    target = tmp_path / name
    target.write_text('foo = 1\n', encoding='utf-8')
    return target


# =============================================================================
# (a) The post-edit publish arrives AFTER the settle window
# =============================================================================


def test_edit_waits_for_the_post_change_publish_instead_of_the_cached_one(tmp_path):
    """A late verdict is waited for, not pre-empted by the pre-edit one."""
    target = _module(tmp_path, 'm.py')
    config = {
        'rename_edit': _rename_edit(target),
        'files': {'m.py': {'open': [], 'change': [_error('undefined symbol')]}},
        # Strictly greater than SETTLE: the stream goes quiet with only the
        # pre-edit verdict cached, which is exactly when the old wait returned.
        'publish_delay': {'change': SETTLE * 3},
    }
    session = _session(tmp_path, config)
    try:
        result = client._run_edit(session, 'python', str(target), 0, 0, 'bar')
    finally:
        session.close()

    assert result['status'] == 'failed'
    assert result['reason'] == REASON_WORSENED
    assert result['rolled_back'] is True
    assert target.read_text() == 'foo = 1\n'  # byte-identical to its pre-edit content


# =============================================================================
# (b) A server that answers initialize and never publishes
# =============================================================================


def test_diagnose_reports_unknown_when_the_server_never_publishes(tmp_path):
    """Silence and a clean verdict differ in state, answered, and the count fields."""
    target = _module(tmp_path, 'm.py')

    silent_root = tmp_path / 'silent'
    silent_root.mkdir()
    clean_root = tmp_path / 'clean'
    clean_root.mkdir()

    silent = _session(silent_root, {'files': {}}, timeout=1.0)
    try:
        unanswered = client._run_diagnose(silent, 'python', str(target))
    finally:
        silent.close()

    speaking = _session(clean_root, {'files': {'m.py': {'open': []}}})
    try:
        clean = client._run_diagnose(speaking, 'python', str(target))
    finally:
        speaking.close()

    assert unanswered['state'] == STATE_UNKNOWN
    assert unanswered['answered'] is False
    assert unanswered['reason'] == REASON_UNANSWERED
    # The count fields are ABSENT, not zero: a zero here is the false clean
    # signal the whole verb exists not to emit.
    assert 'error_count' not in unanswered
    assert 'diagnostics' not in unanswered

    assert clean['state'] == STATE_OK
    assert clean['answered'] is True
    assert clean['error_count'] == 0

    differing = {key for key in set(unanswered) | set(clean) if unanswered.get(key) != clean.get(key)}
    assert differing  # not byte-identical payloads, which is what they used to be


def test_edit_fails_closed_when_the_server_never_publishes(tmp_path):
    """The BASELINE verdict is missing, so the verb stops before writing anything.

    ``rolled_back`` is ``False`` here because there was nothing to roll back —
    NOT because a rollback failed. That distinction is what ``phase`` carries,
    and a leaf that reads the flag without it concludes the tree is damaged when
    no byte was written. Asserted rather than assumed, because this is the
    payload a pull-diagnostics server returns on *every* call.
    """
    target = _module(tmp_path, 'm.py')
    config = {'rename_edit': _rename_edit(target), 'files': {}}
    session = _session(tmp_path, config, timeout=1.0)
    try:
        result = client._run_edit(session, 'python', str(target), 0, 0, 'bar')
    finally:
        session.close()

    assert result['status'] == 'failed'
    assert result['reason'] == REASON_UNAVAILABLE
    assert result['applied'] is False
    assert result['phase'] == 'before'
    assert result['rolled_back'] is False
    assert result['unverified_path'] == str(target)
    assert 'restore_error' not in result  # the flag's OTHER meaning, absent here
    assert target.read_text() == 'foo = 1\n'


def test_a_missing_post_edit_verdict_rolls_back_and_says_so(tmp_path):
    """The BASELINE arrives and the post-change verdict does not.

    The opposite route to the one above, through the same reason code: the edit
    WAS applied and then restored, so ``rolled_back`` is ``True``. Both routes
    are pinned because the two are indistinguishable on ``reason`` alone, and
    the documented reading of ``rolled_back`` turns entirely on which one ran.
    """
    target = _module(tmp_path, 'm.py')
    config = {'rename_edit': _rename_edit(target), 'files': {'m.py': {'open': []}}}
    session = _session(tmp_path, config, timeout=1.0)
    try:
        result = client._run_edit(session, 'python', str(target), 0, 0, 'bar')
    finally:
        session.close()

    assert result['status'] == 'failed'
    assert result['reason'] == REASON_UNAVAILABLE
    assert result['phase'] == 'after'
    assert result['rolled_back'] is True
    assert result['unverified_path'] == str(target)
    assert target.read_text() == 'foo = 1\n'  # restored, not left edited


# =============================================================================
# (c) A swapped error, and an error that moves between two files
# =============================================================================


def test_swapping_one_error_for_another_in_one_file_fails_and_rolls_back(tmp_path):
    """[A] -> [B] leaves the count at 1 either side; the SET says the edit is worse."""
    target = _module(tmp_path, 'm.py')
    config = {
        'rename_edit': _rename_edit(target),
        'files': {'m.py': {'open': [_error('A')], 'change': [_error('B')]}},
    }
    session = _session(tmp_path, config)
    try:
        result = client._run_edit(session, 'python', str(target), 0, 0, 'bar')
    finally:
        session.close()

    assert result['errors_before'] == result['errors_after'] == 1  # the count nets to zero
    assert result['status'] == 'failed'
    assert result['reason'] == REASON_WORSENED
    assert target.read_text() == 'foo = 1\n'


def test_an_error_moving_between_footprint_files_fails_and_rolls_both_back(tmp_path):
    """A footprint-wide count cannot see an error move from a.py to b.py."""
    first = _module(tmp_path, 'a.py')
    second = _module(tmp_path, 'b.py')
    config = {
        'rename_edit': _rename_edit(first, second),
        'files': {
            'a.py': {'open': [_error('A')], 'change': []},
            'b.py': {'open': [], 'change': [_error('A')]},
        },
    }
    session = _session(tmp_path, config)
    try:
        result = client._run_edit(session, 'python', str(first), 0, 0, 'bar')
    finally:
        session.close()

    assert result['errors_before'] == result['errors_after'] == 1
    assert result['status'] == 'failed'
    assert result['reason'] == REASON_WORSENED
    assert first.read_text() == 'foo = 1\n'
    assert second.read_text() == 'foo = 1\n'


# =============================================================================
# (d) new_diagnostics carries the added set only
# =============================================================================


def test_new_diagnostics_lists_the_added_error_and_not_the_pre_existing_one(tmp_path):
    target = _module(tmp_path, 'm.py')
    config = {
        'rename_edit': _rename_edit(target),
        'files': {'m.py': {'open': [_error('A')], 'change': [_error('A'), _error('B', line=4)]}},
    }
    session = _session(tmp_path, config)
    try:
        result = client._run_edit(session, 'python', str(target), 0, 0, 'bar')
    finally:
        session.close()

    assert result['status'] == 'failed'
    messages = [row['message'] for row in result['new_diagnostics']]
    assert messages == ['B']
    assert result['new_diagnostic_count'] == 1
