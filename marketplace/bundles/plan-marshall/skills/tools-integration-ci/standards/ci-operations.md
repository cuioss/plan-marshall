# CI Operations

CI status checking, waiting, rerunning, and log retrieval.

---

## Workflow: Check CI Status

**Pattern**: Provider-Agnostic Router

Check CI status for a pull request.

### Step 1: Resolve and Execute

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci checks status \
    (--pr-number 123 | --head feature/x) \
    [--error-style maven|gradle|npm|generic]
```

Supply exactly one of `--pr-number` or `--head`. The `--head` form is required when invoking
from the main checkout against a worktree-isolated plan branch — see
[pr-operations.md § Worktree-Isolated Plans](pr-operations.md#worktree-isolated-plans).

`--error-style` (default `generic`) selects how an auto-downloaded failure log is filtered
when one or more checks fail — see Step 3 below.

### Step 2: Process Result (all passing / pending)

```toon
status: success
operation: ci_status
pr_number: 123
overall_status: pending
elapsed_sec: 45

checks[3]{name,status,result,elapsed_sec,url,workflow}:
build	completed	success	120	https://github.com/org/repo/actions/runs/111	CI
test	in_progress	-	45	https://github.com/org/repo/actions/runs/112	CI
lint	completed	success	30	https://github.com/org/repo/actions/runs/113	Lint
```

### Step 3: Process Result (one or more checks failed)

When any check completes with `result: failure`, `checks status` automatically downloads
and filters that check's failing-job log — for **every** failing check — before returning.
No separate subcommand is involved; the behavior is built into `checks status`.

For each failing check, two files are written under `artifacts/ci-runs/{run_id}/`:

```text
artifacts/ci-runs/{run_id}/{slug}.log           # raw downloaded failing-job log
artifacts/ci-runs/{run_id}/{slug}.filtered.log  # error-extraction filtered variant
```

`{slug}` is the check name slugified (lowercased, non-alphanumeric runs collapsed to `-`;
e.g. `verify / verify` → `verify-verify`). Each path is surfaced **per entry** inside the
`failing_checks[]` array — as the entry's `log_file` and `filtered_log_file` fields — never
as scalar top-level keys.

For a **reusable-workflow** check (name contains `" / "`, e.g. `verify / verify`), the
auto-download targets the nested **job id** — parsed from the check `link`'s `/job/{job_id}`
segment — rather than the caller `run_id`. Targeting the caller run returns an empty log for
such checks; targeting the nested job retrieves the called job's failure log.

```toon
status: success
operation: ci_status
pr_number: 123
overall_status: failure
check_count: 3
elapsed_sec: 210

checks[3]{name,status,result,elapsed_sec,url,workflow}:
build	completed	success	120	https://github.com/org/repo/actions/runs/111	CI
verify / verify	completed	failure	180	https://github.com/org/repo/actions/runs/112	CI
lint	completed	failure	40	https://github.com/org/repo/actions/runs/113	Lint

failing_checks[2]{name,run_id,error_style,log_file,filtered_log_file}:
verify / verify	112	generic	artifacts/ci-runs/112/verify-verify.log	artifacts/ci-runs/112/verify-verify.filtered.log
lint	113	generic	artifacts/ci-runs/113/lint.log	artifacts/ci-runs/113/lint.filtered.log
```

The normative spec for this transport shape, the `--error-style` heuristics, and the slug
naming scheme is the central standard — see
[api-contract.md § CI Failure Log Download & Filtering](api-contract.md#ci-failure-log-download--filtering).

---

## Workflow: Wait for CI

**Pattern**: Polling with Timeout

Wait for CI checks to complete with two-layer timeout pattern. See [wait-pattern.md](../../tools-script-executor/standards/wait-pattern.md) for the full adaptive timeout architecture.

### Step 1: Execute with Timeout

Use outer shell timeout as safety net:

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci checks wait \
    --pr-number 123 \
    [--error-style maven|gradle|npm|generic]
```

