envelope_version=1
sender_type=plan
sender_id=post-run-steps-ordered-before-their-evidence
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-02T21:55:09Z

component=plan-marshall:automatic-review
category=bug
title=Incremental review declined after loop-back leaves the final commits unreviewed while quorum reads green

# Incremental review declined after loop-back leaves the final commits unreviewed while quorum reads green

> **Suggested routing: `review-apparatus` epic (cross-epic delegation).** Per the standing three-way finding-routing rule, a review-participation / quorum-truthfulness defect is a review concern, not a `code-intelligence-substrate` concern. Forwarded through the inbox rather than filed locally; the orchestrator owns the delegation decision.

## Observation

On PR [#1080](https://github.com/cuioss/plan-marshall/pull/1080):

- After a loop-back, **CodeRabbit's incremental-review model declined to re-review**, stating it "does not re-review already reviewed commits".
- The consequence: the PR's **final 8 commits carry no bot review at all**.
- Meanwhile the **participation quorum still read green** — the gate saw a review from CodeRabbit and was satisfied.
- **Sourcery was hard-quota throughout**, so it contributed nothing either.

So the merge gate's green asserted "the bots reviewed this PR" while the truthful statement was "the bots reviewed an earlier state of this PR, and nothing reviewed the last 8 commits."

## Why this is a defect, not a bot quirk

The quorum's proposition is about **the diff being merged**, but its evidence is **the existence of a review event**. Those come apart exactly when an incremental-review model refuses a re-review after a loop-back — which is the normal shape of a plan-marshall run, not an edge case. This is the same family as the already-recorded findings that a *detected* refusal was still reported as a clean review, and that a comment *from* a bot is not a review *by* it.

## Rule / follow-up for review-apparatus

- The participation quorum must be evaluated **against the HEAD being merged**, not against "a review exists on this PR". A review whose reviewed-SHA is an ancestor of HEAD is stale evidence for the current diff.
- A reviewer that **declines** (incremental-model refusal, quota exhaustion) must be recorded as **declined**, and declined must not count toward quorum. Two reviewers declined here and the quorum was still green.
- `re_review_on_loopback=false` in the org config is directly implicated — worth revisiting now that the cost is measured.
- **Never read a green finalize as proof the bots saw the diff** — this run is a fresh, concrete recurrence of that standing rule.

## Impact

Review-bot quorum evaluation, `finalize-step-review-retrospective` participation reporting, org-level PR-Agent/CodeRabbit configuration (`re_review_on_loopback`), and the post-merge PR revisit obligation (owed on #1080).
