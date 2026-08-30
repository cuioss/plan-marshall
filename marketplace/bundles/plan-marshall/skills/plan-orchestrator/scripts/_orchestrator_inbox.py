#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Inbox envelope schema, validation seam, and epic-store write/drain surface.

Backs ``orchestrator.py``'s ``inbox`` verb group. The inbox is the epic tree's
single plan-writable OUTBOX: an executing plan appends
``inbox/{sender_id}-{NNN}.md`` messages to its governing epic and never touches
any other path under ``.plan/local/orchestrator/{slug}/``. The carve-out is
enforced here **by construction** — :func:`cmd_inbox_write` derives the target
path solely from the validated slug and ``--sender-id`` and accepts no
caller-supplied output path, so no argument value can reach ``status.json``,
``epic.md``, ``workstreams/``, ``plans/``, or ``landings/``.

A filed message is corrected through the sanctioned surface, never by a direct
file edit: :func:`cmd_inbox_amend` replaces a message's body in place while
preserving ``created`` and stamping an ``amended`` marker plus a monotonic
``revision``, and :func:`cmd_inbox_supersede` retires a message in favour of a
named successor (tombstone-style — the retired message stays resolvable but
stops presenting as live). Both make the post-filing mutation visible in the
envelope, so a corrected message is never byte-indistinguishable from a virgin
one. :func:`cmd_inbox_close_stream` files a terminal ``lifecycle=stream-end``
marker so a sender can signal its stream ended, and the message-state vocabulary
(``lifecycle`` ∈ :data:`LIFECYCLES`) carries all three concepts in ONE enum.

The archive is foldered per sender (``inbox/archive/{sender}/``);
:func:`cmd_inbox_migrate_archive` folds a flat archive into that layout, and the
sequence allocator, the resolver, and the counter all read both layouts so no
retired sequence number is ever re-opened during a partial migration.

The orchestrator-side drain surface (:func:`cmd_inbox_list`,
:func:`cmd_inbox_archive`) is bounded by the same construction: both derive
their target from the validated slug plus a bare message filename, and the only
path they ever write is ``inbox/archive/{sender}/`` — the per-sender layout
above — joined with either the source message's own bare filename or the bare,
sender-constrained ``--as-name`` override. One carve-out is deliberate: a source
name matching no message-name pattern yields no sender, so its destination stays
FLAT under ``inbox/archive/`` and its ``os.link`` failure still surfaces as
``invalid_message_name`` rather than being masked by a foldering step. In both
branches the destination is composed here from validated parts — never a
caller-supplied path.

The message format is markdown with the repo's existing ``key=value`` metadata
header (``file_ops.parse_markdown_metadata`` /
``file_ops.generate_markdown_metadata``): typed scalars ride the header, free
prose is the body, and the two are separated by exactly one blank line. The
schema itself is documented in
``plan-orchestrator/standards/inbox-envelope.md``.
"""

import os
import re
from pathlib import Path
from typing import Any, NamedTuple

from epic_spec_parser import PLAN_ID_SEGMENT
from file_ops import (
    atomic_write_file,
    generate_markdown_metadata,
    get_store_dir,
    now_utc_iso,
    parse_markdown_metadata,
    read_json,
)
from input_validation import validate_plan_id

ORCHESTRATOR_STORE = 'orchestrator'

#: The epic status document, relative to the epic store root — the machine
#: authority for per-plan lifecycle state (``plans[]`` rows carrying ``id`` and
#: ``status``).
STATUS_FILE = 'status.json'

#: The plan-lifecycle status a plan row carries WHILE it is executing. This is
#: the single source of the token: ``orchestrator.py`` imports it from here
#: rather than re-declaring the literal, so the two modules cannot drift. A
#: message aimed at a plan in this state is undeliverable — the inbox is drained
#: BETWEEN plans, so a running plan will have finished before the next drain and
#: never reads the message (see :func:`cmd_inbox_write`).
RUNNING_STATUS = 'running'

#: Envelope schema version. A message carrying any other value is REJECTED
#: (``unknown_envelope_version``) rather than silently accepted — the
#: forward-compatibility rule is fail-closed.
ENVELOPE_VERSION = 1

#: Who may send a message. ``plan`` is the executing-plan OUTBOX case;
#: ``orchestrator`` reserves the discriminator for orchestrator-to-orchestrator
#: messages so a future sender class needs no envelope-version bump.
SENDER_TYPES = frozenset({'plan', 'orchestrator'})

#: The payload kinds the channel carries.
KINDS = frozenset({'landing', 'finding', 'candidate-lesson'})

#: The message-state vocabulary — the SINGLE closed enum this channel carries
#: for message lifecycle. Derived from the ``manage-lessons`` ``status`` model
#: (``active`` / ``superseded`` / ``removed``): a state field on the record that
#: defaults to the live value when absent and lets a replaced record stay
#: resolvable while it stops presenting as live. All THREE state concepts ride
#: this one field so no second enum is introduced:
#:
#: - ``live`` — the message as filed and current (the default; an absent
#:   ``lifecycle`` header reads as ``live``, so every message written by
#:   ``write`` is ``live`` without carrying the field). Amendment does not leave
#:   this state — it rides :data:`_REVISION_FIELD` / :data:`_AMENDED_FIELD`
#:   instead, which are a COUNTER and a TIMESTAMP, not a second enum.
#: - ``superseded`` — replaced by a named successor (``superseded_by``); stays on
#:   disk and validates green, but stops presenting as live in the listing.
#: - ``stream-end`` — a terminal control marker: the sender that filed it will
#:   send no more. This is the stream-termination concept expressed as one more
#:   value in THIS vocabulary rather than a parallel ``stream_status`` enum.
LIFECYCLE_LIVE = 'live'
LIFECYCLE_SUPERSEDED = 'superseded'
LIFECYCLE_STREAM_END = 'stream-end'
LIFECYCLES = frozenset({LIFECYCLE_LIVE, LIFECYCLE_SUPERSEDED, LIFECYCLE_STREAM_END})

#: The payload kind a stream-end control marker carries. A stream closure is an
#: observation the epic should know about, so it rides the existing ``finding``
#: kind — the terminal signal is the ``lifecycle`` header, NOT the kind, so no
#: value is added to :data:`KINDS`. Keeping ``kind`` purely the payload-type
#: vocabulary and ``lifecycle`` the sole state vocabulary is what makes the
#: whole design one vocabulary rather than two.
STREAM_END_KIND = 'finding'

#: The default body a ``close-stream`` marker carries when no ``--reason`` is
#: supplied. A non-empty body keeps the marker a fully-valid message that needs
#: no message-class branch in :func:`validate_envelope`.
STREAM_END_DEFAULT_NOTE = (
    'Sender stream closed; no further messages will be filed on this stream.'
)

#: The revision counter and amendment-timestamp header fields. Neither is an
#: enum — they are the attributes an ``amend`` stamps on a still-``live``
#: message, which is what lets amendment be visible from the envelope alone
#: without inventing a second state vocabulary.
_REVISION_FIELD = 'revision'
_AMENDED_FIELD = 'amended'
_SUPERSEDED_BY_FIELD = 'superseded_by'
_LIFECYCLE_FIELD = 'lifecycle'

#: Header fields, in the fixed order :func:`compose_envelope` emits them.
#: Every field is required; a message missing any one is ``missing_header_field``.
#: The state fields (:data:`_LIFECYCLE_FIELD`, :data:`_REVISION_FIELD`,
#: :data:`_AMENDED_FIELD`, :data:`_SUPERSEDED_BY_FIELD`) are DELIBERATELY not
#: here: they are optional-with-default, so a virgin message stays byte-identical
#: to how it looked before this vocabulary existed and ``envelope_version`` need
#: not bump.
HEADER_FIELDS = (
    'envelope_version',
    'sender_type',
    'sender_id',
    'epic',
    'kind',
    'created',
)

#: The inbox subdirectory of an epic tree.
INBOX_SUBDIR = 'inbox'

#: Where a consumed message is retired to, relative to ``inbox/``. Created on
#: first use — deliberately NOT a member of ``orchestrator.py``'s
#: ``EPIC_SUBDIRS``, so no existing scaffold assertion moves.
INBOX_ARCHIVE_SUBDIR = 'archive'

#: The closed vocabulary :func:`resolve_message_path` reports. ``queued`` and
#: ``archived`` are the two RESOLUTION outcomes a caller can act on; ``missing``
#: is the third, which :func:`cmd_inbox_validate` surfaces as ``file_not_found``.
#: These are resolution outcomes, NOT envelope-validation verdicts — a message
#: resolved as ``archived`` is still validated through the same
#: :func:`validate_envelope` seam as a ``queued`` one.
MESSAGE_LOCATIONS = frozenset({'queued', 'archived', 'missing'})

#: The closed vocabulary :func:`cmd_inbox_list` reports as ``inbox_state``.
#: ``present`` means the enumeration looked at a real directory; ``missing``
#: means it could not look because the epic has no ``inbox/`` yet. The verb
#: stays non-faulting either way, so the two zeros are told apart by the
#: PAYLOAD, never by the status.
INBOX_STATES = frozenset({'present', 'missing'})

#: ``{sender_id}-{NNN}.md`` — the one message-file shape the channel allocates.
#: The sender group is non-greedy so the LAST dash-separated all-digit run is
#: the sequence: a four-digit sequence, or a sender id that itself ends in
#: digits, still splits at the right dash.
_MESSAGE_NAME_RE = re.compile(r'^(?P<sender>.+?)-(?P<seq>\d{3,})\.md$')

#: The orchestrator plan-spec pointer ``phase-1-init`` records as
#: ``request.md``'s ``source_id`` for an orchestrated plan. The id segment is
#: NOT spelled out here: it is :data:`epic_spec_parser.PLAN_ID_SEGMENT`, the
#: single definition of the settled plan-id forms, which
#: :func:`epic_spec_parser.plan_id_of` reads the same corpus through. Composing
#: from that binding rather than carrying a second copy is what keeps this
#: pointer grammar and the corpus parser from drifting apart.
_SOURCE_ID_RE = re.compile(
    r'^\.plan/local/orchestrator/(?P<slug>[^/]+)/plans/' + PLAN_ID_SEGMENT + r'[^/]*\.md$'
)

#: Shape-only sibling of :data:`_SOURCE_ID_RE` — any markdown file directly
#: under an epic's ``plans/`` directory, whatever its id segment. It is the
#: predicate that separates "not an orchestrator pointer at all" from
#: "orchestrator pointer whose id segment matches none of the accepted forms",
#: which is the case that previously reclassified silently.
_ORCHESTRATOR_PLANS_RE = re.compile(
    r'^\.plan/local/orchestrator/(?P<slug>[^/]+)/plans/[^/]+\.md$'
)

#: The closed vocabulary :func:`classify_source_id` reports in its ``detection``
#: field. Consumers assert against this set rather than re-listing literals.
DETECTION_TOKENS = frozenset(
    {
        'orchestrated',
        'not_orchestrator_pointer',
        'unrecognised_id',
        'unsafe_slug',
    }
)


class SourceIdClassification(NamedTuple):
    """The verdict :func:`classify_source_id` returns.

    ``epic`` and ``plan_spec`` are populated only when ``orchestrated`` is
    ``True``; ``detection`` always carries one of :data:`DETECTION_TOKENS` and
    is what makes the three negative outcomes distinguishable.
    """

    orchestrated: bool
    epic: str | None
    plan_spec: str | None
    detection: str


def _error(error: str, message: str, **extra: Any) -> dict[str, Any]:
    """Build the standard TOON error envelope for the inbox verbs."""
    result: dict[str, Any] = {
        'status': 'error',
        'store': ORCHESTRATOR_STORE,
        'error': error,
        'message': message,
    }
    result.update(extra)
    return result


def _validate_identifier(value: str) -> str | None:
    """Validate a slug / sender id (kebab-case, safe as a path component).

    Returns an error message string when invalid, ``None`` when valid. The
    check is load-bearing: both values become path components under the
    orchestrator store, so a malformed value must never reach
    :func:`file_ops.get_store_dir` or a filename join.
    """
    try:
        validate_plan_id(value)
    except ValueError as exc:
        return str(exc)
    return None


def _is_bare_filename(name: str) -> bool:
    """Whether ``name`` is a bare filename safe to join onto ``inbox/``.

    The shared guard behind every ``--message`` argument: an empty value, or a
    value carrying a path separator, a traversal segment, or a directory
    reference, is refused with ``invalid_message_name`` before it can reach a
    filesystem join. The emptiness test is load-bearing rather than defensive:
    ``Path('').name`` is itself ``''``, so the empty string satisfies the
    bare-name equality on its own and the join would resolve to ``inbox/``
    itself — surfacing a confusing not-found against a directory path instead
    of naming the actual defect in the argument.
    """
    return bool(name) and name == Path(name).name and name not in ('.', '..')


def _read_epic_root(slug: str) -> Path:
    """Resolve the epic's store root for a READ-side verb.

    Uses :func:`file_ops.get_store_dir`'s ``allow_archived=True`` read-fallback
    so an archived epic resolves transparently when its active tree is gone —
    the same resolution ``inbox validate`` uses.
    """
    return get_store_dir(ORCHESTRATOR_STORE, slug, allow_archived=True)


def _inbox_dir(slug: str) -> Path:
    """Resolve the epic's ``inbox/`` directory for a READ-side verb."""
    return _read_epic_root(slug) / INBOX_SUBDIR


