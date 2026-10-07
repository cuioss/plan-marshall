# Lessons Disposition — ingestion of the 2026-09-19 corpus into quality-aspect

> Operator-directed full-corpus ingestion (all 173 active lessons; dated-epic
> convention set aside at operator direction — this epic's charter widens to the
> whole corpus). First pass: `manage-lessons aggregate` produced 31 multi-lesson
> groups covering 146 lessons; 27 lessons are singletons (no group at any signal
> tier). `2026-09-05-14-002` is superseded and excluded (stays in corpus for
> `cleanup-superseded`). Every handled lesson is archived at
> `lessons-archive/{id}.md` and removed from `.plan/local/lessons-learned/`.
>
> Verification depth per cluster: DEEP = full body read + implementing-source
> corroboration; CODE = claim checked against implementing source by search;
> TRIAGE = active-status + title/component + aggregate preview (fix verified at
> outline by the consuming plan — every spec carries verify-at-outline clauses).

## Group dispositions (31 groups, 146 lessons)

| # | Primary | +abs | Depth | Verdict | Plan |
|---|---------|------|-------|---------|------|
| G01 | 2026-08-25-09-001 footprint capture | 3 | TRIAGE | valid | PLAN-07 |
| G02 | 2026-09-02-14-001 delete-to-one-home verify | 22 | TRIAGE | valid | PLAN-03/04 |
| G03 | 2026-08-25-09-012 Sourcery refusal | 1 | TRIAGE | valid | PLAN-06 |
| G04 | 2026-08-30-16-001 consult worktree | 4 | DEEP | valid — false-negative confirmed against `_lessons_query.py` § outline_not_found | PLAN-12 |
| G05 | 2026-09-02-14-003 docstring detectors | 1 | TRIAGE | valid | PLAN-13 |
| G06 | 2026-09-04-14-002 extract-chat-signal | 3 | TRIAGE | valid | PLAN-14 |
| G07 | 2026-09-03-19-006 handshake diagnostics | 1 | TRIAGE | valid | PLAN-11 |
| G08 | 2026-09-03-18-001 pollution guard | 1 | TRIAGE | valid | PLAN-02 |
| G09 | 2026-09-03-19-001 baseline-reconcile | 7 | DEEP (09-03-22-002) | valid — 12 corpus members YAML-frontmatter, id-verbs return not_found; removal for those 12 is file-level (authorized) with ledger audit | PLAN-08 |
| G10 | 2026-09-04-17-004 changed_files | 1 | TRIAGE | valid | PLAN-01 |
| G11 | 2026-09-05-16-003 fabricated anchor | 1 | TRIAGE | valid | PLAN-11 |
| G12 | 2026-09-09-01-001 mirrored-table surfacer | 1 | TRIAGE | valid | PLAN-13 |
| G13 | 2026-09-03-06-002 sleep pacer | 13 | TRIAGE | valid | PLAN-05/06 |
| G14 | 2026-09-04-14-008 build_queue release | 2 | TRIAGE | valid | PLAN-02 |
| G15 | 2026-09-16-17-001 marshal.json root | 1 | CODE | likely valid — core guard exists at `_config_core.py:134`, lesson names `_cmd_interaction_mode.py` § load_config; consuming plan verifies | PLAN-15 |
| G16 | 2026-09-04-17-015 advisory close | 2 | TRIAGE | valid | PLAN-13 |
| G17 | 2026-09-02-13-002 ledger pairing | 1 | TRIAGE | valid | PLAN-01 |
| G18 | 2026-09-03-10-001 freshness verdicts | 2 | TRIAGE | valid | PLAN-10 |
| G19 | 2026-09-03-07-007 hoisted argv | 2 | TRIAGE | valid | PLAN-15 |
| G20 | 2026-09-03-16-002 suspicion heuristic | 1 | TRIAGE | valid | PLAN-11 |
| G21 | 2026-09-04-17-003 sweep declarations | 11 | TRIAGE | valid | PLAN-09 |
| G22 | 2026-09-02-15-001 tasks-file staging | 2 | TRIAGE | valid | PLAN-10 |
| G23 | 2026-08-30-11-001 zero-overlap absorb | 3 | TRIAGE | valid | PLAN-10 |
| G24 | 2026-08-25-09-002 returned_with_findings | 13 | TRIAGE | valid | PLAN-17/18 |
| G25 | 2026-08-25-09-005 B7 carve-out | 3 | TRIAGE | valid | PLAN-11 |
| G26 | 2026-09-03-07-004 sweep sizing | 2 | TRIAGE | valid | PLAN-07 |
| G27 | 2026-08-25-09-009 analyze-logs build_count | 6 | TRIAGE | valid | PLAN-01 |
| G28 | 2026-09-13-12-001 merge-queue proof | 1 | TRIAGE | valid | PLAN-18 |
| G29 | 2026-09-13-12-010 test mirror seam | 2 | TRIAGE | valid | PLAN-15 |
| G30 | 2026-09-07-15-002 origin/main surfacing | 1 | DEEP+CODE | valid — body recurrence-confirmed; `_self_review_diff.py` resolves bare `base_branch` merge-base with no upstream-behind check | PLAN-07 |
| G31 | 2026-09-06-10-002 plugin-doctor naming | 1 | TRIAGE | valid | PLAN-13 |

