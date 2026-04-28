#!/usr/bin/env python3
"""
Tests for the manage-lessons.py script.

Tests subcommands:
- add: Create a new lesson
- get: Get a single lesson
- list: List lessons with filtering
- update: Update lesson metadata (component/category only)
- convert-to-plan: Move a lesson into a plan directory
- from-error: Create lesson from error context

Tier 2 (direct import) with 2 subprocess tests for CLI plumbing.
"""

import importlib.util
import json
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

import pytest

from conftest import MARKETPLACE_ROOT, ScriptTestCase, run_script

# Script path for remaining subprocess (CLI plumbing) tests
SCRIPT_PATH = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'manage-lessons' / 'scripts' / 'manage-lessons.py'
)

# Tier 2 direct imports - load hyphenated module via importlib
_MANAGE_LESSONS_SCRIPT = str(SCRIPT_PATH)
_spec = importlib.util.spec_from_file_location('manage_lessons', _MANAGE_LESSONS_SCRIPT)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

cmd_add = _mod.cmd_add
cmd_get = _mod.cmd_get
cmd_list = _mod.cmd_list
cmd_update = _mod.cmd_update
cmd_convert_to_plan = _mod.cmd_convert_to_plan
cmd_from_error = _mod.cmd_from_error
cmd_remove = _mod.cmd_remove
cmd_supersede = _mod.cmd_supersede
cmd_cleanup_superseded = _mod.cmd_cleanup_superseded
cmd_set_body = _mod.cmd_set_body
get_next_id = _mod.get_next_id


class _FakeDatetime:
    """Stand-in for ``datetime.datetime`` that returns a fixed aware ``now()``.

    The module under test calls ``datetime.now().astimezone()`` at the module
    level import ``from datetime import UTC, datetime``. Tests monkeypatch
    ``_mod.datetime`` with this fake so ID generation becomes deterministic
    regardless of the host timezone or wall clock.
    """

    def __init__(self, fixed_now):
        self._fixed_now = fixed_now

    def now(self, tz=None):  # noqa: D401 - mirrors datetime API
        if tz is None:
            # Strip tzinfo to mimic the naive ``datetime.now()`` behaviour so
            # the subsequent ``.astimezone()`` call attaches the local tz.
            return self._fixed_now.replace(tzinfo=None)
        return self._fixed_now.astimezone(tz)


# =============================================================================
# Tier 2: cmd_add
# =============================================================================


class TestCmdAdd:
    """Test cmd_add direct invocation."""

    def test_add_allocates_lesson_file_and_returns_path(self, tmp_path):
        """Should create a lesson file with metadata header + title and return its absolute path."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_add(
                Namespace(
                    component='test-component',
                    category='bug',
                    title='Test Lesson',
                    bundle=None,
                )
            )

        assert result['status'] == 'success'
        assert result['component'] == 'test-component'
        assert result['category'] == 'bug'
        assert 'id' in result
        assert 'path' in result

        path = Path(result['path'])
        assert path.is_absolute()
        assert path.parent == lessons_dir.resolve()
        assert path.exists()

        content = path.read_text(encoding='utf-8')
        assert f'id={result["id"]}' in content
        assert 'component=test-component' in content
        assert 'category=bug' in content
        assert '# Test Lesson' in content
        # Body is empty — the section after the title should be whitespace only
        body = content.split('# Test Lesson', 1)[1]
        assert body.strip() == ''

    def test_add_with_invalid_category_fails(self, tmp_path):
        """Should fail when using invalid category."""
        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_add(
                Namespace(
                    component='test-component',
                    category='invalid-category',
                    title='Test',
                    bundle=None,
                )
            )

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_category'

    def test_add_with_bundle_reference(self, tmp_path):
        """Should accept optional bundle reference and persist it in the metadata header."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_add(
                Namespace(
                    component='test-component',
                    category='improvement',
                    title='Test Lesson',
                    bundle='pm-dev-java',
                )
            )

        assert result['status'] == 'success'
        content = Path(result['path']).read_text(encoding='utf-8')
        assert 'bundle=pm-dev-java' in content


# =============================================================================
# Tier 2: cmd_list
# =============================================================================


class TestCmdList:
    """Test cmd_list direct invocation."""

    def test_list_empty_directory(self, tmp_path):
        """Should return empty list when no lessons exist."""
        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_list(Namespace(component=None, category=None, full=False))

        assert result['status'] == 'success'
        assert result['total'] == 0
        assert result['filtered'] == 0

    def test_list_with_lessons(self, tmp_path):
        """Should list existing lessons."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        lesson_content = """id=2025-01-01-001
component=test-component
category=bug
created=2025-01-01

# Test Lesson Title

This is the lesson body.
"""
        (lessons_dir / '2025-01-01-001.md').write_text(lesson_content)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_list(Namespace(component=None, category=None, full=False))

        assert result['status'] == 'success'
        assert result['total'] == 1
        assert result['filtered'] == 1

    def test_list_filter_by_component(self, tmp_path):
        """Should filter lessons by component."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        lesson1 = """id=2025-01-01-001
component=component-a
category=bug
created=2025-01-01

# Lesson A
"""
        lesson2 = """id=2025-01-01-002
component=component-b
category=bug
created=2025-01-01

# Lesson B
"""
        (lessons_dir / '2025-01-01-001.md').write_text(lesson1)
        (lessons_dir / '2025-01-01-002.md').write_text(lesson2)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_list(Namespace(component='component-a', category=None, full=False))

        assert result['status'] == 'success'
        assert result['total'] == 2
        assert result['filtered'] == 1

    def test_list_filter_by_category(self, tmp_path):
        """Should filter lessons by category."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        lesson1 = """id=2025-01-01-001
component=test
category=bug
created=2025-01-01

# Bug Lesson
"""
        lesson2 = """id=2025-01-01-002
component=test
category=improvement
created=2025-01-01

# Improvement Lesson
"""
        (lessons_dir / '2025-01-01-001.md').write_text(lesson1)
        (lessons_dir / '2025-01-01-002.md').write_text(lesson2)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_list(Namespace(component=None, category='bug', full=False))

        assert result['status'] == 'success'
        assert result['filtered'] == 1

    def test_list_full_includes_body_content(self, tmp_path):
        """Should include lesson body content when --full is set."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        lesson_content = """id=2025-01-01-001
component=test-component
category=bug
created=2025-01-01

# Test Lesson Title

This is the lesson body with details.
"""
        (lessons_dir / '2025-01-01-001.md').write_text(lesson_content)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_list(Namespace(component=None, category=None, full=True))

        assert result['status'] == 'success'
        assert result['filtered'] == 1
        assert 'content' in result['lessons'][0]
        assert 'This is the lesson body with details.' in result['lessons'][0]['content']

    def test_list_without_full_excludes_body(self, tmp_path):
        """Should not include body content without --full."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        lesson_content = """id=2025-01-01-001
component=test-component
category=bug
created=2025-01-01

# Test Lesson Title

Body content here.
"""
        (lessons_dir / '2025-01-01-001.md').write_text(lesson_content)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_list(Namespace(component=None, category=None, full=False))

        assert result['status'] == 'success'
        assert 'content' not in result['lessons'][0]


# =============================================================================
# Tier 2: cmd_get
# =============================================================================


class TestCmdGet:
    """Test cmd_get direct invocation."""

    def test_get_existing_lesson(self, tmp_path):
        """Should return lesson details."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        lesson_content = """id=2025-01-01-001
component=test-component
category=bug
created=2025-01-01

# Test Lesson Title

This is the lesson body.
"""
        (lessons_dir / '2025-01-01-001.md').write_text(lesson_content)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_get(Namespace(lesson_id='2025-01-01-001'))

        assert result['status'] == 'success'
        assert result['component'] == 'test-component'
        assert result['category'] == 'bug'
        assert result['title'] == 'Test Lesson Title'

    def test_get_nonexistent_lesson(self, tmp_path):
        """Should return error for non-existent lesson."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_get(Namespace(lesson_id='nonexistent-id'))

        assert result['status'] == 'error'
        assert result['error'] == 'not_found'


