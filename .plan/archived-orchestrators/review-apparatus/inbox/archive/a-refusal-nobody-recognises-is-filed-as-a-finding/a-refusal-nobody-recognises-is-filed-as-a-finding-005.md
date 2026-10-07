envelope_version=1
sender_type=plan
sender_id=a-refusal-nobody-recognises-is-filed-as-a-finding
epic=review-apparatus
kind=candidate-lesson
created=2026-08-25T07:22:48Z

component=plan-marshall:plan-retrospective
category=bug
title=Step 5b documents an executor notation that does not exist, so the orchestrated branch cannot fire as written

# plan-retrospective's orchestrated recording path names a script notation the executor rejects

## Context

`plan-retrospective/SKILL.md` Step 5b prescribes, for the `orchestrated: true` branch:

```
python3 .plan/execute-script.py plan-marshall:marshall-orchestrator:orchestrator inbox write ...
```

Invoked verbatim during this retrospective, the executor returned:

```
SCRIPT_ERROR	plan-marshall:marshall-orchestrator:orchestrator	1	Unknown notation
```

The live notation is `plan-marshall:plan-orchestrator:orchestrator`. The skill *name* `plan-marshall:marshall-orchestrator` exists; the script notation does not.

## Root cause

The skill was renamed (or its script re-homed) and the consuming workflow doc's canonical invocation was not updated. Nothing catches it: the notation appears in prose inside a fenced block, and no test exercises the orchestrated branch of Step 5b.

## Proposed action

Correct the notation in Step 5b. More durably: the same `manage-invocation-invalid` plugin-doctor rule that guards `manage-*` canonical blocks should also validate `orchestrator` notations, or the executor's `SCRIPTS` mapping should be the checked source for every 3-part notation appearing in a marketplace fenced block.

## Evidence

- Observed first-hand during this run: the documented invocation failed, the corrected one succeeded
- `plan-retrospective/SKILL.md` Step 5b
- Every orchestrated plan's retrospective would fail at its recording step; every non-orchestrated one takes the other branch and never touches this line, which is why it has survived
