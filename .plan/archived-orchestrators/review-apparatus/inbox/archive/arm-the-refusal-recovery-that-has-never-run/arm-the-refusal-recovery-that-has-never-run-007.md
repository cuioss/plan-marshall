envelope_version=1
sender_type=plan
sender_id=arm-the-refusal-recovery-that-has-never-run
epic=review-apparatus
kind=candidate-lesson
created=2026-09-07T14:29:28Z

# Always-on skip gate fails every macOS verify via the /proc test

component: plan-marshall:build-server
category: bug
confidence: high

## Context

Live and blocking on `main`. Filed in this plan's Q-Gate store as `c27d28`, resolution **pending** — deliberately left unfixed rather than silently patched.

Whole-tree verify reports `25050 passed, 12 skipped` and then FAILS with:

```
ERROR: 1 test(s) skipped outside the 11-entry residual skippable set
```

naming `test/plan-marshall/build-server/test_manage_build_server.py::test_read_process_argv_reads_this_process_from_proc`, reason `no /proc on this platform`. That is a Linux-only test skipping on macOS, and its nodeid is not in `_SKIP_EXCEPTIONS` (which enumerates pyright-langserver absent-dependency entries only).

Observed while validating PR #1441, on a branch based on `c0e945d6a`, on top of this plan's own merge `29a3dad1c`.

## Root cause

The gate's own docstring records that it was recently changed from opt-in to **always on** ("it previously required an opt-in environment flag, and no producer ever set it"). Arming it exposed a platform-conditional skip that had never been measured, because nothing had ever evaluated the gate.

CI is unaffected — it runs on Linux, where `/proc` exists and the test does not skip — so the failure is invisible to CI and blocks only local whole-tree validation. Consequence: **no plan can pass local whole-tree verify on macOS on current `main`, regardless of its own changes.**

## Proposed action

The gate itself names the remedy: add the nodeid to `_SKIP_EXCEPTIONS` with its class and reason. This was deliberately NOT done in the originating plan because the docstring states only two skip classes are legitimate, and a platform-conditional skip may warrant a third — that is a contract decision about what the gate is for, not a mechanical entry.

So the action is: decide whether platform-conditional skips are a legitimate third class; if yes, add the class and this entry; if no, make the test unconditional-by-construction on non-Linux (skip at collection via a marker the gate recognises, or provide the `/proc` read through a platform shim).

## Evidence

- qgate finding `c27d28` (severity error, component `plan-marshall:build-server`, file `test/conftest.py`), resolution `pending` at the time of this retrospective.
- observed on PR #1441's branch, based on `c0e945d6a`, atop merge `29a3dad1c`.
- routing note: carried into the epic inbox because this plan archives shortly and a pending finding in an archived plan's store needs an explicit route out.
