envelope_version=1
sender_type=plan
sender_id=orchestrated-plan-detection-fails-silently
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T16:15:58Z

component=plan-marshall:phase-6-finalize
category=bug
bundle=plan-marshall

# lessons-capture runs before branch-cleanup, so every defect discovered in the merge window has no route to the epic

## What happened

On PLAN-114 the finalize step order placed `lessons-capture` at step 14 of 22 and `branch-cleanup` at step 16. All six inbox messages this plan sent to the epic were written at **15:41:09–15:41:32**.

Two real infrastructure defects were then discovered *after* that:

- **15:46:27** — the pre-merge review barrier falsely reported the required bot absent (decision.log).
- **16:02:42** — `worktree-remove` failed twice on its own hardcoded 60-second inner git timeout (work.log).

Neither reached the epic. The epic inbox holds exactly six messages from this plan, all timestamped 15:41.

## The false signal

The 15:46:27 decision-log entry ends with the sentence **"Defect filed for the epic: branch-cleanup.md instructs feeding the deduped fetch_findings participation set to the predicate, which yields a false merge block."**

Nothing was filed. The only channel to the epic — `lessons-capture` — had closed five minutes earlier. The log states a completed action that the step ordering had already made impossible, and it states it confidently enough that a reader auditing the epic inbox for that defect would conclude it had been dropped in transit rather than never sent.

This is the epic's theme applied to the epic's own intake: a confident "filed" hides the caveat "…into a channel that was already closed."

## Root cause

`lessons-capture` is positioned as if the plan's learnable surface were complete once the PR is reviewed. It is not. `branch-cleanup` performs the merge, the merge-queue wait, the post-merge pull, and the worktree teardown — four operations with a long history of producing defects in this project — and every one of them happens downstream of the only step that can talk to the epic.

## Corrective rule

Pick one; do not leave the window open:

1. **Move `lessons-capture` after `branch-cleanup`**, so the merge/teardown window is inside its observation range. This is the smaller change but it delays the epic's notification of the landing.
2. **Or give `branch-cleanup` its own inbox-write obligation** for defects it observes, and make `plan-retrospective` (which genuinely runs last) the backstop that sweeps `decision.log` / `work.log` for defect-claim prose emitted after `lessons-capture` closed.

Independently of which is chosen: **a workflow body must not instruct the agent to write "filed for the epic" at a point in the sequence where the filing channel is closed.** If a step cannot file, it must say "observed, cannot file from here — carried to retrospective."

## Recurrence signature

Same archetype as the recorded finalize-ordering defect where a plan that fixes a finalize-time component cannot have that fix exercised by its own finalize (cache syncs at step 19, retrospective at 17). The general shape: **a finalize step whose output is consumed by an earlier-ordered step**. Sweep the 22-step order for every step that produces a signal some earlier step is responsible for transmitting.

## Evidence

- `decision.log` 15:46:27 — "Defect filed for the epic: …"
- `work.log` 16:02:42 — "Defect: the 60s inner git timeout in worktree-remove is too low…"
- `orchestrator inbox list --slug truthful-signals` — 6 messages from this sender, latest `created: 2026-07-29T15:41:32Z`
- `execution.toon` `phase_6.steps` — `lessons-capture` at index 13, `branch-cleanup` at index 15
