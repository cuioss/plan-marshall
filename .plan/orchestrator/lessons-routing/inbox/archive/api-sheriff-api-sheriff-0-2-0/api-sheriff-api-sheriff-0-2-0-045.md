envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=candidate-lesson
created=2026-10-22T05:50:10Z

# Candidate lesson: execute_commits_unrecorded after a loop-back fix pass (phase-5-execute Step 10a / transition gate)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-45-request-body-and-h2-buffer-bounds (PR cuioss/API-Sheriff#506), source message 014.

RECURRENCE of api-sheriff-api-sheriff-0-2-0-010 and -031.

`manage-status transition --completed 5-execute` returned `execute_commits_unrecorded` twice in PLAN-V02-45: first one of seven commits had no kind=change ledger row, then after a loop-back from finalize eight commits had none. The remedy in the message worked both times (Step 10a settlement bookkeeping, then retry), about 25-30 s per refusal.

Third occurrence in this epic: the loop-back path still does not run the settlement bookkeeping before it tries the transition. Candidate fix: run Step 10a as part of the loop-back fix pass's close, before the transition call, rather than relying on the refusal.
