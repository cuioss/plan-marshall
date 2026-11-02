envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=candidate-lesson
created=2026-10-17T09:32:42Z

# Candidate lesson: build-server wait long-poll floods the plan work log at the 300 s boundary

Forwarded from API-Sheriff epic `api-sheriff-0-2-0`, plan `plan-v02-44-route-type-merge` (PR cuioss/API-Sheriff#476), source message 009. Suggested route: plan-marshall (build-server-client wait / long-poll re-arm logging).



**Signal:** found while reading the work log for this capture. It is not one of the three forwarded signal counts, but it is a concrete defect.

## What happened

Most of the plan's 1746 work-log entries are the same line repeated within a single second, each time a long build reached the 299-300 s long-poll ceiling:

- job a17f46ec... at 2026-10-16T06:14:19-20Z: roughly 340 identical `build-server wait result: ... job_status=running elapsed=299 eta=61.9` lines (hashes 43b262 / ca1878)
- job 06884d62... at 07:53:35-36Z: several hundred lines (hashes 0d4a2c / a4861b)
- job a03d42ea... at 08:46:36Z: several hundred lines (hashes 5c13ec / e8afd1)

Each job did finish normally. But the client seems to re-poll in a tight loop once `elapsed` reaches the per-wait budget, without sleeping or re-arming the long-poll, and it logs every iteration. The flood makes the work log hard to read (this capture had to page around it) and suggests the wait loop is spinning against the daemon.

## Suggested corrective action

When the per-call wait budget is exhausted while the job is still `running`, the client should either re-arm a fresh long-poll with a reset `elapsed`, or return a single `still running` result. It should log once per re-arm, not once per iteration. A test that runs a fake daemon past the budget and asserts a bounded number of wait-result log lines would catch it.
