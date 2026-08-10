#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
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

import argparse
import json
import shutil
import sys
from pathlib import Path

import pytest
from conftest import get_script_path

SCRIPT_PATH = get_script_path('plan-marshall', 'lsp-client', 'lsp_client.py')
SCRIPTS_DIR = SCRIPT_PATH.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import lsp_client as client  # noqa: E402
import run_config  # noqa: E402
from _lsp_jsonrpc import LspSession, StdioTransport  # noqa: E402
from _lsp_workspace_edit import (  # noqa: E402
    apply_workspace_edit,
    count_error_diagnostics,
    edit_verdict,
    path_to_uri,
    restore_files,
)

_PYRIGHT = shutil.which('pyright-langserver')
pytestmark = pytest.mark.skipif(_PYRIGHT is None, reason='pyright-langserver not installed')


def _configure(project: Path) -> None:
    run_config.cmd_language_server_set(argparse.Namespace(
        language='python', command=json.dumps([_PYRIGHT, '--stdio']), language_id='python', disabled=False))


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
    result = client.cmd_preflight(argparse.Namespace(language='python', project_path=str(project)))
    assert result['state'] == client.STATE_READY  # the reachable sentinel the consumer wiring gates on
    assert result['configured'] is True
    assert result['reachable'] is True


def test_real_document_symbol_and_references(plan_context, tmp_path):
    project = _sample_project(tmp_path)
    _configure(project)
    target = str(project / 'sample.py')

    docsym = client.cmd_lookup(argparse.Namespace(
        language='python', project_path=str(project), kind='document-symbol',
        file=target, line=0, character=0, symbol=None))
    assert docsym['state'] == client.STATE_OK
    assert docsym['provider_count'] == 1
    names = {row['name'] for row in docsym['locations']}
    assert {'compute', 'caller'} <= names

    refs = client.cmd_lookup(argparse.Namespace(
        language='python', project_path=str(project), kind='references',
        file=target, line=0, character=4, symbol=None))
    assert refs['provider_count'] == 1
    assert refs['location_count'] >= 2  # definition + two call sites


def test_real_workspace_symbol_after_indexing(plan_context, tmp_path):
    project = _sample_project(tmp_path)
    _configure(project)
    result = client.cmd_lookup(argparse.Namespace(
        language='python', project_path=str(project), kind='workspace-symbol',
        file=None, line=0, character=0, symbol='compute'))
    assert result['state'] == client.STATE_OK
    assert result['provider_count'] == 1
    assert result['location_count'] >= 1
    assert any(row['name'] == 'compute' for row in result['locations'])


def test_real_clean_rename_edit(plan_context, tmp_path):
    project = _sample_project(tmp_path)
    _configure(project)
    target = project / 'sample.py'
    result = client.cmd_edit(argparse.Namespace(
        language='python', project_path=str(project), file=str(target),
        line=0, character=4, new_name='renamed'))
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
        errors_before = count_error_diagnostics(session.diagnostics(str(target)))

        # Replace a valid line with a reference to an undefined symbol.
        defect = {'documentChanges': [{
            'textDocument': {'uri': path_to_uri(target), 'version': 2},
            'edits': [{'range': {'start': {'line': 1, 'character': 4}, 'end': {'line': 1, 'character': 20}},
                       'newText': 'return undefined_symbol_xyz'}],
        }]}
        _footprint, originals = apply_workspace_edit(defect)
        session.change_to_disk(str(target))
        errors_after = count_error_diagnostics(session.diagnostics(str(target)))

        assert errors_after > errors_before  # the real parser caught the defect
        assert edit_verdict(errors_before, errors_after) == 'failed'

        restore_files(originals)
        assert target.read_text() == original
    finally:
        session.close()
