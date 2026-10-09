#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Tests for ``affected_lessons.py``, the lessons-housekeeping delta rule.

The script decides, for a re-fire of the lessons-housekeeping finalize step,
whether the whole corpus must be judged again (``mode: full``) or only the
lessons a commit could affect (``mode: delta``).

The script lives under ``.claude/skills/``, outside the marketplace bundles, so
it is loaded here by file path. Every end-to-end test runs against a REAL
temporary git repository and a real lessons corpus in the per-test sandbox
store. Only the status document is substituted, through the ``read_status``
seam: the step-record lookup, the tree difference, the corpus read and the
component-to-directory mapping loaded from ``manage-lessons.py`` all run for
real.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

import _lessons_io
import _status_core
from toon_parser import parse_toon

from conftest import PROJECT_ROOT

_SKILL_DIR = PROJECT_ROOT / '.claude' / 'skills' / 'finalize-step-lessons-housekeeping'
_SCRIPT = _SKILL_DIR / 'scripts' / 'affected_lessons.py'


def _load_script() -> ModuleType:
    """Load the script by path, publishing nothing in ``sys.modules``."""
    spec = importlib.util.spec_from_file_location('affected_lessons_under_test', _SCRIPT)
    assert spec is not None and spec.loader is not None, f'no import spec for {_SCRIPT}'
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_mod = _load_script()

_PLAN_ID = 'affected-lessons-plan'
_FIRING_STARTED_AT = '2025-09-01T00:00:00Z'

#: The start of the previous firing, as the step records it.
_CLASSIFIED_AT = '2025-06-01T00:00:00Z'
_BEFORE_LAST_FIRING = datetime(2025, 1, 1, tzinfo=UTC).timestamp()
_AFTER_LAST_FIRING = datetime(2025, 7, 1, tzinfo=UTC).timestamp()

_ALPHA_STANDARD = 'marketplace/bundles/alpha/skills/one/standards/rule.md'

#: Six lessons in three components, two per component, in corpus (id) order.
_CORPUS: tuple[tuple[str, str], ...] = (
    ('2025-01-01-01-001', 'alpha:one'),
    ('2025-01-01-01-002', 'alpha:one'),
    ('2025-01-01-01-003', 'beta:two'),
    ('2025-01-01-01-004', 'beta:two'),
    ('2025-01-01-01-005', 'gamma:three'),
    ('2025-01-01-01-006', 'gamma:three'),
)


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ['git', '-C', str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout.strip()


def _commit(repo: Path, files: dict[str, str]) -> str:
    """Write ``files`` and commit them together, returning the new HEAD."""
    for relative, body in files.items():
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding='utf-8')
        _git(repo, 'add', relative)
    _git(repo, 'commit', '--quiet', '-m', 'commit')
    return _git(repo, 'rev-parse', 'HEAD')


