#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""
CRUD command handlers for manage-lessons.py.

Currently contains: ``set_body`` (path-allocate body-write flow).

Path-allocate flow (canonical):
    1. ``manage-lessons add ...`` → script returns the absolute path of a fresh
       lesson stub (metadata header + H1 title, empty body).
    2. Caller writes the body to ``{plan_dir}/work/lesson-body-{id}.md`` via the
       Write tool — multi-line markdown, code fences, and shell-unsafe content
       all pass through cleanly because the body never crosses a shell boundary.
    3. ``manage-lessons set-body --lesson-id {id} --file {path}`` → this module
       reads the body file and overwrites the body section of the lesson while
       preserving the ``key=value`` frontmatter and H1 title verbatim.

The secondary ``--content STRING`` form is intended for tiny payloads only; the
primary form is ``--file PATH`` against a path the caller has already written.
"""

from collections.abc import Callable
from datetime import date, datetime
from pathlib import Path

from file_ops import atomic_write_file, parse_markdown_metadata  # type: ignore[import-not-found]

# Body H2 marker appended on each arch-constraint recurrence. The format matches
# the existing ``RECURRENCE_H2_REGEX`` (``^## Recurrence —``) the aggregate verb
# already counts, so a reinforced arch-constraint lesson's recurrence sections
# are recognised by the same scanner.
RECURRENCE_SECTION_MARKER = '## Recurrence —'

# Hard fallback for the retire-on-quiet window (days) when neither the CLI flag
# nor ``system.retention.arch_constraint_quiet_days`` in marshal.json yields an
# integer. 90 days mirrors a "one quarter quiet ⇒ retire" default.
DEFAULT_ARCH_CONSTRAINT_QUIET_DAYS = 90


def _split_lesson(content: str) -> tuple[str, str, str]:
    """Split a lesson file's content into (frontmatter_block, h1_line, _body).

    The frontmatter block is the literal text from the start of the file up to
    and including the blank line that terminates the ``key=value`` header. The
    ``h1_line`` is the first ``# `` line found after that. The body (third
    element) is everything after the H1; it is returned for completeness but
    callers replacing the body should ignore it.

    Returns empty strings for any segment that cannot be located so callers can
    treat malformed lessons uniformly.
    """
    lines = content.split('\n')

    # Locate the blank line that ends the metadata header.
    header_end = -1
    for i, line in enumerate(lines):
        if line == '':
            header_end = i
            break

    if header_end == -1:
        return '', '', ''

    # Locate the H1 title after the blank line.
    h1_index = -1
    for i in range(header_end + 1, len(lines)):
        if lines[i].startswith('# '):
            h1_index = i
            break

    if h1_index == -1:
        return '', '', ''

    frontmatter_block = '\n'.join(lines[: header_end + 1])
    h1_line = lines[h1_index]
    body = '\n'.join(lines[h1_index + 1 :])

    return frontmatter_block, h1_line, body


def set_body(
    lessons_dir: Path,
    lesson_id: str,
    file_path: str | None = None,
    content: str | None = None,
) -> dict:
    """Overwrite the body of an existing lesson stub.

    Validates that exactly one of ``file_path`` / ``content`` is supplied
    (the CLI layer enforces mutual exclusion via argparse, but this guard
    keeps the function safe under direct programmatic use), confirms the
    lesson stub exists, and rewrites the file with the original frontmatter
    block and H1 title preserved verbatim, replacing everything after the H1
    with the supplied body.

    Args:
        lessons_dir: Directory containing lesson files (typically the result
            of ``get_lessons_dir()`` in the caller).
        lesson_id: Identifier of the lesson stub to update (no ``.md`` suffix).
        file_path: Path to a file whose contents become the new body. Mutually
            exclusive with ``content``.
        content: Inline body content. Mutually exclusive with ``file_path``.

    Returns:
        TOON-shaped dict ``{status, id, path, body_bytes_written}`` on
        success; ``{status: error, error, message, ...}`` otherwise.
    """
    if (file_path is None) == (content is None):
        return {
            'status': 'error',
            'error': 'invalid_input',
            'message': 'Exactly one of --file or --content must be supplied',
        }

    target = lessons_dir / f'{lesson_id}.md'
    if not target.exists():
        return {
            'status': 'error',
            'id': lesson_id,
            'error': 'not_found',
            'message': f'Lesson {lesson_id} not found',
        }

    if file_path is not None:
        source = Path(file_path)
        if not source.is_file():
            return {
                'status': 'error',
                'id': lesson_id,
                'error': 'file_not_found',
                'message': (f'Body source path does not exist or is not a regular file: {file_path}'),
            }
        try:
            body = source.read_text(encoding='utf-8')
        except OSError as e:
            return {
                'status': 'error',
                'id': lesson_id,
                'error': 'file_read_error',
                'message': f'Cannot read body source file {file_path}: {e}',
            }
    else:
        body = content or ''

    original = target.read_text(encoding='utf-8')
    frontmatter_block, h1_line, _ = _split_lesson(original)

    if not frontmatter_block or not h1_line:
        return {
            'status': 'error',
            'id': lesson_id,
            'error': 'malformed_lesson',
            'message': (
                f'Lesson {lesson_id} is missing a frontmatter header or H1 title; cannot safely overwrite body'
            ),
        }

    # Reassemble: frontmatter block (already ends with the blank line),
    # H1 line, blank line, body. Ensure trailing newline for POSIX-friendly
    # files and to match the shape produced by the ``add`` flow.
    rebuilt = f'{frontmatter_block}\n{h1_line}\n\n{body}'
    if not rebuilt.endswith('\n'):
        rebuilt += '\n'

    atomic_write_file(target, rebuilt)

    body_bytes = body.encode('utf-8')

    return {
        'status': 'success',
        'id': lesson_id,
        'path': str(target.resolve()),
        'body_bytes_written': len(body_bytes),
    }


# =============================================================================
# arch-constraint lifecycle — rule-identity dedup + reinforce/retire routines
# =============================================================================
#
# An arch-constraint lesson carries a ``rule=`` metadata header (the rule
# identity emitted by the arch-gate producer). Recurrence of the same rule
# REINFORCES the one lesson (recurrence_count bump + a ``## Recurrence —`` body
# section) rather than allocating a new lesson; a rule that stays quiet past a
# configurable window RETIRES the lesson. This is a parallel age/quiet-based
# lifecycle alongside ``cleanup-superseded`` — deliberately NOT promote-to-skill.


def find_active_arch_constraint_by_rule(lessons_dir: Path, rule: str) -> str | None:
    """Return the id of the active arch-constraint lesson for ``rule``, or None.

    The rule-identity dedup key: scans the corpus for an ``active`` lesson whose
    ``category`` is ``arch-constraint`` and whose ``rule`` header equals ``rule``.
    Returns the first match's id (corpus ids are unique per rule by construction —
    a second observation reinforces rather than allocates). Returns None when no
    such lesson exists (the allocate-new path).
    """
    if not rule or not lessons_dir.exists():
        return None
    for path in sorted(lessons_dir.glob('*.md')):
        try:
            metadata = parse_markdown_metadata(path.read_text(encoding='utf-8'))
        except OSError:
            continue
        if (
            metadata.get('category') == 'arch-constraint'
            and metadata.get('status', 'active') == 'active'
            and metadata.get('rule') == rule
        ):
            return metadata.get('id', path.stem)
    return None


def reinforce_arch_constraint(
    lessons_dir: Path,
    lesson_id: str,
    observed_date: str,
    detail: str = '',
) -> dict:
    """Reinforce an existing arch-constraint lesson on a recurring violation.

    Bumps the ``recurrence_count`` metadata, refreshes ``last_seen`` to
    ``observed_date`` (resetting the retire-on-quiet clock), and appends a
    ``## Recurrence — {observed_date}`` body section (optionally carrying
    ``detail``). The append format matches the ``RECURRENCE_H2_REGEX`` the
    aggregate verb already counts.

    Returns TOON ``{status, id, action: 'reinforced', recurrence_count,
    last_seen}`` on success, or an error dict when the lesson is absent.
    """
    target = lessons_dir / f'{lesson_id}.md'
    if not target.exists():
        return {
            'status': 'error',
            'id': lesson_id,
            'error': 'not_found',
            'message': f'Lesson {lesson_id} not found',
        }

    content = target.read_text(encoding='utf-8')
    metadata = parse_markdown_metadata(content)
    raw_lines = content.split('\n')
    title = ''
    body_start = 0
    for i, line in enumerate(raw_lines):
        if line.startswith('# '):
            title = line[2:].strip()
            body_start = i + 1
            break
    if not title:
        return {
            'status': 'error',
            'id': lesson_id,
            'error': 'malformed_lesson',
            'message': f'Lesson {lesson_id} is missing its H1 title; cannot safely reinforce',
        }
    body = '\n'.join(raw_lines[body_start:]).strip()

    try:
        count = int(metadata.get('recurrence_count', '1')) + 1
    except (TypeError, ValueError):
        count = 2
    metadata['recurrence_count'] = str(count)
    metadata['last_seen'] = observed_date

    section = f'{RECURRENCE_SECTION_MARKER} {observed_date}'
    if detail:
        section += f'\n\n{detail.rstrip()}'
    new_body = f'{body.rstrip()}\n\n{section}' if body.strip() else section

    out_lines = [f'{key}={value}' for key, value in metadata.items()]
    out_lines.append('')
    out_lines.append(f'# {title}')
    out_lines.append('')
    out_lines.append(new_body)
    rendered = '\n'.join(out_lines)
    if not rendered.endswith('\n'):
        rendered += '\n'
    atomic_write_file(target, rendered)

    return {
        'status': 'success',
        'id': lesson_id,
        'action': 'reinforced',
        'recurrence_count': count,
        'last_seen': observed_date,
    }


def _parse_iso_date(value: str) -> date | None:
    """Parse a ``YYYY-MM-DD`` string into a date, or None when unparseable."""
    if not value:
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except (TypeError, ValueError):
        return None


def retire_quiet_arch_constraints(
    lessons_dir: Path,
    quiet_days: int,
    today: date,
    write_tombstone: Callable[[str, str, str], object],
    dry_run: bool = False,
) -> dict:
    """Retire active arch-constraint lessons whose rule has been quiet too long.

    A lesson is QUIET when ``today - last_seen >= quiet_days`` (``last_seen``
    falls back to ``created`` when absent). Quiet lessons are retired: a tombstone
    is written via the injected ``write_tombstone`` callable (signature
    ``(lesson_id, reason, status)`` — same as manage-lessons ``_write_tombstone``)
    and the ``.md`` is unlinked, mirroring ``cleanup-superseded``'s
    tombstone-preserving prune. A lesson whose ``last_seen`` is unparseable is
    left untouched (reported under ``skipped_unparseable_date``) — fail-safe, never
    destroying a record on a bad date.

    On ``dry_run`` nothing is unlinked and no tombstone is written; the would-be
    retirements are still reported.

    Returns TOON ``{status, dry_run, quiet_days, retired[], retained[],
    skipped_unparseable_date[]}``.
    """
    retired: list[dict] = []
    retained: list[dict] = []
    skipped_unparseable_date: list[dict] = []

    if not lessons_dir.exists():
        return {
            'status': 'success',
            'dry_run': bool(dry_run),
            'quiet_days': quiet_days,
            'retired': retired,
            'retained': retained,
            'skipped_unparseable_date': skipped_unparseable_date,
        }

    for path in sorted(lessons_dir.glob('*.md')):
        try:
            metadata = parse_markdown_metadata(path.read_text(encoding='utf-8'))
        except OSError:
            continue
        if metadata.get('category') != 'arch-constraint':
            continue
        if metadata.get('status', 'active') != 'active':
            continue

        lesson_id = metadata.get('id', path.stem)
        rule = metadata.get('rule', '')
        last_seen_raw = metadata.get('last_seen') or metadata.get('created', '')
        last_seen = _parse_iso_date(last_seen_raw)
        if last_seen is None:
            skipped_unparseable_date.append({'lesson_id': lesson_id, 'last_seen': last_seen_raw})
            continue

        quiet_for = (today - last_seen).days
        if quiet_for >= quiet_days:
            if not dry_run:
                write_tombstone(
                    lesson_id,
                    f'arch-constraint retired: rule {rule!r} quiet {quiet_for}d >= {quiet_days}d',
                    'removed',
                )
                path.unlink()
            retired.append({'lesson_id': lesson_id, 'rule': rule, 'quiet_days_elapsed': quiet_for})
        else:
            retained.append({'lesson_id': lesson_id, 'rule': rule, 'quiet_days_elapsed': quiet_for})

    return {
        'status': 'success',
        'dry_run': bool(dry_run),
        'quiet_days': quiet_days,
        'retired': retired,
        'retained': retained,
        'skipped_unparseable_date': skipped_unparseable_date,
    }
