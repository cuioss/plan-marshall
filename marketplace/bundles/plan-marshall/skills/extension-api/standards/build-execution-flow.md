# Build Execution Flow

Visual reference for the complete build command execution lifecycle.

## Overview

This document shows the end-to-end flow from command resolution through structured result output. For detailed specifications of each component, see the related documents.

## Complete Execution Lifecycle

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         BUILD EXECUTION LIFECYCLE                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. COMMAND RESOLUTION                                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ architecture.py resolve --command verify --name my-module           │    │
│  │                                                                     │    │
│  │ Input: canonical command name + module name                         │    │
│  │ Source: .plan/project-architecture/derived-data.json                │    │
│  │ Output: Complete command string with all routing embedded           │    │
│  │                                                                     │    │
│  │ "python3 .plan/execute-script.py pm-dev-java:plan-marshall-plugin:  │    │
│  │  maven run --commandArgs \"verify -Ppre-commit -pl my-module\""     │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                              │                                               │
│                              ▼                                               │
│  2. EXECUTION (execute_direct)                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                                                                     │    │
│  │  a. create_log_file(build_system, scope, project_dir)              │    │
│  │     → .plan/temp/build-output/{scope}/{system}-{timestamp}.log     │    │
│  │                                                                     │    │
│  │  b. timeout_get(command_key, default, project_dir)                 │    │
│  │     → Returns learned_timeout * 1.25 or default                    │    │
│  │                                                                     │    │
│  │  c. detect_wrapper(project_dir)                                    │    │
│  │     → Maven: ./mvnw > mvn                                          │    │
│  │     → npm: detects npm vs npx based on command                     │    │
│  │                                                                     │    │
│  │  d. subprocess.run(cmd, timeout=timeout, cwd=project_dir)          │    │
│  │     → All output captured to log file (R1 compliance)              │    │
│  │                                                                     │    │
│  │  e. timeout_set(command_key, actual_duration, project_dir)         │    │
│  │     → Records duration for adaptive learning                       │    │
│  │                                                                     │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                              │                                               │
│              ┌───────────────┼───────────────┐                               │
│              ▼               ▼               ▼                               │
│        [exit_code=0]    [exit_code>0]    [TimeoutExpired]                   │
│              │               │               │                               │
│              ▼               ▼               ▼                               │
│  3. RESULT HANDLING                                                          │
│  ┌──────────────┐  ┌─────────────────────┐  ┌──────────────────┐            │
│  │   SUCCESS    │  │    BUILD FAILED     │  │     TIMEOUT      │            │
│  │              │  │                     │  │                  │            │
│  │ success_     │  │ a. parse_log()      │  │ timeout_result() │            │
│  │ result()     │  │    → [Issue], test  │  │                  │            │
│  │              │  │      summary, status│  │ Fields:          │            │
│  │ Fields:      │  │                     │  │ - status: timeout│            │
│  │ - status:    │  │ b. partition_       │  │ - exit_code: -1  │            │
│  │   success    │  │    issues()         │  │ - timeout_used   │            │
│  │ - exit_code: │  │    → (errors,       │  │ - error: timeout │            │
│  │   0          │  │       warnings)     │  │                  │            │
│  │ - duration   │  │                     │  │                  │            │
│  │ - log_file   │  │ c. filter_warnings()│  │                  │            │
│  │ - command    │  │    → mode-based     │  │                  │            │
│  │              │  │      filtering      │  │                  │            │
│  │              │  │                     │  │                  │            │
│  │              │  │ d. error_result()   │  │                  │            │
│  │              │  │    + errors[]       │  │                  │            │
│  │              │  │    + warnings[]     │  │                  │            │
│  │              │  │    + tests{}        │  │                  │            │
│  └──────────────┘  └─────────────────────┘  └──────────────────┘            │
│              │               │               │                               │
│              └───────────────┼───────────────┘                               │
│                              ▼                                               │
│  4. OUTPUT FORMATTING                                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                                                                     │    │
│  │  --format toon (default)           --format json                   │    │
│  │  format_toon(result)               format_json(result)             │    │
│  │                                                                     │    │
│  │  status    success                 {"status": "success",           │    │
│  │  exit_code 0                        "exit_code": 0,                │    │
│  │  duration_seconds  45               "duration_seconds": 45,        │    │
│  │  log_file  .plan/temp/...           "log_file": "...",             │    │
│  │  command   ./mvnw ...               "command": "..."}              │    │
│  │                                                                     │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Timeout Learning Cycle

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        ADAPTIVE TIMEOUT LEARNING                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  FIRST RUN (no learned value)                                                │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                                                                       │  │
│  │  timeout_get("maven:verify", default=300)                            │  │
│  │  → Returns: 300 (the default)                                        │  │
│  │                                                                       │  │
│  │  [Execute build - takes 45 seconds]                                  │  │
│  │                                                                       │  │
│  │  timeout_set("maven:verify", duration=45)                            │  │
│  │  → Stores: {"maven:verify": {"timeout_seconds": 45}}                 │  │
│  │                                                                       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                              │                                               │
│                              ▼                                               │
│  SUBSEQUENT RUNS                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                                                                       │  │
│  │  timeout_get("maven:verify", default=300)                            │  │
│  │  → Returns: 45 * 1.25 = 56 seconds (learned + safety margin)        │  │
│  │                                                                       │  │
│  │  [Execute build - takes 50 seconds this time]                        │  │
│  │                                                                       │  │
│  │  timeout_set("maven:verify", duration=50)                            │  │
│  │  → Updates using weighted average:                                   │  │
│  │    0.80 * max(45,50) + 0.20 * min(45,50) = 49 seconds               │  │
│  │                                                                       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  Storage: .plan/run-configuration.json                                       │
│  Minimum enforced: 120 seconds (prevents warm JVM issues)                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Warning Filtering by Mode

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        WARNING FILTERING MODES                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Input: list[Issue] (all warnings from parse_log)                            │
│  Config: acceptable_warnings patterns from run-configuration.json            │
│                                                                              │
│                         filter_warnings(warnings, patterns, mode)            │
│                                        │                                     │
│              ┌─────────────────────────┼─────────────────────────┐           │
│              ▼                         ▼                         ▼           │
│  ┌─────────────────────┐   ┌─────────────────────┐   ┌─────────────────────┐│
│  │  --mode actionable  │   │  --mode structured  │   │   --mode errors     ││
│  │     (default)       │   │                     │   │                     ││
│  │                     │   │                     │   │                     ││
│  │ Filter out accepted │   │ Keep all warnings   │   │ Return empty list   ││
│  │ warnings            │   │ Mark accepted with  │   │                     ││
│  │                     │   │ [accepted] flag     │   │ Warnings excluded   ││
│  │ Show only warnings  │   │                     │   │ entirely            ││
│  │ requiring action    │   │ Full diagnostic     │   │                     ││
│  │                     │   │ view                │   │ Errors-only output  ││
│  └─────────────────────┘   └─────────────────────┘   └─────────────────────┘│
│              │                         │                         │           │
│              ▼                         ▼                         ▼           │
│  warnings[2]:              warnings[4]:              (no warnings section)   │
│  file1  10  msg1           file1  10  msg1                                   │
│  file2  20  msg2           file2  20  msg2  [accepted]                       │
│                            file3  30  msg3  [accepted]                       │
│                            file4  40  msg4                                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## File Responsibilities