## Singleton dispositions (27 lessons, each its own single-lesson cluster)

| Lesson | Component | Plan |
|--------|-----------|------|
| 2026-08-25-09-003 read --phase filter | manage-logging | PLAN-14 |
| 2026-08-25-09-008 generator interpreter | finalize-step-deploy-target | PLAN-02 |
| 2026-08-25-09-013 STATUS barrier | workflow-integration-github | PLAN-11 |
| 2026-09-03-02-001 decision.log bypass visibility | (empty — YAML) | PLAN-16 |
| 2026-09-03-02-002 ci pr view body | (empty — YAML) | PLAN-16 |
| 2026-09-03-02-003 pr_intent duplication | (empty — YAML) | PLAN-16 |
| 2026-09-03-02-004 re-review timeout vs leaf | (empty — YAML) | PLAN-16 |
| 2026-09-03-02-005 pytest basetemp | (empty — YAML) | PLAN-16 |
| 2026-09-03-02-006 manifest snapshot source | (empty — YAML) | PLAN-16 |
| 2026-09-03-02-007 findings persistence | (empty — YAML) | PLAN-16 |
| 2026-09-03-02-008 outline counts | (empty — YAML) | PLAN-16 |
| 2026-09-03-02-009 footprint prune timing | (empty — YAML) | PLAN-16 |
| 2026-09-03-06-005 version stamp | finalize-step-sync-plugin-cache | PLAN-14 |
| 2026-09-03-16-001 scope_estimate | manage-status | PLAN-10 |
| 2026-09-03-17-001 TestFindSkillsRoot | (empty — YAML) | PLAN-14 |
| 2026-09-04-07-001 localized merge-tree | (empty — YAML) | PLAN-12 |
| 2026-09-04-07-002 consult worktree outline | (empty — YAML) | PLAN-12 |
| 2026-09-04-12-001 manifest snapshot stale | manage-execution-manifest | PLAN-10 |
| 2026-09-05-16-002 down daemon | manage-build-server | PLAN-02 |
| 2026-09-07-15-005 deliverables verb name | manage-solution-outline | PLAN-12 |
| 2026-09-07-15-010 invocation quoting | ref-workflow-architecture | PLAN-12 |
| 2026-09-08-01-003 branch-cleanup metadata | phase-6-finalize:branch-cleanup | PLAN-02 |
| 2026-09-08-13-009 build_scope_narrow evidence | manage-change-ledger | PLAN-02 |
| 2026-09-08-21-001 CodeRabbit nitpicks | manage-providers | PLAN-06 |
| 2026-09-13-12-005 argparse rejections | tools-script-executor | PLAN-12 |
| 2026-09-14-05-003 capture-footprint flag | manage-references | PLAN-02 |
| 2026-09-17-15-001 shared script registration | (empty) | PLAN-14 |

