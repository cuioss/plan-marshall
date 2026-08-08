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

import os
from pathlib import Path
from typing import NamedTuple

from constants import DIR_LESSONS
from file_ops import parse_markdown_metadata
from input_validation import COMPONENT_RE
from marketplace_paths import (
    _override_is_set,
    main_anchored_store_owns_bundle,
    resolve_main_anchored_path,
)

#: The closed vocabulary :func:`resolve_lesson_store` reports as ``resolution``.
#:
#: - ``main_anchored`` — the store was anchored on the MAIN checkout through the
#:   git common dir, which is the production path.
#: - ``override`` — a ``PLAN_BASE_DIR`` / ``set_base_dir()`` override stood in
#:   for the main checkout, which is the test path.
#: - ``unresolved`` — the store was NOT reached, so the caller could not look at
#:   it at all. :func:`resolve_lesson_store` returns this when neither anchor
#:   could be resolved; a consumer reporting the field for a path that never
#:   attempted resolution (``manage-status delete-plan --no-restore-lessons``)
#:   also reports ``unresolved``, because "I did not look" is the fact the
#:   field states and the reason it did not look is carried by the sibling
#:   action value.
#:
#: The third value is the one that carries the contract: without it a caller
#: cannot tell "I looked at the corpus and it was empty" from "I never reached
#: the corpus", and every lesson-retirement site collapsed those two into the
#: same benign zero. It follows that a resolved value must never be reported
#: for a store that was not reached — including by borrowing a sibling store's
#: resolution when the one being reported on is the one that failed. Consumers
#: assert against this set rather than re-listing the literals.
STORE_RESOLUTIONS = frozenset({'main_anchored', 'override', 'unresolved'})


class LessonStore(NamedTuple):
    """A resolved lessons-store handle together with the resolution provenance.

    ``path`` is ``None`` exactly when ``resolution == 'unresolved'``; on every
    other resolution it is the absolute resolved path. Callers therefore state
    which substrate a count was computed from instead of reporting a bare zero,
    and compare ``resolution`` against a :data:`STORE_RESOLUTIONS` member by
    explicit equality — never by the truthiness of ``path``, which cannot tell a
    legitimately-empty store from an unreachable one.

    Attributes:
        path: The resolved absolute store path, or ``None`` when unresolved.
        resolution: One of :data:`STORE_RESOLUTIONS`.
        detail: Human-readable provenance naming the substrate (or, when
            unresolved, the reason resolution failed) for direct inclusion in a
            report line.
    """

    path: Path | None
    resolution: str
    detail: str


def resolve_lesson_store(subpath: str | Path = DIR_LESSONS) -> LessonStore:
    """Resolve a main-anchored store subpath and report HOW it resolved.

    The explicit handle behind :func:`get_lessons_dir`. Where that resolver
    answers only "where is the store", this one also answers "did I actually
    reach it, and through which anchor" — the discriminator every consumer on
    the lesson-retirement path needs in order to distinguish a genuinely empty
    corpus from one it never reached.

    ``subpath`` defaults to the lessons corpus but is a parameter because the
    same main-anchored anchoring governs the ``plans`` root that
    ``restore-from-plan`` and ``list-stalled`` scan: a plan directory reached
    through a cwd-keyed resolver is the wrong-store failure direction, exactly
    as an unreachable corpus is the could-not-look one.

    The override branch is detected with the SAME predicate
    :func:`marketplace_paths.resolve_main_anchored_path` itself branches on, so
    the reported provenance can never disagree with the path actually returned.
    (Importing that sibling private mirrors the existing convention in this
    foundation — ``file_ops`` imports ``_find_plan_root_from_cwd`` from the same
    module for the same reason.)

    Args:
        subpath: Path under the main checkout's ``.plan/local`` to resolve;
            defaults to the lessons corpus.

    Returns:
        A :class:`LessonStore` handle. Never raises — an unresolvable store is
        returned as the ``unresolved`` resolution so the caller can report it,
        rather than as an exception that a caller might swallow into a zero.
    """
    resolution = 'override' if (os.environ.get('PLAN_BASE_DIR') or _override_is_set()) else 'main_anchored'

    try:
        path = resolve_main_anchored_path(subpath)
    except RuntimeError as exc:
        return LessonStore(
            None,
            'unresolved',
            f'cannot resolve the main-anchored store for {subpath!r}: {exc}',
        )

    return LessonStore(path, resolution, f'{path} (resolved {resolution})')


