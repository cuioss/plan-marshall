#!/usr/bin/env python3
"""Tests for manage-tasks.py script with the path-allocate add API.

Tier 2 (direct import) tests with 2-3 subprocess tests for CLI plumbing.

Add flow (path-allocate pattern):
    1. prepare-add → script returns a scratch path under <plan>/work/pending-tasks/
    2. Main context writes the TOON task definition to that path
    3. commit-add → script reads the file, validates, and creates TASK-NNN.json

The helper `_add_task` encapsulates all three steps for legacy test bodies.
"""

import json
import os
from argparse import Namespace
from pathlib import Path

import pytest

from conftest import PlanContext, get_script_path, run_script

# Script path for remaining subprocess (CLI plumbing) tests
SCRIPT_PATH = get_script_path('plan-marshall', 'manage-tasks', 'manage-tasks.py')

# Tier 2 direct imports via importlib (scripts loaded via PYTHONPATH at runtime)
import importlib.util  # noqa: E402

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


_crud = _load_module('_tasks_cmd_crud', '_tasks_crud.py')
_query = _load_module('_tasks_cmd_query', '_tasks_query.py')
_step = _load_module('_tasks_cmd_step', '_cmd_step.py')
_core = _load_module('_tasks_cmd_core', '_tasks_core.py')

parse_stdin_task = _core.parse_stdin_task

cmd_prepare_add = _crud.cmd_prepare_add
cmd_commit_add = _crud.cmd_commit_add
cmd_remove, cmd_update = _crud.cmd_remove, _crud.cmd_update


def cmd_add(ns):
    """Test shim: drive the three-step path-allocate add flow.

    Accepts the legacy `Namespace(plan_id, content)` shape where `content`
    is a newline-escaped TOON string, decodes it, writes it to the scratch
    path allocated by `prepare-add`, and finally calls `commit-add`. This
    keeps the existing assertion bodies intact while exercising the real
    path-allocate code paths end-to-end.
    """
    text = (ns.content or '').replace('\\n', '\n')
    if not text.strip():
        return _add_task_empty(ns.plan_id)
    return _add_task(ns.plan_id, text)
cmd_read, cmd_list, cmd_next = _query.cmd_read, _query.cmd_list, _query.cmd_next
cmd_exists = _query.cmd_exists
cmd_next_tasks, cmd_tasks_by_domain, cmd_tasks_by_profile = (
    _query.cmd_next_tasks,
    _query.cmd_tasks_by_domain,
    _query.cmd_tasks_by_profile,
)
cmd_add_step, cmd_finalize_step, cmd_remove_step = _step.cmd_add_step, _step.cmd_finalize_step, _step.cmd_remove_step


# =============================================================================
# Test Helpers
# =============================================================================


def build_task_toon(
    title='Test task',
    deliverable=None,
    domain='java',
    description='Task description',
    steps=None,
    depends_on='none',
    verification_commands=None,
    verification_criteria='',
    origin=None,
):
    """Build TOON content for task definition via stdin.

    Steps MUST be file paths per task contract (plan-type-api/standards/task-contract.md).
    """
    if deliverable is None:
        deliverable = 1
    if steps is None:
        # Default steps must be file paths (contract enforcement)
        steps = ['src/main/java/TestFile.java']
    if verification_commands is None:
        verification_commands = []

    lines = [
        f'title: {title}',
        f'deliverable: {deliverable}',
        f'domain: {domain}',
        f'description: {description}',
        'steps:',
    ]

    if origin is not None:
        lines.insert(3, f'origin: {origin}')

    for step in steps:
        lines.append(f'  - {step}')

    lines.append(f'depends_on: {depends_on}')

    if verification_commands or verification_criteria:
        lines.append('verification:')
        if verification_commands:
            lines.append('  commands:')
            for cmd in verification_commands:
                lines.append(f'    - {cmd}')
        if verification_criteria:
            lines.append(f'  criteria: {verification_criteria}')

    return '\n'.join(lines)


def _add_ns(plan_id='test-plan', content=''):
    """Compatibility helper for the legacy add-test call shape.

    Returns a Namespace the test shim `cmd_add` knows how to consume:
    the shim decodes the escaped-newline content, writes it to the
    scratch path allocated by `prepare-add`, and then invokes
    `commit-add` to create the task record.
    """
    return Namespace(plan_id=plan_id, content=content)


def _prepare_add_ns(plan_id='test-plan', slot=None):
    """Build Namespace for cmd_prepare_add."""
    return Namespace(plan_id=plan_id, slot=slot)


def _commit_add_ns(plan_id='test-plan', slot=None):
    """Build Namespace for cmd_commit_add."""
    return Namespace(plan_id=plan_id, slot=slot)


def _add_task(plan_id, toon_text, slot=None):
    """Run the three-step add flow end-to-end and return the commit result.

    Step 1: allocate scratch path via prepare-add.
    Step 2: write the TOON task definition to that path.
    Step 3: call commit-add to validate and persist TASK-NNN.json.
    """
    prep = cmd_prepare_add(_prepare_add_ns(plan_id=plan_id, slot=slot))
    if prep.get('status') != 'success':
        return prep
    Path(prep['path']).write_text(toon_text, encoding='utf-8')
    return cmd_commit_add(_commit_add_ns(plan_id=plan_id, slot=slot))


def _add_task_empty(plan_id, slot=None):
    """Run prepare-add and commit-add with an empty scratch file."""
    prep = cmd_prepare_add(_prepare_add_ns(plan_id=plan_id, slot=slot))
    if prep.get('status') != 'success':
        return prep
    Path(prep['path']).write_text('', encoding='utf-8')
    return cmd_commit_add(_commit_add_ns(plan_id=plan_id, slot=slot))


def _read_ns(plan_id='test-plan', number=1):
    """Build Namespace for cmd_read."""
    return Namespace(plan_id=plan_id, task_number=number)


def _exists_ns(plan_id='test-plan', number=1):
    """Build Namespace for cmd_exists."""
    return Namespace(plan_id=plan_id, task_number=number)


