envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T15:13:52Z

# Dispatch-boundary rows record zero tokens for late re-entries; finalize reruns record no row

**Component:** plan-marshall:manage-metrics (`record-dispatch-boundary`, `enrich`), plan-marshall:phase-5-execute and plan-marshall:phase-6-finalize dispatch sites
**Category:** bug
**Source plan:** plan-14-operator-and-question-stores, from plan-retrospective

## Observation

`work/metrics-dispatch-boundaries-5-execute.toon` holds 13 rows. The last four (08:21Z, 08:34Z, 11:06Z, 11:18Z; envelopes 5 and 6, which ran fix tasks 15-24) record `total_tokens 0`, `tool_uses 0` and `duration_ms 0`, although those envelopes did real work (two commits, 10 tasks, repeated `test -pl pm-core` runs). The 6-finalize file has 9 rows, the last at 07:12Z, but the finalize review chain ran five times in total and dispatched about 45 times (dispatch audit channel ratio 0.214, confidence low). Every row also has its four token-split columns unmeasured. As a result, phase totals are floors, and a recorded `0` reads as a measured zero.

## Suggested corrective action

- Never write a measured `0` when the `<usage>` figure was not captured: record the columns as unmeasured, as the split columns already are.
- Find why rows stopped after the 07:12Z finalize dispatch, and why the late execute rows carry zeros. Both started after the session compaction, which suggests the dispatcher lost the usage-capture step on resume.
