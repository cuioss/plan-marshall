#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the persisted architecture store's concept model.

Covers the four deliverables of ``150-architecture-store-concept-model``:

* **D1 — path is identity.** Package-entry keys are repo-relative paths; a
  non-resolving key is refused at write time; legacy dotted keys migrate to
  paths on read via the derived packages bridge.
* **D2 — a required, closed ``type``.** Every concept document carries a
  validated type; an unknown type is refused at write time and on read; a
  pre-field document migrates deterministically to ``module``.
* **D3 — the root index carries descriptions** without becoming the discovery
  gatekeeper (a module on disk but absent from the index is still discovered).
* **D4 — generation provenance and freshness.** Every document records who
  generated it and the tree it was generated against; a staleness verdict is
  derived from the tree identifier (not mtime) from the header alone.

Every store-shape claim is verified against the WRITER and against fixtures —
the live store lives under the git-ignored ``.plan/`` tree and is not reachable
from a clone.
"""

import argparse
import json
import sys
import tempfile
from pathlib import Path

import pytest

from conftest import load_script_module

sys.path.insert(0, str(Path(__file__).parent))

from _arch_fixtures import setup_test_project  # noqa: E402


_architecture_core = load_script_module(
    'plan-marshall', 'manage-architecture', '_architecture_core.py', '_architecture_core'
)
_cmd_manage = load_script_module('plan-marshall', 'manage-architecture', '_cmd_manage.py', '_cmd_manage')
_cmd_enrich = load_script_module('plan-marshall', 'manage-architecture', '_cmd_enrich.py', '_cmd_enrich')
_cmd_client_query = load_script_module(
    'plan-marshall', 'manage-architecture', '_cmd_client_query.py', '_cmd_client_query'
)

InvalidConceptTypeError = _architecture_core.InvalidConceptTypeError
NonResolvingPathKeyError = _architecture_core.NonResolvingPathKeyError

CONCEPT_TYPES = _architecture_core.CONCEPT_TYPES
migrate_concept_document = _architecture_core.migrate_concept_document
validate_concept_type = _architecture_core.validate_concept_type
build_generation = _architecture_core.build_generation
derive_freshness = _architecture_core.derive_freshness
migrate_key_packages = _architecture_core.migrate_key_packages
package_key_resolves = _architecture_core.package_key_resolves
validate_package_key = _architecture_core.validate_package_key

save_module_enriched = _architecture_core.save_module_enriched
load_module_enriched = _architecture_core.load_module_enriched
save_module_derived = _architecture_core.save_module_derived
save_project_meta = _architecture_core.save_project_meta
load_project_meta = _architecture_core.load_project_meta
merge_module_data = _architecture_core.merge_module_data
get_module_enriched_path = _architecture_core.get_module_enriched_path
iter_modules = _architecture_core.iter_modules
invalidate_crawl_cache = _architecture_core.invalidate_crawl_cache

api_discover = _cmd_manage.api_discover
_empty_module_enrichment = _cmd_manage._empty_module_enrichment

enrich_package = _cmd_enrich.enrich_package
cmd_enrich_package = _cmd_enrich.cmd_enrich_package

get_project_info = _cmd_client_query.get_project_info


# =============================================================================
# D2 — a required, closed, validated concept ``type``
# =============================================================================


def test_empty_stub_carries_module_type():
    """The seeded empty stub declares ``type: module`` — every concept doc has a type."""
    assert _empty_module_enrichment()['type'] == 'module'


def test_save_stamps_module_type_when_absent():
    """Saving a document without a type fills the module default (deterministic)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        save_module_enriched('mod', {'responsibility': 'R'}, tmpdir)
        assert load_module_enriched('mod', tmpdir)['type'] == 'module'


