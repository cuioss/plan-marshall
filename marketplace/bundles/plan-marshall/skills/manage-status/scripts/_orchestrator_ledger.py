#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The single owner of the per-concern orchestrator ledger layout.

Notation: imported as a module (PYTHONPATH) — ``from _orchestrator_ledger import
assemble_view, create_row``. NOT an executor entry point.

An epic's machine state is split into files that each hold ONE concern, so two
sessions that write different concerns write different files. The layout, the
per-file decision behind it, and the one reader deliberately left outside this
module are the contract in
``persona-plan-orchestrator/standards/orchestration-model.md`` § Directory Layout;
this module enacts that contract and does not restate its reasoning.

Every function takes the epic ROOT directory (the ``.plan/orchestrator/{slug}/``
tree), so the store resolution — active or archived, strict or read-fallback —
stays with the caller that owns it. What this module owns is everything below
the root:

* **Path resolution.** :func:`header_path`, :func:`anchor_path`,
  :func:`queue_dir`, :func:`row_path` and :func:`view_path`. A plan id becomes a
  filename only after :func:`row_path` checks it against the shared plan-id
  grammar (ADR-016: containment happens at the shared resolver). The generated
  view's path is NAMED here and never read or written: its renderer and writer
  live in ``plan-orchestrator``.
* **The assembled read.** :func:`assemble_view` reads the header, the anchor and
  every row file into the one shape every reader consumes, rows ordered by
  ``(seq, id)``. An absent ``queue/`` directory is a MEASURED empty queue; a row
  file that cannot be read is reported as its own state and never as an absent
  row (ADR-019).
* **The writes.** :func:`create_ledger`, :func:`create_row`, :func:`mutate_row`,
  :func:`write_anchor`, :func:`write_header_field` and :func:`set_metadata_field`.
  No write stamps a shared ``updated`` field — a stamp every write restamps is
  the collision line the layout exists to remove.
* **The monolithic layout.** :func:`detect_legacy` recognises a ``status.json``
  that still carries the queue or the anchor, and :func:`legacy_layout_error`
  names ``orchestrator migrate-layout`` as the remedy. There is no read-fallback:
  a legacy ledger is refused, never read as an empty one. :func:`migrate_document`
  converts a legacy document into the per-concern files' content and
  :func:`write_layout` materialises it.

**Concurrency (TOCTOU / check-then-act).** Staging a row is a check-then-act: the
duplicate-slug scan runs, then the row file is created. Duplicate IDs are
refused by the atomic primitive — the row file is published with ``os.link``,
which never replaces an existing file — and the slug scan, the ``seq``
allocation and the publish run inside ONE critical section scoped to the queue.
Mutating a row runs through :func:`_locks_core.rmw_json` over that row's own
file, so two sessions acting on different rows never contend. No lock spans
machines: a duplicate id staged on two machines surfaces as a git add/add
conflict on the same filename. The mitigation menu lives in
``ref-code-quality/standards/code-organization.md#toctou--check-then-act-hazards``.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from _locks_core import _acquire_guard, _atomic_write_json, rmw_json
from epic_spec_parser import PLAN_ID_SEGMENT

# --- file names -------------------------------------------------------------

#: The epic header: ``kind``, ``title``, ``phase``, ``workstreams``,
#: ``metadata``, ``created``.
HEADER_FILE = 'status.json'

#: The resume anchor text, alone.
ANCHOR_FILE = 'resume_anchor.md'

#: The plan queue directory, one ``{PLAN-ID}.json`` row per file.
QUEUE_DIR = 'queue'

#: The generated view — named here, rendered and written by ``plan-orchestrator``.
VIEW_FILE = 'queue-view.md'

#: Suffix of a row file inside :data:`QUEUE_DIR`.
ROW_SUFFIX = '.json'

#: The transient guard file the queue-scoped critical section holds. It sits
#: beside ``queue/`` rather than inside it so a row listing never has to skip it.
QUEUE_GUARD_FILE = 'queue.lock'

# --- document shapes ----------------------------------------------------------

#: The header fields, in the order a created header is written.
HEADER_FIELDS = ('kind', 'title', 'phase', 'workstreams', 'metadata', 'created')

