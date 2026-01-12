---
name: pm-workflow-architecture
description: Centralized architecture documentation for the pm-workflow bundle with visual diagrams
allowed-tools: Read
---

# PM-Workflow Architecture

**Role**: Central architecture reference for the pm-workflow bundle. Provides visual documentation of the 5-phase execution model, thin agent pattern, and data layer.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                         PM-WORKFLOW ARCHITECTURE                            │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                      5-PHASE EXECUTION MODEL                          │  │
│  │                                                                       │  │
│  │   ┌──────┐   ┌─────────┐   ┌──────┐   ┌─────────┐   ┌──────────┐     │  │
│  │   │ init │──▶│ outline │──▶│ plan │──▶│ execute │──▶│ finalize │     │  │
│  │   └──────┘   └─────────┘   └──────┘   └─────────┘   └──────────┘     │  │
│  │       │           │            │            │             │          │  │
│  │       ▼           ▼            ▼            ▼             ▼          │  │
│  │   config      solution      TASK-*      project       commit        │  │
│  │   status      outline       .toon        files          PR          │  │
│  │   request                                                            │  │
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
│  │   manage-config  manage-lifecycle  manage-tasks  manage-solution     │  │
│  │        │               │               │              │               │  │
│  │        ▼               ▼               ▼              ▼               │  │
│  │   config.toon    status.toon    TASK-*.toon   solution_outline.md    │  │
│  │                                                                       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Quick Navigation

| Document | Focus | Key Visuals |
|----------|-------|-------------|
| [standards/phases.md](standards/phases.md) | 5-phase model | Phase flow, transitions, outputs |
| [standards/agents.md](standards/agents.md) | Thin agent pattern | Agent structure, delegation |
| [standards/data-layer.md](standards/data-layer.md) | manage-* skills | File operations, TOON format |
| [standards/skill-loading.md](standards/skill-loading.md) | Two-tier loading | System vs domain skills |
| [standards/artifacts.md](standards/artifacts.md) | Plan file formats | config.toon, status.toon, TASK-*.toon |

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
│     Agents are minimal wrappers that:                                       │
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
│  │  /plan-manage  /plan-execute  /pr-doctor                             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                     │                                       │
│                                     ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  AGENTS (Thin Wrappers)                                              │   │
│  │  ══════════════════════                                              │   │
│  │  plan-init-agent       solution-outline-agent                        │   │
│  │  task-plan-agent       task-execute-agent                            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                     │                                       │
│                                     ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  WORKFLOW SKILLS (Phase Logic)                                       │   │
│  │  ═════════════════════════════                                       │   │
│  │  phase-init           phase-refine-outline   phase-refine-plan       │   │
│  │  phase-execute        phase-finalize                                 │   │
│  │  phase-execute-implementation  phase-execute-testing                 │   │
│  │  git-workflow         pr-workflow                                    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                     │                                       │
│                                     ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  DATA LAYER (manage-* Skills)                                        │   │
│  │  ════════════════════════════                                        │   │
│  │  manage-config      manage-lifecycle    manage-tasks                 │   │
│  │  manage-solution-outline                manage-plan-documents        │   │
│  │  manage-files       manage-references                                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                     │                                       │
│                                     ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  PLAN FILES (.plan/plans/{plan_id}/)                                 │   │
│  │  ═══════════════════════════════════                                 │   │
│  │  config.toon  status.toon  request.md  solution_outline.md           │   │
│  │  references.toon  TASK-001.toon  TASK-002.toon  ...                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Related Skills

| Skill | Purpose |
|-------|---------|
| `pm-workflow:plan-wf-skill-api` | Contract definitions for workflow skills |
| `pm-workflow:phase-init` | Init phase implementation |
| `pm-workflow:phase-refine-outline` | Outline phase implementation |
| `pm-workflow:phase-refine-plan` | Plan phase implementation |
| `pm-workflow:phase-execute` | Execute phase implementation |
| `pm-workflow:phase-finalize` | Finalize phase implementation |
| `pm-workflow:phase-execute-implementation` | Implementation profile workflow |
| `pm-workflow:phase-execute-testing` | Testing profile workflow |

---

## Standards Documents

Load on-demand based on what aspect of the architecture you need to understand:

```bash
# Understanding the 5-phase model
Read standards/phases.md

# Understanding thin agent pattern
Read standards/agents.md

# Understanding data layer (manage-* skills)
Read standards/data-layer.md

# Understanding skill loading
Read standards/skill-loading.md

# Understanding plan file formats
Read standards/artifacts.md
```
