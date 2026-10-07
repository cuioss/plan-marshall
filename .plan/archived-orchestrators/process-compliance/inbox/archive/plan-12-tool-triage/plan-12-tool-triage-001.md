envelope_version=1
sender_type=plan
sender_id=plan-12-tool-triage
epic=process-compliance
kind=finding
created=2026-09-27T14:23:16Z

# `manage-status transition` mailbox probe misclassifies every orchestrated plan as `not_orchestrated`

## Observed

`manage-status transition --plan-id plan-12-tool-triage --completed 1-init` returned:

```text
mailbox:
  checkpoint: phase-transition
  probe: not_orchestrated
  reason: "request.md source_id is not an orchestrator plan-spec pointer (detection=not_orchestrator_pointer) ..."
```

For the SAME source_id, `orchestrator inbox detect --source-id .plan/orchestrator/process-compliance/plans/PLAN-12-tool-triage.md`
returned `orchestrated: true`, `epic: process-compliance`, `detection: orchestrated`, and
`manage-plan-documents request read` confirms `source_id` is stored verbatim in request.md.

## Root cause (read, not reproduced by a test)

`manage-status/scripts/_cmd_lifecycle.py:174` feeds the raw request.md text to
`file_ops.parse_markdown_metadata`, which parses **`key=value`** lines and **stops at the first blank
line or heading** (`tools-file-ops/scripts/file_ops.py:1554`). request.md starts with an HTML comment,
then `# Request: ...`, then `key: value` lines — so the parser returns `{}` for every request.md and
`classify_source_id('')` yields `not_orchestrator_pointer`.

## Impact

The phase-transition mailbox check-point is a confident false negative for every orchestrated plan:
it reports "this plan has no epic and no mailbox" (a measured-fact probe value) when it never read
the provenance at all. It should be `unresolved` at worst. Mail delivered to a running plan is never
surfaced at phase transitions.

## Suggested fix

Read `source_id` through the same parser `manage-plan-documents request read` uses (the request
document schema), and add a regression test that transitions a plan whose request.md carries an
orchestrator pointer and asserts `probe != not_orchestrated`.