#: The keys whose presence in ``status.json`` marks the monolithic layout. The
#: split moves both out of the header, so a header carrying either is a legacy
#: document, whatever else it holds.
LEGACY_KEYS = frozenset({'plans', 'resume_anchor'})

#: The one legacy header field a conversion drops: the shared stamp every write
#: restamped, which is the collision line the per-concern layout removes.
_DROPPED_ON_MIGRATION = 'updated'

#: The fields of one row, in the order a row file is written. ``seq`` is the
#: queue-order key allocated at append time.
ROW_FIELDS = ('id', 'slug', 'workstream', 'status', 'plan_marshall_plan_id', 'pr', 'landing', 'seq')

#: The shape every reader consumes — the pre-split document without ``updated``.
VIEW_FIELDS = ('kind', 'title', 'phase', 'workstreams', 'plans', 'resume_anchor', 'metadata', 'created')

# --- read states ----------------------------------------------------------------

#: The ledger read found no header at the epic root.
LEDGER_ABSENT = 'absent'
#: The header could not be read as a JSON object.
LEDGER_UNREADABLE = 'unreadable'
#: The header still carries the queue or the anchor — the monolithic layout.
LEDGER_LEGACY = 'legacy_layout'
#: The header was read, and the view was assembled.
LEDGER_OK = 'ok'

#: ``queue/`` does not exist — a measured empty queue.
QUEUE_ABSENT = 'absent'
#: ``queue/`` was listed.
QUEUE_PRESENT = 'present'
#: ``queue/`` exists but could not be listed — nothing is known about the rows.
QUEUE_UNLISTABLE = 'unlistable'

#: The error code a legacy ledger is refused with, on every read and write.
LEGACY_LAYOUT_ERROR = 'legacy_layout'

#: The plan-id grammar a row id must match before it becomes a filename. The
#: segment is owned by ``epic_spec_parser`` and imported rather than re-spelled;
#: it is anchored here because the shared segment is deliberately unanchored for
#: prose scans. ``\\Z`` rather than ``$``: ``$`` also matches before a trailing
#: newline, which would let ``PLAN-01\\n`` through as a filename.
_ROW_ID_RE = re.compile(rf'^{PLAN_ID_SEGMENT}\Z')


class LedgerPathError(ValueError):
    """A plan id that does not match the plan-id grammar reached a path resolver."""


# =============================================================================
# Path resolution
# =============================================================================


def header_path(root: Path) -> Path:
    """Return the epic header path (``status.json``)."""
    return root / HEADER_FILE


def anchor_path(root: Path) -> Path:
    """Return the resume-anchor path (``resume_anchor.md``)."""
    return root / ANCHOR_FILE


def queue_dir(root: Path) -> Path:
    """Return the queue directory (``queue/``)."""
    return root / QUEUE_DIR


def view_path(root: Path) -> Path:
    """Return the generated view path (``queue-view.md``). Named, never opened here."""
    return root / VIEW_FILE


def is_valid_row_id(plan_id: object) -> bool:
    """Whether ``plan_id`` matches the plan-id grammar a row filename requires."""
    return isinstance(plan_id, str) and _ROW_ID_RE.match(plan_id) is not None


def row_path(root: Path, plan_id: str) -> Path:
    """Return the row file path for ``plan_id``, refusing an id outside the grammar.

    Raises:
        LedgerPathError: when ``plan_id`` does not match the plan-id grammar, so a
            path-shaped or otherwise malformed id never becomes a filename.
    """
    if not is_valid_row_id(plan_id):
        raise LedgerPathError(
            f'plan id {plan_id!r} does not match the plan-id grammar; refusing to use it as a filename'
        )
    return queue_dir(root) / f'{plan_id}{ROW_SUFFIX}'


# =============================================================================
# The monolithic layout
# =============================================================================


def detect_legacy(header: Mapping[str, Any]) -> bool:
    """Whether ``header`` is a monolithic-layout document (carries the queue or the anchor)."""
    return any(key in header for key in LEGACY_KEYS)


def legacy_layout_error(slug: str) -> dict[str, str]:
    """The refusal fields for a legacy ledger, naming the one remedy."""
    remedy = f'orchestrator migrate-layout --slug {slug}'
    return {
        'error': LEGACY_LAYOUT_ERROR,
        'message': (
            f'epic {slug!r} is in the monolithic ledger layout (its status.json still carries the queue or the '
            f'resume anchor). It is refused rather than read; convert it with `{remedy}`. Nothing was written.'
        ),
        'remedy': remedy,
    }


