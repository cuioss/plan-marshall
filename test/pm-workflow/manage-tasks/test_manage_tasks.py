#!/usr/bin/env python3
"""Tests for manage-tasks.py script with stdin-based add API."""

import os
import shutil
import sys
from pathlib import Path

# Import shared infrastructure
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import run_script, create_temp_dir, TestRunner, get_script_path

# Script under test
SCRIPT_PATH = get_script_path('pm-workflow', 'manage-tasks', 'manage-tasks.py')


# =============================================================================
# Test Helpers
# =============================================================================

def setup_plan_dir():
    """Create temp plan directory and set PLAN_BASE_DIR."""
    temp_dir = create_temp_dir()
    plan_base = temp_dir / '.plan'
    plan_base.mkdir()
    os.environ['PLAN_BASE_DIR'] = str(plan_base)

    # Create plan directory
    plan_dir = plan_base / 'plans' / 'test-plan'
    plan_dir.mkdir(parents=True)

    return temp_dir


def cleanup(temp_dir):
    """Clean up temp directory and env var."""
    if 'PLAN_BASE_DIR' in os.environ:
        del os.environ['PLAN_BASE_DIR']
    shutil.rmtree(temp_dir, ignore_errors=True)


def build_task_toon(title='Test task', deliverables=None, domain='java',
                    description='Task description', steps=None, phase='execute',
                    depends_on='none', delegation_skill='', delegation_workflow='',
                    context_skills=None, verification_commands=None,
                    verification_criteria=''):
    """Build TOON content for task definition via stdin.

    Steps MUST be file paths per task contract (plan-type-api/standards/task-contract.md).
    """
    if deliverables is None:
        deliverables = [1]
    if steps is None:
        # Default steps must be file paths (contract enforcement)
        steps = ['src/main/java/TestFile.java']
    if context_skills is None:
        context_skills = []
    if verification_commands is None:
        verification_commands = []

    # Build deliverables array string
    deliverables_str = '[' + ', '.join(str(d) for d in deliverables) + ']'

    lines = [
        f'title: {title}',
        f'deliverables: {deliverables_str}',
        f'domain: {domain}',
        f'phase: {phase}',
        f'description: {description}',
        'steps:'
    ]

    for step in steps:
        lines.append(f'  - {step}')

    lines.append(f'depends_on: {depends_on}')

    if delegation_skill or delegation_workflow or context_skills:
        lines.append('delegation:')
        if delegation_skill:
            lines.append(f'  skill: {delegation_skill}')
        if delegation_workflow:
            lines.append(f'  workflow: {delegation_workflow}')
        if context_skills:
            lines.append('  context_skills:')
            for skill in context_skills:
                lines.append(f'    - {skill}')

    if verification_commands or verification_criteria:
        lines.append('verification:')
        if verification_commands:
            lines.append('  commands:')
            for cmd in verification_commands:
                lines.append(f'    - {cmd}')
        if verification_criteria:
            lines.append(f'  criteria: {verification_criteria}')

    return '\n'.join(lines)


def add_basic_task(plan_id='test-plan', title='Test task', deliverables=None,
                   domain='java', description='Task description', steps=None):
    """Helper to add a task with minimal required params."""
    toon = build_task_toon(title=title, deliverables=deliverables,
                           domain=domain, description=description, steps=steps)
    return run_script(SCRIPT_PATH, 'add', '--plan-id', plan_id, input_data=toon)


# =============================================================================
# Tests: add command with stdin-based API
# =============================================================================

def test_add_first_task():
    """Add first task creates TASK-001."""
    temp_dir = setup_plan_dir()
    try:
        toon = build_task_toon(
            title='First task',
            deliverables=[1],
            domain='java',
            description='Task description',
            steps=['src/main/java/First.java', 'src/main/java/Second.java']  # File paths per contract
        )
        result = run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', input_data=toon)

        assert result.returncode == 0, f"Failed: {result.stderr}"
        assert 'status: success' in result.stdout
        assert 'TASK-001' in result.stdout
        assert 'total_tasks: 1' in result.stdout

        # Verify file exists
        task_dir = Path(os.environ['PLAN_BASE_DIR']) / 'plans' / 'test-plan' / 'tasks'
        files = list(task_dir.glob('TASK-001-*.toon'))
        assert len(files) == 1, f"Expected 1 file, got {files}"
    finally:
        cleanup(temp_dir)


def test_add_sequential_numbering():
    """Adding multiple tasks gets sequential numbers."""
    temp_dir = setup_plan_dir()
    try:
        add_basic_task(title='First', deliverables=[1], steps=['src/main/java/First.java'])
        result = add_basic_task(title='Second', deliverables=[2], steps=['src/main/java/Second.java', 'src/test/java/SecondTest.java'])

        assert result.returncode == 0
        assert 'TASK-002' in result.stdout
        assert 'total_tasks: 2' in result.stdout
    finally:
        cleanup(temp_dir)


def test_add_creates_type_based_filename():
    """Filename uses TASK-SEQ-TYPE format (not slug)."""
    temp_dir = setup_plan_dir()
    try:
        add_basic_task(title='Implement JWT Service!', deliverables=[1])

        task_dir = Path(os.environ['PLAN_BASE_DIR']) / 'plans' / 'test-plan' / 'tasks'
        files = list(task_dir.glob('TASK-001-*.toon'))
        assert len(files) == 1
        # Filename uses type suffix (default IMPL), not title slug
        assert files[0].name == 'TASK-001-IMPL.toon'
    finally:
        cleanup(temp_dir)


