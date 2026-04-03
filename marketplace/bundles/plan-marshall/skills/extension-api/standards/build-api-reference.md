# Build API Reference

Shared subcommand documentation for all build skills. Each build skill (Maven, Gradle, npm, Python) implements these subcommands through the unified build framework. Tool-specific deviations are documented in each skill's SKILL.md.

For execution contract details (input/output fields, lifecycle, format specs), see `build-execution.md`.
For common standards (timeouts, log handling, acceptable warnings), see `build-systems-common.md`.

---

## Enforcement (All Build Skills)

**Execution mode**: Run scripts exactly as documented; parse TOON output for status and route accordingly.

**Prohibited actions:**
- Do not invoke build tools directly; all builds go through the script API
- Do not invent script arguments not listed in the subcommand documentation
- Do not bypass wrapper detection logic

**Constraints:**
- All commands use `python3 .plan/execute-script.py {bundle}:{skill}:{script} {subcommand} {args}`
- Output format defaults to TOON; use `--format json` only when explicitly required (e.g., programmatic parsing by scripts, CI pipeline integration)
- Always analyze the result TOON: check `status` for success/error/timeout, review `errors` for failures

---

## Subcommands

All build skills share these subcommands. Availability per tool:

| Subcommand | Maven | Gradle | npm | Python | Purpose |
|------------|-------|--------|-----|--------|---------|
| `run` | Yes | Yes | Yes | Yes | Execute build and auto-parse on failure (primary API) |
| `parse` | Yes | Yes | Yes | Yes | Parse build output from log file |
| `coverage-report` | Yes | Yes | Yes | Yes | Parse coverage report |
| `check-warnings` | Yes | Yes | Yes | Yes | Categorize build warnings against acceptable patterns |
| `discover` | Yes | Yes | Yes | Yes | Discover modules with metadata |
| `search-markers` | Yes | Yes | No | No | Search OpenRewrite TODO markers in source files |
| `find-project` | No | Yes | No | No | Find Gradle subproject path from name |

---

### run (Primary API)

Execute a build command and auto-parse the log on failure to extract structured errors.

```bash
python3 .plan/execute-script.py {notation} run \
    --command-args "<args>" \
    [--timeout <seconds>] \
    [--mode <mode>] \
    [--format <toon|json>] \
    [--project-dir <path>]
```

**Parameters**:
- `--command-args` — Complete build command arguments with all routing embedded (required). Examples:
  - Maven: `"verify -Ppre-commit -pl my-module"`
  - Gradle: `":module:build"` or `"build"`
  - npm: `"run test"` or `"run test --workspace=pkg"`
  - Python: `"verify"` or `"module-tests core"`
- `--timeout` — Timeout in seconds (default: 300, adaptive via run-config, min floor: 60s)
- `--mode` — Output mode: `actionable` (default), `structured`, `errors`
- `--format` — Output format: `toon` (default), `json`
- `--project-dir` — Project root directory (default: `.`)

**npm-specific additional parameters**:
- `--working-dir` — Working directory for command execution (for nested frontend projects)
- `--env` — Environment variables (e.g., `"NODE_ENV=test CI=true"`)

**Output Format (TOON)**:

Success:
```
status	success
exit_code	0
duration_seconds	45
log_file	.plan/temp/build-output/default/{tool}-{timestamp}.log
command	{wrapper} {args}
```

Build Failure:
```
status	error
exit_code	1
duration_seconds	23
log_file	.plan/temp/build-output/default/{tool}-{timestamp}.log
command	{wrapper} {args}
error	build_failed

errors[N]{file,line,message,category}:
src/main/java/Foo.java    42    cannot find symbol    compile
src/main/java/Bar.java    15    test assertion failed    test_failure

tests:
  passed: 40
  failed: 2
  skipped: 1
```

**Tool-specific output fields**:
- npm: includes `command_type` field (`npm` or `npx`) indicating which executable was used
- Python: includes `wrapper` field showing resolved pyprojectx executable path

---

### parse

Parse a previously captured build log file and extract structured issues.

```bash
python3 .plan/execute-script.py {notation} parse \
    --log <path> [--mode <mode>]
```

**Parameters**:
- `--log` — Path to build log file (required)
- `--mode` — Output mode (default: `structured`):
  - `default` — All issues, unfiltered
  - `errors` — Only error-severity issues
  - `structured` — All issues with structured summary
  - `no-openrewrite` — Exclude OpenRewrite informational messages (Maven and Gradle only)

---

### coverage-report

Parse a coverage report and check against a threshold.

```bash
python3 .plan/execute-script.py {notation} coverage-report \
    [--project-path <path>] \
    [--report-path <path>] \
    [--threshold <percent>]
```

**Parameters**:
- `--project-path` — Module/project directory path (for auto-detection of report files)
- `--report-path` — Override report path (default: auto-detect in build output directories)
- `--threshold` — Coverage threshold percent (default: 80)