@dataclass(frozen=True)
class MigratedLedger:
    """The per-concern content a legacy document converts into.

    ``rejected_rows`` names every ``plans[]`` entry that could not become a row
    file — a non-mapping entry, or an id outside the plan-id grammar — so a
    conversion never drops a row silently.
    """

    header: dict[str, Any]
    anchor: str
    rows: tuple[dict[str, Any], ...]
    rejected_rows: tuple[dict[str, Any], ...] = field(default_factory=tuple)


def migrate_document(document: Mapping[str, Any]) -> MigratedLedger:
    """Convert a monolithic ``status.json`` document into the per-concern content.

    Pure: nothing is read or written. Every header field carries over verbatim —
    the declared :data:`HEADER_FIELDS` first, in their order, then every other
    key the document held (``title_token``, say), so no value is lost to a field
    list — the anchor text moves to its own file, each ``plans[]`` row gains a
    ``seq`` taken from its ARRAY POSITION (so the rendered order reproduces the
    old insertion order), and ``updated`` is dropped. A row that cannot become a
    row file is returned in ``rejected_rows`` with the reason, never discarded.
    """
    header = {key: document[key] for key in HEADER_FIELDS if key in document}
    for key, value in document.items():
        if key not in LEGACY_KEYS and key != _DROPPED_ON_MIGRATION:
            header.setdefault(key, value)
    anchor_value = document.get('resume_anchor', '')
    anchor = anchor_value if isinstance(anchor_value, str) else str(anchor_value)
    rows: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    plans = document.get('plans', [])
    if not isinstance(plans, list):
        rejected.append({'index': '', 'id': '', 'reason': f'plans is a {type(plans).__name__}, not a list'})
        plans = []
    for index, row in enumerate(plans):
        if not isinstance(row, dict):
            rejected.append({'index': str(index), 'id': '', 'reason': f'row is a {type(row).__name__}, not an object'})
            continue
        if not is_valid_row_id(row.get('id')):
            rejected.append(
                {'index': str(index), 'id': str(row.get('id', '')), 'reason': 'id does not match the plan-id grammar'}
            )
            continue
        rows.append(_ordered_row({**row, 'seq': index + 1}))
    return MigratedLedger(header=header, anchor=anchor, rows=tuple(rows), rejected_rows=tuple(rejected))


def write_layout(root: Path, header: Mapping[str, Any], anchor: str, rows: tuple[dict[str, Any], ...]) -> None:
    """Materialise the per-concern files: the header, the anchor, and one file per row.

    Overwrites whatever is at each path, so it is the writer for a conversion or a
    fixture — never for staging, which goes through :func:`create_row`.

    The header is written LAST. Over a legacy document the header write is the
    step that removes the queue and the anchor from ``status.json``, so every row
    file and the anchor file exist before it happens: an interrupted conversion
    leaves the legacy document intact and a re-run converts it again, rather than
    leaving a per-concern header whose rows were never written.
    """
    for row in rows:
        _atomic_write_json(row_path(root, row['id']), _ordered_row(row))
    write_anchor(root, anchor)
    _atomic_write_json(header_path(root), dict(header))


# =============================================================================
# The assembled read
# =============================================================================


@dataclass(frozen=True)
class QueueRead:
    """The rows one listing of ``queue/`` established, and what it could not read."""

    state: str
    rows: tuple[dict[str, Any], ...] = ()
    unreadable_rows: tuple[dict[str, str], ...] = ()
    detail: str = ''


@dataclass(frozen=True)
class LedgerRead:
    """One assembled read of an epic ledger.

    ``document`` holds the :data:`VIEW_FIELDS` shape only when ``state`` is
    :data:`LEDGER_OK`; for every other state it is empty and ``detail`` says why.
    ``unreadable_rows`` names every row file that could not be read — those rows
    are absent from ``document['plans']`` because nothing about them is known,
    and they are reported so that absence is never read as "no such row".
    """

    state: str
    document: dict[str, Any] = field(default_factory=dict)
    queue_state: str = QUEUE_ABSENT
    unreadable_rows: tuple[dict[str, str], ...] = ()
    detail: str = ''


