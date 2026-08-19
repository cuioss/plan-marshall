#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-tasks.py new fields: domain, profile, skills, origin.

Tier 2 (direct import) tests with 2 subprocess tests for CLI plumbing.
"""


from _task_new_fields_fixtures import (
    _add_ns,
    _list_ns,
    _read_ns,
    add_task_with_fields,
    cmd_add,
    cmd_list,
    cmd_read,
)

# =============================================================================
# Tests: add with new fields
# =============================================================================


def test_add_with_profile(plan_context):
    """Add task with profile field."""
    result = add_task_with_fields(
        plan_id='nf-add-prof',
        title='Test task',
        deliverable=1,
        domain='java',
        profile='implementation',
        skills=['pm-dev-java:java-core'],
    )

    assert result['status'] == 'success'
    assert result['task']['profile'] == 'implementation'


def test_add_with_testing_profile(plan_context):
    """Add task with testing profile."""
    result = add_task_with_fields(
        plan_id='nf-test-prof',
        title='Test task',
        deliverable=1,
        domain='java',
        profile='testing',
        skills=['pm-dev-java:junit-core'],
    )

    assert result['status'] == 'success'
    assert result['task']['profile'] == 'testing'


def test_add_with_quality_profile(plan_context):
    """Add task with quality profile."""
    result = add_task_with_fields(
        plan_id='nf-qual-prof',
        title='Quality check task',
        deliverable=1,
        domain='java',
        profile='quality',
        skills=['pm-dev-java:java-maintenance'],
    )

    assert result['status'] == 'success'
    assert result['task']['profile'] == 'quality'


def test_add_with_skills(plan_context):
    """Add task with skills array."""
    result = add_task_with_fields(
        plan_id='nf-skills',
        title='Multi-skill task',
        deliverable=1,
        domain='java',
        profile='implementation',
        skills=['pm-dev-java:java-core', 'pm-dev-java:java-cdi', 'pm-dev-java:java-lombok'],
    )

    assert result['status'] == 'success'
    assert len(result['task']['skills']) == 3
    assert 'pm-dev-java:java-core' in result['task']['skills']


def test_add_with_origin(plan_context):
    """Add task with origin field."""
    result = add_task_with_fields(
        plan_id='nf-origin',
        title='Plan origin task',
        deliverable=1,
        domain='java',
        profile='implementation',
        origin='plan',
    )

    assert result['status'] == 'success'
    assert result['task']['origin'] == 'plan'


def test_add_with_arbitrary_profile(plan_context):
    """Add accepts any profile value (profiles are config-driven, not hardcoded)."""
    toon = """title: Architecture task
deliverable: 1
domain: java
profile: architecture
description: Desc
skills:
  - pm-dev-java:java-core
steps:
  - src/main/java/File.java (write-replace)"""
    result = cmd_add(_add_ns(plan_id='nf-arb-prof', content=toon.replace('\n', '\\n')))

    assert result['status'] == 'success'
    assert result['task']['profile'] == 'architecture'


def test_add_with_planning_profile(plan_context):
    """Add accepts 'planning' profile (config-driven)."""
    toon = """title: Planning task
deliverable: 1
domain: java
profile: planning
description: Desc
skills:
  - pm-dev-java:java-core
steps:
  - src/main/java/File.java (write-replace)"""
    result = cmd_add(_add_ns(plan_id='nf-plan-prof', content=toon.replace('\n', '\\n')))

    assert result['status'] == 'success'
    assert result['task']['profile'] == 'planning'


def test_add_with_custom_profile(plan_context):
    """Add accepts custom profile values (config-driven)."""
    toon = """title: Custom task
deliverable: 1
domain: java
profile: my-custom-profile
description: Desc
skills:
  - pm-dev-java:java-core
steps:
  - src/main/java/File.java (write-replace)"""
    result = cmd_add(_add_ns(plan_id='nf-cust-prof', content=toon.replace('\n', '\\n')))

    assert result['status'] == 'success'
    assert result['task']['profile'] == 'my-custom-profile'


def test_add_fails_with_invalid_skill_format(plan_context):
    """Add fails with invalid skill format (missing colon)."""
    toon = """title: Invalid skill
deliverable: 1
domain: java
profile: implementation
description: Desc
skills:
  - invalid-skill-no-colon
steps:
  - src/main/java/File.java (write-replace)"""
    result = cmd_add(_add_ns(plan_id='nf-bad-skill', content=toon.replace('\n', '\\n')))

    assert result['status'] == 'error'
    msg = result.get('message', '').lower()
    assert 'skill' in msg or 'bundle:skill' in msg


# =============================================================================
# Tests: read returns new fields
# =============================================================================


def test_get_returns_domain(plan_context):
    """Read returns domain field."""
    add_task_with_fields(plan_id='nf-get-dom', title='Test', domain='javascript', profile='implementation')
    result = cmd_read(_read_ns(plan_id='nf-get-dom', number=1))

    assert result['status'] == 'success'
    assert result['task']['domain'] == 'javascript'


def test_get_returns_profile(plan_context):
    """Read returns profile field."""
    add_task_with_fields(plan_id='nf-get-prof', title='Test', profile='testing')
    result = cmd_read(_read_ns(plan_id='nf-get-prof', number=1))

    assert result['status'] == 'success'
    assert result['task']['profile'] == 'testing'


def test_get_returns_skills(plan_context):
    """Read returns skills array."""
    add_task_with_fields(
        plan_id='nf-get-skills', title='Test', skills=['pm-dev-java:java-core', 'pm-dev-java:java-cdi']
    )
    result = cmd_read(_read_ns(plan_id='nf-get-skills', number=1))

    assert result['status'] == 'success'
    assert len(result['task']['skills']) == 2
    assert 'pm-dev-java:java-core' in result['task']['skills']
    assert 'pm-dev-java:java-cdi' in result['task']['skills']


def test_get_returns_origin(plan_context):
    """Read returns origin field."""
    add_task_with_fields(plan_id='nf-get-origin', title='Test', origin='plan')
    result = cmd_read(_read_ns(plan_id='nf-get-origin', number=1))

    assert result['status'] == 'success'
    assert result['task']['origin'] == 'plan'


# =============================================================================
# Tests: list includes new columns
# =============================================================================


def test_list_includes_domain_column(plan_context):
    """List includes domain column."""
    add_task_with_fields(plan_id='nf-list-dom', title='Java task', domain='java', profile='implementation')
    add_task_with_fields(plan_id='nf-list-dom', title='JS task', domain='javascript', profile='implementation')

    result = cmd_list(_list_ns(plan_id='nf-list-dom'))

    assert result['status'] == 'success'
    domains = [t['domain'] for t in result['tasks_table']]
    assert 'java' in domains
    assert 'javascript' in domains


def test_list_includes_profile_column(plan_context):
    """List includes profile column."""
    add_task_with_fields(plan_id='nf-list-prof', title='Impl task', profile='implementation')
    add_task_with_fields(plan_id='nf-list-prof', title='Test task', profile='testing')

    result = cmd_list(_list_ns(plan_id='nf-list-prof'))

    assert result['status'] == 'success'
    profiles = [t['profile'] for t in result['tasks_table']]
    assert 'implementation' in profiles
    assert 'testing' in profiles
