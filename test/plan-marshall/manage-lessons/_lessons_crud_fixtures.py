#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Shared preamble for the ``lessons crud`` test modules.

Holds the module-level loads, constants and helpers those modules
share, so each of them carries the import and not the preamble.
"""


from pathlib import Path
from _lessons_helpers import _mod


# ``cmd_set_title`` is not re-exported by ``_lessons_helpers`` (that module is
# owned elsewhere and is not modified by this suite), so it is bound off the
# shared module handle. This keeps the single-load contract intact.
cmd_set_title = _mod.cmd_set_title


def _seed_cli_lesson(tmp_path: Path, lesson_id: str, title: str) -> None:
    """Seed a minimal lesson file under ``{tmp_path}/lessons-learned``."""
    lessons_dir = tmp_path / 'lessons-learned'
    lessons_dir.mkdir(parents=True, exist_ok=True)
    (lessons_dir / f'{lesson_id}.md').write_text(
        f'id={lesson_id}\ncomponent=test-component\ncategory=bug\n'
        f'created=2025-01-01\n\n# {title}\n\nThis is the lesson body.\n',
        encoding='utf-8',
    )


# =============================================================================
# Tier 2: cmd_list --status filter
# =============================================================================


def _seed_lesson_with_status(lessons_dir: Path, lesson_id: str, status: str | None, title: str) -> Path:
    """Write a minimal lesson file with optional ``status`` frontmatter."""
    metadata_lines = [
        f'id={lesson_id}',
        'component=test',
        'category=bug',
        'created=2025-01-01',
    ]
    if status is not None:
        metadata_lines.insert(3, f'status={status}')
    content = '\n'.join(metadata_lines) + f'\n\n# {title}\n\nBody.\n'
    path = lessons_dir / f'{lesson_id}.md'
    path.write_text(content, encoding='utf-8')
    return path


# =============================================================================
# cmd_set_title fixture helpers
# =============================================================================


def _seed_active_lesson(
    lessons_dir: Path,
    lesson_id: str = '2025-01-01-01-001',
    title: str = 'Original Title',
    body: str = '',
    extra_frontmatter: str = '',
) -> Path:
    """Create an active lesson markdown file with frontmatter, H1 title, and body.

    The shape mirrors what ``cmd_add`` produces: ``key=value`` lines, a blank
    line, the ``# {title}`` H1, then optional body content.
    """
    path = lessons_dir / f'{lesson_id}.md'
    frontmatter = (
        f'id={lesson_id}\n'
        'component=test-component\n'
        'category=bug\n'
        'created=2025-01-01\n'
        'status=active\n'
    )
    if extra_frontmatter:
        frontmatter += extra_frontmatter
    content = f'{frontmatter}\n# {title}\n'
    if body:
        content += f'\n{body}'
    path.write_text(content, encoding='utf-8')
    return path


def _seed_superseded_lesson(
    lessons_dir: Path,
    lesson_id: str = '2025-01-01-01-002',
    title: str = 'Superseded Title',
    superseded_by: str = '2025-01-01-01-099',
) -> Path:
    """Create a superseded lesson stub. Superseded lessons remain on disk but
    have ``status=superseded`` and a ``superseded_by`` pointer in frontmatter.
    """
    path = lessons_dir / f'{lesson_id}.md'
    content = (
        f'id={lesson_id}\n'
        'component=test-component\n'
        'category=bug\n'
        'created=2025-01-01\n'
        'status=superseded\n'
        f'superseded_by={superseded_by}\n'
        '\n'
        f'# {title}\n'
    )
    path.write_text(content, encoding='utf-8')
    return path
