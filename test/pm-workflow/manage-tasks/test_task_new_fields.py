#!/usr/bin/env python3
"""Tests for manage-tasks.py new fields: domain, profile, skills, origin."""

import os
import shutil
import sys
from pathlib import Path

# Import shared infrastructure
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from conftest import create_temp_dir, get_script_path, run_script

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


def build_task_toon_with_new_fields(
    title='Test task',
    deliverables=None,
    domain='java',
    profile='implementation',
    skills=None,
    origin='plan',
    description='Task description',
    steps=None,
    phase='4-execute',
    depends_on='none',
):
    """Build TOON content for task with new fields."""
    if deliverables is None:
        deliverables = [1]
    if steps is None:
        steps = ['src/main/java/TestFile.java']
    if skills is None:
        skills = ['pm-dev-java:java-core']

    deliverables_str = '[' + ', '.join(str(d) for d in deliverables) + ']'

    lines = [
        f'title: {title}',
        f'deliverables: {deliverables_str}',
        f'domain: {domain}',
        f'profile: {profile}',
        f'phase: {phase}',
        f'origin: {origin}',
        f'description: {description}',
        'skills:',
    ]

    for skill in skills:
        lines.append(f'  - {skill}')

    lines.append('steps:')
    for step in steps:
        lines.append(f'  - {step}')

    lines.append(f'depends_on: {depends_on}')

    return '\n'.join(lines)


def add_task_with_fields(plan_id='test-plan', **kwargs):
    """Helper to add a task with new fields."""
    toon = build_task_toon_with_new_fields(**kwargs)
    return run_script(SCRIPT_PATH, 'add', '--plan-id', plan_id, input_data=toon)


# =============================================================================
# Tests: add with new fields
# =============================================================================


def test_add_with_profile():
    """Add task with profile field."""
    temp_dir = setup_plan_dir()
    try:
        result = add_task_with_fields(
            title='Test task',
            deliverables=[1],
            domain='java',
            profile='implementation',
            skills=['pm-dev-java:java-core'],
        )

        assert result.returncode == 0, f'Failed: {result.stderr}'
        assert 'status: success' in result.stdout
        assert 'profile: implementation' in result.stdout
    finally:
        cleanup(temp_dir)


def test_add_with_testing_profile():
    """Add task with testing profile."""
    temp_dir = setup_plan_dir()
    try:
        result = add_task_with_fields(
            title='Test task', deliverables=[1], domain='java', profile='testing', skills=['pm-dev-java:junit-core']
        )

        assert result.returncode == 0, f'Failed: {result.stderr}'
        assert 'profile: testing' in result.stdout
    finally:
        cleanup(temp_dir)


def test_add_with_quality_profile():
    """Add task with quality profile."""
    temp_dir = setup_plan_dir()
    try:
        result = add_task_with_fields(
            title='Quality check task',
            deliverables=[1],
            domain='java',
            profile='quality',
            skills=['pm-dev-java:java-maintenance'],
        )

        assert result.returncode == 0, f'Failed: {result.stderr}'
        assert 'profile: quality' in result.stdout
    finally:
        cleanup(temp_dir)


def test_add_with_skills():
    """Add task with skills array."""
    temp_dir = setup_plan_dir()
    try:
        result = add_task_with_fields(
            title='Multi-skill task',
            deliverables=[1],
            domain='java',
            profile='implementation',
            skills=['pm-dev-java:java-core', 'pm-dev-java:java-cdi', 'pm-dev-java:java-lombok'],
        )

        assert result.returncode == 0, f'Failed: {result.stderr}'
        assert 'skills:' in result.stdout
        assert 'pm-dev-java:java-core' in result.stdout
    finally:
        cleanup(temp_dir)


def test_add_with_origin():
    """Add task with origin field."""
    temp_dir = setup_plan_dir()
    try:
        result = add_task_with_fields(
            title='Plan origin task', deliverables=[1], domain='java', profile='implementation', origin='plan'
        )

        assert result.returncode == 0, f'Failed: {result.stderr}'
        assert 'origin: plan' in result.stdout
    finally:
        cleanup(temp_dir)


