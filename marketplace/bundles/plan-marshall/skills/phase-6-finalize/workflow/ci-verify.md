---
name: default:ci-verify
description: "Classify CI run failures into the multi-failure-mode taxonomy and emit one structured triage finding per failing check (requires: [ci-complete] in consume-failures mode)"
order: 22
requires: [ci-complete]
implements: plan-marshall:extension-api/standards/ext-point-execution-context-workflow
---

# ci-verify

Dispatched body for the `default:ci-verify` finalize step (lesson
`2026-05-18-16-001` deliverable 6). Placement: AFTER `create-pr`,
BEFORE `architecture-refresh`. The standards counterpart is
[`../standards/ci-verify.md`](../standards/ci-verify.md).

Unlike the existing precondition-only consumers (`automated-review`,
`sonar-roundtrip`), this step's purpose is the *opposite* — it
**consumes** CI failures into a structured taxonomy rather than
short-circuiting on them. The `requires: [ci-complete]` precondition
is therefore invoked in `consume-failures` mode (see Step 3 in
[`../SKILL.md`](../SKILL.md) § "Precondition resolution"): the
resolver runs the same wait loop but threads
`final_status ∈ {success, failure, none, timeout}` and
`failing_checks` through to this body WITHOUT short-circuiting the
step to `failed`. This body then classifies each failing check into
the deterministic taxonomy and files one `triage` finding per
failing check.

## Inputs

- `{pr_number}` — resolved from the `create-pr` step's outcome record.
- `{plan_id}` — forwarded from the dispatcher.
- `{worktree_path}` — resolved from the dispatcher.

## Steps

### 1. Resolve CI run state via the provider abstraction

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci \
  --plan-id {plan_id} ci status --pr-number {pr_number}
```

The returned envelope carries `checks[]` (the full per-job array),
`failing_checks[]`, `run_id`, `head_sha`, `wait_outcome`, and
`final_status` (post lesson `2026-05-18-16-001` deliverable 1).
Extract these fields. The `checks[]` array enumerates **every** job —
green and red — and is the input to the jobs-capture step below.

### 2. Capture the jobs array into a JSON file

The `persist` call below records one per-job log slice plus a
`manifest.toon` jobs row for every job it is handed. To populate the
manifest's `jobs[]` it MUST be given the job array via `--jobs-file` —
omitting it produces a `jobs_source: empty` manifest that looks (to a
retrospective) as though no CI ran.

Write the `checks[]` array from step 1 to a JSON file under
`.plan/temp/` (one job dict per array entry; the persist layer reads
`name`, `workflow_name`, `job_name`, `conclusion`, `started_at`,
`completed_at`, `run_url` keys and tolerates absent ones):

```
Write(file_path=".plan/temp/{plan_id}-ci-jobs-{run_id}.json", content="{json_array_of_checks}")
```

The `{json_array_of_checks}` content is the step-1 envelope's
`checks[]` array serialised as a JSON array. When the envelope's
`checks[]` is empty, write `[]` — the persist call then deliberately
records a `jobs_source: empty` manifest.

### 3. Persist the CI run artifacts

Before classification, invoke `manage-ci-artifacts` to write the
per-job log slices plus `manifest.toon` under
`artifacts/ci-runs/{run_id}/`. This MUST run even on a green CI so
retrospectives have full evidence. Pass the jobs file from step 2 via
`--jobs-file` so the green-CI path persists per-job evidence:

```bash
python3 .plan/execute-script.py plan-marshall:manage-ci-artifacts:manage-ci-artifacts \
  persist --plan-id {plan_id} --run-id {run_id} --head-sha {head_sha} \
  --pr-number {pr_number} --provider {github|gitlab} \
  --wait-outcome {wait_outcome} --final-status {final_status} \
  --jobs-file .plan/temp/{plan_id}-ci-jobs-{run_id}.json
