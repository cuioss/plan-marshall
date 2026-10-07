envelope_version=1
sender_type=plan
sender_id=architecture-store-query-truthfulness
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-09-15T07:56:23Z

component=plan-marshall:manage-status
category=bug

# `.get('metadata', {})` does not defend against an explicit `metadata: null`

Source: PR #1489 CodeRabbit inline finding e9d1db (resolution=fixed, TASK-035).

The dict default on `.get('metadata', {})` applies only when the KEY IS ABSENT, so an
explicit `metadata: null` flows straight through and `_status_query.py:334` raises
AttributeError (line 342's `list(metadata.keys())` likewise). This is the
`any_checkout --get` read the PR itself authored, over an operator-editable status.json,
so the guard belongs at that boundary.

## Solution

Route through the existing normalize_metadata helper in _status_core.py rather than
adding a second normalization shape, and check the module's other producers against that
same seam.

The reusable rule: a `.get(key, default)` is a MISSING-key guard, never a
wrong-TYPE guard. Wherever the document is operator-editable, the two failure modes are
both reachable and only one is covered.

## Impact

A hand-edited status.json crashes a read verb the same plan had just widened.
