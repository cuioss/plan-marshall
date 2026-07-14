#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``set-body`` subcommand of manage-lessons.py.

``cmd_set_body`` implements the path-allocate body-write flow's overwrite
step: it preserves the ``key=value`` frontmatter and the H1 title verbatim
while replacing everything after the H1 with the supplied body. The
canonical input form is ``--file PATH`` (writes pass through the Write
tool, not the shell); ``--content STRING`` exists as a secondary form for
tiny payloads. Both forms share the TOON output shape
``{status, id, path, body_bytes_written}`` on success.
"""

from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from _lessons_helpers import cmd_set_body


class TestCmdSetBody:
    """Test cmd_set_body direct invocation."""

    _STUB_TEMPLATE = 'id={lesson_id}\ncomponent=test-component\ncategory=bug\ncreated=2025-01-01\n\n# {title}\n\n'

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

        def _raising_read_text(self, *args, **kwargs):
            # Only raise for the body source; allow reads on the lesson stub
            # (the function reads the original lesson via ``target.read_text``
            # AFTER the body source). We restrict to the exact body file path.
            if self == body_file:
                raise PermissionError('simulated read failure')
            return original_read_text(self, *args, **kwargs)

        with (
            patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}),
            patch.object(Path, 'read_text', _raising_read_text),
        ):
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