def _list_ns(plan_id='test-plan', status='all', deliverable=None, ready=False):
    """Build Namespace for cmd_list."""
    return Namespace(plan_id=plan_id, status=status, deliverable=deliverable, ready=ready)


def _next_ns(plan_id='test-plan', include_context=False, ignore_deps=False):
    """Build Namespace for cmd_next."""
    return Namespace(plan_id=plan_id, include_context=include_context, ignore_deps=ignore_deps)


def _update_ns(
    plan_id='test-plan',
    number=1,
    title=None,
    description=None,
    depends_on=None,
    status=None,
    domain=None,
    profile=None,
    skills=None,
    deliverable=None,
):
    """Build Namespace for cmd_update."""
    return Namespace(
        plan_id=plan_id,
        task_number=number,
        title=title,
        description=description,
        depends_on=depends_on,
        status=status,
        domain=domain,
        profile=profile,
        skills=skills,
        deliverable=deliverable,
    )


def _remove_ns(plan_id='test-plan', number=1):
    """Build Namespace for cmd_remove."""
    return Namespace(plan_id=plan_id, task_number=number)


def _finalize_step_ns(plan_id='test-plan', task=1, step=1, outcome='done', reason=None):
    """Build Namespace for cmd_finalize_step."""
    return Namespace(plan_id=plan_id, task_number=task, step=step, outcome=outcome, reason=reason)


def _add_step_ns(plan_id='test-plan', task=1, target='New Step', after=None):
    """Build Namespace for cmd_add_step."""
    return Namespace(plan_id=plan_id, task_number=task, target=target, after=after)


def _remove_step_ns(plan_id='test-plan', task=1, step=1):
    """Build Namespace for cmd_remove_step."""
    return Namespace(plan_id=plan_id, task_number=task, step=step)


def _tasks_by_domain_ns(plan_id='test-plan', domain='java'):
    """Build Namespace for cmd_tasks_by_domain."""
    return Namespace(plan_id=plan_id, domain=domain)


def _tasks_by_profile_ns(plan_id='test-plan', profile='implementation'):
    """Build Namespace for cmd_tasks_by_profile."""
    return Namespace(plan_id=plan_id, profile=profile)


def _next_tasks_ns(plan_id='test-plan'):
    """Build Namespace for cmd_next_tasks."""
    return Namespace(plan_id=plan_id)


def add_basic_task(
    plan_id='test-plan',
    title='Test task',
    deliverable=1,
    domain='java',
    description='Task description',
    steps=None,
    depends_on='none',
    origin=None,
):
    """Helper to add a task with minimal required params via direct import."""
    toon = build_task_toon(
        title=title,
        deliverable=deliverable,
        domain=domain,
        description=description,
        steps=steps,
        depends_on=depends_on,
        origin=origin,
    )
    return cmd_add(_add_ns(plan_id=plan_id, content=toon.replace('\n', '\\n')))


# =============================================================================
# Tests: add command with stdin-based API
# =============================================================================


def test_add_first_task():
    """Add first task creates TASK-001."""
    with PlanContext(plan_id='add-first'):
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

        # Verify file exists
        task_dir = Path(os.environ['PLAN_BASE_DIR']) / 'plans' / 'add-first' / 'tasks'
        files = list(task_dir.glob('TASK-001.json'))
        assert len(files) == 1, f'Expected 1 file, got {files}'


def test_add_sequential_numbering():
    """Adding multiple tasks gets sequential numbers."""
    with PlanContext(plan_id='add-seq'):
        add_basic_task(plan_id='add-seq', title='First', deliverable=1, steps=['src/main/java/First.java'])
        result = add_basic_task(
            plan_id='add-seq',
            title='Second',
            deliverable=2,
            steps=['src/main/java/Second.java', 'src/test/java/SecondTest.java'],
        )

        assert result['file'] == 'TASK-002.json'
        assert result['total_tasks'] == 2


def test_add_creates_numbered_filename():
    """Filename uses TASK-NNN format (not slug or type suffix)."""
    with PlanContext(plan_id='add-fname'):
        add_basic_task(plan_id='add-fname', title='Implement JWT Service!', deliverable=1)

        task_dir = Path(os.environ['PLAN_BASE_DIR']) / 'plans' / 'add-fname' / 'tasks'
        files = list(task_dir.glob('TASK-001.json'))
        assert len(files) == 1
        assert files[0].name == 'TASK-001.json'


def test_add_rejects_zero_deliverable_for_plan_origin():
    """deliverable=0 is rejected for non-holistic origins."""
    with PlanContext(plan_id='add-zero-del'):
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


def test_add_accepts_holistic_with_zero_deliverable():
    """deliverable=0 is accepted for holistic origin tasks."""
    with PlanContext(plan_id='add-holistic'):
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


def test_add_fails_without_content():
    """Add fails if the prepared TOON file is empty."""
    with PlanContext(plan_id='add-empty'):
        result = cmd_add(_add_ns(plan_id='add-empty', content=''))

        assert result['status'] == 'error'


def test_add_fails_without_deliverable():
    """Add fails if deliverable is missing."""
    with PlanContext(plan_id='add-no-del'):
        toon = """title: No deliverable
domain: java
description: Desc
steps:
  - Step 1"""
        result = cmd_add(_add_ns(plan_id='add-no-del', content=toon.replace('\n', '\\n')))

        assert result['status'] == 'error'
        assert 'deliverable' in result.get('message', '').lower()


def test_add_fails_with_invalid_deliverable():
    """Add fails with invalid deliverable format."""
    with PlanContext(plan_id='add-bad-del'):
        toon = build_task_toon(
            title='Bad format',
            deliverable=0,
            domain='java',
            description='Desc',
            steps=['src/main/java/Component.java'],
        )
        result = cmd_add(_add_ns(plan_id='add-bad-del', content=toon.replace('\n', '\\n')))

        assert result['status'] == 'error'


def test_add_fails_without_domain():
    """Add fails if domain is missing."""
    with PlanContext(plan_id='add-no-dom'):
        toon = """title: No domain
deliverable: 1
description: Desc
steps:
  - Step 1"""
        result = cmd_add(_add_ns(plan_id='add-no-dom', content=toon.replace('\n', '\\n')))

        assert result['status'] == 'error'
        assert 'domain' in result.get('message', '').lower()


