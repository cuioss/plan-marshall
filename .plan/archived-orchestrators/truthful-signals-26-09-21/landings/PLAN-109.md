# Landing Analysis: PLAN-109 — manage-lessons mixes local time and UTC

epic: truthful-signals
workstream: WS-01
pr: [#1058](https://github.com/cuioss/plan-marshall/pull/1058) — merged

⚠ **This landing was NOT reported by the operator.** Found by the orchestrator's
landed-but-unreconciled scan.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|---|---|---|
| D1 — classify intent (accidental vs deliberate) | shipped-as-specified, discharged at outline | `intent=ACCIDENTAL` on **four independent git-history lines**: `419e92b46` converged both sites on UTC; `f4c27ac72` (PR #222) reverted only `get_next_id()` to local as a side effect of adding the hour segment; #222's own body supports computing `now` once; nothing in docs/tests/comments asserts local ids are intentional |
| D2 — converge on UTC | shipped-as-specified | `get_next_id()` derives the id prefix from UTC, matching every other date field |

⭐ **The plan re-grounded its spec and corrected it in three directions rather than confirming it.**
This is the emit-time re-grounding obligation working, and the anchor's warning that PLAN-109's line
numbers were stale by construction (`manage-lessons.py` changed twice, #1039 and #1050) was correct:

- **REFUTED** — the hypothesised sequence-allocation collision. `get_next_id()` is the sole allocator
  and all three reservation scans use the same locally-derived prefix, so the scan was already
  self-consistent in any zone. **No collision existed.**
- **CORRECTED** — the claimed off-by-one in retention arithmetic. Retention was internally
  UTC-consistent all along; what diverged was the **id relative to every other date field on the same
  record**, not the retention math.
- **CONFIRMED** — same-command date divergence (id prefix vs `created`) was real and deterministic
  near a UTC/local boundary.

## Metrics and Anomalies

⭐ **Test-infrastructure defect found in flight — a direct hit on the epic's theme.** `_FakeDatetime`
in `test/plan-marshall/manage-lessons/_lessons_helpers.py` **could not express a zone divergence at
all**: its `now(tz=None)` did a bare tzinfo strip rather than projecting to local time, so a
regression test written against it **would pass identically whether the bug was present or fixed**.
The freezer had to be corrected before the regression test could ever be observed red pre-fix.

⛔ *The instrument could not see the defect it exists to detect.* Same family as the
`test_dispatch_roster_closure.py` blind spot and the vacuous `--help` freshness evidence.

**A doc-contract defect the plan itself introduced**: CodeRabbit caught, on a line **this plan
authored**, that `file-format.md` claimed an exact 3-digit sequence width while `get_next_id()`
formats with `:03d` — a *minimum*-width format that widens past 999. Fixed via loop-back TASK-4.

**Two further signal defects observed during finalize:**

- The build wrapper's outer envelope reported `duration_seconds: 0` for a `module-tests` run that
  consumed 330s and then **timed out** (inner log correctly recorded `status=timeout,
  duration_seconds=330`). ⭐ Another instance of the known outer-envelope-lies defect — and note the
  polarity: memory carries both a GREEN reported as `timeout/-1` and now a TIMEOUT reported as `0`.
- `pre-commit-verify-freshness` returned `status=fresh` with
  `matched_notation: plan-marshall:build-npm:js_coverage` **on a Python-only tree with no JS
  anywhere** — a mis-attributed ledger match. ⛔ Compounds the vacuous `--help` freshness finding
  (lesson `2026-07-29-18-004`): the gate accepts non-evidence AND mis-attributes evidence.

## Routing and Merge Behavior

⛔ **The final merged diff was seen by `pr-agent` ONLY.** Sourcery never reviewed (weekly quota).
CodeRabbit reviewed the **first** HEAD substantively but **refused the second HEAD** — the one-line
doc fix from the TASK-4 loop-back — on a rate limit.

⭐ **This is the sharpest form of the coverage gap yet**: the bot reviewed an earlier HEAD, so it
counts as having participated, while the diff that actually merged went unreviewed by it. Partial
participation reads as participation. Direct input to **PLAN-116** and **PLAN-119**.

## Reconciliation Actions

- [x] row `status` → `shipped`; `pr` = 1058; `landing` = landings/PLAN-109.md;
      `plan_marshall_plan_id` = manage-lessons-mixes-local-time-and-utc
- [x] Landing found by scan, not by report

## Follow-Ups

1. **`pre-commit-verify-freshness` mis-attributes a ledger match across build systems** — Open
   Defect; folds with lesson `2026-07-29-18-004`.
2. **Reviewed-an-earlier-HEAD counts as participation** — folded into PLAN-116's observable set.
3. Four companion candidate-lessons queued in the inbox.
