envelope_version=1
sender_type=plan
sender_id=plan-130-sweep-the-prose-the-widened-rules
epic=test-quality
kind=candidate-lesson
created=2026-09-07T15:22:35Z

# Observation to verify: the lessons-capture Signal Gate forwarded 1 script-failure cluster where the phase log holds 3 distinct failing notations

**Status**: unverified observation, not a finding. Recorded for the orchestrator to confirm or refute — the leaf that observed it cannot check the gate's derivation without recomputing the signal it is contractually barred from recomputing.

## What was observed

The `lessons-capture` dispatch forwarded `signal_script_failure_clusters_count: 1`.

Reading the `6-finalize` work log for the records behind that signal (reading the records is permitted; re-deriving the count is not) surfaced **three** distinct failing notations, all `failure_kind=argparse_rejection`, all timestamped **before** the gate was evaluated:

- `plan-marshall:workflow-integration-github:github_pr` — `2026-09-07T06:13:08Z`
- `plan-marshall:manage-references:manage-references` — `2026-09-07T15:08:36Z`
- `plan-marshall:manage-solution-outline:manage-solution-outline` — `2026-09-07T15:11:09Z`

The `lessons-capture` step began at `2026-09-07T15:18:43Z` and dispatched at `15:19:19Z`, so all three records existed at gate-evaluation time. The gate's definition is "number of **distinct failing script notations**" across `[FAILED]`, `[ERROR] ... script_failure`, and `voluntary_checkpoint → error` markers, with union dedup **by distinct notation** — three distinct notations should dedup to three.

## Why it may still be correct

Explanations the leaf could not rule out, listed so the check is cheap:

1. The gate may scope its log scan to a phase other than, or narrower than, the whole run (e.g. `5-execute` only) — in which case 1 is right for its scope and the count's *name* is what misleads.
2. The gate may dedup by something other than notation (failure kind, or step) despite the documented rule.
3. The gate may read the `script` log rather than the `work` log, and the two may not carry the same markers.

## Why it is worth checking anyway

The gate is a **skip decision**. At all-zero signals this workflow body is never dispatched at all. A cluster counter that under-reports by 3x is therefore not merely a cosmetic number — it is the thing that decides whether the run's script failures are ever looked at. An undercount that reaches zero silently discards the whole class.

This is the same shape as the sweep's own rule-undercount finding already routed to this epic (a rule reporting only the first match per segment cannot serve as its own worklist), at a different site: **a derived count consumed as a gate must be checked against an independent enumeration at least once.** If the gate is confirmed correct here, that check is what makes its zeros trustworthy.
