> ⛔ **FIRST INSTRUCTION — do not skip, do not delete, do not move below the title.**
>
> Before reading the rest of this plan and before any other action, load the working contract that
> governs this run:
>
> ```text
> Skill: cloud-plan-lane
> ```
>
> It owns the branch/PR/review-comment cycle, the build gate, the pre-PR verification sub-agent, the
> run report, and the closing self-check. **Nothing in this plan overrides it** — where this plan and
> the contract disagree, the contract wins, and the disagreement is reported.
>
> If the skill cannot be loaded, **stop and report the run blocked**. Do not reconstruct the workflow
> from this file: the parts that matter most — the merge gate, the verification dispatch, the report
> — are not in here.
>
> This block is part of the plan, not part of the template. It survives into every copy.

# A `compact` verb — regenerate the derivable ledger, relocate the settled narrative, delete nothing

**Epic:** truthful-signals
**Branch prefix:** feature

## Problem

An orchestrator epic's ledger accumulates two very different kinds of content, and nothing separates
them. The operator has repeatedly asked, by hand, for a "complete, thorough cleanup … persist
everything so we can restart the orchestrator." The manual version is being performed; it is simply
not repeatable and not auditable.

⚠ **The existing `archive` verb does NOT already do this.** That verb is post-`close`, mechanical, and
whole-tree: it relocates a **closed** epic. This verb operates on a **live, mid-flight** epic and
touches content. They are complements, not overlaps.

## ⛔ The design constraint that makes or breaks it: the axis is DERIVABLE vs NARRATIVE, not OLD vs NEW

The request's own words — *"historical / archaeological"* — name the **wrong axis**, and following
them literally would produce a destructive verb. This ledger's highest-value content is old, settled,
and reads exactly like archaeology:

- *"that spec-corruption claim was RETRACTED — don't re-flag it"*
- *"that fold was MISATTRIBUTED — a deliverable aimed there would find nothing"*
- *"the row said `staged` while the plan was closed-superseded; it was offered as a candidate because
  the row lied"*
- *"the gate itself may be stale rather than pending"*

**Every one of those exists to prevent rework, and a trim-by-age pass deletes all of them.**

⭐ The correct discriminator is whether a statement is **re-derivable from `status.json` and the
filesystem**:

| Class | Treatment |
|---|---|
| **Derivable** — counts, queue tables, per-plan status mirrors, PR/landing stamps | **REGENERATE.** Never curate; a hand-maintained copy of a derivable fact *is* the defect. |
| **Narrative** — decisions, retractions, refutations, standing rules, "do not re-derive this" | **PRESERVE**, regardless of age. Relocate if bulky; never drop. |

⚠ **And the split cannot be applied mechanically per field.** The clearest counter-example: the
operator-confirmed `running` state has no machine field, and **nothing observes it** — no liveness
signal exists. It is narrative because *the world offers no derivable source*, **not** because someone
wrote prose where a field belonged. ⇒ **Regenerating it would fabricate a fact.** Leave it narrative
and say why.

## Goal

A live epic's ledger can be compacted by a verb rather than by hand: every derivable surface is
regenerated under a guarded marker, every narrative item is preserved or relocated with a pointer left
behind, and the verb reports everything it moved and everything it declined to touch.

## Deliverables

1. **D1 — GATE: name, relocation target, and idempotence.** Mutates nothing. Settle three things:
   - **Verb name.** `cleanup` is the operator's word but **implies deletion, which this verb must never
     do**. **Recommend `compact`.** (`reconcile` collides — the standard already uses it for the
     status.json → epic.md direction.) ⚠ Whichever wins, **the router table, the standard, and the
     workflow doc must all agree** — a verb named in one and not the others is this epic's
     doc-contract-divergence archetype, shipped inside a plan that exists to close it.
   - **Relocation target.** `history.md` is currently written only at `close`. Decide whether `compact`
     appends to it mid-life, uses a new `settled.md`, or moves items into the `landings/` records they
     belong to. ⛔ **Whatever is chosen, a pointer must remain at the origin** — a reader following the
     old path must land on the content, not on absence.
   - **Idempotence.** Running it twice must be a no-op. State the mechanism (content-addressed markers,
     or a per-section stamp).
   *Done when:* all three are decided and recorded.
