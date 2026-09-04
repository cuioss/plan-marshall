#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The write path is all-or-nothing — no partial edit is ever reported as one.

Three ways the shipped code landed part of a change and called it a success:

* a ``WorkspaceEdit`` carrying a create/rename/delete-file operation had that
  part silently dropped, the text-edit remainder applied, and the footprint
  reported without it;
* an exception part-way through the apply loop escaped with earlier files
  already rewritten, ``originals`` discarded and no footprint in the output;
* the same file was opened twice with no ``didClose`` between, resetting the
  document version a strict server tracks.

Two of these are driven through ``cmd_edit`` **as a subprocess**, with real
argparse and real TOON rendering, because the helper-level proof cannot see a
defect in argument plumbing or in how ``files[]`` renders.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _fake_lsp_server import write_fake_server
from _lsp_jsonrpc import LspSession
from _lsp_workspace_edit import path_to_uri
from test_lsp_client import FakeTransport

from conftest import get_script_path, load_script_module, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'lsp-client', 'lsp_client.py')

client = load_script_module('plan-marshall', 'lsp-client', 'lsp_client.py')

# Literals, not imports from the module under test — see test_lsp_diagnostics_contract.
REASON_UNSUPPORTED = 'unsupported_resource_operation'
REASON_APPLY_FAILED = 'apply_failed'

_ORIGINAL = 'foo = 1\n'


def _module(directory: Path, name: str) -> Path:
    target = directory / name
    target.write_text(_ORIGINAL, encoding='utf-8')
    return target


def _replace_first_three(target: Path) -> dict[str, Any]:
    return {
        'textDocument': {'uri': path_to_uri(target), 'version': 2},
        'edits': [{'range': {'start': {'line': 0, 'character': 0}, 'end': {'line': 0, 'character': 3}},
                   'newText': 'bar'}],
    }


def _session(workspace_edit: dict[str, Any], diagnostics: list[Any]) -> tuple[LspSession, FakeTransport]:
    transport = FakeTransport({'textDocument/rename': workspace_edit}, diagnostics)
    return LspSession(transport, '/tmp'), transport


def _configure_fake_server(
    plan_base: Path,
    workspace_edit: dict[str, Any],
    workspace_symbols: list[dict[str, Any]] | None = None,
) -> None:
    """Write a run-configuration pointing `python` at the fake server subprocess."""
    command = write_fake_server(
        plan_base,
        {'rename_edit': workspace_edit, 'workspace_symbols': workspace_symbols, 'files': {}},
    )
    (plan_base / 'run-configuration.json').write_text(
        json.dumps({'language_servers': {'python': {'enabled': True, 'command': command, 'language_id': 'python'}}}),
        encoding='utf-8',
    )


# =============================================================================
# (c) A resource operation fails the verb whole
# =============================================================================


def test_resource_operation_fails_the_verb_and_modifies_nothing(tmp_path):
    """A rename-file operation is refused, not applied minus the part we cannot do."""
    target = _module(tmp_path, 'm.py')
    workspace_edit = {'documentChanges': [
        {'kind': 'rename', 'oldUri': path_to_uri(target), 'newUri': path_to_uri(tmp_path / 'renamed.py')},
        _replace_first_three(target),
    ]}
    session, _transport = _session(workspace_edit, [[], []])

    result = client._run_edit(session, 'python', str(target), 0, 0, 'bar')

    assert result['status'] == 'failed'
    assert result['reason'] == REASON_UNSUPPORTED
    assert result['applied'] is False
    assert result['unapplied_operation_count'] == 1
    assert any('rename' in note for note in result['notes'])
    assert target.read_text() == _ORIGINAL  # nothing on disk was touched


def test_resource_operation_is_refused_through_the_cli_seam(plan_context, tmp_path):
    """The same refusal, with real argparse and real TOON rendering in between."""
    plan_base = Path(plan_context.fixture_dir)
    target = _module(tmp_path, 'm.py')
    workspace_edit = {'documentChanges': [
        {'kind': 'create', 'uri': path_to_uri(tmp_path / 'new.py')},
        _replace_first_three(target),
    ]}
    _configure_fake_server(plan_base, workspace_edit)

    result = run_script(
        SCRIPT_PATH, 'edit', '--language', 'python', '--project-path', str(tmp_path),
        '--file', str(target), '--line', '0', '--character', '0', '--new-name', 'bar',
        env_overrides={'PLAN_BASE_DIR': str(plan_base)}, timeout=60,
    )

    assert result.returncode == 0
    assert 'status: failed' in result.stdout
    assert REASON_UNSUPPORTED in result.stdout
    assert 'create' in result.stdout  # the unapplied operation is NAMED, not just counted
    assert target.read_text() == _ORIGINAL


# =============================================================================
# (d) A failure mid-apply rolls every written file back
# =============================================================================


def test_three_file_edit_failing_on_the_second_rolls_all_three_back(tmp_path):
    first, second, third = (_module(tmp_path, name) for name in ('a.py', 'b.py', 'c.py'))
    workspace_edit = {'documentChanges': [
        _replace_first_three(first),
        # No 'range' — raises inside the apply loop, after a.py is rewritten.
        {'textDocument': {'uri': path_to_uri(second)}, 'edits': [{'newText': 'oops'}]},
        _replace_first_three(third),
    ]}
    session, _transport = _session(workspace_edit, [[], [], []])

    result = client._run_edit(session, 'python', str(first), 0, 0, 'bar')

    assert result['status'] == 'failed'
    assert result['reason'] == REASON_APPLY_FAILED
    assert result['failed_path'] == str(second.resolve())
    assert result['rolled_back'] is True
    for path in (first, second, third):
        assert path.read_text() == _ORIGINAL


