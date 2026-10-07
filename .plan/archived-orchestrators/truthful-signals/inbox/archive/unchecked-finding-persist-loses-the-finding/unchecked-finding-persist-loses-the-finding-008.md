envelope_version=1
sender_type=plan
sender_id=unchecked-finding-persist-loses-the-finding
epic=truthful-signals
kind=candidate-lesson
created=2026-07-28T16:30:08Z

component=plan-marshall:tools-integration-ci
category=bug
created=2026-07-28

# Dispatched leaves get a truncated PATH, so gh/ci failures misread as auth problems

Dispatched leaves receive a truncated `PATH` that is missing `/opt/homebrew/bin`. When a
`gh`/`ci` call resolves to nothing (or a wrong binary) under that truncated PATH, the
resulting error reads as "Not authenticated" — a misleading signal that looks like an
auth/credential problem when the actual root cause is PATH resolution.

## Solution

When a `gh`/`ci` call inside a dispatched envelope fails with an auth-shaped error,
verify the resolved binary path first (e.g. `which gh`) before treating it as a
credentials issue. Consider hardening the CI abstraction layer to resolve the binary via
an explicit known-install-location fallback rather than relying on inherited PATH.

## Impact

Every dispatched-leaf CI/gh call is at risk of this misdiagnosis; wasted troubleshooting
time chasing an auth problem that is actually an environment/PATH problem.
