envelope_version=1
sender_type=plan
sender_id=plan-12-tool-triage
epic=process-compliance
kind=finding
created=2026-09-27T14:24:05Z

# `session_ids` never captured for a plan created mid-session

## Observed

phase-1-init Step 8a read `manage-status metadata --get --field session_ids` right after
`manage-status create` and got `status: not_found` (available fields: `use_worktree`,
`request_aspect`). The step emitted its `[WARNING]` and continued, as documented.

Step 8a and the plan-marshall SKILL § Session ID Resolver state the platform-runtime `SessionStart`
hook "normally APPENDS the session id ... at plan-init time". A `SessionStart` hook fires when the
session starts — before this plan existed — so for the normal `/plan-marshall task=...` flow (plan
created inside a running session) there is no plan to append to at hook time. The "normally" case
appears to be the exception, and every such plan defers to phase-6-finalize's late capture before a
hard-block abort.

## Suggested fix

Have phase-1-init Step 3a (or `manage-status create`) call the platform-runtime `session capture`
operation explicitly once `status.json` exists, and keep Step 8a as the verification — so the
documented "normal" path is actually the one that runs.
