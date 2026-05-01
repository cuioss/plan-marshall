# Architecture Manage API

Script API for managing architecture data. Used during the enrichment workflow.

## Purpose

These commands support the LLM enrichment workflow:
- Reading raw discovered data (per-module `derived.json` files only).
- Writing enrichment data (top-level `_project.json` for project-level
  fields, per-module `enriched.json` for module-scoped fields).

For client/consumer commands, see [client-api.md](client-api.md).

For the on-disk layout (`_project.json` + per-module `{derived,enriched}.json`)
and the atomic tmp+swap protocol used by `discover --force`, see
[architecture-persistence.md](architecture-persistence.md).

## Script Pattern

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture {verb} [options]
```

---

## Setup Commands

### discover

Run extension API discovery.

```bash
architecture.py discover [--force]
```

**Options**:
| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--force` | No | false | Overwrite existing `project-architecture/` tree (atomic tmp+swap) |

**Output (TOON)**:
```toon
status	success
modules_discovered	4
output_file	.plan/project-architecture/_project.json
```

The whole layout (`_project.json` + per-module `{derived,enriched}.json`)
is staged under `.plan/project-architecture.tmp/` and then `os.replace`-ed
onto the live path so the swap is atomic.

---

### init

Initialize per-module `enriched.json` stubs for every module listed in
`_project.json`.

```bash
architecture.py init [--check] [--force]
```

**Options**:
| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--check` | No | false | Check whether `_project.json` exists and how many per-module `enriched.json` stubs are present; output status only |
| `--force` | No | false | Overwrite existing per-module `enriched.json` stubs |

**Output (TOON)** - with `--check`:
```toon
status	exists
file	.plan/project-architecture/_project.json
modules_enriched	3
```

Or if `_project.json` does not exist:
```toon
status	missing
file	.plan/project-architecture/_project.json
```

**Output (TOON)** - without `--check`:
```toon
status	success
modules_initialized	4
output_file	.plan/project-architecture/_project.json
```

---

## Read Commands (Derived Data)

### derived

Read raw discovered data for all modules.

```bash
architecture.py derived
```

**Output (TOON)**:
```toon
project:
  name: oauth-sheriff
  root: /path/to/oauth-sheriff

modules[4]{name,path,build_systems,readme,description}:
oauth-sheriff-parent,.,maven,,Parent POM for OAuth Sheriff
oauth-sheriff-core,oauth-sheriff-core,maven,oauth-sheriff-core/README.adoc,Core validation library
oauth-sheriff-quarkus,oauth-sheriff-quarkus,maven,,
nifi-ui,nifi-ui,maven+npm,nifi-ui/README.md,NiFi frontend components
```

**Fields**:
| Field | Description |
|-------|-------------|
| `name` | Module name |
| `path` | Relative path from project root |
| `build_systems` | Build systems joined with `+` (e.g., `maven+npm`) |
| `readme` | README path if detected (empty if none) |
| `description` | Description from build file if available (empty if none) |

---

### derived-module

Read raw discovered data for a single module.

```bash
architecture.py derived-module --module MODULE
```

**Options**:
| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--module` | Yes | - | Module name |

**Output (TOON)**:
```toon
module:
  name: oauth-sheriff-core
  path: oauth-sheriff-core
  build_systems: maven

paths:
  readme: oauth-sheriff-core/README.adoc
  descriptor: oauth-sheriff-core/pom.xml
  sources[1]:
    - src/main/java
  tests[1]:
    - src/test/java

metadata:
  artifact_id: oauth-sheriff-core
  group_id: de.cuioss.sheriff.oauth
  packaging: jar
  description: Core OAuth Sheriff functionality

packages[3]{name,path,package_info}:
de.cuioss.sheriff.oauth.core,oauth-sheriff-core/src/main/java/de/cuioss/sheriff/oauth/core,oauth-sheriff-core/src/main/java/de/cuioss/sheriff/oauth/core/package-info.java
de.cuioss.sheriff.oauth.core.pipeline,oauth-sheriff-core/src/main/java/de/cuioss/sheriff/oauth/core/pipeline,
de.cuioss.sheriff.oauth.core.util,oauth-sheriff-core/src/main/java/de/cuioss/sheriff/oauth/core/util,

dependencies[12]:
  - de.cuioss:cui-java-tools:compile
  - org.projectlombok:lombok:compile
  - org.junit.jupiter:junit-jupiter:test
  ...

stats:
  source_files: 45
  test_files: 38

commands[3]:
  - module-tests
  - verify
  - quality-gate
```

---

