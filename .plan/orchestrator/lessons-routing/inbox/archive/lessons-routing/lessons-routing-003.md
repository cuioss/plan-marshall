envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=lessons-routing
kind=finding
created=2026-10-27T05:55:19Z

# Two phase guards are learned from a refused transition instead of up front

Source: API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-20-cookie-key-file-model (PR #527), candidate lessons 010 and 013. Observed with plugin and executor 0.1.2010.

## Observation

1. After the operator answered the outline prompts, one answer changed the file format and so revised the success criteria. The transition `--completed 3-outline` was refused with `refreeze_requires_decision`: `work/criteria-snapshot.json` was frozen at outline approval and re-freezing needs an operator decision logged through `criteria-refreeze-authorize`. The authorization was logged and the transition went through. The same re-freeze was needed again in 4-plan.
2. The end-of-5-execute transition was refused because one of seven worktree-branch commits since diverging from main carried no `kind=change` ledger row. It succeeded after `manage-change-ledger append --kind change` was run for that commit. The commit came from a fix made outside a task's normal commit step.

## What to consider

- When an outline-prompt answer is known to change success criteria, record the re-freeze authorization in the same step as the answer, or have the prompt flow offer it, so the need is not discovered from a refused transition.
- Find which execute path produced a commit with no ledger row (a verification-driven fix outside a task) and make that path append the row itself, so the transition guard is a backstop and not the first signal.