@pytest.fixture
def git_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A repository that is also the marketplace root the mapping resolves against.

    ``_derive_standards_dir`` anchors a component's standards directory on the
    resolved ``marketplace/bundles`` tree. Pointing that resolution at this
    repository is what makes a derived directory comparable with the paths the
    repository's own tree difference reports.
    """
    repo = tmp_path / 'repo'
    repo.mkdir()
    _git(repo, 'init', '--quiet')
    _git(repo, 'config', 'user.email', 'test@example.invalid')
    _git(repo, 'config', 'user.name', 'Test')
    _git(repo, 'config', 'commit.gpgsign', 'false')
    monkeypatch.setenv('PM_MARKETPLACE_ROOT', str(repo))
    return repo


@pytest.fixture
def lessons_dir() -> Path:
    """The lessons corpus of the per-test sandbox store, created empty."""
    directory = _lessons_io.get_lessons_dir()
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _seed_lesson(
    lessons_dir: Path,
    lesson_id: str,
    component: str,
    body: str = 'Body with no path in it.',
    modified_at: float = _BEFORE_LAST_FIRING,
) -> Path:
    path = lessons_dir / f'{lesson_id}.md'
    path.write_text(
        f'id={lesson_id}\ncomponent={component}\ncategory=improvement\ncreated=2025-01-01\nstatus=active\n'
        f'\n# Lesson {lesson_id}\n\n{body}\n',
        encoding='utf-8',
    )
    os.utime(path, (modified_at, modified_at))
    return path


def _seed_corpus(lessons_dir: Path, overrides: dict[str, dict[str, Any]] | None = None) -> None:
    """Seed :data:`_CORPUS`, every lesson last modified before the previous firing.

    ``overrides`` maps a lesson id to the ``_seed_lesson`` keywords that differ
    for that one lesson.
    """
    for lesson_id, component in _CORPUS:
        _seed_lesson(lessons_dir, lesson_id, component, **(overrides or {}).get(lesson_id, {}))


def _status_with(record: dict[str, Any] | None) -> dict[str, Any]:
    """A status document in the persisted shape, holding ``record`` for the step."""
    steps = {} if record is None else {_mod.STEP_ID: record}
    return {'title': 'affected-lessons', 'metadata': {'phase_steps': {'6-finalize': steps}}}


def _patch_status(monkeypatch: pytest.MonkeyPatch, status: dict[str, Any]) -> None:
    monkeypatch.setattr(_status_core, 'read_status', lambda _plan_id: status)


def _classified_record(head: str, classified_at: str = _CLASSIFIED_AT) -> dict[str, Any]:
    """A completed record of a firing that judged a corpus under the delta rule."""
    return {
        'outcome': 'done',
        'display_detail': 'corpus judged',
        'head_at_completion': head,
        'facts': {_mod.CLASSIFIED_AT_FACT: classified_at},
    }


def _resolve(repo: Path) -> dict[str, Any]:
    payload: dict[str, Any] = _mod.resolve_delta(_PLAN_ID, str(repo), _FIRING_STARTED_AT)
    return payload


def _affected(payload: dict[str, Any]) -> dict[str, str]:
    return {row['lesson_id']: row['reason'] for row in payload['affected']}


def _assert_full(payload: dict[str, Any], reason: str) -> None:
    """A full run names its reason and carries no trace of a delta."""
    assert payload['status'] == 'success'
    assert payload['mode'] == _mod.MODE_FULL
    assert payload['reason'] == reason
    assert payload['firing_started_at'] == _FIRING_STARTED_AT
    assert 'affected' not in payload
    assert 'carried_over' not in payload
    assert 'examined' not in payload


# ---------------------------------------------------------------------------
# Citation shapes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ('span', 'expected'),
    [
        ('src/app.py:598', ['src/app.py']),
        ('src/app.py:10:4', ['src/app.py']),
        ('doc/guide/*.md', ['doc/guide']),
        ('plans/{plan_id}/request.md', ['plans']),
        ('*/standards/rule.md', []),
    ],
    ids=['line-suffix', 'line-and-column-suffix', 'glob', 'placeholder', 'pattern-first-segment'],
)
def test_cited_span_is_reduced_to_the_literal_path_it_stands_for(span: str, expected: list[str]) -> None:
    """A citation git could never report verbatim still names a literal path."""
    assert _mod.named_paths(f'See `{span}` for the rule.') == expected


# ---------------------------------------------------------------------------
# Delta runs
# ---------------------------------------------------------------------------


def test_standards_change_selects_that_component_plus_the_lesson_edited_since(
    git_repo: Path, lessons_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Arrange
    recorded = _commit(git_repo, {_ALPHA_STANDARD: 'rule v1\n', 'src/app.py': 'x = 1\n'})
    live = _commit(git_repo, {_ALPHA_STANDARD: 'rule v2\n'})
    _seed_corpus(lessons_dir, {'2025-01-01-01-006': {'modified_at': _AFTER_LAST_FIRING}})
    _patch_status(monkeypatch, _status_with(_classified_record(recorded)))

    # Act
    payload = _resolve(git_repo)

    # Assert
    assert payload['status'] == 'success'
    assert payload['mode'] == _mod.MODE_DELTA
    assert _affected(payload) == {
        '2025-01-01-01-001': _mod.REASON_STANDARDS_DIR,
        '2025-01-01-01-002': _mod.REASON_STANDARDS_DIR,
        '2025-01-01-01-006': _mod.REASON_EDITED,
    }
    assert payload['lessons_total'] == len(_CORPUS)
    assert payload['examined'] == 3
    assert payload['carried_over'] == 3
    assert payload['changed_path_count'] == 1
    assert payload['recorded_head'] == recorded
    assert payload['live_head'] == live
    assert payload['firing_started_at'] == _FIRING_STARTED_AT
    assert payload['store_resolution'] == 'override'


def test_empty_change_list_with_no_edited_lesson_examines_nothing(
    git_repo: Path, lessons_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Arrange
    recorded = _commit(git_repo, {_ALPHA_STANDARD: 'rule v1\n'})
    _seed_corpus(lessons_dir)
    _patch_status(monkeypatch, _status_with(_classified_record(recorded)))

    # Act
    payload = _resolve(git_repo)

    # Assert
    assert payload['status'] == 'success'
    assert payload['mode'] == _mod.MODE_DELTA
    assert payload['examined'] == 0
    assert payload['affected'] == []
    assert payload['changed_path_count'] == 0
    assert payload['lessons_total'] == len(_CORPUS)
    assert payload['carried_over'] == len(_CORPUS)


@pytest.mark.parametrize(
    'named',
    [
        'src/app.py',
        './src/app.py',
        'src/',
        'src/app.py:598',
        'src/app.py:10-20',
        'src/*.py',
        'src/{name}.py',
    ],
    ids=[
        'exact-path',
        'dot-slash-prefix',
        'enclosing-directory',
        'line-suffix',
        'line-range-suffix',
        'glob',
        'placeholder',
    ],
)
def test_lesson_naming_a_changed_path_in_backticks_is_selected(
    named: str, git_repo: Path, lessons_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Arrange
    recorded = _commit(git_repo, {_ALPHA_STANDARD: 'rule v1\n', 'src/app.py': 'x = 1\n'})
    _commit(git_repo, {'src/app.py': 'x = 2\n'})
    _seed_corpus(lessons_dir, {'2025-01-01-01-003': {'body': f'The defect was in `{named}` all along.'}})
    _patch_status(monkeypatch, _status_with(_classified_record(recorded)))

    # Act
    payload = _resolve(git_repo)

    # Assert
    assert payload['mode'] == _mod.MODE_DELTA
    assert _affected(payload) == {'2025-01-01-01-003': _mod.REASON_NAMED_PATH}
    assert payload['carried_over'] == len(_CORPUS) - 1


def test_path_named_without_backticks_does_not_select_the_lesson(
    git_repo: Path, lessons_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Negative control for the backtick rule: prose naming a path selects nothing."""
    # Arrange
    recorded = _commit(git_repo, {_ALPHA_STANDARD: 'rule v1\n', 'src/app.py': 'x = 1\n'})
    _commit(git_repo, {'src/app.py': 'x = 2\n'})
    _seed_corpus(lessons_dir, {'2025-01-01-01-003': {'body': 'The defect was in src/app.py all along.'}})
    _patch_status(monkeypatch, _status_with(_classified_record(recorded)))

    # Act
    payload = _resolve(git_repo)

    # Assert
    assert payload['mode'] == _mod.MODE_DELTA
    assert payload['changed_path_count'] == 1
    assert payload['affected'] == []


