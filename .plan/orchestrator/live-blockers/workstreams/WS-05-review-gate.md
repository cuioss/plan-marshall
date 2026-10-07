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
| PLAN-LB-18-coderabbit-quota-recovery | staged | CodeRabbit quota refusals are read correctly and waited out without a hung agent |
| PLAN-LB-19-review-gate-currency | staged | The merge gate credits only a review of the current commit |
| PLAN-LB-20-review-bot-fleet-rollout | staged | The remaining thirteen repositories get the in-house reviewer |
| PLAN-LB-21-in-house-reviewer-efficacy | staged | Measure whether the in-house reviewer finds anything, then decide the roster |

## Sequencing and Surface Notes

- LB-18 and LB-19 both edit the GitHub review provider scripts and `automatic-review/`; sequence them.
- LB-21 before LB-20: the measurement decides whether finishing the rollout is worth it.