| Script | Location | Responsibility |
|--------|----------|----------------|
| `extension_discovery.py` | extension-api | Extension loading, module aggregation |
| `_build_result.py` | extension-api | Log file creation, result dict builders |
| `_build_parse.py` | extension-api | Issue structures, warning filtering |
| `_build_format.py` | extension-api | TOON/JSON output formatting |
| `_maven_execute.py` | pm-dev-java | Maven wrapper detection, execution |
| `_maven_cmd_parse.py` | pm-dev-java | Maven log parsing, issue extraction |
| `npm.py` | pm-dev-frontend | npm/npx execution, tool detection |
| `_npm_parse_*.py` | pm-dev-frontend | Tool-specific parsers (TS, Jest, ESLint) |
| `run_config.py` | plan-marshall | Timeout learning, warning patterns |

## Persistence Points

| File | Owner | Content |
|------|-------|---------|
| `.plan/project-architecture/derived-data.json` | analyze-project-architecture | Discovered modules with command strings |
| `.plan/run-configuration.json` | run-config | Learned timeouts, acceptable warnings |
| `.plan/temp/build-output/{scope}/{system}-{ts}.log` | build scripts | Raw build output (timestamped) |

## Output Format (TOON)

Build commands output tab-separated key-value pairs (TOON format).

**Success:**
```
status	success
exit_code	0
duration_seconds	45
log_file	.plan/temp/build-output/my-module/maven-2025-01-14-143022.log
command	./mvnw -l .plan/temp/build-output/... verify -pl my-module
```

**Build Failed (with parsed issues):**
```
status	error
exit_code	1
duration_seconds	23
log_file	.plan/temp/build-output/my-module/maven-2025-01-14-143022.log
command	./mvnw -l .plan/temp/build-output/... verify -pl my-module
error	build_failed

errors[2]{file,line,message,category}:
src/Main.java	15	cannot find symbol	compilation_error
src/Test.java	42	assertion failed	test_failure

warnings[1]{file,line,message}:
pom.xml	-	deprecated dependency	deprecation_warning

tests:
  passed: 40
  failed: 2
  skipped: 0
```

**Timeout:**
```
status	timeout
exit_code	-1
duration_seconds	300
timeout_used_seconds	300
log_file	.plan/temp/build-output/my-module/maven-2025-01-14-143022.log
command	./mvnw -l .plan/temp/build-output/... verify -pl my-module
error	timeout
```

See [build-return.md](build-return.md) for complete field definitions and JSON format.

## Related Documents

| Document | Content |
|----------|---------|
| [build-execution.md](build-execution.md) | R1-R5 requirements, CLI interface |
| [build-return.md](build-return.md) | Return structure specification |
| [build-parsing-design.md](build-parsing-design.md) | Parser architecture, Issue structures |
| [canonical-commands.md](canonical-commands.md) | Command vocabulary and resolution |
| [architecture-overview.md](architecture-overview.md) | Discovery and aggregation flow |
