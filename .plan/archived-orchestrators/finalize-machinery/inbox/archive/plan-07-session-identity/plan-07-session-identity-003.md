envelope_version=1
sender_type=plan
sender_id=plan-07-session-identity
epic=finalize-machinery
kind=candidate-lesson
created=2026-09-18T20:09:11Z

component=plan-marshall:plan-marshall
category=bug

# Transcript-less branch promised a logged decision without a decision-log write

The transcript-less branch in `plan-marshall/workflow/execution.md` promised a logged decision but carried no explicit `manage-logging decision` invocation. The dispatch-logging seam covers `execution-context` resolver calls, but this branch directly dispatches `Skill: plan-marshall:phase-6-finalize`.

## Evidence

- PR #1530 inline finding 2bb2b1 (coderabbit, inline, execution.md:590), resolution fixed via TASK-5.
- Follow-up commit on branch feature/plan-07-session-identity added the decision-log write before the finalize dispatch, naming the absent `session_id` and transcript-less target.
- Plan: plan-07-session-identity. Source signal: automated-review remediated finding (pr-comment fixed).

## Proposed rule

Every branch that promises a logged decision carries its own explicit `manage-logging decision` write naming the absent identity and target; do not rely on the dispatch-logging seam when the branch dispatches the skill directly.
