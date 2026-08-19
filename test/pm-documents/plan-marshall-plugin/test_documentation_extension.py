#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the pm-documents extension's three faces.

- **Axis-A** (discovery): the ``documentation`` module is discovered for a project
  whose docs are NESTED — the recursive-detection fix, the whole reason the
  documentation domain's discovery seat is no longer inert in a nested-doc repo.
- **Axis-D** (attribution): the doc corpus and repo-root prose docs are claimed for
  ``documentation``; the agent-instruction files (``CLAUDE.md`` / ``AGENTS.md``) are
  deliberately NOT.
- **Axis-C** (derivation): the resolver reports a broken reference and derives an
  edge for a resolved cross-module one, scoped to documentation modules, reading no
  file at resolve time.
"""

import builtins

from extension_base import DerivationResolverBase, ExtensionBase, PathAttributionBase

from conftest import load_skill_module


def _load_documentation_extension():
    """Load the pm-documents Extension by explicit path (every bundle shares the
    ``extension`` basename, so a bare import would collide)."""
    return load_skill_module(
        'pm-documents', 'plan-marshall-plugin', 'extension.py', 'pm_documents_extension'
    )


_extension_module = _load_documentation_extension()
Extension = _extension_module.Extension


def _write(root, rel, text):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding='utf-8')
    return p


# --------------------------------------------------------------------------- #
# Multiple-inheritance opt-in
# --------------------------------------------------------------------------- #


def test_extension_opts_into_all_three_axes():
    ext = Extension()
    assert isinstance(ext, ExtensionBase)
    assert isinstance(ext, PathAttributionBase)
    assert isinstance(ext, DerivationResolverBase)


# --------------------------------------------------------------------------- #
# Axis-A: recursive discovery
# --------------------------------------------------------------------------- #


def test_discovers_documentation_module_for_nested_docs(tmp_path):
    # No top-level doc file — only a nested one. The old non-recursive glob
    # returned [] here; recursive detection must find it.
    _write(tmp_path, 'doc/concepts/intro.adoc', '= Intro\n')
    modules = Extension().discover_modules(str(tmp_path))
    assert len(modules) == 1
    module = modules[0]
    assert module['name'] == 'documentation'
    assert module['paths']['module'] == 'doc'
    assert 'documentation' in module['build_systems']
    assert 'component_refs' in module


def test_no_documentation_module_without_docs(tmp_path):
    (tmp_path / 'src').mkdir()
    assert Extension().discover_modules(str(tmp_path)) == []


def test_discovered_component_refs_carry_resolution(tmp_path):
    _write(tmp_path, 'doc/a.adoc', 'xref:b.adoc[ok] and xref:gone.adoc[broken]\n')
    _write(tmp_path, 'doc/b.adoc', '= B\n')
    modules = Extension().discover_modules(str(tmp_path))
    refs = modules[0]['component_refs']
    assert any(r['resolved'] for r in refs)
    assert any(r['resolved'] is False for r in refs)


# --------------------------------------------------------------------------- #
# Axis-D: path attribution
# --------------------------------------------------------------------------- #


def test_attributor_id():
    assert Extension().path_attributor_id() == 'documentation'


def test_claims_doc_corpus_and_prose_but_not_agent_files():
    claims, notes = Extension().claim_paths()
    prefixes = {prefix for prefix, _module in claims}
    assert ('doc', 'documentation') in claims
    assert ('README.md', 'documentation') in claims
    assert ('CONTRIBUTING.md', 'documentation') in claims
    # Agent-instruction files are per-file EXCLUDED — not swept in by a root glob.
    assert 'CLAUDE.md' not in prefixes
    assert 'AGENTS.md' not in prefixes
    # Every claim names the documentation module.
    assert all(module == 'documentation' for _prefix, module in claims)
    assert notes == []


# --------------------------------------------------------------------------- #
# Axis-C: derivation resolver
# --------------------------------------------------------------------------- #


def test_resolver_id():
    assert Extension().derivation_resolver_id() == 'documentation'


def _doc_module(refs):
    return {'build_systems': ['documentation'], 'component_refs': refs}


def test_resolved_cross_module_reference_becomes_edge():
    derived = {
        'documentation': _doc_module([{'target_bundle': 'plan-marshall', 'dep_type': 'path', 'resolved': True}]),
        'plan-marshall': {'build_systems': ['python']},
    }
    edges, notes = Extension().derive_edges(derived, {})
    assert ('documentation', 'plan-marshall') in edges
    assert notes == []


def test_unresolved_reference_is_reported_not_edged():
    derived = {
        'documentation': _doc_module([{'target_bundle': 'documentation', 'dep_type': 'path', 'resolved': False}]),
    }
    edges, notes = Extension().derive_edges(derived, {})
    assert edges == []
    assert any('unresolved-target' in note for note in notes)


def test_self_reference_is_suppressed_and_reported():
    derived = {
        'documentation': _doc_module([{'target_bundle': 'documentation', 'dep_type': 'path', 'resolved': True}]),
    }
    edges, notes = Extension().derive_edges(derived, {})
    assert edges == []
    assert any('self-edge' in note for note in notes)


def test_unknown_endpoint_is_reported():
    derived = {
        'documentation': _doc_module([{'target_bundle': 'nowhere', 'dep_type': 'path', 'resolved': True}]),
    }
    edges, notes = Extension().derive_edges(derived, {})
    assert edges == []
    assert any('unknown-endpoint' in note for note in notes)


def test_resolver_ignores_non_documentation_modules():
    # A marketplace bundle's own 'path' refs belong to the markdown resolver; this
    # resolver is scoped to documentation modules and must not double-derive them.
    derived = {
        'pm-dev-java': {
            'build_systems': ['python'],
            'component_refs': [{'target_bundle': 'plan-marshall', 'dep_type': 'path', 'resolved': True}],
        },
        'plan-marshall': {'build_systems': ['python']},
    }
    edges, notes = Extension().derive_edges(derived, {})
    assert edges == []
    assert notes == []


def test_derive_edges_reads_no_file(monkeypatch):
    # Purity: the Axis-C contract forbids filesystem access at resolve time.
    def _forbidden(*_a, **_k):
        raise AssertionError('derive_edges must not open a file')

    monkeypatch.setattr(builtins, 'open', _forbidden)
    derived = {
        'documentation': _doc_module([{'target_bundle': 'plan-marshall', 'dep_type': 'path', 'resolved': True}]),
        'plan-marshall': {'build_systems': ['python']},
    }
    edges, _notes = Extension().derive_edges(derived, {})
    assert ('documentation', 'plan-marshall') in edges
