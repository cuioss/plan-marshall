# CI Artifacts Persistence Layout

Standards document for the `manage-ci-artifacts` skill. Defines the
on-disk layout, manifest schema, idempotence contract, and retention
policy for the persistence layer that backs the `ci-verify` finalize
step.

## Storage layout

Per-plan, under the plan directory:

```text
.plan/plans/{plan_id}/
  artifacts/
    ci-runs/
      {run_id}/                      # GitHub run.databaseId or GitLab pipeline.id
        manifest.toon                # one per run — enumerates every job
        {job_name}.log               # per-job log slice, one file per job
        {job_name}.log               # (failing AND non-failing jobs both persisted)
        ...
      {next_run_id}/                 # loop-back commit produces a new run dir
        manifest.toon
        ...
```

`{job_name}` is sanitised to a portable file name segment — every run
of non-`[A-Za-z0-9._-]` characters is replaced with a single
underscore, and leading/trailing underscores are stripped. Empty job
names yield `unnamed-job`. Sanitisation is applied uniformly so the
on-disk layout is platform-portable.

## Manifest schema

One `manifest.toon` per `{run_id}` directory:

```toon
run_id: {run_id}
provider: github | gitlab
head_sha: {sha}
fetched_at: {iso8601}
pr_number: {pr_number}
plan_id: {plan_id}
wait_outcome: completed | deadline_exceeded
final_status: success | failure | none | timeout | ""
jobs_source: enumerated | empty
jobs[N]{name,workflow_name,job_name,conclusion,started_at,completed_at,run_url,log_path}:
  ...
```

The `head_sha` field makes the loop-back ↔ commit linkage auditable: a
retrospective sweeping every `artifacts/ci-runs/*/manifest.toon` can
correlate every CI run to the exact HEAD it ran against.

The `jobs_source` field labels how the `jobs[]` array was populated so
a zero-job manifest is never silently mistaken for "no CI ran":

- `enumerated` — the `persist` call was handed a non-empty jobs array
  (from the `checks status` / `checks wait` envelope), so every job is
  recorded with its per-job log slice.
- `empty` — the `persist` call received no jobs (an empty or missing
  `--jobs-file`). The manifest records zero jobs **deliberately**; this
  is a labelling state, not evidence that CI never ran. Callers that
  see `jobs_source: empty` on a green-CI path should treat it as a
  persist-invocation defect (the jobs array was not captured upstream),
  not as a genuine no-CI verdict.

`jobs_source` is also surfaced on the `persist` subcommand's TOON
return alongside `job_count` so the caller can react without re-reading
the manifest.

The `wait_outcome` and `final_status` fields are forwarded verbatim
from the `checks wait` envelope; they enable retrospectives to walk the
deliverable-5 / deliverable-6 producer-string classification without
re-fetching CI.

## Multi-run persistence (loop-back cascade)

Every loop-back commit (a HEAD-advancing fix-and-retry from
`verification-feedback` triage) produces a fresh CI run with a fresh
`run_id`. The persistence layer keys directories by `run_id`, so each
loop-back commit creates a new `artifacts/ci-runs/{run_id}/` directory
**without overwriting** previous runs. A typical loop-back cascade
produces N+1 run directories under `artifacts/ci-runs/` where N is the
number of loop-back commits.

## Idempotence contract

The `persist` subcommand is idempotent for the `(plan_id, run_id)`
pair:

1. First invocation: fetches every job's log via the
   `tools-integration-ci:ci checks logs` abstraction, writes one
   `.log` file per job, and emits `manifest.toon`. Returns
   `already_persisted: false` plus the per-job log paths.
2. Second invocation for the same `(plan_id, run_id)`: a no-op that
   re-reads the existing manifest and re-emits the per-job log paths.
   Returns `already_persisted: true` and does NOT re-fetch any logs.

The idempotence guarantee covers re-firing `ci-verify` against an
unchanged HEAD (cache-hit scenario). Loop-back commits that advance
HEAD produce a NEW `run_id` and therefore a fresh persist round —
idempotence applies per `run_id`, not per plan.

## Retention

Default retention: **keep all runs for the lifetime of the plan
directory**. No automatic pruning at phase-6-finalize completion.

Rationale:

- The plan dir is itself the unit of retention — when `archive-plan`
  archives the plan, the `artifacts/ci-runs/` tree archives with it.
- The multi-run history is the audit trail of the loop-back cascade;
  pruning it would orphan retrospectives that walk
  `manage-ci-artifacts list` to reconstruct the cascade.
- A single CI run on the typical marketplace project is a few MB of
  compressed logs; even a pathological 10-loop-back plan keeps well
  under 100 MB. The cost of "keep all" is negligible relative to the
  auditability gain.

Opt-in pruning (e.g., a `ci-verify-prune` finalize sub-step that drops
everything except the latest green run) is OUT OF SCOPE for this
skill. The decision is recorded here so future authors do not silently
re-invent it.

## Provider abstraction

All CI log fetching MUST flow through the
`plan-marshall:tools-integration-ci:ci fetch-logs` abstraction. Direct
`gh` or `glab` calls inside `manage_ci_artifacts.py` are forbidden by
the skill's enforcement block. The abstraction resolves to
`gh run view --log {run_id}` on GitHub and the equivalent `glab ci
trace` invocation on GitLab.

`manage_ci_artifacts.py` exposes a ``log_fetcher`` keyword argument on
``persist()`` as a test seam so unit tests can substitute a
deterministic fetcher without spawning real subprocesses. Production
callers do not supply the argument; the script's default fetcher
delegates to the CI abstraction.
