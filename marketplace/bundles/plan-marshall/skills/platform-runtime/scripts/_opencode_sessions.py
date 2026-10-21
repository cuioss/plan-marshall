#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Read-only reader over the OpenCode session store (``opencode.db``).

The single home of every SESSION read of the OpenCode database: path resolution,
the read-only connection, the two-tier schema gate, the ``parent_id`` walk, tree
totals, per-window usage sums and the sub-agent listing. ``runtime_info``
measures the model through it and ``opencode_runtime`` serves session identity
and normalized tokens through it, so neither of them opens or parses the
session tables itself. The one separate read is the persisted-permission scan in
``opencode_runtime``, which inspects the operator's ``permission`` table — a
governance surface with its own schema, not a session read.

Two schema tiers, because the store evolves and a reader must answer from what a
given installation actually carries:

- **tier 1** — ``session_v2(id, parent_id, model)``. Everything the model
  measurement needs, and nothing more, so a database carrying no message table
  still measures its model.
- **tier 2** — tier 1 plus ``session_v2.directory`` and the ``tokens_*`` /
  ``cost`` columns, plus ``session_message(session_id, type, time_created,
  data)``. Gates the totals and window functions alone.

Every unavailable source yields its NAMED reason, never a zero: ``0`` is only
ever a measured value (ADR-009 / ADR-019). No function raises past this module's
boundary and no code path writes — the connection is opened ``mode=ro``.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Configuration constants
# ---------------------------------------------------------------------------

#: Primary environment variable naming the OpenCode session database.
DB_ENV_PRIMARY = 'OPENCODE_DB'

#: Retained test/deployment override, honoured after :data:`DB_ENV_PRIMARY`.
DB_ENV_OVERRIDE = 'OPENCODE_DB_PATH'

#: Path appended to the XDG data home (and to the home-directory fallback).
DB_RELATIVE_PATH = Path('opencode') / 'opencode.db'

#: Named reason: the resolved path names no readable file.
REASON_DB_NOT_FOUND = 'db_not_found'

#: Named reason: the file exists but cannot be opened or queried.
REASON_DB_UNREADABLE = 'db_unreadable'

#: Named reason: the database carries no schema tier this reader understands.
REASON_SCHEMA_UNSUPPORTED = 'schema_unsupported'

#: Named reason: the session id names no row in the tree.
REASON_SESSION_NOT_FOUND = 'session_not_found'

#: Tier reached when only ``session_v2(id, parent_id, model)`` is present.
TIER_MODEL = 1

#: Tier reached when the totals/window schema is present too.
TIER_TOTALS = 2

#: ``session_v2`` token column → normalized usage key, in column order.
TOKEN_COLUMNS: dict[str, str] = {
    'tokens_input': 'input_tokens',
    'tokens_output': 'output_tokens',
    'tokens_cache_read': 'cache_read_input_tokens',
    'tokens_cache_write': 'cache_creation_input_tokens',
}

#: The normalized usage keys, in :data:`TOKEN_COLUMNS` column order.
USAGE_KEYS: tuple[str, ...] = tuple(TOKEN_COLUMNS.values())

#: Columns the tier-1 model read requires.
_TIER1_COLUMNS = frozenset({'id', 'parent_id', 'model'})

#: Columns the tier-2 ``session_v2`` schema requires on top of tier 1.
_TIER2_SESSION_COLUMNS = _TIER1_COLUMNS | {'directory', 'cost', *TOKEN_COLUMNS}

#: Columns the tier-2 ``session_message`` schema requires.
_TIER2_MESSAGE_COLUMNS = frozenset({'session_id', 'type', 'time_created', 'data'})

#: Paths inside an assistant message's ``data.tokens`` → normalized usage key.
_MESSAGE_TOKEN_PATHS: tuple[tuple[tuple[str, ...], str], ...] = (
    (('input',), 'input_tokens'),
    (('output',), 'output_tokens'),
    (('cache', 'read'), 'cache_read_input_tokens'),
    (('cache', 'write'), 'cache_creation_input_tokens'),
)

