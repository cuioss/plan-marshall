#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Shared preamble for the ``lessons crud`` test modules.

Holds the module-level loads, constants and helpers those modules
share. The contract they pin, in full:

Tests for the trivial getter/setter CRUD subcommands of manage-lessons.py.

This module absorbs the four single-verb suites whose bodies were each small
enough that a dedicated file cost more navigation than it bought:

* ``get`` — ``cmd_get`` direct invocation (metadata retrieval, not-found) plus
  the Tier 3 subprocess check pinning ``read`` as an alias for ``get``
  (TestCmdGet, TestCliReadAlias).
* ``list`` — core ``cmd_list`` behaviour (empty dir, basic listing,
  component/category filters, ``--full`` body inclusion, default no-body
  exclusion), the ``--status`` filter matrix, and legacy ``YYYY-MM-DD-NNN``
  filename compatibility across both the list and get read paths
  (TestCmdList, TestLegacyFormatCompatibility, TestCmdListStatusFilter).
* ``set-title`` — ``cmd_set_title`` H1 rewriting: active and superseded
  lessons, the not-found and malformed-lesson error paths, idempotency,
  frontmatter preservation, and first-outside-fence-H1 selection
  (TestCmdSetTitle*).
* ``set-body`` — ``cmd_set_body`` body overwrite via the canonical ``--file``
  form and the secondary ``--content`` form, the mutual-exclusion guard, the
  file-not-found / file-read-error guards, and frontmatter preservation
  (TestCmdSetBody).

The complex-verb suites (``supersede``, ``convert_to_plan``,
``restore_from_plan``, ``from_error``, ``add``, ``remove``, ``update``) keep
their own files — only the trivial getter/setter verbs are co-located here.

All four absorbed suites now share ONE module-load path: ``_lessons_helpers``
loads ``manage-lessons.py`` exactly once and re-exports the ``cmd_*``
callables. ``cmd_set_title`` is not among the helper's re-exports, so it is
resolved off the shared ``_mod`` handle rather than by re-loading the script —
the previous ``test_set_title.py`` paid a second ``spec_from_file_location``
load of the same production module under a separate name.
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
