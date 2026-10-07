envelope_version=1
sender_type=plan
sender_id=config-seeding-effort-presets-steward-upgrade
epic=truthful-signals
kind=candidate-lesson
created=2026-08-26T14:40:23Z

component=plan-marshall:plan-retrospective
category=bug
source_plan=config-seeding-effort-presets-steward-upgrade
confidence=high

# [DISPATCH] rides the resolve seam so re-firings are invisible and both audit directions pass

## Context

The execution-context dispatch audit reported **zero violations** in every category for this run. Both directions passed: 19 `effort resolve-target` decision entries paired 1:1 with 19 `[DISPATCH]` work-log lines, every target was a canonical `execution-context-level-{3,4,5}` envelope, and every DISPATCHED step on the roster carried at least one `[DISPATCH]` line.

Independent evidence says the run actually spawned far more envelopes than that. `manage-metrics enrich` walked **40 subagent transcripts** for this session. `record-dispatch-boundary` wrote 16 rows. `work.log` carries 24 `[SKILL] (plan-marshall:execution-context.*)` load lines. Emission covered at most 19 of 40 discovered spawns — **47.5%**.

The gap is entirely in **re-firings**:

| step | firings | `[DISPATCH]` lines | resolves |
|------|--------:|-------------------:|---------:|
| `pre-submission-self-review` | 8 | 2 | 2 |
| `plan-marshall:automatic-review` | 3 | 1 | 1 |
| phase-5-execute envelope | 10 | 1 | 1 |
| `wait-region-unified-triage` | 1 | 0 | 0 |

Rounds 3–8 of the self-review each logged their own `DEVIATION` line to `decision.log`, so there is no doubt they ran.

## Root cause

Two independent blind spots that happen to cancel.

**Emission.** `[DISPATCH]` rides the `effort resolve-target` **resolve seam** — it is a side effect of resolving a target. A re-dispatch of an already-resolved step does not re-resolve, so it emits nothing.

**Detection.** Because the un-instrumented case drops *both* the resolve entry and the `[DISPATCH]` line, the `shape_violation` detector — which pairs resolves against dispatches — sees a perfectly balanced 19 = 19 and reports clean. It is structurally blind to total omission, which is the dominant failure mode. The `dispatch_coverage_violation` detector is blind for a different reason: it asserts *at least one* `[DISPATCH]` per DISPATCHED step, so a step that fired eight times and emitted twice passes.

An audit whose two arms are blind in complementary ways reports a clean bill over a 52.5% coverage gap.

## Proposed action

1. Emit `[DISPATCH]` at the **dispatch call site**, not on the resolve seam — or make every re-dispatch re-resolve so the seam still fires.
2. Give the audit a **population**: compare `[DISPATCH]` line count against an independently-derived spawn count (`enrich`'s `subagent_transcripts_walked`, or the dispatch-boundary row count) and report the ratio. A `total: 0` finding count is only trustworthy alongside the coverage it was computed over.
3. Change `dispatch_coverage_violation` from per-step to **per-firing**: `status.metadata.phase_steps` already carries `firing_count` and `prior_firings[]`, so the expected `[DISPATCH]` count per step is derivable rather than assumed to be one.

## Evidence

- aspect: `execution-context-dispatch-audit` — `surface_a_dispatch_lines: 19`, `surface_b_resolve_entries: 19`, `subagent_transcripts_walked: 40`, `emission_coverage_vs_transcripts_pct: 47.5`, and the `per_step_refiring` table.
- `phase-6-finalize/standards/dispatch-inline-split.md` line 15 states the emission "rides the `effort resolve-target` **resolve seam** (a per-firing side effect of the resolve each dispatch performs)" — the parenthetical assumes each dispatch resolves, which re-firings do not.
- `status.metadata.phase_steps["6-finalize"]["pre-submission-self-review"]`: `firing_count: 8`, `prior_firings[7]` all `failed`.
- `logs/decision.log` DEVIATION entries at 07:27:47Z, 07:41:20Z, 08:06:44Z, 08:15:56Z, 09:26:49Z, 09:50:43Z — one per un-instrumented round.