#: ``name:`` / ``plan_id:`` header lines carried by a dispatched task prompt.
_HEADER_PATTERN = re.compile(r'(?mi)^[ \t]*(name|plan_id)[ \t]*:[ \t]*(\S.*?)[ \t]*$')

#: How many of a session's earliest messages are scanned for its header.
_PROMPT_SCAN_LIMIT = 50

#: Marker a message ``type`` carries when it records tool activity.
_TOOL_TYPE_MARKER = 'tool'

#: Epoch values above this are milliseconds rather than seconds.
_EPOCH_MS_THRESHOLD = 100_000_000_000

#: Bound-variable budget per statement, below SQLite's historical 999 limit.
_SQL_VARIABLE_BUDGET = 900


# ---------------------------------------------------------------------------
# Path resolution and connection
# ---------------------------------------------------------------------------


def db_path(env: Mapping[str, str] | None = None) -> Path:
    """Resolve the OpenCode session database path.

    Resolution order, first non-blank value wins:

    1. ``OPENCODE_DB`` — the primary override;
    2. ``OPENCODE_DB_PATH`` — the retained test/deployment override;
    3. ``$XDG_DATA_HOME/opencode/opencode.db``;
    4. ``~/.local/share/opencode/opencode.db``.

    Every value is ``expanduser``-ed, so a ``~``-relative override resolves.
    This function never raises: an unresolvable home directory falls back to
    ``$HOME`` and then to ``/tmp``.

    Args:
        env: Explicit environment mapping for tests; defaults to ``os.environ``.

    Returns:
        The path the reader will probe. Its existence is not implied.
    """
    source: Mapping[str, str] = env if env is not None else os.environ
    for name in (DB_ENV_PRIMARY, DB_ENV_OVERRIDE):
        value = source.get(name)
        if isinstance(value, str) and value.strip():
            return Path(value.strip()).expanduser()

    xdg_home = source.get('XDG_DATA_HOME')
    if isinstance(xdg_home, str) and xdg_home.strip():
        return Path(xdg_home.strip()).expanduser() / DB_RELATIVE_PATH

    return _home_dir() / '.local' / 'share' / DB_RELATIVE_PATH


def _home_dir() -> Path:
    """Return the current home directory, falling back when it cannot resolve."""
    try:
        return Path.home()
    except (RuntimeError, OSError):
        return Path(os.environ.get('HOME') or '/tmp')


def connect(path: Path | str | None) -> sqlite3.Connection | None:
    """Open *path* read-only (``mode=ro``), or return ``None``.

    The read-only mode is the write-safety boundary: no statement executed on
    the returned connection can mutate the developer's session store. A ``None``
    return means the connection could not be established; callers that need the
    reason call :func:`probe`, which names it.

    Args:
        path: The database file to open.

    Returns:
        An open read-only connection, or ``None`` when one could not be created.
    """
    target = _resolve(path)
    if target is None:
        return None
    try:
        # ``as_uri()`` percent-encodes ``?``, ``#`` and ``%`` in the path, so a
        # filename carrying a URI metacharacter is opened rather than truncated
        # at that character (which would silently read the wrong file or none).
        return sqlite3.connect(f'{Path(target).resolve().as_uri()}?mode=ro', uri=True)
    except (sqlite3.Error, OSError, ValueError):
        return None


def _resolve(path: Path | str | None) -> Path | None:
    """Expand *path* into a ``Path``, or ``None`` when no usable path was given."""
    if path is None:
        return None
    try:
        expanded = Path(path).expanduser()
    except (TypeError, ValueError, OSError):
        return None
    return expanded if str(expanded) else None