## Write Commands (Enrichment)

### enrich project

Update project-level description.

```bash
architecture.py enrich project --description "..."
```

**Options**:
| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--description` | Yes | - | Project description (1-2 sentences) |

**Output (TOON)**:
```toon
status	success
updated	project.description
```

---

### enrich module

Update module responsibility and purpose.

```bash
architecture.py enrich module --name NAME --responsibility "..." [--purpose VALUE]
```

**Options**:
| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--name` | Yes | - | Module name |
| `--responsibility` | Yes | - | Module description (1-3 sentences) |
| `--purpose` | No | - | Module classification (see values below) |

**Purpose values**:
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

**Output (TOON)**:
```toon
status	success
module	oauth-sheriff-core
updated[2]:
  - responsibility
  - purpose
```

---

### enrich package

Add or update key package description.

```bash
architecture.py enrich package --module NAME --package PKG --description "..."
```

**Options**:
| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--module` | Yes | - | Module name |
| `--package` | Yes | - | Full package name |
| `--description` | Yes | - | Package description (1-2 sentences) |

**Output (TOON)**:
```toon
status	success
module	oauth-sheriff-core
package	de.cuioss.sheriff.oauth.core.pipeline
action	added
```

---

### enrich dependencies

Update key and internal dependencies.

```bash
architecture.py enrich dependencies --module NAME [--key "dep1,dep2,..."] [--internal "mod1,mod2,..."]
```

**Options**:
| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--module` | Yes | - | Module name |
| `--key` | No | - | Comma-separated key external dependencies |
| `--internal` | No | - | Comma-separated internal module dependencies |

**Output (TOON)**:
```toon
status	success
module	oauth-sheriff-quarkus
key_dependencies[2]:
  - io.quarkus:quarkus-core
  - de.cuioss:cui-java-tools
internal_dependencies[1]:
  - oauth-sheriff-core
```

---

### enrich tip

Add implementation tip to a module.

```bash
architecture.py enrich tip --module NAME --tip "..."
```

**Options**:
| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--module` | Yes | - | Module name |
| `--tip` | Yes | - | Implementation tip |

**Output (TOON)**:
```toon
status	success
module	oauth-sheriff-core
tips[3]:
  - Use @ApplicationScoped for singleton services
  - Prefer constructor injection over field injection
  - New tip added here
```

---

### enrich insight

Add learned insight to a module.

```bash
architecture.py enrich insight --module NAME --insight "..."
```

**Options**:
| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--module` | Yes | - | Module name |
| `--insight` | Yes | - | Learned insight from implementation |

**Output (TOON)**:
```toon
status	success
module	oauth-sheriff-core
insights[2]:
  - Heavy validation happens in boundary layer
  - New insight added here
```

---

### enrich best-practice

Add best practice to a module.

```bash
architecture.py enrich best-practice --module NAME --practice "..."
```

**Options**:
| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--module` | Yes | - | Module name |
| `--practice` | Yes | - | Established best practice |

**Output (TOON)**:
```toon
status	success
module	oauth-sheriff-core
best_practices[2]:
  - Always validate tokens before extracting claims
  - New best practice added here
```

---

## Error Handling

### Module Not Found

```toon
error	Module not found
module	unknown-module
available[4]:
  - oauth-sheriff-parent
  - oauth-sheriff-core
  - oauth-sheriff-quarkus
  - oauth-sheriff-quarkus-deployment
```

### Data Files Missing

```toon
error	Derived data not found
resolution	Run 'architecture.py discover' first
expected_file	.plan/project-architecture/_project.json
```

---

## Data Sources

`_project.json` lives at the top of `.plan/project-architecture/` and acts
as the source of truth for the module index. Per-module files live under
`.plan/project-architecture/{module}/{derived,enriched}.json`.

| Command | Reads | Writes |
|---------|-------|--------|
| `discover` | Extension API, run-configuration.json | `_project.json` + per-module `{derived,enriched}.json` (via tmp+swap) |
| `init` | `_project.json` | per-module `enriched.json` (one per module) |
| `derived` | `_project.json` + per-module `derived.json` | - |
| `derived-module` | `_project.json` + `{module}/derived.json` | - |
| `enrich project` | `_project.json` | `_project.json` |
| `enrich module` | `{module}/enriched.json` | `{module}/enriched.json` |
| `enrich package` | `{module}/enriched.json` | `{module}/enriched.json` |
| `enrich skills` | `{module}/enriched.json` | `{module}/enriched.json` |
| `enrich dependencies` | `{module}/enriched.json` | `{module}/enriched.json` |
| `enrich tip` | `{module}/enriched.json` | `{module}/enriched.json` |
| `enrich insight` | `{module}/enriched.json` | `{module}/enriched.json` |
| `enrich best-practice` | `{module}/enriched.json` | `{module}/enriched.json` |

---

## Orchestration Flow

The `architecture.py` script acts as the thin orchestrator for project
structure discovery. It delegates to the extension-api for module discovery
and persists results into the per-module layout under
`.plan/project-architecture/` (top-level `_project.json` plus per-module
`{derived,enriched}.json`).

### Orchestrator Responsibilities

```
1. Invoke extension-api discovery
2. Receive aggregated module data
3. Stage the new layout under .plan/project-architecture.tmp/ and
   atomically swap it onto .plan/project-architecture/
