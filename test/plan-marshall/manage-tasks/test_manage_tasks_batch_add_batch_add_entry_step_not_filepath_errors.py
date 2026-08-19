#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the `batch-add` subcommand of manage-tasks.

Covers:
  - successful multi-task atomic insertion (sequential numbering, persisted files)
  - empty array no-op
  - validation rejection (per-entry error reporting)
  - schema rejection (top-level type errors)
  - all-or-nothing semantics (one bad entry → no files written)
  - depends_on alternative encodings
"""


import json

import pytest
from _manage_tasks_batch_add_fixtures import (
    _BARE_BLOCK_TASK_TOON,
    _BRACKETED_TASK_TOON,
    _entry,
    _ns,
    cmd_batch_add,
    parse_stdin_task,
)


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


@pytest.mark.parametrize(
    'toon,label',
    [
        (_BARE_BLOCK_TASK_TOON, 'bare-block'),
        (_BRACKETED_TASK_TOON, 'bracketed'),
    ],
)
def test_parse_stdin_task_accepts_both_steps_forms(toon, label):
    """Both bare-block and bracketed ``steps`` forms parse to the same step list."""
    parsed = parse_stdin_task(toon)

    assert parsed['steps'] == [
        {'target': 'test/plan-marshall/manage-tasks/test_a.py', 'intent': 'write-replace'},
        {'target': 'test/plan-marshall/manage-tasks/test_b.py', 'intent': 'write-replace'},
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
    parsed = parse_stdin_task(toon)

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
    parsed = parse_stdin_task(toon)

    expected_cmd = 'python3 .plan/execute-script.py x:y:z run --command-args "module-tests"'
    assert parsed['verification']['commands'] == [expected_cmd], (
        f'{label} verification.commands did not normalise to canonical list'
    )


def test_parse_stdin_task_bracketed_and_bare_block_parse_to_identical_output():
    """Round-trip equivalence — identical content in either shape produces identical dicts.

    The two TOON renderings differ only in length declarations; the
    parser's job is to erase that difference. Anything that diverges
    here is a per-shape branch the contract forbids.

    Every field except ``title`` and ``description`` must match — those two
    are intentionally different per-fixture to keep error messages
    unambiguous about which fixture is failing.
    """
    bare = parse_stdin_task(_BARE_BLOCK_TASK_TOON)
    bracketed = parse_stdin_task(_BRACKETED_TASK_TOON)

    for field in ('deliverable', 'domain', 'profile', 'skills', 'origin', 'steps', 'depends_on', 'verification'):
        assert bare[field] == bracketed[field], f'field {field!r} diverged between shapes'


def test_parse_stdin_task_bracketed_steps_zero_count_raises_missing_steps():
    """Bracketed form with a zero-count and empty body still triggers the required-field error.

    ``steps[0]:`` with no items is structurally well-formed but semantically
    empty — the parser must surface the canonical ``Missing required field:
    steps`` message rather than silently accepting an empty list.
    """
    toon = (
        'title: Empty steps\n'
        'deliverable: 1\n'
        'domain: plan-marshall-plugin-dev\n'
        'description: Empty steps must fail required-field validation\n'
        'steps[0]:\n'
        'depends_on: none\n'
    )

    with pytest.raises(ValueError) as excinfo:
        parse_stdin_task(toon)
    assert 'steps' in str(excinfo.value)


def test_parse_stdin_task_bracketed_steps_outer_quotes_still_rejected():
    """The outer-quotes anti-pattern is still rejected in the bracketed form.

    Adding bracketed-form support must not weaken the existing quoting
    contract — the same ValueError fires whether the steps header is
    ``steps:`` or ``steps[N]:``.
    """
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

    Fixture declares count 5 with only 2 actual rows.
    """
    toon = (
        'title: Count mismatch\n'
        'deliverable: 1\n'
        'domain: plan-marshall-plugin-dev\n'
        'description: Bracketed count is advisory and should not fail\n'
        'steps[5]:\n'
        '  - test/plan-marshall/manage-tasks/test_a.py (write-replace)\n'
        '  - test/plan-marshall/manage-tasks/test_b.py (write-replace)\n'
        'depends_on: none\n'
    )

    parsed = parse_stdin_task(toon)

    assert parsed['steps'] == [
        {'target': 'test/plan-marshall/manage-tasks/test_a.py', 'intent': 'write-replace'},
        {'target': 'test/plan-marshall/manage-tasks/test_b.py', 'intent': 'write-replace'},
    ]