# ---------------------------------------------------------------------------
# Full runs — exactly three conditions, the third on each of its routes
# ---------------------------------------------------------------------------


def test_no_record_for_the_step_is_a_full_run_first_firing(
    git_repo: Path, lessons_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Arrange
    _commit(git_repo, {_ALPHA_STANDARD: 'rule v1\n'})
    _seed_corpus(lessons_dir)
    _patch_status(monkeypatch, _status_with(None))

    # Act
    payload = _resolve(git_repo)

    # Assert
    _assert_full(payload, _mod.FULL_FIRST_FIRING)


def test_unresolvable_recorded_commit_is_a_full_run_diff_unavailable(
    git_repo: Path, lessons_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Arrange
    _commit(git_repo, {_ALPHA_STANDARD: 'rule v1\n'})
    _seed_corpus(lessons_dir)
    _patch_status(monkeypatch, _status_with(_classified_record('deadbeef' * 5)))

    # Act
    payload = _resolve(git_repo)

    # Assert
    _assert_full(payload, _mod.FULL_DIFF_UNAVAILABLE)


def test_failed_previous_firing_is_a_full_run_last_firing_not_done(
    git_repo: Path, lessons_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Arrange
    recorded = _commit(git_repo, {_ALPHA_STANDARD: 'rule v1\n'})
    _commit(git_repo, {_ALPHA_STANDARD: 'rule v2\n'})
    _seed_corpus(lessons_dir)
    record = {
        'outcome': 'failed',
        'display_detail': 'corpus unreadable',
        'head_at_completion': recorded,
        'facts': {_mod.CLASSIFIED_AT_FACT: _CLASSIFIED_AT},
    }
    _patch_status(monkeypatch, _status_with(record))

    # Act
    payload = _resolve(git_repo)

    # Assert
    _assert_full(payload, _mod.FULL_LAST_FIRING_NOT_DONE)


@pytest.mark.parametrize(
    'extra',
    [{}, {'facts': {'work_performed': 'true'}}],
    ids=['no-facts-key', 'facts-without-classified-at'],
)
def test_commit_restamp_record_shape_is_a_full_run_classified_at_absent(
    extra: dict[str, Any], git_repo: Path, lessons_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The record the commit re-stamp leaves is never read as a carry-over anchor.

    ``outcome: done``, a ``head_at_completion`` git resolves and a non-empty
    change list are everything a delta would need except ``classified_at``.
    Without that fact the rule cannot tell which lessons were edited since, so
    it reports a full run and names no affected lesson and no carried-over count.
    """
    # Arrange
    recorded = _commit(git_repo, {_ALPHA_STANDARD: 'rule v1\n'})
    _commit(git_repo, {_ALPHA_STANDARD: 'rule v2\n'})
    _seed_corpus(lessons_dir)
    record = {'outcome': 'done', 'display_detail': 're-stamped', 'head_at_completion': recorded, **extra}
    _patch_status(monkeypatch, _status_with(record))

    # Act
    payload = _resolve(git_repo)

    # Assert
    _assert_full(payload, _mod.FULL_CLASSIFIED_AT_ABSENT)
    assert payload['recorded_head'] == recorded


def test_classified_at_that_is_not_a_timestamp_is_a_full_run_classified_at_unreadable(
    git_repo: Path, lessons_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Arrange
    recorded = _commit(git_repo, {_ALPHA_STANDARD: 'rule v1\n'})
    _commit(git_repo, {_ALPHA_STANDARD: 'rule v2\n'})
    _seed_corpus(lessons_dir)
    _patch_status(monkeypatch, _status_with(_classified_record(recorded, classified_at='last tuesday')))

    # Act
    payload = _resolve(git_repo)

    # Assert
    _assert_full(payload, _mod.FULL_CLASSIFIED_AT_UNREADABLE)


def test_full_run_reasons_are_distinct() -> None:
    """Each full-run condition is told apart by its reason, so none may collide."""
    # Arrange
    reasons = [
        _mod.FULL_FIRST_FIRING,
        _mod.FULL_DIFF_UNAVAILABLE,
        _mod.FULL_LAST_FIRING_NOT_DONE,
        _mod.FULL_CLASSIFIED_AT_ABSENT,
        _mod.FULL_CLASSIFIED_AT_UNREADABLE,
    ]

    # Act / Assert
    assert len(set(reasons)) == len(reasons)


# ---------------------------------------------------------------------------
# Could not look — a named error, never a delta
# ---------------------------------------------------------------------------


def test_unknown_plan_is_a_named_error_not_a_first_firing(
    git_repo: Path, lessons_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Arrange
    _commit(git_repo, {_ALPHA_STANDARD: 'rule v1\n'})
    _seed_corpus(lessons_dir)
    _patch_status(monkeypatch, {})

    # Act
    payload = _resolve(git_repo)

    # Assert
    assert payload['status'] == 'error'
    assert payload['error'] == _mod.ERROR_CHANGE_LIST_FAILED
    assert payload['firing_started_at'] == _FIRING_STARTED_AT
    assert 'mode' not in payload
    assert 'affected' not in payload


def test_lesson_without_a_metadata_header_is_a_named_error(
    git_repo: Path, lessons_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Arrange
    recorded = _commit(git_repo, {_ALPHA_STANDARD: 'rule v1\n'})
    _seed_corpus(lessons_dir)
    (lessons_dir / '2025-01-01-01-007.md').write_text('# No header\n\nJust prose.\n', encoding='utf-8')
    _patch_status(monkeypatch, _status_with(_classified_record(recorded)))

    # Act
    payload = _resolve(git_repo)

    # Assert
    assert payload['status'] == 'error'
    assert payload['error'] == _mod.ERROR_LESSON_UNREADABLE
    assert '2025-01-01-01-007.md' in payload['message']
    assert 'affected' not in payload


def test_standards_directory_outside_the_worktree_is_a_named_error(
    git_repo: Path, lessons_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A mapping that cannot be compared with the change list is not read as "unchanged"."""
    # Arrange
    recorded = _commit(git_repo, {_ALPHA_STANDARD: 'rule v1\n'})
    _seed_corpus(lessons_dir)
    elsewhere = tmp_path / 'elsewhere'
    (elsewhere / 'marketplace' / 'bundles').mkdir(parents=True)
    monkeypatch.setenv('PM_MARKETPLACE_ROOT', str(elsewhere))
    _patch_status(monkeypatch, _status_with(_classified_record(recorded)))

    # Act
    payload = _resolve(git_repo)

    # Assert
    assert payload['status'] == 'error'
    assert payload['error'] == _mod.ERROR_STANDARDS_DIR_OUTSIDE_REPO
    assert 'affected' not in payload


# ---------------------------------------------------------------------------
# Pure selection and boundary helpers
# ---------------------------------------------------------------------------


def test_first_matching_rule_is_the_reported_reason() -> None:
    """A lesson all three rules select reports the first one in the checked order."""
    # Arrange
    lesson = _mod.LessonRecord('L1', 'alpha:one', 'See `src/app.py`.', modified_at=200.0)
    changed = ['std/alpha/rule.md', 'src/app.py']

    # Act
    edited = _mod.select_affected(changed, 100.0, [lesson], lambda _component: 'std/alpha/')
    standards = _mod.select_affected(changed, 300.0, [lesson], lambda _component: 'std/alpha/')
    named = _mod.select_affected(changed, 300.0, [lesson], lambda _component: '')

    # Assert
    assert edited == [_mod.AffectedLesson('L1', _mod.REASON_EDITED)]
    assert standards == [_mod.AffectedLesson('L1', _mod.REASON_STANDARDS_DIR)]
    assert named == [_mod.AffectedLesson('L1', _mod.REASON_NAMED_PATH)]


def test_component_without_a_standards_directory_matches_no_changed_path() -> None:
    """An empty mapping must not behave as a prefix of every path."""
    # Arrange
    lesson = _mod.LessonRecord('L1', 'project-local', 'No path named.', modified_at=0.0)

    # Act
    affected = _mod.select_affected(['any/changed/file.py'], 100.0, [lesson], lambda _component: '')

    # Assert
    assert affected == []


def test_named_paths_keeps_repo_relative_paths_only() -> None:
    # Arrange
    body = (
        'Paths: `src/app.py`, `./doc/notes.md`, `marketplace/bundles/alpha/`, `src/app.py` again. '
        'Not paths: `plain_word`, `https://example.invalid/a/b`, `/etc/hosts`, `~/notes/x`, '
        '`--flag/with-slash`, `two words/here`.'
    )

    # Act
    paths = _mod.named_paths(body)

    # Assert
    assert paths == ['src/app.py', 'doc/notes.md', 'marketplace/bundles/alpha']


def test_sibling_path_sharing_a_name_prefix_is_not_under_the_named_path() -> None:
    # Arrange
    lesson = _mod.LessonRecord('L1', 'project-local', 'See `src/app`.', modified_at=0.0)

    # Act
    affected = _mod.select_affected(['src/app_helpers.py'], 100.0, [lesson], lambda _component: '')

    # Assert
    assert affected == []


@pytest.mark.parametrize(
    ('value', 'expected'),
    [
        ('2025-06-01T00:00:00Z', datetime(2025, 6, 1, tzinfo=UTC).timestamp()),
        ('2025-06-01T00:00:00', datetime(2025, 6, 1, tzinfo=UTC).timestamp()),
        ('2025-06-01T02:00:00+02:00', datetime(2025, 6, 1, tzinfo=UTC).timestamp()),
        ('last tuesday', None),
        ('', None),
        (None, None),
        (1748736000, None),
    ],
    ids=['utc-z', 'naive-read-as-utc', 'offset', 'not-a-timestamp', 'empty', 'none', 'not-a-string'],
)
def test_parse_timestamp(value: object, expected: float | None) -> None:
    # Act
    parsed = _mod.parse_timestamp(value)

    # Assert
    assert parsed == expected


def test_repo_relative_dir(tmp_path: Path) -> None:
    # Arrange
    repo = tmp_path / 'repo'
    inside = repo / 'marketplace' / 'bundles' / 'alpha' / 'skills' / 'one' / 'standards'
    inside.mkdir(parents=True)

    # Act / Assert
    assert _mod.repo_relative_dir('', repo) == ''
    assert _mod.repo_relative_dir('rel/standards/', repo) == 'rel/standards/'
    assert _mod.repo_relative_dir(f'{inside}/', repo) == 'marketplace/bundles/alpha/skills/one/standards/'
    assert _mod.repo_relative_dir(str(tmp_path / 'elsewhere' / 'standards'), repo) is None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _run_cli(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], repo: Path
) -> tuple[int, dict[str, Any]]:
    monkeypatch.setattr(
        sys,
        'argv',
        ['affected_lessons.py', 'resolve', '--plan-id', _PLAN_ID, '--worktree-path', str(repo)],
    )
    exit_code = _mod.main()
    parsed: dict[str, Any] = parse_toon(capsys.readouterr().out)
    return exit_code, parsed


def test_cli_emits_the_delta_payload_and_exits_zero(
    git_repo: Path, lessons_dir: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Arrange
    recorded = _commit(git_repo, {_ALPHA_STANDARD: 'rule v1\n'})
    _commit(git_repo, {_ALPHA_STANDARD: 'rule v2\n'})
    _seed_corpus(lessons_dir)
    _patch_status(monkeypatch, _status_with(_classified_record(recorded)))

    # Act
    exit_code, parsed = _run_cli(monkeypatch, capsys, git_repo)

    # Assert
    assert exit_code == 0
    assert parsed['mode'] == _mod.MODE_DELTA
    assert _affected(parsed) == {
        '2025-01-01-01-001': _mod.REASON_STANDARDS_DIR,
        '2025-01-01-01-002': _mod.REASON_STANDARDS_DIR,
    }
    assert _mod.parse_timestamp(parsed['firing_started_at']) is not None


def test_cli_exits_zero_on_a_full_run(
    git_repo: Path, lessons_dir: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Arrange
    _commit(git_repo, {_ALPHA_STANDARD: 'rule v1\n'})
    _seed_corpus(lessons_dir)
    _patch_status(monkeypatch, _status_with(None))

    # Act
    exit_code, parsed = _run_cli(monkeypatch, capsys, git_repo)

    # Assert
    assert exit_code == 0
    assert parsed['mode'] == _mod.MODE_FULL
    assert parsed['reason'] == _mod.FULL_FIRST_FIRING
    assert 'affected' not in parsed
