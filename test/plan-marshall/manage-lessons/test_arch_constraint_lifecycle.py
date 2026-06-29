#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Tests for the arch-constraint lesson lifecycle (deliverable 4).

Covers:

* create — ``add --category arch-constraint --rule X`` allocates a lesson carrying
  ``rule`` / ``recurrence_count=1`` / ``last_seen`` and returns ``action: created``.
* missing rule — ``add --category arch-constraint`` without ``--rule`` errors.
* reinforce-on-recurrence — a second add for the same rule reinforces the existing
  lesson (recurrence_count bump + ``## Recurrence —`` section) instead of allocating
  a new file, returning ``action: reinforced`` with the existing id.
* distinct rules — different rules allocate distinct lessons.
* retire-on-quiet — ``retire-quiet`` retires lessons whose ``last_seen`` is past the
  quiet window while retaining still-recent ones.
"""

from argparse import Namespace
from datetime import UTC, datetime
from pathlib import Path

from _lessons_helpers import _FakeDatetime, _mod, cmd_add

cmd_retire_quiet = _mod.cmd_retire_quiet


def _add_ns(**overrides) -> Namespace:
    """Build a full ``add`` Namespace with arch-constraint-aware defaults."""
    base = {
        'component': 'pm-dev-java:plan-marshall-plugin',
        'category': 'arch-constraint',
        'title': 'Layer service must not depend on web',
        'bundle': None,
        'rule': None,
    }
    base.update(overrides)
    return Namespace(**base)


def _frozen(year: int, month: int, day: int) -> _FakeDatetime:
    return _FakeDatetime(datetime(year, month, day, 12, 0, 0, tzinfo=UTC))


def _lesson_files(lessons_dir: Path) -> list[Path]:
    return sorted(lessons_dir.glob('*.md'))


# =============================================================================
# create + validation
# =============================================================================


def test_add_arch_constraint_creates_lesson_with_rule_metadata(tmp_path, monkeypatch):
    """A first arch-constraint observation allocates a lesson with the rule metadata."""
    (tmp_path / 'lessons-learned').mkdir(parents=True)
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    monkeypatch.setattr(_mod, 'datetime', _frozen(2026, 6, 29))

    result = cmd_add(_add_ns(rule='java:no-web-in-service'))

    assert result['status'] == 'success'
    assert result['action'] == 'created'
    assert result['rule'] == 'java:no-web-in-service'

    content = Path(result['path']).read_text(encoding='utf-8')
    assert 'category=arch-constraint' in content
    assert 'rule=java:no-web-in-service' in content
    assert 'recurrence_count=1' in content
    assert 'last_seen=2026-06-29' in content


def test_add_arch_constraint_without_rule_errors(tmp_path, monkeypatch):
    """arch-constraint add without --rule fails with missing_rule (dedup key required)."""
    (tmp_path / 'lessons-learned').mkdir(parents=True)
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    monkeypatch.setattr(_mod, 'datetime', _frozen(2026, 6, 29))

    result = cmd_add(_add_ns(rule=None))

    assert result['status'] == 'error'
    assert result['error'] == 'missing_rule'


# =============================================================================
# reinforce-on-recurrence
# =============================================================================


def test_add_same_rule_reinforces_existing_lesson(tmp_path, monkeypatch):
    """A recurring rule reinforces the existing lesson rather than allocating a new one."""
    lessons_dir = tmp_path / 'lessons-learned'
    lessons_dir.mkdir(parents=True)
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    monkeypatch.setattr(_mod, 'datetime', _frozen(2026, 6, 29))

    first = cmd_add(_add_ns(rule='java:no-web-in-service'))
    assert first['action'] == 'created'

    second = cmd_add(_add_ns(rule='java:no-web-in-service'))

    assert second['status'] == 'success'
    assert second['action'] == 'reinforced'
    assert second['id'] == first['id']
    assert second['recurrence_count'] == 2

    # No second file allocated — the rule dedups to one lesson.
    assert len(_lesson_files(lessons_dir)) == 1

    content = (lessons_dir / f'{first["id"]}.md').read_text(encoding='utf-8')
    assert 'recurrence_count=2' in content
    assert content.count('## Recurrence —') == 1


def test_distinct_rules_allocate_distinct_lessons(tmp_path, monkeypatch):
    """Two different rules produce two separate arch-constraint lessons."""
    lessons_dir = tmp_path / 'lessons-learned'
    lessons_dir.mkdir(parents=True)
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    monkeypatch.setattr(_mod, 'datetime', _frozen(2026, 6, 29))

    a = cmd_add(_add_ns(rule='java:no-web-in-service'))
    b = cmd_add(_add_ns(rule='java:no-cycles', title='No package cycles'))

    assert a['id'] != b['id']
    assert len(_lesson_files(lessons_dir)) == 2


# =============================================================================
# retire-on-quiet
# =============================================================================


def test_retire_quiet_retires_quiet_lessons_and_retains_recent(tmp_path, monkeypatch):
    """retire-quiet retires lessons past the quiet window and retains recent ones."""
    lessons_dir = tmp_path / 'lessons-learned'
    lessons_dir.mkdir(parents=True)
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))

    # Quiet lesson — created/last_seen far in the past.
    monkeypatch.setattr(_mod, 'datetime', _frozen(2026, 1, 1))
    quiet = cmd_add(_add_ns(rule='java:no-web-in-service'))

    # Recent lesson — created the day before "today".
    monkeypatch.setattr(_mod, 'datetime', _frozen(2026, 6, 28))
    recent = cmd_add(_add_ns(rule='java:no-cycles', title='No package cycles'))

    # Retire at 2026-06-29 with a 90-day quiet window.
    monkeypatch.setattr(_mod, 'datetime', _frozen(2026, 6, 29))
    result = cmd_retire_quiet(Namespace(quiet_days=90, dry_run=False))

    assert result['status'] == 'success'
    retired_ids = {row['lesson_id'] for row in result['retired']}
    retained_ids = {row['lesson_id'] for row in result['retained']}
    assert quiet['id'] in retired_ids
    assert recent['id'] in retained_ids

    # The quiet lesson's .md is gone; the recent one survives. A tombstone is kept.
    assert not (lessons_dir / f'{quiet["id"]}.md').exists()
    assert (lessons_dir / f'{recent["id"]}.md').exists()
    assert (lessons_dir / '.tombstones' / f'{quiet["id"]}.json').exists()


def test_retire_quiet_dry_run_reports_without_mutating(tmp_path, monkeypatch):
    """retire-quiet --dry-run reports retirements without unlinking the .md."""
    lessons_dir = tmp_path / 'lessons-learned'
    lessons_dir.mkdir(parents=True)
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))

    monkeypatch.setattr(_mod, 'datetime', _frozen(2026, 1, 1))
    quiet = cmd_add(_add_ns(rule='java:no-web-in-service'))

    monkeypatch.setattr(_mod, 'datetime', _frozen(2026, 6, 29))
    result = cmd_retire_quiet(Namespace(quiet_days=90, dry_run=True))

    assert result['status'] == 'success'
    assert result['dry_run'] is True
    assert quiet['id'] in {row['lesson_id'] for row in result['retired']}
    # Dry-run leaves the lesson and writes no tombstone.
    assert (lessons_dir / f'{quiet["id"]}.md').exists()
    assert not (lessons_dir / '.tombstones' / f'{quiet["id"]}.json').exists()


def test_reinforce_resets_quiet_clock(tmp_path, monkeypatch):
    """A reinforced lesson's refreshed last_seen keeps it out of the retire set."""
    lessons_dir = tmp_path / 'lessons-learned'
    lessons_dir.mkdir(parents=True)
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))

    monkeypatch.setattr(_mod, 'datetime', _frozen(2026, 1, 1))
    created = cmd_add(_add_ns(rule='java:no-web-in-service'))

    # Reinforce near "today" — refreshes last_seen to 2026-06-28.
    monkeypatch.setattr(_mod, 'datetime', _frozen(2026, 6, 28))
    reinforced = cmd_add(_add_ns(rule='java:no-web-in-service'))
    assert reinforced['action'] == 'reinforced'
    assert reinforced['id'] == created['id']

    monkeypatch.setattr(_mod, 'datetime', _frozen(2026, 6, 29))
    result = cmd_retire_quiet(Namespace(quiet_days=90, dry_run=False))

    # last_seen is now 2026-06-28 (1 day quiet) — retained, not retired.
    assert created['id'] in {row['lesson_id'] for row in result['retained']}
    assert (lessons_dir / f'{created["id"]}.md').exists()
