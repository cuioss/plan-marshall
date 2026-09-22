# Landing Analysis: PLAN-CIS-045 — Generator fails open and its fixtures cannot see it

epic: code-intelligence-substrate
workstream: WS-05
pr: 1164
merge_commit: `a3a4da6`
lane: cloud-plan-lane (the `doc/plans/` export wave; NOT the plan-marshall lifecycle, so no `plan_marshall_plan_id` exists)
artifacts: `cloud-runs/040-generator-fails-open-and-its-fixtures-cannot-see-it/` — `plan.md`, `report-01.md`, `verification.md`, `gaps.md`

## Outcome

**completed** — 1 of 3 deliverables fully confirmed. Independent post-run audit verdict: **CONFIRMED WITH GAPS**.

The fail-open guard, the population-derived fixture and the required regen-smoke all landed and work. **But the guard's refusal exits 0** — not the non-zero the plan and four shipped statements claim — so a real consumer (`test/conftest.py`'s `check=True` bootstrap) is blind to it. And **72.6% of D2's "population-derived" corpus can never detect any derivation defect**, because the validator short-circuits before reading the surface.

## Premise verdict

Confirmed on both arms — the generator genuinely returned `status: success` over a zero-surface derivation, and every hand-built fixture did declare at least one flag pre-fix. ✅ **Standing question answered: the fail-open IS closed** (mutation-proven: forcing the stats line conditional turns a dedicated test red), **but the guard is only partially non-vacuous.**

## Gaps carried out of this landing

**15 total — 2 high, 10 medium, 3 low.** High: G1, G9.

- ⛔ **Do not credit the 2412-check population figure as coverage.** 1750 of 2412 checks (the help-spelling half) are **surface-insensitive by construction** — no derivation strip can ever redden them.
- **The exit-0-vs-non-zero confusion is now baked into four shipped surfaces** (two code comments, a `SKILL.md` line, the merged commit message). The repo's own `manage-contract.md` forbids a non-zero here, so **the plan was wrong, not the run** — but the consumer is still blind.
- G9 (high): dry-run publishes a false `scripts_registered: 0`.

## Inconsistencies found, and what was verified

- Report claims the refusal yields "`status: error`, non-zero exit" | verified live via the unmocked CLI three times, plus a read of `main()` and `manage-contract.md` | **verdict: it exits 0** — the report and four shipped statements assert a contract the repo's own convention forbids.

## Residue

A stale "four guards" enumeration survives at two sites after the sweep claimed all were fixed; the stats line is not truly unconditional on two early-return paths; `read_previous_surfaces` cannot distinguish *no previous* from *unreadable previous*.

## Reconciliation actions

- [x] row `status` -> `shipped` — `orchestrator queue --transition PLAN-CIS-045 --status shipped`
- [x] row `pr` stamped `1164` — `orchestrator queue --set-row PLAN-CIS-045 --field pr --value 1164`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-CIS-045 --field landing --value landings/PLAN-CIS-045.md`
- [ ] `plan_marshall_plan_id` — **deliberately empty**: this plan ran in the cloud plan lane and never held a plan-marshall plan id. The START-HERE completeness marker checks `pr` and `landing` only, so the row renders clean.
- [x] gaps routed to the `5xx` remediation wave (WS-07); see `## Follow-ups`

## Follow-ups

The exit-code contract confusion needs a dedicated doc fix and routes to **PLAN-CIS-054** (`560`); the surface-insensitive half routes to **PLAN-CIS-053** (`550`).