def test_add_multiple_deliverables():
    """Add task with multiple deliverables."""
    temp_dir = setup_plan_dir()
    try:
        toon = build_task_toon(
            title='Multi-deliverable task',
            deliverables=[1, 2, 3],
            domain='java',
            description='Task covers multiple deliverables',
            steps=['src/main/java/Test.java']
        )
        result = run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', input_data=toon)

        assert result.returncode == 0, f"Failed: {result.stderr}"
        assert 'status: success' in result.stdout
        assert 'deliverables: [1, 2, 3]' in result.stdout
    finally:
        cleanup(temp_dir)


def test_add_fails_without_stdin():
    """Add fails if no stdin provided."""
    temp_dir = setup_plan_dir()
    try:
        result = run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', input_data='')

        assert result.returncode != 0
        assert 'error' in result.stderr.lower()
    finally:
        cleanup(temp_dir)


def test_add_fails_without_deliverables():
    """Add fails if deliverables are missing."""
    temp_dir = setup_plan_dir()
    try:
        toon = """title: No deliverables
domain: java
description: Desc
steps:
  - Step 1"""
        result = run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', input_data=toon)

        assert result.returncode != 0
        assert 'deliverables' in result.stderr.lower()
    finally:
        cleanup(temp_dir)


def test_add_fails_with_invalid_deliverable():
    """Add fails with invalid deliverable format."""
    temp_dir = setup_plan_dir()
    try:
        toon = build_task_toon(
            title='Bad format',
            deliverables=[0],  # Must be positive
            domain='java',
            description='Desc',
            steps=['src/main/java/Component.java']
        )
        result = run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', input_data=toon)

        assert result.returncode == 1
        assert 'error' in result.stderr.lower()
    finally:
        cleanup(temp_dir)


def test_add_fails_without_domain():
    """Add fails if domain is missing."""
    temp_dir = setup_plan_dir()
    try:
        toon = """title: No domain
deliverables: [1]
description: Desc
steps:
  - Step 1"""
        result = run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', input_data=toon)

        assert result.returncode != 0
        assert 'domain' in result.stderr.lower()
    finally:
        cleanup(temp_dir)


def test_add_accepts_arbitrary_domain():
    """Add accepts any domain value (domains are config-driven, not hardcoded)."""
    temp_dir = setup_plan_dir()
    try:
        toon = build_task_toon(
            title='Python domain',
            deliverables=[1],
            domain='python',  # Arbitrary domain - now accepted
            description='Desc',
            steps=['src/main/python/script.py']
        )
        result = run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', input_data=toon)

        assert result.returncode == 0
        assert 'domain: python' in result.stdout
    finally:
        cleanup(temp_dir)


def test_add_fails_without_steps():
    """Add fails if no steps provided."""
    temp_dir = setup_plan_dir()
    try:
        toon = """title: No steps
deliverables: [1]
domain: java
description: Desc"""
        result = run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', input_data=toon)

        assert result.returncode != 0
        assert 'steps' in result.stderr.lower()
    finally:
        cleanup(temp_dir)


def test_add_with_phase():
    """Add task with specific phase."""
    temp_dir = setup_plan_dir()
    try:
        toon = build_task_toon(
            title='Init task',
            deliverables=[1],
            domain='java',
            phase='init',
            description='Init phase task',
            steps=['src/main/java/Component.java']
        )
        result = run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', input_data=toon)

        assert result.returncode == 0
        assert 'phase: init' in result.stdout
    finally:
        cleanup(temp_dir)


def test_add_with_dependencies():
    """Add task with depends-on."""
    temp_dir = setup_plan_dir()
    try:
        # Create first task
        add_basic_task(title='First', deliverables=[1])

        # Create second task depending on first
        toon = build_task_toon(
            title='Second',
            deliverables=[2],
            domain='java',
            description='Depends on first',
            steps=['src/main/java/Component.java'],
            depends_on='TASK-1'
        )
        result = run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', input_data=toon)

        assert result.returncode == 0
        assert 'depends_on: [TASK-1]' in result.stdout
    finally:
        cleanup(temp_dir)


def test_add_with_delegation():
    """Add task with delegation block."""
    temp_dir = setup_plan_dir()
    try:
        toon = build_task_toon(
            title='Delegated task',
            deliverables=[1],
            domain='java',
            description='Task with delegation',
            steps=['src/main/java/Component.java'],
            delegation_skill='pm-dev-java:java-implement',
            delegation_workflow='implement',
            context_skills=['pm-dev-java:java-cdi']
        )
        result = run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', input_data=toon)

        assert result.returncode == 0
        # Task created successfully
        assert 'status: success' in result.stdout
    finally:
        cleanup(temp_dir)


def test_add_with_verification():
    """Add task with verification block."""
    temp_dir = setup_plan_dir()
    try:
        toon = build_task_toon(
            title='Verified task',
            deliverables=[1],
            domain='java',
            description='Task with verification',
            steps=['src/main/java/Component.java'],
            verification_commands=['mvn test', 'mvn verify'],
            verification_criteria='Build passes'
        )
        result = run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', input_data=toon)

        assert result.returncode == 0
        assert 'status: success' in result.stdout
    finally:
        cleanup(temp_dir)


