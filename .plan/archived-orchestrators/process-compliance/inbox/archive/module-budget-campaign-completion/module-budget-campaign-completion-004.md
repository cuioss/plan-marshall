envelope_version=1
sender_type=plan
sender_id=module-budget-campaign-completion
epic=process-compliance
kind=finding
created=2026-09-24T07:39:31Z

envelope_version=1
sender_type=plan
sender_id=module-budget-campaign-completion
epic=process-compliance
kind=finding
created=2026-09-24T07:15:00Z

# Phase-transition mailbox probe never fires `probe: read` on a real request.md

At the `1-init → 2-refine` transition, `manage-status transition --completed 1-init`
returned `mailbox.probe: not_orchestrated` with
`reason: "request.md source_id is not an orchestrator plan-spec pointer
(detection=not_orchestrator_pointer)"` — for a plan whose `source_id` IS a valid
orchestrator pointer
(`.plan/orchestrator/test-quality/plans/PLAN-182-module-budget-campaign-completion.md`).

## Root cause

`_cmd_lifecycle.py` `_resolve_mailbox_checkpoint` extracts `source_id` from
`request.md` via `file_ops.parse_markdown_metadata`, which parses only
`key=value` lines that appear BEFORE the first blank line or markdown heading.

The real `request.md` (wriitten by `manage-plan-documents request create`) carries
its metadata as `plan_id: …` / `source: …` / `source_id: …` (COLON-separated)
BELOW an HTML template comment and the `# Request: …` heading. Verified by direct
invocation: the real template parses to `{}`; the test-seed shape
(`source_id=…\n\n# Request`) parses to the source_id.

Consequence: **every** plan initialized via the real template probes
`not_orchestrated` at every phase transition, so the phase-transition mailbox
check-point is inert for the exact plans it exists for. The test fixture
(`test_manage_status_transition.py::_seed_plan_with_provenance`) writes the
key=value shape, so the positive control passes against a shape production never
produces — test/production shape drift masking the defect.

## Evidence

- `python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator
  inbox detect --source-id ".plan/orchestrator/test-quality/plans/PLAN-182-…
  .md"` → `orchestrated: true`, `epic: test-quality`, `detection: orchestrated`.
- `parse_markdown_metadata(real_request_header)` → `{}`;
  `parse_markdown_metadata(test_seed_header)` → `{'source_id': …}`.
- Archived slice-1 plan root `request.md` shows the same real template shape, so
  this is a standing defect, not a run-specific observation.

## Suggested rule improvement (spans one seam)

Make the mailbox probe's extractor shape-faithful: read `source_id` from the real
template, e.g. reuse the headline-agnostic scanner already used elsewhere
(`_cmd_planning_lane._REQUEST_SOURCE_ID_RE` matches colon-formatted
`^source_id:` over the whole file, or `_cmd_sibling_collision`'s section reader),
or add a template-faithful fixture to `test_manage_status_transition.py` whose
request.md uses the real colon/heading shape so the positive control cannot pass
on a phantom key=value precedent.

## Disposition applied

Advisory only (`mailbox` is never a gate — `phase-lifecycle.md` branches on
`mailbox.probe` before any count and treats `not_orchestrated` as a measured
fact). The plan continues on the `not_orchestrated` branch exactly as the
contract prescribes. Filed for the owning epic to correct the probe and its
fixture.
