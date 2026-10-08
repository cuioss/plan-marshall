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
| PLAN-LB-29-harness-sync | staged | Registry pin follows every Claude sync; non-Claude installs ship every routed file |
| PLAN-LB-30-org-ci-release | staged | Test-input paths force a verify build; project.yml validates against a truthful schema; one organisation release |
| PLAN-LB-15-plugin-registry-pin | superseded | PLAN-LB-29 (all deliverables) |
| PLAN-LB-16-config-only-prs-skip-verify | superseded | PLAN-LB-30 (all deliverables) |
| PLAN-LB-17-non-claude-workflow-docs | superseded | PLAN-LB-29 (all deliverables) |

## Sequencing and Surface Notes

- PLAN-LB-29 runs after PLAN-LB-14 (shared `orchestrator.py`). PLAN-LB-30 shares no file with any plan of the epic.
- PLAN-LB-30 needs an organisation release, which the operator cuts; start it early because of that lead time.
