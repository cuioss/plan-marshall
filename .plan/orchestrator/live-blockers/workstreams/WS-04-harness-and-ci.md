# WS-04: Harness Sync and CI

epic: live-blockers

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-04-harness-and-ci.md` and is tracked in the
> `workstreams[]` field of the epic header, `status.json`. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

Things the rewrite does not replace: how the harness installs are kept current, what CI verifies, and what the non-Claude targets receive. The workstream closes when a landing leaves every harness current without a manual repair, and a config-only change cannot redden `main`.

## Scope

- In scope: `marketplace/targets/`, the project-local sync skills, `.github/workflows/`, the organisation reusable workflow
- Out of scope: review-bot workflows (WS-05)

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-LB-15-plugin-registry-pin | staged | A harness sync leaves the plugin registry current, or says loudly that it is not |
| PLAN-LB-16-config-only-prs-skip-verify | staged | A change to test-relevant config cannot skip the test build |
| PLAN-LB-17-non-claude-workflow-docs | staged | OpenCode and Antigravity installs carry every document a skill routes to |

## Sequencing and Surface Notes

- LB-15 and LB-17 both edit `marketplace/targets/sync.py`; sequence them.
- LB-16 is mostly foreign-repo work in `cuioss-organization`.
