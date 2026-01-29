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
python3 .plan/execute-script.py plan-marshall:analyze-project-architecture:architecture {verb} [options]
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

**Output**: See [module-graph-format.md](module-graph-format.md) for complete format specification.

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

---

### module

Get module information including description, paths, and commands.

```bash
architecture.py module [--name NAME] [--full]
```

**Options**:
| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--name` | No | (root module) | Module name. Root module = module at project root (path "." or ""), or first module if no root exists. |
| `--full` | No | false | Include all fields (packages, dependencies, reasoning) |

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

---

### commands

Get available commands for a module.

```bash
architecture.py commands [--name NAME]
```

**Options**:
| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--name` | No | (root module) | Module name |

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
architecture.py resolve --command COMMAND [--name NAME]
```

**Options**:
| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--command` | Yes | - | Command name to resolve |
| `--name` | No | (root module) | Module name |

**Output** (TOON):
```toon
module: oauth-sheriff-core
command: module-tests
executable: python3 .plan/execute-script.py pm-dev-java:plan-marshall-plugin:maven run --module oauth-sheriff-core --targets test
```

**Hybrid module example** (both Maven and npm):
```toon
module: nifi-cuioss-ui
command: module-tests

executables[2]{build_system,command}:
maven,python3 .plan/execute-script.py pm-dev-java:plan-marshall-plugin:maven run --module nifi-cuioss-ui --targets test
npm,python3 .plan/execute-script.py pm-dev-frontend:plan-marshall-plugin:npm run --package nifi-cuioss-ui --targets test
```

---

## Command Summary

| Command | Purpose | Output |
|---------|---------|--------|
| `info` | Project overview | Project metadata + module list |
| `modules` | List modules | Module names, optionally filtered by `--command` |
| `graph` | Module dependency graph | Dependency tree for ordering |
| `module` | Module details | Condensed (default) or full (`--full`) |
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

## Data Source

**Location**: `.plan/project-architecture/`

```
.plan/project-architecture/
├── derived-data.json  # Extension API output
└── llm-enriched.json  # LLM-enriched fields
```

See [architecture-persistence.md](architecture-persistence.md) for complete schema.

Commands merge both files for output. If data does not exist, commands return error with instructions to run discovery first.
