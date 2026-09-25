# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import _compose_ns, cmd_compose, json


def test_early_terminate_analysis_with_empty_files(plan_context):
    """Row 1 — analysis with affected_files_count=0 → early_terminate=true."""
    result = cmd_compose(
        _compose_ns(
            plan_id='matrix-analysis',
            change_type='analysis',
            scope_estimate='none',
            affected_files_count=0,
        )
    )
    assert result is not None and result['rule_fired'] == 'early_terminate_analysis'
    assert result['phase_5']['early_terminate'] is True
    assert result['phase_5']['verification_steps_count'] == 0
    # Phase 6 keeps the records-and-archive trio: lessons-capture, adr-propose
    # (an analysis plan that made a decision can still propose an ADR), and
    # archive-plan.
    assert result['phase_6']['steps_count'] == 3



def test_early_terminate_analysis_falls_through_when_task_queue_pending(plan_context):
    """Row 1 task-queue guard — analysis + 0 files + pending task → Rule 7 default.

    End-to-end exercise of the task-queue-aware predicate: one pending task file
    on disk forces Rule 1 to fall through to Rule 7, so phase-5 iterates the queue
    instead of short-circuiting past work that is still owed.
    """
    plan_id = 'matrix-analysis-pending-task'
    tasks_dir = plan_context.plan_dir_for(plan_id) / 'tasks'
    tasks_dir.mkdir(parents=True, exist_ok=True)
    (tasks_dir / 'TASK-001.json').write_text(json.dumps({'number': 1, 'status': 'pending', 'steps': []}, indent=2))
    result = cmd_compose(
        _compose_ns(
            plan_id=plan_id,
            change_type='analysis',
            scope_estimate='none',
            affected_files_count=0,
        )
    )
    assert result is not None and result['rule_fired'] == 'default'
    assert result['phase_5']['early_terminate'] is False



# =============================================================================
# Rule precedence + edge-case coverage
# =============================================================================


def test_early_terminate_wins_over_recipe_when_both_match(plan_context):
    """Rule 1 evaluates before Rule 2 — analysis + recipe_key + 0 files → early_terminate."""
    result = cmd_compose(
        _compose_ns(
            plan_id='matrix-precedence-er',
            change_type='analysis',
            scope_estimate='none',
            recipe_key='lesson_cleanup',
            affected_files_count=0,
        )
    )
    assert result is not None and result['rule_fired'] == 'early_terminate_analysis'
