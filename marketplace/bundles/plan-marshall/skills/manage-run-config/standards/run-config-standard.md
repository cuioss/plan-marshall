# Run Configuration Standard

JSON schema specification, timeout management, and warning handling for run configuration storage (via `file-operations-base` skill).

## Purpose

The run configuration file stores:
- Command execution history
- Adaptive timeout values for build commands
- Acceptable warnings and skip lists
- Maven build configurations

> **Note**: Lessons learned are stored separately via `manage-lessons` skill.

---

## Schema

```json
{
  "version": 1,
  "commands": {
    "<command-name>": {
      "last_execution": {
        "date": "2025-11-25",
        "status": "SUCCESS|FAILURE"
      },
      "skipped_files": ["file1.txt"],
      "skipped_directories": ["dir/"],
      "acceptable_warnings": [],
      "user_approved_permissions": []
    }
  },
  "maven": {
    "acceptable_warnings": {
      "transitive_dependency": [],
      "plugin_compatibility": [],
      "platform_specific": []
    }
  },
  "architecture_refresh": {
    "tier_0": "enabled",
    "tier_1": "prompt"
  }
}
```

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| version | integer | Schema version (currently 1) |
| commands | object | Command-specific configurations |

### Optional Sections

| Section | Purpose |
|---------|---------|
| maven | Maven build configurations |
| architecture_refresh | Tier knobs consumed by the `phase-6-finalize` `architecture-refresh` step |

---

## Commands Section

Each command entry can have:

| Field | Type | Description |
|-------|------|-------------|
| last_execution | object | Most recent execution details |
| timeout_seconds | integer | Learned timeout value in seconds |
| acceptable_warnings | array | Warning patterns to ignore |
| skipped_files | array | Files to skip in processing |
| skipped_directories | array | Directories to skip |
| user_approved_permissions | array | Permissions approved by user |

### last_execution Fields

| Field | Type | Description |
|-------|------|-------------|
| date | string | ISO date of execution |
| status | string | SUCCESS, FAILURE, or TIMEOUT |
| duration_ms | integer | Execution duration in milliseconds (optional, used for adaptive timeouts) |

### Command-Key Naming Convention

Command keys support namespaced naming for organized storage:

| Key Pattern | Description | Example |
|-------------|-------------|---------|
| `ci:<operation>` | CI/CD operations | `ci:pr_checks`, `ci:sonar_analysis` |
| `build:<type>` | Build operations | `build:maven_verify`, `build:npm_test` |
| `deploy:<env>` | Deployment waits | `deploy:staging`, `deploy:production` |

The `duration_ms` field enables adaptive timeout learning. The `await_until` script uses previous execution durations to calculate appropriate timeouts for polling operations.

### JSON Path Access

Use dot notation for field access:

| Path | Access |
|------|--------|
| `commands` | All commands |
| `commands.my-cmd` | Specific command |
| `commands.my-cmd.last_execution.date` | Execution date |
| `commands.my-cmd.skipped_files[0]` | First skipped file |
| `maven.acceptable_warnings` | Maven warnings |

---

## Maven Section

Maven acceptable warnings configuration.

| Field | Type | Description |
|-------|------|-------------|
| acceptable_warnings | object | Warning patterns by category |

### acceptable_warnings Categories

| Category | Description |
|----------|-------------|
| transitive_dependency | Dependency-related warnings |
| plugin_compatibility | Plugin compatibility warnings |
| platform_specific | Platform-specific warnings |

---

## Architecture-Refresh Section

The `architecture_refresh` section holds two enum knobs consumed by the `phase-6-finalize` `architecture-refresh` step. The section is optional — defaults are applied transparently when the section (or any individual field) is missing. `init` does not need to materialise the section for queries to succeed.

### Schema

| Field | Type | Allowed Values | Default | Description |
|-------|------|----------------|---------|-------------|
| `tier_0` | string (enum) | `enabled`, `disabled` | `enabled` | Controls the deterministic `architecture discover --force` + `diff-modules --pre` step. When `disabled`, the entire architecture-refresh finalize step exits early. |
| `tier_1` | string (enum) | `prompt`, `auto`, `disabled` | `prompt` | Controls LLM re-enrichment after Tier 0 detects affected modules. `prompt` (default) asks the user via AskUserQuestion; `auto` runs re-enrichment unattended; `disabled` only commits the deterministic refresh and notes the module list in the PR body. |

### Example — Section After `set-tier-0 --value disabled`

After invoking `architecture-refresh set-tier-0 --value disabled` against a fresh project (no prior `architecture_refresh` section), the persisted JSON looks like:

```json
{
  "version": 1,
  "commands": {},
  "architecture_refresh": {
    "tier_0": "disabled"
  }
}
```

