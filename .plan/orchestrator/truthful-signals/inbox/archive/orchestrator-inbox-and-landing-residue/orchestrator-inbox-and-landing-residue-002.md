envelope_version=1
sender_type=plan
sender_id=orchestrator-inbox-and-landing-residue
epic=truthful-signals
kind=candidate-lesson
created=2026-08-24T16:52:23Z

component=plan-marshall:plan-retrospective
category=bug
confidence=high
source_plan=orchestrator-inbox-and-landing-residue
source_aspects=chat_history_analysis

# Chat-history aspect must analyse every recorded session_id

## Context

`plan-retrospective` takes a single optional `--session-id` and dispatches the chat-history aspect against that one transcript. This plan's `status.metadata.session_ids` records **two** sessions, and the dispatcher supplied only the second.

Measured on the supplied session alone (`fbc49fc3-c096-4302-b5eb-a8ab3115dcae`):

- `raw_turn_count: 340`, `operator_turn_count: 1`, `gate_decision_count: 0`
- the single operator turn is the `/plan-marshall:plan-marshall` slash-command invocation itself

Measured on the first session (`e0c9a71c-978a-4bf5-aaaa-ebd8e3a93e3c`):

- `raw_turn_count: 1691`, `operator_turn_count: 10`, `gate_decision_count: 15`

Every operator gate decision the plan took, every operator correction, and every unblocking prod lives in the session the dispatcher did not supply. Had this retrospective analysed only what it was given, it would have reported a confident "essentially no operator interaction" for a plan whose narrative includes two overridden routers, three scope widenings, a force-removed worktree over an inconclusive investigation, and six bare `continue` prods.

## Root cause

The aspect's input contract is a single `--session-id`, but the plan's own state records the session set. A resumed plan — which is the normal shape for any plan spanning more than one working session — always has more sessions than the dispatcher forwards, and the aspect has no way to know it is looking at a fraction. `no_signal: false` and `over_budget: false` both came back clean, so the Tier-1/Tier-2 degradation path did not fire either: the reduction succeeded, over the wrong population.

This is a could-not-look reporting as evaluated-clean, at whole-aspect granularity.

## Proposed action

- Derive the transcript set from `status.metadata.session_ids` rather than from the single `--session-id` argument, treating the supplied id as a hint (or as the session to analyse *in addition to* the recorded set) rather than as the population.
- Emit the coverage explicitly on the fragment: `sessions_recorded`, `sessions_analysed`, and per-transcript turn/decision counts, so a partial analysis is visible rather than indistinguishable from a quiet plan.
- When a recorded session's transcript cannot be resolved on disk, report it as a named unresolved transcript, not as a session with zero signal.

## Evidence

- aspect: chat_history_analysis — `sessions_recorded_in_status_metadata: 2`, `supplied_session_id: fbc49fc3-...`
- `extract-chat-signal run --transcript-path .../fbc49fc3-....jsonl` → `operator_turn_count: 1`, `gate_decision_count: 0`
- `extract-chat-signal run --transcript-path .../e0c9a71c-....jsonl` → `operator_turn_count: 10`, `gate_decision_count: 15`
- `manage-status read` → `metadata.session_ids[2]`
