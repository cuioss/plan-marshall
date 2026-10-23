#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the shared OpenCode session reader.

Drive ``_opencode_sessions`` directly against tmp databases for both schema
tiers: path resolution, the read-only connection, the two-tier gate, the
``parent_id`` walk, tree totals, per-window usage and the sub-agent listing.

Every unavailable path is pinned to its NAMED reason with no bucket present —
the no-fabricated-zero control is that ``0`` is only ever a measured value.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from conftest import get_script_path

SCRIPT_PATH = get_script_path('plan-marshall', 'platform-runtime', 'runtime_info.py')
SCRIPTS_DIR = SCRIPT_PATH.parent

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import _opencode_sessions as opencode_sessions

#: Fixed clock so a window boundary is never a function of the wall clock.
_BASE = datetime(2026, 10, 20, 10, 0, tzinfo=UTC)

#: Columns a tier-2 ``session_v2`` carries on top of the tier-1 trio.
_TIER2_SESSION_DDL = (
    'CREATE TABLE session_v2 ('
    'id TEXT, parent_id TEXT, model TEXT, directory TEXT,'
    ' tokens_input INTEGER, tokens_output INTEGER,'
    ' tokens_cache_read INTEGER, tokens_cache_write INTEGER, cost REAL)'
)


def _at(minutes: int) -> int:
    """Return the epoch-millisecond stamp *minutes* after the fixed clock."""
    return int((_BASE + timedelta(minutes=minutes)).timestamp() * 1000)


def _iso(minutes: int) -> str:
    """Return the ISO stamp *minutes* after the fixed clock."""
    return (_BASE + timedelta(minutes=minutes)).isoformat()


def _model(model_id: str, variant: str = 'high', provider: str = 'opencode') -> str:
    """Return a ``session_v2.model`` cell shaped as OpenCode writes it."""
    return json.dumps({'id': model_id, 'providerID': provider, 'variant': variant})


def _create_tier1_db(path: Path, rows: list[tuple[str, str | None, str]]) -> None:
    """Create a tier-1 store: ``session_v2(id, parent_id, model)`` only."""
    connection = sqlite3.connect(path)
    try:
        connection.execute('CREATE TABLE session_v2 (id TEXT, parent_id TEXT, model TEXT)')
        connection.executemany('INSERT INTO session_v2 (id, parent_id, model) VALUES (?, ?, ?)', rows)
        connection.commit()
    finally:
        connection.close()


def _create_tier2_db(
    path: Path,
    sessions: list[tuple[str, str | None, int, int, int, int, float]],
    messages: Sequence[tuple[str, str, int | str, Any]],
) -> None:
    """Create a tier-2 store with token columns and a ``session_message`` table.

    Args:
        path: Database file to create.
        sessions: ``(id, parent_id, input, output, cache_read, cache_write, cost)``
            rows; the model cell is fixed so a measurement assertion can read it.
        messages: ``(session_id, type, time_created, data)`` rows, where
            ``time_created`` is either the millisecond integer the store uses or
            an ISO-8601 TEXT stamp (both shapes exist in real stores).
    """
    connection = sqlite3.connect(path)
    try:
        connection.execute(_TIER2_SESSION_DDL)
        connection.executemany(
            'INSERT INTO session_v2 (id, parent_id, model, directory, tokens_input,'
            ' tokens_output, tokens_cache_read, tokens_cache_write, cost)'
            ' VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
            [
                (session_id, parent_id, _model('deepseek-v4.1-flash'), '/tmp/worktree', *usage)
                for session_id, parent_id, *usage in sessions
            ],
        )
        connection.execute('CREATE TABLE session_message (session_id TEXT, type TEXT, time_created INTEGER, data TEXT)')
        connection.executemany(
            'INSERT INTO session_message (session_id, type, time_created, data) VALUES (?, ?, ?, ?)',
            [
                (session_id, message_type, created, data if isinstance(data, str) else json.dumps(data))
                for session_id, message_type, created, data in messages
            ],
        )
        connection.commit()
    finally:
        connection.close()


# =============================================================================
# Path resolution
# =============================================================================


def test_db_path_prefers_the_primary_variable(tmp_path: Path) -> None:
    """``OPENCODE_DB`` outranks the retained ``OPENCODE_DB_PATH`` override."""
    env = {
        'OPENCODE_DB': str(tmp_path / 'primary.db'),
        'OPENCODE_DB_PATH': str(tmp_path / 'override.db'),
        'XDG_DATA_HOME': str(tmp_path / 'xdg'),
    }

    assert opencode_sessions.db_path(env) == tmp_path / 'primary.db'


