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

# Graduate the deployment/topology diagram type into `pm-documents:ref-svg-diagrams`

**Epic:** truthful-signals
**Branch prefix:** feature

## Problem

A downstream consumer repository authored a deployment/topology SVG diagram type, deliberately *"shaped
to graft upstream unchanged"*, with an explicit graduation statement and a stated non-goal of *not*
modifying the upstream skill in that PR. The graduation was designed to happen later — this plan is
that later.

⚠ **A scope correction the requester should see: the template CANNOT move alone.** The request named
only the `.svg`, but moving it by itself would **violate the target skill's own documented contract**:

- The skill states that per-diagram-type standards live under `standards/diagram-type-{name}.md`. **A
  type without its standard is undefined.**
- Its templates table gives **every** template row an owning standard in the second column. A
  `deployment` row would have nothing to name.
- The skill explicitly says that when no existing type fits, *a new diagram-type standard is needed* —
  which is exactly this case.

**So the graduated set is the standard AND the template.** The reference implementation is a separate
question, and D1 owns it.

⚠ **THEME NOTE, stated openly:** this is a documentation-tooling graduation, **not** an instance of
this epic's confident-signal-hides-a-caveat theme. It sits in this epic because that is where new
non-review work lands by default, not because it fits the charter. Low priority — but it must not be
lost.

## Goal

`pm-documents:ref-svg-diagrams` owns a complete deployment/topology diagram type — standard, template,
and both index rows — and the downstream copy is retired without leaving a dangling reference.

## Deliverables

1. **D1 — GATE: decide the graduation set and the reference-implementation column.** Mutates nothing.
   Every existing type row names a **reference implementation** living in this repository's own docs.
   The graduated type has none, because its only reference implementation is the consumer's own
   topology diagram. Choose:
   - **(a)** graduate standard + template only, with the type row carrying **no** reference
     implementation (or an explicit *"no reference implementation yet"* note), accepting asymmetry with
     the other rows. **← default recommendation**
   - **(b)** additionally author a native deployment diagram as the reference implementation. **Larger
     scope, and it must depict real infrastructure of this project, never a synthetic example.**
   - **(c)** cite the consumer repository's diagram. ⛔ **REJECTED up front** — a marketplace skill must
     not depend on a consumer repo's file as its reference.
   Also settle whether the type lands **authored-and-indexed** or as a future placeholder, following
   whichever pattern the skill already uses for a placeholder type.
   *Done when:* both decisions are recorded with reasons.
2. **D2 — Land the standard and the template.** Copy both into the skill.
   *Done when:* both exist upstream and comply with the marketplace documentation rules.
   ⛔ **The standard was written to graft unchanged — verify rather than assume.** Strip or rewrite any
   consumer-specific reference, and comply with the marketplace documentation rules: **no transitionary
   prose, no version history, no dated sections, no "recently added" framing**.
   ⛔ **The graduation statement inside the standard is itself transitional and must be DROPPED on
   landing** — upstream *is* the destination, so a document explaining that it intends to move upstream
   is false the moment it arrives.
3. **D3 — Index it in the skill.** Add the type row to the per-diagram-type table and the template row
   to the templates table, **with its owning standard named**, matching the existing column contract
   exactly.
   *Done when:* both rows exist and match the contract.
   ⚠ **Re-derive any prose count adjacent to those tables.** A hand-written count sitting next to a
   table that just grew is **this epic's most-repeated defect**. Check the skill and any bundle README
   for such a count and correct it — or better, remove it.
4. **D4 — Record the downstream retirement as a proposal for the operator.** The downstream copy lives
   in a **different repository**, which this run cannot reach.
   *Done when:* the report records, precisely and actionably: which two files to remove, that the
   removal must be **upstream-first, downstream-second** (so the downstream README never points at a
   skill path that does not exist yet), that the downstream `README.adoc` and topology `.adoc` must be
   repointed at the upstream skill, and that **a whole-repository sweep for dangling references is
   required** because the two known referrers are a **SAMPLE, not an enumeration**.
   ⛔ **Do NOT attempt the cross-repository change from this run.** It is a different repository with
   its own PR flow, and there is no operator here to approve it. Record the proposal; do not make the
   change.
5. **D5 — Gates.**
   *Done when:* the plugin-doctor gate is clean over the touched bundle, and the render question below
   is resolved rather than skipped.
   ⚠ **Render verification is a real open blocker, not a formality.** The upstream standard treats
   render-and-read-back as **non-skippable**, and the downstream PR recorded that **no rasteriser was
   installed**, resolving it as its own gate deliverable. **Either re-establish a render path here, or
   record explicitly why the graduated template's already-verified render carries over.** ⛔ Silently
   skipping it would ship an unrendered template into a skill whose own standard forbids exactly that.

Five deliverables, under the split presumption.

## Out of scope

- **The consumer repository's real topology diagram and the document describing it.** Those are
  consumer-specific *content*, not the reusable type. Graduating them would move a specific deployment
  into a generic skill.