# =============================================================================
# Tier 2: cmd_update
# =============================================================================


class TestCmdUpdate:
    """Test cmd_update direct invocation."""

    def test_update_component(self, tmp_path):
        """Should update component field."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        lesson_content = """id=2025-01-01-001
component=old-component
category=bug
created=2025-01-01

# Test Lesson

Body.
"""
        (lessons_dir / '2025-01-01-001.md').write_text(lesson_content)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_update(
                Namespace(lesson_id='2025-01-01-001', component='new-component', category=None)
            )

        assert result['status'] == 'success'
        assert result['field'] == 'component'
        assert result['value'] == 'new-component'

        # Verify file was updated
        updated_content = (lessons_dir / '2025-01-01-001.md').read_text()
        assert 'component=new-component' in updated_content

    def test_update_nonexistent_lesson_fails(self, tmp_path):
        """Should fail when updating non-existent lesson."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_update(
                Namespace(lesson_id='nonexistent', component='x', category=None)
            )

        assert result['status'] == 'error'
        assert result['error'] == 'not_found'


# =============================================================================
# Tier 2: cmd_set_body
# =============================================================================


class TestCmdSetBody:
    """Test cmd_set_body direct invocation.

    ``cmd_set_body`` implements the path-allocate body-write flow's overwrite
    step: it preserves the ``key=value`` frontmatter and the H1 title verbatim
    while replacing everything after the H1 with the supplied body. The
    canonical input form is ``--file PATH`` (writes pass through the Write
    tool, not the shell); ``--content STRING`` exists as a secondary form for
    tiny payloads. Both forms share the TOON output shape
    ``{status, id, path, body_bytes_written}`` on success.
    """

    _STUB_TEMPLATE = (
        'id={lesson_id}\n'
        'component=test-component\n'
        'category=bug\n'
        'created=2025-01-01\n'
        '\n'
        '# {title}\n'
        '\n'
    )

    def _seed_stub(self, lessons_dir: Path, lesson_id: str, title: str = 'Stub Title') -> Path:
        """Create a fresh lesson stub mirroring the shape produced by ``cmd_add``."""
        path = lessons_dir / f'{lesson_id}.md'
        path.write_text(
            self._STUB_TEMPLATE.format(lesson_id=lesson_id, title=title),
            encoding='utf-8',
        )
        return path

    def test_set_body_with_file_input_overwrites_body(self, tmp_path):
        """``--file`` form must read the file and replace the lesson body.

        Seeds an empty stub, writes a multi-line markdown body to a sidecar
        file, and asserts the resulting lesson has the new body, the original
        frontmatter intact, and the success TOON shape with the byte count
        matching the body source's UTF-8 length.
        """
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        self._seed_stub(lessons_dir, '2025-01-01-02-001', 'My Lesson')

        body_file = tmp_path / 'body.md'
        body_text = '## Context\n\nMulti-line body with `code` and a list:\n\n- item one\n- item two\n'
        body_file.write_text(body_text, encoding='utf-8')

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_set_body(
                Namespace(
                    lesson_id='2025-01-01-02-001',
                    file=str(body_file),
                    content=None,
                )
            )

        assert result['status'] == 'success'
        assert result['id'] == '2025-01-01-02-001'
        assert Path(result['path']) == (lessons_dir / '2025-01-01-02-001.md').resolve()
        assert result['body_bytes_written'] == len(body_text.encode('utf-8'))

        updated = (lessons_dir / '2025-01-01-02-001.md').read_text(encoding='utf-8')
        # Body content present
        assert '## Context' in updated
        assert '- item one' in updated
        # Frontmatter and H1 still present
        assert 'id=2025-01-01-02-001' in updated
        assert 'component=test-component' in updated
        assert '# My Lesson' in updated

    def test_set_body_with_content_input_overwrites_body(self, tmp_path):
        """``--content`` form must use the inline string as the new body.

        This covers the secondary inline form used for tiny payloads. The
        function must return the same TOON shape as the ``--file`` form and
        the byte count must reflect the inline string's UTF-8 length.
        """
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        self._seed_stub(lessons_dir, '2025-01-01-02-001', 'Inline Lesson')

        inline_body = 'Short inline body.\n'

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_set_body(
                Namespace(
                    lesson_id='2025-01-01-02-001',
                    file=None,
                    content=inline_body,
                )
            )

        assert result['status'] == 'success'
        assert result['id'] == '2025-01-01-02-001'
        assert result['body_bytes_written'] == len(inline_body.encode('utf-8'))

        updated = (lessons_dir / '2025-01-01-02-001.md').read_text(encoding='utf-8')
        assert 'Short inline body.' in updated
        assert '# Inline Lesson' in updated

    def test_set_body_missing_lesson_returns_not_found(self, tmp_path):
        """Calling ``cmd_set_body`` against a non-existent stub must error out.

        The stub-existence check runs before any body source is read, so the
        error code is ``not_found`` regardless of which input form was used.
        """
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_set_body(
                Namespace(
                    lesson_id='nonexistent-id',
                    file=None,
                    content='whatever',
                )
            )

        assert result['status'] == 'error'
        assert result['error'] == 'not_found'
        assert result['id'] == 'nonexistent-id'

    def test_set_body_rejects_neither_or_both_inputs(self, tmp_path):
        """Mutual-exclusion guard must reject both-supplied and neither-supplied calls.

        The CLI layer enforces ``--file`` vs. ``--content`` exclusivity via
        argparse's ``add_mutually_exclusive_group(required=True)``, but the
        underlying function still guards against direct programmatic misuse —
        both branches must return ``invalid_input``. We check the
        neither-supplied branch (both ``None``) and the both-supplied branch
        because the implementation uses ``(file is None) == (content is None)``,
        which catches both shapes with one comparison.
        """
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        self._seed_stub(lessons_dir, '2025-01-01-02-001')

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            neither_result = cmd_set_body(
                Namespace(
                    lesson_id='2025-01-01-02-001',
                    file=None,
                    content=None,
                )
            )
            both_result = cmd_set_body(
                Namespace(
                    lesson_id='2025-01-01-02-001',
                    file='/tmp/some-file.md',
                    content='inline body',
                )
            )

        assert neither_result['status'] == 'error'
        assert neither_result['error'] == 'invalid_input'
        assert both_result['status'] == 'error'
        assert both_result['error'] == 'invalid_input'

    def test_set_body_with_directory_path_returns_file_not_found(self, tmp_path):
        """``--file`` form must reject a path that is a directory, not a regular file.

        Mirrors the ``_tasks_crud.py`` ``--tasks-file`` guard: ``Path.is_file()``
        is stricter than ``Path.exists()`` and rejects directories, broken
        symlinks, and special files. The error code must be ``file_not_found``
        and the message must surface the offending path so callers can react.
        """
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        self._seed_stub(lessons_dir, '2025-01-01-02-001', 'Dir Test')

        # A directory exists at this path — ``Path.exists()`` would return True
        # but ``is_file()`` returns False, which the guard must surface as
        # ``file_not_found`` rather than crashing in ``read_text``.
        bogus_dir = tmp_path / 'not-a-file-dir'
        bogus_dir.mkdir()

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_set_body(
                Namespace(
                    lesson_id='2025-01-01-02-001',
                    file=str(bogus_dir),
                    content=None,
                )
            )

        assert result['status'] == 'error'
        assert result['error'] == 'file_not_found'
        assert result['id'] == '2025-01-01-02-001'
        assert str(bogus_dir) in result['message']

    def test_set_body_with_unreadable_file_returns_file_read_error(self, tmp_path):
        """``--file`` form must surface ``OSError`` from ``read_text`` as ``file_read_error``.

        Simulates a transient I/O failure (permission flip, EIO, vanished mount)
        by monkeypatching ``Path.read_text`` to raise ``PermissionError`` (an
        ``OSError`` subclass). The guard must trap the exception, leave the
        target lesson stub on disk untouched, and return a structured error
        payload with ``error: file_read_error`` and the offending path
        reflected in the message — never let the exception propagate.
        """
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        stub_path = self._seed_stub(lessons_dir, '2025-01-01-02-001', 'Read Error Test')
        stub_content_before = stub_path.read_text(encoding='utf-8')

        body_file = tmp_path / 'body.md'
        body_file.write_text('Body that cannot be read.', encoding='utf-8')

        original_read_text = Path.read_text

        def _raising_read_text(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            # Only raise for the body source; allow reads on the lesson stub
            # (the function reads the original lesson via ``target.read_text``
            # AFTER the body source). We restrict to the exact body file path.
            if self == body_file:
                raise PermissionError('simulated read failure')
            return original_read_text(self, *args, **kwargs)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}), \
                patch.object(Path, 'read_text', _raising_read_text):
            result = cmd_set_body(
                Namespace(
                    lesson_id='2025-01-01-02-001',
                    file=str(body_file),
                    content=None,
                )
            )

        assert result['status'] == 'error'
        assert result['error'] == 'file_read_error'
        assert result['id'] == '2025-01-01-02-001'
        assert str(body_file) in result['message']
        # The lesson stub on disk must be untouched — the failure happened
        # before the rewrite stage, so no atomic write should have run.
        assert stub_path.read_text(encoding='utf-8') == stub_content_before

    def test_set_body_preserves_frontmatter_across_overwrite(self, tmp_path):
        """Frontmatter block and H1 title must survive a body overwrite verbatim.

        Seeds a stub with a richer frontmatter (including an optional
        ``bundle`` field) and a populated body, runs ``cmd_set_body`` to
        replace the body, and asserts:

        * Every original frontmatter line is present in the rewritten file in
          its original order.
        * The H1 title line is unchanged.
        * The original body content is gone — i.e. the overwrite is a true
          replacement, not an append.
        * The new body is present.
        """
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        original_lesson = (
            'id=2025-01-01-02-001\n'
            'component=preserved-component\n'
            'category=improvement\n'
            'bundle=pm-dev-java\n'
            'created=2025-01-01\n'
            '\n'
            '# Preserved Title\n'
            '\n'
            'Original body that must be discarded.\n'
            'Second line of original body.\n'
        )
        target = lessons_dir / '2025-01-01-02-001.md'
        target.write_text(original_lesson, encoding='utf-8')

        new_body = 'Replacement body — original lines must be gone.\n'

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_set_body(
                Namespace(
                    lesson_id='2025-01-01-02-001',
                    file=None,
                    content=new_body,
                )
            )

        assert result['status'] == 'success'

        rewritten = target.read_text(encoding='utf-8')

        # Frontmatter lines preserved verbatim, in order.
        rewritten_lines = rewritten.split('\n')
        for expected in (
            'id=2025-01-01-02-001',
            'component=preserved-component',
            'category=improvement',
            'bundle=pm-dev-java',
            'created=2025-01-01',
        ):
            assert expected in rewritten_lines, f'frontmatter line missing: {expected}'

        # Frontmatter ordering preserved (header lines appear before the H1).
        h1_index = rewritten_lines.index('# Preserved Title')
        for expected in (
            'id=2025-01-01-02-001',
            'component=preserved-component',
            'category=improvement',
            'bundle=pm-dev-java',
            'created=2025-01-01',
        ):
            assert rewritten_lines.index(expected) < h1_index

        # Original body is gone — the overwrite is a replacement, not an append.
        assert 'Original body that must be discarded.' not in rewritten
        assert 'Second line of original body.' not in rewritten

        # New body is present.
        assert 'Replacement body' in rewritten


