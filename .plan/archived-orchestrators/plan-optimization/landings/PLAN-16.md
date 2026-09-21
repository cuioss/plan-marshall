# Landing Analysis: PLAN-16 — planning-phase-checkout-guard

epic: plan-optimization
workstream: WS-08
pr: 945 — https://github.com/cuioss/plan-marshall/pull/945 (merged `a4ba622ec`)

> Landing record for one shipped plan. Claims verified against ground truth: PR #945 confirmed
> `state: merged` via the CI abstraction; merge commit `a4ba622ec` present on `origin/main`; the
> merged diff inspected (`git show --stat`) — the 6 files match the two-deliverable claim exactly
> (runtime guard in `planning-outline.md` + static complement in `_analyze_phase2_refine_contract.py`).

## Deliverable Fidelity vs Spec

The staged spec carried a single deliverable **D1** (enforce the planning-phase no-main-mutation
invariant) with the explicit outline instruction to **confirm the seam** — Q-Gate vs phase-boundary
post-condition vs execution-context write-guard. At outline the seam resolved to **(b) phase-boundary
clean-main assertion + static plugin-doctor complement**; (a) Q-Gate (validates outline *content*, can't
observe a filesystem write) and (c) execution-context write-guard (unowned tool layer, overlaps
out-of-scope PLAN-03) were rejected. D1 was delivered as two complementary halves.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 (runtime half) — block planning→next-phase on a dirty main | shipped-modified (seam confirmed at outline) | `planning-outline.md` (+106): `git -C . status --porcelain` clean-main assertions at Step 2c (`outline_contract_violation`, refuses 3-outline→4-plan) and Step 4b (`plan_contract_violation`, refuses 4-plan→5-execute), mirroring `planning.md`'s proven phase-2-refine block; **no assertion at any phase-5/worktree boundary** so legitimate worktree edits are unaffected |
| D1 (static half) — plugin-doctor complement | shipped-added (decomposed from D1) | `_analyze_phase2_refine_contract.py` (+159): generalized from a single phase-2-refine scan to a phase-dir→rule-id map emitting `outline-contract-violation` / `plan-contract-violation` (`RULE_DESCRIPTOR`→`RULE_DESCRIPTORS`, public fn name retained for import stability) + `rule-provenance.md` rows + `_doctor_analysis.py` wiring + regression tests (+206) |

Net: 2/2 (the spec's single D1 delivered both a runtime assertion and its static complement — the
belt-and-suspenders shape phase-2-refine already ships). Acceptance holds precisely: a planning-phase
main-checkout edit is blocked at the phase boundary; a worktree edit is not.

## Metrics and Anomalies

- Tokens: ~2.2M
- Duration: 1h21m worked / 3h56m wall
- Anomalies:
  - **marshalld daemon contaminated whole-tree module-tests** — the runner stopped and restarted the
    live daemon because whole-tree module-tests produced **8 spurious failures**: the live daemon made
    the script-shared build-queue unit tests route real builds to it. **Not a regression — reproduces on
    main.** Stopping the daemon gave clean runs; it was restarted at the end. Captured as lesson
    `2026-07-19-22-001`. Build-server (plan-server epic) surface artifact, not a PLAN-16 defect — re-homed
    into this epic's existing build-server watch (see Follow-Ups), not opened as new work here.

## Routing and Merge Behavior

- Review: **Pre-submission self-review caught 2 real contract-drift defects** (a stale `_doctor_analysis.py`
  comment and a missing phase-4-plan enforcement bullet) — both fixed inline and folded into the PR.
  Review bots: 2 Gemini micro-optimization suggestions accepted-but-deferred (deliberately avoided a
  ~15-min loop-back for a cosmetic change), 1 Sourcery rate-limit notice rejected as noise (the
  bot-agnostic rate-limit class — the open 13-21-001 follow-up).
- CI/merge: all 22 finalize steps green; squash-merged via the **merge queue**; worktree removed, branch
  deleted, on-main executor regenerated (v0.1.1156). **No rebase conflict with PLAN-11** — the predicted
  phase-4 adjacency did not bite (PLAN-16 added a single phase-4 SKILL.md bullet, disjoint from PLAN-11's
  Step 11b).

## Reconciliation Actions

- [x] status.json `plans[]` entry updated — PLAN-16 → shipped, pr 945, plan_marshall_plan_id `planning-phase-checkout-guard`, landing recorded
- [x] epic.md queue reconciled from status.json (WS-08 row 16)
- [x] Watch retired — the graduated "Planning-phase edit of the MAIN checkout (n=2)" watch is now CLOSED by enforcement (it had graduated to PLAN-16; PLAN-16 shipped)
- [x] resume_anchor updated
- [x] START-HERE block regenerated

## Follow-Ups

- **Lesson `2026-07-19-22-001`** filed (live+registered marshalld contaminates script-shared build-queue
  unit tests in a whole-tree run; stop the daemon for clean runs) — a build-server surface artifact.
  Re-homed into this epic's **build-server inert watch** (owned by the plan-server epic); no new work
  opened here.
- **`step_record_mismatched_key` recurrence** — PLAN-16 merged a mark-step-done key-form-mismatch into
  `2026-07-13-12-003` (project:/default:-prefixed finalize steps record under a key mismatching the
  manifest `step_id`). Same class as this epic's `step_record_mismatched_key` watch — **n keeps climbing;
  now a very strong promote candidate** (finalize step-key hygiene plan).
- **Phase-5 occurrence `2026-07-17-17-001` retained, NOT absorbed** — PLAN-16 enforces only the
  *planning-phase* (3-outline/4-plan) invariant; the phase-5/worktree occurrence is deliberately out of
  scope and remains a standing lesson. Correct scoping — do not conflate.
