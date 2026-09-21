envelope_version=1
sender_type=plan
sender_id=plan-145-publish-the-missing-parser-seams
epic=test-quality
kind=candidate-lesson
created=2026-09-04T14:48:29Z

# The description-drift check reads a haystack that excludes risks_and_mitigations, so an accurate task description is flagged

**Signal**: Q-Gate finding (`4-plan`, hash `6940f1`, severity `warning`, resolution `accepted`)
**Component**: `plan-marshall:phase-4-plan`
**Plan**: `plan-145-publish-the-missing-parser-seams` (PR #1395, merged `8d8c17bd`)

## What was observed

TASK-1's description named the structural token `register=False`. The drift check reported it as ungrounded, because the token appears in the deliverable's `risks_and_mitigations` section — which the checked haystack (Title / Metadata / Intent gloss / Profiles / Affected files / Change per file / Verification / Success Criteria) excludes.

The token *is* genuinely specified by the solution outline, in the risks row "Probe with `register=False`, which `parse_ns` documents as the correct choice when only the namespace (or its absence) is wanted." The finding was operator-accepted: removing an accurate, load-bearing implementation constraint from a task description to satisfy the haystack boundary would have made the task worse.

## Why it is candidate-lesson material

The check flagged a **haystack boundary**, not an ungrounded claim, and it presented the two identically. Acting on the flag as stated would have degraded the artifact. This is a false-positive shape whose only remedy on the day was an operator override — a cost the check imposes on every plan whose deliverable puts an implementation constraint in a risks row, which is exactly where implementation constraints belong.

## Proposed rule (for orchestrator judgement)

Either include `risks_and_mitigations` in the drift haystack, or have the check report which sections it searched so a reader can tell "not in the outline" from "not in the part I read". A grounding check that cannot say what it looked at is indistinguishable from one that looked everywhere.

## Related already-active lessons

- `2026-09-03-09-001` — verification-only guard's `affected_files`-empty check misfires on survey-scope deliverables
