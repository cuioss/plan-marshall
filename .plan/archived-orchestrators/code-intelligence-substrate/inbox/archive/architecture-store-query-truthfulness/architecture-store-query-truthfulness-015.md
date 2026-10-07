envelope_version=1
sender_type=plan
sender_id=architecture-store-query-truthfulness
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-09-15T07:51:38Z

component=plan-marshall:phase-3-outline
category=anti-pattern

# A closure claim over an enumeration in a solution outline is a defect the outline itself commits

Source: Q-Gate finding 0bbdb1 (3-outline, resolution=taken_into_account).

D5's Design notes asserted the spanned skills were "every one script-deterministic
(mode: script-executor)" over an eight-member enumeration. Re-derived at HEAD over the
complete skill population (files_scanned 157, truncated false, elided[] empty,
unreadable[] empty): 40 skills declare mode: script-executor and two of D5's eight are
NOT among them — plan-marshall/SKILL.md declares mode: workflow, tools-script-executor/
SKILL.md declares mode: knowledge.

## Solution

The design model was sound (the files D5 actually edits under those two skills are
deterministic scripts); only the cited evidence was false. Before writing "every one of
these is X", re-read X's declaring source per member. This is the exact defect class the
plan itself existed to close, committed inside its own planning artifact.

## Impact

Not acted on, because the outline is plan-internal and its only consumer (phase-4-plan)
had already run. The recurrence is the point: a closure claim is cheap to write and
expensive to falsify after the fact.