def _open(path: Path | str | None) -> tuple[sqlite3.Connection | None, str | None]:
    """Open *path* read-only, naming why when it cannot be opened."""
    target = _resolve(path)
    if target is None:
        return None, REASON_DB_NOT_FOUND
    try:
        if not target.is_file():
            return None, REASON_DB_NOT_FOUND
    except OSError:
        return None, REASON_DB_UNREADABLE
    connection = connect(target)
    if connection is None:
        return None, REASON_DB_UNREADABLE
    return connection, None


def _close(connection: sqlite3.Connection) -> None:
    """Close *connection*, swallowing any close-time error."""
    try:
        connection.close()
    except sqlite3.Error:
        pass


# ---------------------------------------------------------------------------
# Statement budgeting
# ---------------------------------------------------------------------------


def _chunked(values: Sequence[str], size: int) -> list[list[str]]:
    """Split *values* into consecutive chunks of at most *size* entries.

    The caller derives *size* from :data:`_SQL_VARIABLE_BUDGET`, so a statement
    built from one chunk stays below SQLite's bound-variable limit however many
    sessions a tree carries.
    """
    return [list(values[index : index + size]) for index in range(0, len(values), size)]


def _in_clause(column: str, entries: Sequence[str]) -> tuple[str, list[str]]:
    """Return an ``"column" IN (?, ...)`` fragment and its bound values."""
    placeholders = ', '.join('?' for _entry in entries)
    return f'"{column}" IN ({placeholders})', list(entries)


# ---------------------------------------------------------------------------
# Schema gate
# ---------------------------------------------------------------------------


def _table_columns(connection: sqlite3.Connection, table: str) -> set[str] | None:
    """Return *table*'s column names lower-cased, or ``None`` when it is absent."""
    rows = connection.execute(f'PRAGMA table_info("{table}")').fetchall()
    if not rows:
        return None
    return {str(row[1]).lower() for row in rows}


def _probe_connection(connection: sqlite3.Connection) -> tuple[int, str | None]:
    """Return ``(tier, reason)`` for an open connection.

    ``tier`` is 0 when no usable schema was found — in which case ``reason``
    names why — otherwise the highest tier reached: :data:`TIER_MODEL` for a
    ``session_v2(id, parent_id, model)``-only store, :data:`TIER_TOTALS` when
    the totals/window schema is present too.

    Raises:
        sqlite3.Error: When the schema itself cannot be read; callers map that
            to :data:`REASON_DB_UNREADABLE`.
    """
    session_columns = _table_columns(connection, 'session_v2')
    if session_columns is None or not _TIER1_COLUMNS <= session_columns:
        return 0, REASON_SCHEMA_UNSUPPORTED
    if not _TIER2_SESSION_COLUMNS <= session_columns:
        return TIER_MODEL, None
    message_columns = _table_columns(connection, 'session_message')
    if message_columns is None or not _TIER2_MESSAGE_COLUMNS <= message_columns:
        return TIER_MODEL, None
    return TIER_TOTALS, None


def probe(path: Path | str | None) -> dict[str, Any]:
    """Probe *path* for a schema tier this reader understands.

    The gate is two-tier: tier 1 is ``session_v2(id, parent_id, model)``, all the
    model measurement needs, and tier 2 additionally requires
    ``session_v2.directory`` and the ``tokens_*`` / ``cost`` columns plus
    ``session_message(session_id, type, time_created, data)``.

    Args:
        path: The database file to probe.

    Returns:
        ``{'ok': bool, 'tier': int, 'reason': str | None}`` — ``ok`` with the
        tier reached, or ``ok: False`` with ``tier: 0`` and the named reason
        (``db_not_found``, ``db_unreadable`` or ``schema_unsupported``).
    """
    connection, reason = _open(path)
    if connection is None:
        return {'ok': False, 'tier': 0, 'reason': reason}
    try:
        tier, reason = _probe_connection(connection)
    except sqlite3.Error:
        return {'ok': False, 'tier': 0, 'reason': REASON_DB_UNREADABLE}
    finally:
        _close(connection)
    if tier == 0:
        return {'ok': False, 'tier': 0, 'reason': reason or REASON_SCHEMA_UNSUPPORTED}
    return {'ok': True, 'tier': tier, 'reason': None}