def test_add_with_arbitrary_profile():
    """Add accepts any profile value (profiles are config-driven, not hardcoded)."""
    temp_dir = setup_plan_dir()
    try:
        # Test with 'architecture' profile (not in old VALID_PROFILES)
        toon = """title: Architecture task
deliverables: [1]
domain: java
profile: architecture
phase: 4-execute
description: Desc
skills:
  - pm-dev-java:java-core
steps:
  - src/main/java/File.java"""
        result = run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', input_data=toon)

        assert result.returncode == 0
        assert 'profile: architecture' in result.stdout
    finally:
        cleanup(temp_dir)


def test_add_with_planning_profile():
    """Add accepts 'planning' profile (config-driven)."""
    temp_dir = setup_plan_dir()
    try:
        toon = """title: Planning task
deliverables: [1]
domain: java
profile: planning
phase: 4-execute
description: Desc
skills:
  - pm-dev-java:java-core
steps:
  - src/main/java/File.java"""
        result = run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', input_data=toon)

        assert result.returncode == 0
        assert 'profile: planning' in result.stdout
    finally:
        cleanup(temp_dir)


def test_add_with_custom_profile():
    """Add accepts custom profile values (config-driven)."""
    temp_dir = setup_plan_dir()
    try:
        toon = """title: Custom task
deliverables: [1]
domain: java
profile: my-custom-profile
phase: 4-execute
description: Desc
skills:
  - pm-dev-java:java-core
steps:
  - src/main/java/File.java"""
        result = run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', input_data=toon)

        assert result.returncode == 0
        assert 'profile: my-custom-profile' in result.stdout
    finally:
        cleanup(temp_dir)


def test_add_fails_with_invalid_skill_format():
    """Add fails with invalid skill format (missing colon)."""
    temp_dir = setup_plan_dir()
    try:
        toon = """title: Invalid skill
deliverables: [1]
domain: java
profile: implementation
phase: 4-execute
description: Desc
skills:
  - invalid-skill-no-colon
steps:
  - Step 1"""
        result = run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', input_data=toon)

        assert result.returncode != 0
        assert 'skill' in result.stderr.lower() or 'bundle:skill' in result.stderr.lower()
    finally:
        cleanup(temp_dir)


# =============================================================================
# Tests: get returns new fields
# =============================================================================


def test_get_returns_domain():
    """Get returns domain field."""
    temp_dir = setup_plan_dir()
    try:
        add_task_with_fields(title='Test', domain='javascript', profile='implementation')
        result = run_script(SCRIPT_PATH, 'get', '--plan-id', 'test-plan', '--number', '1')

        assert result.returncode == 0
        assert 'domain: javascript' in result.stdout
    finally:
        cleanup(temp_dir)


def test_get_returns_profile():
    """Get returns profile field."""
    temp_dir = setup_plan_dir()
    try:
        add_task_with_fields(title='Test', profile='testing')
        result = run_script(SCRIPT_PATH, 'get', '--plan-id', 'test-plan', '--number', '1')

        assert result.returncode == 0
        assert 'profile: testing' in result.stdout
    finally:
        cleanup(temp_dir)


def test_get_returns_skills():
    """Get returns skills array."""
    temp_dir = setup_plan_dir()
    try:
        add_task_with_fields(title='Test', skills=['pm-dev-java:java-core', 'pm-dev-java:java-cdi'])
        result = run_script(SCRIPT_PATH, 'get', '--plan-id', 'test-plan', '--number', '1')

        assert result.returncode == 0
        assert 'skills:' in result.stdout
        assert 'pm-dev-java:java-core' in result.stdout
        assert 'pm-dev-java:java-cdi' in result.stdout
    finally:
        cleanup(temp_dir)


def test_get_returns_origin():
    """Get returns origin field."""
    temp_dir = setup_plan_dir()
    try:
        add_task_with_fields(title='Test', origin='plan')
        result = run_script(SCRIPT_PATH, 'get', '--plan-id', 'test-plan', '--number', '1')

        assert result.returncode == 0
        assert 'origin: plan' in result.stdout
    finally:
        cleanup(temp_dir)