def _running_plan_ids(epic_root: Path) -> set[str]:
    """Return the ids of every plan currently ``running`` in the epic.

    Reads the epic's ``status.json`` — the machine authority for per-plan
    lifecycle state — and returns the id of every ``plans[]`` row whose
    ``status`` is :data:`RUNNING_STATUS`, mirroring the extraction
    ``orchestrator.py`` performs for its own running-plans readiness signal.

    A missing, unreadable, or malformed status document, or one carrying no
    ``plans[]`` array, yields an EMPTY set: with no readable queue there is no
    plan whose running state can be confirmed, so the deliverability guard that
    consumes this set does not fire on an unverifiable state (it refuses only a
    plan it can positively read as running).
    """
    data = read_json(epic_root / STATUS_FILE)
    if not isinstance(data, dict):
        return set()
    rows = data.get('plans')
    if not isinstance(rows, list):
        return set()
    return {
        str(row.get('id', ''))
        for row in rows
        if isinstance(row, dict) and str(row.get('status', '')) == RUNNING_STATUS
    }


def _mutate_epic_root(slug: str) -> Path:
    """Resolve the epic's store root for a MUTATING verb.

    Deliberately omits the ``allow_archived=True`` read-fallback
    :func:`_read_epic_root` opts into. Archival relocates a file, so a verb
    that MUTATES must never resolve into ``archived-orchestrators/{slug}`` and
    write inside an epic's frozen audit record once its active tree is gone —
    :func:`file_ops.get_store_dir`'s strict default returns the (absent) active
    path instead, which the caller refuses with ``epic_not_found``.
    """
    return get_store_dir(ORCHESTRATOR_STORE, slug)


def _render_envelope(header: dict[str, str], payload_body: str) -> str:
    """Render a message from an already-ordered header dict and a body.

    The single place the header/body layout lives: the ``key=value`` header,
    exactly one blank line, then the trimmed markdown body. The header dict's
    key order IS the emission order, so callers control field ordering by
    insertion order.
    """
    return f'{generate_markdown_metadata(header)}\n\n{payload_body.strip()}\n'


def _apply_state_fields(
    header: dict[str, str],
    *,
    lifecycle: str,
    revision: int,
    amended: str,
    superseded_by: str,
) -> None:
    """Append the non-default message-state fields onto ``header`` in place.

    Each field is emitted ONLY when it departs from its default (``lifecycle``
    other than ``live``, a non-zero ``revision``, a non-empty ``amended`` /
    ``superseded_by``). A virgin message therefore carries none of them and
    stays byte-identical to the pre-vocabulary shape, while an amended or
    superseded one is distinguishable from its envelope alone.
    """
    if lifecycle and lifecycle != LIFECYCLE_LIVE:
        header[_LIFECYCLE_FIELD] = lifecycle
    if revision:
        header[_REVISION_FIELD] = str(revision)
    if amended:
        header[_AMENDED_FIELD] = amended
    if superseded_by:
        header[_SUPERSEDED_BY_FIELD] = superseded_by


def compose_envelope(
    sender_type: str,
    sender_id: str,
    epic: str,
    kind: str,
    payload_body: str,
    *,
    lifecycle: str = LIFECYCLE_LIVE,
    revision: int = 0,
    amended: str = '',
    superseded_by: str = '',
) -> str:
    """Render a complete inbox message.

    The ``key=value`` header carries :data:`HEADER_FIELDS` in order, one blank
    line separates it from the markdown payload body, and ``created`` is
    stamped at compose time. The optional message-state fields are appended only
    when non-default (see :func:`_apply_state_fields`), so the default call — the
    ``write`` path — emits exactly the six base fields.

    Args:
        sender_type: One of :data:`SENDER_TYPES`.
        sender_id: The sender's identifier (a plan id, or an epic slug for an
            ``orchestrator`` sender).
        epic: Epic slug the message is addressed to.
        kind: One of :data:`KINDS`.
        payload_body: The markdown payload; surrounding whitespace is trimmed.
        lifecycle: One of :data:`LIFECYCLES`; ``live`` is the default and is not
            emitted. ``stream-end`` marks a terminal control message.
        revision: Amendment counter; emitted only when non-zero.
        amended: Amendment timestamp; emitted only when non-empty.
        superseded_by: Successor message filename; emitted only when non-empty.

    Returns:
        The full message text.
    """
    header = {
        'envelope_version': str(ENVELOPE_VERSION),
        'sender_type': sender_type,
        'sender_id': sender_id,
        'epic': epic,
        'kind': kind,
        'created': now_utc_iso(),
    }
    _apply_state_fields(
        header,
        lifecycle=lifecycle,
        revision=revision,
        amended=amended,
        superseded_by=superseded_by,
    )
    return _render_envelope(header, payload_body)


def _split_message(text: str) -> tuple[dict[str, str], str]:
    """Split a message into its parsed header and its payload body.

    The header block is terminated by the FIRST blank line — the same
    separator :func:`compose_envelope` emits. Everything after it is the
    payload. A message with no blank line has no payload at all (the body is
    empty), which the validator surfaces as ``empty_payload``.
    """
    lines = text.split('\n')
    body_start = len(lines)
    for index, line in enumerate(lines):
        if not line.strip():
            body_start = index + 1
            break
    return parse_markdown_metadata(text), '\n'.join(lines[body_start:]).strip()


def validate_envelope(
    text: str, expected_epic: str | None = None, filename: str | None = None
) -> tuple[bool, str | None, dict[str, str]]:
    """The named validation seam: check a message against the envelope schema.

    Checks run in a fixed order so a given malformed message always yields the
    same error code: header completeness, envelope version, sender type, kind,
    payload presence, epic agreement, filename agreement, then the message-state
    fields. The epic/filename pair is checked only when the corresponding context
    argument is supplied; the state checks run last so the base rejection codes
    are unchanged and a message carrying none of the state fields (the virgin
    ``live`` case) always reaches ``True``.

    The state checks enforce the invariants the vocabulary rests on:
    ``invalid_lifecycle`` (a ``lifecycle`` outside :data:`LIFECYCLES`),
    ``invalid_revision`` (a non-integer/negative ``revision``),
    ``revision_not_monotonic`` (an ``amended`` stamp and a ``revision >= 1`` must
    move together — a claimed amendment with no advanced revision, or an advanced
    revision with no stamp, is rejected), and ``invalid_supersede_state`` (a
    ``superseded_by`` pointer is present iff ``lifecycle`` is ``superseded``).

    Args:
        text: The full message text.
        expected_epic: When supplied, the ``epic`` header MUST equal it
            (``epic_mismatch`` otherwise).
        filename: When supplied, the message file's name MUST begin with
            ``{sender_id}-`` (``filename_sender_mismatch`` otherwise).

    Returns:
        ``(ok, error_code, parsed_header)``. ``error_code`` is ``None`` when
        ``ok`` is ``True``. ``parsed_header`` is whatever the header parser
        recovered, returned even on rejection so callers can report context.
    """
    header, body = _split_message(text)
    for field in HEADER_FIELDS:
        if not header.get(field):
            return False, 'missing_header_field', header
    if header['envelope_version'] != str(ENVELOPE_VERSION):
        return False, 'unknown_envelope_version', header
    if header['sender_type'] not in SENDER_TYPES:
        return False, 'invalid_sender_type', header
    if header['kind'] not in KINDS:
        return False, 'invalid_kind', header
    if not body:
        return False, 'empty_payload', header
    if expected_epic is not None and header['epic'] != expected_epic:
        return False, 'epic_mismatch', header
    if filename is not None:
        match = _MESSAGE_NAME_RE.match(filename)
        if match is None or match.group('sender') != header['sender_id']:
            return False, 'filename_sender_mismatch', header
    state_error = _validate_state_fields(header)
    if state_error is not None:
        return False, state_error, header
    return True, None, header


def _validate_state_fields(header: dict[str, str]) -> str | None:
    """Validate the message-state fields; return an error code or ``None``.

    Kept a separate seam from :func:`validate_envelope`'s base sweep so the two
    concerns stay independently readable and the state invariants are testable
    in isolation. Absent fields read as their defaults (``lifecycle`` → ``live``,
    ``revision`` → ``0``, no ``amended`` / ``superseded_by``), so a virgin
    message passes every check.
    """
    lifecycle = header.get(_LIFECYCLE_FIELD, LIFECYCLE_LIVE)
    if lifecycle not in LIFECYCLES:
        return 'invalid_lifecycle'
    revision_raw = header.get(_REVISION_FIELD, '')
    revision = 0
    if revision_raw != '':
        if not revision_raw.isdigit():
            return 'invalid_revision'
        revision = int(revision_raw)
    amended = header.get(_AMENDED_FIELD, '').strip()
    # Monotonicity: a revision advance and its amendment stamp move together.
    if (revision >= 1) != bool(amended):
        return 'revision_not_monotonic'
    superseded_by = header.get(_SUPERSEDED_BY_FIELD, '').strip()
    if (lifecycle == LIFECYCLE_SUPERSEDED) != bool(superseded_by):
        return 'invalid_supersede_state'
    return None


