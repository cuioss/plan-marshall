# Landing Analysis: PLAN-15 — Opencode enforcement parity

epic: process-compliance
workstream: WS-06
pr: 1618 (https://github.com/cuioss/plan-marshall/pull/1618, merge e37e47203d442b708a3a24170faab0652ed68478)

> Landing record for one shipped plan. Lives at `landings/PLAN-NN.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| Two-tier permission map + per-agent overrides | shipped-as-specified | PR #1618 diff: opencode.json |
| tool.execute.before guard (R1–R4 + 9 review hardenings) | shipped-as-specified | .opencode/plugin/guard.js + decision-table tests |
| Role×surface×path matrix | shipped-as-specified | doc/developer/opencode.adoc |
| Docs | shipped-as-specified | platform-runtime SKILL.md, no-op-policy.md |
| Steward wizard handoff | shipped-as-specified | marshall-steward SKILL.md + wizard-flow.md |
| Decision-table tests | shipped-as-specified | platform-runtime + manifest + providers tests |
| Infra-config recognition (opencode.json/c) | shipped-as-specified | _manifest_core.py + classifier tests |

Landing relayed via operator paste (no kind=landing message queued — reconciled
against PR ground truth): PR #1618 verified merged (e37e4720), scope matches the
6 staged deliverables plus review-driven hardening. Verification figures are
plan-reported: CI green on landed HEAD (27k verify), per-bundle gates green,
scoped plugin-doctor clean, self-review clean, 23 review findings resolved.
Overrides exercised are operator decisions on record (false-red gate ship-past,
freshness override, coderabbit decline, stale-bot gap via fresh-PR strategy).
Open defects the run disclaims (whole-tree module-tests red on main,
test_ensure_denied failures, metrics enrich hard-error) are recorded as-is for
their owners — verified as out-of-scope here, not re-checked.

## Metrics and Anomalies

- Tasks: 22 (plan-reported); findings -001..-008 all filed to this epic's inbox
- Anomalies: -001..-007 already drained in earlier passes; -008 arrived with
  this landing and folds into the executor-regen defect below

## Routing and Merge Behavior

- Review: 23 findings (9 fix tasks + accepts); merge-queue path; no rebase
  conflicts reported; no cross-plan collision observed

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-15 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-15 --field pr --value 1618`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-15 --field landing --value landings/PLAN-15.md`
- [x] row `plan_marshall_plan_id` stamped — `orchestrator queue --set-row PLAN-15 --field plan_marshall_plan_id --value implement-opencode-enforcement-parity`
- [x] epic.md queue reconciled from status.json
- [x] PLAN-15 watch/shipped note below
- [x] resume_anchor updated — `manage-status update-field --field resume_anchor --store orchestrator`
- [x] view regenerated — `orchestrator resume-summary`

## Follow-Ups

- parity-008 → executor-regen poisoning defect (recurrence with fail-safe facet)
- lessons-routing-003 → PLAN-12 D4 recurrence fold
