# Extension API Architecture Overview

How modules are discovered, merged, and persisted.

## System Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    1. MODULE DISCOVERY (extension-api)                       │
│                                                                              │
│  extension.discover_project_modules(project_root)                            │
│                                                                              │
│  Single entry point that handles everything:                                 │
│    1a. Discovers applicable extensions                                       │
│    1b. Calls discover_modules() on each                                      │
│    1c. Merges hybrid modules (same path from multiple extensions)            │
│    1d. Returns final merged structure                                        │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ 1a. Extension Discovery                                             │    │
│  │                                                                     │    │
│  │ Scans plugin cache for bundles with extension.py:                  │    │
│  │   ~/.claude/plugins/cache/plan-marshall/{bundle}/*/skills/         │    │
│  │     plan-marshall-plugin/extension.py                               │    │
│  │                                                                     │    │
│  │ Filters to applicable extensions (have descriptors in project)     │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                              │                                               │
│                              ▼                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ 1b. Module Discovery (per extension)                                │    │
│  │                                                                     │    │
│  │ Each extension's discover_modules():                                │    │
│  │   - Finds its descriptors (pom.xml, package.json, etc.)            │    │
│  │   - Extracts metadata via build tools                               │    │
│  │   - Returns commands per module                                     │    │
│  │   - Returns [] if no descriptors found (no-op)                     │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                              │                                               │
│                              ▼                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ 1c. Hybrid Module Merging                                           │    │
│  │                                                                     │    │
│  │ When multiple extensions discover same module (by path):            │    │
│  │   pom.xml + package.json in same directory                         │    │
│  │   → Merge into single module with build_systems: [maven, npm]      │    │
│  │                                                                     │    │
│  │ Merge rules:                                                        │    │
│  │   - build_systems arrays merged                                     │    │
│  │   - paths.sources, paths.tests (concatenate)                        │    │
│  │   - commands (nest by build system for conflicts)                   │    │
│  │   - dependencies (deduplicate)                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                              │                                               │
│                              ▼                                               │
│  Returns:                                                                    │
│  {                                                                           │
│    "modules": { "mod-a": {...}, "mod-b": {...} },                           │
│    "extensions_used": ["pm-dev-java", "pm-dev-frontend"]                    │
│  }                                                                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    2. PERSISTENCE (project-structure skill)                  │
│                                                                              │
│  manage_project_structure.py collect-raw-data                                │
│                                                                              │
│  Thin orchestrator:                                                          │
│    - Calls discover_project_modules()                                        │
│    - Adds project_root to result                                             │
│    - Writes to .plan/raw-project-data.json                                   │
│                                                                              │
│  Output: .plan/raw-project-data.json                                         │
│  {                                                                           │
│    "project_root": "/path/to/project",                                       │
│    "modules": { "mod-a": {...}, "mod-b": {...} },                           │
│    "extensions_used": ["pm-dev-java", "pm-dev-frontend"]                    │
│  }                                                                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         3. STRUCTURE ENRICHMENT                              │
│                                                                              │
│  analyze-project-architecture skill: discover + LLM enrichment               │
│                                                                              │
│  Reads: .plan/project-architecture/derived-data.json                         │
│  Writes: .plan/project-architecture/llm-enriched.json                        │
│                                                                              │
│  {                                                                           │
│    "project": { "description": "..." },                                      │
│    "modules": {                                                              │
│      "mod-a": {                                                              │
│        "responsibility": "Core business logic for...",     ← LLM enriched   │
│        "purpose": "library",                               ← LLM enriched   │
│        "key_packages": {                                                     │
│          "com.example.core": {                                               │
│            "description": "Provides..."                    ← LLM enriched   │
│          }                                                                   │
│        },                                                                    │
│        "skills_by_profile": {"implementation": [...]}     ← LLM enriched   │
│      }                                                                       │
│    }                                                                         │
│  }                                                                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow Summary

| Step | Input | Process | Output |
|------|-------|---------|--------|
| 1. Module Discovery | project_root | `discover_project_modules()` | Merged module dict |
| 2. Persistence | Merged dict | Write to architecture dir | `.plan/project-architecture/derived-data.json` |
| 3. Enrichment | derived-data.json | LLM analysis | `.plan/project-architecture/llm-enriched.json` |

## extension.py API

| Function | Purpose | Used By |
|----------|---------|---------|
| `discover_project_modules(root)` | **Primary API**: Discover + merge modules | analyze-project-architecture |
| `discover_all_extensions()` | List all bundles with extensions | plan-marshall-config |
| `discover_extensions(root)` | List applicable extensions | plan-marshall-config |
| `get_skill_domains_from_extensions()` | Skill domain metadata | plan-marshall-config |
| `get_workflow_extensions_from_extensions()` | Triage/outline refs | plan-marshall-config |

## Command Resolution

Commands are resolved at two levels:

| Level | Location | Purpose |
|-------|----------|---------|
| **Vocabulary** | [canonical-commands.md](canonical-commands.md) | Canonical names (module-tests, quality-gate, verify) |
| **Resolution** | `extension.discover_modules()` | Build-system-specific commands per module |

**Required commands** (must exist for non-pom modules):
- `module-tests` - Unit tests
- `quality-gate` - Static analysis, linting
- `verify` - Full verification

## Key Files

| File | Owner | Purpose |
|------|-------|---------|
| `.plan/project-architecture/derived-data.json` | `analyze-project-architecture` | Merged module data (includes commands) |
| `.plan/project-architecture/llm-enriched.json` | `analyze-project-architecture` | LLM-enriched structure with descriptions |

## Library Responsibilities

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         EXTENSION-API (plan-marshall)                        │
│                                                                              │
│  extension_base.py   │ Abstract base class, canonical commands              │
│  extension.py        │ Extension discovery, module aggregation, merging     │
│  build_discover.py   │ Descriptor discovery, path building                  │
│  build_result.py     │ Log file creation, result construction               │
│  build_parse.py      │ Issue structures, warning filtering                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                   │
                                   │ used by
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DOMAIN EXTENSIONS                                    │
│                                                                              │
│  pm-dev-java/extension.py       │ Maven/Gradle: discover_modules()          │
│  pm-dev-frontend/extension.py   │ npm: discover_modules()                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ called by
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ANALYZE-PROJECT-ARCHITECTURE (thin orchestrator)          │
│                                                                              │
│  architecture.py                                                             │
│    discover          │ Calls discover_project_modules(), writes JSON        │
│    init              │ Create llm-enriched.json template                    │
│    info              │ Output merged structure as TOON                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Module Data Structure

### Single-Technology Module

Each extension returns modules with `build_systems` array:

```json
{
  "name": "module-name",
  "build_systems": ["maven"],
  "paths": {
    "module": "relative/path",
    "descriptor": "relative/path/pom.xml",
    "sources": ["src/main/java"],
    "tests": ["src/test/java"],
    "readme": "README.adoc"
  },
  "metadata": {
    "artifact_id": "...",
    "group_id": "...",
    "packaging": "jar",
    "profiles": [{"id": "...", "canonical": "...", "activation": {...}}]
  },
  "packages": {
    "com.example.core": {"path": "...", "package_info": "..."}
  },
  "dependencies": ["groupId:artifactId:scope"],
  "stats": {"source_files": 45, "test_files": 38},
  "commands": {
    "module-tests": "python3 .plan/execute-script.py ...",
    "quality-gate": "...",
    "verify": "..."
  }
}
```

### Hybrid Module (After Merge)

When `discover_project_modules()` merges modules from multiple extensions:

```json
{
  "name": "hybrid-module",
  "build_systems": ["maven", "npm"],
  "paths": {
    "module": "relative/path",
    "descriptors": ["pom.xml", "package.json"],
    "sources": ["src/main/java", "src/main/js"],
    "tests": ["src/test/java", "src/test/js"]
  },
  "commands": {
    "module-tests": {
      "maven": "python3 ... --module hybrid-module",
      "npm": "python3 ... --package hybrid-module"
    },
    "quality-gate": {
      "maven": "...",
      "npm": "..."
    },
    "lint": "python3 ... --package hybrid-module"
  }
}
```

**Command merging rules**:
- Both extensions provide same command → nested object by build system
- Only one extension provides command → string value

## Default Module

The **default module** represents the project root directory:
- `path: "."` - The project root
- `name: "default"` - Reserved module name
- Commands without `--module` flag - Operates on entire project

For single-module projects, the default module is the only module.

## Invocation

```bash
# Collect raw data (calls discover_project_modules internally)
python3 .plan/execute-script.py plan-marshall:project-structure:manage_project_structure \
  collect-raw-data --project-root /path/to/project

# Generate enrichable structure
python3 .plan/execute-script.py plan-marshall:project-structure:manage_project_structure \
  generate
```

## Related Specifications

| Document | Purpose |
|----------|---------|
| [extension-contract.md](extension-contract.md) | Extension API methods |
| [build-project-structure.md](build-project-structure.md) | discover_modules() output structure |
| [build-base-libs.md](build-base-libs.md) | Base library API reference |
| [canonical-commands.md](canonical-commands.md) | Command vocabulary |
