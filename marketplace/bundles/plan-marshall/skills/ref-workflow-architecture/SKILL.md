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
│  │  task-implementation           task-module-testing                   │   │
│  │  git_workflow         pr-workflow                                    │   │
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

---

## Workflow Skill Orchestration

The PR doctor orchestrates three integration workflow skills plus supporting skills:

```
/workflow-pr-doctor (orchestrator, user-invocable)
  ├─> workflow-integration-ci    (PR review comment fetch & triage)
  │     └─> tools-integration-ci (provider abstraction: GitHub/GitLab)
  ├─> workflow-integration-sonar (Sonar issue fetch & triage)
  ├─> workflow-integration-git   (commit formatting, artifact cleanup)
  ├─> manage-architecture        (build command resolution — on-demand for BUILD_FAILURE)
  └─> manage-findings            (Q-Gate findings — on-demand for Automated Review mode)
```

`workflow-permission-web` is a standalone user-invocable skill (not part of the PR doctor flow).

### Shared Infrastructure

All workflow scripts share `triage_helpers` from `ref-toon-format` (`marketplace/bundles/plan-marshall/skills/ref-toon-format/scripts/triage_helpers.py`):

| Helper | Purpose | Consumers |
|--------|---------|-----------|
| `print_toon` / `print_error` | Output serialization + exit code | All 5 scripts |
| `safe_main` | Exception-to-TOON wrapper | All 5 scripts |
| `create_workflow_cli` | Argparse boilerplate reduction | All 5 scripts |
| `load_skill_config` | Standards directory config loading | All 5 scripts |
| `ErrorCode` / `make_error` | Structured error taxonomy | All 5 scripts |
| `cmd_triage_single` / `cmd_triage_batch_handler` | Triage command handlers | pr.py, sonar.py |
| `calculate_priority` | Priority escalation arithmetic | sonar.py |
| `is_test_file` | Cross-language test file detection | sonar.py, git_workflow.py |

### Triage Override Guidance

The triage scripts use regex pattern matching (CI comments) or rule-based classification (Sonar issues) and will sometimes misclassify nuanced inputs. When the script's `action` or `priority` doesn't match the semantic intent, override it. Use the script result as a starting point, not a final answer. Document overrides in the commit message or suppression comment.

### Common Error Handling Patterns

| Pattern | When to Apply |
|---------|--------------|
| Report error with stderr details, do not proceed | Script returns `status: failure` for a blocking operation (CI status, fetch) |
| Log warning, skip item, continue remaining | Non-critical per-item failure in batch processing (triage, thread-reply) |
| Ask user via `AskUserQuestion` (continue/skip/abort) | Timeout, missing file, or ambiguous state requiring human judgment |
| Report remaining issues, stop looping | `max-fix-attempts` reached for a category |
| Never force-push as fallback | Push failure — report error and stop |

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
