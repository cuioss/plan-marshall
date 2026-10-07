envelope_version=1
sender_type=orchestrator
sender_id=orchestrator-refactor
epic=review-apparatus
kind=finding
created=2026-10-05T14:43:13Z

# Transfer from `orchestrator-refactor` (epic closing, routed by operator decision)

## `ci checks pull-request-runs` read `run_count=0` on a PR that had pull_request checks

This was observed during PLAN-09's finalize on PR #1652 (`orchestrator-worktree-substrate`, merged as `438a0a71f`). `ci checks pull-request-runs` returned `run_count=0` although the PR had `pull_request`-triggered checks. A zero there reads as "never triggered". When the verb is used as the `not_triggered` observable, a wrong zero makes the run look like it was never triggered when it was.

This is a lead and has not been re-verified at HEAD. Re-run the verb against #1652 and compare the result with the PR's actual check runs before staging. It is related to the known gap where `ci checks status` can omit a workflow's nested checks.
