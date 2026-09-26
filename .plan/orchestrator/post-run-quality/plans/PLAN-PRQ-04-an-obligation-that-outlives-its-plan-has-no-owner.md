# PLAN-PRQ-04: An obligation that outlives its plan has no owner

> ⛔⛔ **SUPERSEDED BY PM-MCP (2026-09-26, operator decision; row status `parked`).** `plan-marshall-mcp` replaces both the
> process prose and the Python scripts this plan edits, so implementing it here is legacy work. Its
> implementation-independent content (rules, invariants, classifications, data, fixtures) was extracted to
> `plan-marshall-mcp/doc/known-defects/post-run-quality-carry-over.md` as PM-MCP input.
> **Do NOT emit; un-park only by explicit operator decision.** The spec body below stays intact as the evidence chain.

epic: post-run-quality
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.

## Provenance

Staged 2026-09-17 at epic creation from three independent observations: two standing Open Defects in the
`truthful-signals` ledger (D-087-e, D-087-f), and one first-party configuration read by this orchestrator
on 2026-09-17 while assembling this epic.

## Objective

**A finalize run routinely ends owing something, and the plan that owes it is archived minutes later.**
Today an owed item survives only as prose written by whoever noticed: an unissued `architecture enrich
insight` hint against a git-TRACKED file is a lost repository change once its owning plan is archived, and
a deferred `marshalld` reconcile sits at `owed: true` with nothing re-checking it. Neither is reachable
from any machine-readable surface, so no drain, audit or roll-up can ask *what is still outstanding?*

⛔ **A third observation was staged here at epic creation and has since been ANALYZED OUT of this spec.**
The `lane: "off"`-but-`done` contradiction is now `PLAN-PRQ-06`, and both readings this spec originally
carried were REFUTED: the immunity is contractual and the landing told the truth. Nothing about that
finding is this plan's any more — it is named here only so a reader of the original framing is not left
following a premise that no longer holds.

⛔ **RE-GROUNDED 2026-09-18 (cleanup, `checked_at: 1605831c5`).** `D-087-e` (the four unissued
`architecture enrich insight` calls) is **DISCHARGED** — `truthful-signals` epic.md:2202 records it
resolved 2026-08-25 via PR #1347: `enriched.json` on `main` now carries 6 insights, was 2. The Objective's
flagship worked example is closed; only the STRUCTURAL point survives as the durable half — the target is
a tracked file, so an unissued hint is a lost repository change, whichever plan next demonstrates it.
`D-087-f` (the deferred `marshalld` reconcile) still stands, unowned. A third item in the same
`truthful-signals` block, `D-087-g` ("no metric or step record captures a stall"), was previously unnamed
here and is now folded into D0's population as a fourth known kind.

⛔ **Folded 2026-09-22 from inbox `lessons-handling-26-09-22-01-001.md`, `2026-09-21-13-005`.** A fifth
known kind for D0's population: "Owed architecture hints: preference-emitter, plan
lessons-corpus-producers-report-success" — filed the same way D-087-e/-f/-g were, and split out at its
source specifically because it is this spec's own pattern ("the obligation a finished plan left behind has
no owner once archived"). No new file/module surface — the preference-emitter hint route is already the
`architecture enrich insight` mechanism D-087-e's discharge covers structurally.

## Deliverables

Four deliverables. D0 is a gate.

