#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Tests for manage-tasks.py add / prepare-add / commit-add subcommands.

Split from test_manage_tasks.py: covers the three-step path-allocate add
flow, validation rules at task creation, and verification.commands quoting
contract (parse_stdin_task).
"""

import json

import pytest

from _helpers import (
    _add_ns,
    _add_task,
    add_basic_task,
    build_task_toon,
    cmd_add,
    parse_stdin_task,
)


# =============================================================================
# Tests: add command with stdin-based API
# =============================================================================


def test_add_first_task(plan_context):
    """Add first task creates TASK-001."""
    toon = build_task_toon(
        title='First task',
        deliverable=1,
        domain='java',
        description='Task description',
        steps=['src/main/java/First.java', 'src/main/java/Second.java'],
    )
    result = _add_task('add-first', toon)

    assert result['status'] == 'success'
    assert result['file'] == 'TASK-001.json'
    assert result['total_tasks'] == 1

    task_dir = plan_context.plan_dir_for('add-first') / 'tasks'
    files = list(task_dir.glob('TASK-001.json'))
    assert len(files) == 1, f'Expected 1 file, got {files}'


def test_add_sequential_numbering(plan_context):
    """Adding multiple tasks gets sequential numbers."""
    add_basic_task(plan_id='add-seq', title='First', deliverable=1, steps=['src/main/java/First.java'])
    result = add_basic_task(
        plan_id='add-seq',
        title='Second',
        deliverable=2,
        steps=['src/main/java/Second.java', 'src/test/java/SecondTest.java'],
    )

    assert result['file'] == 'TASK-002.json'
    assert result['total_tasks'] == 2


def test_add_creates_numbered_filename(plan_context):
    """Filename uses TASK-NNN format (not slug or type suffix)."""
    add_basic_task(plan_id='add-fname', title='Implement JWT Service!', deliverable=1)

    task_dir = plan_context.plan_dir_for('add-fname') / 'tasks'
    files = list(task_dir.glob('TASK-001.json'))
    assert len(files) == 1
    assert files[0].name == 'TASK-001.json'


def test_add_rejects_zero_deliverable_for_plan_origin(plan_context):
    """deliverable=0 is rejected for non-holistic origins."""
    toon = build_task_toon(
        title='Zero deliverable task',
        deliverable=0,
        domain='java',
        description='Invalid zero deliverable',
        steps=['src/main/java/Test.java'],
    )
    result = cmd_add(_add_ns(plan_id='add-zero-del', content=toon.replace('\n', '\\n')))

    assert result['status'] == 'error'
    assert 'deliverable' in result.get('message', '').lower()


def test_add_accepts_holistic_with_zero_deliverable(plan_context):
    """deliverable=0 is accepted for holistic origin tasks."""
    toon = build_task_toon(
        title='Holistic verification task',
        deliverable=0,
        domain='plan-marshall-plugin-dev',
        description='Bundle-wide verification',
        steps=['./pw verify plan-marshall'],
        origin='holistic',
    )
    result = cmd_add(_add_ns(plan_id='add-holistic', content=toon.replace('\n', '\\n')))

    assert result['status'] == 'success'
    assert result['file'] == 'TASK-001.json'


def test_add_fails_without_content(plan_context):
    """Add fails if the prepared TOON file is empty."""
    result = cmd_add(_add_ns(plan_id='add-empty', content=''))

    assert result['status'] == 'error'


def test_add_fails_without_deliverable(plan_context):
    """Add fails if deliverable is missing."""
    toon = """title: No deliverable
domain: java
description: Desc
steps:
  - src/main/java/Step.java (write-replace)"""
    result = cmd_add(_add_ns(plan_id='add-no-del', content=toon.replace('\n', '\\n')))

    assert result['status'] == 'error'
    assert 'deliverable' in result.get('message', '').lower()


def test_add_fails_with_invalid_deliverable(plan_context):
    """Add fails with invalid deliverable format."""
    toon = build_task_toon(
        title='Bad format',
        deliverable=0,
        domain='java',
        description='Desc',
        steps=['src/main/java/Component.java'],
    )
    result = cmd_add(_add_ns(plan_id='add-bad-del', content=toon.replace('\n', '\\n')))

    assert result['status'] == 'error'


def test_add_fails_without_domain(plan_context):
    """Add fails if domain is missing."""
    toon = """title: No domain