Notes:
- `tier_1` is omitted because it was never set; subsequent `get-tier-1` calls return the default `prompt`.
- `set-tier-1 --value auto` would extend the section to `{"tier_0": "disabled", "tier_1": "auto"}`.

### Operations

| Subcommand | Purpose |
|------------|---------|
| `architecture-refresh get-tier-0` | Read `tier_0` (returns `enabled` if section absent) |
| `architecture-refresh set-tier-0 --value VALUE` | Persist `tier_0` after enum validation |
| `architecture-refresh get-tier-1` | Read `tier_1` (returns `prompt` if section absent) |
| `architecture-refresh set-tier-1 --value VALUE` | Persist `tier_1` after enum validation |

Invalid `--value` arguments produce the standard `invalid_value` error response with an `allowed: [...]` list.

---

## Timeout Management

Adaptive timeout management for **synchronous command execution** (Maven, npm, Gradle builds), enabling learned timeout values based on historical execution data.

### Two-Layer Timeout Concept

**Key Insight**: Claude's Bash tool has a **default 120-second timeout**. Long-running builds need two timeout layers:

1. **Outer timeout**: Bash tool's `timeout` parameter (prevents Claude from canceling the operation)
2. **Inner timeout**: Shell `timeout` command (controls actual execution)

```
                TWO-LAYER TIMEOUT ARCHITECTURE

    +-------------------------------------------------------------+
    |  Claude Bash Tool                                           |
    |  timeout: INNER + 30 seconds                                |
    |  +-------------------------------------------------------+  |
    |  |  Shell timeout (inner, from run-config)               |  |
    |  |  timeout ${TIMEOUT}s mvn verify                       |  |
    |  |  +---------------------------------------------+  |  |
    |  |  |  Actual command execution                       |  |  |
    |  |  |  mvn verify                                     |  |  |
    |  |  +---------------------------------------------+  |  |
    |  +-------------------------------------------------------+  |
    +-------------------------------------------------------------+

    Why two layers?
    - Outer: Prevents Claude from canceling (must be > inner)
    - Inner: Actual control from run-config (adaptive learning)
```

**Note**: When using Bash tool, set `timeout` parameter to `TIMEOUT + 30` seconds to ensure outer > inner.

### Timeout Behavior

- **Safety margin on retrieval**: Persisted timeout values are multiplied by a safety buffer when read, accounting for execution variance
- **Adaptive learning on update**: When updating with a new duration, the algorithm weights towards the higher value for reliability
- **Minimum floor**: A minimum timeout (currently 120s) prevents unreasonably short timeouts -- JVM-based tools have cold startup times (30-90s) that warm-run measurements miss

Implementation constants are defined in `manage_run_config.py`. See the script source for exact values.

**Flow**: `timeout get` -> execute with shell timeout -> record duration -> `timeout set` (adaptive learning)

### Timeout API

#### Get Timeout

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

#### Set Timeout

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

### Timeout Storage

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

### Weighting Algorithm

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
| 240 | 180 | 240 | 180 | 0.8x240 + 0.2x180 = 228 |
| 180 | 240 | 240 | 180 | 0.8x240 + 0.2x180 = 228 |
| 300 | 300 | 300 | 300 | 0.8x300 + 0.2x300 = 300 |
| 100 | 500 | 500 | 100 | 0.8x500 + 0.2x100 = 420 |

**Rationale**: Operations occasionally complete faster (network conditions, caching, etc.) but rarely exceed the worst-case time. Weighting towards higher values prevents premature timeouts.

### Integration with await_until

The timeout subcommand complements `await_until.py` from `script-executor`:

```bash
# Get learned timeout (or default) - outputs plain number
TIMEOUT=$(python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config timeout get \
  --command "ci:pr_checks" --default 300)

# Use in await_until with outer shell timeout as safety net
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci ci wait \
  --pr-number 123 \
  --timeout "$TIMEOUT" \
  --interval 30

# Record actual duration for learning
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config timeout set \
  --command "ci:pr_checks" --duration 180
```

> **Note**: `await_until.py` has built-in adaptive timeout support via `--command-key`. This API provides an alternative for scripts that need explicit timeout control. When using Bash tool, set `timeout` parameter to `600` seconds.

### Polling Operations (Corner Case)

For **async polling** (CI checks, Sonar analysis), use `await_until --command-key` instead. It handles timeout internally with a generous external timeout as circuit breaker:

```bash
# await_until manages timeout internally via run-config
# External timeout (600s) is just a safety net
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci ci wait \
  --pr-number 123
```

**Key difference from synchronous builds**:
- **Synchronous builds**: Two timeout layers with adaptive inner (shell `timeout` + Bash tool `timeout` parameter)
- **Polling operations**: Two timeout layers with generous outer as safety net (600s external + internal adaptive)

