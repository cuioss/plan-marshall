envelope_version=1
sender_type=plan
sender_id=unchecked-finding-persist-loses-the-finding
epic=truthful-signals
kind=candidate-lesson
created=2026-07-28T16:29:15Z

component=plan-marshall:persona-module-tester
category=anti-pattern
created=2026-07-28

# A test suite that stubs the function under test can never catch its defect

All six existing unit tests for `scope_creep_check` stubbed `_emit_finding` to return
`True` unconditionally. The real function's vacuous `returncode == 0` guard and its
malformed argv were therefore never executed by any test — the defect was untestable by
construction, not merely untested.

## Solution

When a test suite exists to cover a function, at least one test must exercise the real
implementation end-to-end (or through the lowest-level real subprocess/IO boundary) —
never mock every call site of the function the suite claims to verify. A stub that
always returns the "success" value is a red flag: check whether any test still calls the
real code path.

## Impact

Green test suites over a fully-stubbed dependency are a false-clean signal — coverage
percentage looks fine while the real code path is provably never executed.
