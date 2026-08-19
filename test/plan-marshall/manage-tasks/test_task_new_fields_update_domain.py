#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-tasks.py new fields: domain, profile, skills, origin.

Tier 2 (direct import) tests with 2 subprocess tests for CLI plumbing.
"""


import json
import os
from pathlib import Path

from _task_new_fields_fixtures import (
    _add_ns,
    _finalize_step_ns,
    _list_ns,
    _next_ns,
    _next_tasks_ns,
    _read_ns,
    _update_ns,
    add_task_with_fields,
    cmd_add,
    cmd_finalize_step,
    cmd_list,
    cmd_next,
    cmd_next_tasks,
    cmd_read,
    cmd_update,
)

# =============================================================================
# Tests: update with new field parameters
# =============================================================================


def test_update_domain(plan_context):
    """Update domain field."""
    add_task_with_fields(plan_id='nf-upd-dom', title='Task', domain='java')
    result = cmd_update(_update_ns(plan_id='nf-upd-dom', number=1, domain='javascript'))

    assert result['status'] == 'success'
    assert result['task']['domain'] == 'javascript'

    get_result = cmd_read(_read_ns(plan_id='nf-upd-dom', number=1))
    assert get_result['task']['domain'] == 'javascript'


def test_update_profile(plan_context):
    """Update profile field."""
    add_task_with_fields(plan_id='nf-upd-prof', title='Task', profile='implementation')
    result = cmd_update(_update_ns(plan_id='nf-upd-prof', number=1, profile='testing'))

    assert result['status'] == 'success'
    assert result['task']['profile'] == 'testing'

    get_result = cmd_read(_read_ns(plan_id='nf-upd-prof', number=1))
    assert get_result['task']['profile'] == 'testing'


def test_update_skills(plan_context):
    """Update skills field."""
    add_task_with_fields(plan_id='nf-upd-skills', title='Task', skills=['pm-dev-java:java-core'])
    result = cmd_update(
        _update_ns(
            plan_id='nf-upd-skills',
            number=1,
            skills='pm-dev-java:java-cdi,pm-dev-java:java-lombok',
        )
    )

    assert result['status'] == 'success'

    get_result = cmd_read(_read_ns(plan_id='nf-upd-skills', number=1))
    assert 'pm-dev-java:java-cdi' in get_result['task']['skills']
    assert 'pm-dev-java:java-lombok' in get_result['task']['skills']


def test_update_deliverable(plan_context):
    """Update deliverable field (single integer)."""
    add_task_with_fields(plan_id='nf-upd-del', title='Task', deliverable=1)
    result = cmd_update(_update_ns(plan_id='nf-upd-del', number=1, deliverable=2))

    assert result['status'] == 'success'

    get_result = cmd_read(_read_ns(plan_id='nf-upd-del', number=1))
    assert get_result['task']['deliverable'] == 2


def test_update_with_arbitrary_profile(plan_context):
    """Update accepts any profile value (profiles are config-driven)."""
    add_task_with_fields(plan_id='nf-upd-arb-prof', title='Task', profile='implementation')

    result = cmd_update(_update_ns(plan_id='nf-upd-arb-prof', number=1, profile='architecture'))

    assert result['status'] == 'success'
    assert result['task']['profile'] == 'architecture'

    get_result = cmd_read(_read_ns(plan_id='nf-upd-arb-prof', number=1))
    assert get_result['task']['profile'] == 'architecture'


def test_update_with_custom_profile(plan_context):
    """Update accepts custom profile values."""
    add_task_with_fields(plan_id='nf-upd-cust-prof', title='Task', profile='implementation')

    result = cmd_update(_update_ns(plan_id='nf-upd-cust-prof', number=1, profile='my-custom-profile'))

    assert result['status'] == 'success'
    assert result['task']['profile'] == 'my-custom-profile'


def test_update_fails_with_invalid_skills(plan_context):
    """Update fails with invalid skill format."""
    add_task_with_fields(plan_id='nf-upd-bad-skill', title='Task', skills=['pm-dev-java:java-core'])
    result = cmd_update(
        _update_ns(
            plan_id='nf-upd-bad-skill',
            number=1,
            skills='invalid-no-colon',
        )
    )

    assert result['status'] == 'error'
    msg = result.get('message', '').lower()
    assert 'skill' in msg or 'bundle:skill' in msg


# =============================================================================
# Tests: list --domain filter
# =============================================================================


def test_list_domain_filter(plan_context):
    """list --domain filters by domain."""
    add_task_with_fields(plan_id='nf-by-dom', title='Java task 1', domain='java')
    add_task_with_fields(plan_id='nf-by-dom', title='JS task', domain='javascript')
    add_task_with_fields(plan_id='nf-by-dom', title='Java task 2', domain='java')

    result = cmd_list(_list_ns(plan_id='nf-by-dom', domain='java'))

    assert result['status'] == 'success'
    assert result['counts']['total'] == 2
    titles = [t['title'] for t in result['tasks_table']]
    assert 'Java task 1' in titles
    assert 'Java task 2' in titles
    assert 'JS task' not in titles


def test_list_domain_filter_empty_result(plan_context):
    """list --domain returns empty when no matches."""
    add_task_with_fields(plan_id='nf-by-dom-empty', title='Java task', domain='java')

    result = cmd_list(_list_ns(plan_id='nf-by-dom-empty', domain='javascript'))

    assert result['status'] == 'success'
    assert result['counts']['total'] == 0


# =============================================================================
# Tests: list --profile filter
# =============================================================================


def test_list_profile_filter(plan_context):
    """list --profile filters by profile."""
    add_task_with_fields(plan_id='nf-by-prof', title='Impl task 1', profile='implementation')
    add_task_with_fields(plan_id='nf-by-prof', title='Test task', profile='testing')
    add_task_with_fields(plan_id='nf-by-prof', title='Impl task 2', profile='implementation')

    result = cmd_list(_list_ns(plan_id='nf-by-prof', profile='implementation'))

    assert result['status'] == 'success'
    assert result['counts']['total'] == 2
    titles = [t['title'] for t in result['tasks_table']]
    assert 'Impl task 1' in titles
    assert 'Impl task 2' in titles
    assert 'Test task' not in titles


def test_list_profile_filter_testing(plan_context):
    """list --profile filters testing profile."""
    add_task_with_fields(plan_id='nf-by-prof-test', title='Impl task', profile='implementation')
    add_task_with_fields(plan_id='nf-by-prof-test', title='Test task 1', profile='testing')
    add_task_with_fields(plan_id='nf-by-prof-test', title='Test task 2', profile='testing')

    result = cmd_list(_list_ns(plan_id='nf-by-prof-test', profile='testing'))

    assert result['status'] == 'success'
    assert result['counts']['total'] == 2
    titles = [t['title'] for t in result['tasks_table']]
    assert 'Test task 1' in titles
    assert 'Test task 2' in titles


# =============================================================================
# Tests: next-tasks query
# =============================================================================


def test_next_tasks_returns_ready_tasks(plan_context):
    """next-tasks returns all tasks with satisfied dependencies."""
    add_task_with_fields(plan_id='nf-next-tasks', title='Task 1', depends_on='none')
    add_task_with_fields(plan_id='nf-next-tasks', title='Task 2', depends_on='none')
    add_task_with_fields(plan_id='nf-next-tasks', title='Task 3', depends_on='TASK-1')

    result = cmd_next_tasks(_next_tasks_ns(plan_id='nf-next-tasks'))

    assert result['status'] == 'success'
    assert result['ready_count'] == 2
    ready_titles = [t['title'] for t in result['ready_tasks']]
    assert 'Task 1' in ready_titles
    assert 'Task 2' in ready_titles
    assert result['blocked_count'] == 1


def test_next_tasks_includes_skills(plan_context):
    """next-tasks includes skills in ready task output."""
    add_task_with_fields(
        plan_id='nf-next-skills',
        title='Task with skills',
        skills=['pm-dev-java:java-core', 'pm-dev-java:java-cdi'],
        depends_on='none',
    )

    result = cmd_next_tasks(_next_tasks_ns(plan_id='nf-next-skills'))

    assert result['status'] == 'success'
    assert 'pm-dev-java:java-core' in result['ready_tasks'][0]['skills']
    assert 'pm-dev-java:java-cdi' in result['ready_tasks'][0]['skills']


def test_next_tasks_shows_blocked(plan_context):
    """next-tasks shows blocked tasks with waiting_for."""
    add_task_with_fields(plan_id='nf-next-blocked', title='Blocked task', depends_on='TASK-99')

    result = cmd_next_tasks(_next_tasks_ns(plan_id='nf-next-blocked'))

    assert result['status'] == 'success'
    assert result['ready_count'] == 0
    assert result['blocked_count'] == 1
    assert 'TASK-99' in result['blocked_tasks'][0]['waiting_for']


def test_next_tasks_includes_in_progress(plan_context):
    """next-tasks includes in_progress tasks."""
    add_task_with_fields(
        plan_id='nf-next-inprog',
        title='Task 1',
        depends_on='none',
        steps=['src/main/java/FileA.java', 'src/main/java/FileB.java'],
    )
    add_task_with_fields(plan_id='nf-next-inprog', title='Task 2', depends_on='none')

    # Complete first step of task 1 (puts task in_progress with step 2 remaining)
    cmd_finalize_step(_finalize_step_ns(plan_id='nf-next-inprog', task=1, step=1, outcome='done'))

    result = cmd_next_tasks(_next_tasks_ns(plan_id='nf-next-inprog'))

    assert result['status'] == 'success'
    assert result['in_progress_count'] == 1
    assert result['ready_count'] == 1


def test_next_returns_new_fields(plan_context):
    """Next command returns domain, profile, skills in output."""
    add_task_with_fields(
        plan_id='nf-next-fields',
        title='Task with all fields',
        domain='java',
        profile='implementation',
        skills=['pm-dev-java:java-core', 'pm-dev-java:java-cdi'],
    )

    result = cmd_next(_next_ns(plan_id='nf-next-fields'))

    assert result['status'] == 'success'
    assert result['next']['domain'] == 'java'
    assert result['next']['profile'] == 'implementation'
    assert len(result['next']['skills']) == 2
    assert result['next']['origin'] == 'plan'


# =============================================================================
# Tests: file format
# =============================================================================


def test_file_contains_all_new_fields(plan_context):
    """Created file contains all new fields (JSON format)."""
    add_task_with_fields(
        plan_id='nf-file-fields',
        title='Complete task',
        domain='java',
        profile='implementation',
        skills=['pm-dev-java:java-core', 'pm-dev-java:java-cdi'],
        origin='plan',
    )

    task_dir = Path(os.environ['PLAN_BASE_DIR']) / 'plans' / 'nf-file-fields' / 'tasks'
    files = list(task_dir.glob('TASK-001.json'))
    content = files[0].read_text(encoding='utf-8')
    task = json.loads(content)

    assert task['domain'] == 'java'
    assert task['profile'] == 'implementation'
    assert task['origin'] == 'plan'
    assert 'pm-dev-java:java-core' in task['skills']
    assert 'pm-dev-java:java-cdi' in task['skills']


# =============================================================================
# Tests: arbitrary domains (config-driven, not hardcoded)
# =============================================================================


def test_add_with_arbitrary_domain(plan_context):
    """Add accepts any domain value (domains are config-driven)."""
    toon = """title: Requirements task