def test_add_with_shell_metacharacters_in_verification():
    """Add task with shell metacharacters in verification commands (the original issue)."""
    temp_dir = setup_plan_dir()
    try:
        toon = build_task_toon(
            title='Task with complex verification',
            deliverables=[1, 2, 3],
            domain='plan-marshall-plugin-dev',
            description='Migrate outputs from JSON to TOON',
            steps=['Update agent1.md', 'Update agent2.md'],
            delegation_skill='pm-plugin-development:plugin-maintain',
            delegation_workflow='update-component',
            verification_commands=["grep -l '```json' marketplace/bundles/*.md | wc -l"],
            verification_criteria='All grep commands return 0'
        )
        result = run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', input_data=toon)

        assert result.returncode == 0, f"Failed: {result.stderr}"
        assert 'status: success' in result.stdout

        # Verify the verification commands were stored correctly
        task_dir = Path(os.environ['PLAN_BASE_DIR']) / 'plans' / 'test-plan' / 'tasks'
        files = list(task_dir.glob('TASK-001-*.toon'))
        content = files[0].read_text(encoding='utf-8')
        assert "grep -l '```json'" in content
        assert '| wc -l' in content
    finally:
        cleanup(temp_dir)


# =============================================================================
# Tests: get
# =============================================================================

def test_get_existing_task():
    """Get returns full task details."""
    temp_dir = setup_plan_dir()
    try:
        toon = build_task_toon(
            title='Test task',
            deliverables=[1, 2],
            domain='java',
            description='Test description',
            steps=['src/main/java/One.java', 'src/main/java/Two.java', 'src/main/java/Three.java']
        )
        run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', input_data=toon)

        result = run_script(SCRIPT_PATH, 'get', '--plan-id', 'test-plan', '--number', '1')

        assert result.returncode == 0
        assert 'status: success' in result.stdout
        assert 'number: 1' in result.stdout
        assert 'Test task' in result.stdout
        assert 'deliverables: [1, 2]' in result.stdout
        assert 'Test description' in result.stdout
        assert 'One.java' in result.stdout  # Updated to file path
        assert 'Two.java' in result.stdout  # Updated to file path
    finally:
        cleanup(temp_dir)


def test_get_nonexistent_returns_error():
    """Get nonexistent task returns error."""
    temp_dir = setup_plan_dir()
    try:
        result = run_script(SCRIPT_PATH, 'get', '--plan-id', 'test-plan', '--number', '99')

        assert result.returncode == 1
        assert 'error' in result.stderr.lower()
        assert 'TASK-99' in result.stderr
    finally:
        cleanup(temp_dir)


def test_get_returns_delegation_block():
    """Get returns delegation block details."""
    temp_dir = setup_plan_dir()
    try:
        toon = build_task_toon(
            title='Delegated task',
            deliverables=[1],
            domain='plan-marshall-plugin-dev',
            description='Task with delegation',
            steps=['src/main/java/Component.java'],
            delegation_skill='pm-plugin-development:plugin-create',
            delegation_workflow='create-skill',
            context_skills=['pm-plugin-development:plugin-architecture']
        )
        run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', input_data=toon)

        result = run_script(SCRIPT_PATH, 'get', '--plan-id', 'test-plan', '--number', '1')

        assert result.returncode == 0
        assert 'delegation:' in result.stdout
        assert 'skill: pm-plugin-development:plugin-create' in result.stdout
        assert 'workflow: create-skill' in result.stdout
        assert 'domain: plan-marshall-plugin-dev' in result.stdout
    finally:
        cleanup(temp_dir)


def test_get_returns_verification_block():
    """Get returns verification block details."""
    temp_dir = setup_plan_dir()
    try:
        toon = build_task_toon(
            title='Verified task',
            deliverables=[1],
            domain='java',
            description='Task with verification',
            steps=['src/main/java/Component.java'],
            verification_commands=['mvn test'],
            verification_criteria='Tests pass'
        )
        run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', input_data=toon)

        result = run_script(SCRIPT_PATH, 'get', '--plan-id', 'test-plan', '--number', '1')

        assert result.returncode == 0
        assert 'verification:' in result.stdout
        assert 'criteria: Tests pass' in result.stdout
    finally:
        cleanup(temp_dir)


# =============================================================================
# Tests: list
# =============================================================================

def test_list_empty():
    """List with no tasks shows zero counts."""
    temp_dir = setup_plan_dir()
    try:
        result = run_script(SCRIPT_PATH, 'list', '--plan-id', 'test-plan')

        assert result.returncode == 0
        assert 'total: 0' in result.stdout
    finally:
        cleanup(temp_dir)


def test_list_with_tasks():
    """List shows all tasks in table format with domain, profile, phase and deliverables."""
    temp_dir = setup_plan_dir()
    try:
        add_basic_task(title='First', deliverables=[1], steps=['src/main/java/File.java'])
        add_basic_task(title='Second', deliverables=[2], steps=['src/main/java/FileA.java', 'src/main/java/FileB.java'])

        result = run_script(SCRIPT_PATH, 'list', '--plan-id', 'test-plan')

        assert result.returncode == 0
        assert 'total: 2' in result.stdout
        assert 'tasks[2]' in result.stdout
        # Format: {number,title,domain,profile,phase,deliverables,status,progress}
        assert '1,First,java,implementation,execute,[1],pending,0/1' in result.stdout
        assert '2,Second,java,implementation,execute,[2],pending,0/2' in result.stdout
    finally:
        cleanup(temp_dir)


