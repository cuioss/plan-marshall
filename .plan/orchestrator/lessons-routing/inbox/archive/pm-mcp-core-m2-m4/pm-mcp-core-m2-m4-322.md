envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T09:56:33Z

component=plan-marshall:phase-6-finalize
category=bug
source=dispatcher-observed fact (2); qgate 6-finalize c7150b; work log 2026-10-17T23:27:16Z to 2026-10-18T06:23:18Z

# A delta code-review round loaded 6 of 22 rule-source skills and closed over a real lost-data defect

## Observation

Finalize needed four code-review rounds. The author of the third (delta) round loaded only 6 of the 22 rule-source skills the review resolves and closed the round. A later full round found c7150b: a move into a store that already holds an integrity key overwrites it or deletes it in the clean-up, which is a real lost-data defect.

## Rule

A delta review round must load the same rule-source set as a full round, because the delta narrows the files reviewed, not the rules applied. The code-review workflow should verify the loaded-skill count against the resolved set before it accepts a close verdict (fail closed on under-load), and the verifier should check the author's loaded set.
