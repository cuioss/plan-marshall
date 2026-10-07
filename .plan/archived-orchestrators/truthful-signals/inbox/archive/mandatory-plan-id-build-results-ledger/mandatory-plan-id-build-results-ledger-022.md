envelope_version=1
sender_type=plan
sender_id=mandatory-plan-id-build-results-ledger
epic=truthful-signals
kind=candidate-lesson
created=2026-08-02T07:20:38Z

component=plan-marshall:ref-workflow-architecture
category=bug
title=Dispatch instrumentation is partial in three places and read downstream as complete

# Dispatch instrumentation is partial and read as complete

Three independent dispatch-recording surfaces under-record on PR #1075. Each is consumed
downstream as if it were the full population — the classic truthful-signals shape: an
incomplete instrument reported without a completeness qualifier.

## 1. `[DISPATCH]` is not emitted at 5 finalize dispatch sites

The `[STATUS] (plan-marshall:execution-context.{name}) Complete` line is emitted by the
execution-context envelope itself (dispatcher Step 6). Its presence is therefore *independent
proof* that a dispatch happened. Five finalize steps have that marker, are recorded
`outcome: done` in `status.metadata.phase_steps`, and have **no `[DISPATCH]` line anywhere**:

| Step | Complete marker |
|---|---|
| `sonar-roundtrip` | 20:44:01Z |
| `project:finalize-step-review-retrospective` | 21:20:22Z |
| `lessons-capture` | 21:28:51Z |
| `adr-propose` | 21:35:08Z |
| `plan-marshall:plan-retrospective` | this envelope |

Coverage: **8 of 13 finalize dispatch sites** honour the emission contract.

## 2. `[DISPATCH]` is not emitted at envelope RE-ENTRY

Phase 5 recorded **6** execution-context `Complete` markers and **9** dispatch-boundary rows
against only **3** `phase-5-execute` `[DISPATCH]` lines (`envelope_id` 1, 2, 3). The clean
example is 16:34:39Z: a re-entry after the mid-phase `verification-feedback` dispatch returned,
carrying its own envelope-scoped `[SKILL] (plan-marshall:execution-context.phase-5-execute)
Loaded plan-marshall:execute-task` line and a `Re-entering execute phase — 6 tasks pending`
marker, with no `[DISPATCH]` line between the 16:22:23Z dispatch and it.

Re-entry is a dispatch. It costs an envelope, it burns tokens, it appears in the boundary file.
It is invisible in the dispatch log.

## 3. The 6-finalize dispatch-boundary artifact captured 18% of its population

| Source | Metric-bearing finalize dispatches | Tokens |
|---|---|---|
| `execution.toon` → `execution_log` | **11** | **1,564,096** |
| `work/metrics-dispatch-boundaries-6-finalize.toon` | **2** | 196,912 |

The boundary file holds only the first two dispatched steps (lessons-housekeeping 127,797 and
plugin-doctor 69,115) and then stops. `record-step` captured all 11 over the same population,
so this is a gap in the boundary emitter, not in the run.

The `analyze-logs` retrospective aspect reads the boundary file and reports
`6-finalize: rows[2]` with no completeness qualifier. A reader of the compiled retrospective
would conclude finalize made **two** dispatches costing 197K tokens rather than **eleven**
costing 1.56M — an 87% understatement of the phase.

## 4. Bonus: one `[DISPATCH]` line is attributed to a leaf

```
2026-08-01T16:22:23Z [DISPATCH] (plan-marshall:phase-5-execute) target=execution-context-level-4 role=verification-feedback
```

The emitter tag names `phase-5-execute`, a dispatched leaf. **A leaf cannot dispatch.** The
line at 16:21:15Z records the leaf returning `triage_required`, so the orchestrator made this
dispatch and stamped it with the leaf's component tag. No invariant was actually broken — but
anyone auditing leaf/dispatch topology from the logs alone reads this as a violation, and the
dispatch-audit aspect exists precisely to be audited from the logs alone.

## Do this instead

- The emission contract in `dispatch-logging.md` needs an **enforcement consumer that fails**,
  not just an aspect that reports. The inverse-coverage check already exists conceptually
  (`dispatch_coverage_violation`); on this plan it had to be computed by hand against the
  envelope's own Complete markers.
- **Re-entry must emit.** Whatever emits on first dispatch must emit on re-entry, or the
  boundary-row count and the dispatch-line count can never reconcile.
- The boundary file and `execution_log` cover the same population and disagree 2-vs-11.
  Either reconcile them or make `execution_log` the single source and retire the boundary file
  for phase 6.
- Any aspect rendering a count from an instrument that can under-record must carry the
  instrument's **denominator**, not just its numerator.

## Verdict on the other direction

Direction 1 of the dispatch audit — *every spawn rode the canonical envelope* — is **clean**:
all 17 recorded dispatches name an `execution-context-level-N` target (3× level-3, 1× level-4,
13× level-5), and phase-5 correctly yielded six times rather than running or backgrounding an
orchestrator-tier build inside a leaf. The leaf invariant held.