- **Making the cross-repository change.** See D4. A run with no operator must not open a PR against a
  second repository on its own judgement — and the lane binds this run to this repository in any case.
- **Modifying any other diagram type.** The graduation adds a type; it does not revisit the five that
  exist. Touching them would put unrelated diagram churn in a PR whose reviewers are checking a
  graduation.

## Expected surface

- `marketplace/bundles/pm-documents/skills/ref-svg-diagrams/standards/diagram-type-deployment.md` — new.
- `marketplace/bundles/pm-documents/skills/ref-svg-diagrams/templates/deployment-diagram-skeleton.svg` — new.
- `marketplace/bundles/pm-documents/skills/ref-svg-diagrams/SKILL.md` — the two index tables.
- A `pm-documents` README or bundle index carrying a diagram-type or template **count**, if one exists.

⭐ **`pm-documents` is disjoint from every other plan in this epic**, which all sit in `plan-marshall`
bundles. That makes this a good low-cost parallel filler whenever a slot is free.

## Claim labels

⚠⚠ **This plan is derived from a spec that carried NO claim-label section.** Labels were deliberately
**not** retrofitted at authoring time: assigning `OBSERVED` to a claim the author did not personally
verify manufactures provenance, and a wrong label reads as a checked one.

⇒ **Treat EVERY claim below as `HYPOTHESIS` until this run verifies it**, including every count, path,
and line total. ⭐ **Asserted absences are the higher-risk half.**

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The skill requires per-type standards under `standards/diagram-type-{name}.md` | HYPOTHESIS | `ref-svg-diagrams/SKILL.md` — **by quoted phrase**, not by line |
| Every templates-table row names its owning standard in the second column | HYPOTHESIS | that table. ⛔ This is the constraint that makes the standard non-optional |
| Every type row names a reference implementation living in this repository | HYPOTHESIS | that table. ⛔ An asserted **completeness** claim — if even one row already lacks one, D1(a)'s "asymmetry" concern evaporates |
| The source standard is ~429 lines and the template ~129 | HYPOTHESIS | ⛔ **not reachable from this clone** — the source lives in another repository. The **content** must be obtained by the operator, not reconstructed. If it is not supplied, **this plan cannot proceed past D1** |
| The standard covers five affordances plus naming, theme strategy, and a render recipe | HYPOTHESIS | the standard's own text, once available |
| The standard contains a graduation statement that must be dropped | HYPOTHESIS | that text — an asserted **presence**, cheap to check once the file is in hand |
| A prose count of diagram types/templates exists somewhere and will go stale | HYPOTHESIS | the skill and the bundle README — ⛔ an asserted **presence**; if absent, nothing to fix, and say so |
| No rasteriser is installed, blocking render verification | HYPOTHESIS | try to render. ⚠ Reported downstream against a different environment; **this environment may differ** |
| Only two downstream files reference the graduated paths | HYPOTHESIS | ⛔ **not verifiable from this clone**, and explicitly flagged as a **SAMPLE**. D4 records the sweep as required work rather than asserting the count |

An asserted **absence** is verified exactly as an asserted presence, and is the higher-risk half.
Every count above is a **lead** — re-derive it at the moment of the claim.

## Verification

- ⛔ **STOP CONDITION, stated plainly: this plan cannot complete without the source files.** They live
  in another repository that this clone cannot reach. **If the standard and template are not present in
  this repository or supplied with the hand-over, halt after D1 and report the plan blocked on
  input.** ⛔ **Do NOT reconstruct a 429-line standard from this plan's summary of it** — an invented
  standard that looks authoritative is far worse than a missing one.
- **D3's index rows get a cold read**: give the Step 6 verification sub-agent the amended tables with
  no other context and ask which standard governs the deployment template. If it cannot answer from the
  table alone, the column contract was not matched.
- **D5's render question must produce an explicit verdict in the report** — rendered, or carried over
  with a stated reason. "Not mentioned" is a failed deliverable, because the skill's own standard makes
  render-and-read-back non-skippable.
- Documentation and asset changes are expected, so the build gate will likely take its docs-only path.
  **Confirm from git evidence rather than assuming.**

## Notes

- ⭐ **Worth preserving from the downstream work:** its reference implementation was cross-checked
  service-by-service against real compose and gateway configuration rather than being synthetic. **If
  D1 picks option (b), hold the native reference diagram to that same standard** — a synthetic example
  would be a weaker artifact than the one being graduated away from.
- ⚠ **Ordering across repositories is upstream-first.** The downstream README must never point at a
  skill path that does not exist yet, which is why D4 is a recorded proposal rather than a
  simultaneous change.
- ⛔ **Do not go looking for the orchestrator spec or any landing record.** They live under `.plan/`,
  which is git-ignored and absent from this clone. Everything needed and knowable is in this file; the
  source artifacts are the one thing that must arrive from outside it.
