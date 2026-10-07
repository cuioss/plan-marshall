envelope_version=1
sender_type=plan
sender_id=config-seeding-effort-presets-steward-upgrade
epic=truthful-signals
kind=candidate-lesson
created=2026-08-26T14:40:22Z

component=plan-marshall:tools-integration-ci
category=bug
source_plan=config-seeding-effort-presets-steward-upgrade
confidence=high

# ci pr merge-queue corroborates enqueued:true against the branch rule, not PR membership

## Context

`ci pr merge-queue` was invoked twice against PR #1351. Both calls returned `enqueued: true`. Across roughly 25 minutes and three polls, `ci pr landing-state` stayed `pr_open` the whole time. Nothing had been queued.

The corroboration the verb attaches to its own success is the string **"merge_queue rule active on branch"**. That attests a property of the *branch protection configuration* — that a merge queue rule exists — and says nothing whatsoever about whether *this pull request* entered that queue. The verb therefore reports a success it never observed, twice, and the honest reading of `enqueued: true` is only "a merge queue exists here".

Two neighbouring behaviours in the same run make the contrast sharp:

- `ci pr safe-merge`, asked separately, **refused** with a correct and specific explanation: an immediate merge would close the PR unmerged. That is the #1081 false-green landing defect being caught at the tool layer, and it is exactly the right shape.
- `ci pr auto-merge` landed the PR immediately when finally tried.

So within one surface, one verb reports unverified success, one verb refuses honestly, and one verb works.

## Root cause

The verb's post-condition check reads a property of the branch rather than a property of the PR. `repo merge-queue probe` returned `eligible_configured, externally_managed: true, SQUASH` — the queue is externally managed, so membership is not something the branch rule can report. The check that would substantiate `enqueued: true` is a per-PR membership read, and it is not being made.

This is the epic's theme placed directly in the merge path: a confident boolean whose corroborating evidence answers an adjacent question.

## Proposed action

1. Make `enqueued: true` conditional on a **per-PR** membership observation, not on the branch rule's existence. Where the queue is `externally_managed` and membership cannot be read, return an explicit `enqueued: indeterminate` with the reason, never `true`.
2. Name the corroboration source in the returned payload so a caller can see what was actually checked, in the manner `safe-merge` already does when it refuses.
3. Consider whether `merge-queue` should defer to `auto-merge` when membership is unreadable, since `auto-merge` landed this PR without any of the conditions `merge-queue` implied were missing.

## Evidence

- `logs/work.log` 2026-08-26T13:37:55Z: "PR #1351 was enqueued TWICE (both returned `enqueued: true`) but landing-state stayed `pr_open` across ~25 minutes and three polls. The enqueue corroboration is only 'merge_queue rule active on branch', which attests the RULE not this PR's membership".
- Same line: `repo merge-queue probe: eligible_configured, externally_managed: true, SQUASH`.
- `status.metadata.phase_steps["6-finalize"]["branch-cleanup"]` final `display_detail`: merged via **auto-merge**, not via the queue.
- aspect: `chat_history_analysis` → `false_blocker_analysis`.
