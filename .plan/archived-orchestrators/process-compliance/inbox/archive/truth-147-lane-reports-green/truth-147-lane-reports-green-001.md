envelope_version=1
sender_type=plan
sender_id=truth-147-lane-reports-green
epic=process-compliance
kind=finding
created=2026-09-23T07:12:34Z

# Process-compliance finding — PLAN-TRUTH-147 init (truth-147-lane-reports-green)

Source plan: truth-147-lane-reports-green (init from file-pointer task implementing PLAN-TRUTH-147 spec).
Filed per operator instruction: all issues with the process rules go to .plan/orchestrator/process-compliance/inbox.

## 1. Hand-off command path does not match the tracked store location

- Spec `Hand-Off Command` block (PLAN-TRUTH-147) emits:
  `implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-147-....md`
- Actual sanctioned read path resolved via `orchestrator corpus read --slug truthful-signals --plan PLAN-TRUTH-147`:
  spec `PLAN-TRUTH-147-a-lane-reports-green-yields-or-transitions-without-the-artifact-its-own-gate-requires.md`
  under the tracked orchestrator store (`.plan/orchestrator/truthful-signals/plans/`).
- The `local` segment in the hand-off path does not resolve to the tracked tree the corpus reader serves.
- Init proceeded with the tracked-store path (corpus read succeeded; `request create --body-file` succeeded with `status: success`).
- Request: correct the hand-off template to emit the tracked-store path, or document the local-vs-tracked mapping so file-pointer ingestion does not depend on operator correction.

## 2. Tier 1 recipe-match / aspect-classify have no file-passing surface for ingested briefs

- Phase-1-init Step 4 file-pointer branch rebinds `{request_narrative}` to the ingested spec body (here ~17KB, 185 lines, many `#` headings).
- Step 5c invokes `manage-config recipe-match --request-text "{request_narrative}"` and `aspect-classify --request-text` inline.
- Inline multi-line payloads whose lines begin with `#` trip the Bash permission heuristic ("Newline followed by `#` inside a quoted argument"), and 17KB verbatim via `--request-text` exceeds safe single-arg practice.
- `manage-files write` solves the same class via `--content-file`/`--stdin`; `recipe-match`/`aspect-classify` expose only `--request-text` (verified via `--help`).
- Request: add `--request-file`/`--stdin` to both verbs, or document the sanctioned large-brief marshaling so init does not have to choose between verbatim-scoring and Bash safety.

## 3. Preflight marshal staleness (advisory, recorded for completeness)

- `generate_executor preflight` returned `executor_action: fresh`, `marshal_status: stale` (installed 0.1.1752, executor 0.1.1752, marshal 0.1.1740).
- Per SKILL.md auto-detect Step 0 this is advisory-only and non-blocking; routing continued. Operator note: run `/marshall-steward` to reconcile config stamps.