def test_add_accepts_arbitrary_domain():
    """Add accepts any domain value (domains are config-driven, not hardcoded)."""
    with PlanContext(plan_id='add-arb-dom'):
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


def test_add_fails_without_steps():
    """Add fails if no steps provided."""
    with PlanContext(plan_id='add-no-steps'):
        toon = """title: No steps
deliverable: 1
domain: java
description: Desc"""
        result = cmd_add(_add_ns(plan_id='add-no-steps', content=toon.replace('\n', '\\n')))

        assert result['status'] == 'error'
        assert 'steps' in result.get('message', '').lower()


def test_add_with_dependencies():
    """Add task with depends-on."""
    with PlanContext(plan_id='add-deps'):
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


def test_add_with_verification():
    """Add task with verification block."""
    with PlanContext(plan_id='add-verif'):
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


def test_add_with_shell_metacharacters_in_verification():
    """Add task with shell metacharacters in verification commands (the original issue)."""
    with PlanContext(plan_id='add-shell-meta'):
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

        # Verify the verification commands were stored correctly
        task_dir = Path(os.environ['PLAN_BASE_DIR']) / 'plans' / 'add-shell-meta' / 'tasks'
        files = list(task_dir.glob('TASK-001.json'))
        content = files[0].read_text(encoding='utf-8')
        assert "grep -l '```json'" in content
        assert '| wc -l' in content


# =============================================================================
# Tests: read
# =============================================================================


def test_get_existing_task():
    """Read returns full task details."""
    with PlanContext(plan_id='get-exist'):
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


def test_get_nonexistent_returns_error():
    """Read nonexistent task returns error."""
    with PlanContext(plan_id='get-noexist'):
        result = cmd_read(_read_ns(plan_id='get-noexist', number=99))

        assert result['status'] == 'error'
        assert 'TASK-99' in result.get('message', '')


def test_get_returns_verification_block():
    """Read returns verification block details."""
    with PlanContext(plan_id='get-verif'):
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


def test_exists_returns_true_for_present_task():
    """exists returns status: success exists: true for a task that was added."""
    with PlanContext(plan_id='exists-present'):
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


def test_exists_returns_false_for_absent_task():
    """exists never errors on absence — returns status: success exists: false."""
    with PlanContext(plan_id='exists-absent'):
        result = cmd_exists(_exists_ns(plan_id='exists-absent', number=99))

        assert result['status'] == 'success'
        assert result['exists'] is False
        assert result['task'] == 99
        # The defining contract: presence probe must NOT report status: error,
        # otherwise the executor records a recoverable [ERROR] row in
        # script-execution.log (the entire reason exists exists).
        assert 'message' not in result


def test_exists_rejects_non_integer_task_argument():
    """exists CLI rejects malformed --task-number input (argparse type=int).

    Drives the subprocess wrapper to confirm the argparse layer rejects a
    non-integer task value with exit code 2 (argparse error), matching how
    read and other typed task arguments behave for malformed input.
    """
    result = run_script(SCRIPT_PATH, 'exists', '--plan-id', 'exists-bad-arg', '--task-number', 'abc')

    assert result.returncode == 2
    assert 'invalid int value' in result.stderr


# =============================================================================
# Tests: list
# =============================================================================


def test_list_empty():
    """List with no tasks shows zero counts."""
    with PlanContext(plan_id='list-empty'):
        result = cmd_list(_list_ns(plan_id='list-empty'))

        assert result['status'] == 'success'
        assert result['counts']['total'] == 0


def test_list_with_tasks():
    """List shows all tasks in table format with domain, profile and deliverables."""
    with PlanContext(plan_id='list-tasks'):
        add_basic_task(plan_id='list-tasks', title='First', deliverable=1, steps=['src/main/java/File.java'])
        add_basic_task(
            plan_id='list-tasks',
            title='Second',
            deliverable=2,
            steps=['src/main/java/FileA.java', 'src/main/java/FileB.java'],
        )

        result = cmd_list(_list_ns(plan_id='list-tasks'))

        assert result['status'] == 'success'
        assert result['counts']['total'] == 2
        assert len(result['tasks_table']) == 2
        # Check table row content
        assert result['tasks_table'][0]['number'] == 1
        assert result['tasks_table'][0]['title'] == 'First'
        assert result['tasks_table'][0]['domain'] == 'java'
        assert result['tasks_table'][0]['progress'] == '0/1'
        assert result['tasks_table'][1]['progress'] == '0/2'


def test_list_filter_by_status():
    """List can filter by status."""
    with PlanContext(plan_id='list-status'):
        add_basic_task(plan_id='list-status', title='First', deliverable=1, steps=['src/main/java/File.java'])
        add_basic_task(plan_id='list-status', title='Second', deliverable=2, steps=['src/main/java/File.java'])
        # Mark first task as done by finalizing its only step
        cmd_finalize_step(_finalize_step_ns(plan_id='list-status', task=1, step=1, outcome='done'))

        result = cmd_list(_list_ns(plan_id='list-status', status='pending'))

        assert result['status'] == 'success'
        assert len(result['tasks_table']) == 1
        assert result['tasks_table'][0]['title'] == 'Second'


def test_list_filter_by_deliverable():
    """List can filter by deliverable number."""
    with PlanContext(plan_id='list-del'):
        add_basic_task(plan_id='list-del', title='First', deliverable=1, steps=['src/main/java/File.java'])
        add_basic_task(plan_id='list-del', title='Second', deliverable=1, steps=['src/main/java/File.java'])
        add_basic_task(plan_id='list-del', title='Third', deliverable=2, steps=['src/main/java/File.java'])

        result = cmd_list(_list_ns(plan_id='list-del', deliverable=1))

        assert result['status'] == 'success'
        assert result['counts']['total'] == 2
        titles = [t['title'] for t in result['tasks_table']]
        assert 'First' in titles
        assert 'Second' in titles
        assert 'Third' not in titles


