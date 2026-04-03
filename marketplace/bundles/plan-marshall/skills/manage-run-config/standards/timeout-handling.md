# Timeout Handling Specification

Adaptive timeout management for **synchronous command execution** (Maven, npm, Gradle builds), enabling learned timeout values based on historical execution data.

---

## Two-Layer Timeout Concept

**Key Insight**: Claude's Bash tool has a **default 120-second timeout**. Long-running builds need two timeout layers:

1. **Outer timeout**: Bash tool's `timeout` parameter (prevents Claude from canceling the operation)
2. **Inner timeout**: Shell `timeout` command (controls actual execution)

```
                TWO-LAYER TIMEOUT ARCHITECTURE

    ┌─────────────────────────────────────────────────────────────┐
    │  Claude Bash Tool                                           │
    │  timeout: INNER + 30 seconds                                │
    │  ┌───────────────────────────────────────────────────────┐  │
    │  │  Shell timeout (inner, from run-config)               │  │
    │  │  timeout ${TIMEOUT}s mvn verify                       │  │
    │  │  ┌─────────────────────────────────────────────────┐  │  │
    │  │  │  Actual command execution                       │  │  │
    │  │  │  mvn verify                                     │  │  │
    │  │  └─────────────────────────────────────────────────┘  │  │
    │  └───────────────────────────────────────────────────────┘  │
    └─────────────────────────────────────────────────────────────┘

    Why two layers?
    - Outer: Prevents Claude from canceling (must be > inner)
    - Inner: Actual control from run-config (adaptive learning)
```

**Note**: When using Bash tool, set `timeout` parameter to `TIMEOUT + 30` seconds to ensure outer > inner.

---

## Overview

The timeout handling system provides:
- **Retrieval with defaults**: Get timeout for a command with fallback to default value
- **Safety margin**: Apply buffer to persisted values to account for variance
- **Adaptive learning**: Update timeouts weighted towards longer durations for reliability

**Primary use case**: Synchronous builds where shell `timeout` is the single timeout mechanism.

**Flow**: `timeout get` → execute with shell timeout → record duration → `timeout set` (adaptive learning)

---

## Behavior

- **Safety margin on retrieval**: Persisted timeout values are multiplied by a safety buffer when read, accounting for execution variance
- **Adaptive learning on update**: When updating with a new duration, the algorithm weights towards the higher value for reliability
- **Minimum floor**: A minimum timeout (currently 120s) prevents unreasonably short timeouts — JVM-based tools have cold startup times (30-90s) that warm-run measurements miss

Implementation constants are defined in `manage_run_config.py`. See the script source for exact values.

---

## API Design

### Get Timeout

Retrieve timeout for a command with default fallback. Returns plain number (seconds).

```bash
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config timeout get \
  --command "build:maven_verify" \
  --default 300
```

**Parameters**:

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--command` | Yes | Command identifier (e.g., `build:maven_verify`) |
| `--default` | Yes | Default timeout in seconds if no persisted value |

**Logic**:
1. Look up `commands.<command>.timeout_seconds` in run-configuration.json
2. If not found: use `--default` value
3. If found: apply safety margin to persisted value
4. Return the higher of the calculated value or the minimum floor

**Output**: Plain number (e.g., `300`)

### Set Timeout

Update timeout for a command with adaptive weighting.

```bash
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config timeout set \
  --command "build:maven_verify" \
  --duration 180
```

**Parameters**:

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--command` | Yes | Command identifier (e.g., `build:maven_verify`) |
| `--duration` | Yes | Observed duration in seconds |

**Logic**:
1. Look up existing `commands.<command>.timeout_seconds`
2. If not found: write `--duration` directly
3. If found: compute weighted average favoring the higher value for reliability

**Output** (TOON format):
```
status	success
command	build:maven_verify
timeout_seconds	228
previous_seconds	240
source	computed|initial
```

---

## Storage Format

> **Schema reference**: See `standards/run-config-format.md` for the complete storage schema.

Timeouts are stored in `run-configuration.json` under the command entry:

```json
{
  "version": 1,
  "commands": {
    "build:maven_verify": {
      "timeout_seconds": 240,
      "last_execution": {
        "date": "2025-12-17",
        "duration_seconds": 180,
        "status": "SUCCESS"
      }
    }
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `timeout_seconds` | integer | Learned timeout value in seconds |

---

## Weighting Algorithm

The update algorithm is **biased towards higher values** to ensure reliability:

```python
def compute_weighted_timeout(existing: int, new_duration: int) -> int:
    """Compute weighted timeout favoring higher value."""
    HIGHER_WEIGHT = 0.80

    higher = max(existing, new_duration)
    lower = min(existing, new_duration)

    return int(HIGHER_WEIGHT * higher + (1 - HIGHER_WEIGHT) * lower)
```

**Examples**:

| Existing | New | Higher | Lower | Result |
|----------|-----|--------|-------|--------|
| 240 | 180 | 240 | 180 | 0.8×240 + 0.2×180 = 228 |
| 180 | 240 | 240 | 180 | 0.8×240 + 0.2×180 = 228 |
| 300 | 300 | 300 | 300 | 0.8×300 + 0.2×300 = 300 |
| 100 | 500 | 500 | 100 | 0.8×500 + 0.2×100 = 420 |

**Rationale**: Operations occasionally complete faster (network conditions, caching, etc.) but rarely exceed the worst-case time. Weighting towards higher values prevents premature timeouts.

---

## Integration with await_until

The timeout subcommand complements `await_until.py` from `script-executor`:

```bash
# Get learned timeout (or default) - outputs plain number
TIMEOUT=$(python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config timeout get \
  --command "ci:pr_checks" --default 300)

# Use in await_until with outer shell timeout as safety net
timeout 600s python3 .plan/execute-script.py plan-marshall:tools-script-executor:await_until poll \
  --check-cmd "gh pr checks 123 --json state" \
  --success-field "status=success" \
  --timeout "$TIMEOUT" \
  --interval 30

# Record actual duration for learning
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config timeout set \
  --command "ci:pr_checks" --duration 180
```

> **Note**: `await_until.py` has built-in adaptive timeout support via `--command-key`. This API provides an alternative for scripts that need explicit timeout control. When using Bash tool, set `timeout` parameter to `600` seconds.

---

## Polling Operations (Corner Case)

For **async polling** (CI checks, Sonar analysis), use `await_until --command-key` instead. It handles timeout internally with a generous external timeout as circuit breaker:

```bash
# await_until manages timeout internally via run-config
# External timeout (600s) is just a safety net
timeout 600s python3 .plan/execute-script.py plan-marshall:tools-script-executor:await_until poll \
  --check-cmd "gh pr checks 123 --json state" \
  --success-field "state=completed" \
  --command-key "ci:pr_checks"
```

**Key difference from synchronous builds**:
- **Synchronous builds**: Two timeout layers with adaptive inner (shell `timeout` + Bash tool `timeout` parameter)
- **Polling operations**: Two timeout layers with generous outer as safety net (600s external + internal adaptive)

**Note**: When using Bash tool for polling, set `timeout` parameter to `600` seconds to match shell timeout.

---

## References

- [run-config-format.md](../standards/run-config-format.md) - Complete schema documentation
- [wait-pattern.md](../../script-executor/standards/wait-pattern.md) - Awaitility-style synchronous wait