# ---------------------------------------------------------------------------
# Session tree
# ---------------------------------------------------------------------------


def _session_rows(connection: sqlite3.Connection) -> dict[str, tuple[str | None, object]]:
    """Read ``session_v2`` (id, parent_id, model) into a mapping, read-only."""
    cursor = connection.execute('SELECT id, parent_id, model FROM session_v2')
    return {str(row[0]): (row[1], row[2]) for row in cursor.fetchall()}


def read_session_rows(path: Path | str | None) -> dict[str, Any]:
    """Read ``session_v2`` id → ``(parent_id, model)`` pairs, read-only.

    Tier 1 only: the model measurement needs nothing else, so a database
    carrying no message table or token columns still answers here.

    Args:
        path: The database file to read.

    Returns:
        ``{'ok': True, 'rows': {id: (parent_id, model)}}`` or
        ``{'ok': False, 'reason': <named reason>}`` — never a partial mapping
        presented as a complete one.
    """
    connection, reason = _open(path)
    if connection is None:
        return {'ok': False, 'reason': reason}
    try:
        tier, reason = _probe_connection(connection)
        if tier == 0:
            return {'ok': False, 'reason': reason or REASON_SCHEMA_UNSUPPORTED}
        return {'ok': True, 'rows': _session_rows(connection)}
    except sqlite3.Error:
        return {'ok': False, 'reason': REASON_DB_UNREADABLE}
    finally:
        _close(connection)


def session_root(session_id: str | None, rows: Mapping[str, tuple[str | None, object]]) -> str | None:
    """Resolve *session_id* to its root through ``parent_id``, or ``None``.

    ``None`` means the id names no row in the tree — there is nothing to
    measure. A cycle in a malformed tree terminates at the last unvisited id,
    so the walk always halts.
    """
    if not session_id or session_id not in rows:
        return None
    current = session_id
    seen: set[str] = set()
    while current not in seen:
        seen.add(current)
        parent = rows[current][0]
        if not isinstance(parent, str) or not parent or parent not in rows:
            return current
        current = parent
    return current


def session_tree(root: str, rows: Mapping[str, tuple[str | None, object]]) -> list[str]:
    """Return *root* plus every descendant reachable through ``parent_id``."""
    children: dict[str, list[str]] = {}
    for session_id, (parent, _model) in rows.items():
        if isinstance(parent, str) and parent:
            children.setdefault(parent, []).append(session_id)
    ordered: list[str] = []
    stack = [root]
    seen: set[str] = set()
    while stack:
        current = stack.pop()
        if current in seen or current not in rows:
            continue
        seen.add(current)
        ordered.append(current)
        stack.extend(children.get(current, ()))
    return ordered


def _resolve_tree(connection: sqlite3.Connection, session_id: str | None) -> tuple[str | None, list[str], str | None]:
    """Resolve ``(root, tree, reason)`` for *session_id* on an open connection.

    ``reason`` is ``None`` when a tree was resolved; otherwise it names why none
    was (``session_not_found`` when the id names no row).
    """
    rows = _session_rows(connection)
    root = session_root(session_id, rows)
    if root is None:
        return None, [], REASON_SESSION_NOT_FOUND
    return root, session_tree(root, rows), None


# ---------------------------------------------------------------------------
# Value coercion and message parsing
# ---------------------------------------------------------------------------


def _as_int(value: Any) -> int:
    """Coerce *value* to ``int``, treating an absent/non-numeric cell as 0."""
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value))
        except ValueError:
            return 0
    return 0


def _as_float(value: Any) -> float:
    """Coerce *value* to ``float``, treating an absent/non-numeric cell as 0.0."""
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return 0.0
    return 0.0


