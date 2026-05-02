# Architecture Client API

Script API for consumers querying architectural data. Output in TOON format.

**For manage commands** (setup, read raw, enrich): See [manage-api.md](manage-api.md)

## Script Pattern

Following `{noun}.py {verb}` convention:

```
architecture.py {verb} [options]
```

**Invocation**:
```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture {verb} [options]
```

## Commands

### info

Get project summary with metadata, technologies, and module overview.

```bash
architecture.py info
```

**Output** (TOON):
```toon
project:
  name: oauth-sheriff
  description: JWT validation library for Quarkus
  root: /path/to/oauth-sheriff

technologies[1]:
  - maven

modules[4]{name,path,purpose}:
oauth-sheriff-parent,.,parent
oauth-sheriff-core,oauth-sheriff-core,library
oauth-sheriff-quarkus,oauth-sheriff-quarkus,extension
oauth-sheriff-quarkus-deployment,oauth-sheriff-quarkus-deployment,deployment
```

---

### modules

List available module names, optionally filtered by command availability.

```bash
architecture.py modules [--command COMMAND]
```

**Options**:
| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--command` | No | (none) | Filter to modules that provide this command |

**Output** (TOON, no filter):
```toon
modules[4]:
  - oauth-sheriff-parent
  - oauth-sheriff-core
  - oauth-sheriff-quarkus
  - oauth-sheriff-quarkus-deployment
```

**Output** (TOON, `--command verify`):
```toon
command: verify
modules[3]:
  - oauth-sheriff-core
  - oauth-sheriff-quarkus
  - oauth-sheriff-quarkus-deployment
```

**Use case**: Find which modules support a specific build command (e.g., `verify`, `module-tests`).

---

### graph

Get module dependency graph for ordering and parallelization.

```bash
architecture.py graph [--full]
```

**Parameters**:
- `--full`: Include aggregator modules (pom-only parents). By default, modules with no source paths are filtered out.

**Output**: See the "Module Graph Format" section in [architecture-persistence.md](architecture-persistence.md) for complete format specification.

**Single module output**:
```
status: success

module: my-module
```

**Multi-module output** (dependency tree):
```
status: success

oauth-sheriff-quarkus-integration-tests
  - oauth-sheriff-quarkus
    - oauth-sheriff-core
  - oauth-sheriff-quarkus-devui
    - oauth-sheriff-quarkus
```

Tree interpretation:
- Top-level nodes are **leaves** (nothing depends on them)
- Indented nodes are **dependencies** of the parent
- Deepest nodes are **roots** (depend on nothing internal)

**Use cases**:
- Order deliverables in multi-module tasks (execute deepest nodes first, work up to top-level)
- Identify modules that can run in parallel (same depth, no cross-dependencies)
- Detect circular dependencies (warning section if graph cannot be topologically sorted)

**Related**: For incremental graph queries that don't need the full topological dump, prefer `path`, `neighbors`, or `impact` (below). For a side-by-side comparison of two architecture snapshots, see [`diff-modules`](#diff-modules).

---

### path

BFS shortest path between two modules over the dependency graph.

```bash
architecture.py path SOURCE TARGET
```

**Arguments**:
| Argument | Required | Description |
|----------|----------|-------------|
| `SOURCE` | Yes | Starting module name |
| `TARGET` | Yes | Destination module name |

Edges are directed: there is an edge from `M` to `N` iff `N ∈ M.internal_dependencies`. The returned path therefore walks the "depends on" relation — each successor in the list is a direct dependency of its predecessor.

**Output** (TOON):
```toon
status: success
source: oauth-sheriff-quarkus-integration-tests
target: oauth-sheriff-core
path[3]:
  - oauth-sheriff-quarkus-integration-tests
  - oauth-sheriff-quarkus
  - oauth-sheriff-core
```

When `SOURCE == TARGET`, the path is a singleton `[SOURCE]`.

When `TARGET` is unreachable from `SOURCE`, `path` is rendered as `null`:
```toon
status: success
source: lefty
target: righty
path: null
```

When either module is unknown, the standard `Module not found` error envelope is returned.

**Use cases**:
- Justify why module A transitively depends on module B (audit trail)
- Identify the shortest refactor surface to break a dependency

---

### neighbors

N-hop neighborhood of a module over the dependency graph (forward edges).

```bash
architecture.py neighbors --module MODULE [--depth N]
```

**Options**:
| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--module` | Yes | - | Starting module name |
| `--depth` | No | 1 | Hop count. `0` returns just the module itself; values above the cap (8) are silently clamped. |

The closure walks the same "depends on" edges as `path`. The starting module is always included in the result; results are sorted alphabetically for determinism.

**Output** (TOON):
```toon
status: success
module: oauth-sheriff-quarkus-integration-tests
depth: 2
neighbors[4]:
  - oauth-sheriff-core
  - oauth-sheriff-quarkus
  - oauth-sheriff-quarkus-devui
  - oauth-sheriff-quarkus-integration-tests
```

The `depth` echoed in the response is the **clamped** value — useful when callers pass `--depth 999` and want to verify the actual horizon used.

