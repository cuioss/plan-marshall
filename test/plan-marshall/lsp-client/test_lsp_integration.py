#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Real-server integration tests — driven against a live pyright-langserver.

These are the plan's D0/D1/D2 evidence against a genuine language server (no
hand-built stand-in): coordinate lookups, an indexed workspace-symbol search, a
clean multi-edit rename, and the **adversarial** control — a deliberate defect
introduced through the WorkspaceEdit path, which the re-run diagnostics must
catch so the verdict fails.

Skipped when ``pyright-langserver`` is not installed (e.g. a CI runner without
it); the CI-portable logic coverage lives in ``test_lsp_client.py`` and
``test_lsp_workspace_edit.py``.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
import run_config
from _lsp_jsonrpc import LspSession, StdioTransport
from _lsp_workspace_edit import (
    apply_workspace_edit,
    count_error_diagnostics,
    diagnostic_delta,
    edit_verdict,
    path_to_uri,
    restore_files,
)

from conftest import load_script_module, parse_ns

client = load_script_module('plan-marshall', 'lsp-client', 'lsp_client.py')

_PYRIGHT = shutil.which('pyright-langserver')
pytestmark = pytest.mark.skipif(_PYRIGHT is None, reason='pyright-langserver not installed')


def _configure(project: Path) -> None:
    run_config.cmd_language_server_set(parse_ns('plan-marshall', 'manage-run-config', 'run_config.py', 'language-server', 'set', '--language', 'python', '--command', str(json.dumps([_PYRIGHT, '--stdio'])), '--language-id', 'python'))


def _sample_project(tmp_path: Path) -> Path:
    project = tmp_path / 'proj'
    project.mkdir()
    (project / 'sample.py').write_text(
        'def compute(value):\n    return value + 1\n\n\ndef caller():\n    return compute(1) + compute(2)\n'
    )
    return project


def test_real_preflight_ready(plan_context, tmp_path):
    project = _sample_project(tmp_path)
    _configure(project)
    result = client.cmd_preflight(parse_ns('plan-marshall', 'lsp-client', 'lsp_client.py', 'preflight', '--language', 'python', '--project-path', str(project)))
    assert result['state'] == client.STATE_READY  # the reachable sentinel the consumer wiring gates on
    assert result['configured'] is True
    assert result['reachable'] is True


def test_real_document_symbol_and_references(plan_context, tmp_path):
    project = _sample_project(tmp_path)
    _configure(project)
    target = str(project / 'sample.py')

    docsym = client.cmd_lookup(parse_ns('plan-marshall', 'lsp-client', 'lsp_client.py', 'lookup', '--language', 'python', '--project-path', str(project), '--kind', 'document-symbol', '--file', str(target), '--line', '0', '--character', '0'))
    assert docsym['state'] == client.STATE_OK
    assert docsym['provider_count'] == 1
    names = {row['name'] for row in docsym['locations']}
    assert {'compute', 'caller'} <= names

    refs = client.cmd_lookup(parse_ns('plan-marshall', 'lsp-client', 'lsp_client.py', 'lookup', '--language', 'python', '--project-path', str(project), '--kind', 'references', '--file', str(target), '--line', '0', '--character', '4'))
    assert refs['provider_count'] == 1
    assert refs['location_count'] >= 2  # definition + two call sites


def test_real_workspace_symbol_after_indexing(plan_context, tmp_path):
    project = _sample_project(tmp_path)
    _configure(project)
    result = client.cmd_lookup(parse_ns('plan-marshall', 'lsp-client', 'lsp_client.py', 'lookup', '--language', 'python', '--project-path', str(project), '--kind', 'workspace-symbol', '--line', '0', '--character', '0', '--symbol', 'compute'))
    assert result['state'] == client.STATE_OK
    assert result['provider_count'] == 1
    assert result['location_count'] >= 1
    assert any(row['name'] == 'compute' for row in result['locations'])


