#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Delta rule for the lessons-housekeeping finalize step.

The step judges every lesson in the corpus against the plan outcome. When it is
re-fired because HEAD advanced, most of those judgements cannot have changed:
a lesson's coverage verdict depends on the lesson itself and on the files it is
about. This script names the lessons a commit could affect, so a re-fire judges
those and carries every other lesson's previous result over.

One verb, ``resolve``, returns one of two modes:

* ``mode: full`` — judge the whole corpus. Returned, with a named ``reason``,
  whenever there is no trustworthy previous firing to carry results over from.
* ``mode: delta`` — judge only the lessons listed under ``affected``.

A lesson is affected when one of three rules holds, checked in this order (the
first that holds is the reported ``reason``):

* ``edited_since_last_firing`` — the lesson file was modified after the previous
  firing started, which also covers a lesson added since.
* ``standards_dir_changed`` — a changed path lies under the standards directory
  of the lesson's component.
* ``named_path_changed`` — a changed path contains, as a run of whole path
  segments, a path the lesson body names in backticks.

Full-run conditions — exactly three, each with its own ``reason``:

1. ``first_firing`` — the step has no record for this plan.
2. ``diff_unavailable`` — the difference to the previous firing's tree could
   not be computed.
3. The previous firing did not finish cleanly under this rule:
   ``last_firing_not_done`` (the record is not a completed one),
   ``classified_at_absent`` (the record is complete but carries no
   ``classified_at`` fact — the shape the dispatcher's commit re-stamp leaves
   after a source-editing firing, and the shape the step itself records when
   the firing could not stand as an anchor: a per-lesson removal, promotion or
   adaptation failed, the plan's footprint could not be read, or the firing
   ended before this script returned a payload), or
   ``classified_at_unreadable`` (the fact is present but is not a timestamp).

A carry-over anchor is never inferred from ``head_at_completion`` alone: without
a readable ``classified_at`` the rule cannot tell which lessons were edited since
the previous firing, so it runs in full.

Anything this script cannot look at — the change list, the lessons store, a
lesson file, the component-to-directory mapping — is ``status: error`` with a
named ``error``. The step treats every error as a full run.

The change list is obtained by calling ``verdict_currency.changed_paths_for_step``
in-process, so no repository-controlled path is ever interpolated into a command
line. The component-to-directory mapping is ``_derive_standards_dir`` from
``manage-lessons.py``, loaded by file path because that file name is hyphenated.

Usage::

    python3 .plan/execute-script.py \\
      default-bundle:finalize-step-lessons-housekeeping:affected_lessons resolve \\
      --plan-id PLAN_ID --worktree-path PATH
