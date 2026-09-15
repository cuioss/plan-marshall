#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``discover --force`` delta attribution and the ``--apply`` projection.

``api_discover`` classifies its own rewrite of ``.plan/project-architecture/``
against the on-disk pre-state into the delta classes declared in
``_descriptor_delta.DELTA_CLASSES``, reduces them to a verdict, and — under
``--apply plan`` / ``--apply migration`` — writes only that kind of change.

Every scenario drives the real ``api_discover`` over a seeded temp tree with the
discovery delegate replaced by a deterministic stub (the pattern
``test_discover_descriptor_stability.py`` established). Seeded documents are
written in COMPACT JSON, which the store's writer never produces, so a document
that got re-serialized is visible as a byte change even when its content did not
move — that is what makes the byte-identity assertions bite.
"""

import json
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from conftest import load_script_module, parse_ns

_cmd_manage = load_script_module('plan-marshall', 'manage-architecture', '_cmd_manage.py', '_cmd_manage')
_descriptor_delta = load_script_module(
    'plan-marshall', 'manage-architecture', '_descriptor_delta.py', '_descriptor_delta'
)

api_discover = _cmd_manage.api_discover
DELTA_CLASSES: dict[str, str] = _descriptor_delta.DELTA_CLASSES
VERDICTS: tuple[str, ...] = _descriptor_delta.VERDICTS
APPLY_MODES: tuple[str, ...] = _descriptor_delta.APPLY_MODES

_ARCH_DIR = Path('.plan') / 'project-architecture'
_META = '_project.json'
_HEADER = {'by': 'architecture', 'tree_sha': 'TREE-0'}
_UNKNOWN_HEADER = {'by': 'architecture', 'tree_sha': None}
_DROP = object()

Setup = Callable[[str, pytest.MonkeyPatch], None]


# =============================================================================
# Fixture helpers
# =============================================================================


def _module_data(name: str, packages: dict[str, Any]) -> dict[str, Any]:
    return {
        'name': name,
        'build_systems': ['maven'],
        'paths': {'module': name},
        'metadata': {},
        'packages': packages,
        'dependencies': [],
        'stats': {},
        'commands': {},
    }


def _stub_discovery(
    monkeypatch: pytest.MonkeyPatch,
    module_packages: dict[str, dict[str, Any]],
    extensions_used: tuple[str, ...] = ('ext',),
) -> None:
    """Replace the discovery delegate with a stub crawling exactly ``module_packages``."""
    import extension_discovery

    def _discover(_project_root: Any) -> dict[str, Any]:
        return {
            'modules': {name: _module_data(name, packages) for name, packages in module_packages.items()},
            'extensions_used': list(extensions_used),
        }

    monkeypatch.setattr(extension_discovery, 'discover_project_modules', _discover)


def _document(name: str, **overrides: Any) -> dict[str, Any]:
    """A fully-migrated concept document; an override of ``_DROP`` removes the field."""
    document: dict[str, Any] = {
        'type': 'module',
        'generation': dict(_HEADER),
        'responsibility': f'Handles {name}',
        'key_packages': {},
    }
    for field, value in overrides.items():
        if value is _DROP:
            document.pop(field, None)
        else:
            document[field] = value
    return document


def _index_entry(document: dict[str, Any]) -> dict[str, Any]:
    """The index entry a document implies; no header on the document means none here."""
    entry: dict[str, Any] = {'description': document.get('responsibility', '')}
    if 'generation' in document:
        entry['generation'] = document['generation']
    return entry


def _seed(
    tmpdir: str,
    documents: dict[str, dict[str, Any]],
    *,
    extensions_used: tuple[str, ...] = ('ext',),
    index: dict[str, Any] | None = None,
    write_meta: bool = True,
) -> None:
    """Write the pre-state tree in compact JSON."""
    data_dir = Path(tmpdir) / _ARCH_DIR
    for name, document in documents.items():
        path = data_dir / name / 'enriched.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(document), encoding='utf-8')
    if write_meta:
        meta = {
            'name': 'proj',
            'description': 'Curated',
            'description_reasoning': 'README',
            'extensions_used': list(extensions_used),
            'modules': index if index is not None else {n: _index_entry(d) for n, d in documents.items()},
        }
        data_dir.mkdir(parents=True, exist_ok=True)
        (data_dir / _META).write_text(json.dumps(meta), encoding='utf-8')


def _snapshot(tmpdir: str) -> dict[str, bytes]:
    """Every file under the descriptor tree, relative path → bytes."""
    data_dir = Path(tmpdir) / _ARCH_DIR
    if not data_dir.is_dir():
        return {}
    return {
        path.relative_to(data_dir).as_posix(): path.read_bytes()
        for path in sorted(data_dir.rglob('*'))
        if path.is_file()
    }


def _classes(result: dict[str, Any]) -> set[str]:
    return {row['class'] for row in result['delta_classes']}


def _make_package_dir(tmpdir: str) -> None:
    (Path(tmpdir) / 'module-a' / 'src' / 'pkg').mkdir(parents=True)


# =============================================================================
# One scenario per delta class
# =============================================================================


def _scenario_module_added(tmpdir: str, monkeypatch: pytest.MonkeyPatch) -> None:
    _seed(tmpdir, {'module-a': _document('module-a')})
    _stub_discovery(monkeypatch, {'module-a': {}, 'module-b': {}})


def _scenario_module_removed(tmpdir: str, monkeypatch: pytest.MonkeyPatch) -> None:
    _seed(tmpdir, {'module-a': _document('module-a'), 'module-b': _document('module-b')})
    _stub_discovery(monkeypatch, {'module-a': {}})


def _scenario_extensions_used_changed(tmpdir: str, monkeypatch: pytest.MonkeyPatch) -> None:
    _seed(tmpdir, {'module-a': _document('module-a')}, extensions_used=('ext',))
    _stub_discovery(monkeypatch, {'module-a': {}}, extensions_used=('other-ext',))


def _scenario_generation_backfill(tmpdir: str, monkeypatch: pytest.MonkeyPatch) -> None:
    _seed(tmpdir, {'module-a': _document('module-a', generation=_DROP)})
    _stub_discovery(monkeypatch, {'module-a': {}})


def _scenario_concept_type_backfill(tmpdir: str, monkeypatch: pytest.MonkeyPatch) -> None:
    _seed(tmpdir, {'module-a': _document('module-a', type=_DROP)})
    _stub_discovery(monkeypatch, {'module-a': {}})


def _scenario_key_packages_rekey(tmpdir: str, monkeypatch: pytest.MonkeyPatch) -> None:
    _make_package_dir(tmpdir)
    _seed(tmpdir, {'module-a': _document('module-a', key_packages={'com.example.pkg': {'description': 'Pkg'}})})
    _stub_discovery(monkeypatch, {'module-a': {'com.example.pkg': {'path': 'module-a/src/pkg'}}})


def _scenario_unclassified(tmpdir: str, monkeypatch: pytest.MonkeyPatch) -> None:
    document = _document('module-a')
    _seed(
        tmpdir,
        {'module-a': document},
        index={'module-a': {'description': 'A stale description', 'generation': document['generation']}},
    )
    _stub_discovery(monkeypatch, {'module-a': {}})


_CLASS_SCENARIOS: dict[str, Setup] = {
    'module_added': _scenario_module_added,
    'module_removed': _scenario_module_removed,
    'extensions_used_changed': _scenario_extensions_used_changed,
    'generation_backfill': _scenario_generation_backfill,
    'concept_type_backfill': _scenario_concept_type_backfill,
    'key_packages_rekey': _scenario_key_packages_rekey,
    'unclassified': _scenario_unclassified,
}


def test_every_declared_class_has_a_scenario():
    """The parametrization below is derived from the vocabulary, and it is not empty."""
    assert len(DELTA_CLASSES) > 0, 'the class vocabulary is empty, so the per-class tests would pass vacuously'
    assert set(_CLASS_SCENARIOS) == set(DELTA_CLASSES), (
        f'scenario set drifted from DELTA_CLASSES. Without a scenario: '
        f'{sorted(set(DELTA_CLASSES) - set(_CLASS_SCENARIOS))}. '
        f'Not declared: {sorted(set(_CLASS_SCENARIOS) - set(DELTA_CLASSES))}.'
    )


@pytest.mark.parametrize('delta_class', sorted(DELTA_CLASSES))
def test_each_class_is_detected_alone_with_its_attribution(delta_class, monkeypatch):
    """Each scenario produces exactly its class, carrying the declared attribution."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _CLASS_SCENARIOS[delta_class](tmpdir, monkeypatch)

        result = api_discover(tmpdir, force=True, apply='plan')

        assert result['status'] == 'success'
        assert _classes(result) == {delta_class}, result['delta_classes']
        row = result['delta_classes'][0]
        assert row['attribution'] == DELTA_CLASSES[delta_class]


