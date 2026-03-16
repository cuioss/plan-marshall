# Orchestrator Integration

How manage-architecture orchestrates extension discovery, module aggregation, and command storage.

## Role of the Orchestrator

The `architecture.py` script acts as the thin orchestrator for project structure discovery. It delegates to the extension-api for module discovery and handles persistence to `derived-data.json`.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      ORCHESTRATOR RESPONSIBILITIES                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. Invoke extension-api discovery                                           │
│  2. Receive aggregated module data                                           │
│  3. Persist to derived-data.json                                             │
│  4. Provide client query interface                                           │
│                                                                              │
│  What the orchestrator does NOT do:                                          │
│  - Extension loading (delegated to extension_discovery.py)                   │
│  - Module merging (delegated to _module_aggregation.py)                      │
│  - Command generation (delegated to domain extensions)                       │
│  - Build execution (separate workflow)                                       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Discovery Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          DISCOVERY ORCHESTRATION                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  architecture.py discover --project-dir /path/to/project                     │
│                              │                                               │
│                              ▼                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ 1. EXTENSION DISCOVERY (extension_discovery.py)                     │    │
│  │                                                                     │    │
│  │    discover_extensions(project_root)                                │    │
│  │    → Scans plugin cache for extension.py files                     │    │
│  │    → Filters to extensions with discover_modules() method          │    │
│  │    → Returns: [{bundle, path, module}]                             │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                              │                                               │
│                              ▼                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ 2. MODULE DISCOVERY (per extension)                                 │    │
│  │                                                                     │    │
│  │    For each extension:                                              │    │
│  │      modules = extension.discover_modules(project_root)             │    │
│  │                                                                     │    │
│  │    pm-dev-java: Finds pom.xml/build.gradle, extracts metadata      │    │
│  │    pm-dev-frontend: Finds package.json, npm workspace detection    │    │
│  │                                                                     │    │
│  │    Returns: Module dicts with paths, metadata, commands            │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                              │                                               │
│                              ▼                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ 3. VIRTUAL MODULE SPLITTING (_module_aggregation.py)                │    │
│  │                                                                     │    │
│  │    When same path discovered by multiple extensions:                │    │
│  │      pom.xml + package.json at ./my-module/                        │    │
│  │                                                                     │    │
│  │    Split into virtual modules:                                      │    │
│  │      my-module-maven (build_systems: ["maven"])                    │    │
│  │      my-module-npm   (build_systems: ["npm"])                      │    │
│  │                                                                     │    │
│  │    Each module has:                                                 │    │
│  │      virtual_module.physical_path = "my-module"                    │    │
│  │      virtual_module.technology = "maven" | "npm"                   │    │
│  │      virtual_module.sibling_modules = ["my-module-npm"]            │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                              │                                               │
│                              ▼                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ 4. PERSISTENCE                                                      │    │
│  │                                                                     │    │
│  │    Write to: .plan/project-architecture/derived-data.json           │    │
│  │                                                                     │    │
│  │    {                                                                │    │
│  │      "project": {"name": "project-name"},                          │    │
│  │      "modules": {...},                                             │    │
│  │      "extensions_used": ["pm-dev-java", "pm-dev-frontend"]         │    │
│  │    }                                                                │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Module Aggregation Algorithm

The `_module_aggregation.py` module handles splitting when multiple extensions discover the same physical path.

### Decision Logic

```
For each unique path in discovered modules:

  IF only 1 module at path:
    → Keep as-is (single technology)

  IF multiple modules at path:
    → Split into virtual modules with technology suffixes
    → Use Maven module name as base (most canonical)
    → Track sibling relationships
```

### Example

```
Input (from two extensions):
  pm-dev-java discovered:   {name: "ui-core", path: "packages/ui-core", build_systems: ["maven"]}
  pm-dev-frontend discovered: {name: "ui-core", path: "packages/ui-core", build_systems: ["npm"]}

Output (after splitting):
  {
    "ui-core-maven": {
      "name": "ui-core-maven",
      "build_systems": ["maven"],
      "virtual_module": {
        "physical_path": "packages/ui-core",
        "technology": "maven",
        "sibling_modules": ["ui-core-npm"]
      },
      "commands": {
        "verify": "python3 ... maven run --command-args \"verify -pl ui-core\"",
        "module-tests": "..."
      }
    },
    "ui-core-npm": {
      "name": "ui-core-npm",
      "build_systems": ["npm"],
      "virtual_module": {
        "physical_path": "packages/ui-core",
        "technology": "npm",
        "sibling_modules": ["ui-core-maven"]
      },
      "commands": {
        "verify": "python3 ... npm run --command-args \"run build --workspace=packages/ui-core\"",
        "module-tests": "..."
      }
    }
  }
```