# =============================================================================
# (e) One didOpen per distinct URI, monotonic didChange versions
# =============================================================================


def test_multi_file_edit_opens_each_uri_once_with_monotonic_versions(tmp_path):
    first, second = (_module(tmp_path, name) for name in ('a.py', 'b.py'))
    workspace_edit = {'documentChanges': [_replace_first_three(first), _replace_first_three(second)]}
    session, transport = _session(workspace_edit, [[], [], [], []])

    result = client._run_edit(session, 'python', str(first), 0, 0, 'bar')
    assert result['status'] == 'success'

    opened = [params['textDocument']['uri'] for method, params in transport.notifications
              if method == 'textDocument/didOpen']
    assert sorted(opened) == sorted({path_to_uri(first), path_to_uri(second)})
    assert len(opened) == len(set(opened))  # a.py is reached twice but opened once

    for uri in set(opened):
        versions = [params['textDocument']['version'] for method, params in transport.notifications
                    if method in ('textDocument/didOpen', 'textDocument/didChange')
                    and params['textDocument']['uri'] == uri]
        assert versions == sorted(versions)
        assert len(versions) == len(set(versions))


def test_reopening_an_open_document_does_not_reset_its_version(tmp_path):
    """The precondition the version guarantee rests on, pinned on its own."""
    target = _module(tmp_path, 'm.py')
    transport = FakeTransport()
    session = LspSession(transport, str(tmp_path))

    session.open(str(target))
    session.change_to_disk(str(target))
    session.open(str(target))  # second open — must be a no-op
    session.change_to_disk(str(target))

    versions = [params['textDocument']['version'] for _method, params in transport.notifications]
    assert versions == [1, 2, 3]
    assert session.is_open(str(target))


# =============================================================================
# Lookup rows carry their file — the CLI seam for the read verb
# =============================================================================


def test_workspace_symbol_rows_carry_path_through_the_cli_seam(plan_context, tmp_path):
    """A workspace-symbol row without `path` is the Grep round-trip this verb removes.

    Driven end to end: the fake server returns a real ``SymbolInformation``, so
    the assertion lands on what ``output_toon`` actually RENDERED. Asserting on a
    direct ``_symbol_rows`` call instead would leave a defect in argument
    plumbing or in the rendering of the new ``path`` / ``container`` / ``depth``
    keys entirely unseen — which is the hiding place this drive-through exists
    to close.
    """
    plan_base = Path(plan_context.fixture_dir)
    defining = _module(tmp_path, 'defines.py')
    _configure_fake_server(plan_base, {}, workspace_symbols=[
        {'name': 'Thing', 'kind': 5, 'containerName': 'Enclosing',
         'location': {'uri': path_to_uri(defining),
                      'range': {'start': {'line': 7, 'character': 4}, 'end': {'line': 7, 'character': 9}}}},
    ])

    result = run_script(
        SCRIPT_PATH, 'lookup', '--language', 'python', '--project-path', str(tmp_path),
        '--kind', 'workspace-symbol', '--symbol', 'Thing',
        env_overrides={'PLAN_BASE_DIR': str(plan_base)}, timeout=60,
    )

    assert result.returncode == 0, result.stderr
    assert 'state: ok' in result.stdout
    assert 'location_count: 1' in result.stdout
    # The row's own file, as rendered — not as a helper returned it.
    assert str(defining.resolve()) in result.stdout
    # The other two new keys must survive rendering as well.
    assert 'container' in result.stdout and 'Enclosing' in result.stdout
    assert 'depth' in result.stdout


def test_document_symbol_and_workspace_symbol_emit_the_same_key_set(tmp_path):
    target = _module(tmp_path, 'm.py')
    document_rows = client._run_lookup(
        LspSession(FakeTransport({'textDocument/documentSymbol': [
            {'name': 'Widget', 'kind': 5, 'range': {'start': {'line': 0, 'character': 0}}},
        ]}), str(tmp_path)),
        'python', 'document-symbol', str(target), 0, 0, None,
    )['locations']
    workspace_rows = client._run_lookup(
        LspSession(FakeTransport({'workspace/symbol': [
            {'name': 'Widget', 'kind': 5,
             'location': {'uri': path_to_uri(target), 'range': {'start': {'line': 0, 'character': 0}}}},
        ]}), str(tmp_path)),
        'python', 'workspace-symbol', None, 0, 0, 'Widget',
    )['locations']

    assert set(document_rows[0]) == set(workspace_rows[0])
    assert document_rows[0]['path'] == workspace_rows[0]['path'] == str(target.resolve())


def test_document_symbol_flattens_a_class_so_its_methods_appear(tmp_path):
    target = _module(tmp_path, 'm.py')
    symbols = [
        {'name': 'Widget', 'kind': 5, 'range': {'start': {'line': 0, 'character': 0}}, 'children': [
            {'name': 'spin', 'kind': 6, 'range': {'start': {'line': 1, 'character': 4}}},
            {'name': 'stop', 'kind': 6, 'range': {'start': {'line': 4, 'character': 4}}},
        ]},
        {'name': 'top_level', 'kind': 12, 'range': {'start': {'line': 8, 'character': 0}}},
    ]
    rows = client._run_lookup(
        LspSession(FakeTransport({'textDocument/documentSymbol': symbols}), str(tmp_path)),
        'python', 'document-symbol', str(target), 0, 0, None,
    )['locations']

    by_name = {row['name']: row for row in rows}
    assert set(by_name) == {'Widget', 'spin', 'stop', 'top_level'}
    assert by_name['spin']['line'] == 1
    assert by_name['spin']['container'] == 'Widget'
    assert by_name['spin']['depth'] == 1
    assert by_name['top_level']['depth'] == 0