def _foldered_archive_dir(archive_dir: Path, sender_id: str) -> Path | None:
    """Return ``archive/{sender_id}/`` when ``sender_id`` is path-safe, else ``None``.

    The archive is foldered per sender, so the sender becomes a DIRECTORY name.
    That is a stricter requirement than the filename-component check the sender
    already passes at write time: a value valid inside a filename (``..``, a
    dotted token) could traverse out of the archive as a directory. The sender
    is therefore re-validated against the path-safety validator here, and an
    unsafe one yields ``None`` rather than a traversing path — the single guard
    every foldered-archive path construction routes through.
    """
    if _validate_identifier(sender_id) is not None:
        return None
    return archive_dir / sender_id


def _foldered_archive_path(archive_dir: Path, name: str) -> Path | None:
    """Return ``archive/{sender}/{name}`` for a message name, or ``None``.

    ``None`` when ``name`` yields no sender (off-shape) or a sender that is
    unsafe as a directory component (:func:`_foldered_archive_dir`).
    """
    match = _MESSAGE_NAME_RE.match(name)
    if match is None:
        return None
    sender_dir = _foldered_archive_dir(archive_dir, match.group('sender'))
    if sender_dir is None:
        return None
    return sender_dir / name


def next_sequence(inbox_dir: Path, sender_id: str) -> int:
    """Return the next unused sequence number for ``sender_id`` in ``inbox_dir``.

    The scan spans the live queue (``inbox_dir``), the sender's foldered archive
    subdirectory (``inbox_dir / archive / {sender_id}``), AND any flat file left
    directly under ``inbox_dir / archive`` (a pre-migration twin), taking the
    highest ``{sender_id}-{NNN}.md`` sequence across all three. Consulting the
    archive is load-bearing: a drain retires a sender's messages out of the live
    queue, so a scan that missed them would reset the proposal to ``001`` and
    hand the sender a number whose archived twin already exists. Scanning BOTH
    the foldered subdirectory and the flat archive root is what keeps that
    guarantee across the foldering migration — an un-migrated flat twin is still
    seen, so no sequence is re-opened while an archive is only partly foldered.
    Each directory is scanned only when it exists, so an absent ``inbox/``,
    ``archive/``, or per-sender subdirectory contributes nothing rather than
    raising.

    Only the PROPOSAL widens. On its own this is still a check-then-act read —
    :func:`allocate_message_path` turns it into a safe claim by making the
    ``O_EXCL`` create the atomic step and retrying the next free sequence on
    collision, and that claim stays scoped to ``inbox/`` alone: no archived
    path is ever a claim target.
    """
    archive_dir = inbox_dir / INBOX_ARCHIVE_SUBDIR
    scan_dirs = [inbox_dir, archive_dir]
    foldered = _foldered_archive_dir(archive_dir, sender_id)
    if foldered is not None:
        scan_dirs.append(foldered)
    highest = 0
    for directory in scan_dirs:
        if not directory.is_dir():
            continue
        for entry in directory.iterdir():
            if not entry.is_file():
                continue
            match = _MESSAGE_NAME_RE.match(entry.name)
            if match is not None and match.group('sender') == sender_id:
                highest = max(highest, int(match.group('seq')))
    return highest + 1


def list_messages(inbox_dir: Path) -> list[Path]:
    """Return ``inbox_dir``'s message files in deterministic (sender, sequence) order.

    The enumeration seam behind ``inbox list``. Only direct children matching
    :data:`_MESSAGE_NAME_RE` are returned: the scan is non-recursive, so nothing
    under the ``archive/`` subdirectory is ever enumerated, and the subdirectory
    entry itself is filtered out by the file check along with any other
    off-shape name. That non-recursive scan is specific to ENUMERATION and is
    no longer a module-wide invariant — :func:`next_sequence` does consult the
    archive.

    Args:
        inbox_dir: The epic's ``inbox/`` directory; an absent directory yields
            an empty list.

    Returns:
        The message paths, sorted by sender id then numeric sequence.
    """
    if not inbox_dir.is_dir():
        return []
    entries: list[tuple[str, int, Path]] = []
    for entry in inbox_dir.iterdir():
        if not entry.is_file():
            continue
        match = _MESSAGE_NAME_RE.match(entry.name)
        if match is None:
            continue
        entries.append((match.group('sender'), int(match.group('seq')), entry))
    entries.sort(key=lambda item: (item[0], item[1]))
    return [path for _, _, path in entries]


class InboxCounts(NamedTuple):
    """The derived inbox tallies :func:`inbox_counts` returns.

    ``present`` is the same *which kind of zero* discriminator
    :func:`cmd_inbox_list` reports as ``inbox_state``: when it is ``False`` both
    counts are zero because the directory could not be looked at, not because
    the queue was empty.
    """

    queued: int
    archived: int
    present: bool


def inbox_counts(inbox_dir: Path) -> InboxCounts:
    """Count the epic's queued and archived messages, derived from the filesystem.

    The derivation seam behind ``resume-summary``'s inbox line. Both counts come
    from the SAME filename grammar the channel allocates with
    (:data:`_MESSAGE_NAME_RE`): the queued count re-uses :func:`list_messages`
    (so it agrees with ``inbox list`` by construction rather than by a parallel
    re-implementation), and the archived count applies the same shape filter to
    ``inbox/archive/``.

    Args:
        inbox_dir: The epic's ``inbox/`` directory.

    Returns:
        An :class:`InboxCounts`. An absent ``inbox/`` yields
        ``(0, 0, present=False)`` — *could not look* — rather than the
        indistinguishable ``(0, 0, present=True)`` an empty queue yields. A
        not-yet-created ``archive/`` simply contributes ``0``.
    """
    if not inbox_dir.is_dir():
        return InboxCounts(0, 0, False)
    archived = _count_archived(inbox_dir / INBOX_ARCHIVE_SUBDIR)
    return InboxCounts(len(list_messages(inbox_dir)), archived, True)


def _count_archived(archive_dir: Path) -> int:
    """Count archived messages across BOTH the foldered and flat layouts.

    Message-shaped files directly under ``archive/`` (a flat, pre-migration
    twin) and those one level down under a per-sender subdirectory
    (``archive/{sender}/``) both count. Counting both is what keeps the derived
    archive tally correct while an archive is only partly foldered — the same
    dual-layout awareness :func:`next_sequence` needs.
    """
    if not archive_dir.is_dir():
        return 0
    total = 0
    for entry in archive_dir.iterdir():
        if entry.is_file():
            if _MESSAGE_NAME_RE.match(entry.name) is not None:
                total += 1
        elif entry.is_dir():
            total += sum(
                1
                for sub in entry.iterdir()
                if sub.is_file() and _MESSAGE_NAME_RE.match(sub.name) is not None
            )
    return total


def resolve_message_path(inbox_dir: Path, name: str) -> tuple[Path, str]:
    """Resolve one message name to its path, probing the archive second.

    The single place the archive-probe ORDER lives. A drain relocates a consumed
    message under ``inbox/archive/{sender}/`` rather than deleting it, so a name
    that is absent from the live queue is not necessarily missing — it may have
    been consumed. Probing ``inbox/{name}`` first, then the sender's foldered
    ``inbox/archive/{sender}/{name}``, then any un-migrated flat
    ``inbox/archive/{name}`` twin, is what makes those two states distinguishable
    instead of collapsing both into "not found".

    Args:
        inbox_dir: The epic's ``inbox/`` directory.
        name: A bare message filename (already guarded by
            :func:`_is_bare_filename`).

    Returns:
        ``(path, location)`` where ``location`` is one of
        :data:`MESSAGE_LOCATIONS`. On ``missing`` the returned path is the
        LIVE-queue candidate, so a caller's not-found message keeps naming the
        queue path a reader would look at first.
    """
    queued = inbox_dir / name
    if queued.is_file():
        return queued, 'queued'
    archive_dir = inbox_dir / INBOX_ARCHIVE_SUBDIR
    foldered = _foldered_archive_path(archive_dir, name)
    if foldered is not None and foldered.is_file():
        return foldered, 'archived'
    flat = archive_dir / name
    if flat.is_file():
        return flat, 'archived'
    return queued, 'missing'


