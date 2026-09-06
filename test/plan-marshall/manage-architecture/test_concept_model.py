#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
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

A final section covers the Axis-D **claimed-path collapse at its two reader call
sites** (``cmd_find`` and ``cmd_search``). The collapse helper itself is unit-
tested in ``test_doc_corpus_dedup.py`` against synthetic rows, which leaves the
CALL SITES uncovered: deleting both invocations keeps every one of those unit
tests green because the helper is still there and still correct in isolation.
The tests here drive the shipped handlers end to end over a seeded project, so a
removed call site reddens.
"""

import argparse
import copy
import json
import re
import tempfile
from pathlib import Path
from typing import Any

import pytest
from _arch_fixtures import seed_project, setup_test_project

from conftest import MARKETPLACE_ROOT, load_script_module, parse_ns

_architecture_core = load_script_module(
    'plan-marshall', 'manage-architecture', '_architecture_core.py', '_architecture_core'
)
_cmd_manage = load_script_module('plan-marshall', 'manage-architecture', '_cmd_manage.py', '_cmd_manage')
_cmd_enrich = load_script_module('plan-marshall', 'manage-architecture', '_cmd_enrich.py', '_cmd_enrich')
_cmd_client_query = load_script_module(
    'plan-marshall', 'manage-architecture', '_cmd_client_query.py', '_cmd_client_query'
)
#: Loaded DIRECTLY (rather than through the ``_cmd_client`` facade) so the
#: attribution stub below patches the very module globals
#: ``_collapse_claimed_duplicate_rows`` reads. Going through the facade would
#: risk patching a different module object than the handler's own globals.
_handlers = load_script_module(
    'plan-marshall', 'manage-architecture', '_cmd_client_handlers.py', '_cmd_client_handlers'
)

InvalidConceptTypeError = _architecture_core.InvalidConceptTypeError
NonResolvingPathKeyError = _architecture_core.NonResolvingPathKeyError

CONCEPT_TYPES = _architecture_core.CONCEPT_TYPES

#: The standard that RESTATES the concept-type vocabulary in prose. It is a second
#: copy of a closed vocabulary, so it can drift from the code constant silently.
_PERSISTENCE_STANDARD = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'manage-architecture'
    / 'standards'
    / 'architecture-persistence.md'
)

#: The STABLE MARKER the parse anchors on — the constant's own name, which the
#: standard cites where it enumerates the vocabulary. Anchoring on the marker
#: rather than on a line number keeps the parse working when the document is
#: reflowed or a section is inserted above it.
_CONCEPT_TYPES_MARKER = 'CONCEPT_TYPES'

#: A backticked lowercase identifier — the spelling the standard uses for each
#: accepted type inside its parenthesised enumeration.
_BACKTICKED_IDENTIFIER = re.compile(r'`([a-z_]+)`')


def _documented_concept_types() -> set[str]:
    """Parse the accepted concept types out of the standard's own enumeration.

    Walks to the first line carrying the ``CONCEPT_TYPES`` marker that also holds a
    parenthesised enumeration of backticked identifiers, and returns those
    identifiers. The document cites the marker in more than one place; the lines
    that merely reference the vocabulary carry no such enumeration and are skipped,
    so the parse lands on the declaring site without depending on its position.

    Raises:
        AssertionError: when no enumeration can be found. A silent empty set would
            make the equality assertion below compare the code constant against
            nothing and pass for the wrong reason.
    """
    for line in _PERSISTENCE_STANDARD.read_text(encoding='utf-8').splitlines():
        if _CONCEPT_TYPES_MARKER not in line:
            continue
        parenthesised = re.search(r'\(([^)]*)\)', line)
        if parenthesised is None:
            continue
        names = set(_BACKTICKED_IDENTIFIER.findall(parenthesised.group(1)))
        if names:
            return names
    raise AssertionError(
        f'no parenthesised concept-type enumeration found beside a '
        f'{_CONCEPT_TYPES_MARKER!r} marker in {_PERSISTENCE_STANDARD} — the '
        f'standard was restructured and this parse must follow it.'
    )


def test_standard_and_code_declare_the_same_concept_type_vocabulary():
    """The standard's restatement is held equal to the shipped constant.

    ``architecture-persistence.md`` restates the ``CONCEPT_TYPES`` vocabulary
    verbatim while the shipped test checked only the code constant, so the two
    copies could diverge without anything noticing: a type added to the code would
    leave the standard documenting a closed set that is no longer closed, and a
    reader obeying the "quote values verbatim from the docs" rule would be led to a
    wrong value rather than merely an incomplete one.

    Set-equality in BOTH directions, so neither an addition nor a removal on either
    side can pass.
    """
    documented = _documented_concept_types()

    # Anti-vacuity: an empty parse would make the comparison meaningless.
    assert documented, 'parsed no concept types out of the standard'
    assert CONCEPT_TYPES, 'the code constant declares no concept types'

    assert documented == set(CONCEPT_TYPES), (
        'the concept-type vocabulary has desynced between the standard and the code. '
        f'Only in {_PERSISTENCE_STANDARD.name}: {sorted(documented - set(CONCEPT_TYPES))}. '
        f'Only in _architecture_core.CONCEPT_TYPES: {sorted(set(CONCEPT_TYPES) - documented)}.'
    )
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

#: The architecture script's address, as module-level string constants so the
#: ``parse_ns`` call below stays statically resolvable.
_ARCH_BUNDLE = 'plan-marshall'
_ARCH_SKILL = 'manage-architecture'
_ARCH_SCRIPT = 'architecture.py'


def _variant(base: argparse.Namespace, **overrides: Any) -> argparse.Namespace:
    """Derive a namespace from the hoisted parser-derived base.

    The base supplies every parser default; ``overrides`` names only the fields
    this call differs in. A shallow copy is enough because a namespace's values
    are the parser's own scalars, and the base must stay unmutated for the other
    callers sharing it.
    """
    derived = copy.copy(base)
    for field, value in overrides.items():
        setattr(derived, field, value)
    return derived


#: The ``enrich package`` namespace, built by ``architecture.py``'s OWN parser
#: so it carries every default the production CLI applies — the ``command`` /
#: ``enrich_command`` discriminators and the ``plan_id`` half of the
#: ``--plan-id``/``--project-dir`` pair among them, none of which the hand-built
#: namespace carried. Hoisted to module scope because ``parse_ns`` re-executes
#: the script module on every call, and ``register=False`` because only the
#: namespace is wanted here.
_ENRICH_PACKAGE_ARGS = parse_ns(
    _ARCH_BUNDLE, _ARCH_SKILL, _ARCH_SCRIPT,
    '--project-dir', '.', 'enrich', 'package',
    '--module', 'module', '--package', 'package', '--description', 'description',
    register=False,
)

#: The ``find`` and ``search`` namespaces, built by the same parser for the same
#: reason — the reader call sites below must run against the defaults the shipped
#: CLI applies, including ``search``'s ``--literal`` / ``--ignore-case``
#: store_true pair.
_FIND_ARGS = parse_ns(
    _ARCH_BUNDLE, _ARCH_SKILL, _ARCH_SCRIPT,
    '--project-dir', '.', 'find', '--pattern', '.',
    register=False,
)

_SEARCH_ARGS = parse_ns(
    _ARCH_BUNDLE, _ARCH_SKILL, _ARCH_SCRIPT,
    '--project-dir', '.', 'search', '--content', '--pattern', '.',
    register=False,
)


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
        args = _variant(
            _ENRICH_PACKAGE_ARGS,
            module='module-a', package='de.cuioss.nope', description='X', project_dir=tmpdir,
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


def test_package_key_resolves_refuses_target_escaping_root():
    """A key whose target resolves OUTSIDE the project root is refused, even though
    the target exists — path identity means in-tree identity. Guards the containment
    check that also catches the Windows drive-letter escape (`Path.__truediv__`
    discarding project_dir for a `C:/…` key)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        outside = Path(tmpdir) / 'outside'
        outside.mkdir()
        project = Path(tmpdir) / 'project'
        project.mkdir()
        # A symlink inside the project that points outside it: the target exists,
        # but resolves out of the tree, so the key must not validate.
        (project / 'escape').symlink_to(outside)
        assert package_key_resolves('escape', str(project)) is False


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