2. **D2 — Extend the GENERATED-block mechanism to every derivable surface.** The START-HERE block
   already carries `BEGIN/END GENERATED` markers and a regeneration invocation. **The Ordered Queue
   table — same file, same authority, four derivable columns — has no such guard.** Bring every
   derivable surface under the same marker-and-regenerate contract.
   *Done when:* each derivable surface is guarded and regenerable.
   ⛔ **Settle the known tension the operator is already owed a decision on.** The persist contract says
   the generated block is *"GENERATED, never hand-written"* — yet a live block was found **hand-
   annotated**, substituting a pointer sentence for the verbatim generator output, as a deliberate
   deviation to avoid duplicating an oversized anchor into `epic.md`. **Either the generator must emit
   the annotations (blocked reasons, per-row caveats), or the contract must permit an annotation zone
   outside the markers.** ⛔ **Pasting the verbatim output as-is would destroy information the
   annotations carry** — so "just follow the contract" is not an available answer.
3. **D3 — Relocate settled narrative, with pointers.** Move bulky settled narrative to D1's target.
   *Done when:* each relocated item is verbatim at its destination and reachable from a pointer at its
   origin.
   ⛔ **Preserve verbatim.** Retractions, refutations, and do-not-re-derive notes are the anti-rework
   record and must survive intact. ⛔ **A section is "settled" only when its subject is closed** — a
   shipped plan's residue, a resolved defect — **never merely because it is old.**
4. **D4 — Report what moved; never trim silently.** Emit a structured report: sections regenerated,
   items relocated with source and destination, invariants checked, and **anything the verb declined to
   touch and why**.
   *Done when:* the report names every mutation and every abstention.
   ⛔ **A silent compaction is indistinguishable from a lossy one** — this epic's entire theme. **The
   report is the deliverable that makes the verb safe to run unattended.**
5. **D5 — Invariant verification, and tests.** After compaction, verify: queue rows ↔ spec files
   **bidirectionally**; no shipped rows in the live Ordered Queue; no orphaned spec file; every
   relocated item reachable from its pointer.
   ⛔ **Bidirectional is the check that bites** — a count match alone passes with a mismatched pair.
   ⚠ **For any whole-array write, use snapshot → write → diff, expecting only the intended change.**
   Tests: (a) idempotence — a second run is a no-op; (b) a narrative retraction survives a pass
   **verbatim**; (c) a stale derivable row is **corrected**, not preserved; (d) the report names every
   mutation.
   *Done when:* all four pass and each was seen to fail pre-fix.

Five deliverables, under the split presumption — **after the cut described below**.

⭐ **Split-guard verdict, recorded before hand-over.** The source spec carried **fourteen** deliverables
against a ceiling of twelve, with a second cut explicitly owed and recorded rather than papered over.
**That cut is applied here**: the `resume_anchor` shape question is moved out (see Out of scope), and
the inbox-archive foldering had already moved to a sibling plan whose declared surface it exactly is.
What remains is one coherent unit — regenerate the derivable, relocate the settled, report both.

## Out of scope

- ⛔ **The `resume_anchor` shape question — CUT FROM THIS PLAN, and it needs its own.** The anchor is
  the machine authority a fresh session reads first; it has been observed rewritten **eight times in
  one day** and grown past **12 KB**, accumulating settled content that belongs in `epic.md`. **An
  anchor that must be read in full to find the next action has stopped being an anchor.** It is cut
  because it is a **different file, a different authority, and its own operator-owed decision** — and
  because at least one other plan in this epic depends on it, which argues for sequencing it early and
  separately rather than burying it inside a large plan. **Record this in the report as owed work.**
- **Folding the inbox archive into per-sender subdirectories.** Moved to the sibling plan owning the
  `inbox` verb group, and the load-bearing constraint travelled with it: the sequence allocator
  **scans both the live and archived directories**, so a naive move into subdirectories silently
  re-opens a sequence-reuse defect that a previous plan already fixed. ⛔ **Do not re-implement it
  here.**
- **Deleting anything.** The verb's name may end up being `compact`, but its contract is that it
  **never deletes**. A deliverable that removes content has left this plan's scope.
- **Running on a closed epic.** ⚠ **The verb must refuse.** That tree is the frozen audit record and
  `close` already froze it; compaction is a live-epic operation only.
- **LLM judgement over the whole file to infer "noise".** ⭐ The derivable half is mechanical and must
  stay mechanical. Only the settled-versus-live narrative call needs judgement, and it should be
  **presented for confirmation rather than applied silently** on a first run.

## Expected surface

- `marketplace/bundles/plan-marshall/skills/marshall-orchestrator/SKILL.md` — the verb-routing table,
  plus a new `workflow/compact.md`.
- `marketplace/bundles/plan-marshall/skills/persona-marshall-orchestrator/standards/orchestration-model.md`
  — § Persist / Stop-Resume currently describes only *close freezes* and *archive relocates*; a third
  content-level operation needs stating there.
