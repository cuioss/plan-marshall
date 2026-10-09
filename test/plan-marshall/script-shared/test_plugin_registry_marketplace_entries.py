# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the one walk that decides which registry entries belong to a marketplace.

``iter_marketplace_entries`` is the single filter over a parsed registry
document. ``read_registry`` builds its rows from it, and a caller that modifies
the registry walks it too, so both see the same entries in the same order.
"""

import ast
import json
from pathlib import Path

import plugin_registry
import pytest
from plugin_registry import (
    REGISTRY_NO_PLAN_MARSHALL_ENTRY,
    REGISTRY_OK,
    iter_marketplace_entries,
    read_registry,
)

OWN = 'plan-marshall'


def _entry(version: str, scope: str = 'user') -> dict:
    return {'scope': scope, 'installPath': f'/cache/{version}', 'version': version}


def _mixed_document() -> dict:
    """A registry holding every shape the walk keeps beside every shape it skips."""
    return {
        'version': 2,
        'plugins': {
            'pm-dev-java@plan-marshall': [_entry('0.1.2')],
            'other@elsewhere': [_entry('9.9.9')],
            'plan-marshall@plan-marshall': [_entry('0.1.1', 'user'), 'not-an-object', _entry('0.1.3', 'project')],
            'plan-marshall@some-other-marketplace': [_entry('0.0.1')],
            'no-separator-key': [_entry('0.0.2')],
            'pm-dev-python@plan-marshall': 'not-a-list',
            'scoped@name@plan-marshall': [_entry('0.1.4')],
        },
    }


def test_yields_the_entries_of_the_marketplace_in_document_order():
    # Arrange
    document = _mixed_document()

    # Act
    pairs = list(iter_marketplace_entries(document))

    # Assert — keys in their order, each key's entries in list order.
    assert [(bundle, entry['version']) for bundle, entry in pairs] == [
        ('pm-dev-java', '0.1.2'),
        ('plan-marshall', '0.1.1'),
        ('plan-marshall', '0.1.3'),
        ('scoped@name', '0.1.4'),
    ]


def test_yields_the_documents_own_dicts_not_copies():
    # Arrange
    document = _mixed_document()

    # Act — mutate what the walk handed out.
    for _, entry in iter_marketplace_entries(document):
        entry['version'] = 'rewritten'

    # Assert — the document changed, and only in this marketplace's entries.
    plugins = document['plugins']
    assert plugins['plan-marshall@plan-marshall'][0]['version'] == 'rewritten'
    assert plugins['plan-marshall@plan-marshall'][2]['version'] == 'rewritten'
    assert plugins['other@elsewhere'][0]['version'] == '9.9.9'
    assert plugins['plan-marshall@some-other-marketplace'][0]['version'] == '0.0.1'


def test_honours_the_marketplace_argument():
    pairs = list(iter_marketplace_entries(_mixed_document(), 'elsewhere'))

    assert [(bundle, entry['version']) for bundle, entry in pairs] == [('other', '9.9.9')]


@pytest.mark.parametrize(
    'document',
    [
        None,
        ['not', 'an', 'object'],
        'text',
        17,
        {},
        {'plugins': None},
        {'plugins': ['a', 'list']},
        {'plugins': {}},
        {'plugins': {'plan-marshall@plan-marshall': []}},
        {'plugins': {'plan-marshall@plan-marshall': {'scope': 'user'}}},
        {'plugins': {'plan-marshall@plan-marshall': ['text', 17, None]}},
    ],
    ids=[
        'null-document',
        'list-document',
        'string-document',
        'number-document',
        'no-plugins-member',
        'null-plugins',
        'list-plugins',
        'empty-plugins',
        'empty-entry-list',
        'object-instead-of-entry-list',
        'no-object-entry',
    ],
)
def test_malformed_document_yields_nothing_and_raises_nothing(document):
    assert list(iter_marketplace_entries(document)) == []


# ---------------------------------------------------------------------------
# read_registry is pinned to the walk
# ---------------------------------------------------------------------------


def test_read_registry_rows_line_up_with_the_walk_index_for_index(tmp_path):
    # Arrange
    registry = tmp_path / 'installed_plugins.json'
    registry.write_text(json.dumps(_mixed_document()), encoding='utf-8')
    pairs = list(iter_marketplace_entries(_mixed_document()))

    # Act
    state, rows = read_registry(registry)

    # Assert — one row per pair, same bundle, same pinned version, same position.
    assert state == REGISTRY_OK
    assert [(row['bundle'], row['version']) for row in rows] == [(bundle, entry['version']) for bundle, entry in pairs]


def test_read_registry_reads_exactly_what_the_walk_yields(tmp_path, monkeypatch):
    # Arrange — a walk that yields one entry the document does not even hold.
    registry = tmp_path / 'installed_plugins.json'
    registry.write_text(json.dumps(_mixed_document()), encoding='utf-8')
    seen: list[tuple[object, str]] = []

    def substituted_walk(document, marketplace):
        seen.append((document, marketplace))
        yield 'substituted', _entry('7.7.7')

    monkeypatch.setattr(plugin_registry, 'iter_marketplace_entries', substituted_walk)

    # Act
    state, rows = read_registry(registry, marketplace='elsewhere')

    # Assert — the rows are the walk's output and nothing else; the reader
    # handed it the parsed document and the marketplace it was asked for.
    assert state == REGISTRY_OK
    assert rows == [{'bundle': 'substituted', 'scope': 'user', 'install_path_version': '7.7.7', 'version': '7.7.7'}]
    assert seen == [(_mixed_document(), 'elsewhere')]


def test_read_registry_reports_no_entry_when_the_walk_yields_nothing(tmp_path, monkeypatch):
    # Arrange — a registry full of entries, and a walk that yields none of them.
    registry = tmp_path / 'installed_plugins.json'
    registry.write_text(json.dumps(_mixed_document()), encoding='utf-8')
    monkeypatch.setattr(plugin_registry, 'iter_marketplace_entries', lambda *_args: iter(()))

    # Act / Assert
    assert read_registry(registry) == (REGISTRY_NO_PLAN_MARSHALL_ENTRY, [])


def _reads_registry_structure(node: ast.AST) -> bool:
    """Whether ``node`` looks up the ``plugins`` member or names the key separator."""
    if isinstance(node, ast.Constant):
        return node.value == '@'
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == 'get'
        and any(isinstance(arg, ast.Constant) and arg.value == 'plugins' for arg in node.args)
    )


def test_module_walks_the_plugins_member_in_one_function_only():
    """A second filter would have to look the ``plugins`` member up or split a key itself."""
    # Arrange
    tree = ast.parse(Path(plugin_registry.__file__).read_text(encoding='utf-8'))

    # Act — every function that does either.
    readers = {
        function.name
        for function in ast.walk(tree)
        if isinstance(function, ast.FunctionDef)
        for node in ast.walk(function)
        if _reads_registry_structure(node)
    }

    # Assert
    assert readers == {'iter_marketplace_entries'}
