envelope_version=1
sender_type=plan
sender_id=lb-37-functional-review
epic=live-blockers
kind=finding
created=2026-10-14T06:00:32Z

# LB-37 post-landing deliverables done: consumer rollout (TASK-26 / D9) and review-bot code-review pass (TASK-27 / D15)

Both post-landing deliverables owed by PLAN-LB-37 (landing message lb-37-functional-review-009) are complete. The landing Residue entries for TASK-26 and TASK-27 can be closed.

## TASK-26 / D9 — consumer rollout

Every repository under `/home/oliver/git/` with a `.plan/marshal.json` (re-derived at run time: the eight from the plan plus `pm-mcp-core`) was migrated onto `default:functional-review` + `default:code-review` via `/marshall-steward upgrade integrate=true`, shipped through a `chore/migrate-review-steps` PR, and merged through each repository's merge queue:

| Repository | PR |
|---|---|
| cuioss/API-Sheriff | #441 |
| cuioss/TokenSheriff | #802 |
| cuioss/cui-http | #284 |
| cuioss/cui-jsf-test-basic | #215 |
| cuioss/cui-open-rewrite | #197 |
| cuioss/cuioss-parent-pom | #1515 |
| cuioss/nifi-extensions | #650 |
| plan-marshall/plan-marshall-mcp | #74 |
| plan-marshall/pm-mcp-core | #57 |

Beyond the steward's migration, each `marshal.json` was checked by hand against the 0.1.1916 schema and corrected where invalid:

- every repository's `plan-marshall:automatic-review` step now carries exactly `required_bots: "cuioss-review-bot,coderabbit"`, `optional_bots: "sourcery"`, `bot_lists_provenance: "answered"` (operator directive: this is the only correct value for every marshal.json);
- `lane: "auto"` (not a valid lane override) removed from five steps in cui-open-rewrite;
- the dead step `default:finalize-step-whole-tree-gate` removed and both review steps added in cui-jsf-test-basic;
- retired keys removed where present: phase-6 `self_review`, `simplify`, `drop_review_on_scope_gate`; phase-3 `qgate`; phase-5 `per_task_budget_reserve_tokens`. One residue: the phase-3 `qgate` key remains in cui-jsf-test-basic (the edit was blocked by the permission classifier; the key is read by nothing).

## TASK-27 / D15 — the external bot reads the same rulebook

The code-review packs were already published to `cuioss/cuioss-review-bot` (publish PR #68) and match what current plan-marshall `main` generates. The operator chose a two-pass design: the security pass is unchanged, and a separate code-review pass runs next to it.

- **cuioss/cuioss-organization #326** (merged; released by the operator as **v0.42.0**, tag commit `711571432df351d3c5b08d5d50cb6c331f61abb1`): a new `code-review` job in `reusable-cuioss-review-bot.yml`, parallel to `review`, with its own check `review / code-review`. Opt-in through a nested `cuioss-review-bot.code_review: {enabled, packs, additional_rules}` block in `.github/project.yml`, independent of the outer `enabled`, fail-closed on malformed declarations. The charter is `code-review-spine.md` plus the selected `code-review-*` packs. A publisher script posts the review as its own persistent comment `## PR Code Review Guide 🧭`, so it never overwrites the security comment `## PR Reviewer Guide 🔍`; the fail-closed gate accepts only a comment carrying exactly this run's review (content match, no timestamp path, so overlapping runs cannot satisfy each other). A comment-triggered run is refused unless it is a plain `/review`, which closes the `--config.publish_output=true` bypass. The security-concerns row is kept in the code-review comment (operator choice).
- **cuioss/cuioss-review-bot #69** (merged): comment-only `.pr_agent.toml` note, `validate-packs` also requires both spines, and the docs describe the two passes and the v0.42.0 prerequisite.
- **cuioss/plan-marshall #1767** (merged, `187f7314a`): `automatic-review` recognises the second comment as cuioss-review-bot participation (new registry field `contentless_review_headings`; the contentless-guide rule applies per comment; one current Guide credits the bot), and plan-marshall's `.github/project.yml` opts in with `code-review-python`, `code-review-plan-marshall-plugin-dev`, `code-review-documentation`. The caller pin was already v0.42.0 on main.

## Still to confirm

The `code_review` block took effect only with #1767's merge, so no live code-review comment exists yet. The first plan-marshall PR after `187f7314a` should show both comments and both checks green. Its code-review comment confirms the real comment shape, which the registry (`automatic-review/standards/cuioss-review-bot.md`) still marks UNVERIFIED.
