# PLAN-TRUTH-040: the generic dispatch template cannot express a step-specific mandatory field

epic: truthful-signals
workstream: WS-01

## Objective — the report said "the template omits a field"; the verified defect is worse

The filed item states: *"the phase-6-finalize dispatcher's prompt-body template omits the mandatory
`candidates` field that `pre-submission-self-review` declares."*

⭐ **Verified first-party, and the framing needs correcting before it is scoped.** The step's own
workflow doc carries a **correct** dispatch snippet including `candidates`. The problem is that
**a second, generic template exists** — `phase-6-finalize/SKILL.md`, twice:

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

⇒ **A fixed five-field body with no slot for step-specific mandatory fields at all.** Meanwhile
`pre-submission-self-review.md:49` declares `candidates` **Required: Yes**.

⛔ **So this is not one missing line in one template — it is a generic dispatcher that structurally
cannot express a per-step contract, plus a per-step snippet that can.** Two templates for the same
dispatch, and only one of them is right. **A fix that adds `candidates` to the generic template
hard-codes one step's needs into the generic path and leaves the class open.**

## ⭐ Archetype: this is a producerless contract row

A step **declares** a mandatory field; the dispatcher that actually runs it has **no way to carry it**;
**nothing fails when the two disagree.** That is the same shape as the `dispatch_boundaries`
producerless row and the declared-but-never-emitted `display_detail` (already a second sighting on
`PLAN-TRUTH-012`). ⇒ **Declaring and satisfying are two edits in two places with no link between them.**

## Deliverables

1. **D0 — GATE: derive every step that declares a required prompt-body field beyond the generic five.**
   ⛔ **Population derived from the step docs' own required-field tables, not sampled** — `candidates`
   is one instance and the report found it by hitting it. ⚠ **Both directions**: fields declared but
   uncarriable, AND fields the generic template carries that no step declares.
2. **D1 — decide how the generic path carries step-specific fields, and record the rejected option.**
   Either the generic template gains an explicit extension slot, or the dispatcher is required to use
   the step's own snippet and the generic one is demoted to illustrative. ⭐ **The second is cheaper and
   removes the duplication rather than managing it** — but confirm no step lacks its own snippet first.
3. **D2 — make the divergence fail.** A step declaring a required field the dispatch body does not
   carry must be a build-time or test-time error. ⛔ **This is the load-bearing deliverable** — without
   it, D1 fixes today's instance and the next declaration silently reopens it.
4. **D3 — tests, verified to FAIL pre-fix.** (a) A step declaring a required field absent from its
   dispatch body is rejected. (b) The D0 population is asserted non-empty and contains
   `pre-submission-self-review`/`candidates`. (c) A control: a step with no extra fields still
   dispatches unchanged.

## Claim Labels

- **OBSERVED (first-party)**: the two generic five-field templates in `phase-6-finalize/SKILL.md`; the
  `candidates` **Required: Yes** declaration at `pre-submission-self-review.md:49`; the correct
  step-local dispatch snippet carrying `candidates: | {candidates_toon}`.
- ⛔ **PARTIALLY REFUTED as filed**: the step-local template does **NOT** omit the field. **Do not scope
  from the original wording** — the defect is the generic path and the duplication, not a missing line.
- **HYPOTHESIS**: other steps have the same shape. **n=1 — DERIVE at D0.** If `candidates` is the only
  instance, D1 gets much cheaper and D2 is still required.
- **Verify-first clause**: assumes the generic template is actually followed by some dispatch path
  rather than being purely illustrative. ⛔ **If it is illustrative only, the observed failure had a
  different cause and this plan is mis-aimed — confirm at D0 before implementing.**

## Expected Surface

- **OBSERVED**: `phase-6-finalize/SKILL.md` — the two generic templates
- **OBSERVED**: `phase-6-finalize/workflow/pre-submission-self-review.md` — the declaration and snippet
- **HYPOTHESIS**: `ref-workflow-architecture` — where the prompt-body contract is defined
- **HYPOTHESIS**: `extension-api/standards/ext-point-finalize-step.md` — #1076 added a `records_facts`
  frontmatter obligation here; **a required-fields declaration may belong in the same seam.**

## Dependencies and Sequencing

- ⚠ **Re-ground against #1076** — it introduced per-step frontmatter obligations with both-direction
  guards. ⭐ **That is the reference implementation for D2** and may make it nearly free.
- ⚠ Adjacent to `PLAN-TRUTH-012` (producerless-row archetype, second sighting). **Sequence, do not
  pair** — evaluate at outline whether 012 should absorb this.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-040-the-generic-dispatch-template-cannot-carry-a-step-specific-mandatory-field.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message. Qualifiers
are in `persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