deliverable: 1
description: Desc
steps:
  - src/main/java/Step.java (write-replace)"""
    result = cmd_add(_add_ns(plan_id='add-no-dom', content=toon.replace('\n', '\\n')))

    assert result['status'] == 'error'
    assert 'domain' in result.get('message', '').lower()


def test_add_accepts_arbitrary_domain(plan_context):
    """Add accepts any domain value (domains are config-driven, not hardcoded)."""
    toon = build_task_toon(
        title='Python domain',
        deliverable=1,
        domain='python',
        description='Desc',
        steps=['src/main/python/script.py'],
    )
    result = cmd_add(_add_ns(plan_id='add-arb-dom', content=toon.replace('\n', '\\n')))

    assert result['status'] == 'success'
    assert result['task']['domain'] == 'python'


def test_add_fails_without_steps(plan_context):
    """Add fails if no steps provided."""
    toon = """title: No steps
deliverable: 1
domain: java
description: Desc"""
    result = cmd_add(_add_ns(plan_id='add-no-steps', content=toon.replace('\n', '\\n')))

    assert result['status'] == 'error'
    assert 'steps' in result.get('message', '').lower()


def test_add_with_dependencies(plan_context):
    """Add task with depends-on."""
    add_basic_task(plan_id='add-deps', title='First', deliverable=1)

    toon = build_task_toon(
        title='Second',
        deliverable=2,
        domain='java',
        description='Depends on first',
        steps=['src/main/java/Component.java'],
        depends_on='TASK-1',
    )
    result = cmd_add(_add_ns(plan_id='add-deps', content=toon.replace('\n', '\\n')))

    assert result['status'] == 'success'
    assert 'TASK-1' in result['task']['depends_on']


def test_add_with_verification(plan_context):
    """Add task with verification block."""
    toon = build_task_toon(
        title='Verified task',
        deliverable=1,
        domain='java',
        description='Task with verification',
        steps=['src/main/java/Component.java'],
        verification_commands=['mvn test', 'mvn verify'],
        verification_criteria='Build passes',
    )
    result = cmd_add(_add_ns(plan_id='add-verif', content=toon.replace('\n', '\\n')))

    assert result['status'] == 'success'


def test_add_with_shell_metacharacters_in_verification(plan_context):
    """Add task with shell metacharacters in verification commands (the original issue)."""
    toon = build_task_toon(
        title='Task with complex verification',
        deliverable=1,
        domain='plan-marshall-plugin-dev',
        description='Migrate outputs from JSON to TOON',
        steps=['Update agent1.md', 'Update agent2.md'],
        verification_commands=["grep -l '```json' marketplace/bundles/*.md | wc -l"],
        verification_criteria='All grep commands return 0',
    )
    result = cmd_add(_add_ns(plan_id='add-shell-meta', content=toon.replace('\n', '\\n')))

    assert result['status'] == 'success'

    task_dir = plan_context.plan_dir_for('add-shell-meta') / 'tasks'
    files = list(task_dir.glob('TASK-001.json'))
    content = files[0].read_text(encoding='utf-8')
    assert "grep -l '```json'" in content
    assert '| wc -l' in content


# =============================================================================
# Tests: parse_stdin_task verification.commands quoting (fail-fast contract)
# =============================================================================
#
# These tests guard the contract that `verification.commands` list items must
# be written as bare hyphenated items with literal inner double-quotes — the
# anti-pattern of wrapping the whole item in outer double-quotes with escaped
# inner quotes must be rejected at parse time with a pointed error.
# See `plan-marshall:phase-4-plan` SKILL.md for the authoring rule.


def test_parse_stdin_task_accepts_inner_double_quotes_in_verification_command():
    """Positive: bare verification.commands item with literal inner double-quotes parses verbatim."""
    canonical_command = (
        'python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build '
        'run --command-args "module-tests plan-marshall"'
    )
    toon = (
        'title: Inner quotes positive\n'
        'deliverable: 1\n'
        'domain: plan-marshall-plugin-dev\n'
        'description: Parses verification command with inner double-quotes\n'
        'steps:\n'
        '  - test/plan-marshall/manage-tasks/test_manage_tasks.py (write-replace)\n'
        'depends_on: none\n'
        'verification:\n'
        '  commands:\n'
        f'    - {canonical_command}\n'
        '  criteria: tests pass\n'
    )

    parsed = parse_stdin_task(toon)

    assert parsed['verification']['commands'] == [canonical_command]
    assert '"module-tests plan-marshall"' in parsed['verification']['commands'][0]


def test_parse_stdin_task_rejects_outer_double_quoted_verification_command():
    """Negative: outer-double-quoted verification.commands item raises ValueError."""
    offending_item = (
        r'"python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build '
        r'run --command-args \"module-tests plan-marshall\""'
    )
    toon = (
        'title: Outer quotes negative\n'
        'deliverable: 1\n'
        'domain: plan-marshall-plugin-dev\n'
        'description: Outer-quoted verification command should fail fast\n'
        'steps:\n'
        '  - test/plan-marshall/manage-tasks/test_manage_tasks.py (write-replace)\n'
        'depends_on: none\n'
        'verification:\n'
        '  commands:\n'
        f'    - {offending_item}\n'
        '  criteria: must reject outer quoting\n'
    )

    with pytest.raises(ValueError) as excinfo:
        parse_stdin_task(toon)

    message = str(excinfo.value)
    assert 'verification.commands' in message
    assert 'outer double-quotes' in message
    assert 'plan-marshall:phase-4-plan' in message


def test_parse_stdin_task_rejects_outer_double_quoted_verification_profile_step():
    """Negative: outer-double-quoted step under verification profile raises ValueError."""
    offending_step = (
        r'"python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build '
        r'run --command-args \"quality-gate plan-marshall\""'
    )
    toon = (
        'title: Outer-quoted verification step should fail fast\n'
        'deliverable: 0\n'
        'domain: plan-marshall-plugin-dev\n'
        'profile: verification\n'
        'origin: holistic\n'
        'description: Verification-profile step must not be outer-quoted\n'
        'steps:\n'
        f'  - {offending_step}\n'
        'depends_on: none\n'
        'verification:\n'
        '  criteria: must reject outer quoting on steps\n'
    )

    with pytest.raises(ValueError) as excinfo:
        parse_stdin_task(toon)

    message = str(excinfo.value)
    assert 'steps' in message
    assert 'outer double-quotes' in message
    assert 'plan-marshall:phase-4-plan' in message


# =============================================================================
# Tests: required per-step intent marker (TOON commit-add path)
# =============================================================================


def _intent_toon(step_line, deliverable=1):
    return (
        'title: Intent task\n'
        f'deliverable: {deliverable}\n'
        'domain: plan-marshall-plugin-dev\n'
        'description: Intent round-trip\n'
        'steps:\n'
        f'  - {step_line}\n'
        'depends_on: none\n'
    )


@pytest.mark.parametrize('intent', ['read', 'write-new', 'write-replace', 'delete'])
def test_commit_add_stores_each_valid_intent(plan_context, intent):
    """Each valid intent round-trips into the stored TASK-NNN.json step dict."""
    toon = _intent_toon(f'src/main/java/Component.java ({intent})')
    result = _add_task(f'intent-store-{intent}', toon)

    assert result['status'] == 'success'
    task_dir = plan_context.plan_dir_for(f'intent-store-{intent}') / 'tasks'

    task = json.loads((task_dir / 'TASK-001.json').read_text(encoding='utf-8'))
    assert task['steps'][0]['intent'] == intent
    assert task['steps'][0]['target'] == 'src/main/java/Component.java'


def test_commit_add_rejects_bare_step_without_intent(plan_context):
    """A TOON step with no (intent) marker is rejected at parse time."""
    toon = _intent_toon('src/main/java/Component.java')
    result = _add_task('intent-missing', toon)

    assert result['status'] == 'error'
    assert 'intent' in result.get('message', '').lower()


def test_commit_add_rejects_invalid_intent(plan_context):
    """A present-but-invalid intent value is rejected at parse time."""
    toon = _intent_toon('src/main/java/Component.java (sideways)')
    result = _add_task('intent-invalid', toon)

    assert result['status'] == 'error'
    assert 'intent' in result.get('message', '').lower()


def test_parse_stdin_task_returns_target_intent_dicts():
    """parse_stdin_task returns each step as a {target, intent} dict."""
    toon = _intent_toon('src/main/java/A.java (write-new)')
    parsed = parse_stdin_task(toon)

    assert parsed['steps'] == [{'target': 'src/main/java/A.java', 'intent': 'write-new'}]