def allocate_message_path(inbox_dir: Path, sender_id: str, text: str) -> Path:
    """Claim the next free message path and write ``text`` into it.

    The exclusive create (``O_CREAT | O_EXCL``) IS the claim, so a concurrent
    or re-entered finalize cannot clobber another message: a collision raises
    ``FileExistsError`` and the loop advances to the next sequence. This is the
    exclusive-create mitigation the TOCTOU / check-then-act menu prescribes,
    and the same primitive ``_locks_core`` uses.

    Args:
        inbox_dir: The epic's ``inbox/`` directory (created when absent).
        sender_id: Sender identifier — the filename's ``{sender}`` segment.
        text: The full message text to write.

    Returns:
        Path to the newly created message file.
    """
    inbox_dir.mkdir(parents=True, exist_ok=True)
    sequence = next_sequence(inbox_dir, sender_id)
    while True:
        candidate = inbox_dir / f'{sender_id}-{sequence:03d}.md'
        try:
            handle = os.open(candidate, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            sequence += 1
            continue
        with os.fdopen(handle, 'w', encoding='utf-8') as stream:
            stream.write(text)
        return candidate


def classify_source_id(source_id: str) -> SourceIdClassification:
    """Classify ``request.md``'s ``source_id`` as an orchestrated plan pointer.

    Pure classification of the string ``phase-1-init`` already persisted — no
    filesystem access and no second detector. A pointer under
    ``.plan/local/orchestrator/{slug}/plans/`` whose ``{slug}`` is a safe
    identifier and whose id segment matches one of the three settled forms is
    orchestrated:

    - ``PLAN-{DIGITS}`` — ``PLAN-03-content-search-seam.md``
    - ``PLAN-{SLUG}-{DIGITS}`` — ``PLAN-CIS-01-content-search-seam.md``
    - ``{SLUG}-{DIGITS}`` — ``CIS-01-content-search-seam.md``

    Every other string is not, and ``detection`` says WHY over the closed
    :data:`DETECTION_TOKENS` vocabulary: ``orchestrated`` for a recognised
    pointer with a safe slug, ``unsafe_slug`` for a recognised pointer whose
    ``{slug}`` fails the path-safety validator, ``unrecognised_id`` for a path
    that IS an orchestrator plan-spec path but whose id segment matches none of
    the three forms, and ``not_orchestrator_pointer`` for everything else (a
    prose description, an unrelated path, a traversal attempt).

    Check order is load-bearing: the slug-safety check runs on the FULL match,
    and the shape-only check runs only after the full match has failed.

    Returns:
        A :class:`SourceIdClassification` carrying ``(orchestrated, epic,
        plan_spec, detection)``; ``epic`` and ``plan_spec`` are ``None`` on
        every negative verdict.
    """
    pointer = source_id.strip() if source_id else ''
    match = _SOURCE_ID_RE.match(pointer) if pointer else None
    if match is not None:
        slug = match.group('slug')
        if _validate_identifier(slug) is not None:
            return SourceIdClassification(False, None, None, 'unsafe_slug')
        return SourceIdClassification(True, slug, pointer, 'orchestrated')
    if pointer and _ORCHESTRATOR_PLANS_RE.match(pointer) is not None:
        return SourceIdClassification(False, None, None, 'unrecognised_id')
    return SourceIdClassification(False, None, None, 'not_orchestrator_pointer')


# =============================================================================
# Landing payload completeness (drain-completeness check)
# =============================================================================

#: The ``landing`` payload's fenced-block language tag and its schema marker. The
#: schema rides the block as a required key so an unrecognised payload version is
#: fail-closed exactly as ``envelope_version`` is (see
#: ``standards/landing-payload-spec.md``).
LANDING_FACTS_FENCE = 'landing-facts'
LANDING_FACTS_SCHEMA = 'landing-facts/1'

#: The required machine-readable fact keys a COMPLETE landing carries — the
#: mechanisable half of the report<->inbox delta the payload spec derives. A
#: landing missing any one is INCOMPLETE, and the drain records the gap rather
#: than reconciling as if the inbox had drained everything material.
#:
#: This tuple is the EXECUTABLE AUTHORITY: it is what
#: :func:`check_landing_completeness` actually enforces, so a key's presence here
#: is what makes it required in fact. Two documents restate the same set for
#: their own readers — ``landing-payload-spec.md`` § "Required machine-readable
#: fact keys" (the consumer-side contract) and ``emit-landing.md`` Step 2 (the
#: producer-side instruction) — and each is bound back to this tuple by a test
#: (``test_landing_completeness.py``
#: ``test_payload_spec_table_names_exactly_the_required_keys`` and
#: ``test_emit_landing_enumeration_names_exactly_the_required_keys``). Adding a
#: key here without updating both surfaces turns those tests red; that is the
#: intended failure, not a reason to relax them. Which document wins a prose
#: disagreement is settled by ``landing-payload-spec.md``'s own tie-break
#: sentence, which this comment does not restate or override.
LANDING_REQUIRED_KEYS: tuple[str, ...] = (
    'schema',
    'plan_id',
    'pr',
    'merge_state',
    'deliverables_total',
    'deliverables_done',
    'total_tokens',
    'steps',
)

#: The ANSWERED-degraded class: a value a producer is SANCTIONED to write
#: (``phase-6-finalize/standards/emit-landing.md``) that ASSERTS A REAL END STATE.
#: ``n/a`` says "there is no such thing", so at a key where that state is
#: legitimate it IS the fact rather than a gap. Compared case-insensitively after
#: stripping.
#:
#: This class is gated PER KEY by :data:`LANDING_SENTINEL_REJECTING_KEYS` —
#: unsupplied at the keys named there, an answer everywhere else.
LANDING_ANSWERED_SENTINELS: frozenset[str] = frozenset({'n/a'})

#: The COULD-NOT-READ class: a value that asserts only that NOTHING WAS OBSERVED.
#: ``unknown`` is named by ``standards/landing-payload-spec.md`` as "a PR whose
#: state could not be read, and asserts only that nothing was observed" — a
#: FAILED READ, never an end state. Compared case-insensitively after stripping.
#:
#: ⛔ This class carries **NO allow-list and no per-key gate**: a key holding one
#: of these values is unsupplied at EVERY key, ``pr`` and ``merge_state``
#: included — precisely the two keys :data:`LANDING_SENTINEL_REJECTING_KEYS`
#: deliberately omits. That asymmetry between the two classes is the whole point
#: of splitting them. Gating this class the way the answered class is gated would
#: reintroduce the defect the split closes: ``merge_state=unknown`` would drain as
#: a settled merge fact while recording that the merge state could not be read.
LANDING_COULD_NOT_READ_SENTINELS: frozenset[str] = frozenset({'unknown'})

#: The allow-list gate for the ANSWERED class ALONE
#: (:data:`LANDING_ANSWERED_SENTINELS`): the required keys at which ``n/a`` is NOT
#: an answer. Each names something a landed plan always has, so ``n/a`` there
#: records a producer that could not read it — a gap the drain must report, never
#: a fact it may reconcile against.
#:
#: ⛔ It does NOT gate :data:`LANDING_COULD_NOT_READ_SENTINELS`, which is
#: unsupplied at every key with no allow-list. Reading this set as "the keys at
#: which a degraded value is rejected" — as though one vocabulary existed — is
#: exactly the conflation the two-class split removes.
#:
#: The set is deliberately a SUBSET of :data:`LANDING_REQUIRED_KEYS`, and the
#: asymmetry is the point: ``pr`` and ``merge_state`` stay allowed to be ``n/a``
#: because "no PR exists" is a real end state the payload spec names, so an
#: ANSWERED-degraded value there is an answer rather than a gap. They are NOT
#: thereby allowed to be ``unknown`` — that value is a failed read at every key,
#: which is why the fix is this split and NOT the widening of this set to include
#: ``merge_state``. ``schema`` needs no entry —
#: :func:`check_landing_completeness` fail-closes on any value other than
#: :data:`LANDING_FACTS_SCHEMA` before the required-key sweep runs, so a sentinel
#: of either class is already rejected there by the stricter check.
LANDING_SENTINEL_REJECTING_KEYS: frozenset[str] = frozenset({
    'plan_id',
    'deliverables_total',
    'deliverables_done',
    'total_tokens',
    'steps',
})


def _is_unsupplied(key: str, facts: dict[str, str]) -> bool:
    """Return whether ``key`` carries no usable value in ``facts``.

    The SINGLE named predicate both degraded-value classes route through, so the
    two vocabularies stay one decision rather than two drifting checks. A key is
    unsupplied in exactly three cases, tested in this order:

    1. **Absent or empty** — nothing was written at all.
    2. **A COULD-NOT-READ sentinel** (:data:`LANDING_COULD_NOT_READ_SENTINELS`) —
       unsupplied at EVERY key, with no allow-list. The value asserts only that
       nothing was observed, which is never an answer, so there is no key at
       which it could legitimately stand in for a fact. This test runs BEFORE the
       per-key gate below precisely so the gate cannot exempt it: ``pr`` and
       ``merge_state`` are outside
       :data:`LANDING_SENTINEL_REJECTING_KEYS`, and a gated could-not-read value
       would drain there as a settled fact.
    3. **An ANSWERED sentinel** (:data:`LANDING_ANSWERED_SENTINELS`) at a key
       named by :data:`LANDING_SENTINEL_REJECTING_KEYS` — the per-key gate. At
       every other key the value asserts a real end state and IS the fact.

    Both sentinel comparisons are exact after stripping and case-folding, so a
    real value that merely CONTAINS a sentinel's letters is unaffected.
    """
    value = facts.get(key, '')
    if not value:
        return True
    normalised = value.strip().lower()
    if normalised in LANDING_COULD_NOT_READ_SENTINELS:
        return True
    if key not in LANDING_SENTINEL_REJECTING_KEYS:
        return False
    return normalised in LANDING_ANSWERED_SENTINELS


#: Matches the first ``landing-facts`` fenced block in a payload body. DOTALL so
#: the body spans lines; non-greedy so it stops at the first closing fence.
_LANDING_FENCE_RE = re.compile(
    r'^```' + LANDING_FACTS_FENCE + r'[ \t]*\n(?P<body>.*?)\n```[ \t]*$',
    re.MULTILINE | re.DOTALL,
)


def parse_landing_facts(payload_body: str) -> dict[str, str] | None:
    """Extract the ``landing-facts`` fenced block from a landing body as a dict.

    Returns the ``key=value`` pairs of the first ``landing-facts`` fenced block, or
    ``None`` when the body carries NO such block at all — the pre-fix, prose-only
    landing. The distinction is load-bearing: ``None`` (no block) is what
    :func:`check_landing_completeness` maps to "every required key missing", so a
    narrative-only landing is reported incomplete rather than silently accepted.

    The parse is lenient about the block's CONTENT (blank lines, ``#`` comment
    lines, and lines with no ``=`` are skipped) because completeness is judged by
    the required-key check, not by parse strictness; it is strict only about the
    block's PRESENCE.
    """
    match = _LANDING_FENCE_RE.search(payload_body or '')
    if match is None:
        return None
    facts: dict[str, str] = {}
    for line in match.group('body').splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith('#') or '=' not in stripped:
            continue
        key, _, value = stripped.partition('=')
        key = key.strip()
        if key:
            facts[key] = value.strip()
    return facts


def check_landing_completeness(payload_body: str) -> tuple[bool, list[str]]:
    """Return ``(complete, missing_keys)`` for a landing payload body.

    A landing is COMPLETE when it carries a ``landing-facts`` block whose ``schema``
    is :data:`LANDING_FACTS_SCHEMA` and which SUPPLIES every key in
    :data:`LANDING_REQUIRED_KEYS`. Non-empty is necessary but NOT sufficient: a
    degraded value counts as unsupplied — at the keys
    :data:`LANDING_SENTINEL_REJECTING_KEYS` names for the ANSWERED class, and at
    EVERY key for the COULD-NOT-READ class. See the fourth bullet below.
    Otherwise it is INCOMPLETE and ``missing_keys`` names why:

    - No block at all (a prose-only landing) -> every required key is missing. This
      is the case the drain-completeness check exists to catch: a landing carrying
      only narrative transmits none of the mechanisable delta, so the operator
      paste keeps surfacing what the inbox never saw.
    - Block present but ``schema`` != :data:`LANDING_FACTS_SCHEMA` -> ``['schema']``,
      fail-closed like the envelope's ``unknown_envelope_version`` — a mismatched
      payload version is never best-effort-accepted.
    - Block present with the right schema but missing (or empty) required keys ->
      exactly those keys.
    - Block present with the right schema but a DEGRADED VALUE where a fact
      belongs -> that key too. Every degraded value is truthy, so a presence-only
      check would accept a landing whose token total, step list and deliverable
      counts all failed to read. The two classes are rejected on DIFFERENT terms,
      and the difference is the point:

      - An ANSWERED sentinel (``n/a``, per :data:`LANDING_ANSWERED_SENTINELS`) is
        rejected only at :data:`LANDING_SENTINEL_REJECTING_KEYS`. ``pr`` and
        ``merge_state`` stay allowed to be ``n/a``, because "no PR exists" is a
        real end state the payload spec names and the value there is an answer
        rather than a gap.
      - A COULD-NOT-READ sentinel (``unknown``, per
        :data:`LANDING_COULD_NOT_READ_SENTINELS`) is rejected at EVERY key, with
        no allow-list — ``pr`` and ``merge_state`` included. It asserts only that
        nothing was observed, so it is a failed read wherever it appears. This is
        why the fix was to SPLIT the vocabulary rather than to add ``merge_state``
        to the rejecting set: ``merge_state=n/a`` must stay an answer while
        ``merge_state=unknown`` must read as a gap, and one gated vocabulary
        cannot express both.

    A check that PASSED on a prose-only landing would be the vacuous guard this one
    exists to replace; the no-block branch is what keeps it non-vacuous, and it is
    pinned by a test that feeds a pre-fix prose landing and asserts the failure.
    """
    facts = parse_landing_facts(payload_body)
    if facts is None:
        return False, list(LANDING_REQUIRED_KEYS)
    if facts.get('schema') != LANDING_FACTS_SCHEMA:
        return False, ['schema']
    missing = [key for key in LANDING_REQUIRED_KEYS if _is_unsupplied(key, facts)]
    return (not missing), missing


def find_stream_end_marker(inbox_dir: Path, epic: str, sender_id: str) -> str | None:
    """Return the name of ``sender_id``'s queued stream-end marker, or ``None``.

    The ONE predicate behind both stream-closure entry points — the write-side
    refusal (:func:`cmd_inbox_write`) and the close-side idempotence
    (:func:`cmd_inbox_close_stream`). A single seam is what keeps the two from
    disagreeing about whether a stream is closed: they would otherwise be two
    independent scans that could drift.

    Only a marker that VALIDATES counts. A malformed file claiming
    ``lifecycle=stream-end`` is not a closure the drain would honour either — it
    is excluded from ``inbox list``'s ``closed_senders`` for the same reason — so
    treating it as one here would refuse writes on the strength of a message the
    drain will report as invalid.

    ⛔ **The scan covers ``inbox/`` only, never ``inbox/archive/``.** That bound
    is deliberate and is a real limitation, stated rather than hidden: once the
    drain consumes and archives a sender's marker, this predicate no longer finds
    it and that sender may write again. The queue is the live state, and a
    consumed marker has been acted on; re-refusing against the archive would make
    the guard depend on drain history rather than on queue state. A sender that
    must stay closed across a drain is a larger design question this guard does
    not settle.

    **Cost, stated precisely because the two bounds differ.** The enumeration is
    O(n log n) in the queue depth: :func:`list_messages` lists the directory once
    and sorts the result. The FILE READS are
    not — the loop skips a path whose filename sender segment does not match
    ``sender_id`` *before* opening it, so ``read_text`` and
    :func:`validate_envelope` run at most once per message **that sender** has
    queued. So a write costs one directory listing plus O(this sender's queued
    messages) reads, not O(queue) reads. Both are accepted rather than optimised:
    the queue is drained between plans and is small by construction, and the
    alternative (an index, or trusting the filename) would either add a second
    source of truth or honour a marker the validator would reject. Revisit only
    if a queue is ever allowed to grow unbounded.

    Args:
        inbox_dir: The epic's ``inbox/`` directory.
        epic: The epic slug, passed through as ``expected_epic`` so a marker
            filed against a different epic is not honoured here.
        sender_id: The sender whose closure is being tested.

    Returns:
        The bare filename of the first validating stream-end marker for that
        sender in enumeration order, or ``None`` when the sender has none.
    """
    for path in list_messages(inbox_dir):
        match = _MESSAGE_NAME_RE.match(path.name)
        if match is None or match.group('sender') != sender_id:
            continue
        try:
            text = path.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            continue
        ok, _, header = validate_envelope(text, expected_epic=epic, filename=path.name)
        if ok and header.get(_LIFECYCLE_FIELD) == LIFECYCLE_STREAM_END:
            return path.name
    return None


def cmd_inbox_write(args: Any) -> dict[str, Any]:
    """Append one message to the epic's inbox.

    The write boundary is enforced by construction: the target resolves
    strictly to ``get_store_dir('orchestrator', slug) / 'inbox' /
    '{sender_id}-{NNN}.md'``, both components are validated identifiers, and no
    caller-supplied output path exists in the argument surface. The payload
    arrives via ``--payload-file`` (staged with the Write tool) so no message
    body ever passes through a shell argument.

    Refuses a sender that has already closed its stream (``stream_closed``). The
    check runs BEFORE the ``--target-plan`` deliverability guard, because it is
    about whether this sender may write at all, which does not depend on where
    the message was aimed. Without it the ``stream-end`` marker declared a
    closure nothing enforced.
    """
    invalid = _validate_identifier(args.slug)
    if invalid:
        return _error('invalid_slug', invalid, slug=args.slug)
    invalid = _validate_identifier(args.sender_id)
    if invalid:
        return _error('invalid_sender_id', invalid, slug=args.slug)
    if args.sender_type not in SENDER_TYPES:
        return _error(
            'invalid_sender_type',
            f'--sender-type must be one of {sorted(SENDER_TYPES)}, got: {args.sender_type}',
            slug=args.slug,
        )
    if args.kind not in KINDS:
        return _error(
            'invalid_kind',
            f'--kind must be one of {sorted(KINDS)}, got: {args.kind}',
            slug=args.slug,
        )
    root = get_store_dir(ORCHESTRATOR_STORE, args.slug)
    if not root.is_dir():
        return _error(
            'epic_not_found',
            f'epic {args.slug!r} has no tree at {root}; run scaffold first',
            slug=args.slug,
        )
    # Stream-closure guard. A sender that filed a ``lifecycle=stream-end`` marker
    # declared its stream ended; without this refusal that declaration meant
    # nothing and the sender could keep writing, so every consumer reading
    # ``closed_senders`` as "this sender will send no more" was reading a claim
    # the machinery did not support.
    closed_by = find_stream_end_marker(root / INBOX_SUBDIR, args.slug, args.sender_id)
    if closed_by is not None:
        return _error(
            'stream_closed',
            f'sender {args.sender_id!r} closed its stream in epic {args.slug!r} '
            f'with marker {closed_by}; a closed stream accepts no further '
            'messages. The marker is the sender\'s own declaration that it will '
            'send no more, and the drain reports it as such — writing after it '
            'would contradict a signal the orchestrator has already acted on.',
            slug=args.slug,
            sender_id=args.sender_id,
            marker=closed_by,
        )
    # Deliverability guard. ``--target-plan`` NAMES a plan the message is aimed
    # at, but the inbox is the epic's plan->orchestrator OUTBOX, drained BETWEEN
    # plans; it has no delivery path to a plan, and a plan never reads it. When
    # the named plan is currently RUNNING, the message is architecturally
    # undeliverable — the plan will have finished before the orchestrator's next
    # drain — so it is REFUSED at write time and never silently queued for a
    # reader that will not exist. A message aimed at a plan that is NOT running
    # (landed, parked, or absent from the queue) is not blocked: it queues as an
    # ordinary epic-addressed message the orchestrator drains. Building a mid-run
    # delivery channel is a larger design question and is deliberately NOT done
    # here — this guard only makes the existing undeliverability visible.
    target_plan = getattr(args, 'target_plan', None)
    if target_plan is not None:
        invalid = _validate_identifier(target_plan)
        if invalid:
            return _error('invalid_target_plan', invalid, slug=args.slug)
        if target_plan in _running_plan_ids(root):
            return _error(
                'undeliverable_to_running_plan',
                f'message names target plan {target_plan!r}, which is currently '
                f'running in epic {args.slug!r}. The inbox is the epic OUTBOX, '
                'drained by the orchestrator between plans; it has no delivery '
                'path to a running plan, so this message would never be read. It '
                'is refused at write time rather than silently queued. To reach a '
                'running plan, do not aim a message at it — mid-run delivery is '
                'not a channel this inbox provides.',
                slug=args.slug,
                target_plan=target_plan,
            )
    payload_path = Path(args.payload_file)
    if not payload_path.is_file():
        return _error(
            'payload_not_found',
            f'--payload-file not found: {payload_path}',
            slug=args.slug,
        )
    payload_body = payload_path.read_text(encoding='utf-8').strip()
    if not payload_body:
        return _error(
            'empty_payload',
            f'--payload-file is empty: {payload_path}',
            slug=args.slug,
        )
    text = compose_envelope(
        args.sender_type, args.sender_id, args.slug, args.kind, payload_body
    )
    message_path = allocate_message_path(root / INBOX_SUBDIR, args.sender_id, text)
    return {
        'status': 'success',
        'operation': 'inbox-write',
        'slug': args.slug,
        'store': ORCHESTRATOR_STORE,
        'sender_type': args.sender_type,
        'sender_id': args.sender_id,
        'kind': args.kind,
        'message': message_path.name,
        'path': str(message_path),
    }


def cmd_inbox_validate(args: Any) -> dict[str, Any]:
    """Validate one already-written inbox message against the envelope schema.

    ``--message`` names a file INSIDE the epic's ``inbox/`` directory (a bare
    filename, never a path), so the read surface is bounded by the same
    construction the write surface uses. The epic slug and the filename are
    both fed to :func:`validate_envelope`, so ``epic_mismatch`` and
    ``filename_sender_mismatch`` are reachable here.

    Resolution probes the archive via :func:`resolve_message_path`, so a
    CONSUMED message is distinguishable from a MISSING one. Three outcomes:

    - present in ``inbox/`` → success with ``location: queued`` and an empty
      ``archive_path``.
    - absent from ``inbox/`` but present in ``inbox/archive/`` → success with
      ``location: archived`` and ``archive_path`` set to the resolved archived
      path. The archived read goes through the SAME :func:`validate_envelope`
      seam and reports the same header fields as the queued branch.
    - present at neither path → ``file_not_found``, which now means exactly
      that: not queued AND not archived.

    Resolution keeps using :func:`_inbox_dir` (the ``allow_archived=True`` read
    root), so an archived EPIC still resolves as before — that fallback is
    about the epic tree, and the archive probe here is about the message.
    """
    invalid = _validate_identifier(args.slug)
    if invalid:
        return _error('invalid_slug', invalid, slug=args.slug)
    name = args.message
    if not _is_bare_filename(name):
        return _error(
            'invalid_message_name',
            f'--message must be a bare filename inside inbox/, got: {name}',
            slug=args.slug,
        )
    path, location = resolve_message_path(_inbox_dir(args.slug), name)
    if location == 'missing':
        return _error(
            'file_not_found', f'inbox message not found: {path}', slug=args.slug
        )
    ok, error_code, header = validate_envelope(
        path.read_text(encoding='utf-8'), expected_epic=args.slug, filename=name
    )
    if not ok:
        return _error(
            error_code or 'invalid_envelope',
            f'inbox message {name} failed validation: {error_code}',
            slug=args.slug,
            message_name=name,
        )
    return {
        'status': 'success',
        'operation': 'inbox-validate',
        'slug': args.slug,
        'store': ORCHESTRATOR_STORE,
        'message': name,
        'location': location,
        'archive_path': str(path) if location == 'archived' else '',
        'envelope_version': header['envelope_version'],
        'sender_type': header['sender_type'],
        'sender_id': header['sender_id'],
        'kind': header['kind'],
        'created': header['created'],
        'lifecycle': header.get(_LIFECYCLE_FIELD, LIFECYCLE_LIVE),
        'revision': header.get(_REVISION_FIELD, '0'),
        'amended': header.get(_AMENDED_FIELD, ''),
        'superseded_by': header.get(_SUPERSEDED_BY_FIELD, ''),
    }


def cmd_inbox_list(args: Any) -> dict[str, Any]:
    """Enumerate and validate every message queued in the epic's inbox.

    The drain's enumeration seam: one row per message, in deterministic
    (sender, sequence) order, each row carrying the header context the
    orchestrator routes on plus the validation verdict. A malformed message is
    REPORTED with the validator's distinct error code — never silently dropped,
    and never aborting the enumeration — so a broken message stays visible to
    the drain instead of disappearing from it. A message that cannot even be
    READ (non-UTF-8 bytes, or the file vanishing mid-drain under a concurrent
    writer) is reported the same way, with the distinct ``unreadable`` code, so
    a read failure never aborts the rest of the enumeration either. Consumed
    messages already moved under ``inbox/archive/`` are not enumerated, which
    is what makes a re-scan of a completed drain a no-op.

    The payload also states WHICH KIND OF ZERO a ``count: 0`` is, so the
    three zeros are separately representable: ``epic_not_found`` (no epic tree
    at all — the retained error branch), ``inbox_state: missing`` (the epic is
    there but has no ``inbox/`` directory, so the enumeration could not look),
    and ``inbox_state: present`` with ``count: 0`` (it looked and found
    nothing). ``inbox_dir`` reports the absolute path the enumeration actually
    scanned. The ``inbox_state`` discriminator is captured ONCE, immediately
    before the enumeration loop, so it reports the same observation the
    enumeration itself acted on: under a concurrent drain that removes
    ``inbox/`` mid-scan, the payload can never pair a non-zero ``count`` with
    ``inbox_state: missing``. An absent ``inbox/`` is NOT a fault — the verb
    still returns ``status: success`` so a drain is never aborted by it; the
    discriminator rides the payload, not the status.
    """
    invalid = _validate_identifier(args.slug)
    if invalid:
        return _error('invalid_slug', invalid, slug=args.slug)
    root = _read_epic_root(args.slug)
    if not root.is_dir():
        return _error(
            'epic_not_found',
            f'epic {args.slug!r} has no tree at {root}; run scaffold first',
            slug=args.slug,
        )
    inbox_dir = root / INBOX_SUBDIR
    inbox_present = inbox_dir.is_dir()
    messages: list[dict[str, Any]] = []
    for path in list_messages(inbox_dir):
        try:
            text = path.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            messages.append(
                {
                    'name': path.name,
                    'sender_id': '',
                    'kind': '',
                    'created': '',
                    'lifecycle': '',
                    'revision': '',
                    'superseded_by': '',
                    'valid': False,
                    'error': 'unreadable',
                }
            )
            continue
        ok, error_code, header = validate_envelope(
            text,
            expected_epic=args.slug,
            filename=path.name,
        )
        messages.append(
            {
                'name': path.name,
                'sender_id': header.get('sender_id', ''),
                'kind': header.get('kind', ''),
                'created': header.get('created', ''),
                'lifecycle': header.get(_LIFECYCLE_FIELD, LIFECYCLE_LIVE),
                'revision': header.get(_REVISION_FIELD, '0'),
                'superseded_by': header.get(_SUPERSEDED_BY_FIELD, ''),
                'valid': ok,
                'error': '' if ok else (error_code or 'invalid_envelope'),
            }
        )
    # ``live_count`` is the drainable set — VALID messages still presenting as
    # live, so a superseded message (resolvable but retired), a stream-end marker,
    # AND an invalid message are all excluded. That last exclusion is why
    # ``live_count`` alone does not discriminate: with ``closed_senders`` and
    # ``invalid_count`` it separates THREE zeros, not two.
    #
    #   live_count 0 + closed_senders empty     + invalid_count 0  -> EMPTY
    #   live_count 0 + closed_senders non-empty + invalid_count 0  -> FINISHED
    #   live_count 0 + closed_senders any       + invalid_count >0 -> BLOCKED
    #
    # BLOCKED is the one a two-way reading absorbs into EMPTY: a queue holding
    # nothing but malformed messages reports ``live_count: 0`` while carrying work
    # nobody has read, so reading it as empty claims a completed drain over
    # messages the drain declined. See ``standards/inbox-envelope.md`` § Drain
    # semantics, which is the same table for the drain's own reader.
    live_count = sum(
        1 for row in messages if row['valid'] and row['lifecycle'] == LIFECYCLE_LIVE
    )
    closed_senders = sorted(
        {
            row['sender_id']
            for row in messages
            if row['valid']
            and row['lifecycle'] == LIFECYCLE_STREAM_END
            and row['sender_id']
        }
    )
    return {
        'status': 'success',
        'operation': 'inbox-list',
        'slug': args.slug,
        'store': ORCHESTRATOR_STORE,
        'inbox_dir': str(inbox_dir),
        'inbox_state': 'present' if inbox_present else 'missing',
        'count': len(messages),
        'live_count': live_count,
        'closed_senders': closed_senders,
        'invalid_count': sum(1 for row in messages if not row['valid']),
        'messages': messages,
    }


def _archive_success(
    slug: str, name: str, dest: Path, already_archived: bool
) -> dict[str, Any]:
    """Build the ``inbox-archive`` success envelope."""
    return {
        'status': 'success',
        'operation': 'inbox-archive',
        'slug': slug,
        'store': ORCHESTRATOR_STORE,
        'message': name,
        'already_archived': already_archived,
        'archived_to': str(dest),
    }


def cmd_inbox_archive(args: Any) -> dict[str, Any]:
    """Retire one consumed message under ``inbox/archive/``.

    The destination filename is the source ``--message`` name by default, and
    the ``--as-name`` override when one is supplied — the recovery path for a
    message stranded by a pre-fix sequence collision. An override is subject to
    two separate rules: the retained :func:`_is_bare_filename` guard still
    yields ``invalid_message_name`` for a path-shaped value, and the
    sender-provenance constraint requires the override to keep the source
    message's ``{sender}-`` segment.

    Archival is the consume marker: the message leaves the enumeration
    :func:`cmd_inbox_list` returns while its audit record survives at the
    archived path, so the append-only invariant is unbroken — the file is
    relocated, never edited or deleted. Because this verb MUTATES, the epic
    root resolves strictly (:func:`_mutate_epic_root`): an epic whose active
    tree is gone is refused with ``epic_not_found`` rather than silently
    relocating a file inside its frozen archived record.

    The relocation itself is an ATOMIC claim rather than a check-then-move:
    :func:`os.link` creates ``inbox/archive/{sender}/{name}`` (the foldered
    destination) without ever replacing an existing destination, and the source
    is unlinked only once that claim has succeeded. Every response is derived from the claim's own outcome, so two
    racing drains cannot both clear a presence check and have the loser fault
    on a source the winner already moved:

    - claim refused because the source is gone (``FileNotFoundError``) and the
      destination is present → idempotent success (``already_archived``), so a
      resumed, repeated, or race-losing drain is safe.
    - claim refused because the source is gone and the destination is absent
      → ``error: file_not_found``.
    - claim refused because the destination already exists
      (``FileExistsError``) and ``dest`` is a DISTINCT inode from ``source``
      → ``error: archive_conflict`` (never clobber the retired audit record).
    - claim refused because the destination already exists but ``dest`` and
      ``source`` are the SAME inode — the claim is a hard link, so a
      concurrent winner that has linked and not yet unlinked leaves both
      paths pointing at one file → idempotent success (``already_archived``),
      because ``dest`` is that winner's own in-flight artifact rather than a
      second, competing audit record. Source presence is NOT the
      discriminator; inode identity is.
    - claim refused for any other reason (a bare ``--message`` that names a
      DIRECTORY under ``inbox/`` makes ``os.link`` raise a plain ``OSError``)
      → ``error: invalid_message_name``.
    - claim succeeded → unlink the source and report the relocation.
    - refused BEFORE the claim because a supplied ``--as-name`` override does
      not preserve the source message's ``{sender}-`` segment — or because the
      source ``--message`` name yields no sender segment at all — →
      ``error: as_name_sender_mismatch``. Distinct from the retained
      ``invalid_message_name`` bare-filename refusal, so the two rules are
      separately assertable.
    """
    invalid = _validate_identifier(args.slug)
    if invalid:
        return _error('invalid_slug', invalid, slug=args.slug)
    name = args.message
    if not _is_bare_filename(name):
        return _error(
            'invalid_message_name',
            f'--message must be a bare filename inside inbox/, got: {name}',
            slug=args.slug,
        )
    dest_name = getattr(args, 'as_name', None) or name
    if dest_name != name:
        if not _is_bare_filename(dest_name):
            return _error(
                'invalid_message_name',
                '--as-name must be a bare filename inside inbox/archive/, '
                f'got: {dest_name}',
                slug=args.slug,
                message_name=name,
            )
        source_match = _MESSAGE_NAME_RE.match(name)
        sender = source_match.group('sender') if source_match is not None else None
        if sender is None or not dest_name.startswith(f'{sender}-'):
            required = f'{sender}-' if sender else f'(none derivable from {name})'
            return _error(
                'as_name_sender_mismatch',
                "--as-name must preserve the source message's sender segment; "
                f'required prefix {required}, got: {dest_name}',
                slug=args.slug,
                message_name=name,
            )
    root = _mutate_epic_root(args.slug)
    if not root.is_dir():
        return _error(
            'epic_not_found',
            f'epic {args.slug!r} has no active tree at {root}; '
            'refusing to archive inside an archived epic',
            slug=args.slug,
        )
    inbox_dir = root / INBOX_SUBDIR
    source = inbox_dir / name
    archive_dir = inbox_dir / INBOX_ARCHIVE_SUBDIR
    # The destination is foldered under archive/{sender}/, keyed on the SOURCE
    # message's sender — so a message and its ``--as-name`` recovery twin land in
    # the same per-sender subdirectory (the override is already constrained to
    # ``{source_sender}-*``). An off-shape source (no derivable sender — e.g. the
    # literal ``archive``, which names a directory) keeps a flat destination so
    # its os.link OSError still surfaces as ``invalid_message_name`` below. A
    # shaped source whose sender is unsafe as a DIRECTORY component is refused
    # fail-closed here rather than allowed to traverse out of the archive — the
    # check the sender's filename-component validation does not itself make.
    source_match = _MESSAGE_NAME_RE.match(name)
    if source_match is not None:
        sender_dir = _foldered_archive_dir(archive_dir, source_match.group('sender'))
        if sender_dir is None:
            return _error(
                'invalid_message_name',
                f'the sender segment of {name!r} is not safe as an archive '
                'directory name',
                slug=args.slug,
                message_name=name,
            )
        dest = sender_dir / dest_name
    else:
        dest = archive_dir / dest_name
    # Created before the claim so a FileNotFoundError from os.link below can
    # only mean "the source is gone", never "the archive directory is missing".
    # Guarded in its OWN try/except (never folded into the os.link try block
    # below) so a genuine filesystem failure here (permission denied, disk
    # full, read-only filesystem) returns its own precise error code instead
    # of either propagating uncaught or being mislabelled as the unrelated
    # `invalid_message_name` the broader `except OSError` below reports for
    # `os.link`.
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return _error(
            'archive_dir_unavailable',
            f'could not create the inbox archive directory {dest.parent}: {exc}',
            slug=args.slug,
            message_name=name,
        )
    try:
        os.link(source, dest)
    except FileNotFoundError:
        if dest.is_file():
            return _archive_success(args.slug, name, dest, already_archived=True)
        return _error(
            'file_not_found',
            f'inbox message not found: {source}',
            slug=args.slug,
            message_name=name,
        )
    except FileExistsError:
        # The claim is a HARD LINK, so between a concurrent winner's own
        # ``os.link`` and its ``source.unlink()`` the two paths are the SAME
        # inode. Source presence therefore does NOT discriminate: it is still
        # true inside that window, where ``dest`` is the winner's in-flight
        # artifact rather than a second, competing audit record. Inode
        # identity is the discriminator.
        try:
            distinct = not source.samefile(dest)
        except FileNotFoundError:
            # ``source`` vanished between the claim and this check (the winner
            # finished its unlink), or ``dest`` did — either way there is no
            # distinct record to protect, so fall through to idempotent
            # success exactly as a plainly race-losing drain does.
            distinct = False
        if distinct:
            return _error(
                'archive_conflict',
                f'inbox message {name} is already archived at {dest}; '
                'refusing to clobber the audit record',
                slug=args.slug,
                message_name=name,
                archived_to=str(dest),
            )
        return _archive_success(args.slug, name, dest, already_archived=True)
    except OSError as exc:
        # Ordering is load-bearing: FileNotFoundError and FileExistsError are
        # both OSError subclasses and MUST stay above this broader clause. A
        # bare component like the literal ``archive`` clears
        # :func:`_is_bare_filename` yet names a DIRECTORY once joined onto
        # ``inbox/``, and ``os.link`` refuses a directory source with a plain
        # OSError (``PermissionError`` on most platforms) that neither narrow
        # clause catches — without this clause it escapes the handler instead
        # of returning a structured response.
        return _error(
            'invalid_message_name',
            f'--message does not name an archivable file: {name} ({exc})',
            slug=args.slug,
            message_name=name,
        )
    source.unlink()
    return _archive_success(args.slug, name, dest, already_archived=False)


def _read_payload_body(payload_file: str) -> tuple[str | None, dict[str, Any] | None]:
    """Read a staged payload body, returning ``(body, error)``.

    Mirrors :func:`cmd_inbox_write`'s payload handling so ``amend`` accepts a
    correction body through the same staged-file surface — no message body ever
    crosses a shell argument. ``(None, error_dict)`` on a missing or empty file;
    ``(body, None)`` on success. The error dict carries no ``slug``; the caller
    adds it.
    """
    payload_path = Path(payload_file)
    if not payload_path.is_file():
        return None, {
            'error': 'payload_not_found',
            'message': f'--payload-file not found: {payload_path}',
        }
    body = payload_path.read_text(encoding='utf-8').strip()
    if not body:
        return None, {
            'error': 'empty_payload',
            'message': f'--payload-file is empty: {payload_path}',
        }
    return body, None


def _resolve_live_message(
    slug: str, name: str
) -> tuple[Path | None, dict[str, str], str, dict[str, Any] | None]:
    """Resolve a bare message name to a QUEUED, valid message for mutation.

    The shared front half of ``amend`` and ``supersede``: both mutate a message
    IN PLACE, so both resolve the epic root strictly (no archived read-fallback),
    require the message to be present in the LIVE queue rather than the archive
    (a consumed message is past correcting), and require it to validate before it
    is touched (mutating a message that is already malformed would silently ship
    a broken result). It does NOT filter on ``lifecycle`` — the
    lifecycle-specific guard is the caller's, because ``amend`` and ``supersede``
    refuse different states (``amend`` refuses any non-``live`` message;
    ``supersede`` refuses only a ``stream-end`` marker). Returns
    ``(path, header, body, error_dict)``; on any refusal ``path`` is ``None`` and
    ``error_dict`` carries ``error``/``message`` (no ``slug`` — the caller adds
    it).
    """
    root = _mutate_epic_root(slug)
    if not root.is_dir():
        return None, {}, '', {
            'error': 'epic_not_found',
            'message': f'epic {slug!r} has no active tree at {root}',
        }
    path, location = resolve_message_path(root / INBOX_SUBDIR, name)
    if location == 'missing':
        return None, {}, '', {
            'error': 'file_not_found',
            'message': f'inbox message not found: {path}',
        }
    if location != 'queued':
        return None, {}, '', {
            'error': 'not_live',
            'message': (
                f'inbox message {name} is {location}, not live; a consumed '
                'message is past correcting through this surface'
            ),
        }
    text = path.read_text(encoding='utf-8')
    ok, error_code, header = validate_envelope(text, expected_epic=slug, filename=name)
    if not ok:
        return None, header, '', {
            'error': error_code or 'invalid_envelope',
            'message': f'cannot mutate an invalid message: {error_code}',
        }
    _header, body = _split_message(text)
    return path, dict(header), body, None


def cmd_inbox_amend(args: Any) -> dict[str, Any]:
    """Correct the body of a filed message IN PLACE through the sanctioned verb.

    The channel is append-only for a sender's OWN new files, but a message found
    wrong after filing had no sanctioned correction path — writing a successor
    dirtied the queue, and editing the file directly broke the scripts-only
    access rule. ``amend`` is that missing verb: it replaces the body with the
    staged ``--payload-file`` content, PRESERVES ``created`` (so the timestamp
    keeps naming the message's first filing), stamps ``amended`` at the current
    UTC instant, and bumps a monotonic ``revision``. The message stays
    ``lifecycle=live``.

    The mutation is made VISIBLE from the envelope alone — the load-bearing half:
    a bare in-place body edit that left the envelope untouched would only replace
    an authorized bypass with an unauthorized one. The ``amended`` /
    ``revision`` stamp is what distinguishes a corrected message from a virgin
    one without diffing bodies.

    Refuses an unsafe slug (``invalid_slug``), a path-shaped ``--message``
    (``invalid_message_name``), a missing/empty payload (``payload_not_found`` /
    ``empty_payload``), an absent epic (``epic_not_found``), a message present at
    neither path (``file_not_found``), a consumed message (``not_live``), an
    already-invalid message (the validator's own code), and a message that is not
    currently ``live`` — a superseded or stream-end message is not amendable
    (``not_amendable``).
    """
    invalid = _validate_identifier(args.slug)
    if invalid:
        return _error('invalid_slug', invalid, slug=args.slug)
    name = args.message
    if not _is_bare_filename(name):
        return _error(
            'invalid_message_name',
            f'--message must be a bare filename inside inbox/, got: {name}',
            slug=args.slug,
        )
    body, payload_error = _read_payload_body(args.payload_file)
    if payload_error is not None:
        return _error(payload_error['error'], payload_error['message'], slug=args.slug)
    path, header, _old_body, resolve_error = _resolve_live_message(args.slug, name)
    if resolve_error is not None:
        return _error(
            resolve_error['error'],
            resolve_error['message'],
            slug=args.slug,
            message_name=name,
        )
    assert path is not None  # resolve_error is None ⇒ path resolved
    lifecycle = header.get(_LIFECYCLE_FIELD, LIFECYCLE_LIVE)
    if lifecycle != LIFECYCLE_LIVE:
        return _error(
            'not_amendable',
            f'inbox message {name} is {lifecycle}; only a live message is amendable',
            slug=args.slug,
            message_name=name,
        )
    new_revision = int(header.get(_REVISION_FIELD, '0')) + 1
    header[_REVISION_FIELD] = str(new_revision)
    header[_AMENDED_FIELD] = now_utc_iso()
    atomic_write_file(path, _render_envelope(header, body or ''))
    return {
        'status': 'success',
        'operation': 'inbox-amend',
        'slug': args.slug,
        'store': ORCHESTRATOR_STORE,
        'message': name,
        'revision': new_revision,
        'amended': header[_AMENDED_FIELD],
        'created': header.get('created', ''),
    }


def cmd_inbox_supersede(args: Any) -> dict[str, Any]:
    """Retire a filed message in favour of a named successor, tombstone-style.

    Mirrors the ``manage-lessons`` supersede model: the retired message stays on
    disk and keeps validating, but flips to ``lifecycle=superseded`` and records
    a ``superseded_by`` pointer, so it stops presenting as live in ``inbox list``
    while staying resolvable through ``inbox validate``. Unlike the lessons
    surface it does NOT rewrite the body into a redirect stub — the inbox is
    append-only for content, so the original body is preserved byte-for-byte and
    the supersession is recorded purely in the envelope, which IS the resolvable
    tombstone.

    Refuses an unsafe slug (``invalid_slug``), a path-shaped ``--message`` or
    ``--by`` (``invalid_message_name`` / ``invalid_successor_name``), a message
    superseding itself (``self_supersede``), an absent epic (``epic_not_found``),
    a target present at neither path or not live (``file_not_found`` /
    ``not_live``), an already-invalid target (the validator's own code), a
    stream-end marker (``not_supersedable`` — a terminal control marker cannot be
    retired by a successor), and a successor present at neither path
    (``successor_not_found``).
    """
    invalid = _validate_identifier(args.slug)
    if invalid:
        return _error('invalid_slug', invalid, slug=args.slug)
    name = args.message
    if not _is_bare_filename(name):
        return _error(
            'invalid_message_name',
            f'--message must be a bare filename inside inbox/, got: {name}',
            slug=args.slug,
        )
    successor = args.by
    if not _is_bare_filename(successor):
        return _error(
            'invalid_successor_name',
            f'--by must be a bare filename inside inbox/, got: {successor}',
            slug=args.slug,
            message_name=name,
        )
    if successor == name:
        return _error(
            'self_supersede',
            'a message cannot supersede itself',
            slug=args.slug,
            message_name=name,
        )
    path, header, body, resolve_error = _resolve_live_message(args.slug, name)
    if resolve_error is not None:
        return _error(
            resolve_error['error'],
            resolve_error['message'],
            slug=args.slug,
            message_name=name,
        )
    assert path is not None  # resolve_error is None ⇒ path resolved
    # A stream-end marker is a terminal control record, not a payload message to
    # retire: flipping it to ``superseded`` would drop the sender from
    # ``closed_senders`` and silently re-open the stream. Refuse it. An
    # already-superseded message may be re-superseded (the pointer is updated).
    if header.get(_LIFECYCLE_FIELD, LIFECYCLE_LIVE) == LIFECYCLE_STREAM_END:
        return _error(
            'not_supersedable',
            f'inbox message {name} is a stream-end marker; a terminal control '
            'marker cannot be superseded',
            slug=args.slug,
            message_name=name,
        )
    root = _mutate_epic_root(args.slug)
    _succ_path, succ_location = resolve_message_path(root / INBOX_SUBDIR, successor)
    if succ_location == 'missing':
        return _error(
            'successor_not_found',
            f'successor {successor!r} is present at neither inbox/ nor inbox/archive/',
            slug=args.slug,
            message_name=name,
            successor=successor,
        )
    header[_LIFECYCLE_FIELD] = LIFECYCLE_SUPERSEDED
    header[_SUPERSEDED_BY_FIELD] = successor
    atomic_write_file(path, _render_envelope(header, body or ''))
    return {
        'status': 'success',
        'operation': 'inbox-supersede',
        'slug': args.slug,
        'store': ORCHESTRATOR_STORE,
        'message': name,
        'lifecycle': LIFECYCLE_SUPERSEDED,
        'superseded_by': successor,
    }


def cmd_inbox_close_stream(args: Any) -> dict[str, Any]:
    """File a terminal marker declaring the sender's stream ended.

    The stream-termination half of the vocabulary: a sender marks its stream
    ended by filing one ``lifecycle=stream-end`` marker, allocated like any other
    message (so its sequence number is claimed and never re-opened). The marker
    is a fully-valid message — it carries the ``finding`` kind and a body (the
    ``--reason`` note, or a default sentence) — so no message-class branch is
    needed anywhere; the terminal signal rides ``lifecycle`` alone.

    The drain reads the closure from ``inbox list``'s ``closed_senders``. That is
    one of THREE zeros, not one of two: ``live_count: 0`` with the sender present
    in ``closed_senders`` and ``invalid_count: 0`` is a *finished* stream;
    ``live_count: 0`` with an empty ``closed_senders`` and ``invalid_count: 0`` is
    an *empty* queue that may yet receive more; and ``live_count: 0`` with
    ``invalid_count > 0`` is *blocked* — nothing drainable, but messages the drain
    refuses to consume. See ``standards/inbox-envelope.md`` § Drain semantics.

    **Idempotent.** Closing a stream that is already closed returns SUCCESS
    naming the existing marker, with ``already_closed: true``, and allocates
    nothing — the caller asked for a state that already holds. A first close
    reports ``already_closed: false``. Allocating a second marker instead would
    be a second declaration of one fact, and it would be effectively invisible:
    ``inbox list``'s ``closed_senders`` is a SET, so the duplicate dedups away
    and shows up only as an unexplained extra row in ``count``.

    Refuses an unsafe slug (``invalid_slug``), an unsafe sender id
    (``invalid_sender_id``), an out-of-enum sender type (``invalid_sender_type``),
    and an unscaffolded epic (``epic_not_found``).
    """
    invalid = _validate_identifier(args.slug)
    if invalid:
        return _error('invalid_slug', invalid, slug=args.slug)
    invalid = _validate_identifier(args.sender_id)
    if invalid:
        return _error('invalid_sender_id', invalid, slug=args.slug)
    if args.sender_type not in SENDER_TYPES:
        return _error(
            'invalid_sender_type',
            f'--sender-type must be one of {sorted(SENDER_TYPES)}, got: {args.sender_type}',
            slug=args.slug,
        )
    root = get_store_dir(ORCHESTRATOR_STORE, args.slug)
    if not root.is_dir():
        return _error(
            'epic_not_found',
            f'epic {args.slug!r} has no tree at {root}; run scaffold first',
            slug=args.slug,
        )
    inbox_dir = root / INBOX_SUBDIR
    # Idempotence, not refusal: closing an already-closed stream asks for a state
    # that already holds, so the call SUCCEEDS and names the existing marker
    # rather than allocating a second one. A second marker would be a second
    # declaration of the same fact, invisible in ``inbox list``'s
    # ``closed_senders`` (a set, so the duplicate dedups away) and visible only as
    # an unexplained extra message in ``count``.
    existing = find_stream_end_marker(inbox_dir, args.slug, args.sender_id)
    if existing is not None:
        return {
            'status': 'success',
            'operation': 'inbox-close-stream',
            'slug': args.slug,
            'store': ORCHESTRATOR_STORE,
            'sender_type': args.sender_type,
            'sender_id': args.sender_id,
            'lifecycle': LIFECYCLE_STREAM_END,
            'already_closed': True,
            'message': existing,
            'path': str(inbox_dir / existing),
        }
    reason = (getattr(args, 'reason', None) or '').strip() or STREAM_END_DEFAULT_NOTE
    text = compose_envelope(
        args.sender_type,
        args.sender_id,
        args.slug,
        STREAM_END_KIND,
        reason,
        lifecycle=LIFECYCLE_STREAM_END,
    )
    message_path = allocate_message_path(inbox_dir, args.sender_id, text)
    return {
        'status': 'success',
        'operation': 'inbox-close-stream',
        'slug': args.slug,
        'store': ORCHESTRATOR_STORE,
        'sender_type': args.sender_type,
        'sender_id': args.sender_id,
        'lifecycle': LIFECYCLE_STREAM_END,
        'already_closed': False,
        'message': message_path.name,
        'path': str(message_path),
    }


def cmd_inbox_migrate_archive(args: Any) -> dict[str, Any]:
    """Fold a flat ``inbox/archive/`` into per-sender subdirectories.

    The one-shot migration that folds every message-shaped file sitting directly
    under ``archive/`` into ``archive/{sender}/``. It reports the count moved PER
    SENDER, because a silent relocation is indistinguishable from a lossy one —
    the operator can reconcile the reported per-sender tallies against the
    archive they expected. Idempotent: a message already foldered contributes
    nothing, and a re-run over an already-migrated archive moves zero.

    Each file's sender segment is re-validated as a DIRECTORY component before
    the move (:func:`_foldered_archive_dir`); an unsafe or off-shape name is left
    in place and reported under ``skipped[]`` rather than folded into a
    traversing path. A destination that already exists (a foldered twin) is also
    skipped rather than clobbered, preserving the audit record.

    Because this verb MUTATES, it resolves the epic root strictly and refuses an
    archived-only epic (``epic_not_found``).
    """
    invalid = _validate_identifier(args.slug)
    if invalid:
        return _error('invalid_slug', invalid, slug=args.slug)
    root = _mutate_epic_root(args.slug)
    if not root.is_dir():
        return _error(
            'epic_not_found',
            f'epic {args.slug!r} has no active tree at {root}',
            slug=args.slug,
        )
    archive_dir = root / INBOX_SUBDIR / INBOX_ARCHIVE_SUBDIR
    moved_by_sender: dict[str, int] = {}
    skipped: list[dict[str, str]] = []
    if archive_dir.is_dir():
        for entry in sorted(archive_dir.iterdir()):
            if not entry.is_file():
                continue
            match = _MESSAGE_NAME_RE.match(entry.name)
            if match is None:
                skipped.append({'name': entry.name, 'reason': 'off_shape'})
                continue
            sender = match.group('sender')
            sender_dir = _foldered_archive_dir(archive_dir, sender)
            if sender_dir is None:
                skipped.append({'name': entry.name, 'reason': 'unsafe_sender'})
                continue
            dest = sender_dir / entry.name
            if dest.exists():
                skipped.append({'name': entry.name, 'reason': 'foldered_twin_exists'})
                continue
            sender_dir.mkdir(parents=True, exist_ok=True)
            os.rename(entry, dest)
            moved_by_sender[sender] = moved_by_sender.get(sender, 0) + 1
    return {
        'status': 'success',
        'operation': 'inbox-migrate-archive',
        'slug': args.slug,
        'store': ORCHESTRATOR_STORE,
        'moved_total': sum(moved_by_sender.values()),
        'senders': sorted(moved_by_sender),
        'moved_by_sender': dict(sorted(moved_by_sender.items())),
        'skipped': skipped,
    }


def cmd_inbox_detect(args: Any) -> dict[str, Any]:
    """Classify a ``source_id`` string as an orchestrated plan pointer.

    The single detection seam every consumer calls; it re-uses the pointer
    ``phase-1-init`` already persisted rather than introducing a parallel
    detector or a new persisted metadata field. ``detection`` reports which of
    :data:`DETECTION_TOKENS` the verdict is, so an orchestrator-shaped pointer
    with an unrecognised id segment is distinguishable from a plain negative.
    """
    verdict = classify_source_id(args.source_id)
    return {
        'status': 'success',
        'operation': 'inbox-detect',
        'store': ORCHESTRATOR_STORE,
        'orchestrated': verdict.orchestrated,
        'epic': verdict.epic or '',
        'plan_spec': verdict.plan_spec or '',
        'detection': verdict.detection,
    }


def cmd_inbox_landing_check(args: Any) -> dict[str, Any]:
    """Validate a landing message's payload completeness against the required facts.

    Resolves ``--message`` inside the epic's ``inbox/`` (queued or archived, via
    :func:`resolve_message_path`), splits the envelope, and runs
    :func:`check_landing_completeness` over the payload body. The drain
    (``analyze.md`` Step 4) runs this as it reconciles a ``landing`` message, so a
    landing that carried only narrative — transmitting none of the mechanisable
    report<->inbox delta — is recorded as an incompleteness rather than reconciled
    as if the inbox had drained everything material. That is what lets the
    orchestrator establish, after a drain reports zero, that every REQUIRED fact
    drained — which is narrower than "nothing is outstanding". Several
    mechanisable facts ride OPTIONAL keys this check does not require (the
    per-step typed facts, the wall-clock, the repository end-state), so a
    ``complete: true`` landing may carry none of them.

    **A degraded value is judged by which of TWO classes it belongs to**, so
    ``missing_keys`` can name a key the producer did write. An ANSWERED sentinel
    (``n/a``, :data:`LANDING_ANSWERED_SENTINELS`) asserts a real end state and is
    reported missing only at :data:`LANDING_SENTINEL_REJECTING_KEYS`; a
    COULD-NOT-READ sentinel (``unknown``,
    :data:`LANDING_COULD_NOT_READ_SENTINELS`) asserts only that nothing was
    observed and is reported missing at EVERY key, ``pr`` and ``merge_state``
    included. So ``merge_state=n/a`` leaves a landing complete while
    ``merge_state=unknown`` does not — the drain records the failed read as a gap
    instead of reconciling against it as a settled merge fact.

    ``complete: false`` is a VERDICT, not a fault: the verb stays ``status:
    success`` and rides the completeness on the payload, so a drain is never
    aborted by an incomplete landing — it is recorded and surfaced.
    """
    invalid = _validate_identifier(args.slug)
    if invalid:
        return _error('invalid_slug', invalid, slug=args.slug)
    name = args.message
    if not _is_bare_filename(name):
        return _error(
            'invalid_message_name',
            f'--message must be a bare filename inside inbox/, got: {name}',
            slug=args.slug,
        )
    path, location = resolve_message_path(_inbox_dir(args.slug), name)
    if location == 'missing':
        return _error(
            'file_not_found', f'inbox message not found: {path}', slug=args.slug
        )
    try:
        text = path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError) as exc:
        return _error(
            'unreadable',
            f'inbox message {name} could not be read: {exc}',
            slug=args.slug,
            message_name=name,
        )
    _, body = _split_message(text)
    complete, missing = check_landing_completeness(body)
    return {
        'status': 'success',
        'operation': 'inbox-landing-check',
        'slug': args.slug,
        'store': ORCHESTRATOR_STORE,
        'message': name,
        'location': location,
        'complete': complete,
        'missing_keys': missing,
    }
