---
name: ref-workflow-architecture
description: Centralized architecture documentation for the plan-marshall bundle with visual diagrams
user-invocable: false
---

# Plan-Marshall Architecture

**Role**: Central architecture reference for the plan-marshall bundle. Provides visual documentation of the 6-phase execution model, thin agent pattern, and data layer.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                         PLAN-MARSHALL ARCHITECTURE                            │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                      6-PHASE EXECUTION MODEL                          │  │
│  │                                                                       │  │
│  │  1-init → 2-refine → 3-outline → 4-plan → 5-execute ──┐             │  │
│  │                                                ↑        │             │  │
│  │                                                │   [findings?]        │  │
│  │                                                │    ↓       ↓         │  │
│  │                                                │  yes      no         │  │
│  │                                                │   ↓        ↓         │  │
│  │                                           fix tasks  6-finalize       │  │
│  │                                           (triage)   (max 3x)        │  │
│  │                                                │      ↓       ↓       │  │
│  │                                                │   [PR issues?]       │  │
│  │                                                │    ↓       ↓         │  │
│  │                                                │  yes      no         │  │
│  │                                                │   │       ↓          │  │
│  │                                                └───┘    COMPLETE      │  │
│  │                                                                       │  │
│  │  Iteration Limits: 5-execute verify (max 5x) | 6-finalize (max 3x)   │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                        THIN AGENT PATTERN                             │  │
│  │                                                                       │  │
│  │   Orchestrator ──▶ Agent ──▶ Skill                                    │  │
│  │                       │         │                                     │  │
│  │                       │         └──▶ Domain Knowledge                 │  │
│  │                       │                                               │  │
│  │                       └──▶ Context Isolation                          │  │
│  │                                                                       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                          DATA LAYER                                   │  │
│  │                                                                       │  │
│  │   manage-references  manage-lifecycle  manage-tasks  manage-solution  │  │
│  │        │               │               │              │               │  │
│  │        ▼               ▼               ▼              ▼               │  │
│  │   references.json status.toon    TASK-*.json   solution_outline.md   │  │
│  │                                                                       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Quick Navigation

| Document | Focus | Key Visuals |
|----------|-------|-------------|
| [standards/phases.md](standards/phases.md) | 6-phase model | Phase flow, transitions, outputs |
| [standards/agents.md](standards/agents.md) | Thin agent pattern | Agent structure, skill invocation |
| [standards/data-layer.md](standards/data-layer.md) | manage-* skills | File operations, TOON format |
| [standards/skill-loading.md](standards/skill-loading.md) | Two-tier loading | System vs domain skills |
| [standards/artifacts.md](standards/artifacts.md) | Plan file formats | references.json, status.toon, TASK-*.json |
| [standards/task-executor-routing.md](standards/task-executor-routing.md) | Task executor routing | Profile→executor mapping, extensibility |
| [standards/task-executor-base.md](standards/task-executor-base.md) | Shared executor steps | Common workflow for all task-* skills |
| [standards/change-types.md](standards/change-types.md) | Change type vocabulary | analysis, feature, enhancement, bug_fix, tech_debt, verification |
| `plan-marshall:extension-api` | Extension mechanism | Domain extensions for outline/triage |

---

## Core Principles

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                          CORE DESIGN PRINCIPLES                             │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. DOMAIN-AGNOSTIC WORKFLOW                                                │
│     ════════════════════════                                                │
│     Workflow skills contain NO domain-specific logic.                       │
│     Domain knowledge comes from marshal.json at runtime.                    │
│                                                                             │
│  2. THIN AGENT PATTERN                                                      │
│     ═══════════════════                                                     │
│     A single parameterized agent (plan-phase-agent) with different          │
│     `phase` parameters results in 5 invocation modes, all sharing           │
│     one implementation. Agents are minimal wrappers that:                   │
│     • Resolve skills from marshal.json                                      │
│     • Load resolved skills                                                  │
│     • Delegate to skills for actual work                                    │
│                                                                             │
│  3. SINGLE SOURCE OF TRUTH                                                  │
│     ════════════════════════                                                │
│     Plan files (.toon, .md) are the source of truth.                        │
│     Skills read/write via manage-* scripts only.                            │
│                                                                             │
│  4. SCRIPT-BASED FILE ACCESS                                                │
│     ═════════════════════════                                               │
│     ALL .plan/ file access goes through execute-script.py.                  │
│     NEVER use Read/Write/Edit on .plan/ files directly.                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                          COMPONENT HIERARCHY                                │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  COMMANDS (User-facing)                                              │   │
│  │  ══════════════════════                                              │   │
│  │  /plan-marshall  /workflow-pr-doctor                                          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                     │                                       │
│                                     ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  AGENTS (Single Parameterized Agent)                                 │   │
│  │  ═══════════════════════════════════                                 │   │
│  │  plan-phase-agent phase=1-init | 2-refine | 3-outline | 4-plan | 5-execute | 6-finalize │
│  │  (One agent, 6 invocation modes)                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                     │                                       │
│                                     ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  WORKFLOW SKILLS (Phase Logic)                                       │   │
│  │  ═════════════════════════════                                       │   │
│  │  phase-1-init   phase-2-refine   phase-3-outline   phase-4-plan      │   │
│  │  phase-5-execute   phase-6-finalize                                  │   │
│  │  task-implementation   task-module-testing   task-verification        │   │
│  │  workflow-integration-git     workflow-integration-ci                │   │
│  │  workflow-integration-sonar   workflow-pr-doctor                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                     │                                       │
│                                     ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  DATA LAYER (manage-* Skills)                                        │   │
│  │  ════════════════════════════                                        │   │
│  │  manage-references    manage-lifecycle     manage-tasks                │   │
│  │  manage-solution-outline    manage-plan-documents    manage-files     │   │
│  │  manage-architecture        manage-findings          manage-logging   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                     │                                       │
│                                     ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  PLAN FILES (.plan/plans/{plan_id}/)                                 │   │
│  │  ═══════════════════════════════════                                 │   │
│  │  status.toon  request.md  references.json  solution_outline.md        │   │
│  │  TASK-001.json  TASK-002.json  ...                                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Related Skills

