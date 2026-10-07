envelope_version=1
sender_type=plan
sender_id=terminal-title-channel-reconciliation
epic=truthful-signals
kind=candidate-lesson
created=2026-07-27T19:55:42Z

component=plan-marshall:persona-code-reviewer
category=anti-pattern
source_plan=terminal-title-channel-reconciliation
source_pr=1023

# A reviewer's list of call sites is a sample, not an enumeration

## Observation (first-party, PLAN-79 / PR #1023)

CodeRabbit reported a last-writer-wins race on `write_status` and **named three call sites**.
The actual number of `write_status` call sites was **fourteen**.

Had the fix been scoped to the three named sites — which is the natural, review-responsive
thing to do, and which would have resolved the review comment and closed the finding — the
result would have been a fix that leaves eleven writers racing. That is exactly the defect
class recorded in the sibling candidate-lesson (a guard added in one place, absent in its
siblings): **a reviewer-scoped fix reproduces the archetype by construction.**

The fix instead moved to the **shared write seam**, so all fourteen writers inherit the
serialisation.

## The corrective rule

A review comment names the sites the reviewer *saw* in the diff hunks it was given. It is
evidence that a defect class exists; it is **not** an enumeration of that class's instances.
A reviewer that only reads the diff cannot enumerate call sites that are not in the diff.

Therefore, for any review finding of the form "this call site has problem P":

1. **Enumerate the class before fixing.** Resolve the full instance set (`architecture find`
   / structured query, grep fallback) and compare its size to the reviewer's list. A
   divergence is the normal case, not the exception.
2. **Prefer the shared seam.** When the instance count is greater than the named count, fix
   at the common seam every instance routes through, rather than patching the named subset.
   A seam fix is also the only form that covers instances added later.
3. **Never let the review comment define the fix scope.** Resolving the reviewer's comment
   and fixing the defect are two different completion criteria; the finding is resolved when
   the class is closed, not when the named sites are patched.

## Truthful-signals relevance

This is the review channel's version of the theme: a finding that is *correct* and
*actionable* also carries an implicit, unstated, and wrong claim about its own completeness.
"3 sites affected" was never asserted by the reviewer — it was inferred from the fact that
three were listed. A green re-review after patching those three would have been truthful
about the reviewer's comment and silent about the eleven remaining writers.
