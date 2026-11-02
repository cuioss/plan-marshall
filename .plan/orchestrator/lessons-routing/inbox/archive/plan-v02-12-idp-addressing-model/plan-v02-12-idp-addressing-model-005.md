envelope_version=1
sender_type=plan
sender_id=plan-v02-12-idp-addressing-model
epic=lessons-routing
kind=finding
created=2026-10-20T20:29:41Z

# Recurrence: execute_commits_unrecorded refused after a rebase because the ledger holds the pre-rebase SHA (plan-marshall:manage-status / manage-change-ledger)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-12-idp-addressing-model (PR cuioss/API-Sheriff#492), lessons-capture step.

Recurrence of pending message api-sheriff-api-sheriff-0-2-0-010 ("execute_commits_unrecorded miscounts after the finalize baseline rebase"). New in this occurrence: the rebase happened during 5-execute, not at the finalize baseline sync, so the defect is not specific to finalize.

## Evidence

- Work log 2026-10-20T13:16:41Z: the 5-execute -> 6-finalize transition refused with "1 of 7 worktree-branch commit(s) ... carry no kind=change ledger row". The commit was c9fc294c (rebased D5 commit); the ledger held the pre-rebase b1e0fcfe. Recovery: append a D5 change row for c9fc294c by hand, retry once.
- Work log 2026-10-20T14:14:48Z and 14:15:21Z: the same refusal fired twice more ("1 of 9").

## Suggested direction

Match ledger rows to commits by patch-id (or rewrite recorded SHAs on rebase) rather than by raw commit SHA, so a rebase never makes a recorded commit read as unrecorded.
