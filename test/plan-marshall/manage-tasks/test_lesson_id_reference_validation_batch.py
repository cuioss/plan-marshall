#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for at-write-time lesson-ID reference validation in manage-tasks.

Covers the validation surface in ``cmd_commit_add`` and ``cmd_batch_add``
(``_tasks_crud.py``):
tasks that cite lesson IDs MUST resolve against the live manage-lessons
inventory at write time. A miss aborts the entire write atomically — no
``TASK-NNN.json`` file is created.

Cases:
  (a) task with no lesson-ID-shaped tokens succeeds
  (b) task citing an ID that resolves in inventory succeeds
  (c) task citing a phantom ID hard-fails with
      ``validation_error: lesson_id_not_found`` and no TASK file is written
  (d) batch-add with one valid + one phantom rejects the entire batch
      with no TASK files written
  (e) lesson IDs cited in the title only are still scanned

The inventory is mocked at the ``_tasks_crud`` module-level binding so the
tests are deterministic and do NOT depend on the live ``manage-lessons``
inventory state. Real-ID fixtures are copy-pasted from live
``manage-lessons list`` output (mirrors the fixture pattern in
``test/plan-marshall/tools-input-validation/test_lesson_id_scanner.py``).
"""


import json

import pytest
from _lesson_id_reference_validation_fixtures import (
    PHANTOM_IDS,
    REAL_LESSON_IDS,
    _batch_ns,
    _commit_ns,
    _crud,
    _entry,
    _iv,
    _make_inventory_stub,
    _seed_pending,
    _seed_plan_dir_lesson,
    _toon_task_body,
    cmd_batch_add,
    cmd_commit_add,
)


@pytest.fixture(autouse=True)
def short_circuit_anchor(monkeypatch):
    """Bypass the runtime regex anchor for every test in this module.

    ``scan_lesson_id_tokens`` triggers ``verify_lesson_id_regex_against_inventory``
    on first use per process, which subprocesses ``manage-lessons list``. In the
    test environment this is non-deterministic (depends on cwd and live inventory
    state). Tests in this file exercise the regex+membership wiring; the anchor's
    integration behavior is covered by ``test_lesson_id_scanner.py`` directly.
    """
    monkeypatch.setattr(_iv, '_lesson_anchor_checked', True)
    monkeypatch.setattr(_iv, 'verify_lesson_id_regex_against_inventory', lambda: None)


@pytest.fixture
def patch_inventory(monkeypatch):
    """Patch the module-level ``verify_lesson_ids_exist`` binding in
    ``_tasks_crud`` so tests are deterministic. Also short-circuit the
    runtime regex anchor in ``input_validation`` so ``scan_lesson_id_tokens``
    does NOT subprocess ``manage-lessons list`` from the test environment.
    The real regex behavior in ``scan_lesson_id_tokens`` is preserved — only
    the anchor's first-use subprocess call is bypassed."""

    def _apply(present_ids):
        # 1. Stub the inventory verifier in _tasks_crud's namespace.
        monkeypatch.setattr(_crud, 'verify_lesson_ids_exist', _make_inventory_stub(present_ids))
        # 2. Mark the runtime anchor as already-checked so scan_lesson_id_tokens
        #    skips its first-use subprocess call. Reset by monkeypatch teardown.
        monkeypatch.setattr(_iv, '_lesson_anchor_checked', True)
        # 3. Stub the anchor function itself as a defensive no-op in case the
        #    module-level flag is bypassed (e.g., a future refactor recomputes
        #    on every call).
        monkeypatch.setattr(_iv, 'verify_lesson_id_regex_against_inventory', lambda: None)

    return _apply


def test_batch_add_all_real_succeeds(plan_context, patch_inventory):
    """Sanity check: a batch of entries citing only real lesson IDs
    succeeds and creates the expected TASK files (proves the batch path
    is not over-rejecting)."""
    patch_inventory(REAL_LESSON_IDS)

    entries = [
        _entry(
            title='First',
            description=f'See {REAL_LESSON_IDS[0]}.',
            steps=['src/A.java'],
        ),
        _entry(
            title='Second',
            description=f'See {REAL_LESSON_IDS[1]}.',
            steps=['src/B.java'],
        ),
    ]

    result = cmd_batch_add(_batch_ns('lesson-ref-batch-good', tasks_json=json.dumps(entries)))

    assert result['status'] == 'success'
    assert result['tasks_created'] == 2
    files = sorted((plan_context.plan_dir_for('lesson-ref-batch-good') / 'tasks').glob('TASK-*.json'))
    assert [f.name for f in files] == ['TASK-001.json', 'TASK-002.json']


# =============================================================================
# Case (e) — lesson IDs cited in the TITLE only are still scanned
# =============================================================================


def test_commit_add_phantom_in_title_only_aborts(plan_context, patch_inventory):
    """A phantom ID cited ONLY in the title (description is empty of
    lesson IDs) must still abort the write — the scanner spans
    ``title + ' ' + description`` per ``_scan_unresolved_lesson_ids``."""
    patch_inventory(REAL_LESSON_IDS)

    plan_dir = plan_context.plan_dir_for('lesson-ref-title-only')
    body = _toon_task_body(
        title=f'Phantom {PHANTOM_IDS[0]} in title',
        description='Description has no lesson IDs at all.',
    )
    _seed_pending(plan_dir, body)

    result = cmd_commit_add(_commit_ns('lesson-ref-title-only'))

    assert result['status'] == 'error'
    assert result['validation_error'] == 'lesson_id_not_found'
    assert result['unresolved_ids'] == [PHANTOM_IDS[0]]

    task_dir = plan_dir / 'tasks'
    if task_dir.exists():
        assert list(task_dir.glob('TASK-*.json')) == []


