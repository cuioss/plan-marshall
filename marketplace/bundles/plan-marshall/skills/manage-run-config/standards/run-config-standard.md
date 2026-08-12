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
  },
  "ci_durations": {
    "<command-name>": [420, 380, 455]
  },
  "language_servers": {
    "python": {"enabled": true, "command": ["pyright-langserver", "--stdio"], "language_id": "python"}
  },
  "display_timezone": "UTC"
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
| ci_durations | Bounded rolling window of observed successful CI-run durations (keyed by command) seeding the adaptive CI-wait first-sleep via `p50` |
| language_servers | Machine-local binding of a language to its locally-installed language server, read by the `lsp-client` skill |
| display_timezone | Display-only IANA zone name (default `UTC`) consumed at rendering surfaces to convert stored UTC timestamps for human reading; never consulted on a write or compare path |

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

## CI-Duration Section

The `ci_durations` section holds a bounded rolling window of observed **successful** CI-run durations, keyed by command (mirroring the `commands` keyed shape). It seeds the adaptive CI-wait first-sleep: the median (`p50`) of a key's window is how many seconds the CI-wait sleeps before it begins polling, so a run whose CI historically takes ~7 min does not poll from second zero. The section is optional — a missing or empty window yields a `null` seed and the consumer skips the sleep. Durations are persisted in the main-anchored `run-configuration.json`, so reads/writes resolve against the main checkout regardless of caller cwd.

### Schema

| Field | Type | Description |
|-------|------|-------------|
| `ci_durations.<command>` | array[int] | Bounded rolling window (newest last) of observed successful CI-run durations in seconds for the command key. Bounded to the newest `CI_DURATION_WINDOW_SIZE` (default 5) entries; `record` evicts the oldest on overflow. |

### Operations

| Subcommand | Purpose |
|------------|---------|
| `ci-duration record --command KEY --duration SECONDS` | Append an observed successful CI-run duration to the key's window, evicting the oldest beyond `CI_DURATION_WINDOW_SIZE` |
| `ci-duration p50 --command KEY` | Return the median of the key's window as `p50_seconds` (the first-sleep seed); `p50_seconds: null` when the window is empty or absent |

For an odd-sized window `p50_seconds` is the middle observed duration; for an even-sized window it is the mean of the two middle values. `CI_DURATION_WINDOW_SIZE` is defined in `run_config.py`; see the script source for the exact value.

Producer: the CI-wait handlers (`_github_ci`, `gitlab_ops`) record a duration on natural (non-timeout) completion. Consumer: the same handlers read `p50` to seed the CI-wait first-sleep.

---

## Language-Servers Section

The `language_servers` section binds a language to its locally-installed language server. It is read by the [`lsp-client`](../../lsp-client/SKILL.md) skill, which a `phase-5-execute` leaf uses for opt-in symbol lookup and verified edits. The section is **machine-local**: a language server is locally-installed tooling that differs per machine, so the binding lives in the git-ignored run-configuration store rather than in a version-controlled project file. It is the shared configuration surface the resolver-configuration work extends — not a parallel store.

The section is optional. An absent language, or one with `enabled: false`, is treated by `lsp-client` as *not configured*: the client degrades to the `Read` / `Edit` path, so a project that never configures a server loses nothing.

### Schema

| Field | Type | Description |
|-------|------|-------------|
| `language_servers.<language>.enabled` | boolean | Whether the binding is active. Absent defaults to `true`; `false` opts the language out without discarding its command. |
| `language_servers.<language>.command` | array[string] | The server invocation as an argv list (e.g. `["pyright-langserver", "--stdio"]`). Machine-specific. |
| `language_servers.<language>.language_id` | string | The LSP `languageId` sent on `didOpen` (defaults to `<language>`). |

### Operations

| Subcommand | Purpose |
|------------|---------|
| `language-server get --language <lang>` | Read the binding (`configured: false` when absent) |
| `language-server set --language <lang> --command <json-array> [--language-id <id>] [--disabled]` | Persist the binding (`--command` is a JSON array of strings) |
| `language-server list` | List configured language keys |
| `language-server remove --language <lang>` | Remove the binding |

```bash
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config language-server set \
  --language python --command '["pyright-langserver", "--stdio"]' --language-id python
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config language-server get \
  --language python
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config language-server list
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config language-server remove \
  --language python
```

---

## Display-Timezone Section