# =============================================================================
# Axis-D claimed-path collapse — covered at its CALL SITES, not in isolation
# =============================================================================
#
# ``_collapse_claimed_duplicate_rows`` is invoked from exactly two places:
# ``cmd_find`` and ``cmd_search``. Replacing BOTH invocations with a no-op used
# to leave every covering directory green, because the only tests of the collapse
# drove the helper directly with synthetic rows and a stubbed resolver — a shape
# that keeps passing however the readers are wired. The unit tests are correct and
# stay; what was missing is a reader that actually reaches the seam.
#
# The recorded fixture constraint is honoured rather than worked around: the crawl
# reads the live worktree and no Axis-D attributor is registered in a bare tmp
# project, so seeding two modules alone would make the collapse a deliberate
# no-op and the assertion vacuous. The resolver is therefore INJECTED, and each
# test carries its no-claim arm as a matched negative control — that arm is what
# proves the fixture really produces the cross-module duplicate the claimed arm
# then collapses, so neither result can be explained by an empty population.
#
# Every expected count is DERIVED from the two seeded populations — the claimed
# corpus and the set of modules inventorying it — never written as a literal, so
# growing either fixture cannot silently leave a stale expectation behind.

#: The claimed documentation corpus — every entry is a real file on disk AND is
#: listed in BOTH seeded modules' inventories, which is the duplicate shape.
_CLAIMED_DOCS = ('doc/api.adoc', 'doc/guide.adoc')

