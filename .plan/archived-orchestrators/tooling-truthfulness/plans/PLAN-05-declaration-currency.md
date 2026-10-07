# PLAN-05: A declared surface that is no longer true

epic: tooling-truthfulness
workstream: WS-01

> Staged plan spec — one shippable unit of work. SELF-SUFFICIENT.

## Epic Constraints (bind every deliverable)

- **ADR-019 binds reflexively:** every guard is red-first.
- **Confirm the Expected Surface against the tree as the first action.** ⛔ A surface expansion updates this section IN THE SAME ACT — a rule this plan is itself about.

## Objective

PLAN-04 asks whether the gate can COMPARE two declarations. This plan asks whether either
declaration is still TRUE. Two mechanisms let a spec's `## Expected Surface` drift away from reality
while the gate goes on reading it. A staged spec's work list decays as siblings land — PLAN-05 of
`multiplattform` closed two of PLAN-12's named D1 sites and nothing noticed, because no mechanism
compares a LANDED plan's realized footprint against OTHER staged specs. And a running plan that
expands its surface discloses it in the PR body and the landing report but never in the spec — three
consecutive instances, so the pattern is established: **plans disclose reliably and declare never.**

⛔ The two failures point opposite ways. Decay leaves a spec claiming work that no longer EXISTS —
which no gate reads at all, so a plan launched on it finds nothing to change and either reports a
no-op or invents work to justify the deliverable. Expansion leaves a spec claiming LESS surface than
it touches — which the gate does read, and mis-clears.

## Deliverables

1. **D1 — a landed footprint is reconciled against other staged specs' declarations.** Today two reconciliations exist and neither covers this: the plan lifecycle derives a landed plan's realized footprint, and cleanup re-grounds a staged spec's own claims. ⛔ `corpus cross-check` CANNOT close it — it compares DECLARED surfaces, so it reports a collision, which is a different statement from *this work is already done*.
   *Done when:* a read surface reports, for each staged spec, which of its declared paths a landed plan has since touched — enough for the A2 positive-account rule to be applied without a manual sweep. Red-first, with a matched control where a spec whose sites are untouched reports clean.
2. **D2 — the same-act surface obligation reaches an in-flight expansion.** The obligation binds the orchestrator when it FOLDS into a staged spec; it says nothing about a plan already running that widens its own scope, whether operator-authorised or emergent. ⛔ **Stating the rule in the spec was TRIED and did not bind** — PLAN-22 carried it explicitly, worded against the previous landing's failure shape (*"if D1's remedy needs a platform-runtime op"*), and its remedy needed a shared helper instead, so the antecedent never fired.
   *Done when:* a surface expansion is DETECTABLE at landing without a manual diff — the drain can compare realized footprint against declared surface and report the delta as a first-class field. ⚠️ **This deliverable is a mechanism, not a rule.** Another prose obligation is precisely what has already failed three times; do not ship a fourth wording.

## Claim Labels

- OBSERVED: `multiplattform`'s PLAN-05 (`30cd8aaf8`, #1379) closed two of PLAN-12's three named D1 sites — both measured **0** hits at `a83389fdb` — while PLAN-12 sat staged, and no surface reported it. Read at `landings/PLAN-12.md` and the `multiplattform` Open Defects.
  - verdict: corroborated | checked_at: 5c18ef918 | by: tooling-truthfulness/cleanup | rescoped: n/a | evidence: multiplattform PLAN-05 landed (#1379) and its landing record documents closing two of PLAN-12's named D1 sites - historical record corroborated by the multiplattform landings tree
- OBSERVED: three consecutive disclosed-but-undeclared expansions — PLAN-10's D4 (19 undeclared paths), PLAN-22's shared helper (2), PLAN-12's two — each disclosed honestly in the PR body and landing report, each leaving `corpus surfaces` unchanged. Read at those three landing records.
  - verdict: corroborated | checked_at: 5c18ef918 | by: tooling-truthfulness/cleanup | rescoped: n/a | evidence: three disclosed-but-undeclared expansions recorded in multiplattform landings (PLAN-10 D4, PLAN-22 shared helper, PLAN-12) - historical record corroborated by the multiplattform landing records
- OBSERVED: `manage-references` already carries a three-way reconciliation of declared, derived and realized footprint WITHIN one plan — read at its SKILL.md. ⭐ D1 may be able to consume that rather than build a second comparison; the missing half is the CROSS-SPEC direction, not the comparison itself.
  - verdict: corroborated | checked_at: 5c18ef918 | by: tooling-truthfulness/cleanup | rescoped: n/a | evidence: manage-references scripts/_cmd_reconcile_scope.py implements three-way reconciliation (SIDE_A references.affected_files / declared derivation / realized_footprint) and _cmd_compute_footprint.py persists realized_footprint - the three-way surface exists
- HYPOTHESIS: D2's delta can be computed entirely at drain time from data the orchestrator already has (the merged diff and `corpus surfaces`) with no new plan-side obligation — confirm/refute at `analyze.md` Step 4 before scoping (verify-at-outline). ⛔ If true, D2 is a report field and not a contract change, which is the outcome to prefer.
  - verdict: unverifiable | checked_at: 5c18ef918 | by: tooling-truthfulness/cleanup | rescoped: n/a | evidence: whether D2's delta is fully computable at drain time from merged diff + corpus surfaces is a design settlement for the launched plan's outline (analyze.md Step 4); not settleable from a static read - the drain already holds the diff, but the field-shape decision is outline's
- Verify-first clause: **do not ship a prose rule for D2.** Three wordings have failed. If the outline concludes the only available remedy IS a rule, that is a refutation of this deliverable's premise — loop back and re-scope rather than shipping a fourth.
  - verdict: unverifiable | checked_at: 5c18ef918 | by: tooling-truthfulness/cleanup | rescoped: n/a | evidence: whether a prose rule is the only available D2 remedy is the launched plan's outline settlement (the spec itself loops back to re-scope on refutation) - not source-settleable

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py` — D1, D2
- OBSERVED: `test/plan-marshall/plan-orchestrator/**` — the red-first guards
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-references/**` and `test/plan-marshall/manage-references/**` — only if D1 consumes or extends the existing three-way reconciliation rather than reading footprints directly (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none, but **runs best AFTER PLAN-04** — D2's delta report is more useful once the comparison it feeds is sound, and both edit `orchestrator.py`.
- Overlaps with: **PLAN-01** and **PLAN-04** at `orchestrator.py`. ⛔ Not concurrent with either.
- Adjacent to: the plan lifecycle's own footprint capture, which this plan does NOT edit. The declared side is the orchestrator's; the realized side is the plan's. ⛔ Building one mechanism across both stores is the failure that split is designed to prevent.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/tooling-truthfulness/plans/PLAN-05-declaration-currency.md"
```

## Write-Boundary

The plan touches only its own repository source and tests. It creates and edits NO file under
`.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