# =============================================================================
# Tests: list includes new columns
# =============================================================================


def test_list_includes_domain_column():
    """List includes domain column."""
    temp_dir = setup_plan_dir()
    try:
        add_task_with_fields(title='Java task', domain='java', profile='implementation')
        add_task_with_fields(title='JS task', domain='javascript', profile='implementation')

        result = run_script(SCRIPT_PATH, 'list', '--plan-id', 'test-plan')

        assert result.returncode == 0
        # Check table includes domain
        assert 'java' in result.stdout
        assert 'javascript' in result.stdout
    finally:
        cleanup(temp_dir)


def test_list_includes_profile_column():
    """List includes profile column."""
    temp_dir = setup_plan_dir()
    try:
        add_task_with_fields(title='Impl task', profile='implementation')
        add_task_with_fields(title='Test task', profile='testing')

        result = run_script(SCRIPT_PATH, 'list', '--plan-id', 'test-plan')

        assert result.returncode == 0
        assert 'implementation' in result.stdout
        assert 'testing' in result.stdout
    finally:
        cleanup(temp_dir)


# =============================================================================
# Tests: update with new field parameters
# =============================================================================


def test_update_domain():
    """Update domain field."""
    temp_dir = setup_plan_dir()
    try:
        add_task_with_fields(title='Task', domain='java')
        result = run_script(SCRIPT_PATH, 'update', '--plan-id', 'test-plan', '--number', '1', '--domain', 'javascript')

        assert result.returncode == 0
        assert 'domain: javascript' in result.stdout

        # Verify with get
        get_result = run_script(SCRIPT_PATH, 'get', '--plan-id', 'test-plan', '--number', '1')
        assert 'domain: javascript' in get_result.stdout
    finally:
        cleanup(temp_dir)


def test_update_profile():
    """Update profile field."""
    temp_dir = setup_plan_dir()
    try:
        add_task_with_fields(title='Task', profile='implementation')
        result = run_script(SCRIPT_PATH, 'update', '--plan-id', 'test-plan', '--number', '1', '--profile', 'testing')

        assert result.returncode == 0
        assert 'profile: testing' in result.stdout

        # Verify with get
        get_result = run_script(SCRIPT_PATH, 'get', '--plan-id', 'test-plan', '--number', '1')
        assert 'profile: testing' in get_result.stdout
    finally:
        cleanup(temp_dir)


def test_update_skills():
    """Update skills field."""
    temp_dir = setup_plan_dir()
    try:
        add_task_with_fields(title='Task', skills=['pm-dev-java:java-core'])
        result = run_script(
            SCRIPT_PATH,
            'update',
            '--plan-id',
            'test-plan',
            '--number',
            '1',
            '--skills',
            'pm-dev-java:java-cdi,pm-dev-java:java-lombok',
        )

        assert result.returncode == 0

        # Verify with get
        get_result = run_script(SCRIPT_PATH, 'get', '--plan-id', 'test-plan', '--number', '1')
        assert 'pm-dev-java:java-cdi' in get_result.stdout
        assert 'pm-dev-java:java-lombok' in get_result.stdout
    finally:
        cleanup(temp_dir)


def test_update_deliverables():
    """Update deliverables field."""
    temp_dir = setup_plan_dir()
    try:
        add_task_with_fields(title='Task', deliverables=[1])
        result = run_script(SCRIPT_PATH, 'update', '--plan-id', 'test-plan', '--number', '1', '--deliverables', '1,2,3')

        assert result.returncode == 0

        # Verify with get
        get_result = run_script(SCRIPT_PATH, 'get', '--plan-id', 'test-plan', '--number', '1')
        assert 'deliverables: [1, 2, 3]' in get_result.stdout
    finally:
        cleanup(temp_dir)