def test_db_path_falls_back_to_the_retained_override(tmp_path: Path) -> None:
    """With no primary variable the retained test override supplies the path."""
    env = {
        'OPENCODE_DB_PATH': str(tmp_path / 'override.db'),
        'XDG_DATA_HOME': str(tmp_path / 'xdg'),
    }

    assert opencode_sessions.db_path(env) == tmp_path / 'override.db'


def test_db_path_uses_the_xdg_data_home(tmp_path: Path) -> None:
    """With neither override set the XDG data home is the parent."""
    env = {'XDG_DATA_HOME': str(tmp_path / 'xdg')}

    assert opencode_sessions.db_path(env) == tmp_path / 'xdg' / 'opencode' / 'opencode.db'


def test_db_path_falls_back_to_the_home_directory(tmp_path: Path, monkeypatch: Any) -> None:
    """With no variable set the home-directory default applies."""
    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.delenv('OPENCODE_DB', raising=False)
    monkeypatch.delenv('OPENCODE_DB_PATH', raising=False)
    monkeypatch.delenv('XDG_DATA_HOME', raising=False)

    assert opencode_sessions.db_path() == tmp_path / '.local' / 'share' / 'opencode' / 'opencode.db'


def test_db_path_expands_a_tilde_override(tmp_path: Path, monkeypatch: Any) -> None:
    """A ``~``-relative override resolves against the home directory."""
    monkeypatch.setenv('HOME', str(tmp_path))

    assert opencode_sessions.db_path({'OPENCODE_DB': '~/custom.db'}) == tmp_path / 'custom.db'


def test_probe_names_db_not_found_for_an_unexpandable_tilde_path() -> None:
    """An unresolvable ``~user`` prefix degrades to ``db_not_found``, never raises."""
    result = opencode_sessions.probe('~nosuchuser/opencode.db')

    assert result == {'ok': False, 'tier': 0, 'reason': 'db_not_found'}


def test_connect_returns_none_for_an_unexpandable_tilde_path() -> None:
    """``connect`` returns ``None`` for an unresolvable ``~user`` prefix, never raises."""
    assert opencode_sessions.connect('~nosuchuser/opencode.db') is None


def test_an_unexpandable_tilde_environment_override_is_never_raised() -> None:
    """The env-reachable path ``OPENCODE_DB=~nosuchuser/...`` returns a named reason."""
    resolved = opencode_sessions.db_path({'OPENCODE_DB': '~nosuchuser/opencode.db'})

    assert opencode_sessions.probe(resolved) == {'ok': False, 'tier': 0, 'reason': 'db_not_found'}


# =============================================================================
# Read-only connection
# =============================================================================


def test_connection_is_read_only_and_leaves_the_file_bytes_unchanged(tmp_path: Path) -> None:
    """A write through the reader's connection fails and mutates nothing."""
    db_path = tmp_path / 'opencode.db'
    _create_tier1_db(db_path, [('ses-root', None, _model('m'))])
    before = db_path.read_bytes()

    connection = opencode_sessions.connect(db_path)

    assert connection is not None
    try:
        with pytest.raises(sqlite3.OperationalError):
            connection.execute('INSERT INTO session_v2 (id, parent_id, model) VALUES (?, ?, ?)', ('x', None, '{}'))
    finally:
        connection.close()
    assert db_path.read_bytes() == before


# =============================================================================
# Schema gate
# =============================================================================


def test_missing_database_names_db_not_found(tmp_path: Path) -> None:
    """An absent file yields ``db_not_found``, never a readable empty store."""
    result = opencode_sessions.probe(tmp_path / 'absent.db')

    assert result['ok'] is False
    assert result['tier'] == 0
    assert result['reason'] == 'db_not_found'


def test_unreadable_database_names_db_unreadable(tmp_path: Path) -> None:
    """A file carrying no SQLite schema yields ``db_unreadable``."""
    db_path = tmp_path / 'garbage.db'
    db_path.write_bytes(b'this is not a sqlite database')

    result = opencode_sessions.probe(db_path)

    assert result['ok'] is False
    assert result['reason'] == 'db_unreadable'


def test_tier1_database_probes_as_tier_model(tmp_path: Path) -> None:
    """A ``session_v2(id, parent_id, model)``-only store reaches tier 1."""
    db_path = tmp_path / 'opencode.db'
    _create_tier1_db(db_path, [('ses-root', None, _model('m'))])

    result = opencode_sessions.probe(db_path)

    assert result == {'ok': True, 'tier': opencode_sessions.TIER_MODEL, 'reason': None}


