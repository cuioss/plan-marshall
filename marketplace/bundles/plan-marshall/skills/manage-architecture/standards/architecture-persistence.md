# Architecture Persistence

Storage format for project architecture data. The on-disk layout is fanned
out per module: a single top-level `_project.json` plus one directory per
module containing `derived.json` (deterministic discovery output) and
`enriched.json` (LLM-augmented fields).

## Storage

**Location**: `.plan/project-architecture/`

```
.plan/project-architecture/
├── _project.json                   # Top-level project metadata + module index
├── {module-1}/
│   ├── derived.json                # Extension API output (deterministic)
│   └── enriched.json               # LLM-enriched fields
├── {module-2}/
│   ├── derived.json
│   └── enriched.json
└── ...
```

**Atomicity contract**: `architecture discover --force` builds the new tree
under a sibling staging directory `project-architecture.tmp/` and then
`os.replace`-swaps it onto the real path. A forced interruption either
before or after the rename leaves the project in a consistent state — the
old layout is intact, or the new layout is intact, never half-written.

**Source of truth invariant**: `_project.json`'s `modules` field is the
canonical answer to "which modules exist". Per-module directory presence on
disk is **not** a substitute for the index — half-written directories from
interrupted writes must be ignored. Clients iterate `_project.json` and
lazy-load per-module files; they MUST NOT enumerate the directory tree.

**Benefits of the per-module layout:**
- Smaller, easier-to-read files per module (no 60+ KB monoliths).
- Per-module re-enrichment is local — editing one module never rewrites the
  whole project.
- Atomic writes via tmp+swap are simple to reason about.
- Clear provenance: extensions own `derived.json`; the LLM owns
  `enriched.json`; the project metadata sits in `_project.json`.

---

## `_project.json`

Top-level project metadata and the module index.

### Structure

```json
{
  "name": "oauth-sheriff",
  "description": "JWT validation library for Quarkus applications",
  "description_reasoning": "Derived from: root README.md first paragraph",
  "extensions_used": ["pm-dev-java", "plan-marshall"],
  "modules": {
    "oauth-sheriff-parent": {},
    "oauth-sheriff-core": {},
    "oauth-sheriff-quarkus": {},
    "oauth-sheriff-quarkus-deployment": {}
  }
}
```

### Fields

| Field | Description |
|-------|-------------|
| `name` | Project name (typically the repository directory name) |
| `description` | LLM-generated 1-2 sentence project description |
| `description_reasoning` | Source/rationale for the description |
| `extensions_used` | Domain extensions that contributed to discovery |
| `modules` | **Module index** — keys are module names, values are reserved for future per-module overrides (empty objects today). The set of keys is the canonical "which modules exist" answer. |

### `modules` index — discovery surface

Clients iterate `_project.json["modules"]` to know which modules to load.
The values are presently empty objects but the field is reserved as the
extension point for per-module project-level metadata in future revisions.

The `iter_modules()` core helper returns the sorted key list and is the
only blessed way to enumerate modules; callers MUST NOT scan the
`project-architecture/` directory tree directly.

---

## Per-module `derived.json`

Path: `.plan/project-architecture/{module}/derived.json`

Direct output from `discover_project_modules()` for one module. See
[module-discovery.md](../../extension-api/standards/module-discovery.md) for
the full extension contract.

### Structure

```json
{
  "name": "oauth-sheriff-core",
  "build_systems": ["maven"],
  "paths": {
    "module": "oauth-sheriff-core",
    "descriptor": "oauth-sheriff-core/pom.xml",
    "sources": ["oauth-sheriff-core/src/main/java"],
    "tests": ["oauth-sheriff-core/src/test/java"],
    "readme": "oauth-sheriff-core/README.adoc"
  },
  "metadata": {
    "artifact_id": "oauth-sheriff-core",
    "group_id": "de.cuioss.sheriff.oauth",
    "packaging": "jar",
    "description": "Core OAuth Sheriff functionality",
    "profiles": []
  },
  "packages": {
    "de.cuioss.sheriff.oauth.core": {
      "path": "oauth-sheriff-core/src/main/java/de/cuioss/sheriff/oauth/core",
      "package_info": "oauth-sheriff-core/src/main/java/de/cuioss/sheriff/oauth/core/package-info.java"
    }
  },
  "dependencies": ["de.cuioss:cui-java-tools:compile"],
  "stats": {"source_files": 45, "test_files": 38},
  "commands": {
    "module-tests": "python3 ...",
    "verify": "python3 ...",
    "quality-gate": "python3 ..."
  }
}
```

### Fields

