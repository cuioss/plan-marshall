envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T11:06:00Z

# Candidate lesson: deep-lane outline written with an empty assessment store

Source: Q-Gate finding 338c41 (3-outline, warning, resolved fixed in-run)

## What happened

The deep-lane solution outline declared 26 affected / survey / mutation paths across deliverables 1-7, but the
assessment store was empty (`assessment list` total_count 0, `findings_store_state: missing`). The outline
Q-Gate (validator 2.2: every affected file must carry a CERTAIN_INCLUDE assessment) flagged it. The scope itself
was sound; only the assessment records were never written.

## Fix applied in-run

One outline re-dispatch recorded 26 CERTAIN_INCLUDE assessments, one per declared path (existing paths verified on
disk, write-new paths verified absent).

## Candidate rule

The deep-lane outline author should record the CERTAIN_INCLUDE assessments as part of writing the deliverables,
not leave them to the Q-Gate to discover. One re-dispatch here also fixed fc4618, so the cost was small, but the
miss is systematic (the store was not merely incomplete, it did not exist).

Likely owner: plan-marshall:phase-3-outline (deep lane).

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `scenario-replay-harness-001.md` from plan scenario-replay-harness (PLAN-22, #50; Claude Code)
