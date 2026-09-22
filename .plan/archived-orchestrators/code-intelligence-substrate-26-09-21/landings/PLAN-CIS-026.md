# Landing Analysis: PLAN-CIS-026 — LSP derivation resolver

epic: code-intelligence-substrate
workstream: WS-02
pr: 1243
merge_commit: `c86de8b5a`
lane: cloud-plan-lane (the `doc/plans/` export wave; NOT the plan-marshall lifecycle, so no `plan_marshall_plan_id` exists)
artifacts: `cloud-runs/200-lsp-derivation-resolver/` — `plan.md`, `report-01.md`, `verification.md`, `gaps.md`

## Outcome

**partial** — 2 of 6 deliverables confirmed. Independent post-run audit verdict: **PARTIALLY REFUTED**.

The resolver is registered and never yields a silent zero-edge success — but **on this repository it derives ZERO module edges.** No cross-bundle reference resolves, because marketplace bare imports depend on the generated executor's runtime `sys.path`, which pyright at the workspace root cannot follow. The crawl costs ~60-85 s to produce nothing.

## Premise verdict

**REFUTED at the point of use.** D0's premise (the server can be driven headlessly) held; the Goal — *the module graph carries edges from actual symbol references* — is unmet on the only materialised project. D2's stated mechanism (the Axis-D path-attribution seam) was silently REPLACED by a bundle-local prefix table, undisclosed in the report and contradicted by three shipped documents (G3-G6).

## Gaps carried out of this landing

**13 total — 2 high, 10 medium, 1 low.** High: G1, G2.

- **This resolver is effectively dead for the marketplace corpus itself** (G1, high): zero edges for a ~60-85 s crawl.
- **Every count this plan publishes is interpreter-dependent** — a venv on PATH moves the numbers by hundreds. Treat all its figures as environment-scoped, never as constants.
- D3's fourth failure mode (server-side rejection) misreports as a timeout.

## Inconsistencies found, and what was verified

- Report's D0 extrapolation "~118 s full crawl" | verified against the report's own D1 measurement of 60.4 s | **verdict: self-contradictory inside one report**; the audit measured 56-84 s.
- Report's stated root cause ("everything resolvable is intra-directory, hence a self-edge") | verified by re-measuring the 1920 resolved references | **verdict: false** — 1172 of 1920 are not intra-directory; the true cause is that no cross-bundle reference resolves at all.

## Residue

The harvest is off by default and unexercised in CI; one language only (Python).

## Reconciliation actions

- [x] row `status` -> `shipped` — `orchestrator queue --transition PLAN-CIS-026 --status shipped`
- [x] row `pr` stamped `1243` — `orchestrator queue --set-row PLAN-CIS-026 --field pr --value 1243`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-CIS-026 --field landing --value landings/PLAN-CIS-026.md`
- [ ] `plan_marshall_plan_id` — **deliberately empty**: this plan ran in the cloud plan lane and never held a plan-marshall plan id. The START-HERE completeness marker checks `pr` and `landing` only, so the row renders clean.
- [x] gaps routed to the `5xx` remediation wave (WS-07); see `## Follow-ups`

## Follow-ups

Routes to **PLAN-CIS-048** (`500`, run) and **PLAN-CIS-049** (`510`). ⛔ The ledger records the outcome as *shipped but non-functional for its primary target* — `PARTIALLY REFUTED` alone under-states it for downstream planning.