def test_update_with_arbitrary_profile():
    """Update accepts any profile value (profiles are config-driven)."""
    temp_dir = setup_plan_dir()
    try:
        add_task_with_fields(title='Task', profile='implementation')

        # Update to arbitrary profile
        result = run_script(
            SCRIPT_PATH, 'update', '--plan-id', 'test-plan', '--number', '1', '--profile', 'architecture'
        )

        assert result.returncode == 0
        assert 'profile: architecture' in result.stdout

        # Verify persisted
        get_result = run_script(SCRIPT_PATH, 'get', '--plan-id', 'test-plan', '--number', '1')
        assert 'profile: architecture' in get_result.stdout
    finally:
        cleanup(temp_dir)


def test_update_with_custom_profile():
    """Update accepts custom profile values."""
    temp_dir = setup_plan_dir()
    try:
        add_task_with_fields(title='Task', profile='implementation')

        # Update to custom profile
        result = run_script(
            SCRIPT_PATH, 'update', '--plan-id', 'test-plan', '--number', '1', '--profile', 'my-custom-profile'
        )

        assert result.returncode == 0
        assert 'profile: my-custom-profile' in result.stdout
    finally:
        cleanup(temp_dir)


def test_update_fails_with_invalid_skills():
    """Update fails with invalid skill format."""
    temp_dir = setup_plan_dir()
    try:
        add_task_with_fields(title='Task', skills=['pm-dev-java:java-core'])
        result = run_script(
            SCRIPT_PATH, 'update', '--plan-id', 'test-plan', '--number', '1', '--skills', 'invalid-no-colon'
        )

        assert result.returncode != 0
        assert 'skill' in result.stderr.lower() or 'bundle:skill' in result.stderr.lower()
    finally:
        cleanup(temp_dir)


# =============================================================================
# Tests: tasks-by-domain query
# =============================================================================


def test_tasks_by_domain_filters():
    """tasks-by-domain filters by domain."""
    temp_dir = setup_plan_dir()
    try:
        add_task_with_fields(title='Java task 1', domain='java')
        add_task_with_fields(title='JS task', domain='javascript')
        add_task_with_fields(title='Java task 2', domain='java')

        result = run_script(SCRIPT_PATH, 'tasks-by-domain', '--plan-id', 'test-plan', '--domain', 'java')

        assert result.returncode == 0
        assert 'total: 2' in result.stdout
        assert 'Java task 1' in result.stdout
        assert 'Java task 2' in result.stdout
        assert 'JS task' not in result.stdout
    finally:
        cleanup(temp_dir)


def test_tasks_by_domain_empty_result():
    """tasks-by-domain returns empty when no matches."""
    temp_dir = setup_plan_dir()
    try:
        add_task_with_fields(title='Java task', domain='java')

        result = run_script(SCRIPT_PATH, 'tasks-by-domain', '--plan-id', 'test-plan', '--domain', 'javascript')

        assert result.returncode == 0
        assert 'total: 0' in result.stdout
    finally:
        cleanup(temp_dir)


# =============================================================================
# Tests: tasks-by-profile query
# =============================================================================


def test_tasks_by_profile_filters():
    """tasks-by-profile filters by profile."""
    temp_dir = setup_plan_dir()
    try:
        add_task_with_fields(title='Impl task 1', profile='implementation')
        add_task_with_fields(title='Test task', profile='testing')
        add_task_with_fields(title='Impl task 2', profile='implementation')

        result = run_script(SCRIPT_PATH, 'tasks-by-profile', '--plan-id', 'test-plan', '--profile', 'implementation')

        assert result.returncode == 0
        assert 'total: 2' in result.stdout
        assert 'Impl task 1' in result.stdout
        assert 'Impl task 2' in result.stdout
        assert 'Test task' not in result.stdout
    finally:
        cleanup(temp_dir)


def test_tasks_by_profile_testing():
    """tasks-by-profile filters testing profile."""
    temp_dir = setup_plan_dir()
    try:
        add_task_with_fields(title='Impl task', profile='implementation')
        add_task_with_fields(title='Test task 1', profile='testing')
        add_task_with_fields(title='Test task 2', profile='testing')

        result = run_script(SCRIPT_PATH, 'tasks-by-profile', '--plan-id', 'test-plan', '--profile', 'testing')

        assert result.returncode == 0
        assert 'total: 2' in result.stdout
        assert 'Test task 1' in result.stdout
        assert 'Test task 2' in result.stdout
    finally:
        cleanup(temp_dir)


