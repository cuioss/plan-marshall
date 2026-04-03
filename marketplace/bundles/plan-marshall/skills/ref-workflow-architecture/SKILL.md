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
│  │   manage-references  manage-status     manage-tasks  manage-solution  │  │
│  │        │               │               │              │               │  │
│  │        ▼               ▼               ▼              ▼               │  │
│  │   references.json status.json    TASK-*.json   solution_outline.md   │  │
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
| [standards/data-layer.md](standards/data-layer.md) | manage-* skills | Inventory, dependency graph, data flow, shared infra |
| [standards/manage-contract.md](standards/manage-contract.md) | manage-* contract | Enforcement, error codes, shared formats |
| [standards/skill-loading.md](standards/skill-loading.md) | Two-tier loading | System vs domain skills |
| [standards/artifacts.md](standards/artifacts.md) | Plan file formats | references.json, status.json, TASK-*.json |
| [standards/task-executors.md](standards/task-executors.md) | Task executors | Routing, shared workflow, extensibility |
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
│  │  DATA LAYER (14 manage-* Skills)                                     │   │
│  │  ══════════════════════════════                                      │   │
│  │  manage-status  manage-references  manage-tasks  manage-files        │   │
│  │  manage-solution-outline  manage-plan-documents  manage-findings     │   │
│  │  manage-architecture  manage-config  manage-logging  manage-metrics  │   │
│  │  manage-lessons  manage-memories  manage-run-config                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                     │                                       │
│                                     ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  PLAN FILES (.plan/plans/{plan_id}/)                                 │   │
│  │  ═══════════════════════════════════                                 │   │
│  │  status.json  request.md  references.json  solution_outline.md        │   │
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
| `plan-marshall:workflow-integration-git` | Git commit workflow |
| `plan-marshall:workflow-integration-ci` | CI/PR review comment workflow |
| `plan-marshall:workflow-integration-sonar` | Sonar issue workflow |
| `plan-marshall:workflow-pr-doctor` | PR issue diagnosis workflow |

---

## Shared Workflow Infrastructure

All workflow scripts share `triage_helpers` from `ref-toon-format` (`marketplace/bundles/plan-marshall/skills/ref-toon-format/scripts/triage_helpers.py`). See `plan-marshall:ref-toon-format` SKILL.md for the module overview. Key exports: `print_toon`, `safe_main`, `create_workflow_cli`, `ErrorCode`, `calculate_priority`, `is_test_file`, triage command handlers.

The triage scripts use pattern matching and will sometimes misclassify nuanced inputs. Use script results as a starting point — override when the `action` or `priority` doesn't match semantic intent. Document overrides in the commit message or suppression comment.

---

## Workflow Skill Conventions

### SKILL.md Template

Script-bearing workflow skills follow this canonical section order. Sections marked (optional) may be omitted when not applicable (e.g., task-* skills omit Parameters and Usage Examples since their input comes from task JSON).

```
---
name: workflow-<name>
description: <one-line description>
user-invocable: true|false
---

# <Title> Skill

<One paragraph summary.>

## Enforcement
## Parameters          (optional — omit for task executors)
## Prerequisites       (optional)
## Architecture        (optional)
## Usage Examples      (optional — omit for non-user-invocable skills)
## Workflow(s)
## Scripts
## Error Handling
## Standards (Load On-Demand)
## Related
```

### Config Loading Convention

Script-bearing workflow skills load JSON config from `standards/` using `load_skill_config(__file__, 'config-name.json')` from `triage_helpers`. This resolves to `<script_dir>/../standards/<config_name>`. Configuration that drives script behavior (patterns, rules, thresholds, severity mappings) should be externalized to JSON — not hardcoded in the script. (Task executor skills typically do not load config files — they receive configuration via the task JSON.)

### Priority Vocabulary

All workflow scripts use the shared `PRIORITY_LEVELS` tuple from `triage_helpers`: `low`, `medium`, `high`, `critical`. Scripts must map their domain-specific severity to these canonical levels. Do not use `none` or other values outside this vocabulary.

### TOON Output Conventions

See [manage-contract.md — TOON Output Contract](standards/manage-contract.md) for the full output contract (success/error format, `output_toon` vs `serialize_toon`).

### Error Handling Patterns

All workflow skills use a consistent `| Failure | Action |` table. Common patterns shared across skills:

| Pattern | Action | Used By |
|---------|--------|---------|
| Script returns error | Report error to caller with details. Do not proceed to next step. | All |
| Triage/classification failure | Log warning, skip the item, continue processing remaining items. | ci, sonar |
| Best-effort operation failure | Log warning, continue — replies, resolutions, status changes are best-effort. | ci, sonar |
| Push failure | Report error. Never force-push as fallback. | git, pr-doctor |
| Settings file not found | Report as missing. Ask user (create defaults, skip, abort). | permission-web |
| CI wait timeout | Ask user via AskUserQuestion (continue/skip/abort). | pr-doctor |
| Max fix attempts reached | Report remaining issues with details. Do not loop further. | pr-doctor |
| Build verification failure | Report failing tests/compilation. Do not commit broken state. | sonar, pr-doctor |

Each skill's Error Handling section documents skill-specific overrides only.

### Standards (Load On-Demand) Convention

All `standards/*.json` files are loaded at script import time by `load_skill_config()`. All `standards/*.md` files are loaded on-demand by the LLM when edge cases or deep reference is needed. Each skill documents its load-on-demand standards in a `## Standards (Load On-Demand)` table.

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

# Understanding task executors (routing + shared workflow)
Read standards/task-executors.md

# Understanding manage-* shared contract
Read standards/manage-contract.md

# Understanding change type vocabulary
Read standards/change-types.md
```