#: The module the injected attributor names as the owner of that corpus.
_DOC_OWNER = 'documentation'

#: The second inventorying module — the whole-tree crawl that also sees ``doc/**``.
_ROOT_CRAWLER = 'root-crawl'

#: Written into every seeded doc body so ``search --content`` has a real hit.
_DOC_BODY_TOKEN = 'CLAIMED_CORPUS_TOKEN'

#: The modules that BOTH inventory the claimed corpus, mapped to the
#: ``paths.module`` root each declares — the whole-tree root crawl, and the
#: documentation module that owns ``doc/**``. The seeding below and the expected
#: duplicate arity are read from this ONE mapping, so a third inventorying module
#: moves the fixture and the expected counts together instead of leaving a stale
#: literal behind.
_INVENTORYING_MODULES = {_ROOT_CRAWLER: '.', _DOC_OWNER: 'doc'}

#: Rows a reader emits over the seeded corpus while NO ownership claim applies —
#: one per (module, file) pair. Derived from both populations, never a literal, so
#: neither can grow without the expectation following it.
_UNCOLLAPSED_ROWS = len(_INVENTORYING_MODULES) * len(_CLAIMED_DOCS)


def _seed_claimed_doc_corpus(tmpdir: str) -> None:
    """Seed real doc files inventoried by BOTH modules under an explicit block.

    The ``files`` blocks are explicit and uncapped, so the reader takes the
    ``_resolve_module_inventory`` fast path and the inventory under test is
    exactly what is written here — no dependence on the crawler's heuristics.
    """
    project = Path(tmpdir)
    for rel in _CLAIMED_DOCS:
        target = project / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f'= Heading\n\n{_DOC_BODY_TOKEN}\n', encoding='utf-8')

    inventory = {'doc': list(_CLAIMED_DOCS)}
    seed_project(
        tmpdir,
        {
            name: {'name': name, 'paths': {'module': root}, 'files': dict(inventory)}
            for name, root in _INVENTORYING_MODULES.items()
        },
    )


def _claiming_attributor(path: str, _module_names: list[str]) -> tuple[str | None, list[dict]]:
    """Stand in for the Axis-D seam, claiming the seeded corpus for its owner."""
    owner = _DOC_OWNER if path in _CLAIMED_DOCS else None
    return owner, [{'id': 'stub-doc-claim', 'notes': []}]


def _no_claim_attributor(_path: str, _module_names: list[str]) -> tuple[None, list[dict]]:
    """The negative control: an attributor that runs and claims nothing."""
    return None, [{'id': 'stub-doc-claim', 'notes': []}]


