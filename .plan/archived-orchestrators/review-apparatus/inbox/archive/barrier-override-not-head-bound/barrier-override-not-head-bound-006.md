envelope_version=1
sender_type=plan
sender_id=barrier-override-not-head-bound
epic=review-apparatus
kind=candidate-lesson
created=2026-08-02T11:43:24Z

component=plan-marshall:automatic-review
category=anti-pattern
title=Both substantive bots refused on PR #1077 and the review step still reported green - a one-reviewer no-issues comparison is not review coverage

# A green review step over a single non-substantive reviewer is not evidence of review

## What happened — PR #1077, live instance

Plan `barrier-override-not-head-bound` shipped a hardening of the **pre-merge review
barrier itself**. On its PR #1077:

- **coderabbit REFUSED** — `awaitable_window` (rate-limit class: awaitable).
- **sourcery REFUSED** — `hard_quota`.
- **pr-agent participated** — with a no-issues guide (a walkthrough, not a finding-bearing
  review).

Downstream signals: `automatic-review` recorded *"1 comment(s) found (unified triage
pending)"*; `review-retrospective` recorded *"1 reviewer compared, 0 actionable comments"*;
the finalize step chain stayed green throughout. The operator read the situation correctly,
**explicitly accepted the gap, and chose to merge** — which is the right disposition, and is
exactly why the gap must be recorded rather than absorbed.

Net: **a change to the review barrier shipped with zero substantive external review of the
barrier change.** Nothing in the pipeline said so out loud.

## Why it recurs

The step's outcome answers *"did the review machinery run to completion?"* — not *"was the
diff substantively reviewed?"*. Those two questions have looked identical every time both
bots participate, which is most of the time. They diverge precisely when a refusal happens,
and a refusal is silent:

- A **refusal is participation-shaped**. The bot posts *something* (a rate-limit notice, a
  walkthrough), so a comment-count check reads non-zero. `ci pr comments` is necessary but
  NOT sufficient — a comment *from* a bot is not a review *by* it.
- **"1 reviewer compared, 0 actionable comments"** is ambiguous by construction: it reads
  identically for "one reviewer looked hard and found nothing" and "two reviewers refused and
  the third only wrote a summary". The denominator is the missing number.
- **A no-issues guide is not a finding-bearing review.** A walkthrough is generated from the
  diff without adversarial analysis, so counting it as a participating reviewer inflates
  coverage.
- The refusal classes differ in remedy and must not be collapsed: `awaitable_window` is
  recoverable by waiting; `hard_quota` is not recoverable within the run at all.

This is a direct recurrence of the #1026 shape — *a DETECTED refusal was still reported as a
clean review* — and of the standing rule **never read a green finalize as proof the bots saw
the diff**.

## Rule

1. **Report the denominator, always.** The review summary must read
   `{participated}/{expected} substantive reviewers` with the refusing bots and their refusal
   class named. "1 reviewer compared" without "of 3 expected, 2 refused" is a coverage claim
   made from a volume number.
2. **A refusal comment is not participation.** Classify each reviewer as
   `substantive | non-substantive | refused` before counting. A no-issues walkthrough is
   `non-substantive`.
3. **Zero substantive reviewers is a distinct, loud outcome** — never the same signal as
   "reviewed, nothing found". At minimum a WARNING that names the class; the merge decision
   stays the operator's.
4. **Escalate on the CONTENT of the change, not only on the count.** A PR that modifies the
   review/merge-gate apparatus itself and receives zero substantive review is the highest-risk
   combination in the system, because the mechanism that would have caught the defect is the
   mechanism being changed.
5. **Carry the accepted gap forward.** When an operator merges past a review gap, the
   acceptance must land in the epic's ledger as owed post-merge revisit work — a late review
   is a recurrence, not an incident.

## Owed follow-up

**Post-merge PR revisit on #1077 is owed**, plus a scan of sibling PRs merged in the same
window (coderabbit's `awaitable_window` and sourcery's `hard_quota` are account-scoped, so
neighbouring PRs in the same period are likely to carry the same silent gap).

## Scope note for the orchestrator

This is squarely `review-apparatus`-owned — it is the epic's core theme, with a live
instance. Overlaps existing epic knowledge on rate-limit classes and `review_completeness`;
the new increment is the **denominator-and-classification reporting requirement** plus the
content-based escalation trigger (item 4).