def _message_data(value: Any) -> Mapping[str, Any]:
    """Parse a message ``data`` cell into a mapping, or an empty mapping."""
    if isinstance(value, Mapping):
        return value
    if isinstance(value, (str, bytes)):
        try:
            parsed = json.loads(value)
        except (json.JSONDecodeError, UnicodeDecodeError, TypeError):
            return {}
        return parsed if isinstance(parsed, Mapping) else {}
    return {}


def _message_time(value: Any) -> datetime | None:
    """Read a message ``time_created`` cell as an aware UTC datetime.

    OpenCode stores epoch milliseconds as an integer; an ISO-8601 string is
    accepted too so a fixture (or a schema change) reads correctly. An
    unreadable value yields ``None`` — the row then cannot be attributed to a
    window and is skipped rather than guessed into one.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        seconds = value / 1000.0 if value > _EPOCH_MS_THRESHOLD else float(value)
        try:
            return datetime.fromtimestamp(seconds, UTC)
        except (OverflowError, OSError, ValueError):
            return None
    if isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.strip().replace('Z', '+00:00'))
        except (ValueError, TypeError):
            return None
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)
    return None


def _parse_windows(windows: Sequence[tuple[str, str, str]]) -> list[tuple[str, datetime, datetime]]:
    """Parse ``(phase, start_iso, end_iso)`` triples into datetime windows.

    Entries whose start or end cannot be read are dropped rather than widened to
    a boundary they never carried. Naive timestamps are read as UTC, matching
    :func:`_message_time`, so the comparison never mixes naive and aware values.
    """
    parsed: list[tuple[str, datetime, datetime]] = []
    for entry in windows or ():
        if not isinstance(entry, Sequence) or isinstance(entry, (str, bytes)) or len(entry) != 3:
            continue
        phase_name, start_raw, end_raw = entry
        start = _message_time(start_raw)
        end = _message_time(end_raw)
        if start is None or end is None:
            continue
        parsed.append((str(phase_name), start, end))
    return parsed


def _window_index(moment: datetime, windows: Sequence[tuple[str, datetime, datetime]]) -> int | None:
    """Return the index of the half-open ``[start, end)`` window holding *moment*.

    Windows are half-open, so a timestamp exactly on a boundary belongs to the
    window that starts there, never to the one that ends there. The first
    matching window wins when windows overlap.
    """
    for index, (_phase, start, end) in enumerate(windows):
        if start <= moment < end:
            return index
    return None


def _window_pre_filter(windows: Sequence[tuple[str, datetime, datetime]]) -> tuple[str, list[Any]]:
    """Return a SQL pre-filter and its bound values for the *windows* envelope.

    The envelope is ``[earliest start, latest end)`` over every parsed window.
    Every window is a sub-interval of it, so a row outside the envelope can fall
    in no window and dropping it in SQL removes exactly the rows
    :func:`_window_index` would have skipped — the per-window attribution itself
    stays in Python, where first-match-wins and half-open edges are decided.

    The numeric halves mirror :func:`_message_time`'s own rule: a cell above
    :data:`_EPOCH_MS_THRESHOLD` is milliseconds, at or below it seconds. A TEXT
    cell is always kept, because only the parser can read an ISO-8601 stamp —
    the pre-filter must not decide a format it cannot decode.

    Returns:
        ``(fragment, params)`` where *fragment* is empty when there is no window
        to bound (nothing is attributable, so no pre-filter is needed) and
        otherwise starts with `` AND `` so it appends to a ``WHERE`` clause.
    """
    if not windows:
        return '', []
    starts = [start.timestamp() for _phase, start, _end in windows]
    ends = [end.timestamp() for _phase, _start, end in windows]
    low, high = min(starts), max(ends)
    fragment = (
        ' AND (typeof("time_created") = \'text\''
        ' OR ("time_created" > ? AND "time_created" >= ? AND "time_created" < ?)'
        ' OR ("time_created" <= ? AND "time_created" >= ? AND "time_created" < ?))'
    )
    params: list[Any] = [
        _EPOCH_MS_THRESHOLD,
        low * 1000.0,
        high * 1000.0,
        _EPOCH_MS_THRESHOLD,
        low,
        high,
    ]
    return fragment, params


def _empty_bucket() -> dict[str, Any]:
    """Return a zeroed usage bucket for one window and one session scope."""
    bucket: dict[str, Any] = dict.fromkeys(USAGE_KEYS, 0)
    bucket['cost'] = 0.0
    bucket['message_count'] = 0
    bucket['tool_uses'] = 0
    bucket['duration_ms'] = 0
    bucket['sessions'] = 0
    return bucket


def _add_message_usage(data: Mapping[str, Any], bucket: dict[str, Any]) -> None:
    """Add one assistant message's ``tokens``/``cost`` to *bucket*."""
    tokens = data.get('tokens')
    if isinstance(tokens, Mapping):
        for path, key in _MESSAGE_TOKEN_PATHS:
            node: Any = tokens
            for segment in path:
                node = node.get(segment) if isinstance(node, Mapping) else None
            bucket[key] += _as_int(node)
    bucket['cost'] += _as_float(data.get('cost'))
    bucket['message_count'] += 1