# =============================================================================
# Tests: next-tasks query
# =============================================================================


def test_next_tasks_returns_ready_tasks():
    """next-tasks returns all tasks with satisfied dependencies."""
    temp_dir = setup_plan_dir()
    try:
        # Task 1 - no deps
        add_task_with_fields(title='Task 1', depends_on='none')
        # Task 2 - no deps
        add_task_with_fields(title='Task 2', depends_on='none')
        # Task 3 - depends on task 1
        add_task_with_fields(title='Task 3', depends_on='TASK-1')

        result = run_script(SCRIPT_PATH, 'next-tasks', '--plan-id', 'test-plan')

        assert result.returncode == 0
        assert 'ready_count: 2' in result.stdout
        assert 'Task 1' in result.stdout
        assert 'Task 2' in result.stdout
        # Task 3 should be in blocked
        assert 'blocked_count: 1' in result.stdout
    finally:
        cleanup(temp_dir)


def test_next_tasks_includes_skills():
    """next-tasks includes skills in ready task output."""
    temp_dir = setup_plan_dir()
    try:
        add_task_with_fields(
            title='Task with skills', skills=['pm-dev-java:java-core', 'pm-dev-java:java-cdi'], depends_on='none'
        )

        result = run_script(SCRIPT_PATH, 'next-tasks', '--plan-id', 'test-plan')

        assert result.returncode == 0
        assert 'skills:' in result.stdout
        assert 'pm-dev-java:java-core' in result.stdout
    finally:
        cleanup(temp_dir)


def test_next_tasks_shows_blocked():
    """next-tasks shows blocked tasks with waiting_for."""
    temp_dir = setup_plan_dir()
    try:
        # Only task depends on non-existent task
        add_task_with_fields(title='Blocked task', depends_on='TASK-99')

        result = run_script(SCRIPT_PATH, 'next-tasks', '--plan-id', 'test-plan')

        assert result.returncode == 0
        assert 'ready_count: 0' in result.stdout
        assert 'blocked_count: 1' in result.stdout
        # waiting_for is in the table header and TASK-99 is in the data
        assert 'blocked_tasks[1]' in result.stdout
        assert 'waiting_for' in result.stdout  # in the header
        assert 'TASK-99' in result.stdout
    finally:
        cleanup(temp_dir)


def test_next_tasks_includes_in_progress():
    """next-tasks includes in_progress tasks."""
    temp_dir = setup_plan_dir()
    try:
        add_task_with_fields(title='Task 1', depends_on='none')
        add_task_with_fields(title='Task 2', depends_on='none')

        # Start task 1
        run_script(SCRIPT_PATH, 'step-start', '--plan-id', 'test-plan', '--task', '1', '--step', '1')

        result = run_script(SCRIPT_PATH, 'next-tasks', '--plan-id', 'test-plan')

        assert result.returncode == 0
        assert 'in_progress_count: 1' in result.stdout
        # Task 2 is ready (not started)
        assert 'ready_count: 1' in result.stdout
    finally:
        cleanup(temp_dir)


# =============================================================================
# Tests: backward compatibility
# =============================================================================


def test_backward_compat_old_file_without_new_fields():
    """Old task files without new fields are handled gracefully."""
    temp_dir = setup_plan_dir()
    try:
        # Create task file manually without new fields (simulating old format)
        task_dir = Path(os.environ['PLAN_BASE_DIR']) / 'plans' / 'test-plan' / 'tasks'
        task_dir.mkdir(parents=True, exist_ok=True)

        old_format = """number: 1
title: Old task
status: pending
phase: 4-execute
created: 2025-01-01T00:00:00Z
updated: 2025-01-01T00:00:00Z

deliverables[1]:
- 1

depends_on: none

description: |
  Old task without new fields

steps[1]{number,title,status}:
1,Step 1,pending

current_step: 1
"""
        (task_dir / 'TASK-001-old-task.toon').write_text(old_format, encoding='utf-8')

        # Get should work and return defaults for missing fields
        result = run_script(SCRIPT_PATH, 'get', '--plan-id', 'test-plan', '--number', '1')

        assert result.returncode == 0
        assert 'Old task' in result.stdout
        # Should have default values
        assert 'origin: plan' in result.stdout  # default
        assert 'skills: []' in result.stdout  # empty array
    finally:
        cleanup(temp_dir)


