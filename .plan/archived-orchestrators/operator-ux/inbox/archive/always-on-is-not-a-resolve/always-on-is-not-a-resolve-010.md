envelope_version=1
sender_type=plan
sender_id=always-on-is-not-a-resolve
epic=operator-ux
kind=candidate-lesson
created=2026-09-03T19:27:16Z

component=plan-marshall:manage-status
category=anti-pattern
created=2026-09-03

# `manage-status read` invoked with an undeclared flag, from two different callers

The identical rejection fired twice in plan `always-on-is-not-a-resolve`, from
two different dispatched envelopes, roughly 47 minutes apart:

```text
[18:22:40] (inside plan-marshall:automatic-review)
  script_failure notation=plan-marshall:manage-status:manage-status exit_code=2
  failure_kind=argparse_rejection
  detail=Use a declared flag for `plan-marshall:manage-status:manage-status read`: ['plan-id', 'store']

[19:09:44] (inside project:finalize-step-review-retrospective)
  ...identical...
```

`manage-status read` declares exactly two flags — `--plan-id` and `--store` —
and each caller passed something outside that set. Two unrelated callers making
the same mistake against the same verb points at the invocation surface rather
than at either caller.

## Solution

`manage-status read` accepts only `--plan-id` and `--store`. Any narrowing a
caller wants (a phase, a step, a metadata key) is done by reading the returned
payload, not by adding a filter flag to the call.

Callers that want a phase- or step-scoped answer should use the verb that
declares that scope rather than decorating `read`.

## Impact

Both call sites are in the finalize band, so the rejection is invisible in the
phase narrative — the envelope continued and its step still reported
`outcome=done`. Worth checking whether the two calling workflow docs show a
`manage-status read` form carrying a flag the verb does not declare; if so, the
doc is the propagation vector and both copies need the same correction.