def test_batch_add_phantom_in_title_only_aborts(plan_context, patch_inventory):
    """The batch path also scans title text — a phantom ID cited only in
    one entry's title aborts the entire batch."""
    patch_inventory(REAL_LESSON_IDS)

    entries = [
        _entry(
            title='Good task',
            description='No IDs.',
            steps=['src/A.java'],
        ),
        _entry(
            title=f'Phantom {PHANTOM_IDS[1]} in title',
            description='Description is clean.',
            steps=['src/B.java'],
        ),
    ]

    result = cmd_batch_add(_batch_ns('lesson-ref-batch-title', tasks_json=json.dumps(entries)))

    assert result['status'] == 'error'
    assert result['validation_error'] == 'lesson_id_not_found'
    assert result['task_index'] == 1
    assert result['unresolved_ids'] == [PHANTOM_IDS[1]]

    task_dir = plan_context.plan_dir_for('lesson-ref-batch-title') / 'tasks'
    if task_dir.exists():
        assert list(task_dir.glob('TASK-*.json')) == []


# =============================================================================
# Case (f) — plan-dir converted-lesson artifact is the tier-2 exemption.
#
# A lesson ID absent from the active inventory but present on disk at
# ``{plan_dir}/lesson-{id}.md`` resolves and the write proceeds. A token
# absent from BOTH tiers still hard-fails with the unchanged
# ``lesson_id_not_found`` payload. (Covers the plan-dir exemption in
# ``_scan_unresolved_lesson_ids``.)
# =============================================================================


def test_commit_add_plan_dir_artifact_exempts_inventory_miss(plan_context, patch_inventory):
    """A token the inventory reports ABSENT but whose converted artifact
    exists in the plan dir is exempted — it does NOT appear in the
    unresolved list and commit-add succeeds."""
    # Inventory knows only the real IDs; the exempt token is NOT among them.
    patch_inventory(REAL_LESSON_IDS)
    exempt_id = PHANTOM_IDS[0]

    plan_dir = plan_context.plan_dir_for('lesson-ref-plandir-exempt')
    # Seed the tier-2 artifact under get_plan_dir(plan_id) — the inventory
    # verifier reports this id absent, so only the on-disk artifact can resolve it.
    _seed_plan_dir_lesson(plan_dir, exempt_id)

    body = _toon_task_body(
        title='Apply converted lesson',
        description=f'Per lesson {exempt_id}: this lesson was converted into this plan.',
    )
    _seed_pending(plan_dir, body)

    result = cmd_commit_add(_commit_ns('lesson-ref-plandir-exempt'))

    assert result['status'] == 'success'
    assert result['file'] == 'TASK-001.json'
    assert (plan_dir / 'tasks' / 'TASK-001.json').is_file()


def test_batch_add_plan_dir_artifact_exempts_inventory_miss(plan_context, patch_inventory):
    """The batch path honours the same tier-2 exemption: an entry citing an
    inventory-absent id whose plan-dir artifact exists does NOT abort the
    batch, and all TASK files are written."""
    patch_inventory(REAL_LESSON_IDS)
    exempt_id = PHANTOM_IDS[0]

    plan_dir = plan_context.plan_dir_for('lesson-ref-batch-plandir-exempt')
    _seed_plan_dir_lesson(plan_dir, exempt_id)

    entries = [
        _entry(
            title='Inventory-resolved task',
            description=f'See {REAL_LESSON_IDS[0]}.',
            steps=['src/A.java'],
        ),
        _entry(
            title='Plan-dir-exempt task',
            description=f'Cites converted lesson {exempt_id} (absent from inventory, present on disk).',
            steps=['src/B.java'],
        ),
    ]

    result = cmd_batch_add(_batch_ns('lesson-ref-batch-plandir-exempt', tasks_json=json.dumps(entries)))

    assert result['status'] == 'success'
    assert result['tasks_created'] == 2
    files = sorted(
        (plan_context.plan_dir_for('lesson-ref-batch-plandir-exempt') / 'tasks').glob('TASK-*.json')
    )
    assert [f.name for f in files] == ['TASK-001.json', 'TASK-002.json']


def test_commit_add_absent_from_both_tiers_still_hard_fails(plan_context, patch_inventory):
    """Regression guard: a token absent from BOTH the active inventory AND
    the plan dir still hard-fails with the unchanged
    ``lesson_id_not_found`` payload. The tier-2 exemption must not weaken
    the genuine-miss path."""
    patch_inventory(REAL_LESSON_IDS)
    missing_id = PHANTOM_IDS[0]

    plan_dir = plan_context.plan_dir_for('lesson-ref-both-tiers-miss')
    # Seed an UNRELATED artifact to prove the exemption matches by exact id,
    # not by "any lesson-*.md exists in the plan dir".
    _seed_plan_dir_lesson(plan_dir, PHANTOM_IDS[1])

    body = _toon_task_body(
        title='Bad task',
        description=f'Cites {missing_id}, which exists in neither inventory nor plan dir.',
    )
    _seed_pending(plan_dir, body)

    result = cmd_commit_add(_commit_ns('lesson-ref-both-tiers-miss'))

    # Unchanged hard-fail payload contract.
    assert result['status'] == 'error'
    assert result['error'] == 'validation_error'
    assert result['validation_error'] == 'lesson_id_not_found'
    assert result['unresolved_ids'] == [missing_id]
    assert result['task_index'] == 0
    assert missing_id in result['message']

    task_dir = plan_dir / 'tasks'
    if task_dir.exists():
        assert list(task_dir.glob('TASK-*.json')) == []
