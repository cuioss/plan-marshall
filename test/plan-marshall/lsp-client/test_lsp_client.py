#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for lsp_client verb logic using an injected fake transport.

These cover the coverage contract (no-server vs ran-and-found-nothing must stay
distinguishable), the opt-in degradation states (not_configured vs unreachable),
and the edit orchestration (worsened diagnostics fail the step and roll back) —
all without a live language server.
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

from conftest import get_script_path

SCRIPT_PATH = get_script_path('plan-marshall', 'lsp-client', 'lsp_client.py')
SCRIPTS_DIR = SCRIPT_PATH.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import lsp_client as client  # noqa: E402
import run_config  # noqa: E402
from _lsp_jsonrpc import LspSession  # noqa: E402
from _lsp_workspace_edit import path_to_uri  # noqa: E402


class FakeTransport:
    """A canned transport: requests return fixtures, diagnostics pop a queue."""

    def __init__(self, responses: dict[str, Any] | None = None, diagnostics: list[list[dict[str, Any]]] | None = None):
        self._responses = responses or {}
        self._diagnostics = list(diagnostics or [])
        self.notifications: list[tuple[str, dict[str, Any]]] = []
        self.closed = False

    def request(self, method: str, params: dict[str, Any], timeout: float = 30.0) -> dict[str, Any]:
        return {'jsonrpc': '2.0', 'id': 0, 'result': self._responses.get(method)}

    def notify(self, method: str, params: dict[str, Any]) -> None:
        self.notifications.append((method, params))

    def wait_for_diagnostics(self, uri: str, settle: float = 2.0, timeout: float = 15.0) -> list[dict[str, Any]]:
        return self._diagnostics.pop(0) if self._diagnostics else []

    def wait_until_idle(self, settle: float = 1.5, timeout: float = 8.0) -> None:
        return None

    def close(self) -> None:
        self.closed = True


def _session(responses=None, diagnostics=None, root='/tmp') -> LspSession:
    return LspSession(FakeTransport(responses, diagnostics), root)


def _text_edit(sl, sc, el, ec, new_text):
    return {'range': {'start': {'line': sl, 'character': sc}, 'end': {'line': el, 'character': ec}}, 'newText': new_text}


# =============================================================================
# select_language_server (pure config resolution)
# =============================================================================


def test_select_language_server_enabled():
    config = {'language_servers': {'python': {'enabled': True, 'command': ['srv', '--stdio'], 'language_id': 'python'}}}
    resolved = client.select_language_server(config, 'python')
    assert resolved == {'command': ['srv', '--stdio'], 'language_id': 'python'}


def test_select_language_server_disabled_is_none():
    config = {'language_servers': {'python': {'enabled': False, 'command': ['srv']}}}
    assert client.select_language_server(config, 'python') is None


def test_select_language_server_absent_is_none():
    assert client.select_language_server({'language_servers': {}}, 'python') is None
    assert client.select_language_server({}, 'python') is None


def test_select_language_server_bad_command_is_none():
    assert client.select_language_server({'language_servers': {'python': {'command': 'not-a-list'}}}, 'python') is None
    assert client.select_language_server({'language_servers': {'python': {'command': []}}}, 'python') is None


# =============================================================================
# Coverage contract — the three states are separately representable
# =============================================================================


def test_lookup_ran_found_nothing_is_ok_with_provider(tmp_path):
    target = tmp_path / 'm.py'
    target.write_text('x = 1\n')
    result = client._run_lookup(_session({'textDocument/documentSymbol': []}), 'python', 'document-symbol',
                                str(target), 0, 0, None)
    assert result['status'] == 'success'
    assert result['state'] == client.STATE_OK
    assert result['provider_count'] == 1
    assert result['location_count'] == 0  # a real "found nothing", not a missing capability


def test_lookup_document_symbol_returns_coordinates(tmp_path):
    target = tmp_path / 'm.py'
    target.write_text('def foo():\n    return 1\n')
    symbols = [{'name': 'foo', 'kind': 12, 'selectionRange': {'start': {'line': 0, 'character': 4}}}]
    result = client._run_lookup(_session({'textDocument/documentSymbol': symbols}), 'python', 'document-symbol',
                                str(target), 0, 0, None)
    assert result['provider_count'] == 1
    assert result['location_count'] == 1
    assert result['locations'][0]['name'] == 'foo'
    assert result['locations'][0]['line'] == 0


def test_lookup_references_returns_locations(tmp_path):
    target = tmp_path / 'm.py'
    target.write_text('x = 1\n')
    locations = [{'uri': path_to_uri(target), 'range': {'start': {'line': 3, 'character': 2},
                                                        'end': {'line': 3, 'character': 5}}}]
    result = client._run_lookup(_session({'textDocument/references': locations}), 'python', 'references',
                                str(target), 0, 0, None)
    assert result['location_count'] == 1
    assert result['locations'][0]['path'] == str(target.resolve())
    assert result['locations'][0]['line'] == 3


def test_lookup_workspace_symbol():
    symbols = [{'name': 'Thing', 'kind': 5, 'location': {'uri': 'file:///a.py',
                                                         'range': {'start': {'line': 1, 'character': 0}}}}]
    result = client._run_lookup(_session({'workspace/symbol': symbols}), 'python', 'workspace-symbol',
                                None, 0, 0, 'Thing')
    assert result['location_count'] == 1
    assert result['locations'][0]['name'] == 'Thing'