def test_unclassified_names_the_field_it_could_not_explain(monkeypatch):
    """An undecidable delta reports WHICH field it could not attribute."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _scenario_unclassified(tmpdir, monkeypatch)

        result = api_discover(tmpdir, force=True, apply='plan')

        assert result['unclassified_fields'] == [{'document': _META, 'field': 'modules.module-a.description'}]


# =============================================================================
# One scenario per verdict
# =============================================================================


def _verdict_clean(tmpdir: str, monkeypatch: pytest.MonkeyPatch) -> None:
    _seed(tmpdir, {'module-a': _document('module-a')})
    _stub_discovery(monkeypatch, {'module-a': {}})


def _verdict_mixed(tmpdir: str, monkeypatch: pytest.MonkeyPatch) -> None:
    _seed(tmpdir, {'module-a': _document('module-a', generation=_DROP)})
    _stub_discovery(monkeypatch, {'module-a': {}, 'module-b': {}})


def _verdict_undecidable(tmpdir: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """A plan class, a migration class AND an unclassified field — undecidable must win."""
    _seed(
        tmpdir,
        {'module-a': _document('module-a', generation=_DROP)},
        index={'module-a': {'description': 'A stale description'}},
    )
    _stub_discovery(monkeypatch, {'module-a': {}, 'module-b': {}})


def _verdict_no_baseline(tmpdir: str, monkeypatch: pytest.MonkeyPatch) -> None:
    _seed(tmpdir, {'module-a': _document('module-a')}, write_meta=False)
    _stub_discovery(monkeypatch, {'module-a': {}})


_VERDICT_SCENARIOS: dict[str, Setup] = {
    'clean': _verdict_clean,
    'plan_attributable': _scenario_module_added,
    'migration_only': _scenario_generation_backfill,
    'mixed': _verdict_mixed,
    'undecidable': _verdict_undecidable,
    'no_baseline': _verdict_no_baseline,
}


def test_every_declared_verdict_has_a_scenario():
    assert len(VERDICTS) > 0
    assert set(_VERDICT_SCENARIOS) == set(VERDICTS)


@pytest.mark.parametrize('verdict', sorted(VERDICTS))
def test_each_verdict_is_reached(verdict, monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        _VERDICT_SCENARIOS[verdict](tmpdir, monkeypatch)

        result = api_discover(tmpdir, force=True, apply='plan')

        assert result['status'] == 'success'
        assert result['attribution'] == verdict


def test_undecidable_dominates_plan_and_migration_classes(monkeypatch):
    """Precedence: the scenario carries every attribution, and the verdict is still undecidable."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _verdict_undecidable(tmpdir, monkeypatch)

        result = api_discover(tmpdir, force=True, apply='plan')

        attributions = {row['attribution'] for row in result['delta_classes']}
        assert attributions == {'plan', 'migration', 'undecidable'}, 'the precedence fixture lost a class'
        assert result['attribution'] == 'undecidable'
        assert result['applied'] == 'none'


