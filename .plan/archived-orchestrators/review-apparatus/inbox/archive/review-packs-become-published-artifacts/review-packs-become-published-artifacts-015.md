envelope_version=1
sender_type=plan
sender_id=review-packs-become-published-artifacts
epic=review-apparatus
kind=candidate-lesson
created=2026-09-03T22:44:20Z

# A posted review disposition is a promise nothing re-checks against what landed

component: plan-marshall:automatic-review
category: bug
confidence: high

## Context

The run answered CodeRabbit threads in the "Agreed. Will be addressed by TASK-N" form, which states a remedy before the fix is designed. On thread 166827 the stated remedy was not what shipped, and the divergence had to be corrected on the thread afterwards:

> "That reply said PrAgentTarget.generate would reject a non-None bundles filter rather than silently ignoring it, and you agreed on that basis. That is NOT what shipped."

The reject remedy was withdrawn on operator direction: `generate.py` forwards `bundles=` to every registered target, so raising would have made the valid invocation `--target all --bundles X` exit 2 for every OTHER target. The shipped remedy was the reviewer's second option — remove the allow-list parameter from the derivation functions entirely. The correction was posted, which is the right handling. The point is that nothing DETECTED the divergence; an agent happened to notice it while composing a later reply.

The same run posted eight dispositions across two review rounds, seven resolved `fixed`, each naming a task number and a remedy.

## Root cause

A disposition is transmitted at triage time and never reconciled against the landed diff. The reviewer's agreement is obtained against a DESCRIBED remedy, so a changed remedy silently converts an agreed thread into an unreviewed change — and by then the reviewer's rate window may be spent. CodeRabbit's included budget read "0 remain after this review" on both rounds here, so the follow-up commit landed with no re-review available to catch the substitution.

`review_commitments` sits in this neighbourhood but reconciles simplify-pass DELETIONS against commitments, not posted dispositions against landed diffs — and it returned a vacuous `clear` this run anyway (finding d4501c, `commitments_considered: 0`).

## Proposed action

Before the merge gate, reconcile each posted disposition against the diff that landed after it: the files it named, the task it routed to, and whether the remedy it described is the one present. Report a divergence rather than requiring an agent to notice one.

Where a divergence is found and the reviewer's rate window is spent, that is exactly the condition the pre-merge review barrier should weigh: a thread agreed on a superseded remedy is not a reviewed thread, and it currently presents as one.

## Evidence

- pr-comment 166827 — correction posted at 2026-09-03T20:18:17Z reversing the earlier agreement on the same thread
- pr-comment 1002a8 — a second reversal in the same run, of an earlier triage call on the fingerprint gap
- 8 pr-comment findings, 7 resolved `fixed`, all dispositioned in the pre-emptive "will be addressed by TASK-N" form
- CodeRabbit review budget: "Your plan provides up to 1 included review per hour; 0 remain after this review" on BOTH rounds
- finding d4501c — the adjacent commitment guard returned `clear` over an empty population
- The merge ultimately cleared its review barrier through a `barrier-ask-override`, not through completed bot participation
