#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-tasks.py new fields: domain, profile, skills, origin.

Tier 2 (direct import) tests with 2 subprocess tests for CLI plumbing.
"""


from _task_new_fields_fixtures import SCRIPT_PATH, _add_ns, cmd_add

from conftest import run_script


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


# =============================================================================
# Tests: task ID format TASK-NNN (type in JSON only, not in filename)
# =============================================================================


def test_task_file_uses_numbered_format(plan_context):
    """Task file uses TASK-NNN.json format."""
    toon = """title: Implementation task with long title
deliverable: 1
domain: java
profile: implementation
description: Desc
skills:
  - pm-dev-java:java-core
steps:
  - src/main/java/File.java (write-replace)"""
    result = cmd_add(_add_ns(plan_id='nf-num-fmt', content=toon.replace('\n', '\\n')))

    assert result['status'] == 'success'
    assert result['file'] == 'TASK-001.json'
    assert result['task']['origin'] == 'plan'


def test_fix_task_file_uses_numbered_format(plan_context):
    """Fix task file uses same TASK-NNN.json format."""
    toon = """title: Fix broken test
deliverable: 1
domain: java
profile: testing
origin: fix
description: Desc
skills:
  - pm-dev-java:junit-core
steps:
  - src/test/java/FileTest.java (write-new)"""
    result = cmd_add(_add_ns(plan_id='nf-fix-fmt', content=toon.replace('\n', '\\n')))

    assert result['status'] == 'success'
    assert result['file'] == 'TASK-001.json'
    assert result['task']['origin'] == 'fix'


# =============================================================================
# Subprocess tests (CLI plumbing - Tier 3)
# =============================================================================


def test_cli_tasks_by_domain_subcommand_removed_exits_2():
    """The removed `tasks-by-domain` subcommand exits with code 2 (argparse error)."""
    result = run_script(SCRIPT_PATH, 'tasks-by-domain', '--plan-id', 'test-plan')
    assert result.returncode == 2


def test_cli_tasks_by_profile_subcommand_removed_exits_2():
    """The removed `tasks-by-profile` subcommand exits with code 2 (argparse error)."""
    result = run_script(SCRIPT_PATH, 'tasks-by-profile', '--plan-id', 'test-plan')
    assert result.returncode == 2
