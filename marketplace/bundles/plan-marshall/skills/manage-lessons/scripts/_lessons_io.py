#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Read-core helpers for ``manage-lessons.py``.

Co-located helper module holding the directory resolvers and the read-side
lesson parsing that carry no wall-clock dependency and no test-patched
collaborators. The write path (``write_lesson`` / ``write_lesson_to``) stays in
the entry module because ``manage-lessons`` tests patch ``_mod.atomic_write_file``
to inject write failures, and that patch only reaches a writer whose
``atomic_write_file`` global lives in the entry module's namespace.

This module imports only shared script-shared modules and stdlib, so the entry
module can re-import these names without an import cycle.
"""

from pathlib import Path

from constants import DIR_LESSONS
from file_ops import parse_markdown_metadata
from marketplace_paths import (
    main_anchored_store_owns_bundle,
    resolve_main_anchored_path,
)


class WrongStoreError(Exception):
    """Raised when a lesson's component bundle is not owned by the resolved store repo.

    The manage-lessons entry module catches this and renders it as the standard
    ``status: error`` TOON (exit non-zero) rather than allocating a lesson into a
    store repo that does not own the component's bundle.
    """


def guard_component_store_match(component: str, allow_foreign: bool) -> None:
    """Refuse to file a lesson whose bundle is not owned by the resolved store repo.

    Parses the bundle (first ``:``-segment) from the ``bundle:skill[:script]``
    component notation and consults
    :func:`marketplace_paths.main_anchored_store_owns_bundle`. When the resolved
    main-anchored store repo does not own the bundle AND ``allow_foreign`` is
    ``False``, raises :class:`WrongStoreError`. When ``allow_foreign`` is ``True``
    or ownership holds (including under a test override, where the ownership
    predicate short-circuits to ``True``), returns without effect.

    Args:
        component: The ``bundle:skill[:script]`` component notation.
        allow_foreign: When ``True``, bypass the refusal (explicit override).

    Raises:
        WrongStoreError: when the store repo does not own the component's bundle
            and ``allow_foreign`` is ``False``.
    """
    if allow_foreign:
        return

    bundle = component.split(':', 1)[0]
    if main_anchored_store_owns_bundle(bundle):
        return

    store_repo = resolve_main_anchored_path('')
    raise WrongStoreError(
        f"lessons store repo '{store_repo}' does not own bundle '{bundle}' "
        f"(from component '{component}'); refusing to file into the wrong store. "
        f'Pass --allow-foreign-store to override.'
    )


def get_lessons_dir() -> Path:
    """Get the lessons-learned directory.

    The lessons corpus is a genuinely-shared cross-session global-scope state,
    so it is main-anchored via the single sanctioned resolver
    :func:`marketplace_paths.resolve_main_anchored_path` (ADR-002): it resolves
    to the MAIN checkout regardless of caller cwd (test override first, then
    git-common-dir). This is required by the audit finding — a phase-5
    ``execute-task`` lesson recording runs with cwd pinned to the worktree, and
    without main-anchoring the lesson would land in the worktree's empty corpus
    and be lost on move-back. There is NO local git-common-dir copy here.
    """
    return resolve_main_anchored_path(DIR_LESSONS)


def get_tombstones_dir() -> Path:
    """Get the tombstones directory under lessons-learned."""
    return get_lessons_dir() / '.tombstones'


def read_lesson(lesson_id: str) -> tuple[dict, str, str]:
    """Read a lesson file and return (metadata, title, body)."""
    lessons_dir = get_lessons_dir()
    path = lessons_dir / f'{lesson_id}.md'

    if not path.exists():
        return {}, '', ''

    content = path.read_text(encoding='utf-8')
    metadata = parse_markdown_metadata(content)

    # Extract title and body
    lines = content.split('\n')
    title = ''
    body_start = 0

    for i, line in enumerate(lines):
        if line.startswith('# '):
            title = line[2:].strip()
            body_start = i + 1
            break

    body = '\n'.join(lines[body_start:]).strip()

    return metadata, title, body


def _build_lesson_content(metadata: dict, title: str, body: str) -> str:
    """Render a lesson file's content to a string.

    Mirrors the on-disk shape produced by ``write_lesson_to`` /
    ``atomic_write_file`` (metadata header, blank line, ``# title``, blank line,
    body, terminating newline) so callers using exclusive create can write the
    same bytes without going through the atomic temp-file path.
    """
    lines = [f'{key}={value}' for key, value in metadata.items()]
    lines.append('')
    lines.append(f'# {title}')
    lines.append('')
    lines.append(body)
    rendered = '\n'.join(lines)
    if not rendered.endswith('\n'):
        rendered += '\n'
    return rendered