def test_real_workspace_symbol_rows_name_the_defining_file(plan_context, tmp_path):
    """The cross-file lookup answers *which file*, over a module the call never opens."""
    project = _sample_project(tmp_path)
    defining = project / 'other.py'
    defining.write_text('class WidgetFromOtherModule:\n    def spin(self):\n        return 1\n')
    _configure(project)

    result = client.cmd_lookup(parse_ns('plan-marshall', 'lsp-client', 'lsp_client.py', 'lookup', '--language', 'python', '--project-path', str(project), '--kind', 'workspace-symbol', '--line', '0', '--character', '0', '--symbol', 'WidgetFromOtherModule'))

    assert result['state'] == client.STATE_OK
    matches = [row for row in result['locations'] if row['name'] == 'WidgetFromOtherModule']
    assert matches, f'workspace-symbol found nothing: {result}'
    for row in matches:
        assert row['path'] == str(defining.resolve())


def test_real_document_symbol_flattens_a_class_and_carries_its_path(plan_context, tmp_path):
    """A class's methods are present, with the queried file on every row."""
    project = _sample_project(tmp_path)
    target = project / 'widget.py'
    target.write_text('class Widget:\n    def spin(self):\n        return 1\n\n    def stop(self):\n        return 2\n\n\ndef top_level():\n    return 3\n')
    _configure(project)

    result = client.cmd_lookup(parse_ns('plan-marshall', 'lsp-client', 'lsp_client.py', 'lookup', '--language', 'python', '--project-path', str(project), '--kind', 'document-symbol', '--file', str(target), '--line', '0', '--character', '0'))

    by_name = {row['name']: row for row in result['locations']}
    assert {'Widget', 'spin', 'stop', 'top_level'} <= set(by_name)
    assert by_name['spin']['line'] == 1
    assert by_name['spin']['container'] == 'Widget'
    for row in result['locations']:
        assert row['path'] == str(target.resolve())


def test_real_clean_rename_edit(plan_context, tmp_path):
    project = _sample_project(tmp_path)
    _configure(project)
    target = project / 'sample.py'
    result = client.cmd_edit(parse_ns('plan-marshall', 'lsp-client', 'lsp_client.py', 'edit', '--language', 'python', '--project-path', str(project), '--file', str(target), '--line', '0', '--character', '4', '--new-name', 'renamed'))
    assert result['status'] == 'success'
    assert result['applied'] is True
    assert result['file_count'] == 1
    text = target.read_text()
    assert 'renamed(' in text
    assert 'compute' not in text


def test_real_adversarial_defect_fails_and_rolls_back(plan_context, tmp_path):
    """A defect introduced through the WorkspaceEdit path must fail the re-diagnose."""
    project = _sample_project(tmp_path)
    target = project / 'sample.py'
    original = target.read_text()

    transport = StdioTransport([_PYRIGHT, '--stdio'], cwd=str(project))
    session = LspSession(transport, str(project))
    try:
        session.initialize()
        session.open(str(target))
        before = session.diagnostics(str(target))
        assert before is not None  # the real server DID publish a baseline verdict
        errors_before = count_error_diagnostics(before)

        # Replace a valid line with a reference to an undefined symbol.
        defect = {'documentChanges': [{
            'textDocument': {'uri': path_to_uri(target), 'version': 2},
            'edits': [{'range': {'start': {'line': 1, 'character': 4}, 'end': {'line': 1, 'character': 20}},
                       'newText': 'return undefined_symbol_xyz'}],
        }]}
        _footprint, originals = apply_workspace_edit(defect)
        seq_before_change = session.change_to_disk(str(target))
        after = session.diagnostics(str(target), after_seq=seq_before_change)
        assert after is not None  # a verdict about the EDITED content, not the cached one
        errors_after = count_error_diagnostics(after)

        assert errors_after > errors_before  # the real parser caught the defect
        added, _removed = diagnostic_delta(before, after)
        assert added  # the defect is in the ADDED set, not merely in a larger count
        assert edit_verdict({str(target): added}) == 'failed'

        restore_files(originals)
        assert target.read_text() == original
    finally:
        session.close()
