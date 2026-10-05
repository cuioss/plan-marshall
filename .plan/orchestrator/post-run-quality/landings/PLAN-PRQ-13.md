# Landing Analysis: PLAN-PRQ-13 — Telemetry analyze: outcome and quality reports

epic: post-run-quality
workstream: WS-05
pr: none — `cuioss/plan-marshall-telemetry` is main-only by design; landed as commits
`5546bde` (implementation) and `0965060` (run report)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying claims against ground
> truth — a pasted claim is a lead, never a fact.

⭐ **The first plan this epic landed OUTSIDE the plan-marshall lifecycle, and the lane worked.** No phases,
no finalize steps, no PR, no CI, no retrospective and no inbox landing — and every substitute the brief
named was honoured and is checkable. The run report (`doc/runs/2026-10-04-PRQ-13-run-report.md`, 253 lines)
is what stands in for the machinery, exactly as the brief's irony clause required.

## Deliverable Fidelity vs Spec

All ten shipped. Verified against `git show --stat 5546bde`, the repo tree, and the run report:

| Deliverable | Verdict | Evidence |
|---|---|---|
| D0 — partition, diff, location call | **shipped, and it CORRECTED the brief** | `ANALYZE_CHECKS` / `RETIRED_CHECKS` in `audit.py`; three departures from the proposal, each reasoned (below) |
| D1 — plan outcome report | shipped | `report_timing.py`, `report_tokens.py`, `report_prs.py`, `report_lines.py`, `report_deliverables.py` |
| D2 — project kind, a SET | shipped | `report_project_kind.py` |
| D3 — orchestrator outcome report | shipped | `report_orchestrator.py`; carries queue population, never-launched specs, inbox drain, population-labelled roll-up |
| D4 — quality report | shipped | `ontology.py` as the single axis home; `report_findings.py`, `report_gates.py`, `report_scope_stability.py`, `report_severity.py` |
| D4a — producer-side hand-back | **shipped as a hand-back, nothing touched here** | 5 items returned; staged as `PLAN-PRQ-14` |
| D5 — script-first, manual-capable, three states | shipped | `subject_reports.py`, `report_context.py`; `doc/outcome-report.md` § Manual completion |
| D6 — de-scope and report the drop | shipped | `run-summary` block, per-check error guard, banners on all 13 retired checks |
| D7 — controls | shipped | `test_subject_reports_controls.py`, `test_subject_reports_engine.py`, `test_ontology_doc_consistency.py` |
| D8 — ontology documentation | shipped | `doc/quality-ontology.md`, `doc/outcome-report.md`, both linked from the README |

✅ **The report-location invariant was honoured, not amended** — D0 took option (a). Reports land under
`reports/{project-slug}/`, *beside* the archive and never inside it, so `{project-slug}/` remains written
only by `transfer`. The README's Layout section now documents both trees.

⭐ **Unasked-for and correct: the single-classifier guarantee was made structural.** The `quality-chain`
check and the quality report now share one mechanism × resolution classifier in `ontology.py`, so "there
is no second formatter" is enforced by construction rather than by the brief saying so.

### D0 corrected the brief's partition in three places, and two of the three corrections are against me

My proposal was 7 keep-outcome + 4 keep-quality + 13 drop. The settled partition is 6 + 3 + 1 foundation +
1 re-scoped + 13 retired = 24. ⭐ **This is a gate behaving exactly as a gate should** — the proposal was
built from check *names*, and D0 read each check:

- **`input-integrity` is KEPT, where I dropped it.** It is the engine's no-false-healthy foundation: the
  kept `metrics` / `token-*` checks rely on its `metrics_blind` floor annotation, and it is the
  check-level form of D5's own measurement-state discipline. Dropping it would have removed the floor the
  kept checks stand on.
- **`merge-window-accounting` is DROPPED, where I kept it.** ⛔ **The sharpest correction**: the merge-lock
  logs it reads are never transferred, so in that repository it can only ever report `unmeasured`. It fails
  *the brief's own test* — "does not survive archival" — which I wrote and then mis-applied by reading the
  name as outcome-shaped.
- **`cross-check-synthesis` is RE-SCOPED, not kept whole.** Seven of its ten couplings need a retired
  check. It now computes only non-retired upstreams and reports `evaluated: yes / partial / no` per
  coupling, so a coupling that *could not* be evaluated is never counted as one whose facets did not
  co-occur. Three are evaluated on the default run — one fully, two partially.

## Self-review: seven defects, all of this epic's own founding class

The deliberate pre-commit pass found and fixed seven. ⭐ **Six of the seven are honest-zero or
folded-state defects — the precise failure mode this epic exists to eliminate**, found in the instrument
built to measure it:

1. ⛔ **Component assessments were counted as findings.** All **820** records in `assessments.jsonl` are
   footprint assessments, and the inherited `quality-chain` check scored them as pending `self-review`
   findings — which made **255 of PLAN-PRQ-07's 255 "actionable pending" items** assessments rather than
   findings. Fixed once in `ontology.is_finding_record`, so the check and the report cannot disagree. ⚠
   **This is a pre-existing defect in the relocated check**, so any earlier `quality-chain` reading of this
   corpus overstated actionable chain debt. See the Watch.
