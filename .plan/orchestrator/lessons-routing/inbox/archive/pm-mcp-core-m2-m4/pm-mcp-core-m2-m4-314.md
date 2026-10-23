envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T09:56:30Z

component=plan-marshall:phase-6-finalize
category=improvement
source=qgate 6-finalize 61bc1a (code-review-state verdict_refused, warning)

# Code-review verifier refused an over-graded blocking finding

## Observation

In the third code-review round the verifier refused the author's verdict: F1 (a42796) was real and reachable but graded too high. The spec puts a store change in the move, the entries and the key are stranded rather than destroyed, and the race claim was unsound because `recorded()` is read under the lock. Because F1 was blocking, it also barred close. The round cost an extra verifier pass before closing with may_close=true.

## Rule

A code-review author grading a finding blocking must state the consequence class it proved (destroys data / strands data / race) and the evidence for the trigger condition. A race claim must name the unlocked read it depends on. Unsupported race or loss claims inflate severity and trigger verdict refusals.
