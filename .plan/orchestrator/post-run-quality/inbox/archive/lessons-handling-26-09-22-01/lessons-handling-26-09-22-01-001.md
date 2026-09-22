envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-22-01
epic=post-run-quality
kind=candidate-lesson
created=2026-09-22T07:15:14Z

# Candidate lessons routed from lessons-handling-26-09-22-01

6 lessons matched to this epic's scope (plan-retrospective, metrics/findings measurement substrate, the
lessons corpus, obligations an archived plan leaves behind). All `active` in the source corpus.

## Dispatch-boundary measurement gap (cross-ref pair)
- **2026-09-20-08-006** (primary): every one of the 12 `6-finalize` rows in the execution manifest's
  `execution_log` carries `total_tokens: unmeasured` / `tool_uses: unmeasured` / `duration_ms:
  unmeasured` — no `work/metrics-dispatch-boundaries-6-finalize.toon` is written at all, though the
  equivalent files exist for `4-plan` and `5-execute`.
- **2026-09-21-13-001**: `plan-retrospective`'s own Phase Dispatch Boundaries section is unreachable
  because its trigger key is never registered — the two are the same underlying gap viewed from
  producer and consumer sides.

## plan-retrospective inertness (shared-component pair)
- **2026-09-20-08-009** (primary): Step 2.5's metrics reconcile is inert when no phase accumulator file
  exists — the exact case it exists to catch.
- **2026-09-21-13-002**: the chat-signal pre-pass reports Tier 1 over a transcript truncated to its
  first line.

## Owed obligation with no owner after archival
- **2026-09-21-13-005**: "Owed architecture hints: preference-emitter, plan lessons-corpus-producers-
  report-success" — split out of the phase-6-finalize shared-component cluster (its 4 siblings went to
  `process-compliance` as finalize-mechanism defects) because this one is specifically the "obligation a
  finished plan left behind has no owner once archived" pattern this epic's own Vision names.

## manage-findings validator discipline (positive pattern, worth preserving not just fixing)
- **2026-09-21-10-008**: do not back-fill an empty assessment population to make a validator pass —
  record it unverified instead. `assessment_coverage` had no filed component assessment; back-filling
  CERTAIN_INCLUDE assessments from the same deliverable list the check measures would have manufactured
  100% coverage by construction. This was correctly REJECTED in the observed instance; recorded as a
  reusable positive pattern rather than a bug to fix.

## Disposition
All 6 are `standalone`/`clustered-into`, none `already-covered`. Source files removed from
`.plan/local/lessons-learned/` after this message is confirmed queued.
