envelope_version=1
sender_type=plan
sender_id=test-fidelity-rules-follow-up
epic=process-compliance
kind=finding
created=2026-09-19T21:03:33Z

# Process-rule gap: zero phase-handshake captures across two completed phases

## Observed

- `phase_handshake list --plan-id test-fidelity-rules-follow-up` returns `count: 0` (no captured rows).
- Status shows `1-init done`, `2-refine done`, `3-outline in_progress`.
- `phase_handshake verify --phase 2-refine --strict` returns `status: skipped — no capture exists for phase`, so the mandated pre-entry verify for `3-outline` cannot attest anything.

## Conflict

- The outline workflow mandates a capture-then-verify pair at every phase boundary; the boundary metrics for `2-refine -> 3-outline` report `stamped` while the handshake store is empty.
- Metrics stamping and handshake capture are independent operations; one passing does not cover the other.

## What was done on this run

- Stopped before any outline dispatch instead of entering `3-outline` on an unattested boundary.
- Logged a decision-level block entry; no transition was issued.

## Request

- Clarify whether a resume with an empty handshake store should backfill captures for closed phases or refuse entry until the owning phase re-runs, and make the empty-store state fail loudly at the transition that would otherwise stamp metrics alone.
