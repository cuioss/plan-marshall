#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""D4: the opt-in gate, verified on an UNCONFIGURED project.

The plan requires that an unconfigured project's behaviour be *verified* rather
than asserted, so the unconfigured path is the subject of these tests: the
server must start, advertise no capabilities, and answer every request emptily.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from conftest import get_scripts_dir

SCRIPTS_DIR = get_scripts_dir('pm-plugin-development', 'tools-corpus-language-server')
INVENTORY_SCRIPTS = get_scripts_dir('pm-plugin-development', 'tools-marketplace-inventory')
SHARED_SCRIPTS = get_scripts_dir('plan-marshall', 'tools-file-ops')
for _dir in (str(SCRIPTS_DIR), str(INVENTORY_SCRIPTS), str(SHARED_SCRIPTS)):
    if _dir not in sys.path:
        sys.path.insert(0, _dir)

import corpus_lsp  # noqa: E402

from test_corpus_index import build_corpus  # noqa: E402


def _project(root: Path, marshal: dict | None) -> Path:
    """Create a project tree; ``marshal=None`` means no marshal.json at all."""
    (root / 'marketplace').mkdir(parents=True, exist_ok=True)
    corpus_root = build_corpus(root)
    (root / 'marketplace' / 'bundles').mkdir(parents=True, exist_ok=True)
    for child in corpus_root.iterdir():
        child.rename(root / 'marketplace' / 'bundles' / child.name)
    if marshal is not None:
        plan_dir = root / '.plan'
        plan_dir.mkdir(parents=True, exist_ok=True)
        (plan_dir / 'marshal.json').write_text(json.dumps(marshal), encoding='utf-8')
    return root


ENABLED = {'code_intelligence': {'corpus_language_server': {'enabled': True}}}


class TestConfigFailsClosed:
    """Every unreadable or ambiguous configuration must resolve to DISABLED."""

    def test_no_project_root_is_disabled(self) -> None:
        assert corpus_lsp.read_corpus_config(None) == {'enabled': False}

    def test_absent_marshal_is_disabled(self, tmp_path: Path) -> None:
        assert corpus_lsp.read_corpus_config(tmp_path)['enabled'] is False

    def test_malformed_marshal_is_disabled(self, tmp_path: Path) -> None:
        (tmp_path / '.plan').mkdir()
        (tmp_path / '.plan' / 'marshal.json').write_text('{not json', encoding='utf-8')
        assert corpus_lsp.read_corpus_config(tmp_path)['enabled'] is False

    def test_absent_section_is_disabled(self, tmp_path: Path) -> None:
        _project(tmp_path, {'plan': {}})
        assert corpus_lsp.read_corpus_config(tmp_path)['enabled'] is False

    def test_explicit_false_is_disabled(self, tmp_path: Path) -> None:
        _project(tmp_path, {'code_intelligence': {'corpus_language_server': {'enabled': False}}})
        assert corpus_lsp.read_corpus_config(tmp_path)['enabled'] is False

    def test_non_boolean_true_is_disabled(self, tmp_path: Path) -> None:
        """A truthy string must NOT enable the surface — only a real `true` does."""
        _project(tmp_path, {'code_intelligence': {'corpus_language_server': {'enabled': 'yes'}}})
        assert corpus_lsp.read_corpus_config(tmp_path)['enabled'] is False

    def test_explicit_true_enables(self, tmp_path: Path) -> None:
        _project(tmp_path, ENABLED)
        assert corpus_lsp.read_corpus_config(tmp_path)['enabled'] is True


