envelope_version=1
sender_type=plan
sender_id=orchestrated-plan-detection-fails-silently
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T15:41:14Z

component=plan-marshall:phase-3-outline
category=bug
bundle=plan-marshall

# Light-lane collapsed envelope never writes status.metadata.pr_title, so phase_handshake capture fails at BOTH the refine and outline boundaries

## What happened

On PLAN-114 (`planning_lane: light`), `phase_handshake capture` FAILED with `pr_title_missing` at **both** the 2-refine→3-outline boundary and the 3-outline→4-plan boundary. The orchestrator had to author `status.metadata.pr_title` by hand to unblock the run.

## Root cause

`phase-2-refine` Step 13 is the writer that authors `status.metadata.pr_title`. The light lane (`phase-3-outline/workflow/light-lane.md`) collapses the refine envelope and folds Step 13 away — **and supplies no replacement writer**. Every light-lane plan therefore arrives at the handshake with the field unset. The failure is not intermittent; it is structural and fires on every light-lane run.

Corroborating evidence from the same collapse: the plan's `status.json` finished the run with `phases[].2-refine` still at `in_progress` while `current_phase` was `6-finalize`. The refine phase row was never closed either.

## Why it matters for truthful signals

The handshake is a real gate and it refused correctly — the gate is not the defect. The defect is that a **lane variant silently removed the only producer of a field a downstream consumer requires**. A collapsed envelope that drops a step must either re-home that step's writes or declare the field optional; doing neither converts a lane choice into a guaranteed mid-run failure that only surfaces as an opaque `pr_title_missing` two boundaries downstream of the omission.

## Corrective rule

When a lane variant collapses a phase envelope, **enumerate every `status.metadata` / `references.json` field the folded steps WROTE, and re-home each write into the collapsed lane**. Do not rely on a downstream handshake to surface the omission — by the time the handshake fires, the producer's identity is no longer visible from the error.

## Recurrence signature

Sweep the folded steps for `manage-status update-field` / `manage-references set` calls; any field written there and read later by another phase is a producerless-consumer candidate. This is the same archetype as the epic's existing `dispatch_boundaries` producerless row — the third instance in this epic.
