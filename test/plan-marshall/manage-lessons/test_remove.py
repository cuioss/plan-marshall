#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Tests for the ``remove`` subcommand of manage-lessons.py.

``cmd_remove`` deletes a lesson file, writes a tombstone capturing the reason
and the retirement verdict, and emits an INFO audit entry to
script-execution.log. Tests cover the ``--force`` happy path, the not-found
error path, interactive-cancel behaviour (``input()`` returning ``n``), and the
audit-log emission shape.

Retirement evidence (the two-key path) is covered by a matched pair of controls
driven through the SAME vehicle — the real ``manage-lessons.py`` argparse
surface via ``run_script`` — so the negative control's rejection and the
positive control's success are directly comparable:

* **Negative control** — ``--coverage-verdict completely_covered`` without the
  evidence pair is rejected by the real CLI AND the lesson survives on disk.
  Asserting survival matters as much as asserting rejection: a rejection that
  still unlinked the file would be a silent data loss the exit code alone would
  not reveal.
* **Positive control** — a complete evidence set removes the lesson and writes
  a tombstone carrying ``coverage_verdict``, ``covering_clause`` and
  ``covering_input``.

Both controls exercise the shipped argparse declaration, never a stubbed or
re-implemented validator; the handler-side backstop (``cmd_remove`` invoked
directly, as a programmatic caller would) is covered separately so BOTH keys of
the two-key path are pinned.

