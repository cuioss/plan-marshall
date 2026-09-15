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

```text
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture {verb} [options]
```

`{verb}` is a placeholder, so this block is fenced `text` rather than `bash`: a
`bash` fence declares a copyable invocation, and `documented-verb-set-drift`
reads every such fence as naming a real verb — a placeholder in one is reported
as a `phantom_documented_verb`, because no script registers a subcommand called
`{verb}`. See [../SKILL.md](../SKILL.md) § Canonical invocations for the
runnable per-verb blocks.

---

## Setup Commands

### discover

Run extension API discovery, classify the rewrite against the on-disk
descriptor tree, and write the requested part of it.

```bash
architecture.py discover [--force] [--regenerate-description] [--apply {all,plan,migration}]
```

**Options**:
| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--force` | No | false | Overwrite existing `project-architecture/` tree (atomic tmp+swap) |
| `--regenerate-description` | No | false | Blank the project `description` / `description_reasoning` instead of preserving the curated values |
| `--apply` | No | `all` | Which part of the regenerated tree is written: `all`, `plan` or `migration` (see § Attribution) |

The written layout (`_project.json` + per-module `enriched.json`) is staged
under `.plan/project-architecture.tmp/` and then `os.replace`-ed onto the live
path so the swap is atomic. What `--apply plan` / `--apply migration` stage is
specified in [architecture-persistence.md](architecture-persistence.md)
§ "Atomicity: tmp+swap protocol".

#### Attribution

Every call reads the on-disk pre-state (`_project.json` plus every module
`enriched.json`) before the crawl, builds the full regenerated tree in memory,
and decomposes the difference per document into delta classes. The class table
is declared once, as `DELTA_CLASSES` in `scripts/_descriptor_delta.py`; this is
its published form:

| Class | Attribution | Detected when |
|-------|-------------|---------------|
| `module_added` | plan | the live crawl holds the module and the pre-state has no `enriched.json` for it |
| `module_removed` | plan | the pre-state holds the module (document or index entry) and the live crawl does not |
| `extensions_used_changed` | plan | `_project.json` `extensions_used` differs |
| `generation_backfill` | migration | an existing document, or its index entry, had no `generation` header and receives one (`{by: architecture, tree_sha: null}` on the document; the document's header on the index entry) |
| `concept_type_backfill` | migration | an existing document had no `type` and receives the legacy default `module` |
| `key_packages_rekey` | migration | every `key_packages` difference is a dotted key replaced by its bridge path with a byte-identical value |
| `unclassified` | undecidable | any other field difference in an existing document, its index entry or `_project.json`, and any pre-state file that does not parse |

**Verdict** (`attribution`) — reduced from the observed classes:

| Verdict | When |
|---------|------|
| `no_baseline` | no `_project.json` on disk — nothing to compare against |
| `undecidable` | any `unclassified` class — dominates every other class |
| `mixed` | at least one plan class and at least one migration class |
| `plan_attributable` | plan classes only |
| `migration_only` | migration classes only |
| `clean` | no class — the regenerated tree carries nothing the pre-state lacks |

**Named residual.** A structural drift that predates the plan — an `origin/main`
index already lagging its tree — classifies as `plan`. It is real structural
knowledge the plan's tree carries, not a tool migration.

**What `--apply` writes:**

| `--apply` | Writes |
|-----------|--------|
| `all` (default) | The full regenerated tree on every call, whatever the verdict — `undecidable` and `no_baseline` included. `applied: all`. |
| `plan` | The pre-state plus the plan classes only. Nothing on `undecidable`, on `no_baseline`, or when no plan class exists; nothing when the projection equals the pre-state. `applied: plan` or `none`. |
| `migration` | The pre-state plus the migration classes only. Nothing on `undecidable`, on `no_baseline`, or when no migration class exists; nothing when the projection equals the pre-state. `applied: migration` or `none`. |

First-run discovery (`no_baseline`) therefore stays with `all`.

**Output fields**:
| Field | Description |
|-------|-------------|
| `status` | `success` (or `exists` without `--force` when `_project.json` is present) |
| `modules_discovered` | Modules in the live crawl |
| `output_file` | The `_project.json` path |
| `attribution` | The verdict |
| `applied` | `all`, `plan`, `migration`, or `none` when nothing was written |
| `delta_classes[]{class,attribution,module_count}` | Every observed class, in table order; `module_count` counts distinct modules, and a class seen only on `_project.json` top-level fields counts `0` |
| `unclassified_fields[]{document,field}` | Each difference no class explains; `document` is relative to `.plan/project-architecture/` |
| `unresolved_key_packages[]{module,key}` | `key_packages` keys the dotted→path migration kept dotted (no bridge, a non-resolving bridge path, or a target-key collision) |
| `unresolved_key_packages_count` | Length of `unresolved_key_packages` — `0` when every key resolved |
| `modules_examined` | Modules the classification compared (pre-state ∪ live crawl); `0` on `no_baseline` |

**Output (TOON)** — `--apply plan` over a generation back-fill plus a partial
re-key, no structural change:
```toon
status: success
modules_discovered: 3
output_file: .plan/project-architecture/_project.json
attribution: migration_only
applied: none
delta_classes[2]{class,attribution,module_count}:
  generation_backfill,migration,3
  key_packages_rekey,migration,1