def test_list_filter_by_status():
    """List can filter by status."""
    temp_dir = setup_plan_dir()
    try:
        add_basic_task(title='First', deliverables=[1], steps=['src/main/java/File.java'])
        add_basic_task(title='Second', deliverables=[2], steps=['src/main/java/File.java'])
        # Mark first task as in_progress
        run_script(SCRIPT_PATH, 'step-start', '--plan-id', 'test-plan', '--task', '1', '--step', '1')

        result = run_script(SCRIPT_PATH, 'list', '--plan-id', 'test-plan', '--status', 'pending')

        assert result.returncode == 0
        assert 'tasks[1]' in result.stdout
        assert '2,Second' in result.stdout
        assert '1,First' not in result.stdout
    finally:
        cleanup(temp_dir)


def test_list_filter_by_deliverable():
    """List can filter by deliverable number."""
    temp_dir = setup_plan_dir()
    try:
        add_basic_task(title='First', deliverables=[1], steps=['src/main/java/File.java'])
        add_basic_task(title='Second', deliverables=[1], steps=['src/main/java/File.java'])
        add_basic_task(title='Third', deliverables=[2], steps=['src/main/java/File.java'])

        result = run_script(SCRIPT_PATH, 'list', '--plan-id', 'test-plan', '--deliverable', '1')

        assert result.returncode == 0
        assert 'total: 2' in result.stdout
        assert 'First' in result.stdout
        assert 'Second' in result.stdout
        assert 'Third' not in result.stdout
    finally:
        cleanup(temp_dir)


def test_list_filter_by_phase():
    """List can filter by phase."""
    temp_dir = setup_plan_dir()
    try:
        toon_init = build_task_toon(
            title='Init Task', deliverables=[1], domain='java',
            phase='init', description='D1', steps=['src/main/java/File.java']
        )
        toon_exec = build_task_toon(
            title='Execute Task', deliverables=[2], domain='java',
            phase='execute', description='D2', steps=['src/main/java/File.java']
        )
        run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', input_data=toon_init)
        run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', input_data=toon_exec)

        result = run_script(SCRIPT_PATH, 'list', '--plan-id', 'test-plan', '--phase', 'init')

        assert result.returncode == 0
        assert 'Init Task' in result.stdout
        assert 'Execute Task' not in result.stdout
    finally:
        cleanup(temp_dir)


def test_list_filter_ready():
    """List --ready shows only tasks with satisfied dependencies."""
    temp_dir = setup_plan_dir()
    try:
        # First task - no deps
        add_basic_task(title='First', deliverables=[1], steps=['src/main/java/File.java'])

        # Second task - depends on first
        toon = build_task_toon(
            title='Second', deliverables=[2], domain='java',
            description='D2', steps=['src/main/java/File.java'], depends_on='TASK-1'
        )
        run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', input_data=toon)

        result = run_script(SCRIPT_PATH, 'list', '--plan-id', 'test-plan', '--ready')

        assert result.returncode == 0
        assert 'First' in result.stdout
        # Second is blocked by TASK-1
        assert 'Second' not in result.stdout
    finally:
        cleanup(temp_dir)


# =============================================================================
# Tests: next with dependency checking
# =============================================================================

def test_next_returns_first_pending():
    """Next returns first pending task and step."""
    temp_dir = setup_plan_dir()
    try:
        toon = build_task_toon(
            title='First Task', deliverables=[1], domain='java',
            description='D1', steps=['src/main/java/One.java', 'src/main/java/Two.java']
        )
        run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', input_data=toon)

        result = run_script(SCRIPT_PATH, 'next', '--plan-id', 'test-plan')

        assert result.returncode == 0
        assert 'task_number: 1' in result.stdout
        assert 'task_title: First Task' in result.stdout
        assert 'step_number: 1' in result.stdout
        assert 'One.java' in result.stdout  # File path instead of descriptive text
    finally:
        cleanup(temp_dir)


def test_next_returns_in_progress_task():
    """Next prioritizes in_progress tasks."""
    temp_dir = setup_plan_dir()
    try:
        add_basic_task(title='First', deliverables=[1], steps=['src/main/java/FileA.java', 'src/main/java/FileB.java'])
        add_basic_task(title='Second', deliverables=[2], steps=['src/main/java/File.java'])
        # Start first task
        run_script(SCRIPT_PATH, 'step-start', '--plan-id', 'test-plan', '--task', '1', '--step', '1')

        result = run_script(SCRIPT_PATH, 'next', '--plan-id', 'test-plan')

        assert result.returncode == 0
        assert 'task_number: 1' in result.stdout
        assert 'step_number: 1' in result.stdout
    finally:
        cleanup(temp_dir)


def test_next_returns_null_when_all_done():
    """Next returns null when all tasks complete."""
    temp_dir = setup_plan_dir()
    try:
        add_basic_task(title='Only Task', deliverables=[1], steps=['src/main/java/File.java'])
        run_script(SCRIPT_PATH, 'step-done', '--plan-id', 'test-plan', '--task', '1', '--step', '1')

        result = run_script(SCRIPT_PATH, 'next', '--plan-id', 'test-plan')

        assert result.returncode == 0
        assert 'next: null' in result.stdout
        assert 'All tasks completed' in result.stdout
    finally:
        cleanup(temp_dir)


def test_next_empty_plan():
    """Next on empty plan returns null."""
    temp_dir = setup_plan_dir()
    try:
        result = run_script(SCRIPT_PATH, 'next', '--plan-id', 'test-plan')

        assert result.returncode == 0
        assert 'next: null' in result.stdout
    finally:
        cleanup(temp_dir)