def test_tier2_database_probes_as_tier_totals(tmp_path: Path) -> None:
    """A store carrying the token columns and message table reaches tier 2."""
    db_path = tmp_path / 'opencode.db'
    _create_tier2_db(db_path, [('ses-root', None, 1, 2, 3, 4, 0.5)], [])

    result = opencode_sessions.probe(db_path)

    assert result == {'ok': True, 'tier': opencode_sessions.TIER_TOTALS, 'reason': None}


def test_database_without_the_session_table_is_schema_unsupported(tmp_path: Path) -> None:
    """A readable database carrying no ``session_v2`` is unsupported, not empty."""
    db_path = tmp_path / 'other.db'
    connection = sqlite3.connect(db_path)
    try:
        connection.execute('CREATE TABLE unrelated (id TEXT)')
        connection.commit()
    finally:
        connection.close()

    result = opencode_sessions.probe(db_path)

    assert result['ok'] is False
    assert result['reason'] == 'schema_unsupported'


# =============================================================================
# Rows, root and tree
# =============================================================================


def _chain_rows() -> dict[str, tuple[str | None, object, str | None]]:
    """Return a three-level ``root -> mid -> leaf`` row mapping."""
    return {
        'ses-root': (None, _model('m'), None),
        'ses-mid': ('ses-root', _model('m'), None),
        'ses-leaf': ('ses-mid', _model('m'), None),
    }


def test_read_session_rows_maps_id_to_parent_and_model(tmp_path: Path) -> None:
    """The tier-1 read returns id → ``(parent_id, model)`` pairs."""
    db_path = tmp_path / 'opencode.db'
    _create_tier1_db(db_path, [('ses-root', None, _model('m')), ('ses-leaf', 'ses-root', _model('m'))])

    reading = opencode_sessions.read_session_rows(db_path)

    assert reading['ok'] is True
    assert reading['rows']['ses-leaf'][0] == 'ses-root'
    assert reading['rows']['ses-root'][0] is None


def test_session_root_walks_a_multi_level_parent_chain() -> None:
    """The root is reached through every intermediate ``parent_id`` hop."""
    rows = _chain_rows()

    assert opencode_sessions.session_root('ses-leaf', rows) == 'ses-root'
    assert opencode_sessions.session_root('ses-root', rows) == 'ses-root'


def test_session_root_terminates_on_a_malformed_cycle() -> None:
    """A cyclic ``parent_id`` chain returns a member instead of hanging."""
    rows: dict[str, tuple[str | None, object, str | None]] = {
        'ses-a': ('ses-b', _model('m'), None),
        'ses-b': ('ses-a', _model('m'), None),
    }

    assert opencode_sessions.session_root('ses-a', rows) in {'ses-a', 'ses-b'}


def test_session_root_names_no_row_for_an_unknown_session() -> None:
    """An id that names no row has no root — the caller has nothing to measure."""
    assert opencode_sessions.session_root('ses-absent', _chain_rows()) is None


def test_session_tree_returns_the_root_and_every_descendant() -> None:
    """The walk covers the root plus all transitive descendants."""
    rows = {**_chain_rows(), 'ses-sibling': ('ses-root', _model('m'), None)}

    tree = opencode_sessions.session_tree('ses-root', rows)

    assert set(tree) == {'ses-root', 'ses-mid', 'ses-leaf', 'ses-sibling'}


# =============================================================================
# Tree totals
# =============================================================================


def test_session_totals_sums_the_token_columns_over_the_tree(tmp_path: Path) -> None:
    """Totals sum the ``tokens_*`` / ``cost`` columns and map every key."""
    db_path = tmp_path / 'opencode.db'
    _create_tier2_db(
        db_path,
        [
            ('ses-root', None, 10, 20, 3, 4, 0.5),
            ('ses-child', 'ses-root', 100, 200, 30, 40, 1.5),
            ('ses-other', None, 7, 7, 7, 7, 7.0),
        ],
        [],
    )

    totals = opencode_sessions.session_totals(db_path, 'ses-child')

    assert totals['ok'] is True
    assert totals['root'] == 'ses-root'
    assert totals['sessions'] == 2
    assert totals['input_tokens'] == 110
    assert totals['output_tokens'] == 220
    assert totals['cache_read_input_tokens'] == 33
    assert totals['cache_creation_input_tokens'] == 44
    assert totals['cost'] == 2.0