**Note**: When using Bash tool for polling, set `timeout` parameter to `600` seconds to match shell timeout.

---

## Warning Management

Manage acceptable warnings that should be filtered from build output. Build scripts use this configuration to distinguish actionable warnings from known/accepted ones. Patterns stored here are used to filter build output in `--mode actionable`.

### Warning Categories

| Category | Description |
|----------|-------------|
| `transitive_dependency` | Dependency management warnings about transitive dependencies |
| `plugin_compatibility` | Maven/Gradle plugin version compatibility warnings |
| `platform_specific` | Platform-specific warnings (e.g., Windows vs Unix paths) |

### Warning Operations

#### Add Warning Pattern

Add a pattern to the acceptable warnings list:

```bash
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config warning add \
  --category transitive_dependency \
  --pattern "uses transitive dependency"
```

**Options:**
- `--category` - Warning category (required)
- `--pattern` - Pattern to match in warning messages (required)
- `--build-system` - Build system (default: maven)
- `--project-dir` - Project directory (default: current)

**Output (JSON):**
```json
{
  "success": true,
  "action": "added",
  "category": "transitive_dependency",
  "pattern": "uses transitive dependency",
  "build_system": "maven"
}
```

#### List Warning Patterns

List all acceptable warning patterns:

```bash
# List all categories
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config warning list

# List specific category
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config warning list \
  --category transitive_dependency
```

**Output (JSON):**
```json
{
  "success": true,
  "build_system": "maven",
  "categories": {
    "transitive_dependency": ["pattern1", "pattern2"],
    "plugin_compatibility": [],
    "platform_specific": []
  }
}
```

#### Remove Warning Pattern

Remove a pattern from the acceptable warnings list:

```bash
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config warning remove \
  --category transitive_dependency \
  --pattern "uses transitive dependency"
```

**Output (JSON):**
```json
{
  "success": true,
  "action": "removed",
  "category": "transitive_dependency",
  "pattern": "uses transitive dependency",
  "build_system": "maven"
}
```

### Usage in Build Scripts

Build scripts with `--mode actionable` filter warnings matching patterns in `acceptable_warnings`:

```bash
# Run build with actionable mode (default) - filters accepted warnings
python3 .plan/execute-script.py plan-marshall:build-maven:maven run \
  --targets "clean verify" --mode actionable

# Run with structured mode - shows all warnings with [accepted] markers
python3 .plan/execute-script.py plan-marshall:build-maven:maven run \
  --targets "clean verify" --mode structured
```

### Warning Storage

Warning patterns are stored in `run-configuration.json`:

```json
{
  "maven": {
    "acceptable_warnings": {
      "transitive_dependency": ["pattern1", "pattern2"],
      "plugin_compatibility": [],
      "platform_specific": []
    }
  }
}
```

---

## Cleanup Operations

Clean temporary files, logs, archived plans, and memory based on retention settings.

### Default Retention

Retention defaults are defined in `manage-config/standards/data-model.md` under `system.retention`. Refer to that standard for the canonical table of retention fields, types, and default values.

### Cleaned Directories

| Directory | Content |
|-----------|---------|
| `.plan/logs/` | Execution logs |
| `.plan/archived/` | Archived plan files |
| `.plan/memory/` | Memory/context files |
| `.plan/temp/` | Temporary files (always cleaned) |

---

## Full Example

```json
{
  "version": 1,
  "commands": {
    "setup-project-permissions": {
      "last_execution": {
        "date": "2025-11-25",
        "status": "SUCCESS"
      },
      "user_approved_permissions": []
    },
    "docs-technical-adoc-review": {
      "last_execution": {
        "date": "2025-11-24",
        "status": "SUCCESS"
      },
      "skipped_files": ["CHANGELOG.adoc"],
      "skipped_directories": ["target/", "node_modules/"],
      "acceptable_warnings": []
    },
    "ci:pr_checks": {
      "last_execution": {
        "date": "2025-12-17",
        "duration_ms": 95000,
        "status": "SUCCESS"
      }
    },
    "build:maven_verify": {
      "timeout_seconds": 240,
      "last_execution": {
        "date": "2025-12-17",
        "duration_seconds": 180,
        "status": "SUCCESS"
      }
    }
  },
  "maven": {
    "acceptable_warnings": {
      "transitive_dependency": [],
      "plugin_compatibility": [],
      "platform_specific": []
    }
  },
  "architecture_refresh": {
    "tier_0": "enabled",
    "tier_1": "prompt"
  }
}
```

---

## References

- [wait-pattern.md](../../tools-script-executor/standards/wait-pattern.md) - Awaitility-style synchronous wait