def test_save_refuses_unknown_type():
    """An unknown ``type`` is refused at write time (fail-closed)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with pytest.raises(InvalidConceptTypeError):
            save_module_enriched('mod', {'type': 'bogus', 'responsibility': 'R'}, tmpdir)


def test_load_migrates_pre_field_document():
    """A pre-field document (no ``type``) migrates deterministically to ``module`` on read.

    This is the first of the three migration states the plan pins: a document
    written before the field existed produces the NAMED outcome (migrate to
    ``module``), never a silent, indistinguishable default.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        path = get_module_enriched_path('mod', tmpdir)
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({'responsibility': 'R'}), encoding='utf-8')

        assert load_module_enriched('mod', tmpdir)['type'] == 'module'


def test_load_of_migrated_document_keeps_its_type():
    """The second migration state: a document already carrying a valid type is kept."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = get_module_enriched_path('mod', tmpdir)
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({'type': 'skill', 'responsibility': 'R'}), encoding='utf-8')

        assert load_module_enriched('mod', tmpdir)['type'] == 'skill'


def test_load_refuses_unknown_type_document():
    """The third migration state: a document with an unknown type is refused on read."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = get_module_enriched_path('mod', tmpdir)
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({'type': 'bogus', 'responsibility': 'R'}), encoding='utf-8')

        with pytest.raises(InvalidConceptTypeError):
            load_module_enriched('mod', tmpdir)


def test_migrate_concept_document_three_states():
    """The named migration in one place: absent → module, valid → kept, unknown → refused."""
    assert migrate_concept_document({'responsibility': 'R'})['type'] == 'module'
    assert migrate_concept_document({'type': 'standard'})['type'] == 'standard'
    with pytest.raises(InvalidConceptTypeError):
        migrate_concept_document({'type': 'bogus'})


def test_migrate_concept_document_does_not_mutate_caller():
    """The migration returns a copy — the caller's dict is never mutated in place."""
    original = {'responsibility': 'R'}
    migrated = migrate_concept_document(original)
    assert 'type' not in original
    assert migrated is not original


def test_vocabulary_is_closed_and_enumerated_once():
    """The accepted set is enumerated in one place and holds more than modules."""
    assert 'module' in CONCEPT_TYPES
    assert {'skill', 'script', 'standard', 'decision_record'} <= CONCEPT_TYPES


def test_refusal_message_names_the_accepted_set():
    """The refusal names the accepted vocabulary, so it is actionable."""
    with pytest.raises(InvalidConceptTypeError) as exc:
        validate_concept_type('bogus')
    message = str(exc.value)
    for accepted in ('module', 'skill', 'script', 'standard', 'decision_record'):
        assert accepted in message


# =============================================================================
# D4 — generation provenance and tree-derived freshness
# =============================================================================


def test_save_stamps_generation_header():
    """Every write stamps a generation header recording who and against which tree."""
    with tempfile.TemporaryDirectory() as tmpdir:
        save_module_enriched('mod', {'responsibility': 'R'}, tmpdir)
        generation = load_module_enriched('mod', tmpdir)['generation']
        assert generation['by'] == 'architecture'
        # A non-git tmpdir has no resolvable tree; the key is present and null.
        assert 'tree_sha' in generation


