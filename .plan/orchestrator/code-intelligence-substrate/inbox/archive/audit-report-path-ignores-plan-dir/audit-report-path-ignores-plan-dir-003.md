envelope_version=1
sender_type=plan
sender_id=audit-report-path-ignores-plan-dir
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-07-30T08:06:13Z

component=plan-marshall:finalize-step-review-retrospective
category=bug
title=Review-bot participation is per-commit, not per-PR — a loop-back fix commit ships unreviewed

# Review-bot participation is per-commit, not per-PR

## Observation

On PR #1063 the automated-review step ran, CodeRabbit reviewed the tree and produced an actionable finding. The plan looped back and fixed it in commit `2475cd17`. The finalize pipeline then proceeded to the merge gate.

The plan's own review-retrospective recorded the outcome in one sentence: **the final shipped commit was reviewed by nobody.**

## Mechanism

Two facts compose into the gap:

1. **A review is a verdict on a commit, not on a PR.** A green "reviewed" state on the PR is a statement about whatever the head was when the bot ran — not about the tree that merges.
2. **Trigger B re-triggers only the most-recently-reviewed bot.** After a loop-back commit, the re-review path does not fan back out to the full required set, so the *required* bot (pr-agent, here) is never re-invited. Its earlier verdict — on the pre-fix tree — is what the gate reads.

The result is systematic, not incidental: **every loop-back that fixes a bot finding produces a shipped commit the required reviewer never saw.** The higher the review quality, the more loop-backs, the more often this fires.

## Rule

- Treat "the PR was reviewed" as **unsound**. The question is always: *which commit* did each required reviewer see, and is that the commit that merges?
- After any loop-back commit at phase-5/6, the review state for **every** required reviewer is stale, not just the one that produced the finding. Re-trigger the full required set, not the last responder.
- The review-retrospective must report per-reviewer *head SHA at review time* against the shipped head, so "reviewed by nobody" is a machine-detected verdict rather than a prose observation a human happens to write down.

## Relation to known corpus

Reinforces the standing "review bots — check states lie in both directions" body of evidence: a *detected* refusal was previously reported as a clean review (#1026). This is the same failure polarity at a different seam — the state says reviewed, the shipped bytes were not.
