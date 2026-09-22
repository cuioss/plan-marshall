# PLAN-TRUTH-143: The orchestrator inbox has no delivery path, and its corpus instruments publish an unmeasured zero

## Objective

Two defects on the same target — the orchestrator's own machinery — merged because they are read and
tested through the same seams. First, the orchestrator to plan channel is one-way by construction: a plan
writes, the orchestrator drains between plans, and **no plan-side reader exists anywhere in the tree**. The
`--target-plan` field is a visibility device only; a message aimed at a `running` plan is REFUSED at write
time (`undeliverable_to_running_plan`) precisely because nothing would ever read it. Second, the corpus
instruments that report on that machinery publish a zero nobody measured, and collapse a suffixed plan id.

⚠ **This plan amends a standing invariant, and that is the substance of the work, not a side effect.**
`orchestration-model.md` § Ledger Write-Boundary states the channel is *"One-way"* and that *"The plan never
reads the ledger to make a decision."* D0 settles the amended wording BEFORE any code changes; a plan that
quietly builds a reader while leaving that sentence standing produces exactly the doc-contract divergence
this epic exists to remove.

## Deliverables

10 deliverables, within the epic's operator-set ceiling of 12 (recorded 2026-09-12: the orchestration-model scope-bloat guard presumptively splits at ~6 and permits proceeding unsplit with a recorded rationale; that decision is the rationale). **D0 is a gate: nothing downstream starts until every carried claim is re-grounded at HEAD.** Each deliverable names the superseded spec it came from, so the audit trail back to the source is a pointer, not a restatement.