def test_build_generation_shape():
    """The generation header carries exactly the provenance keys (who + tree)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        generation = build_generation(tmpdir)
        assert set(generation) == {'by', 'tree_sha'}
        assert generation['by'] == 'architecture'


def test_derive_freshness_fresh_on_matching_tree():
    """A document generated against the current tree is fresh."""
    assert derive_freshness({'by': 'architecture', 'tree_sha': 'TREE-A'}, 'TREE-A') == 'fresh'


def test_derive_freshness_stale_on_different_tree():
    """A document generated against a different tree is reported stale."""
    assert derive_freshness({'by': 'architecture', 'tree_sha': 'TREE-A'}, 'TREE-B') == 'stale'


def test_derive_freshness_unknown_when_sha_absent():
    """Absent provenance never reads as fresh — the verdict is unknown (fail-closed)."""
    assert derive_freshness({'tree_sha': None}, 'TREE-A') == 'unknown'
    assert derive_freshness({}, 'TREE-A') == 'unknown'
    assert derive_freshness(None, 'TREE-A') == 'unknown'
    assert derive_freshness({'tree_sha': 'TREE-A'}, None) == 'unknown'


def test_freshness_verdict_derived_from_header_alone():
    """The staleness verdict is obtainable from the index header — no concept body.

    The plan's D4 verification: the verdict must be readable without parsing the
    concept body. Here the verdict comes from a bare index-entry generation
    header; there is no ``enriched.json`` on disk to read at all.
    """
    index_entry = {'description': 'Handles A', 'generation': {'by': 'architecture', 'tree_sha': 'TREE-A'}}
    assert derive_freshness(index_entry['generation'], 'TREE-A') == 'fresh'
    assert derive_freshness(index_entry['generation'], 'TREE-B') == 'stale'


def test_info_surfaces_freshness_from_index(monkeypatch):
    """``info`` surfaces per-module description + freshness read from the index header."""
    with tempfile.TemporaryDirectory() as tmpdir:
        invalidate_crawl_cache()
        save_module_derived('mod', {'name': 'mod', 'build_systems': ['maven'], 'paths': {'module': 'mod'}}, tmpdir)
        save_project_meta(
            {
                'name': 'p',
                'description': '',
                'extensions_used': [],
                'modules': {
                    'mod': {'description': 'Does things', 'generation': {'by': 'architecture', 'tree_sha': 'TREE-A'}}
                },
            },
            tmpdir,
        )

        monkeypatch.setattr(_cmd_client_query, 'current_worktree_sha', lambda _pd: 'TREE-A')
        row = next(m for m in get_project_info(tmpdir)['modules'] if m['name'] == 'mod')
        assert row['description'] == 'Does things'
        assert row['freshness'] == 'fresh'

        # A moved tree flips the same header's verdict to stale — no re-read of the body.
        monkeypatch.setattr(_cmd_client_query, 'current_worktree_sha', lambda _pd: 'TREE-B')
        row = next(m for m in get_project_info(tmpdir)['modules'] if m['name'] == 'mod')
        assert row['freshness'] == 'stale'


# =============================================================================
# D3 — root index carries descriptions, without becoming the gatekeeper
# =============================================================================


def _fake_single_module(_project_root):
    return {
        'modules': {
            'module-a': {
                'name': 'module-a',
                'build_systems': ['maven'],
                'paths': {'module': 'module-a'},
                'metadata': {},
                'packages': {},
                'dependencies': [],
                'stats': {},
                'commands': {},
            }
        },
        'extensions_used': [],
    }


def test_discover_index_carries_description_and_generation(monkeypatch):
    """After discover, the root index entry mirrors the module's description + generation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # A curated responsibility exists before discover; discover mirrors it.
        save_module_enriched('module-a', {'responsibility': 'Handles A'}, tmpdir)

        import extension_discovery

        monkeypatch.setattr(extension_discovery, 'discover_project_modules', _fake_single_module)
        api_discover(tmpdir, force=True)

        entry = load_project_meta(tmpdir)['modules']['module-a']
        assert entry['description'] == 'Handles A'
        assert entry['generation']  # non-empty header mirrored from the concept document


def test_discover_index_description_defaults_empty_for_fresh_module(monkeypatch):
    """A first-seen module with no responsibility still gets an index entry (empty description)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        import extension_discovery

        monkeypatch.setattr(extension_discovery, 'discover_project_modules', _fake_single_module)
        api_discover(tmpdir, force=True)

        entry = load_project_meta(tmpdir)['modules']['module-a']
        assert entry['description'] == ''
        assert entry['generation']['tree_sha'] is not None or entry['generation']['by'] == 'architecture'


def test_module_on_disk_absent_from_index_is_still_discovered():
    """D3 negative control: the index is NOT the discovery gatekeeper.

    A module present on disk (a ``derived.json`` under project-architecture) but
    absent from ``_project.json``'s ``modules`` index is still discovered — the
    crawl reads the live filesystem, never the index. Adding descriptions to the
    index must not regress this.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        invalidate_crawl_cache()
        # The index lists NO modules ...
        save_project_meta({'name': 'p', 'description': '', 'extensions_used': [], 'modules': {}}, tmpdir)
        # ... but a module exists on disk.
        save_module_derived('orphan', {'name': 'orphan', 'paths': {'module': 'orphan'}}, tmpdir)

        assert 'orphan' in iter_modules(tmpdir)


