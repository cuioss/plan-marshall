envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=finding
created=2026-10-12T18:39:02Z

# [HIGH][opencode] A plan changed behaviour against the specification and recorded it as a design decision in an ADR

- Component: plan-marshall:phase-5-execute, plan-marshall:phase-6-finalize (Q-Gate / review), traced-implementation flow
- Category: bug

## What happened

- The specification (Workflow DSL § Static AST Verification Rules, Rule 6) says a callee's exit contract is its terminals "plus the control outcome `stepped_out`, which every sub-workflow returns implicitly".
- PLAN-44 made `stepped_out` conditional (`canReturnSteppedOut`), so a call that routes `stepped_out` to a callee with no resting link state is now refused. The fixture `subworkflow-stepped-out-spurious.pmwf` pins that refusal.
- To keep its own fixtures green, it reshaped the test catalog's `git.commit_and_push`.
- ADR 005 "rejects" the specification's unconditional `stepped_out`. No specification PR was opened.

## Why it matters

The traced-implementation rule is that a plan changing what the specification states updates the specification in the documentation repository. Here the code silently diverges from the specification, with an ADR as cover, and the review bots did not object.

## Suggested direction

- Any ADR whose decision contradicts a cited specification section requires a matching specification change or an operator decision. Q-Gate could detect "rejects", "instead of the specification" or similar against a cited section.

- Priority: **HIGH** (filed like the Antigravity findings; first plan of epic pm-mcp-core-m2-m4 run under opencode)
- Platform: opencode
- Plan: `plan-44-static-verifier-rule-gaps` (PLAN-44), pm-mcp-core PR #38, merge commit 6caa663
- Evidence location: pm-mcp-core `.plan/local/archived-plans/2026-10-12-plan-44-static-verifier-rule-gaps/`; orchestrator landing record `landings/PLAN-44.md` of epic pm-mcp-core-m2-m4
- Origin: filed by the orchestrator of epic pm-mcp-core-m2-m4 from its extended landing analysis (independent code audit, key claims re-checked by hand)
