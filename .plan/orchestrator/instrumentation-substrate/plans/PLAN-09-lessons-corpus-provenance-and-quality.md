> ⛔ **TRANSFERRED OUT 2026-09-17 — this spec is RETIRED and must not be launched from here.**
> Its substance now lives at
> `.plan/local/orchestrator/post-run-quality/plans/PLAN-PRQ-05-lessons-corpus-provenance-and-quality.md`
> (epic `post-run-quality`, WS-03), which carries all four deliverables, adds a fifth (what share of filed
> lessons reach the contract they govern), and points back at this file as the audit record. This file
> stays on disk unchanged below the line. Its queue row is `parked` because `queue --transition` cannot
> write the `transferred` status the ledger already contains.
> ⭐ **Why it moved**: this epic owns whether an instrument exists for the agent-steering substrate;
> `post-run-quality` owns what the project does with a run once it is over — which is where lessons are
> produced and where they must land. The instrument and its consumer now sit in one ledger.

# PLAN-09: Lessons-corpus provenance and quality measurement

epic: instrumentation-substrate
workstream: WS-05

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off. The orchestrator
> EMITS the command below; it never launches the plan inline. This spec is SELF-SUFFICIENT: the
> emitted command is a one-line pointer and carries no brief, so every per-plan carry is authored here
> and nowhere else.

Staged from inbox `next-level-009` during the 2026-09-14 drain, with `next-level-010` folded in.

## Objective

The lessons corpus is a live part of the substrate that steers every session, and **nothing measures
it**. A lesson is `live` or retired, with no position between them: no confidence that moves, no
freshness term, no provenance record, and no number anywhere saying what share of the corpus is accurate,
relevant, or load-bearing. Give it a measurement and the minimum mechanism that measurement implies.

⭐ This plan is the epic's charter applied to the corpus the epic itself reads from. The absent thing is
an instrument, which is what makes it ours rather than the lessons-handling epics' — those are routers,
not implementers.

## Deliverables

1. A **precision** measurement of the corpus against an enumerated golden set: of the lessons that exist,
   what share are accurate and still relevant. Scored against a derived population and publishing it, per
   this repository's own discipline.
2. A **sized** estimate of the golden set's construction cost, published **before** any labelling begins.
   ⛔ Non-negotiable, and it precedes deliverable 1. A golden set is human labour, and this epic has
   already recorded what happens when a verification layer's cost is not bounded at design time.
3. A provenance field per lesson recording **where it came from** — enough to tell a lesson derived from
   a run artifact or tool return from one derived from a settled operator decision.
4. A decision on the two absent mechanisms below: adopt, defer with a stated reason, or refute.

## The two absent mechanisms — from `next-level-010`

**A confidence that moves.** The source frames trustworthiness as provenance — origin plus freshness —
and ranks source types, putting tool output in its lowest-trust class: *"Generating memories from Tool
Output is generally discouraged because these memories tend to be brittle and stale."* ⚠ A large share of
our corpus is derived from exactly that: observed tool returns, run artifacts, build and CI output.

⭐⭐ **Our own record corroborates the failure mode independently of the source.** Entries that were
accurate when written and silently decayed are a recorded phenomenon here, and there is a standing
discipline of verifying that a named file or flag still exists before acting on a remembered claim.
**That discipline exists because the corpus has no freshness model** — the verification is done by hand,
per recall, forever. The proposed remedy is a confidence raised by corroboration, lowered by age and by
contradiction, with pruning triggered by decay, by never-corroborated low confidence, or by irrelevance.

**Regeneration instead of trimming.** On removing content derived from a withdrawn source, the source
argues that deleting everything *touched* by it is overly aggressive, and that regenerating the affected
memory from the remaining valid sources is more precise. ⭐ Our current move for a partially-covered
lesson is to **trim** it — and trimming edits a conclusion in place while leaving its unstated derivation
intact, which is how a lesson ends up asserting something its surviving sources no longer support.
Regeneration is a different primitive with a different failure mode, and it is the one that matches this
epic's derive-don't-assert discipline.

## The framing — from `next-level-009`

The corpus is **procedural** memory (the "how" — playbooks, workflows, distilled procedures) managed by a
**declarative** lifecycle (store a body, mark it stalled, retire it). The two differ in kind: procedural
consolidation *patches a flawed step inside a plan that otherwise holds*, and we have no primitive for
that — the closest thing is a human promoting reusable residue into the governing skill before retiring
the lesson, performed by hand, one lesson at a time, with no schema behind it.

⭐ **The schema claim is what makes this worth a plan rather than a naming.** If procedural retrieval
genuinely wants a different shape than declarative retrieval, the lesson body format inherited from a
fact-shaped store is the wrong container, and the hand-promotion step is a symptom of that mismatch
rather than a workflow choice. ⚠ The source supplies **no data** for any of this and is describing a gap
in commercial memory platforms, not prescribing a design. Deliverable 4 may refute the reframe outright.

## Claim Labels

- OBSERVED: `manage-lessons` carries **no** confidence, freshness, decay, or precision model. A targeted
  sweep of `marketplace/bundles/plan-marshall/skills/manage-lessons/SKILL.md` for
  `confidence|freshness|decay|precision` returns exactly one hit, and it belongs to an unrelated
  recipe-registry matcher's confidence floor — not to the lessons store. Measured in this checkout on
  2026-09-14.
- OBSERVED: The store's lifecycle is binary — live or retired via tombstones — read at
  `marketplace/bundles/plan-marshall/skills/manage-lessons/SKILL.md`, whose own description names the
  retirement surface and its four-state outcome without any intermediate confidence position.
- HYPOTHESIS: The corpus's dominant derivation source is run artifacts and tool returns rather than
  settled operator decisions — confirm/refute by a derived sweep of the live corpus (verify-at-outline).
  ⛔ This is the claim the whole provenance argument rests on, it is currently **impression rather than
  measurement**, and deliverable 3 is partly what would make it answerable at all. If refuted, the
  lowest-trust-class argument dissolves and deliverables 3 and 4 shrink accordingly.
- HYPOTHESIS: Trimming is the current primitive for a partially-covered lesson — confirm/refute at
  `marketplace/bundles/plan-marshall/skills/manage-lessons/SKILL.md` and the lessons-handling workflow
  (verify-at-outline).
- Verify-first clause: ⛔ **Never wipe or bulk-mutate the lessons directory in this plan.** The store
  carries tombstones whose loss is unrecoverable, and `manage-lessons remove` has a recorded failure mode
  in which it destroys a lesson while returning `not_found` — so a retry on `not_found` destroys a second
  one. Every deliverable here is read-and-measure or additive; none is a deletion pass.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-lessons/` — the store, its schema, and its
  lifecycle surface
- OBSERVED: `test/plan-marshall/manage-lessons/` — the mirror test directory

⚠ The lessons corpus itself lives in a git-ignored store outside the inventory and is **not** declarable
here. It is the measurement's subject, never a deliverable's target.

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: none declared.
- Adjacent to: the lessons-handling epics, which route lessons but implement nothing. ⭐ This plan gives
  them an instrument; it does not take their routing role. Notify rather than assume — if a lessons epic
  is mid-flight over the same store, sequence behind it.

## Non-Goals

⛔ No lesson is deleted, retired, or rewritten by this plan. ⛔ No change to the routing behaviour of the
lessons-handling epics. ⛔ No confidence mechanism is *implemented* before deliverable 1's measurement
says the corpus needs one — building the mechanism first would be the same mistake as tuning a corpus
before measuring it.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/instrumentation-substrate/plans/PLAN-09-lessons-corpus-provenance-and-quality.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