CLI plumbing (subprocess) tests for the ``remove`` subcommand live in
``test_remove_supersede_cli.py``.
"""

import json
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

import pytest

from _lessons_helpers import SCRIPT_PATH, _mod, cmd_remove
from conftest import run_script

# The verdicts that assert a weaker claim than ``completely_covered`` and
# therefore require no evidence pair. Derived from the production vocabulary so
# a new verdict cannot be added without this test set being reconsidered.
_NON_EVIDENCE_VERDICTS = [v for v in _mod.COVERAGE_VERDICTS if v != _mod.EVIDENCE_REQUIRED_VERDICT]

_CLAUSE = 'manage-lessons/SKILL.md Canonical invocations -> remove'
_INPUT = 'remove --coverage-verdict completely_covered with no --covering-clause'


def _seed_lesson_file(lessons_dir: Path, lesson_id: str) -> Path:
    """Write a minimal, canonically-shaped lesson file and return its path."""
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


class TestCmdRemove:
    """``cmd_remove`` deletes the lesson, writes a tombstone, and logs an audit entry."""

    def _seed_lesson(self, lessons_dir: Path, lesson_id: str = '2025-01-01-01-001') -> Path:
        return _seed_lesson_file(lessons_dir, lesson_id)

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
                    coverage_verdict='redundant',
                    covering_clause=None,
                    covering_input=None,
                )
            )

        assert result['status'] == 'success'
        assert result['id'] == '2025-01-01-01-001'
        assert result['reason'] == 'duplicate of 2025-01-02-01-001'
        assert result['coverage_verdict'] == 'redundant'

        # Lesson file is gone.
        assert not seeded.exists()

        # Tombstone exists with the expected payload.
        tombstone_path = lessons_dir / '.tombstones' / '2025-01-01-01-001.json'
        assert tombstone_path.exists()
        payload = json.loads(tombstone_path.read_text(encoding='utf-8'))
        assert payload['lesson_id'] == '2025-01-01-01-001'
        assert payload['reason'] == 'duplicate of 2025-01-02-01-001'
        assert payload['status'] == 'removed'
        assert payload['coverage_verdict'] == 'redundant'
        assert 'removed_at' in payload
        assert 'superseded_by' not in payload
        # A non-completely_covered verdict records no evidence pair.
        assert 'covering_clause' not in payload
        assert 'covering_input' not in payload

    def test_remove_unknown_lesson_returns_not_found(self, tmp_path):
        """Removing a lesson that does not exist returns ``error: not_found``."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_remove(
                Namespace(
                    lesson_id='nope',
                    reason='gone',
                    force=True,
                    coverage_verdict='obsolete',
                    covering_clause=None,
                    covering_input=None,
                )
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
                Namespace(
                    lesson_id='2025-01-01-01-001',
                    reason='maybe',
                    force=False,
                    coverage_verdict='superseded',
                    covering_clause=None,
                    covering_input=None,
                )
            )

        assert result['status'] == 'cancelled'
        # File preserved.
        assert seeded.exists()
        # No tombstone written.
        tombstone_path = lessons_dir / '.tombstones' / '2025-01-01-01-001.json'
        assert not tombstone_path.exists()

    def test_remove_logs_audit_entry(self, tmp_path):
        """``cmd_remove --force`` emits an INFO audit entry naming the reason and verdict."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        self._seed_lesson(lessons_dir)

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            cmd_remove(
                Namespace(
                    lesson_id='2025-01-01-01-001',
                    reason='dedup',
                    force=True,
                    coverage_verdict='redundant',
                    covering_clause=None,
                    covering_input=None,
                )
            )

            log_files = list((tmp_path / 'logs').glob('script-execution-*.log'))

        assert log_files, 'expected at least one script-execution log file'
        log_text = '\n'.join(p.read_text(encoding='utf-8') for p in log_files)
        assert '[INFO]' in log_text
        assert '(plan-marshall:manage-lessons) Removed lesson 2025-01-01-01-001' in log_text
        assert 'dedup' in log_text
        assert 'verdict=redundant' in log_text


class TestRemoveEvidenceControlsViaRealArgparse:
    """Matched controls for the evidence requirement, both via the real CLI surface.

    Every test in this class drives ``manage-lessons.py`` through ``run_script``,
    so the assertion is made against the shipped argparse declaration — the flag
    that actually gates a retirement — rather than against a re-implementation
    of the rule inside the test.
    """

    @pytest.mark.parametrize(
        ('case', 'extra_flags', 'expected_missing'),
        [
            ('neither_flag', [], ['--covering-clause', '--covering-input']),
            ('clause_only', ['--covering-clause', _CLAUSE], ['--covering-input']),
            ('input_only', ['--covering-input', _INPUT], ['--covering-clause']),
            (
                'blank_values',
                ['--covering-clause', '   ', '--covering-input', '  '],
                ['--covering-clause', '--covering-input'],
            ),
        ],
    )
    def test_completely_covered_without_full_evidence_is_rejected_and_lesson_survives(
        self, tmp_path, case, extra_flags, expected_missing
    ):
        """NEGATIVE CONTROL: an unevidenced ``completely_covered`` retirement is refused.

        Each case fails for a DIFFERENT reason — no evidence at all, one half
        supplied, or values that are present but blank — so the parametrisation
        exercises distinct branches of the evidence predicate rather than
        repeating one assertion. Both halves of the outcome are asserted: the
        CLI rejects, AND the lesson is still on disk afterwards.
        """
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        seeded = _seed_lesson_file(lessons_dir, '2025-01-01-01-001')

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = run_script(
                SCRIPT_PATH,
                'remove',
                '--lesson-id',
                '2025-01-01-01-001',
                '--reason',
                f'evidence-gap-{case}',
                '--coverage-verdict',
                'completely_covered',
                *extra_flags,
                '--force',
            )

        # The retirement is refused at the argparse boundary.
        assert not result.success
        for flag in expected_missing:
            assert flag in result.stderr

        # ...and the lesson it would have deleted is untouched.
        assert seeded.exists()
        assert not (lessons_dir / '.tombstones' / '2025-01-01-01-001.json').exists()

    def test_completely_covered_with_full_evidence_removes_and_records_evidence(self, tmp_path):
        """POSITIVE CONTROL: a complete evidence set removes the lesson and is recorded.

        The mirror of the negative control above, through the same vehicle: the
        only difference is that both evidence flags carry real values. The
        tombstone must carry all three evidence fields, because recording them
        is what makes the justification outlive the lesson it deleted.
        """
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        seeded = _seed_lesson_file(lessons_dir, '2025-01-01-01-002')

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = run_script(
                SCRIPT_PATH,
                'remove',
                '--lesson-id',
                '2025-01-01-01-002',
                '--reason',
                'guarded failure mode can no longer occur',
                '--coverage-verdict',
                'completely_covered',
                '--covering-clause',
                _CLAUSE,
                '--covering-input',
                _INPUT,
                '--force',
            )

        assert result.success, f'Script failed: {result.stderr}'
        assert 'status: success' in result.stdout
        assert not seeded.exists()

        tombstone_path = lessons_dir / '.tombstones' / '2025-01-01-01-002.json'
        assert tombstone_path.exists()
        payload = json.loads(tombstone_path.read_text(encoding='utf-8'))
        assert payload['coverage_verdict'] == 'completely_covered'
        assert payload['covering_clause'] == _CLAUSE
        assert payload['covering_input'] == _INPUT

    def test_remove_without_coverage_verdict_is_rejected_and_lesson_survives(self, tmp_path):
        """``--coverage-verdict`` has no default: omitting it refuses the removal."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        seeded = _seed_lesson_file(lessons_dir, '2025-01-01-01-003')

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = run_script(
                SCRIPT_PATH,
                'remove',
                '--lesson-id',
                '2025-01-01-01-003',
                '--reason',
                'no verdict supplied',
                '--force',
            )

        assert not result.success
        assert '--coverage-verdict' in result.stderr
        assert seeded.exists()

    @pytest.mark.parametrize('verdict', _NON_EVIDENCE_VERDICTS)
    def test_non_completely_covered_verdicts_need_no_evidence_pair(self, tmp_path, verdict):
        """Each weaker verdict retires the lesson without the evidence flags.

        Parametrised over the production vocabulary rather than a hand-copied
        list, so a verdict added to ``COVERAGE_VERDICTS`` is covered here
        automatically instead of silently escaping the suite.
        """
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        seeded = _seed_lesson_file(lessons_dir, '2025-01-01-01-004')

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = run_script(
                SCRIPT_PATH,
                'remove',
                '--lesson-id',
                '2025-01-01-01-004',
                '--reason',
                f'retired as {verdict}',
                '--coverage-verdict',
                verdict,
                '--force',
            )

        assert result.success, f'Script failed: {result.stderr}'
        assert not seeded.exists()
        payload = json.loads(
            (lessons_dir / '.tombstones' / '2025-01-01-01-004.json').read_text(encoding='utf-8')
        )
        assert payload['coverage_verdict'] == verdict

    def test_unknown_verdict_is_rejected_and_lesson_survives(self, tmp_path):
        """A verdict outside the vocabulary is refused by the argparse ``choices``."""
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        seeded = _seed_lesson_file(lessons_dir, '2025-01-01-01-005')

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = run_script(
                SCRIPT_PATH,
                'remove',
                '--lesson-id',
                '2025-01-01-01-005',
                '--reason',
                'invented verdict',
                '--coverage-verdict',
                'probably_fine',
                '--force',
            )

        assert not result.success
        assert seeded.exists()