def test_three_states_are_distinguishable(plan_context):
    """not_configured vs unreachable vs ran-found-nothing differ on state+provider_count+status."""
    # ran-and-found-nothing (server ran)
    ran = client._run_lookup(_session({'workspace/symbol': []}), 'python', 'workspace-symbol', None, 0, 0, 'x')
    # not configured (empty store)
    not_configured = client.cmd_lookup(argparse.Namespace(
        language='python', project_path='.', kind='workspace-symbol', file=None, line=0, character=0, symbol='x'))
    # configured but unreachable
    run_config.cmd_language_server_set(argparse.Namespace(
        language='python', command='["/nonexistent/definitely-not-a-real-lsp"]', language_id='python', disabled=False))
    unreachable = client.cmd_lookup(argparse.Namespace(
        language='python', project_path='.', kind='workspace-symbol', file=None, line=0, character=0, symbol='x'))

    triples = {
        (ran['status'], ran['state'], ran['provider_count']),
        (not_configured['status'], not_configured['state'], not_configured['provider_count']),
        (unreachable['status'], unreachable['state'], unreachable['provider_count']),
    }
    assert len(triples) == 3  # all three states are separately representable
    assert ran['status'] == 'success' and ran['provider_count'] == 1
    assert not_configured['state'] == client.STATE_NOT_CONFIGURED and not_configured['provider_count'] == 0
    assert unreachable['state'] == client.STATE_UNREACHABLE and unreachable['provider_count'] == 0
    assert 'reason' in unreachable


# =============================================================================
# Preflight — configured/reachable distinguishability (D4)
# =============================================================================


def test_preflight_not_configured(plan_context):
    result = client.cmd_preflight(argparse.Namespace(language='python', project_path='.'))
    assert result['state'] == client.STATE_NOT_CONFIGURED
    assert result['configured'] is False
    assert result['reachable'] is False


def test_preflight_unreachable(plan_context):
    run_config.cmd_language_server_set(argparse.Namespace(
        language='python', command='["/nonexistent/definitely-not-a-real-lsp"]', language_id='python', disabled=False))
    result = client.cmd_preflight(argparse.Namespace(language='python', project_path='.'))
    assert result['state'] == client.STATE_UNREACHABLE
    assert result['configured'] is True
    assert result['reachable'] is False
    assert 'reason' in result


# =============================================================================
# Edit orchestration — worsened diagnostics fail the step and roll back
# =============================================================================


def test_edit_clean_applies_and_captures_footprint(tmp_path):
    target = tmp_path / 'm.py'
    target.write_text('foo = 1\n')
    workspace_edit = {'documentChanges': [
        {'textDocument': {'uri': path_to_uri(target)}, 'edits': [_text_edit(0, 0, 0, 3, 'bar')]}]}
    session = _session({'textDocument/rename': workspace_edit}, diagnostics=[[], []])
    result = client._run_edit(session, 'python', str(target), 0, 0, 'bar')
    assert result['status'] == 'success'
    assert result['applied'] is True
    assert result['file_count'] == 1
    assert result['files'][0]['path'] == str(target.resolve())
    assert target.read_text() == 'bar = 1\n'


def test_edit_worsened_fails_and_rolls_back(tmp_path):
    target = tmp_path / 'm.py'
    target.write_text('foo = 1\n')
    workspace_edit = {'documentChanges': [
        {'textDocument': {'uri': path_to_uri(target)}, 'edits': [_text_edit(0, 0, 0, 3, 'bar')]}]}
    # baseline clean, post-application one Error diagnostic -> worsened.
    session = _session({'textDocument/rename': workspace_edit}, diagnostics=[[], [{'severity': 1, 'message': 'boom'}]])
    result = client._run_edit(session, 'python', str(target), 0, 0, 'bar')
    assert result['status'] == 'failed'
    assert result['applied'] is False
    assert result['rolled_back'] is True
    assert result['reason'] == 'diagnostics_worsened'
    assert result['errors_before'] == 0
    assert result['errors_after'] == 1
    assert target.read_text() == 'foo = 1\n'  # rolled back to the original


def test_edit_no_workspace_edit(tmp_path):
    target = tmp_path / 'm.py'
    target.write_text('foo = 1\n')
    session = _session({'textDocument/rename': {}})
    result = client._run_edit(session, 'python', str(target), 0, 0, 'bar')
    assert result['status'] == 'success'
    assert result['applied'] is False
    assert result['reason'] == 'no_workspace_edit'
    assert result['file_count'] == 0


def test_edit_degraded_when_not_configured(plan_context, tmp_path):
    target = tmp_path / 'm.py'
    target.write_text('foo = 1\n')
    result = client.cmd_edit(argparse.Namespace(
        language='python', project_path='.', file=str(target), line=0, character=0, new_name='bar'))
    assert result['status'] == 'degraded'
    assert result['state'] == client.STATE_NOT_CONFIGURED
    assert result['fallback'] == 'read_edit'
    assert target.read_text() == 'foo = 1\n'  # untouched — byte-identical fallback


# =============================================================================
# Diagnose — pre-build signal carrying the gate boundary
# =============================================================================


def test_diagnose_carries_boundary_note(tmp_path):
    target = tmp_path / 'm.py'
    target.write_text('import nope\n')
    diags = [{'severity': 1, 'range': {'start': {'line': 0, 'character': 7}}, 'message': 'unresolved', 'code': 'x'}]
    result = client._run_diagnose(_session(diagnostics=[diags]), 'python', str(target))
    assert result['provider_count'] == 1
    assert result['error_count'] == 1
    note = result['boundary_note'].lower()
    assert 'supplement' in note and 'replace' in note
