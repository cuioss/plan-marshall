# Aspect: Logging Gap Analysis

Identifies places where the LLM or a component should have logged but didn't — gaps make plan introspection harder and invalidate log-analysis findings. LLM-driven; inputs include the existing logs and the skill references that drive the plan.

## Inputs

- `work.log`, `decision.log`, `script.log` — what was actually logged.
- Skill reference documents in scope (loaded from marketplace based on `references.json` domains).
- `references.json` `affected_files` — evidence of actions that should produce log entries.
- `work/metrics-dispatch-boundaries-5-execute.toon` (when present) — per-dispatch termination-cause audit trail written by `manage-metrics record-dispatch-boundary`. Used by the `DISPATCH_TERMINATION_CAUSE` rule below to detect agent-initiated re-dispatch and correlate it with `[OUTCOME]`-log coverage gaps. Plans whose execution preceded this artifact will not have the file; the rule is precondition-guarded so its absence is not a gap.

## Expected Log Patterns

Phase skills are expected to emit:
- `[STATUS] (plan-marshall:{skill}) Starting {phase} — ...` at entry.
- `[STATUS] (plan-marshall:{skill}) Completed {phase}` at exit.
- `[DECISION] (plan-marshall:{skill}:{sub}) ...` for each non-trivial choice.
- `[ARTIFACT] (plan-marshall:{skill}) ...` when an artifact is produced.
- `[VERIFY] (plan-marshall:{skill}) ...` when verification runs.
- `[ERROR] (plan-marshall:{skill}) ...` on any error.

## TOON Fragment Shape

```toon
aspect: logging_gap_analysis
status: success
plan_id: {plan_id}
expected_vs_actual[*]{category,expected_min,observed}:
  STATUS,12,10
  DECISION,6,2
  ARTIFACT,8,8
  VERIFY,6,6
  ERROR,any,3
  OUTCOME_COVERAGE,{tasks_done},{outcome_lines}
  RE_ENTRY_COVERAGE,{re_entry_count},{re_entry_count}
  ARTIFACT_EMISSION,{outcome_with_changes},{artifacts_after_outcome}
  DISPATCH_TERMINATION_CAUSE,{dispatch_rows},{dispatch_rows}
  VOLUNTARY_CHECKPOINT_POLLING,0,{polling_pairs_count}
gaps[*]{skill_or_phase,category,detail}:
  phase-3-outline,DECISION,"0 decision entries — deliverable packaging decisions not logged"
  phase-5-execute,OUTCOME_COVERAGE,"3 tasks done but only 1 [OUTCOME] line — likely lost on agent-initiated re-dispatch"
  phase-5-execute,RE_ENTRY_COVERAGE,"2 dispatch clusters detected but only 1 [STATUS] Re-entering line — orchestrator may have skipped re-entry logging"
  phase-5-execute,ARTIFACT_EMISSION,"5 [OUTCOME] lines but only 2 [ARTIFACT] entries — task-completion artifact emission missing for 3 tasks"
  phase-5-execute,DISPATCH_TERMINATION_CAUSE,"4 dispatches recorded with termination_cause=voluntary_checkpoint — agent-initiated re-dispatch is the dominant termination mode"
findings[*]{severity,message}:
  warning,"Decision log sparse in outline phase"
  error,"phase-5-execute [OUTCOME] coverage mismatch — see lesson 2026-05-08-14-001"
```

## LLM Interpretation Rules

- The ratio `observed / expected_min < 0.5` is a `warning`.
- Zero `DECISION` entries in phases that made visible choices (outline packaging, plan task ordering) is always a `warning`.
- Zero `ARTIFACT` entries is an `error` — artifacts were produced but not announced. `phase-5-execute` is expected to emit one `[ARTIFACT]` entry per file operation at task completion, so the canonical check is `counts.artifact_entries > 0` whenever the plan footprint is non-empty (derived live from the worktree, falling back to the legacy `references.modified_files` key only for older archived plans); this is enforced programmatically by the retrospective pipeline rather than being treated as a known offender.
- `ERROR` entries are expected to be zero; count them but do not flag count itself — the errors surface via log-analysis / script-failure-analysis.

### Phase-5 invariants (precondition-guarded)

The four rules below guard `[OUTCOME]`-log coverage against loss on
agent-initiated re-dispatch. Each rule is **precondition-guarded** so it does
NOT false-positive on plans whose execution predates the corresponding
deliverable. When the precondition is absent, the rule emits no finding.

- **OUTCOME_COVERAGE** (category: `OUTCOME_COVERAGE`) — **Precondition**: at
  least one `[OUTCOME] (plan-marshall:phase-5-execute) Completed` entry
  exists in `work.log` (i.e. the plan ran on a build that includes the
  script-level `[OUTCOME]` guard from D1). When the precondition holds,
  count: number of tasks with `status: done` in `tasks_table` (`tasks_done`)
  vs. number of `[OUTCOME] (plan-marshall:phase-5-execute) Completed
  TASK-NNN` entries in `work.log` (`outcome_lines`). If
  `outcome_lines < tasks_done`, emit an `error`-severity finding citing
  lesson `2026-05-08-14-001`. Plans without any `[OUTCOME]` line skip this
  rule entirely.