# =============================================================================
# Tier 2: cmd_convert_to_plan
# =============================================================================


class TestCmdConvertToPlan:
    """Test cmd_convert_to_plan direct invocation."""

    def test_convert_to_plan_moves_file(self, tmp_path):
        """Should move lesson file from lessons-learned into plan directory."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        lesson_content = """id=2025-01-01-001
component=test-component
category=bug
created=2025-01-01

# Test Lesson

Body content here.
"""
        source = lessons_dir / '2025-01-01-001.md'
        source.write_text(lesson_content)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_convert_to_plan(
                Namespace(lesson_id='2025-01-01-001', plan_id='my-plan')
            )

        assert result['status'] == 'success'
        assert result['lesson_id'] == '2025-01-01-001'
        assert result['plan_id'] == 'my-plan'

        # Source file no longer exists
        assert not source.exists()

        # Destination exists with identical content
        destination = tmp_path / 'plans' / 'my-plan' / 'lesson-2025-01-01-001.md'
        assert destination.exists()
        assert destination.read_text() == lesson_content

    def test_convert_to_plan_missing_source(self, tmp_path):
        """Should return error when source lesson does not exist."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_convert_to_plan(
                Namespace(lesson_id='nonexistent-id', plan_id='my-plan')
            )

        assert result['status'] == 'error'
        assert result['error'] == 'not_found'

    def test_convert_to_plan_creates_plan_dir_if_missing(self, tmp_path):
        """Should create the plan directory on the fly when it does not exist."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        lesson_content = """id=2025-01-01-001
component=test-component
category=bug
created=2025-01-01

# Test Lesson

Body.
"""
        (lessons_dir / '2025-01-01-001.md').write_text(lesson_content)

        plan_dir = tmp_path / 'plans' / 'fresh-plan'
        assert not plan_dir.exists()

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_convert_to_plan(
                Namespace(lesson_id='2025-01-01-001', plan_id='fresh-plan')
            )

        assert result['status'] == 'success'
        assert plan_dir.exists()
        assert (plan_dir / 'lesson-2025-01-01-001.md').exists()

    def test_convert_to_plan_rejects_path_traversal(self, tmp_path):
        """Should reject identifiers containing path separators or traversal sequences."""
        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            for bad_id in ('../escape', 'sub/dir', 'back\\slash'):
                result = cmd_convert_to_plan(
                    Namespace(lesson_id=bad_id, plan_id='p')
                )
                assert result['status'] == 'error'
                assert result['error'] == 'invalid_id'

            for bad_plan in ('../escape', 'sub/dir', 'back\\slash'):
                result = cmd_convert_to_plan(
                    Namespace(lesson_id='good-id', plan_id=bad_plan)
                )
                assert result['status'] == 'error'
                assert result['error'] == 'invalid_id'


# =============================================================================
# Tier 2: cmd_from_error
# =============================================================================


class TestCmdFromError:
    """Test cmd_from_error direct invocation."""

    def test_from_error_creates_lesson(self, tmp_path):
        """Should create lesson from error context JSON."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        error_context = json.dumps(
            {
                'component': 'maven-build',
                'error': 'Build failed due to missing dependency',
                'solution': 'Add the missing dependency to pom.xml',
            }
        )

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_from_error(Namespace(context=error_context))

        assert result['status'] == 'success'
        assert result['created_from'] == 'error_context'

    def test_from_error_invalid_json_fails(self, tmp_path):
        """Should fail with invalid JSON context."""
        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_from_error(Namespace(context='not valid json'))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_json'


# =============================================================================
# Tier 2: get_next_id (hour-aware ID generation)
# =============================================================================


