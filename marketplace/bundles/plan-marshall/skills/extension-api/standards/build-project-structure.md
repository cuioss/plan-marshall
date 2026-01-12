# Project Structure Discovery API

Specification for project structure discovery in domain extensions.

## Purpose

Domain bundles that provide build capabilities expose a **unified discovery API** that:
- Discovers all project modules with complete metadata
- Extracts dependencies, packages, and source structure
- Detects hybrid modules (e.g., Maven+npm in same directory)
- Returns structured data for project analysis

## Discovery Contract

### Input

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `project_root` | string | Yes | Absolute path to project root directory |

### Output (Per Extension)

Each extension returns modules it discovered with `build_systems` field:

```json
{
  "name": "oauth-sheriff-core",
  "build_systems": ["maven"],
  "paths": {
    "module": "oauth-sheriff-core",
    "descriptor": "oauth-sheriff-core/pom.xml",
    "sources": [
      "oauth-sheriff-core/src/main/java",
      "oauth-sheriff-core/src/main/resources"
    ],
    "tests": [
      "oauth-sheriff-core/src/test/java",
      "oauth-sheriff-core/src/test/resources"
    ],
    "readme": "oauth-sheriff-core/README.adoc"
  },
  "metadata": {
    "artifact_id": "oauth-sheriff-core",
    "group_id": "de.cuioss.sheriff.oauth",
    "packaging": "jar",
    "description": "Core OAuth Sheriff functionality",
    "parent": "de.cuioss.sheriff.oauth:oauth-sheriff-parent",
    "profiles": [
      {"id": "coverage", "canonical": "coverage"},
      {"id": "pre-commit", "canonical": "quality-gate"}
    ]
  },
  "packages": {
    "de.cuioss.sheriff.oauth.core": {
      "path": "oauth-sheriff-core/src/main/java/de/cuioss/sheriff/oauth/core",
      "package_info": "oauth-sheriff-core/src/main/java/de/cuioss/sheriff/oauth/core/package-info.java"
    },
    "de.cuioss.sheriff.oauth.core.util": {
      "path": "oauth-sheriff-core/src/main/java/de/cuioss/sheriff/oauth/core/util"
    }
  },
  "dependencies": [
    "de.cuioss:cui-java-tools:compile",
    "org.projectlombok:lombok:compile",
    "org.junit.jupiter:junit-jupiter:test"
  ],
  "stats": {
    "source_files": 45,
    "test_files": 38
  },
  "commands": {
    "module-tests": "python3 .plan/execute-script.py pm-dev-java:plan-marshall-plugin:maven run --commandArgs \"test -pl oauth-sheriff-core\"",
    "quality-gate": "python3 .plan/execute-script.py pm-dev-java:plan-marshall-plugin:maven run --commandArgs \"verify -Ppre-commit -pl oauth-sheriff-core\"",
    "verify": "python3 .plan/execute-script.py pm-dev-java:plan-marshall-plugin:maven run --commandArgs \"verify -pl oauth-sheriff-core\""
  }
}
```

### Output (Aggregated by Orchestrator)

See [orchestrator-integration.md](../../analyze-project-architecture/standards/orchestrator-integration.md) for:
- Complete aggregated output structure including `commands`
- Hybrid module merging algorithm
- Command resolution flow
- Output location (`.plan/raw-project-data.json`)

**Field types (per-extension)**:

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Module name |
| `build_systems` | string[] | Build systems (e.g., `["maven"]` or `["maven", "npm"]` for hybrid) |
| `paths.module` | string | Relative path from project root |
| `paths.descriptor` | string | Path to descriptor |
| `paths.sources` | string[] | Source directories |
| `paths.tests` | string[] | Test directories |
| `paths.readme` | string | Path to README if exists |
| `metadata.*` | string \| null | Extracted metadata (snake_case) |
| `metadata.profiles` | array \| null | Build-system-specific profiles (Maven only, see below) |
| `packages` | object | Package name → {path, package_info?} |
| `dependencies` | string[] | `groupId:artifactId:scope` |
| `stats` | object | `{source_files, test_files}` |
| `commands` | object | Canonical command name → resolved command string |

## Profile Structure (Maven)

The `metadata.profiles` field contains build profiles with canonical command mapping:

```json
"profiles": [
  {"id": "pre-commit", "canonical": "quality-gate"},
  {"id": "jacoco", "canonical": "coverage"},
  {"id": "custom-profile", "canonical": "NO-MATCH-FOUND"}
]
```

**Profile fields**:

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Original profile ID from pom.xml |
| `canonical` | string | Mapped canonical command name or `"NO-MATCH-FOUND"` |

**Canonical mapping**: Profile IDs are matched against known patterns (e.g., "pre-commit" → "quality-gate", "jacoco" → "coverage"). When no pattern matches, the `canonical` field is set to the literal string `"NO-MATCH-FOUND"` (not null).