1. **D0 — GATE: settle the delivery contract, the mailbox residency, the amended invariant, and the plan-id grammar.** Re-ground every claim carried from PLAN-TRUTH-100 and PLAN-TRUTH-131 against the implementing source at HEAD. Settle (a) the delivery contract and mailbox residency, (b) the amended § Ledger Write-Boundary wording, and (c) whether letter suffixes are a legal plan-id form at all — PLAN-TRUTH-131's own D0 question, which decides whether D7 is a fix or a no-op. ⛔ Publish each swept population and its size.
2. **D1 — ONE symmetric channel API over the `(epic_slug, plan_id)` address.** Read this BEFORE D2–D4: it is the shape those three implement against, and its path-resolution clauses forbid the hand-rolled resolution they would otherwise invite. Both plan faces resolve through the resolver that already owns them. (PLAN-TRUTH-100 D6.)
3. **D2 — The writer: replace the refusal with delivery.** `undeliverable_to_running_plan` stops being the answer for a running target. (PLAN-TRUTH-100 D1.)
4. **D3 — The reader: a plan-side read verb, fail-open by construction.** A plan that cannot read its mailbox proceeds; it never blocks on the channel. (PLAN-TRUTH-100 D2.)
5. **D4 — The two check-points.** The running plan notices a message at every phase transition and on return from every dispatched sub-agent. (PLAN-TRUTH-100 D3 — the operator's explicit requirement.)
6. **D5 — Consumption AND non-consumption are both visible.** A message that was delivered and ignored is distinguishable from one never delivered. (PLAN-TRUTH-100 D4.)
7. **D6 — Publish a candidate-side derivation-status tally per `candidate_kind`.** So a `count: 0` from the corpus instruments states which zero it is. (PLAN-TRUTH-131 D1.)
8. **D7 — Derive the id from the queue row wherever a row is already in hand.** Stops the suffixed-id collapse at its source rather than patching each reader. (PLAN-TRUTH-131 D2.)
9. **D8 — Tests: matched controls plus a POPULATION-DERIVED check-point roster.** The roster is derived from the phase/dispatch population, never hand-listed — a hand-listed roster is the vacuous-guard archetype this epic keeps re-introducing. Negative controls for both PLAN-TRUTH-131 members are load-bearing. (PLAN-TRUTH-100 D5 + PLAN-TRUTH-131 D3.)
10. **D9 — the queue's single-row writer cannot write three statuses the ledger already holds.** ⭐ **OBSERVED first-party on 2026-09-12 while this epic's own regrouping ran, and it forced a bulk-array rewrite that the write-boundary reserves for seed-from-nothing.** `orchestrator.py:164` `VALID_STATUS_VOCABULARY` is `{staged, launched, running, parked, shipped, landed}`, so `queue --transition --status superseded` is refused with `invalid_field` — yet the live queue holds 54 rows at `superseded`, 5 at `transferred` and 1 at `retired`. The validator and the data disagree, and the only way to reach those statuses is the whole-array rewrite whose documented hazard is silently losing a concurrent session's row. ⛔ Settle which set is authoritative (extend the vocabulary, or declare the three statuses illegal and migrate the 60 rows) — do NOT widen the validator without deciding that, because a validator widened to match whatever the data happens to contain is the vacuous-guard archetype. Matched control: a status genuinely outside the settled set must still be refused.

   ⭐⭐⭐ **INDEPENDENTLY CORROBORATED by epic `review-apparatus` on 2026-09-12 (inbox
   `review-apparatus-036.md`), which hit the same wall from the other side and supplies three facts
   this deliverable did not have.** (a) **The divergence has a cause: one document, two writers, two
   vocabularies.** The single-row writer validates against the six-member set; the whole-array
   `manage-status update-field --field plans` rewrite performs **no status validation at all**, which
   is how the out-of-set rows got in. Closing only the reader leaves the bulk path free to admit an
   eighth value. (b) **The gap already forces a FALSE RECORD.** Having no way to write `retired`,
   `review-apparatus` recorded **18 superseded specs as `parked`** — `parked` means *blocked and
   resumable*, these are *superseded and dead* — so the true status survives only in each spec's
   header, the `epic.md` record, and the decision log. ⛔ A machine authority that cannot express the
   state its own data holds pushes the truth into prose, which is this epic's archetype one level down.
   (c) **The four `retired` rows currently render as LIVE.** `LIVE_QUEUE_EXCLUDED_STATUSES` is
   `('shipped', 'landed')`, so an out-of-set terminal status is not excluded and shows in the Ordered
   Queue as actionable. ⇒ Widening the vocabulary is therefore **not** the whole fix: every tally and
   exclusion consumer must be re-derived over the widened set, and **that re-derivation is the
   deliverable, not an afterthought**. ⛔ The existing out-of-set rows are **evidence, not debris** —
   silently normalising them to `parked` would destroy the record of why they were retired.

## Claim Labels

⛔ Every claim below is a POINTER at the superseded source spec that authored it. The sources are on disk and are the audit record; re-derive each claim **from the source spec's own section at HEAD**, never from this restatement. D0 owns that re-grounding.

- HYPOTHESIS: every scoping premise carried from PLAN-TRUTH-100 still holds at HEAD — confirm/refute at `.plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-100-the-inbox-has-no-delivery-path-to-a-running-plan.md` § `## Claim Labels` (verify-at-outline)
- HYPOTHESIS: every scoping premise carried from PLAN-TRUTH-131 still holds at HEAD — confirm/refute at `.plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-131-the-corpus-instruments-publish-an-unmeasured-zero-and-collapse-a-suffixed-id.md` § `## Claim Labels` (verify-at-outline)

## Expected Surface

Machine-derived: the union of the `## Expected Surface` sections of every superseded source, resolved through `plan-marshall:script-shared`'s `epic_spec_parser` — the single reader the disjointness gate uses. Not retyped.

- `marketplace/bundles/plan-marshall/skills/persona-plan-orchestrator/standards/orchestration-model.md` — carried from PLAN-TRUTH-100
- `marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/inbox-envelope.md` — carried from PLAN-TRUTH-100
- `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py` — carried from PLAN-TRUTH-100
- `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py` — carried from PLAN-TRUTH-100
- `marketplace/bundles/plan-marshall/skills/plan-orchestrator/SKILL.md` — carried from PLAN-TRUTH-100
- `marketplace/bundles/plan-marshall/skills/manage-status/scripts/manage-status.py` — carried from PLAN-TRUTH-100
- `marketplace/bundles/plan-marshall/skills/manage-status/SKILL.md` — carried from PLAN-TRUTH-100
- `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning.md` — carried from PLAN-TRUTH-100
- `test/plan-marshall/plan-orchestrator/test_inbox_delivery.py` — carried from PLAN-TRUTH-100
- `test/_shared/_dispatch_roster.py` — carried from PLAN-TRUTH-100
- `marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/analyze.md` — carried from PLAN-TRUTH-100
- `marketplace/bundles/plan-marshall/skills/script-shared/scripts/epic_spec_parser.py` — carried from PLAN-TRUTH-131
- `test/plan-marshall/plan-orchestrator/**` — carried from PLAN-TRUTH-131
- `marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/orchestrate.md` — added 2026-09-17,
  folded from `lessons-handling-26-09-04-01-065.md` (the disjointness rule's own text)

## Dependencies and Sequencing

D0 gates everything. D1 precedes D2–D4. This plan's surface includes
`persona-plan-orchestrator/standards/orchestration-model.md` and the `plan-orchestrator` scripts, which are
also declared by other merged plans in this epic — the disjointness gate will report the overlap and sequence
accordingly. PLAN-TRUTH-139, -127 and -103 were running when this plan was staged and were NOT re-scoped.

## Supersession Record

This plan SUPERSEDES the following specs, which stay on disk as the audit record of why they were retired (⛔ a superseded spec is never deleted):

- `PLAN-TRUTH-100-the-inbox-has-no-delivery-path-to-a-running-plan.md` (PLAN-TRUTH-100)
- `PLAN-TRUTH-131-the-corpus-instruments-publish-an-unmeasured-zero-and-collapse-a-suffixed-id.md` (PLAN-TRUTH-131)

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-143-the-orchestrator-inbox-has-no-delivery-path-and-its-corpus-instruments-publish-an-unmeasured-zero.md"
```

## ⭐ FOLDED 2026-09-17 — THE DISJOINTNESS GATE COUNTS TERMINAL AND CLOSED-EPIC SPECS, SO A MATURING EPIC CANNOT EMIT

Forwarded from `lessons-handling-26-09-04-01-065.md` — found by the Token-Sheriff orchestrator while
running `next`, not by a plan, which is why it took ten plans to surface. Expected Surface extended in the
same act (`plan-orchestrator/workflow/orchestrate.md`, above); `orchestrator.py` is already declared.
⛔ **This orchestrator hit the same thing on 2026-09-15 (c)** and worked around it by comparing only
against in-flight rows — an override of the documented `iff`, which is exactly the shape the source
message warns becomes invisible once routine.

`corpus cross-check`'s `candidate_kind: corpus_spec` rows carry no status filter, so a candidate is
compared against `shipped` / `landed` / `superseded` specs and against specs in CLOSED, ARCHIVED sibling
epics — neither of which can hold a live plan. Measured at the sender: PLAN-14 drew 12 overlap rows,
PLAN-16 11, PLAN-17 14, **every one against a terminal or closed-epic spec, with zero `running` rows in
the epic at the time**. By `orchestrate.md` Step 4's literal rule none was emittable. The error grows
monotonically with epic age, because a shipped corpus only accumulates — a false RED that eventually
blocks the whole queue.

**Remedy direction (D6's own shape).** Filter the `corpus_spec` population to rows that can still run
(`staged`, `launched`, `running`, `parked`) and skip sibling epics whose `phase` is `closed` — and keep
the ADR-019 separation: publish how many candidates were excluded BY STATUS and why, so a filtered-out
candidate reads as *not comparable*, never as *compared and clean*. ⛔ Fix the verb and `orchestrate.md`
together: today a reader following the doc exactly gets a different answer than one following its stated
purpose (concurrency), and that gap is what forces the override.

## Write-Boundary

The executing plan MUST NOT create or edit any file under `.plan/local/orchestrator/truthful-signals/` except its own `inbox/{sender}-{seq}.md` messages, written through `plan-marshall:plan-orchestrator:orchestrator inbox write`. The orchestrator owns every other ledger write.
