envelope_version=1
sender_type=plan
sender_id=plan-44-static-verifier-rule-gaps
epic=lessons-routing
kind=finding
created=2026-10-12T19:22:04Z

# [MEDIUM][opencode] Finalize triage scopes were bot-bounded; nothing re-examined the work order after the first loop-back

- Component: plan-marshall:plan-marshall/workflow/verification-feedback.md (triage input scope), plan-marshall:phase-6-finalize (loop-back exit condition)
- Category: improvement

## What happened

Two unified-triage passes ran in finalize (6 findings, then 2 findings), both scoped to the union
of external findings: bot review comments plus Sonar issues. Three FIX tasks (TASK-12–14) addressed review comments; the re-review produced two more comments, both taken into account. The
loop exited when the finding queue emptied.

The plan's own Done-When checklist was never a triage input. Rule 9's unchanged
`checkStepCompletion`, Rule 3's boolean-only substrate, the still-weakened assertions, and the
missing index dependency were outside every triage scope because no bot named them — the bots
reviewed the last commit and found nits, while the structural gaps had no finder. Each loop-back
round therefore refined the work without ever asking whether the work was the ordered work. The
exit condition "no pending findings" is satisfied by a plan that never files findings against
itself.

## Why it matters

Bot-bounded triage converges on reviewer satisfaction, not on work-order completion. Combined with
self-reported task completion, it lets a plan iterate twice through finalize (fix tasks, re-review,
second triage) and still ship 4 of 7 deliverables unmet — each round adding confidence ("CI green,
triage owed", "0 sonar issues") while measuring the wrong thing.

## Suggested direction

- The finalize triage input always includes the plan's Done-When checklist as a standing finding
  source alongside bots and Sonar: one provisioned item per atomic acceptance criterion, closed
  only by the evidence the criterion names (fixture, control, exact assertion). An empty bot queue
  with open checklist items still loops back.
- The loop-back exit condition becomes "no pending external findings AND all checklist items
  evidenced", checked by the orchestrator, not the triage leaf.
- Review-bot prompts (or the triage leaf instructions) include the work-order summary so a
  reviewer can flag "this PR does not do what it says" — the defect class no bot review caught
  here.

- Priority: **MEDIUM**
- Platform: opencode
- Plan: `plan-44-static-verifier-rule-gaps` (PLAN-44), pm-mcp-core PR #38, merge commit 6caa663
- Evidence location: pm-mcp-core `.plan/local/archived-plans/2026-10-12-plan-44-static-verifier-rule-gaps/` (both verification-feedback returns: 3 FIX + 3 resolved, then 2 taken_into_account with `loop_back_needed: false`); orchestrator landing record `landings/PLAN-44.md`
- Origin: executor self-analysis under opencode at operator request (do-not-fix analysis of the PLAN-44 failure)