4. Provide client query interface

What the orchestrator does NOT do:
- Extension loading (delegated to extension_discovery.py)
- Module merging (delegated to _module_aggregation.py)
- Command generation (delegated to domain extensions)
- Build execution (separate workflow)
```

### Discovery Flow

```
architecture.py discover --project-dir /path/to/project
                            │
                            ▼
  1. EXTENSION DISCOVERY (extension_discovery.py)
     discover_applicable_extensions(project_root)
     → Scans plugin cache for extension.py files
     → Filters to extensions with discover_modules() method
     → Returns: [{bundle, path, module}]
                            │
                            ▼
  2. MODULE DISCOVERY (per extension)
     For each extension:
       modules = extension.discover_modules(project_root)
     pm-dev-java: Finds pom.xml/build.gradle, extracts metadata
     pm-dev-frontend: Finds package.json, npm workspace detection
     Returns: Module dicts with paths, metadata, commands
                            │
                            ▼
  3. VIRTUAL MODULE SPLITTING (_module_aggregation.py)
     When same path discovered by multiple extensions:
       pom.xml + package.json at ./my-module/
     Split into virtual modules:
       my-module-maven (build_systems: ["maven"])
       my-module-npm   (build_systems: ["npm"])
                            │
                            ▼
  4. PERSISTENCE (tmp+swap)
     Stage: .plan/project-architecture.tmp/
              ├── _project.json
              └── {module}/{derived,enriched}.json   (one dir per module)
     Swap:  os.replace(.tmp, .plan/project-architecture/)
```

### Module Aggregation Algorithm

The `_module_aggregation.py` module handles splitting when multiple extensions discover the same physical path.

```
For each unique path in discovered modules:

  IF only 1 module at path:
    → Keep as-is (single technology)

  IF multiple modules at path:
    → Split into virtual modules with technology suffixes
    → Use Maven module name as base (most canonical)
    → Track sibling relationships
```

### Command Resolution

```
architecture.py resolve --command verify --module my-module
                            │
                            ▼
  1. Load _project.json + {module}/derived.json
  2. Find module by name (validated against the _project.json index)
  3. Look up command in derived.commands
  4. Return complete command string

Key principle: Commands are STORED complete, not composed at resolution.
The caller executes the returned string directly.
```

### Workflow Integration Points

```
INIT (phase-1)
  marshall-steward calls: architecture.py discover
  Result: _project.json + per-module {derived,enriched}.json populated

REFINE (phase-2)
  (no architecture calls)

SOLUTION OUTLINE (phase-3)
  outline agent calls: architecture.py module --module X
  Uses: module structure, dependencies for placement decisions

TASK PLAN (phase-4)
  task planner calls: architecture.py graph
  Uses: topological layers for task ordering

TASK EXECUTE (phase-5)
  task executor calls: architecture.py resolve --command X --module Y
  Executes: returned command string
```

### Enrichment Workflow Phases

```
DISCOVER → LOAD → ANALYZE → PERSIST → CLIENT

1. DISCOVER: Extension API gathers raw module data
2. LOAD: Iterate _project.json + per-module derived.json, determine domain
   skills from technologies
3. ANALYZE: LLM reads docs/code to derive responsibility, purpose, key packages
4. PERSIST: Write enrichments to per-module enriched.json (project-level
   description writes to _project.json)
5. CLIENT: Provide merged read access via architecture.py {verb}
```

See the manage-architecture SKILL.md for step-by-step execution instructions.

---

## Related

| Document | Purpose |
|----------|---------|
| [client-api.md](client-api.md) | Client/consumer commands (merged data) |
| [architecture-persistence.md](architecture-persistence.md) | Storage format, module graph format, and documentation sources |
| `pm-dev-java:manage-maven-profiles` | Maven profile classification (loaded conditionally) |
