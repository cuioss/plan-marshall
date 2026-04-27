#!/usr/bin/env python3
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

from pathlib import Path

from file_ops import atomic_write_file  # type: ignore[import-not-found]


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
                'message': (
                    f'Body source path does not exist or is not a regular file: {file_path}'
                ),
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
                f'Lesson {lesson_id} is missing a frontmatter header or H1 title; '
                'cannot safely overwrite body'
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