def test_next_returns_new_fields():
    """Next command returns domain, profile, skills in output."""
    temp_dir = setup_plan_dir()
    try:
        add_task_with_fields(
            title='Task with all fields',
            domain='java',
            profile='implementation',
            skills=['pm-dev-java:java-core', 'pm-dev-java:java-cdi'],
        )

        result = run_script(SCRIPT_PATH, 'next', '--plan-id', 'test-plan')

        assert result.returncode == 0
        assert 'domain: java' in result.stdout
        assert 'profile: implementation' in result.stdout
        assert 'skills:' in result.stdout
        assert 'origin: plan' in result.stdout
    finally:
        cleanup(temp_dir)


# =============================================================================
# Tests: file format
# =============================================================================


def test_file_contains_all_new_fields():
    """Created file contains all new fields."""
    temp_dir = setup_plan_dir()
    try:
        add_task_with_fields(
            title='Complete task',
            domain='java',
            profile='implementation',
            skills=['pm-dev-java:java-core', 'pm-dev-java:java-cdi'],
            origin='plan',
        )

        task_dir = Path(os.environ['PLAN_BASE_DIR']) / 'plans' / 'test-plan' / 'tasks'
        files = list(task_dir.glob('TASK-001-*.toon'))
        content = files[0].read_text(encoding='utf-8')

        assert 'domain: java' in content
        assert 'profile: implementation' in content
        assert 'origin: plan' in content
        # Skills use TOON array format: skills[N]:
        assert 'skills[' in content
        assert '- pm-dev-java:java-core' in content
        assert '- pm-dev-java:java-cdi' in content
    finally:
        cleanup(temp_dir)


# =============================================================================
# Tests: 5-phase model (outline + plan instead of refine)
# =============================================================================


def test_add_with_outline_phase():
    """Add accepts '2-outline' phase (5-phase model)."""
    temp_dir = setup_plan_dir()
    try:
        toon = """title: Outline task
deliverables: [1]
domain: java
profile: architecture
phase: 2-outline
description: Desc
skills:
  - pm-dev-java:java-core
steps:
  - src/main/java/File.java"""
        result = run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', input_data=toon)

        assert result.returncode == 0, f'Failed: {result.stderr}'
        assert 'phase: 2-outline' in result.stdout
    finally:
        cleanup(temp_dir)


def test_add_with_plan_phase():
    """Add accepts '3-plan' phase (5-phase model)."""
    temp_dir = setup_plan_dir()
    try:
        toon = """title: Plan task
deliverables: [1]
domain: java
profile: planning
phase: 3-plan
description: Desc
skills:
  - pm-dev-java:java-core
steps:
  - src/main/java/File.java"""
        result = run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', input_data=toon)

        assert result.returncode == 0, f'Failed: {result.stderr}'
        assert 'phase: 3-plan' in result.stdout
    finally:
        cleanup(temp_dir)


# =============================================================================
# Tests: arbitrary domains (config-driven, not hardcoded)
# =============================================================================


def test_add_with_arbitrary_domain():
    """Add accepts any domain value (domains are config-driven)."""
    temp_dir = setup_plan_dir()
    try:
        toon = """title: Requirements task
deliverables: [1]
domain: requirements
profile: implementation
phase: 4-execute
description: Desc
skills:
  - pm-requirements:req-core
steps:
  - docs/requirements.adoc"""
        result = run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', input_data=toon)

        assert result.returncode == 0, f'Failed: {result.stderr}'
        assert 'domain: requirements' in result.stdout
    finally:
        cleanup(temp_dir)


