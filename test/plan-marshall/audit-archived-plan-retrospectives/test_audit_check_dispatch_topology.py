#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``dispatch-topology`` — a leaf that dispatches is flagged, an orchestrator or
phase caller is clean, and a plan with no work log reports zero rather than
an absence.
"""

from pathlib import Path

from _audit_fixtures import audit


def _plan_with_worklog(repo_root: Path, name: str, lines: str) -> audit.PlanInputs:
    pd = repo_root / ".plan" / "local" / "archived-plans" / name
    (pd / "logs").mkdir(parents=True, exist_ok=True)
    (pd / "references.json").write_text('{"scope_estimate": "surgical"}', encoding="utf-8")
    (pd / "status.json").write_text(
        '{"metadata": {"change_type": "bug_fix"}}', encoding="utf-8"
    )
    (pd / "logs" / "work.log").write_text(lines, encoding="utf-8")
    return audit.collect_inputs(pd)


def test_dispatch_topology_flags_leaf_dispatch(tmp_path):
    # A dispatch whose caller is a LEAF skill (execute-task) is a topology
    # violation; the orchestrator dispatch and the bare role marker are clean.
    log = (
        "[2026-06-29T09:00:01Z] [INFO] [a] [DISPATCH] (plan-marshall:plan-marshall) target=execution-context-level-3 role=phase-5-execute\n"
        "[2026-06-29T09:00:02Z] [INFO] [b] [DISPATCH] (plan-marshall:execute-task) target=execution-context-level-2 role=phase-5-execute\n"
        "[2026-06-29T09:00:03Z] [INFO] [c] [DISPATCH] (plan-marshall:plan-marshall) role=phase-6-finalize\n"
    )
    row = audit.check_dispatch_topology(_plan_with_worklog(tmp_path, "p1", log))
    assert row["dispatch_count"] == 2  # bare role marker (no target=) excluded
    assert row["leaf_dispatch"] == 1
    assert "plan-marshall:execute-task" in row["violators"]
    assert audit._dispatch_topology_genuine(row) is True


def test_dispatch_topology_clean_on_orchestrator_and_phase_callers(tmp_path):
    # The orchestrator and phase-context callers are the allowed dispatchers.
    log = (
        "[2026-06-29T09:00:01Z] [INFO] [a] [DISPATCH] (plan-marshall:plan-marshall) target=execution-context-level-3 role=phase-5-execute\n"
        "[2026-06-29T09:00:02Z] [INFO] [b] [DISPATCH] (plan-marshall:phase-5-execute) target=execution-context-level-4 role=verification-feedback\n"
    )
    row = audit.check_dispatch_topology(_plan_with_worklog(tmp_path, "clean", log))
    assert row["leaf_dispatch"] == 0
    assert row["violators"] == ""
    assert audit._dispatch_topology_genuine(row) is False


def test_dispatch_topology_no_worklog_is_zero(tmp_path):
    pd = tmp_path / ".plan" / "local" / "archived-plans" / "nolog"
    pd.mkdir(parents=True)
    (pd / "references.json").write_text('{"scope_estimate": "surgical"}', encoding="utf-8")
    (pd / "status.json").write_text(
        '{"metadata": {"change_type": "bug_fix"}}', encoding="utf-8"
    )
    row = audit.check_dispatch_topology(audit.collect_inputs(pd))
    assert row["dispatch_count"] == 0
    assert row["leaf_dispatch"] == 0