def test_session_totals_refuses_a_tier1_store_rather_than_an_empty_bucket(tmp_path: Path) -> None:
    """A tier-1 store answers ``schema_unsupported`` and carries no bucket."""
    db_path = tmp_path / 'opencode.db'
    _create_tier1_db(db_path, [('ses-root', None, _model('m'))])

    totals = opencode_sessions.session_totals(db_path, 'ses-root')

    assert totals == {'ok': False, 'reason': 'schema_unsupported'}


def test_session_totals_covers_every_tree_member_across_chunk_boundaries(tmp_path: Path, monkeypatch: Any) -> None:
    """A tree split over several ``IN`` statements still sums every member once."""
    monkeypatch.setattr(opencode_sessions, '_SQL_VARIABLE_BUDGET', 2)
    db_path = tmp_path / 'opencode.db'
    _create_tier2_db(
        db_path,
        [
            ('ses-root', None, 1, 1, 1, 1, 0.5),
            ('ses-a', 'ses-root', 2, 2, 2, 2, 1.0),
            ('ses-b', 'ses-a', 4, 4, 4, 4, 2.0),
            ('ses-other', None, 64, 64, 64, 64, 64.0),
        ],
        [],
    )

    totals = opencode_sessions.session_totals(db_path, 'ses-root')

    assert totals['sessions'] == 3
    assert totals['input_tokens'] == 7
    assert totals['cost'] == 3.5


# =============================================================================
# Per-window usage
# =============================================================================


def _window_messages() -> list[tuple[str, str, int, Any]]:
    """Return messages inside and outside one ``[0, 30)`` minute window."""
    return [
        (
            'ses-root',
            'assistant',
            _at(5),
            {'tokens': {'input': 10, 'output': 20, 'cache': {'read': 3, 'write': 4}}, 'cost': 0.5},
        ),
        (
            'ses-child',
            'assistant',
            _at(10),
            {'tokens': {'input': 100, 'output': 200, 'cache': {'read': 30, 'write': 40}}, 'cost': 1.5},
        ),
        ('ses-child', 'tool', _at(12), {'tool': 'bash', 'state': {'status': 'completed'}}),
        (
            'ses-child',
            'assistant',
            _at(40),
            {'tokens': {'input': 999, 'output': 999, 'cache': {'read': 999, 'write': 999}}, 'cost': 99.0},
        ),
    ]


def test_window_usage_splits_main_from_subagent_and_maps_cache_write(tmp_path: Path) -> None:
    """One window splits the root's usage from its descendants', key by key."""
    db_path = tmp_path / 'opencode.db'
    _create_tier2_db(
        db_path,
        [
            ('ses-root', None, 10, 20, 3, 4, 0.5),
            ('ses-child', 'ses-root', 100, 200, 30, 40, 1.5),
        ],
        _window_messages(),
    )

    usage = opencode_sessions.window_usage(db_path, 'ses-root', [('5-execute', _iso(0), _iso(30))])

    assert usage['ok'] is True
    assert usage['root'] == 'ses-root'
    assert usage['subagent_sessions'] == 1
    main = usage['windows'][0]['main']
    subagent = usage['windows'][0]['subagent']
    assert main['input_tokens'] == 10
    assert main['output_tokens'] == 20
    assert main['cache_read_input_tokens'] == 3
    assert main['cache_creation_input_tokens'] == 4
    assert main['cost'] == 0.5
    assert main['message_count'] == 1
    assert subagent['input_tokens'] == 100
    assert subagent['output_tokens'] == 200
    assert subagent['cache_read_input_tokens'] == 30
    # tokens.cache.write lands in cache_creation_input_tokens on the sub-agent row.
    assert subagent['cache_creation_input_tokens'] == 40
    assert subagent['cost'] == 1.5
    assert subagent['message_count'] == 1
    assert subagent['tool_uses'] == 1
    assert subagent['duration_ms'] > 0


def test_window_usage_puts_a_boundary_timestamp_in_the_newer_window(tmp_path: Path) -> None:
    """The window is half-open, so the start instant belongs to it, not the previous one."""
    db_path = tmp_path / 'opencode.db'
    _create_tier2_db(
        db_path,
        [('ses-root', None, 0, 0, 0, 0, 0.0)],
        [('ses-root', 'assistant', _at(30), {'tokens': {'input': 5}, 'cost': 0.0})],
    )

    usage = opencode_sessions.window_usage(
        db_path,
        'ses-root',
        [('first', _iso(0), _iso(30)), ('second', _iso(30), _iso(60))],
    )

    assert usage['windows'][0]['main']['input_tokens'] == 0
    assert usage['windows'][1]['main']['input_tokens'] == 5


