# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_status_manage_status_transition_archive_fixtures import (
    Namespace,
    _seed_finalize_phase_plan,
    _stub_finding_queries,
    cmd_archive,
)

# =============================================================================
# D2 — Finalize completion boundary asserts the blocking-findings STATE.
#
# The blocking-findings gate historically fired only when a
# `phase_handshake capture --phase 6-finalize` CALL was issued during finalize;
# a missing call left no row and raised nothing, so a plan could complete with
# actionable findings still `pending`, and "the gate never ran" was
# indistinguishable from "the gate passed". cmd_transition (completing
# 6-finalize) and cmd_archive (normal completion) now assert the STATE directly,
# armed by REACHING the completion boundary rather than by an optional call.
#
# These controls are the deliverable's proof. The NEGATIVE controls drive a
# pending actionable finding through the REAL blocking-count predicate (via
# `_stub_finding_queries`, the same seam the 5->6 boundary tests use) and assert
# the completion is REFUSED — and refused ONLY because the gate was added, so
# each fails against the pre-fix code. The POSITIVE controls confirm a clean plan
# is still admitted, and the abandonment exemption confirms the gate discriminates
# on the completion intent rather than blocking unconditionally.
# =============================================================================


def test_archive_refuses_when_actionable_finding_pending(plan_context, monkeypatch):
    """NEGATIVE control: a normal-completion archive (no --reason) is REFUSED
    while an actionable finding is pending, and the plan dir is NOT moved."""
    _stub_finding_queries(monkeypatch, {'sonar-issue': 2})
    plan_id = 'finalize-block-archive'
    _seed_finalize_phase_plan(plan_id)

    result = cmd_archive(Namespace(plan_id=plan_id, dry_run=False, reason=None))

    assert result is not None
    assert result['status'] == 'error'
    assert result['error'] == 'blocking_findings_present'
    assert result['blocking_count'] == 2
    assert result['per_type']['sonar-issue'] == 2
    # The plan directory survives — no move happened.
    assert plan_context.plan_dir_for(plan_id).exists()
    assert 'archived_to' not in result
