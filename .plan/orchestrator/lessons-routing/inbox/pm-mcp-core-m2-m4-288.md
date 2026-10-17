envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-17T18:23:15Z

# Candidate lesson: an operator-requested fix commit after the finalize reviews re-runs the whole review chain

Component: plan-marshall:phase-6-finalize (HEAD-dependent steps, pre-commit-verify-freshness)
Category (proposed): improvement
Source: plan spend-removal, finalize (operator asked to fix five advisory review findings before the merge)

## Observation

- Both reviews had closed with no blocking finding and five advisory ones; the operator chose to fix the advisories before merging. Fixing them took one small commit (two test files and one document).
- The commit moved HEAD, so every head-dependent step re-fired: a full functional review (author plus verifier), a full code review (author plus verifier), the pre-push quality gate, the CI wait, the review-bot step (which posted a re-review trigger comment), the Sonar step and a second unified triage. That cost roughly 1.3M tokens and about an hour of wall clock for a change to tests and a trace line.
- `pre-commit-verify-freshness` returned `stale / worktree_mutated` for the manual commit, because the freshness reconciliation record is only written by the dispatcher's own commit instrumentation. The only way forward was a second full `verify -Ppre-commit` on the committed tree, although an identical tree had been built seconds earlier.
- The verdict-currency classifier could not help: the two review steps deliberately declare no `verdict_inputs`, so any HEAD advance re-fires them.

## Proposed correction

- Give the operator a sanctioned verb for a follow-up commit during finalize that records the freshness reconciliation (as item 5f does for dispatcher commits), so a build of the same tree is not repeated.
- Let the review steps run a delta round only (no closing full round) when the new commit touches no file of the reviewed production surface, or offer the operator an explicit, recorded refire waiver for a documentation-or-test-only follow-up.