def test_next_respects_dependencies():
    """Next skips tasks with unmet dependencies."""
    temp_dir = setup_plan_dir()
    try:
        # First task - no deps
        add_basic_task(title='First', deliverables=[1], steps=['src/main/java/File.java'])

        # Second task - depends on first (blocked)
        toon = build_task_toon(
            title='Second', deliverables=[2], domain='java',
            description='D2', steps=['src/main/java/File.java'], depends_on='TASK-1'
        )
        run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', input_data=toon)

        result = run_script(SCRIPT_PATH, 'next', '--plan-id', 'test-plan')

        assert result.returncode == 0
        # Should return first task since second is blocked
        assert 'task_number: 1' in result.stdout
        assert 'task_title: First' in result.stdout
    finally:
        cleanup(temp_dir)


def test_next_shows_blocked_tasks():
    """Next shows blocked tasks when all available are blocked."""
    temp_dir = setup_plan_dir()
    try:
        # Create only task with dependency on non-existent task
        toon = build_task_toon(
            title='Blocked', deliverables=[1], domain='java',
            description='D1', steps=['src/main/java/File.java'], depends_on='TASK-99'
        )
        run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', input_data=toon)

        result = run_script(SCRIPT_PATH, 'next', '--plan-id', 'test-plan')

        assert result.returncode == 0
        assert 'next: null' in result.stdout
        assert 'blocked_tasks' in result.stdout
        assert 'TASK-99' in result.stdout
    finally:
        cleanup(temp_dir)


def test_next_ignore_deps():
    """Next with --ignore-deps ignores dependency constraints."""
    temp_dir = setup_plan_dir()
    try:
        # Only task with unmet dependency
        toon = build_task_toon(
            title='Blocked', deliverables=[1], domain='java',
            description='D1', steps=['src/main/java/File.java'], depends_on='TASK-99'
        )
        run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', input_data=toon)

        result = run_script(SCRIPT_PATH, 'next', '--plan-id', 'test-plan', '--ignore-deps')

        assert result.returncode == 0
        # Should return task despite unmet dependency
        assert 'task_number: 1' in result.stdout
        assert 'task_title: Blocked' in result.stdout
    finally:
        cleanup(temp_dir)


def test_next_filter_by_phase():
    """Next can filter by phase."""
    temp_dir = setup_plan_dir()
    try:
        toon_init = build_task_toon(
            title='Init Task', deliverables=[1], domain='java',
            phase='init', description='D1', steps=['src/main/java/File.java']
        )
        toon_exec = build_task_toon(
            title='Execute Task', deliverables=[2], domain='java',
            phase='execute', description='D2', steps=['src/main/java/File.java']
        )
        run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', input_data=toon_init)
        run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', input_data=toon_exec)

        result = run_script(SCRIPT_PATH, 'next', '--plan-id', 'test-plan', '--phase', 'execute')

        assert result.returncode == 0
        assert 'Execute Task' in result.stdout
        assert 'Init Task' not in result.stdout
    finally:
        cleanup(temp_dir)


def test_next_include_context():
    """Next with --include-context includes deliverable details."""
    temp_dir = setup_plan_dir()
    try:
        toon = build_task_toon(
            title='Feature task', deliverables=[1, 2], domain='java',
            description='Task description', steps=['src/main/java/One.java', 'src/main/java/Two.java']
        )
        run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', input_data=toon)

        result = run_script(SCRIPT_PATH, 'next', '--plan-id', 'test-plan', '--include-context')

        assert result.returncode == 0, f"Failed: {result.stderr}"
        assert 'task_number: 1' in result.stdout
        assert 'deliverables_found: true' in result.stdout
        assert 'deliverable_count: 2' in result.stdout
    finally:
        cleanup(temp_dir)


# =============================================================================
# Tests: step-start
# =============================================================================

def test_step_start_marks_in_progress():
    """Step-start marks step and task as in_progress."""
    temp_dir = setup_plan_dir()
    try:
        add_basic_task(title='Task', deliverables=[1], steps=['src/main/java/FileA.java', 'src/main/java/FileB.java'])

        result = run_script(SCRIPT_PATH, 'step-start', '--plan-id', 'test-plan',
                            '--task', '1', '--step', '1')

        assert result.returncode == 0
        assert 'task_status: in_progress' in result.stdout
        assert 'step_status: in_progress' in result.stdout
    finally:
        cleanup(temp_dir)


def test_step_start_invalid_step():
    """Step-start with invalid step number fails."""
    temp_dir = setup_plan_dir()
    try:
        add_basic_task(title='Task', deliverables=[1], steps=['src/main/java/File.java'])

        result = run_script(SCRIPT_PATH, 'step-start', '--plan-id', 'test-plan',
                            '--task', '1', '--step', '99')

        assert result.returncode == 1
        assert 'Step 99 not found' in result.stderr
    finally:
        cleanup(temp_dir)


# =============================================================================
# Tests: step-done
# =============================================================================

def test_step_done_marks_completed():
    """Step-done marks step as done."""
    temp_dir = setup_plan_dir()
    try:
        add_basic_task(title='Task', deliverables=[1], steps=['src/main/java/FileA.java', 'src/main/java/FileB.java'])

        result = run_script(SCRIPT_PATH, 'step-done', '--plan-id', 'test-plan',
                            '--task', '1', '--step', '1')

        assert result.returncode == 0
        assert 'step_status: done' in result.stdout
        assert 'next_step: 2' in result.stdout
    finally:
        cleanup(temp_dir)