## Packaging Types

The `metadata.packaging` field stores build-system-specific packaging information:

**Maven/Gradle** (`metadata.packaging`):

| Value | Description |
|-------|-------------|
| `jar` | Standard Java library (default if not specified) |
| `war` | Web application archive |
| `pom` | Parent/BOM module (no compiled code) |

**npm**: No packaging field (npm modules are always packages).

**Framework detection** (e.g., Quarkus) is inferred from dependencies, not stored as packaging type.

## Hybrid Module Detection

Modules may use multiple build systems simultaneously (e.g., Maven for backend, npm for frontend in same directory).

**Detection**: A module is hybrid when multiple descriptor files exist:
- `pom.xml` + `package.json` → Maven + npm hybrid
- `build.gradle` + `package.json` → Gradle + npm hybrid

**Merging**: See [orchestrator-integration.md](../../analyze-project-architecture/standards/orchestrator-integration.md) for merge rules.

## Extension Implementation

Extensions use **build tool commands** (not direct file parsing) to extract metadata and dependencies via `execute_direct()`.

**Implementations:**
- Maven: `pm-dev-java/skills/plan-marshall-plugin/scripts/maven_cmd_discover.py`
- Gradle: `pm-dev-java/skills/plan-marshall-plugin/scripts/gradle_cmd_discover.py`
- npm: `pm-dev-frontend/skills/plan-marshall-plugin/extension.py`

See [build-execution.md](build-execution.md) for `execute_direct` API and [build-base-libs.md](build-base-libs.md) for base library details.

### Build-System-Specific Discovery

| Build System | Primary Command | Output |
|--------------|-----------------|--------|
| Maven | `mvnw help:all-profiles dependency:tree` | Profiles + dependency tree in log |
| Gradle | `gradlew projects dependencies` | Projects + dependencies in log |
| npm | `npm pkg get name version description` | JSON metadata |

**Dependency format**: `groupId:artifactId:scope`
- Maven: `org.projectlombok:lombok:compile`
- npm: `npm:lit:compile` (prefixed with `npm:`)

### Package Discovery

**Java packages** (object keyed by package name):
```json
"packages": {
  "de.cuioss.tools": {
    "path": "core/src/main/java/de/cuioss/tools",
    "package_info": "core/src/main/java/de/cuioss/tools/package-info.java"
  },
  "de.cuioss.tools.util": {
    "path": "core/src/main/java/de/cuioss/tools/util"
  }
}
```
- Include `package_info` path if `package-info.java` exists, omit otherwise
- All paths are project-relative

**npm packages** (directory-based or exports-defined):
```json
"packages": {
  "components": {
    "path": "my-lib/src/components"
  },
  "hooks": {
    "path": "my-lib/src/hooks"
  },
  "utils": {
    "path": "my-lib/src/utils",
    "exports": "./utils"
  }
}
```
- Discover from `package.json` [subpath exports](https://nodejs.org/api/packages.html) field
- Fall back to top-level directories under `src/` or `lib/`
- Include `exports` path if defined in package.json exports field
- All paths are project-relative

## Orchestrator Integration

The `project-structure` skill orchestrates discovery across all extensions, merges hybrid modules, and persists results.

See [orchestrator-integration.md](../../analyze-project-architecture/standards/orchestrator-integration.md) for:
- Orchestrator flow and extension discovery
- Hybrid module merging algorithm
- Output location (`.plan/raw-project-data.json`)
- CLI interface

## Compliance

Extensions providing module discovery must:

- [ ] Implement `discover_modules()` returning list of module dicts
- [ ] Return empty list (not None) when no modules found
- [ ] Use `build_systems` field as array (e.g., `["maven"]`)
- [ ] Use `paths` object with `module`, `descriptor`, `sources`, `tests`, `readme`
- [ ] Use snake_case for metadata fields (`artifact_id`, `group_id`)
- [ ] Include `metadata.profiles` for build-system-specific profiles (Maven)
- [ ] Use `packages` as object keyed by package name
- [ ] Use dependency format `groupId:artifactId:scope`
- [ ] Include `commands` with resolved canonical command strings
- [ ] All paths project-relative (not absolute)

## Known Limitations

1. **Nested modules**: Deeply nested modules (e.g., `parent/child/grandchild`) require recursive discovery
2. **Gradle dependencies**: Require Gradle execution (not parsed from `build.gradle`)
3. **Dynamic configuration**: Build-time-only values not discoverable from static analysis

## Related Specifications

- [orchestrator-integration.md](../../analyze-project-architecture/standards/orchestrator-integration.md) - Orchestrator flow and merging
- [extension-contract.md](extension-contract.md) - Extension API contract
- [build-execution.md](build-execution.md) - Build command execution
- [canonical-commands.md](canonical-commands.md) - Command vocabulary
