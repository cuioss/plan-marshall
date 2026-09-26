# PLAN-11: `corpus cross-check`'s sibling-epic enumeration double-counts a live epic against its own dated archive snapshot

> ✅ **RE-STAGED 2026-09-26 by explicit operator decision** — exempted from the PM-MCP supersession that parked
> the rest of this epic's queue the same day. Emittable. Its implementation-independent content is ALSO carried
> in `plan-marshall-mcp/doc/known-defects/orchestrator-refactor-carry-over.md` § PLAN-11 — the PM-MCP rule
> (an epic's own archive is never its sibling; indeterminacy is per candidate) stands regardless of this fix.

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
runs currently report `candidate_comparison_determinate: false` every pass, and this defect is
A cause of it, which means its `next` verb's disjointness admission test currently fails closed
on EVERY staged candidate, every round. **Overclaim corrected at cleanup 2026-09-24**: landing
this plan is not confirmed to fully clear that block — see D3's revised acceptance criterion.
The self-collision this plan fixes accounts for roughly half of the observed
`candidates_indeterminate` count on that epic; the remainder may have an independent cause this
plan does not address. Still worth landing regardless — it measurably shrinks the block and is
the only staged fix for its own mechanism — but "until this lands [it is fully unblocked]" is
too strong a claim to carry forward unverified.

## Objective

`orchestrator.py`'s `_sibling_epic_roots` (used by `corpus cross-check`'s duplication scan)
enumerates every OTHER epic directory under both `.plan/orchestrator/` and
`.plan/archived-orchestrators/`, deduped by exact directory NAME against the queried epic's own
`slug`. When an epic's archived snapshot carries a DATED suffix distinct from its live slug
(the `archive` verb's own pre-#1578 naming habit, e.g. `review-apparatus` live vs
`review-apparatus-26-09-21` archived) the name-equality dedup does not recognise the two as the
same epic, so the live epic's own corpus is enumerated a second time as a "sibling" and compared
against itself.

