# Run Configuration Format

JSON schema specification for run configuration storage (via `file-operations-base` skill).

## Purpose

The run configuration file stores:
- Command execution history
- Acceptable warnings and skip lists
- Maven build configurations

> **Note**: Lessons learned are stored separately via `manage-lessons-learned` skill.

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
  "profile_mappings": {
    "<profile-id>": "<canonical|skip>"
  }
}
```

## Required Fields

| Field | Type | Description |
|-------|------|-------------|
| version | integer | Schema version (currently 1) |
| commands | object | Command-specific configurations |

## Optional Sections

| Section | Purpose |
|---------|---------|
| ci | CI provider tool verification status |
| maven | Maven build configurations |
| profile_mappings | User decisions for build profile classification |

---

## Commands Section

Each command entry can have:

| Field | Type | Description |
|-------|------|-------------|
| last_execution | object | Most recent execution details |
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

The `duration_ms` field enables adaptive timeout learning. The `await-until` script uses previous execution durations to calculate appropriate timeouts for polling operations.

---

## CI Section

CI provider tool verification status (written by `tools-integration-ci:ci_health persist`).

| Field | Type | Description |
|-------|------|-------------|
| git_present | boolean | Whether git is installed |
| authenticated_tools | array | List of authenticated CI tools |
| verified_at | string | ISO timestamp of last verification |

### Example

```json
{
  "ci": {
    "git_present": true,
    "authenticated_tools": ["git", "gh"],
    "verified_at": "2025-12-19T10:30:00Z"
  }
}
```

> **Note**: Provider-specific configuration (provider name, repo URL, static commands) is stored in `marshal.json` (shared via git), while tool authentication status is stored in `run-configuration.json` (local, machine-specific).

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

## Profile Mappings Section

User decisions about build profile classification. Used by `build_env persist` to resolve profiles that can't be auto-classified.

| Field | Type | Description |
|-------|------|-------------|
| profile_mappings | object | Map of profile ID to canonical command or 'skip' |

### Valid Canonicals

| Canonical | Description |
|-----------|-------------|
| integration-tests | Integration test execution |
| coverage | Code coverage analysis |
| benchmark | Performance/benchmark testing |
| quality-gate | Quality checks (lint, static analysis) |
| skip | Exclude profile from command generation |

### Example

```json
{
  "profile_mappings": {
    "jfr": "skip",
    "quick": "skip",
    "perf": "benchmark",
    "analyze-jfr": "skip"
  }
}
```

> **Note**: Profile mappings are stored in `run-configuration.json` (local) not `marshal.json` (shared). This allows different machines to have different profile configurations if needed.

---

## JSON Path Access

Use dot notation for field access:

| Path | Access |
|------|--------|
| `commands` | All commands |
| `commands.my-cmd` | Specific command |
| `commands.my-cmd.last_execution.date` | Execution date |
| `commands.my-cmd.skipped_files[0]` | First skipped file |
| `maven.acceptable_warnings` | Maven warnings |
| `profile_mappings` | All profile mappings |
| `profile_mappings.jfr` | Mapping for specific profile |

---

## Example

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
    }
  },
  "ci": {
    "git_present": true,
    "authenticated_tools": ["git", "gh"],
    "verified_at": "2025-12-19T10:30:00Z"
  },
  "maven": {
    "acceptable_warnings": {
      "transitive_dependency": [],
      "plugin_compatibility": [],
      "platform_specific": []
    }
  },
  "profile_mappings": {
    "jfr": "skip",
    "quick": "skip",
    "perf": "benchmark"
  }
}
```
