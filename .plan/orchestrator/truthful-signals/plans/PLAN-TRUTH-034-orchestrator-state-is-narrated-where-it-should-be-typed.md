# PLAN-TRUTH-034: orchestrator state is narrated where it should be typed

epic: truthful-signals
workstream: WS-01

## Objective

Operator observation (2026-08-02): the orchestrator ledger carries **prose** for things that are
enumerable facts — parallelization scope, related orchestrators, running plans, the plan queue — and
that prose is what a compaction or restart has to re-read. Making them typed fields would be cheaper
and correct-by-construction.

⭐ **The observation is right, but the diagnosis has to be sharpened before it can be fixed, because the
obvious fix is already in place and did not work.** `status.json` ALREADY types every field named
above, and `resume-summary` ALREADY derives them correctly. The defect is that **hand-written prose was
pasted INTO the generated block**, where regeneration cannot correct it and nothing validates it.

## OBSERVED evidence — found while answering the question, in this epic's own tree

The generated START-HERE block in `epic.md` was stale **in the confident direction** on every count:

| Claim in the block | Machine authority | |
|---|---|---|
| Queue: 79 rows | 81 | wrong |
| 43 shipped | 46 | wrong |
| R = 2 of N = 2 — AT CAP | R = 1 of N = 1 | wrong |
| RUNNING: TRUTH-026, TRUTH-031 | TRUTH-010 (both others shipped) | wrong |
| Inbox: 15 queued, 319 archived | 0 queued, 398 archived | wrong |

⛔ **And it contradicted itself inside its own markers**: `R = 2 of N = 2 — AT CAP` twenty lines above
`R = 0 of N = 5 … three genuinely free`. A reader following the second sentence would have emitted three
plans while at cap.

⭐ **Second instance, in the same output**: `resume_anchor` prose states *"27 staged"* while the
generator's **own derived enumeration in the same emission** lists **28**. The narrated copy and the
derived copy disagreed at zero distance from each other.

⇒ This is the epic's flagship archetype turned on the epic's own ledger: **a confident signal that has
stopped tracking what it describes.** The Ordered Queue table had the identical failure on 2026-07-30
(eleven shipped rows shown as launched, eight rows naming plans absent from `status.json`) — so this is
**occurrence 2 of the same defect in the same file**, which is what makes it a plan and not a cleanup.

## Cross-epic evidence — OBSERVED 2026-08-02, all three epics

⭐ **The block sizes give the mechanism away.** Both siblings paste the **full `resume_anchor` inline**
inside the generated markers; this epic replaced it with a pointer:

| Epic | Block size | Anchor | Derived facts vs authority |
|---|---|---|---|
| `code-intelligence-substrate` | 8,326 chars | inline | **current** (R=2 > N=1, correctly flagged over-capacity) |
| `review-apparatus` | 5,168 chars | inline | ⛔ **STALE** |
| `truthful-signals` | 953 chars | pointer | was stale; reconciled 08-02 |