**D0 — GATE: derive the owed-item population.** Every post-run obligation kind a run can end with — at
minimum the four now known (deferred reconcile / `D-087-f`; unissued architecture hint / `D-087-e`, its
worked example closed but the kind still real; unrecorded stall, `D-087-g`; **plus two more found at
re-grounding**: an owed PR-body note that cannot be written before `create-pr` runs
(`architecture-refresh.md:349-352, 436-438`), and an owed source edit with no persisted "fix is owed"
record (`source-edit-pushability.md:73, 91-93, 104, 171`) — and a confirmed-live hint kind at three sites
(`lessons-capture.md:119, 125-127`; `finalize-step-preference-emitter.md:26, 154-180`;
`disposition-to-hint-routing.md:57-105`) — and how each is recorded today. ⛔ Publish the population and
its size — six known kinds now, each found independently, which is the under-derived-population archetype
this D0 exists to close; do not treat six as final.

**D1 — An owed item is a typed fact, not prose.** One record shape, written by the step that incurs the
obligation, carrying what is owed, who may discharge it, and what proves it discharged. The landing
payload already carries `cleanup_owed` — extend that pattern rather than inventing a parallel one.

**D2 — An obligation survives its plan's archival.** The record is readable after the plan directory
moves to `archived-plans/`, and an orchestrator drain can enumerate what is outstanding without reading
prose. The architecture-store obligation is the worked example: it is a lost repository change, not local
bookkeeping. ⛔ This plan records and reports; it does not mutate the architecture store.

**D3 — Controls.** A discharged obligation reports discharged; an undischarged one survives archival and
is enumerable by an orchestrator drain; and the matched negative — a run that owes nothing publishes an
empty owed set that is distinguishable from a run that was never asked.

## Claim Labels

- OBSERVED: `truthful-signals` epic.md records four unissued `architecture enrich insight` calls whose
  owning plan is archived, against a tracked file, with the verdict "the obligation has no owner"
  (D-087-e), and a deferred daemon reconcile at `owed: true`, `defer_count: 1`, marked UNOWNED (D-087-f).
  - verdict: contradicted | checked_at: 7d82d5d90 | by: post-run-quality/cleanup | rescoped: yes | evidence: truthful-signals epic.md:2143-2149 (moved from :2202 by the 7d82d5d90 restructure): D-087-e DISCHARGED via PR #1347, enriched.json on main carries 6 insights (ground-truth verified). D-087-f still unowned (:2160-2162), D-087-g also live (:2164-2166). Rescoped: Objective/D0 already absorb the discharge and fold D-087-g in
- ⚠ HYPOTHESIS: the landing payload's `cleanup_owed` is the right pattern to extend rather than a
  special case — confirm/refute at `plan-orchestrator/standards/landing-payload-spec.md` (verify-at-outline).
  - verdict: corroborated | checked_at: 7d82d5d90 | by: post-run-quality/cleanup | rescoped: n/a | evidence: landing-payload-spec.md:43,95,109,121,128 cleanup_owed four-state contract intact (citation drift from prior :200-207 corrected); emit-landing.md/branch-cleanup.md producer sites and test coverage confirmed. D1 premise holds
- ⚠ HYPOTHESIS: the owed-item kinds above are the whole population. ⛔ Three kinds found by three separate
  accidents is the under-derived-population archetype; D0 owns it (verify-at-outline).
  - verdict: contradicted | checked_at: 7d82d5d90 | by: post-run-quality/cleanup | rescoped: yes | evidence: population is >=6 kinds not the smaller set claimed: architecture-refresh.md:349-352 (owed PR-body note), source-edit-pushability.md:73,91-93 (owed source edit), finalize-step-preference-emitter.md:26,154-181, disposition-to-hint-routing.md:57-105, lessons-capture.md:136,144-149,235-243 (citation drift corrected from :119/:125-127). Rescoped: D0 already owns the derivation and publishes six kinds, do-not-treat-six-as-final

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/landing-payload-spec.md` — the owed-item fact keys (D1, D2)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/**` — the steps that incur an obligation and write the record (D1) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-status/**` — where an owed record persists across archival (D2) (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/phase-6-finalize/**` — D3's controls (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none.
- ⛔ Declares `phase-6-finalize/**`, which `truthful-signals` `-145`, `-147` and `-158` also declare, and
  which `PLAN-PRQ-06` declares too. **The cross-epic half is invisible to both gates.** Check
  `manage-status list` and that epic's queue before launching.
- The `lane: "off"` finding that was staged here at epic creation is now `PLAN-PRQ-06`; the two share
  `phase-6-finalize/**` and must not be paired.
- ⚠ The reviewer-state seam (`review_completeness`'s `bot_states` has no persisted handoff an `order: 990`
  step can read, so `finalize-step-review-retrospective`'s zero-findings grade fails closed to
  `indeterminate`) is NAMED here as an instance of the same missing-carrier shape. ⛔ The producer-side fix
  is `review-apparatus`'s by the standing PR-review routing rule — this plan does not make it.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/post-run-quality/plans/PLAN-PRQ-04-an-obligation-that-outlives-its-plan-has-no-owner.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
