envelope_version=1
sender_type=plan
sender_id=orchestrated-plan-detection-fails-silently
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T15:41:32Z

component=plan-marshall:manage-execution-manifest
category=bug
bundle=plan-marshall

# Compose-time execution_tier stamp for verify:module-tests said per_task while the live resolve says orchestrator / 638s

## What happened

The composed execution manifest stamped `verify:module-tests` with `execution_tier: per_task`. The **live** `architecture resolve` for the same canonical command reports `bash_timeout_seconds: 638, execution_tier: orchestrator`.

The stamp is not merely stale — it is unrunnable as stamped. The build wrapper's own 330 s internal ceiling makes `module-tests` impossible for a per-task leaf to complete, so a leaf that trusted the stamp would be routed into an envelope that cannot finish the command.

## Why it matters for truthful signals

`execution_tier` is a **dispatch-routing decision**, not a cosmetic annotation. A wrong `per_task` stamp routes a long build into a leaf envelope where it is killed or times out — and the resulting failure presents as *a build failure*, not as a routing defect. The true cause is one layer up from where the red appears, which is the most expensive possible place to hide it. It also intersects the known harness behaviour where a killed background job returns zero output: the leaf gets an uninformative failure and the natural (wrong) response is to blind-retry the build.

The structural shape is **derived-value-as-authority**: a value is computed once at compose time, persisted, and thereafter trusted by consumers, while the authoritative resolver it was derived from can move independently. Nothing reconciles the two, so the divergence is permanent and silent.

## Corrective rule

Pick one, and make it the only path:

- **(a) Do not persist it.** Drop `execution_tier` / `bash_timeout_seconds` from the composed manifest entirely and have consumers read them from the live `architecture resolve` at dispatch time. The resolver is already the source of truth; a cached copy buys nothing but drift.
- **(b) If the stamp must be persisted, validate it.** `manifest validate` must re-resolve each stamped command and **fail the validate on divergence** from the live resolve. A persisted derived value with no reconciliation step is not a cache; it is a second, unowned source of truth.

**A derived value that can silently diverge from its own source of truth must not be the value consumers read.**

## Recurrence signature

Any compose-time / plan-time stamp of a value that a live resolver also computes: build commands, timeouts, tier assignments, module lists, bot rosters. Each one needs either removal or a validate-time reconciliation — never bare persistence.
