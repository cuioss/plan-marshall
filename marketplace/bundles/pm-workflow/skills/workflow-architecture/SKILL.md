---
name: workflow-architecture
description: Centralized architecture documentation for the pm-workflow bundle with visual diagrams
user-invokable: false
---

# PM-Workflow Architecture

**Role**: Central architecture reference for the pm-workflow bundle. Provides visual documentation of the 6-phase execution model, thin agent pattern, and data layer.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                         PM-WORKFLOW ARCHITECTURE                            │
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
│  │   references.json status.toon    TASK-*.toon   solution_outline.md   │  │
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
| [standards/artifacts.md](standards/artifacts.md) | Plan file formats | references.json, status.toon, TASK-*.toon |
| [standards/task-executor-routing.md](standards/task-executor-routing.md) | Task executor routing | Profile→executor mapping, extensibility |
| `pm-workflow:workflow-extension-api` | Extension mechanism | Domain extensions for outline/triage |

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
│  │  /plan-marshall  /pr-doctor                                          │   │
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
│  │  task-implementation           task-module_testing                   │   │
│  │  git-workflow         pr-workflow                                    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                     │                                       │
│                                     ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  DATA LAYER (manage-* Skills)                                        │   │
│  │  ════════════════════════════                                        │   │
│  │  manage-references   manage-lifecycle    manage-tasks                 │   │
│  │  manage-solution-outline                manage-plan-documents        │   │
│  │  manage-files       manage-references                                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                     │                                       │
│                                     ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  PLAN FILES (.plan/plans/{plan_id}/)                                 │   │
│  │  ═══════════════════════════════════                                 │   │
│  │  status.toon  request.md  references.json  solution_outline.md        │   │
│  │  TASK-001.toon  TASK-002.toon  ...                                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Related Skills

| Skill | Purpose |
|-------|---------|
| `pm-workflow:plan-marshall` | Unified user-facing entry point for plan lifecycle |
| `pm-workflow:workflow-extension-api` | Extension points for domain customization |
| `pm-workflow:phase-1-init` | Init phase implementation |
| `pm-workflow:phase-2-refine` | Refine phase implementation |
| `pm-workflow:phase-3-outline` | Outline phase implementation |
| `pm-workflow:phase-4-plan` | Plan phase implementation |
| `pm-workflow:phase-5-execute` | Execute phase implementation (includes verification + triage) |
| `pm-workflow:phase-6-finalize` | Finalize phase implementation |
| `pm-workflow:task-implementation` | Implementation profile workflow |
| `pm-workflow:task-module_testing` | Module testing profile workflow |

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
```
