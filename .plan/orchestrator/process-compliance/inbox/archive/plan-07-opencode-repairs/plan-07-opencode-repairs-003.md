envelope_version=1
sender_type=plan
sender_id=plan-07-opencode-repairs
epic=process-compliance
kind=candidate-lesson
created=2026-09-21T01:24:05Z

id=pending-orchestrator-pickup
component=plan-marshall:phase-3-outline
category=improvement
created=2026-09-21

# Q-Gate assessment coverage missing for deliverable 1 (fixed in-run)

When phase-3-outline filed deliverable 1 (Opencode no-session degrade visibility) listing affected files marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/opencode_runtime.py and platform_runtime.py, zero component assessments backed it. Q-Gate finding 8b36da required CERTAIN_INCLUDE assessments or a recorded reason.

## Solution

Filed CERTAIN_INCLUDE assessments for opencode_runtime and platform_runtime in-run (resolution fixed 2026-09-20T20:42:53Z). Pattern repeated for deliverables 2 and 3 in the same run.

## Impact

Outline lanes that list affected files without filing assessments will trip the same gate. File assessments at outline time or record why the lane proceeds without them.

## Source

qgate finding 8b36da phase 3-outline, resolution fixed. Candidate for orchestrator-side classification (global vs epic).
