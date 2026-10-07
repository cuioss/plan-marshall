envelope_version=1
sender_type=plan
sender_id=test-fidelity-rules-follow-up
epic=process-compliance
kind=finding
created=2026-09-19T21:03:33Z

# Process-rule gap: light-lane entry with no solution outline on an 8-deliverable scope

## Observed

- `status.metadata.planning_lane` is `light`; current phase is `3-outline in_progress`.
- `manage-solution-outline read` returns `document_not_found` for `solution_outline.md` — the artifact the light-lane branch assumes already exists at outline-action entry.
- Work-log decision record shows the lane routed `light` at confidence 3/6 resolved (`low_confidence=True`, null `change_type`, `compatibility`, `plan_source`; scope band `single_module` from 4 paths), while the request carries 8 deliverables that exceed the presumptive split guard.
- The outline workflow's light branch (skip dispatch, go to review) has no defined path when the outline file is absent.

## Conflict

- Skipping the dispatch assumes the planning-lane envelope already derived the outline; with the file absent there is nothing to review and no documented re-dispatch from inside the outline action.
- Inventing a light-envelope dispatch from inside the outline action would violate the no-improvisation rule.

## What was done on this run

- Stopped before dispatch and asked the operator; the operator chose the thorough (deep) path.
- Lane escalation and re-run of refine are handled as the recovery (see plan decision log), not as an inline invention.

## Request

- Define the sanctioned recovery for light-lane entry with a missing outline (re-enter via the planning light envelope vs escalate to deep), and consider a scope-guard signal so multi-deliverable scopes do not route light on a low-confidence signal set.
