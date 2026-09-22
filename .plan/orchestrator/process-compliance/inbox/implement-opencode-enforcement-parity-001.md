envelope_version=1
sender_type=plan
sender_id=implement-opencode-enforcement-parity
epic=process-compliance
kind=finding
created=2026-09-22T19:33:35Z

# Finding: phase-transition mailbox probe mis-parses real request.md, always reporting `not_orchestrator_pointer`

## Reported

- Plan: `implement-opencode-enforcement-parity` (PLAN-15), transition `1-init -> 2-refine`
- Location: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_lifecycle.py:174`
- Encounter: transition success payload carried `mailbox.probe: not_orchestrated` with
  `reason: request.md source_id is not an orchestrator plan-spec pointer (detection=not_orchestrator_pointer)`,
  even though the plan's `source_id` IS the canonical orchestrator pointer
  `.plan/orchestrator/process-compliance/plans/PLAN-15-opencode-enforcement-parity.md`.

## Observed disposition

Correct disposition for this plan: `orchestrated` (epic `process-compliance`). Direct test of the
`_SOURCE_ID_RE` regex against the recorded pointer classifies it `orchestrated`. The probe's
`not_orchestrator_pointer` verdict therefore contradicts the provenance the plan actually carries.

## Root cause

`_resolve_mailbox_checkpoint` reads `source_id` from request.md with
`parse_markdown_metadata` (`tools-file-ops/scripts/file_ops.py:1554`), which parses ONLY
`key=value` lines at the top of the file and STOPS at the first blank line or `#` heading.

The production request.md shape (written by `request create` from
`manage-plan-documents/templates/request.md`) is:

```text
<!-- Script template used by _cmd_request.py (plan_id available at creation time).
     phase-1-init has a separate LLM instruction template without plan_id (derived at runtime). -->
# Request: {title}

plan_id: {plan_id}
source: {source}
source_id: {source_id}
created: {timestamp}
```

`parse_markdown_metadata` breaks on the `# Request:` heading (line 3) before any metadata line,
and never matches the colon-separated `key: value` fields. It returns `{}` for every real
request.md, so `source_id` reads as `''`, and `classify_source_id('')` yields
`not_orchestrator_pointer`. The probe reports `not_orchestrated` for EVERY colon-format
request.md, orchestrated or not.

## Divergence evidence (three readers of the same field)

- `manage-status` mailbox probe (`_cmd_lifecycle.py:174`): `parse_markdown_metadata` — key=value,
  breaks at heading — MIS-PARSES the production colon format.
- `manage-status` sibling-collision reader (`_cmd_sibling_collision.py:93`):
  `parse_document_sections` — colon-aware — resolves `source_id` correctly.
- `manage-status` planning-lane S1 bridge (`_cmd_planning_lane.py:427`):
  `_REQUEST_SOURCE_ID_RE = ^source_id:\s*(\S+)\s*$` — colon-aware — resolves correctly.

So the other two readers agree with the provenance; only the mailbox probe diverges, and it does
so uniformly.

## Test-shape divergence

`test/plan-marshall/manage-status/test_manage_status_transition.py` seeds request.md in
`key=value` form (`source=orchestrator\nsource_id={source_id}\n\n# Request\n\n...`), which is the
ONLY form `parse_markdown_metadata` can parse. The unit tests therefore never exercise the
format the writer actually produces, letting the divergence pass green while every real
transition payload mis-classifies.

## Impact

- The `mailbox` block is additive and never a gate, so no transition is refused — consistent with
  its design. The defect is that the published verdict is a FALSE measurement, not a refusal.
- Consumers that read `mailbox.probe == not_orchestrated` (e.g. phase-6-finalize's
  orchestration-context handling, which keys off the same `classify_source_id` seam) will treat an
  orchestrated plan as non-orchestrated when they rely on this probe path. phase-6-finalize
  resolves its verdict through `inbox detect --source-id` against the recorded pointer, so it is
  not affected today; the transition payload itself is the false-negative surface.

## Suggested fix direction

- In `_resolve_mailbox_checkpoint`, resolve `source_id` colon-aware (match `_cmd_sibling_collision`
  / `_cmd_planning_lane`), or read via the canonical `request read --section source_id` verb; and
  add/update the transition tests to seed request.md in the production colon-template shape.
