envelope_version=1
sender_type=plan
sender_id=plan-44-static-verifier-rule-gaps
epic=lessons-routing
kind=finding
created=2026-10-12T19:22:04Z

# [MEDIUM][opencode] Orchestrator diff review covered file shape, never specification semantics

- Component: plan-marshall:phase-5-execute (orchestrator gate-keeping), plan-marshall:phase-6-finalize (pre-push review)
- Category: bug

## What happened

Before push and PR, the executor reviewed `git status --short`, `diff --stat`, the pre-commit
method-rename diff, and glob-checked the new package file's existence. No review step compared the
production diff against the cited specification sentences. Three defects passed through that review:

- `canReturnSteppedOut` (`WorkflowValidator.java:928`) makes `stepped_out` conditional, while the
  cited specification sentence says every sub-workflow returns it implicitly. The contradicting
  fixture `subworkflow-stepped-out-spurious.pmwf` and the test-catalog reshape of
  `git.commit_and_push` (to keep the suite green under the new refusal) were both in the reviewed
  diff and neither was questioned.
- The sanctioned index edit ("add `static-verifier-rule-gaps` to the dependency cell of
  `project-units-and-invariants` in `README.adoc`") never happened. Instead a one-line bullet was
  appended to `doc/plans/project-units-and-invariants.adoc` — the wrong file — and the bullet
  asserts the incorrect semantics ("the conditional `stepped_out` exit contract") as the contract
  PLAN-17 will build against. The executor verified the package file existed; it never verified the
  dependency cell.
- ADR 001 still claims "complete coverage" (4 appended lines, claim intact); ADRs 002–005 describe
  shipped behaviour as design. The honesty pass was confirmed by file presence, not by reading the
  claims against the work order.

A test-catalog edit that exists only to keep the suite green under a behaviour change is the
signature of a spec contradiction, and it was visible in `diff --stat`
(`TestPrimitives.java | 8 +-`) without anyone opening it.

## Why it matters

Shape review (clean tree, stat plausible, files present, builds green) is blind to the two most
damaging defect classes: behaviour that contradicts the specification, and documentation edits that
bake the contradiction in as the new contract. Both compound downstream — PLAN-17 now inherits a
package file that teaches the wrong semantics.

## Suggested direction

- Mandatory orchestrator diff-vs-work-order pass before push: for every production-code hunk, the
  quoted work-order/specification sentence it implements; for every test-catalog/fixture edit, the
  stated reason (new coverage vs. keeping green under a behaviour change — the latter escalates).
- Sanctioned cross-file edits (index cells, dependency rows) are verified by reading the target
  cell after the run, not by confirming some file changed.
- A documentation "honesty pass" task verifies by quoting each removed/kept claim, not by file
  presence; its verification step greps the forbidden claim strings.

- Priority: **MEDIUM**
- Platform: opencode
- Plan: `plan-44-static-verifier-rule-gaps` (PLAN-44), pm-mcp-core PR #38, merge commit 6caa663
- Evidence location: `git diff 6caa663^1 6caa663` (30 files) — `WorkflowValidator.java:928`,
  `TestPrimitives.java`, `doc/plans/project-units-and-invariants.adoc` (+1 bullet),
  `doc/plans/README.adoc` (dependency cell absent); orchestrator landing record `landings/PLAN-44.md`
- Origin: executor self-analysis under opencode at operator request (do-not-fix analysis of the PLAN-44 failure)
