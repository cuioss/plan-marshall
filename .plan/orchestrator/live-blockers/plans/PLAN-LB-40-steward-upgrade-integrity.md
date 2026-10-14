# PLAN-LB-40: Steward upgrade integrity: keep reviewer lists, retire dead keys and steps, bootstrap the executor, and remove the one-shot review-step migration

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-LB-40-steward-upgrade-integrity.md` and is queued as one row file, `queue/PLAN-LB-40.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged from inbox message `lb-37-functional-review-011.md` (the defects `/marshall-steward upgrade integrate=true`
> showed across nine consumer repositories during PLAN-LB-37's rollout) and from the epic Watch
> "The `migrate-review-steps` steward migration is meant to go", whose trigger the rollout met.

## Objective

Running `/marshall-steward upgrade integrate=true` across nine consumer repositories left every one of them with an invalid or lossy `marshal.json` that had to be repaired by hand. The upgrade threw away reviewer lists, left retired keys and invalid lane values in place, failed on a step id that no plugin implements, and could not start in a repository whose executor pointed at a pruned cache. This plan makes the upgrade leave a valid `marshal.json` without hand repair, and removes the one-shot `migrate-review-steps` migration now that every configured repository has been migrated.

## Deliverables

1. **Reviewer lists survive the upgrade, and the seeded default is the standard roster.** Stage 2 runs `reconcile-marshal-json` (which includes `sync-defaults`) before `migrate-bot-lists`. `sync-defaults` back-fills empty `required_bots` / `optional_bots`, and `migrate-bot-lists` then reads the presence of those keys as an operator answer and deletes the legacy `enabled_bots` list. Fix the order or the test so that only a non-empty value, or `bot_lists_provenance: answered`, counts as an operator answer. The seeded default for `plan-marshall:automatic-review` is `required_bots: "cuioss-review-bot,coderabbit"`, `optional_bots: "sourcery"` — the operator directive for every `marshal.json` — and a legacy list is migrated onto that roster, with any bot name the registry does not know (`gemini`, `pr-agent`) reported rather than copied.
   *Done when:* a legacy-only config run through the whole Stage 2 order, not the sub-step alone, ends with the standard roster and an explicit report of the dropped names; a config the operator already answered keeps its answer.

2. **Stale values are retired or reported: phase-level retired keys and invalid lane values.** The upgrade removes, or at least reports, every key no reader consumes: `plan.phase-6-finalize.self_review`, `.simplify`, `.drop_review_on_scope_gate`; `plan.phase-3-outline.qgate`; `plan.phase-5-execute.per_task_budget_reserve_tokens`. A stored `lane: "auto"` is removed (the documented `auto` → omit mapping), and every other stored step lane is validated against `VALID_LANE_OVERRIDE` and reported when it is not a member. `normalize-keys` reports keys below the top level, not only top-level ones.
   *Done when:* a fixture carrying each listed key and five `lane: "auto"` steps comes out of the upgrade with none of them, or with each one named in the report; a test pins the retired-key list so a newly retired key is a deliberate edit.

3. **A step id no plugin implements is detected before it breaks anything.** The upgrade resolves every configured phase-6 step id and removes (or asks about) one that resolves to no implementor, instead of `add-step` failing later with `missing_order` (observed with `default:finalize-step-whole-tree-gate` in cui-jsf-test-basic).
   *Done when:* a fixture with a dead step id upgrades cleanly and the report names the removed id; adding a step to that config afterwards succeeds.

4. **The upgrade bootstraps its own executor and warns on a skill/planner version split.** `upgrade plan` needs the executor, yet regenerating it is a Stage-1 sub-step of that plan, so a consumer whose executor is missing or points at a pruned cache version (`ModuleNotFoundError: plan_logging`) cannot start. The entry point validates the executor and regenerates it from the newest cache before asking for the stage plan. When the loaded `marshall-steward` skill version differs from the planner's version, the upgrade says so and names the restart.
   *Done when:* a test starts the upgrade with a missing executor and with one pointing at an absent cache version, and both reach the stage plan; the version-split warning has a test.

5. **The one-shot `migrate-review-steps` migration is removed.** PLAN-LB-37 D8 added it to be removed once every configured repository was migrated; all nine are (see Claim Labels). Remove `migrate-review-steps`, `_merged_review_params` and its `SHIM(A)` block from `upgrade.py`, its entries in the steward `SKILL.md` and `references/upgrade-flow.md`, `test_review_step_migration.py`, and its cases in `test_upgrade.py` and `test_upgrade_flow_stage2.py`. The `enabled_bots` `SHIM(A)` block stays unless deliverable 1 replaces it.
   *Done when:* no file in the repository names `migrate-review-steps` or `_merged_review_params`, and the steward tests pass.

The split guard: five deliverables, one surface (the steward upgrade and the manage-config readers it calls). Two of the source message's six items were folded rather than dropped: its item 6 (stale skill body) is deliverable 4's warning, and its item 4's "add both review steps for a repository that lists its steps explicitly" is moot once deliverable 5 removes the migration, because every configured repository already carries both steps.

## Claim Labels

- OBSERVED: `migrate_bot_lists` classifies a config as operator-answered on key presence alone (`has_new = _REQUIRED_BOTS_KEY in params or _OPTIONAL_BOTS_KEY in params`) and then deletes the legacy key, reporting `operator_answer_kept` with `discarded_legacy` — read at `marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/upgrade.py` § `migrate_bot_lists`
  - verdict: corroborated | checked_at: 187f7314a | by: live-blockers/cleanup | rescoped: n/a | evidence: upgrade.py migrate_bot_lists: has_new is key presence (L340); state 2 deletes the legacy key and returns operator_answer_kept with discarded_legacy (L351-360).
- OBSERVED: the Stage 2 sub-step order lists `reconcile-marshal-json` before `migrate-bot-lists` — read at `marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/upgrade.py` module docstring and the Stage 2 sub-step tuple
  - verdict: corroborated | checked_at: 187f7314a | by: live-blockers/cleanup | rescoped: n/a | evidence: upgrade.py module docstring L49-50 and the Stage 2 sub-step tuple L176-178 list reconcile-marshal-json before migrate-bot-lists.
- OBSERVED: `normalize-keys` surfaces only top-level unrecognized keys — read at `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_config_core.py` § `unrecognized_top_level_keys`
  - verdict: corroborated | checked_at: 187f7314a | by: live-blockers/cleanup | rescoped: n/a | evidence: _config_core.py unrecognized_top_level_keys at L908 is the normalize-keys detector; it inspects the top level only.
- OBSERVED: `missing_order` is raised by `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_quality_phases.py`
  - verdict: corroborated | checked_at: 187f7314a | by: live-blockers/cleanup | rescoped: n/a | evidence: _cmd_quality_phases.py L172 emits missing_order.
- OBSERVED: `migrate-review-steps` and `_merged_review_params` are named only in the steward `SKILL.md`, `references/upgrade-flow.md`, `scripts/upgrade.py`, `test_review_step_migration.py`, `test_upgrade.py` and `test_upgrade_flow_stage2.py` — read by `git grep` over `marketplace`, `test` and `doc` at `187f7314a`
  - verdict: corroborated | checked_at: 187f7314a | by: live-blockers/cleanup | rescoped: n/a | evidence: git grep over marketplace, test, doc at 187f7314a: the six named files only.
- OBSERVED: all nine configured consumer repositories (API-Sheriff #441, TokenSheriff #802, cui-http #284, cui-jsf-test-basic #215, cui-open-rewrite #197, cuioss-parent-pom #1515, nifi-extensions #650, plan-marshall-mcp #74, pm-mcp-core #57) carry the migration merge commit on their default branch and list `functional-review` and `code-review` with `required_bots: "cuioss-review-bot,coderabbit"` — read with `git -C` on each local clone after a fetch, 2026-10-14
  - verdict: corroborated | checked_at: 187f7314a | by: live-blockers/cleanup | rescoped: n/a | evidence: git -C on each of the nine local clones after fetch, 2026-10-14: migration merge commit on the default branch; marshal.json lists functional-review and code-review; required_bots cuioss-review-bot,coderabbit.
- OBSERVED: the defects were observed by the rollout agents, not by this spec's author: reviewer-list loss in cuioss-parent-pom and cui-open-rewrite, retired keys in nifi-extensions and cui-jsf-test-basic, `lane: "auto"` on five steps in cui-open-rewrite, the dead step in cui-jsf-test-basic, the executor bootstrap failure in every consumer with a stale executor — reported in inbox message `lb-37-functional-review-011.md`; the repaired files are already on those repositories' default branches, so a reproduction needs a fixture, not the live repository
- HYPOTHESIS: `VALID_LANE_OVERRIDE` is declared in `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_config_defaults.py` — `upgrade.py` imports it from there; confirm the declaration at outline (verify-at-outline)
  - verdict: corroborated | checked_at: 187f7314a | by: live-blockers/cleanup | rescoped: n/a | evidence: _config_defaults.py L555 declares VALID_LANE_OVERRIDE = ('off', 'minimal', 'standard', 'full', 'ask'); upgrade.py L620 imports it.
- HYPOTHESIS: the residual phase-3 `qgate` key still sits in cui-jsf-test-basic's `marshal.json` — confirm by reading that repository's default branch; this plan does not edit consumer repositories (verify-at-outline)
- Verify-first clause: before deliverable 5, re-run the consumer check above. A configured repository found without both review steps blocks the removal and is reported; it is not migrated by hand inside this plan.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/upgrade.py` — Stage 2 order, `migrate_bot_lists`, the retirement pass, the executor preflight, the removed review-step migration
- OBSERVED: `marketplace/bundles/plan-marshall/skills/marshall-steward/SKILL.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/marshall-steward/references/upgrade-flow.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_sync_defaults.py` — the bot-list back-fill and the lane mapping
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_config_core.py` — `normalize-keys` below the top level
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_config_defaults.py` — the seeded roster and the retired-key list (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_quality_phases.py` — only if dead-step detection lives beside `missing_order` (verify-at-outline)
- OBSERVED: `test/plan-marshall/marshall-steward/test_upgrade.py`
- OBSERVED: `test/plan-marshall/marshall-steward/test_upgrade_flow_stage2.py`
- OBSERVED: `test/plan-marshall/marshall-steward/test_review_step_migration.py` — deleted
- OBSERVED: `test/plan-marshall/manage-config/test_sync_defaults.py`
- HYPOTHESIS: `test/plan-marshall/manage-config/test_cmd_quality_phases.py` (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none. The consumer rollout it builds on is complete.
- Overlaps with: none of the running plans (PLAN-LB-26, 31, 39) on a declared file.
- Adjacent to: the nine consumer repositories — they were repaired by hand during the rollout and are not edited here; the PLAN-LB-37 code-review and functional-review steps themselves, which are not touched.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/live-blockers/plans/PLAN-LB-40-steward-upgrade-integrity.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