def test_step_done_completes_task():
    """Step-done on last step marks task as done."""
    temp_dir = setup_plan_dir()
    try:
        add_basic_task(title='Task', deliverables=[1], steps=['src/main/java/File.java'])

        result = run_script(SCRIPT_PATH, 'step-done', '--plan-id', 'test-plan',
                            '--task', '1', '--step', '1')

        assert result.returncode == 0
        assert 'task_status: done' in result.stdout
        assert 'next_step: null' in result.stdout
        assert 'Task completed' in result.stdout
    finally:
        cleanup(temp_dir)


# =============================================================================
# Tests: step-skip
# =============================================================================

def test_step_skip_marks_skipped():
    """Step-skip marks step as skipped."""
    temp_dir = setup_plan_dir()
    try:
        add_basic_task(title='Task', deliverables=[1], steps=['src/main/java/FileA.java', 'src/main/java/FileB.java'])

        result = run_script(SCRIPT_PATH, 'step-skip', '--plan-id', 'test-plan',
                            '--task', '1', '--step', '1', '--reason', 'Already done')

        assert result.returncode == 0
        assert 'step_status: skipped' in result.stdout
        assert 'next_step: 2' in result.stdout
    finally:
        cleanup(temp_dir)


def test_step_skip_completes_task():
    """Skipping last step marks task as done."""
    temp_dir = setup_plan_dir()
    try:
        add_basic_task(title='Task', deliverables=[1], steps=['src/main/java/File.java'])

        result = run_script(SCRIPT_PATH, 'step-skip', '--plan-id', 'test-plan',
                            '--task', '1', '--step', '1')

        assert result.returncode == 0
        assert 'task_status: done' in result.stdout
    finally:
        cleanup(temp_dir)


# =============================================================================
# Tests: add-step
# =============================================================================

def test_add_step_appends():
    """Add-step appends to end by default."""
    temp_dir = setup_plan_dir()
    try:
        add_basic_task(title='Task', deliverables=[1], steps=['src/main/java/FileA.java', 'src/main/java/FileB.java'])

        result = run_script(SCRIPT_PATH, 'add-step', '--plan-id', 'test-plan',
                            '--task', '1', '--title', 'New Step')

        assert result.returncode == 0
        assert 'step: 3' in result.stdout

        # Verify step count
        get_result = run_script(SCRIPT_PATH, 'get', '--plan-id', 'test-plan', '--number', '1')
        assert 'steps[3]' in get_result.stdout
    finally:
        cleanup(temp_dir)


def test_add_step_after():
    """Add-step inserts after specified position."""
    temp_dir = setup_plan_dir()
    try:
        add_basic_task(title='Task', deliverables=[1], steps=['src/main/java/FileA.java', 'src/main/java/FileC.java'])

        # Add-step uses the title as-is (no validation on added steps)
        result = run_script(SCRIPT_PATH, 'add-step', '--plan-id', 'test-plan',
                            '--task', '1', '--title', 'src/main/java/FileB.java', '--after', '1')

        assert result.returncode == 0
        assert 'step: 2' in result.stdout

        # Verify order - steps are now file paths
        get_result = run_script(SCRIPT_PATH, 'get', '--plan-id', 'test-plan', '--number', '1')
        assert '1,src/main/java/FileA.java' in get_result.stdout
        assert '2,src/main/java/FileB.java' in get_result.stdout
        assert '3,src/main/java/FileC.java' in get_result.stdout
    finally:
        cleanup(temp_dir)


# =============================================================================
# Tests: remove-step
# =============================================================================

def test_remove_step():
    """Remove-step removes and renumbers."""
    temp_dir = setup_plan_dir()
    try:
        add_basic_task(title='Task', deliverables=[1], steps=['src/main/java/FileA.java', 'src/main/java/FileB.java', 'src/main/java/FileC.java'])

        result = run_script(SCRIPT_PATH, 'remove-step', '--plan-id', 'test-plan',
                            '--task', '1', '--step', '2')

        assert result.returncode == 0
        assert 'Step 2 removed' in result.stdout

        # Verify renumbering - steps are file paths
        get_result = run_script(SCRIPT_PATH, 'get', '--plan-id', 'test-plan', '--number', '1')
        assert 'steps[2]' in get_result.stdout
        assert '1,src/main/java/FileA.java' in get_result.stdout
        assert '2,src/main/java/FileC.java' in get_result.stdout
    finally:
        cleanup(temp_dir)


def test_remove_step_last_fails():
    """Cannot remove the last step."""
    temp_dir = setup_plan_dir()
    try:
        add_basic_task(title='Task', deliverables=[1], steps=['src/main/java/File.java'])

        result = run_script(SCRIPT_PATH, 'remove-step', '--plan-id', 'test-plan',
                            '--task', '1', '--step', '1')

        assert result.returncode == 1
        assert 'Cannot remove the last step' in result.stderr
    finally:
        cleanup(temp_dir)


# =============================================================================
# Tests: update
# =============================================================================

