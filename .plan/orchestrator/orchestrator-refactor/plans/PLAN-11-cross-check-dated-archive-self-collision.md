# PLAN-11: `corpus cross-check`'s sibling-epic enumeration double-counts a live epic against its own dated archive snapshot

epic: orchestrator-refactor
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-11-cross-check-dated-archive-self-collision.md` and is queued in the epic
> `status.json` `plans[]` field. The orchestrator EMITS the command below; it never launches
> the plan inline. This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer
> and carries no brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Provenance

Routed from `review-apparatus`, first observed and recorded as a "tool defect, not a corpus
defect" in that epic's 2026-09-22 A1 re-grounding pass, carried unescalated across two further
cleanup/next passes (2026-09-22, 2026-09-23), and staged here on the third at operator
instruction rather than deferred a fourth time. `review-apparatus`'s own `corpus cross-check`
runs currently report `candidate_comparison_determinate: false` every pass because of this
defect, which means its `next` verb's disjointness admission test fails closed on EVERY staged
candidate, every round, until this lands — not a one-epic nuisance, a structural block on that
epic's ability to emit anything under the documented admission rule.

## Objective

`orchestrator.py`'s `_sibling_epic_roots` (used by `corpus cross-check`'s duplication scan)
enumerates every OTHER epic directory under both `.plan/orchestrator/` and
`.plan/archived-orchestrators/`, deduped by exact directory NAME against the queried epic's own
`slug`. When an epic's archived snapshot carries a DATED suffix distinct from its live slug
(the `archive` verb's own pre-#1578 naming habit, e.g. `review-apparatus` live vs
`review-apparatus-26-09-21` archived) the name-equality dedup does not recognise the two as the
same epic, so the live epic's own corpus is enumerated a second time as a "sibling" and compared
against itself — every one of its own specs collides with its own earlier-snapshot self on every
shared path, manufacturing thousands of false `sibling_epic_spec` overlap rows and driving
`candidates_indeterminate` (and therefore `candidate_comparison_determinate: false`) on every
run that has such a snapshot.

## Deliverables

1. **D0 — GATE: derive the affected population first-party, do not carry the figure 4 forward
   as given.** Re-run the derivation this spec's Claim Labels record and publish the current
   count and the exact slugs, since the live/archived directory listing can change between
   staging and outline.
2. **D1 — recognise a live epic's own dated archive snapshot in `_sibling_epic_roots`, and
   exclude it from the sibling-candidate population.** The discriminator is NOT a fixed date
   suffix pattern to strip and re-compare (fragile, and the naming convention may not be
   `{slug}-{YY-MM-DD}` forever) — read the archived directory's own `status.json` epic
   identity (or an equivalent stable marker) and compare it against the queried epic's own
   identity, so the exclusion holds regardless of naming convention. State and justify the
   chosen discriminator; a string-prefix heuristic is licensed only if the identity-based read
   is established as unavailable or unreliable, with that finding recorded.
3. **D2 — a regression test pinning the exact defect**: an epic with BOTH a live directory and
   a dated-suffix archived directory of its own corpus must NOT appear as a sibling candidate
   against itself, with a matched negative control (a genuinely distinct sibling epic still
   IS enumerated and compared).
4. **D3 — verify `candidate_comparison_determinate` recovers on the real corpus.** After the
   fix, `corpus cross-check --slug review-apparatus` must report `candidate_comparison_determinate: true`
   (or name a DIFFERENT, unrelated cause for any remaining indeterminate candidate) — this is
   the acceptance criterion the defect was actually blocking, not merely the unit-level fix.

## Non-Goals

- No change to how `archive` NAMES a relocated epic tree (whether it should stop using a dated
  suffix at all is a separate, larger question this plan does not decide).
- No change to `corpus cross-check`'s live-plan or corpus-spec candidate kinds — only the
  `sibling_epic_spec` enumeration.

## Claim Labels

- OBSERVED: `_sibling_epic_roots` (`marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py:3736-3752`)
  dedupes sibling candidates by `child.name != slug and child.name not in roots` while walking
  both `.plan/orchestrator/` and `.plan/archived-orchestrators/` (`_epic_store_roots()`).
- OBSERVED: at HEAD `14d8f3ccd`, `.plan/archived-orchestrators/` contains four dated snapshots
  whose slug is `{live_slug}-26-09-21` for a slug that ALSO exists live under
  `.plan/orchestrator/`: `code-intelligence-substrate-26-09-21`, `review-apparatus-26-09-21`,
  `test-quality-26-09-21`, `truthful-signals-26-09-21` — 4 of the 9 currently-live epics are
  affected. Verified by directory listing, not inferred.
- OBSERVED: `review-apparatus`'s `corpus cross-check` at the same HEAD reports
  `candidates_indeterminate: 96` of which `sibling_epic_spec indeterminate: 94`, and
  `candidate_comparison_determinate: false` — the exact symptom this defect predicts, on the
  exact epic whose own dated snapshot exists.
- HYPOTHESIS: the archived directory's own `status.json` carries an identity field (or the
  epic's `title`) stable enough to compare against the live epic's identity for D1's
  discriminator — confirm/refute by reading `.plan/archived-orchestrators/review-apparatus-26-09-21/status.json`
  at outline (verify-at-outline).

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py`
  — `_sibling_epic_roots` and its caller `cmd_corpus_cross_check`.
- HYPOTHESIS: `test/plan-marshall/plan-orchestrator/test_orchestrator_corpus.py` — where the
  cross-check candidate-enumeration tests already live (verify-at-outline; a new test module is
  also acceptable if the existing one is component-scoped elsewhere).

## Dependencies and Sequencing

- Depends on: none in-epic.
- Overlaps with: none declared against this epic's other staged specs (single-file surface,
  `orchestrator.py`'s own candidate-enumeration function).
- Unblocks (cross-epic, not this plan's to touch): `review-apparatus`'s `next` verb, whose
  disjointness admission test fails closed on `candidate_comparison_determinate: false` for
  every staged candidate until this lands. Recorded here so the urgency is visible; this plan
  does not edit `review-apparatus`'s ledger.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/orchestrator-refactor/plans/PLAN-11-cross-check-dated-archive-self-collision.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
