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
│  │ 1c. Virtual Module Splitting                                        │    │
│  │                                                                     │    │
│  │ When multiple extensions discover same path:                        │    │
│  │   pom.xml + package.json in same directory                         │    │
│  │   → Split into separate virtual modules with tech suffixes         │    │
│  │     e.g., app-maven + app-npm                                      │    │
│  │                                                                     │    │
│  │ Each virtual module has:                                            │    │
│  │   - Single build_systems entry (e.g., ["maven"])                   │    │
│  │   - String commands (not nested)                                    │    │
│  │   - virtual_module metadata:                                        │    │
│  │     {physical_path, technology, sibling_modules}                   │    │
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
│                    2. PERSISTENCE (manage-architecture skill)                │
│                                                                              │
│  architecture.py discover                                                    │
│                                                                              │
│  Thin orchestrator:                                                          │
│    - Calls discover_project_modules()                                        │
│    - Adds project_root to result                                             │
│    - Writes to .plan/project-architecture/derived-data.json                  │
│                                                                              │
│  Output: .plan/project-architecture/derived-data.json                        │
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
│  manage-architecture skill: discover + LLM enrichment               │
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

## extension_discovery.py API

| Function | Purpose | Used By |
|----------|---------|---------|
| `discover_project_modules(root)` | **Primary API**: Discover + split virtual modules | manage-architecture |
| `discover_all_extensions()` | List all bundles with extensions | manage-config |
| `discover_extensions(root)` | List applicable extensions | manage-config |
| `get_skill_domains_from_extensions()` | Skill domain metadata | manage-config |
| `get_workflow_extensions_from_extensions()` | Triage/outline refs | manage-config |

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
| `.plan/project-architecture/derived-data.json` | `manage-architecture` | Merged module data (includes commands) |
| `.plan/project-architecture/llm-enriched.json` | `manage-architecture` | LLM-enriched structure with descriptions |

## Library Responsibilities

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         EXTENSION-API (plan-marshall)                        │
│                                                                              │
│  extension_base.py       │ Abstract base class, canonical commands          │
│  extension_discovery.py  │ Extension discovery, loading, config defaults    │
│  _build_discover.py      │ Descriptor discovery, path building              │
│  _build_result.py        │ Log file creation, result construction           │
│  _build_parse.py         │ Issue structures, warning filtering              │
│  _build_format.py        │ TOON and JSON output formatting                  │
│  _build_wrapper.py       │ Build tool wrapper detection                     │
│  _module_aggregation.py  │ Virtual module splitting                         │
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

### Virtual Modules (After Splitting)

When `discover_project_modules()` splits modules from multiple extensions at the same path:

```json
{
  "name": "my-app-maven",
  "build_systems": ["maven"],
  "virtual_module": {
    "physical_path": "my-app",
    "technology": "maven",
    "sibling_modules": ["my-app-npm"]
  },
  "paths": {
    "module": "my-app",
    "descriptor": "my-app/pom.xml",
    "sources": ["my-app/src/main/java"],
    "tests": ["my-app/src/test/java"]
  },
  "commands": {
    "module-tests": "python3 .plan/execute-script.py plan-marshall:build-maven:maven run --command-args \"test -pl my-app\"",
    "verify": "python3 .plan/execute-script.py plan-marshall:build-maven:maven run --command-args \"verify -pl my-app\""
  }
}
```

**Splitting rules**:
- Each virtual module has a single `build_systems` entry
- Commands are strings (not nested by build system)
- `virtual_module` metadata links siblings sharing the same physical path

## Default Module

The **default module** represents the project root directory:
- `path: "."` - The project root
- `name: "default"` - Reserved module name
- Commands without `--module` flag - Operates on entire project

For single-module projects, the default module is the only module.

## Invocation

```bash
# Discover modules and persist to derived-data.json
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture discover \
  --project-dir /path/to/project

# Output merged structure as TOON
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture info
```

## Related Specifications

| Document | Purpose |
|----------|---------|
| [extension-contract.md](extension-contract.md) | Extension API methods |
| [build-project-structure.md](build-project-structure.md) | discover_modules() output structure |
| [build-base-libs.md](build-base-libs.md) | Base library API reference |
| [canonical-commands.md](canonical-commands.md) | Command vocabulary |
