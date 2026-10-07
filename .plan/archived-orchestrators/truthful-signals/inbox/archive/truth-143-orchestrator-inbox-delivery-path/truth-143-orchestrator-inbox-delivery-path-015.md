envelope_version=1
sender_type=plan
sender_id=truth-143-orchestrator-inbox-delivery-path
epic=truthful-signals
kind=candidate-lesson
created=2026-09-20T08:28:08Z

# Candidate lesson (positive pattern): an empty assessment population was recorded UNVERIFIED, and back-filling it was rejected as circular

## Signal source

Q-Gate `3-outline` finding `434242`, resolved `taken_into_account`.

## Observation

The outline's `assessment_coverage` validator could not render a verdict: `manage-findings assessment list --certainty CERTAIN_INCLUDE` returned `total_count: 0` with `findings_store_state: missing`. No component assessment had ever been filed, so the assessed-file population was **empty rather than exhaustive**.

Two wrong readings were available and both were declined:

- Applying the check literally would have flagged all 21 declared paths as unassessed — a statement about the missing assessment pass, not about the deliverables.
- **Back-filling `CERTAIN_INCLUDE` assessments for the declared affected_files was considered and explicitly REJECTED as circular**: the assessment list would have been derived from the very deliverable lists the check measures, producing 100% coverage by construction and manufacturing exactly the unmeasured-zero-read-as-clean failure this plan exists to close.

The finding was instead recorded as an **unevaluated validator, not a clean pass**, and carried forward as a known gap.

## Why this is worth recording

This is the epic's thesis executed correctly under pressure, and it is worth having a named precedent for three reasons:

1. **It names the circularity test.** A remedy that would make a check pass by deriving its reference population from the thing being checked is not a remedy. The check's value depends on the assessed population being *independent* of the deliverables.
2. **It establishes a third verdict state as legitimate.** "Unverified" is a real outcome distinct from pass and fail, and recording it cost nothing while a false green would have been unrecoverable.
3. **It is the counter-example to the default reflex.** The cheap move — make the red thing green — was available, one call away, and defensible-sounding. The reasoning that rejected it is reusable and should be quotable rather than re-derived each time.

## Corrective rule

Before resolving an unevaluated validator by populating its reference set, ask: **would the population be derived, directly or indirectly, from the artifact under test?** If yes, the validator stays unevaluated and the gap is carried forward explicitly. Do not convert an absence of measurement into a measurement of absence.
