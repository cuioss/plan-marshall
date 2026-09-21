envelope_version=1
sender_type=plan
sender_id=unchecked-finding-persist-loses-the-finding
epic=truthful-signals
kind=candidate-lesson
created=2026-07-28T16:29:57Z

component=plan-marshall:build-pyproject
category=improvement
created=2026-07-28

# The whole-tree test-compile gate catches errors mypy-over-test-only cannot see

The whole-tree test-compile gate caught two `no-any-return` mypy errors during this
plan's finalize that a mypy pass scoped to test files only (`mypy-over-test`) would not
have surfaced, because the offending return-type mismatch lived in production code
reached only through the test's call graph, not in the test file itself.

## Solution

Keep the whole-tree test-compile gate as a required pre-push step rather than narrowing
it to changed-files-only or test-files-only scope; the value comes specifically from
compiling the full call graph a test reaches, not just the test module.

## Impact

Confirms the whole-tree gate's coverage value over a narrower "just the changed test
file" scoping — narrowing it would silently drop this defect class.