**Use cases**:
- Bound the working set when refactoring a module (depth 1 = direct deps; depth 2 = deps of deps)
- Generate context for an LLM consumer that needs only the local neighborhood

---

### impact

Transitive reverse-dependency closure for a module.

```bash
architecture.py impact --module MODULE
```

**Options**:
| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--module` | Yes | - | Module whose impact set should be computed |

Returns every module `Y` such that the requested module appears in the transitive closure of `Y.internal_dependencies`. The starting module is excluded from its own impact set. Results are sorted alphabetically.

**Output** (TOON):
```toon
status: success
module: oauth-sheriff-core
impact[3]:
  - oauth-sheriff-quarkus
  - oauth-sheriff-quarkus-devui
  - oauth-sheriff-quarkus-integration-tests
```

A leaf module (nothing depends on it) returns an empty `impact` list.

**Use cases**:
- Estimate blast radius before changing a low-level module
- Identify which downstream modules need re-verification after a breaking change
- Pair with `neighbors` to bound both upstream and downstream working sets

---

### module

Get module information including description, paths, and commands.

```bash
architecture.py module [--module MODULE] [--full] [--budget N]
```

**Options**:
| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--module` | No | (root module) | Module name. Root module = module at project root (path "." or ""), or first module if no root exists. |
| `--full` | No | false | Include all fields (packages, dependencies, reasoning) |
| `--budget` | No | (none) | Render a markdown deep-dive bounded to this many lines. **Only honoured together with `--full`** — `--budget` without `--full` is a no-op (TOON output). |

**Output** (TOON, default):
```toon
module:
  name: oauth-sheriff-core
  responsibility: Core JWT validation logic
  purpose: library
  path: oauth-sheriff-core

paths:
  sources[1]:
    - src/main/java
  tests[1]:
    - src/test/java
  descriptor: pom.xml

key_packages[1]{name,description}:
de.cuioss.sheriff.oauth.core.pipeline,JWT validation pipeline

key_dependencies[2]:
  - io.quarkus:quarkus-core
  - org.eclipse.microprofile.jwt:microprofile-jwt-auth-api

internal_dependencies[0]:

skills_by_profile:
  implementation:
    defaults[1]{skill,description}:
      - pm-dev-java:java-core,"Core Java patterns including modern features and code quality"
    optionals[2]{skill,description}:
      - pm-dev-java:java-null-safety,"JSpecify null safety annotations with @NullMarked, @Nullable"
      - pm-dev-java:java-lombok,"Lombok patterns including @Delegate, @Builder, @Value"
  unit-testing:
    defaults[1]{skill,description}:
      - pm-dev-java:junit-core,"JUnit 5 testing patterns with AAA structure"
    optionals[0]{skill,description}:

commands[3]:
  - module-tests
  - verify
  - quality-gate
```

**Output** (TOON, `--full`):
```toon
module:
  name: oauth-sheriff-core
  responsibility: Core JWT validation logic
  responsibility_reasoning: Derived from README overview
  purpose: library
  purpose_reasoning: packaging=jar, no runtime dependencies
  path: oauth-sheriff-core

paths:
  sources[1]:
    - src/main/java
  tests[1]:
    - src/test/java
  descriptor: pom.xml

key_packages[1]{name,description}:
de.cuioss.sheriff.oauth.core.pipeline,JWT validation pipeline

packages[2]{name,path,has_package_info}:
de.cuioss.sheriff.oauth.core,src/main/java/de/cuioss/sheriff/oauth/core,true
de.cuioss.sheriff.oauth.core.util,src/main/java/de/cuioss/sheriff/oauth/core/util,false

key_dependencies[2]:
  - de.cuioss:cui-java-tools
  - org.jspecify:jspecify
key_dependencies_reasoning: Foundation utilities and null-safety annotations

dependencies[12]{artifact,scope}:
de.cuioss:cui-java-tools,compile
org.projectlombok:lombok,compile
...

internal_dependencies[0]:

skills_by_profile:
  implementation:
    defaults[1]{skill,description}:
      - pm-dev-java:java-core,"Core Java patterns including modern features"
    optionals[2]{skill,description}:
      - pm-dev-java:java-null-safety,"JSpecify null safety annotations"
      - pm-dev-java:java-lombok,"Lombok patterns for reducing boilerplate"
  unit-testing:
    defaults[1]{skill,description}:
      - pm-dev-java:junit-core,"JUnit 5 testing patterns"
    optionals[0]{skill,description}:
skills_by_profile_reasoning: Plain Java library, no CDI/Quarkus runtime

commands[3]:
  - module-tests
  - verify
  - quality-gate
```

#### module --full --budget

When `--full --budget N` is supplied, the command renders a **markdown** deep-dive (not TOON) bounded to roughly `N` lines. Sections in priority order: header (name, purpose, responsibility) > internal dependencies > key packages > skills_by_profile > tips/insights/best practices. When the rendered output exceeds `N` lines, trailing sections are dropped first and a marker is appended:

```
... (truncated to fit budget=N; full output requires --budget {required})
```

The starting module is validated up-front: an unknown module raises the standard `Module not found` error envelope (TOON) instead of the markdown contract.

