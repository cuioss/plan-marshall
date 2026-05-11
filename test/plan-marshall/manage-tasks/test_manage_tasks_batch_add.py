#!/usr/bin/env python3
"""Tests for the `batch-add` subcommand of manage-tasks.

Covers:
  - successful multi-task atomic insertion (sequential numbering, persisted files)
  - empty array no-op
  - validation rejection (per-entry error reporting)
  - schema rejection (top-level type errors)
  - all-or-nothing semantics (one bad entry → no files written)
  - depends_on alternative encodings
"""

import importlib.util
import json
from argparse import Namespace
from pathlib import Path

import pytest

from conftest import PlanContext

# Load _tasks_crud directly via importlib (mirrors test_manage_tasks.py)
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


_crud = _load_module('_tasks_cmd_crud_batch', '_tasks_crud.py')
_core = _load_module('_tasks_core_for_parse_stdin', '_tasks_core.py')
cmd_batch_add = _crud.cmd_batch_add
parse_stdin_task = _core.parse_stdin_task


def _ns(plan_id, tasks_json=None, tasks_file=None):
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
    verification=None,
):
    """Build a valid batch entry dict (per task-contract.md schema)."""
    if steps is None:
        steps = ['src/main/java/Foo.java']
    if depends_on is None:
        depends_on = []
    if skills is None:
        skills = []
    entry = {
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
    if verification is not None:
        entry['verification'] = verification
    return entry


# =============================================================================
# Successful batch insertion
# =============================================================================


def test_batch_add_three_tasks_sequential_numbering():
    """A three-entry batch creates TASK-001/002/003 in order."""
    with PlanContext(plan_id='batch-3') as ctx:
        entries = [
            _entry(title='First', deliverable=1, steps=['src/A.java']),
            _entry(title='Second', deliverable=1, steps=['src/B.java']),
            _entry(title='Third', deliverable=2, steps=['src/C.java']),
        ]
        result = cmd_batch_add(_ns('batch-3', tasks_json=json.dumps(entries)))

        assert result['status'] == 'success'
        assert result['tasks_created'] == 3
        assert result['starting_task_number'] == 1
        assert result['total_tasks'] == 3
        assert [t['number'] for t in result['tasks']] == [1, 2, 3]
        assert [t['title'] for t in result['tasks']] == ['First', 'Second', 'Third']
        assert [t['file'] for t in result['tasks']] == [
            'TASK-001.json',
            'TASK-002.json',
            'TASK-003.json',
        ]

        task_dir = ctx.plan_dir / 'tasks'
        files = sorted(task_dir.glob('TASK-*.json'))
        assert [f.name for f in files] == [
            'TASK-001.json',
            'TASK-002.json',
            'TASK-003.json',
        ]
        # Check first task content
        first = json.loads(files[0].read_text())
        assert first['number'] == 1
        assert first['title'] == 'First'
        assert first['steps'] == [{'number': 1, 'target': 'src/A.java', 'status': 'pending'}]


def test_batch_add_empty_array_is_noop():
    """An empty array returns success with tasks_created=0 and writes nothing."""
    with PlanContext(plan_id='batch-empty') as ctx:
        result = cmd_batch_add(_ns('batch-empty', tasks_json='[]'))
        assert result['status'] == 'success'
        assert result['tasks_created'] == 0
        assert result['tasks'] == []
        # No task files
        task_dir = ctx.plan_dir / 'tasks'
        # Directory may or may not exist after a no-op; if it does, it must be empty
        if task_dir.exists():
            assert list(task_dir.glob('TASK-*.json')) == []


def test_batch_add_appends_after_existing_tasks():
    """Sequential numbering picks up after existing TASK-NNN files."""
    with PlanContext(plan_id='batch-append') as ctx:
        # Pre-seed TASK-001 via direct write (mimics earlier add)
        task_dir = ctx.plan_dir / 'tasks'
        task_dir.mkdir(parents=True, exist_ok=True)
        (task_dir / 'TASK-001.json').write_text(
            json.dumps(
                {
                    'number': 1,
                    'title': 'Pre-existing',
                    'status': 'done',
                    'steps': [],
                    'profile': 'implementation',
                    'domain': 'java',
                    'origin': 'plan',
                    'deliverable': 1,
                    'depends_on': [],
                    'skills': [],
                    'verification': {'commands': [], 'criteria': '', 'manual': False},
                }
            )
        )

        entries = [_entry(title='New 1'), _entry(title='New 2')]
        result = cmd_batch_add(_ns('batch-append', tasks_json=json.dumps(entries)))

        assert result['status'] == 'success'
        assert result['starting_task_number'] == 2
        assert [t['number'] for t in result['tasks']] == [2, 3]
        files = sorted(task_dir.glob('TASK-*.json'))
        assert [f.name for f in files] == [
            'TASK-001.json',
            'TASK-002.json',
            'TASK-003.json',
        ]


def test_batch_add_supports_depends_on_array():
    """depends_on accepts a JSON array of TASK-N strings."""
    with PlanContext(plan_id='batch-deps-array'):
        entries = [
            _entry(title='Base', steps=['src/A.java']),
            _entry(title='Dependant', steps=['src/B.java'], depends_on=['TASK-1']),
        ]
        result = cmd_batch_add(_ns('batch-deps-array', tasks_json=json.dumps(entries)))
        assert result['status'] == 'success'
        # Second task should record depends_on as ['TASK-1'].
        assert result['tasks'][1]['depends_on'] == ['TASK-1']


def test_batch_add_supports_depends_on_string_csv():
    """depends_on accepts a comma-separated string and integers."""
    with PlanContext(plan_id='batch-deps-csv'):
        entries = [
            _entry(title='A'),
            _entry(title='B'),
            _entry(title='C', depends_on='TASK-1, 2'),
        ]
        result = cmd_batch_add(_ns('batch-deps-csv', tasks_json=json.dumps(entries)))
        assert result['status'] == 'success'
        third = result['tasks'][2]
        assert sorted(third['depends_on']) == ['TASK-1', 'TASK-2']


# =============================================================================
# Validation rejection
# =============================================================================


def test_batch_add_missing_payload_errors():
    """No --tasks-json and (effectively) empty stdin -> error."""
    with PlanContext(plan_id='batch-missing'):
        # Pass an empty string explicitly to avoid reading real stdin
        result = cmd_batch_add(_ns('batch-missing', tasks_json='   '))
        assert result['status'] == 'error'
        assert 'JSON array' in result['message']


def test_batch_add_invalid_json_errors():
    """Malformed JSON -> error with parse position."""
    with PlanContext(plan_id='batch-bad-json'):
        result = cmd_batch_add(_ns('batch-bad-json', tasks_json='[{bad json}]'))
        assert result['status'] == 'error'
        assert 'Invalid JSON' in result['message']


def test_batch_add_non_array_errors():
    """JSON object (not array) at top level -> error."""
    with PlanContext(plan_id='batch-non-array'):
        result = cmd_batch_add(_ns('batch-non-array', tasks_json=json.dumps({'foo': 'bar'})))
        assert result['status'] == 'error'
        assert 'JSON array' in result['message']


def test_batch_add_entry_missing_title_errors_atomically():
    """Per-entry validation failure aborts the whole batch — no files written."""
    with PlanContext(plan_id='batch-bad-entry') as ctx:
        entries = [
            _entry(title='Valid', steps=['src/A.java']),
            _entry(title='', steps=['src/B.java']),  # title empty
        ]
        result = cmd_batch_add(_ns('batch-bad-entry', tasks_json=json.dumps(entries)))
        assert result['status'] == 'error'
        assert 'batch entry [1]' in result['message']
        assert 'title' in result['message']

        # Atomic guarantee: nothing on disk
        task_dir = ctx.plan_dir / 'tasks'
        assert not task_dir.exists() or list(task_dir.glob('TASK-*.json')) == []


def test_batch_add_entry_step_not_filepath_errors():
    """Step contract violation (non-file-path) is reported per-entry."""
    with PlanContext(plan_id='batch-bad-step'):
        entries = [_entry(title='Bad', steps=['Update some code'])]
        result = cmd_batch_add(_ns('batch-bad-step', tasks_json=json.dumps(entries)))
        assert result['status'] == 'error'
        assert 'batch entry [0]' in result['message']
        assert 'file paths' in result['message']


def test_batch_add_entry_invalid_skill_format_errors():
    """skills entries must follow bundle:skill format."""
    with PlanContext(plan_id='batch-bad-skill'):
        entries = [_entry(title='X', skills=['plain-skill-no-colon'])]
        result = cmd_batch_add(_ns('batch-bad-skill', tasks_json=json.dumps(entries)))
        assert result['status'] == 'error'
        assert 'batch entry [0]' in result['message']
        assert 'skill format' in result['message']


def test_batch_add_verification_profile_skips_filepath_check():
    """verification profile permits non-file-path steps (commands)."""
    with PlanContext(plan_id='batch-verify') as ctx:
        entries = [
            _entry(
                title='Verify all',
                profile='verification',
                steps=['./pw verify plan-marshall'],
            )
        ]
        result = cmd_batch_add(_ns('batch-verify', tasks_json=json.dumps(entries)))
        assert result['status'] == 'success'
        task_path = ctx.plan_dir / 'tasks' / 'TASK-001.json'
        task = json.loads(task_path.read_text())
        assert task['profile'] == 'verification'
        assert task['steps'][0]['target'] == './pw verify plan-marshall'


# =============================================================================
# --tasks-file PATH input (parity with --tasks-json)
# =============================================================================


def test_batch_add_reads_tasks_from_file(tmp_path):
    """--tasks-file PATH reads a JSON array from disk and creates tasks (parity with --tasks-json)."""
    with PlanContext(plan_id='batch-file-happy') as ctx:
        entries = [
            _entry(title='From File 1', steps=['src/A.java']),
            _entry(title='From File 2', steps=['src/B.java']),
        ]
        tasks_path = tmp_path / 'tasks.json'
        tasks_path.write_text(json.dumps(entries), encoding='utf-8')

        result = cmd_batch_add(_ns('batch-file-happy', tasks_file=str(tasks_path)))

        assert result['status'] == 'success'
        assert result['tasks_created'] == 2
        assert [t['number'] for t in result['tasks']] == [1, 2]
        assert [t['title'] for t in result['tasks']] == ['From File 1', 'From File 2']

        # On-disk parity with --tasks-json path
        task_dir = ctx.plan_dir / 'tasks'
        files = sorted(task_dir.glob('TASK-*.json'))
        assert [f.name for f in files] == ['TASK-001.json', 'TASK-002.json']
        first = json.loads(files[0].read_text())
        assert first['title'] == 'From File 1'
        assert first['steps'] == [{'number': 1, 'target': 'src/A.java', 'status': 'pending'}]


def test_batch_add_tasks_file_and_tasks_json_are_mutually_exclusive(tmp_path):
    """Passing both --tasks-file and --tasks-json yields an invalid_input error.

    The CLI argparse layer enforces mutual exclusion, but cmd_batch_add keeps a
    defensive check for callers (e.g. tests, library users) that build a
    Namespace directly. This test exercises that defensive path.
    """
    with PlanContext(plan_id='batch-file-and-json') as ctx:
        tasks_path = tmp_path / 'tasks.json'
        tasks_path.write_text(json.dumps([_entry(title='File')]), encoding='utf-8')
        json_payload = json.dumps([_entry(title='JSON')])

        result = cmd_batch_add(
            _ns(
                'batch-file-and-json',
                tasks_json=json_payload,
                tasks_file=str(tasks_path),
            )
        )

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_input'
        assert '--tasks-json' in result['message']
        assert '--tasks-file' in result['message']
        assert 'mutually exclusive' in result['message']

        # No tasks should have been written
        task_dir = ctx.plan_dir / 'tasks'
        assert not task_dir.exists() or list(task_dir.glob('TASK-*.json')) == []


def test_batch_add_tasks_file_missing_returns_file_not_found():
    """--tasks-file pointing at a non-existent path returns a file_not_found error."""
    with PlanContext(plan_id='batch-file-missing') as ctx:
        missing_path = '/nonexistent/path/to/tasks.json'

        result = cmd_batch_add(_ns('batch-file-missing', tasks_file=missing_path))

        assert result['status'] == 'error'
        assert result['error'] == 'file_not_found'
        assert missing_path in result['message']

        # No tasks should have been written
        task_dir = ctx.plan_dir / 'tasks'
        assert not task_dir.exists() or list(task_dir.glob('TASK-*.json')) == []


# =============================================================================
# Tests: parse_stdin_task accepts both bracketed and bare-block list forms
# =============================================================================
#
# Pins the breaking-refactor contract from deliverable D2: ``parse_stdin_task``
# accepts BOTH the bare-block form (``steps:`` + indented ``- `` items) AND the
# bracketed length-declared form (``steps[N]:`` + same indented ``- `` items).
# Both shapes normalise to the same internal step list — no per-shape divergence.


_BARE_BLOCK_TASK_TOON = (
    'title: Bare-block form\n'
    'deliverable: 1\n'
    'domain: plan-marshall-plugin-dev\n'
    'description: Bare-block steps + skills + verification commands\n'
    'skills:\n'
    '  - pm-plugin-development:plugin-architecture\n'
    'steps:\n'
    '  - test/plan-marshall/manage-tasks/test_a.py\n'
    '  - test/plan-marshall/manage-tasks/test_b.py\n'
    'depends_on: none\n'
    'verification:\n'
    '  commands:\n'
    '    - python3 .plan/execute-script.py x:y:z run --command-args "module-tests"\n'
    '  criteria: green\n'
)

_BRACKETED_TASK_TOON = (
    'title: Bracketed form\n'
    'deliverable: 1\n'
    'domain: plan-marshall-plugin-dev\n'
    'description: Bracketed steps + skills + verification commands\n'
    'skills[1]:\n'
    '  - pm-plugin-development:plugin-architecture\n'
    'steps[2]:\n'
    '  - test/plan-marshall/manage-tasks/test_a.py\n'
    '  - test/plan-marshall/manage-tasks/test_b.py\n'
    'depends_on: none\n'
    'verification:\n'
    '  commands[1]:\n'
    '    - python3 .plan/execute-script.py x:y:z run --command-args "module-tests"\n'
    '  criteria: green\n'
)


@pytest.mark.parametrize(
    'toon,label',
    [
        (_BARE_BLOCK_TASK_TOON, 'bare-block'),
        (_BRACKETED_TASK_TOON, 'bracketed'),
    ],
)
def test_parse_stdin_task_accepts_both_steps_forms(toon, label):
    """Both bare-block and bracketed ``steps`` forms parse to the same step list."""
    # Arrange + Act
    parsed = parse_stdin_task(toon)

    # Assert
    assert parsed['steps'] == [
        'test/plan-marshall/manage-tasks/test_a.py',
        'test/plan-marshall/manage-tasks/test_b.py',
    ], f'{label} form did not normalise to canonical step list'


@pytest.mark.parametrize(
    'toon,label',
    [
        (_BARE_BLOCK_TASK_TOON, 'bare-block'),
        (_BRACKETED_TASK_TOON, 'bracketed'),
    ],
)
def test_parse_stdin_task_accepts_both_skills_forms(toon, label):
    """Both bare-block and bracketed ``skills`` forms parse to the same skill list."""
    # Arrange + Act
    parsed = parse_stdin_task(toon)

    # Assert
    assert parsed['skills'] == ['pm-plugin-development:plugin-architecture'], (
        f'{label} form did not normalise to canonical skills list'
    )


@pytest.mark.parametrize(
    'toon,label',
    [
        (_BARE_BLOCK_TASK_TOON, 'bare-block'),
        (_BRACKETED_TASK_TOON, 'bracketed'),
    ],
)
def test_parse_stdin_task_accepts_both_verification_commands_forms(toon, label):
    """Both bare-block and bracketed ``verification.commands`` parse identically."""
    # Arrange + Act
    parsed = parse_stdin_task(toon)

    # Assert
    expected_cmd = 'python3 .plan/execute-script.py x:y:z run --command-args "module-tests"'
    assert parsed['verification']['commands'] == [expected_cmd], (
        f'{label} verification.commands did not normalise to canonical list'
    )


def test_parse_stdin_task_bracketed_and_bare_block_parse_to_identical_output():
    """Round-trip equivalence — identical content in either shape produces identical dicts.

    The two TOON renderings differ only in length declarations; the
    parser's job is to erase that difference. Anything that diverges
    here is a per-shape branch the contract forbids.
    """
    # Arrange + Act
    bare = parse_stdin_task(_BARE_BLOCK_TASK_TOON)
    bracketed = parse_stdin_task(_BRACKETED_TASK_TOON)

    # Assert — every field except ``title`` and ``description`` must match
    # (those two are intentionally different per-fixture to keep error
    # messages unambiguous about which fixture is failing).
    for field in ('deliverable', 'domain', 'profile', 'skills', 'origin', 'steps', 'depends_on', 'verification'):
        assert bare[field] == bracketed[field], f'field {field!r} diverged between shapes'


def test_parse_stdin_task_bracketed_steps_zero_count_raises_missing_steps():
    """Bracketed form with a zero-count and empty body still triggers the required-field error.

    ``steps[0]:`` with no items is structurally well-formed but semantically
    empty — the parser must surface the canonical ``Missing required field:
    steps`` message rather than silently accepting an empty list.
    """
    # Arrange
    toon = (
        'title: Empty steps\n'
        'deliverable: 1\n'
        'domain: plan-marshall-plugin-dev\n'
        'description: Empty steps must fail required-field validation\n'
        'steps[0]:\n'
        'depends_on: none\n'
    )

    # Act / Assert
    with pytest.raises(ValueError) as excinfo:
        parse_stdin_task(toon)
    assert 'steps' in str(excinfo.value)


def test_parse_stdin_task_bracketed_steps_outer_quotes_still_rejected():
    """The outer-quotes anti-pattern is still rejected in the bracketed form.

    Adding bracketed-form support must not weaken the existing quoting
    contract — the same ValueError fires whether the steps header is
    ``steps:`` or ``steps[N]:``.
    """
    # Arrange
    offending = '"src/main/java/Foo.java"'
    toon = (
        'title: Outer quotes negative bracketed\n'
        'deliverable: 1\n'
        'domain: plan-marshall-plugin-dev\n'
        'description: Outer-quoted step under bracketed form should fail fast\n'
        'steps[1]:\n'
        f'  - {offending}\n'
        'depends_on: none\n'
    )

    # Act / Assert
    with pytest.raises(ValueError) as excinfo:
        parse_stdin_task(toon)
    message = str(excinfo.value)
    assert 'steps' in message
    assert 'outer double-quotes' in message


def test_parse_stdin_task_bracketed_form_length_declaration_is_advisory():
    """A mismatched ``[N]`` count does NOT raise — TOON treats ``[N]`` as advisory.

    The parser normalises by walking the body until indentation breaks; the
    declared count is informational only. This mirrors the documented TOON
    specification (see ``ref-toon-format``).
    """
    # Arrange — declared count 5, actual rows 2.
    toon = (
        'title: Count mismatch\n'
        'deliverable: 1\n'
        'domain: plan-marshall-plugin-dev\n'
        'description: Bracketed count is advisory and should not fail\n'
        'steps[5]:\n'
        '  - test/plan-marshall/manage-tasks/test_a.py\n'
        '  - test/plan-marshall/manage-tasks/test_b.py\n'
        'depends_on: none\n'
    )

    # Act
    parsed = parse_stdin_task(toon)

    # Assert
    assert parsed['steps'] == [
        'test/plan-marshall/manage-tasks/test_a.py',
        'test/plan-marshall/manage-tasks/test_b.py',
    ]
