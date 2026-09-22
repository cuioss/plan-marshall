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

- ⛔ **CONTRADICTED IN PART at cleanup 2026-09-22 (was OBSERVED).** `manage-lessons` carries no
  `confidence` or `precision` model — that half holds exactly as stated (the sole `confidence` hit is
  the unrelated recipe-registry matcher's floor at line 812; `precision` appears nowhere). But
  **freshness and decay are NOT absent**: the `arch-constraint` category carries `recurrence_count`
  ("observation count, bumped on each reinforce") and `last_seen` ("`YYYY-MM-DD` of the latest
  observation; anchors retire-on-quiet"), with `add --rule` reinforcing on recurrence and a
  `retire-quiet` verb retiring every active arch-constraint lesson quiet for the window, the clock reset
  by reinforcement — precisely "raised by corroboration, lowered by age", already shipped for one
  category. **Consequence, absorbed into this spec's scope**: deliverable 4 should treat this as an
  EXISTING PARTIAL implementation to generalize across categories, not a greenfield design.
  - verdict: contradicted | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: instrumentation-substrate/cleanup | rescoped: yes | evidence: confidence/precision absence holds; freshness+decay already exist for arch-constraint category (recurrence_count/last_seen/retire-quiet); deliverable 4 reframed as generalize-existing not greenfield
- ⛔ **REFUTED at cleanup 2026-09-22 (was OBSERVED).** The store's lifecycle is NOT binary. `list
  --status {active|superseded|removed|all}` names **three** lifecycle states, and an orthogonal
  location-encoded axis adds two more: unapplied lessons live in `.plan/local/lessons-learned/{id}.md`
  and become **applied** via `convert-to-plan` (inverse: `restore-from-plan`), and `list-stalled` names
  a fifth observable state — a lesson **stranded** in a non-terminal plan directory. Full set: active /
  superseded / removed / applied / stalled. **Consequence, absorbed into this spec's scope**: the
  sub-clause about "a four-state outcome" is true but names `restore-from-plan`'s own `action`
  vocabulary, not the lesson lifecycle — deliverable 3's provenance field must be designed against the
  five-state lifecycle above, not a binary live/retired model.
  - verdict: contradicted | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: instrumentation-substrate/cleanup | rescoped: yes | evidence: manage-lessons list --status has 3 states plus applied/stalled orthogonal axis, 5 total not 2; deliverable 3 must design against the 5-state lifecycle
- HYPOTHESIS: The corpus's dominant derivation source is run artifacts and tool returns rather than
  settled operator decisions — confirm/refute by a derived sweep of the live corpus (verify-at-outline).
  ⛔ This is the claim the whole provenance argument rests on, it is currently **impression rather than
  measurement**, and deliverable 3 is partly what would make it answerable at all. If refuted, the
  lowest-trust-class argument dissolves and deliverables 3 and 4 shrink accordingly.
  ⚠ **Unverifiable at cleanup 2026-09-22 — structurally unanswerable, which is itself a finding.** No
  provenance field exists today: the Metadata Fields table is `id`, `component`, `category`, `created`,
  `bundle`, `rule`, `recurrence_count`, `last_seen` — nothing records where a lesson came from, so no
  derived sweep can classify by metadata (only LLM judgment over bodies could, which is not a
  derivation). The corpus also lives in a gitignored store outside the architecture inventory. This is
  the sharpest confirmation of deliverable 3's necessity: the claim cannot be measured until the
  provenance field this plan proposes to add already exists.
  - verdict: unverifiable | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: instrumentation-substrate/cleanup | rescoped: n/a | evidence: no provenance field exists in the metadata schema and corpus is outside the inventory; structurally unanswerable, confirms deliverable 3's necessity
- HYPOTHESIS: Trimming is the current primitive for a partially-covered lesson — confirm/refute at
  `marketplace/bundles/plan-marshall/skills/manage-lessons/SKILL.md` and the lessons-handling workflow
  (verify-at-outline). ⭐ **Corroborated at cleanup 2026-09-22, with two refinements.** (a) The policy
  lives in the project-local `.claude/skills/finalize-step-lessons-housekeeping/SKILL.md`, NOT in
  `manage-lessons`, which declares no `trim` verb at all — the mechanism is `set-body` (full-body
  replace), so this spec's own critique ("trimming edits a conclusion in place while leaving its
  unstated derivation intact") is if anything UNDERSTATED: it is a whole-body overwrite. (b) The
  retirement side has gained a justification contract this spec does not account for — `remove` now
  requires `--coverage-verdict` from a closed four-value vocabulary plus a `--covering-clause`/
  `--covering-input` evidence pair on `completely_covered`, recorded on the tombstone. **Consequence,
  absorbed into this spec's scope**: this provenance-of-retirement mechanism is adjacent to deliverable
  3 and worth folding into its design rather than treated as a separate later addition.
  - verdict: corroborated | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: instrumentation-substrate/cleanup | rescoped: n/a | evidence: finalize-step-lessons-housekeeping trims via full-body set-body; remove now requires --coverage-verdict + evidence pair; both refinements absorbed into deliverable 3's scope
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
