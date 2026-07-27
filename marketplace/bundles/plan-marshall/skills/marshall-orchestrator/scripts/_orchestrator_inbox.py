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

The orchestrator-side drain surface (:func:`cmd_inbox_list`,
:func:`cmd_inbox_archive`) is bounded by the same construction: both derive
their target from the validated slug plus a bare message filename, and the only
path they ever write is ``inbox/archive/{name}``.

The message format is markdown with the repo's existing ``key=value`` metadata
header (``file_ops.parse_markdown_metadata`` /
``file_ops.generate_markdown_metadata``): typed scalars ride the header, free
prose is the body, and the two are separated by exactly one blank line. The
schema itself is documented in
``marshall-orchestrator/standards/inbox-envelope.md``.
"""

import os
import re
from pathlib import Path
from typing import Any

from file_ops import (
    generate_markdown_metadata,
    get_store_dir,
    now_utc_iso,
    parse_markdown_metadata,
)
from input_validation import validate_plan_id

ORCHESTRATOR_STORE = 'orchestrator'

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

#: Header fields, in the fixed order :func:`compose_envelope` emits them.
#: Every field is required; a message missing any one is ``missing_header_field``.
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

#: ``{sender_id}-{NNN}.md`` — the one message-file shape the channel allocates.
#: The sender group is non-greedy so the LAST dash-separated all-digit run is
#: the sequence: a four-digit sequence, or a sender id that itself ends in
#: digits, still splits at the right dash.
_MESSAGE_NAME_RE = re.compile(r'^(?P<sender>.+?)-(?P<seq>\d{3,})\.md$')

#: The orchestrator plan-spec pointer ``phase-1-init`` records as
#: ``request.md``'s ``source_id`` for an orchestrated plan.
_SOURCE_ID_RE = re.compile(
    r'^\.plan/local/orchestrator/(?P<slug>[^/]+)/plans/PLAN-\d+[^/]*\.md$'
)


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


def compose_envelope(
    sender_type: str, sender_id: str, epic: str, kind: str, payload_body: str
) -> str:
    """Render a complete inbox message.

    The ``key=value`` header carries :data:`HEADER_FIELDS` in order, one blank
    line separates it from the markdown payload body, and ``created`` is
    stamped at compose time.

    Args:
        sender_type: One of :data:`SENDER_TYPES`.
        sender_id: The sender's identifier (a plan id, or an epic slug for an
            ``orchestrator`` sender).
        epic: Epic slug the message is addressed to.
        kind: One of :data:`KINDS`.
        payload_body: The markdown payload; surrounding whitespace is trimmed.

    Returns:
        The full message text.
    """
    header = generate_markdown_metadata(
        {
            'envelope_version': str(ENVELOPE_VERSION),
            'sender_type': sender_type,
            'sender_id': sender_id,
            'epic': epic,
            'kind': kind,
            'created': now_utc_iso(),
        }
    )
    return f'{header}\n\n{payload_body.strip()}\n'


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
    payload presence, epic agreement, filename agreement. The last two are
    checked only when the corresponding context argument is supplied.

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
    return True, None, header


def next_sequence(inbox_dir: Path, sender_id: str) -> int:
    """Return the next unused sequence number for ``sender_id`` in ``inbox_dir``.

    A pure scan of the existing ``{sender_id}-{NNN}.md`` files. On its own this
    is a check-then-act read — :func:`allocate_message_path` turns it into a
    safe claim by making the ``O_EXCL`` create the atomic step and retrying the
    next free sequence on collision.
    """
    if not inbox_dir.is_dir():
        return 1
    highest = 0
    for entry in inbox_dir.iterdir():
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
    off-shape name.

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


def classify_source_id(source_id: str) -> tuple[bool, str | None, str | None]:
    """Classify ``request.md``'s ``source_id`` as an orchestrated plan pointer.

    Pure classification of the string ``phase-1-init`` already persisted — no
    filesystem access and no second detector. A pointer of the shape
    ``.plan/local/orchestrator/{slug}/plans/PLAN-NN-*.md`` whose ``{slug}`` is
    a safe identifier is orchestrated; every other string (a prose description,
    an unrelated path, a traversal attempt) is not.

    Returns:
        ``(orchestrated, epic, plan_spec)`` — ``(False, None, None)`` when the
        pointer does not identify an orchestrated plan.
    """
    match = _SOURCE_ID_RE.match(source_id.strip()) if source_id else None
    if match is None:
        return False, None, None
    slug = match.group('slug')
    if _validate_identifier(slug) is not None:
        return False, None, None
    return True, slug, source_id.strip()


def cmd_inbox_write(args: Any) -> dict[str, Any]:
    """Append one message to the epic's inbox.

    The write boundary is enforced by construction: the target resolves
    strictly to ``get_store_dir('orchestrator', slug) / 'inbox' /
    '{sender_id}-{NNN}.md'``, both components are validated identifiers, and no
    caller-supplied output path exists in the argument surface. The payload
    arrives via ``--payload-file`` (staged with the Write tool) so no message
    body ever passes through a shell argument.
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
    path = _inbox_dir(args.slug) / name
    if not path.is_file():
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
        'envelope_version': header['envelope_version'],
        'sender_type': header['sender_type'],
        'sender_id': header['sender_id'],
        'kind': header['kind'],
        'created': header['created'],
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
                'valid': ok,
                'error': '' if ok else (error_code or 'invalid_envelope'),
            }
        )
    return {
        'status': 'success',
        'operation': 'inbox-list',
        'slug': args.slug,
        'store': ORCHESTRATOR_STORE,
        'count': len(messages),
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
    """Retire one consumed message to ``inbox/archive/{name}``.

    Archival is the consume marker: the message leaves the enumeration
    :func:`cmd_inbox_list` returns while its audit record survives at the
    archived path, so the append-only invariant is unbroken — the file is
    relocated, never edited or deleted. Because this verb MUTATES, the epic
    root resolves strictly (:func:`_mutate_epic_root`): an epic whose active
    tree is gone is refused with ``epic_not_found`` rather than silently
    relocating a file inside its frozen archived record.

    The relocation itself is an ATOMIC claim rather than a check-then-move:
    :func:`os.link` creates ``inbox/archive/{name}`` without ever replacing an
    existing destination, and the source is unlinked only once that claim has
    succeeded. Every response is derived from the claim's own outcome, so two
    racing drains cannot both clear a presence check and have the loser fault
    on a source the winner already moved:

    - claim refused because the source is gone (``FileNotFoundError``) and the
      destination is present → idempotent success (``already_archived``), so a
      resumed, repeated, or race-losing drain is safe.
    - claim refused because the source is gone and the destination is absent
      → ``error: file_not_found``.
    - claim refused because the destination already exists
      (``FileExistsError``) while the source is still present →
      ``error: archive_conflict`` (never clobber the retired audit record).
    - claim succeeded → unlink the source and report the relocation.
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
    dest = inbox_dir / INBOX_ARCHIVE_SUBDIR / name
    # Created before the claim so a FileNotFoundError from os.link below can
    # only mean "the source is gone", never "the archive directory is missing".
    dest.parent.mkdir(parents=True, exist_ok=True)
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
        if source.is_file():
            return _error(
                'archive_conflict',
                f'inbox message {name} is already archived at {dest}; '
                'refusing to clobber the audit record',
                slug=args.slug,
                message_name=name,
                archived_to=str(dest),
            )
        return _archive_success(args.slug, name, dest, already_archived=True)
    source.unlink()
    return _archive_success(args.slug, name, dest, already_archived=False)


def cmd_inbox_detect(args: Any) -> dict[str, Any]:
    """Classify a ``source_id`` string as an orchestrated plan pointer.

    The single detection seam every consumer calls; it re-uses the pointer
    ``phase-1-init`` already persisted rather than introducing a parallel
    detector or a new persisted metadata field.
    """
    orchestrated, epic, plan_spec = classify_source_id(args.source_id)
    return {
        'status': 'success',
        'operation': 'inbox-detect',
        'store': ORCHESTRATOR_STORE,
        'orchestrated': orchestrated,
        'epic': epic or '',
        'plan_spec': plan_spec or '',
    }
