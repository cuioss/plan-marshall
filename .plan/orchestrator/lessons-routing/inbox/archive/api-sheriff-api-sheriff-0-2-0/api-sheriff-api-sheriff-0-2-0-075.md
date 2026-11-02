envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=finding
created=2026-10-30T06:51:28Z

# `manage-status loop-back admit` spends a ceiling round on a fresh HEAD-advance re-fire

**Component:** `plan-marshall:manage-status` (`loop-back admit`) and the `phase-6-finalize` item 7b admission gate.

**What happened (API-Sheriff PR #537, plan `plan-v02-07-threat-classification`).** `loop-back admit --source plan-marshall:automatic-review --ceiling 3` increments the persisted per-source count in the same call that decides admission. The orchestrator called it while preparing a re-dispatch of `automatic-review` that was a plain re-fire after a HEAD advance (the record had been invalidated by the new head), not a loop-back that the step had requested. The call still consumed round 3 of 3 for that source, with no warning that nothing had requested a loop-back; any real loop-back from that step afterwards would have been refused at the ceiling.

**Why it is easy to hit.** The same verb name appears in the re-entry narrative for both situations (a step that recorded `loop_back`, and a step re-fired because its `head_at_completion` is stale). The admission is a write, not a read, so an exploratory call is not free.

**Suggested fix.** Either add a read-only `loop-back check`/`--dry-run` that reports `admitted`/`iteration` without persisting, or make the doc state explicitly that `admit` is only called on a recorded `loop_back` outcome, never on a HEAD-advance re-fire.
