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

# The generic dispatch template cannot express a step-specific mandatory field

**Epic:** truthful-signals
**Branch prefix:** fix

## Problem

⭐ **The finding as filed was that a template "omits a field". The verified defect is worse, and the
framing must be corrected before anything is scoped.**

The step's **own** workflow document carries a **correct** dispatch snippet including the field. The
problem is that a **second, generic template exists** — in the finalize dispatcher's own SKILL.md,
**twice**:

```text
Task: plan-marshall:{target}
  prompt: |
    name: <step-name>
    plan_id: {plan_id}
    skills[N]:
    - <step-specific skills>
    workflow: <workflow-doc-from-table>
    WORKTREE: {worktree_path}
```

⇒ **A fixed five-field body with no slot for step-specific mandatory fields at all.** Meanwhile the
self-review step declares its `candidates` field **Required: Yes**.

⛔ **So this is not one missing line in one template. It is a generic dispatcher that structurally cannot
express a per-step contract, plus a per-step snippet that can — two templates for the same dispatch, and
only one of them right.** ⛔ **A fix that adds `candidates` to the generic template hard-codes one step's
needs into the generic path and leaves the class open.**

## ⭐ Archetype: a producerless contract row

A step **declares** a mandatory field; the dispatcher that actually runs it has **no way to carry it**;
**nothing fails when the two disagree.** This is the same shape as a declared-but-never-emitted output
field elsewhere in this project — already a second sighting. ⇒ **Declaring and satisfying are two edits
in two places with no link between them.**

## Goal

A step's declared prompt-body contract and the body the dispatcher actually sends cannot disagree
silently — the divergence is a build-time or test-time error, and the generic path either carries
step-specific fields or stops pretending to be authoritative.

## Deliverables

1. **D0 — GATE: derive every step that declares a required prompt-body field beyond the generic five.**
   Mutates nothing.
   *Done when:* the population is derived **from the step documents' own required-field tables**, in
   **both directions**, with its size reported.
   ⛔ **Not sampled.** The known field is one instance, found by hitting it.
   ⚠ **Both directions matter**: fields **declared but uncarriable**, *and* fields the generic template
   carries that **no step declares**.
   ⛔ **STOP CONDITION, and it can invalidate the whole plan.** **Confirm the generic template is
   actually followed by some dispatch path rather than being purely illustrative.** If it is
   illustrative only, **the observed failure had a different cause and this plan is mis-aimed** — halt
   and report that rather than fixing a template nobody reads.
2. **D1 — Decide how the generic path carries step-specific fields, and record the rejected option.**
   Either the generic template gains an **explicit extension slot**, or the dispatcher is **required to
   use the step's own snippet** and the generic one is demoted to illustrative.
   *Done when:* one option is implemented and the other is recorded as rejected with its reason.
   ⭐ **The second is cheaper and REMOVES the duplication rather than managing it** — but ⛔ **confirm no
   step lacks its own snippet first**, or demoting the generic template strands those steps.
3. **D2 — Make the divergence fail.** A step declaring a required field the dispatch body does not carry
   must be a **build-time or test-time error**.
   *Done when:* an intentionally divergent step fails the gate.
   ⛔ **THIS IS THE LOAD-BEARING DELIVERABLE.** Without it, D1 fixes today's instance and **the next
   declaration silently reopens the class** — which is exactly how this defect came to exist.
4. **D3 — Tests, each verified to FAIL pre-fix.**
   - (a) A step declaring a required field absent from its dispatch body is **rejected**.
   - (b) D0's population is **asserted non-empty and contains the known instance**.
   - (c) ⛔ **A control: a step with no extra fields still dispatches unchanged.**
   *Done when:* all three pass, each seen red first.
   ⛔ **(c) is not optional** — a guard that rejects every dispatch would satisfy (a) and (b).

Four deliverables, under the split presumption.

## Out of scope

- ⛔ **Adding the one known field to the generic template as the fix.** See the Problem section: it
  hard-codes one step's needs into the generic path and leaves the class open. It would also look like a
  completed fix, which is worse than an obvious gap.
- **Redesigning the prompt-body contract itself.** The plan makes declaration and satisfaction agree; it
  does not revisit which fields a dispatch should have.
- **Rewriting the step workflow documents' content.** Only their required-field declarations are in
  scope.

## Expected surface

- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` — the two generic templates.
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md` —
  the declaration and the correct step-local snippet.
- `marketplace/bundles/plan-marshall/skills/ref-workflow-architecture/**` — where the prompt-body
  contract is defined.
- `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-finalize-step.md` — ⭐ a
  per-step frontmatter obligation already lives in this seam; **a required-fields declaration may belong
  in the same place.**
- Tests.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| Two generic five-field templates exist in the finalize dispatcher's SKILL.md | OBSERVED | that file — locate **by content**; the duplication is the point |
| The self-review step declares `candidates` as **Required: Yes** | OBSERVED | that step's workflow document — **by section**, not by line |
| The step-local dispatch snippet **does** carry the field | OBSERVED | the same document. ⛔ **PARTIALLY REFUTES the finding as filed** — do **not** scope from the original wording |
| The generic template is actually followed by some dispatch path | HYPOTHESIS | ⛔ **D0's stop condition.** If it is illustrative only, this plan is mis-aimed |
| Other steps have the same shape | HYPOTHESIS | **D0's derivation. n=1 today.** If the known field is the only instance, D1 gets much cheaper — ⛔ **and D2 is still required**, because the guard is the deliverable, not the count |
| Every step has its own dispatch snippet | HYPOTHESIS | ⛔ an asserted **presence** across a population — **D1's second option depends entirely on it**, and a single step without one makes that option unsafe |
| A per-step frontmatter obligation with both-direction guards already exists in the extension seam | HYPOTHESIS | that standard — ⭐ **the reference implementation for D2, and it may make it nearly free.** Read it before designing anything |

An asserted **absence** is verified exactly as an asserted presence, and is the higher-risk half.
Every count above is a **lead** — re-derive it at the moment of the claim.

## Verification

- ⛔ **D2 must be demonstrated by injecting a divergence**, not merely by the guard existing. Add a
  required field to a step without carrying it, confirm the gate fails, then remove it. A guard never
  seen to fire is indistinguishable from one that cannot.
- ⛔ **D3(c), the control, guards against the over-broad fix.** A gate that rejects any dispatch carrying
  more or fewer than five fields would break every step while passing the other tests.
- **D0 must report the population size and the divergent count separately, and cover both directions.**
  A one-directional sweep would miss fields the template carries that nothing declares — which is the
  half nobody looks for.
- Documentation and test changes are expected, plus possibly Python. **Confirm the build gate's path
  from git evidence.**

## Notes

- ⚠ **Re-ground against the change that introduced per-step frontmatter obligations with both-direction
  guards.** ⭐ **That is the reference implementation for D2.** If it is already in the tree, this plan
  may be mostly a matter of extending an existing mechanism rather than building one.
- ⚠ **A sibling plan in this epic carries the same producerless-row archetype** at the
  documented-enum-versus-argparse layer. **Sequence, do not pair — and evaluate at outline whether that
  plan should absorb this one.** For: one enforcement rule ("a declaration without a producer is a build
  error") could close both. Against: a merged plan spans two bundles.
- ⛔ **Do not go looking for the orchestrator spec, the filed message, or any landing record.** They live
  under `.plan/`, which is git-ignored and absent from this clone. Everything needed is in this file.