def read_header(root: Path) -> tuple[str, dict[str, Any], str]:
    """Read the header, returning ``(state, header, detail)``.

    ``state`` is one of :data:`LEDGER_ABSENT`, :data:`LEDGER_UNREADABLE`,
    :data:`LEDGER_LEGACY` and :data:`LEDGER_OK`. The header dict is populated for
    :data:`LEDGER_LEGACY` too, so a converter can read the legacy document through
    the same probe.
    """
    path = header_path(root)
    try:
        raw = path.read_text(encoding='utf-8')
    except FileNotFoundError:
        return LEDGER_ABSENT, {}, f'{path} does not exist'
    except OSError as exc:
        return LEDGER_UNREADABLE, {}, f'{path} could not be read: {exc}'
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        return LEDGER_UNREADABLE, {}, f'{path} does not parse as JSON: {exc}'
    if not isinstance(parsed, dict):
        return LEDGER_UNREADABLE, {}, f'{path} parses to a {type(parsed).__name__}, not an object'
    if detect_legacy(parsed):
        return LEDGER_LEGACY, parsed, f'{path} still carries the queue or the resume anchor'
    return LEDGER_OK, parsed, ''


def read_anchor(root: Path) -> tuple[str, str]:
    """Read the anchor, returning ``(text, detail)``.

    An absent anchor file reads as the empty anchor — a created ledger starts
    with one, so absence carries no information a reader acts on. An unreadable
    one raises :class:`OSError` rather than reading as empty.
    """
    path = anchor_path(root)
    try:
        text = path.read_text(encoding='utf-8')
    except FileNotFoundError:
        return '', f'{path} does not exist'
    return (text[:-1] if text.endswith('\n') else text), ''


def _read_row_file(path: Path) -> tuple[dict[str, Any] | None, str]:
    """Read one row file, returning ``(row, reason)``; ``row`` is ``None`` when unreadable."""
    try:
        raw = path.read_text(encoding='utf-8')
    except OSError as exc:
        return None, f'could not be read: {exc}'
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        return None, f'does not parse as JSON: {exc}'
    if not isinstance(parsed, dict):
        return None, f'parses to a {type(parsed).__name__}, not an object'
    return parsed, ''


def queue_order_key(row: Mapping[str, Any]) -> tuple[int, str]:
    """The ``(seq, id)`` queue-order key; a row carrying no integer ``seq`` sorts first."""
    seq = row.get('seq')
    return (seq if isinstance(seq, int) and not isinstance(seq, bool) else 0, str(row.get('id', '')))


def read_rows(root: Path) -> QueueRead:
    """List ``queue/`` and read every row file, ordered by ``(seq, id)``.

    An absent directory is :data:`QUEUE_ABSENT` with no rows — a measured empty
    queue. A directory that cannot be listed is :data:`QUEUE_UNLISTABLE`, which
    establishes nothing. A row file that cannot be read lands in
    ``unreadable_rows`` with its file name and the reason, never in ``rows``.
    """
    directory = queue_dir(root)
    try:
        entries = sorted(path for path in directory.iterdir() if path.name.endswith(ROW_SUFFIX))
    except FileNotFoundError:
        return QueueRead(state=QUEUE_ABSENT, detail=f'{directory} does not exist')
    except OSError as exc:
        return QueueRead(state=QUEUE_UNLISTABLE, detail=f'{directory} could not be listed: {exc}')
    rows: list[dict[str, Any]] = []
    unreadable: list[dict[str, str]] = []
    for path in entries:
        row, reason = _read_row_file(path)
        if row is None:
            unreadable.append({'file': path.name, 'reason': reason})
            continue
        rows.append(row)
    rows.sort(key=queue_order_key)
    return QueueRead(state=QUEUE_PRESENT, rows=tuple(rows), unreadable_rows=tuple(unreadable))


