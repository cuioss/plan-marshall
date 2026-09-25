#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_ceremony_finalize_selection_fixtures import Path, json

# =============================================================================
# Test: the plan-local declaration channel governs the ceremony gate
#
# THE R2 SYMMETRIC-PAIR REGRESSION. Two independent readers resolve the same
# ``steps[<step>].lane`` field: ``_read_step_owned_knob`` (behind
# ``_read_finalize_gates`` — each ceremony gate's run-at-all decision) and
# ``_lane_override_for`` (behind ``_has_declared_lane_override`` — the scope
# gate's declared-lane immunity predicate). Before the fix only the SECOND read
# the plan-local channel, so an operator's plan-scoped answer could grant
# scope-gate immunity while leaving the ceremony gate deaf to it — the step was
# spared one subtraction and silently taken by another.
#
# Both now consume ONE merged plan-local-over-marshal map. The assertions below
# are written as EQUIVALENCE between the two channels rather than as two
# independent expectations: a plan-local declaration must produce the same
# outcome a marshal declaration does. That framing is what fails if either reader
# regresses to a marshal-only source, because the two channels would then
# diverge even though each still "works" on its own.
# =============================================================================


def _write_plan_local_overrides(plan_context, plan_id: str, overrides: dict) -> Path:
    """Seed ``status.metadata.finalize_step_overrides`` for ``plan_id``."""
    plan_dir = Path(plan_context.plan_dir_for(plan_id))
    status_path = plan_dir / 'status.json'
    status_path.write_text(json.dumps({'metadata': {'finalize_step_overrides': overrides}}))
    return status_path