def test_find_collapses_a_claimed_duplicate_to_one_row_per_file(monkeypatch):
    """``find`` emits ONE row per physical claimed file, not one per attributor.

    Reddens when the ``cmd_find`` collapse invocation is removed: the reader falls
    back to a row per attributing module and the count doubles.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_claimed_doc_corpus(tmpdir)
        pattern = 'doc/*.adoc'

        # Negative control — no claim, so nothing may collapse. This is what
        # proves the fixture genuinely produces the cross-module duplicate.
        monkeypatch.setattr(_handlers, 'resolve_path_attribution', _no_claim_attributor)
        unclaimed = _handlers.cmd_find(_variant(_FIND_ARGS, project_dir=tmpdir, pattern=pattern))

        assert unclaimed['status'] == 'success'
        assert unclaimed['count'] == _UNCOLLAPSED_ROWS, (
            'the fixture did not produce a cross-module duplicate for every claimed '
            f'doc, so the collapse assertion below would be vacuous: {unclaimed}'
        )

        # Under the claim, the call site collapses each duplicate onto its owner.
        monkeypatch.setattr(_handlers, 'resolve_path_attribution', _claiming_attributor)
        claimed = _handlers.cmd_find(_variant(_FIND_ARGS, project_dir=tmpdir, pattern=pattern))

        assert claimed['status'] == 'success'
        assert claimed['count'] == len(_CLAIMED_DOCS), (
            'find returned more rows than there are physical claimed files — the '
            'reader-side collapse is not running at this call site'
        )
        assert [row['path'] for row in claimed['results']] == sorted(_CLAIMED_DOCS)
        assert {row['module'] for row in claimed['results']} == {_DOC_OWNER}, (
            "the surviving rows are not the owner's — the collapse kept the crawl "
            'row instead of yielding to the ownership claim'
        )


def test_search_count_and_file_count_converge_for_a_claimed_duplicate(monkeypatch):
    """``search``'s row count meets its distinct-file count once the claim applies.

    ``count`` counts ROWS and ``file_count`` counts distinct PATHS, so they diverge
    exactly while a duplicate survives. Convergence is therefore the observable of
    the collapse at this second call site, and it reddens when that invocation is
    removed. ``files_scanned`` is asserted UNCHANGED across both arms: the collapse
    is a reporting-side precedence, not a narrowing of what was read, and a
    convergence bought by scanning fewer files would be a different bug wearing
    this one's green.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_claimed_doc_corpus(tmpdir)

        # Negative control — the unclaimed duplicate makes the two counts differ.
        monkeypatch.setattr(_handlers, 'resolve_path_attribution', _no_claim_attributor)
        unclaimed = _handlers.cmd_search(
            _variant(_SEARCH_ARGS, project_dir=tmpdir, pattern=_DOC_BODY_TOKEN)
        )

        assert unclaimed['status'] == 'success'
        assert unclaimed['count'] == _UNCOLLAPSED_ROWS
        assert unclaimed['file_count'] == len(_CLAIMED_DOCS)
        assert unclaimed['count'] != unclaimed['file_count'], (
            'the fixture produced no divergence to collapse, so the convergence '
            'assertion below would hold for the wrong reason'
        )

        monkeypatch.setattr(_handlers, 'resolve_path_attribution', _claiming_attributor)
        claimed = _handlers.cmd_search(
            _variant(_SEARCH_ARGS, project_dir=tmpdir, pattern=_DOC_BODY_TOKEN)
        )

        assert claimed['status'] == 'success'
        assert claimed['count'] == len(_CLAIMED_DOCS)
        assert claimed['file_count'] == len(_CLAIMED_DOCS)
        assert claimed['count'] == claimed['file_count'], (
            'search still reports more rows than distinct files under an ownership '
            'claim — the reader-side collapse is not running at this call site'
        )
        assert claimed['files_scanned'] == unclaimed['files_scanned'] == _UNCOLLAPSED_ROWS, (
            'the scanned population moved between the two arms; the collapse must '
            'change what is REPORTED, never what is read'
        )
