envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=candidate-lesson
created=2026-10-22T05:50:08Z

# Candidate lesson: A fix task leaves decision-log entries stating superseded behaviour (phase-5-execute fix tasks / decision log)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-45-request-body-and-h2-buffer-bounds (PR cuioss/API-Sheriff#506), source message 005, 006.

Fix task 11 changed two properties of a deliverable's behaviour (when the request-body deadline arms and when it fires). The decision-log hand-off entry that reported that deliverable's result was not superseded, so the functional review flagged it twice: once as a residual on the deliverable, once as a false self-report on the entry. Same root cause.

Candidate rule: a fix task's closing step re-reads the decision-log entries describing the behaviour it changed and appends a superseding entry restating the result against the new behaviour, in the same task. The functional review should not be the first reader to notice.
