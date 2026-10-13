envelope_version=1
sender_type=plan
sender_id=lb-37-functional-review
epic=live-blockers
kind=finding
created=2026-10-12T11:40:40Z

# Follow-up: remove the migrate-review-steps migration in a later plan

**From:** lb-37-functional-review (PLAN-LB-37)
**Operator instruction:** keep the migration in PLAN-LB-37, and remove it again in one of the next plans.

## What

PLAN-LB-37 deliverable 8 added a one-shot `marshall-steward upgrade` Stage-2 sub-step, `migrate-review-steps`. It rewrites a `marshal.json` that still names the retired `default:pre-submission-self-review` step (and the retired `self_review` ceremony key) onto `default:functional-review` + `default:code-review` and the separate `functional_review` / `code_review` keys.

## Why it should go

The operator decided that every configured consumer repository is migrated immediately after PLAN-LB-37 lands (deliverable 10 / TASK-26, the post-landing rollout across the 8 consumer repositories). Once that rollout is done, no configuration naming the old step is expected to remain, so the migration has no lasting purpose. The operator called it of no real sense given that decision, but asked to keep it for now and remove it in a follow-up plan.

## Scope of the removal (for the follow-up plan to verify against HEAD)

- `marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/upgrade.py` — the `migrate-review-steps` subcommand, `_merged_review_params`, and its SHIM(A) marker block
- `marketplace/bundles/plan-marshall/skills/marshall-steward/SKILL.md` and `references/upgrade-flow.md` — the sub-step's documentation and Stage-2 ordering
- `test/plan-marshall/marshall-steward/test_review_step_migration.py` and the related cases in `test_upgrade.py` / `test_upgrade_flow_stage2.py`
- `pm-plugin-development/skills/plugin-doctor/references/rule-catalog.md` and `test/pm-plugin-development/plugin-doctor/test_analyze_shim_marker.py` — the shim-marker recall figures move back down when the SHIM(A) marker goes
- These four D8 files are the only places the retired step id and `self_review` still appear outside `.plan/orchestrator/**`, `doc/adr/**` and `doc/analyzis-cloud-plan/**`; after the removal the retired ids should appear nowhere outside those trees.

## Precondition

Remove only after the post-landing rollout (PLAN-LB-37 D10) is confirmed complete for every configured repository, or after the operator confirms no repository still needs the migration.