**Supported report formats by tool**:
- Maven/Gradle: JaCoCo XML (`jacoco.xml`)
- npm: Jest/Istanbul JSON (`coverage-summary.json`) or LCOV (`.info`)
- Python: coverage.py Cobertura XML (`coverage.xml`)

**Output Format (TOON)**:
```
status	success
passed	true
threshold	80
message	"Coverage meets threshold: 85.2% line, 78.3% branch"

overall:
  line	85.2
  branch	78.3

low_coverage[N]{class,line_pct,missed_methods}:
  com.example.UserService,66.67,deleteUser
```

**Note**: The `overall` metrics vary by tool — JaCoCo provides `instruction` and `method` metrics; coverage.py and Jest do not.

---

### check-warnings

Categorize build warnings against acceptable patterns from run-configuration.

```bash
python3 .plan/execute-script.py {notation} check-warnings \
    --warnings <json> [--acceptable-warnings <json>]
```

**Parameters**:
- `--warnings` — JSON array of warning objects
- `--acceptable-warnings` — JSON object with acceptable patterns (substring or regex)

**Matcher type by tool**:
| Tool | Matcher | Severity Filter |
|------|---------|----------------|
| Maven | `substring` | WARNING only |
| Gradle | `wildcard` | None (all severities) |
| npm | `substring` | None |
| Python | `substring` | None |

---

### discover

Discover project modules with metadata, source layout, and canonical build commands.

```bash
python3 .plan/execute-script.py {notation} discover \
    [--root <path>] [--format <toon|json>]
```

**Parameters**:
- `--root` — Project root directory (default: `.`)
- `--format` — Output format: `toon` (default), `json`

**Output Format (TOON)**:
```
status	success
count	3

modules[N]{name,build_systems,paths,metadata,packages,stats,commands}:
  my-module	["maven"]	{module: "my-module", descriptor: "my-module/pom.xml", ...}	{...}	{...}	{source_files: 12, test_files: 5}	{...}
```

Each module includes:
- `name` — Module identifier
- `build_systems` — Array of detected build systems
- `paths` — `module`, `descriptor`, `sources`, `tests`, `readme`
- `metadata` — Tool-specific (artifact_id/group_id for Maven, group/name for Gradle, version/scripts for npm, name/version/requires_python for Python)
- `packages` / `test_packages` — Discovered package structure
- `stats` — `source_files`, `test_files`
- `commands` — Canonical build commands (see below)

**Discovery mechanism by tool**:
- Maven: reads `pom.xml` `<modules>` declarations; shells out for profiles and dependencies (slower but richer metadata)
- Gradle: reads `settings.gradle(.kts)` `include()` declarations
- npm: reads `package.json` `workspaces` field or `pnpm-workspace.yaml`
- Python: detects directories containing `test/` or `tests/` subdirectories

**Canonical commands generated per module**:

| Canonical | Maven | Gradle | npm | Python |
|-----------|-------|--------|-----|--------|
| `verify` | `verify -pl {m}` | `:{m}:build` | `run build && run test` | `verify {m}` |
| `quality-gate` | `verify -pl {m}` ¹ | `:{m}:check` | `run lint` | `quality-gate {m}` |
| `compile` | `compile -pl {m}` | `:{m}:compileJava` | `run build` | `compile {m}` |
| `module-tests` | `test -pl {m}` | `:{m}:test` | `run test` | `module-tests {m}` |
| `coverage` | `-Pcoverage verify -pl {m}` | `:{m}:test :{m}:jacocoTestReport` | `run test:coverage` | `coverage {m}` |
| `clean` | `clean` | `clean` | `run clean` | `clean` |
| `install` | — | — | `install` | — |

¹ Maven quality-gate defaults to `verify`. When a profile mapping (e.g., `pre-commit:quality-gate`) is configured via extension defaults, it becomes `-P{profile} verify -pl {m}`.

npm commands are conditional on scripts present in `package.json`.

---

### search-markers (Maven, Gradle only)

Search for OpenRewrite TODO markers in source files. Used in conjunction with `parse --mode no-openrewrite` for OpenRewrite workflow: search markers to inventory → decide action → optionally re-parse with the `no-openrewrite` filter.

```bash
python3 .plan/execute-script.py {notation} search-markers \
    --source-dir <dir> [--extensions <ext>]
```

**Parameters**:
- `--source-dir` — Directory to search (default: `src`)
- `--extensions` — Comma-separated file extensions (default: `.java` for Maven, `.java,.kt` for Gradle)

---

### find-project (Gradle only)

Find a Gradle subproject by name or validate a project path. Useful when error output contains a module name but you need the Gradle notation (`:services:auth`) to construct a build command.

```bash
python3 .plan/execute-script.py plan-marshall:build-gradle:gradle find-project \
    --project-name <name> | --project-path <path>
```

**Parameters** (mutually exclusive):
- `--project-name` — Project name to search for
- `--project-path` — Explicit project path to validate (Gradle notation or file path)
- `--root` — Project root directory (default: `.`)

