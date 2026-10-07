# Landing Analysis: PLAN-PRQ-06 — A lane override that cannot take effect is accepted and reported set

epic: post-run-quality
workstream: WS-04
pr: #1541

> Landing record for one shipped plan. Written by the `analyze` verb after verifying claims
> against ground truth — merge commit `a1dd4901f04ed1b4f542b081e6ac0e70163b6772`, branch `main`,
> archived at `.plan/local/archived-plans/2026-09-19-prq-06-a-lane-override-that-cannot-take-effect-is/`.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D0 — GATE: derive the inert-override population, both channels | shipped-as-specified | `test_lane_class_off_immunity.py` (new, 448 lines) exercises the population across `marshal.json` and plan-local `finalize_step_overrides` channels |
| D1 — write surface refuses an inert override | shipped-as-specified | `_cmd_finalize_steps.py` (+15/-x), `_cmd_sync_defaults.py` (+64), `_cmd_quality_phases.py` (new, +85) all touched in the merge diff; `test_finalize_steps_lane_rejection.py` (+158), `test_cmd_quality_phases.py` (new, 162), `test_sync_defaults.py` (+232/-x) |
| D2 — read surface shows declared-vs-effective lane | shipped-as-specified | `manage-config/SKILL.md` (+38), `standards/api-reference.md` (new, +16), `standards/data-model.md` (+16) |
| D3 — reclassify `default:lessons-capture` off the floor (operator-settled) | shipped-as-specified | `phase-6-finalize/workflow/lessons-capture.md` (+19/-x) — class change; matches the 2026-09-17 operator ruling recorded in this epic's Decisions |
| D3a — state the change in the PR body | shipped-as-specified | commit body: *"reclassifies `default:lessons-capture` off the floor class so its stored `off` finally binds"* |
| D2a — manifest records effective lane, requested lane preserved | shipped-as-specified | `manage-execution-manifest.py` (+153/-x), `_manifest_rules.py` (+43/-x), `standards/manifest-schema.md` (+19/-x), `test_step_params.py` (new, +221) — folded 2026-09-17 from corpus lesson `2026-09-13-06-001` |
| D4 — controls, incl. the floor-survives-off negative control | shipped-as-specified | `test_lane_class_off_immunity.py` is the dedicated control file; `test_manage_execution_manifest_compose.py` (+274/-x) extended |

All 7 deliverables (D0–D4 including the D3a/D2a sub-items) verified against the merge diff. No dropped or
added-unplanned deliverable observed.

## Metrics and Anomalies

- Tokens: 9.56M total
- Duration: 34h wall clock / 6h10m worked time
- Anomalies: 10 rounds of self-review convergence before landing; a real fix-task loop-back cycle for 3
  CodeRabbit findings (not merely a re-review pass) — both operator-reported, consistent with this being a
  contract-shape change (write-time refusal + a manifest schema addition) rather than a narrow bug fix.

## Routing and Merge Behavior

- Review: enabled roster `coderabbitai`, `cuioss-review-bot`, `sourcery-ai` (per `automatic-review`
  `required_bots`/`optional_bots`). `coderabbitai`: 4 raw / 2 actionable / 2 meta, 3 `fixed` + 1
  `taken_into_account`, 100% resolved-as-fixed (2/2). `cuioss-review-bot`: 1 raw / 0 actionable / 1 meta, 1
  `accepted`. `sourcery-ai`: **unmeasurable** — no participation record, correctly rendered `—` rather than
  a false `0`. Review-vs-gate delta `verdict: excluded` (`gate_tree_unsubstantiated`) — 2 escapes, both
  `gate_addressable`, structural share deliberately withheld rather than asserted `0`.
- CI/merge: merged via merge queue (`gh-readonly-queue/main/pr-1541-…` ref present), commit
  `a1dd4901f` on `main`. No rebase conflicts or re-verify signals reported.

## Reconciliation Actions

- [x] row `status` → `shipped`
- [x] row `pr` stamped → `1541`
- [x] row `landing` stamped → `landings/PLAN-PRQ-06.md`
- [x] row `plan_marshall_plan_id` stamped → `prq-06-a-lane-override-that-cannot-take-effect-is`
- [x] epic.md queue reconciled from status.json
- [x] Open Defects: the `RESOLVED-AS-REFUTED … re-staged as PLAN-PRQ-06` entry closed out — the refutation
  already stood, and this landing is the fix it pointed at. Owed-obligation half (the invisible
  neutralization) is D2; the D2a manifest-truthfulness half is the corpus-lesson fold — both shipped.
- [x] **New Open Defect opened**: orchestration detection fails open for a plan with no `source_id`
  section — `emit-landing` never fired for this plan even though it is orchestrated under this epic (see
  below). This is a fleet-wide orchestrator-mechanics defect, not this epic's to fix, but it directly cost
  this epic its landing notification and is recorded as first-party evidence.
- [x] resume_anchor updated
- [x] START-HERE and Ordered Queue blocks regenerated

## Follow-Ups

- **Orchestration-detection fails open (fleet-wide, not owned here).** `request.md` carries no `source_id`
  section for this plan (confirmed: `'source_id' in metadata` is `False` in the archived `status.json`), so
  whatever detector `emit-landing`/retrospective/lessons-capture consult for the orchestration verdict
  answered a confident "not orchestrated" instead of an honest "indeterminate" — this is the SAME shape as
  corpus lesson `2026-09-09-06-001` ("orchestrator inbox detect cannot be called for a plan with no
  source_id, which is every description-sourced plan"), previously excluded from this epic's lessons-sweep
  as fleet-wide orchestrator mechanics rather than post-run-quality subject matter. It is recorded again
  here because it just cost this epic a real landing notification: `emit-landing` never fired, so the 23
  retrospective/lessons-capture messages had to be filed manually as a workaround (all drained separately,
  see the epic's decision log). Belongs with whichever epic owns orchestrator-platform mechanics
  (`truthful-signals`, on precedent) — not staged here.
- The 23 manually-filed inbox messages (10 retrospective-lesson observations, 13 lessons-capture findings)
  are dispositioned separately per message — see the epic decision log for the batch.