| Field | Description |
|-------|-------------|
| `name` | Module name (includes technology suffix for virtual modules) |
| `build_systems` | Array with single build system (e.g., `["maven"]` or `["npm"]`) |
| `paths` | Module paths (descriptor, sources, tests, readme) |
| `metadata` | Build-system specific metadata |
| `packages` | All packages with paths and package-info |
| `dependencies` | Full dependency list with scopes (see format below) |
| `stats` | File counts |
| `commands` | Available build commands (string values) |
| `virtual_module` | (Optional) Virtual module metadata for multi-tech directories |

### Dependency Format

Dependencies use technology-native format without prefixes:

| Build System | Format | Example |
|--------------|--------|---------|
| Maven | `groupId:artifactId:scope` | `de.cuioss:cui-java-tools:compile` |
| npm | `name:scope` | `lit:compile`, `@testing-library/dom:test` |

### Virtual Modules

When a directory contains multiple build systems (e.g., pom.xml +
package.json), discovery creates separate **virtual modules** with
technology suffixes instead of merging them. Each virtual module gets its
own per-module directory under `project-architecture/`.

```json
{
  "name": "nifi-cuioss-ui-maven",
  "build_systems": ["maven"],
  "virtual_module": {
    "physical_path": "nifi-cuioss-ui",
    "technology": "maven",
    "sibling_modules": ["nifi-cuioss-ui-npm"]
  },
  "paths": {
    "module": "nifi-cuioss-ui",
    "descriptor": "nifi-cuioss-ui/pom.xml",
    "sources": ["nifi-cuioss-ui/src/main/java"]
  },
  "dependencies": ["jakarta.servlet:jakarta.servlet-api:provided"],
  "commands": {
    "module-tests": "python3 .plan/execute-script.py pm-dev-java:..."
  }
}
```

The corresponding npm sibling lives at
`.plan/project-architecture/nifi-cuioss-ui-npm/derived.json` with
`build_systems: ["npm"]`.

**Virtual Module Fields:**

| Field | Description |
|-------|-------------|
| `physical_path` | Actual directory path (shared by siblings) |
| `technology` | Build system technology (`maven`, `npm`, `gradle`) |
| `sibling_modules` | List of other virtual modules from the same directory |

**Benefits of virtual modules:**
- Each module has a single build system (no ambiguity)
- Commands are strings (no nested technology selection)
- Skills by profile are technology-specific
- Task assignment targets a single technology

---

## Per-module `enriched.json`

Path: `.plan/project-architecture/{module}/enriched.json`

LLM-generated enrichments for one module. Seeded as an empty stub by
`architecture discover` and populated by `architecture init` and the
`architecture enrich *` commands.

### Structure

```json
{
  "responsibility": "Core JWT validation logic including claim extraction and signature verification",
  "responsibility_reasoning": "Derived from: README overview, ClaimValidator pattern",
  "purpose": "library",
  "purpose_reasoning": "packaging=jar, no runtime dependencies",
  "key_packages": {
    "de.cuioss.sheriff.oauth.core.pipeline": {
      "description": "JWT validation pipeline components",
      "components": ["ClaimValidator", "JwtPipeline", "ValidationResult"]
    }
  },
  "internal_dependencies": [],
  "key_dependencies": [
    "de.cuioss:cui-java-tools",
    "org.jspecify:jspecify"
  ],
  "key_dependencies_reasoning": "Foundation utilities and null-safety annotations",
  "skills_by_profile": {
    "implementation": {
      "defaults": [
        {"skill": "pm-dev-java:java-core", "description": "Core Java patterns"}
      ],
      "optionals": []
    }
  },
  "skills_by_profile_reasoning": "Plain Java library, no CDI/Quarkus runtime",
  "tips": ["Use @ApplicationScoped for singleton services"],
  "insights": ["Heavy validation happens in boundary layer"],
  "best_practices": ["Always validate tokens before extracting claims"]
}
```

### Fields

| Field | Description |
|-------|-------------|
| `responsibility` | Human-readable module description (1-2 sentences) |
| `responsibility_reasoning` | Sources used for derivation |
| `purpose` | Module classification (see values below) |
| `purpose_reasoning` | Analysis rationale |
| `key_packages` | Important packages with descriptions and components |
| `internal_dependencies` | Dependencies on other project modules |
| `key_dependencies` | Important external dependencies (no technology prefix) |
| `key_dependencies_reasoning` | Filtering rationale |
| `skills_by_profile` | Skills organized by execution profile (defaults/optionals shape) |
| `skills_by_profile_reasoning` | Selection and filtering rationale |
| `tips` | Implementation tips for working with the module |
| `insights` | Learned insights from implementation experience |
| `best_practices` | Established best practices for the module |

### Skills by Profile

The `skills_by_profile` field organizes skills by execution profile with a
defaults/optionals structure:

