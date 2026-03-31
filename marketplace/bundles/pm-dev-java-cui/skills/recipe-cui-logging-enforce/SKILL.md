---
name: recipe-cui-logging-enforce
description: Recipe for enforcing CUI logging standards across all modules — migrate loggers, implement LogRecords, add test coverage
user-invocable: false
---

# Recipe: Enforce CUI Logging Standards

Custom recipe for enforcing CUI logging standards across Java modules. Discovers modules, creates one deliverable per module. The task executor loads `cui-logging` standards and `cui-logging-enforce` execution reference, then handles analysis and fixing in a single pass per module.

## Input

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan_id` | string | Yes | Plan identifier |
| `recipe_domain` | string | Yes | Domain key (auto-assigned: `java-cui`) |
| `recipe_profile` | string | No | Not used — this recipe scans whole modules, not packages |
| `recipe_package_source` | string | No | Not used — scope is module-level |

---

## Step 1: Resolve Skills

The enforcement requires logging standards and testing standards (for LogAsserts):

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  resolve-domain-skills --domain java-cui --profile core
```

Also resolve the `module_testing` profile for test coverage skills:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  resolve-domain-skills --domain java-cui --profile module_testing
```

Combine all resolved skills. The deliverables will always include both profiles (`implementation` and `module_testing`) since enforcement modifies both production code (logger migration, LogRecord implementation) and test code (LogAsserts).

Additionally, each deliverable must reference the execution guidance skill:
- `pm-dev-java-cui:cui-logging-enforce` — enforcement workflow and batch sequence

---

## Step 2: List Modules

Query the project architecture for available modules:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture modules
```

Present module list to user for confirmation/filtering. User may exclude modules (e.g., parent POMs, modules without Java source files).

---

## Step 3: Discover Files and Collect Deliverable Data

For each selected module:

**3a. Query module details:**

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  module --name {module_name} --full
```

**3b. Discover logging-related files** using Glob patterns within the module path:
- `{module_path}/src/main/java/**/*LogMessages.java` — LogMessages classes
- `{module_path}/src/main/java/**/*.java` — All production Java files (for logger migration scan)
- `{module_path}/src/test/java/**/*Test.java` — Test files (for LogAssert coverage)
- `{module_path}/doc/LogMessages.adoc` — LogMessages documentation

Skip modules with no Java source files.

**3c. Collect one deliverable per module** (in-memory, for Step 4):
- **Title**: `Enforce logging standards: {module}`
- **Description**: `Migrate loggers, implement LogRecords, add LogAssert test coverage`
- **Metadata**:
  - `change_type`: `tech_debt`
  - `execution_mode`: `automated`
  - `domain`: `java-cui`
  - `module`: `{module_name}`
- **Profiles**: `implementation`, `module_testing`
- **Skills**: All skills from Step 1 + `pm-dev-java-cui:cui-logging-enforce`
- **Affected files**: All files discovered in 3b (explicit paths, no wildcards)
- **Change per file**: Enforce CUI logging standards — migrate SLF4J/Log4j to CuiLogger, replace direct string logging with LogRecord constants, add LogAssert coverage for all LogRecords
- **Verification**: Resolved `module-tests` command for the module
- **Success Criteria**:
  - All loggers use CuiLogger (no SLF4J/Log4j)
  - INFO/WARN/ERROR/FATAL use LogRecord constants
  - DEBUG/TRACE use direct CuiLogger calls
  - Every LogRecord has LogAssert coverage in business logic tests
  - LogMessages identifiers properly numbered (INFO 001-099, WARN 100-199, ERROR 200-299, FATAL 300-399)
  - Build and tests pass

---

## Step 4: Outline Writing

**4a. Read the deliverable template** to understand the required structure:

```
Read: marketplace/bundles/plan-marshall/skills/manage-solution-outline/templates/deliverable-template.md
```

**4b. Read an example** to see the full document skeleton:

```
Read: marketplace/bundles/plan-marshall/skills/manage-solution-outline/examples/refactoring.md
```

**4c. Resolve the target path**:

```bash
python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage-solution-outline \
  resolve-path --plan-id {plan_id}
```

**4d. Resolve verification commands** for each module:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  resolve --command module-tests --name {module} --trace-plan-id {plan_id}
```

**4e. Write the solution outline** using the Write tool to `{resolved_path}`. The document MUST include these sections in order:
- `# Solution: Enforce CUI Logging Standards` header with `plan_id`, `created`, `compatibility` metadata
- `## Summary` — scope description ({N} modules)
- `## Overview` — resolved skills list and module breakdown
- `## Deliverables` — all deliverables from Step 3, grouped by module, using the template structure from 4a

**4f. Validate** the written outline:

```bash
python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage-solution-outline \
  write --plan-id {plan_id}
```

---

## Related

- `pm-dev-java-cui:cui-logging` — Core logging standards and maintenance reference
- `pm-dev-java-cui:cui-logging-enforce` — Enforcement execution reference (loaded during task execution)
- `pm-dev-java-cui:cui-testing` — Test standards including LogAsserts
- `plan-marshall:recipe-refactor-to-profile-standards` — Built-in recipe (same 4-step pattern)
- `plan-marshall:phase-3-outline` Step 2.5 — Loads this skill with input parameters
