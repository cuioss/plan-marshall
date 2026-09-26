# PLAN-TRUTH-174: plan-retrospective measurement integrity — an ungated comparison state

> ⛔⛔ **SUPERSEDED BY PM-MCP (2026-09-26, operator decision; row status `parked`).** `plan-marshall-mcp` replaces both the
> process prose and the Python scripts this plan edits, so implementing it here is legacy work. Its
> implementation-independent content (rules, invariants, classifications, data, fixtures) was extracted to
> `plan-marshall-mcp/doc/known-defects/truthful-signals-carry-over.md` as PM-MCP input.
> **Do NOT emit; un-park only by explicit operator decision.** The spec body below stays intact as the evidence chain.

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.

## Objective

⛔ **Re-scoped 2026-09-21 at cleanup A1 re-grounding.** The original D1 (a lossy
`parse_toon` re-parse of `reduced_transcript` in `extract-chat-signal.py`) is
ALREADY FIXED at HEAD `74153664d`: line 186 now routes the value through
`_delivered_transcript()` (line 66), which returns a `BlockScalar` and publishes a
conservation measurement (`reduced_transcript_delivered_bytes`, line 175) beside the
forwarded `reduced_bytes` — the cited source lines 92/145/162/165 no longer
correspond to anything. One narrower residual survives and is now the plan's sole
deliverable: `parse_toon(result.stdout)` (still at line 128) is the INGESTION hop
from the runtime, a separate, unverified step the emission-side fix did not touch.

Fix the one remaining measurement-integrity defect in
`plan-marshall:plan-retrospective` surfaced by PLAN-TRUTH-143's own retrospective
run: the `outline-vs-shipped` aspect reports `comparison: measured` when the
assessment corpus (not the footprint) is entirely absent, so two of its three
outcome classes report a confident zero over nothing.

## Deliverables

1. Confirm whether `parse_toon(result.stdout)` at `extract-chat-signal.py:128` (the
   runtime-to-consumer ingestion hop, upstream of the already-fixed emission path)
   still loses a multi-line value — `parse_toon` not round-tripping embedded
   newlines was the ORIGINAL root cause, and only the emission side has a confirmed
   fix. If it still round-trips lossily, apply the same remedy the emission side
   already uses (route through a `BlockScalar` or an out-of-band file handoff) with
   a conservation assertion at the ingestion boundary; if it turns out already fixed
   too, close this deliverable with a positive account (commit/symbol) rather than
   re-deriving the original finding.
2. Make the `outline-vs-shipped` aspect's `comparison` field three-state over BOTH
   inputs: `measured` requires a resolved footprint AND `assessments_store_present:
   true` with `assessments_read > 0`; an absent/empty assessment store yields a new
   `comparison: no_assessments` state (distinct from the existing `inconclusive`,
   which stays reserved for the unresolvable-footprint case) and withholds
   `include_unrealised` / `exclude_violated` exactly as the footprint guard already
   withholds them. `touched_but_unassessed` continues to report in that state — it
   needs only the footprint.

## Claim Labels

- OBSERVED: `extract-chat-signal.py:128` still calls `parse_toon(result.stdout)` at
  HEAD `74153664d` (the emission-side fix at line 186 did not touch this ingestion
  call) — read at outline whether this specific call still loses a multi-line value,
  since `parse_toon`'s general round-trip behaviour is what the now-fixed emission
  side worked around rather than repaired at the source.
  - verdict: contradicted | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: yes | evidence: FIXED AT HEAD. extract-chat-signal.py no longer forwards reduced_transcript verbatim - line 186 routes it through _delivered_transcript() (line 66), returning a BlockScalar with a conservation measurement published beside reduced_bytes. Spec re-scoped in place: D1 now targets the untouched parse_toon ingestion call at line 128.
- OBSERVED: the `outline-vs-shipped` aspect's existing footprint guard yields
  `comparison: inconclusive` with counts withheld on an unresolvable footprint, but no
  equivalent guard exists on the assessment-store side, so `assessments_store_present:
  false` / `assessments_read: 0` still takes the `measured` branch — read from
  PLAN-TRUTH-143's retrospective finding against `plan-retrospective`'s
  outline-vs-shipped aspect implementation
  - verdict: corroborated | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: n/a | evidence: check-outline-vs-shipped.py declares only TWO comparison states (constants at lines 90-94); inconclusive is set on ONE condition - an unresolvable footprint - and the else-branch sets measured with assessments_store_present/assessments_read merely REPORTED, gating nothing. Exactly as claimed.
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