# =============================================================================
# D1 — path is identity for package entries
# =============================================================================


def test_enrich_package_refuses_non_resolving_key():
    """A non-resolving package key (a dotted pseudo-identifier) is refused at write time."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)
        with pytest.raises(NonResolvingPathKeyError):
            enrich_package('module-a', 'de.cuioss.does.not.exist', 'X', tmpdir)


def test_enrich_package_accepts_resolving_path_key():
    """A key that resolves to a real filesystem location is accepted and persisted by path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)
        (Path(tmpdir) / 'module-a' / 'src').mkdir(parents=True)

        result = enrich_package('module-a', 'module-a/src', 'Source directory', tmpdir)

        assert result['status'] == 'success'
        assert 'module-a/src' in load_module_enriched('module-a', tmpdir)['key_packages']


def test_cmd_enrich_package_returns_named_error_for_non_resolving_key():
    """The CLI handler surfaces a NAMED error code rather than a bare failure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        setup_test_project(tmpdir)
        args = argparse.Namespace(
            module='module-a', package='de.cuioss.nope', description='X', project_dir=tmpdir, components=None
        )
        result = cmd_enrich_package(args)

        assert result['status'] == 'error'
        assert result['error'] == 'non_resolving_package_key'


def test_package_key_resolves_rejects_absolute_and_traversal():
    """Absolute paths and traversal never resolve — a key is a repo-relative location."""
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / 'pkg').mkdir()
        assert package_key_resolves('pkg', tmpdir) is True
        assert package_key_resolves('/etc', tmpdir) is False
        assert package_key_resolves('../pkg', tmpdir) is False
        assert package_key_resolves('missing', tmpdir) is False


def test_validate_package_key_returns_key_when_resolving():
    """The write gate returns the key unchanged when it resolves (chaining contract)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / 'pkg').mkdir()
        assert validate_package_key('pkg', tmpdir) == 'pkg'


def test_migrate_key_packages_rewrites_dotted_to_path():
    """A legacy dotted key is rewritten to its path via the derived packages bridge."""
    key_packages = {'com.example.pkg': {'description': 'D'}}
    derived_packages = {'com.example.pkg': {'path': 'src/pkg'}}

    migrated, unresolved = migrate_key_packages(key_packages, derived_packages, '.')

    assert 'src/pkg' in migrated
    assert 'com.example.pkg' not in migrated
    assert unresolved == []


def test_migrate_key_packages_reports_unresolved_without_dropping():
    """A dotted key with no bridge is kept under its original key AND reported."""
    key_packages = {'com.orphan': {'description': 'D'}}

    migrated, unresolved = migrate_key_packages(key_packages, {}, '.')

    assert 'com.orphan' in migrated
    assert unresolved == ['com.orphan']


def test_merge_module_data_migrates_dotted_key_packages():
    """merge_module_data rewrites legacy dotted key_packages keys to path identity on read."""
    with tempfile.TemporaryDirectory() as tmpdir:
        invalidate_crawl_cache()
        save_module_derived(
            'mod',
            {'name': 'mod', 'paths': {'module': 'mod'}, 'packages': {'com.example.pkg': {'path': 'mod/src/pkg'}}},
            tmpdir,
        )
        save_project_meta({'name': 'p', 'description': '', 'extensions_used': [], 'modules': {'mod': {}}}, tmpdir)
        save_module_enriched('mod', {'key_packages': {'com.example.pkg': {'description': 'D'}}}, tmpdir)

        merged = merge_module_data('mod', tmpdir)

        assert 'mod/src/pkg' in merged['key_packages']
        assert 'com.example.pkg' not in merged['key_packages']