---

## Error Categories

### Shared categories (Maven, Gradle)

These JVM-oriented categories are identical across Maven and Gradle:

| Category | Description |
|----------|-------------|
| `compilation_error` | Compile-time Java errors. Gradle additionally detects Kotlin-specific patterns: `Unresolved reference`, `Type mismatch`, `Smart cast` failures |
| `test_failure` | Test assertion failures |
| `dependency_error` | Dependency resolution issues |
| `javadoc_warning` | JavaDoc documentation issues |
| `deprecation_warning` | Deprecated API usage |
| `unchecked_warning` | Unchecked type conversions |
| `openrewrite_info` | OpenRewrite plugin output |

**Matching strategy**: Maven uses substring matching (case-insensitive). Gradle uses regex patterns for task-specific markers (e.g., `Execution failed for task ':.*:compileJava'`). The shared `categorize_issue()` function auto-detects regex metacharacters and switches matching mode.

**Deduplication**: All tools use the shared `make_dedup_key()` format: `{category}:{file}:{line}:{message[:100]}`.

### npm categories

| Category | Description | Parser |
|----------|-------------|--------|
| `compilation_error` | TypeScript errors (TS2xxx codes) | `_npm_parse_typescript.py` |
| `test_failure` | Jest/Vitest/TAP test failures | `_npm_parse_jest.py`, `_npm_parse_tap.py` |
| `lint_error` | ESLint violations | `_npm_parse_eslint.py` |
| `npm_dependency` | ERESOLVE peer dependency conflicts | `_npm_parse_errors.py` |
| `npm_error` | E404 and other npm command errors | `_npm_parse_errors.py` |

**Parser routing**: npm uses a multi-parser registry that detects the tool type from log content and routes to the appropriate parser. When tool type cannot be determined, parsers are tried in sequence.

### Python categories

| Category | Description |
|----------|-------------|
| `type_error` | mypy type errors |
| `lint_error` | ruff violations |
| `test_failure` | pytest test failures (with line numbers from tracebacks) |
| `import_error` | Module import errors |

**Multi-parser combination**: Unlike Maven/Gradle/npm which route to a single parser, Python's `parse_log()` runs all matching parsers and combines results. This handles pyprojectx `verify` which runs mypy + ruff + pytest in sequence, producing mixed output in a single log file.

---

## Issue Routing

Build errors are routed to domain-specific skills for resolution guidance:

### Maven / Gradle → pm-dev-java

| Category | Target Skill |
|----------|-------------|
| `compilation_error` | `pm-dev-java:java-core` |
| `test_failure` | `pm-dev-java:junit-core` |
| `javadoc_warning` | `pm-dev-java:javadoc` |

### npm → pm-dev-frontend

| Category | Target Skill |
|----------|-------------|
| `compilation_error` | `pm-dev-frontend:javascript` |
| `test_failure` | `pm-dev-frontend:jest-testing` |
| `lint_error` | `pm-dev-frontend:lint-config` |

### Python → pm-dev-python

| Category | Target Skill |
|----------|-------------|
| `type_error` | `pm-dev-python:python-core` |
| `lint_error` | `pm-dev-python:python-core` |
| `test_failure` | `pm-dev-python:pytest-testing` |

---

## Wrapper Detection

| Build System | Detection Order | Fallback Behavior |
|-------------|----------------|-------------------|
| Maven | `./mvnw` → `mvn` (on PATH) | Falls back to system `mvn` |
| Gradle | `./gradlew` → `gradle` (on PATH) | Falls back to system `gradle` |
| npm | System `npm` (no wrapper) | `npm` always available; `npx` used for direct tool invocations |
| Python | `./pw` → `pw.bat` → `pwx` (on PATH) | Raises `FileNotFoundError` — no system fallback since pyprojectx is project-specific |

**npm/npx routing**: Commands are automatically routed based on a built-in list of known CLI tools. Script invocations (`run test`, `run build`) use `npm`; direct tool invocations (eslint, jest, tsc, prettier, webpack, etc.) use `npx`.

---

## Timeout Learning

All build skills integrate with adaptive timeout learning via `run-config`. The timeout for a command is adjusted based on historical execution times:
- First run: uses `--timeout` value or default (300s)
- Subsequent runs: `last_duration × 1.25` (25% safety margin)
- On timeout failure: timeout is doubled for the next run (capped at 1800s)
- Minimum floor: 60 seconds (never below this regardless of learned value)
- Maximum cap: 1800 seconds (prevents exponential growth from successive timeouts)
- Storage: `.plan/run-configuration.json` with command keys like `maven:verify`, `gradle:build`

See `build-execution.md` § R3 for the full algorithm and Python API.

---

## References

- `build-execution.md` — Full execution contract (input/output fields, lifecycle, format specs)
- `build-systems-common.md` — Timeouts, log handling, status determination, acceptable warnings
- `canonical-commands.md` — Command vocabulary specification
- `module-discovery.md` — Module discovery contract