def _message_text(data: Any) -> str:
    """Extract a message's prompt text from its ``data`` cell, or ``''``."""
    if isinstance(data, str):
        return data
    if not isinstance(data, Mapping):
        return ''
    for key in ('text', 'content', 'prompt', 'message'):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value
    parts = data.get('parts')
    if isinstance(parts, Sequence) and not isinstance(parts, (str, bytes)):
        chunks = [part.get('text') for part in parts if isinstance(part, Mapping)]
        texts = [chunk for chunk in chunks if isinstance(chunk, str) and chunk.strip()]
        if texts:
            return '\n'.join(texts)
    return ''


def _parse_header(text: str) -> dict[str, str]:
    """Parse a ``name:`` / ``plan_id:`` header out of *text*, key by key."""
    header: dict[str, str] = {}
    for match in _HEADER_PATTERN.finditer(text):
        key = match.group(1).lower()
        value = match.group(2).strip()
        if value:
            header.setdefault(key, value)
    return header


def _session_header(connection: sqlite3.Connection, session_id: str) -> dict[str, str]:
    """Read one session's header from the first prompt message that carries it.

    Scans the session's earliest messages (bounded by
    :data:`_PROMPT_SCAN_LIMIT`) and returns the header of the first one that
    carries a ``name:`` or ``plan_id:`` line. A session whose messages carry no
    header yields an empty mapping — the keys are absent, never invented. A
    missing message table, or any read error, yields ``{}`` rather than raising.
    """
    try:
        rows = connection.execute(
            'SELECT "data" FROM "session_message" WHERE "session_id" = ? ORDER BY "time_created" LIMIT ?',
            (session_id, _PROMPT_SCAN_LIMIT),
        ).fetchall()
    except sqlite3.Error:
        return {}
    for row in rows:
        header = _parse_header(_message_text(_message_data(row[0])))
        if header:
            return header
    return {}


# ---------------------------------------------------------------------------
# Tree totals
# ---------------------------------------------------------------------------


