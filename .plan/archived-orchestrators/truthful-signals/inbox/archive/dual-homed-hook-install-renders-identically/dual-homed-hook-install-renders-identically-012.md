envelope_version=1
sender_type=plan
sender_id=dual-homed-hook-install-renders-identically
epic=truthful-signals
kind=candidate-lesson
created=2026-09-03T10:15:14Z

# Candidate lesson: two first-party reports grade correct behaviour as a defect — an assessment read at report time, not at decision time

**Component**: `plan-marshall:manage-findings` (assessment staleness) / the reporting steps that consume assessments
**Source signal**: plan-retrospective report for `dual-homed-hook-install-renders-identically`
**Suggested category**: bug

## Claim

Two first-party reports produced by this run graded **correct** behaviour as a violation. The clearest instance: a component assessment recorded as `CERTAIN_EXCLUDE` was **overridden by the operator 26 minutes later**, and the run then correctly acted on the override — yet the report reads that correct action as `exclude_violated`, because it compares the action against the assessment as recorded rather than against the assessment as it stood when the decision was made.

## The mechanism

An assessment is a **point-in-time** judgement with no supersession record. The reporting step reads the latest stored value and tests the run's actions against it, so any assessment revised mid-run makes every action taken under the *previous* value look like a violation — and every action taken under the *new* value look compliant even if it was taken before the revision. The error can therefore land in either direction; this run happened to catch the false-positive direction.

Note what makes this specifically bad: the overriding authority was **the operator**. The report is grading the run for obeying an explicit operator instruction, which is precisely the input that should be unappealable.

## Why it matters beyond the one instance

A report that manufactures false defects is worse than one that misses real ones, because it spends the reader's scarce attention on non-problems and trains them to discount the whole instrument. Once a reader learns that `exclude_violated` sometimes means "the operator changed their mind", every genuine `exclude_violated` becomes a coin flip. That is the archetype this epic tracks, inverted: not a confident green over an unasked question, but a **confident red over a correctly-answered one**.

It also compounds with the sibling candidate on review-retrospective metrics (a reviewer that raised nothing scoring 0.0%): two of this run's reporting surfaces independently produced a wrong verdict from a correct run. The common cause is that both compare an action against a stored value with no notion of *when* the value held.

## Suggested directive (for the orchestrator to judge)

1. **Timestamp the comparison, not just the record.** An assessment needs an effective-from instant, and the report must test each action against the assessment in force **at that action's timestamp** — not against the current one. Both ledgers already carry timestamps (`manage-metrics reconcile-ledgers` demonstrates the pattern), so this is a join, not new instrumentation.
2. **Record supersession explicitly.** When an assessment is overridden, keep the prior value with its window rather than overwriting. The `manage-lessons` tombstone model and the `inbox supersede` envelope are both existing in-tree precedents for "stays resolvable, stops presenting as live".
3. **An operator override must be distinguishable from a drift.** Whatever the fix, the report should be able to say *"acted under the assessment then in force, superseded by operator at T"* — never `exclude_violated`.

Derive the affected set rather than assuming these two reports are the only members: enumerate every reporting surface that grades a recorded action against a mutable stored judgement. The retrospective named two; that is the sample it happened to traverse, not an enumeration.