class WrongStoreError(Exception):
    """Raised when a lesson's component bundle is not owned by the resolved store repo.

    The manage-lessons entry module catches this and renders it as the standard
    ``status: error`` TOON (exit non-zero) rather than allocating a lesson into a
    store repo that does not own the component's bundle.
    """


class MalformedComponentError(Exception):
    """Raised when a component does not match the canonical component shape.

    Distinct from :class:`WrongStoreError`: the component is not merely owned by
    another repo, it is not a well-formed component at all. The manage-lessons
    entry module renders this as ``status: error`` with ``error: invalid_component``
    so a malformed input is never reported as an ownership problem.
    """


def guard_component_store_match(component: str, allow_foreign: bool) -> None:
    """Refuse to file a lesson whose bundle prefix is not owned by the store repo.

    The ownership question only exists for a component that actually names a
    bundle. Accordingly the guard evaluates four ordered branches:

    1. The component must match the canonical shape
       :data:`input_validation.COMPONENT_RE` — otherwise
       :class:`MalformedComponentError` is raised. This runs BEFORE the
       ``allow_foreign`` bypass so the override cannot launder a malformed value.
    2. ``allow_foreign`` short-circuits the remaining ownership check.
    3. A **prefix-less** component (no ``:``) is project-local by construction: it
       names no bundle, so there is no cross-repo ownership question to answer and
       no flag is required. Returns without effect.
    4. A **prefixed** component has its bundle taken from the first ``:``-segment
       and checked against
       :func:`marketplace_paths.main_anchored_store_owns_bundle`; a miss raises
       :class:`WrongStoreError` naming that bundle.

    Because branch 4 is the only path that raises :class:`WrongStoreError`, the
    refusal message names a value that genuinely IS a bundle.

    Args:
        component: Either a prefix-less project-local name (``integration-tests``)
            or the ``bundle:skill[:script]`` notation.
        allow_foreign: When ``True``, bypass the ownership refusal (explicit
            override). Does NOT bypass the shape check.

    Raises:
        MalformedComponentError: when ``component`` does not match the canonical
            component shape.
        WrongStoreError: when ``component`` carries a bundle prefix the store repo
            does not own and ``allow_foreign`` is ``False``.
    """
    # fullmatch, not match: `$` also matches just before a trailing newline, so
    # `match` would accept 'integration-tests\n' as well-formed.
    if not isinstance(component, str) or COMPONENT_RE.fullmatch(component) is None:
        raise MalformedComponentError(
            f'malformed component {component!r}; expected the canonical shape '
            f'{COMPONENT_RE.pattern} — either a prefix-less project-local name '
            f"(e.g. 'integration-tests') or a bundle-prefixed notation "
            f"(e.g. 'plan-marshall:manage-lessons')."
        )

    if allow_foreign:
        return

    if ':' not in component:
        # Project-local by construction — no bundle is named, so no store can
        # fail to own it. Filing requires no --allow-foreign-store override.
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

    Expressed in terms of :func:`resolve_lesson_store`, which is the explicit
    handle carrying the resolution provenance. This resolver keeps the bare-path
    signature its many callers use and RAISES on an unresolvable store, so a
    caller that has no discriminator to report cannot silently proceed against a
    store it never reached. A caller that needs to REPORT which substrate it
    read (or that it read none) calls :func:`resolve_lesson_store` directly.

    Raises:
        RuntimeError: when the main-anchored store cannot be resolved.
    """
    store = resolve_lesson_store(DIR_LESSONS)
    if store.path is None:
        raise RuntimeError(store.detail)
    return store.path


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