def test_no_baseline_examines_no_module(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        _verdict_no_baseline(tmpdir, monkeypatch)

        result = api_discover(tmpdir, force=True, apply='plan')

        assert result['modules_examined'] == 0
        assert result['delta_classes'] == []
        assert result['applied'] == 'none'
        assert not (Path(tmpdir) / _ARCH_DIR / _META).exists()


def test_clean_verdict_still_reports_the_modules_it_examined(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        _verdict_clean(tmpdir, monkeypatch)

        result = api_discover(tmpdir, force=True, apply='plan')

        assert result['delta_classes'] == []
        assert result['modules_examined'] == 1


# =============================================================================
# --apply plan / --apply migration projections
# =============================================================================


def _seed_consumer_churn(tmpdir: str, monkeypatch: pytest.MonkeyPatch, *crawled: str) -> None:
    """Generation back-fill plus a partial re-key: one dotted key bridges, its parent does not."""
    _make_package_dir(tmpdir)
    _seed(
        tmpdir,
        {
            'module-a': _document(
                'module-a',
                generation=_DROP,
                key_packages={
                    'com.example.pkg': {'description': 'Pkg'},
                    'com.example': {'description': 'Parent package'},
                },
            )
        },
    )
    _stub_discovery(
        monkeypatch,
        {name: ({'com.example.pkg': {'path': 'module-a/src/pkg'}} if name == 'module-a' else {}) for name in crawled},
    )


def test_apply_plan_over_migration_only_leaves_every_file_byte_identical(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_consumer_churn(tmpdir, monkeypatch, 'module-a')
        before = _snapshot(tmpdir)

        result = api_discover(tmpdir, force=True, apply='plan')

        assert result['attribution'] == 'migration_only'
        assert _classes(result) == {'generation_backfill', 'key_packages_rekey'}
        assert result['applied'] == 'none'
        assert _snapshot(tmpdir) == before
        assert not (Path(tmpdir) / '.plan' / 'project-architecture.tmp').exists()


def test_apply_plan_over_mixed_writes_only_the_added_module_and_its_index_entry(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_consumer_churn(tmpdir, monkeypatch, 'module-a', 'module-b')
        before = _snapshot(tmpdir)
        before_meta = json.loads(before[_META])

        result = api_discover(tmpdir, force=True, apply='plan')

        assert result['attribution'] == 'mixed'
        assert result['applied'] == 'plan'
        after = _snapshot(tmpdir)
        assert set(after) == set(before) | {'module-b/enriched.json'}
        assert after['module-a/enriched.json'] == before['module-a/enriched.json'], (
            'a pre-existing document was rewritten under --apply plan'
        )
        after_meta = json.loads(after[_META])
        added_entry = after_meta['modules'].pop('module-b')
        assert added_entry['description'] == ''
        assert after_meta == before_meta, 'plan projection changed _project.json beyond the added index entry'


def test_apply_migration_over_mixed_writes_only_the_migrated_documents(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_consumer_churn(tmpdir, monkeypatch, 'module-a', 'module-b')
        before = _snapshot(tmpdir)

        result = api_discover(tmpdir, force=True, apply='migration')

        assert result['attribution'] == 'mixed'
        assert result['applied'] == 'migration'
        after = _snapshot(tmpdir)
        assert set(after) == set(before), 'the added module was written under --apply migration'
        migrated = json.loads(after['module-a/enriched.json'])
        assert migrated['generation'] == _UNKNOWN_HEADER
        assert set(migrated['key_packages']) == {'module-a/src/pkg', 'com.example'}
        meta = json.loads(after[_META])
        assert set(meta['modules']) == {'module-a'}
        assert meta['modules']['module-a']['generation'] == _UNKNOWN_HEADER


def test_apply_plan_over_undecidable_writes_nothing(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        _verdict_undecidable(tmpdir, monkeypatch)
        before = _snapshot(tmpdir)

        result = api_discover(tmpdir, force=True, apply='plan')

        assert result['applied'] == 'none'
        assert _snapshot(tmpdir) == before


def test_apply_migration_without_a_migration_class_writes_nothing(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        _scenario_module_added(tmpdir, monkeypatch)
        before = _snapshot(tmpdir)

        result = api_discover(tmpdir, force=True, apply='migration')

        assert result['attribution'] == 'plan_attributable'
        assert result['applied'] == 'none'
        assert _snapshot(tmpdir) == before


# =============================================================================
# Unresolved re-key keys reach the output
# =============================================================================


def test_unresolved_key_packages_are_reported_by_module_and_key(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_consumer_churn(tmpdir, monkeypatch, 'module-a')

        result = api_discover(tmpdir, force=True, apply='plan')

        assert result['unresolved_key_packages'] == [{'module': 'module-a', 'key': 'com.example'}]
        assert result['unresolved_key_packages_count'] == len(result['unresolved_key_packages'])


def test_unresolved_key_packages_count_is_zero_not_absent_when_every_key_resolves(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        _scenario_key_packages_rekey(tmpdir, monkeypatch)

        result = api_discover(tmpdir, force=True, apply='plan')

        assert _classes(result) == {'key_packages_rekey'}, 'the fixture migrated nothing, so a zero would be vacuous'
        assert 'unresolved_key_packages_count' in result
        assert result['unresolved_key_packages_count'] == 0
        assert result['unresolved_key_packages'] == []


# =============================================================================
# Default path (--apply all) controls
# =============================================================================


def test_default_apply_over_undecidable_still_writes_the_full_regenerated_tree(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        _verdict_undecidable(tmpdir, monkeypatch)

        result = api_discover(tmpdir, force=True)

        assert result['attribution'] == 'undecidable'
        assert result['applied'] == 'all'
        after = _snapshot(tmpdir)
        assert 'module-b/enriched.json' in after
        meta = json.loads(after[_META])
        assert meta['modules']['module-a']['description'] == 'Handles module-a'


def test_default_apply_over_no_baseline_still_writes_the_full_regenerated_tree(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        _verdict_no_baseline(tmpdir, monkeypatch)

        result = api_discover(tmpdir, force=True)

        assert result['attribution'] == 'no_baseline'
        assert result['applied'] == 'all'
        assert (Path(tmpdir) / _ARCH_DIR / _META).is_file()


def test_default_apply_over_migration_only_rewrites_the_tree(monkeypatch):
    """Matched control for the byte-identity test: the same fixture under ``all`` IS dirtied."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_consumer_churn(tmpdir, monkeypatch, 'module-a')
        before = _snapshot(tmpdir)

        result = api_discover(tmpdir, force=True)

        assert result['attribution'] == 'migration_only'
        assert result['applied'] == 'all'
        assert _snapshot(tmpdir) != before


# =============================================================================
# CLI surface
# =============================================================================


def test_discover_apply_flag_defaults_to_all_and_accepts_every_mode():
    default = parse_ns('plan-marshall', 'manage-architecture', 'architecture.py', 'discover', '--force', register=False)
    assert default.apply == 'all'
    assert len(APPLY_MODES) > 0
    for mode in APPLY_MODES:
        parsed = parse_ns(
            'plan-marshall',
            'manage-architecture',
            'architecture.py',
            'discover',
            '--force',
            '--apply',
            mode,
            register=False,
        )
        assert parsed.apply == mode
