# Landing Analysis: PLAN-CIS-017 — Freshness gate cannot distinguish test-authored evidence

epic: code-intelligence-substrate
workstream: WS-05
pr: 1279
merge_commit: `e2b6665`
lane: cloud-plan-lane (the `doc/plans/` export wave; NOT the plan-marshall lifecycle, so no `plan_marshall_plan_id` exists)
artifacts: `cloud-runs/300-freshness-gate-cannot-distinguish-test-authored-evidence/` — `plan.md`, `report-01.md`, `verification.md`, `gaps.md`

## Outcome

**completed** — 4 of 5 deliverables confirmed (a companion contract change landed as #1280 / `075a646`). Independent post-run audit verdict: **CONFIRMED WITH GAPS**.

The cross-check is real, correct and mutation-proven in both directions — it refuses an unrelated notation and admits a legitimate multi-notation plan. **But D4 shipped a project-wide union rather than the plan's literal plan-scoped commands (a disclosed departure), and the guard built specifically to stop the cross-check silently degrading to a permanent no-op cannot itself detect that fault in a full-suite run.**

## Premise verdict

Confirmed on both named weaknesses, with the tier-blindness claim **refined during the run**: the ledger row itself is not tier-blind (it carries `args` / `command`) — the *gate* was. This run makes the gate read `notation` only, leaving the rest as declared, disclosed residue rather than a silently abandoned fix.

## Gaps carried out of this landing

**15 total — 1 high, 5 medium, 9 low.** High: G8.

⛔⛔ **THE LEDGER'S G1 WITHDRAWAL IS CONFIRMED AND MUST NOT BE RE-DERIVED.** The gaps entry opens with an explicit disclosure: the original claim (that the shipped 1-5 s range is roughly 2x too low) is **WITHDRAWN**. Nine fresh measurements all landed inside the shipped range; **the audit's own contradicting figures were reproduced as CPU contention from concurrent agents sharing one working tree**, not a host property. Severity was lowered medium -> low and the action narrowed to a documentation qualifier. ✅ **No fix run was sent to rewrite correct documentation.**

- **What survived and was RAISED medium -> high is a different finding, G8**: the anti-vacuity control added as the remedy for an earlier finding **fires red alone but green (25/25) when its sibling test file is collected first** — exactly reproducing the fault it exists to catch, in the configuration that gates a merge.
- The gate is **still tier-blind by design**: a `compile`-only build satisfies a verdict readers interpret as *tests are fresh*.

## Inconsistencies found, and what was verified

- Ledger's record of the G1 withdrawal | verified against the gaps entry and the nine re-measurements | **verdict: confirmed exactly as recorded.** ⭐ This is direct evidence the adversarial pass does real work — it killed a finding that would have sent a run to rewrite correct docs.

## Residue

A false "shells out to Maven/Gradle discovery verbs" mechanism claim propagated into three documentation surfaces from one authoritative docstring; a reproduced runtime-bug fix has no regression test (reverting it leaves 504 green).

## Reconciliation actions

- [x] row `status` -> `shipped` — `orchestrator queue --transition PLAN-CIS-017 --status shipped`
- [x] row `pr` stamped `1279` — `orchestrator queue --set-row PLAN-CIS-017 --field pr --value 1279`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-CIS-017 --field landing --value landings/PLAN-CIS-017.md`
- [ ] `plan_marshall_plan_id` — **deliberately empty**: this plan ran in the cloud plan lane and never held a plan-marshall plan id. The START-HERE completeness marker checks `pr` and `landing` only, so the row renders clean.
- [x] gaps routed to the `5xx` remediation wave (WS-07); see `## Follow-ups`

## Follow-ups

**G8 is the canonical `550` input** — a guard that cannot fire in the collection order that gates a merge. Tier-blindness is carried as its own future plan; the three propagated doc claims route to **PLAN-CIS-054** (`560`).
