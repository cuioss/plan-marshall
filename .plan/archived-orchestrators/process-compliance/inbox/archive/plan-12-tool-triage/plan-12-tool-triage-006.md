envelope_version=1
sender_type=plan
sender_id=plan-12-tool-triage
epic=process-compliance
kind=finding
created=2026-09-27T15:22:06Z

# Post-refine clean-main assertion fires on sanctioned `.plan/orchestrator/` writes

## Observed

`plan-marshall/workflow/planning.md` § 2-Refine → Post-dispatch contract assertion runs
`git -C . status --porcelain` and treats ANY non-empty output as a refine contract violation
(`[CRITICAL]`, refuse to advance). After the phase-2-refine dispatch of plan-12-tool-triage it fired
on paths refine never wrote — all under the git-tracked orchestrator store:

- `inbox/plan-12-tool-triage-001..005.md` — this plan's own findings, filed via `orchestrator inbox write`
  (a sanctioned write the spec's Write-Boundary explicitly allows, and the operator asked for)
- `inbox/plan-13-finalize-mechanism-defects-001..002.md` — a concurrently running plan's messages
- `epic.md`, `plans/PLAN-10-entry-capture.md`, `queue/PLAN-10.json` — ledger edits by another session

The run stopped and needed an operator decision to continue. Meanwhile
`phase_handshake verify` in the same run already classified the same inbox files as
`main_dirty_exempted` (informational) — so the two clean-main checks disagree on which paths count.

## Impact

With the orchestrator store git-tracked on main and several plans/sessions writing to it
concurrently, the porcelain assertion is a near-certain false positive for any orchestrated plan,
and it trains operators to wave the `[CRITICAL]` through. The recovery text ("revert them or move
them into `.plan/local/plans/{plan_id}/**`") is wrong for these paths — reverting would destroy
other sessions' ledger work.

## Suggested fix

Drive the post-dispatch assertions (1→2, post-refine, and the outline/plan boundaries that reference
the same block) from the same exemption set `phase_handshake` uses for `main_dirty_exempted`, or
compare against a pre-dispatch porcelain snapshot so only paths that changed DURING the dispatch
count.

## Secondary observation

The `2-refine` handshake capture reports `pending_findings_blocking_count: 1` while every
`pending_findings_by_type` bucket is `0`. The one open item is the refine Q-Gate
"all dimensions scored 100%" flag (flag-not-block per the refine report). A blocking count that no
per-type bucket accounts for cannot be reconciled from the capture itself.