| Profile | Purpose |
|---------|---------|
| `implementation` | Skills for writing production code |
| `module_testing` | Skills for writing unit tests |
| `integration-testing` | Skills for integration tests (if applicable) |
| `benchmark-testing` | Skills for performance tests (if applicable) |

**Structure** (defaults/optionals with descriptions):

```json
{
  "skills_by_profile": {
    "implementation": {
      "defaults": [
        {
          "skill": "pm-plugin-development:plugin-architecture",
          "description": "Architecture principles for building marketplace components"
        }
      ],
      "optionals": [
        {
          "skill": "pm-plugin-development:plugin-script-architecture",
          "description": "Script development standards covering implementation patterns"
        }
      ]
    }
  }
}
```

**Resolution behaviour**:
- `defaults`: Always loaded for the profile.
- `optionals`: LLM-selected based on description match against deliverable
  context.

Skills are derived from configured domain skill sets. Query available
domains and their skills via:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config get-skills-by-profile --domain java
```

### Purpose Values

| Value | Description |
|-------|-------------|
| `library` | Reusable code, no runtime |
| `extension` | Framework plugin (Quarkus, NiFi) |
| `deployment` | Build-time processing |
| `runtime` | Application entry point |
| `parent` | Aggregator POM (packaging=pom at root) |
| `bom` | Bill of Materials |
| `integration-tests` | Integration test module |
| `benchmark` | Performance testing |

---

## Atomicity: tmp+swap protocol

`architecture discover --force` writes the entire layout to a sibling
staging directory before atomically replacing the live tree:

```
Step 1. Stage:    Build .plan/project-architecture.tmp/
                    ├── _project.json
                    ├── {module-1}/{derived,enriched}.json
                    └── {module-2}/{derived,enriched}.json
Step 2. Swap:     os.replace(project-architecture.tmp, project-architecture)
                  (after rmtree-ing the old tree if it existed)
```

**Guarantee**: An interrupt either before or after Step 2 leaves either the
old layout intact (interrupt before swap) or the new layout intact
(interrupt after swap). There is never a half-written `project-architecture/`
directory. Implementation lives in
[`_architecture_core.py:swap_data_dir`](../scripts/_architecture_core.py).

---

## Client API Mapping

The [client-api.md](client-api.md) merges `_project.json` and per-module
files for output:

| API Output | `_project.json` | `{module}/derived.json` | `{module}/enriched.json` |
|------------|-----------------|--------------------------|---------------------------|
| `module` (default) | — | paths, commands | responsibility, purpose, key_packages, internal_dependencies, key_dependencies, skills_by_profile |
| `module --full` | — | + packages, dependencies | + reasoning fields |
| `info` | name, description | build_systems (per module) | purpose (per module) |

---

## Field Summary

| Field | Source | Default Output | Full Output |
|-------|--------|----------------|-------------|
| `name` | `derived.json` | Yes | Yes |
| `build_systems` | `derived.json` | Yes | Yes |
| `paths` | `derived.json` | Yes | Yes |
| `metadata` | `derived.json` | Yes | Yes |
| `packages` | `derived.json` | No | Yes |
| `dependencies` | `derived.json` | No | Yes |
| `stats` | `derived.json` | Yes | Yes |
| `commands` | `derived.json` | Yes | Yes |
| `virtual_module` | `derived.json` | Yes | Yes |
| `responsibility` | `enriched.json` | Yes | Yes |
| `responsibility_reasoning` | `enriched.json` | No | Yes |
| `purpose` | `enriched.json` | Yes | Yes |
| `purpose_reasoning` | `enriched.json` | No | Yes |
| `key_packages` | `enriched.json` | Yes | Yes |
| `internal_dependencies` | `enriched.json` | Yes | Yes |
| `key_dependencies` | `enriched.json` | Yes | Yes |
| `key_dependencies_reasoning` | `enriched.json` | No | Yes |
| `skills_by_profile` | `enriched.json` | Yes | Yes |
| `skills_by_profile_reasoning` | `enriched.json` | No | Yes |
| `tips` | `enriched.json` | Yes | Yes |
| `insights` | `enriched.json` | Yes | Yes |
| `best_practices` | `enriched.json` | Yes | Yes |

---

## Module Graph Format

Output format for the `architecture graph` command. Returns module
dependencies as a tree.

### Purpose

Provides a view of internal module dependencies for:
- Ordering deliverables in multi-module tasks
- Identifying dependency chains
- Detecting circular dependencies

### Parameters

| Parameter | Description |
|-----------|-------------|
| `--full` | Include aggregator modules (pom-only parents with no source paths) |

By default, aggregator modules (pom packaging) are filtered out since they
contain no code to implement.

### Filtering Logic

Modules are included in the default view if ANY of these conditions are true:

1. **Non-pom packaging**: jar, war, nar, etc.
2. **is_leaf flag**: Enriched data explicitly marks the module as
   `is_leaf: true`.
3. **Leaf purpose**: Enriched data has `purpose` in
   `["integration-tests", "deployment", "benchmark"]`.

This allows test modules with pom packaging (like e2e-playwright) to appear
in the default view when their per-module `enriched.json` carries the
appropriate purpose.

### Output Format

**Single Module**:

```
status: success

