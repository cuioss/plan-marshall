# Landing Analysis: PLAN-54 — Retrospective checker assertion integrity

epic: truthful-signals
workstream: WS-01
pr: #1015 (https://github.com/cuioss/plan-marshall/pull/1015)

> Landing record. **This landing produced evidence that REVERSED an orchestrator verdict recorded
> earlier the same day** — see § Follow-Ups, item 1.

## Deliverable Fidelity vs Spec

2/2 shipped; 21/21 finalize steps.

| Deliverable | Verdict | Evidence |
|---|---|---|
| D1 — per-deliverable detection of the Affected-files declaration | shipped-as-specified | determination moved to true per-deliverable granularity via a new `split_deliverable_blocks()` that **reuses `manage-solution-outline`'s own segmentation rather than copying the `### N.` regex a third time** — the correct call; a third copy would have been a fresh divergence source |
| D2 — pin sibling-independence end-to-end | shipped-as-specified | regression coverage for the cross-deliverable interaction |
| *(spec correction)* D1/D3/D4 of the spec were already live in #998 | correctly narrowed | **verified at ground truth, not taken on the spec's word** — the plan reduced itself to the genuine D2 residual instead of re-shipping landed work |

**Two things worth crediting.** First, the executing plan **verified the spec against reality and
narrowed its own scope** — the spec over-claimed, and the plan caught it rather than performing the
work. Second, the outline found the defect was **worse than the spec described**: the check keyed on
both the document-wide bullet union *and* `len(deliverables)`, so `not declared` was **unreachable the
moment any sibling declared a file** — a vacuous-guard instance inside the checker, sharper than the
"fails in both directions" the spec anticipated. `_AFFECTED_FILE_BULLET_RE` (the #998 fix) is
byte-identical — no collateral drift.

## Metrics and Anomalies

- 2h8m / 2.2M tokens, n=6/6 phases; quality-gate and module-tests green.
- **Review: 2 of 3 bots responded.** PR-Agent did not review — and this time the pre-merge barrier's
  `responded_bots` named only `coderabbit` and `sourcery`, so **participation is OBSERVED, not
  inferred**. See follow-up 3.

## Routing and Merge Behavior

Merged via queue; worktree removed; main clean; archived to
`.plan/local/archived-plans/2026-07-27-retrospective-checker-assertion-integrity`.
Surface collisions: none — ran concurrently with PLAN-55.

## Reconciliation Actions

- [x] status.json — PLAN-54 `launched` → `shipped`, `pr=1015`, `landing=landings/PLAN-54.md`
- [x] **PLAN-75 Defect B REINSTATED; D0 discharged** (below)
- [x] PLAN-82 strengthened — lesson `2026-07-27-08-002` is the 4th on that store
- [x] PLAN-72 — PR-Agent non-participation now observed, not inferred
- [x] epic.md + resume_anchor regenerated

## Follow-Ups

### ⛔ 1. PLAN-75 Defect B is REAL — my refutation was wrong, and this PR falsified it

This plan's own manifest is the decisive artifact. Orchestrator-verified:

- `execution.toon:31-33` sequences `lessons-capture` → **`branch-cleanup`** → **`finalize-step-preference-emitter`**,
  executed 07:06:43 and 07:07:35 on 2026-07-27.
- **Every cache live at that composition time declares `order: 61`** — `0.1.1219` (mtime 07-26T21:17),
  `0.1.1221`, `0.1.1222`. Only the long-retired `0.1.1194` ever said `80`. And `0.1.1224` was written
  at 09:00, ~2h *after* this ran, so it is irrelevant here.
- **⇒ A manifest composed against `order: 61` still sequenced the step after order 70.** The
  stale-cache explanation cannot account for it.

**The error was mine and it was a specific reasoning failure**: cache `0.1.1194` genuinely declared
`order: 80`, and I generalized that true fact about one cache into a claim about the defect. The
available conclusion was *"that 07-26 artifact cannot serve as proof"* — not *"the defect does not
exist."* Absence of usable evidence read as evidence of absence, which is this epic's subject matter.

**What worked:** the refutation was recorded with a falsifiable prediction — *"the step should sort to
61 and Defect B should close."* It was falsified within hours by the next plan to finalize. Without
that prediction the wrong verdict would have sat in the ledger until PLAN-75 executed and found
nothing. **Keep stating expectations in advance.**

⚠ **This PR's own narrative classified the inversion "latent-not-triggered."** Correct that nothing
cleared the promotion threshold on this run; **incorrect that it is therefore not a defect.** Its own
stated consequence is the point: *"if a pattern ever does, the edit lands post-merge and cannot ride
the PR."* A `mutates_source` step scheduled past the merge gate is a latent false-green.

### ⛔ 2. `2026-07-27-08-002` — the freshness gate is TIER-BLIND. Fourth lesson on one store.

*"`pre-commit-verify-freshness` returns fresh on a tree whose tests never ran. The `kind=build` ledger
row is tier-blind, so the gate's predicate is strictly weaker than the claim its consumers read."*

**Folded into PLAN-82**, and it changes that plan's shape: PLAN-82 was scoped on the gate accepting
*unrelated* evidence (wrong notation). This is a second, independent weakness — the evidence can be
*related* and still insufficient, because a `kind=build` row does not record which tier ran. The
gate's predicate and its consumers' reading have diverged in two different ways.

**The framing to keep is the lesson's own: "one structural gap, not four bugs."** Four lessons on the
same store is the tell that the store's evidence model — not any individual gate — is under-specified.
PLAN-82's D1 must address the model, not add a second special case.

### 3. `2026-07-27-08-003` — a task asserted coverage that did not exist

*"TASK-2 asserted `extract_deliverables` coverage that did not exist, making deliverable 1's success
criterion vacuously true and unverifiable."* Closed in-plan by the plan's own TASK-4; **the authoring
rule is the reusable part.** Adjacent to **PLAN-81** (in-house review cannot see an unreachable
predicate) — same family, one layer earlier: here the *success criterion* was vacuous rather than a
guard. Cross-linked; no separate plan.

### 4. PR-Agent participation — the discharge stands, the reliability does not

PR-Agent did **not** review this PR; `responded_bots` named only coderabbit and sourcery. This does
**not** reverse the #1013 discharge (it did publish a valid, sharper-than-CodeRabbit finding there —
that artifact exists). It does mean **participation is erratic across consecutive PRs**: #1013 yes,
#1014 silent-behind-green, #1015 absent. **Recorded into PLAN-72** — a quorum keyed on *configured*
bots would have counted 3 on all three PRs.

### 5. `2026-07-27-00-001` (merged) — routed build reported green verify as timeout

*"the daemon conflated 'I stopped waiting' with 'the job failed'"* — 12635 passed, `verify: SUCCESS`,
reported as `timeout / exit_code -1`. This is the inverse polarity of the standing
never-trust-a-routed-build's-outer-status rule (that one hides failure; this one manufactures it).
Already merged into the existing lesson; **no plan staged** — but note the standing memory rule
currently warns only about false *green*, and false *red* from the same seam is now observed.

### Operator-owed

`marshal.json` provisioning stamp still behind installed. `/marshall-steward` refreshes it.
