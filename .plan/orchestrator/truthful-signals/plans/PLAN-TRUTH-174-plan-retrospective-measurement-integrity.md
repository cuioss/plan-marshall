# PLAN-TRUTH-174: plan-retrospective measurement integrity — a lossy TOON hop and an ungated comparison state

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.

## Objective

Fix two independent measurement-integrity defects in `plan-marshall:plan-retrospective`
surfaced by PLAN-TRUTH-143's own retrospective run: `extract-chat-signal` silently
truncates the transcript it forwards while reporting the runtime's full size as if it
were what was delivered, and the `outline-vs-shipped` aspect reports `comparison:
measured` when the assessment corpus (not the footprint) is entirely absent, so two
of its three outcome classes report a confident zero over nothing.

## Deliverables

1. Stop routing `reduced_transcript` through a `parse_toon` re-parse in
   `extract-chat-signal.py` (a multi-line value does not round-trip): either have the
   runtime operation write the reduction to a file and return its path, or give
   `parse_toon`/`serialize_toon` a tested multi-line round-trip with a fixture
   containing embedded newlines. Add a conservation assertion
   (`len(reduced_transcript.encode()) == reduced_bytes`) or publish
   `reduced_bytes_reported` / `reduced_bytes_delivered` side by side.
2. Make the `outline-vs-shipped` aspect's `comparison` field three-state over BOTH
   inputs: `measured` requires a resolved footprint AND `assessments_store_present:
   true` with `assessments_read > 0`; an absent/empty assessment store yields a new
   `comparison: no_assessments` state (distinct from the existing `inconclusive`,
   which stays reserved for the unresolvable-footprint case) and withholds
   `include_unrealised` / `exclude_violated` exactly as the footprint guard already
   withholds them. `touched_but_unassessed` continues to report in that state — it
   needs only the footprint.

## Claim Labels

- OBSERVED: `extract-chat-signal.py` re-parses the runtime's TOON output with
  `parse_toon(result.stdout)` and forwards `record.get('reduced_transcript', '')`
  verbatim, losing everything past the first line of a multi-line value — read from
  PLAN-TRUTH-143's retrospective finding (source lines 92, 145, 162, 165 named in the
  finding) at `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/extract-chat-signal.py`
- OBSERVED: the `outline-vs-shipped` aspect's existing footprint guard yields
  `comparison: inconclusive` with counts withheld on an unresolvable footprint, but no
  equivalent guard exists on the assessment-store side, so `assessments_store_present:
  false` / `assessments_read: 0` still takes the `measured` branch — read from
  PLAN-TRUTH-143's retrospective finding against `plan-retrospective`'s
  outline-vs-shipped aspect implementation
- Verify-first clause: confirm the exact line numbers and current behaviour of both
  sites against HEAD at outline before scoping the fix — the retrospective finding is
  first-party but was not independently re-read by the orchestrator before staging.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/extract-chat-signal.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/ref-toon-format/scripts/toon_parser.py`
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/` — `outline-vs-shipped aspect module` (verify-at-outline: exact filename for the outline-vs-shipped aspect was not named in the source finding)
- OBSERVED: `test/plan-marshall/plan-retrospective/**`

## Dependencies and Sequencing

- Depends on: none
- Overlaps with: none known
- Adjacent to: PLAN-TRUTH-175 (dispatch/phase-boundary measurement integrity) — different
  component surface (plan-retrospective vs manage-metrics/phase-6-finalize/manage-change-ledger),
  no file overlap expected

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/truthful-signals/plans/PLAN-TRUTH-174-plan-retrospective-measurement-integrity.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message.
