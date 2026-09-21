# Landing Analysis: PLAN-09 — interaction_mode

epic: operator-ux
workstream: WS-06
pr: #1502 (https://github.com/cuioss/plan-marshall/pull/1502)

> Landing record for one shipped plan. Verified against ground truth (PR view, git log, archived plan artifacts) — the paste was a lead, never a fact.

## Deliverable Fidelity vs Spec

Spec `plans/PLAN-09-interaction-mode.md` carries 5 deliverables (under the split-guard); the archived plan reports 3 deliverables across 11 tasks (its own grouping) with all 11 done.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| interaction_mode field in marshal.json (default advanced) | shipped-as-specified | PR #1502 diff: `_config_defaults.py`, `_config_core.py`, `data-model.md`; `test_interaction_mode.py` resolution tests |
| manage-config read/write surface | shipped-as-specified | `_cmd_interaction_mode.py`, `manage-config.py`, `api-reference.md` in realized footprint |
| steward menu entry (first-run + later) | shipped-as-specified | `menu-configuration.md`, `wizard-flow.md` updated; PR body confirms |
| mode-to-behaviour mapping vs landed PLAN-04/05/07 | shipped-as-specified | `standards/interaction-mode.md` landed; verified against landed code per paste |
| tests per mode + invalid refused + absent defaults | shipped-as-specified | `test_interaction_mode.py`; CI green on final HEAD |
| Operator-added: plugin-doctor stale-accept-set live re-verification + regression tests | added-unplanned, gated green | `_analyze_argument_naming.py`, `test_argument_naming_stale_cache_reverify.py`; fixes plugin-doctor false positive on `ci pr list --limit` |
| Operator-added: phase-1-init Step 7 mode-aware domain branch | added-unplanned, gated green | `phase-1-init/SKILL.md` in realized footprint |
| Operator-added: 7 review-driven fix tasks (3 loop-backs of 5) | added-unplanned, gated green | review-retrospective + paste; 23 finalize steps done, zero pending findings |

No deliverable dropped. `expert` constraint held (no re-enable of the PLAN-01-removed domain prompt).

## Metrics and Anomalies

- Tokens: 0 tracked (OpenCode target exposes no transcript; session-token metrics absent — recorded, non-blocking).
- Duration: 43h56m wall (init 23m57s, refine 6m21s, outline 14m54s, plan 11m29s, execute 40h43m across 4 closes, finalize 2h16m); 11/11 tasks with artifacts.
- Anomalies: 5-execute long tail is review-loop driven (#1496 → 7x90min quota waits, close unmerged, recreate #1502, full-range review there). Retrospective notes PR-number staleness in its own prose (#1496 named; merged PR is #1502 — supersession documented in inbox landing message). `references.json` still names `pr_number 1496` (history) while `merge_commit_sha ef5959dc` matches #1502. `create-pr` step record naming #1496 retained as history per paste — accepted residue, not a defect.

## Routing and Merge Behavior

- Review: CodeRabbit 7 findings on #1496 → 3 fix tasks, then quota-silent on fix range (7 waits, closed unmerged per operator order); #1502 full-range review 4 findings → 3 fix + 1 scope question (operator answered Split) + 1 re-review fix. CI green final HEAD, barrier clean. Paste claims zero pending findings — corroborated by merge (queue requires barrier clean).
- CI/merge: squash-merged via merge queue as ef5959dc0a89c73a8fc67fe6a1118ea10e376d92. `git log` shows ef5959dc at HEAD~0 area; `pr view` state merged with matching merge SHA. Main checkout clean (`git status` empty). No rebase-collision signal vs other staged specs (PLAN-09 was the last staged plan; no concurrent).
- Surface note: realized footprint (15 paths) exceeds the spec's 9 declared entries — expected for operator-added scope + review hardening, all within WS-06/manage-config/steward surface. No unpredicted collision to record.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-09 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-09 --field pr --value #1502`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-09 --field landing --value landings/PLAN-09.md`
- [x] row `plan_marshall_plan_id` stamped — `orchestrator queue --set-row PLAN-09 --field plan_marshall_plan_id --value implement-plan-09-interaction-mode`
- [x] epic.md queue reconciled from status.json
- [x] resume_anchor updated — `manage-status update-field --field resume_anchor --store orchestrator`
- [x] START-HERE and Ordered Queue blocks regenerated — `orchestrator resume-summary`

## Follow-Ups

- Epic inbox holds 14 live messages from `implement-plan-09-interaction-mode` (13 candidate-lesson + 1 landing-014, `inbox_state present`, `invalid_count 0`): accepted follow-ups per paste are consumer wiring for interaction_mode (known gap) plus one candidate architecture hint. NOT drained here (paste mode); next `analyze slug=operator-ux` with no paste drains them message by message.
- WS-07-persona-loading-structure still undecomposed; epic has no staged plans left after this landing — decompose vs close decision is now due.
