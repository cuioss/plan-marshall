envelope_version=1
sender_type=plan
sender_id=plan-07-session-identity
epic=finalize-machinery
kind=candidate-lesson
created=2026-09-18T20:09:19Z

component=plan-marshall:plan-marshall
category=bug

# Finalize dispatch template requires session_id on the transcript-less path

The transcript-less branch requires finalize without `session_id`, but the only finalize dispatch template always included `session_id: {resolved session id from resolver above}`. The transcript-less branch has no resolved value, so it cannot implement the optional-session contract with that template.

## Evidence

- PR #1530 inline finding d1bd5d (coderabbit, inline, execution.md:591), resolution fixed via TASK-5.
- Follow-up commit on branch feature/plan-07-session-identity added a separate dispatch form that omits `session_id` and retained the current form for resolved session IDs.
- Plan: plan-07-session-identity. Source signal: automated-review remediated finding (pr-comment fixed).

## Proposed rule

When an input contract demotes a field from required to optional, ship both dispatch forms (with-field and without-field) and keep the with-field form for the resolved path; a single always-present template cannot implement the optional contract.