deliverable: 1
domain: requirements
profile: implementation
description: Desc
skills:
  - pm-requirements:req-core
steps:
  - docs/requirements.adoc (write-new)"""
    result = cmd_add(_add_ns(plan_id='nf-arb-dom', content=toon.replace('\n', '\\n')))

    assert result['status'] == 'success'
    assert result['task']['domain'] == 'requirements'


def test_add_with_custom_domain(plan_context):
    """Add accepts custom domain values (config-driven)."""
    toon = """title: Custom domain task
deliverable: 1
domain: my-custom-domain
profile: implementation
description: Desc
skills:
  - pm-dev-java:java-core
steps:
  - src/main/java/File.java (write-replace)"""
    result = cmd_add(_add_ns(plan_id='nf-cust-dom', content=toon.replace('\n', '\\n')))

    assert result['status'] == 'success'
    assert result['task']['domain'] == 'my-custom-domain'


def test_update_with_arbitrary_domain(plan_context):
    """Update accepts any domain value."""
    add_task_with_fields(plan_id='nf-upd-arb-dom', title='Task', domain='java')

    result = cmd_update(_update_ns(plan_id='nf-upd-arb-dom', number=1, domain='requirements'))

    assert result['status'] == 'success'
    assert result['task']['domain'] == 'requirements'


# =============================================================================
# Tests: task type field
# =============================================================================


def test_add_with_plan_origin(plan_context):
    """Add task with plan origin (default)."""
    toon = """title: Implementation task
deliverable: 1
domain: java
profile: implementation
description: Desc
skills:
  - pm-dev-java:java-core
steps:
  - src/main/java/File.java (write-replace)"""
    result = cmd_add(_add_ns(plan_id='nf-plan-origin', content=toon.replace('\n', '\\n')))

    assert result['status'] == 'success'
    assert result['task']['origin'] == 'plan'


def test_add_with_fix_origin(plan_context):
    """Add task with fix origin."""
    toon = """title: Fix task
deliverable: 1
domain: java
profile: implementation
origin: fix
description: Desc
skills:
  - pm-dev-java:java-core
steps:
  - src/main/java/File.java (write-replace)"""
    result = cmd_add(_add_ns(plan_id='nf-fix-origin', content=toon.replace('\n', '\\n')))

    assert result['status'] == 'success'
    assert result['task']['origin'] == 'fix'
