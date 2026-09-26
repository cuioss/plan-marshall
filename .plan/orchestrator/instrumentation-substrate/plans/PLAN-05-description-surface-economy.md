# PLAN-05: Description-surface economy

> ⛔⛔ **SUPERSEDED BY PM-MCP (2026-09-26, operator decision relayed by `review-apparatus-001`; row status `parked`).** `plan-marshall-mcp` replaces both the process prose and the Python scripts this plan edits, so implementing it here is legacy work. Its implementation-independent content (rules, invariants, classifications, data, fixtures) was extracted as rows `05.*` to `/Users/oliver/git/plan-marshall-mcp/doc/known-defects/instrumentation-substrate-carry-over.md` as PM-MCP input. **Do NOT emit; un-park only by explicit operator decision.** The body below is kept intact as the evidence chain.

epic: instrumentation-substrate
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

- ⛔ **CONTRADICTED on the figures at cleanup 2026-09-22 (population and shape hold).** The original
  measuring script (`.plan/temp/size-description-surface.py`, gitignored) is gone at HEAD; re-derived
  from scratch over the SAME population (`marketplace/bundles/*/skills/*/SKILL.md`, UTF-8 byte length of
  `description:`). **Corrected figures**: **157 components ✓** (unchanged), total **27,354 bytes** (was
  26,694, drifted +660), mean **174** (was 170), median **119 ✓** (exact), `components_without_description:
  0 ✓`, `unreadable: 0 ✓`. Per-component: `manage-references` **713 ✓**, `plugin-security` **587 ✓**,
  `ext-self-review-plan-marshall` **714** (was 689), `plan-orchestrator` **621** (was 579). **The
  ranking itself is also wrong**: the current top component is `plan-marshall:manage-lessons` at **721
  bytes**, unnamed in the original measurement, with `persona-module-tester` at **651** also unnamed.
  Corrected top-8 by byte count: `manage-lessons` 721, `ext-self-review-plan-marshall` 714,
  `manage-references` 713, `persona-module-tester` 651, `plan-orchestrator` 621, `plugin-security` 587,
  `arch-gate-java` 519, `oci-standards` 501. **Consequence, absorbed into this spec's scope**:
  deliverable 4's "top decile by byte count" must be re-run against this corrected ranking, not the
  original one — the original top-4 list would have missed the actual #1 and #4 components entirely.
  - verdict: contradicted | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: instrumentation-substrate/cleanup | rescoped: yes | evidence: measuring script gone at HEAD; re-derived over same population, 157 components + median 119 hold, 4 of 6 stated figures drifted; corrected top-8 ranking in spec text
- OBSERVED: The median is 119 bytes, which means most descriptions are already short and the
  addressable cost is concentrated in a small tail. ⭐ This is the fact that makes deliverable 2's
  "close it unfixed" branch a live possibility rather than a formality.
  - verdict: corroborated | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: instrumentation-substrate/cleanup | rescoped: n/a | evidence: median re-derived at exactly 119; mean/median ratio 1.46 confirms right skew; top-8=18.4% of total from 5.1% of components
- HYPOTHESIS: Registration status determines whether a component's description is resident — a
  script-only three-part component does not register and therefore costs nothing per turn — confirm/
  refute at `CLAUDE.md` § "Tool Usage" and the bundle `plugin.json` registration contract
  (verify-at-outline). ⭐ **Corroborated at cleanup 2026-09-22, via the SECOND target only — the first
  is mis-cited.** `CLAUDE.md` § "Tool Usage" says nothing about registration (it is four lines on
  Read/Edit/Write over shell commands). The `plugin.json` half settles it: summing each bundle's
  `.claude-plugin/plugin.json` `skills` array gives **154 registered skills** against **157 SKILL.md
  files on disk** — registration is an explicit per-component opt-in and **3 on-disk skills sit outside
  it**, matching `CLAUDE.md` § "Repository Overview" ("158 registered components (154 skills, 2
  agents, 2 commands)"). **Consequence, absorbed into this spec's scope**: deliverable 1's population
  concern is real and quantified — the corrected measurement above, taken over all 157 on-disk SKILL.md
  files, overstates the resident surface by the 3 unregistered components; a resident-only re-cut is
  owed before deliverable 2's decision.
  - verdict: corroborated | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: instrumentation-substrate/cleanup | rescoped: n/a | evidence: CLAUDE.md Tool Usage is mis-cited (unrelated); plugin.json sums confirm 154/157 registered, 3 unregistered; deliverable 1 population concern quantified
- ⛔ **REFUTED at cleanup 2026-09-22 (was HYPOTHESIS).** A description phrased as a *trigger* ("Use
  when …") rather than as a *summary* is NOT the shape this corpus's own standard prescribes.
  `plugin-architecture/references/frontmatter-standards.md` § Skill Frontmatter → description DOES
  state a shape rule, and it is the OPPOSITE shape: "Min length: 30 characters / Max length: 500
  characters / Should describe the standards domain covered / Single-line preferred." **Consequence,
  absorbed into this spec's scope**: deliverable 2's decision is now between (a) enforcing the EXISTING
  summary-shaped rule — already unenforced, since 8 of 157 descriptions exceed its own 500-char max
  (`manage-lessons` 721, `ext-self-review-plan-marshall` 714, `manage-references` 713,
  `persona-module-tester` 651, `plan-orchestrator` 621, `plugin-security` 587, `arch-gate-java` 519,
  `oci-standards` 501) — or (b) proposing a CHANGE to the standard toward a trigger shape, which is a
  larger, separately-justified move than "adopt what's already written". The retrieval half remains
  unverifiable — no instrument exists for it, exactly as this spec's own ⛔ already states — and is not
  grounds for choosing (b) over (a).
  - verdict: contradicted | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: instrumentation-substrate/cleanup | rescoped: yes | evidence: frontmatter-standards.md prescribes the opposite (summary, max 500 chars, single-line); 8/157 already exceed it; deliverable 2 reframed as enforce-existing vs change-standard
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
/plan-marshall task="implement .plan/orchestrator/instrumentation-substrate/plans/PLAN-05-description-surface-economy.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
