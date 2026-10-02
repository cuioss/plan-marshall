# PLAN-PRQ-05: Lessons-corpus provenance and quality measurement

> ⛔⛔ **SUPERSEDED BY PM-MCP (2026-09-26, operator decision; row status `parked`).** `plan-marshall-mcp` replaces both the
> process prose and the Python scripts this plan edits, so implementing it here is legacy work. Its
> implementation-independent content (rules, invariants, classifications, data, fixtures) was extracted to
> `plan-marshall-mcp/doc/known-defects/post-run-quality-carry-over.md` as PM-MCP input.
> **Do NOT emit; un-park only by explicit operator decision.** The spec body below stays intact as the evidence chain.

epic: post-run-quality
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.

## Provenance

**TRANSFERRED 2026-09-17 from `next-level` PLAN-09** (staged there 2026-09-14 from inbox `next-level-009`
with `next-level-010` folded in). The source spec stays on disk in that epic as the audit record and is
the authority for every carried claim:
`.plan/local/orchestrator/next-level/plans/PLAN-09-lessons-corpus-provenance-and-quality.md`.

The source row is retired in `next-level` with a pointer here. ⛔ `parked` rather than `transferred`,
for the mechanical reason in this epic's `## Decisions`.

⭐ **Why it moved.** `next-level` owns "the substrate that steers the agent, and whether anything measures
it"; this epic owns what the project does with a run once it is over, which is where lessons come from and
where they must land. The corpus is the learning half of post-run quality, so the instrument and its
consumer now sit in one ledger.

## Objective

**The lessons corpus is a live part of the substrate that steers every session, and nothing measures it.**
A lesson is `live` or retired with no position between: no confidence that moves, no freshness term, no
provenance record, and no number anywhere saying what share of the corpus is accurate, relevant, or
load-bearing. Give it a measurement and the minimum mechanism that measurement implies.

⭐ **The outcome metric this epic adds to the source objective**: `doc/analyzis-cloud-plan/test-quality.adoc:738-755`
measured that **1 of 5** recorded process lessons reached the governing contract. A corpus that is accurate
but never reaches a contract is a cost with no yield, so precision alone does not close this plan.

⛔⛔ **CORPUS SIZE HAS MOVED ~5× SINCE STAGING AND MUST NOT BE TRUSTED FROM THIS DOCUMENT (corrected
2026-09-21, cleanup, `checked_at: e8a71650`).** Every population figure below (131 active files, 729
tombstones, "6 of 194", "23 of 194") was measured at staging (2026-09-17/18) or at the first cleanup pass
(2026-09-18). At `e8a71650` the live corpus is a different size again (observed 4-24 active files across
several checks this session, 862 tombstones) — it has been legitimately drained multiple times since
staging by activity outside this epic's control (see the epic's Decisions log). ⛔ **D0/D1 MUST re-derive
the live population count as their first act, from `manage-lessons list --status all` at launch time, and
must not carry forward any count printed in this spec.** Every figure below is a HISTORICAL reading, kept
as evidence of the archetype (a corpus whose size nobody tracks), not as a current fact.

## Deliverables

Five deliverables — the source's four, carried in substance, plus the reach measurement this epic owns.

1. **D1 — A precision measurement of the corpus against an enumerated golden set**: of the lessons that
   exist, what share are accurate and still relevant. Scored against a derived population and publishing
   it, per this repository's own discipline.
2. **D0 — GATE: a sized estimate of the golden set's construction cost, published BEFORE any labelling
   begins.** ⛔ Non-negotiable, and it precedes D1. A golden set is human labour, and this project has
   already recorded what happens when a verification layer's cost is not bounded at design time.
3. **D2 — A provenance field per lesson recording where it came from** — enough to tell a lesson derived
   from a run artifact or tool return from one derived from a settled operator decision.
4. **D3 — A decision on the two absent mechanisms: adopt, defer with a stated reason, or refute.**
   (a) **A confidence that moves** — raised by corroboration, lowered by age and contradiction, with
   pruning on decay, never-corroborated low confidence, or irrelevance. (b) **Regeneration instead of
   trimming** — trimming edits a conclusion in place while leaving its unstated derivation intact, which
   is how a lesson ends up asserting what its surviving sources no longer support.
5. **D4 — The reach measurement: what share of filed lessons reach the contract they govern.** Derive it
   over the corpus rather than sampling; publish the population. This is the epic-level outcome metric,
   and the `1 of 5` figure above is its only prior reading — a lead to re-derive, not a baseline to trust.