All singletons: verdict valid, depth TRIAGE. The 12 YAML-frontmatter rows
(09-03-02-001..009, 09-03-17-001, 09-04-07-001, 09-04-07-002) are archived and
removed file-level — no id-keyed verb can address them (defect documented in
G09's primary). Removal audit for those 12 lives in this ledger + decision log.

## Excluded (1)

- `2026-09-05-14-002` — lifecycle superseded by `2026-08-25-09-013`; stays in
  corpus for `cleanup-superseded`. Not archived, not removed, no plan.

## Transfers out 2026-09-19 (operator direction)

- test-quality PLAN-180-test-fidelity-rules (WS-01, staged): G19 (2026-09-03-07-007,
  2026-09-03-22-001, 2026-09-14-05-006) + G29 (2026-09-13-12-010, 2026-09-13-12-011,
  2026-09-18-11-001) + singletons 2026-09-03-17-001, 2026-09-17-15-001,
  2026-09-03-02-005 (9 lessons). quality-aspect PLAN-15 reshaped to config guards
  only (G15); PLAN-14 dropped the two test-infra singletons (6 left).
- process-compliance PLAN-08-process-contracts (WS-03, staged): singletons
  2026-09-03-02-001/002/003/004/006/007/008/009 (8 lessons; basetemp single-owned
  by test-quality). quality-aspect PLAN-16 retired (spec removed, row retired).
- Lesson evidence for all transferred lessons stays at `lessons-archive/` (ingestion
  record); canonical homes are the sibling specs above.

## Retirements 2026-09-19 cross-machine reconciliation

The truthful-signals response flagged shipped-elsewhere aspects as duplication
risk. Each flag below was verified against THIS tree before retiring — remote
verdicts about sibling-only epics (review-apparatus, code-intelligence-substrate)
do not apply here and changed nothing. Retired deliverables (9, specs and
summary.md updated, surfaces re-derived 17/17 declarative):

- PLAN-01 transcript-less policy — transcript-gated resolver + gap flag + hard
  block documented (phase-6-finalize/SKILL.md, plan-marshall/workflow/execution.md)
- PLAN-02 mutex reclamation — budget-reclaim verb + stale reclaim + waiter prune
  (manage-locks/scripts/merge_lock.py)
- PLAN-04 verdict_inputs surface — verdict-currency classifier + ext-point
  declarations (phase-6-finalize/scripts/verdict_currency.py)
- PLAN-07 footprint capture — capture-footprint verb + branch-cleanup wiring
  (manage-references/SKILL.md, scripts/_cmd_compute_footprint.py)
- PLAN-11 transcript-less decision log + session_id template + anchor validation —
  execution.md logs the decision; session_id optional with gap-flag skip;
  _cmd_mark_step.py refuses non-resolving sha fail-closed
- PLAN-17 returned_with_findings stamping + metrics re-close — stamp by
  construction (phase-6-finalize/SKILL.md); end-phase accumulates with
  close_count/re_entered_phases/value_scope (manage-metrics)

Kept despite remote OBSERVED (not present in this tree): context-load flag
plumbing, VERIFY emission, archive-plan receipt, whole-passage re-review,
merge-queue membership proof, re-fire split, auto-fix churn accounting,
change-ledger row per build, plan_creation_sha, LC_ALL pinning, per-file
assessments, freshness single-verdict, chat-signal retention, symmetric-pair
pair-vs-pair comparison. Remote HYPOTHESIS items stay as written.

## Population accounting (revised, minus 9 retired deliverables)

173 handled = 16 retained plans (156 lessons) + test-quality PLAN-180 (9) +
process-compliance PLAN-08 (8) = 173 unique, single-owner each. 0 stale.
9 shipped-in-tree deliverables retired (specs + summary.md updated, surfaces
re-derived 17/17 declarative); no plan emptied, queue unchanged.
