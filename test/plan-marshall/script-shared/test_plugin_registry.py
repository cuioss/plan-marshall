# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the plugin_registry shared reader module.

Every fixture is a real file tree under ``tmp_path``: a registry in the shape
the plugin manager writes, an executor carrying (or not carrying) the
``MARSHALL_VERSION`` assignment, and a cache bundle directory holding version
directories. No reader is mocked.
"""

import ast
import importlib.util
import json
import sys
from pathlib import Path

import marketplace_bundles
import plugin_registry
import pytest
from plugin_registry import (
    EXECUTOR_VERSION_EMPTY,
    EXECUTOR_VERSION_FOUND,
    EXECUTOR_VERSION_NOT_FOUND,
    EXECUTOR_VERSION_UNREADABLE,
    ORPHAN_MARKER_NAME,
    PARITY_AHEAD,
    PARITY_BEHIND,
    PARITY_IN_PARITY,
    PARITY_UNREADABLE,
    PARITY_VERDICTS,
    REGISTRY_ABSENT,
    REGISTRY_IO_ERROR,
    REGISTRY_NO_PLAN_MARSHALL_ENTRY,
    REGISTRY_NOT_JSON,
    REGISTRY_OK,
    classify_parity,
    is_orphan_marked,
    newest_cache_version,
    read_executor_version,
    read_registry,
    version_key,
)

REFERENCE = '0.1.1069'
OLDER = '0.1.999'
NEWER = '0.1.1070'

CACHE_ROOT = '/home/someone/.claude/plugins/cache/plan-marshall'


def _entry(
    version: str, *, scope: str = 'user', bundle: str = 'plan-marshall', path_version: str | None = None
) -> dict:
    """One scope entry in the shape the plugin manager writes."""
    return {
        'scope': scope,
        'installPath': f'{CACHE_ROOT}/{bundle}/{path_version if path_version is not None else version}',
        'version': version,
    }


def _write_registry(tmp_path: Path, plugins: dict) -> Path:
    registry = tmp_path / 'installed_plugins.json'
    registry.write_text(json.dumps({'version': 2, 'plugins': plugins}), encoding='utf-8')
    return registry


def _rows(*versions: str) -> list[dict[str, str | None]]:
    """Registry rows whose two pinned fields both carry the given version."""
    return [
        {'bundle': 'plan-marshall', 'scope': 'user', 'install_path_version': version, 'version': version}
        for version in versions
    ]


# ---------------------------------------------------------------------------
# version_key
# ---------------------------------------------------------------------------


def test_version_key_orders_numerically_not_lexically():
    # Arrange / Act / Assert — a lexical sort would put '0.1.999' last.
    assert version_key('0.1.1069') > version_key('0.1.999')
    assert max([OLDER, REFERENCE], key=version_key) == REFERENCE


@pytest.mark.parametrize('name', ['0.1.1069', '0.1.999', '0.1-BETA', '1.0.0', 'no-digits', '', '10.2.3-rc4'])
def test_version_key_matches_marketplace_bundles_sort_key(name):
    assert version_key(name) == marketplace_bundles._version_sort_key(name)


def test_version_key_without_digits_is_empty_tuple():
    assert version_key('BETA') == ()


# ---------------------------------------------------------------------------
# read_registry
# ---------------------------------------------------------------------------


def test_read_registry_yields_one_row_per_scope_entry(tmp_path):
    # Arrange — one bundle installed in user AND project scope, at different versions.
    registry = _write_registry(
        tmp_path,
        {'plan-marshall@plan-marshall': [_entry(OLDER, scope='user'), _entry(REFERENCE, scope='project')]},
    )

    # Act
    state, rows = read_registry(registry)

    # Assert — two rows, never collapsed, each carrying both pinned fields.
    assert state == REGISTRY_OK
    assert rows == [
        {'bundle': 'plan-marshall', 'scope': 'user', 'install_path_version': OLDER, 'version': OLDER},
        {'bundle': 'plan-marshall', 'scope': 'project', 'install_path_version': REFERENCE, 'version': REFERENCE},
    ]


def test_read_registry_reports_install_path_version_and_version_field_separately(tmp_path):
    # Arrange — an entry that disagrees with itself.
    registry = _write_registry(tmp_path, {'plan-marshall@plan-marshall': [_entry(REFERENCE, path_version=OLDER)]})

    # Act
    state, rows = read_registry(registry)

    # Assert
    assert state == REGISTRY_OK
    assert rows[0]['install_path_version'] == OLDER
    assert rows[0]['version'] == REFERENCE


def test_read_registry_covers_every_bundle_of_the_marketplace(tmp_path):
    registry = _write_registry(
        tmp_path,
        {
            'plan-marshall@plan-marshall': [_entry(REFERENCE)],
            'pm-dev-java@plan-marshall': [_entry(REFERENCE, bundle='pm-dev-java')],
        },
    )

    state, rows = read_registry(registry)

    assert state == REGISTRY_OK
    assert sorted(str(row['bundle']) for row in rows) == ['plan-marshall', 'pm-dev-java']


def test_read_registry_ignores_foreign_marketplace_key(tmp_path):
    # Arrange — a foreign marketplace pinned far behind must not produce a row.
    registry = _write_registry(
        tmp_path,
        {
            'plan-marshall@plan-marshall': [_entry(REFERENCE)],
            'plan-marshall@some-other-marketplace': [_entry('0.0.1')],
            'unrelated@claude-plugins-official': [_entry('0.0.1', bundle='unrelated')],
        },
    )

    # Act
    state, rows = read_registry(registry)

    # Assert
    assert state == REGISTRY_OK
    assert len(rows) == 1
    assert rows[0]['version'] == REFERENCE
    assert classify_parity(rows, REFERENCE) == PARITY_IN_PARITY


def test_read_registry_honours_explicit_marketplace_argument(tmp_path):
    registry = _write_registry(tmp_path, {'thing@other': [_entry('2.0.0', bundle='thing')]})

    assert read_registry(registry)[0] == REGISTRY_NO_PLAN_MARSHALL_ENTRY
    state, rows = read_registry(registry, marketplace='other')
    assert state == REGISTRY_OK
    assert rows[0]['bundle'] == 'thing'


def test_read_registry_reports_missing_fields_as_none(tmp_path):
    # Arrange — absent, empty and non-string fields are all "unknown".
    registry = _write_registry(
        tmp_path,
        {'plan-marshall@plan-marshall': [{'scope': '', 'installPath': 17}]},
    )

    # Act
    state, rows = read_registry(registry)

    # Assert
    assert state == REGISTRY_OK
    assert rows == [{'bundle': 'plan-marshall', 'scope': None, 'install_path_version': None, 'version': None}]


def test_read_registry_absent_file(tmp_path):
    assert read_registry(tmp_path / 'installed_plugins.json') == (REGISTRY_ABSENT, [])


def test_read_registry_not_json(tmp_path):
    registry = tmp_path / 'installed_plugins.json'
    registry.write_text('{"plugins": ', encoding='utf-8')

    assert read_registry(registry) == (REGISTRY_NOT_JSON, [])


def test_read_registry_unreadable_path_is_io_error(tmp_path):
    # Arrange — a directory at the registry path exists but cannot be read as a file.
    registry = tmp_path / 'installed_plugins.json'
    registry.mkdir()

    assert read_registry(registry) == (REGISTRY_IO_ERROR, [])


@pytest.mark.parametrize(
    'payload',
    [
        {'version': 2, 'plugins': {}},
        {'version': 2, 'plugins': {'other@elsewhere': [{'scope': 'user', 'version': '1.0.0'}]}},
        {'version': 2, 'plugins': {'plan-marshall@plan-marshall': []}},
        {'version': 2, 'plugins': {'plan-marshall@plan-marshall': 'not-a-list'}},
        {'version': 2, 'plugins': {'no-separator-key': [{'scope': 'user', 'version': '1.0.0'}]}},
        {'version': 2},
        ['not', 'an', 'object'],
    ],
    ids=[
        'empty',
        'foreign-only',
        'empty-entry-list',
        'non-list-entries',
        'key-without-at',
        'no-plugins-key',
        'non-dict',
    ],
)
def test_read_registry_without_plan_marshall_entry(tmp_path, payload):
    registry = tmp_path / 'installed_plugins.json'
    registry.write_text(json.dumps(payload), encoding='utf-8')

    assert read_registry(registry) == (REGISTRY_NO_PLAN_MARSHALL_ENTRY, [])


def test_non_ok_registry_states_are_distinct_and_all_classify_unreadable(tmp_path):
    # Arrange — three non-ok states.
    absent = tmp_path / 'absent.json'
    not_json = tmp_path / 'not_json.json'
    not_json.write_text('<<<not json>>>', encoding='utf-8')
    no_entry = tmp_path / 'no_entry.json'
    no_entry.write_text(json.dumps({'version': 2, 'plugins': {}}), encoding='utf-8')

    # Act
    results = [read_registry(path) for path in (absent, not_json, no_entry)]

    # Assert — three different states, no rows, and one shared verdict.
    states = [state for state, _ in results]
    assert states == [REGISTRY_ABSENT, REGISTRY_NOT_JSON, REGISTRY_NO_PLAN_MARSHALL_ENTRY]
    assert len(set(states)) == 3
    for _, rows in results:
        assert rows == []
        assert classify_parity(rows, REFERENCE) == PARITY_UNREADABLE


# ---------------------------------------------------------------------------
# read_executor_version
# ---------------------------------------------------------------------------


def _write_executor(tmp_path: Path, body: str) -> Path:
    executor = tmp_path / 'execute-script.py'
    executor.write_text(body, encoding='utf-8')
    return executor


def test_read_executor_version_with_assignment(tmp_path):
    executor = _write_executor(tmp_path, f"#!/usr/bin/env python3\nimport sys\n\nMARSHALL_VERSION = '{REFERENCE}'\n")

    assert read_executor_version(executor) == (EXECUTOR_VERSION_FOUND, REFERENCE)


def test_read_executor_version_accepts_double_quotes(tmp_path):
    executor = _write_executor(tmp_path, f'MARSHALL_VERSION = "{REFERENCE}"\nSCRIPTS = {{}}\n')

    assert read_executor_version(executor) == (EXECUTOR_VERSION_FOUND, REFERENCE)


def test_read_executor_version_without_assignment(tmp_path):
    executor = _write_executor(tmp_path, '#!/usr/bin/env python3\nSCRIPTS = {}\n')

    assert read_executor_version(executor) == (EXECUTOR_VERSION_NOT_FOUND, None)


def test_read_executor_version_ignores_indented_or_commented_mentions(tmp_path):
    # Arrange — only a module-level assignment counts.
    executor = _write_executor(
        tmp_path,
        "# MARSHALL_VERSION = '9.9.9'\ndef f():\n    MARSHALL_VERSION = '8.8.8'\n    return MARSHALL_VERSION\n",
    )

    assert read_executor_version(executor) == (EXECUTOR_VERSION_NOT_FOUND, None)


def test_read_executor_version_empty_sentinel(tmp_path):
    executor = _write_executor(tmp_path, "MARSHALL_VERSION = ''\n")

    assert read_executor_version(executor) == (EXECUTOR_VERSION_EMPTY, None)


def test_read_executor_version_absent_file_is_unreadable(tmp_path):
    assert read_executor_version(tmp_path / 'execute-script.py') == (EXECUTOR_VERSION_UNREADABLE, None)


def test_executor_states_are_distinct():
    states = {
        EXECUTOR_VERSION_FOUND,
        EXECUTOR_VERSION_UNREADABLE,
        EXECUTOR_VERSION_NOT_FOUND,
        EXECUTOR_VERSION_EMPTY,
    }
    assert len(states) == 4


# ---------------------------------------------------------------------------
# newest_cache_version / is_orphan_marked
# ---------------------------------------------------------------------------


def _make_cache(tmp_path: Path, *versions: str) -> Path:
    bundle_dir = tmp_path / 'plan-marshall'
    for version in versions:
        (bundle_dir / version).mkdir(parents=True)
    return bundle_dir


def test_newest_cache_version_picks_numerically_newest(tmp_path):
    bundle_dir = _make_cache(tmp_path, OLDER, REFERENCE, '0.1.10')

    assert newest_cache_version(bundle_dir) == REFERENCE


def test_newest_cache_version_ignores_orphan_marker_for_selection(tmp_path):
    # Arrange — the newest version dir carries the marker.
    bundle_dir = _make_cache(tmp_path, OLDER, REFERENCE)
    (bundle_dir / REFERENCE / ORPHAN_MARKER_NAME).write_text('1700000000', encoding='utf-8')

    # Act / Assert — still selected; the marker is reported separately.
    assert newest_cache_version(bundle_dir) == REFERENCE
    assert is_orphan_marked(bundle_dir, REFERENCE) is True
    assert is_orphan_marked(bundle_dir, OLDER) is False


def test_newest_cache_version_skips_files_and_non_version_directories(tmp_path):
    bundle_dir = _make_cache(tmp_path, OLDER, '.tmp-staging', 'latest')
    (bundle_dir / '9.9.9').write_text('a file, not a version dir', encoding='utf-8')

    assert newest_cache_version(bundle_dir) == OLDER


def test_newest_cache_version_none_when_absent_or_empty(tmp_path):
    assert newest_cache_version(tmp_path / 'missing') is None
    empty = tmp_path / 'empty-bundle'
    empty.mkdir()
    assert newest_cache_version(empty) is None


def test_is_orphan_marked_false_for_missing_version_dir(tmp_path):
    assert is_orphan_marked(tmp_path / 'plan-marshall', REFERENCE) is False


# ---------------------------------------------------------------------------
# classify_parity
# ---------------------------------------------------------------------------


def test_parity_verdict_set_is_closed_and_declared_once():
    assert PARITY_VERDICTS == (PARITY_IN_PARITY, PARITY_BEHIND, PARITY_AHEAD, PARITY_UNREADABLE)
    assert set(PARITY_VERDICTS) == {'in_parity', 'behind', 'ahead', 'unreadable'}


@pytest.mark.parametrize(
    ('pinned', 'expected'),
    [(OLDER, PARITY_BEHIND), (REFERENCE, PARITY_IN_PARITY), (NEWER, PARITY_AHEAD)],
    ids=['one-behind', 'equal', 'one-ahead'],
)
def test_classify_parity_three_version_relations(tmp_path, pinned, expected):
    # Arrange — through the real reader, so the row shape is the producer's own.
    registry = _write_registry(tmp_path, {'plan-marshall@plan-marshall': [_entry(pinned)]})
    state, rows = read_registry(registry)
    assert state == REGISTRY_OK

    # Act / Assert
    assert classify_parity(rows, REFERENCE) == expected


def test_classify_parity_behind_wins_over_ahead():
    assert classify_parity(_rows(OLDER, NEWER), REFERENCE) == PARITY_BEHIND
    assert classify_parity(_rows(NEWER, OLDER), REFERENCE) == PARITY_BEHIND


def test_classify_parity_ahead_requires_none_older():
    assert classify_parity(_rows(REFERENCE, NEWER), REFERENCE) == PARITY_AHEAD


def test_classify_parity_disagreeing_scope_entries_are_never_in_parity(tmp_path):
    # Arrange — user scope at the reference, project scope behind it.
    registry = _write_registry(
        tmp_path,
        {'plan-marshall@plan-marshall': [_entry(REFERENCE, scope='user'), _entry(OLDER, scope='project')]},
    )
    _, rows = read_registry(registry)

    # Act / Assert
    assert classify_parity(rows, REFERENCE) == PARITY_BEHIND


@pytest.mark.parametrize('other', [OLDER, NEWER, '0.1.1069-dirty', '1.0.0', '0.1'])
def test_classify_parity_never_in_parity_when_any_entry_differs(other):
    assert classify_parity(_rows(REFERENCE, other), REFERENCE) != PARITY_IN_PARITY


def test_classify_parity_entry_disagreeing_with_itself_is_not_in_parity():
    # Arrange — installPath names an older version dir than the version field.
    rows: list[dict[str, str | None]] = [
        {'bundle': 'plan-marshall', 'scope': 'user', 'install_path_version': OLDER, 'version': REFERENCE}
    ]

    assert classify_parity(rows, REFERENCE) == PARITY_BEHIND


def test_classify_parity_unknown_field_is_unreadable():
    rows: list[dict[str, str | None]] = [
        {'bundle': 'plan-marshall', 'scope': 'user', 'install_path_version': None, 'version': REFERENCE}
    ]

    assert classify_parity(rows, REFERENCE) == PARITY_UNREADABLE


def test_classify_parity_behind_wins_over_unknown_field():
    rows: list[dict[str, str | None]] = [
        {'bundle': 'plan-marshall', 'scope': 'user', 'install_path_version': None, 'version': OLDER}
    ]

    assert classify_parity(rows, REFERENCE) == PARITY_BEHIND


def test_classify_parity_same_key_different_spelling_is_unreadable():
    # '0.1-1069' has the reference's digit runs but is not the reference.
    assert classify_parity(_rows('0.1-1069'), REFERENCE) == PARITY_UNREADABLE


@pytest.mark.parametrize('reference', [None, '', 'no-digits'])
def test_classify_parity_unusable_reference_is_unreadable(reference):
    assert classify_parity(_rows(REFERENCE), reference) == PARITY_UNREADABLE


def test_classify_parity_no_rows_is_unreadable():
    assert classify_parity([], REFERENCE) == PARITY_UNREADABLE


def test_classify_parity_only_returns_members_of_the_verdict_set():
    for rows in ([], _rows(OLDER), _rows(REFERENCE), _rows(NEWER), _rows(OLDER, NEWER), _rows('junk')):
        assert classify_parity(rows, REFERENCE) in PARITY_VERDICTS


# ---------------------------------------------------------------------------
# Module constraints
# ---------------------------------------------------------------------------


def _module_tree() -> ast.Module:
    return ast.parse(Path(plugin_registry.__file__).read_text(encoding='utf-8'))


def test_module_imports_only_the_standard_library():
    # Arrange
    imported: set[str] = set()
    for node in ast.walk(_module_tree()):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split('.')[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0, 'relative import of a sibling module'
            imported.add((node.module or '').split('.')[0])

    # Assert — non-vacuous, and every name is a stdlib module.
    assert imported
    assert imported <= set(sys.stdlib_module_names)


def test_module_defines_no_dataclass():
    for node in ast.walk(_module_tree()):
        if isinstance(node, ast.ClassDef):
            decorators = [ast.unparse(decorator) for decorator in node.decorator_list]
            assert not any('dataclass' in decorator for decorator in decorators)
        if isinstance(node, ast.Name):
            assert node.id != 'dataclass'


def test_module_loads_by_file_location_without_sys_modules_registration(tmp_path):
    # Arrange — the way marketplace/targets/ loads it: by path, never registered.
    spec = importlib.util.spec_from_file_location('_plugin_registry_by_location', plugin_registry.__file__)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)

    # Act
    spec.loader.exec_module(module)

    # Assert — usable end to end, and it never registered itself.
    assert '_plugin_registry_by_location' not in sys.modules
    registry = _write_registry(tmp_path, {'plan-marshall@plan-marshall': [_entry(OLDER)]})
    state, rows = module.read_registry(registry)
    assert state == module.REGISTRY_OK
    assert module.classify_parity(rows, REFERENCE) == module.PARITY_BEHIND
