envelope_version=1
sender_type=plan
sender_id=merge-queue-enqueue-does-not-take
epic=truthful-signals
kind=candidate-lesson
created=2026-08-03T20:58:30Z

component=plan-marshall:build-pyproject
category=bug
title=parse reports SUCCESS with tests_failed 0 on any log lacking a pytest summary
confidence=high
source_plan=merge-queue-enqueue-does-not-take
source_pr=1087
routed_from=review-apparatus

# parse reports SUCCESS with tests_failed 0 on any log lacking a pytest summary

## Context

`pyproject_build parse --log X` is the sanctioned way to read a build's real verdict, because the build wrapper exits 0 even on failure. The standing project rule is "read the TOON `status`, not the exit code." That rule is only sound if `parse` can tell "no failures" from "no test data". It cannot.

## Root cause

`parse` derives its verdict purely from pytest summary lines present in the log. When the log contains no pytest summary — a mypy/quality-gate log, a wrapper TOON, a daemon job-log — it does not report "no test data". It reports a clean pass:

```
$ pyproject_build parse --log build-results/default/python-2026-08-03-151833.log --format json
{"status": "success",
 "data": {"build_status": "SUCCESS", "issues": [], "summary": {"total_issues": 0, ...}},
 "metrics": {"tests_run": 0, "tests_failed": 0}}
```

That file is a **mypy log**. Same invocation against the corresponding inner pytest log for the same plan:

```
{"status": "error",
 "data": {"build_status": "FAILURE", ... 7 test_failure issues ...},
 "metrics": {"tests_run": 14939, "tests_failed": 7}}
```

`tests_run: 0` is the only tell, and it is a *metric*, not a status. Every consumer branching on `status`, on `build_status`, or on `tests_failed == 0` gets a confident green from a log that contains no tests at all. In TOON (the default format) the non-structured modes render as a bare `status: success` with the counts not surfaced at all, so the tell is invisible on the default path.

This plan hit the live version of it: the operator reported `parse` returning `total_failures 0` when pointed at the marshalld **daemon job-log** (a wrapper TOON) instead of the inner pytest log, on a run that had 3 real failures. The plan's own workaround is visible in its logs — the 19:35:19Z entry deliberately says "**inner** pytest log reports 14938 passed 2 skipped 0 failed", i.e. the operator learned to bypass the hazard by hand.

Note the compounding: qgate finding `7a535a` recorded its own verification as "module-tests plan-marshall green with **log-layer parse reporting total_failures 0**". A green derived from `parse` is only as trustworthy as the log it was aimed at.

## Proposed action

1. Add an explicit third state. `parse` MUST distinguish `no_test_data` from `pass`. Concretely: when no pytest summary line is found, return `status: warning` (or `build_status: NO_TEST_DATA`) rather than `SUCCESS`, and name the reason.
2. Surface `tests_run` on the default TOON path, not only under `--format json --mode structured`.
3. Refuse a wrapper/daemon TOON outright — if the log's first non-blank line parses as TOON, that is not a build log; error with the inner-log path if it can be derived.

## Evidence

- Verified side-by-side on this plan's own artifacts: `build-results/default/python-2026-08-03-151833.log` (mypy) → SUCCESS/0; `build-results/plan-marshall/python-2026-08-03-154843.log` (pytest) → FAILURE/7.
- work.log 19:35:19Z — the "inner pytest log" phrasing as a hand-applied workaround.
- Standing project rule "Build wrapper exit code misleading — read TOON status" is undermined by this.

## Dedup context for the orchestrator

Directly extends the standing `Build wrapper exit code misleading` / `Never trust a routed build's outer status` pair — but those say *read the TOON status*, and this shows the TOON status itself lies when aimed at the wrong log. Worth folding INTO those lessons rather than filing beside them. Gate 1 dedup NOT run (`orchestrated: true`).
