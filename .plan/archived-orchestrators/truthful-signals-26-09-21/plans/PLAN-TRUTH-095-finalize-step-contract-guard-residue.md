> ⛔ **STAGED AT THE 2026-08-22 INGESTION — this plan closes REMEDIATION RESIDUE.**
>
> It exists because the gap-fix plans `500`/`510`/`520` ran **after** the epic audit closed, so every
> gap they filed, and every gap they left partially closed, is owned by no other staged plan. This was
> found by re-deriving ownership over the whole live gap set at ingestion: **218 gaps open, 38 unowned.**
>
> **Re-ground every gap below at HEAD before implementing it.** Its source is
> `cloud-runs/{NNN}-{slug}/gaps.md` in this ledger (git-ignored, ingested from `doc/plans/`), and a
> gap document is a snapshot. Line numbers in it are **leads, not addresses**; locate by quoted text.
> A gap that no longer reproduces is recorded as *already closed by `{sha}`* and **dropped, never
> re-fixed**.
>
> ⛔ **A run report is a dated record.** No deliverable here corrects one. Where a gap's `Where` names
> an archived `report-01.md`, the correction of record is the gap entry itself; only a live restatement
> is actionable, and it must be re-derived.

# The finalize-step contract's guards are narrower than the contract they enforce

**Epic:** truthful-signals
**Branch prefix:** fix
**Source gaps:** `510/G1`–`G9` (`cloud-runs/510-finalize-step-contract-ordering-and-refire-currency/gaps.md`)

## Problem

Plan `510` (PR #1309) is the corpus's largest gap-closer — 33 upstream gaps genuinely closed. It also
left two `high` defects of its own, and both are the shape it was written to remove.

**The central mechanism fires on an undocumented magic string.** The input-table conformance scope that
`ext-point-finalize-step.md` itself calls *"where the contract is actually held"* fires only on tables
whose first header cell is the literal `Prompt-body field` — a convention stated in **no normative
document**. A matched positive/negative control differing only in that header flips the suite from RED
to 19-passed-green.

**A dead config key still persists.** `phase-6-finalize set --field self_review` still succeeds and
writes a key nothing reads. `510`'s own D4 preamble diagnoses this as *"a shipped false signal on the
highest-risk gate the page describes"* — and then fixes only the documentation half, with no residue
entry. Upstream `190/G6` is therefore closed for its prose and **open for its code**.

## Goal

Every finalize-step contract guard derives its own scope from a documented rule, and the config surface
refuses a key it does not read.

## Deliverables

**D0 — GATE: derive the guard population and each guard's actual scope.** For every conformance guard
over the finalize-step contract, state the population it examines and the rule by which it selects it.
Publish examined-vs-selected as two numbers. *(gates D1–D5.)*

**D1 — the input-table guard selects by a documented rule.** *(closes 510/G1 — high)*
Either normalise the header convention into `ext-point-finalize-step.md` as a stated requirement and
test it, or select tables structurally. **Either way a matched control differing only in the header
must go RED.**

**D2 — `set --field` refuses a key the reader does not accept.** *(closes 510/G2 — high; completes 190/G6)*
`get --field self_review` errors while `set --field self_review --value banana` returns `success`.
Make the write path reject exactly what the read path rejects, and pin the asymmetry closed.

**D3 — the wildcard-free glob guard cannot examine zero globs silently.** *(closes 510/G3)*
If every declaration goes wildcard-bearing the guard examines nothing and passes. Add a non-vacuity
floor that publishes the examined count.

**D4 — bind the baseline-reconcile reason/error tables to the script.** *(closes 510/G4, 510/G9)*
Two new tables and the settle-band occupancy list restate a population with no binding test.

**D5 — retire the last "derived" label that is not derived, and the stale figures.** *(closes 510/G8, 510/G6, 510/G7)*
`_gate_coverage.py:417` still calls the parity population "derived"; `510`'s own § Cost figure (52 vs
58) shipped into the PR body and the squash commit message; its participation figure used a floating
endpoint. Fix the live one and record the rest.

