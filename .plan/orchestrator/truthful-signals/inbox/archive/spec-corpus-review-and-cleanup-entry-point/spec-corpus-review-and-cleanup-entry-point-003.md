envelope_version=1
sender_type=plan
sender_id=spec-corpus-review-and-cleanup-entry-point
epic=truthful-signals
kind=candidate-lesson
created=2026-08-22T16:17:00Z

component=plan-marshall:manage-change-ledger
category=bug
confidence=high
source_plan=spec-corpus-review-and-cleanup-entry-point
source_aspects=plan_efficiency,log_analysis

# Change-ledger recorded zero build rows while 144 build invocations ran

## Context

`analyze-logs` reports the build-time oracle for this plan as:

```
build_time:
  total_build_seconds: 0.0
  build_count: 0
  suspect_count: 0
  pass: 0
  error: 0
  timeout: 0
  killed: 0
```

The *same fragment*, roughly thirty lines further down, reports from a different channel:

```
ranked[10]{notation,calls,cumulative_ms,...}:
  "plan-marshall:build-pyproject:pyproject_build",144,16054170.0,...
```

144 build invocations totalling 16,054,170 ms — four hours twenty-seven minutes, **62.4% of all script wall time this plan consumed**. The plan directory additionally contains 96 concrete build-result log files under `build-results/`, several of them 5 MB. The builds unambiguously ran. The ledger did not observe a single one.

## Root cause

Not established here. The candidates are that the change-ledger write is not reached on the routed/daemon build path (this plan's builds resolved as `mechanism=daemon`, visible in a `[BUILD-SERVER] resolved build (requested=auto, resolved=routed...)` line in the script log), or that the ledger is written to a location the retrospective's live-mode reader does not resolve after the worktree is removed. Both are checkable; neither is assumed.

## Why this matters beyond one wrong number

`plan-efficiency.md` explicitly instructs its consumer that `build_count: 0` means build time is **UNAVAILABLE, not zero** — "absent is not zero" — and this retrospective followed that instruction, reporting `total_build_seconds: unavailable`. So the documented contract held and no false figure was published. But the contract only protects a reader who knows to distinguish the two. Because the ledger is declared the build-time ORACLE and the aspect is forbidden from re-deriving build time from a log, the single largest cost component of this plan — 62% of its script wall time — is invisible to the one aspect whose job is grading cost, while a second channel in the same document holds the answer.

## Proposed action

1. Determine whether the ledger write is skipped on the routed/daemon build path or whether the ledger is written somewhere the retrospective reader does not resolve post-worktree-removal.
2. Fix the write (or the resolution), so `build_count` reflects the population that actually ran.
3. Independently of that fix, have `analyze-logs` cross-check its own two channels: when `build_count == 0` but the cost rollup ranks a build notation with a non-zero call count, emit a finding naming both figures. A document that already contains its own contradiction should say so rather than leaving it to a reader to notice.

## Evidence

- aspect: log_analysis — `build_time.build_count: 0` and `build_time.total_build_seconds: 0.0`
- aspect: log_analysis — `script_cost_rollup.ranked[0]` = `pyproject_build, 144 calls, 16054170.0 ms, share_pct 62.357`
- aspect: plan_efficiency — `build_time_provenance.total_build_seconds: unavailable` with the contradiction recorded as its stated reason
- corroborating: 96 build-result log files present in the plan directory under `build-results/default/` and `build-results/plan-marshall/`
