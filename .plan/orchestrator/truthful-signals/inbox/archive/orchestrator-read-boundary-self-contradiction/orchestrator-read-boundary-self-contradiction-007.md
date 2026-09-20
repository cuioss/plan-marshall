envelope_version=1
sender_type=plan
sender_id=orchestrator-read-boundary-self-contradiction
epic=truthful-signals
kind=candidate-lesson
created=2026-07-28T20:44:26Z

component=plan-marshall:manage-execution-manifest
category=improvement
created=2026-07-28
bundle=plan-marshall

# An inline finalize step records total_tokens=0 — a measured zero where "unmeasured" is the truth

## What happened

`manage-execution-manifest record-step` wrote nine entries in this run of the form:

```
Recorded ci-verify phase=6-finalize outcome=executed — total_tokens=0, tool_uses=0, duration_ms=0
```

Every one of those steps did real, expensive work:

| Step | What it actually did |
|---|---|
| `pre-push-quality-gate` | three build invocations (18:28–18:30) |
| `architecture-refresh` | discover + tier-0 comparison |
| `push` | pushed the branch |
| `ci-verify` (×2) | ~10 min each — `ci_complete_precondition` recorded at 591 s and 562 s |
| `branch-cleanup` | ~16 min including merge-queue wait and the merge itself |
| `era-stamp-fill`, `preference-emitter` | scanned and decided |

All recorded as `0`. The reason is mechanical and legitimate: these steps ran
**inline** in the orchestrator context, so there is no dispatched-agent `<usage>`
envelope to read. The defect is not the missing measurement — it is writing `0`
where the honest value is *absent*.

The consequence compounds: `6-finalize` never closed its metrics row at all, so
`metrics.md` renders the **most expensive phase of the entire run** as:

```
| 6-finalize | - | - | - | - | - |
| **Total**  | **53m13s (n=4/6)** | ... | **1,152,463 (n=4/6)** |
```

The `n=4/6` partiality marker is doing real work here and is the one honest signal
in the table — but the nine `0`s upstream of it are not marked partial anywhere.
They are indistinguishable from a step that genuinely consumed nothing.

## Solution

**Rule:** a cost field with no measurement must serialize as *absent/null*, never as
`0`. `0` is a legitimate measured value (a no-op step really can cost nothing) and
must stay available to mean exactly that.

1. Make `record-step` accept and persist a **null/omitted** cost triple distinctly
   from a zero triple, and render inline steps that way.
2. Have the decision-log line say so: `total_tokens=unmeasured (inline step)` rather
   than `total_tokens=0`.
3. Close the `6-finalize` metrics row on the terminal path so the phase is *recorded*
   even when its cost is unmeasured — the `end-phase` contract already treats a
   timestamps-only closed row as fully recorded (the sanctioned inline-phase recording
   mode), so this is a call-site omission, not a missing capability.

Aggregation then has the information it needs: sum the measured, count the unmeasured,
and report both — instead of silently summing zeros into a total that looks complete.

## Impact

Directly on theme, and it corrupts the epic's own instrumentation. Any cross-plan
token-economics or lane-lever-effectiveness analysis that reads these fields is
summing structural zeros as if they were measurements, and will systematically
under-attribute cost to the finalize phase — the phase where, on this run, the
majority of the wall-clock and a large share of the tokens actually went.

Related but distinct from the recorded floor-not-truth work on `generate`'s
`partial` / `unrecorded_phases`: that made *phase-level* incompleteness first-class.
This is the *step-level* hole underneath it, and it is not covered by the same marker.
