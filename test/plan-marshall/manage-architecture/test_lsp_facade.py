#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Tests for the LSP-shaped facade (D1).

The facade is ADDITIVE: it lets a consumer address the query surface in LSP
vocabulary (hover, references, workspace/symbol, definition) without renaming a
single existing verb. Each facade handler is a thin dispatch to the verb it maps
onto, so the defining property is EQUALITY — the facade's answer is byte-for-byte
the underlying verb's answer.

Pinned here:

* **each facade equals its target verb** — hover == module, references == impact,
  workspace-symbol == find, definition == resolve, over the same fixture.
* **the facade genuinely answers** — at least one facade resolves to a real
  ``status: success`` payload, so the equality is not a mirror of two errors.
* **the CLI speaks LSP vocabulary** — ``architecture lsp hover --module M`` parses
  and dispatches through the shipped argparse surface.
* **the residue verbs are unchanged** — the four traversal/inventory verbs the
  facade does NOT replace (path, impact, find, which-module) stay reachable under
  their own names.
"""

import sys
import tempfile
from argparse import Namespace
from pathlib import Path

from conftest import get_script_path, load_script_module, run_script

sys.path.insert(0, str(Path(__file__).parent))

_architecture_core = load_script_module(
    'plan-marshall', 'manage-architecture', '_architecture_core.py', '_architecture_core'
)
_cmd_client = load_script_module('plan-marshall', 'manage-architecture', '_cmd_client.py', '_cmd_client')

save_project_meta = _architecture_core.save_project_meta
save_module_derived = _architecture_core.save_module_derived
save_module_enriched = _architecture_core.save_module_enriched

cmd_module = _cmd_client.cmd_module
cmd_impact = _cmd_client.cmd_impact
cmd_find = _cmd_client.cmd_find
cmd_resolve = _cmd_client.cmd_resolve
cmd_which_module = _cmd_client.cmd_which_module
cmd_path = _cmd_client.cmd_path
cmd_lsp_hover = _cmd_client.cmd_lsp_hover
cmd_lsp_references = _cmd_client.cmd_lsp_references
cmd_lsp_workspace_symbol = _cmd_client.cmd_lsp_workspace_symbol
cmd_lsp_definition = _cmd_client.cmd_lsp_definition

_ARCHITECTURE_SCRIPT = get_script_path('plan-marshall', 'manage-architecture', 'architecture.py')


def _seed_module_project(tmpdir: str) -> None:
    """Seed one real module with a command and a one-file inventory."""
    save_project_meta(
        {
            'name': 'lsp-fixture',
            'description': '',
            'description_reasoning': '',
            'extensions_used': [],
            'modules': {'lib': {}},
        },
        tmpdir,
    )
    save_module_derived(
        'lib',
        {
            'name': 'lib',
            'paths': {'module': 'lib'},
            'dependencies': ['org.example:external:compile'],
            'commands': {'verify': 'python3 verify'},
            'files': {'source': ['lib/core.py']},
        },
        tmpdir,
    )
    save_module_enriched(
        'lib',
        {
            'responsibility': 'The library module',
            'purpose': 'library',
            'key_packages': {},
            'skills_by_profile': {},
            'skills_by_profile_reasoning': '',
        },
        tmpdir,
    )


def test_lsp_hover_equals_module_and_genuinely_answers():
    """``lsp hover`` is the ``module`` verb's answer, unchanged — and it succeeds."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_module_project(tmpdir)

        facade = cmd_lsp_hover(Namespace(project_dir=tmpdir, module='lib', full=False))
        direct = cmd_module(Namespace(project_dir=tmpdir, module='lib', full=False, budget=None))

        assert facade == direct
        # Not a mirror of two errors: the facade genuinely answers.
        assert facade['status'] == 'success'
        assert facade['module']['name'] == 'lib'


def test_lsp_references_equals_impact():
    """``lsp references`` is the ``impact`` verb's answer, unchanged."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_module_project(tmpdir)

        facade = cmd_lsp_references(Namespace(project_dir=tmpdir, module='lib'))
        direct = cmd_impact(Namespace(project_dir=tmpdir, module='lib'))

        assert facade == direct
        assert facade['status'] == 'success'


def test_lsp_workspace_symbol_equals_find():
    """``lsp workspace-symbol --query Q`` is the ``find --pattern Q`` answer, unchanged."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_module_project(tmpdir)

        facade = cmd_lsp_workspace_symbol(
            Namespace(project_dir=tmpdir, query='*core.py', category=None)
        )
        direct = cmd_find(Namespace(project_dir=tmpdir, pattern='*core.py', category=None))

        assert facade == direct
        assert facade['status'] == 'success'
        # The query really matched the inventory path, so the facade answers.
        assert facade['count'] == 1


def test_lsp_definition_equals_resolve():
    """``lsp definition --command C`` is the ``resolve --command C`` answer, unchanged."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_module_project(tmpdir)

        facade = cmd_lsp_definition(Namespace(project_dir=tmpdir, command='verify', module='lib'))
        direct = cmd_resolve(Namespace(project_dir=tmpdir, resolve_command='verify', module='lib'))

        assert facade == direct


def test_cli_speaks_lsp_vocabulary():
    """The shipped CLI dispatches ``lsp hover --module M`` through argparse."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_module_project(tmpdir)

        result = run_script(
            _ARCHITECTURE_SCRIPT, '--project-dir', tmpdir, 'lsp', 'hover', '--module', 'lib'
        )

        assert result.success, result.stderr
        data = result.toon()
        assert data['status'] == 'success'


def test_residue_verbs_remain_reachable_unchanged():
    """The four residue verbs the facade does not replace still answer under their own names."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_module_project(tmpdir)

        # impact / find / which-module / path are untouched by the additive facade.
        assert cmd_impact(Namespace(project_dir=tmpdir, module='lib'))['status'] == 'success'
        assert cmd_find(Namespace(project_dir=tmpdir, pattern='*.py', category=None))['status'] == 'success'
        assert (
            cmd_which_module(Namespace(project_dir=tmpdir, path='lib/core.py'))['status'] == 'success'
        )
        # path over a single module resolves to a singleton (source == target).
        path_result = cmd_path(Namespace(project_dir=tmpdir, source='lib', target='lib'))
        assert path_result['status'] == 'success'
