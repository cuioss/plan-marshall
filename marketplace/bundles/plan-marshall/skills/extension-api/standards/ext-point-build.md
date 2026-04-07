# Extension Point: Build System

> **Type**: Module Discovery + Build Execution | **Hook Method**: `discover_modules()` + `ExecuteConfig` factory | **Implementations**: 4 | **Status**: Active

## Overview

Build system extensions provide module discovery and build command execution for a specific build tool. Unlike other extension points, build systems are implemented as standalone skills (not via a single hook method) — each build skill provides a `discover` subcommand for module discovery and a `run` subcommand for build execution, both following the `ExecuteConfig` factory pattern.

This document is a unifying reference that links to the detailed specifications without duplicating them.

## Parameters

### Discovery

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `project_root` | str | Yes | Absolute path to project root |

### Execution

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `command_args` | str | Yes | Build command string (e.g., `compile module-name`) |
| `module` | str | No | Module scope (varies by tool) |

## Pre-Conditions (Discovery)

- Project root contains recognizable descriptor files (e.g., `pom.xml`, `package.json`, `build.gradle`, `pyproject.toml`)
- Build tool wrapper or system installation available

## Post-Conditions (Discovery)

- Module list with `name`, `build_systems`, `paths`, `metadata`, `commands`
- All commands fully resolved with routing embedded
- See [module-discovery.md](module-discovery.md) for complete output specification

## Pre-Conditions (Execution)

- Wrapper or system build tool available on PATH
- Log directory writable (`.plan/logs/`)
- Command resolved via `architecture resolve`

## Post-Conditions (Execution)

- Result dict with `status`, `exit_code`, `duration_seconds`, `log_file`, `command`
- Log file persisted to `.plan/logs/`
- Timeout learning updated in `run-configuration.json`
- See [build-execution.md](build-execution.md) for complete execution API

## Factory Pattern

Build skills use the `ExecuteConfig` dataclass + `create_execute_handlers()` factory in `_build_execute_factory.py`:

```python
@dataclass
class ExecuteConfig:
    tool_name: str           # e.g., "maven", "gradle"
    wrapper_names: list      # e.g., ["mvnw", "./mvnw"]
    system_command: str      # e.g., "mvn"
    descriptor_file: str     # e.g., "pom.xml"
```

## CLI Contract

Standard subcommands for all build skills:

| Subcommand | Description |
|------------|-------------|
| `run` | Execute a build command |
| `parse` | Parse build output for errors/warnings |
| `check-warnings` | Check warnings against configured thresholds |
| `coverage-report` | Parse coverage report (JaCoCo, etc.) |
| `discover` | Discover project modules |

## Detailed Specifications

| Document | Content |
|----------|---------|
| [module-discovery.md](module-discovery.md) | `discover_modules()` contract, output structure, module fields |
| [canonical-commands.md](canonical-commands.md) | Command vocabulary (`compile`, `verify`, `module-tests`, etc.) |
| [build-execution.md](build-execution.md) | Build execution API, `ExecuteConfig`, return structure |
| [build-api-reference.md](build-api-reference.md) | Internal API reference for build scripts |
| [build-systems-common.md](build-systems-common.md) | Shared patterns across build systems |

## Implementation Pattern

To create a new build skill:

1. Create `skills/build-{tool}/` under `plan-marshall` bundle
2. Implement `ExecuteConfig` with tool-specific wrapper/command
3. Provide standard subcommands via `create_execute_handlers()`
4. Register module discovery in `extension.py` `discover_modules()`
5. Add `implements` frontmatter to SKILL.md

## Implementor Frontmatter

All build implementor skills must include in their SKILL.md frontmatter:

```yaml
implements: plan-marshall:extension-api/standards/ext-point-build
```

## Current Implementations

| Bundle | Skill | Build Tool | Descriptor |
|--------|-------|------------|------------|
| plan-marshall | build-maven | Maven | pom.xml |
| plan-marshall | build-gradle | Gradle | build.gradle / build.gradle.kts |
| plan-marshall | build-npm | npm | package.json |
| plan-marshall | build-python | Python (pyprojectx) | pyproject.toml |