```

Capture the returned `manifest_path`, `jobs_source`, and per-job
`log_paths[]`. A `jobs_source: empty` value on a green-CI run is a
defect signal — it means the `checks[]` array was not captured in
step 2 — and SHOULD be surfaced rather than silently accepted.

### 4. Green-CI early return

When `final_status == "success"` AND `failing_checks == []`, mark the
step `done` with `display_detail: "ci-verify: all checks green"` and
return. Artifacts have already been persisted in step 3.

### 5. No-checks case (`final_status == "none"`)

File exactly ONE finding with producer `ci-verify-missing`, subtype
`ci_no_checks`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings add \
  --plan-id {plan_id} --type triage --severity warning \
  --component "plan-marshall:phase-6-finalize" \
  --title "[ci_no_checks] CI run produced zero checks" \
  --detail "[ci_no_checks] CI run produced zero checks for PR {pr_number} at HEAD {head_sha}" \
  --file-path "artifacts/ci-runs/{run_id}/manifest.toon"
```

Then dispatch `verification-feedback` ONCE with `producer=ci-verify-missing`.

### 6. Per-check classification (failing partition)

For each entry in `failing_checks[]`, classify into one of the rows
in the taxonomy table from
[`../standards/ci-verify.md`](../standards/ci-verify.md). The
classification reads each entry's `conclusion` and `workflow_name`
fields:

| Detection | Row producer | Subtype |
|-----------|--------------|---------|
| `conclusion in {failure, failed}` AND workflow_name matches a build profile name | `ci-verify-build` | `ci_build_failure` |
| `conclusion in {failure, failed}` AND workflow_name does NOT match a build profile name | `ci-verify-policy` | `ci_policy_failure` |
| `conclusion in {timed_out}` OR `wait_outcome == deadline_exceeded` | `ci-verify-timeout` | `ci_timeout` |
| `conclusion in {cancelled, canceled}` | `ci-verify-cancelled` | `ci_cancelled` |
| `conclusion == action_required` | `ci-verify-action-required` | `ci_action_required` |
| `conclusion == stale` | `ci-verify-stale` | `ci_stale` |

Build profile matching: resolve via
`architecture resolve --command verify` and treat the resolved
command's canonical names (`verify`, `quality-gate`, `module-tests`,
`coverage`) as the build-profile workflow set. Workflow names that
match this set produce `ci-verify-build` findings; non-matching names
produce `ci-verify-policy` findings.

For each classified check, file ONE finding:

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings add \
  --plan-id {plan_id} --type triage --severity warning \
  --component "plan-marshall:phase-6-finalize" \
  --title "[{subtype}] {check_name} failed" \
  --detail "[{subtype}] {check_name} failed on PR {pr_number} at HEAD {head_sha}" \
  --file-path "artifacts/ci-runs/{run_id}/{job_name}.log"
```

The `{subtype}` token is the second column of the taxonomy table
above; substitute literally (e.g. `[ci_build_failure]`). Retrospectives
grep for `[ci_*]` prefixes in the message body to filter by subtype
without requiring a schema change.

### 7. Batched triage dispatch (one per producer string)

Group findings by producer string and dispatch
`verification-feedback` ONCE per producer (NOT per finding) so the
triage workflow can batch findings of the same kind. The seven
distinct producer strings are
`ci-verify-{build,policy,timeout,cancelled,action-required,stale,missing}`.
Each dispatch carries `--phase phase-6-finalize --role
verification-feedback producer={producer-string}`. See
[`../SKILL.md`](../SKILL.md) Step 3 dispatch table for the resolution
target.

### 8. Aggregate outcomes

After all triage dispatches return, aggregate per-producer outcomes
into the step's terminal outcome:

- If ANY triage returned `loop_back` → mark step `loop_back`.
- Otherwise → mark step `done`.

Sonar quality-gate failures continue to flow exclusively through
`sonar-roundtrip` and are NEVER reported as findings from this body.
A Sonar status check that appears as a GitHub check lands in row (c)
`ci_policy_failure`; the authoritative consumer remains
`sonar-roundtrip`.