**Bash tool timeout**: 1800000ms (30-minute safety net). Internal timeout managed by script.

`--error-style` (default `generic`) selects how an auto-downloaded failure log is filtered
when the run finishes with one or more failing checks — see Step 3 below.

### Step 2: Process Result (all passing)

```toon
status: success
operation: ci_wait
pr_number: 123
final_status: success
duration_sec: 95
elapsed_sec: 95

checks[3]{name,status,result,elapsed_sec,url,workflow}:
build	completed	success	120	https://github.com/org/repo/actions/runs/111	CI
test	completed	success	90	https://github.com/org/repo/actions/runs/112	CI
lint	completed	success	30	https://github.com/org/repo/actions/runs/113	Lint
```

### Step 3: Process Result (one or more checks failed)

When the run finishes with `final_status: failure`, `checks wait` automatically downloads
and filters the failing-job log for **every** failing check before returning — built into
`checks wait`, not a separate subcommand. Per failing check, two files are written under
`artifacts/ci-runs/{run_id}/`:

```text
artifacts/ci-runs/{run_id}/{slug}.log           # raw downloaded failing-job log
artifacts/ci-runs/{run_id}/{slug}.filtered.log  # error-extraction filtered variant
```

`{slug}` is the check name slugified (lowercased, non-alphanumeric runs collapsed to `-`;
e.g. `verify / verify` → `verify-verify`). Each path appears **per entry** in the
`failing_checks[]` array as the entry's `log_file` / `filtered_log_file` fields — never as
scalar top-level keys.

For a **reusable-workflow** check (name contains `" / "`, e.g. `verify / verify`), the
auto-download targets the nested **job id** — parsed from the check `link`'s `/job/{job_id}`
segment — rather than the caller `run_id`. Targeting the caller run returns an empty log for
such checks; targeting the nested job retrieves the called job's failure log.

```toon
status: success
operation: ci_wait
pr_number: 123
final_status: failure
duration_sec: 210
polls: 7
elapsed_sec: 210

checks[3]{name,status,result,elapsed_sec,url,workflow}:
build	completed	success	120	https://github.com/org/repo/actions/runs/111	CI
verify / verify	completed	failure	180	https://github.com/org/repo/actions/runs/112	CI
lint	completed	failure	40	https://github.com/org/repo/actions/runs/113	Lint

failing_checks[2]{name,run_id,error_style,log_file,filtered_log_file}:
verify / verify	112	generic	artifacts/ci-runs/112/verify-verify.log	artifacts/ci-runs/112/verify-verify.filtered.log
lint	113	generic	artifacts/ci-runs/113/lint.log	artifacts/ci-runs/113/lint.filtered.log
```

The normative spec for this transport shape, the `--error-style` heuristics, and the slug
naming scheme is the central standard — see
[api-contract.md § CI Failure Log Download & Filtering](api-contract.md#ci-failure-log-download--filtering).

---

## Workflow: Rerun CI

**Pattern**: Provider-Agnostic Router

Rerun a failed CI workflow run.

### Step 1: Execute

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci checks rerun \
    --run-id 12345
```

### Step 2: Process Result

```toon
status: success
operation: ci_rerun
run_id: 12345
```

---

## Workflow: Get CI Logs

**Pattern**: Provider-Agnostic Router

Get logs from a CI workflow run.

### Step 1: Execute

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci checks logs \
    --run-id 12345
```

### Step 2: Process Result

```toon
status: success
operation: ci_logs
run_id: 12345
log_lines: 142
content: [build log output]
```

For a **failed** run, `checks logs` returns an **error-context window** rather than the first
N head lines: the raw `--log-failed` output is filtered to the lines matching
`ERROR`/`FAIL`/`Exception`/`Traceback` plus surrounding context, with non-adjacent windows
joined by an elision marker. This guarantees the failure tail is surfaced even when runner-setup
lines fill the head of the log. `log_lines` reports the filtered line count.