def test_list_filter_ready():
    """List --ready shows only tasks with satisfied dependencies."""
    with PlanContext(plan_id='list-ready'):
        add_basic_task(plan_id='list-ready', title='First', deliverable=1, steps=['src/main/java/File.java'])

        toon = build_task_toon(
            title='Second',
            deliverable=2,
            domain='java',
            description='D2',
            steps=['src/main/java/File.java'],
            depends_on='TASK-1',
        )
        cmd_add(_add_ns(plan_id='list-ready', content=toon.replace('\n', '\\n')))

        result = cmd_list(_list_ns(plan_id='list-ready', ready=True))

        assert result['status'] == 'success'
        titles = [t['title'] for t in result['tasks_table']]
        assert 'First' in titles
        assert 'Second' not in titles


# =============================================================================
# Tests: next with dependency checking
# =============================================================================


def test_next_returns_first_pending():
    """Next returns first pending task and step."""
    with PlanContext(plan_id='next-first'):
        toon = build_task_toon(
            title='First Task',
            deliverable=1,
            domain='java',
            description='D1',
            steps=['src/main/java/One.java', 'src/main/java/Two.java'],
        )
        cmd_add(_add_ns(plan_id='next-first', content=toon.replace('\n', '\\n')))

        result = cmd_next(_next_ns(plan_id='next-first'))

        assert result['status'] == 'success'
        assert result['next']['task_number'] == 1
        assert result['next']['task_title'] == 'First Task'
        assert result['next']['step_number'] == 1
        assert 'One.java' in result['next']['step_target']


def test_next_returns_in_progress_task():
    """Next prioritizes in_progress tasks."""
    with PlanContext(plan_id='next-inprog'):
        add_basic_task(
            plan_id='next-inprog',
            title='First',
            deliverable=1,
            steps=['src/main/java/FileA.java', 'src/main/java/FileB.java'],
        )
        add_basic_task(plan_id='next-inprog', title='Second', deliverable=2, steps=['src/main/java/File.java'])
        # Complete first step to put task in_progress (still has step 2)
        cmd_finalize_step(_finalize_step_ns(plan_id='next-inprog', task=1, step=1, outcome='done'))

        result = cmd_next(_next_ns(plan_id='next-inprog'))

        assert result['status'] == 'success'
        assert result['next']['task_number'] == 1
        assert result['next']['step_number'] == 2


def test_next_returns_null_when_all_done():
    """Next returns null when all tasks complete."""
    with PlanContext(plan_id='next-done'):
        add_basic_task(plan_id='next-done', title='Only Task', deliverable=1, steps=['src/main/java/File.java'])
        cmd_finalize_step(_finalize_step_ns(plan_id='next-done', task=1, step=1, outcome='done'))

        result = cmd_next(_next_ns(plan_id='next-done'))

        assert result['status'] == 'success'
        assert result['next'] is None
        assert 'All tasks completed' in result['context']['message']


def test_next_empty_plan():
    """Next on empty plan returns null."""
    with PlanContext(plan_id='next-empty'):
        result = cmd_next(_next_ns(plan_id='next-empty'))

        assert result['status'] == 'success'
        assert result['next'] is None


def test_next_respects_dependencies():
    """Next skips tasks with unmet dependencies."""
    with PlanContext(plan_id='next-deps'):
        add_basic_task(plan_id='next-deps', title='First', deliverable=1, steps=['src/main/java/File.java'])

        toon = build_task_toon(
            title='Second',
            deliverable=2,
            domain='java',
            description='D2',
            steps=['src/main/java/File.java'],
            depends_on='TASK-1',
        )
        cmd_add(_add_ns(plan_id='next-deps', content=toon.replace('\n', '\\n')))

        result = cmd_next(_next_ns(plan_id='next-deps'))

        assert result['status'] == 'success'
        assert result['next']['task_number'] == 1
        assert result['next']['task_title'] == 'First'


def test_next_shows_blocked_tasks():
    """Next shows blocked tasks when all available are blocked."""
    with PlanContext(plan_id='next-blocked'):
        toon = build_task_toon(
            title='Blocked',
            deliverable=1,
            domain='java',
            description='D1',
            steps=['src/main/java/File.java'],
            depends_on='TASK-99',
        )
        cmd_add(_add_ns(plan_id='next-blocked', content=toon.replace('\n', '\\n')))

        result = cmd_next(_next_ns(plan_id='next-blocked'))

        assert result['status'] == 'success'
        assert result['next'] is None
        assert 'blocked_tasks' in result
        assert any('TASK-99' in str(bt.get('waiting_for', '')) for bt in result['blocked_tasks'])


def test_next_ignore_deps():
    """Next with --ignore-deps ignores dependency constraints."""
    with PlanContext(plan_id='next-igdeps'):
        toon = build_task_toon(
            title='Blocked',
            deliverable=1,
            domain='java',
            description='D1',
            steps=['src/main/java/File.java'],
            depends_on='TASK-99',
        )
        cmd_add(_add_ns(plan_id='next-igdeps', content=toon.replace('\n', '\\n')))

        result = cmd_next(_next_ns(plan_id='next-igdeps', ignore_deps=True))

        assert result['status'] == 'success'
        assert result['next']['task_number'] == 1
        assert result['next']['task_title'] == 'Blocked'


def test_next_include_context():
    """Next with --include-context includes deliverable details."""
    with PlanContext(plan_id='next-ctx'):
        toon = build_task_toon(
            title='Feature task',
            deliverable=1,
            domain='java',
            description='Task description',
            steps=['src/main/java/One.java', 'src/main/java/Two.java'],
        )
        cmd_add(_add_ns(plan_id='next-ctx', content=toon.replace('\n', '\\n')))

        result = cmd_next(_next_ns(plan_id='next-ctx', include_context=True))

        assert result['status'] == 'success'
        assert result['next']['task_number'] == 1
        assert result['next']['deliverable'] == 1
        assert 'deliverable_source' in result['next']


# =============================================================================
# Tests: finalize-step
# =============================================================================