def assemble_view(root: Path) -> LedgerRead:
    """Assemble the epic ledger into the one shape every reader consumes.

    The header must read as a per-concern header; a legacy one is refused with
    :data:`LEDGER_LEGACY` rather than assembled. The anchor and the rows are then
    folded in, ``plans`` ordered by ``(seq, id)``.
    """
    state, header, detail = read_header(root)
    if state != LEDGER_OK:
        return LedgerRead(state=state, detail=detail)
    try:
        anchor, _ = read_anchor(root)
    except OSError as exc:
        return LedgerRead(state=LEDGER_UNREADABLE, detail=f'{anchor_path(root)} could not be read: {exc}')
    queue = read_rows(root)
    if queue.state == QUEUE_UNLISTABLE:
        return LedgerRead(state=LEDGER_UNREADABLE, queue_state=queue.state, detail=queue.detail)
    document: dict[str, Any] = {key: header[key] for key in HEADER_FIELDS if key in header}
    document['plans'] = [dict(row) for row in queue.rows]
    document['resume_anchor'] = anchor
    ordered = {key: document[key] for key in VIEW_FIELDS if key in document}
    for key, value in header.items():
        ordered.setdefault(key, value)
    return LedgerRead(
        state=LEDGER_OK,
        document=ordered,
        queue_state=queue.state,
        unreadable_rows=queue.unreadable_rows,
    )


# =============================================================================
# Writes
# =============================================================================


def _ordered_row(row: Mapping[str, Any]) -> dict[str, Any]:
    """Return ``row`` with :data:`ROW_FIELDS` first, in order, then any extra keys."""
    ordered = {key: row[key] for key in ROW_FIELDS if key in row}
    for key, value in row.items():
        ordered.setdefault(key, value)
    return ordered


def _atomic_write_text(path: Path, text: str) -> None:
    """Commit ``text`` to ``path`` through a same-directory temp file and ``os.replace``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f'{path.name}.{os.getpid()}.tmp')
    tmp_path.write_text(text, encoding='utf-8')
    os.replace(str(tmp_path), str(path))


def create_ledger(root: Path, title: str, created: str) -> dict[str, Any]:
    """Write a fresh header and an empty anchor; return the header written.

    The queue is not touched: a new ledger has no ``queue/`` directory, which
    every reader takes as a measured empty queue.
    """
    header = {
        'kind': 'orchestrator',
        'title': title,
        'phase': 'init',
        'workstreams': [],
        'metadata': {},
        'created': created,
    }
    _atomic_write_json(header_path(root), header)
    write_anchor(root, '')
    return header


def write_anchor(root: Path, text: str) -> None:
    """Replace the resume anchor text."""
    _atomic_write_text(anchor_path(root), f'{text}\n')


def write_header_field(root: Path, field_name: str, value: Any) -> dict[str, Any]:
    """Set one header field inside the header's own critical section.

    Returns ``{'previous': ...}`` when the field was set, or ``{'legacy': True}``
    when the in-lock read found a legacy document — in which case the document
    is returned unchanged. Callers probe the header first and refuse a legacy or
    unreadable one before reaching here; the in-lock check only covers a
    conversion racing the write.
    """
    outcome: dict[str, Any] = {}

    def _mutate(state: dict[str, Any]) -> dict[str, Any]:
        if detect_legacy(state):
            outcome['legacy'] = True
            return state
        outcome['previous'] = state.get(field_name)
        state[field_name] = value
        return state

    rmw_json(header_path(root), _mutate)
    return outcome


def set_metadata_field(root: Path, field_name: str, value: Any) -> dict[str, Any]:
    """Set one entry of the header's ``metadata`` object inside the header's critical section.

    Returns ``{'previous': ...}`` or ``{'legacy': True}`` exactly as
    :func:`write_header_field` does.
    """
    outcome: dict[str, Any] = {}

    def _mutate(state: dict[str, Any]) -> dict[str, Any]:
        if detect_legacy(state):
            outcome['legacy'] = True
            return state
        metadata = state.get('metadata')
        if not isinstance(metadata, dict):
            metadata = {}
            state['metadata'] = metadata
        outcome['previous'] = metadata.get(field_name)
        metadata[field_name] = value
        return state

    rmw_json(header_path(root), _mutate)
    return outcome


def _release_guard(fd: int, guard: Path) -> None:
    os.close(fd)
    try:
        os.unlink(str(guard))
    except OSError:
        pass


def _publish_new_file(path: Path, row: dict[str, Any]) -> bool:
    """Publish ``row`` at ``path`` only if nothing is there; return whether it was created.

    The content is written to a temp file first and published with ``os.link``,
    which never replaces an existing file. The link IS the exclusive create, and
    it publishes a complete file, so no reader ever observes a half-written row.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f'.{path.name}.{os.getpid()}.tmp')
    tmp_path.write_text(json.dumps(row, indent=2), encoding='utf-8')
    try:
        os.link(str(tmp_path), str(path))
    except FileExistsError:
        return False
    finally:
        tmp_path.unlink(missing_ok=True)
    return True