- `marketplace/bundles/plan-marshall/skills/marshall-orchestrator/scripts/orchestrator.py` — the
  deterministic half (regeneration, invariant checks, the report) belongs in the script per the
  dispatch-granularity heuristics; the narrative-versus-settled judgement does not.
- `test/plan-marshall/marshall-orchestrator/**`.

## Claim labels

⚠⚠ **This plan is derived from a spec that carried NO claim-label section.** Labels were deliberately
**not** retrofitted at authoring time: assigning `OBSERVED` to a claim the author did not personally
verify manufactures provenance, and a wrong label reads as a checked one.

⇒ **Treat EVERY claim below as `HYPOTHESIS` until this run verifies it**, including every count. ⭐
**Asserted absences are the higher-risk half.**

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The START-HERE block carries `BEGIN/END GENERATED` markers and a regeneration invocation | HYPOTHESIS | the orchestration standard and the resume-summary generator — **by symbol** |
| The Ordered Queue table duplicates four `status.json` columns with **no** generated-block guard | HYPOTHESIS | the epic-document template and the standard. ⛔ An asserted **absence**, verified as a presence |
| The Decisions list duplicates the decision log **with no stated authority** | HYPOTHESIS | the template and the standard. ⚠ **Declaring the authority may be the cheaper half of the fix** and is a prerequisite to regenerating it |
| Five emitted verb-output counts are LLM-tallied from free text and cannot be checked | HYPOTHESIS | the verb workflow docs' output contracts |
| The operator-confirmed `running` state has no machine field and no liveness signal exists | HYPOTHESIS | the status schema and any liveness source. ⛔ **This is the one that must NOT be "fixed" by regeneration** — confirm the absence before deciding, because regenerating it would fabricate a fact |
| A prior gate enumerated 13 derivable assertion classes vs 8 narrative across 7 files | HYPOTHESIS | ⛔ **REPORTED, not reachable from this clone.** Use it as a starting shape, **re-derive it**, and note that the same prior work warned its own list was a **sample of the class, not the class** |
| An anchor was rewritten 8× in one day and grew past 12 KB | HYPOTHESIS | ⛔ **not reachable from this clone** — the ledger is under `.plan/`. Motivation for the cut, not evidence to cite |
| The verb-routing table exists and can take a tenth entry | HYPOTHESIS | that SKILL.md § verb routing |
| No existing verb already performs live-epic compaction | HYPOTHESIS | ⛔ asserted **absence**, the higher-risk half — read every existing verb's workflow before building a new one |

An asserted **absence** is verified exactly as an asserted presence, and is the higher-risk half.
Every count above is a **lead** — re-derive it at the moment of the claim.

## Verification

- ⛔ **D5(b) — a narrative retraction surviving verbatim — is the test that protects everything this
  plan is for.** If a compaction pass can drop a retraction, the verb is a destructive tool wearing a
  tidy name, and no other passing test compensates.
- ⛔ **D3's derivable-versus-narrative boundary is judgement expressed as text**, so it gets a **cold
  read**: give the Step 6 verification sub-agent four ledger snippets — a stale count, a queue row, a
  retraction, and the operator-confirmed `running` note — with no other context, and ask which may be
  regenerated. The correct answers are **the first two only**. If it regenerates the `running` note, the
  written boundary invites fabricating a fact.
- **D4's report must include the abstentions, not only the mutations.** A report that lists only what
  changed cannot distinguish "nothing needed touching" from "the verb could not see it".
- **Verify the verb refuses on a closed epic**, explicitly. That refusal is what keeps the frozen audit
  record frozen.
- Python, doc, and test changes are expected, so the build gate takes its full path.

## Notes

- ⛔ **Sequencing is tight and matters.** This plan collides with the plan that renames the whole
  orchestrator skill — **run this one first**, because renaming a verb set is cheaper than adding a verb
  to a renamed set. It also collides with the plan that declares itself exclusive against anything
  touching dispatched workflow docs, since a new `workflow/compact.md` is exactly that: **never
  concurrent**. And it shares `orchestrator.py` with the inbox plans, so **serialize** against those.
- ⭐ **Evidence this is a real recurring need, not a nicety:** the instruction has been issued by hand
  repeatedly, and in a single day one epic's ordered queue drifted to phantom rows and live-shown
  shipped plans while its generated block went stale carrying a contract violation.
- ⛔ **Do not go looking for the orchestrator spec, the drained inbox messages, or any landing record.**
  They live under `.plan/`, which is git-ignored and absent from this clone. Everything needed is in
  this file.
