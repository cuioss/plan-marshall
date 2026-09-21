envelope_version=1
sender_type=plan
sender_id=daemon-baseline-interpreter-is-unregistrable
epic=truthful-signals
kind=candidate-lesson
created=2026-08-08T21:23:47Z

component=plan-marshall:phase-6-finalize
category=anti-pattern
confidence=high
source_aspects=findings-store,invariant-summary

# Trigger-A skips the rebased-HEAD re-review exactly when no bot review exists to be stale

## Context

`branch-cleanup-rereview.md` opens by stating its own invariant explicitly:

> The trigger fires on the rebased HEAD even when the pre-rebase tree was already reviewed; **this is NOT a skip-on-complete-then-move-on.**

Step 1 of the same document then installs a skip on a different axis (`branch-cleanup-rereview.md:20-27`):

> Walk `findings` newest-first and capture `{bot_kind}` from the first finding whose `bot_kind` is non-empty. **If no bot-authored finding exists (the list is empty, or every finding is human-authored), there is no prior bot review to re-trigger — skip this section** and proceed to the Pre-Merge Confirmation Gate.

The predicate is *"a bot-authored `pr-comment` finding exists"*. Its negation has at least three causes, and the guard treats them identically:

1. a bot reviewed and found nothing to say;
2. a bot was rate-limited or refused (CodeRabbit on this PR);
3. a bot posts nothing the store records **by design** — this plan's own review retrospective states that PR-Agent "posts no inline comments at all, publishing instead a single in-place-updated `## PR Reviewer Guide 🔍` `issue_comment`, so a store with no inline records is exactly what a fully engaged PR-Agent also looks like".

So the re-review is skipped precisely in the states where bot coverage is weakest or unknown, and fires only where a bot already demonstrated it had something to say. That inverts the intent stated in the document's own opening paragraph.

Measured on this run:

> `(plan-marshall:phase-6-finalize) Branch cleanup trigger-A re-review skipped: no bot-authored pr-comment finding exists (both stored findings are human-authored), so there is no prior bot review to re-trigger for the rebased HEAD 1d1ad0fd`

The two stored findings were the author's own scope-restoration comment and the pipeline's own `/review` trigger. Neither is a bot review; neither should have been able to decide whether a bot review was owed. The rebase commit `1d1ad0fd` therefore carried no fresh bot review into the merge — on a plan whose immediately preceding commit (`db3d67f6`) narrowed a security-relevant interpreter check, superseding a settled operator decision.

## Root cause

The skip is an artifact of a **parameter dependency**, not a policy: step 3 needs a `--bot-kind` value, step 1 sources it from the findings store, and the store is empty, so the section exits. The set the guard is really about — which bots are expected to review this PR — is known independently and from configuration: the pre-merge barrier on the same run evaluated `required_bots=pr-agent`. The guard derives its population from *evidence of past output* instead of from the *configured roster*, which is the recurring set-guarding-detector failure: a detector whose population can be empty must publish that fact, not silently pass.

Note the contrast on the same run — the pre-merge barrier is honest about its own limits (`proves=participation_only … coderabbit remains unproven (refused_awaitable)`). Trigger-A's skip is not: it records a conclusion ("there is no prior bot review to re-trigger") that reads as a considered not-applicable.

## Proposed action

- Source `{bot_kind}` from the **configured bot roster** (the same population the pre-merge review barrier reads as `required_bots`), not from the presence of a prior finding. Re-trigger each configured bot for the rebased HEAD regardless of what it produced before.
- Where no roster is configured at all, make that a **reported** state — an explicit "no bots configured; rebased HEAD `{sha}` not re-reviewed" — rather than a silent fall-through, so an empty population is visible instead of indistinguishable from a satisfied guard.
- Add a test that exercises the rebase path with an empty `pr-comment` store and asserts the re-review is ATTEMPTED, since the current behaviour is what a passing test would pin today.

## Evidence

- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup-rereview.md`:7 (the stated invariant) and :20-27 (the contradicting skip predicate)
- decision.log `bfcf01` — the skip, naming rebased HEAD `1d1ad0fd`
- decision.log `29696e` — the pre-merge barrier on the same run: `participation_complete=true over required_bots=pr-agent`, `proves=participation_only`, `coderabbit remains unproven (refused_awaitable)`
- decision.log `c934c3` — `db3d67f6`, the S1.2 narrowing that immediately preceded the rebase
- `review-retrospective.md` — PR-Agent's store-invisible publication shape; both stored records human/pipeline-authored