module: my-module
```

**Multi-Module (Dependency Tree)**:

```
status: success

oauth-sheriff-quarkus-deployment
  - oauth-sheriff-core
    - oauth-sheriff-api
  - oauth-sheriff-quarkus
    - oauth-sheriff-core
```

The tree shows what each module depends on:
- `oauth-sheriff-quarkus-deployment` depends on `oauth-sheriff-core` and
  `oauth-sheriff-quarkus`.
- `oauth-sheriff-core` depends on `oauth-sheriff-api`.
- `oauth-sheriff-quarkus` depends on `oauth-sheriff-core`.

### Use Cases

**Ordering Deliverables**: Read the tree bottom-up for execution order:

1. `oauth-sheriff-api` — no dependencies, execute first.
2. `oauth-sheriff-core` — depends on api.
3. `oauth-sheriff-quarkus` — depends on core.
4. `oauth-sheriff-quarkus-deployment` — depends on quarkus and core.

Modules at the same tree depth with no cross-dependencies can execute in
parallel.

**Detecting Circular Dependencies**:

```
status: success

module-a

warning: circular_dependencies_detected
circular_dependencies[2]:
  - module-b
  - module-c
```

---

## Documentation Sources

Priority order for documentation sources when analyzing project
architecture. Documentation sources vary by technology domain — the
examples below include Java-specific patterns where noted; other domains
follow similar conventions with their native documentation formats.

### Project-Level Sources

Sources for understanding overall project structure and purpose.

| Priority | Source | Path Pattern | Content Type |
|----------|--------|--------------|--------------|
| 1 | Project README | `README.md`, `README.adoc` | Project overview, getting started |
| 2 | Architecture docs | `doc/architecture/*.adoc` | Architectural decisions, design |
| 3 | Module overview | `doc/modules.adoc` | Module relationships |
| 4 | ADR documents | `doc/adr/*.adoc` | Design decisions |

### Module-Level Sources

Sources for understanding individual module purpose and implementation.

| Priority | Source | Path Pattern | Content Type |
|----------|--------|--------------|--------------|
| 1 | Module README | `{module}/README.md` | Module overview |
| 2 | Package info | `{module}/src/main/java/**/package-info.java` | Package JavaDoc |
| 3 | Main class | Entry point class(es) | Implementation patterns |
| 4 | Test classes | `{module}/src/test/**/*Test.java` | Usage examples |

### Reading Strategy

**Project-Level Analysis**:

1. Start with `README.md` — often has architecture overview.
2. Check `doc/` directory for detailed documentation.
3. Review ADRs for design decisions that affect structure.

**Module-Level Analysis**:

1. Check the module README first — quickest understanding.
2. Read `package-info.java` for Java modules.
3. Sample 2-3 main source files for actual patterns.
4. Check test files for usage examples.

### Missing Documentation Handling

| Missing Source | Fallback Strategy |
|----------------|-------------------|
| Module README | Analyze source code directly |
| package-info.java | Use directory structure and class names |
| All docs | Infer from: parent module context, imports, annotations |

### Content Extraction

**From README Files**: Look for first paragraph (module purpose), "Overview"
or "Description" section, code examples (show usage patterns).

**From package-info.java** (Java-specific): Look for package-level JavaDoc
comment, `@see` references to related packages, links to documentation.

**From Source Files** (Java-specific examples, adapt for other languages):
Look for class-level JavaDoc (or equivalent doc comments), framework
annotations (`@Path`, `@Processor`, etc.), import statements (show
dependencies), method signatures (show capabilities).

### Output Integration

Documentation findings feed into the per-module `enriched.json`:

| Documentation Finding | Target Field |
|----------------------|--------------|
| Module purpose statement | `responsibility` |
| Module classification | `purpose` |
| Package descriptions | `key_packages.{pkg}.description` |
| Important dependencies | `key_dependencies` |
| Framework/library usage | `skills_by_profile` |

---

## Related

| Document | Purpose |
|----------|---------|
| [module-discovery.md](../../extension-api/standards/module-discovery.md) | Raw data field specification |
| [client-api.md](client-api.md) | API for reading merged data and consumer view |
