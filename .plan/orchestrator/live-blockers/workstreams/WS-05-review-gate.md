# WS-05: Automated Review Gate

epic: live-blockers

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-05-review-gate.md` and is tracked in the
> `workstreams[]` field of the epic header, `status.json`. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

The review bots and the gate that reads them. The workstream closes when a review-bot refusal is recovered without operator babysitting, the merge gate only credits a review of the commit being merged, the bot fleet is enrolled, and the required in-house reviewer has a measured reason to be required.

## Scope

- In scope: the `automatic-review` step, the GitHub review provider scripts, review-comment triage replies, bot configuration and fleet rollout in other repositories
- Out of scope: short poll pacing and CI-timeout classification (WS-01, PLAN-LB-05)

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-LB-24-review-step | staged | Runnable completion poll; CodeRabbit quota recovery that finishes; the gate credits only a review of the merge commit |
| PLAN-LB-31-in-house-reviewer | staged | Measure the in-house reviewer, decide its roster place, then finish the fleet enrolment |
| PLAN-LB-18-coderabbit-quota-recovery | superseded | PLAN-LB-24 (all deliverables) |
| PLAN-LB-19-review-gate-currency | superseded | PLAN-LB-24 (all deliverables) |
| PLAN-LB-20-review-bot-fleet-rollout | superseded | D1 to D3 to PLAN-LB-30; D4 and D5 to PLAN-LB-31 |
| PLAN-LB-21-in-house-reviewer-efficacy | superseded | PLAN-LB-31 (all deliverables) |

## Sequencing and Surface Notes

- PLAN-LB-24 shares `phase-6-finalize/SKILL.md` with PLAN-LB-22, PLAN-LB-25 and PLAN-LB-27 and `merge_lock.py` with PLAN-LB-25; it may run beside PLAN-LB-23.
- PLAN-LB-31 starts its measurement at once; its two enrolment deliverables wait for the schema PLAN-LB-30 releases.
