#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Tests for the ``add`` subcommand of manage-lessons.py.

Covers:

* ``cmd_add`` CLI plumbing via subprocess (TestCliPlumbingAdd)
* ``status=active`` frontmatter seeding on add (TestStatusFrontmatterOnAdd)
* Collision-safe id allocation in ``cmd_add`` / ``cmd_from_error``
  ``_allocate_and_write_scaffold`` helper that both subcommands share;
  ``cmd_from_error`` is exercised in one regression test to pin the shared
  contract rather than be split across files.
"""


import json
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch
import file_ops
from _lessons_helpers import (
    SCRIPT_PATH,
    _FakeDatetime,
    _mod,
    cmd_add,
    cmd_from_error,
    get_next_id,
)
from conftest import run_script


# =============================================================================
# Tier 2: cmd_from_error input validation (non-dict context, non-string component)
# =============================================================================


class TestFromErrorInputValidation:
    """Regression guard for ``cmd_from_error`` untrusted-JSON validation.

    ``args.context`` is parsed with ``json.loads`` and previously used
    ``context.get(...)`` unchecked, so a valid JSON array or scalar (e.g.
    ``"[]"``) crashed with ``AttributeError`` instead of a structured error, and
    a non-string ``component`` (explicit null / numeric) crashed inside
    ``guard_component_store_match``. The guards now reject a non-dict context and
    coerce a non-string component to ``'unknown'``.
    """

    def test_non_dict_json_array_context_returns_structured_error(self, tmp_path):
        """A JSON array parses cleanly but is not a dict — reject with invalid_json."""
        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_from_error(Namespace(context='[]'))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_json'
        assert result['message'] == 'Context must be a valid JSON object'

    def test_non_dict_json_scalar_context_returns_structured_error(self, tmp_path):
        """A JSON scalar (number) is not a dict — reject with invalid_json."""
        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_from_error(Namespace(context='42'))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_json'
        assert result['message'] == 'Context must be a valid JSON object'

    def test_malformed_json_still_rejected(self, tmp_path):
        """Truly malformed JSON keeps returning the structured invalid_json error."""
        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_from_error(Namespace(context='{not valid'))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_json'
        assert result['message'] == 'Context must be a valid JSON object'

    def test_explicit_null_component_is_rejected_as_invalid(self, tmp_path):
        """An explicitly-supplied null component is malformed, not a request to default.

        It must not crash (the original concern) and must not be silently coerced to
        'unknown' either — coercion would make the guard's isinstance check
        unreachable from this path and file a lesson under a component the caller
        never supplied. Only an ABSENT component defaults; see
        `test_absent_component_defaults_to_unknown` for that path.
        """
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        error_context = json.dumps({'component': None, 'error': 'boom', 'solution': 'fix'})

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_from_error(Namespace(context=error_context))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_component'
        assert not list(lessons_dir.glob('*.md'))

    def test_numeric_component_is_rejected_as_invalid(self, tmp_path):
        """A numeric component is malformed for the same reason as an explicit null."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        error_context = json.dumps({'component': 7, 'error': 'boom'})

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_from_error(Namespace(context=error_context))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_component'
        assert not list(lessons_dir.glob('*.md'))

    def test_absent_component_defaults_to_unknown(self, tmp_path):
        """An ABSENT component still defaults to the prefix-less 'unknown' and succeeds."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        error_context = json.dumps({'error': 'boom', 'solution': 'fix'})

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_from_error(Namespace(context=error_context))

        assert result['status'] == 'success'
        assert result['created_from'] == 'error_context'
        lesson_path = next(lessons_dir.glob(f'{result["id"]}.md'))
        assert 'component=unknown' in lesson_path.read_text(encoding='utf-8')


# =============================================================================
# Tier 2: status frontmatter on new lessons
# =============================================================================


class TestStatusFrontmatterOnAdd:
    """``cmd_add`` and ``cmd_from_error`` must seed ``status=active``."""

    def test_add_writes_status_active(self, tmp_path):
        """Newly added lessons must include ``status=active`` in the metadata header."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_add(
                Namespace(
                    component='test-component',
                    category='bug',
                    title='Status Active Default',
                    bundle=None,
                )
            )

        assert result['status'] == 'success'
        content = Path(result['path']).read_text(encoding='utf-8')
        assert 'status=active' in content

    def test_from_error_writes_status_active(self, tmp_path):
        """Error-context lessons must include ``status=active`` in the metadata header."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        error_context = json.dumps({'component': 'cmpt', 'error': 'boom', 'solution': 'fix it'})

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_from_error(Namespace(context=error_context))

        assert result['status'] == 'success'
        # Locate the file by id in the lessons dir.
        lesson_path = next(lessons_dir.glob(f'{result["id"]}.md'))
        assert 'status=active' in lesson_path.read_text(encoding='utf-8')


# =============================================================================
# Tier 3: CLI plumbing (subprocess) - kept for end-to-end coverage
# =============================================================================


class TestCliPlumbingAdd:
    """Subprocess test for add subcommand CLI plumbing."""

    def test_cli_add_creates_lesson(self, tmp_path):
        """Should create a lesson via CLI and produce TOON output with an absolute path."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = run_script(
                SCRIPT_PATH,
                'add',
                '--component',
                'test-component',
                '--category',
                'bug',
                '--title',
                'Test Lesson',
            )

        assert result.success, f'Script failed: {result.stderr}'
        assert 'status: success' in result.stdout
        assert 'component: test-component' in result.stdout
        assert 'category: bug' in result.stdout
        assert 'path: ' in result.stdout
        assert 'file: ' not in result.stdout

    def test_cli_invalid_category_rejected_by_argparse(self, tmp_path):
        """Should reject invalid category at argparse level."""
        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = run_script(
                SCRIPT_PATH,
                'add',
                '--component',
                'test-component',
                '--category',
                'invalid-category',
                '--title',
                'Test',
            )

        assert not result.success
        assert 'invalid choice' in result.stderr

    def test_cli_detail_flag_rejected(self, tmp_path):
        """Should reject the legacy --detail flag at argparse level."""
        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = run_script(
                SCRIPT_PATH,
                'add',
                '--component',
                'test-component',
                '--category',
                'bug',
                '--title',
                'Test Lesson',
                '--detail',
                'Legacy inline body that must no longer be accepted',
            )

        assert not result.success
        assert 'unrecognized arguments' in result.stderr