unclassified_fields[0]:
unresolved_key_packages[1]{module,key}:
  api-sheriff,de.cuioss.sheriff.api
unresolved_key_packages_count: 1
modules_examined: 3
```

**Output (TOON)** — `--apply plan` over the same tree after a module was added:
```toon
status: success
modules_discovered: 4
output_file: .plan/project-architecture/_project.json
attribution: mixed
applied: plan
delta_classes[3]{class,attribution,module_count}:
  module_added,plan,1
  generation_backfill,migration,3
  key_packages_rekey,migration,1
unclassified_fields[0]:
unresolved_key_packages[1]{module,key}:
  api-sheriff,de.cuioss.sheriff.api
unresolved_key_packages_count: 1
modules_examined: 4
```

**Output (TOON)** — `--apply plan` when a curated field would change:
```toon
status: success
modules_discovered: 3
output_file: .plan/project-architecture/_project.json
attribution: undecidable
applied: none
delta_classes[2]{class,attribution,module_count}:
  generation_backfill,migration,3
  unclassified,undecidable,0
unclassified_fields[1]{document,field}:
  _project.json,description
unresolved_key_packages[0]:
unresolved_key_packages_count: 0
modules_examined: 3
```

---

### init

Initialize per-module `enriched.json` stubs for every module listed in
`_project.json`, preserving existing enrichment by default: only modules
whose stub is MISSING are seeded. The destructive blank-all is gated behind
`--reset`.

```bash
architecture.py init [--check] [--force] [--reset]
```

**Options**:
| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--check` | No | false | Check whether `_project.json` exists and how many per-module `enriched.json` stubs are present; output status only |
| `--force` | No | false | Re-seed only MISSING per-module `enriched.json` stubs, preserving existing enrichment |
| `--reset` | No | false | Blank ALL existing per-module `enriched.json` content back to the empty stub (destructive; honored together with `--force`) |

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

`_project.json` lives at the top of `.plan/project-architecture/` and holds
project identity plus the module index — a read-side pre-flight surface
(per-module `description` + `generation` header), **not** the discovery
gatekeeper (`iter_modules` crawls the live filesystem). Per-module files live
under `.plan/project-architecture/{module}/{derived,enriched}.json`.

| Command | Reads | Writes |
|---------|-------|--------|
| `discover` | Extension API, run-configuration.json, the on-disk `_project.json` + per-module `enriched.json` pre-state | `_project.json` + per-module `enriched.json` (via tmp+swap; `--apply plan` / `migration` write a projection or nothing) |
| `init` | `_project.json` | per-module `enriched.json` (one per module) + `_project.json` (batched index write-through) |
| `derived` | `_project.json` + per-module `derived.json` | - |
| `derived-module` | `_project.json` + `{module}/derived.json` | - |
| `enrich project` | `_project.json` | `_project.json` |
| `enrich module` | `{module}/enriched.json` | `{module}/enriched.json` + `_project.json` (index write-through) |
| `enrich package` | `{module}/enriched.json` | `{module}/enriched.json` + `_project.json` (index write-through) |
| `enrich skills` | `{module}/enriched.json` | `{module}/enriched.json` + `_project.json` (index write-through) |
| `enrich dependencies` | `{module}/enriched.json` | `{module}/enriched.json` + `_project.json` (index write-through) |
| `enrich tip` | `{module}/enriched.json` | `{module}/enriched.json` + `_project.json` (index write-through) |
| `enrich insight` | `{module}/enriched.json` | `{module}/enriched.json` + `_project.json` (index write-through) |
| `enrich best-practice` | `{module}/enriched.json` | `{module}/enriched.json` + `_project.json` (index write-through) |

---

## Orchestration Flow

`architecture.py` is a thin orchestrator for project structure discovery: it
invokes extension-api discovery, splits multi-technology paths into virtual
modules, and persists the result into `.plan/project-architecture/` via the
tmp+swap protocol. It delegates the work it does NOT own:

| Concern | Owner |
|---------|-------|
| Extension loading | `extension_discovery.py` |
| Module merging / virtual-module splitting | `_module_aggregation.py` |
| Command generation | Domain extensions |
| Build execution | Separate build workflow |

The discovery → enrichment → client sequence (DISCOVER → LOAD → ANALYZE →
PERSIST → CLIENT) is the step-by-step workflow in the manage-architecture
SKILL.md (Steps 1-9). The on-disk layout and the tmp+swap atomicity guarantee
are specified once in
[architecture-persistence.md](architecture-persistence.md) § Storage and
§ "Atomicity: tmp+swap protocol". Command resolution returns the complete
stored command string for the caller to execute directly — commands are stored
complete, never composed at resolution time.

---

## Related

| Document | Purpose |
|----------|---------|
| [client-api.md](client-api.md) | Client/consumer commands (merged data) |
| [architecture-persistence.md](architecture-persistence.md) | Storage format, module graph format, and documentation sources |
| `pm-dev-java:manage-maven-profiles` | Maven profile classification (loaded conditionally) |
