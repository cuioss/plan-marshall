# Architecture Manage API

Script API for managing architecture data. Used during the enrichment workflow.

## Purpose

These commands support the LLM enrichment workflow:
- Reading raw discovered data (derived-data.json only)
- Writing enrichment data (llm-enriched.json)

For client/consumer commands, see [client-api.md](client-api.md).

## Script Pattern

```bash
python3 .plan/execute-script.py plan-marshall:analyze-project-architecture:architecture {verb} [options]
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
| `--force` | No | false | Overwrite existing derived-data.json |

**Output (TOON)**:
```toon
status	success
modules_discovered	4
output_file	.plan/project-architecture/derived-data.json
```

---

### init

Initialize llm-enriched.json template from derived-data.json.

```bash
architecture.py init [--check] [--force]
```

**Options**:
| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--check` | No | false | Check if llm-enriched.json exists, output status only |
| `--force` | No | false | Overwrite existing llm-enriched.json |

**Output (TOON)** - with `--check`:
```toon
status	exists
file	.plan/project-architecture/llm-enriched.json
modules_enriched	3
```

Or if file doesn't exist:
```toon
status	missing
file	.plan/project-architecture/llm-enriched.json
```

**Output (TOON)** - without `--check`:
```toon
status	success
modules_initialized	4
output_file	.plan/project-architecture/llm-enriched.json
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
architecture.py derived-module --name NAME
```

**Options**:
| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--name` | Yes | - | Module name |

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
expected_file	.plan/project-architecture/derived-data.json
```

---

## Data Sources

| Command | Reads | Writes |
|---------|-------|--------|
| `discover` | Extension API, run-configuration.json | derived-data.json |
| `init` | derived-data.json | llm-enriched.json |
| `derived` | derived-data.json | - |
| `derived-module` | derived-data.json | - |
| `enrich project` | llm-enriched.json | llm-enriched.json |
| `enrich module` | llm-enriched.json | llm-enriched.json |
| `enrich package` | llm-enriched.json | llm-enriched.json |
| `enrich skills` | llm-enriched.json | llm-enriched.json |
| `enrich dependencies` | llm-enriched.json | llm-enriched.json |
| `enrich tip` | llm-enriched.json | llm-enriched.json |
| `enrich insight` | llm-enriched.json | llm-enriched.json |
| `enrich best-practice` | llm-enriched.json | llm-enriched.json |

---

## Related Documents

| Document | Purpose |
|----------|---------|
| [client-api.md](client-api.md) | Client/consumer commands (merged data) |
| [architecture-persistence.md](architecture-persistence.md) | Storage format specification |
| [architecture-workflow.md](architecture-workflow.md) | Workflow phases |
| `pm-dev-java:maven-profile-management` | Maven profile classification (loaded conditionally) |
