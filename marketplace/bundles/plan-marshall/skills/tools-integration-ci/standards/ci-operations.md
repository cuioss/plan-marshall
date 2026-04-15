# CI Operations

CI status checking, waiting, rerunning, and log retrieval.

---

## Workflow: Check CI Status

**Pattern**: Provider-Agnostic Router

Check CI status for a pull request.

### Step 1: Resolve and Execute

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci ci status \
    (--pr-number 123 | --head feature/x)
```

Supply exactly one of `--pr-number` or `--head`. The `--head` form is required when invoking
from the main checkout against a worktree-isolated plan branch — see
[pr-operations.md § Worktree-Isolated Plans](pr-operations.md#worktree-isolated-plans).

### Step 2: Process Result

```toon
status: success
operation: ci_status
pr_number: 123
overall_status: pending
elapsed_sec: 45

checks[3]{name,status,result,elapsed_sec,url,workflow}:
build	completed	success	120	https://github.com/org/repo/actions/runs/111	CI
test	in_progress	-	45	https://github.com/org/repo/actions/runs/112	CI
lint	completed	failure	30	https://github.com/org/repo/actions/runs/113	Lint
```

---

## Workflow: Wait for CI

**Pattern**: Polling with Timeout

Wait for CI checks to complete with two-layer timeout pattern. See [wait-pattern.md](../../tools-script-executor/standards/wait-pattern.md) for the full adaptive timeout architecture.

### Step 1: Execute with Timeout

Use outer shell timeout as safety net:

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci ci wait \
    --pr-number 123
```

**Bash tool timeout**: 1800000ms (30-minute safety net). Internal timeout managed by script.

### Step 2: Process Result

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

---

## Workflow: Rerun CI

**Pattern**: Provider-Agnostic Router

Rerun a failed CI workflow run.

### Step 1: Execute

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci ci rerun \
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
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci ci logs \
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