def create_row(root: Path, row: Mapping[str, Any], *, epic_slug: str | None = None) -> dict[str, Any]:
    """Stage one new row: allocate its ``seq`` and create its file atomically.

    Returns a dict carrying exactly one outcome key:

    * ``row`` — the row written, ``seq`` included.
    * ``invalid_id`` — the id does not match the plan-id grammar; nothing written.
    * ``epic_slug`` — the row slug equals the epic slug; decided before any lock.
    * ``duplicate`` — a row file for this id already exists (the existing row, or
      ``{'id': ...}`` when that file cannot be read).
    * ``duplicate_slug`` — a readable row already carries this slug.
    * ``queue_unlistable`` — ``queue/`` could not be listed, so the slug check
      could not run; nothing written.

    The slug scan, the ``seq`` allocation and the publish share one critical
    section scoped to the queue, so two local sessions staging different plans
    get distinct ``seq`` values and two staging one slug cannot both pass the
    scan. The publish is itself the atomic id check.
    """
    plan_id = row.get('id')
    if not isinstance(plan_id, str) or not is_valid_row_id(plan_id):
        return {'invalid_id': plan_id}
    if epic_slug is not None and row.get('slug') == epic_slug:
        return {'epic_slug': epic_slug}
    path = row_path(root, plan_id)
    guard = root / QUEUE_GUARD_FILE
    fd = _acquire_guard(guard)
    try:
        if path.exists():
            existing, _ = _read_row_file(path)
            return {'duplicate': existing if existing is not None else {'id': plan_id}}
        listing = read_rows(root)
        if listing.state == QUEUE_UNLISTABLE:
            return {'queue_unlistable': listing.detail}
        for existing_row in listing.rows:
            if existing_row.get('slug') == row.get('slug'):
                return {'duplicate_slug': existing_row}
        seqs = [
            value
            for value in (existing_row.get('seq') for existing_row in listing.rows)
            if isinstance(value, int) and not isinstance(value, bool)
        ]
        record = _ordered_row({**row, 'seq': max(seqs, default=0) + 1})
        if not _publish_new_file(path, record):
            existing, _ = _read_row_file(path)
            return {'duplicate': existing if existing is not None else {'id': plan_id}}
        return {'row': record}
    finally:
        _release_guard(fd, guard)


def mutate_row(root: Path, plan_id: str, apply: Callable[[dict[str, Any]], Any]) -> dict[str, Any]:
    """Apply ``apply`` to one row inside that row file's own critical section.

    Returns a dict carrying exactly one outcome key:

    * ``result`` — whatever ``apply`` returned for the located row.
    * ``invalid_id`` — the id does not match the plan-id grammar.
    * ``available_plans`` — no row file exists for the id; every readable row id,
      in queue order.
    * ``unreadable`` — the row file exists but is not a readable JSON object. It is
      refused rather than mutated, because the shared read-modify-write reads an
      unreadable file as empty and would commit that empty object over it.
    """
    if not is_valid_row_id(plan_id):
        return {'invalid_id': plan_id}
    path = row_path(root, plan_id)
    if not path.exists():
        return {'available_plans': [str(row.get('id', '')) for row in read_rows(root).rows]}
    existing, reason = _read_row_file(path)
    if existing is None:
        return {'unreadable': f'{path.name} {reason}'}
    outcome: dict[str, Any] = {}

    def _mutate(state: dict[str, Any]) -> dict[str, Any]:
        if not state:
            outcome['unreadable'] = f'{path.name} read as empty inside the critical section'
            return existing
        outcome['result'] = apply(state)
        return _ordered_row(state)

    rmw_json(path, _mutate)
    return outcome