**Causal chain CORRECTED at cleanup 2026-09-24** — the original framing above ("collides on
every shared path, manufacturing thousands of false overlap rows and driving
`candidates_indeterminate`") conflated two different populations read from `orchestrator.py`
source (`_spec_candidate_state` :3946-3965, `cmd_corpus_cross_check` :4008 onward). A
`sibling_epic_spec` candidate is classified `CANDIDATE_INDETERMINATE`
(`candidate_tally`/`candidates_indeterminate`, :4151-4152) purely from ITS OWN
`derivation_status` being in `SURFACE_INDETERMINATE_STATES` — a per-candidate property,
independent of whether it collides with anything. A candidate that IS comparable and DOES
collide contributes to `file_overlap_matches` instead, a separate count. So the true mechanism
is: the self-collision duplicates the WHOLE candidate population (both comparable and
indeterminate specs) once per affected epic, and since roughly half of `review-apparatus`'s own
corpus apparently has a non-declarative Expected Surface, doubling that population via the
duplicate `review-apparatus-26-09-21` sibling is what produces the observed
`sibling_epic_spec indeterminate: 94` — not "false overlap rows" manufacturing indeterminacy.
Practical consequence for D3: excluding the duplicate removes roughly HALF of
`candidates_indeterminate`'s current sibling-side contribution, not necessarily all of it — see
D3's revised acceptance criterion.

## Deliverables

1. **D0 — GATE: derive the affected population first-party, do not carry the figure 4 forward
   as given.** Re-run the derivation this spec's Claim Labels record and publish the current
   count and the exact slugs, since the live/archived directory listing can change between
   staging and outline.
2. **D1 — recognise a live epic's own dated archive snapshot in `_sibling_epic_roots`, and
   exclude it from the sibling-candidate population. Discriminator SETTLED at cleanup
   2026-09-24: string-prefix / date-suffix, not an identity-field read.** The original framing
   ("read the archived directory's own `status.json` epic identity and compare it against the
   queried epic's own identity") is now established as unreliable, not merely deferred: a
   direct read of `.plan/archived-orchestrators/review-apparatus-26-09-21/status.json`'s
   `title` (`"Review Apparatus — archived 2026-09-21"`) against the LIVE
   `.plan/orchestrator/review-apparatus/status.json`'s `title`
   (`"Automated PR review apparatus reliability"`) shows the two share no substring — `title`
   diverges freely between an epic's live and archived self and is not comparable, and no
   other identity field (slug, epic id) exists in either `status.json`. Per this deliverable's
   own licensed fallback clause, the chosen discriminator is therefore the string-prefix /
   date-suffix heuristic: recognise an archived directory name of the form
   `{live_slug}-{YY-MM-DD}` against a live directory named `{live_slug}` under
   `.plan/orchestrator/`, matching the `archive` verb's own current naming convention. Record
   in the implementing plan that this IS the licensed fallback (identity-based read confirmed
   unreliable, not merely unavailable) — the naming-convention fragility this D1 originally
   worried about is accepted as the exclusion mechanism's known limitation, not solved.
3. **D2 — a regression test pinning the exact defect**: an epic with BOTH a live directory and
   a dated-suffix archived directory of its own corpus must NOT appear as a sibling candidate
   against itself, with a matched negative control (a genuinely distinct sibling epic still
   IS enumerated and compared).
4. **D3 — verify `candidates_indeterminate` measurably drops on the real corpus; do not assume
   it reaches zero.** Per the Objective's corrected causal chain, D1 removes the SELF-COLLISION
   contribution to `candidates_indeterminate` (roughly half of `review-apparatus`'s current
   `sibling_epic_spec indeterminate: 94`, since that count doubles a population that is itself
   already partly non-comparable) — it does NOT touch whatever indeterminate candidates exist
   for reasons unrelated to this defect (an epic's own specs with a genuinely non-declarative
   Expected Surface, unreadable siblings, etc.). After the fix, `corpus cross-check --slug
   review-apparatus` must report a candidate count and `candidate_comparison_determinate`
   verdict CONSISTENT with only the self-collision contribution being removed — `true` is the
   best case, not the required one; a remaining `false` is acceptable ONLY if the remaining
   `candidates_indeterminate` count is accounted for by candidates this plan never claimed to
   fix (named individually, not waved past). This is the acceptance criterion the defect was
   actually blocking, calibrated to what D1 can actually deliver, not the unit-level fix alone.

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
  - verdict: contradicted | checked_at: 9588b30b317d0312ede90f1982122aa3145ea871 | by: orchestrator-refactor/cleanup | rescoped: yes | evidence: First verdict; refuted by direct read. .plan/archived-orchestrators/review-apparatus-26-09-21/status.json's title is 'Review Apparatus — archived 2026-09-21', while the LIVE .plan/orchestrator/review-apparatus/status.json's title is 'Automated PR review apparatus reliability' -- the two titles share no substring, so title is NOT a usable identity-based discriminator: it can diverge freely between an epic's live and archived self, and a live/archived comparison keyed on it would produce false negatives (failing to recognise a genuine self-collision) as readily as it fixes false positives. No other identity field (slug, epic id) exists in status.json at either location. Per this deliverable's own licensed fallback clause, this establishes that an identity-based read is unreliable, so D1's discriminator should be the string-prefix/date-suffix heuristic (matching the archive verb's own {slug}-{YY-MM-DD} naming convention) with that unreliability finding recorded in the plan, not a status.json field read.

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
- Partially unblocks (cross-epic, not this plan's to touch): `review-apparatus`'s `next` verb,
  whose disjointness admission test fails closed on `candidate_comparison_determinate: false`
  for every staged candidate today. This plan removes the self-collision's contribution to that
  count but is not confirmed to clear it entirely — see D3. Recorded here so the urgency is
  visible; this plan does not edit `review-apparatus`'s ledger.

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
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
