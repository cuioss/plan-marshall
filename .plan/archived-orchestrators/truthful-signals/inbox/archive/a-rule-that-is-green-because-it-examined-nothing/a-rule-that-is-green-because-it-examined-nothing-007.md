envelope_version=1
sender_type=plan
sender_id=a-rule-that-is-green-because-it-examined-nothing
epic=truthful-signals
kind=candidate-lesson
created=2026-08-08T18:41:33Z

component=plan-marshall:manage-status
category=improvement
title=phase_steps is last-write-wins and erases errored attempts a sibling store recorded
confidence=medium
source_plan=a-rule-that-is-green-because-it-examined-nothing

# phase_steps is last-write-wins and erases errored attempts a sibling store recorded

## Context

`default:pre-submission-self-review` ran **four** times on this plan (dispatches at 14:22:23, 14:30:06, 14:36:26, 17:24:48). Two of those dispatches terminated with `termination_cause=error`, consuming 392,736 tokens between them, and the manifest execution log recorded the step's outcome as `error`:

```
[2026-08-08T14:28:57Z] (plan-marshall:manage-execution-manifest:record-step)
  Recorded pre-submission-self-review phase=6-finalize outcome=error — total_tokens=206005
```

What `status.metadata.phase_steps["6-finalize"]["pre-submission-self-review"]` carries is:

```
outcome: done
display_detail: "self-review clean: 19 candidates examined, no check matched"
head_at_completion: 3a9190f8e9537ae1dd286c632c3f6c82e1f70b3e
```

A single clean `done`. No attempt count, no record that two earlier attempts errored, no trace of the 392,736 tokens. A reader of `status.json` — which is the surface the finalize dispatcher's re-entry check, the dispatch audit's Surface C, and any downstream consumer read — sees a first-try pass.

## Root cause

`mark-step-done` is a single-slot upsert: a later terminal outcome replaces an earlier one for the same `{phase, step}` key. That is the right primitive for idempotency and for the resumable re-entry check, but it means the record is a *latest state*, not a *history*, while its consumers treat it as the authoritative account of what the step did.

The information is not lost from the system — the manifest execution log and the dispatch-boundary file both hold it — but it is lost from the one surface that presents itself as the per-step record, and the three stores are never reconciled.

## Proposed action

- Add an `attempts` counter (and optionally `prior_outcomes[]`) to the `phase_steps` entry shape, incremented on every `mark-step-done` for an already-recorded `{phase, step}` key. This costs one integer and makes the retry visible without changing the terminal-outcome semantics anything currently branches on.
- Alternatively, have `mark-step-done` refuse to silently overwrite a terminal `failed`/`error` record without `--force`, forcing the overwrite to be deliberate.
- Either way, surface the attempt count in the finalize vertical-steps render, so `done` after three failures does not read identically to `done` first time.

## Evidence

- aspect: logging_gap_analysis — the manifest execution log and `phase_steps` disagree in kind for the same step
- aspect: dispatch_boundaries — 2 rows with `termination_cause=error` at 14:28:55 and 14:35:27, 392,736 tokens combined
- source: `decision.log` 462e5d (`outcome=error`) vs `status.metadata.phase_steps` (`outcome: done`)