def session_totals(path: Path | str | None, session_id: str | None) -> dict[str, Any]:
    """Sum the ``tokens_*`` and ``cost`` columns over *session_id*'s tree.

    Tier 2 only: the totals read needs the token and cost columns, so a
    tier-1 store answers ``schema_unsupported`` rather than an empty bucket.

    The read names the tree's sessions in its ``WHERE`` clause — chunked to stay
    below SQLite's bound-variable limit — so a store carrying every project's
    sessions is never walked row by row in Python.

    Args:
        path: The database file to read.
        session_id: Any session in the tree — resolved to its root first.

    Returns:
        ``{'ok': True, 'root', 'sessions', <four usage keys>, 'cost'}`` or
        ``{'ok': False, 'reason': <named reason>}``.
    """
    connection, reason = _open(path)
    if connection is None:
        return {'ok': False, 'reason': reason}
    try:
        tier, reason = _probe_connection(connection)
        if tier < TIER_TOTALS:
            return {'ok': False, 'reason': reason or REASON_SCHEMA_UNSUPPORTED}
        root, tree, reason = _resolve_tree(connection, session_id)
        if root is None:
            return {'ok': False, 'reason': reason}
        columns = ', '.join(f'"{column}"' for column in TOKEN_COLUMNS)
        totals: dict[str, Any] = dict.fromkeys(USAGE_KEYS, 0)
        cost = 0.0
        sessions = 0
        for chunk in _chunked(tree, _SQL_VARIABLE_BUDGET):
            clause, clause_params = _in_clause('id', chunk)
            query = f'SELECT {columns}, "cost" FROM "session_v2" WHERE {clause}'
            for row in connection.execute(query, clause_params):
                sessions += 1
                for index, key in enumerate(USAGE_KEYS):
                    totals[key] += _as_int(row[index])
                cost += _as_float(row[len(USAGE_KEYS)])
        totals['cost'] = cost
        return {'ok': True, 'root': root, 'sessions': sessions, **totals}
    except sqlite3.Error:
        return {'ok': False, 'reason': REASON_DB_UNREADABLE}
    finally:
        _close(connection)


# ---------------------------------------------------------------------------
# Per-window usage
# ---------------------------------------------------------------------------


def window_usage(
    path: Path | str | None,
    session_id: str | None,
    windows: Sequence[tuple[str, str, str]],
) -> dict[str, Any]:
    """Sum assistant-message usage per half-open window, main versus sub-agent.

    Each ``session_message`` row in *session_id*'s tree is attributed to the
    first half-open ``[start, end)`` window containing its ``time_created``, and
    to the ``main`` scope when it belongs to the root session or ``subagent``
    when it belongs to any descendant. Assistant messages contribute their
    ``tokens``/``cost``; the message's ``tokens.input`` maps to
    ``input_tokens``, ``tokens.output`` to ``output_tokens``, ``tokens.cache.read``
    to ``cache_read_input_tokens`` and ``tokens.cache.write`` to
    ``cache_creation_input_tokens``.

    Every bucket also carries the measured ``message_count``, ``tool_uses``
    (rows whose ``type`` names a tool event), ``duration_ms`` (the span between
    the bucket's earliest and latest message) and ``sessions`` (how many distinct
    sessions of that scope contributed).

    The read is bounded by the two filters the attribution would apply anyway:
    ``session_message.session_id`` is constrained to the tree (chunked to stay
    below SQLite's bound-variable limit) and the window envelope of
    :func:`_window_pre_filter` bounds ``time_created``, so the scan never walks
    a store's rows from sessions outside the tree or messages outside the run.

    Args:
        path: The database file to read.
        session_id: Any session in the tree — resolved to its root first.
        windows: ``(phase, start, end)`` triples; an unreadable bound drops the
            window rather than widening it.

    Returns:
        ``{'ok': True, 'root', 'windows': [{'phase', 'main', 'subagent'}],
        'subagent_sessions'}`` or ``{'ok': False, 'reason': <named reason>}``.
    """
    connection, reason = _open(path)
    if connection is None:
        return {'ok': False, 'reason': reason}
    try:
        tier, reason = _probe_connection(connection)
        if tier < TIER_TOTALS:
            return {'ok': False, 'reason': reason or REASON_SCHEMA_UNSUPPORTED}
        root, tree, reason = _resolve_tree(connection, session_id)
        if root is None:
            return {'ok': False, 'reason': reason}
        parsed = _parse_windows(windows)
        rows: list[dict[str, Any]] = [
            {'phase': phase, 'main': _empty_bucket(), 'subagent': _empty_bucket()} for phase, _s, _e in parsed
        ]
        if not parsed:
            return {'ok': True, 'root': root, 'windows': rows, 'subagent_sessions': 0}
        spans: dict[tuple[int, str], list[datetime]] = {}
        contributors: dict[tuple[int, str], set[str]] = {}
        subagent_sessions: set[str] = set()
        window_clause, window_params = _window_pre_filter(parsed)
        chunk_size = max(1, _SQL_VARIABLE_BUDGET - len(window_params))
        for chunk in _chunked(tree, chunk_size):
            member_clause, member_params = _in_clause('session_id', chunk)
            query = (
                'SELECT "session_id", "type", "time_created", "data" FROM "session_message"'
                f' WHERE {member_clause}{window_clause}'
            )
            for message_session, message_type, created, data in connection.execute(
                query, [*member_params, *window_params]
            ):
                owning = str(message_session)
                moment = _message_time(created)
                if moment is None:
                    continue
                index = _window_index(moment, parsed)
                if index is None:
                    continue
                scope = 'main' if owning == root else 'subagent'
                bucket = rows[index][scope]
                spans.setdefault((index, scope), []).append(moment)
                contributors.setdefault((index, scope), set()).add(owning)
                if scope == 'subagent':
                    subagent_sessions.add(owning)
                kind = str(message_type).strip().lower()
                if kind == 'assistant':
                    _add_message_usage(_message_data(data), bucket)
                elif _TOOL_TYPE_MARKER in kind:
                    bucket['tool_uses'] += 1
        for (index, scope), moments in spans.items():
            rows[index][scope]['duration_ms'] = int((max(moments) - min(moments)).total_seconds() * 1000)
            rows[index][scope]['sessions'] = len(contributors.get((index, scope), ()))
        return {
            'ok': True,
            'root': root,
            'windows': rows,
            'subagent_sessions': len(subagent_sessions),
        }
    except sqlite3.Error:
        return {'ok': False, 'reason': REASON_DB_UNREADABLE}
    finally:
        _close(connection)


