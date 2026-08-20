#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the `batch-add` subcommand of manage-tasks."""


import json

import pytest
from _manage_tasks_batch_add_fixtures import _entry, _ns, cmd_batch_add

# =============================================================================
# Successful batch insertion
# =============================================================================


def test_batch_add_three_tasks_sequential_numbering(plan_context):
    """A three-entry batch creates ``TASK-001``, ``TASK-002`` and ``TASK-003`` in order."""
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

    task_dir = plan_context.plan_dir_for('batch-3') / 'tasks'
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
    assert first['steps'] == [
        {'number': 1, 'target': 'src/A.java', 'status': 'pending', 'intent': 'write-replace'}
    ]


def test_batch_add_empty_array_is_noop(plan_context):
    """An empty array returns success with tasks_created=0 and writes nothing."""
    result = cmd_batch_add(_ns('batch-empty', tasks_json='[]'))
    assert result['status'] == 'success'
    assert result['tasks_created'] == 0
    assert result['tasks'] == []
    # No task files
    task_dir = plan_context.plan_dir_for('batch-empty') / 'tasks'
    # Directory may or may not exist after a no-op; if it does, it must be empty
    if task_dir.exists():
        assert list(task_dir.glob('TASK-*.json')) == []


def test_batch_add_appends_after_existing_tasks(plan_context):
    """Sequential numbering picks up after existing TASK-NNN files."""
    # Pre-seed ``TASK-001`` via direct write (mimics earlier add)
    task_dir = plan_context.plan_dir_for('batch-append') / 'tasks'
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


def test_batch_add_supports_depends_on_array(plan_context):
    """depends_on accepts a JSON array of TASK-N strings."""
    entries = [
        _entry(title='Base', steps=['src/A.java']),
        _entry(title='Dependant', steps=['src/B.java'], depends_on=['TASK-1']),
    ]
    result = cmd_batch_add(_ns('batch-deps-array', tasks_json=json.dumps(entries)))
    assert result['status'] == 'success'
    # Second task should record depends_on as ['TASK-1'].
    assert result['tasks'][1]['depends_on'] == ['TASK-1']


def test_batch_add_supports_depends_on_string_csv(plan_context):
    """depends_on accepts a comma-separated string and integers."""
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


def test_batch_add_missing_payload_errors(plan_context):
    """No --tasks-json and (effectively) empty stdin -> error."""
    # Pass an empty string explicitly to avoid reading real stdin
    result = cmd_batch_add(_ns('batch-missing', tasks_json='   '))
    assert result['status'] == 'error'
    assert 'JSON array' in result['message']


def test_batch_add_invalid_json_errors(plan_context):
    """Malformed JSON -> error with parse position."""
    result = cmd_batch_add(_ns('batch-bad-json', tasks_json='[{bad json}]'))
    assert result['status'] == 'error'
    assert 'Invalid JSON' in result['message']


def test_batch_add_non_array_errors(plan_context):
    """JSON object (not array) at top level -> error."""
    result = cmd_batch_add(_ns('batch-non-array', tasks_json=json.dumps({'foo': 'bar'})))
    assert result['status'] == 'error'
    assert 'JSON array' in result['message']


def test_batch_add_entry_missing_title_errors_atomically(plan_context):
    """Per-entry validation failure aborts the whole batch — no files written."""
    entries = [
        _entry(title='Valid', steps=['src/A.java']),
        _entry(title='', steps=['src/B.java']),  # title empty
    ]
    result = cmd_batch_add(_ns('batch-bad-entry', tasks_json=json.dumps(entries)))
    assert result['status'] == 'error'
    assert 'batch entry [1]' in result['message']
    assert 'title' in result['message']

    # Atomic guarantee: nothing on disk
    task_dir = plan_context.plan_dir_for('batch-bad-entry') / 'tasks'
    assert not task_dir.exists() or list(task_dir.glob('TASK-*.json')) == []


def test_batch_add_entry_step_not_filepath_errors(plan_context):
    """Step contract violation (non-file-path) is reported per-entry."""
    entries = [_entry(title='Bad', steps=['Update some code'])]
    result = cmd_batch_add(_ns('batch-bad-step', tasks_json=json.dumps(entries)))
    assert result['status'] == 'error'
    assert 'batch entry [0]' in result['message']
    assert 'file paths' in result['message']


def test_batch_add_entry_invalid_skill_format_errors(plan_context):
    """skills entries must follow bundle:skill format."""
    entries = [_entry(title='X', skills=['plain-skill-no-colon'])]
    result = cmd_batch_add(_ns('batch-bad-skill', tasks_json=json.dumps(entries)))
    assert result['status'] == 'error'
    assert 'batch entry [0]' in result['message']
    assert 'skill format' in result['message']


