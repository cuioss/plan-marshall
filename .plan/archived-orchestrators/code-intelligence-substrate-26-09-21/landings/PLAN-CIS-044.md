# Landing Analysis: PLAN-CIS-044 — Blocking boundary arms on a call, not a state

epic: code-intelligence-substrate
workstream: WS-05
pr: 1199
merge_commit: `66a5d66`
lane: cloud-plan-lane (the `doc/plans/` export wave; NOT the plan-marshall lifecycle, so no `plan_marshall_plan_id` exists)
artifacts: `cloud-runs/110-blocking-boundary-arms-on-a-call-not-a-state/` — `plan.md`, `report-01.md`, `verification.md`, `gaps.md`

## Outcome

**completed** — 2 of 3 deliverables shipped as specified. Independent post-run audit verdict: **CONFIRMED WITH GAPS**.

D1's gate established that the finalize-phase handshake row is **universally absent** — no code path emits it, so the gate was fleet-wide inert. D2 converted the arming condition from a call to a state assertion and D3's evidenced-fix resolver is real and mutation-proven. **But the state-armed gate fires only at completion (`order: 1100`), long after the merge (`order: 70`), and its refusal is invisible to its one production caller** — `manage-status.py` exits 0 unconditionally and the archive-plan step never parses the returned status.

## Premise verdict

Confirmed and sharpened: "no finalize-phase handshake row ever existed" was confirmed **structurally** — universal, not incidental — by reading every calling workflow doc.

## Gaps carried out of this landing

**14 total — 1 high, 4 medium, 9 low.** High: G1.

- ⛔ **G1 (high) is the plan's own archetype relocated, and its audit says so in those words**: the refusal is real and mutation-proven internally, but unobservable at the one place a human or the orchestrator would notice. *The gate fires and it is indistinguishable from passing.*
- ⛔ **G1 + G2 together fully reconstruct the original defect**: the merge boundary itself is still armed by a call an LLM must issue; only the completion assertion, 1030 order-units later, is state-armed. **A skipped or mis-parsed pre-merge findings check still lets a plan merge with pending findings.**
- `normal_completion` is still advertised in help text and silently disarms the new gate.

## Inconsistencies found, and what was verified

- None beyond the audit's own.

## Residue

Fail-open on an unevaluable query is untested; D3's evidence-diff anchor can be orphaned by a loop-back rebase, resolving a finding `fixed` with no landed change.

## Reconciliation actions

- [x] row `status` -> `shipped` — `orchestrator queue --transition PLAN-CIS-044 --status shipped`
- [x] row `pr` stamped `1199` — `orchestrator queue --set-row PLAN-CIS-044 --field pr --value 1199`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-CIS-044 --field landing --value landings/PLAN-CIS-044.md`
- [ ] `plan_marshall_plan_id` — **deliberately empty**: this plan ran in the cloud plan lane and never held a plan-marshall plan id. The START-HERE completeness marker checks `pr` and `landing` only, so the row renders clean.
- [x] gaps routed to the `5xx` remediation wave (WS-07); see `## Follow-ups`

## Follow-ups

**G1/G2 are the most consequential pair in batch F** — they leave the original merge-with-pending-findings hole reachable. Route to **PLAN-CIS-052** (`540`).
