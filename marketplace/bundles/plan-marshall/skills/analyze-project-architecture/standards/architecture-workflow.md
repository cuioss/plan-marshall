# Architecture Analysis Workflow

High-level workflow for the analyze-project-architecture skill.

## Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      analyze-project-architecture                           │
│                                                                             │
│  ┌───────────┐    ┌───────────┐    ┌───────────┐    ┌───────────┐          │
│  │  DISCOVER │───▶│   LOAD    │───▶│  ANALYZE  │───▶│  PERSIST  │          │
│  │           │    │           │    │           │    │           │          │
│  │ Extension │    │ derived + │    │ LLM reads │    │ Write to  │          │
│  │ API call  │    │ skills    │    │ docs/code │    │ llm-enrich│          │
│  └───────────┘    └───────────┘    └───────────┘    └───────────┘          │
│        │                                                   │                │
│        ▼                                                   ▼                │
│  derived-data.json                                  llm-enriched.json       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
                               ┌───────────┐
                               │  CLIENT   │
                               │           │
                               │architecture│
                               │.py {verb} │
                               └───────────┘
```

---

## Phase 1: DISCOVER

**Purpose**: Gather raw project structure data via Extension API.

```
┌─────────────────────────────────────────────────────┐
│                     DISCOVER                         │
├─────────────────────────────────────────────────────┤
│                                                      │
│  Input:  Project root path                           │
│                                                      │
│  Action: python3 .plan/execute-script.py             │
│          plan-marshall:extension-api:extension_discovery │
│          discover-modules                            │
│                                                      │
│  Output: .plan/project-architecture/derived-data.json│
│                                                      │
│  Content:                                            │
│    - Module names and paths                          │
│    - Build systems (maven, npm, gradle)              │
│    - Source/test directories                         │
│    - All packages with paths                         │
│    - Full dependency lists                           │
│    - Available build commands                        │
│                                                      │
└─────────────────────────────────────────────────────┘
```

**Single script call encapsulates**:
1. Detect installed extensions (pm-dev-java, pm-dev-frontend)
2. Run each extension's discover function
3. Merge hybrid modules (same path, multiple build systems)
4. Write JSON output

---

## Phase 2: LOAD

**Purpose**: Load derived data and determine required domain skills.

```
┌─────────────────────────────────────────────────────┐
│                       LOAD                           │
├─────────────────────────────────────────────────────┤
│                                                      │
│  Input:  derived-data.json                           │
│                                                      │
│  Step 1: Read derived-data.json (script call)        │
│                                                      │
│  Step 2: Extract technologies from modules           │
│          - maven/gradle → pm-dev-java domain         │
│          - npm → pm-dev-frontend domain              │
│                                                      │
│  Step 3: Load domain skills for context              │
│          - pm-dev-java:java-core                     │
│          - pm-dev-java:javadoc                       │
│          - pm-dev-frontend:cui-javascript            │
│          - etc.                                      │
│                                                      │
│  Output: LLM context with:                           │
│          - Project structure data                    │
│          - Domain-specific knowledge                 │
│                                                      │
└─────────────────────────────────────────────────────┘
```

**Skill Resolution**:

| Technology | Domain Bundle | Skills to Load |
|------------|---------------|----------------|
| maven | pm-dev-java | java-core, javadoc, junit-core |
| gradle | pm-dev-java | java-core, javadoc, junit-core |
| npm | pm-dev-frontend | cui-javascript, cui-javascript-unit-testing |

**Resolution**: Query via script:
```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall-config:plan-marshall-config skill-domains list
```

---

## Phase 3: ANALYZE

**Purpose**: LLM analyzes documentation and code to enrich understanding.

```
┌─────────────────────────────────────────────────────┐
│                      ANALYZE                         │
├─────────────────────────────────────────────────────┤
│                                                      │
│  Input:  - derived-data.json (module structure)      │
│          - Domain skills (technology patterns)       │
│          - documentation-sources.md (reading guide)  │
│                                                      │
│  LLM Actions per module:                             │
│                                                      │
│  1. Read documentation (priority order):             │
│     - Module README                                  │
│     - package-info.java files                        │
│     - Sample source files                            │
│                                                      │
│  2. Derive semantic understanding:                   │
│     - responsibility: What does this module do?      │
│     - purpose: library|extension|deployment|...      │
│     - key_packages: Important packages + why         │
│     - internal_dependencies: Project module deps     │
│     - key_dependencies: Important external deps      │
│     - skills_by_profile: Which skills apply          │
│                                                      │
│  3. Record reasoning for each derivation             │
│                                                      │
│  Output: Enrichment data ready for persistence       │
│                                                      │
└─────────────────────────────────────────────────────┘
```

**Analysis Guide**: See [documentation-sources.md](documentation-sources.md) for reading priorities and fallback strategies.

---

## Phase 4: PERSIST

**Purpose**: Write LLM analysis to persistent storage.

```
┌─────────────────────────────────────────────────────┐
│                      PERSIST                         │
├─────────────────────────────────────────────────────┤
│                                                      │
│  Input:  LLM analysis results                        │
│                                                      │
│  Action: Write to                                    │
│          .plan/project-architecture/llm-enriched.json│
│                                                      │
│  Content per module:                                 │
│    - responsibility + reasoning                      │
│    - purpose + reasoning                             │
│    - key_packages (subset with descriptions)         │
│    - internal_dependencies                           │
│    - key_dependencies + reasoning                    │
│    - skills_by_profile + reasoning                   │
│                                                      │
│  Project level:                                      │
│    - description + reasoning                         │
│                                                      │
└─────────────────────────────────────────────────────┘
```

**Note**: Reasoning fields stored but only exposed via `--full` flag in client API.

---

## Phase 5: CLIENT

**Purpose**: Provide read access to merged architecture data.

```
┌─────────────────────────────────────────────────────┐
│                      CLIENT                          │
├─────────────────────────────────────────────────────┤
│                                                      │
│  Script: architecture.py {verb}                      │
│                                                      │
│  Input:  - derived-data.json (raw structure)         │
│          - llm-enriched.json (semantic analysis)     │
│                                                      │
│  Commands:                                           │
│    info     - Project overview                       │
│    modules  - List module names                      │
│    module   - Module details (--full for all)        │
│    commands - Available build commands               │
│    resolve  - Get executable command                 │
│                                                      │
│  Output: TOON format (token-efficient)               │
│                                                      │
│  Consumers:                                          │
│    - solution-outline (module placement)             │
│    - task-plan (command resolution)                  │
│    - LLM queries (project understanding)             │
│                                                      │
└─────────────────────────────────────────────────────┘
```

See [client-api.md](client-api.md) for complete command reference.

---

## Complete Data Flow

```
Extension API                    LLM Analysis
     │                                │
     ▼                                ▼
┌─────────────┐              ┌─────────────────┐
│ derived-    │              │  llm-enriched   │
│ data.json   │              │  .json          │
├─────────────┤              ├─────────────────┤
│ modules     │              │ responsibility  │
│ paths       │              │ purpose         │
│ packages    │              │ key_packages    │
│ dependencies│              │ internal_deps   │
│ commands    │              │ key_dependencies│
│             │              │ skill_domains   │
└─────────────┘              └─────────────────┘
        │                            │
        └──────────┬─────────────────┘
                   │ read both
                   ▼
            ┌─────────────┐
            │ architecture│
            │ .py {verb}  │
            └─────────────┘
                   │ merge
                   ▼
            ┌─────────────┐
            │   TOON      │
            │   Output    │
            └─────────────┘
```

---

## Related Documents

| Document | Purpose |
|----------|---------|
| [architecture-persistence.md](architecture-persistence.md) | Storage format specification |
| [client-api.md](client-api.md) | Script API reference |
| [client-view.md](client-view.md) | Consumer requirements |
| [documentation-sources.md](documentation-sources.md) | Analysis reading guide |