def test_window_usage_refuses_a_tier1_store_rather_than_an_empty_bucket(tmp_path: Path) -> None:
    """A tier-1 store answers ``schema_unsupported`` and carries no windows."""
    db_path = tmp_path / 'opencode.db'
    _create_tier1_db(db_path, [('ses-root', None, _model('m'))])

    usage = opencode_sessions.window_usage(db_path, 'ses-root', [('5-execute', _iso(0), _iso(30))])

    assert usage == {'ok': False, 'reason': 'schema_unsupported'}


def test_window_usage_attributes_a_message_on_a_start_millisecond_that_rounds_up(tmp_path: Path) -> None:
    """A start millisecond whose float scale rounds up still attributes its message.

    ``datetime.timestamp()`` is a float, so the SQL millisecond bound can land a
    fraction ABOVE the exact millisecond of the window start (2038-07-25's
    ``.313`` second is the reported case: ``low * 1000.0`` is
    ``2163638855313.0002``). The one-millisecond slack keeps that row inside the
    SQL envelope, and Python's half-open attribution still places it at the start.
    """
    start_iso = '2038-07-25T02:47:35.313000+00:00'
    start_moment = datetime.fromisoformat(start_iso)
    exact_ms = int(start_moment.timestamp() * 1000)
    # Guard the premise: this start is one whose scaled float rounds up.
    assert start_moment.timestamp() * 1000.0 > exact_ms
    db_path = tmp_path / 'opencode.db'
    _create_tier2_db(
        db_path,
        [('ses-root', None, 0, 0, 0, 0, 0.0)],
        [('ses-root', 'assistant', exact_ms, {'tokens': {'input': 7}})],
    )

    usage = opencode_sessions.window_usage(
        db_path,
        'ses-root',
        [('round-up', start_iso, '2038-07-25T03:47:35.313000+00:00')],
    )

    main = usage['windows'][0]['main']
    assert main['input_tokens'] == 7
    assert main['message_count'] == 1


def test_window_usage_attributes_every_in_window_message_through_the_filtered_read(tmp_path: Path) -> None:
    """Every in-window message is summed across the tree; its neighbours are not."""
    db_path = tmp_path / 'opencode.db'
    _create_tier2_db(
        db_path,
        [
            ('ses-root', None, 0, 0, 0, 0, 0.0),
            ('ses-child', 'ses-root', 0, 0, 0, 0, 0.0),
        ],
        [
            ('ses-root', 'assistant', _at(0), {'tokens': {'input': 1}}),
            ('ses-root', 'assistant', _at(29), {'tokens': {'input': 2}}),
            ('ses-child', 'assistant', _at(15), {'tokens': {'input': 4}}),
            ('ses-root', 'assistant', _at(30), {'tokens': {'input': 8}}),
            ('ses-root', 'assistant', _at(-1), {'tokens': {'input': 16}}),
        ],
    )

    usage = opencode_sessions.window_usage(db_path, 'ses-root', [('first', _iso(0), _iso(30))])

    main = usage['windows'][0]['main']
    assert main['input_tokens'] == 3
    assert main['message_count'] == 2
    assert usage['windows'][0]['subagent']['input_tokens'] == 4
    assert usage['windows'][0]['subagent']['message_count'] == 1


def test_window_usage_ignores_a_message_from_a_session_outside_the_member_set(tmp_path: Path) -> None:
    """A same-instant message from a session outside the tree contributes nothing."""
    db_path = tmp_path / 'opencode.db'
    _create_tier2_db(
        db_path,
        [('ses-root', None, 0, 0, 0, 0, 0.0)],
        [
            ('ses-root', 'assistant', _at(5), {'tokens': {'input': 1}}),
            ('ses-foreign', 'assistant', _at(5), {'tokens': {'input': 500}}),
        ],
    )

    usage = opencode_sessions.window_usage(db_path, 'ses-root', [('first', _iso(0), _iso(30))])

    assert usage['windows'][0]['main']['input_tokens'] == 1
    assert usage['windows'][0]['main']['message_count'] == 1
    assert usage['windows'][0]['subagent']['message_count'] == 0
    assert usage['subagent_sessions'] == 0