def test_batch_add_verification_profile_skips_filepath_check(plan_context):
    """verification profile permits non-file-path steps (commands)."""
    entries = [
        _entry(
            title='Verify all',
            profile='verification',
            steps=['./pw verify plan-marshall'],
        )
    ]
    result = cmd_batch_add(_ns('batch-verify', tasks_json=json.dumps(entries)))
    assert result['status'] == 'success'
    task_path = plan_context.plan_dir_for('batch-verify') / 'tasks' / 'TASK-001.json'
    task = json.loads(task_path.read_text())
    assert task['profile'] == 'verification'
    assert task['steps'][0]['target'] == './pw verify plan-marshall'


# =============================================================================
# Required per-step intent (JSON batch object-step contract)
# =============================================================================


@pytest.mark.parametrize('intent', ['read', 'write-new', 'write-replace', 'delete'])
def test_batch_add_stores_each_valid_intent(plan_context, intent):
    """Each valid intent on a JSON object-step round-trips into the stored task."""
    entries = [_entry(title='X', steps=[{'target': 'src/A.java', 'intent': intent}])]
    result = cmd_batch_add(_ns(f'batch-intent-{intent}', tasks_json=json.dumps(entries)))

    assert result['status'] == 'success'
    task_path = plan_context.plan_dir_for(f'batch-intent-{intent}') / 'tasks' / 'TASK-001.json'
    task = json.loads(task_path.read_text())
    assert task['steps'][0]['intent'] == intent


def test_batch_add_rejects_bare_string_step(plan_context):
    """A bare-string JSON step (no intent object) is rejected atomically."""
    entries = [{'title': 'X', 'deliverable': 1, 'domain': 'java', 'steps': ['src/A.java']}]
    result = cmd_batch_add(_ns('batch-bare-step', tasks_json=json.dumps(entries)))

    assert result['status'] == 'error'
    assert 'batch entry [0]' in result['message']
    assert 'object' in result['message'].lower()


def test_batch_add_rejects_step_missing_intent(plan_context):
    """A JSON object-step lacking the required intent key is rejected."""
    entries = [{'title': 'X', 'deliverable': 1, 'domain': 'java', 'steps': [{'target': 'src/A.java'}]}]
    result = cmd_batch_add(_ns('batch-no-intent', tasks_json=json.dumps(entries)))

    assert result['status'] == 'error'
    assert 'intent' in result['message'].lower()


def test_batch_add_rejects_invalid_intent(plan_context):
    """A present-but-invalid intent value is rejected per-entry."""
    entries = [_entry(title='X', steps=[{'target': 'src/A.java', 'intent': 'sideways'}])]
    result = cmd_batch_add(_ns('batch-bad-intent', tasks_json=json.dumps(entries)))

    assert result['status'] == 'error'
    assert 'intent' in result['message'].lower()


# =============================================================================
# --tasks-file PATH input (parity with --tasks-json)
# =============================================================================


def test_batch_add_reads_tasks_from_file(plan_context, tmp_path):
    """--tasks-file PATH reads a JSON array from disk and creates tasks (parity with --tasks-json)."""
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
    task_dir = plan_context.plan_dir_for('batch-file-happy') / 'tasks'
    files = sorted(task_dir.glob('TASK-*.json'))
    assert [f.name for f in files] == ['TASK-001.json', 'TASK-002.json']
    first = json.loads(files[0].read_text())
    assert first['title'] == 'From File 1'
    assert first['steps'] == [
        {'number': 1, 'target': 'src/A.java', 'status': 'pending', 'intent': 'write-replace'}
    ]


def test_batch_add_tasks_file_and_tasks_json_are_mutually_exclusive(plan_context, tmp_path):
    """Passing both --tasks-file and --tasks-json yields an invalid_input error.

    The CLI argparse layer enforces mutual exclusion, but cmd_batch_add keeps a
    defensive check for callers (e.g. tests, library users) that build a
    Namespace directly. This test exercises that defensive path.
    """
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
    task_dir = plan_context.plan_dir_for('batch-file-and-json') / 'tasks'
    assert not task_dir.exists() or list(task_dir.glob('TASK-*.json')) == []


def test_batch_add_tasks_file_missing_returns_file_not_found(plan_context):
    """--tasks-file pointing at a non-existent path returns a file_not_found error."""
    missing_path = '/nonexistent/path/to/tasks.json'

    result = cmd_batch_add(_ns('batch-file-missing', tasks_file=missing_path))

    assert result['status'] == 'error'
    assert result['error'] == 'file_not_found'
    assert missing_path in result['message']

    # No tasks should have been written
    task_dir = plan_context.plan_dir_for('batch-file-missing') / 'tasks'
    assert not task_dir.exists() or list(task_dir.glob('TASK-*.json')) == []