The `display_timezone` field is a single top-level IANA zone name (default `UTC`). It is a **display-only** setting: it is resolved at rendering surfaces to convert a stored UTC timestamp into the operator's chosen zone for human reading, and is **never** consulted on a write or compare path. Storage and comparison stay UTC unconditionally — a stored timestamp is byte-identical under any `display_timezone` value.

The default `UTC` makes the unset behaviour byte-identical to the pre-knob rendering: no existing artifact changes unless the operator opts in. Every rendered timestamp that is actually converted (a non-UTC zone) carries an unambiguous zone label of the form `ABBREV (UTC±HH:MM)`, so both the zone and the exact instant are recoverable; an unlabelled converted timestamp is never emitted.

### Schema

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `display_timezone` | string (IANA zone name) | `UTC` | The display-only render timezone. An absent field, a non-string value, or a stored zone that no longer loads all resolve to `UTC`. |

### Operations

| Subcommand | Purpose |
|------------|---------|
| `display-timezone get` | Read `display_timezone` (returns `UTC` when absent or unreadable) |
| `display-timezone set --value ZONE` | Persist `display_timezone` after IANA-name validation |

A `--value` that is not a loadable IANA zone produces the standard `invalid_value` error response and persists nothing.

```bash
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config display-timezone get
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config display-timezone set \
  --value America/New_York
```

### Boundary — display versus storage

The knob reaches rendering surfaces exclusively. The write and compare paths (record `created`/`removed_at`/`set_at` fields, lesson identifier prefixes, retention and quiet-window cutoffs, CI/build durations, staleness checks, and ordering keys) stay UTC unconditionally. This boundary is enforced by a guard test that scans the bundles and fails if any store/compare site consults `display_timezone`.

---

## Timeout Management

Adaptive timeout management for **synchronous command execution** (Maven, npm, Gradle builds), enabling learned timeout values based on historical execution data.

### Two-Layer Timeout Concept

**Key Insight**: the host platform's Bash tool has a **default 120-second timeout**. Long-running builds need two timeout layers:

1. **Outer timeout**: Bash tool's `timeout` parameter (prevents the host platform from canceling the operation)
2. **Inner timeout**: Shell `timeout` command (controls actual execution)

```text
                TWO-LAYER TIMEOUT ARCHITECTURE

    +-------------------------------------------------------------+
    |  Host platform Bash tool                                    |
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
    - Outer: Prevents the host platform from canceling (must be > inner)
    - Inner: Actual control from run-config (adaptive learning)
```

**Note**: When using Bash tool, set `timeout` parameter to `TIMEOUT + 30` seconds to ensure outer > inner.

### Timeout Behavior

