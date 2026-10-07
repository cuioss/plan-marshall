envelope_version=1
sender_type=plan
sender_id=prompt-standard-and-doctor-rule
epic=operator-ux
kind=landing
created=2026-09-02T13:52:06Z

## What landed

prompt-standard-and-doctor-rule shipped as #1378 (merged) — the AskUserQuestion authoring
standard is now five numbered testable obligations, and `askuserquestion-prompt-quality`
enforces the three mechanically checkable ones on the analyze surface.

```landing-facts
schema=landing-facts/1
plan_id=prompt-standard-and-doctor-rule
epic=operator-ux
pr=#1378
merge_state=merged
deliverables_total=2
deliverables_done=2
total_tokens=3899218
total_wall_seconds=64130
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,pre-push-quality-gate:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,finalize-step-simplify:done,architecture-refresh:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,lessons-capture:skipped,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:done,archive-plan:done
step.branch-cleanup.merge_mechanism=merge_queue
step.branch-cleanup.merge_state=merged
step.finalize-step-sync-baseline.action=noop
step.pre-submission-self-review.rounds=5
step.pre-submission-self-review.findings=11
```

## Residue

**PLAN-05's deliverable 4 is only half-shipped, and the epic should know which half.** The
plan was to state a deliberate scope for what the rule cannot catch. It does that for
obligations 3 and 4. It does NOT close the structural question CodeRabbit raised: the
checked/blind-spot sets are stated independently in four places and derived from nothing,
so the documents can drift from the analyzer silently. Filed as
`prompt-standard-and-doctor-rule-001.md` (kind=finding) with two directions — derive or
collapse — and deliberately not decided at plan level.

**The self-review loop is the epic's most expensive instrument and two of its five rounds
were avoidable.** 677,934 tokens, 43% of the phase-6 dispatch total. All eleven findings
were genuine false claims in shipped prose. But round 1's own finding text said
*"Convergent fix is DELETION of the over-claiming clause"* and the fix narrowed instead;
round 4's finding then names round 1's replacement as still false. The convergence rule was
written in the finding being read and was not followed, twice. This is an operator/executor
discipline failure, not a tooling gap — no mechanism change would have prevented it.

**Two active lessons recurred that the corpus already held.** `2026-08-25-09-002`
(`returned_with_findings` unreachable) and `2026-08-25-09-007` (finalize cost concentration)
are both unapplied, and this run's own lessons-housekeeping reviewed and RETAINED both on
2026-09-01 as "surface untouched by this plan". Second independent instance of each. A
corpus that knows about a defect and a run that then commits it is the gap worth the epic's
attention.

**Review-machinery defects found by running the machinery, not by auditing it** — five, all
recorded rather than fixed: `head_sha_verified` misreads a bot that re-reviews by editing one
comment in place (forced a spurious operator escalation this run); sourcery `refusal_patterns`
miss the diff-character quota wording, and the miss does not even register in
`unrecognised_refusal[]`; the `rejected` bucket is overloaded so a 0-for-4 false-positive
inference reads as reviewer error; a bot finding re-recorded as a triage summary loses its
attribution, scoring CodeRabbit 0/1 on a fix it actually produced; `RE_ENTRY_COVERAGE`'s
precondition is the presence of the marker whose absence is the defect.

**Ledger integrity is not sound enough to cost this phase.** Only 8 of 20 6-finalize
execution-log rows pair with a boundary row; 574,858 tokens of dispatch spend are named by no
`record-step`. No single-ledger cost sum for the phase is defensible, including the 43% figure
above, which is a floor.

**Reviewer yield, measured**: in-house instruments 11 findings, external bots 2, one overlap.
The required bot (pr-agent) found nothing on either pass. CodeRabbit's distinct contribution
was the structural observation the in-house rounds converged straight past — they deleted
eleven individual over-claims without ever naming the duplication that kept producing them.
The gate-delta parity measurement is `excluded`, not zero: the gate certified c98a2512 and the
reviewers saw b40df538.
