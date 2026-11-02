envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=candidate-lesson
created=2026-10-22T05:50:10Z

# Candidate lesson: git-workflow commit refused with no_sanction for a finalize inline correction filed after the commit (phase-6-finalize source-commit sanction)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-45-request-body-and-h2-buffer-bounds (PR cuioss/API-Sheriff#506), source message 015.

A docs-only inline correction in 6-finalize was committed before its review-rubric section 6 inline-correction Q-Gate record existed; `git-workflow commit` refused with `no_sanction`. Filing the record and retrying succeeded. The guard worked as designed; the cost was one refused call.

Candidate rule for the finalize guidance: file the inline-correction record (or open the fix task, or pass --step) before calling git-workflow commit, and say so in the inline-correction procedure where the commit step is described.
