envelope_version=1
sender_type=plan
sender_id=provider-logging-path-containment
epic=truthful-signals
kind=candidate-lesson
created=2026-08-08T23:38:45Z

# Candidate lesson L7 — status.metadata.session_id is single-valued but a plan spans multiple sessions

- component: `plan-marshall:manage-status`
- category: bug
- source plan: `provider-logging-path-containment` (PLAN-TRUTH-011, PR #1123)
- theme: confident-signal-hides-a-caveat

## Observation

This plan executed across **two** host-platform sessions:

- `4f88b922-07ca-4520-8ff8-2d59cc602d01` — launch, 414 turns, phases 1-5 (`task="implement …PLAN-TRUTH-011…"`)
- `6d1aa894-65e8-473d-b46d-97ab3b5fb326` — finalize, 1047 turns, phase 6 (`action=finalize plan=provider-logging-path-containment`)

`status.metadata.session_id` holds only the **latest** (`6d1aa894`). `platform_runtime session capture` re-confirmed and re-stored that single value. Both transcripts exist on disk.

`manage-metrics enrich` takes exactly one `--session-id` and attributes usage per phase from that one parent transcript plus its subagent directory. With a single-valued field, a multi-session plan can only ever have one session's transcripts walked — here, the finalize session. **Phase 1-5 four-field/billing attribution from session `4f88b922` is unreachable through the recorded field**, and `enrich` has no way to report that its coverage was partial, because it does not know a second session existed.

A related symptom: this retrospective was *dispatched* with `session_id: 4f88b922` while `status.metadata` said `6d1aa894`. A consumer trusting either field alone sees half the plan.

## Why this is on-theme

`enrich` returns a confident, structured envelope (`subagent_transcripts_walked`, `four_field_phases_attributed`) with no denominator. Those counts are true of the session it was given and say nothing about the sessions it was not given. There is no `partial` marker on the session dimension, unlike the phase dimension where `#812` already installed one.

## Proposed remedy

1. Record `session_ids[]` (append-on-change) rather than a single `session_id`, so the set of sessions that touched the plan is observable.
2. Have `enrich` walk every recorded session and report per-session coverage, with a `partial` verdict when any recorded session's transcript is missing — the same floor-not-truth shape `generate` already uses for phases.
