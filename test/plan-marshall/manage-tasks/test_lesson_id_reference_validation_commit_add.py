#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for at-write-time lesson-ID reference validation in manage-tasks."""


import pytest
from _lesson_id_reference_validation_fixtures import (
    PHANTOM_IDS,
    REAL_LESSON_IDS,
    _commit_ns,
    _crud,
    _iv,
    _make_inventory_stub,
    _seed_pending,
    _seed_plan_dir_lesson,
    _toon_task_body,
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


# =============================================================================
# Case (a) — no lesson-ID tokens → success (and inventory is NOT consulted)
# =============================================================================


def test_commit_add_no_lesson_id_tokens_succeeds(plan_context, patch_inventory):
    """A task with no lesson-ID-shaped tokens must succeed; the scanner
    short-circuits and never queries the inventory."""

    # A sentinel verify that BLOWS UP if called proves no inventory query.
    def _exploding_verify(_tokens):
        raise AssertionError('verify_lesson_ids_exist must not be called when no tokens are present')

    # Replace verify with the exploder for this test only.
    original = _crud.verify_lesson_ids_exist
    _crud.verify_lesson_ids_exist = _exploding_verify
    try:
        plan_dir = plan_context.plan_dir_for('lesson-ref-no-tokens')
        body = _toon_task_body(
            title='Plain refactor',
            description='No lesson IDs anywhere in here.',
        )
        _seed_pending(plan_dir, body)

        result = cmd_commit_add(_commit_ns('lesson-ref-no-tokens'))

        # result is success and ``TASK-001.json`` exists.
        assert result['status'] == 'success'
        assert result['file'] == 'TASK-001.json'
        assert (plan_dir / 'tasks' / 'TASK-001.json').is_file()
    finally:
        _crud.verify_lesson_ids_exist = original


# =============================================================================
# Case (b) — task cites a real lesson ID that resolves → success
# =============================================================================


def test_commit_add_real_lesson_id_succeeds(plan_context, patch_inventory):
    """A task citing a lesson ID that resolves against the inventory must
    succeed and produce a TASK file."""
    patch_inventory(REAL_LESSON_IDS)

    plan_dir = plan_context.plan_dir_for('lesson-ref-real')
    body = _toon_task_body(
        title='Apply fix',
        description=f'Per lesson {REAL_LESSON_IDS[0]}: refactor the parser.',
    )
    _seed_pending(plan_dir, body)

    result = cmd_commit_add(_commit_ns('lesson-ref-real'))

    assert result['status'] == 'success'
    assert result['file'] == 'TASK-001.json'
    assert (plan_dir / 'tasks' / 'TASK-001.json').is_file()


# =============================================================================
# Case (c) — phantom ID hard-fails; no TASK file written; payload contract held
# =============================================================================


def test_commit_add_phantom_lesson_id_aborts_atomically(plan_context, patch_inventory):
    """A task citing a phantom lesson ID must hard-fail with the typed
    error payload AND must NOT create any TASK-NNN.json file."""
    patch_inventory(REAL_LESSON_IDS)  # phantom is NOT in this set

    plan_dir = plan_context.plan_dir_for('lesson-ref-phantom')
    body = _toon_task_body(
        title='Bad task',
        description=f'Cites phantom lesson {PHANTOM_IDS[0]} that does not exist.',
    )
    _seed_pending(plan_dir, body)

    result = cmd_commit_add(_commit_ns('lesson-ref-phantom'))

    # Payload contract from _lesson_id_validation_error.
    assert result['status'] == 'error'
    assert result['error'] == 'validation_error'
    assert result['validation_error'] == 'lesson_id_not_found'
    assert result['unresolved_ids'] == [PHANTOM_IDS[0]]
    assert result['task_index'] == 0
    assert PHANTOM_IDS[0] in result['message']

    # Atomic-write contract: zero TASK files on failure.
    task_dir = plan_dir / 'tasks'
    # Directory may not exist at all when the abort happens before write.
    if task_dir.exists():
        assert list(task_dir.glob('TASK-*.json')) == []


def test_commit_add_phantom_payload_dedupes_and_sorts(plan_context, patch_inventory):
    """Multiple unresolved IDs in title+description are returned
    deduplicated and sorted (per _lesson_id_validation_error contract)."""
    patch_inventory(REAL_LESSON_IDS)

    # Cite both phantoms twice across title and description; payload
    # must collapse to a sorted unique list.
    plan_dir = plan_context.plan_dir_for('lesson-ref-phantom-dedup')
    body = _toon_task_body(
        title=f'Phantom {PHANTOM_IDS[1]}',
        description=(f'See {PHANTOM_IDS[0]} and {PHANTOM_IDS[1]} again, plus {PHANTOM_IDS[0]} repeated.'),
    )
    _seed_pending(plan_dir, body)

    result = cmd_commit_add(_commit_ns('lesson-ref-phantom-dedup'))

    assert result['status'] == 'error'
    assert result['validation_error'] == 'lesson_id_not_found'
    assert result['unresolved_ids'] == sorted(set(PHANTOM_IDS))


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
