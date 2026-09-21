envelope_version=1
sender_type=plan
sender_id=gates-do-not-refire-over-the-loop-back-diff
epic=truthful-signals
kind=candidate-lesson
created=2026-08-01T19:49:50Z

component=plan-marshall:phase-6-finalize
category=bug

# Two ledgers disagree about the same step, and a productive loop-back is tokenized as an error

## Observation

`pre-submission-self-review` on PLAN-TRUTH-001 has two on-disk outcome records that do not agree.

**Ledger A — `manage-execution-manifest record-step` rows in `decision.log`:**

```
16:21:23Z  outcome=error     total_tokens=202832  tool_uses=33  duration_ms=370689
16:44:46Z  outcome=error     total_tokens=228067  tool_uses=47  duration_ms=541011
17:18:57Z  outcome=executed  total_tokens=222106  tool_uses=29  duration_ms=447747
```

**Ledger B — `status.metadata.phase_steps["6-finalize"]`:**

```
pre-submission-self-review:
  outcome: done
  display_detail: "3 passes at max_iterations, 6 findings all fixed and committed"
  head_at_completion: 2efa62b8a292dc67d5410776ca520813d93edba4
```

Ledger A says the step failed twice and then succeeded. Ledger B says the step ran three passes and found six defects, all fixed. **Both are on disk; they cannot both be read as authoritative.**

Ledger B is the correct account. Passes 1 and 2 did exactly what a self-review pass is supposed to do: each found genuine defects (six across the three passes, two of them introduced by the plan's own earlier fixes) and looped back so they could be fixed. That is the mechanism working, recorded under the token reserved for the mechanism breaking.

**Why this matters beyond bookkeeping.** Any consumer that reads Ledger A — a cross-plan audit, a step-reliability metric, a failure-rate dashboard — will score `pre-submission-self-review` as 33% successful on this plan. The truth is that it was 100% successful and the two "errors" are its highest-value outputs. The step that found the most defects looks like the step that failed the most.

The `outcome` vocabulary already carries `loop_back` alongside `done` / `skipped` / `failed` — the token exists and was not used.

## Root cause

Two independent completion ledgers are written by two different producers at two different granularities: `record-step` fires per *dispatch*, `mark-step-done` fires per *step*. Neither producer knows what the other wrote, and nothing reconciles them.

The `error` tokenization compounds it: the dispatch returned a non-success status because it had findings to report, and `record-step` mapped "did not return success" onto `error` rather than onto `loop_back`. A three-valued reality (succeeded / found work and looped back / genuinely failed) was squeezed into a two-valued encoding at the recording site.

## Proposed action

1. Record a loop-back as `outcome=loop_back`, not `outcome=error`. The value already exists in the vocabulary; the recording site needs to distinguish "returned findings" from "raised a fatal error".
2. Reconcile the two ledgers at step close — when `mark-step-done` writes a terminal outcome, either fold the per-dispatch rows into it (`iterations: 3, outcomes: [loop_back, loop_back, done]`) or have `record-step` defer to it. Two ledgers of the same fact must agree or one must be derived from the other.
3. Until then, any consumer aggregating step reliability must read `phase_steps`, not `record-step` rows. Worth stating explicitly wherever the manifest ledger is documented as a metrics source, because the divergence is silent and biases in the pessimistic direction.

## Evidence

- aspect: logging_gap_analysis — `gaps[].detail`: "the manifest step ledger and the phase_steps ledger disagree about the same step"
- `logs/decision.log` — three `(plan-marshall:manage-execution-manifest:record-step)` rows for `pre-submission-self-review` at 16:21:23Z, 16:44:46Z, 17:18:57Z
- `status.metadata.phase_steps["6-finalize"]["pre-submission-self-review"]` — single `outcome: done`
- `logs/work.log:249` — `[STATUS] (plan-marshall:execution-context.pre-submission-self-review) Complete - iteration 3, 72 candidates examined, 3 findings`
- Sibling context: epic inbox message 004 records that the three-pass behaviour was correct and valuable; this message records that the ledger says otherwise
