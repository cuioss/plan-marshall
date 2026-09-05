# Aspect: Logging Gap Analysis

Identifies places where the LLM or a component should have logged but didn't — gaps make plan introspection harder and invalidate log-analysis findings. LLM-driven; inputs include the existing logs and the skill references that drive the plan.

## Exit-code convention for every script call

Every `python3 .plan/execute-script.py` call in this document — of EVERY notation, **not only `manage-*`** — carries the following exit-code contract unless a step explicitly states otherwise. The scope is widened past `manage-*` because this document invokes `collect-fragments` — a `manage-*`-scoped convention leaves exactly those calls with no rule at all, which is the swallowed-rejection gap.

- **`exit_code == 0` AND `status: success`**: parse the returned TOON and use the value as the step describes.
- **`exit_code == 0` with a `status` other than `success`, or with no parseable `status` at all**: NOT a usable value — STOP exactly as the `exit_code != 0` disposition below requires, with one difference in what the error TOON carries: on this path the diagnostic is on STDOUT, not stderr. Preserve the stdout **error envelope** as emitted — every field it carries, verbatim — into the returned error TOON; it is the only account of the cause that exists. Copy the whole envelope rather than a fixed field list, because the diagnostic fields vary by verb and `error` is sometimes a generic string whose real cause sits in one of the others. A zero exit is not evidence the operation succeeded; a script MAY print `status: error` and still exit 0. Read `status` FIRST, and never read a **success-payload** field off a non-`success` return. A malformed or truncated stdout carrying **no parseable `status` at all** takes this same path: an unreadable read is not evidence of success, so it fails closed onto STOP rather than falling through to the first clause.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

The middle clause is what the `ci` family makes load-bearing: a `ci` verb reports failure as `status: error` at exit 0 **by design**, so a caller must branch on the payload `status` and never on the exit code. That rule is stated authoritatively in `plan-marshall:tools-integration-ci`; it is not restated here.

Step-level exceptions — calls whose non-zero exit is itself the signal — are documented inline in the step that issues them.

## Inputs