def test_finalize_step_done_marks_completed():
    """finalize-step --outcome done marks step as done."""
    with PlanContext(plan_id='fin-done'):
        add_basic_task(
            plan_id='fin-done',
            title='Task',
            deliverable=1,
            steps=['src/main/java/FileA.java', 'src/main/java/FileB.java'],
        )

        result = cmd_finalize_step(_finalize_step_ns(plan_id='fin-done', task=1, step=1, outcome='done'))

        assert result['status'] == 'success'
        assert result['finalized']['outcome'] == 'done'
        assert result['next_step'] is not None
        assert result['next_step']['number'] == 2


def test_finalize_step_done_completes_task():
    """finalize-step --outcome done on last step marks task as done."""
    with PlanContext(plan_id='fin-complete'):
        add_basic_task(plan_id='fin-complete', title='Task', deliverable=1, steps=['src/main/java/File.java'])

        result = cmd_finalize_step(_finalize_step_ns(plan_id='fin-complete', task=1, step=1, outcome='done'))

        assert result['status'] == 'success'
        assert result['task_complete'] is True
        assert result['task_status'] == 'done'
        assert result['next_step'] is None


def test_finalize_step_skipped_marks_skipped():
    """finalize-step --outcome skipped marks step as skipped."""
    with PlanContext(plan_id='fin-skip'):
        add_basic_task(
            plan_id='fin-skip',
            title='Task',
            deliverable=1,
            steps=['src/main/java/FileA.java', 'src/main/java/FileB.java'],
        )

        result = cmd_finalize_step(
            _finalize_step_ns(
                plan_id='fin-skip',
                task=1,
                step=1,
                outcome='skipped',
                reason='Already done',
            )
        )

        assert result['status'] == 'success'
        assert result['finalized']['outcome'] == 'skipped'
        assert result['next_step'] is not None
        assert result['next_step']['number'] == 2


def test_finalize_step_skipped_completes_task():
    """Skipping last step via finalize-step marks task as done."""
    with PlanContext(plan_id='fin-skip-last'):
        add_basic_task(plan_id='fin-skip-last', title='Task', deliverable=1, steps=['src/main/java/File.java'])

        result = cmd_finalize_step(_finalize_step_ns(plan_id='fin-skip-last', task=1, step=1, outcome='skipped'))

        assert result['status'] == 'success'
        assert result['task_complete'] is True
        assert result['task_status'] == 'done'


def test_finalize_step_invalid_step():
    """finalize-step with invalid step number fails."""
    with PlanContext(plan_id='fin-invalid'):
        add_basic_task(plan_id='fin-invalid', title='Task', deliverable=1, steps=['src/main/java/File.java'])

        result = cmd_finalize_step(_finalize_step_ns(plan_id='fin-invalid', task=1, step=99, outcome='done'))

        assert result['status'] == 'error'
        assert 'Step 99 not found' in result.get('message', '')


def test_finalize_step_returns_progress():
    """finalize-step returns progress indicator."""
    with PlanContext(plan_id='fin-prog'):
        add_basic_task(
            plan_id='fin-prog',
            title='Task',
            deliverable=1,
            steps=['src/main/java/FileA.java', 'src/main/java/FileB.java', 'src/main/java/FileC.java'],
        )

        result = cmd_finalize_step(_finalize_step_ns(plan_id='fin-prog', task=1, step=1, outcome='done'))

        assert result['status'] == 'success'
        assert result['progress'] == '1/3'


# =============================================================================
# Tests: finalize-step --outcome failed
# =============================================================================


def test_finalize_step_failed_marks_failed():
    """finalize-step --outcome failed marks step as failed."""
    with PlanContext(plan_id='fin-fail'):
        add_basic_task(
            plan_id='fin-fail',
            title='Task',
            deliverable=1,
            steps=['src/main/java/FileA.java', 'src/main/java/FileB.java'],
        )

        result = cmd_finalize_step(
            _finalize_step_ns(
                plan_id='fin-fail',
                task=1,
                step=1,
                outcome='failed',
                reason='Verification failed',
            )
        )

        assert result['status'] == 'success'
        assert result['finalized']['outcome'] == 'failed'
        assert result['finalized']['reason'] == 'Verification failed'
        assert result['next_step'] is not None
        assert result['next_step']['number'] == 2


def test_finalize_step_failed_completes_task_as_failed():
    """Failing last step via finalize-step marks task as failed (not done)."""
    with PlanContext(plan_id='fin-fail-last'):
        add_basic_task(plan_id='fin-fail-last', title='Task', deliverable=1, steps=['src/main/java/File.java'])

        result = cmd_finalize_step(
            _finalize_step_ns(plan_id='fin-fail-last', task=1, step=1, outcome='failed', reason='Build broke')
        )

        assert result['status'] == 'success'
        assert result['task_complete'] is True
        assert result['task_status'] == 'failed'


def test_finalize_step_mixed_done_and_failed_marks_task_failed():
    """Task with mix of done and failed steps gets status 'failed'."""
    with PlanContext(plan_id='fin-mixed'):
        add_basic_task(
            plan_id='fin-mixed',
            title='Task',
            deliverable=1,
            steps=['src/main/java/FileA.java', 'src/main/java/FileB.java'],
        )

        cmd_finalize_step(_finalize_step_ns(plan_id='fin-mixed', task=1, step=1, outcome='done'))
        result = cmd_finalize_step(
            _finalize_step_ns(plan_id='fin-mixed', task=1, step=2, outcome='failed', reason='Test failed')
        )

        assert result['status'] == 'success'
        assert result['task_complete'] is True
        assert result['task_status'] == 'failed'


def test_finalize_step_all_done_no_failed_marks_task_done():
    """Task with all done steps (no failed) still gets status 'done'."""
    with PlanContext(plan_id='fin-all-done'):
        add_basic_task(
            plan_id='fin-all-done',
            title='Task',
            deliverable=1,
            steps=['src/main/java/FileA.java', 'src/main/java/FileB.java'],
        )

        cmd_finalize_step(_finalize_step_ns(plan_id='fin-all-done', task=1, step=1, outcome='done'))
        result = cmd_finalize_step(_finalize_step_ns(plan_id='fin-all-done', task=1, step=2, outcome='done'))

        assert result['task_status'] == 'done'