class TestGetNextIdHourAware:
    """Deterministic tests for hour-aware ID generation in ``get_next_id``."""

    def test_get_next_id_resets_per_hour(self, tmp_path, monkeypatch):
        """Counter must reset to 001 when the hour changes.

        Seeds the lessons dir with a lesson from hour 01, freezes ``datetime.now``
        to a local-aware instant at ``2025-01-01 02:15:00``, then asserts that
        ``get_next_id`` returns ``2025-01-01-02-001`` — the hour prefix rolls
        forward and the sequence number resets because no prior lesson exists
        for hour 02.
        """
        from datetime import datetime as real_datetime

        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        # Legacy-format-for-hour-scheme fixture from hour 01.
        (lessons_dir / '2025-01-01-01-001.md').write_text(
            'id=2025-01-01-01-001\ncomponent=x\ncategory=bug\ncreated=2025-01-01\n\n# seed\n'
        )

        frozen = real_datetime(2025, 1, 1, 2, 15, 0)
        monkeypatch.setattr(_mod, 'datetime', _FakeDatetime(frozen))

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            next_id = get_next_id()

        assert next_id == '2025-01-01-02-001'

    def test_get_next_id_increments_within_same_hour(self, tmp_path, monkeypatch):
        """Sequence number must increment when multiple lessons share an hour."""
        from datetime import datetime as real_datetime

        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        (lessons_dir / '2025-01-01-02-001.md').write_text(
            'id=2025-01-01-02-001\ncomponent=x\ncategory=bug\ncreated=2025-01-01\n\n# seed\n'
        )

        frozen = real_datetime(2025, 1, 1, 2, 30, 0)
        monkeypatch.setattr(_mod, 'datetime', _FakeDatetime(frozen))

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            next_id = get_next_id()

        assert next_id == '2025-01-01-02-002'

    def test_get_next_id_ignores_legacy_ids_when_computing_hour_sequence(self, tmp_path, monkeypatch):
        """Legacy ``YYYY-MM-DD-NNN`` files must not collide with a new hour prefix.

        Seeds a legacy lesson ``2025-01-01-005.md`` (no hour segment), freezes
        ``now`` to hour 03, and asserts ``get_next_id`` returns ``2025-01-01-03-001``
        rather than reading the legacy counter. The legacy file must remain
        on disk untouched — this test only covers the generation path.
        """
        from datetime import datetime as real_datetime

        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        legacy_path = lessons_dir / '2025-01-01-005.md'
        legacy_content = (
            'id=2025-01-01-005\ncomponent=x\ncategory=bug\ncreated=2025-01-01\n\n# legacy seed\n'
        )
        legacy_path.write_text(legacy_content)

        frozen = real_datetime(2025, 1, 1, 3, 0, 0)
        monkeypatch.setattr(_mod, 'datetime', _FakeDatetime(frozen))

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            next_id = get_next_id()

        assert next_id == '2025-01-01-03-001'
        # Legacy file remains readable and untouched.
        assert legacy_path.exists()
        assert legacy_path.read_text() == legacy_content


# =============================================================================
# Tier 2: legacy-format compatibility (read paths)
# =============================================================================