"""

from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NamedTuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: The finalize step whose record anchors the delta.
STEP_ID = 'project:finalize-step-lessons-housekeeping'

#: The fact the step records at the start of a firing that judged a corpus.
CLASSIFIED_AT_FACT = 'classified_at'

MODE_FULL = 'full'
MODE_DELTA = 'delta'

# Affected-lesson reasons, in the order the rules are checked.
REASON_EDITED = 'edited_since_last_firing'
REASON_STANDARDS_DIR = 'standards_dir_changed'
REASON_NAMED_PATH = 'named_path_changed'

# Full-run reasons.
FULL_FIRST_FIRING = 'first_firing'
FULL_DIFF_UNAVAILABLE = 'diff_unavailable'
FULL_LAST_FIRING_NOT_DONE = 'last_firing_not_done'
FULL_CLASSIFIED_AT_ABSENT = 'classified_at_absent'
FULL_CLASSIFIED_AT_UNREADABLE = 'classified_at_unreadable'

# Error tokens — something this script could not look at.
ERROR_CHANGE_LIST_UNAVAILABLE = 'change_list_unavailable'
ERROR_CHANGE_LIST_FAILED = 'change_list_failed'
ERROR_UNKNOWN_OUTCOME = 'unknown_change_list_outcome'
ERROR_STORE_UNRESOLVED = 'lessons_store_unresolved'
ERROR_LESSON_UNREADABLE = 'lesson_unreadable'
ERROR_MAPPING_UNAVAILABLE = 'standards_mapping_unavailable'
ERROR_STANDARDS_DIR_OUTSIDE_REPO = 'standards_dir_outside_repo'

#: A backtick span with no whitespace inside it — the shape a lesson body uses
#: to name a path.
_BACKTICK_SPAN = re.compile(r'`([^`\s]+)`')

#: Characters that make a path segment a pattern rather than a literal name — a
#: glob (``*``, ``?``, ``[``) or a placeholder (``{id}``, ``<name>``).
_PATTERN_CHARS = frozenset('*?[{<')

#: Segments that carry no name of their own.
_RELATIVE_SEGMENTS = frozenset({'', '.', '..'})


# ---------------------------------------------------------------------------
# Pure selection
# ---------------------------------------------------------------------------


class LessonRecord(NamedTuple):
    """The four facts about a lesson the delta rule reads."""

    lesson_id: str
    component: str
    body: str
    modified_at: float


class AffectedLesson(NamedTuple):
    """A lesson the delta rule selected, with the first rule that selected it."""

    lesson_id: str
    reason: str


def named_paths(body: str) -> list[str]:
    """Return the path fragments a lesson body names in backticks.

    A span counts as a citation when it contains a ``/`` and is not a URL, an
    absolute path, a home-relative path or a command-line flag. Each citation is
    reduced to the runs of literal path segments it carries, because a citation
    kept verbatim in any of the shapes below could never match a path git
    reports and the lesson would silently never be selected:

    - a test id (``path::test_x``) or an anchor (``path#section``) behind the
      path is dropped;
    - a single colon does not decide what the citation means, because the same
      character introduces a line (``path:598``) or a symbol (``path:main``),
      ends a notation prefix (``bundle:skill/standards/x.md``), separates a
      revision from its path (``origin/main:src/app.py``) and may be part of a
      file name (``src/a:b.py``). The citation therefore yields every reading
      that names a path: the span with its colons kept, and each
      colon-delimited piece that contains a ``/``. A piece without a ``/`` — a
      line number, a symbol, a bundle or skill token — names no path and yields
      nothing;
    - a glob, a placeholder or a relative segment (``dir/*.md``,
      ``plans/{id}/x``, ``../SKILL.md``) ends a run, and the first literal
      run is kept — the directory in front of the pattern, or the tail behind
      it when nothing literal precedes it (``*/standards/rule.md``).

    A span with no literal segment at all names nothing and is skipped. For a
    span that carries no colon the readings coincide and one fragment results.
    """
    paths: list[str] = []
    for span in _BACKTICK_SPAN.findall(body):
        if '/' not in span or '://' in span or span.startswith(('/', '~', '-')):
            continue
        for candidate in _cited_paths(span):
            fragment = _literal_run(candidate)
            if fragment and fragment not in paths:
                paths.append(fragment)
    return paths


def _cited_paths(span: str) -> list[str]:
    """Return every reading of a citation that names a path, colons kept first."""
    cited = span.split('#', 1)[0].split('::', 1)[0]
    return [cited, *(piece for piece in cited.split(':') if '/' in piece)]


def _literal_run(cited: str) -> str:
    run: list[str] = []
    for segment in cited.split('/'):
        if segment in _RELATIVE_SEGMENTS or _PATTERN_CHARS.intersection(segment):
            if run:
                break
            continue
        run.append(segment)
    return '/'.join(run)


def _names(changed_path: str, fragment: str) -> bool:
    """Whether ``fragment`` occurs in ``changed_path`` as a run of whole segments.

    A fragment is not anchored at the repository root: a lesson may cite a file
    relative to its skill, or behind a notation prefix or a revision. The
    match therefore selects more lessons than an anchored one would, which is
    the direction a rule deciding what may be carried over unjudged must err in.
    """
    changed = changed_path.split('/')
    wanted = fragment.split('/')
    return any(changed[start : start + len(wanted)] == wanted for start in range(len(changed) - len(wanted) + 1))


def select_affected(
    changed_paths: Sequence[str],
    last_firing_at: float,
    lessons: Sequence[LessonRecord],
    standards_dir_of: Callable[[str], str],
) -> list[AffectedLesson]:
    """Select the lessons a change list could affect.

    Pure: no filesystem, no git, no clock. ``standards_dir_of`` maps a lesson's
    component to its repo-relative standards directory (with a trailing ``/``),
    or to the empty string when the component names no such directory.

    Args:
        changed_paths: Repo-relative paths that differ since the last firing.
        last_firing_at: Start of the last firing, as seconds since the epoch.
        lessons: The corpus, one record per lesson.
        standards_dir_of: Component to repo-relative standards directory.

    Returns:
        The affected lessons in corpus order, each with the first rule that
        selected it. A lesson no rule selects is absent from the result.
    """
    affected: list[AffectedLesson] = []
    for lesson in lessons:
        reason = _first_matching_rule(lesson, changed_paths, last_firing_at, standards_dir_of)
        if reason is not None:
            affected.append(AffectedLesson(lesson.lesson_id, reason))
    return affected


def _first_matching_rule(
    lesson: LessonRecord,
    changed_paths: Sequence[str],
    last_firing_at: float,
    standards_dir_of: Callable[[str], str],
) -> str | None:
    if lesson.modified_at > last_firing_at:
        return REASON_EDITED
    standards_dir = standards_dir_of(lesson.component)
    if standards_dir and any(path.startswith(standards_dir) for path in changed_paths):
        return REASON_STANDARDS_DIR
    names = named_paths(lesson.body)
    if any(_names(path, name) for path in changed_paths for name in names):
        return REASON_NAMED_PATH
    return None


# ---------------------------------------------------------------------------
# Boundary helpers
# ---------------------------------------------------------------------------


def parse_timestamp(value: object) -> float | None:
    """Parse an ISO-8601 timestamp into seconds since the epoch, or ``None``.

    A value with no UTC offset is read as UTC, matching how the step writes it.
    """
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip())
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.timestamp()


def repo_relative_dir(directory: str, repo_root: Path) -> str | None:
    """Make a derived standards directory repo-relative, with a trailing ``/``.

    Returns the empty string for an empty input (the component names no
    standards directory) and ``None`` when an absolute directory lies outside
    ``repo_root`` — a mapping that cannot be compared against the change list.
    """
    if not directory:
        return ''
    path = Path(directory)
    if not path.is_absolute():
        return f'{path.as_posix().rstrip("/")}/'
    try:
        relative = path.resolve().relative_to(repo_root.resolve())
    except ValueError:
        return None
    return f'{relative.as_posix().rstrip("/")}/'


def _error(error: str, message: str, firing_started_at: str) -> dict[str, Any]:
    return {
        'status': 'error',
        'error': error,
        'message': message,
        'firing_started_at': firing_started_at,
    }


def _full(reason: str, detail: str, firing_started_at: str, change_list: dict[str, Any]) -> dict[str, Any]:
    return {
        'status': 'success',
        'mode': MODE_FULL,
        'reason': reason,
        'detail': detail,
        'firing_started_at': firing_started_at,
        'recorded_head': change_list.get('recorded_head'),
        'live_head': change_list.get('live_head'),
    }


def _load_standards_dir_deriver(lessons_scripts_dir: Path) -> Callable[[str], str]:
    """Load ``_derive_standards_dir`` from ``manage-lessons.py`` by file path."""
    source = lessons_scripts_dir / 'manage-lessons.py'
    spec = importlib.util.spec_from_file_location('manage_lessons_for_affected_lessons', source)
    if spec is None or spec.loader is None:
        raise ImportError(f'no import spec for {source}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    deriver: Callable[[str], str] = module._derive_standards_dir
    return deriver


def _read_corpus(lessons_dir: Path, resolve_lesson: Callable[[str], Any]) -> tuple[list[LessonRecord], str | None]:
    """Read every lesson in the corpus; report the first one that cannot be read."""
    records: list[LessonRecord] = []
    if not lessons_dir.is_dir():
        return records, None
    for lesson_file in sorted(lessons_dir.glob('*.md')):
        read = resolve_lesson(lesson_file.stem)
        if read.state != 'found':
            return [], f'{lesson_file.name}: {read.detail}'
        try:
            modified_at = lesson_file.stat().st_mtime
        except OSError as exc:
            return [], f'{lesson_file.name}: modification time unreadable ({exc})'
        records.append(
            LessonRecord(
                lesson_id=lesson_file.stem,
                component=str(read.metadata.get('component', '')),
                body=read.body,
                modified_at=modified_at,
            )
        )
    return records, None


# ---------------------------------------------------------------------------
# The ``resolve`` verb
# ---------------------------------------------------------------------------


def _classify_change_list(change_list: dict[str, Any], firing_started_at: str) -> dict[str, Any] | float:
    """Return a terminal payload, or the last-firing time when a delta is possible."""
    from verdict_currency import (
        OUTCOME_COMPUTED,
        OUTCOME_DIFF_UNAVAILABLE,
        OUTCOME_FIRST_FIRING,
        OUTCOME_LAST_FIRING_NOT_DONE,
    )

    outcome = change_list.get('outcome')
    if outcome == OUTCOME_FIRST_FIRING:
        return _full(FULL_FIRST_FIRING, 'the step has no record for this plan', firing_started_at, change_list)
    if outcome == OUTCOME_DIFF_UNAVAILABLE:
        return _full(
            FULL_DIFF_UNAVAILABLE,
            'the difference to the previous firing could not be computed',
            firing_started_at,
            change_list,
        )
    if outcome == OUTCOME_LAST_FIRING_NOT_DONE:
        return _full(
            FULL_LAST_FIRING_NOT_DONE,
            'the previous firing left no completed record anchored to a commit',
            firing_started_at,
            change_list,
        )
    if outcome != OUTCOME_COMPUTED:
        return _error(
            ERROR_UNKNOWN_OUTCOME,
            f'the change list reported an outcome this script does not know: {outcome!r}',
            firing_started_at,
        )

    facts = change_list.get('recorded_facts')
    classified_at = facts.get(CLASSIFIED_AT_FACT) if isinstance(facts, dict) else None
    if classified_at is None or classified_at == '':
        return _full(
            FULL_CLASSIFIED_AT_ABSENT,
            f'the previous record carries no {CLASSIFIED_AT_FACT} fact, so there is no carry-over anchor',
            firing_started_at,
            change_list,
        )
    last_firing_at = parse_timestamp(classified_at)
    if last_firing_at is None:
        return _full(
            FULL_CLASSIFIED_AT_UNREADABLE,
            f'the previous record carries {CLASSIFIED_AT_FACT}={classified_at!r}, which is not a timestamp',
            firing_started_at,
            change_list,
        )
    return last_firing_at


def resolve_delta(plan_id: str, worktree_path: str, firing_started_at: str) -> dict[str, Any]:
    """Decide between a full run and a delta run, and name the affected lessons.

    Args:
        plan_id: The plan whose status holds the step record.
        worktree_path: The worktree the change list is computed in.
        firing_started_at: The start of this firing, echoed on every payload so
            the step can record it as ``classified_at`` whichever mode it runs in.

    Returns:
        The verb's payload — ``mode: full``, ``mode: delta``, or ``status: error``.
    """
    try:
        from verdict_currency import changed_paths_for_step
    except ImportError as exc:
        return _error(ERROR_CHANGE_LIST_UNAVAILABLE, f'verdict_currency is not importable ({exc})', firing_started_at)

    change_list = changed_paths_for_step(plan_id=plan_id, step=STEP_ID, worktree_path=worktree_path)
    if change_list.get('status') != 'success':
        return _error(
            ERROR_CHANGE_LIST_FAILED,
            f'the change list could not be read: {change_list.get("error")} — {change_list.get("message")}',
            firing_started_at,
        )

    classified = _classify_change_list(change_list, firing_started_at)
    if isinstance(classified, dict):
        return classified
    last_firing_at = classified

    try:
        import _lessons_io
    except ImportError as exc:
        return _error(ERROR_STORE_UNRESOLVED, f'the lessons readers are not importable ({exc})', firing_started_at)

    store = _lessons_io.resolve_lesson_store()
    if store.path is None:
        return _error(ERROR_STORE_UNRESOLVED, store.detail, firing_started_at)

    lessons, unreadable = _read_corpus(store.path, _lessons_io.resolve_lesson)
    if unreadable is not None:
        return _error(ERROR_LESSON_UNREADABLE, unreadable, firing_started_at)

    try:
        derive = _load_standards_dir_deriver(Path(_lessons_io.__file__).resolve().parent)
    except Exception as exc:  # any load failure means the mapping is unavailable
        return _error(
            ERROR_MAPPING_UNAVAILABLE, f'_derive_standards_dir could not be loaded ({exc})', firing_started_at
        )

    repo_root = Path(worktree_path)
    standards_dirs: dict[str, str] = {}
    for component in {lesson.component for lesson in lessons}:
        relative = repo_relative_dir(derive(component), repo_root)
        if relative is None:
            return _error(
                ERROR_STANDARDS_DIR_OUTSIDE_REPO,
                f'the standards directory of component {component!r} lies outside {repo_root}',
                firing_started_at,
            )
        standards_dirs[component] = relative

    changed_paths = [str(path) for path in change_list.get('changed_paths') or []]
    affected = select_affected(changed_paths, last_firing_at, lessons, lambda component: standards_dirs[component])

    return {
        'status': 'success',
        'mode': MODE_DELTA,
        'firing_started_at': firing_started_at,
        'recorded_head': change_list.get('recorded_head'),
        'live_head': change_list.get('live_head'),
        'store_resolution': store.resolution,
        'changed_path_count': len(changed_paths),
        'lessons_total': len(lessons),
        'examined': len(affected),
        'carried_over': len(lessons) - len(affected),
        'affected': [{'lesson_id': lesson.lesson_id, 'reason': lesson.reason} for lesson in affected],
    }


def cmd_resolve(args: argparse.Namespace) -> int:
    """CLI wrapper around :func:`resolve_delta` — emits TOON, returns 0.

    Exit code 0 on every payload: the caller branches on ``status`` and then
    ``mode``, never on the exit code.
    """
    from input_validation import require_valid_plan_id
    from toon_parser import serialize_toon

    require_valid_plan_id(args)
    firing_started_at = datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')
    payload = resolve_delta(
        plan_id=args.plan_id,
        worktree_path=args.worktree_path,
        firing_started_at=firing_started_at,
    )
    print(serialize_toon(payload))
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser with the ``resolve`` subcommand."""
    parser = argparse.ArgumentParser(
        description=(
            'Delta rule for the lessons-housekeeping finalize step: name the lessons a '
            'HEAD advance could affect, or report that the whole corpus must be judged.'
        ),
        allow_abbrev=False,
    )
    sub = parser.add_subparsers(dest='command_name', required=True)

    resolve_parser = sub.add_parser(
        'resolve',
        help='Return mode: full or mode: delta for this firing',
        allow_abbrev=False,
    )
    resolve_parser.add_argument(
        '--plan-id',
        required=True,
        dest='plan_id',
        help='Plan whose status holds the step record.',
    )
    resolve_parser.add_argument(
        '--worktree-path',
        required=True,
        dest='worktree_path',
        help='Worktree root the change list is computed in.',
    )
    resolve_parser.set_defaults(func=cmd_resolve)

    return parser


def main() -> int:
    """Parse args and dispatch to the selected subcommand handler."""
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == '__main__':
    sys.exit(main())


__all__ = [
    'AffectedLesson',
    'LessonRecord',
    'named_paths',
    'parse_timestamp',
    'repo_relative_dir',
    'resolve_delta',
    'select_affected',
]
