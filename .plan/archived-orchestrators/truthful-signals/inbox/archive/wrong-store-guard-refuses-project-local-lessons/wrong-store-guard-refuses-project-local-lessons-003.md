envelope_version=1
sender_type=plan
sender_id=wrong-store-guard-refuses-project-local-lessons
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T11:56:42Z

component=plan-marshall:manage-lessons
category=anti-pattern
created=2026-07-29

# Vacuous guard introduced BY a fix, and a test that pinned the old defect

`cmd_from_error` coerces a missing/non-string `component` value to the literal string `'unknown'`. This plan added a new `isinstance(component, str)` guard on the store-ownership check — but the pre-existing coercion runs first, so the new guard was UNREACHABLE from the exact input path it was written to defend. This is the vacuous-guard archetype recurring (now n+1 in this project's history), and — as before — it was introduced INSIDE the fix meant to correct a different, already-identified false-signal defect, not by an unrelated later change.

The plan's own malformed-component test also passed for the wrong reason: it passed `'bad/component'`, which happens to already be a `str`, so the test never exercised the coercion path it was meant to guard against. This is the test-pins-the-defect archetype: a test that looks like it covers the fix but actually only exercises the branch where the old buggy behavior was already absent.

CodeRabbit caught both post-push, not the plan's own self-review or its authored tests.

## Impact

Every fix that adds a new guard (isinstance check, prefix check, non-null check) MUST verify the guard is reachable from the exact failure-mode input it targets — not just from a superficially similar valid input. A malformed-input test that happens to satisfy every upstream type-coercion silently proves nothing. Self-review's existing "flag unreachable guards" capability (landed via #1042) should be checked against this concrete recurrence to confirm it would have caught this shape.
