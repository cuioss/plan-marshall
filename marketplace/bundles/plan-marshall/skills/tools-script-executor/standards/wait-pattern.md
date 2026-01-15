# Wait Pattern Specification

Synchronous polling utility for blocking until an async operation completes, inspired by the [Awaitility](http://www.awaitility.org/) JUnit library.

---

## Overview

The wait pattern provides a **synchronous blocking** mechanism that:
- Polls a condition until satisfied or timeout
- Returns immediately when condition is met (early return)
- Uses generous outer timeouts with configurable poll intervals
- Supports adaptive timeout learning from execution history

```
                    WAIT PATTERN FLOW

    ┌─────────────────────────────────────────────────────┐
    │                                                     │
    │   Caller (Skill/Script)                             │
    │   ┌───────────────────────────────────────────┐     │
    │   │  await_until(                             │     │
    │   │    condition = check_ci_status,           │     │
    │   │    timeout = 300s,                        │     │
    │   │    poll_interval = 30s                    │     │
    │   │  )                                        │     │
    │   └───────────────────────────────────────────┘     │
    │                       │                             │
    │                       ▼                             │
    │   ┌───────────────────────────────────────────┐     │
    │   │  Wait Utility (BLOCKS)                    │     │
    │   │                                           │     │
    │   │  ┌─────────────────────────────────────┐  │     │
    │   │  │ Poll Loop                           │  │     │
    │   │  │                                     │  │     │
    │   │  │  1. Call condition()                │  │     │
    │   │  │  2. If satisfied → RETURN SUCCESS   │  │     │
    │   │  │  3. If timeout → RETURN TIMEOUT     │  │     │
    │   │  │  4. Sleep(poll_interval)            │  │     │
    │   │  │  5. GOTO 1                          │  │     │
    │   │  │                                     │  │     │
    │   │  └─────────────────────────────────────┘  │     │
    │   └───────────────────────────────────────────┘     │
    │                       │                             │
    │                       ▼                             │
    │   ┌───────────────────────────────────────────┐     │
    │   │  Result: {status, duration, polls, data}  │     │
    │   └───────────────────────────────────────────┘     │
    │                                                     │
    └─────────────────────────────────────────────────────┘
```

---

## Two-Layer Timeout Concept

**Key Insight**: Claude's Bash tool has a **default 120-second timeout**. Long-running polling operations need two timeout layers:

1. **Outer timeout**: Bash tool's `timeout` parameter (prevents Claude from canceling the operation)
2. **Inner timeout**: await-until's adaptive timeout (controls actual polling duration)

```
                TWO-LAYER TIMEOUT ARCHITECTURE

    ┌─────────────────────────────────────────────────────────────┐
    │  Claude Bash Tool                                           │
    │  timeout: 600000ms (set via tool parameter)                 │
    │  ┌───────────────────────────────────────────────────────┐  │
    │  │  Shell timeout wrapper (generous safety net)          │  │
    │  │  timeout 600s python3 .plan/execute-script.py ...     │  │
    │  │  ┌─────────────────────────────────────────────────┐  │  │
    │  │  │  await-until (adaptive internal timeout)        │  │  │
    │  │  │  --command-key ci:pr_checks                     │  │  │
    │  │  │                                                 │  │  │
    │  │  │  Polls every 30s until success or timeout       │  │  │
    │  │  │  Timeout from run-config: ~180s (learned)       │  │  │
    │  │  └─────────────────────────────────────────────────┘  │  │
    │  └───────────────────────────────────────────────────────┘  │
    └─────────────────────────────────────────────────────────────┘

    Why two layers?
    - Outer (600s): Safety net - generous enough to never interfere
    - Inner (adaptive): Actual control - learned from execution history
```

**Note**: When using Bash tool, set `timeout` parameter to match shell timeout (e.g., `600000` for 600s).

---

## Design Principles

### 1. Synchronous Blocking

The wait utility **blocks the calling script** until:
- The condition is satisfied (success)
- The timeout is reached (timeout)
- An error occurs (failure)

This is intentional - the caller wants to wait for the operation to complete before proceeding.

### 2. Early Return

If the condition is satisfied on the first poll (or any subsequent poll), return immediately. Don't wait for the full timeout.

```
    Time ──────────────────────────────────────────────▶

    Timeout: 300s
    Poll interval: 30s

    ┌─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┐
    │ 0s  │ 30s │ 60s │ 90s │120s │150s │180s │...  │
    └──┬──┴──┬──┴──┬──┴─────┴─────┴─────┴─────┴─────┘
       │     │     │
       ▼     ▼     ▼
    PENDING PENDING SUCCESS ← Returns here (60s)
                             Not at 300s timeout
```

### 3. Generous Outer Timeout

The caller should provide a **generous timeout** that allows for:
- Normal operation completion
- Network delays
- Queue times
- Retry scenarios

The inner poll interval handles the "check frequently" aspect.

### 4. Condition Function

The condition is a **callable** that returns:
- `True` / `"success"` - condition satisfied, return immediately
- `False` / `"pending"` - not yet satisfied, continue polling
- `"failure"` - permanent failure, stop polling and return error

---

## State Machine

```
                        WAIT STATE MACHINE

    ┌──────────────────────────────────────────────────────────┐
    │                                                          │
    │                    ┌─────────┐                           │
    │                    │  START  │                           │
    │                    └────┬────┘                           │
    │                         │                                │
    │                         ▼                                │
    │                  ┌──────────────┐                        │
    │          ┌───────│   POLLING    │◀──────────┐            │
    │          │       └──────┬───────┘           │            │
    │          │              │                   │            │
    │          │              ▼                   │            │
    │          │       ┌──────────────┐           │            │
    │          │       │    CHECK     │           │            │
    │          │       │  CONDITION   │           │            │
    │          │       └──────┬───────┘           │            │
    │          │              │                   │            │
    │          │     ┌────────┼────────┐          │            │
    │          │     │        │        │          │            │
    │          │     ▼        ▼        ▼          │            │
    │          │  SUCCESS  PENDING  FAILURE       │            │
    │          │     │        │        │          │            │
    │          │     │        │        │          │            │
    │          │     │        ▼        │          │            │
    │          │     │  ┌──────────┐   │          │            │
    │          │     │  │ TIMEOUT? │   │          │            │
    │          │     │  └────┬─────┘   │          │            │
    │          │     │    NO │ YES     │          │            │
    │          │     │       │  │      │          │            │
    │          │     │       │  │      │          │            │
    │          │     │  ┌────┘  │      │          │            │
    │          │     │  │       │      │          │            │
    │          │     │  │       ▼      │          │            │
    │          │     │  │   ┌───────┐  │          │            │
    │          │     │  │   │TIMEOUT│  │          │            │
    │          │     │  │   └───┬───┘  │          │            │
    │          │     │  │       │      │          │            │
    │          │     │  │       │      │          │            │
    │          │     │  │ SLEEP │      │          │            │
    │          │     │  └───────┼──────┘          │            │
    │          │     │          │                 │            │
    │          │     │          └─────────────────┘            │
    │          │     │                                         │
    │          │     ▼                                         │
    │          │  ┌───────┐                                    │
    │          │  │SUCCESS│                                    │
    │          │  └───────┘                                    │
    │          │                                               │
    │          ▼                                               │
    │       ┌───────┐                                          │
    │       │FAILURE│                                          │
    │       └───────┘                                          │
    │                                                          │
    └──────────────────────────────────────────────────────────┘
```

---

## API Design (Awaitility-Style)

### Python Script API

```python
from await_util import await_until, ConditionResult

# Basic usage
result = await_until(
    condition=lambda: check_ci_status(pr_number),
    timeout_seconds=300,
    poll_interval_seconds=30,
    description="CI checks to pass"
)

# With condition result object
def check_build_status():
    status = get_build_status()
    if status == "success":
        return ConditionResult.success(data={"build_id": 123})
    elif status == "failed":
        return ConditionResult.failure(error="Build failed")
    else:
        return ConditionResult.pending(message="Build in progress")

result = await_until(
    condition=check_build_status,
    timeout_seconds=600,
    poll_interval_seconds=60
)
```

### CLI Script API

The CLI provides two modes: **explicit** (manual timeout/interval) and **adaptive** (managed via run-config).

**Important**: Always wrap in shell `timeout` as safety net for Claude's Bash tool.

```bash
# ADAPTIVE MODE (recommended): timeout/interval managed internally via run-config
# Outer shell timeout (600s) is safety net; inner adaptive timeout controls polling
timeout 600s python3 .plan/execute-script.py plan-marshall:tools-script-executor:await-until poll \
    --check-cmd "python3 .plan/execute-script.py plan-marshall:tools-integration-ci:github ci check-status --pr-number 123" \
    --success-field "status=success" \
    --failure-field "status=failure" \
    --command-key "ci:pr_checks"

# EXPLICIT MODE: manual timeout/interval (useful for one-off operations)
timeout 600s python3 .plan/execute-script.py plan-marshall:tools-script-executor:await-until poll \
    --check-cmd "python3 .plan/execute-script.py plan-marshall:tools-integration-ci:github ci check-status --pr-number 123" \
    --success-field "status=success" \
    --timeout 300 \
    --interval 30

# Wait for Sonar analysis completion
timeout 600s python3 .plan/execute-script.py plan-marshall:tools-script-executor:await-until poll \
    --check-cmd "python3 .plan/execute-script.py plan-marshall:tools-integration-ci:github sonar get-status --pr-number 123" \
    --success-field "qualityGate=OK" \
    --failure-field "qualityGate=ERROR" \
    --command-key "ci:sonar_analysis"
```

**Note**: When using Bash tool, set `timeout` parameter to `600000` (ms) to match shell timeout.

### Command-Key Naming Convention

The `--command-key` parameter identifies the operation in run-config for timeout learning:

| Key Pattern | Description | Example |
|-------------|-------------|---------|
| `ci:<operation>` | CI/CD operations | `ci:pr_checks`, `ci:sonar_analysis` |
| `build:<type>` | Build operations | `build:maven_verify`, `build:npm_test` |
| `deploy:<env>` | Deployment waits | `deploy:staging`, `deploy:production` |

The key is used to store/retrieve execution history in `run-configuration.json` under `commands.<key>`.

---

## Timeout Strategy

```
                    TIMEOUT HIERARCHY

    ┌─────────────────────────────────────────────────────────┐
    │                                                         │
    │  Caller Script (e.g., plan-finalize)                    │
    │  ┌───────────────────────────────────────────────────┐  │
    │  │                                                   │  │
    │  │  GENEROUS OUTER TIMEOUT: 600s (10 min)            │  │
    │  │  ┌───────────────────────────────────────────┐    │  │
    │  │  │                                           │    │  │
    │  │  │  await_until(timeout=600s, interval=30s)  │    │  │
    │  │  │                                           │    │  │
    │  │  │  Poll 1 (0s)    → PENDING                 │    │  │
    │  │  │  Poll 2 (30s)   → PENDING                 │    │  │
    │  │  │  Poll 3 (60s)   → PENDING                 │    │  │
    │  │  │  Poll 4 (90s)   → SUCCESS ← Early return  │    │  │
    │  │  │                                           │    │  │
    │  │  │  Actual duration: 90s (not 600s)          │    │  │
    │  │  │                                           │    │  │
    │  │  └───────────────────────────────────────────┘    │  │
    │  │                                                   │  │
    │  └───────────────────────────────────────────────────┘  │
    │                                                         │
    └─────────────────────────────────────────────────────────┘

    Key insight:
    - Outer timeout = maximum wait (generous, accounts for edge cases)
    - Poll interval = how often to check (frequent, for early return)
    - Actual duration = when condition is satisfied (usually much less)
```

### Recommended Timeout Values

| Operation | Timeout | Poll Interval | Rationale |
|-----------|---------|---------------|-----------|
| PR checks | 300s | 30s | CI typically completes in 2-5 min |
| Full pipeline | 900s | 60s | Complex builds may take longer |
| Sonar analysis | 180s | 20s | Usually quick, but queued |
| PR merge | 60s | 10s | Fast operation, quick feedback |

---

## Adaptive Timeout Learning

The wait utility delegates all timeout management to `run-config timeout get/set`. See [timeout-handling.md](../../run-config/standards/timeout-handling.md) for the algorithm specification.

```
                ADAPTIVE TIMEOUT LEARNING

    ┌────────────────────────────────────────────────────────┐
    │                                                        │
    │  Execution 1: PR Checks                                │
    │  ┌──────────────────────────────────────────────────┐  │
    │  │ Timeout: 300s (default)                          │  │
    │  │ Actual:  120s                                    │  │
    │  │ Status:  SUCCESS                                 │  │
    │  └──────────────────────────────────────────────────┘  │
    │                       │                                │
    │                       ▼                                │
    │  ┌──────────────────────────────────────────────────┐  │
    │  │ run-config timeout set --command-key ci:pr_checks│  │
    │  │              --duration 120                      │  │
    │  │                                                  │  │
    │  │ (run-config handles weighted update internally)  │  │
    │  └──────────────────────────────────────────────────┘  │
    │                       │                                │
    │                       ▼                                │
    │  Execution 2: PR Checks                                │
    │  ┌──────────────────────────────────────────────────┐  │
    │  │ run-config timeout get --command-key ci:pr_checks│  │
    │  │                                                  │  │
    │  │ (run-config handles safety margin internally)    │  │
    │  └──────────────────────────────────────────────────┘  │
    │                                                        │
    └────────────────────────────────────────────────────────┘
```

### Delegation to run-config

await-until uses subprocess calls to delegate timeout management:

```python
def get_adaptive_timeout(command_key: str) -> Optional[int]:
    """Get timeout via run-config timeout get."""
    result = subprocess.run([
        "python3", ".plan/execute-script.py",
        "plan-marshall:manage-run-config:run_config",
        "timeout", "get", "--command", command_key, "--default", "300"
    ], capture_output=True, text=True)
    # Returns plain number in seconds
    return int(result.stdout.strip())  # Clamped to 60s-600s bounds

def update_timeout(command_key: str, duration_sec: int) -> None:
    """Update timeout via run-config timeout set."""
    subprocess.run([
        "python3", ".plan/execute-script.py",
        "plan-marshall:manage-run-config:run_config",
        "timeout", "set", "--command", command_key,
        "--duration", str(duration_sec)
    ])
```

All margin and weighting logic is encapsulated in `run-config timeout`.

---

## Integration with run-config

When `--command-key` is provided, await-until delegates timeout management to `run-config timeout`:

1. **Before polling**: Calls `run-config timeout get` (returns timeout with safety margin)
2. **After completion**: Calls `run-config timeout set` (applies weighted update)

```
                CONFIG INTEGRATION

    ┌─────────────────────────────────────────────────────────┐
    │                                                         │
    │  await-until.py --command-key "ci:pr_checks"            │
    │                                                         │
    │  ┌───────────────────────────────────────────────────┐  │
    │  │ 1. run-config timeout get --command-key ci:...    │  │
    │  │    → Returns timeout with margin applied          │  │
    │  └───────────────────────────────────────────────────┘  │
    │                         │                               │
    │                         ▼                               │
    │  ┌───────────────────────────────────────────────────┐  │
    │  │ 2. Execute poll loop with adaptive timeout        │  │
    │  │    ... polling condition ...                      │  │
    │  │    Result: SUCCESS after 95s                      │  │
    │  └───────────────────────────────────────────────────┘  │
    │                         │                               │
    │                         ▼                               │
    │  ┌───────────────────────────────────────────────────┐  │
    │  │ 3. run-config timeout set --command-key ci:...    │  │
    │  │    --duration 95                                  │  │
    │  │    → run-config applies weighted update           │  │
    │  └───────────────────────────────────────────────────┘  │
    │                         │                               │
    │                         ▼                               │
    │  ┌───────────────────────────────────────────────────┐  │
    │  │ 4. Output result (TOON format)                    │  │
    │  │    status=success, duration_sec=95, ...            │  │
    │  └───────────────────────────────────────────────────┘  │
    │                                                         │
    └─────────────────────────────────────────────────────────┘
```

---

## Output Contract

Output uses TOON format (Tab-delimited Object Notation):

```
status	success
duration_sec	95
polls	4
timeout_used_sec	180
timeout_source	adaptive
command_key	ci:pr_checks
final_result.state	completed
final_result.conclusion	success
```

### Status Values

| Status | Description |
|--------|-------------|
| `success` | Condition satisfied within timeout |
| `timeout` | Timeout reached without condition being satisfied |
| `failure` | Permanent failure detected (check returned failure state) |

### Fields

| Field | Description |
|-------|-------------|
| `status` | Result status (success/timeout/failure) |
| `duration_sec` | Actual wait duration in seconds |
| `polls` | Number of condition checks performed |
| `timeout_used_sec` | Timeout value used (explicit or adaptive) in seconds |
| `timeout_source` | Source of timeout: `explicit`, `adaptive`, or `default` |
| `command_key` | The command key used (if adaptive mode) |
| `final_result.*` | Flattened fields from the last condition check |
| `error` | Error message (only present on failure) |

---

## Example: CI Wait Flow

```
                    CI WAIT EXAMPLE

    ┌─────────────────────────────────────────────────────────┐
    │                                                         │
    │  plan-finalize skill                                    │
    │  ┌───────────────────────────────────────────────────┐  │
    │  │ 1. Create PR                                      │  │
    │  │    gh pr create --title "..." --body "..."        │  │
    │  │    → PR 123 created                               │  │
    │  └───────────────────────────────────────────────────┘  │
    │                         │                               │
    │                         ▼                               │
    │  ┌───────────────────────────────────────────────────┐  │
    │  │ 2. Wait for CI                                    │  │
    │  │                                                   │  │
    │  │    await_until(                                   │  │
    │  │      condition=lambda: check_pr_status(123),      │  │
    │  │      timeout=300,                                 │  │
    │  │      interval=30                                  │  │
    │  │    )                                              │  │
    │  │                                                   │  │
    │  │    Poll 1 (0s):   "pending" - CI queued           │  │
    │  │    Poll 2 (30s):  "pending" - CI running          │  │
    │  │    Poll 3 (60s):  "pending" - CI running          │  │
    │  │    Poll 4 (90s):  "success" - CI passed! ✓        │  │
    │  │                                                   │  │
    │  │    → Returns immediately at 90s                   │  │
    │  └───────────────────────────────────────────────────┘  │
    │                         │                               │
    │                         ▼                               │
    │  ┌───────────────────────────────────────────────────┐  │
    │  │ 3. Continue with PR workflow                      │  │
    │  │    - Check for reviews                            │  │
    │  │    - Merge if approved                            │  │
    │  └───────────────────────────────────────────────────┘  │
    │                                                         │
    └─────────────────────────────────────────────────────────┘
```

---


## References

- [Awaitility](http://www.awaitility.org/) - Java DSL for synchronous testing
- [run-config SKILL.md](../../run-config/SKILL.md) - Execution history storage
