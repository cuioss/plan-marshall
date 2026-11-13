envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4-v2
epic=lessons-routing
kind=candidate-lesson
created=2026-11-13T09:16:41Z

component=plan-marshall:phase-5-execute
category=improvement
bundle=plan-marshall

# Style and gate-rewrite commits made outside the deliverable settlement leave no change-ledger row, so 5-execute -> 6-finalize is refused

Observed in PLAN-V2-40 (plan-v2-40-envelope-packing, PR #402).

Two commits on the feature branch were not deliverable commits: an import-order style commit (4d9ff969) after deliverable 2, and the whitespace rewrite of the pre-commit gate (f87166ef) after deliverable 4. Neither passed through the Step 10a settlement, so neither had a `kind=change` row in the change ledger.

The `5-execute -> 6-finalize` transition then refused with `error=execute_commits_unrecorded signature=bookkeeping_gap unrecorded_count=2 recorded_count=5 branch_commit_count=7`. The refusal payload named each unrecorded commit with its own append invocation, so the repair was mechanical: two `manage-change-ledger append --kind change` calls, then the transition passed. The same run also had to re-run the whole-tree test build on the final HEAD, because the whitespace commit had made the freshness gate stale.

Corrective action: a commit the executor makes for gate output (style or whitespace rewrite) should be recorded at the point it is made, under the deliverable it belongs to, instead of being discovered at the transition. Either the execute-phase commit path appends the row for every branch commit (as the finalize commit path already does), or the gate-rewrite step documents the owed append next to its commit instruction.

Evidence: work log 2026-11-12T22:36:44Z (script_failure, manage-status) and 22:36:49Z (transition refused).
