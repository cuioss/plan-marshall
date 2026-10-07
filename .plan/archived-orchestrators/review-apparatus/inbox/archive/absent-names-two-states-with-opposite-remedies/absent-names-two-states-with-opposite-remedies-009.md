envelope_version=1
sender_type=plan
sender_id=absent-names-two-states-with-opposite-remedies
epic=review-apparatus
kind=candidate-lesson
created=2026-08-08T20:44:48Z

# Candidate lesson: an `architecture` invocation inside the automatic-review dispatch was rejected by argparse

**Source records:** `[ERROR] … script_failure` work-log lines at `2026-08-08T19:32:15Z` (hash `429c71`) and `2026-08-08T19:02:51Z` (hash `0e3c73`).

## Record 1 — the argparse rejection, 19:32:15Z

```
notation=plan-marshall:manage-architecture:architecture
exit_code=2
failure_kind=argparse_rejection
architecture.py: error: unrecognized arguments: --plan-id absent-names-two-states-with-opposite-remedies
```

It fired **17 seconds after** `[SKILL] (plan-marshall:execution-context.automatic-review) Loaded …` — i.e. as one of the first actions inside the epic's own automated-review dispatch, at 19:31:58Z. The dispatch then ran for another 19 minutes and completed.

This is the **verb-scoped `--plan-id`** recurrence signature already named in `persona-plan-marshall-agent` § "Never invent script subcommands". `architecture.py` accepts `--plan-id` as a **top-level router flag**, before the subcommand — the same router-versus-argparse-table distinction that has bitten this project before. Passing it after the verb is rejected.

Two things make it worth the epic's attention rather than being a routine typo:

1. **It happened inside `automatic-review`.** The step that adjudicates whether a PR was reviewed lost a structured architecture query, silently, and proceeded. Whatever the query was for, the dispatch's later reasoning ran without it and nothing downstream recorded a degraded input.
2. **A documented recurrence signature still recurred inside a level-5 dispatch.** The prose guard exists and did not prevent it. The structural guard (`ARGUMENT_NAMING_*` under `quality-gate`) governs authored invocations in skill bodies, not invocations an agent composes at runtime.

## Record 2 — the build failure, 19:02:51Z

```
notation=plan-marshall:build-pyproject:pyproject_build
exit_code=1
failure_kind=script_internal_failure
command: … pyproject_build run --command-args module-tests
```

This one is ordinary and self-resolving: `module-tests` failed after the second fix commit and the next submission (`2f00ae18`, 19:03:17Z → 19:10:39Z) succeeded. Recorded for completeness, not proposed as a lesson. Note that the run carried two build failures overall — the earlier one at 18:49:56Z (`52e1da80`) also reported `job_status=failure` through the build server without producing a `script_failure` marker.

## Observation for the orchestrator, not a recomputed count

The dispatcher forwarded `signal_script_failure_clusters_count: 1`. Reading the records behind that signal, **two distinct failing notations** pre-date this envelope (`manage-architecture:architecture` and `build-pyproject:pyproject_build`), and a third and fourth `script_failure` marker were emitted by this very envelope at 20:38:16Z and 20:38:45Z (both `manage-findings`, both argparse rejections — a `qgate list` missing the required `--phase`, and an invented `--fields` flag; the `--fields` one is a fresh instance of the same "never invent a flag" class).

The mismatch between one forwarded cluster and two pre-existing notations is passed on as an observation for the orchestrator to judge. This message does not restate or correct the count — the gate's arithmetic is not this plan's to recompute.

## Why it is routed here

Record 1 landed inside the epic's own `automatic-review` dispatch. The count-versus-records mismatch concerns the finalize signal gate that decides whether lessons-capture runs at all, which is adjacent enough to hand over rather than drop.
