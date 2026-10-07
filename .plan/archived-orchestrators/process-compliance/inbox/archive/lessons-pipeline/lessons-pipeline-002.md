envelope_version=1
sender_type=plan
sender_id=lessons-pipeline
epic=process-compliance
kind=finding
created=2026-09-18T06:41:34Z

# Finding: finalize session_id resolver hard-blocks unattended opencode runs

kind: finding
source_plan: lessons-pipeline
phase: 6-finalize-entry

## Observation

`plan-marshall:plan-marshall/workflow/execution.md` Finalize Phase resolver requires `status.metadata.session_ids` (or retired scalar) and aborts finalize when late `platform-runtime session capture` also fails. On opencode there is no hosted session id:

- `session capture --plan-id lessons-pipeline` → `hook_not_configured` ($CLAUDE_CODE_SESSION_ID unset)
- `session bind --plan-id lessons-pipeline` → `bound: false, reason: no_session_id`

`phase-6-finalize` itself degrades gracefully (`metrics normalized-tokens` returns `no-op` on OpenCode, `enrich` skips). The hard-block lives one layer above the graceful degradation, so unattended opencode finalize cannot enter the phase that already knows how to handle the absence.

## Relevance test

Proposes a structural guard repair: make the execution.md resolver opencode-aware (treat `hook_not_configured`/`no_session_id` as `session_id: absent → enrich no-op` instead of abort), or move the hard-block into `record-metrics` where the no-op already exists.

## Action in this run

Filed here per standing instruction (process-rule issues → process-compliance inbox). Proceeding with finalize entry carrying `session_id` absent; `record-metrics` expected to no-op enrichment.
