# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import _mem, _write_status_metadata

# =============================================================================
# Decision-log emission lands in the plan's own logs/decision.log (loggability fix)
# =============================================================================


def test_emit_decision_log_writes_in_process(plan_context):
    """``_emit_decision_log`` writes directly to the plan's decision.log.

    Regression guard for the ``unloggable`` defect: the composer runs from the
    plugin cache (outside the project tree), so the former
    executor-subprocess emission silently dropped every line. The in-process
    write via ``plan_logging.log_entry`` must land the entry in
    ``{plan_dir}/logs/decision.log``. status.json must exist for the log path
    to resolve plan-scoped rather than to the global fallback.
    """
    plan_id = 'decision-log-in-process'
    _write_status_metadata(plan_context, plan_id, {'change_type': 'feature'})
    message = '(plan-marshall:manage-execution-manifest:compose) Rule default fired — sentinel'

    _mem._emit_decision_log(plan_id, message)

    decision_log = plan_context.plan_dir_for(plan_id) / 'logs' / 'decision.log'
    assert decision_log.is_file(), 'decision.log was not written in-process'
    assert message in decision_log.read_text(encoding='utf-8')
