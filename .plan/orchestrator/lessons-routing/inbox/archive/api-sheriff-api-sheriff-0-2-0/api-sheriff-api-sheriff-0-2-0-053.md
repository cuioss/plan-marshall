envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=candidate-lesson
created=2026-10-24T15:38:01Z

# Candidate lesson: a rebase rewrites commit SHAs and the 5->6 transition refuses with execute_commits_unrecorded (plan-marshall:manage-change-ledger)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-23-cookie-forwarding-policy-r2 (PR cuioss/API-Sheriff#515, merge bd730f5a), inbox message(s) plan-v02-23-cookie-forwarding-policy-r2-001.

A rebase of the plan branch onto a moved main rewrote 13 of 17 commit SHAs. The 5-execute to 6-finalize transition then refused: "13 of 17 worktree-branch commit(s) since diverging from main carry no kind=change ledger row". The work was recorded before the rebase; only the SHAs changed. Recovery was one hand-appended kind=change row per new SHA. The refusal text points at Step 10a bookkeeping, which reads as "work not recorded", not "history rewritten".

Suggested direction: make the ledger rebase-aware (map old to new SHAs by patch-id or range-diff), or add a re-key verb. At minimum, detect unrecorded commits whose patch-ids match recorded rows and name the re-key remedy in the refusal.
