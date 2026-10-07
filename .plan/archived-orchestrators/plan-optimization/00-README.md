# Plan-Optimization — Token-Usage Analysis & Roadmap

Token-usage retrospective over the **plan-marshall archived + dormated plan corpus** plus the
**TokenSheriff source plan** that seeded lesson `2026-06-30-08-001` — and the resulting optimization
roadmap. Produced by the `audit-archived-plan-retrospectives` skill run with a token-usage focus and
direct `.plan` access; roadmap maintained across sessions.

**START HERE → [`HANDOVER.md`](HANDOVER.md)** — live status, the decided target dispatch topology,
and the ordered queue.

**Roadmap status (2026-07-17, post full-scale cleanup):** the token-optimization **cost-driver
roadmap is COMPLETE** (`plan-8-context-trim` #899) AND the entire **aggregated findings/lessons queue
— P1–P9 + design-first SS — has SHIPPED** (#906→#922), along with the `marshall-orchestrator` epic
skill (#915). All of that shipped detail is archived in
[`HISTORY-snapshot-4-queue-wave.md`](HISTORY-snapshot-4-queue-wave.md); HANDOVER §3 is now a pointer
only. **What remains is WAVE 2 (HANDOVER §4):** 4 startable, surface-disjoint plans distilled from the
open defects wave 1 surfaced — `manifest-compose-gaps`, `finalize-step-integrity`,
`leaf-validator-yield`, `P7 docs-contract-consistency` — plus parked items (TT, ci-pr-safe-merge,
consumer migrations). **The plan-server epic (Rung 1 → marshalld) is tracked separately in
[`../plan-server/00-README.md`](../plan-server/00-README.md), not here.**

## Directory layout & convention

**One plan document = one command.** Every queued plan under [`plans/`](plans/) is a self-contained
spec; execute it with

```
/plan-marshall task="implement .plan/plan-optimization/plans/<doc>.md"
```

**Lifecycle (plan docs are handled like lesson sources):** `plans/` holds only not-yet-started
work. When a plan is created from a doc, the doc moves into the plan's own directory and is
**archived with the plan** (`.plan/local/archived-plans/<date>-<plan_id>/`) by the phase-6 archive
step — no separate landed copy. After archiving, as the last step, `HANDOVER.md` §3 and this README
are updated to point at the archived location (each plan doc carries the exact steps in its
"Lifecycle" footer). [`landed/`](landed/) holds only the pre-roadmap design specs (04/05/06).
`plans/` empty = roadmap complete.

**Corpus cut (plan-11, 2026-07-09).** `plan-11-audit-check-refresh` refreshed the
`audit-archived-plan-retrospectives` skill (era-aware `fixed_since` sentinels + retire-on-quiet
proposals + four new roadmap-mechanics checks: `dispatch-topology`, `finalize-flow-conformance`,
`merge-window-accounting`, `lane-lever-effectiveness` — the last is the armed-checkpoint measurement
arm). Its closing step runs the refreshed audit ONCE over the full pre-cut corpus, then dormates the
plans archived BEFORE this plan's start date (operator-confirmed, `--dormate ID … --confirmed`, plus
`--dormate-global-logs`) so the sentinels start on a clean post-roadmap corpus. **After the cut, the
`.plan/local/archived-plans/…` path columns in HANDOVER §3 become historical** — dormated plans move
to the purgeable `.plan/temp/dormated-plans/`, so the **PR number + git history are the durable
reference**, not the archive path. **Era-boundary footer convention (carry forward):** every
remaining roadmap plan that fixes a failure mode adds, as part of its landing, its `fixed_since` era
stamp to the audit skill's `CHECK_ERA` registry so the audit distinguishes pre-fix rows from
regressions.

| Location | Contents |
|----------|----------|
| [`HANDOVER.md`](HANDOVER.md) | Live status + design contract + the wave-2 queue + open defects. The only doc that changes between sessions. **Compacted three times (2026-07-12, -13, and a full rewrite 2026-07-17) — removed detail is frozen in HISTORY.md + HISTORY-snapshot-4.** |
| [`HISTORY.md`](HISTORY.md) | Frozen snapshots 1–3 (the roadmap proper, #811→#899): (1) full pre-cleanup HANDOVER of 2026-07-12 — legacy §-refs (§7.1–27, §8) resolve here; (2) detailed shipped rows #877–#887; (3) roadmap-complete #888–#899 + resolved defects. Not maintained. |
| [`HISTORY-snapshot-4-queue-wave.md`](HISTORY-snapshot-4-queue-wave.md) | **Snapshot 4 (2026-07-17):** the post-roadmap TAIL (#906–#912) + `marshall-orchestrator` #915 + the entire P1–P9/SS aggregated-queue wave (#914–#922). The "what shipped" record for everything after the roadmap closed. |
| [`plans/`](plans/) | The executable queue — now **WAVE 2**: `plan-manifest-compose-gaps`, `plan-finalize-step-integrity`, `plan-leaf-validator-yield`, `plan-docs-contract-consistency` (P7), plus `plan-terminal-title-stale-build-busy` (TT, parked). Wave-1 shipped specs were removed (archived with their plans + in HISTORY-snapshot-4). `plans/` empty = epic complete. |
| [`landed/`](landed/) | Shipped design specs, kept as reference — `04` (lane feature, PR #811), `05` (single improvements; §6 shipped PR #812, rest extracted to plans/), `06` (execution-context dispatch; §3 shipped PR #812, rest extracted to plans/, planning-coalescing retired). Do not execute from these. |
| [`01-token-master-table.md`](01-token-master-table.md) | The per-plan data table: change-type · scope · lane · wall · LOC · tokens · tok/LOC · per-phase split. All 58 plans. |
| [`02-token-aggregates.md`](02-token-aggregates.md) | Distribution: corpus totals, the ~1.0M fixed-overhead floor, tok/LOC by bucket, per-phase share. |
| [`03-synthesis-optimal-path.md`](03-synthesis-optimal-path.md) | The synthesis: was refine necessary, which steps add value (adversarial) vs not (transform/confirm), the optimal path, priority recommendations. |
| [`2026-06-30-08-001.md`](2026-06-30-08-001.md) | Snapshot of the seeding lesson (the TokenSheriff doc-move run + the integrate-sonar recurrence). |

## Headline findings (from the analysis docs)

1. **The edit is the smallest macro-bucket.** Planning 35.9% · execute 27.4% · finalize 36.8% — ~73%
   of every plan is framework overhead around the edit.
2. **A hard ~1.0M-token floor.** No fully-recorded plan landed under it; an 11-LOC fix cost 1.04M
   (94,715 tok/LOC). Median 3,504 tok/LOC, range 418 → 94,715 (226×), tracking LOC inversely.
3. **Refine is conditional, not universal** — all 58 plans were ≥95% confidence; refine ran on every
   one, mostly as confirm-work. **⚠ CONTESTED — see HANDOVER §5 counter-evidence:** six tail plans
   (#911/#906/#909/#908 + TokenSheriff #572) had refine/outline invalidate the *source premise*, which
   is load-bearing, not confirm-work. The ≥95% figure measured the *plan's* confidence, never the
   *input's* validity. Do NOT act on this finding (e.g. make refine conditional) without re-deriving
   it against premise-validity.
4. **Value = adversarial steps; waste = transform/confirm steps on inputs that don't need them.**
5. **The biggest fixable drain is a reliability bug** — the execute envelope loop re-dispatches per
   task (~9 dispatches for a 1-envelope plan). No sizing knob touches it → `plans/plan-1`.

## Data-confidence note

Seven plans have partial metrics (≥1 phase unrecorded, usually 6-finalize) — their totals are floors.
Ratio statistics use the 51 fully-recorded plans with known LOC. Fixed at the source by PR #812
(first-class `partial`/`unrecorded_phases`).

## Lesson-filing disposition (three-gate policy)

No new lesson filed from the analysis itself: the token-cost structure was owned by lesson
`2026-06-30-08-001` (verified ABSENT from the live lesson store at plan-8 finale — already retired by a
prior roadmap landing; no reconcile carried) and remains operationalized by the shipped
`token-economics` audit check. The
`token-efficiency-trend` +36% regression over the latest 8 plans shares 08-001's root cause and is
folded into the roadmap rather than filed as a duplicate.

## Reproduce the analysis

```
python3 .plan/temp/token-analysis/analyze.py   # walks both corpora + TS, joins git LOC -> data.json
python3 .plan/temp/token-analysis/gen.py       # data.json -> 01/02 markdown
```