# =============================================================================
# Tier 2: main-anchored lessons corpus via the shared utility (deliverable 3)
# =============================================================================


class TestLessonsCorpusMainAnchoring:
    """The lessons corpus resolves to the MAIN checkout via
    ``resolve_main_anchored_path`` regardless of caller cwd (deliverable 3).

    Audit finding: phase-5 ``execute-task`` records lessons with cwd pinned to a
    worktree. With the corpus main-anchored, a ``cmd_add`` from a worktree cwd
    lands the lesson under MAIN's ``lessons-learned``, NOT the worktree's empty
    corpus. The override-first branch keeps every PLAN_BASE_DIR-based test green.
    """

    def test_add_writes_lesson_under_main_base_from_worktree_cwd(self, tmp_path, monkeypatch):
        """``cmd_add`` from a worktree cwd lands the lesson under MAIN's corpus."""
        # PLAN_BASE_DIR = main-checkout stand-in; cwd pinned into a
        # worktree fixture that owns its OWN .plan/local (empty corpus).
        main_base = tmp_path / 'main' / '.plan' / 'local'
        (main_base / 'lessons-learned').mkdir(parents=True)
        monkeypatch.setenv('PLAN_BASE_DIR', str(main_base))

        monkeypatch.setattr(file_ops, '_BASE_DIR_OVERRIDE', None)
        worktree = tmp_path / 'worktrees' / 'some-plan'
        (worktree / '.plan' / 'local' / 'lessons-learned').mkdir(parents=True)
        monkeypatch.chdir(worktree)

        result = cmd_add(
            Namespace(
                component='worktree-cwd-component',
                category='bug',
                title='Worktree-recorded Lesson',
                bundle=None,
            )
        )

        # the lesson landed under MAIN's lessons-learned, NOT the worktree.
        assert result['status'] == 'success'
        path = Path(result['path'])
        assert path.parent == (main_base / 'lessons-learned').resolve()
        assert path.exists()
        assert not list((worktree / '.plan' / 'local' / 'lessons-learned').glob('*.md'))
        # The corpus resolver itself anchors at MAIN regardless of cwd.
        assert _mod.get_lessons_dir() == (main_base / 'lessons-learned')

    def test_get_next_id_scans_main_plans_corpus_from_worktree_cwd(self, tmp_path, monkeypatch):
        """id-allocation scans MAIN's plans corpus, not the worktree's.

        Seeds a plan-derived lesson reserving sequence 001 under MAIN's corpus;
        from a worktree cwd ``get_next_id`` must clear that reservation and
        return ``-002``, proving the ``plans`` scan is main-anchored.
        """
        from datetime import UTC as real_utc
        from datetime import datetime as real_datetime

        main_base = tmp_path / 'main' / '.plan' / 'local'
        (main_base / 'lessons-learned').mkdir(parents=True)
        plan_dir = main_base / 'plans' / 'lesson-2025-01-01-02-001'
        plan_dir.mkdir(parents=True)
        (plan_dir / 'lesson-2025-01-01-02-001.md').write_text(
            'id=2025-01-01-02-001\ncomponent=x\ncategory=bug\ncreated=2025-01-01\n\n# converted\n'
        )
        monkeypatch.setenv('PLAN_BASE_DIR', str(main_base))

        monkeypatch.setattr(file_ops, '_BASE_DIR_OVERRIDE', None)
        worktree = tmp_path / 'worktrees' / 'some-plan'
        (worktree / '.plan' / 'local').mkdir(parents=True)
        monkeypatch.chdir(worktree)

        frozen = real_datetime(2025, 1, 1, 2, 30, 0, tzinfo=real_utc)
        monkeypatch.setattr(_mod, 'datetime', _FakeDatetime(frozen))

        next_id = get_next_id()

        # the main-anchored plans scan reserved 001 → next is 002.
        assert next_id == '2025-01-01-02-002'