def test_list_surfaces_failed_count():
    """List command includes failed count in counts."""
    with PlanContext(plan_id='list-fail-count'):
        add_basic_task(plan_id='list-fail-count', title='Task', deliverable=1, steps=['src/main/java/File.java'])
        cmd_finalize_step(
            _finalize_step_ns(plan_id='list-fail-count', task=1, step=1, outcome='failed', reason='Broke')
        )

        result = cmd_list(Namespace(plan_id='list-fail-count', status='all', deliverable=None, ready=False))

        assert result['counts']['failed'] == 1
        assert result['counts']['done'] == 0


# =============================================================================
# Tests: add-step
# =============================================================================


def test_add_step_appends():
    """Add-step appends to end by default."""
    with PlanContext(plan_id='addstep-app'):
        add_basic_task(
            plan_id='addstep-app',
            title='Task',
            deliverable=1,
            steps=['src/main/java/FileA.java', 'src/main/java/FileB.java'],
        )

        result = cmd_add_step(_add_step_ns(plan_id='addstep-app', task=1, target='New Step'))

        assert result['status'] == 'success'
        assert result['step'] == 3

        # Verify step count
        get_result = cmd_read(_read_ns(plan_id='addstep-app', number=1))
        assert len(get_result['task']['steps']) == 3


def test_add_step_after():
    """Add-step inserts after specified position."""
    with PlanContext(plan_id='addstep-aft'):
        add_basic_task(
            plan_id='addstep-aft',
            title='Task',
            deliverable=1,
            steps=['src/main/java/FileA.java', 'src/main/java/FileC.java'],
        )

        result = cmd_add_step(
            _add_step_ns(
                plan_id='addstep-aft',
                task=1,
                target='src/main/java/FileB.java',
                after=1,
            )
        )

        assert result['status'] == 'success'
        assert result['step'] == 2

        # Verify order
        get_result = cmd_read(_read_ns(plan_id='addstep-aft', number=1))
        steps = get_result['task']['steps']
        assert steps[0]['target'] == 'src/main/java/FileA.java'
        assert steps[1]['target'] == 'src/main/java/FileB.java'
        assert steps[2]['target'] == 'src/main/java/FileC.java'


# =============================================================================
# Tests: remove-step
# =============================================================================


def test_remove_step():
    """Remove-step removes and renumbers."""
    with PlanContext(plan_id='rmstep'):
        add_basic_task(
            plan_id='rmstep',
            title='Task',
            deliverable=1,
            steps=['src/main/java/FileA.java', 'src/main/java/FileB.java', 'src/main/java/FileC.java'],
        )

        result = cmd_remove_step(_remove_step_ns(plan_id='rmstep', task=1, step=2))

        assert result['status'] == 'success'
        assert 'Step 2 removed' in result.get('message', '')

        # Verify renumbering
        get_result = cmd_read(_read_ns(plan_id='rmstep', number=1))
        steps = get_result['task']['steps']
        assert len(steps) == 2
        assert steps[0]['target'] == 'src/main/java/FileA.java'
        assert steps[1]['target'] == 'src/main/java/FileC.java'


def test_remove_step_last_fails():
    """Cannot remove the last step."""
    with PlanContext(plan_id='rmstep-last'):
        add_basic_task(plan_id='rmstep-last', title='Task', deliverable=1, steps=['src/main/java/File.java'])

        result = cmd_remove_step(_remove_step_ns(plan_id='rmstep-last', task=1, step=1))

        assert result['status'] == 'error'
        assert 'Cannot remove the last step' in result.get('message', '')


# =============================================================================
# Tests: update
# =============================================================================


def test_update_title_keeps_filename():
    """Updating title does NOT rename file (TASK-NNN format is stable)."""
    with PlanContext(plan_id='upd-title'):
        add_basic_task(plan_id='upd-title', title='Old Title', deliverable=1, steps=['src/main/java/File.java'])

        task_dir = Path(os.environ['PLAN_BASE_DIR']) / 'plans' / 'upd-title' / 'tasks'
        initial_files = list(task_dir.glob('TASK-001.json'))
        assert len(initial_files) == 1, 'Should have TASK-001.json'

        result = cmd_update(_update_ns(plan_id='upd-title', number=1, title='New Title'))

        assert result['status'] == 'success'
        assert result['file'] == 'TASK-001.json'

        final_files = list(task_dir.glob('TASK-001.json'))
        assert len(final_files) == 1, 'File should still be TASK-001.json'


def test_update_depends_on():
    """Update depends_on field."""
    with PlanContext(plan_id='upd-deps'):
        add_basic_task(plan_id='upd-deps', title='Task', deliverable=1, steps=['src/main/java/File.java'])

        result = cmd_update(_update_ns(plan_id='upd-deps', number=1, depends_on=['TASK-5', 'TASK-6']))

        assert result['status'] == 'success'

        # Verify
        get_result = cmd_read(_read_ns(plan_id='upd-deps', number=1))
        assert 'TASK-5' in get_result['task']['depends_on']
        assert 'TASK-6' in get_result['task']['depends_on']


def test_update_clear_depends_on():
    """Update depends_on to none clears dependencies."""
    with PlanContext(plan_id='upd-clear-deps'):
        toon = build_task_toon(
            title='Task',
            deliverable=1,
            domain='java',
            description='D',
            steps=['src/main/java/File.java'],
            depends_on='TASK-1',
        )
        cmd_add(_add_ns(plan_id='upd-clear-deps', content=toon.replace('\n', '\\n')))

        result = cmd_update(_update_ns(plan_id='upd-clear-deps', number=1, depends_on=['none']))

        assert result['status'] == 'success'

        # Verify
        get_result = cmd_read(_read_ns(plan_id='upd-clear-deps', number=1))
        assert get_result['task']['depends_on'] == []


# =============================================================================
# Tests: remove
# =============================================================================