def test_window_usage_keeps_a_text_timestamp_for_the_parser(tmp_path: Path) -> None:
    """An ISO-8601 stamp is still attributed — the pre-filter leaves TEXT to the parser."""
    db_path = tmp_path / 'opencode.db'
    _create_tier2_db(
        db_path,
        [('ses-root', None, 0, 0, 0, 0, 0.0)],
        [('ses-root', 'assistant', _iso(5), {'tokens': {'input': 6}})],
    )

    usage = opencode_sessions.window_usage(db_path, 'ses-root', [('first', _iso(0), _iso(30))])

    assert usage['windows'][0]['main']['input_tokens'] == 6
    assert usage['windows'][0]['main']['message_count'] == 1


# =============================================================================
# Tool use, reasoning, cost and spans — the store's real shape
# =============================================================================


def test_window_usage_counts_tool_parts_in_an_assistant_messages_content(tmp_path: Path) -> None:
    """Tool use is counted from ``content[]`` parts of type ``tool``.

    The store records a tool call as a part of the assistant message's
    ``content`` array; it carries no ``session_message`` row type containing
    ``tool``. Counting the row type therefore reported a measured ``0`` for every
    phase of the plan that shipped the reader.
    """
    db_path = tmp_path / 'opencode.db'
    _create_tier2_db(
        db_path,
        [('ses-root', None, 10, 20, 3, 4, 0.5), ('ses-child', 'ses-root', 100, 200, 30, 40, 1.5)],
        [
            (
                'ses-child',
                'assistant',
                _at(10),
                {
                    'tokens': {'input': 100, 'output': 200},
                    'cost': 1.5,
                    'content': [
                        {'type': 'text', 'text': 'running'},
                        {'type': 'tool', 'tool': 'bash', 'state': {'status': 'completed'}},
                        {'type': 'tool', 'tool': 'read', 'state': {'status': 'completed'}},
                    ],
                },
            ),
            (
                'ses-root',
                'assistant',
                _at(11),
                {
                    'tokens': {'input': 10, 'output': 20},
                    'cost': 0.5,
                    'content': [{'type': 'tool', 'tool': 'write'}],
                },
            ),
        ],
    )

    usage = opencode_sessions.window_usage(db_path, 'ses-root', [('5-execute', _iso(0), _iso(30))])

    window = usage['windows'][0]
    assert window['subagent']['tool_uses'] == 2
    assert window['main']['tool_uses'] == 1


def test_window_usage_counts_a_legacy_row_typed_tool_event(tmp_path: Path) -> None:
    """A row-typed tool event is still counted when no content array answers.

    The legacy shape is honoured, but only as a fallback: a bucket whose assistant
    message carried a content array counts its parts, never the row types too.
    """
    db_path = tmp_path / 'opencode.db'
    _create_tier2_db(
        db_path,
        [('ses-root', None, 0, 0, 0, 0, 0.0), ('ses-child', 'ses-root', 0, 0, 0, 0, 0.0)],
        [
            ('ses-child', 'tool', _at(5), {'tool': 'bash'}),
            ('ses-child', 'tool', _at(6), {'tool': 'read'}),
        ],
    )

    usage = opencode_sessions.window_usage(db_path, 'ses-root', [('5-execute', _iso(0), _iso(30))])

    assert usage['windows'][0]['subagent']['tool_uses'] == 2


def test_window_usage_does_not_count_a_call_recorded_in_both_shapes(tmp_path: Path) -> None:
    """One call recorded as a content part AND a row type is counted once."""
    db_path = tmp_path / 'opencode.db'
    _create_tier2_db(
        db_path,
        [('ses-root', None, 0, 0, 0, 0, 0.0), ('ses-child', 'ses-root', 0, 0, 0, 0, 0.0)],
        [
            ('ses-child', 'assistant', _at(5), {'tokens': {'input': 1}, 'content': [{'type': 'tool'}]}),
            ('ses-child', 'tool', _at(6), {'tool': 'bash'}),
        ],
    )

    usage = opencode_sessions.window_usage(db_path, 'ses-root', [('5-execute', _iso(0), _iso(30))])

    assert usage['windows'][0]['subagent']['tool_uses'] == 1


