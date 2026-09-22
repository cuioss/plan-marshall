# Landing Analysis: PLAN-CIS-013 — Chat-signal provenance filter is under-inclusive

epic: code-intelligence-substrate
workstream: WS-04
pr: 1271
merge_commit: `8a11858`
lane: cloud-plan-lane (the `doc/plans/` export wave; NOT the plan-marshall lifecycle, so no `plan_marshall_plan_id` exists)
artifacts: `cloud-runs/260-chat-signal-provenance-filter-under-inclusive/` — `plan.md`, `report-01.md`, `verification.md`, `gaps.md`

## Outcome

**completed** — 3 of 4 deliverables confirmed. Independent post-run audit verdict: **CONFIRMED WITH GAPS**.

The positive-predicate provenance filter, the gate-decision counters and 160 non-vacuous tests (10 of 10 mutants killed) all shipped. **But a high-severity envelope-pairing hole remains**: an injected body quoting its own outermost tag name still lets a wholly harness-authored transcript read as a clean operator verdict. It is latent in the reachable 81-transcript corpus, but content-reachable — not fixture-only.

## Premise verdict

Confirmed for D1/D3/D4. **Refuted for D2's completeness**: the published guarantee — *residue-based classification fails toward synthetic for any injection that carries an envelope* — is falsified by two escape variants. That is the exact compounding failure (survivor count rises, verdict reads healthier) this plan exists to eliminate.

## Gaps carried out of this landing

**8 total — 1 high, 2 medium, 5 low.** High: G1.

- ⛔ **G1's two variants have asymmetric reachability**, and the variant that actually fires on the real block shape is a *different, initially-undocumented* one found only on adversarial review. Fix both, not the demonstrated one.
- **G3 explains the survival**: no test exercises an envelope whose body carries an unbalanced token of its own outermost tag name — the class that let G1 survive twelve rounds and a 240-probe mutation campaign.
- The gate-decision channel has never fired against real data (0 of 81 transcripts).

## Inconsistencies found, and what was verified

- Report's build-gate record claimed the final gate was at a commit after which "any commit landing is Markdown-only" | verified against the PR commit list and per-commit file stats | **verdict: stale** — a later commit modified three Python test modules. This is the **fifth recurrence of the identical defect class the same report catalogues four times in its own findings table.**

## Residue

The envelope-less notice class remains a hand-maintained enumeration, published as a residual gap deliberately rather than closed. Kept `user` turns still render raw envelope text into the Tier-1 prompt — a token-reduction opportunity foregone, not a regression.

## Reconciliation actions

- [x] row `status` -> `shipped` — `orchestrator queue --transition PLAN-CIS-013 --status shipped`
- [x] row `pr` stamped `1271` — `orchestrator queue --set-row PLAN-CIS-013 --field pr --value 1271`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-CIS-013 --field landing --value landings/PLAN-CIS-013.md`
- [ ] `plan_marshall_plan_id` — **deliberately empty**: this plan ran in the cloud plan lane and never held a plan-marshall plan id. The START-HERE completeness marker checks `pr` and `landing` only, so the row renders clean.
- [x] gaps routed to the `5xx` remediation wave (WS-07); see `## Follow-ups`

## Follow-ups

G1 routes to **PLAN-CIS-051** (`530`); G3 to **PLAN-CIS-053** (`550`). ⭐ This run's verify-loop stopping-rule proposal **landed separately** as a lane fix — a working precedent for out-of-band process changes.
