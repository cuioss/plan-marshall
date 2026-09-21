# PLAN-CIS-033: An Empty `skills_by_profile.{profile}` Is Indistinguishable From A Deliberately Minimal One

epic: code-intelligence-substrate
workstream: WS-01

> Staged 2026-08-03 from `truthful-signals-028` — item 7 of a consuming project's round-7 bundle
> findings, compiled 2026-08-01→02 against bundle **0.1.1276** and checked first-party by the filer,
> then **delegated to this epic and REMOVED from the sender's ledger**. This spec is SELF-SUFFICIENT.

## Objective

At task-allocation time, a task whose module/profile resolves **no** architecture-provided skills is
handled identically to one that resolves a **deliberately minimal** set: both degrade silently to the
persona floor. The task then runs, produces output, and **nothing reports that its methodology skills
were absent.**

Make "the inventory answered nothing" a **distinct, named condition** at allocation time, separable
from "the inventory answered, and the answer is small".

## ⭐ The masking effect is what makes this a fix rather than a note

The observed instance: a `module_testing`-profile task on the `documentation` module resolved
`[plan-marshall:persona-plan-marshall-agent]` **only** — the persona floor, with no
architecture-resolved defaults (the filer's Q-Gate finding `7e0391`).

The proximate cause was a **task mis-domaining**, and it was fixed in-plan by re-domaining the task.
⛔ **But a mis-domained task hits the SAME empty resolution as a genuinely empty inventory**, so the
symptom is easy to misdiagnose as a task-allocation bug and "fix" **without ever touching the
inventory — which is exactly what happened. The real inventory gap survived the fix.**

⇒ **Two distinct causes converge on one indistinguishable observable, and the cheaper explanation
wins every time.** That is the defect: not the empty set, but the fact that the two cannot be told
apart at the moment someone is deciding what to fix.

## Why this is ours

Architecture / inventory resolution — routing test 2, no PR/review surface. ⭐ The sender notes it is
**also** their archetype (*a signal that cannot distinguish "nothing to report" from "nothing was
looked at"*) and the same shape as two items they track: an ArchUnit rule green because it examined
nothing (`PLAN-TRUTH-042`), and a self-review reporting *"{N} candidates examined, no check matched"*
where the zero case and the no-match case are separate verdicts. **They offered to take it on the
archetype; the decision recorded here is to keep it** — the three-way rule routes by subject, and the
subject is inventory resolution. **Answer them rather than leaving the offer open.**

## ⛔ The design caveat that makes a naive fix worse than the defect

⛔ **A fix that simply ERRORS on an empty set will be worked around by inserting a placeholder skill,
and the signal is lost again — this time invisibly, because the inventory will then look populated.**

⇒ A deliberately-minimal profile needs a way to **say so**. The distinction must be expressible in
the inventory, not inferred from cardinality. This is the closed-vocabulary / fail-closed posture
`PLAN-CIS-008` and `PLAN-CIS-009` already defend, applied to skill resolution — **align with them
rather than inventing a third mechanism.**

## Deliverables

1. **D1 — GATE: re-ground against the current tree (mutates nothing).** ⚠ The finding was checked
   against bundle **0.1.1276**, which **predates our tree**. Confirm or refute that an empty
   resolution is still indistinguishable from a minimal one at allocation time **today**, and name
   the resolution site. ⛔ **Do not build on a version-stale observation.**
2. **D2 — make the two states distinguishable in the inventory.** A profile that is deliberately
   minimal must be able to declare it. Settle the mechanism against the CIS-008/009 vocabulary
   posture and **record the reasoning**, including what makes the next unmarked-empty profile
   detectable.
3. **D3 — report the named condition at allocation time.** An unresolved (as opposed to
   declared-minimal) profile emits a distinct, named condition rather than degrading silently to the
   persona floor. ⛔ **Per ADR-009's no-vacuous-success posture the condition must be reportable
   without being fatal** — an empty inventory in a consuming project is a real state, and hard-failing
   it strands that project rather than informing it.
4. **D4 — a test that fails today.** A task whose profile resolves nothing is asserted to surface the
   named condition; a task whose profile resolves a declared-minimal set is asserted **not** to. ⛔
   **Both directions, or the fix is the vacuous guard this epic keeps finding** — an assertion that
   only checks the empty case cannot detect that the declared-minimal escape hatch swallowed it.

Four deliverables (D1 a gate) — below the ~6 split guard, no split rationale owed.

## Claim Labels

- **HYPOTHESIS (second-hand, `truthful-signals-028`, filer-verified against 0.1.1276)**: the empty
  resolution is indistinguishable from the minimal one at allocation time. **D1 is this
  verification** (verify-at-outline).
- **OBSERVED (reported first-party by the filer)**: the `documentation` / `module_testing` task
  resolved the persona floor only; Q-Gate finding `7e0391`.
- ⛔ **EXPLICITLY OUT OF SCOPE**: the consuming project's own inventory gap
  (`documentation.skills_by_profile.module_testing` genuinely empty **in their repo**) is a
  **repo-side fix**, tracked as an Open Defect in *their* epic. It is **not a bundle item and not
  ours** — do not let the outline drift into fixing their data.

## Expected Surface

- **HYPOTHESIS**: the task-allocation skill-resolution site in `phase-4-plan` (verify-at-outline)
- **HYPOTHESIS**: `manage-architecture`'s `skills_by_profile` producer and its schema
  (verify-at-outline) — resolve via `architecture which-module` at outline rather than assuming
- **HYPOTHESIS**: `manage-personas resolve`, if the persona floor is applied there rather than at
  allocation (verify-at-outline)

## Dependencies and Sequencing

- **Depends on**: nothing. Wave-1 eligible.
- **Aligns with** `PLAN-CIS-008` (scope-estimate vocabulary closure) and `PLAN-CIS-009`
  (documented-enum vs argparse-choices) on the closed-vocabulary posture. ⚠ **Check surface
  disjointness before pairing with either** — a shared vocabulary mechanism is exactly the
  same-namespace-different-file shape that has cost this epic time before.
- ⚠ **Adjacent to `PLAN-CIS-029`** (architecture-store concept model): both touch the architecture
  store's schema. **Never pair.**

## Reply owed

`truthful-signals` asked whether they should take this on the archetype instead. **Answer: no —
staged here.** Send that reply; an unanswered offer is a second ledger holding the same item.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/code-intelligence-substrate/plans/PLAN-CIS-033-empty-skill-resolution-indistinguishable-from-minimal.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and
edits NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message —
the orchestrator owns every other ledger write — and reports its outcome through its PR and its
inbox message. See `persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger
Write-Boundary.
