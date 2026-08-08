---
name: plan-marshall-manage-ci-artifacts
description: Persist CI run artifacts (logs + manifest) under the plan directory for offline retrospectives
compatibility: Adapted from plan-marshall marketplace (Claude Code native)
---

# Manage CI Artifacts Skill

Persistence layer for CI run artifacts. The `ci-verify` finalize step
calls this skill to write a per-job log slice plus a `manifest.toon`
under `artifacts/ci-runs/{run_id}/` inside the plan directory at
classification
time. The eager-fetch model keeps the evidence on disk before
retrospectives run, immune to GitHub's 90-day log retention window.

## Enforcement

> **Base contract**: See [manage-contract.md](../ref-workflow-architecture/standards/manage-contract.md) for shared enforcement rules, TOON output format, and error response patterns.

**Skill-specific constraints:**

- `--run-id` MUST be a non-empty string; the value is the per-run directory
  key and an empty value would collide every run into the same directory.
- The `persist` subcommand is idempotent: a second invocation for the same
  `(plan_id, run_id)` MUST be a no-op that re-emits the existing manifest
  (no log re-fetching).
- All CI log fetching MUST flow through the
  `plan-marshall:tools-integration-ci:ci fetch-logs` abstraction; no
  direct `gh` / `glab` calls inside this skill's scripts.

## Storage Location

```text
.plan/plans/{plan_id}/
  artifacts/
    ci-runs/
      {run_id}/
        manifest.toon      # one per run — enumerates every job
        {job_name}.log     # per-job log slice
        ...
      {next_run_id}/       # loop-back commit produces a new run dir
        manifest.toon
        ...
```

The `manifest.toon` shape is documented in
[`standards/persistence-layout.md`](standards/persistence-layout.md).
Multi-run loop-back cascades MUST NOT overwrite previous runs — every
`{run_id}` directory is independent and survives until the plan dir is
archived.

---

## Operations

Script: `plan-marshall:manage-ci-artifacts:manage-ci-artifacts`

### persist

Fetch and write the full run artifacts (eager mode).

```bash
python3 .plan/execute-script.py plan-marshall:manage-ci-artifacts:manage-ci-artifacts \
  persist --plan-id {plan_id} --run-id {run_id} --head-sha {sha} \
  --pr-number {pr_number} --provider {github|gitlab}
```

**Output (TOON)**:

```toon
status: success
plan_id: {plan_id}
run_id: {run_id}
run_dir: artifacts/ci-runs/{run_id}
already_persisted: true | false
job_count: N
manifest_path: artifacts/ci-runs/{run_id}/manifest.toon
log_paths[N]:
  - artifacts/ci-runs/{run_id}/{job_name}.log
  - ...
```

**Idempotence**: when `artifacts/ci-runs/{run_id}/manifest.toon` already
exists, the script returns `already_persisted: true` and re-emits the
existing manifest contents (paths and job_count) without re-fetching logs.

### read

Read a previously persisted manifest. Used by the retrospective phase.

```bash
python3 .plan/execute-script.py plan-marshall:manage-ci-artifacts:manage-ci-artifacts \
  read --plan-id {plan_id} --run-id {run_id}
```

**Output (TOON)**: The persisted manifest content.

### list

Enumerate all persisted runs under the plan dir, sorted by `fetched_at`.

```bash
python3 .plan/execute-script.py plan-marshall:manage-ci-artifacts:manage-ci-artifacts \
  list --plan-id {plan_id}
```

**Output (TOON)**:

```toon
status: success
plan_id: {plan_id}
run_count: N
runs[N]{run_id,head_sha,fetched_at,job_count}:
  ...
```

---

## Retention

Default: keep all runs for the lifetime of the plan dir. The plan dir is
itself the unit of retention — when `archive-plan` archives the plan, the
`artifacts/ci-runs/` tree archives with it. No automatic pruning at
phase-6-finalize completion; opt-in pruning is out of scope for this
skill and would be a future enhancement gated by user demand. See
[`standards/persistence-layout.md`](standards/persistence-layout.md) for
the no-prune decision rationale.

## Canonical invocations

The canonical argparse surface for `manage-ci-artifacts.py`. The plugin-doctor analyzer (`_analyze_manage_invocation.py`) reads this section as source-of-truth for the `manage-invocation-invalid` and `missing-canonical-block` rules. Consuming docs xref this section by name instead of restating the command inline. See [`pm-plugin-development:plugin-script-architecture` cross-skill-integration.md](../../../pm-plugin-development/skills/plugin-script-architecture/standards/cross-skill-integration.md) § "Script invocation in documentation".

### persist

```bash
python3 .plan/execute-script.py plan-marshall:manage-ci-artifacts:manage-ci-artifacts persist \
  --plan-id PLAN_ID --run-id RUN_ID --head-sha HEAD_SHA --pr-number PR_NUMBER \
  --provider {github,gitlab} \
  [--jobs-file JOBS_FILE] [--wait-outcome {completed,deadline_exceeded}] [--final-status FINAL_STATUS]
```

### read

```bash
python3 .plan/execute-script.py plan-marshall:manage-ci-artifacts:manage-ci-artifacts read \
  --plan-id PLAN_ID (--run-id RUN_ID | --latest)
```

`--run-id` and `--latest` are mutually exclusive; exactly one must be supplied.

### list

```bash
python3 .plan/execute-script.py plan-marshall:manage-ci-artifacts:manage-ci-artifacts list \
  --plan-id PLAN_ID
```
