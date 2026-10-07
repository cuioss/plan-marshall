envelope_version=1
sender_type=plan
sender_id=self-ingested-reply-non-terminating-barrier-loop
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T10:19:32Z

component=plan-marshall:phase-5-execute
category=bug
bundle=plan-marshall

# The first entry into 5-execute is logged as "Re-entering execute phase"

## Observation

This plan entered phase-5-execute twice — once normally, once via the finalize loop-back that added TASK-004. Both entries emitted the **same** marker:

- `work.log:76` — `2026-07-29T06:58:17Z [STATUS] (plan-marshall:phase-5-execute) Re-entering execute phase - 3 tasks pending` — this was the **first** entry. `decision.log` confirms the loop-back did not happen until 08:31:23Z.
- `work.log:226` — `2026-07-29T08:33:05Z ... Re-entering execute phase - 1 tasks pending` — the genuine re-entry.

`analyze-logs` reports the consequence directly:

```
dispatch_clustering:
  inferred_dispatches: 2
  starting_markers: 0
  re_entering_markers: 2
```

Zero `Starting` markers for a plan that started.

## Why it matters

`references/logging-gap-analysis.md`'s **RE_ENTRY_COVERAGE** rule clusters `{Starting, Re-entering} execute phase` lines and asserts `re_entry_count == clusters - 1`. With `starting_markers` structurally 0, the observed count is always one greater than the expected count, so the rule's arithmetic is off by one on **every** plan and its `Starting` branch is dead code. The check reports a warning that is a property of the emitter, not of the plan.

It is also a plain truthfulness defect independent of the detector: a log line that says "Re-entering" on a first entry misreports what happened, and anyone reconstructing the plan's history from `work.log` alone will infer a loop-back that did not occur.

## Corrective rule

Emit `Starting execute phase` on first entry and `Re-entering execute phase` only when `status.metadata.loop_back_reentry` is set (or when a prior 5-execute completion is recorded). The discriminator already exists in status metadata — `decision.log` 08:31:23Z shows `persisted metadata.loop_back_reentry`, and 09:05:47Z shows it being consumed — the log line simply does not read it.

## Evidence

- `work.log:76` and `work.log:226` — identical "Re-entering" prefix, 95 minutes apart.
- `analyze-logs` fragment: `starting_markers: 0, re_entering_markers: 2, inferred_dispatches: 2`.
- `decision.log` 08:31:23Z (loop-back set-phase 6-finalize -> 5-execute, marker persisted), 09:05:47Z (marker consumed).
- `references/logging-gap-analysis.md` § RE_ENTRY_COVERAGE.