| Skill | Purpose |
|-------|---------|
| `plan-marshall:plan-marshall` | Unified user-facing entry point for plan lifecycle |
| `plan-marshall:extension-api` | Extension points for domain customization |
| `plan-marshall:phase-1-init` | Init phase implementation |
| `plan-marshall:phase-2-refine` | Refine phase implementation |
| `plan-marshall:phase-3-outline` | Outline phase implementation |
| `plan-marshall:phase-4-plan` | Plan phase implementation |
| `plan-marshall:phase-5-execute` | Execute phase implementation (includes verification + triage) |
| `plan-marshall:phase-6-finalize` | Finalize phase implementation |
| `plan-marshall:task-implementation` | Implementation profile workflow |
| `plan-marshall:task-module-testing` | Module testing profile workflow |
| `plan-marshall:task-verification` | Verification-only profile workflow |

---

## Shared Workflow Infrastructure

All workflow scripts share `triage_helpers` from `ref-toon-format` (`marketplace/bundles/plan-marshall/skills/ref-toon-format/scripts/triage_helpers.py`). See `plan-marshall:ref-toon-format` SKILL.md for the module overview. Key exports: `print_toon`, `safe_main`, `create_workflow_cli`, `ErrorCode`, `calculate_priority`, `is_test_file`, triage command handlers.

The triage scripts use pattern matching and will sometimes misclassify nuanced inputs. Use script results as a starting point — override when the `action` or `priority` doesn't match semantic intent. Document overrides in the commit message or suppression comment.

---

## Workflow Skill Conventions

### SKILL.md Template

All workflow skills follow this canonical section order:

```
---
name: workflow-<name>
description: <one-line description>
user-invocable: true|false
---

# <Title> Skill

<One paragraph summary.>

## Enforcement
## Parameters
## Prerequisites
## Architecture
## Usage Examples
## Workflow(s)
## Scripts
## Error Handling
## Standards (Load On-Demand)
## Related
```

### Config Loading Convention

All workflow scripts load JSON config from `standards/` using `load_skill_config(__file__, 'config-name.json')` from `triage_helpers`. This resolves to `<script_dir>/../standards/<config_name>`. Configuration that drives script behavior (patterns, rules, thresholds, severity mappings) should be externalized to JSON — not hardcoded in the script.

### Priority Vocabulary

All workflow scripts use the shared `PRIORITY_LEVELS` tuple from `triage_helpers`: `low`, `medium`, `high`, `critical`. The additional value `none` is used only for non-actionable items (e.g., ignored comments). Scripts should map their domain-specific severity to these canonical levels.

### TOON Output Conventions

- All outputs include `status: success|failure` at the top level
- Array fields use the hint notation: `field_name[N]:` for simple arrays, `field_name[N]{key1,key2}:` for arrays of objects
- Error outputs use `make_error()` for structured error payloads with `error`, `status`, `error_code` fields
- Use `print_error()` for direct error-and-exit; use `make_error()` + `print_toon()` only when additional processing is needed before output

### Error Handling Tables

All workflow skills use a consistent `| Failure | Action |` table in their Error Handling section. Keep actions specific and prescriptive.

---

## Standards Documents

Load on-demand based on what aspect of the architecture you need to understand:

```bash
# Understanding the 6-phase model
Read standards/phases.md

# Understanding thin agent pattern
Read standards/agents.md

# Understanding data layer (manage-* skills)
Read standards/data-layer.md

# Understanding skill loading
Read standards/skill-loading.md

# Understanding plan file formats
Read standards/artifacts.md

# Understanding task executor routing
Read standards/task-executor-routing.md

# Understanding shared task executor workflow
Read standards/task-executor-base.md

# Understanding change type vocabulary
Read standards/change-types.md
```