def test_window_usage_omits_tool_uses_when_the_store_cannot_answer(tmp_path: Path) -> None:
    """A window whose messages carry no ``content`` array omits ``tool_uses``.

    ``0`` is only ever a measured value: a store that records no content parts
    has not told the reader that no tool ran.
    """
    db_path = tmp_path / 'opencode.db'
    _create_tier2_db(
        db_path,
        [('ses-root', None, 10, 20, 3, 4, 0.5)],
        [('ses-root', 'assistant', _at(5), {'tokens': {'input': 10, 'output': 20}, 'cost': 0.5})],
    )

    usage = opencode_sessions.window_usage(db_path, 'ses-root', [('5-execute', _iso(0), _iso(30))])

    bucket = usage['windows'][0]['main']
    assert 'tool_uses' not in bucket
    assert bucket['message_count'] == 1


def test_window_usage_carries_reasoning_tokens_from_the_message(tmp_path: Path) -> None:
    """``tokens.reasoning`` is read into its own normalized bucket.

    The store keeps reasoning apart from ``tokens.output`` (``session_v2`` carries
    a distinct ``tokens_reasoning`` column), so folding it into output would
    double-count it.
    """
    db_path = tmp_path / 'opencode.db'
    _create_tier2_db(
        db_path,
        [('ses-root', None, 10, 20, 3, 4, 0.5)],
        [
            (
                'ses-root',
                'assistant',
                _at(5),
                {'tokens': {'input': 10, 'output': 20, 'reasoning': 7}, 'cost': 0.5},
            )
        ],
    )

    usage = opencode_sessions.window_usage(db_path, 'ses-root', [('5-execute', _iso(0), _iso(30))])

    assert usage['windows'][0]['main']['reasoning_tokens'] == 7


def test_window_usage_sums_each_subagent_sessions_own_span(tmp_path: Path) -> None:
    """Two disjoint sub-agent spans sum; the outer span over them is not a duration.

    A phase whose sub-agents ran minutes each reported a 20.9-hour
    ``subagent_duration_ms`` because the figure was the first sub-agent message to
    the last one, not the time any sub-agent was actually running.
    """
    db_path = tmp_path / 'opencode.db'
    _create_tier2_db(
        db_path,
        [
            ('ses-root', None, 0, 0, 0, 0, 0.0),
            ('ses-child-a', 'ses-root', 0, 0, 0, 0, 0.0),
            ('ses-child-b', 'ses-root', 0, 0, 0, 0, 0.0),
        ],
        [
            ('ses-child-a', 'assistant', _at(1), {'tokens': {'input': 1}}),
            ('ses-child-a', 'assistant', _at(5), {'tokens': {'input': 1}}),
            ('ses-child-b', 'assistant', _at(10), {'tokens': {'input': 1}}),
            ('ses-child-b', 'assistant', _at(12), {'tokens': {'input': 1}}),
        ],
    )

    usage = opencode_sessions.window_usage(db_path, 'ses-root', [('5-execute', _iso(0), _iso(30))])

    subagent = usage['windows'][0]['subagent']
    assert subagent['duration_ms'] == (4 + 2) * 60 * 1000
    assert subagent['sessions'] == 2


# =============================================================================
# Bounded root resolution
# =============================================================================


def _create_directory_db(path: Path, rows: list[tuple[str, str | None, str | None]]) -> None:
    """Create a tier-1 store whose ``session_v2`` carries the directory column."""
    connection = sqlite3.connect(path)
    try:
        connection.execute('CREATE TABLE session_v2 (id TEXT, parent_id TEXT, model TEXT, directory TEXT)')
        connection.executemany(
            'INSERT INTO session_v2 (id, parent_id, model, directory) VALUES (?, ?, NULL, ?)',
            rows,
        )
        connection.commit()
    finally:
        connection.close()


def test_resolve_session_root_stops_at_the_session_in_the_plans_directory(tmp_path: Path) -> None:
    """The climb stops at the outermost ancestor started in the plan's worktree.

    An operator's long-lived outer session is a common parent of the plan's
    driving session; taking it as the root pulls every unrelated descendant into
    the measurement.
    """
    db_path = tmp_path / 'opencode.db'
    worktree = tmp_path / 'worktree'
    _create_directory_db(
        db_path,
        [
            ('ses-outer', None, str(tmp_path)),
            ('ses-plan', 'ses-outer', str(worktree)),
            ('ses-subagent', 'ses-plan', str(worktree)),
            ('ses-elsewhere', 'ses-outer', str(tmp_path / 'other')),
        ],
    )

    bounded = opencode_sessions.resolve_session_root(db_path, 'ses-subagent', directory=str(worktree))
    unbounded = opencode_sessions.resolve_session_root(db_path, 'ses-subagent')

    assert bounded == {'ok': True, 'root': 'ses-plan'}
    assert unbounded == {'ok': True, 'root': 'ses-outer'}
    reading = opencode_sessions.read_session_rows(db_path)
    tree = opencode_sessions.session_tree('ses-plan', reading['rows'])
    assert 'ses-elsewhere' not in tree


