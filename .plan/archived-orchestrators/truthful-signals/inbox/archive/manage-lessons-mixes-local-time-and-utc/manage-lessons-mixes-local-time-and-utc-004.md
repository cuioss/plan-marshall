envelope_version=1
sender_type=plan
sender_id=manage-lessons-mixes-local-time-and-utc
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T16:38:56Z

component=plan-marshall:build-pyproject
category=bug
created=2026-07-29

# Build wrapper's outer `duration_seconds: 0` can hide a real multi-minute timeout

During this plan's finalize, a `module-tests` build call's OUTER envelope reported `duration_seconds: 0`, which reads as an instantaneous / trivial run. The INNER log for the same call correctly recorded `status: timeout, duration_seconds: 330` — the run had genuinely consumed 5.5 minutes before timing out. The outer envelope's confident-looking `0` actively hid the real signal a caller would need to diagnose the timeout.

## Solution

The outer envelope should compute and propagate real elapsed wall-clock time on every exit path, including timeout and error exits, rather than defaulting the field to `0` when the happy-path timer never completes. Until fixed at the tool layer, any consumer that sees `duration_seconds: 0` alongside a command that is not trivially fast MUST treat it as suspicious and cross-check the inner log rather than trusting the outer number.

## Impact

This is the same "confident outer signal hides the real one" pattern already tracked by the truthful-signals epic (build wrapper exit-code-misleading, routed-build outer-status). A build-server / wrapper hardening pass should add an assertion that outer `duration_seconds` is monotonically consistent with (or absent when unavailable, never a bare `0`) the inner log's own duration.
