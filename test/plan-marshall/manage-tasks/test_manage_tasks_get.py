#!/usr/bin/env python3
# ruff: noqa: I001
"""Tests for manage-tasks.py read (get) and exists subcommands.

Split from test_manage_tasks.py: covers the read and exists query verbs and
the canonical TOON-error contract for malformed --task-number.
"""

from conftest import run_script

from _helpers import (
    SCRIPT_PATH,
    _add_ns,
    _exists_ns,
    _read_ns,
    build_task_toon,
    cmd_add,
    cmd_exists,
    cmd_read,
)


# =============================================================================
# Tests: read
# =============================================================================


def test_get_existing_task(plan_context):
    """Read returns full task details."""
    toon = build_task_toon(
        title='Test task',
        deliverable=1,
        domain='java',
        description='Test description',
        steps=['src/main/java/One.java', 'src/main/java/Two.java', 'src/main/java/Three.java'],
    )
    cmd_add(_add_ns(plan_id='get-exist', content=toon.replace('\n', '\\n')))

    result = cmd_read(_read_ns(plan_id='get-exist', number=1))

    assert result['status'] == 'success'
    assert result['task']['number'] == 1
    assert result['task']['title'] == 'Test task'
    assert result['task']['deliverable'] == 1
    assert result['task']['description'] == 'Test description'
    assert 'One.java' in result['task']['steps'][0]['target']
    assert 'Two.java' in result['task']['steps'][1]['target']


def test_get_nonexistent_returns_error(plan_context):
    """Read nonexistent task returns error."""
    result = cmd_read(_read_ns(plan_id='get-noexist', number=99))

    assert result['status'] == 'error'
    assert 'TASK-99' in result.get('message', '')


def test_get_returns_verification_block(plan_context):
    """Read returns verification block details."""
    toon = build_task_toon(
        title='Verified task',
        deliverable=1,
        domain='java',
        description='Task with verification',
        steps=['src/main/java/Component.java'],
        verification_commands=['mvn test'],
        verification_criteria='Tests pass',
    )
    cmd_add(_add_ns(plan_id='get-verif', content=toon.replace('\n', '\\n')))

    result = cmd_read(_read_ns(plan_id='get-verif', number=1))

    assert result['status'] == 'success'
    assert result['task']['verification']['criteria'] == 'Tests pass'


# =============================================================================
# Tests: exists
# =============================================================================


def test_exists_returns_true_for_present_task(plan_context):
    """exists returns status: success exists: true for a task that was added."""
    toon = build_task_toon(
        title='Probe target',
        deliverable=1,
        domain='java',
        description='Task to probe',
        steps=['src/main/java/Probe.java'],
    )
    cmd_add(_add_ns(plan_id='exists-present', content=toon.replace('\n', '\\n')))

    result = cmd_exists(_exists_ns(plan_id='exists-present', number=1))

    assert result['status'] == 'success'
    assert result['exists'] is True
    assert result['task'] == 1
    assert result['plan_id'] == 'exists-present'


def test_exists_returns_false_for_absent_task(plan_context):
    """exists never errors on absence — returns status: success exists: false."""
    result = cmd_exists(_exists_ns(plan_id='exists-absent', number=99))

    assert result['status'] == 'success'
    assert result['exists'] is False
    assert result['task'] == 99
    # The defining contract: presence probe must NOT report status: error,
    # otherwise the executor records a recoverable [ERROR] row in
    # script-execution.log (the entire reason exists exists).
    assert 'message' not in result


def test_exists_rejects_non_integer_task_argument():
    """exists CLI rejects malformed --task-number with canonical TOON error."""
    result = run_script(SCRIPT_PATH, 'exists', '--plan-id', 'exists-bad-arg', '--task-number', 'abc')

    assert result.returncode == 0
    data = result.toon()
    assert data.get('status') == 'error'
    assert data.get('error') == 'invalid_task_number'


# =============================================================================
# Tests: get alias for read (subprocess / CLI plumbing)
# =============================================================================


class TestCliGetAlias:
    """Subprocess test pinning ``get`` as an alias for the ``read`` subcommand."""

    def test_cli_get_alias_succeeds(self, plan_context):
        """``manage-tasks get`` succeeds via the CLI for an existing task."""
        toon = build_task_toon(
            title='Aliased task',
            deliverable=1,
            domain='java',
            description='Task read via the get alias',
            steps=['src/main/java/Aliased.java'],
        )
        cmd_add(_add_ns(plan_id='get-alias', content=toon.replace('\n', '\\n')))

        result = run_script(SCRIPT_PATH, 'get', '--plan-id', 'get-alias', '--task-number', '1')

        assert result.returncode == 0, f'Script failed: {result.stderr}'
        data = result.toon()
        assert data['status'] == 'success'
        assert data['task']['number'] == 1
        assert data['task']['title'] == 'Aliased task'

    def test_cli_get_alias_matches_read(self, plan_context):
        """``get`` and ``read`` produce identical payloads for the same task."""
        toon = build_task_toon(
            title='Aliased task',
            deliverable=1,
            domain='java',
            description='Task read via both verbs',
            steps=['src/main/java/Aliased.java'],
        )
        cmd_add(_add_ns(plan_id='get-alias-match', content=toon.replace('\n', '\\n')))

        get_result = run_script(SCRIPT_PATH, 'get', '--plan-id', 'get-alias-match', '--task-number', '1')
        read_result = run_script(SCRIPT_PATH, 'read', '--plan-id', 'get-alias-match', '--task-number', '1')

        assert get_result.returncode == 0
        assert read_result.returncode == 0
        assert get_result.returncode == read_result.returncode
        assert get_result.stdout == read_result.stdout
