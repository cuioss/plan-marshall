envelope_version=1
sender_type=plan
sender_id=implement-opencode-enforcement-parity
epic=process-compliance
kind=finding
created=2026-09-22T19:45:49Z

# Finding: light-lane pre-dispatch 2-refine capture can never pass `pr_title_present`

## Reported

- Plan: `implement-opencode-enforcement-parity` (PLAN-15), light-lane pre-dispatch close
- Location: `plan-marshall/workflow/planning.md` § "Light-lane branch" step 2 / `phase-3-outline/workflow/light-lane.md` Step 6
- Encounter: `phase_handshake capture --phase 2-refine` returned `error: pr_title_missing` — `metadata.pr_title` is
  absent, but `pr_title_present` is `blocking_at_every_boundary` from `2-refine` onward
  (`_invariants.py` `_capture_pr_title_present`, raised by `_handshake_commands.py`).

## Observed disposition

Correct disposition for a light-lane plan: capture succeeds (planning.md light-lane step 2c lists capture as one of
the three pre-dispatch calls the orchestrator MUST issue). It cannot today.

## Root cause

`pr_title` is authored at exactly ONE lifecycle site: phase-2-refine Step 13 (`phase-2-refine/SKILL.md` line 266,
`phase-2-refine/standards/refine-workflow-detail.md` line 808). That step runs inside the deep-lane refine body.
On the light lane, refine-no-loop is FOLDED into the collapsed envelope (`phase-3-outline/workflow/light-lane.md`
Step 1) — and the planning.md light-lane branch requires the `2-refine` capture to happen BEFORE that envelope is
dispatched:

- `planning.md` step 2a-c: transition 2-refine → phase-boundary → capture, all pre-dispatch.
- `light-lane.md` Step 6: "the 2-refine transition is owned by the orchestrator ... before this envelope is
  dispatched; this envelope does not own it and must not issue it."

So at capture time the plan is a normal running plan (no envelope ran), and `pr_title` has never been authored —
the folded refine body that would author it has not executed, and the envelope does not author it either
(`light-lane.md` Step 1 is a read of the clarified request, with no Step-13-equivalent persist).

## Evidence

- The three pre-dispatch calls in planning.md step 2 contain NO `pr_title` authoring step.
- `light-lane.md` (steps 1-6 and Output) contains no `pr_title` / `metadata --set` write anywhere.
- `_capture_pr_title_present` treats `1-init` as the only phase where an absent title is legitimate and raises
  `PrTitleMissing` for `2-refine`+ unconditionally — it has no light-lane carve-out.
- The documented remedy is "re-run phase-2-refine Step 13 title authoring"; on the light lane that step's home
  (the refine body) never runs, so the remedy only works when re-performed by the orchestrator ad hoc.

## Impact

Every light-lane plan would fail its pre-dispatch 2-refine capture, halting the light-lane branch at step 2c
before the envelope dispatch. The orchestrator can work around it only by authoring `pr_title` itself (the action
taken here), but that is not documented in the light-lane branch, so the failure is a genuine process-rule gap
rather than an intended workflow step.

## Suggested fix direction

- Either document an orchestrator-side `pr_title` authoring step in planning.md § "Light-lane branch" step 2
  (before the capture), positioned as the light-lane counterpart to refine Step 13; or
- Teach `_capture_pr_title_present` to accept an absent title at `2-refine` when the plan is on the light lane,
  deferring the presence check to a later boundary where the title must exist — keyed on
  `status.metadata.planning_lane == light`, which is resolved and persisted long before this capture runs.
- Either way, update the light-lane tests / the phase-handshake reference to cover the light-lane
  pre-dispatch capture explicitly.
