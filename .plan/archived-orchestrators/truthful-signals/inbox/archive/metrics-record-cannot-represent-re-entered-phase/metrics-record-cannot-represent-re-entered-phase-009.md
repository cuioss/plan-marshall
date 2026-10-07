envelope_version=1
sender_type=plan
sender_id=metrics-record-cannot-represent-re-entered-phase
epic=truthful-signals
kind=candidate-lesson
created=2026-08-09T21:04:28Z

# Candidate lesson: an operator ruling recorded only in the outline leaves the source of truth contradicting the plan

**Source**: Q-Gate finding `2805d1` (3-outline), resolved `taken_into_account`
**Defect class**: source-of-truth divergence / request-alignment

## The finding

Deliverable 3 mapped onto no request requirement. It mapped onto a request **EXCLUSION**. The
clarified request's Exclusions block stated verbatim:

> "The absorbed -053 spec stays superseded — not implemented from this plan"

The outline was aware of this and overrode it *in prose*: its Operator Decisions table recorded
ruling 3 as ADD A DENOMINATOR DELIVERABLE, and a following paragraph stated the exclusion line was
superseded by that ruling.

**The ruling itself was never in question.** The gap was that the reconciliation lived ONLY inside
`solution_outline.md`, while `request.md` remained the plan's source of truth and still carried
the unamended exclusion.

## Why an unreconciled ruling is not merely untidy

Two concrete downstream consumers read `request.md`, not the outline:

1. **phase-4-plan** reads `request.md` for task-planning context and would have seen deliverable 3
   as out of scope.
2. **The phase-6-finalize request-result-alignment retrospective aspect** compares the shipped
   result against `request.md` — and would have reported deliverable 3 as **unrequested scope
   creep**, because nothing in `request.md` recorded the ruling that authorized it.

So the cost is not confusion; it is a *false finding manufactured at finalize* against work the
operator explicitly authorized. The signal would have been confident and wrong.

## The fix shape worth copying

Amended `request.md` via the three-step path-allocate flow (`request path` → direct edit →
`request mark-clarified`, which returned `clarified: true`). Two edits landed:

- A new scope item **D6** records ruling 3 in the source of truth — the denominator plus mandatory
  sampling-point field, reuse of D1 discriminator vocabulary with an explicit prohibition on a
  second one, the not-persisted-if-undatable rule, and the simplicity bound.
- The Exclusions line was **struck through and annotated RETIRED by operator ruling 3** rather
  than deleted, preserving the distinction the line was reaching for: the -053 spec DOCUMENT stays
  superseded and nothing is read out of it, while its SCOPE is implemented from this plan's own
  outline.

Striking through rather than deleting is the load-bearing detail — it keeps the scope change
**visible** to phase-4-plan and to the finalize alignment aspect, instead of erasing the evidence
that a change occurred.

## Candidate rule

> An operator ruling that changes scope MUST be written back to `request.md`, the source of truth.
> Recording it in `solution_outline.md` alone leaves every `request.md` consumer — phase-4-plan
> and the finalize request-result-alignment aspect — working from a document that contradicts the
> plan, and invites a confident false scope-creep finding at finalize.

> When retiring a superseded request line, strike it through with the authorizing ruling named;
> do not delete it. Deletion removes the audit trail of the scope change.

Note also the cascade this surfaced: amending scope FIRED a conditional constraint (the
notify-CIS-if-the-vocabulary-moves trigger), which was correctly upgraded from conditional to
REQUIRED-before-landing. Scope amendments can activate dormant obligations — re-read the
Constraints block after every ruling write-back.
