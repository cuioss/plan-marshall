# Phase 6: Finalize Workflow Overview

Visual overview of the finalization workflow for human readers.

## 6-Phase Model

```
1-init → 2-refine → 3-outline → 4-plan → 5-execute → 6-finalize
                                              ↑              │
                                              └──────────────┘
                                              (loop on PR issues)
```

**Iteration limit**: 3 cycles max for PR issue resolution.

## Manifest-Driven Dispatch

Phase 6 is a pure executor of the per-plan execution manifest. The manifest is composed at outline time by `manage-execution-manifest:compose` and stored at `.plan/local/plans/{plan_id}/execution.toon`. Phase 6 reads `manifest.phase_6.steps` and dispatches each step in order — it never invents steps, never reorders them, and never applies its own skip logic.

```
┌──────────────────────────────────────────────────────────────────────┐
│                     FINALIZE PIPELINE (manifest-driven)              │
│                                                                      │
│   ┌────────────────────────────────────────────┐                     │
│   │  Step 2: Read manifest.phase_6.steps       │                     │
│   │          + cross-phase config              │                     │
│   └─────────────────────┬──────────────────────┘                     │
│                         ↓                                            │
│   ┌────────────────────────────────────────────┐                     │
│   │  Step 3: FOR each step_id in manifest:     │                     │
│   │    a. Re-entry check (resumable):          │                     │
│   │       outcome=done   -> SKIP               │                     │
│   │       outcome=failed -> RETRY              │                     │
│   │       (no record)    -> dispatch           │                     │
│   │    b. Dispatch under per-agent timeout:    │                     │
│   │       sonar / automated-review : 15 min    │                     │
│   │       lessons                  :  5 min    │                     │
│   │       inline-only              : no wrap   │                     │
│   │    c. On timeout: log ERROR,               │                     │
│   │       mark step failed, CONTINUE           │                     │
│   └─────────────────────┬──────────────────────┘                     │
│                         ↓                                            │
│   ┌────────────────────────────────────────────┐                     │
│   │  Steps 4–7: phase transition,              │                     │
│   │            output template, terminal title │                     │
│   └────────────────────────────────────────────┘                     │
└──────────────────────────────────────────────────────────────────────┘
```

### Resumable Re-Entry

Every Phase 6 entry is implicitly resumable. The Step 3 dispatch loop consults `status.metadata.phase_steps["6-finalize"][step_id].outcome` before each step:

- `done`   → step completed on a previous invocation; skip dispatch
- `failed` → previous attempt failed (typically a timeout); retry from scratch (one fresh attempt per invocation)
- absent / other → dispatch as a first-time run

There is no separate "resume" mode. Interrupted finalize runs are restarted by simply re-entering Phase 6.

### Per-Agent Timeout Wrapper

Agent-suitable steps (Task-dispatched) run under a per-agent budget enforced by the dispatch loop:

| Step | Budget | Rationale |
|------|--------|-----------|
| `sonar-roundtrip`    | 15 min (900 s) | Full Sonar gate roundtrip + optional fix-task creation |
| `automated-review`   | 15 min (900 s) | CI wait + review-bot buffer + comment triage |
| `lessons-capture`    |  5 min (300 s) | Bounded `manage-lessons add` + Write workflow |
| All other steps      | none           | Inline-only or no explicit budget |

On timeout, the dispatcher logs an `[ERROR]` entry, records the step as `outcome=failed` with `display_detail="timed out after Ns"`, and continues with the next manifest step. The pipeline is never aborted by a single agent timeout — graceful degradation is the default. The next Phase 6 entry retries the failed step.

## Loop-Back on Findings

```
┌────────────────────────────────────────────┐
│            AUTOMATED REVIEW / SONAR        │
│                                            │
│              [issues]    [no issues]       │
│                 │             │            │
│                 ↓             ↓            │
│       create fix tasks    COMPLETE         │
│       loop → 5-execute                     │
│       (max 3 iterations)                   │
└────────────────────────────────────────────┘
```

A loop-back is initiated by `automated-review` or `sonar-roundtrip` only when their underlying workflow returns `loop_back_needed=true`. The loop-back is a phase transition, not a step skip — Phase 6 returns to Phase 5, which executes fix tasks, then re-enters Phase 6. Both paths respect the manifest unchanged on re-entry.