def test_remove_deletes_file():
    """Remove deletes the task file."""
    with PlanContext(plan_id='rm-del'):
        add_basic_task(plan_id='rm-del', title='To Delete', deliverable=1, steps=['src/main/java/File.java'])

        result = cmd_remove(_remove_ns(plan_id='rm-del', number=1))

        assert result['status'] == 'success'
        assert result['total_tasks'] == 0

        task_dir = Path(os.environ['PLAN_BASE_DIR']) / 'plans' / 'rm-del' / 'tasks'
        files = list(task_dir.glob('TASK-*.json'))
        assert len(files) == 0


def test_remove_preserves_gaps():
    """Removing a task preserves number gaps."""
    with PlanContext(plan_id='rm-gaps'):
        add_basic_task(plan_id='rm-gaps', title='First', deliverable=1, steps=['src/main/java/File.java'])
        add_basic_task(plan_id='rm-gaps', title='Second', deliverable=2, steps=['src/main/java/File.java'])
        add_basic_task(plan_id='rm-gaps', title='Third', deliverable=3, steps=['src/main/java/File.java'])

        cmd_remove(_remove_ns(plan_id='rm-gaps', number=2))

        result = add_basic_task(plan_id='rm-gaps', title='Fourth', deliverable=4, steps=['src/main/java/File.java'])

        assert result['file'] == 'TASK-004.json'


# =============================================================================
# Tests: progress tracking
# =============================================================================


def test_progress_calculation():
    """Progress is correctly calculated in list output."""
    with PlanContext(plan_id='prog-calc'):
        add_basic_task(
            plan_id='prog-calc',
            title='Task',
            deliverable=1,
            steps=['src/main/java/FileA.java', 'src/main/java/FileB.java', 'src/main/java/FileC.java'],
        )
        cmd_finalize_step(_finalize_step_ns(plan_id='prog-calc', task=1, step=1, outcome='done'))
        cmd_finalize_step(_finalize_step_ns(plan_id='prog-calc', task=1, step=2, outcome='skipped'))

        result = cmd_list(_list_ns(plan_id='prog-calc'))

        assert result['status'] == 'success'
        assert '2/3' in result['tasks_table'][0]['progress']


# =============================================================================
# Tests: file content verification
# =============================================================================


def test_file_contains_new_fields():
    """Created file contains all new fields (JSON format)."""
    with PlanContext(plan_id='file-fields'):
        toon = build_task_toon(
            title='Test task',
            deliverable=1,
            domain='java',
            description='Test description',
            steps=['src/main/java/File1.java', 'src/main/java/File2.java'],
            depends_on='none',
            verification_commands=['mvn test'],
            verification_criteria='Tests pass',
        )
        cmd_add(_add_ns(plan_id='file-fields', content=toon.replace('\n', '\\n')))

        task_dir = Path(os.environ['PLAN_BASE_DIR']) / 'plans' / 'file-fields' / 'tasks'
        files = list(task_dir.glob('TASK-001.json'))
        content = files[0].read_text(encoding='utf-8')

        task = json.loads(content)
        assert task['number'] == 1
        assert task['status'] == 'pending'
        assert task['deliverable'] == 1
        assert task['depends_on'] == []
        assert task['domain'] == 'java'
        assert 'verification' in task
        assert task['verification']['criteria'] == 'Tests pass'
        assert len(task['steps']) == 2
        assert task['steps'][0]['target'] == 'src/main/java/File1.java'
        assert task['steps'][0]['status'] == 'pending'
        assert task['current_step'] == 1


def test_deliverable_is_single_number_not_array():
    """Deliverable field is a single integer, not an array (1:1 constraint)."""
    with PlanContext(plan_id='del-single'):
        toon = build_task_toon(
            title='Test task',
            deliverable=1,
            domain='java',
            description='Test description',
            steps=['src/main/java/File1.java'],
        )
        cmd_add(_add_ns(plan_id='del-single', content=toon.replace('\n', '\\n')))

        task_dir = Path(os.environ['PLAN_BASE_DIR']) / 'plans' / 'del-single' / 'tasks'
        files = list(task_dir.glob('TASK-001.json'))
        content = files[0].read_text(encoding='utf-8')

        task = json.loads(content)
        assert 'deliverable' in task
        assert 'deliverables' not in task
        assert isinstance(task['deliverable'], int), f'Expected int, got {type(task["deliverable"])}'
        assert task['deliverable'] == 1


# =============================================================================
# Tests: numbered filename format
# =============================================================================


def test_numbered_filename_ignores_title_special_chars():
    """Filename uses TASK-NNN format regardless of special characters in title."""
    with PlanContext(plan_id='fname-special'):
        add_basic_task(plan_id='fname-special', title='Test@#$%Special!!!Characters', deliverable=1)

        task_dir = Path(os.environ['PLAN_BASE_DIR']) / 'plans' / 'fname-special' / 'tasks'
        files = list(task_dir.glob('TASK-001.json'))
        assert len(files) == 1, f'Expected TASK-001.json, found: {list(task_dir.glob("TASK-*.json"))}'


def test_numbered_filename_ignores_title_length():
    """Filename uses TASK-NNN format regardless of title length."""
    with PlanContext(plan_id='fname-long'):
        long_title = 'A' * 100
        add_basic_task(plan_id='fname-long', title=long_title, deliverable=1)

        task_dir = Path(os.environ['PLAN_BASE_DIR']) / 'plans' / 'fname-long' / 'tasks'
        files = list(task_dir.glob('TASK-001.json'))
        assert len(files) == 1, f'Expected TASK-001.json, found: {list(task_dir.glob("TASK-*.json"))}'


# =============================================================================
# Tests: domain validation
# =============================================================================


def test_arbitrary_domains_accepted():
    """Arbitrary domain strings are accepted (config-driven, not hardcoded)."""
    with PlanContext(plan_id='arb-domains'):
        domains = ['java', 'my-custom-domain', 'frontend-react', 'backend-api', 'devops']
        for i, domain in enumerate(domains, 1):
            toon = build_task_toon(
                title=f'Task {i}',
                deliverable=i,
                domain=domain,
                description=f'Test {domain}',
                steps=['src/main/java/File.java'],
            )
            result = cmd_add(_add_ns(plan_id='arb-domains', content=toon.replace('\n', '\\n')))
            assert result['status'] == 'success', f'Domain {domain} failed'


