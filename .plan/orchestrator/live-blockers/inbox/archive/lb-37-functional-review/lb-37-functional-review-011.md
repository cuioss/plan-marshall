envelope_version=1
sender_type=plan
sender_id=lb-37-functional-review
epic=live-blockers
kind=finding
created=2026-10-14T06:00:58Z

# marshall-steward upgrade: defects found during the LB-37 consumer rollout

Running `/marshall-steward upgrade integrate=true` across the nine consumer repositories (TASK-26) surfaced the defects below. Each one left an invalid or lossy `marshal.json` that had to be repaired by hand. They need a plan of their own.

## 1. Reviewer lists are discarded (data loss)

**Observed in:** cuioss-parent-pom, cui-open-rewrite (both carried `enabled_bots: "coderabbit,sourcery,gemini"`).

**Mechanism:** Stage 2 runs `reconcile-marshal-json` (which includes `sync-defaults`) **before** `migrate-bot-lists`. `sync-defaults` back-fills empty `required_bots` / `optional_bots` keys; `migrate-bot-lists` then sees "a new key is present", classifies it as an operator answer (`state: operator_answer_kept`, `marshall-steward/scripts/upgrade.py` `migrate_bot_lists` state 2) and deletes the legacy list (`discarded_legacy`). The result is empty lists with no provenance.

**Needed:** run `migrate-bot-lists` before any defaults back-fill, or treat an empty back-filled key as "not answered" (only a non-empty value or provenance `answered` counts as an operator answer). Add a regression test with a legacy-only config run through the whole Stage 2 order, not the sub-step alone.

**Related operator directive:** every marshal.json must carry exactly `required_bots: "cuioss-review-bot,coderabbit"`, `optional_bots: "sourcery"`. Consider whether the seeded default and the migration target should be that value instead of a verbatim copy of the legacy list (the legacy lists contained the unregistered `gemini` and `pr-agent`).

## 2. Retired phase-level keys are left behind

**Observed in:** nifi-extensions, cui-jsf-test-basic.

**Keys no code reads any more:** `plan.phase-6-finalize.self_review`, `.simplify`, `.drop_review_on_scope_gate`; `plan.phase-3-outline.qgate` (superseded by `q_gate_validation`); `plan.phase-5-execute.per_task_budget_reserve_tokens`.

`migrate-review-steps` only handles `self_review` inside the retired step's param object, not the phase-level key; `sync-defaults` migrates only the phase-6 `qgate`; `normalize-keys` reported **no unrecognized keys** for these files, so nothing flags them.

**Needed:** a retirement pass (or `normalize-keys` schema check) that removes or at least reports every key no reader consumes, with the phase-level `self_review` mapped like the step-level one (`never`→`off`, `always`→`minimal`, `auto`→no lane).

## 3. Invalid lane value `auto` survives

**Observed in:** cui-open-rewrite — `lane: "auto"` on five steps (`finalize-step-simplify`, `automatic-review`, `pre-push-quality-gate`, `sonar-roundtrip`, `finalize-step-print-phase-breakdown`).

`auto` is not in `VALID_LANE_OVERRIDE` (`off, minimal, standard, full, ask`). The documented mapping is `auto` → omit the key (`_cmd_sync_defaults.py` run_at_all→lane shim), but values already written as `lane: "auto"` are never cleaned. No validator runs over existing step lanes.

**Needed:** upgrade normalizes `lane: "auto"` by removing the key and validates every stored lane against `VALID_LANE_OVERRIDE`, reporting the rest.

## 4. A dead step blocks adding the new review steps

**Observed in:** cui-jsf-test-basic — `default:finalize-step-whole-tree-gate`, a step with no doc in any cached plugin version (0.1.1841–0.1.1916).

`manage-config plan phase-6-finalize add-step` failed with `missing_order` on the dead entry, so `functional-review` / `code-review` could not be added. `sync-defaults` held both as `held_for_ask` instead of adding them (the repo lists its steps explicitly and never had the old step), so the migration left the repo with **neither** review step.

**Needed:**
- upgrade detects step ids that resolve to no implementor and removes them (or asks), instead of failing later on `missing_order`;
- for a repository that never had `pre-submission-self-review` but lists its steps explicitly (also cuioss-parent-pom, pm-mcp-core), adding both review steps is part of the migration, not an optional held default.

## 5. Executor bootstrap order

**Observed in:** every consumer whose executor was missing or pointed at a pruned cache version (`ModuleNotFoundError: plan_logging`).

`upgrade plan` needs the executor, but regenerating it is a Stage-1 sub-step of that plan, so every agent had to run `generate_executor.py generate` directly from the newest cache before the plan could be emitted.

**Needed:** the upgrade entry point regenerates (or validates) the executor before asking it for the stage plan.

## 6. Stale skill body vs. emitted plan (minor)

The session loaded `marshall-steward` 0.1.1900, whose `upgrade-flow.md` does not document `migrate-review-steps`, while the 0.1.1916 planner emitted it. The agents followed the 0.1.1916 doc. A session needs a restart after the registry repin to see the new skill body; the upgrade could warn when the loaded skill version differs from the planner's version.
