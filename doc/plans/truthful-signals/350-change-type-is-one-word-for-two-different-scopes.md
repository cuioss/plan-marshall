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

# `change_type` is one word for two different scopes, and the narrower one narrows the plan

**Epic:** truthful-signals
**Branch prefix:** fix

## Problem

`change_type` is meaningful at **two different scopes** — a **plan's** settled classification, and a
**deliverable's** local kind — and **one word carries both**.

Manifest composition takes the change type as a **required caller-supplied flag** and **never reconciles
it against the plan's own settled classification**. So a caller that forwards the **first deliverable's**
value **silently narrows verification for the whole plan**.

⭐ **The observed instance is unusually clean.** Composition was called with a change type of
`verification` while the plan's settled classification was `bug_fix`; the decision log recorded the
detection of `bug_fix` at high confidence, explicitly overriding an earlier heuristic value; and a later
finalize step **read the settled value back correctly**. ⇒ **Only the compose call disagreed** — which is
what makes this a **scope confusion**, not a detection failure.

## Goal

The two scopes are named apart so a caller cannot pass one where the other is meant, composition refuses
a value that contradicts the plan's settled classification, and the narrowing decision records which
scope it used.

## Deliverables

1. **D0 — GATE: derive both scopes and every producer and consumer of each.** Mutates nothing.
   *Done when:* every site is classified as meaning the **plan** scope or the **deliverable** scope, in
   **both directions**, with the population stated.
   ⛔ **The two-scope split IS the finding. Do not assume the deliverable scope is the accidental one**
   until the sweep says so — it may be the plan scope that was bolted on.
   ⛔ **Confirm the forwarding path by symbol.** The value is *believed* to have come from the first
   deliverable, and **a plausible provenance is not a proven one** — the remedy differs if it came from
   somewhere else.
2. **D1 — Composition reconciles against the plan's settled classification.** A supplied value that
   contradicts it is **refused, with both values named** — never silently accepted.
   *Done when:* the contradiction is refused and the message names both.
   ⚠ **Decide explicitly whether the flag should remain caller-supplied at all once a settled value
   exists.** ⭐ **A required flag duplicating a stored fact is a lost-update shape** — and answering that
   question may be a smaller change than reconciling the two.
3. **D2 — Name the two scopes apart** wherever both appear.
   *Done when:* the names differ. ⛔ **A rename is preferred to a comment** — a comment does not stop a
   caller from passing the wrong one.
4. **D3 — The narrowing decision records which scope it used.**
   *Done when:* the decision carries its input.
   ⭐ **The run's own logs disagreed with themselves and nothing noticed.** A decision that does not
   record its input cannot be audited afterwards, which is why this went unseen until someone read two
   logs side by side.
5. **D4 — Tests, each verified to FAIL pre-fix.**
   - (a) **The live shape**: a plan settled as one type whose caller passes a deliverable's type is
     **refused**.
   - (b) A **matching** pair passes.
   - (c) ⛔ **A control: a plan with NO settled classification still composes.** Without this, the fix
     blocks every plan that has not been classified.
   - (d) The narrowing decision **names its scope**.
   *Done when:* all four pass, each seen red first.

Five deliverables, under the split presumption.

## Out of scope

- **Changing how a plan's change type is detected.** ⭐ Detection worked correctly in the observed
  instance — the classification was right and was read back right. **The defect is in what composition
  does with it.** Widening into detection would chase a component that is not at fault.
- **The manifest cross-check that failed to notice this narrowing.** A sibling plan owns it: a
  bare-versus-canonical token mismatch means the check always skips. ⭐ **Different site, same run,
  complementary** — that plan makes the check able to fire; this one makes the narrowing correct.
  **Cite, do not merge.**

## Expected surface

- `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/**` — the compose verb and its
  change-type flag.
- `marketplace/bundles/plan-marshall/skills/phase-4-plan/**` — the caller that forwards the value.
- `marketplace/bundles/plan-marshall/skills/manage-status/**` — the settled classification, **read
  side**.
- Tests.

⛔ **Every entry is a HYPOTHESIS until D0 resolves it to a file and a symbol.**

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| Composition takes the change type as a required caller-supplied flag and never reconciles it | HYPOTHESIS | the compose verb, **by symbol** — ⛔ **the plan's central premise, and cheap to check** |
| A compose call used a deliverable's type while the plan's settled type differed | HYPOTHESIS | ⛔ **first-party to another run's logs, under `.plan/`, NOT reachable here and NOT re-derived.** ⭐ **But the code-side claim above is checkable without it** — if the reconciliation is absent, the defect exists regardless of that run |
| The detection recorded the settled value at high confidence, overriding an earlier heuristic | HYPOTHESIS | same provenance caveat. ⭐ **Its significance is that detection was RIGHT** — which is what makes this a scope confusion |
| A later finalize step read the settled value back correctly | HYPOTHESIS | same caveat — ⭐ **the control that rules out a detection failure** |
| The wrong value came from the first deliverable | HYPOTHESIS | ⛔ **the forwarding path, by symbol. "Likely" was the word used** — confirm it, because the remedy differs if it came from elsewhere |
| A five-instance corpus cluster is the same defect at population scale | HYPOTHESIS | ⛔ **a corpus not reachable from this clone.** **If those instances are not the same defect, that cluster returns to being an unowned lead and this plan stays scoped to the reconciliation** |
| The compose path still exists at HEAD | HYPOTHESIS | ⛔ **verify-first: a related change landed AFTER the observation.** Confirm the path before scoping |
| Nothing already reconciles the two | HYPOTHESIS | ⛔ asserted **absence**, the higher-risk half — check before adding a reconciliation |

An asserted **absence** is verified exactly as an asserted presence, and is the higher-risk half.
Every count above is a **lead** — re-derive it at the moment of the claim.

## Verification

- ⛔ **D4(c), the no-settled-classification control, is the test that stops this fix from blocking every
  unclassified plan.** It is easy to omit and expensive to omit.
- ⛔ **D1's refusal message must name BOTH values.** Verify by reading an actual refusal: a message
  saying only "change type mismatch" sends the caller to guess which side is wrong, which is how the
  original confusion persisted.
- **D0's classification must be published, both directions.** A one-directional sweep would find the
  sites that mean *plan* and miss the ones that mean *deliverable* — and the split is the finding.
- **D2's rename must be verified as a rename**, not an alias. An alias leaves both spellings usable and
  changes nothing for the next caller.
- Python and test changes are expected, so the build gate takes its full path.

## Notes

- ⚠ **Sequencing: serialize against the sibling plan that also touches composition.** That plan is at its
  deliverable cap, which is why this is a separate plan rather than a merge. **Do not pair them** — both
  reach the same verb.
- ⛔ **Do not go looking for the orchestrator spec, the originating run's logs, the corpus cluster, or
  any landing record.** They live under `.plan/`, which is git-ignored and absent from this clone. ⭐ **The
  code-side premise is fully checkable from this clone**, which is why D0 is scoped to symbols rather
  than to that run.
