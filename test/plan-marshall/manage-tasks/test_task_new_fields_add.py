#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-tasks.py new fields: add, across every profile and skills/origin combination."""


from _task_new_fields_fixtures import _add_ns, add_task_with_fields, cmd_add

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


def test_add_with_sonar_origin(plan_context):
    """Add task with sonar origin."""
    toon = """title: Sonar fix task
deliverable: 1
domain: java
profile: quality
origin: sonar
description: Desc
skills:
  - pm-dev-java:java-core
steps:
  - src/main/java/File.java (write-replace)"""
    result = cmd_add(_add_ns(plan_id='nf-sonar-origin', content=toon.replace('\n', '\\n')))

    assert result['status'] == 'success'
    assert result['task']['origin'] == 'sonar'
