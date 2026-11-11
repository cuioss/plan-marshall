envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-security-hardening-tier-1
epic=lessons-routing
kind=candidate-lesson
created=2026-11-09T11:45:57Z

component=plan-marshall:workflow-integration-git
category=bug
title=worktree-rebase-to returns a generic error on a conflicting rebase, and no verb covers continue/abort

# worktree-rebase-to returns a generic error on a conflicting rebase, and no verb covers continue/abort

Source: API-Sheriff epic `security-hardening-tier-1`, inbox message `plan-sec-03-pending-authorization-store-fairness-003.md` (plan `plan-sec-03-pending-authorization-store-fairness`, PR cuioss/API-Sheriff#581, 2026-11-09). Related to, but distinct from, the earlier `worktree-rebase-to` executor drift-probe lessons (`api-sheriff-api-sheriff-0-2-0-040`, `pm-mcp-core-m2-m4-044` / `-217`): those concern the drift probe; this concerns the conflict outcome.

## Observation

The feature branch was rebased onto a base that had moved because another PR had landed on main, and the rebase hit a content conflict. `git-workflow worktree-rebase-to` returned a generic `status: error`. It did not return a structured conflict outcome naming the conflicted files and leaving the rebase in a resumable, documented state.

The rebase was left mid-flight in the worktree. After the conflicts were resolved by hand, it had to be continued with a raw `git -c core.editor=true rebase --continue`. The `core.editor=true` is needed because a non-interactive `rebase --continue` otherwise tries to open an editor for the commit message.

## Why it matters

- Callers branch on `status`. An error cannot be told apart from an infrastructure failure, so a finalize step cannot route a conflict deterministically to the conflict-resolution path or to the operator.
- The manual continue bypasses the gated git surface entirely, the opposite of what the phase-6 git discipline wants.

## Suggested correction (from the reporting plan)

- Return a distinct outcome (for example `status: conflict` or `action: conflict`) carrying `conflicted_files[]` and the in-progress rebase state.
- Add sanctioned `rebase-continue` / `rebase-abort` verbs, with continue using a non-interactive editor, so the conflict path never needs raw git.
