# Landing: PLAN-PR-023 — A foreign task reports done with no PR anywhere

epic: review-apparatus · workstream: WS-02 · shipped 2026-08-10
cloud run: `cloud-runs/020-a-foreign-task-reports-done-with-no-pr-anywhere/`
PR #1151 (`9c679c999`)

> Landing analysis over the cloud-wave corpus. `report-01.md` is the run's claim; `verification.md`
> is ground truth. Where they disagree, verification wins.

**Verification verdict: `verified-with-gaps`.**

## What landed

All three deliverables landed and survive under the names the report gives — the `landing-state` verb,
`LANDING_STATES`, `is_foreign_path`, `_annotate_foreign`, `foreign_pr_gate.check` and the
`archive-plan.md` wiring all exist, and 56 named tests pass.

**Deliverables: 3 — 1 done (D0, on partly false evidence), 2 partial.**

## ⛔ The gate clears in three ways it must not

- On a deliverable payload carrying **no** `foreign` classification at all — the exact bytes the
  fail-open classifier emits when it cannot resolve the project root.
- On `unpushed`, which by definition has no PR anywhere. Re-verified at HEAD:
  `foreign_pr_gate.py:78 BLOCKING_LANDING_STATE = 'pushed_no_pr'` — a single state, not a set, pinned
  by `test_unpushed_foreign_deliverable_clears`.
- Compounding: `unpushed` is derived from `git branch -r --contains` with **no** `fetch`/`ls-remote`
  anywhere in the landing-state path, so a stale remote-tracking ref makes a **pushed** branch read
  `unpushed` — and clear.

And it never passes the `--branch` its own D1 signature specified, so it classifies whatever ref the
foreign checkout happens to have out. Re-verified: `--branch` appears nowhere in `foreign_pr_gate.py`.

## ⭐ A test named for a boundary is not a test of that boundary

`test_pushed_no_pr_foreign_deliverable_is_refused_at_archive` asserts on `check()` through three
injected seams — no archive traversal. Re-verified: `foreign_pr_gate` has **4** references across
source and tests and **no code caller**; deleting the whole gate section from `archive-plan.md` breaks
nothing. Same archetype as the epic's standing *N passing checks of a pure function* rule.

## Report claims the verification found false

- "`done` is written in exactly one place: `_tasks_crud.py::cmd_update`" — **false**. Re-verified:
  `_cmd_step.py:73` writes it too, and that is the path the phase-5 runner drives. **Any plan that
  moves enforcement to "the" completion seam will miss one.**
- "plus the archive-refusal test proving a `pushed_no_pr` foreign deliverable is `blocked`" —
  overstated (above).
- "the gate fails closed … an unresolvable project root yields `status: error`" — narrower than it
  reads: the classification runs in the `list-deliverables` subprocess, which resolves its own root and
  fails **open**.
- "the coverage column distinguishes the two populations" — data availability only; no consumer
  computes a split.
- § Build gate `15848 passed` vs § Contract check `15859 passed` — internally inconsistent, both
  presented as the green run.

## Gaps: 19 — 17 full, 2 partial, 0 uncovered

- **partial**: **G4** (major — read-intent and survey-scope foreign paths enter the blocking
  population; PLAN-PR-028 D6 records both options and their failure modes and **changes nothing**. The
  deadlock is real: `deliverable_write_set` (#1283) says exclude read intent, while `survey_scope` was
  added to the gate's field list deliberately (#1295) with a test pinning "the whole declared surface".
  **Needs an operator decision → staged as PLAN-PR-033**), G6 (minor — the *enforcement* hole, that an
  executing agent can ignore correct prose, is the house convention for all eight `phase-6-finalize`
  scripts; carried as an epic-level open item, not a plan)

## Standing facts

- ⛔ **This run's report carries a live false finding a later plan will trip on.** Treat its §D0
  "one `done` writer" as wrong until PLAN-PR-028 D5 lands.
- ⚠ **`080 G10` is already partly discharged on main and PLAN-PR-028 D0 does not know it.**
  `dispatch-inline-split.md:49` now carries a `default:emit-landing` inline roster row, and the tracked
  `.plan/marshal.json` holds **26** steps including `emit-landing` — not the 25-without-it the gap
  describes. A run must re-derive D0(c) before editing.
