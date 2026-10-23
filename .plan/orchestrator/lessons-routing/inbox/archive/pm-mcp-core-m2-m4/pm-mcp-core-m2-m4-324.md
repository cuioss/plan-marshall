envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T09:56:33Z

component=plan-marshall:phase-6-finalize
category=improvement
source=dispatcher-observed fact (4); work log 2026-10-18T08:05:16Z to 08:44:36Z

# A two-line inline Sonar fix re-fired both full reviews and the whole wait region

## Observation

After verification-feedback applied a two-line inline Sonar fix (about 08:05), finalize re-ran the full functional review and code review, then pre-push-quality-gate, ci-verify, sonar-roundtrip and automatic-review: about 40 minutes for a trivial delta.

## Rule

Scale the re-review on a loop-back to the delta. A delta confined to lines a static analyser flagged, with no behaviour change, should take a delta review (or the quality gate plus a Sonar re-check), not two full reviews and a full bot wait region. This is the reverse of the under-load failure in the delta-round candidate: narrow the files reviewed, never the rules applied.
