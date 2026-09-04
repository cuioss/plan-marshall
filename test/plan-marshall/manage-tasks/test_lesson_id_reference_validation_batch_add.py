#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2

"""Tests for at-write-time lesson-ID reference validation in manage-tasks.

Its sections, in order:

* Case (d) — batch with one valid + one phantom rejects the entire batch
* Case (e) — lesson IDs cited in the TITLE only are still scanned
* Case (f) — plan-dir converted-lesson artifact is the tier-2 exemption.
"""


import json

from _lesson_id_reference_validation_fixtures import (
    PHANTOM_IDS,
    REAL_LESSON_IDS,
    _batch_ns,
    _crud,
    _entry,
    _iv,
    _make_inventory_stub,
    _seed_plan_dir_lesson,
    cmd_batch_add,
    patch_inventory,
    short_circuit_anchor,
)

# =============================================================================
# Case (d) — batch with one valid + one phantom rejects the entire batch
# =============================================================================


def test_batch_add_one_phantom_rejects_entire_batch(plan_context, patch_inventory):
    """A batch of N entries where ONE cites a phantom ID rejects the
    whole batch — no TASK-NNN.json files are written."""
    patch_inventory(REAL_LESSON_IDS)

    entries = [
        _entry(
            title='Good task',
            description=f'Cites {REAL_LESSON_IDS[0]} which is real.',
            steps=['src/A.java'],
        ),
        _entry(
            title='Bad task',
            description=f'Cites phantom {PHANTOM_IDS[0]}.',
            steps=['src/B.java'],
        ),
        _entry(
            title='Another good task',
            description='No lesson IDs here.',
            steps=['src/C.java'],
        ),
    ]

    result = cmd_batch_add(_batch_ns('lesson-ref-batch-mixed', tasks_json=json.dumps(entries)))

    assert result['status'] == 'error'
    assert result['error'] == 'validation_error'
    assert result['validation_error'] == 'lesson_id_not_found'
    # task_index points to the offending entry (index 1 — the bad one).
    assert result['task_index'] == 1
    assert result['unresolved_ids'] == [PHANTOM_IDS[0]]

    # Atomic semantics: zero TASK files on disk.
    task_dir = plan_context.plan_dir_for('lesson-ref-batch-mixed') / 'tasks'
    if task_dir.exists():
        assert list(task_dir.glob('TASK-*.json')) == []


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