class TestLegacyFormatCompatibility:
    """Legacy ``YYYY-MM-DD-NNN`` lessons must remain readable through read APIs."""

    def test_legacy_ids_remain_readable_and_listable(self, tmp_path):
        """``cmd_get`` and ``cmd_list`` must surface legacy-format lessons.

        Seeds the lessons dir with a legacy ``2025-01-01-001.md`` fixture (the
        pre-hour-aware filename layout) and asserts:

        * ``cmd_get(lesson_id='2025-01-01-001')`` returns ``status: success`` and
          surfaces the metadata fields intact.
        * ``cmd_list`` enumerates the legacy entry alongside any hour-aware
          entries and does not drop it.
        """
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        legacy_content = """id=2025-01-01-001
component=legacy-component
category=improvement
created=2025-01-01

# Legacy Lesson Title

Legacy body content.
"""
        (lessons_dir / '2025-01-01-001.md').write_text(legacy_content)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            get_result = cmd_get(Namespace(lesson_id='2025-01-01-001'))
            list_result = cmd_list(Namespace(component=None, category=None, full=False))

        # cmd_get surfaces the legacy entry with full metadata.
        assert get_result['status'] == 'success'
        assert get_result['id'] == '2025-01-01-001'
        assert get_result['component'] == 'legacy-component'
        assert get_result['category'] == 'improvement'
        assert get_result['title'] == 'Legacy Lesson Title'

        # cmd_list enumerates the legacy file.
        assert list_result['status'] == 'success'
        assert list_result['total'] == 1
        assert list_result['filtered'] == 1
        listed_ids = [entry['id'] for entry in list_result['lessons']]
        assert '2025-01-01-001' in listed_ids

    def test_legacy_and_hour_aware_ids_coexist_in_list(self, tmp_path):
        """``cmd_list`` must enumerate both legacy and hour-aware lessons together."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        (lessons_dir / '2025-01-01-001.md').write_text(
            'id=2025-01-01-001\ncomponent=a\ncategory=bug\ncreated=2025-01-01\n\n# Legacy\n'
        )
        (lessons_dir / '2025-01-01-02-001.md').write_text(
            'id=2025-01-01-02-001\ncomponent=b\ncategory=bug\ncreated=2025-01-01\n\n# Hour-aware\n'
        )

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_list(Namespace(component=None, category=None, full=False))

        assert result['status'] == 'success'
        assert result['total'] == 2
        assert result['filtered'] == 2
        listed_ids = {entry['id'] for entry in result['lessons']}
        assert '2025-01-01-001' in listed_ids
        assert '2025-01-01-02-001' in listed_ids


# =============================================================================
# Tier 2: Collision-safe id allocation in cmd_add and cmd_from_error
# =============================================================================


class TestCollisionSafeAllocation:
    """Regression tests for collision-safe lesson id allocation.

    The original ``cmd_add`` / ``cmd_from_error`` allocated an id via
    ``get_next_id()`` and wrote unconditionally — which silently overwrote any
    existing lesson file when ``get_next_id`` returned a colliding id (e.g.
    after a stale-cache filesystem read or a concurrent caller). The
    collision-safe helper uses ``open(path, "x")`` (kernel-enforced exclusive
    create) with a bounded retry of 99 attempts, logs a WARNING per collision to
    ``script-execution.log``, and returns ``error: id_exhausted`` on
    exhaustion. These tests pin that contract.
    """

    def _seed_existing_lesson(self, lessons_dir: Path, lesson_id: str, marker: str) -> Path:
        """Create a sentinel lesson file the new allocation must NOT overwrite.

        Returns the path so callers can assert the file's content is preserved.
        """
        path = lessons_dir / f'{lesson_id}.md'
        path.write_text(
            f'id={lesson_id}\ncomponent=existing\ncategory=bug\ncreated=2025-01-01\n\n'
            f'# {marker}\n',
            encoding='utf-8',
        )
        return path

    def test_add_does_not_overwrite_on_id_collision(self, tmp_path, monkeypatch):
        """``cmd_add`` must allocate a fresh id when the candidate already exists.

        Pre-creates a file at ``2025-01-01-02-001.md`` (the id ``get_next_id``
        would naively return for the frozen clock), runs ``cmd_add``, and
        asserts the new lesson lands at ``-002`` while the seeded ``-001`` file
        is byte-for-byte unchanged.
        """
        from datetime import datetime as real_datetime

        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        seeded = self._seed_existing_lesson(lessons_dir, '2025-01-01-02-001', 'Existing Lesson')
        seeded_content = seeded.read_text(encoding='utf-8')

        frozen = real_datetime(2025, 1, 1, 2, 30, 0)
        monkeypatch.setattr(_mod, 'datetime', _FakeDatetime(frozen))
        # Force ``get_next_id`` to collide with the seeded file regardless of
        # the directory listing — keeps the test focused on the collision
        # branch in ``_allocate_and_write_scaffold``.
        monkeypatch.setattr(_mod, 'get_next_id', lambda: '2025-01-01-02-001')

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_add(
                Namespace(
                    component='new-component',
                    category='improvement',
                    title='Fresh Lesson',
                    bundle=None,
                )
            )

        assert result['status'] == 'success'
        assert result['id'] == '2025-01-01-02-002'
        # Seeded file untouched.
        assert seeded.read_text(encoding='utf-8') == seeded_content
        # Fresh lesson written at the next sequential id.
        fresh_path = Path(result['path'])
        assert fresh_path == (lessons_dir / '2025-01-01-02-002.md').resolve()
        assert fresh_path.exists()
        assert '# Fresh Lesson' in fresh_path.read_text(encoding='utf-8')

    def test_add_logs_warning_on_collision(self, tmp_path, monkeypatch):
        """A ``[WARNING] id_collision`` line must be appended to ``script-execution.log``.

        The exact format documented in the helper docstring is
        ``[WARNING] (plan-marshall:manage-lessons) id_collision at {path} —
        retrying with seq+1`` — this test pins the message substring rather
        than the full line so the timestamp/hash prefix from
        ``format_log_entry`` does not couple the assertion.
        """
        from datetime import datetime as real_datetime

        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        self._seed_existing_lesson(lessons_dir, '2025-01-01-02-001', 'Seed')

        frozen = real_datetime(2025, 1, 1, 2, 30, 0)
        monkeypatch.setattr(_mod, 'datetime', _FakeDatetime(frozen))
        monkeypatch.setattr(_mod, 'get_next_id', lambda: '2025-01-01-02-001')

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            cmd_add(
                Namespace(
                    component='new-component',
                    category='bug',
                    title='Fresh Lesson',
                    bundle=None,
                )
            )

            # ``log_entry`` writes to the global script-execution log because
            # we pass ``plan_id=None``. Path resolution mirrors
            # ``plan_logging.get_log_path(None, 'script')``.
            log_files = list((tmp_path / 'logs').glob('script-execution-*.log'))

        assert log_files, 'expected at least one script-execution log file'
        log_text = '\n'.join(p.read_text(encoding='utf-8') for p in log_files)
        assert '[WARNING]' in log_text
        assert '(plan-marshall:manage-lessons) id_collision' in log_text
        assert '2025-01-01-02-001.md' in log_text
        assert 'retrying with seq+1' in log_text

    def test_from_error_does_not_overwrite_on_id_collision(self, tmp_path, monkeypatch):
        """Parallel collision test for ``cmd_from_error`` — must allocate a fresh id."""
        from datetime import datetime as real_datetime

        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        seeded = self._seed_existing_lesson(lessons_dir, '2025-01-01-02-001', 'Existing')
        seeded_content = seeded.read_text(encoding='utf-8')

        frozen = real_datetime(2025, 1, 1, 2, 30, 0)
        monkeypatch.setattr(_mod, 'datetime', _FakeDatetime(frozen))
        monkeypatch.setattr(_mod, 'get_next_id', lambda: '2025-01-01-02-001')

        error_context = json.dumps(
            {
                'component': 'maven-build',
                'error': 'Build failed',
                'solution': 'Add missing dependency',
            }
        )

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_from_error(Namespace(context=error_context))

        assert result['status'] == 'success'
        assert result['created_from'] == 'error_context'
        assert result['id'] == '2025-01-01-02-002'
        # Seeded file untouched — the bug under test was silent overwrite.
        assert seeded.read_text(encoding='utf-8') == seeded_content
        # Fresh from-error lesson exists at the next sequential id with the
        # error scaffold body.
        fresh_path = lessons_dir / '2025-01-01-02-002.md'
        assert fresh_path.exists()
        fresh_content = fresh_path.read_text(encoding='utf-8')
        assert '## Error' in fresh_content
        assert 'Build failed' in fresh_content

    def test_add_raises_id_exhausted_after_99_collisions(self, tmp_path, monkeypatch):
        """After ``MAX_ID_ALLOCATION_RETRIES`` collisions ``cmd_add`` must error.

        Pre-creates 99 colliding files at ``-001`` through ``-099``, forces
        ``get_next_id`` to return ``-001`` so every retry hits ``FileExistsError``,
        and asserts ``cmd_add`` returns ``status: error`` / ``error: id_exhausted``
        rather than silently overwriting ``-099`` (the original bug) or escaping
        the bound.
        """
        from datetime import datetime as real_datetime

        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        seeded_content_by_id = {}
        for seq in range(1, 100):
            lesson_id = f'2025-01-01-02-{seq:03d}'
            path = self._seed_existing_lesson(lessons_dir, lesson_id, f'Seed {seq}')
            seeded_content_by_id[lesson_id] = path.read_text(encoding='utf-8')

        frozen = real_datetime(2025, 1, 1, 2, 30, 0)
        monkeypatch.setattr(_mod, 'datetime', _FakeDatetime(frozen))
        monkeypatch.setattr(_mod, 'get_next_id', lambda: '2025-01-01-02-001')

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_add(
                Namespace(
                    component='new-component',
                    category='bug',
                    title='Fresh Lesson',
                    bundle=None,
                )
            )

        assert result['status'] == 'error'
        assert result['error'] == 'id_exhausted'
        # No seeded file was overwritten — the bug under test was silent
        # clobber of ``-099`` once the retry budget was exhausted.
        for lesson_id, original in seeded_content_by_id.items():
            current = (lessons_dir / f'{lesson_id}.md').read_text(encoding='utf-8')
            assert current == original, f'lesson {lesson_id} was overwritten'


# =============================================================================
# Tier 3: CLI plumbing (subprocess) - kept for end-to-end coverage
# =============================================================================


class TestCliPlumbingAdd(ScriptTestCase):
    """Subprocess test for add subcommand CLI plumbing."""

    bundle = 'plan-marshall'
    skill = 'manage-lessons'
    script = 'manage-lessons.py'

    def test_cli_add_creates_lesson(self):
        """Should create a lesson via CLI and produce TOON output with an absolute path."""
        lessons_dir = self.temp_dir / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(self.temp_dir)}):
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

        self.assert_success(result)
        self.assertIn('status: success', result.stdout)
        self.assertIn('component: test-component', result.stdout)
        self.assertIn('category: bug', result.stdout)
        self.assertIn('path: ', result.stdout)
        self.assertNotIn('file: ', result.stdout)

    def test_cli_invalid_category_rejected_by_argparse(self):
        """Should reject invalid category at argparse level."""
        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(self.temp_dir)}):
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

        self.assert_failure(result)
        self.assertIn('invalid choice', result.stderr)

    def test_cli_detail_flag_rejected(self):
        """Should reject the legacy --detail flag at argparse level."""
        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(self.temp_dir)}):
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

        self.assert_failure(result)
        self.assertIn('unrecognized arguments', result.stderr)


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
# Tier 2: cmd_list --status filter
# =============================================================================


def _seed_lesson_with_status(
    lessons_dir: Path, lesson_id: str, status: str | None, title: str
) -> Path:
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


class TestCmdListStatusFilter:
    """``cmd_list --status`` filter behaviour."""

    def _seed_three_statuses(self, lessons_dir: Path) -> None:
        _seed_lesson_with_status(lessons_dir, '2025-01-01-01-001', 'active', 'Active Lesson')
        _seed_lesson_with_status(lessons_dir, '2025-01-01-01-002', 'superseded', 'Superseded Lesson')
        _seed_lesson_with_status(lessons_dir, '2025-01-01-01-003', None, 'Legacy No Status')

    def test_default_excludes_superseded(self, tmp_path):
        """Default filter (``status=active``) hides superseded lessons; absent status treated as active."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        self._seed_three_statuses(lessons_dir)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_list(
                Namespace(component=None, category=None, status='active', full=False)
            )

        assert result['status'] == 'success'
        listed_ids = {entry['id'] for entry in result['lessons']}
        assert '2025-01-01-01-001' in listed_ids
        assert '2025-01-01-01-003' in listed_ids  # absent status ⇒ active
        assert '2025-01-01-01-002' not in listed_ids  # superseded hidden

    def test_status_all_returns_every_lesson(self, tmp_path):
        """``--status all`` returns every lesson regardless of lifecycle status."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        self._seed_three_statuses(lessons_dir)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_list(
                Namespace(component=None, category=None, status='all', full=False)
            )

        listed_ids = {entry['id'] for entry in result['lessons']}
        assert listed_ids == {
            '2025-01-01-01-001',
            '2025-01-01-01-002',
            '2025-01-01-01-003',
        }

    def test_status_superseded_returns_only_superseded(self, tmp_path):
        """``--status superseded`` returns only lessons with frontmatter ``status=superseded``."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        self._seed_three_statuses(lessons_dir)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_list(
                Namespace(component=None, category=None, status='superseded', full=False)
            )

        listed_ids = {entry['id'] for entry in result['lessons']}
        assert listed_ids == {'2025-01-01-01-002'}

    def test_legacy_namespace_without_status_attr_defaults_to_active(self, tmp_path):
        """Backwards compatibility: a Namespace without a ``status`` attribute must default to ``active``."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        self._seed_three_statuses(lessons_dir)

        # Legacy Namespace without status field — older callers must still work.
        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_list(Namespace(component=None, category=None, full=False))

        listed_ids = {entry['id'] for entry in result['lessons']}
        assert '2025-01-01-01-002' not in listed_ids  # superseded still hidden
        assert '2025-01-01-01-001' in listed_ids


# =============================================================================
# Tier 2: cmd_remove
# =============================================================================


class TestCmdRemove:
    """``cmd_remove`` deletes the lesson, writes a tombstone, and logs an audit entry."""

    def _seed_lesson(self, lessons_dir: Path, lesson_id: str = '2025-01-01-01-001') -> Path:
        content = (
            f'id={lesson_id}\n'
            'component=test\n'
            'category=bug\n'
            'status=active\n'
            'created=2025-01-01\n\n'
            f'# {lesson_id} Title\n\nBody.\n'
        )
        path = lessons_dir / f'{lesson_id}.md'
        path.write_text(content, encoding='utf-8')
        return path

    def test_remove_force_deletes_file_and_writes_tombstone(self, tmp_path):
        """``--force`` skips the prompt; the lesson file is deleted and a tombstone is written."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        seeded = self._seed_lesson(lessons_dir)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_remove(
                Namespace(
                    lesson_id='2025-01-01-01-001',
                    reason='duplicate of 2025-01-02-01-001',
                    force=True,
                )
            )

        assert result['status'] == 'success'
        assert result['id'] == '2025-01-01-01-001'
        assert result['reason'] == 'duplicate of 2025-01-02-01-001'

        # Lesson file is gone.
        assert not seeded.exists()

        # Tombstone exists with the expected payload.
        tombstone_path = lessons_dir / '.tombstones' / '2025-01-01-01-001.json'
        assert tombstone_path.exists()
        payload = json.loads(tombstone_path.read_text(encoding='utf-8'))
        assert payload['lesson_id'] == '2025-01-01-01-001'
        assert payload['reason'] == 'duplicate of 2025-01-02-01-001'
        assert payload['status'] == 'removed'
        assert 'removed_at' in payload
        assert 'superseded_by' not in payload

    def test_remove_unknown_lesson_returns_not_found(self, tmp_path):
        """Removing a lesson that does not exist returns ``error: not_found``."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_remove(
                Namespace(lesson_id='nope', reason='gone', force=True)
            )

        assert result['status'] == 'error'
        assert result['error'] == 'not_found'

    def test_remove_declined_via_input_keeps_file(self, tmp_path, monkeypatch):
        """Without ``--force``, an answer other than ``y/yes`` cancels removal."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        seeded = self._seed_lesson(lessons_dir)

        # Stub builtins.input on the manage-lessons module to simulate "no".
        # The remove subcommand writes the prompt to stderr separately, then
        # calls input() with no arguments — so the stub takes none.
        monkeypatch.setattr(_mod, 'input', lambda: 'n', raising=False)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_remove(
                Namespace(lesson_id='2025-01-01-01-001', reason='maybe', force=False)
            )

        assert result['status'] == 'cancelled'
        # File preserved.
        assert seeded.exists()
        # No tombstone written.
        tombstone_path = lessons_dir / '.tombstones' / '2025-01-01-01-001.json'
        assert not tombstone_path.exists()

    def test_remove_logs_audit_entry(self, tmp_path):
        """``cmd_remove --force`` emits an INFO audit entry to script-execution.log."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        self._seed_lesson(lessons_dir)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            cmd_remove(
                Namespace(
                    lesson_id='2025-01-01-01-001',
                    reason='dedup',
                    force=True,
                )
            )

            log_files = list((tmp_path / 'logs').glob('script-execution-*.log'))

        assert log_files, 'expected at least one script-execution log file'
        log_text = '\n'.join(p.read_text(encoding='utf-8') for p in log_files)
        assert '[INFO]' in log_text
        assert '(plan-marshall:manage-lessons) Removed lesson 2025-01-01-01-001' in log_text
        assert 'dedup' in log_text


# =============================================================================
# Tier 2: cmd_supersede
# =============================================================================


class TestCmdSupersede:
    """``cmd_supersede`` redirects a lesson to a canonical and updates both files."""

    def _seed_pair(self, lessons_dir: Path, with_consolidated_section: bool = False) -> tuple[Path, Path]:
        source = lessons_dir / '2025-01-01-01-001.md'
        source.write_text(
            'id=2025-01-01-01-001\n'
            'component=test\n'
            'category=bug\n'
            'status=active\n'
            'created=2025-01-01\n\n'
            '# Source Lesson\n\nSource body content.\n',
            encoding='utf-8',
        )
        canonical_body = '# Canonical Lesson\n\nCanonical body content.\n'
        if with_consolidated_section:
            canonical_body = (
                '# Canonical Lesson\n\nCanonical body content.\n\n'
                '## Consolidated from\n\n- 2024-12-31-23-099\n'
            )
        canonical = lessons_dir / '2025-01-02-01-001.md'
        canonical.write_text(
            'id=2025-01-02-01-001\n'
            'component=test\n'
            'category=bug\n'
            'status=active\n'
            'created=2025-01-02\n\n' + canonical_body,
            encoding='utf-8',
        )
        return source, canonical

    def test_supersede_writes_redirect_and_tombstone(self, tmp_path):
        """Source body is replaced with a redirect stub; tombstone records ``superseded_by``."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        source, canonical = self._seed_pair(lessons_dir)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_supersede(
                Namespace(
                    lesson_id='2025-01-01-01-001',
                    by='2025-01-02-01-001',
                    reason='merged into canonical',
                )
            )

        assert result['status'] == 'success'
        assert result['superseded_by'] == '2025-01-02-01-001'

        # Source lesson body replaced with redirect stub and frontmatter updated.
        source_content = source.read_text(encoding='utf-8')
        assert '[SUPERSEDED]' in source_content
        assert '`2025-01-02-01-001`' in source_content
        assert 'merged into canonical' in source_content
        assert 'status=superseded' in source_content
        assert 'Source body content.' not in source_content

        # Canonical received a "Consolidated from" entry.
        canonical_content = canonical.read_text(encoding='utf-8')
        assert '## Consolidated from' in canonical_content
        assert '- 2025-01-01-01-001' in canonical_content

        # Tombstone has superseded_by populated.
        tombstone_path = lessons_dir / '.tombstones' / '2025-01-01-01-001.json'
        assert tombstone_path.exists()
        payload = json.loads(tombstone_path.read_text(encoding='utf-8'))
        assert payload['lesson_id'] == '2025-01-01-01-001'
        assert payload['status'] == 'superseded'
        assert payload['superseded_by'] == '2025-01-02-01-001'
        assert payload['reason'] == 'merged into canonical'

    def test_supersede_appends_to_existing_consolidated_section(self, tmp_path):
        """When the canonical already has a ``Consolidated from`` section, the new id is appended."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        _, canonical = self._seed_pair(lessons_dir, with_consolidated_section=True)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            cmd_supersede(
                Namespace(
                    lesson_id='2025-01-01-01-001',
                    by='2025-01-02-01-001',
                    reason='dedup',
                )
            )

        canonical_content = canonical.read_text(encoding='utf-8')
        # Both the original entry and the new one are present.
        assert '- 2024-12-31-23-099' in canonical_content
        assert '- 2025-01-01-01-001' in canonical_content
        # Only one "Consolidated from" header — the section is reused, not duplicated.
        assert canonical_content.count('## Consolidated from') == 1

    def test_supersede_unknown_source_returns_not_found(self, tmp_path):
        """Superseding a non-existent source lesson returns ``error: not_found``."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        self._seed_pair(lessons_dir)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_supersede(
                Namespace(
                    lesson_id='no-such-lesson',
                    by='2025-01-02-01-001',
                    reason='whatever',
                )
            )

        assert result['status'] == 'error'
        assert result['error'] == 'not_found'

    def test_supersede_unknown_canonical_returns_canonical_not_found(self, tmp_path):
        """Superseding by a non-existent canonical lesson returns ``error: canonical_not_found``."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        source, _ = self._seed_pair(lessons_dir)
        original_source_content = source.read_text(encoding='utf-8')

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_supersede(
                Namespace(
                    lesson_id='2025-01-01-01-001',
                    by='no-such-canonical',
                    reason='whatever',
                )
            )

        assert result['status'] == 'error'
        assert result['error'] == 'canonical_not_found'
        # Source must remain untouched on canonical-missing error.
        assert source.read_text(encoding='utf-8') == original_source_content

    def test_supersede_self_is_rejected(self, tmp_path):
        """A lesson cannot supersede itself."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        self._seed_pair(lessons_dir)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_supersede(
                Namespace(
                    lesson_id='2025-01-01-01-001',
                    by='2025-01-01-01-001',
                    reason='self',
                )
            )

        assert result['status'] == 'error'
        assert result['error'] == 'self_supersede'

    def test_supersede_first_merge_creates_consolidated_lessons_h2(self, tmp_path):
        """First supersede creates ``## Consolidated lessons`` H2 plus a ``### {id} — {title}`` subsection."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        _, canonical = self._seed_pair(lessons_dir)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_supersede(
                Namespace(
                    lesson_id='2025-01-01-01-001',
                    by='2025-01-02-01-001',
                    reason='first merge',
                )
            )

        assert result['status'] == 'success'
        assert result['merged_bytes'] > 0

        canonical_content = canonical.read_text(encoding='utf-8')
        assert canonical_content.count('## Consolidated lessons') == 1
        assert '### 2025-01-01-01-001 — Source Lesson' in canonical_content
        assert '**Component**: `test` · **Category**: bug' in canonical_content
        # Source body is preserved in the canonical.
        assert 'Source body content.' in canonical_content

    def test_supersede_second_merge_appends_under_existing_h2(self, tmp_path):
        """A second supersede against the same canonical adds another ``### {id}`` without duplicating the H2."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        _, canonical = self._seed_pair(lessons_dir)

        # Seed a second source lesson with distinct metadata so we can assert
        # the per-source `Component`/`Category` line is rendered correctly.
        second_source = lessons_dir / '2025-01-03-01-001.md'
        second_source.write_text(
            'id=2025-01-03-01-001\n'
            'component=other\n'
            'category=improvement\n'
            'status=active\n'
            'created=2025-01-03\n\n'
            '# Second Source\n\nSecond source body.\n',
            encoding='utf-8',
        )

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            cmd_supersede(
                Namespace(
                    lesson_id='2025-01-01-01-001',
                    by='2025-01-02-01-001',
                    reason='first',
                )
            )
            cmd_supersede(
                Namespace(
                    lesson_id='2025-01-03-01-001',
                    by='2025-01-02-01-001',
                    reason='second',
                )
            )

        canonical_content = canonical.read_text(encoding='utf-8')
        # Both subsections present, single H2.
        assert canonical_content.count('## Consolidated lessons') == 1
        assert '### 2025-01-01-01-001 — Source Lesson' in canonical_content
        assert '### 2025-01-03-01-001 — Second Source' in canonical_content
        # Per-source metadata line uses the second source's component/category.
        assert '**Component**: `other` · **Category**: improvement' in canonical_content
        assert 'Second source body.' in canonical_content

    def test_supersede_idempotent_when_subsection_present(self, tmp_path):
        """Re-running supersede whose ``### {id}`` already exists on the canonical is a body no-op (merged_bytes=0)."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        _, canonical = self._seed_pair(lessons_dir)

        # Pre-populate the canonical with a subsection for the source id so the
        # idempotency check fires before any append happens.
        canonical.write_text(
            'id=2025-01-02-01-001\n'
            'component=test\n'
            'category=bug\n'
            'status=active\n'
            'created=2025-01-02\n\n'
            '# Canonical Lesson\n\nCanonical body content.\n\n'
            '## Consolidated lessons\n\n'
            '### 2025-01-01-01-001 — Pre-existing Title\n\n'
            '**Component**: `test` · **Category**: bug\n\n'
            'pre-existing merged body\n',
            encoding='utf-8',
        )

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_supersede(
                Namespace(
                    lesson_id='2025-01-01-01-001',
                    by='2025-01-02-01-001',
                    reason='retry',
                )
            )

        assert result['status'] == 'success'
        assert result['merged_bytes'] == 0

        canonical_after = canonical.read_text(encoding='utf-8')
        # H2 stays single, the pre-existing subsection is preserved, and no
        # second `### 2025-01-01-01-001` was added.
        assert canonical_after.count('## Consolidated lessons') == 1
        assert canonical_after.count('### 2025-01-01-01-001') == 1
        assert 'pre-existing merged body' in canonical_after
        # The pre-existing title is preserved verbatim — supersede did not
        # rewrite it with the source's current title.
        assert 'Pre-existing Title' in canonical_after

    def test_supersede_atomic_canonical_write_failure_leaves_source_intact(
        self, tmp_path, monkeypatch
    ):
        """A failure during the canonical write leaves the source body and frontmatter unchanged."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        source, canonical = self._seed_pair(lessons_dir)
        source_before = source.read_text(encoding='utf-8')

        canonical_path_str = str(canonical)
        original_atomic_write = _mod.atomic_write_file

        def failing_atomic_write(path, content):
            # Raise only when the canonical is the target so the tombstone
            # write (which precedes the canonical write) still succeeds.
            if str(path) == canonical_path_str:
                raise OSError('simulated canonical write failure')
            return original_atomic_write(path, content)

        monkeypatch.setattr(_mod, 'atomic_write_file', failing_atomic_write)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            with pytest.raises(OSError, match='simulated canonical write failure'):
                cmd_supersede(
                    Namespace(
                        lesson_id='2025-01-01-01-001',
                        by='2025-01-02-01-001',
                        reason='atomic',
                    )
                )

        # Source body and frontmatter survive the failed canonical write.
        assert source.read_text(encoding='utf-8') == source_before

    def test_supersede_log_entry_records_merged_bytes(self, tmp_path, monkeypatch):
        """The script-execution log entry includes the appended byte count."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        self._seed_pair(lessons_dir)

        captured: list[tuple] = []

        def fake_log_entry(*args, **kwargs):
            captured.append(args)

        monkeypatch.setattr(_mod, 'log_entry', fake_log_entry)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_supersede(
                Namespace(
                    lesson_id='2025-01-01-01-001',
                    by='2025-01-02-01-001',
                    reason='log-test',
                )
            )

        assert result['status'] == 'success'
        merged_bytes = result['merged_bytes']
        assert merged_bytes > 0

        # cmd_supersede emits exactly one INFO log entry per success path.
        supersede_calls = [args for args in captured if 'Superseded lesson' in args[3]]
        assert len(supersede_calls) == 1
        log_message = supersede_calls[0][3]
        assert f'merged_bytes={merged_bytes}' in log_message


# =============================================================================
# Tier 2: cmd_cleanup_superseded
# =============================================================================


class TestCmdCleanupSuperseded:
    """``cmd_cleanup_superseded`` prunes redirect stubs while preserving tombstones."""

    def _seed_superseded(
        self,
        lessons_dir: Path,
        lesson_id: str,
        canonical_id: str = '2025-12-31-23-001',
        title: str = 'Source',
    ) -> Path:
        """Create a lesson and immediately supersede it via ``cmd_supersede``.

        Returns the path of the redirect stub so callers can assert on it
        directly. Reuses production ``cmd_supersede`` rather than handcrafting
        the on-disk shape so the test exercises the real coupling between
        supersede and cleanup.
        """
        canonical_path = lessons_dir / f'{canonical_id}.md'
        if not canonical_path.exists():
            canonical_path.write_text(
                f'id={canonical_id}\n'
                'component=test\n'
                'category=bug\n'
                'status=active\n'
                'created=2025-12-31\n\n'
                '# Canonical\n\nCanonical body.\n',
                encoding='utf-8',
            )
        source = lessons_dir / f'{lesson_id}.md'
        source.write_text(
            f'id={lesson_id}\n'
            'component=test\n'
            'category=bug\n'
            'status=active\n'
            'created=2025-01-01\n\n'
            f'# {title}\n\nSource body.\n',
            encoding='utf-8',
        )
        cmd_supersede(
            Namespace(lesson_id=lesson_id, by=canonical_id, reason='merged into canonical')
        )
        return source

    def test_cleanup_superseded_retention_filter_removes_only_old_stubs(self, tmp_path):
        """Age-filtered mode prunes only stubs whose mtime is older than the threshold."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            old_stub = self._seed_superseded(lessons_dir, '2025-01-01-01-001', title='Old')
            fresh_stub = self._seed_superseded(lessons_dir, '2025-01-01-01-002', title='Fresh')

            # Backdate the old stub past the 7-day cutoff.
            import os as _os
            old_mtime = old_stub.stat().st_mtime - (10 * 86400)
            _os.utime(old_stub, (old_mtime, old_mtime))

            result = cmd_cleanup_superseded(
                Namespace(lesson_id=None, retention_days=7, dry_run=False)
            )

        assert result['status'] == 'success'
        assert result['retention_days_effective'] == 7
        removed_ids = {entry['lesson_id'] for entry in result['removed']}
        assert removed_ids == {'2025-01-01-01-001'}
        assert not old_stub.exists()
        assert fresh_stub.exists()
        # Fresh stub's tombstone is also untouched.
        assert (lessons_dir / '.tombstones' / '2025-01-01-01-002.json').exists()

    def test_cleanup_superseded_explicit_lesson_ids_ignore_age(self, tmp_path):
        """Explicit ``--lesson-id`` removes the stub regardless of file age."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            stub = self._seed_superseded(lessons_dir, '2025-02-01-01-001')

            # File is fresh (no mtime backdating); explicit-id mode should still remove it.
            result = cmd_cleanup_superseded(
                Namespace(
                    lesson_id=['2025-02-01-01-001'], retention_days=None, dry_run=False
                )
            )

        assert result['status'] == 'success'
        assert {entry['lesson_id'] for entry in result['removed']} == {'2025-02-01-01-001'}
        assert not stub.exists()

    def test_cleanup_superseded_preserves_tombstones(self, tmp_path):
        """The matching ``.tombstones/{id}.json`` survives every removal mode byte-for-byte."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            self._seed_superseded(lessons_dir, '2025-03-01-01-001')
            tombstone_path = lessons_dir / '.tombstones' / '2025-03-01-01-001.json'
            tombstone_bytes_before = tombstone_path.read_bytes()

            cmd_cleanup_superseded(
                Namespace(
                    lesson_id=['2025-03-01-01-001'], retention_days=None, dry_run=False
                )
            )

        assert tombstone_path.exists()
        assert tombstone_path.read_bytes() == tombstone_bytes_before

    def test_cleanup_superseded_idempotent_on_already_removed(self, tmp_path):
        """Re-running with the same id reports it under ``already_removed`` (not error)."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            self._seed_superseded(lessons_dir, '2025-04-01-01-001')

            first = cmd_cleanup_superseded(
                Namespace(
                    lesson_id=['2025-04-01-01-001'], retention_days=None, dry_run=False
                )
            )
            second = cmd_cleanup_superseded(
                Namespace(
                    lesson_id=['2025-04-01-01-001'], retention_days=None, dry_run=False
                )
            )

        assert first['status'] == 'success'
        assert {e['lesson_id'] for e in first['removed']} == {'2025-04-01-01-001'}

        assert second['status'] == 'success'
        assert second['removed'] == []
        assert {e['lesson_id'] for e in second['already_removed']} == {'2025-04-01-01-001'}

    def test_cleanup_superseded_skips_files_without_tombstone(self, tmp_path):
        """A ``status: superseded`` file lacking a tombstone is reported under ``skipped_no_tombstone``."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        # Handcraft a superseded-style stub WITHOUT writing a tombstone.
        orphan = lessons_dir / '2025-05-01-01-001.md'
        orphan.write_text(
            'id=2025-05-01-01-001\n'
            'component=test\n'
            'category=bug\n'
            'status=superseded\n'
            'created=2025-05-01\n\n'
            '# Orphan Stub\n\n[SUPERSEDED]\n',
            encoding='utf-8',
        )

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_cleanup_superseded(
                Namespace(
                    lesson_id=['2025-05-01-01-001'], retention_days=None, dry_run=False
                )
            )

        assert result['status'] == 'success'
        assert result['removed'] == []
        assert {e['lesson_id'] for e in result['skipped_no_tombstone']} == {'2025-05-01-01-001'}
        # The .md must still be on disk — refusing to act preserves the audit trail.
        assert orphan.exists()

    def test_cleanup_superseded_dry_run_does_not_delete(self, tmp_path):
        """``--dry-run`` reports candidates under ``removed[]`` but leaves the .md on disk."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            stub = self._seed_superseded(lessons_dir, '2025-06-01-01-001')

            result = cmd_cleanup_superseded(
                Namespace(
                    lesson_id=['2025-06-01-01-001'], retention_days=None, dry_run=True
                )
            )

        assert result['status'] == 'success'
        assert result['dry_run'] is True
        assert {e['lesson_id'] for e in result['removed']} == {'2025-06-01-01-001'}
        # File remains on disk under dry-run.
        assert stub.exists()


# =============================================================================
# Tier 3: CLI plumbing for remove and supersede
# =============================================================================


class TestCliPlumbingRemoveSupersede(ScriptTestCase):
    """Subprocess test for ``remove`` and ``supersede`` subcommand wiring."""

    bundle = 'plan-marshall'
    skill = 'manage-lessons'
    script = 'manage-lessons.py'

    def _seed_lesson(self, lesson_id: str, title: str, status: str = 'active') -> None:
        lessons_dir = self.temp_dir / 'lessons-learned'
        lessons_dir.mkdir(parents=True, exist_ok=True)
        (lessons_dir / f'{lesson_id}.md').write_text(
            f'id={lesson_id}\ncomponent=test\ncategory=bug\nstatus={status}\n'
            f'created=2025-01-01\n\n# {title}\n\nBody.\n',
            encoding='utf-8',
        )

    def test_cli_remove_force(self):
        """``manage-lessons remove --force`` deletes the lesson via the CLI."""
        self._seed_lesson('2025-01-01-01-001', 'Removable')

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(self.temp_dir)}):
            result = run_script(
                SCRIPT_PATH,
                'remove',
                '--lesson-id',
                '2025-01-01-01-001',
                '--reason',
                'duplicate',
                '--force',
            )

        self.assert_success(result)
        self.assertIn('status: success', result.stdout)
        self.assertIn('id: 2025-01-01-01-001', result.stdout)
        self.assertFalse((self.temp_dir / 'lessons-learned' / '2025-01-01-01-001.md').exists())

    def test_cli_remove_requires_reason(self):
        """``remove`` without ``--reason`` is rejected at argparse."""
        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(self.temp_dir)}):
            result = run_script(
                SCRIPT_PATH,
                'remove',
                '--lesson-id',
                '2025-01-01-01-001',
                '--force',
            )

        self.assert_failure(result)
        self.assertIn('--reason', result.stderr)

    def test_cli_supersede(self):
        """``manage-lessons supersede`` wires the redirect via the CLI."""
        self._seed_lesson('2025-01-01-01-001', 'Source')
        self._seed_lesson('2025-01-02-01-001', 'Canonical')

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(self.temp_dir)}):
            result = run_script(
                SCRIPT_PATH,
                'supersede',
                '--lesson-id',
                '2025-01-01-01-001',
                '--by',
                '2025-01-02-01-001',
                '--reason',
                'merged',
            )

        self.assert_success(result)
        self.assertIn('status: success', result.stdout)
        self.assertIn('superseded_by: 2025-01-02-01-001', result.stdout)

    def test_cli_cleanup_superseded_rejects_combined_flags(self):
        """``cleanup-superseded`` rejects ``--lesson-id`` combined with ``--retention-days``.

        Argparse mutually-exclusive groups raise SystemExit(2) and write the
        error to stderr. We assert the failure is loud at the CLI boundary so
        callers cannot accidentally silently fall back to one mode.
        """
        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(self.temp_dir)}):
            result = run_script(
                SCRIPT_PATH,
                'cleanup-superseded',
                '--lesson-id',
                '2025-07-01-01-001',
                '--retention-days',
                '7',
            )

        self.assert_failure(result)
        # argparse emits the offending option in the usage error message.
        self.assertIn('not allowed with', result.stderr)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
