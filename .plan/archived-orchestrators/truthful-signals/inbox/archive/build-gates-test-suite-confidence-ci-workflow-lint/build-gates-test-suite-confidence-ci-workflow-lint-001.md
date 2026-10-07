envelope_version=1
sender_type=plan
sender_id=build-gates-test-suite-confidence-ci-workflow-lint
epic=truthful-signals
kind=candidate-lesson
created=2026-08-25T14:49:33Z

component=plan-marshall:phase-6-finalize
category=anti-pattern
bundle=plan-marshall

# A self-review round's own fix authors the next round's finding

`pre-submission-self-review` ran three rounds on PLAN-TRUTH-087 (PR #1340),
finding 4, then 4, then 2 findings. In each round the finding population was
authored by the PREVIOUS round's fix, not by the code the plan wrote. The loop
was self-seeding: it converged only because round 3 deleted the offending
sentence outright rather than rewriting it again.

The two mechanisms observed, in order:

- **Rounds 1-2 — rewriting an over-claim re-over-claims.** The fix for a
  sentence that claimed more than the change delivered was a rewrite. Each
  rewrite restated the claim at a new altitude and the next round flagged the
  new statement. Prose written to satisfy a precision finding is itself a fresh
  precision surface.
- **Round 3 — deletion is not antecedent-safe.** Deleting interior sentences
  from a paragraph silently re-pointed a pronoun's antecedent. A claim scoped to
  the RUN came to read as a claim about `parse`, because the noun it had
  referred to was in one of the deleted sentences. No edit was made to the
  surviving sentence, yet its meaning changed.

## Solution

Two rules, both cheap:

1. **Re-scope, do not re-word.** When a self-review finding says a claim
   over-reaches, prefer deleting the claim to restating it. A narrower
   restatement is a new claim and re-enters the finding population.
2. **After deleting an interior sentence, re-read every pronoun and every
   bare definite noun phrase in the surviving paragraph.** A deletion changes
   the referent set of text it did not touch; the diff shows only the removal,
   so the meaning change is invisible in review.

A terminating move exists and should be reached for early: delete the
cross-cutting sentence entirely rather than trying to make it true for every
verb it spans.

## Impact

Applies to every pre-submission-self-review loop and to any doc-precision
finding remediation. Each extra round in this run cost a full dispatch; three
rounds produced 10 findings of which the majority were self-inflicted. The
deletion-changes-antecedents half applies to all prose editing, not only to
self-review.