- **Explicit override wins over the learned value**: An explicitly-supplied bound (`--explicit` on the CLI, `--timeout` on a build `run`) is a true override of the persisted learned value — it binds outright, and no learned value can reduce it. This is the only path that ignores the persisted value; it exists so a caller who knows a command needs longer cannot be silently capped by a shorter learned value.
- **Safety margin on retrieval**: On the no-override path, persisted timeout values are multiplied by a safety buffer when read, accounting for execution variance. Adaptive learning is unchanged on this path.
- **Adaptive learning on update**: When updating with a new duration, the algorithm weights towards the higher value for reliability
- **Minimum floor**: A minimum timeout (currently 120s) prevents unreasonably short timeouts -- JVM-based tools have cold startup times (30-90s) that warm-run measurements miss. The floor binds on **both** paths: an explicit override does not waive it, because the floor protects against under-specification. Build engines layer their own, higher floor on top (see each engine's declared `min_timeout`).

Implementation constants are defined in `run_config.py`. See the script source for exact values.

**Flow**: `timeout get` -> execute with shell timeout -> record duration -> `timeout set` (adaptive learning)

### Timeout API

#### Get Timeout

Retrieve timeout for a command, either from an explicit override or from the learned value with default fallback. Returns plain number (seconds).

```bash
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config timeout get \
  --command "build:maven_verify" \
  --default 300
```

Override the learned value with an explicit bound:

```bash
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config timeout get \
  --command "build:maven_verify" \
  --default 300 \
  --explicit 1800
```

**Parameters**:

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--command` | Yes | Command identifier (e.g., `build:maven_verify`) |
| `--default` | Yes | Default timeout in seconds if no persisted value |
| `--explicit` | No | Explicit timeout in seconds that overrides the persisted learned value |

**Logic**:
1. If `--explicit` is supplied: return the higher of it and the minimum floor — the persisted value is not consulted
2. Otherwise, look up `commands.<command>.timeout_seconds` in run-configuration.json
3. If not found: use `--default` value
4. If found: apply safety margin to persisted value
5. Return the higher of the calculated value or the minimum floor

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
```text
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

### What `timeout_seconds` actually measures — and what it does not

The persisted `timeout_seconds` is **not** a model of how long a command takes.
Reading it as one leads to a specific, reproducible surprise: **a command can
exceed its budget while a STRICT SUPERSET of that command completes well inside
its own.** That is not a bug in either budget; it follows from three properties
of the design, and a reader who does not hold all three will misdiagnose it.

**1. The field holds two different quantities, with nothing to tell them apart.**
The success path persists a *measured duration*; the timeout path persists a
*doubled budget* (`min(timeout_used * 2, MAX_TIMEOUT)`). Both land in
`timeout_seconds`, and `timeout_get` applies the `1.25` safety margin to whichever
it finds. So the same field means "what this took" on one key and "what we last
allowed it" on another, and the retrieval cannot distinguish them.

**2. The budget therefore tracks the key's TIMEOUT HISTORY, not the command's
work.** A key that has only ever succeeded settles near `1.25 x measured`, floored
at the tool's `min_timeout`. A key that has timed out once jumps to
`1.25 x (2 x previous budget)` and doubles again on each further timeout, up to
`MAX_TIMEOUT`. Two keys ratchet independently, so **nothing in the design makes
`budget(subset) <= budget(superset)`** — the ordering across keys is decided by
which key happened to time out first, not by which command does more work.

**3. Keys are per-argument-string, and the string does not encode cache state.**
`quality-gate` and `quality-gate plan-marshall` are separate keys with separate
histories (see the cold-start note in
[`../../extension-api/standards/build-execution.md`](../../extension-api/standards/build-execution.md)).
Neither key records whether the run that taught it was cold or warm, yet the
difference is first-order: a measured whole-tree `verify` over 19 231 tests
completed in 444 s warm while a scoped `module-tests` subset of 16 154 tests took
489 s cold — the subset ran **longer** than the superset containing it, on 3 077
fewer tests, purely on cache state.

**The consequence for a caller.** A budget overrun is evidence about the KEY, not
about the command — so a timeout does not mean the command got slower, and
certainly does not mean the tree is broken. **Do not "fix" an inversion by
raising the budget**: the raise closes the symptom, and the next inversion
appears on whichever key has not yet ratcheted. Diagnose which of the three
properties above produced it first.

**What the learner is fed.** Only a genuine finish updates the persisted value. A
run whose child was **externally killed** reports an elapsed that is a truncation
of work that never completed, so `_build_execute` deliberately does NOT call
`timeout_set` on that path — blending a non-measurement in at 20 % weight would
launder a figure of unknown sign into the budget that decides the next kill.

### Integration with await_until

The timeout subcommand complements `await_until.py` from `script-executor`:

```bash
# Get learned timeout (or default) - outputs plain number
python3 .plan/execute-script.py plan-marshall:manage-run-config:run_config timeout get \
  --command "ci:pr_checks" --default 300
```

Capture the numeric output as `{TIMEOUT}` and substitute it into the next call.

```bash
# Use in await_until with outer shell timeout as safety net
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci checks wait \
  --pr-number 123 \
  --timeout "{TIMEOUT}" \
  --interval 30
```

After the wait completes, record the actual duration so the learner can refine future estimates:

```bash
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
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci checks wait \
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
- `--plan-id` - Plan identifier — auto-resolves the worktree path via `manage-status get-worktree-path`. Mutually exclusive with `--project-dir`.
- `--project-dir` - Project directory (default: current). Escape hatch / explicit override; mutually exclusive with `--plan-id`.

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
  --command-args "clean verify" --mode actionable

# Run with structured mode - shows all warnings with [accepted] markers
python3 .plan/execute-script.py plan-marshall:build-maven:maven run \
  --command-args "clean verify" --mode structured
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
  },
  "ci_durations": {
    "ci:wait": [420, 380, 455]
  }
}
```

---

## References

- [wait-pattern.md](../../tools-script-executor/standards/wait-pattern.md) - Awaitility-style synchronous wait
