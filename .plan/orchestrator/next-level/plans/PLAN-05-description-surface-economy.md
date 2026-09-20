# PLAN-05: Description-surface economy

epic: next-level
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off. The orchestrator
> EMITS the command below; it never launches the plan inline. This spec is SELF-SUFFICIENT: the
> emitted command is a one-line pointer and carries no brief, so every per-plan carry is authored here
> and nowhere else.

## Objective

A component's frontmatter `description` is resident on every turn of every session whether or not the
component is ever loaded — the most expensive byte in the corpus per unit of information it carries.
Derive what that surface actually costs, decide whether a shape rule for it earns its keep, and either
enforce the rule or close the question with the measurement on record.

⚠ **The lever was sized before this spec was staged, and it came back small.** Publishing that number
here is deliberate: it is what keeps the plan honest about its own ceiling rather than discovering the
ceiling after the work.

## Deliverables

1. A derived measurement of the always-resident description surface, reported per component and in
   total, with the population it was computed over. ⛔ The measurement must distinguish the components
   whose descriptions are actually resident in a session from those that are not — registration
   status decides residency, and a total over all components on disk would overstate the cost.
2. A decision, recorded either way: enforce a trigger-shaped description rule, or close the question.
   ⭐ **"Close it unfixed" is a first-class outcome of this plan, not a failure of it.** If the
   recoverable bytes do not justify rewriting 157 descriptions and carrying a new lint rule forever,
   saying so with the number attached is the deliverable.
3. If the decision is to enforce: a `plugin-doctor` rule for description shape, with its threshold
   derived from the measurement rather than picked.
4. If the decision is to enforce: the rewrite applied to the top decile by byte count only — the part
   where the measurement says the money is.

## Claim Labels

- OBSERVED: The always-resident description surface totals **26,694 bytes across 157 components**,
  mean 170 bytes and median 119, with the top 20 components carrying a disproportionate share
  (`manage-references` 713 bytes, `ext-self-review-plan-marshall` 689, `plugin-security` 587,
  `plan-orchestrator` 579). Measured in this session at `main` `77cb2e251` over
  `marketplace/bundles/*/skills/*/SKILL.md`; `components_without_description: 0`, `unreadable: 0`, so
  the population is complete. ⚠ The measuring script is at `.plan/temp/size-description-surface.py`
  and is **temporary** — re-derive rather than trusting these numbers if they have aged.
- OBSERVED: The median is 119 bytes, which means most descriptions are already short and the
  addressable cost is concentrated in a small tail. ⭐ This is the fact that makes deliverable 2's
  "close it unfixed" branch a live possibility rather than a formality.
- HYPOTHESIS: Registration status determines whether a component's description is resident — a
  script-only three-part component does not register and therefore costs nothing per turn — confirm/
  refute at `CLAUDE.md` § "Tool Usage" and the bundle `plugin.json` registration contract
  (verify-at-outline). ⛔ If refuted, deliverable 1's population is wrong and the measurement above
  overstates or understates the real resident cost.
- HYPOTHESIS: A description phrased as a *trigger* ("Use when …") rather than as a *summary* both
  shortens the text and improves retrieval — confirm/refute against
  `marketplace/bundles/pm-plugin-development/skills/plugin-architecture/references/frontmatter-standards.md`,
  which may already state a shape rule (verify-at-outline). ⛔ The retrieval half of this hypothesis is
  a behavioural claim about a model, and this plan has no instrument for it. State it as unverified or
  drop it — do not assert it.
- Verify-first clause: ⚠ Descriptions are how **every** runtime in the fleet locates a skill, and the
  generator emits them byte-identical to all of them. A shape rule reasoned about one model's retrieval
  behaviour is the same defect WS-02 exists to prevent, at a smaller scale. This plan must state which
  runtimes its rule was reasoned about and which it was not.

## Expected Surface

- OBSERVED: `marketplace/bundles/` — read to derive the measurement; written only in the top-decile
  rewrite, and only if the decision is to enforce
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/` — the lint rule, only if
  the decision is to enforce
- OBSERVED: `test/pm-plugin-development/plugin-doctor/` — the mirror test directory for that rule
- HYPOTHESIS: `marketplace/bundles/pm-plugin-development/skills/plugin-architecture/references/frontmatter-standards.md`
  — updated if a shape rule is adopted and this document is where it belongs (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: none declared, but see the adjacency below.
- Adjacent to: PLAN-01 and PLAN-02, which create a component `plugin-doctor` lints. They do not modify
  `plugin-doctor`; this plan may. ⚠ If this plan and either WS-01 plan are ever in flight together
  under a raised parallelization scope, that adjacency becomes a real overlap and must be re-checked
  before pairing.

## Non-Goals

⛔ No description is rewritten for reasons other than shape, and no component's behaviour, name, or
registration changes. ⛔ No blanket rewrite of all 157 descriptions — the measurement says the cost is
in the tail, and a full sweep would spend more review effort than the bytes are worth.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/next-level/plans/PLAN-05-description-surface-economy.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
