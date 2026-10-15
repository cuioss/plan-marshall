# PLAN-LB-60: Fix-forward for PLAN-LB-40 — a config sync never deletes what it cannot see, and the upgrade starts without a working executor

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-LB-60-lb-40-regression-fixes.md` and is queued as one row file,
> `queue/PLAN-LB-60.json`, in the epic ledger. The orchestrator EMITS the command below; it never
> launches the plan inline. This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer
> and carries no brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged 2026-10-15 from the adversarial landing analysis of PLAN-LB-40 (#1774, `f5d661d87`),
> `landings/PLAN-LB-40.md`: 2 met / 2 partial / 1 unmet against its spec, four regressions on
> `main`. **Each deliverable is its own outline deliverable, and each Done-when is its own success
> criterion — copy them, do not rewrite them. Do not merge deliverables.** A criterion that says
> "fails at `f5d661d87`" is evidenced only by a run against that tree. Every test cited as evidence
> must exist at the graded head.

## Objective

PLAN-LB-40 made `sync-defaults` repair a `marshal.json`, but the repair now runs on every sync — the
wizard's silent materialize step included — and it deletes configured steps whenever plugin
discovery comes back empty for any reason. `normalize-keys` warns on the product's own
`removed_steps` key. And the headline failure the plan existed for — an upgrade that cannot start
because the executor is missing or points at a pruned cache — is still there.

## Deliverables

1. **Dead-step detection fails closed.**
   - `_find_dead_step_ids` (`_cmd_quality_phases.py:212`) distinguishes "discovery answered and no
     implementor exists" from "discovery returned nothing or failed"
     (`extension_discovery.py:1268-1276, 1336-1338`); the second is `unknown` and deletes nothing.
   - A removed dead step is recorded in `removed_steps` with its params, and reported; a `project:`
     step whose `SKILL.md` lacks `implements:` is reported, never deleted.
   - At least one test runs real discovery (no monkeypatch of `_find_dead_step_ids`).

   *Done when:* tests: a discovery surface that returns `[]` because its directory is absent
   deletes no step; a genuinely dead `default:` id is removed AND recorded in `removed_steps`; a
   `project:` step without `implements:` is reported and kept; one test uses real discovery over a
   fixture tree. The first three fail at `f5d661d87`.

2. **`sync-defaults` outside an upgrade adds nothing the operator did not answer.**
   - The bot-roster back-fill runs only inside the upgrade's Stage 2 (or carries an explicit flag
     the upgrade passes); a plain `sync-defaults` — the wizard's materialize step, the re-run
     remediation pass — leaves a never-answered `required_bots` / `optional_bots` as it is.
   - When the upgrade back-fills, it records `bot_lists_provenance` so never-asked and
     answered-empty stay distinguishable (marshall-steward `SKILL.md:389, 431-433`).
   - The docs state one default: manage-config `SKILL.md:718, 790`, `data-model.md:111-113,
     356-369`, marshall-steward `SKILL.md:389, 443-444` (the "VERBATIM" sentence).

   *Done when:* tests: a never-answered config through plain `sync-defaults` keeps empty lists and
   no provenance; the same config through the upgrade's Stage 2 ends with the standard roster and
   a provenance value; a doc test finds no "VERBATIM" seeding sentence. The first fails at
   `f5d661d87`.

3. **`normalize-keys` knows the product's own nested keys.**
   - `removed_steps` (both phases) and every other key the product writes below the top level are
     recognised (`_NESTED_DIFF_DYNAMIC_PREFIXES`, `_config_core.py:927`), sourced from the
     declaring constants rather than a second list.
   - The `test_config_write_guard.py:91-121` fixtures go back to arbitrary nested keys, so the
     guard's behaviour on unknown keys is tested again.

   *Done when:* `normalize-keys` on this repository's `.plan/marshal.json` returns no warning (it
   reports `plan.phase-6-finalize.removed_steps` at `f5d661d87`); a config after `remove-step` is
   warning-free; an invented nested key still warns.

4. **The upgrade starts with a missing or broken executor, and regenerates only with consent.**
   - The upgrade's entry (marshall-steward `upgrade-flow.md` Step 0) has a path that does not need
     a working `.plan/execute-script.py`: when the executor is missing or fails to import
     (`ModuleNotFoundError`), it runs the planner by its cache path and regenerates the executor
     from the newest cache.
   - Regeneration outside that recovery case asks first — `--bootstrap` defaults to `false`, or
     the bootstrap moves behind Stage 1's prompt — so `integrate=false` never rewrites the
     executor unasked (`upgrade.py:973-975`).
   - The version-split warning compares the loaded `marshall-steward` skill version with the
     planner's version, as specified, not only the executor stamp with the cache
     (`resolve_bootstrap_action`, `upgrade.py:732-764`).

   *Done when:* tests: the upgrade reaches the stage plan with (a) no executor and (b) an executor
   whose imports fail; a stale executor with `integrate=false` and no consent is reported, not
   rewritten; a loaded skill 0.1.1900 with planner 0.1.1916 warns. Each fails at `f5d661d87`.

5. **The legacy roster migration reports what it dropped, tested through the real order.**
   - A legacy `enabled_bots` naming a bot the registry does not know (`gemini`, `pr-agent`) yields
     a report naming each dropped bot, not the raw legacy string.
   - One test runs `cmd_sync_defaults` then `cmd_migrate_bot_lists` (the real Stage 2 order) on the
     bug shape — `enabled_bots` set, `required_bots: ''`, `optional_bots: ''`.
   - One test shows `add-step` succeeding on a config the upgrade cleaned of a dead step.

   *Done when:* those three tests exist and pass; the first and second fail at `f5d661d87`.

Split guard: five deliverables, one surface (the steward upgrade and the manage-config sync it
calls). D4 is the original PLAN-LB-40 D4, unmet.

## Claim Labels

- OBSERVED: `_config_core.unrecognized_nested_keys` on `.plan/marshal.json` at `f5d661d87` returns `['plan.phase-6-finalize.removed_steps']` — orchestrator-run.
- OBSERVED: `upgrade.py:973-975` `--bootstrap` choices `true|false`, default `true` — orchestrator-read.
- OBSERVED: no test named `test_add_step_no_longer_fails_missing_order` or `test_dead_step_id_removed_or_reported` exists at `origin/main`; PLAN-LB-40's verdict cites the first — orchestrator-checked.
- OBSERVED: every sync test monkeypatches `_find_dead_step_ids`; discovery surfaces return `[]` on absent dir / `OSError` / unresolvable root (`extension_discovery.py:1268-1276, 1336-1338`) (delegated agent).
- OBSERVED: the bootstrap is inside `upgrade.py plan`, reached only through `.plan/execute-script.py` (`upgrade-flow.md` Step 0); no test starts without an executor (delegated agent).
- OBSERVED: the wizard runs `sync-defaults` silently (`wizard-flow.md:827-833`) (delegated agent).
- HYPOTHESIS: the planner can run from the newest cache path without the executor (its imports resolve through `PM_MARKETPLACE_ROOT`, as `_run_bootstrap_generate` already does) — confirm at outline (verify-at-outline).
- Verify-first clause: before D1, list every caller of `_find_dead_step_ids` and `_remove_dead_step_ids` (`architecture search --content`). Record the result in the decision log BEFORE changing either — the evidence must predate the change.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_quality_phases.py` (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_sync_defaults.py` (D1, D2)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/extension_discovery.py` — only if "unknown" must be signalled there (verify-at-outline) (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_config_core.py` (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_config_defaults.py` (D2, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/SKILL.md` (D2)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-config/standards/data-model.md` (verify-at-outline) (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/upgrade.py` (D2, D4, D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/marshall-steward/SKILL.md` (D2, D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/marshall-steward/references/upgrade-flow.md` (D4)
- OBSERVED: `test/plan-marshall/manage-config/test_sync_defaults.py` (D1, D2)
- OBSERVED: `test/plan-marshall/manage-config/test_cmd_quality_phases.py` (D1, D5)
- OBSERVED: `test/plan-marshall/manage-config/test_config_write_guard.py` (D3)
- OBSERVED: `test/plan-marshall/marshall-steward/test_upgrade.py` (D4, D5)
- OBSERVED: `test/plan-marshall/marshall-steward/test_legacy_bot_list_migration.py` (D5)

## Dependencies and Sequencing

- Depends on: none. High priority: regression 3 can delete a consumer's configured steps on any
  wizard run.
- Overlaps with: PLAN-LB-50 (running) on the `marshall-steward/scripts/` directory
  (`configure_harness.py`, a different file). The gate will ask.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/live-blockers/plans/PLAN-LB-60-lb-40-regression-fixes.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
