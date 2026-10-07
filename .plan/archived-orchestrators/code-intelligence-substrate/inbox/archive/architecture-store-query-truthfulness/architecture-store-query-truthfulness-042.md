envelope_version=1
sender_type=plan
sender_id=architecture-store-query-truthfulness
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-09-15T07:56:18Z

component=plan-marshall:execute-task
category=bug

# bool(None) collapsed "not measured" into "measured zero" in the payload

Source: PR #1489 CodeRabbit inline finding 3ffbd8 (resolution=fixed, TASK-034).

When the identifiers file is empty, assert_identifiers_in_log() does not read the log
and returns log_nodeid_count=None. Line 366 rendered
`'log_enumerates_nodeids': bool(result.log_nodeid_count)`, so the SUCCESSFUL TOON
payload claimed the log enumerated no nodeids while log_nodeid_count was null. That
contradicts the DiffResult docstring's own statement that None and 0 are different
facts.

## Solution

Emit null when the count is unmeasured; emit false only after a measured zero.

The general rule: `bool(x)` over an Optional is a silent tri-state-to-binary collapse,
and it is most damaging on the SUCCESS path, where nothing prompts a reader to doubt
the value. A module whose purpose is distinguishing "could not look" from "looked and
found nothing" must not use a truthiness cast at its own output boundary.

## Impact

Found by an external reviewer in a plan whose entire subject was reporting only what the
data supports.