def test_update_title_keeps_filename():
    """Updating title does NOT rename file (TASK-SEQ-TYPE format is stable)."""
    temp_dir = setup_plan_dir()
    try:
        add_basic_task(title='Old Title', deliverables=[1], steps=['src/main/java/File.java'])

        # Verify initial filename uses TYPE suffix, not slug
        task_dir = Path(os.environ['PLAN_BASE_DIR']) / 'plans' / 'test-plan' / 'tasks'
        initial_files = list(task_dir.glob('TASK-001-IMPL.toon'))
        assert len(initial_files) == 1, "Should have TASK-001-IMPL.toon"

        result = run_script(SCRIPT_PATH, 'update', '--plan-id', 'test-plan',
                            '--number', '1', '--title', 'New Title')

        assert result.returncode == 0
        # Filename stays the same (TASK-SEQ-TYPE format)
        assert 'TASK-001-IMPL.toon' in result.stdout

        # File still exists with same name
        final_files = list(task_dir.glob('TASK-001-IMPL.toon'))
        assert len(final_files) == 1, "File should still be TASK-001-IMPL.toon"
    finally:
        cleanup(temp_dir)


def test_update_depends_on():
    """Update depends_on field."""
    temp_dir = setup_plan_dir()
    try:
        add_basic_task(title='Task', deliverables=[1], steps=['src/main/java/File.java'])

        result = run_script(SCRIPT_PATH, 'update', '--plan-id', 'test-plan',
                            '--number', '1', '--depends-on', 'TASK-5', 'TASK-6')

        assert result.returncode == 0

        # Verify
        get_result = run_script(SCRIPT_PATH, 'get', '--plan-id', 'test-plan', '--number', '1')
        assert 'depends_on: [TASK-5, TASK-6]' in get_result.stdout
    finally:
        cleanup(temp_dir)


def test_update_clear_depends_on():
    """Update depends_on to none clears dependencies."""
    temp_dir = setup_plan_dir()
    try:
        toon = build_task_toon(
            title='Task', deliverables=[1], domain='java',
            description='D', steps=['src/main/java/File.java'], depends_on='TASK-1'
        )
        run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', input_data=toon)

        result = run_script(SCRIPT_PATH, 'update', '--plan-id', 'test-plan',
                            '--number', '1', '--depends-on', 'none')

        assert result.returncode == 0

        # Verify
        get_result = run_script(SCRIPT_PATH, 'get', '--plan-id', 'test-plan', '--number', '1')
        assert 'depends_on: none' in get_result.stdout
    finally:
        cleanup(temp_dir)


# =============================================================================
# Tests: remove
# =============================================================================

def test_remove_deletes_file():
    """Remove deletes the task file."""
    temp_dir = setup_plan_dir()
    try:
        add_basic_task(title='To Delete', deliverables=[1], steps=['src/main/java/File.java'])

        result = run_script(SCRIPT_PATH, 'remove', '--plan-id', 'test-plan', '--number', '1')

        assert result.returncode == 0
        assert 'status: success' in result.stdout
        assert 'total_tasks: 0' in result.stdout

        # Verify file gone
        task_dir = Path(os.environ['PLAN_BASE_DIR']) / 'plans' / 'test-plan' / 'tasks'
        files = list(task_dir.glob('TASK-*.toon'))
        assert len(files) == 0
    finally:
        cleanup(temp_dir)


def test_remove_preserves_gaps():
    """Removing a task preserves number gaps."""
    temp_dir = setup_plan_dir()
    try:
        add_basic_task(title='First', deliverables=[1], steps=['src/main/java/File.java'])
        add_basic_task(title='Second', deliverables=[2], steps=['src/main/java/File.java'])
        add_basic_task(title='Third', deliverables=[3], steps=['src/main/java/File.java'])

        # Remove middle
        run_script(SCRIPT_PATH, 'remove', '--plan-id', 'test-plan', '--number', '2')

        # Next add should be 4, not 2
        result = add_basic_task(title='Fourth', deliverables=[4], steps=['src/main/java/File.java'])

        assert 'TASK-004' in result.stdout
    finally:
        cleanup(temp_dir)


# =============================================================================
# Tests: progress tracking
# =============================================================================

def test_progress_calculation():
    """Progress is correctly calculated in list output."""
    temp_dir = setup_plan_dir()
    try:
        add_basic_task(title='Task', deliverables=[1], steps=['src/main/java/FileA.java', 'src/main/java/FileB.java', 'src/main/java/FileC.java'])
        run_script(SCRIPT_PATH, 'step-done', '--plan-id', 'test-plan', '--task', '1', '--step', '1')
        run_script(SCRIPT_PATH, 'step-skip', '--plan-id', 'test-plan', '--task', '1', '--step', '2')

        result = run_script(SCRIPT_PATH, 'list', '--plan-id', 'test-plan')

        assert result.returncode == 0
        assert '2/3' in result.stdout  # 2 completed (done + skipped) out of 3
    finally:
        cleanup(temp_dir)


# =============================================================================
# Tests: file content verification
# =============================================================================

