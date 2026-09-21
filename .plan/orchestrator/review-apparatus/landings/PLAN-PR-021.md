# Landing: PLAN-PR-021 — Coverage shortfall disclosed against the roster, not the required set

epic: review-apparatus · workstream: WS-03 · shipped 2026-08-11
cloud run: `cloud-runs/050-coverage-shortfall-disclosed-against-the-roster-not-the-required-set/`
PR #1170 (`b286928c8`)

> Landing analysis over the cloud-wave corpus. `report-01.md` is the run's claim; `verification.md`
> is ground truth. Where they disagree, verification wins.

**Verification verdict: `verified-with-gaps`.**

## What landed

The two contract-touching deliverables correctly produced exact replacement text without editing
`cloud-plan-lane/SKILL.md`; the executor-free config read was settled correctly (`.gitignore:45-47`
un-ignores `.plan/marshal.json` — re-verified true today); and ten `comparison`-grade tests landed
that provably fail pre-fix.

**Deliverables: 4 — 3 done (D1, D3, D4), 1 partial (D2).**

## ⛔ The one piece of code shipped reproduces the plan's own archetype in four places

- `clean` is **unreachable in production** — no producer of `--reviewed-reviewers` exists anywhere in
  the tree.
- `measured` is earned by META records alone (the code passes `len(records)`, counting records the
  module's own contract says never inflate `actionable_count`).
- `clean` is roster-denominated, not required-denominated.
- `vacuous` asserts "no roster configured" from an argument the caller may simply have omitted.

**Standing rule: before crediting a discrimination fix, sweep for the producer of its discriminating
input.**

## ⛔ D1's proposals have gone stale and are now a REGRESSION if applied verbatim

The D1a replacement span acquired the `unreadable` verdict row (PR #1281) and the whole `Reopens?`
subsection (PR #1244) after the merge. Applying the recorded text verbatim would **delete both**.
27 commits have touched `cloud-plan-lane/SKILL.md` since `b286928c` and none applied the proposal.

## Report claims the verification found false

- "**38 passed** — including all **8** new `comparison`-grade tests" — inaccurate (stale, not
  invented): 30 at `b286928c^`, **40** at the merge, 43 at HEAD; **ten** added, all comparison-grade.
- "`cloud-plan-lane` is the **only** emitter of an 'N of M' reviewer-coverage ratio at all" —
  overstated; `review_gate_delta.py:313,345` emits `reviewer_coverage` as `covered/roster`. (It owes no
  gap — it publishes its populations beside the figure.) The roster-denominated clause holds: 3 sites.
- "The in-lifecycle mechanism is **correct** on this axis" — overstated; `check_completeness` returns
  `participation_complete: true` for an empty `required_bots` with no marker and no provenance — D3's
  own vacuous-authority archetype, live, one surface over.
- Contract-check row "ran the plan's central cold read" — overstated; the plan demanded three answers
  verbatim, only a paraphrase of Q2 appears.

## Gaps: 16 — 14 full, 2 partial, 0 uncovered

- **partial**: **G4** (major) and **G5** (minor) — both are `cloud-plan-lane/SKILL.md` contract edits.
  PLAN-PR-031 D5 re-anchors the text and **explicitly forbids touching the file**; PLAN-PR-026 D6 does
  the same for the third emission site. **A cloud-lane run can never close a `cloud-plan-lane` gap.**

⭐ **This is the finding that most changes what the ledger should do next.** Now that these plans are
ingested into the LOCAL orchestrator lane, the prohibition that produced the deadlock — *a run governed
by the contract may not amend it* — no longer binds: a `/plan-marshall` plan is not a lane run.
`050 G4`'s own Task says as much: *"Then apply — the proposal-only prohibition binds a run governed by
that contract, not a run outside the lane."* Staged as **PLAN-PR-032**.

## Standing facts

- **A metric can name its population correctly and still be defeated by shrinking it.** This run's
  verification cleared `review_gate_delta.assess` of the denominator-naming defect; plan 130's
  verification made the *same emitter* a blocker because that denominator is a caller argument. Two
  audits, one emitter, opposite verdicts, **both right**. "Publishes its population" ≠ "cannot shrink
  its population".
- **A proposal-only deliverable decays.** D1a/D1b were correct at merge and are a regression today.
  A recorded proposal against a live file needs a re-anchor step, or an owner outside the lane.
- **A legend keyed off the constants it guards is a vacuous guard** — proved by mutation here (fifth
  grade + fifth return branch, no legend entry, 43 passed unchanged). The fix for one defect created
  it. Repair before PLAN-PR-026 and PLAN-PR-030 add further grades.