⛔ **`review-apparatus` is failing LIVE, and in the OPPOSITE direction to ours.** Its block renders
*"NEXT ACTION: WAIT - both slots are full … R=2, N-R=0 -> emit nothing"*, naming PLAN-PR-014 and
PLAN-PR-001 as running. Its authority (read at `updated: 2026-08-02T13:42:48Z`) says
`parallelization_scope=1`, **zero running**, and both of those plans **shipped** (#1070, #1071). ⇒ **R=0
of N=1 — a free slot, blocked by its own rendering.**

⇒ **The failure is bidirectional and both directions cost.** Ours over-permitted (rendered three free
slots while at cap → risk of breaching the cap); theirs under-permits (renders a full queue while a slot
is free → **throughput loss, right now**). A fix that only prevents over-permitting is half a fix.

⭐ **Neither sibling's `status.json` is at fault** — `review-apparatus`'s was updated *more recently than
this epic's*. **The authority is well-maintained in all three; only the rendering lags.** That is the
strongest available evidence that structure is not the missing ingredient.

⭐ **Two conventions exist across three epics** (anchor inline ×2, anchor pointer ×1) — so D4's
"deviation" is not a local irregularity, it is an **unresolved contract question the fleet has already
answered two different ways**. D4 is therefore promoted from cleanup to a real decision.

⚠ **Notified, not fixed**: a finding was routed to `review-apparatus`'s inbox
(`truthful-signals-011.md`) reporting its free slot and the load-bearing-prose caveat. **Their ledger,
their call** — this plan owns the machinery, never a sibling's state.

## Why "add frontmatter to `epic.md`" is the WRONG fix, and what is right

⛔ **A YAML frontmatter block in `epic.md` would be a SECOND COPY of `status.json`** — a new staleness
site with the same failure mode, not a fix. `epic.md` is the *rendering*; `status.json` is the
authority. **Where a copy exists, delete the copy** (standing epic rule).

The real repairs, in dependency order:

1. **Nothing derivable may be hand-written inside the generated markers.** Today the contract *says*
   this and the file *violated* it, because the violation is invisible — a hand-edit inside the markers
   survives every regeneration that is never run. Needs a **check**, not stronger prose.
2. **Non-derivable content needs a home OUTSIDE the markers.** It had none, which is *why* it was
   pasted inside. Three genuine invariants were in there (029's id permanently spent, the load-bearing
   scope reason, the id-space split) — none encoded in `status.json`, so a faithful regeneration would
   have silently DROPPED them. ⚠ **The contract violation was load-bearing.** Any fix that just
   enforces "regenerate verbatim" destroys real information unless (2) lands with (1).
3. **`resume_anchor` should carry only what is NOT derivable.** It is 9.7 KB of free text and it
   re-states counts the generator computes — which is exactly how it came to disagree with them.

## Deliverables

1. **D0 — GATE: derive which START-HERE facts are `status.json`-derivable and which are not.**
   Population from the current block plus `resume-summary`'s emission, both directions: derivable-but-
   narrated, and narrated-but-underivable. ⛔ **Both directions or the sweep is vacuous** — direction 2
   is what protects the three invariants above.
2. **D1 — a drift check that FAILS when the generated block disagrees with `status.json`.** ⛔ It must
   be able to fail for the observed reason: re-run it against the pre-fix `epic.md` (recoverable from
   git) and confirm it flags the 79-vs-81 / N=2-vs-N=1 / running-set drift. **A check that passes on a
   known-broken input is not a check.** ⭐ Prefer failing on *any* hand-edit inside the markers
   (byte-compare against a fresh `resume-summary`) over field-by-field comparison — the latter re-derives
   the producer's rules and will drift (standing rule). ⛔ **It must run over EVERY epic under
   `.plan/local/orchestrator/`, not the invoking one** — the defect is fleet-wide, and a per-epic check
   would have left `review-apparatus` blocked on a phantom full queue. **Verify it flags `review-apparatus`
   today.**
3. **D2 — a sanctioned home for non-derivable standing invariants**, outside the markers, that a
   regeneration provably cannot drop. An interim `## Standing Invariants` section was written by hand on
   2026-08-02 — **make it contractual or replace it, do not leave it as an undocumented local habit.**
4. **D3 — shrink `resume_anchor` to the underivable residue.** Anything D0 classes derivable is REMOVED
   from the anchor, not restated. ⚠ **Removal only — this must not become a rewrite of the anchor's
   standing-rules record**, which is the epic's anti-rework memory.
5. **D4 — resolve the recorded contract deviation** (`epic.md` carries an anchor *pointer* where the
   contract says paste verbatim): either teach `resume-summary` to emit the pointer form, or amend the
   contract. **Pick one and record the rejected one.**

## Adjacent, and DELIBERATELY out of scope

The operator's frontmatter instinct **does** pay off one layer down, on **plan specs** — `PLAN-*.md`
files state `epic:` / `workstream:` as bare lines and carry Dependencies, Expected Surface and blocking
reasons as prose, which is what the orchestrator reads *by hand* to decide surface disjointness at every
emit. Typed spec frontmatter would make disjointness checkable. ⛔ **Not folded in here** — it is a
different artifact, a different consumer, and this plan is already at 5 deliverables (scope-bloat guard).
Stage separately if wanted.

## Claim Labels

- **OBSERVED**: every drift figure in the table above — read from `status.json` and `epic.md` on
  2026-08-02, and from `resume-summary`'s live emission.
- **OBSERVED**: the internal contradiction, the 27-vs-28 disagreement, and the three non-derivable
  invariants that a faithful regeneration would have dropped.
- **OBSERVED**: the 2026-07-30 Ordered Queue reconciliation (recorded in `epic.md`), establishing
  recurrence.
- **HYPOTHESIS**: the three invariants are the COMPLETE set of underivable content in the pre-fix block.
  ⛔ **Assembled by reading one file once — DERIVE IT at D0.** A missed invariant is deleted by the
  first enforced regeneration.
- **OBSERVED — the defect is GENERAL, not local to this epic.** Operator reported seeing it in the
  siblings; verified 2026-08-02 by reading all three `status.json` + `epic.md` (reads are unrestricted
  in location; nothing written in either sibling tree). ⇒ The fix is a **shared-seam** fix. Detail in
  § Cross-epic evidence.
- **Verify-first clause**: D1 assumes `resume-summary` is deterministic for unchanged `status.json`.
  **Confirm before byte-comparison is adopted** — a timestamp or an unordered map in the emission would
  make byte-equality fail spuriously and force the field-by-field form D1 otherwise rejects.

## Expected Surface

- **OBSERVED**: `marshall-orchestrator/scripts/orchestrator.py` — `resume-summary`
- **HYPOTHESIS**: `persona-marshall-orchestrator/standards/orchestration-model.md` — the persist and
  START-HERE contracts, and D2's home for invariants
- **HYPOTHESIS**: `marshall-orchestrator/templates/epic.md` — the marker convention
- **HYPOTHESIS**: `marshall-orchestrator/workflow/resume.md` / `orchestrate.md` — where regeneration is
  invoked

## Dependencies and Sequencing

- **Depends on**: none.
- ⚠ **`PLAN-TRUTH-015` renames `marshall-orchestrator`** — re-ground paths if it lands first.
- ⚠ **Surface-adjacent to `PLAN-TRUTH-032`** (inbox protocol, same script). **Sequence, do not pair.**
- ⛔ Epic is **AT CAP (`parallelization_scope` = 1)**. Staged only; not emittable until TRUTH-010 lands,
  and TRUTH-027 / TRUTH-028 are already the named next two.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-034-orchestrator-state-is-narrated-where-it-should-be-typed.md"
```

## ⭐ FOLDED 2026-08-02 — plan completion is a typed fact that every orchestrator infers from an untyped proxy

**Offered by `review-apparatus` (msg `-016` § 4) for this plan's scope**, from an incident in their lane:

They recorded a plan `shipped` on **verified first-party evidence that its PR had merged**. It was still
running — `branch-cleanup` is step 9 of 12, with `plan-retrospective`, `sync-plugin-cache` and
`archive-plan` all following. The operator caught it; they reverted the transition.

⭐⭐ **The generalisable part, and why it belongs here**: they had **already** hardened against a
known-bad oracle (the plan's own landing message) and replaced it with the PR state — **another wrong
oracle, which felt rigorous precisely because it was first-party and verified.**

> **Verifying a claim against the wrong artifact is indistinguishable, from the inside, from verifying
> it against the right one.**

✅ **The correct oracle is cheap and already typed**: a plan is complete when it **leaves
`manage-status list`**. Confirmed by contrast in the same query — a plan that reached `archive-plan` is
**absent** from the list.

⇒ **This is precisely this plan's thesis**: a fact that IS typed and machine-readable is being narrated
and inferred instead. **D0's population must include plan-completion**, not only the START-HERE block's
fields — the defect is not confined to one rendered artifact.

## ⭐⭐ MERGED 2026-08-08 — this plan ABSORBS -033

**Component:** `marshall-orchestrator (state that should be typed, identity that should be visible)` · **Deliverables after merge: 10** (raised cap is 12).

Both plans are *"the orchestrator holds a fact as prose where it should hold it as data."*

- **`-034`** — the ledger narrates enumerable facts (parallelization scope, related epics, plan states)
  instead of typing them. **This session is the evidence**: four shipped plans sat in the Ordered Queue
  table, three staged plans had no row, and a stale `BLOCKED` label survived — every one a fact that was
  prose in one place and data in another.
- **`-033`** — a plan has two identities (`PLAN-TRUTH-NNN` and its `plan_marshall_plan_id`) that never
  appear together, so the operator cannot map one to the other at the moment it matters. ⛔ Its dominant
  half is the terminal-title **latch presented as a state**.

⭐ **One deliverable serves both**: a typed record that carries a plan's identities and state together
is simultaneously 034's typing and 033's mapping. Shipped separately, 033 would render an identity pair
that 034 then re-types.

⛔ **The absorbed spec(s) are `superseded` and retained as the record — do not implement or emit them.**
⚠ **Re-count at outline; overlapping deliverables COLLAPSE rather than concatenate.**

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. ⛔ **Special care
here**: its subject matter is this epic's ledger, but it edits NO file under
`.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — it changes the
*generator and the contract*, never this epic's live ledger content. The orchestrator owns every other
ledger write. Qualifiers and the sole sanctioned write mechanism are in
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