def test_add_with_custom_domain():
    """Add accepts custom domain values (config-driven)."""
    temp_dir = setup_plan_dir()
    try:
        toon = """title: Custom domain task
deliverables: [1]
domain: my-custom-domain
profile: implementation
phase: 4-execute
description: Desc
skills:
  - pm-dev-java:java-core
steps:
  - src/main/java/File.java"""
        result = run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', input_data=toon)

        assert result.returncode == 0, f'Failed: {result.stderr}'
        assert 'domain: my-custom-domain' in result.stdout
    finally:
        cleanup(temp_dir)


def test_update_with_arbitrary_domain():
    """Update accepts any domain value."""
    temp_dir = setup_plan_dir()
    try:
        add_task_with_fields(title='Task', domain='java')

        result = run_script(
            SCRIPT_PATH, 'update', '--plan-id', 'test-plan', '--number', '1', '--domain', 'requirements'
        )

        assert result.returncode == 0
        assert 'domain: requirements' in result.stdout
    finally:
        cleanup(temp_dir)


# =============================================================================
# Tests: task type field
# =============================================================================


def test_add_with_impl_type():
    """Add accepts type field with IMPL value."""
    temp_dir = setup_plan_dir()
    try:
        toon = """title: Implementation task
deliverables: [1]
domain: java
profile: implementation
phase: 4-execute
type: IMPL
description: Desc
skills:
  - pm-dev-java:java-core
steps:
  - src/main/java/File.java"""
        result = run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', input_data=toon)

        assert result.returncode == 0, f'Failed: {result.stderr}'
        assert 'type: IMPL' in result.stdout
    finally:
        cleanup(temp_dir)


def test_add_with_fix_type():
    """Add accepts type field with FIX value."""
    temp_dir = setup_plan_dir()
    try:
        toon = """title: Fix task
deliverables: [1]
domain: java
profile: implementation
phase: 4-execute
type: FIX
origin: fix
description: Desc
skills:
  - pm-dev-java:java-core
steps:
  - src/main/java/File.java"""
        result = run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', input_data=toon)

        assert result.returncode == 0, f'Failed: {result.stderr}'
        assert 'type: FIX' in result.stdout
    finally:
        cleanup(temp_dir)


def test_add_with_sonar_type():
    """Add accepts type field with SONAR value."""
    temp_dir = setup_plan_dir()
    try:
        toon = """title: Sonar fix task
deliverables: [1]
domain: java
profile: quality
phase: 4-execute
type: SONAR
origin: fix
description: Desc
skills:
  - pm-dev-java:java-core
steps:
  - src/main/java/File.java"""
        result = run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', input_data=toon)

        assert result.returncode == 0, f'Failed: {result.stderr}'
        assert 'type: SONAR' in result.stdout
    finally:
        cleanup(temp_dir)


# =============================================================================
# Tests: task ID format TASK-SEQ-TYPE
# =============================================================================


def test_task_file_uses_type_suffix():
    """Task file uses TASK-SEQ-TYPE format instead of slug."""
    temp_dir = setup_plan_dir()
    try:
        toon = """title: Implementation task with long title
deliverables: [1]
domain: java
profile: implementation
phase: 4-execute
type: IMPL
description: Desc
skills:
  - pm-dev-java:java-core
steps:
  - src/main/java/File.java"""
        result = run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', input_data=toon)

        assert result.returncode == 0, f'Failed: {result.stderr}'
        # Should use TASK-001-IMPL.toon format
        assert 'file: TASK-001-IMPL.toon' in result.stdout
    finally:
        cleanup(temp_dir)


def test_fix_task_file_uses_fix_suffix():
    """Fix task file uses TASK-SEQ-FIX format."""
    temp_dir = setup_plan_dir()
    try:
        toon = """title: Fix broken test
deliverables: [1]
domain: java
profile: testing
phase: 4-execute
type: FIX
origin: fix
description: Desc
skills:
  - pm-dev-java:junit-core
steps:
  - src/test/java/FileTest.java"""
        result = run_script(SCRIPT_PATH, 'add', '--plan-id', 'test-plan', input_data=toon)

        assert result.returncode == 0, f'Failed: {result.stderr}'
        # Should use TASK-001-FIX.toon format
        assert 'file: TASK-001-FIX.toon' in result.stdout
    finally:
        cleanup(temp_dir)


# =============================================================================
# Main
# =============================================================================