## Claim Labels

⛔ Claims 1–4 are carried from the source spec and are re-derivable from its own `## Claim Labels` section
at the path in `## Provenance`. Re-ground each at HEAD before scoping.

- OBSERVED: `manage-lessons` carries no confidence, freshness, decay or precision model — a targeted sweep
  of its SKILL.md for `confidence|freshness|decay|precision` returned exactly one hit, belonging to an
  unrelated recipe-registry matcher (measured 2026-09-14; re-verify at outline).
  - verdict: corroborated | checked_at: 7d82d5d90 | by: post-run-quality/cleanup | rescoped: n/a | evidence: manage-lessons/SKILL.md metadata schema (id,component,category,created,bundle,rule,recurrence_count,last_seen) carries no confidence/freshness/decay/precision term; live corpus rows carry id/component/category/status/title only
- OBSERVED: the store's lifecycle is binary — live or retired via tombstones — with no intermediate
  confidence position (source spec, read at `manage-lessons/SKILL.md`).
  - verdict: corroborated | checked_at: 7d82d5d90 | by: post-run-quality/cleanup | rescoped: n/a | evidence: SKILL.md:343 status is active|superseded|removed|all -- binary live/retired axis with no intermediate confidence position; D2/D3 stand
- ⚠ HYPOTHESIS: the corpus's dominant derivation source is run artifacts and tool returns rather than
  settled operator decisions — confirm/refute by a derived sweep of the live corpus (verify-at-outline).
  ⛔ The whole provenance argument rests on this, it is impression rather than measurement, and D2 is
  partly what makes it answerable. If refuted, D2 and D3 shrink accordingly.
  - verdict: unverifiable | checked_at: 7d82d5d90 | by: post-run-quality/cleanup | rescoped: n/a | evidence: corpus has drained again (10/10 at HEAD); no header key names a derivation source, only category (subject axis, not derivation-source axis) -- answering requires D2's own body-level classification work
- ⚠ HYPOTHESIS: trimming is the current primitive for a partially-covered lesson — confirm/refute at
  `manage-lessons/SKILL.md` and the lessons-handling workflow (verify-at-outline).
  - verdict: corroborated | checked_at: 7d82d5d90 | by: post-run-quality/cleanup | rescoped: n/a | evidence: no trim verb exists among manage-lessons' 17 verbs; the primitive lives at finalize-step-lessons-housekeeping/SKILL.md as a hand-edit path with no script surface
- ⚠ HYPOTHESIS: the `1 of 5` contract-reach ratio holds at HEAD over the full corpus. ⛔ It was measured
  over the five process lessons of one cloud-run analysis, which is not the corpus — D4 derives it
  properly (verify-at-outline).
  - verdict: unverifiable | checked_at: 7d82d5d90 | by: post-run-quality/cleanup | rescoped: n/a | evidence: test-quality.adoc:738-755 anchor exact; the 1-of-5 figure is drawn from 2 cloud-lane run reports, not a corpus-wide measurement -- a lead, never a baseline; D4 must derive it