- `work.log`, `decision.log`, `script.log` — what was actually logged.
- Skill reference documents in scope (loaded from marketplace based on `references.json` domains).
- `references.json` `affected_files` — evidence of actions that should produce log entries.
- `work/metrics-dispatch-boundaries-{phase}.toon` (each phase that dispatches Task agents — in practice `5-execute` **and** `6-finalize`, whichever are present) — per-dispatch termination-cause audit trail written by `manage-metrics record-dispatch-boundary`. The fact extractor (`analyze-logs.py read_dispatch_boundaries_per_phase`) globs every `metrics-dispatch-boundaries-*.toon` and surfaces each phase's rows under its own key, so the `DISPATCH_TERMINATION_CAUSE` rule below reads **all** dispatching phases — not the execute file alone. The finalize file is where a review-shaped dispatch's `returned_with_findings` (productive loop-back) and `error` (genuine terminal failure) rows land, and it carries the majority of the finalize dispatch spend; a rule scoped to execute only would leave it audited by nothing. Used to detect agent-initiated re-dispatch and correlate it with `[OUTCOME]`-log coverage gaps. Plans whose execution preceded this artifact will not have the file; the rule is precondition-guarded so its absence is not a gap.

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
- Zero `ARTIFACT` entries is an `error` — artifacts were produced but not announced. `phase-5-execute` is expected to emit one `[ARTIFACT]` entry per file operation at task completion, so the canonical check is `counts.artifact_entries > 0` whenever the plan footprint is non-empty (recovered through the shared footprint resolver, whose declared `RESOLVING_TIERS` list is authoritative); this is enforced programmatically by the retrospective pipeline rather than being treated as a known offender.
- ⛔ **That plan-level floor cannot fire on a real plan, and nothing may be deferred to it.** `artifact_entries` counts `[ARTIFACT]` lines from EVERY caller, and `phase-1-init` emits one unconditionally, so the count is never zero however completely per-task emission was bypassed. The per-task population rule below is the only detector of this class that can actually fire; read the floor as a structural backstop for a plan with no logs at all, never as the guard against missing per-task emission.
- The floor is a **three-way** read of that footprint, not a truthiness test. A footprint no tier resolved is `None`, and it emits `ARTIFACT_COVERAGE_UNMEASURABLE` at `severity: warning` instead of the `error` above: nothing was measured, so nothing failed — but the check did not run, and an un-run check must not present as a clean one. A resolved-but-**empty** footprint is a genuine measurement (the plan touched nothing, so no `[ARTIFACT]` entry is expected) and emits no finding at all. Reading the unresolvable state as an empty footprint silently disables this floor, which is the defect the sentinel removes.
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

  The rule is stated as a POPULATION, `N of M change-qualified completed tasks
  emitted >= 1 [ARTIFACT] line`, and both numbers are published on every run — a
  partial count read as a total is the defect a bare non-zero assertion
  produces.

  ⛔ **`M` is CHANGE-QUALIFIED, and `N` is drawn from that same eligible set.**
  `M` = task files with `status: done` **whose own task diff is non-empty**;
  `N` = the subset of those carrying at least one per-task artifact line.
  Counting every completed task into `M` was wrong in the one direction that
  matters: Step 8 emits nothing when a task's diff is empty, so a compliant
  no-op task — a verification task, a task whose edit another task already made
  — lowered `N/M` while behaving exactly as specified, and enough of them pushed
  a healthy plan into `ARTIFACT_EMISSION_PARTIAL` or, when every completed task
  was a no-op, into `ARTIFACT_EMISSION_ABSENT`. A non-empty PLAN footprint does
  not repair this: it is a property of the plan, not evidence that any
  particular task changed a file.

  ⛔ **When per-task change attribution is unavailable, emit NO finding.** The
  qualification needs each task's own realized change set, which the offline
  inputs carry only when a task record holds a `changed_files` LIST — the
  per-task SHA range Step 8 diffs is not persisted in a stable place. A
  present-but-empty list is a measurement ("this task changed nothing").

  ⛔ `measured` requires that list on **every** completed task, not on at least
  one. A completed task without the key joins neither the changed set nor the
  unchanged one, so qualifying while any record is missing draws both `M` and `N`
  from the recorded subset alone and silently narrows the population to it — one
  recorded task that changed files and emitted no line, beside nine unrecorded
  ones that all emitted, reads as `M=1` / `N=0` and fires
  `ARTIFACT_EMISSION_ABSENT`. Partial recording is not full measurement. Two
  states therefore report `unavailable` — no completed record carries the list,
  and a MIXED corpus where some do and some do not — and the reason names which,
  because the remedies differ.

  The extractor publishes `change_attribution: measured | unavailable`, and it is
  the field to read FIRST. On `measured` it also publishes `eligible_tasks` (`M`),
  `eligible_tasks_with_artifacts` (`N`) and `eligible_tasks_without_artifacts`. On
  `unavailable` those three keys are **ABSENT**, not zero — a consumer that gates
  on them finds no key rather than a false zero — and a
  `change_attribution_reason` names why. The un-qualified `completed_tasks` count
  is published throughout as provenance and MUST NOT be substituted for `M`: that
  is the absent-read-as-measured swap this whole aspect exists to prevent, and it
  would reinstate exactly the false positive above.

  Two findings come off the eligible set, and the whole incomplete range
  `N < M` is covered rather than only its interior:

  - `ARTIFACT_EMISSION_PARTIAL` (`warning`) — `0 < N < M`. The per-task emitting
    path is demonstrably in use yet incomplete over the tasks that DID change
    files. A no-op task can no longer contribute to this gap, so a residual one
    is a real shortfall rather than a compliant silence.
  - `ARTIFACT_EMISSION_ABSENT` (`warning`) — `N == 0` with `M >= 1`, **and the
    plan footprint resolved non-empty**. That footprint condition is the
    discriminator between the two causes of a total absence: with files changed
    and change-qualified tasks completed, not one of them emitting means the
    path was bypassed, whereas an empty or unresolvable footprint leaves "this
    plan uses no per-task emission" and "emission was bypassed"
    indistinguishable. In that indistinguishable case NO finding is emitted —
    which is also what keeps archived plans predating per-task emission from
    reporting one — and the published `0 of M` population still states what was
    measured. `M >= 1` is now a statement about eligible tasks, so a plan whose
    completed tasks were all no-ops has `M == 0` and reaches neither finding.