def test_resolve_session_root_names_an_unknown_session(tmp_path: Path) -> None:
    """An id naming no row reports the named reason, never a fabricated root."""
    db_path = tmp_path / 'opencode.db'
    _create_directory_db(db_path, [('ses-root', None, str(tmp_path))])

    assert opencode_sessions.resolve_session_root(db_path, 'ses-absent') == {
        'ok': False,
        'reason': 'session_not_found',
    }


def test_resolve_session_root_names_an_unavailable_store(tmp_path: Path) -> None:
    """An absent store declines with the reader's named reason."""
    assert opencode_sessions.resolve_session_root(tmp_path / 'absent.db', 'ses-root') == {
        'ok': False,
        'reason': 'db_not_found',
    }


# =============================================================================
# Sub-agent listing
# =============================================================================


def test_list_subagents_carries_the_parsed_header(tmp_path: Path) -> None:
    """Each descendant is listed with the ``name:`` / ``plan_id:`` header."""
    db_path = tmp_path / 'opencode.db'
    _create_tier2_db(
        db_path,
        [
            ('ses-root', None, 0, 0, 0, 0, 0.0),
            ('ses-child', 'ses-root', 0, 0, 0, 0, 0.0),
        ],
        [
            ('ses-root', 'user', _at(0), {'text': 'name: main\nthe operator prompt'}),
            (
                'ses-child',
                'user',
                _at(1),
                {'text': 'name: phase-5-execute\nplan_id: lb-49-opencode-measurement\n\nbody'},
            ),
        ],
    )

    listing = opencode_sessions.list_subagents(db_path, 'ses-root')

    assert listing['ok'] is True
    assert listing['subagents'] == [
        {
            'session_id': 'ses-child',
            'name': 'phase-5-execute',
            'plan_id': 'lb-49-opencode-measurement',
        }
    ]


def test_list_subagents_excludes_the_root_and_omits_an_absent_header(tmp_path: Path) -> None:
    """The root is not a sub-agent, and a headerless descendant carries no key."""
    db_path = tmp_path / 'opencode.db'
    _create_tier2_db(
        db_path,
        [
            ('ses-root', None, 0, 0, 0, 0, 0.0),
            ('ses-child', 'ses-root', 0, 0, 0, 0, 0.0),
        ],
        [('ses-child', 'user', _at(1), {'text': 'no header here'})],
    )

    listing = opencode_sessions.list_subagents(db_path, 'ses-root')

    assert listing['subagents'] == [{'session_id': 'ses-child'}]


# =============================================================================
# No-fabricated-zero control
# =============================================================================


@pytest.mark.parametrize(
    ('call', 'absent_key'),
    [
        (lambda path: opencode_sessions.read_session_rows(path), 'rows'),
        (lambda path: opencode_sessions.session_totals(path, 'ses-root'), 'input_tokens'),
        (lambda path: opencode_sessions.window_usage(path, 'ses-root', []), 'windows'),
        (lambda path: opencode_sessions.list_subagents(path, 'ses-root'), 'subagents'),
    ],
)
def test_every_unavailable_path_names_its_reason_and_carries_no_bucket(
    tmp_path: Path,
    call: Any,
    absent_key: str,
) -> None:
    """An unavailable source returns a reason and no zero-valued bucket at all."""
    result = call(tmp_path / 'absent.db')

    assert result['ok'] is False
    assert result['reason'] == 'db_not_found'
    assert absent_key not in result
    assert 'cost' not in result
    assert 'input_tokens' not in result


def test_an_unknown_session_names_its_reason_and_carries_no_bucket(tmp_path: Path) -> None:
    """A session id naming no row reports ``session_not_found``, never a zero."""
    db_path = tmp_path / 'opencode.db'
    _create_tier2_db(db_path, [('ses-root', None, 1, 1, 1, 1, 0.1)], [])

    totals = opencode_sessions.session_totals(db_path, 'ses-absent')
    usage = opencode_sessions.window_usage(db_path, 'ses-absent', [('5-execute', _iso(0), _iso(30))])

    assert totals == {'ok': False, 'reason': 'session_not_found'}
    assert usage == {'ok': False, 'reason': 'session_not_found'}