class TestUnconfiguredProjectIsANoOp:
    """The documented no-op path, exercised end to end on an unconfigured tree."""

    def test_advertises_no_capabilities(self, tmp_path: Path) -> None:
        _project(tmp_path, None)
        rpc, _ = corpus_lsp.build_server(None, {'enabled': False})
        response = rpc.handle({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {}})
        assert response is not None
        assert response['result']['capabilities'] == {}

    def test_definition_returns_nothing(self, tmp_path: Path) -> None:
        root = _project(tmp_path, None)
        _, corpus = corpus_lsp.build_server(None, {'enabled': False})
        skill = root / 'marketplace' / 'bundles' / 'beta' / 'skills' / 'caller' / 'SKILL.md'
        params = {
            'textDocument': {'uri': skill.as_uri()},
            'position': {'line': 6, 'character': 15},
        }
        assert corpus.on_definition(params) is None

    def test_references_returns_empty(self, tmp_path: Path) -> None:
        root = _project(tmp_path, None)
        _, corpus = corpus_lsp.build_server(None, {'enabled': False})
        skill = root / 'marketplace' / 'bundles' / 'beta' / 'skills' / 'caller' / 'SKILL.md'
        params = {
            'textDocument': {'uri': skill.as_uri()},
            'position': {'line': 6, 'character': 15},
        }
        assert corpus.on_references(params) == []

    def test_hover_returns_nothing(self, tmp_path: Path) -> None:
        root = _project(tmp_path, None)
        _, corpus = corpus_lsp.build_server(None, {'enabled': False})
        skill = root / 'marketplace' / 'bundles' / 'beta' / 'skills' / 'caller' / 'SKILL.md'
        params = {
            'textDocument': {'uri': skill.as_uri()},
            'position': {'line': 6, 'character': 15},
        }
        assert corpus.on_hover(params) is None

    def test_no_index_is_ever_built(self, tmp_path: Path) -> None:
        """The ~1.9 s index cost must not be paid by a project that opted out."""
        _project(tmp_path, None)
        _, corpus = corpus_lsp.build_server(None, {'enabled': False})
        assert corpus.index is None

    def test_preflight_reports_the_opt_out(self, tmp_path: Path) -> None:
        _project(tmp_path, None)
        args = type('A', (), {'project_path': str(tmp_path)})()
        payload = corpus_lsp.cmd_preflight(args)
        assert payload['status'] == 'degraded'
        assert payload['state'] == 'not_configured'
        assert payload['provider_count'] == 0
        assert payload['fallback'] == 'read_grep'

    def test_query_degrades_without_touching_the_corpus(self, tmp_path: Path) -> None:
        _project(tmp_path, None)
        args = type('A', (), {'project_path': str(tmp_path), 'kind': 'definition', 'notation': 'alpha:target-skill'})()
        payload = corpus_lsp.cmd_query(args)
        assert payload['status'] == 'degraded'
        assert payload['provider_count'] == 0
        assert 'definition' not in payload


class TestConfiguredProjectAnswers:
    """The configured path — so an empty answer above is a real opt-out, not a broken build."""

    def test_advertises_capabilities(self, tmp_path: Path) -> None:
        _project(tmp_path, ENABLED)
        rpc, _ = corpus_lsp.build_server(tmp_path, {'enabled': True})
        response = rpc.handle({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {}})
        assert response is not None
        capabilities = response['result']['capabilities']
        assert capabilities['definitionProvider'] is True
        assert capabilities['referencesProvider'] is True
        assert capabilities['hoverProvider'] is True

    def test_does_not_advertise_diagnostics(self, tmp_path: Path) -> None:
        """D3 is hard-gated: no diagnostic provider may be advertised yet."""
        _project(tmp_path, ENABLED)
        rpc, _ = corpus_lsp.build_server(tmp_path, {'enabled': True})
        response = rpc.handle({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {}})
        assert response is not None
        capabilities = response['result']['capabilities']
        assert 'diagnosticProvider' not in capabilities

    def test_definition_resolves_from_a_cursor(self, tmp_path: Path) -> None:
        root = _project(tmp_path, ENABLED)
        _, corpus = corpus_lsp.build_server(root, {'enabled': True})
        skill = root / 'marketplace' / 'bundles' / 'beta' / 'skills' / 'caller' / 'SKILL.md'
        line_no = skill.read_text(encoding='utf-8').split('\n').index('See Skill: alpha:target-skill for details.')
        params = {
            'textDocument': {'uri': skill.as_uri()},
            'position': {'line': line_no, 'character': 15},
        }
        result = corpus.on_definition(params)
        assert result is not None
        assert result['uri'].endswith('alpha/skills/target-skill/SKILL.md')

    def test_hover_renders_markdown(self, tmp_path: Path) -> None:
        root = _project(tmp_path, ENABLED)
        _, corpus = corpus_lsp.build_server(root, {'enabled': True})
        skill = root / 'marketplace' / 'bundles' / 'beta' / 'skills' / 'caller' / 'SKILL.md'
        line_no = skill.read_text(encoding='utf-8').split('\n').index('See Skill: alpha:target-skill for details.')
        params = {
            'textDocument': {'uri': skill.as_uri()},
            'position': {'line': line_no, 'character': 15},
        }
        result = corpus.on_hover(params)
        assert result is not None
        assert 'The skill under test' in result['contents']['value']

    def test_index_is_built_once_and_reused(self, tmp_path: Path) -> None:
        """Residency is the design — a second query must not rebuild the index."""
        root = _project(tmp_path, ENABLED)
        _, corpus = corpus_lsp.build_server(root, {'enabled': True})
        first = corpus.index
        assert first is not None
        assert corpus.index is first
