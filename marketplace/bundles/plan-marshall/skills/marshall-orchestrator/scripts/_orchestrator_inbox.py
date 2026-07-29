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
path they ever write is ``inbox/archive/`` joined with either the source
message's own bare filename or the bare, sender-constrained ``--as-name``
override — never a caller-supplied path.

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
from typing import Any, NamedTuple

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
#: ``request.md``'s ``source_id`` for an orchestrated plan. The id segment is an
#: explicit three-way alternation over the settled forms — ``PLAN-{DIGITS}``,
#: ``PLAN-{SLUG}-{DIGITS}``, and ``{SLUG}-{DIGITS}``. Writing it as an
#: alternation rather than as one pattern with an OPTIONAL slug group is
#: load-bearing: an optional group would also accept a bare ``01-foo.md`` that
#: is neither ``PLAN-``-prefixed nor slug-prefixed. ``{SLUG}`` is a bounded
#: uppercase-alphanumeric token and its trailing digits are mandatory, so the
#: grammar is widened without drifting toward an always-matching pattern.
_SOURCE_ID_RE = re.compile(
    r'^\.plan/local/orchestrator/(?P<slug>[^/]+)/plans/'
    r'(?:PLAN-(?:[A-Z0-9]{2,8}-)?\d+|[A-Z0-9]{2,8}-\d+)[^/]*\.md$'
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

    The scan spans BOTH the live queue (``inbox_dir``) and the archive
    (``inbox_dir / archive``), taking the highest ``{sender_id}-{NNN}.md``
    sequence across the two. Consulting the archive is load-bearing: a drain
    retires a sender's messages out of the live queue, so a live-only scan
    would reset the proposal to ``001`` and hand the sender a number whose
    archived twin already exists. Each directory is scanned only when it
    exists, so an absent ``inbox/`` or a not-yet-created ``archive/``
    contributes nothing rather than raising.

    Only the PROPOSAL widens. On its own this is still a check-then-act read —
    :func:`allocate_message_path` turns it into a safe claim by making the
    ``O_EXCL`` create the atomic step and retrying the next free sequence on
    collision, and that claim stays scoped to ``inbox/`` alone: no archived
    path is ever a claim target.
    """
    highest = 0
    for directory in (inbox_dir, inbox_dir / INBOX_ARCHIVE_SUBDIR):
        if not directory.is_dir():
            continue
        for entry in directory.iterdir():
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
    dest = inbox_dir / INBOX_ARCHIVE_SUBDIR / dest_name
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
