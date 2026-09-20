# PLAN-PR-071: "Reviewed at all", and every number computed from it

epic: review-apparatus
workstream: WS-03

> **Component-cut spec, authored 2026-09-18.** This plan owns ONE component: `automatic-review` measurement — the reviewed-at-all handoff and `review_gate_delta.py`.
> ⛔ **Every deliverable body below lives in its ORIGINAL source spec and is NOT restated here** — the
> `Carried from` column names the theme spec this deliverable was cut out of, and that spec's own
> pointer names the retired spec holding the body. Follow the chain; do not retype.
>
> The theme specs `PLAN-PR-056` … `PLAN-PR-064` were retired on 2026-09-18 because their surfaces
> overlapped almost totally — `_findings_core.py` was declared by 7 of 9 — so no two could ever run
> concurrently. The cut is by component, so **no file is declared by two live plans**.

## Objective

Build the one handoff that says whether a diff was reviewed at all, persist it where a post-merge reader can see it, and make every ratio computed from it name the population it was computed over.

## Deliverables

| # | Deliverable | Body lives at | Carried from |
|---|---|---|---|
| D1 | Build the reviewed-at-all handoff, producer to consumer — **and persist it where a post-merge step can read it** | `PLAN-PR-026` § D1 **+** `PLAN-PR-047` § D0 | `PLAN-PR-061` D1 |
| D2 | Stop rendering an empty required population as a positive result | `PLAN-PR-026` § D3 | `PLAN-PR-061` D3 |
| D3 | The same collapse at the QUORUM layer, not just the per-bot layer | `PLAN-PR-026` § D3a | `PLAN-PR-061` D4 |
| D4 | Bound and de-glyph every operator-facing string these surfaces render | `PLAN-PR-026` § D4 | `PLAN-PR-061` D5 |
| D5 | Replace guards that cannot fail with guards derived from behaviour | `PLAN-PR-026` § D5 | `PLAN-PR-061` D6 |
| D6 | Model the reviewed tree per ROUND, not once per PR | `PLAN-PR-047` § D1 | `PLAN-PR-061` D8 |
| D7 | Anchor the delta's coverage denominator so a roster shrink cannot restore a share | `PLAN-PR-030` § D1 | `PLAN-PR-062` D1 |
| D8 | Make the escape set's population explicit, matched to its denominator | `PLAN-PR-030` § D2 | `PLAN-PR-062` D2 |
| D9 | Make the delta's published claims about itself true | `PLAN-PR-030` § D3 | `PLAN-PR-062` D3 |
| D10 | Pin both — **and the carve-out that cannot fire on the real record shape** (`raw_input.body` quarantine; the passing fixture is what hid it) | `PLAN-PR-037` §§ D3 + D3a | `PLAN-PR-063` D9 |


**D0 — GATE, mutates nothing.** `PLAN-PR-026` D0 verbatim in scope: derive the handoff's populations
and its persistence channel, or HALT. The derivation now also has to satisfy `PLAN-PR-047` D0's
post-merge reader, because the persisted classification is the same artifact.

*(Carried verbatim from `PLAN-PR-061` D0 at the 2026-09-18 component re-cut.)*

11 deliverables — within the guideline (12 nominal, ~14 when the aspects fit together, operator ruling 2026-09-15). ⛔ **Absorb nothing from another component**: the re-cut exists so this plan's surface stays disjoint.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_gate_delta.py`
- OBSERVED: `test/plan-marshall/automatic-review/test_review_gate_delta_cli.py`
- OBSERVED: `test/plan-marshall/automatic-review/test_review_gate_delta_escapes.py`
- OBSERVED: `test/plan-marshall/automatic-review/test_review_gate_delta_shares.py`
- OBSERVED: `test/plan-marshall/automatic-review/test_review_gate_delta_exclusions.py`
- OBSERVED: `test/plan-marshall/automatic-review/test_counting_rule_parity.py`

## Claim Labels

- OBSERVED (2026-09-18): every deliverable in this plan was carried verbatim from the theme spec named
  in its `Carried from` column, which carries the claim labels for its own deliverables. Confirm/refute
  by reading that spec's `## Claim Labels` section — this plan re-states none of them.
- OBSERVED (2026-09-18, orchestrator `corpus surfaces` + per-deliverable mapping): this plan's declared
  surface is disjoint from every other live plan's in this epic. Confirm/refute with
  `orchestrator corpus cross-check --slug review-apparatus`.
- OBSERVED (corpus pass 2026-09-15): 152 of 156 pr-agent guides in the window are the canned table and
  21 PRs had no baseline reviewer at all, 6 of them merged (`#1380`, `#1406`, `#1407`, `#1438`,
  API-Sheriff `#288`, `#300`) — their only posted review is a canned guide. These are D2/D3's fixtures.
- OBSERVED (corpus pass 2026-09-15): three distinct "nobody reviewed" shapes must stay apart from
  "reviewed clean" — never triggered (`cui-http#185`), re-review failed at token generation
  (`plan-marshall#1479`), and a run `queued` since 2026-09-13 (`34748813129`).

## Dependencies and Sequencing

- ⛔ **Runs AFTER `PLAN-PR-070`**: the handoff D1 builds carries the participation states 070 defines.
  Building the handoff first would publish a vocabulary its producer is about to change.
- ⛔ **D8 (escape-set population) runs AFTER `PLAN-PR-072` D4** (the new disposition member): a
  bucket added later silently changes what D8 counts as an escape.
- ⭐ D9 narrows `test_counting_rule_parity.py`, which pins the delegation D10 depends on — D9 before
  D10, inside this plan.
- ⚠ D4 edits operator-facing strings that `PLAN-PR-076` also renders. One file, two plans: sequence.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/review-apparatus/plans/PLAN-PR-071-reviewed-at-all-and-the-numbers.md"
```

## Write-Boundary

The plan implementing this spec writes to its own repository source only. It creates and edits NO file
under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