# ---------------------------------------------------------------------------
# Sub-agent listing
# ---------------------------------------------------------------------------


def list_subagents(path: Path | str | None, session_id: str | None) -> dict[str, Any]:
    """List every descendant of *session_id*'s root, with its prompt header.

    Each entry carries the sub-agent session id plus whichever of ``name`` and
    ``plan_id`` its first header-bearing prompt message declares. A session
    whose messages carry no header carries neither key — the header is parsed
    from what the store holds, never invented.

    Tier 1 suffices: the tree is resolvable from ``session_v2`` alone, and a
    store with no message table simply yields entries without a header.

    Args:
        path: The database file to read.
        session_id: Any session in the tree — resolved to its root first.

    Returns:
        ``{'ok': True, 'root', 'subagents': [{'session_id', ...}]}`` or
        ``{'ok': False, 'reason': <named reason>}``.
    """
    connection, reason = _open(path)
    if connection is None:
        return {'ok': False, 'reason': reason}
    try:
        tier, reason = _probe_connection(connection)
        if tier == 0:
            return {'ok': False, 'reason': reason or REASON_SCHEMA_UNSUPPORTED}
        root, tree, reason = _resolve_tree(connection, session_id)
        if root is None:
            return {'ok': False, 'reason': reason}
        subagents: list[dict[str, Any]] = []
        for member in tree:
            if member == root:
                continue
            entry: dict[str, Any] = {'session_id': member}
            entry.update(_session_header(connection, member))
            subagents.append(entry)
        return {'ok': True, 'root': root, 'subagents': subagents}
    except sqlite3.Error:
        return {'ok': False, 'reason': REASON_DB_UNREADABLE}
    finally:
        _close(connection)
