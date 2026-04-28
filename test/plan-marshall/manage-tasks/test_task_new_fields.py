#!/usr/bin/env python3
"""Tests for manage-tasks.py new fields: domain, profile, skills, origin.

Tier 2 (direct import) tests with 2 subprocess tests for CLI plumbing.
"""

import json
import os
from argparse import Namespace
from pathlib import Path

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


_crud = _load_module('_tasks_cmd_crud_nf', '_tasks_crud.py')
_query = _load_module('_tasks_cmd_query_nf', '_tasks_query.py')
_step = _load_module('_tasks_cmd_step_nf', '_cmd_step.py')

cmd_prepare_add = _crud.cmd_prepare_add
cmd_commit_add = _crud.cmd_commit_add
cmd_update = _crud.cmd_update


def _add_task_pathalloc(plan_id, toon_text, slot=None):
    """Run the path-allocate add flow end-to-end."""
    prep = cmd_prepare_add(Namespace(plan_id=plan_id, slot=slot))
    if prep.get('status') != 'success':
        return prep
    Path(prep['path']).write_text(toon_text, encoding='utf-8')
    return cmd_commit_add(Namespace(plan_id=plan_id, slot=slot))


def cmd_add(ns):
    """Test shim: drive the three-step path-allocate add flow.

    Accepts the legacy `Namespace(plan_id, content)` shape where `content`
    is a newline-escaped TOON string.
    """
    text = (ns.content or '').replace('\\n', '\n')
    return _add_task_pathalloc(ns.plan_id, text)


cmd_read, cmd_list, cmd_next = _query.cmd_read, _query.cmd_list, _query.cmd_next
cmd_next_tasks, cmd_tasks_by_domain, cmd_tasks_by_profile = (
    _query.cmd_next_tasks,
    _query.cmd_tasks_by_domain,
    _query.cmd_tasks_by_profile,
)
cmd_finalize_step = _step.cmd_finalize_step


# =============================================================================
# Test Helpers
# =============================================================================


