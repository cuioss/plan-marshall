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
            result = cmd_get(Namespace(id='2025-01-01-001'))

        assert result['status'] == 'success'
        assert result['component'] == 'test-component'
        assert result['category'] == 'bug'
        assert result['title'] == 'Test Lesson Title'

    def test_get_nonexistent_lesson(self, tmp_path):
        """Should return error for non-existent lesson."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_get(Namespace(id='nonexistent-id'))

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
                Namespace(id='2025-01-01-001', component='new-component', category=None)
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
                Namespace(id='nonexistent', component='x', category=None)
            )

        assert result['status'] == 'error'
        assert result['error'] == 'not_found'


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
                Namespace(id='2025-01-01-001', plan_id='my-plan')
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
                Namespace(id='nonexistent-id', plan_id='my-plan')
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
                Namespace(id='2025-01-01-001', plan_id='fresh-plan')
            )

        assert result['status'] == 'success'
        assert plan_dir.exists()
        assert (plan_dir / 'lesson-2025-01-01-001.md').exists()

    def test_convert_to_plan_rejects_path_traversal(self, tmp_path):
        """Should reject identifiers containing path separators or traversal sequences."""
        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            for bad_id in ('../escape', 'sub/dir', 'back\\slash'):
                result = cmd_convert_to_plan(
                    Namespace(id=bad_id, plan_id='p')
                )
                assert result['status'] == 'error'
                assert result['error'] == 'invalid_id'

            for bad_plan in ('../escape', 'sub/dir', 'back\\slash'):
                result = cmd_convert_to_plan(
                    Namespace(id='good-id', plan_id=bad_plan)
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

        * ``cmd_get(id='2025-01-01-001')`` returns ``status: success`` and
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
            get_result = cmd_get(Namespace(id='2025-01-01-001'))
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


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