- **Verify-first clause** ⛔ **Never wipe or bulk-mutate the lessons directory in this plan.** The store
  carries tombstones whose loss is unrecoverable, and `manage-lessons remove` has a recorded failure mode
  in which it destroys a lesson while returning `not_found` — so a retry on `not_found` destroys a second
  one. Every deliverable here is read-and-measure or additive; none is a deletion pass.
  - verdict: corroborated | checked_at: 7d82d5d90 | by: post-run-quality/cleanup | rescoped: n/a | evidence: tombstones-never-touched directive intact (SKILL.md:522-525,489-495); the cited not_found-destroys-a-lesson failure mode is now CLOSED at HEAD via the three-state resolution seam and remove --allow-unreadable, but the never-wipe directive itself still binds

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-lessons/` — the store, its schema and its lifecycle surface
- OBSERVED: `test/plan-marshall/manage-lessons/` — the mirror test directory
- HYPOTHESIS: `.claude/skills/finalize-step-lessons-housekeeping/` — the per-plan reconcile D4's reach measurement reads (verify-at-outline)

⚠ The lessons corpus itself lives in a git-ignored store outside the inventory and is **not** declarable
here. It is the measurement's subject, never a deliverable's target.

## ⭐ FOLDED 2026-09-17 — THE CORPUS'S OWN INTEGRITY, MEASURED WHILE ASSEMBLING THIS EPIC

Three first-party observations from the 2026-09-17 lessons sweep. They are corpus-integrity facts, which is
this plan's subject, and each is a measured population rather than an impression.

- ⛔ **6 of 194 lesson files carried NO metadata header at all** (`2026-09-08-22-004/005/006/007`,
  `2026-09-13-06-001/002`). `list` showed them — it derives from file presence — while `get --lesson-id`
  returned `not_found`, so they could be neither read nor retired through the script surface. **They were
  removed on 2026-09-18 by operator instruction, with a direct filesystem delete**, because no sanctioned
  path existed: `manage-lessons` has no repair verb, and `update` and `remove` both resolve by the id that
  fails. All six are preserved at `lessons/invalid-headerless/`.
  ⛔ **The removal wrote NO tombstone** — the tombstone is written by the verb that could not resolve
  them — so six retirements left no record in `.tombstones/`. **That is this deliverable's sharpest
  instance**: a corpus whose audit trail is complete only for the entries the tooling can already see.
  D1's precision measurement must count a headerless file as a distinct state, not as an absent lesson,
  and **D0 must establish how one comes to exist** — the corpus copies are gone, so the cause is no longer
  observable there, only in `lessons/invalid-headerless/`. ⚠ Adjacent owner: `truthful-signals`
  PLAN-TRUTH-144 owns "a lesson can be listed and neither read nor retired" — cross-epic, so coordinate
  rather than re-fix. ⭐ A second obligation follows from the deletion: either the store rejects a
  headerless file at write time, or `remove` gains a path that can retire one with a tombstone. Today
  neither exists, so the same class can silently re-form.
- **Gate 2 of lesson creation cannot read a worktree-resident plan's scope from the main checkout**
  (lesson `2026-09-03-23-006`, preserved in this epic), so the active-plan overlap gate reports clean over
  a population it never read — the three-gate policy's own could-not-look. D3's decision on the absent
  mechanisms must cover it: a gate that cannot see the plans it deduplicates against is not a gate.
- **A lesson allocated by `manage-lessons add` whose `set-body` was never called survives as a titled
  shell** — the header of `2026-09-04-20-001` records exactly that sequence. D1's precision denominator
  must distinguish an empty lesson from an inaccurate one.

⭐ **The reach metric now has a second, harder reading.** D4 asks what share of filed lessons reach the
contract they govern. This sweep measured the upstream half: of 194 lessons, **23 describe post-run quality
defects, and not one had reached a plan** before this epic existed — the oldest filed 2026-08-27. Whatever
D4 derives, that figure is its floor.

## Non-Goals

⛔ No lesson is deleted, retired or rewritten by this plan. ⛔ No change to the routing behaviour of the
lessons-handling epics. ⛔ No confidence mechanism is implemented before D1's measurement says the corpus
needs one — building the mechanism first is the same mistake as tuning a corpus before measuring it.

## Dependencies and Sequencing

- Depends on: none.
- ✅ **RE-GROUNDED 2026-09-22 (cleanup, `checked_at: 7d82d5d90`): the PLAN-TRUTH-144 block is LIFTED.**
  `truthful-signals-26-09-21`'s own queue now reads PLAN-TRUTH-144 as `shipped` (PR #1560, landed as
  `lessons-corpus-producers-report-success`) — the running-collision this spec previously flagged no longer
  exists. Its deliverable is present at HEAD: `manage-lessons/SKILL.md` now documents the three-state
  resolution seam (found/absent/unreadable) plus `remove --allow-unreadable`, closing the specific
  `not_found`-destroys-a-lesson failure mode the prior collision warning was guarding against. This spec's
  own D0/D1/D3 should be re-read against that closed state at outline — the ⭐ FOLDED closing obligation
  ("either the store rejects a headerless file at write time, or remove gains a path that can retire one
  with a tombstone — today NEITHER exists") is now HALF-satisfied by the second branch. This spec is no
  longer blocked on `truthful-signals`.
- ⚠ Adjacent to the lessons-handling epics, which route lessons and implement nothing. This plan gives
  them an instrument and does not take their routing role; if a lessons epic is mid-flight over the same
  store, sequence behind it.
- D4 consumes PLAN-PRQ-03's corpus-population work if that lands first, and derives its own otherwise.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/post-run-quality/plans/PLAN-PRQ-05-lessons-corpus-provenance-and-quality.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