def build_task_toon_with_new_fields(
    title='Test task',
    deliverable=1,
    domain='java',
    profile='implementation',
    skills=None,
    origin='plan',
    description='Task description',
    steps=None,
    depends_on='none',
):
    """Build TOON content for task with new fields."""
    if steps is None:
        steps = ['src/main/java/TestFile.java']
    if skills is None:
        skills = ['pm-dev-java:java-core']

    lines = [
        f'title: {title}',
        f'deliverable: {deliverable}',
        f'domain: {domain}',
        f'profile: {profile}',
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


def _add_ns(plan_id='test-plan', content=''):
    """Build Namespace for cmd_add."""
    return Namespace(plan_id=plan_id, content=content)


def _read_ns(plan_id='test-plan', number=1):
    """Build Namespace for cmd_read."""
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


def _finalize_step_ns(plan_id='test-plan', task=1, step=1, outcome='done', reason=None):
    """Build Namespace for cmd_finalize_step."""
    return Namespace(plan_id=plan_id, task_number=task, step=step, outcome=outcome, reason=reason)


def _tasks_by_domain_ns(plan_id='test-plan', domain='java'):
    """Build Namespace for cmd_tasks_by_domain."""
    return Namespace(plan_id=plan_id, domain=domain)


def _tasks_by_profile_ns(plan_id='test-plan', profile='implementation'):
    """Build Namespace for cmd_tasks_by_profile."""
    return Namespace(plan_id=plan_id, profile=profile)


def _next_tasks_ns(plan_id='test-plan'):
    """Build Namespace for cmd_next_tasks."""
    return Namespace(plan_id=plan_id)


def add_task_with_fields(plan_id='test-plan', **kwargs):
    """Helper to add a task with new fields."""
    toon = build_task_toon_with_new_fields(**kwargs)
    return cmd_add(_add_ns(plan_id=plan_id, content=toon.replace('\n', '\\n')))


# =============================================================================
# Tests: add with new fields
# =============================================================================


def test_add_with_profile():
    """Add task with profile field."""
    with PlanContext(plan_id='nf-add-prof'):
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


def test_add_with_testing_profile():
    """Add task with testing profile."""
    with PlanContext(plan_id='nf-test-prof'):
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


def test_add_with_quality_profile():
    """Add task with quality profile."""
    with PlanContext(plan_id='nf-qual-prof'):
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


def test_add_with_skills():
    """Add task with skills array."""
    with PlanContext(plan_id='nf-skills'):
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


def test_add_with_origin():
    """Add task with origin field."""
    with PlanContext(plan_id='nf-origin'):
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


def test_add_with_arbitrary_profile():
    """Add accepts any profile value (profiles are config-driven, not hardcoded)."""
    with PlanContext(plan_id='nf-arb-prof'):
        toon = """title: Architecture task
deliverable: 1
domain: java
profile: architecture
description: Desc
skills:
  - pm-dev-java:java-core
steps:
  - src/main/java/File.java"""
        result = cmd_add(_add_ns(plan_id='nf-arb-prof', content=toon.replace('\n', '\\n')))

        assert result['status'] == 'success'
        assert result['task']['profile'] == 'architecture'


def test_add_with_planning_profile():
    """Add accepts 'planning' profile (config-driven)."""
    with PlanContext(plan_id='nf-plan-prof'):
        toon = """title: Planning task
deliverable: 1
domain: java
profile: planning
description: Desc
skills:
  - pm-dev-java:java-core
steps:
  - src/main/java/File.java"""
        result = cmd_add(_add_ns(plan_id='nf-plan-prof', content=toon.replace('\n', '\\n')))

        assert result['status'] == 'success'
        assert result['task']['profile'] == 'planning'


def test_add_with_custom_profile():
    """Add accepts custom profile values (config-driven)."""
    with PlanContext(plan_id='nf-cust-prof'):
        toon = """title: Custom task
deliverable: 1
domain: java
profile: my-custom-profile
description: Desc
skills:
  - pm-dev-java:java-core
steps:
  - src/main/java/File.java"""
        result = cmd_add(_add_ns(plan_id='nf-cust-prof', content=toon.replace('\n', '\\n')))

        assert result['status'] == 'success'
        assert result['task']['profile'] == 'my-custom-profile'


def test_add_fails_with_invalid_skill_format():
    """Add fails with invalid skill format (missing colon)."""
    with PlanContext(plan_id='nf-bad-skill'):
        toon = """title: Invalid skill
deliverable: 1
domain: java
profile: implementation
description: Desc
skills:
  - invalid-skill-no-colon
steps:
  - Step 1"""
        result = cmd_add(_add_ns(plan_id='nf-bad-skill', content=toon.replace('\n', '\\n')))

        assert result['status'] == 'error'
        msg = result.get('message', '').lower()
        assert 'skill' in msg or 'bundle:skill' in msg


# =============================================================================
# Tests: read returns new fields
# =============================================================================


def test_get_returns_domain():
    """Read returns domain field."""
    with PlanContext(plan_id='nf-get-dom'):
        add_task_with_fields(plan_id='nf-get-dom', title='Test', domain='javascript', profile='implementation')
        result = cmd_read(_read_ns(plan_id='nf-get-dom', number=1))

        assert result['status'] == 'success'
        assert result['task']['domain'] == 'javascript'


def test_get_returns_profile():
    """Read returns profile field."""
    with PlanContext(plan_id='nf-get-prof'):
        add_task_with_fields(plan_id='nf-get-prof', title='Test', profile='testing')
        result = cmd_read(_read_ns(plan_id='nf-get-prof', number=1))

        assert result['status'] == 'success'
        assert result['task']['profile'] == 'testing'


def test_get_returns_skills():
    """Read returns skills array."""
    with PlanContext(plan_id='nf-get-skills'):
        add_task_with_fields(
            plan_id='nf-get-skills', title='Test', skills=['pm-dev-java:java-core', 'pm-dev-java:java-cdi']
        )
        result = cmd_read(_read_ns(plan_id='nf-get-skills', number=1))

        assert result['status'] == 'success'
        assert len(result['task']['skills']) == 2
        assert 'pm-dev-java:java-core' in result['task']['skills']
        assert 'pm-dev-java:java-cdi' in result['task']['skills']


def test_get_returns_origin():
    """Read returns origin field."""
    with PlanContext(plan_id='nf-get-origin'):
        add_task_with_fields(plan_id='nf-get-origin', title='Test', origin='plan')
        result = cmd_read(_read_ns(plan_id='nf-get-origin', number=1))

        assert result['status'] == 'success'
        assert result['task']['origin'] == 'plan'


# =============================================================================
# Tests: list includes new columns
# =============================================================================


def test_list_includes_domain_column():
    """List includes domain column."""
    with PlanContext(plan_id='nf-list-dom'):
        add_task_with_fields(plan_id='nf-list-dom', title='Java task', domain='java', profile='implementation')
        add_task_with_fields(plan_id='nf-list-dom', title='JS task', domain='javascript', profile='implementation')

        result = cmd_list(_list_ns(plan_id='nf-list-dom'))

        assert result['status'] == 'success'
        domains = [t['domain'] for t in result['tasks_table']]
        assert 'java' in domains
        assert 'javascript' in domains


def test_list_includes_profile_column():
    """List includes profile column."""
    with PlanContext(plan_id='nf-list-prof'):
        add_task_with_fields(plan_id='nf-list-prof', title='Impl task', profile='implementation')
        add_task_with_fields(plan_id='nf-list-prof', title='Test task', profile='testing')

        result = cmd_list(_list_ns(plan_id='nf-list-prof'))

        assert result['status'] == 'success'
        profiles = [t['profile'] for t in result['tasks_table']]
        assert 'implementation' in profiles
        assert 'testing' in profiles


# =============================================================================
# Tests: update with new field parameters
# =============================================================================


def test_update_domain():
    """Update domain field."""
    with PlanContext(plan_id='nf-upd-dom'):
        add_task_with_fields(plan_id='nf-upd-dom', title='Task', domain='java')
        result = cmd_update(_update_ns(plan_id='nf-upd-dom', number=1, domain='javascript'))

        assert result['status'] == 'success'
        assert result['task']['domain'] == 'javascript'

        # Verify with get
        get_result = cmd_read(_read_ns(plan_id='nf-upd-dom', number=1))
        assert get_result['task']['domain'] == 'javascript'


def test_update_profile():
    """Update profile field."""
    with PlanContext(plan_id='nf-upd-prof'):
        add_task_with_fields(plan_id='nf-upd-prof', title='Task', profile='implementation')
        result = cmd_update(_update_ns(plan_id='nf-upd-prof', number=1, profile='testing'))

        assert result['status'] == 'success'
        assert result['task']['profile'] == 'testing'

        # Verify with get
        get_result = cmd_read(_read_ns(plan_id='nf-upd-prof', number=1))
        assert get_result['task']['profile'] == 'testing'


def test_update_skills():
    """Update skills field."""
    with PlanContext(plan_id='nf-upd-skills'):
        add_task_with_fields(plan_id='nf-upd-skills', title='Task', skills=['pm-dev-java:java-core'])
        result = cmd_update(
            _update_ns(
                plan_id='nf-upd-skills',
                number=1,
                skills='pm-dev-java:java-cdi,pm-dev-java:java-lombok',
            )
        )

        assert result['status'] == 'success'

        # Verify with get
        get_result = cmd_read(_read_ns(plan_id='nf-upd-skills', number=1))
        assert 'pm-dev-java:java-cdi' in get_result['task']['skills']
        assert 'pm-dev-java:java-lombok' in get_result['task']['skills']


def test_update_deliverable():
    """Update deliverable field (single integer)."""
    with PlanContext(plan_id='nf-upd-del'):
        add_task_with_fields(plan_id='nf-upd-del', title='Task', deliverable=1)
        result = cmd_update(_update_ns(plan_id='nf-upd-del', number=1, deliverable=2))

        assert result['status'] == 'success'

        # Verify with get
        get_result = cmd_read(_read_ns(plan_id='nf-upd-del', number=1))
        assert get_result['task']['deliverable'] == 2


def test_update_with_arbitrary_profile():
    """Update accepts any profile value (profiles are config-driven)."""
    with PlanContext(plan_id='nf-upd-arb-prof'):
        add_task_with_fields(plan_id='nf-upd-arb-prof', title='Task', profile='implementation')

        result = cmd_update(_update_ns(plan_id='nf-upd-arb-prof', number=1, profile='architecture'))

        assert result['status'] == 'success'
        assert result['task']['profile'] == 'architecture'

        # Verify persisted
        get_result = cmd_read(_read_ns(plan_id='nf-upd-arb-prof', number=1))
        assert get_result['task']['profile'] == 'architecture'


def test_update_with_custom_profile():
    """Update accepts custom profile values."""
    with PlanContext(plan_id='nf-upd-cust-prof'):
        add_task_with_fields(plan_id='nf-upd-cust-prof', title='Task', profile='implementation')

        result = cmd_update(_update_ns(plan_id='nf-upd-cust-prof', number=1, profile='my-custom-profile'))

        assert result['status'] == 'success'
        assert result['task']['profile'] == 'my-custom-profile'


def test_update_fails_with_invalid_skills():
    """Update fails with invalid skill format."""
    with PlanContext(plan_id='nf-upd-bad-skill'):
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
# Tests: tasks-by-domain query
# =============================================================================


def test_tasks_by_domain_filters():
    """tasks-by-domain filters by domain."""
    with PlanContext(plan_id='nf-by-dom'):
        add_task_with_fields(plan_id='nf-by-dom', title='Java task 1', domain='java')
        add_task_with_fields(plan_id='nf-by-dom', title='JS task', domain='javascript')
        add_task_with_fields(plan_id='nf-by-dom', title='Java task 2', domain='java')

        result = cmd_tasks_by_domain(_tasks_by_domain_ns(plan_id='nf-by-dom', domain='java'))

        assert result['status'] == 'success'
        assert result['counts']['total'] == 2
        titles = [t['title'] for t in result['tasks_table']]
        assert 'Java task 1' in titles
        assert 'Java task 2' in titles
        assert 'JS task' not in titles


def test_tasks_by_domain_empty_result():
    """tasks-by-domain returns empty when no matches."""
    with PlanContext(plan_id='nf-by-dom-empty'):
        add_task_with_fields(plan_id='nf-by-dom-empty', title='Java task', domain='java')

        result = cmd_tasks_by_domain(_tasks_by_domain_ns(plan_id='nf-by-dom-empty', domain='javascript'))

        assert result['status'] == 'success'
        assert result['counts']['total'] == 0


# =============================================================================
# Tests: tasks-by-profile query
# =============================================================================


def test_tasks_by_profile_filters():
    """tasks-by-profile filters by profile."""
    with PlanContext(plan_id='nf-by-prof'):
        add_task_with_fields(plan_id='nf-by-prof', title='Impl task 1', profile='implementation')
        add_task_with_fields(plan_id='nf-by-prof', title='Test task', profile='testing')
        add_task_with_fields(plan_id='nf-by-prof', title='Impl task 2', profile='implementation')

        result = cmd_tasks_by_profile(_tasks_by_profile_ns(plan_id='nf-by-prof', profile='implementation'))

        assert result['status'] == 'success'
        assert result['counts']['total'] == 2
        titles = [t['title'] for t in result['tasks_table']]
        assert 'Impl task 1' in titles
        assert 'Impl task 2' in titles
        assert 'Test task' not in titles


def test_tasks_by_profile_testing():
    """tasks-by-profile filters testing profile."""
    with PlanContext(plan_id='nf-by-prof-test'):
        add_task_with_fields(plan_id='nf-by-prof-test', title='Impl task', profile='implementation')
        add_task_with_fields(plan_id='nf-by-prof-test', title='Test task 1', profile='testing')
        add_task_with_fields(plan_id='nf-by-prof-test', title='Test task 2', profile='testing')

        result = cmd_tasks_by_profile(_tasks_by_profile_ns(plan_id='nf-by-prof-test', profile='testing'))

        assert result['status'] == 'success'
        assert result['counts']['total'] == 2
        titles = [t['title'] for t in result['tasks_table']]
        assert 'Test task 1' in titles
        assert 'Test task 2' in titles


# =============================================================================
# Tests: next-tasks query
# =============================================================================


def test_next_tasks_returns_ready_tasks():
    """next-tasks returns all tasks with satisfied dependencies."""
    with PlanContext(plan_id='nf-next-tasks'):
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


def test_next_tasks_includes_skills():
    """next-tasks includes skills in ready task output."""
    with PlanContext(plan_id='nf-next-skills'):
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


def test_next_tasks_shows_blocked():
    """next-tasks shows blocked tasks with waiting_for."""
    with PlanContext(plan_id='nf-next-blocked'):
        add_task_with_fields(plan_id='nf-next-blocked', title='Blocked task', depends_on='TASK-99')

        result = cmd_next_tasks(_next_tasks_ns(plan_id='nf-next-blocked'))

        assert result['status'] == 'success'
        assert result['ready_count'] == 0
        assert result['blocked_count'] == 1
        assert 'TASK-99' in result['blocked_tasks'][0]['waiting_for']


def test_next_tasks_includes_in_progress():
    """next-tasks includes in_progress tasks."""
    with PlanContext(plan_id='nf-next-inprog'):
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


def test_next_returns_new_fields():
    """Next command returns domain, profile, skills in output."""
    with PlanContext(plan_id='nf-next-fields'):
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


def test_file_contains_all_new_fields():
    """Created file contains all new fields (JSON format)."""
    with PlanContext(plan_id='nf-file-fields'):
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


def test_add_with_arbitrary_domain():
    """Add accepts any domain value (domains are config-driven)."""
    with PlanContext(plan_id='nf-arb-dom'):
        toon = """title: Requirements task
deliverable: 1
domain: requirements
profile: implementation
description: Desc
skills:
  - pm-requirements:req-core
steps:
  - docs/requirements.adoc"""
        result = cmd_add(_add_ns(plan_id='nf-arb-dom', content=toon.replace('\n', '\\n')))

        assert result['status'] == 'success'
        assert result['task']['domain'] == 'requirements'


def test_add_with_custom_domain():
    """Add accepts custom domain values (config-driven)."""
    with PlanContext(plan_id='nf-cust-dom'):
        toon = """title: Custom domain task
deliverable: 1
domain: my-custom-domain
profile: implementation
description: Desc
skills:
  - pm-dev-java:java-core
steps:
  - src/main/java/File.java"""
        result = cmd_add(_add_ns(plan_id='nf-cust-dom', content=toon.replace('\n', '\\n')))

        assert result['status'] == 'success'
        assert result['task']['domain'] == 'my-custom-domain'


def test_update_with_arbitrary_domain():
    """Update accepts any domain value."""
    with PlanContext(plan_id='nf-upd-arb-dom'):
        add_task_with_fields(plan_id='nf-upd-arb-dom', title='Task', domain='java')

        result = cmd_update(_update_ns(plan_id='nf-upd-arb-dom', number=1, domain='requirements'))

        assert result['status'] == 'success'
        assert result['task']['domain'] == 'requirements'


# =============================================================================
# Tests: task type field
# =============================================================================


def test_add_with_plan_origin():
    """Add task with plan origin (default)."""
    with PlanContext(plan_id='nf-plan-origin'):
        toon = """title: Implementation task
deliverable: 1
domain: java
profile: implementation
description: Desc
skills:
  - pm-dev-java:java-core
steps:
  - src/main/java/File.java"""
        result = cmd_add(_add_ns(plan_id='nf-plan-origin', content=toon.replace('\n', '\\n')))

        assert result['status'] == 'success'
        assert result['task']['origin'] == 'plan'


def test_add_with_fix_origin():
    """Add task with fix origin."""
    with PlanContext(plan_id='nf-fix-origin'):
        toon = """title: Fix task
deliverable: 1
domain: java
profile: implementation
origin: fix
description: Desc
skills:
  - pm-dev-java:java-core
steps:
  - src/main/java/File.java"""
        result = cmd_add(_add_ns(plan_id='nf-fix-origin', content=toon.replace('\n', '\\n')))

        assert result['status'] == 'success'
        assert result['task']['origin'] == 'fix'


def test_add_with_sonar_origin():
    """Add task with sonar origin."""
    with PlanContext(plan_id='nf-sonar-origin'):
        toon = """title: Sonar fix task
deliverable: 1
domain: java
profile: quality
origin: sonar
description: Desc
skills:
  - pm-dev-java:java-core
steps:
  - src/main/java/File.java"""
        result = cmd_add(_add_ns(plan_id='nf-sonar-origin', content=toon.replace('\n', '\\n')))

        assert result['status'] == 'success'
        assert result['task']['origin'] == 'sonar'


# =============================================================================
# Tests: task ID format TASK-NNN (type in JSON only, not in filename)
# =============================================================================


def test_task_file_uses_numbered_format():
    """Task file uses TASK-NNN.json format."""
    with PlanContext(plan_id='nf-num-fmt'):
        toon = """title: Implementation task with long title
deliverable: 1
domain: java
profile: implementation
description: Desc
skills:
  - pm-dev-java:java-core
steps:
  - src/main/java/File.java"""
        result = cmd_add(_add_ns(plan_id='nf-num-fmt', content=toon.replace('\n', '\\n')))

        assert result['status'] == 'success'
        assert result['file'] == 'TASK-001.json'
        assert result['task']['origin'] == 'plan'


def test_fix_task_file_uses_numbered_format():
    """Fix task file uses same TASK-NNN.json format."""
    with PlanContext(plan_id='nf-fix-fmt'):
        toon = """title: Fix broken test
deliverable: 1
domain: java
profile: testing
origin: fix
description: Desc
skills:
  - pm-dev-java:junit-core
steps:
  - src/test/java/FileTest.java"""
        result = cmd_add(_add_ns(plan_id='nf-fix-fmt', content=toon.replace('\n', '\\n')))

        assert result['status'] == 'success'
        assert result['file'] == 'TASK-001.json'
        assert result['task']['origin'] == 'fix'


# =============================================================================
# Subprocess tests (CLI plumbing - Tier 3)
# =============================================================================


def test_cli_tasks_by_domain_missing_domain_exits_2():
    """tasks-by-domain without --domain exits with code 2 (argparse error)."""
    result = run_script(SCRIPT_PATH, 'tasks-by-domain', '--plan-id', 'test-plan')
    assert result.returncode == 2


def test_cli_tasks_by_profile_missing_profile_exits_2():
    """tasks-by-profile without --profile exits with code 2 (argparse error)."""
    result = run_script(SCRIPT_PATH, 'tasks-by-profile', '--plan-id', 'test-plan')
    assert result.returncode == 2