- **RE_ENTRY_COVERAGE** (category: `RE_ENTRY_COVERAGE`) — **Precondition**:
  at least one `[STATUS] (plan-marshall:phase-5-execute) Re-entering execute
  phase` entry exists in `work.log` (i.e. the plan ran on a build that
  differentiates first entry from re-entry per D2). When the precondition
  holds, cluster `[STATUS] (plan-marshall:phase-5-execute) {Starting,
  Re-entering} execute phase` lines using `gap_threshold_s = 30` (any two
  status lines whose timestamps are more than 30 seconds apart belong to
  separate dispatch clusters). For each cluster after the first, expect
  exactly one `Re-entering` line. If `re_entry_count` (the number of
  dispatch clusters minus one) does not match the number of `Re-entering`
  lines observed, emit a `warning`-severity finding. Plans without any
  `Re-entering` line skip this rule entirely.

- **ARTIFACT_EMISSION** (category: `ARTIFACT_EMISSION`) — preserves the
  pre-existing rule (zero `[ARTIFACT]` entries when the plan footprint is
  non-empty is an `error`) and adds a new
  branch keyed on the OUTCOME_COVERAGE precondition. **Precondition for the
  new branch**: at least one `[OUTCOME] (plan-marshall:phase-5-execute)
  Completed` entry exists. When the precondition holds, every `[OUTCOME]`
  line emitted for a task that produced file changes (i.e. the task's
  diff against its `task_start_sha` is non-empty) MUST be immediately
  followed by at least one `[ARTIFACT] (plan-marshall:phase-5-execute:{N})`
  line. If the count of `[OUTCOME]` lines with a non-empty diff
  (`outcome_with_changes`) exceeds the count of `[ARTIFACT]` entries that
  reference a task number `{N}` matching one of those `[OUTCOME]` lines
  (`artifacts_after_outcome`), emit an `error`-severity finding. Plans
  without any `[OUTCOME]` line skip the new branch (the existing branch
  still applies).

- **DISPATCH_TERMINATION_CAUSE** (category: `DISPATCH_TERMINATION_CAUSE`) —
  **Precondition**: `work/metrics-dispatch-boundaries-5-execute.toon` exists
  (i.e. the orchestrator was running a build that includes the
  `record-dispatch-boundary` subcommand from D3 and the workflow change
  from D4). When the precondition holds, parse the file and count rows by
  `termination_cause`. Emit findings:

  - One `info`-severity finding with the per-cause distribution over the
    canonical value set (e.g. `"4 voluntary_checkpoint,
    1 task_complete_returned_verbatim, 0 harness_cancellation, 0 error,
    1 clean_exit_queue_empty"`).
  - A `warning`-severity finding when `unknown_count > 0` — any row
    carrying the literal `unknown` termination cause is legacy data from
    before the `clean_exit_queue_empty` migration (the recorder no longer
    accepts `unknown`), so its presence is the signal that the plan was
    captured by an older recorder OR a recorder-call-site defect re-emerged
    after the migration. This is the finding that catches any post-merge
    recurrence of the overloaded-fallback defect.
  - A `warning`-severity finding when `voluntary_checkpoint`
    + `task_complete_returned_verbatim` together account for more than
    50 % of recorded dispatches — agent-initiated re-dispatch is the
    failure mode lesson `2026-05-08-14-001` is meant to detect.

  Plans without the artifact skip the rule entirely.

### VOLUNTARY_CHECKPOINT_POLLING (phase-5 invariant, precondition-guarded)

- **VOLUNTARY_CHECKPOINT_POLLING** (category: `VOLUNTARY_CHECKPOINT_POLLING`) —
  **Precondition**: at least one `[ATTEMPT]` work-log line exists in `work.log`
  (i.e. the plan ran on a build that includes execute-task's mandatory `[ATTEMPT]`
  guard, added in the `bash-compound-command-with-tmp-redirect-triggered` deliverable).
  When the precondition holds, scan `work.log` for consecutive-line pairs where an
  `[ATTEMPT]` line is followed within the next 5 lines by any line that contains
  a polling-language keyword: `sleeping`, `polling`, `wait`, `background`, `sleep`,
  or `run_in_background`. Each such pair is a candidate signal that the agent
  dispatched a subagent (the `[ATTEMPT]` line) but then attempted to poll for its
  result rather than running synchronously or using `run_in_background` correctly.
  When `polling_pairs_count > 0`, emit a `warning`-severity finding citing the
  source lesson and the number of candidate pairs detected. Plans without any
  `[ATTEMPT]` line skip this rule entirely.

  The rule is a heuristic: not every `[ATTEMPT]` + polling-keyword pair is a defect
  (e.g. a fire-and-forget background process with `run_in_background: true` that
  logs "dispatching background task"), so the LLM applies judgement when reviewing
  the surfaced candidates. The fact extractor counts candidates only — no
  auto-classification.

## Finding Shape

```toon
aspect: logging_gap_analysis
severity: info|warning|error
category: STATUS|DECISION|ARTIFACT|VERIFY|ERROR|OUTCOME_COVERAGE|RE_ENTRY_COVERAGE|ARTIFACT_EMISSION|DISPATCH_TERMINATION_CAUSE|VOLUNTARY_CHECKPOINT_POLLING
skill_or_phase: "{scope}"
message: "{one-line}"
```

## Out of Scope

- Proposing new log statements line-by-line — emit findings, not diffs.
- Parsing of log bodies beyond tag counts — log-analysis owns that.

## Persistence

After synthesizing the TOON fragment per the shape documented above, the orchestrator writes the fragment to `work/fragment-logging-gap-analysis.toon` via the `Write` tool and registers it with the bundle:

```bash
python3 .plan/execute-script.py plan-marshall:plan-retrospective:collect-fragments add \
  --plan-id {plan_id} --aspect logging-gap-analysis --fragment-file work/fragment-logging-gap-analysis.toon
```

`compile-report run --fragments-file` consumes the assembled bundle in Step 4 of SKILL.md. The bundle file is auto-deleted on successful report write; on failure it is retained for debugging.
