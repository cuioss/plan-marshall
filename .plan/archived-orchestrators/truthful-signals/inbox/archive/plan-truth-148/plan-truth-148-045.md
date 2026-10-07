envelope_version=1
sender_type=plan
sender_id=plan-truth-148
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:04:23Z

# Candidate lesson: a deep-lane plan's assessment-coverage arm ran against an empty population

- source_signal: qgate / 3-outline
- record_id: 07f147
- component: q-gate-assessment-coverage
- resolution: taken_into_account — recorded as ONE declared coverage gap, deliberately not as 24 per-file flags

## What happened

Section 2.2 Assessment Coverage and Step 5 Missing Coverage both read the CERTAIN_INCLUDE assessment set. For this plan that read returned `total_count 0` with `findings_store_state: missing` — the plan directory existed and no assessment was ever filed, though `planning_lane: deep` meant outline-time assessments were expected. Both arms produced no verdict.

The handling was right: recorded as one coverage gap rather than 24 per-file missing-assessment flags, because a zero-size population cannot substantiate a per-file claim in EITHER direction. The consequence was stated plainly — the pass reported by every other validator in the gate does not include assessment-backing for any affected file.

## Candidate rule

Keep as a positive pattern, and generalise it: a validator arm whose population is empty must report "not evaluable" with the population size, never a pass and never a per-member verdict. A zero-size population supports no claim in either direction, and the gate's overall pass must be qualified by which arms did not run.
