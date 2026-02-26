# Project Structure Discovery API

Specification for project structure discovery in domain extensions.

## Purpose

Domain bundles that provide build capabilities expose a **unified discovery API** that:
- Discovers all project modules with complete metadata
- Extracts dependencies, packages, and source structure
- Splits multi-tech directories into virtual modules (e.g., Maven+npm → separate modules)
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
    "module-tests": "python3 .plan/execute-script.py pm-dev-java:plan-marshall-plugin:maven run --command-args \"test -pl oauth-sheriff-core\"",
    "quality-gate": "python3 .plan/execute-script.py pm-dev-java:plan-marshall-plugin:maven run --command-args \"verify -Ppre-commit -pl oauth-sheriff-core\"",
    "verify": "python3 .plan/execute-script.py pm-dev-java:plan-marshall-plugin:maven run --command-args \"verify -pl oauth-sheriff-core\""
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
| `name` | string | Module name (includes technology suffix for virtual modules) |
| `build_systems` | string[] | Single build system (e.g., `["maven"]` or `["npm"]`) |
| `virtual_module` | object \| null | Virtual module metadata (for multi-tech directories) |
| `virtual_module.physical_path` | string | Actual directory path (shared by siblings) |
| `virtual_module.technology` | string | Build system technology |
| `virtual_module.sibling_modules` | string[] | Names of sibling virtual modules |
| `paths.module` | string | Relative path from project root |
| `paths.descriptor` | string | Path to descriptor |
| `paths.sources` | string[] | Source directories |
| `paths.tests` | string[] | Test directories |
| `paths.readme` | string | Path to README if exists |
| `metadata.*` | string \| null | Extracted metadata (snake_case) |
| `metadata.profiles` | array \| null | Build-system-specific profiles (Maven only, see below) |
| `packages` | object | Package name → {path, package_info?} |
| `dependencies` | string[] | Technology-native format (see Dependency format below) |
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

## Virtual Modules (Multi-Tech Directories)

When a directory contains multiple build systems (e.g., pom.xml + package.json), the discovery creates **separate virtual modules** with technology suffixes instead of merging them.

**Detection**: Multiple descriptor files in same directory:
- `pom.xml` + `package.json` → `{name}-maven` + `{name}-npm`
- `build.gradle` + `package.json` → `{name}-gradle` + `{name}-npm`

**Virtual module structure**:
```json
{
  "name": "my-module-maven",
  "build_systems": ["maven"],
  "virtual_module": {
    "physical_path": "my-module",
    "technology": "maven",
    "sibling_modules": ["my-module-npm"]
  },
  "paths": { "module": "my-module", ... },
  "commands": { "module-tests": "..." }
}
```

**Benefits**:
- Each module has single build system (no ambiguity)
- Commands are strings (no nested technology selection)
- Skills by profile are technology-specific
- Task assignment targets single technology

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

**Dependency format**: Technology-native format without prefixes:
- Maven: `groupId:artifactId:scope` (e.g., `org.projectlombok:lombok:compile`)
- npm: `name:scope` (e.g., `lit:compile`, `@testing-library/dom:test`)

### Package Discovery

**Java packages** (object keyed by package name):
```json
"packages": {
  "de.cuioss.tools": {
    "path": "core/src/main/java/de/cuioss/tools",
    "package_info": "core/src/main/java/de/cuioss/tools/package-info.java",
    "files": ["CollectionBuilder.java", "MoreCollections.java", "MoreStrings.java"]
  },
  "de.cuioss.tools.util": {
    "path": "core/src/main/java/de/cuioss/tools/util",
    "files": ["MorePaths.java"]
  }
}
```
- Include `package_info` path if `package-info.java` exists, omit otherwise
- `files`: Sorted list of source file names (direct children only, sub-package files excluded)
- Java: `.java` files, excluding `package-info.java` (tracked separately via `package_info`)
- Omitted when empty (no direct source files — only sub-packages)
- All paths are project-relative

**Java test packages** (same structure, keyed by package name):
```json
"test_packages": {
  "de.cuioss.tools": {
    "path": "core/src/test/java/de/cuioss/tools",
    "files": ["CollectionBuilderTest.java", "MoreStringsTest.java"]
  }
}
```
- Same conventions as `packages` (sorted files, direct children only, omitted when empty)
- Separate field because test packages mirror main package names

**npm packages** (directory-based or exports-defined):
```json
"packages": {
  "components": {
    "path": "my-lib/src/components",
    "files": ["Button.js", "Card.js", "Modal.js"]
  },
  "hooks": {
    "path": "my-lib/src/hooks",
    "files": ["useAuth.ts", "useForm.ts"]
  },
  "utils": {
    "path": "my-lib/src/utils",
    "exports": "./utils",
    "files": ["format.js", "validate.js"]
  }
}
```
- Discover from `package.json` [subpath exports](https://nodejs.org/api/packages.html) field
- Fall back to top-level directories under `src/` or `lib/`
- Include `exports` path if defined in package.json exports field
- `files`: Sorted list of source file names (direct children only)
- npm: `.js`, `.ts`, `.mjs`, `.cjs` files, excluding `.d.ts`
- Omitted when empty (no direct source files)
- All paths are project-relative

## Orchestrator Integration

The `project-structure` skill orchestrates discovery across all extensions, splits multi-tech directories into virtual modules, and persists results.

See [orchestrator-integration.md](../../analyze-project-architecture/standards/orchestrator-integration.md) for:
- Orchestrator flow and extension discovery
- Virtual module splitting algorithm
- Output location (`.plan/raw-project-data.json`)
- CLI interface

## Compliance

Extensions providing module discovery must:

- [ ] Implement `discover_modules()` returning list of module dicts
- [ ] Return empty list (not None) when no modules found
- [ ] Use `build_systems` field as single-element array (e.g., `["maven"]`)
- [ ] Use `paths` object with `module`, `descriptor`, `sources`, `tests`, `readme`
- [ ] Use snake_case for metadata fields (`artifact_id`, `group_id`)
- [ ] Include `metadata.profiles` for build-system-specific profiles (Maven)
- [ ] Use `packages` as object keyed by package name
- [ ] Use technology-native dependency format (Maven: `groupId:artifactId:scope`, npm: `name:scope`)
- [ ] Include `commands` with resolved canonical command strings (not nested)
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
