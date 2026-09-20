envelope_version=1
sender_type=plan
sender_id=provider-logging-path-containment
epic=truthful-signals
kind=candidate-lesson
created=2026-08-08T23:38:33Z

# Candidate lesson L2 — A finalize step can be marked done with no execution_log row and no dispatch-boundary row

- component: `plan-marshall:manage-execution-manifest`
- category: bug
- source plan: `provider-logging-path-containment` (PLAN-TRUTH-011, PR #1123)
- theme: confident-signal-hides-a-caveat

## Observation

Two 6-finalize steps are recorded in `status.metadata.phase_steps["6-finalize"]` with `outcome: done` and substantive `display_detail`:

- `project:finalize-step-deploy-target` — "claude target generated, 1131 entries, version 0.1.1329"
- `project:finalize-step-sync-plugin-cache` — "10 bundles synced; on-main executor regenerated"

Neither has a `record-step` row in `execution.toon` `execution_log`, neither has a row in `work/metrics-dispatch-boundaries-6-finalize.toon`, and neither emitted a `(plan-marshall:manage-execution-manifest:record-step)` line in `decision.log`. Both also lack the `head_at_completion` field that every other dispatched step in the same map carries.

So: **19 finalize steps marked done, 17 with an execution_log row.** Real work happened (the display details are specific and verifiable) and left no ledger trace at all.

## Why this matters beyond bookkeeping

`execution_log` is the substrate that `check-routing-decisions` sums for `cost_preview.actual_tokens` and that any cost or step-coverage audit reads. A step that completes without a row is invisible to every one of those consumers, and nothing reports the gap — the manifest cross-check has no completeness assertion tying `phase_steps` to `execution_log`.

## Proposed remedy

Add a deterministic check to `check-manifest-consistency`: every `phase_steps` entry with `outcome: done` MUST have a matching `execution_log` row; emit one finding per orphan. The population is already on disk in both files, so the check is a pure set difference and cannot return a vacuous zero — publish the population size (steps marked done) alongside the violation count.
