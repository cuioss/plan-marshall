envelope_version=1
sender_type=plan
sender_id=context-byte-attribution-instrumentation
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-03T16:41:33Z

# Record session_ids as a list so enrich can span a multi-session plan

component: plan-marshall:manage-metrics
category: improvement
confidence: high
source_plan: context-byte-attribution-instrumentation
source_pr: 1086

## Context

`manage-metrics enrich` accepts exactly one `--session-id` and walks that session's transcript plus
its subagent transcripts. The four-field context view (`input_tokens`, `output_tokens`,
`cache_read_input_tokens`, `cache_creation_input_tokens`) and `billing_weighted_total` exist ONLY in
those raw `message.usage` dicts — they are unobtainable from any other source.

This plan spanned **at least three distinct session ids**:

1. Phases 1-4 ran with **no session id recorded at all**. `work.log` carries an explicit WARNING at
   07:21:07: "session_id not captured at plan-init".
2. `9c9328ba` was first stamped at 08:51:57, mid-phase-5.
3. At retrospective time the live session is `2bd1b4d5` — the plan survived a weekly-API-limit halt
   at 11:02 and resumed at 11:51, producing the `blocked_session_restart` boundary row.

A single `--session-id` therefore cannot cover this plan. Phases 1-4 are permanently unattributable;
the finalize band ran under a different session than the one stored.

## Root cause

`status.metadata.session_id` is a scalar written by last-writer-wins. Session identity is treated as
a plan-invariant property, but a long plan crossing a quota reset or a context compaction is
routinely multi-session. The scalar cannot express what actually happened.

## Proposed action

Make `status.metadata.session_ids` an append-only list. Every `session capture` appends when the id
is new rather than overwriting. `enrich` then walks every recorded session and sums the four fields
across all of them, reporting the covered set as its population.

This is a direct prerequisite for the epic's flagship claim: without it, no per-phase `cache_read`
figure for a multi-session plan can name a complete population, and D4's "every emitted figure names
its population" degrades to "every figure names a population that is silently a subset".

## Evidence

- aspect: execution_context_dispatch_audit — three distinct session ids observed across one plan; phases 1-4 predate any recorded id
- aspect: chat_history_analysis — the analysed transcript (466 raw turns) covers only session 9c9328ba, an explicit strict subset of the plan's conversational history
- aspect: logging_gap_analysis — the 07:21:07 WARNING documents that init-time capture failed and deferred to a finalize-time "hard-block abort" fallback
