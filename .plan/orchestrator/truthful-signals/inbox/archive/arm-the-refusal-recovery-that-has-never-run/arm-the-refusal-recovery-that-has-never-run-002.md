envelope_version=1
sender_type=plan
sender_id=arm-the-refusal-recovery-that-has-never-run
epic=truthful-signals
kind=finding
created=2026-09-07T14:33:57Z

# Always-on skip gate fails every macOS `verify`: the `/proc` skip is not in `_SKIP_EXCEPTIONS`

**Origin**: `c27d28`, filed during `arm-the-refusal-recovery-that-has-never-run` (epic `review-apparatus`, shipped as #1433 / `29a3dad1c`). **Pre-existing on `main`, not introduced by that plan** — observed while validating fix PR #1441, whose branch sat on `c0e945d6a`, itself on top of that merge. Routed here rather than to `review-apparatus` because it is a test-infrastructure defect, not a PR/review-apparatus one.

## What happens

A whole-tree `verify` on macOS reports a green test run and then fails the run:

```
25050 passed, 12 skipped
ERROR: 1 test(s) skipped outside the 11-entry residual skippable set. A green run must not
quietly cover less than it claims: either fix the condition, or add the nodeid to
_SKIP_EXCEPTIONS in test/conftest.py with its class and reason.
  test/plan-marshall/build-server/test_manage_build_server.py::test_read_process_argv_reads_this_process_from_proc
      reason: Skipped: no /proc on this platform
```

Reproduced again on `05ca6fe7b` at `module-tests plan-marshall` scope: *20586 passed, 9 skipped*, same single gate failure, same nodeid.

## Why it is there

The gate's own docstring records that it was recently changed from opt-in to **always on** — *"it previously required an opt-in environment flag, and no producer ever set it."* Arming it exposed a platform skip that had never been measured. `_SKIP_EXCEPTIONS` enumerates pyright-langserver absent-dependency entries (11 of them) and does not carry this nodeid.

The skipping test is Linux-only: it reads `/proc` to recover the current process's argv.

## Consequence

**No plan can pass a local whole-tree `verify` on macOS on current `main`, regardless of what it changed.** CI is unaffected — it runs on Linux, where `/proc` exists and the test does not skip — so the breakage is invisible to CI and blocks only local validation. That asymmetry is the interesting part: a gate whose whole purpose is *"a green run must not quietly cover less than it claims"* is itself only enforced on the platform where it never fires.

## Why it was not fixed in place

The remedy the gate names — add the nodeid to `_SKIP_EXCEPTIONS` with its class and reason — was deliberately **not** applied. The docstring states that only two skip classes are legitimate; a platform-conditional skip would be a third. Whether to admit that class is a contract decision about what the gate asserts, not a mechanical append, and appending silently would have weakened the gate to unblock a plan that did not own it.

## The shape of the decision

Three routes, and the choice is the deliverable:

1. **Admit a third class** — platform-conditional skips — and document what it may and may not cover. Widens the gate's tolerance permanently.
2. **Make the test platform-independent** so it never skips: read argv through a portable path rather than `/proc`, and the exception is unnecessary.
3. **Make the gate platform-aware** — a skip whose reason names an absent platform facility is measured against a per-platform expected set rather than one global list, so the same run is graded differently on Linux and macOS without loosening either.

Route 2 removes the exception rather than granting one and is the only route that leaves the gate's assertion unweakened; route 3 is the general fix if more platform skips exist (nobody has enumerated them — that enumeration is itself part of the work).

## Files

- `test/conftest.py` — `_SKIP_EXCEPTIONS`, `pytest_sessionfinish`
- `test/plan-marshall/build-server/test_manage_build_server.py::test_read_process_argv_reads_this_process_from_proc`