class TestRemoveEvidenceHandlerBackstop:
    """The handler-side guard — the second key for direct programmatic callers.

    A caller that builds a ``Namespace`` itself bypasses argparse entirely, so
    ``cmd_remove`` re-checks the same contract. These tests pin that backstop;
    they are the handler-path complement to the CLI controls above, not a
    duplicate of them.
    """

    def test_completely_covered_without_evidence_returns_error_and_keeps_lesson(self, tmp_path):
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        seeded = _seed_lesson_file(lessons_dir, '2025-01-01-01-001')

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_remove(
                Namespace(
                    lesson_id='2025-01-01-01-001',
                    reason='claimed coverage without evidence',
                    force=True,
                    coverage_verdict='completely_covered',
                    covering_clause=None,
                    covering_input=None,
                )
            )

        assert result['status'] == 'error'
        assert result['error'] == 'missing_coverage_evidence'
        assert result['missing_flags'] == ['--covering-clause', '--covering-input']
        assert seeded.exists()

    def test_missing_verdict_returns_error_and_keeps_lesson(self, tmp_path):
        lessons_dir = tmp_path / 'lessons-learned'
        lessons_dir.mkdir(parents=True)
        seeded = _seed_lesson_file(lessons_dir, '2025-01-01-01-001')

        with patch.dict('os.environ', {'PLAN_BASE_DIR': str(tmp_path)}):
            result = cmd_remove(
                Namespace(
                    lesson_id='2025-01-01-01-001',
                    reason='no verdict at all',
                    force=True,
                    coverage_verdict=None,
                    covering_clause=None,
                    covering_input=None,
                )
            )

        assert result['status'] == 'error'
        assert result['error'] == 'missing_coverage_verdict'
        assert result['valid_verdicts'] == list(_mod.COVERAGE_VERDICTS)
        assert seeded.exists()
