---
name: build-gradle
description: Gradle build operations with execution, parsing, and module discovery
user-invocable: false
---

# Build Gradle

Gradle build execution with output parsing, module discovery, and wrapper detection.

## Enforcement

**Execution mode**: Run scripts exactly as documented; parse TOON output for status and route accordingly.

**Prohibited actions:**
- Do not invoke Gradle directly; all builds go through the script API
- Do not invent script arguments not listed in the operations table
- Do not bypass wrapper detection logic

**Constraints:**
- All commands use `python3 .plan/execute-script.py plan-marshall:build-gradle:gradle {command} {args}`
- Output format defaults to TOON; use `--format json` only when explicitly required

## Scripts Overview

| Script | Type | Purpose |
|--------|------|---------|
| `gradle.py` | CLI | Gradle operations dispatcher |
| `_gradle_execute.py` | Library | Foundation execution, wrapper detection |
| `_gradle_cmd_discover.py` | Library | Module discovery via build.gradle |
| `_gradle_cmd_parse.py` | Library | Log parsing, issue extraction |
| `_gradle_cmd_find_project.py` | Library | Gradle subproject location |
| `_gradle_cmd_check_warnings.py` | Library | Warning categorization |
| `_gradle_cmd_search_markers.py` | Library | Marker detection in Gradle projects |

## Gradle run (Primary API)

```bash
python3 .plan/execute-script.py plan-marshall:build-gradle:gradle run \
    --targets "<tasks>" \
    [--module <module>] \
    [--format <toon|json>] \
    [--timeout <seconds>] \
    [--mode <mode>]
```

### Low-level Operations

| Command | Purpose |
|---------|---------|
| `gradle parse` | Parse Gradle build output |
| `gradle find-project` | Find Gradle subproject |
| `gradle search-markers` | Search markers in Gradle project |
| `gradle check-warnings` | Check Gradle warnings |

## Wrapper Detection

```
Gradle: ./gradlew > gradle (on PATH)
```

## References

- `plan-marshall:extension-api` - Extension API contract
- `standards/gradle-impl.md` - Gradle execution details