**Determinism**: two consecutive invocations with the same arguments produce byte-identical output.

**Use cases**:
- Generate a token-bounded module summary for an LLM consumer
- Quick CLI inspection of a module without parsing the full TOON dump

---

### overview

Render a deterministic markdown summary of the project architecture.

```bash
architecture.py overview [--budget N]
```

**Options**:
| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--budget` | No | 200 | Maximum line count for the rendered output |

**Output**: markdown text (not TOON) consisting of, in priority order:

1. **Project header** — name + description (from `llm-enriched.json`)
2. **Modules** — table of `Module | Purpose | Responsibility`
3. **Adjacency** — table of `Module | Internal Dependencies`
4. **Skills by Profile** — per-module skill counts (omitted if no module has `skills_by_profile`)

**Truncation rule**: when the rendered output would exceed `--budget` lines, trailing sections are dropped one at a time (Skills first, then Adjacency, etc.) until the output fits, leaving room for a single marker line:

```
... (truncated to fit budget=N; full output requires --budget {required})
```

The Modules section has the highest priority and is preserved as long as any single section can fit.

**Determinism**: byte-identical on repeat invocations with the same arguments.

**No committed `OVERVIEW.md`**: by design, `overview` is render-on-demand. The output is **never** persisted into the working tree (no `OVERVIEW.md` artifact, no commit hook, no auto-write). Callers that need to inspect the overview redirect stdout themselves; the tool stays a pure read-only renderer.

**Use cases**:
- Provide an LLM consumer with a single-chunk architecture summary
- Smoke-test the architecture data after `architecture.py discover` / `enrich`
- Produce ad-hoc documentation snippets without committing duplicate files

---

### commands

Get available commands for a module.

```bash
architecture.py commands [--module MODULE]
```

**Options**:
| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--module` | No | (root module) | Module name |

**Output** (TOON):
```toon
module: oauth-sheriff-core

commands[5]{name,description}:
module-tests,Run unit tests for this module
verify,Full verification (compile + test + package)
quality-gate,Run static analysis and linting
clean,Clean build artifacts
install,Install to local repository
```

---

### resolve

Resolve a command to its executable form.

```bash
architecture.py resolve --command COMMAND [--module MODULE]
```

**Options**:
| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--command` | Yes | - | Command name to resolve |
| `--module` | No | (root module) | Module name |

**Output** (TOON):
```toon
module: oauth-sheriff-core
command: module-tests
executable: python3 .plan/execute-script.py plan-marshall:build-maven:maven run --module oauth-sheriff-core --targets test
```

**Hybrid module example** (both Maven and npm):
```toon
module: nifi-cuioss-ui
command: module-tests

executables[2]{build_system,command}:
maven,python3 .plan/execute-script.py plan-marshall:build-maven:maven run --module nifi-cuioss-ui --targets test
npm,python3 .plan/execute-script.py plan-marshall:build-npm:npm run --package nifi-cuioss-ui --targets test
```

---

## Command Summary

| Command | Purpose | Output |
|---------|---------|--------|
| `info` | Project overview | Project metadata + module list |
| `modules` | List modules | Module names, optionally filtered by `--command` |
| `graph` | Module dependency graph | Dependency tree for ordering |
| `path` | Shortest dependency path between two modules | TOON path list (or `null`) |
| `neighbors` | N-hop neighborhood of a module | TOON sorted module list |
| `impact` | Reverse-dependency closure | TOON sorted module list |
| `module` | Module details | Condensed (default), full (`--full`), or markdown (`--full --budget N`) |
| `overview` | Project architecture summary | Deterministic markdown |
| `commands` | Module commands | Command names with descriptions |
| `resolve` | Executable command | Full python3 invocation |

**Default vs Full**:
- Default: Key packages, key dependencies, proposed skill domains (no reasoning)
- `--full`: All packages, all dependencies, all reasoning fields

## Error Handling

**Module not found**:
```toon
error: Module not found
module: unknown-module
available[4]:
  - oauth-sheriff-parent
  - oauth-sheriff-core
  - oauth-sheriff-quarkus
  - oauth-sheriff-quarkus-deployment
```

**Command not found**:
```toon
error: Command not found
module: oauth-sheriff-core
command: unknown-command
available[5]:
  - module-tests
  - verify
  - quality-gate
  - clean
  - install
```

## Consumer View

The primary consumer is **solution-outline** during task planning.

| Question | Answer Source |
|----------|---------------|
| "Which module handles X?" | `responsibility`, `purpose` |
| "Where does new code go?" | `key_packages` descriptions + skill domains |
| "What depends on what?" | `internal_dependencies`, `key_dependencies` |
| "Which skills apply?" | `skills_by_profile` |

## Data Source

**Location**: `.plan/project-architecture/`

```
.plan/project-architecture/
├── derived-data.json  # Extension API output
└── llm-enriched.json  # LLM-enriched fields
```

See [architecture-persistence.md](architecture-persistence.md) for complete schema.

> **Persistence details**: See `standards/architecture-persistence.md` for the underlying storage schema.

Commands merge both files for output. If data does not exist, commands return error with instructions to run discovery first.