def test_file_contains_new_fields():
    """Created file contains all new fields."""
    temp_dir = setup_plan_dir()
    try:
        toon = build_task_toon(
            title='Test task',
            deliverables=[1, 2],
            domain='java',
            phase='execute',
            description='Test description',
            steps=['src/main/java/File1.java', 'src/main/java/File2.java'],
            depends_on='none',
            delegation_skill='pm-dev-java:java-implement',
            delegation_workflow='implement',
            verification_commands=['mvn test'],
            verification_criteria='Tests pass'
        )
        run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', input_data=toon)

        task_dir = Path(os.environ['PLAN_BASE_DIR']) / 'plans' / 'test-plan' / 'tasks'
        files = list(task_dir.glob('TASK-001-*.toon'))
        content = files[0].read_text(encoding='utf-8')

        assert 'number: 1' in content
        assert 'status: pending' in content
        assert 'phase: execute' in content
        assert 'deliverables[2]:' in content
        assert '- 1' in content
        assert '- 2' in content
        assert 'depends_on: none' in content
        assert 'delegation:' in content
        assert 'skill: pm-dev-java:java-implement' in content
        assert 'workflow: implement' in content
        assert 'domain: java' in content
        assert 'verification:' in content
        assert 'criteria: Tests pass' in content
        assert 'steps[2]{number,title,status}:' in content
        assert '1,src/main/java/File1.java,pending' in content
        assert '2,src/main/java/File2.java,pending' in content
        assert 'current_step: 1' in content
    finally:
        cleanup(temp_dir)


# =============================================================================
# Tests: type-based filename format
# =============================================================================

def test_type_filename_ignores_title_special_chars():
    """Filename uses TYPE suffix regardless of special characters in title."""
    temp_dir = setup_plan_dir()
    try:
        add_basic_task(title='Test@#$%Special!!!Characters', deliverables=[1])

        task_dir = Path(os.environ['PLAN_BASE_DIR']) / 'plans' / 'test-plan' / 'tasks'
        # Filename uses TYPE (IMPL), not slugified title
        files = list(task_dir.glob('TASK-001-IMPL.toon'))
        assert len(files) == 1, f"Expected TASK-001-IMPL.toon, found: {list(task_dir.glob('TASK-*.toon'))}"
    finally:
        cleanup(temp_dir)


def test_type_filename_ignores_title_length():
    """Filename uses TYPE suffix regardless of title length."""
    temp_dir = setup_plan_dir()
    try:
        long_title = 'A' * 100
        add_basic_task(title=long_title, deliverables=[1])

        task_dir = Path(os.environ['PLAN_BASE_DIR']) / 'plans' / 'test-plan' / 'tasks'
        # Filename uses TYPE (IMPL), not truncated title
        files = list(task_dir.glob('TASK-001-IMPL.toon'))
        assert len(files) == 1, f"Expected TASK-001-IMPL.toon, found: {list(task_dir.glob('TASK-*.toon'))}"
    finally:
        cleanup(temp_dir)


# =============================================================================
# Tests: domain validation
# =============================================================================

def test_arbitrary_domains_accepted():
    """Arbitrary domain strings are accepted (config-driven, not hardcoded)."""
    temp_dir = setup_plan_dir()
    try:
        # Various domain names - all should be accepted since domains are arbitrary
        domains = ['java', 'my-custom-domain', 'frontend-react', 'backend-api', 'devops']
        for i, domain in enumerate(domains, 1):
            toon = build_task_toon(
                title=f'Task {i}',
                deliverables=[i],
                domain=domain,
                description=f'Test {domain}',
                steps=['src/main/java/File.java']
            )
            result = run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', input_data=toon)
            assert result.returncode == 0, f"Domain {domain} failed: {result.stderr}"
    finally:
        cleanup(temp_dir)


# =============================================================================
# Main
# =============================================================================

if __name__ == '__main__':
    runner = TestRunner()
    runner.add_tests([
        # add with stdin API
        test_add_first_task,
        test_add_sequential_numbering,
        test_add_creates_type_based_filename,
        test_add_multiple_deliverables,
        test_add_fails_without_stdin,
        test_add_fails_without_deliverables,
        test_add_fails_with_invalid_deliverable,
        test_add_fails_without_domain,
        test_add_accepts_arbitrary_domain,
        test_add_fails_without_steps,
        test_add_with_phase,
        test_add_with_dependencies,
        test_add_with_delegation,
        test_add_with_verification,
        test_add_with_shell_metacharacters_in_verification,
        # get
        test_get_existing_task,
        test_get_nonexistent_returns_error,
        test_get_returns_delegation_block,
        test_get_returns_verification_block,
        # list
        test_list_empty,
        test_list_with_tasks,
        test_list_filter_by_status,
        test_list_filter_by_deliverable,
        test_list_filter_by_phase,
        test_list_filter_ready,
        # next
        test_next_returns_first_pending,
        test_next_returns_in_progress_task,
        test_next_returns_null_when_all_done,
        test_next_empty_plan,
        test_next_respects_dependencies,
        test_next_shows_blocked_tasks,
        test_next_ignore_deps,
        test_next_filter_by_phase,
        test_next_include_context,
        # step-start
        test_step_start_marks_in_progress,
        test_step_start_invalid_step,
        # step-done
        test_step_done_marks_completed,
        test_step_done_completes_task,
        # step-skip
        test_step_skip_marks_skipped,
        test_step_skip_completes_task,
        # add-step
        test_add_step_appends,
        test_add_step_after,
        # remove-step
        test_remove_step,
        test_remove_step_last_fails,
        # update
        test_update_title_keeps_filename,
        test_update_depends_on,
        test_update_clear_depends_on,
        # remove
        test_remove_deletes_file,
        test_remove_preserves_gaps,
        # progress
        test_progress_calculation,
        # file content
        test_file_contains_new_fields,
        # type-based filename
        test_type_filename_ignores_title_special_chars,
        test_type_filename_ignores_title_length,
        # domain
        test_arbitrary_domains_accepted,
    ])
    sys.exit(runner.run())
