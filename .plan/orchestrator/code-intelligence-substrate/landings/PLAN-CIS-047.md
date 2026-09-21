# Landing Analysis: PLAN-CIS-047 — Outline derived-set closure integrity

epic: code-intelligence-substrate
workstream: WS-05
pr: 1295
merge_commit: `63943f5`
lane: cloud-plan-lane (the `doc/plans/` export wave; NOT the plan-marshall lifecycle, so no `plan_marshall_plan_id` exists)
artifacts: `cloud-runs/350-outline-derived-set-closure-integrity/` — `plan.md`, `report-01.md`, `verification.md`, `gaps.md`

## Outcome

**completed** — 5 of 6 deliverables confirmed (run 01 operator-halted; resumed and landed as run 02). Independent post-run audit verdict: **CONFIRMED WITH GAPS**.

All three closures — projection, referrer and claim-vs-index — plus the population-completeness assertion shipped, wired unconditionally so that *closure is a hint, not a licence* is a **structural** property: an adversarial bypass injection kills exactly the one test built to catch it. **But a real coverage hole survives**: a declared write-set glob matching zero files is enforced by NEITHER closure, so a `write-new` pattern for a not-yet-created file passes clean with `population_complete: True` — on the exact deliverable class this plan exists to make checkable.

## Premise verdict

Confirmed **and sharpened at D0**: the run's own gate found the survey-scope declaration fields were not merely unreconciled (the plan's claim) but **parsed by nothing** — a deliverable authored exactly per the standard failed outline validation outright, which is stronger than and subsumes the original claim. D0 also **sited** the routing-decision claim that PLAN-CIS-015 left unsited.

## Gaps carried out of this landing

**19 total — 0 high, 11 medium, 8 low.** No high-severity entries.

- **This row did not exist in the ledger before this ingest.** It is Arm A of PLAN-CIS-015, split off per that plan's own mandate, and is assigned `PLAN-CIS-047` here.
- ⛔ **A record-integrity defect specific to this plan's two-session resume**: two of run 01's eleven pushed commits never reached the PR branch during the cross-session rebase, so `report-01.md` carries a stale commit count and a "pending" build-gate line that was already resolved, while `report-02.md` asserts "nine commits, every tree preserved". **Both are false**, and every commit SHA is now unresolvable post-squash-merge. **This is itself a first-party instance of the record-vs-reality gap this epic tracks.**
- ⭐ **A CI-only-catchable defect was found by CI, not by four internal verification rounds nor the audit** — direct corroboration of the standing rule that N passing checks of a pure function is one assertion repeated N times.

## Inconsistencies found, and what was verified

- `report-01.md`'s commit count and build-gate line vs `report-02.md`'s "nine commits, every tree preserved" | verified against the PR branch | **verdict: both false**; the drop mechanism (a genuine rebase drop vs a fetch taken before run 01's last push) is **not determinable from the tree** — both remain equally consistent with the evidence.

## Residue

The characterization-corpus rule was genuinely applied but is **codified nowhere normative** — the same *prose warning is not a control* failure the plan's own overview names, committed inside the plan meant to end it. Fourteen shipped documentation surfaces still assert a false composition step.

## Reconciliation actions

- [x] row `status` -> `shipped` — `orchestrator queue --transition PLAN-CIS-047 --status shipped`
- [x] row `pr` stamped `1295` — `orchestrator queue --set-row PLAN-CIS-047 --field pr --value 1295`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-CIS-047 --field landing --value landings/PLAN-CIS-047.md`
- [ ] `plan_marshall_plan_id` — **deliberately empty**: this plan ran in the cloud plan lane and never held a plan-marshall plan id. The START-HERE completeness marker checks `pr` and `landing` only, so the row renders clean.
- [x] gaps routed to the `5xx` remediation wave (WS-07); see `## Follow-ups`

## Follow-ups

G8's glob coverage hole routes to **PLAN-CIS-051** (`530`) with the audit's stated fix direction (a projection obligation, **not** referrer relaxation — the audit caught a first proposed Done-when that would have broken a deliberate guard). The 14 doc surfaces route to **PLAN-CIS-054** (`560`).
