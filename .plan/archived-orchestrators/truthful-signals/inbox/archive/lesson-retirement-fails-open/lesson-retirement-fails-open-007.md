envelope_version=1
sender_type=plan
sender_id=lesson-retirement-fails-open
epic=truthful-signals
kind=landing
created=2026-08-08T18:07:06Z

## What landed

**PLAN-TRUTH-044 — `lesson-retirement-fails-open`** shipped as **PR #1113**, merged through the
merge queue into `main`. 12 commits, 9 tasks, 2 loop-back iterations.

The plan closed the lesson-store **fail-open** class: a call site that treats "the lesson store
said nothing" as "there is nothing", so a lesson silently disappears instead of surfacing a
refusal.

## Sites closed

The spec named **three** sites; the plan closed **four**:

1. `restore-from-plan` — the inverse of `convert-to-plan`; a failed restore left the lesson
   stranded in the plan directory.
2. `list-stalled` — the detection half of the stranded-lesson gap.
3. `lessons-housekeeping` (the finalize step) — corpus reconciliation over a store it could not
   prove it had resolved.
4. **`manage-status delete-plan`'s lesson carry-back** — the fourth site, NOT in the spec. It
   silently dropped a colliding lesson *immediately before deleting the directory holding the only
   copy*. Worst-case ordering in the whole class: the drop and the destruction of the last copy
   were adjacent.

### How the fourth site was found — the transferable part

The Q-Gate found it by **deriving the population from a content sweep rather than from the spec's
two rosters**. The spec's rosters were the authored list of "where lessons are resolved"; the
sweep's population was every site that actually resolves one. The two disagreed by one, and the
one they disagreed on was the most damaging instance.

This is the epic's recurring shape: *a roster is a claim about a population, not the population*.
A set-guarding check whose population comes from an authored list can only ever confirm the list.

## Scope decision the epic should hold

**D3 was narrowed to option (a) only** — decouple corpus resolution from cwd via an explicit
main-anchored store handle. Option (b), splitting the finalize step, **stays owned by
PLAN-CIS-034** per the settled ownership boundary. This is a deliberate boundary, not an
under-delivery: do not re-stage (b) here.

## Residue the epic should track

Two defects surfaced by this run are **not ours** and are already recorded as findings:

- **`f49f93`** — `workflow-integration-github`: `post_responses` re-transmits already-answered
  findings, and `fetch_findings` carries no rate-limit-refusal filter (a refusal reads as an empty
  result — the same fail-open shape this plan just closed, one layer out).
- **`8c066f`** — plugin registry pin left at `0.1.1304` while the cache synced to `0.1.1324`.
  **12th recorded instance** of the pin/orphan-GC inversion.

`8c066f` is worth the epic's attention on recurrence count alone: twelve instances is no longer an
incident series, it is a standing condition of the runtime the epic's plans execute in.

## Candidate lessons

Six `candidate-lesson` messages for this plan are already queued
(`lesson-retirement-fails-open-001` … `-006`), routed by `plan-retrospective`. This landing message
adds none — it records the landing only.
