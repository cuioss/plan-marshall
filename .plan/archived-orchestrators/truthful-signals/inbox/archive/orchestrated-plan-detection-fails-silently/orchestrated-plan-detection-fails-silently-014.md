envelope_version=1
sender_type=plan
sender_id=orchestrated-plan-detection-fails-silently
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T16:18:30Z

component=plan-marshall:phase-5-execute
category=bug
bundle=plan-marshall

# Five completed tasks produced one [ARTIFACT] line, and "Re-entering execute phase" was logged on the first and only entry

## Two logging-integrity defects in one phase

### A — [ARTIFACT] emission covered 1 of 5 tasks

`work.log` for PLAN-114's execute phase carries five `[OUTCOME] … Completed TASK-00N` lines (TASK-001 through TASK-005) and exactly **one** `[ARTIFACT] (plan-marshall:phase-5-execute:1)` line — `M …/_orchestrator_inbox.py` at 14:15:59.

All five tasks produced real file changes; the phase landed three per-deliverable commits (`4bc6d98`, `308f73e`, and deliverable 3). The four missing artifact announcements are not "tasks that changed nothing" — they are the test rewrites (+128 and +50 lines) and two SKILL.md edits.

The retrospective's `ARTIFACT_EMISSION` rule expects one `[ARTIFACT]` per file-changing `[OUTCOME]`. Observed ratio: 5:1.

### B — "Re-entering" announced on first entry

`work.log` 14:11:37: `[STATUS] (plan-marshall:phase-5-execute) Re-entering execute phase - 5 tasks pending`.

There was exactly **one** execute dispatch (`[DISPATCH]` at 14:10:01, no second). There is **no** "Starting execute phase" line anywhere in the run. `analyze-logs` recorded the raw asymmetry — `inferred_dispatches: 1, starting_markers: 0, re_entering_markers: 1` — and emitted no finding for it.

So the phase's own entry marker says "this is a resumption" on a run that never resumed, and the marker that would say "this is a fresh start" is never emitted at all.

## Why they matter for truthful signals

Both defects corrupt the substrate the *retrospective itself* reads.

Defect A: `[ARTIFACT]` lines are how the run announces what it touched. With 1 of 5 emitted, a reader reconstructing the plan's footprint from its work log recovers one file out of five and has no indication anything is missing. The commits happen to record the truth, so the loss is currently invisible — which is exactly the condition under which it will stay unfixed.

Defect B is worse than a cosmetic mislabel: `RE_ENTRY_COVERAGE` is a real detector for the agent-initiated-re-dispatch failure mode (lesson `2026-05-08-14-001`). Feeding it a `Re-entering` marker that fires on first entry makes the detector unable to distinguish a resumed run from a fresh one. A signal designed to detect re-dispatch is emitted unconditionally, so it detects nothing.

## Corrective rule

1. **`[ARTIFACT]` emission must be script-enforced at task completion**, not left to the LLM's discretion — the same treatment `[OUTCOME]` already received. If `manage-tasks` marks a task complete and its diff against `task_start_sha` is non-empty, the artifact lines must be emitted by that path.
2. **Fix the entry marker polarity.** Emit `Starting execute phase` on first entry and `Re-entering execute phase` only when a prior execute dispatch for this plan exists. The distinguishing fact is already available — the phase can count its own prior `[DISPATCH]` lines.
3. **`analyze-logs` should promote the asymmetry to a finding.** It already computes `starting_markers: 0, re_entering_markers: 1, inferred_dispatches: 1`; `re_entering_markers > inferred_dispatches - 1` is a one-line predicate over numbers it already has. Computing the evidence and emitting no finding is the same not-quite-reporting shape this epic keeps finding.

## Evidence

- `work.log` 14:11:37 (`Re-entering`), 14:10:01 (the single `[DISPATCH]`), 14:15:59 (the single `[ARTIFACT]`)
- `work.log` 14:13:57 / 14:18:58 / 14:28:05 / 14:28:28 / 14:29:29 — the five `[OUTCOME] Completed` lines
- `fragment-log-analysis.toon` — `dispatch_clustering: {inferred_dispatches: 1, starting_markers: 0, re_entering_markers: 1}` with `findings` carrying nothing about it
