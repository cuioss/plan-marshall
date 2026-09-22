# Landing Analysis: PLAN-CIS-033 — Empty skill resolution indistinguishable from minimal

epic: code-intelligence-substrate
workstream: WS-01
pr: 1220
merge_commit: `f29e5ce0b`
lane: cloud-plan-lane (the `doc/plans/` export wave; NOT the plan-marshall lifecycle, so no `plan_marshall_plan_id` exists)
artifacts: `cloud-runs/160-empty-skill-resolution-indistinguishable-from-minimal/` — `plan.md`, `report-01.md`, `verification.md`, `gaps.md`

## Outcome

**completed** — 3 of 4 deliverables confirmed. Independent post-run audit verdict: **CONFIRMED WITH GAPS**.

The `minimal` marker and its guard are real and mutation-proven in both directions — but **the fix's own escape hatch reproduces the exact masking archetype it was built to close.** A profile declared `minimal: true` and later populated by an ordinary `enrich add-domain` persists both flags at once, silently zeroing a task's real skills.

## Premise verdict

D1's indistinguishability was confirmed and re-derived at the current tree. But the fix introduces a **new and worse** instance of the epic's archetype: the escape hatch can silently launder a populated profile down to zero skills — strictly worse than the pre-fix silent degradation, because it now looks deliberate.

## Gaps carried out of this landing

**15 total — 1 high, 7 medium, 7 low.** High: G2.

- ⛔ **G2 (high) is the sharpest instance of "a fix becomes the next masking archetype" in this ingest**, and the run report's dismissal of it as "nonsensical input" was refuted by executing two ordinary supported CLI verbs in sequence.
- The deterministic guard **cannot fire for the shape the writers actually produce** (an absent profile block, not an empty one) — G3.
- The named condition reaches only a log file, never the structured TOON output the allocation-time consumer actually reads (G9).

## Inconsistencies found, and what was verified

- Report claimed "an empty `skills[]` produces zero signal" | verified against the pre-fix tree | **verdict: overstated** — phase-4-plan already logged a WARNING and recorded a Q-Gate finding. The real gap was inability to *distinguish* deliberate from unresolved, not total silence.
- Report finding #6 rejected as "nonsensical input" | verified by end-to-end reproduction through two supported CLI verbs, re-run at adversarial review | **verdict: refuted by execution** — this is the batch's highest-severity single finding.

## Residue

The render surface still shows both states as `0 skills` (deliberately deferred as out of scope).

## Reconciliation actions

- [x] row `status` -> `shipped` — `orchestrator queue --transition PLAN-CIS-033 --status shipped`
- [x] row `pr` stamped `1220` — `orchestrator queue --set-row PLAN-CIS-033 --field pr --value 1220`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-CIS-033 --field landing --value landings/PLAN-CIS-033.md`
- [ ] `plan_marshall_plan_id` — **deliberately empty**: this plan ran in the cloud plan lane and never held a plan-marshall plan id. The START-HERE completeness marker checks `pr` and `landing` only, so the row renders clean.
- [x] gaps routed to the `5xx` remediation wave (WS-07); see `## Follow-ups`

## Follow-ups

G2 routes to **PLAN-CIS-049** (`510`) and is flagged in `epic.md` § Open Defects as a live masking defect. G3's cannot-fire guard routes to **PLAN-CIS-053** (`550`).
