envelope_version=1
sender_type=plan
sender_id=plan-truth-139
epic=truthful-signals
kind=candidate-lesson
created=2026-09-13T14:20:22Z

# Temp residue poisons the learned build durations and silently re-tiers canonicals

component: plan-marshall:manage-architecture
category: improvement
confidence: high
suggested_epic: truthful-signals
source_plan: plan-truth-139
source_pr: 1479

## Context

This run hit three build timeouts whose established cause was accumulated test
residue, not a slow build.

The measured instance: orchestrator-tier `module-tests` job `a2103840` returned
`status: timeout` at 873s with `adaptive timeout_used_seconds=873`, while earlier
runs the same day had finished in 272-375s. Before re-running, the cause was
established rather than assumed: `run_config cleanup --target temp` reported 52,704
files / 450MB of test residue. Cleared, the same build completed green in 529s with
21,173 tests. A second measurement at worktree removal counted 233,856 scratch
entries (10,659 measured, 60s budget).

The run recorded this and explicitly did NOT rewrite it: "Recorded because the
adaptive timeout was sized against the fast runs and the residue is what crossed
it" (decision `467404`).

## Root cause

The adaptive timeout learns from observed durations, and it learned from the
poisoned ones. The consequence is not a slower build — it is a *routing* change:
canonical commands whose learned `bash_timeout_seconds` crosses the 600s leaf Bash
ceiling resolve to `execution_tier: orchestrator`, which moves them out of the
leaf's runnable slice entirely.

By the end of the run, `quality-gate` live-resolved to 968s and `module-tests` to
1473s — both orchestrator tier. Gates that had run inline earlier in the same plan
(TASK-8 ran `quality-gate` at 360s and `module-tests` at 501s, both `per_task`) were
no longer runnable by the leaf. The run yielded to the orchestrator nine separate
times on this basis, each yield a dispatch boundary and a context re-establishment.

So a hygiene problem in `.plan/temp` propagates into the execution topology through
a learned measurement, and nothing in the resolve output says the learned figure was
taken from a run that had 450MB of residue under it.

## Proposed action

Two parts, and the first is the cheap one:

1. **Make the learned duration state its own hygiene.** When a recorded duration
   comes from a run whose timeout fired, or whose temp footprint exceeded a
   threshold, mark it — and prefer an unmarked observation when learning. A timeout
   is not a duration measurement; it is a non-finish, and the run's own decision log
   already says so ("Treated as a non-finish, NOT a failing build").
2. **Surface the hygiene state at resolve time.** When `architecture resolve`
   returns a `bash_timeout_seconds` that crosses the ceiling and re-tiers a command,
   the caller has no way to tell a genuinely-long build from a poisoned learned
   figure. A field naming the observation population the figure was learned from
   would let the orchestrator run `cleanup --target temp` before accepting a
   re-tiering.

The operational rule is already known in this corpus — run `run_config cleanup
--target temp` before blaming a slow build — but it is operator knowledge, applied
after three timeouts, not something the instrument says.

## Evidence

- aspect: plan_efficiency — build time reports `unavailable` (`build_count: 0` in
  the change-ledger oracle) while `pyproject_build` owns 46.4% of all script time
  (11,066,090ms over 67 calls, max 2,586,970ms). The build-time oracle and the
  script log disagree about whether this plan built at all.
- aspect: log_analysis — decision `467404`: job `a2103840` timeout at 873s,
  52,704 files / 450MB cleared, re-submitted green in 529s
- aspect: routing_decisions — decision `ac9c4b`: "quality-gate (live tier=
  orchestrator, bash_timeout=968s) and module-tests (live tier=orchestrator,
  bash_timeout=1473s) are outside the leaf's runnable slice"
- aspect: log_analysis — decision `834cf9` earlier in the same run: the same two
  canonicals resolved `per_task` at 360s and 501s
- aspect: log_analysis — decision `e310b9`: 233,856 scratch entries cleared at
  worktree removal