## Command Resolution

Commands are resolved through the orchestrator's client interface.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          COMMAND RESOLUTION                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  architecture.py resolve --command verify --name my-module                   │
│                              │                                               │
│                              ▼                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ 1. Load derived-data.json                                           │    │
│  │ 2. Find module by name                                              │    │
│  │ 3. Look up command in module.commands                               │    │
│  │ 4. Return complete command string                                   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                              │                                               │
│                              ▼                                               │
│  Output: "python3 .plan/execute-script.py pm-dev-java:plan-marshall-plugin: │
│           maven run --command-args \"verify -Ppre-commit -pl my-module\""    │
│                                                                              │
│  Key principle: Commands are STORED complete, not composed at resolution.   │
│  The caller executes the returned string directly.                          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Client Query Interface

The orchestrator provides read-only query commands for consumers.

| Command | Purpose |
|---------|---------|
| `architecture.py info` | Project summary with module list |
| `architecture.py modules` | List all module names |
| `architecture.py modules --command verify` | Filter modules by command availability |
| `architecture.py module --name X` | Module details (responsibility, commands) |
| `architecture.py graph` | Dependency graph with topological layers |
| `architecture.py resolve --command X --name Y` | Resolve command to executable |
| `architecture.py profiles` | Extract unique profile keys |

## Integration with Workflow

The orchestrator integrates with the planning workflow at specific points:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       WORKFLOW INTEGRATION POINTS                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  INIT (phase-1)                                                              │
│    marshall-steward calls: architecture.py discover                          │
│    Result: derived-data.json populated                                       │
│                                                                              │
│  REFINE (phase-2)                                                            │
│    (no architecture calls)                                                   │
│                                                                              │
│  SOLUTION OUTLINE (phase-3)                                                  │
│    outline agent calls: architecture.py module --name X                      │
│    Uses: module structure, dependencies for placement decisions              │
│                                                                              │
│  TASK PLAN (phase-4)                                                         │
│    task planner calls: architecture.py graph                                 │
│    Uses: topological layers for task ordering                                │
│                                                                              │
│  TASK EXECUTE (phase-5)                                                      │
│    task executor calls: architecture.py resolve --command X --name Y         │
│    Executes: returned command string                                         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Enrichment Workflow Phases

The manage-architecture skill follows a 5-phase enrichment workflow:

```
┌───────────┐    ┌───────────┐    ┌───────────┐    ┌───────────┐    ┌───────────┐
│  DISCOVER │───▶│   LOAD    │───▶│  ANALYZE  │───▶│  PERSIST  │───▶│  CLIENT   │
│           │    │           │    │           │    │           │    │           │
│ Extension │    │ derived + │    │ LLM reads │    │ Write to  │    │architecture│
│ API call  │    │ skills    │    │ docs/code │    │ llm-enrich│    │.py {verb} │
└───────────┘    └───────────┘    └───────────┘    └───────────┘    └───────────┘
      │                                                                   │
      ▼                                                                   ▼
derived-data.json                                              llm-enriched.json
```

1. **DISCOVER**: Extension API gathers raw module data (see Discovery Flow above)
2. **LOAD**: Read derived-data.json, determine domain skills from technologies
3. **ANALYZE**: LLM reads documentation/code to derive responsibility, purpose, key packages
4. **PERSIST**: Write enrichments to llm-enriched.json
5. **CLIENT**: Provide merged read access via `architecture.py {verb}`

See the manage-architecture SKILL.md for step-by-step execution instructions.

## File Locations

| File | Purpose |
|------|---------|
| `.plan/project-architecture/derived-data.json` | Extension API output (deterministic) |
| `.plan/project-architecture/llm-enriched.json` | LLM analysis (mutable) |

## Related Documents

| Document | Content |
|----------|---------|
| [architecture-persistence.md](architecture-persistence.md) | Storage format specification |
| [extension-api:build-execution.md](../../extension-api/standards/build-execution.md) | Build execution patterns and lifecycle |