**D6 — a finalize step MUST NOT prescribe an action illegal at its own order.** *(folded 2026-08-23 from PR #1330 / L2 — CORROBORATED first-party)*
`standards/architecture-refresh.md` declares `order: 10` and prescribes `git -C {worktree_path} push`
at four sites (lines 220, 358, 526, 562). `default:push` is `order: 11` and the SKILL states "there is
exactly ONE push", so at order 10 the branch has no upstream and the call fails
(`fatal: The current branch ... has no upstream branch`). The doc's own Error Handling table then routes
that failure to `mark-step-done --outcome failed` — and `architecture-refresh` is required in the
`phase_steps_complete` handshake, so a literal implementation BLOCKS the phase transition on a
structurally-guaranteed condition. Its Tier-1 non-enrich branches additionally call
`ci pr view/edit --pr-number` (lines 305, 550) while `default:create-pr` is `order: 20`.
**Preferred remedy (from the source lesson): drop the push from this step** and let the order-11
barrier ship the commit — it preserves the settle band, which moving the step after `create-pr` would
break. Re-home the Tier-1 PR-note branches as an owed follow-up rather than a write they cannot land.
⛔ Verify at HEAD before fixing: `order: 10` / `order: 11` / `order: 20` were each re-confirmed
2026-08-23 (`architecture-refresh.md:7`, `push.md:7`, and `finalize-step-sync-baseline.md:32`, which
states both sibling orders independently).

**D7 — the `Completed step` line must carry the outcome it already holds.** *(folded 2026-08-23 from PR #1330 / L6 — CORROBORATED first-party)*
`_cmd_mark_step.py:215` emits `[STEP] (plan-marshall:phase-{phase}) Completed step: {step}` with **no
outcome field**, and it is emitted from `_emit_completion_log`, called on the `mark-step-done` path
that has the terminal outcome in hand. A failed firing is therefore indistinguishable from a passing
one in `work.log`: the source run logged three `Completed step` lines for `pre-push-quality-gate` whose
`phase_steps` recorded `firing_count: 3, prior_firings: [failed, failed]`. The second channel is not a
backstop — that middle firing wrote **no** `record-step` row at all.
**Remedy:** append the recorded outcome at the same site
(`Completed step: {X} (outcome={done|failed|loop_back})`), and ensure every firing writes a
`record-step` row — a firing that logs a completion and records nothing is invisible to
`reconcile-ledgers`. ⭐ This is the same fused-emission argument the function's own docstring already
makes for *why* the line rides the write; it simply stops one field short.

## Expected Surface

- `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-finalize-step.md`
- `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_finalize_steps.py`
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-push-quality-gate.md`
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/_gate_coverage.py`
- `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/_cmd_baseline_reconcile.py`
- `test/plan-marshall/phase-6-finalize/test_step_records_facts_contract.py`
- `test/plan-marshall/phase-6-finalize/test_finalize_edge_ordering.py`

- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/architecture-refresh.md` *(added 2026-08-23, D6)*
- `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_mark_step.py` *(added 2026-08-23, D7)*
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/push.md` *(added 2026-08-23, D6 — read-only cross-check; ⚠ shared with PLAN-TRUTH-097)*

## Out of scope

- Correcting any archived `report-01.md` under `cloud-runs/` — a run report is a dated record; see the
  banner. Where the same false claim is restated on a live surface, that restatement is in scope and
  must be re-derived rather than inherited from the gap's `Where` line.
- Any gap owned by another staged plan. Ownership was derived at ingestion; if a re-derivation shows
  an overlap, **record it and serialize**, do not silently absorb the sibling's gap.
- Re-fixing a gap that no longer reproduces at HEAD.

## Claim Labels

Every claim in this plan is **HYPOTHESIS** unless the deliverable marks it otherwise. The gap entries
it derives from were OBSERVED at their verification commit and re-checked at the 2026-08-22 ingestion,
but that check was per-gap and sampled, not exhaustive. **Treat every asserted absence as unverified
until the D0 gate re-derives it.**

## Verification

- The D0 gate publishes the population it examined **and** the count that reproduced, as two separate
  numbers. A zero must state which zero it is: *examined N, none reproduced* is a result; *could not
  look* is not.
- Every guard added or widened here is proved by a **matched positive/negative control** — a case that
  goes RED against the defect the guard names, and a near-identical case that stays green. A guard
  whose population can be empty publishes its population size on a clean run.
- No deliverable is reported complete on a read alone where the claim is about behaviour: execute the
  symbol, or mutate it and observe the red.

## Notes

**Derived figures are re-derived AFTER the review cycle closes, not before.** Both `500` and `520` had
their diff silently widened by CodeRabbit after their counts were taken, and `510`'s own participation
figure used a floating `origin/main` endpoint three sections after its own § Build gate corrects that
exact defect. The review is a diff-widening event. Take every count last.