2. **A zero over an empty population published as measured** — `totals_tokens: 0` now `not_measured`, and
   `tokens_by_phase` no longer defaults an absent phase to 0. Control asserts it.
3. **A compatibility policy misread as a contract break** — the first severity rule made 19 of 63 plans
   `critical`. Now uses contract-file evidence in the footprint, and compatibility can only raise a
   contract change from `major` to `critical`.
4. **A machine-specific path leaked into tracked JSON** — the `--source-repo` absolute path appeared in
   reason strings; now a neutral phrase.
5. **Unknown gates folded into clean ones** — `sonar` and `auto-review` reported a measured 0 when the
   gate state was unknown; now `not_measured`, with a control. A disabled pre-submission step also no
   longer makes `self-review` `not_applicable`, because the phase Q-Gates feed it too.
6. **A mechanism could be masked by its gate** — a mechanism with its own records could be marked
   `not_applicable` on gate state alone.
7. **A doc claim corrected** — the synthesis document claimed four evaluated couplings; the real figure is
   three.

## Metrics and Anomalies

- **Tests:** `python3 -m pytest` — **873 passed, 20 skipped** (from 784/19 before the plan). The 20 skips
  need `--plan-marshall-root`.
- ✅ **The mechanism-order control was run against the real thing and passed.** With
  `--plan-marshall-root=/home/oliver/git/plan-marshall`, `test_mechanism_step_orders_match_plan_marshall`
  confirms the five step orders **5, 7, 8, 30, 40** agree with plan-marshall's finalize-step orders — so the
  taxonomy's claim that its mechanism order is *derived* rather than asserted is now mechanically checked
  across two repositories.
- ⚠ **No token figure, no wall time, no phase breakdown, no recall grade, no landing-facts block.** That is
  the lane's accepted cost, named in the brief before the run and not a reporting gap.

## Routing and Merge Behavior

- **Review:** none. The repo is main-only with no PR workflow and CodeRabbit disabled by its own
  `.coderabbit.yaml`. One deliberate self-review pass substituted, and it found seven defects — more than
  several bot-reviewed PRs in this epic produced.
- **CI/merge:** no CI. `python3 -m pytest` green before every commit, per the brief. Committed directly to
  `main` and pushed.
- **Collisions:** none possible — the surface was entirely out-of-repo by construction, and D4a kept it
  that way by handing the one in-repo requirement back instead of reaching for it.

## Reconciliation Actions

- [x] row `status` → `shipped` — `queue --transition PLAN-PRQ-13 --status shipped`
- [x] row `pr` stamped `5546bde` — the landing commit; **there is no PR**, by that repo's design
- [x] row `landing` stamped `landings/PLAN-PRQ-13.md`
- [x] row `plan_marshall_plan_id` left EMPTY — correct: no plan-marshall plan ever existed for this work
- [x] `epic.md` narrative reconciled; WS-05 closed again
- [x] `PLAN-PRQ-14` staged from the D4a hand-back
- [x] four Watches opened (below)
- [x] resume anchor updated; `queue-view.md` regenerated

## Follow-Ups

**D4a hand-back → staged as `PLAN-PRQ-14`** in this repository, where the producer surfaces live. Five
items, three required and two recommended; `PLAN-PRQ-14` carries them.

**Four Watches, from the run's own "not done / not checked" list:**

1. ⚠ **No report files are committed yet** — no project has been transferred, so `reports/` does not exist.
   The reports are therefore **shipped but never executed against real data**. Re-check after the first
   `transfer` + `analyze` run; that run is the real test of D1–D5, not the test suite.
2. ⛔ **Finding severity bands are `not_measured` for every plan** — the Sonar collapse, exactly as the
   brief predicted. **This is the mechanism working, not a bug**: the information was destroyed at
   ingestion. `PLAN-PRQ-14` item 3 is the fix, and until it lands *and new plans run through it*, no
   historical plan will ever have a band.
3. ⚠ **Lines-changed counts only the source project's PRs.** Work landing in another repository is not
   included — so a cross-repo plan like `PLAN-PRQ-07` under-reports, and `PLAN-PRQ-13` itself reports
   nothing at all, since all its work was in the telemetry repo. The same blind spot `PLAN-PRQ-09`'s folded
   recurrence describes, now reproduced in the new instrument.
4. ⚠ **The branch-protection HYPOTHESIS is still unresolved** — the run could not confirm it. The absent
   `.github/` is consistent with main-only but does not establish the protection setting.

**One finding this landing surfaced that is not in the hand-back:** the 820-assessment miscount means every
`quality-chain` reading of this corpus taken before `5546bde` overstated actionable chain debt. Any figure
quoted from such a run is suspect; re-derive rather than cite.
