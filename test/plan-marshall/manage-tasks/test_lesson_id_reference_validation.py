#!/usr/bin/env python3
"""Tests for at-write-time lesson-ID reference validation in manage-tasks.

Covers the validation surface added to ``cmd_commit_add`` and
``cmd_batch_add`` in ``_tasks_crud.py`` per lesson 2026-05-03-21-002:
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

import importlib.util
import json
import sys
from argparse import Namespace
from pathlib import Path

import pytest

from conftest import PlanContext

# =============================================================================
# Module loading — load _tasks_crud directly via importlib so we can patch
# the module-level scan/verify bindings rather than the source bindings in
# input_validation. Mirrors the pattern in test_manage_tasks_batch_add.py.
# =============================================================================

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-tasks'
    / 'scripts'
)


def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_crud = _load_module('_tasks_cmd_crud_lesson_ref', '_tasks_crud.py')
cmd_commit_add = _crud.cmd_commit_add
cmd_batch_add = _crud.cmd_batch_add

# Resolve the input_validation module already loaded by _tasks_crud's import.
# The runtime regex anchor lives there (verify_lesson_id_regex_against_inventory),
# and scan_lesson_id_tokens triggers it on first use per process. Tests must
# short-circuit the anchor so they exercise only the regex+membership path
# instead of subprocessing `manage-lessons list` from the test environment.
_input_validation = _crud.scan_lesson_id_tokens.__module__
_iv = sys.modules[_input_validation]


# =============================================================================
# Fixture data — sample IDs sourced from real `manage-lessons list` output
# (per lesson 2026-04-29-10-001). PHANTOM_IDS are syntactically valid lesson
# IDs that do NOT exist in the live inventory.
# =============================================================================

REAL_LESSON_IDS = (
    '2026-04-29-10-001',
    '2026-05-03-21-002',
    '2026-04-26-11-001',
)

PHANTOM_IDS = (
    '2099-01-01-00-001',
    '2099-12-31-23-999',
)


# =============================================================================
# Helpers
# =============================================================================


def _commit_ns(plan_id, slot=None):
    """Build a Namespace for cmd_commit_add."""
    return Namespace(plan_id=plan_id, slot=slot)


def _batch_ns(plan_id, tasks_json=None, tasks_file=None):
    """Build a Namespace for cmd_batch_add."""
    return Namespace(plan_id=plan_id, tasks_json=tasks_json, tasks_file=tasks_file)


def _entry(
    title='Task',
    deliverable=1,
    domain='java',
    profile='implementation',
    steps=None,
    depends_on=None,
    skills=None,
    description='',
    origin='plan',
):
    """Build a valid batch entry dict (per task-contract.md schema)."""
    if steps is None:
        steps = ['src/main/java/Foo.java']
    if depends_on is None:
        depends_on = []
    if skills is None:
        skills = []
    return {
        'title': title,
        'deliverable': deliverable,
        'domain': domain,
        'profile': profile,
        'steps': steps,
        'depends_on': depends_on,
        'skills': skills,
        'description': description,
        'origin': origin,
    }


def _toon_task_body(
    title='Task',
    deliverable=1,
    domain='java',
    profile='implementation',
    steps=None,
    description='',
):
    """Build a task definition body in the format ``parse_stdin_task`` accepts.

    Matches the legacy fixture format used by ``test_manage_tasks.py``:
    plain ``steps:`` (NOT ``steps[N]:``), unquoted step items, raw
    description (no surrounding quotes). Inner quotes inside title/description
    are not used here to keep the parser path deterministic.
    """
    if steps is None:
        steps = ['src/main/java/Foo.java']
    lines = [
        f'title: {title}',
        f'deliverable: {deliverable}',
        f'domain: {domain}',
        f'profile: {profile}',
        'origin: plan',
        f'description: {description}',
        'steps:',
    ]
    for step in steps:
        lines.append(f'  - {step}')
    lines.append('depends_on: none')
    lines.append('skills:')
    return '\n'.join(lines) + '\n'


def _seed_pending(ctx, body, slot='default'):
    """Write a TOON scratch file under the plan's pending-tasks dir so
    cmd_commit_add can consume it (mimics prepare-add → main-context Write)."""
    pending_dir = ctx.plan_dir / 'work' / 'pending-tasks'
    pending_dir.mkdir(parents=True, exist_ok=True)
    path = pending_dir / f'{slot}.toon'
    path.write_text(body, encoding='utf-8')
    return path


def _make_inventory_stub(present_ids):
    """Return a verify_lesson_ids_exist replacement: every queried token
    maps to True iff it is in ``present_ids``."""
    present = set(present_ids)

    def _stub(tokens):
        return {tok: tok in present for tok in tokens}

    return _stub


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


def test_commit_add_no_lesson_id_tokens_succeeds(patch_inventory):
    """A task with no lesson-ID-shaped tokens must succeed; the scanner
    short-circuits and never queries the inventory."""

    # A sentinel verify that BLOWS UP if called proves no inventory query.
    def _exploding_verify(_tokens):
        raise AssertionError('verify_lesson_ids_exist must not be called when no tokens are present')

    with PlanContext(plan_id='lesson-ref-no-tokens') as ctx:
        # Replace verify with the exploder for this test only.
        original = _crud.verify_lesson_ids_exist
        _crud.verify_lesson_ids_exist = _exploding_verify
        try:
            body = _toon_task_body(
                title='Plain refactor',
                description='No lesson IDs anywhere in here.',
            )
            _seed_pending(ctx, body)

            result = cmd_commit_add(_commit_ns('lesson-ref-no-tokens'))

            # Arrange-Act-Assert: result is success and TASK-001.json exists.
            assert result['status'] == 'success'
            assert result['file'] == 'TASK-001.json'
            assert (ctx.plan_dir / 'tasks' / 'TASK-001.json').is_file()
        finally:
            _crud.verify_lesson_ids_exist = original


# =============================================================================
# Case (b) — task cites a real lesson ID that resolves → success
# =============================================================================


def test_commit_add_real_lesson_id_succeeds(patch_inventory):
    """A task citing a lesson ID that resolves against the inventory must
    succeed and produce a TASK file."""
    patch_inventory(REAL_LESSON_IDS)

    with PlanContext(plan_id='lesson-ref-real') as ctx:
        body = _toon_task_body(
            title='Apply fix',
            description=f'Per lesson {REAL_LESSON_IDS[0]}: refactor the parser.',
        )
        _seed_pending(ctx, body)

        result = cmd_commit_add(_commit_ns('lesson-ref-real'))

        assert result['status'] == 'success'
        assert result['file'] == 'TASK-001.json'
        assert (ctx.plan_dir / 'tasks' / 'TASK-001.json').is_file()


# =============================================================================
# Case (c) — phantom ID hard-fails; no TASK file written; payload contract held
# =============================================================================


def test_commit_add_phantom_lesson_id_aborts_atomically(patch_inventory):
    """A task citing a phantom lesson ID must hard-fail with the typed
    error payload AND must NOT create any TASK-NNN.json file."""
    patch_inventory(REAL_LESSON_IDS)  # phantom is NOT in this set

    with PlanContext(plan_id='lesson-ref-phantom') as ctx:
        body = _toon_task_body(
            title='Bad task',
            description=f'Cites phantom lesson {PHANTOM_IDS[0]} that does not exist.',
        )
        _seed_pending(ctx, body)

        result = cmd_commit_add(_commit_ns('lesson-ref-phantom'))

        # Payload contract from _lesson_id_validation_error.
        assert result['status'] == 'error'
        assert result['error'] == 'validation_error'
        assert result['validation_error'] == 'lesson_id_not_found'
        assert result['unresolved_ids'] == [PHANTOM_IDS[0]]
        assert result['task_index'] == 0
        assert PHANTOM_IDS[0] in result['message']

        # Atomic-write contract: zero TASK files on failure.
        task_dir = ctx.plan_dir / 'tasks'
        # Directory may not exist at all when the abort happens before write.
        if task_dir.exists():
            assert list(task_dir.glob('TASK-*.json')) == []


def test_commit_add_phantom_payload_dedupes_and_sorts(patch_inventory):
    """Multiple unresolved IDs in title+description are returned
    deduplicated and sorted (per _lesson_id_validation_error contract)."""
    patch_inventory(REAL_LESSON_IDS)

    with PlanContext(plan_id='lesson-ref-phantom-dedup') as ctx:
        # Cite both phantoms twice across title and description; payload
        # must collapse to a sorted unique list.
        body = _toon_task_body(
            title=f'Phantom {PHANTOM_IDS[1]}',
            description=(f'See {PHANTOM_IDS[0]} and {PHANTOM_IDS[1]} again, plus {PHANTOM_IDS[0]} repeated.'),
        )
        _seed_pending(ctx, body)

        result = cmd_commit_add(_commit_ns('lesson-ref-phantom-dedup'))

        assert result['status'] == 'error'
        assert result['validation_error'] == 'lesson_id_not_found'
        assert result['unresolved_ids'] == sorted(set(PHANTOM_IDS))


# =============================================================================
# Case (d) — batch with one valid + one phantom rejects the entire batch
# =============================================================================


def test_batch_add_one_phantom_rejects_entire_batch(patch_inventory):
    """A batch of N entries where ONE cites a phantom ID rejects the
    whole batch — no TASK-NNN.json files are written."""
    patch_inventory(REAL_LESSON_IDS)

    with PlanContext(plan_id='lesson-ref-batch-mixed') as ctx:
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
        task_dir = ctx.plan_dir / 'tasks'
        if task_dir.exists():
            assert list(task_dir.glob('TASK-*.json')) == []


def test_batch_add_all_real_succeeds(patch_inventory):
    """Sanity check: a batch of entries citing only real lesson IDs
    succeeds and creates the expected TASK files (proves the batch path
    is not over-rejecting)."""
    patch_inventory(REAL_LESSON_IDS)

    with PlanContext(plan_id='lesson-ref-batch-good') as ctx:
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
        files = sorted((ctx.plan_dir / 'tasks').glob('TASK-*.json'))
        assert [f.name for f in files] == ['TASK-001.json', 'TASK-002.json']


# =============================================================================
# Case (e) — lesson IDs cited in the TITLE only are still scanned
# =============================================================================


def test_commit_add_phantom_in_title_only_aborts(patch_inventory):
    """A phantom ID cited ONLY in the title (description is empty of
    lesson IDs) must still abort the write — the scanner spans
    ``title + ' ' + description`` per ``_scan_unresolved_lesson_ids``."""
    patch_inventory(REAL_LESSON_IDS)

    with PlanContext(plan_id='lesson-ref-title-only') as ctx:
        body = _toon_task_body(
            title=f'Phantom {PHANTOM_IDS[0]} in title',
            description='Description has no lesson IDs at all.',
        )
        _seed_pending(ctx, body)

        result = cmd_commit_add(_commit_ns('lesson-ref-title-only'))

        assert result['status'] == 'error'
        assert result['validation_error'] == 'lesson_id_not_found'
        assert result['unresolved_ids'] == [PHANTOM_IDS[0]]

        task_dir = ctx.plan_dir / 'tasks'
        if task_dir.exists():
            assert list(task_dir.glob('TASK-*.json')) == []


def test_batch_add_phantom_in_title_only_aborts(patch_inventory):
    """The batch path also scans title text — a phantom ID cited only in
    one entry's title aborts the entire batch."""
    patch_inventory(REAL_LESSON_IDS)

    with PlanContext(plan_id='lesson-ref-batch-title') as ctx:
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

        task_dir = ctx.plan_dir / 'tasks'
        if task_dir.exists():
            assert list(task_dir.glob('TASK-*.json')) == []