# =============================================================================
# Subprocess tests (CLI plumbing - Tier 3)
# =============================================================================


def test_cli_missing_subcommand_exits_2():
    """Missing subcommand exits with code 2 (argparse error)."""
    result = run_script(SCRIPT_PATH)
    assert result.returncode == 2


def test_cli_help_exits_0():
    """--help exits with code 0."""
    result = run_script(SCRIPT_PATH, '--help')
    assert result.returncode == 0
    assert 'manage implementation tasks' in result.stdout.lower()


def test_cli_legacy_add_subcommand_removed():
    """The legacy `add` subcommand has been removed (argparse error)."""
    result = run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan')
    assert result.returncode == 2


def test_cli_prepare_add_then_commit_add_roundtrip():
    """End-to-end CLI: prepare-add → write TOON → commit-add creates TASK-001."""
    from toon_parser import parse_toon  # type: ignore[import-not-found]

    with PlanContext(plan_id='cli-add-roundtrip'):
        prep = run_script(
            SCRIPT_PATH,
            'prepare-add',
            '--plan-id',
            'cli-add-roundtrip',
        )
        assert prep.success, f'prepare-add failed: {prep.stderr}'
        prep_data = parse_toon(prep.stdout)
        assert prep_data['status'] == 'success'
        scratch_path = Path(prep_data['path'])

        scratch_path.parent.mkdir(parents=True, exist_ok=True)
        scratch_path.write_text(
            'title: CLI Roundtrip\n'
            'deliverable: 1\n'
            'domain: java\n'
            'description: Roundtrip test\n'
            'steps:\n'
            '  - src/main/java/X.java\n'
            'depends_on: none\n',
            encoding='utf-8',
        )

        commit = run_script(
            SCRIPT_PATH,
            'commit-add',
            '--plan-id',
            'cli-add-roundtrip',
        )
        assert commit.success, f'commit-add failed: {commit.stderr}'
        commit_data = parse_toon(commit.stdout)
        assert commit_data['status'] == 'success'
        assert commit_data['file'] == 'TASK-001.json'
        # Scratch file is consumed on success
        assert not scratch_path.exists()


def test_cli_commit_add_without_prepare_fails():
    """commit-add without a prior prepare-add returns an error."""
    from toon_parser import parse_toon  # type: ignore[import-not-found]

    with PlanContext(plan_id='cli-add-missing'):
        result = run_script(
            SCRIPT_PATH,
            'commit-add',
            '--plan-id',
            'cli-add-missing',
        )
        # The script returns structured error TOON (exit 0) or non-zero;
        # either way, the status is error.
        data = parse_toon(result.stdout) if result.stdout else {}
        assert not result.success or data.get('status') == 'error'


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
    """Positive: bare verification.commands item with literal inner double-quotes parses verbatim.

    Given a TOON task definition whose verification.commands item contains literal
    inner double-quote characters (no outer wrapping),
    When parse_stdin_task parses the content,
    Then the command is stored verbatim, preserving the inner quote characters.
    """
    # Arrange
    canonical_command = (
        'python3 .plan/execute-script.py plan-marshall:build-python:python_build '
        'run --command-args "module-tests plan-marshall"'
    )
    toon = (
        'title: Inner quotes positive\n'
        'deliverable: 1\n'
        'domain: plan-marshall-plugin-dev\n'
        'description: Parses verification command with inner double-quotes\n'
        'steps:\n'
        '  - test/plan-marshall/manage-tasks/test_manage_tasks.py\n'
        'depends_on: none\n'
        'verification:\n'
        '  commands:\n'
        f'    - {canonical_command}\n'
        '  criteria: tests pass\n'
    )

    # Act
    parsed = parse_stdin_task(toon)

    # Assert
    assert parsed['verification']['commands'] == [canonical_command]
    assert '"module-tests plan-marshall"' in parsed['verification']['commands'][0]


def test_parse_stdin_task_rejects_outer_double_quoted_verification_command():
    """Negative: outer-double-quoted verification.commands item raises ValueError.

    Given a TOON task definition whose verification.commands item is wrapped in
    outer double quotes (with escaped inner quotes) — the anti-pattern,
    When parse_stdin_task parses the content,
    Then a ValueError is raised whose message points at the quoting rule and
    references `plan-marshall:phase-4-plan` SKILL.md.
    """
    # Arrange
    offending_item = (
        r'"python3 .plan/execute-script.py plan-marshall:build-python:python_build '
        r'run --command-args \"module-tests plan-marshall\""'
    )
    toon = (
        'title: Outer quotes negative\n'
        'deliverable: 1\n'
        'domain: plan-marshall-plugin-dev\n'
        'description: Outer-quoted verification command should fail fast\n'
        'steps:\n'
        '  - test/plan-marshall/manage-tasks/test_manage_tasks.py\n'
        'depends_on: none\n'
        'verification:\n'
        '  commands:\n'
        f'    - {offending_item}\n'
        '  criteria: must reject outer quoting\n'
    )

    # Act / Assert
    with pytest.raises(ValueError) as excinfo:
        parse_stdin_task(toon)

    message = str(excinfo.value)
    assert 'verification.commands' in message
    assert 'outer double-quotes' in message
    assert 'plan-marshall:phase-4-plan' in message


def test_parse_stdin_task_rejects_outer_double_quoted_verification_profile_step():
    """Negative: outer-double-quoted step under verification profile raises ValueError.

    Given a TOON task definition with profile=verification whose steps item is
    wrapped in outer double quotes — verification-profile tasks store commands
    in the steps field, so the same anti-pattern can land there,
    When parse_stdin_task parses the content,
    Then a ValueError is raised whose message references the steps contract and
    points at `plan-marshall:phase-4-plan` SKILL.md.
    """
    # Arrange
    offending_step = (
        r'"python3 .plan/execute-script.py plan-marshall:build-python:python_build '
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

    # Act / Assert
    with pytest.raises(ValueError) as excinfo:
        parse_stdin_task(toon)

    message = str(excinfo.value)
    assert 'steps' in message
    assert 'outer double-quotes' in message
    assert 'plan-marshall:phase-4-plan' in message