- **DISPATCH_TERMINATION_CAUSE** (category: `DISPATCH_TERMINATION_CAUSE`) —
  **Precondition**: at least one `work/metrics-dispatch-boundaries-{phase}.toon`
  exists (i.e. the orchestrator was running a build that includes the
  `record-dispatch-boundary` subcommand from D3 and the workflow change
  from D4). When the precondition holds, parse **every** such file — the fact
  extractor surfaces one entry per dispatching phase, so read `5-execute` **and**
  `6-finalize` (and any other phase present), not the execute file alone — and
  count rows by `termination_cause`, per phase. The finalize file is where a
  review-shaped dispatch's `returned_with_findings` (productive loop-back) and
  `error` (genuine terminal failure) rows land and carries the majority of the
  finalize dispatch spend; auditing it is the point of the widened scope. Emit
  findings:

  - One `info`-severity finding per dispatching phase with that phase's per-cause
    distribution over the
    canonical `termination_cause` value set. That set is exactly the
    `record-dispatch-boundary` `--termination-cause` `choices` (the
    `DISPATCH_TERMINATION_CAUSES` tuple in `manage-metrics.py`) — the accepted
    causes:
    `voluntary_checkpoint`, `task_complete_returned_verbatim`, `budget_yield`,
    `harness_cancellation`, `error`, `clean_exit_queue_empty`, `step_complete`,
    `blocked_user_review`, `blocked_session_restart`, `task_batch_complete`,
    `agent_returned`, `returned_with_findings`, `baseline_drift`.
    Report the count for every value in that set — including the causes that did
    not occur, as an explicit zero — e.g. `"4 voluntary_checkpoint,
    1 task_complete_returned_verbatim, 2 budget_yield, 0 harness_cancellation,
    0 error, 1 clean_exit_queue_empty, 0 step_complete, 0 blocked_user_review,
    0 blocked_session_restart, 0 task_batch_complete, 0 agent_returned,
    0 returned_with_findings, 0 baseline_drift"`.
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
    **`budget_yield` is EXCLUDED from this > 50 % count**: a `budget_yield`
    row is a deterministic, legitimate plan-time-packed yield (the
    plan-time bin-packer pre-computed the envelope grouping, and the yield
    carries a logged `budget_yield` decision + a wrapped terminal payload),
    NOT the agent-initiated-re-dispatch failure mode. Count only
    `voluntary_checkpoint` + `task_complete_returned_verbatim` toward the
    threshold; a high `budget_yield` share simply reflects how many
    execution envelopes the bin-packer produced (one yield per envelope
    boundary) and is expected for multi-envelope plans.
    **`returned_with_findings` is EXCLUDED from this > 50 % count for the same
    reason, from the opposite direction**: it is a PRODUCTIVE non-completion —
    the dispatch found defects and looped back — so it is the opposite of wasted
    spend and must never be read as an agent-initiated-re-dispatch failure. A
    high `returned_with_findings` share means the review dispatches were doing
    their job; do not flag it.
  - **Genuinely-wasted vs retryable dispatch spend (per phase).** The fact
    extractor also sums `total_tokens` by cause-class so a reader sees the waste
    without reconstructing it from the raw rows:
    - `error_total_tokens` — the spend on dispatches whose terminal state is
      **genuinely non-productive**: they raised a fatal `error` and returned
      nothing (findings-bearing loop-backs are now stamped `returned_with_findings`,
      not `error`, so what remains under `error` is genuine terminal waste). This
      is the figure a reader acts on: a dispatch that examined nothing and
      returned nothing cost real tokens and bought zero detection.
    - `retryable_total_tokens` — the spend on **retryable / infrastructure**
      terminations (`blocked_session_restart` + `harness_cancellation`). Reported
      **distinctly** from `error_total_tokens` because the two need different
      remedies: a session-restart block is infrastructure that a re-run recovers,
      whereas a fatal error may be deterministic. Conflating them produces a fix
      for the wrong half, so they are never summed into one "failure" figure here.

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
