# Thin Agent Pattern

The pm-workflow bundle uses thin agents that delegate to skills for actual work.

---

## Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                         THIN AGENT PATTERN                                  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                                                                      │  │
│  │   ORCHESTRATOR                                                       │  │
│  │   ════════════                                                       │  │
│  │                                                                      │  │
│  │   /plan-marshall action=outline plan=X                                │  │
│  │         │                                                            │  │
│  │         ▼                                                            │  │
│  │   ┌──────────────────────────────────────────────────────────────┐  │  │
│  │   │                         SKILL                               │  │  │
│  │   │                         ═════                               │  │  │
│  │   │                                                              │  │  │
│  │   │   1. Load system skills                                      │  │  │
│  │   │   2. Load domain extension skills                            │  │  │
│  │   │   3. Spawn Task agents (if needed)                           │  │  │
│  │   │   4. Aggregate results                                       │  │  │
│  │   │                                                              │  │  │
│  │   │   ┌────────────────────────────────────────────────────────┐│  │  │
│  │   │   │                  SPAWNED AGENTS                        ││  │  │
│  │   │   │                  ══════════════                        ││  │  │
│  │   │   │                                                        ││  │  │
│  │   │   │   • Run in parallel (isolated context)                 ││  │  │
│  │   │   │   • Analyze files                                      ││  │  │
│  │   │   │   • Return structured results                          ││  │  │
│  │   │   │                                                        ││  │  │
│  │   │   └────────────────────────────────────────────────────────┘│  │  │
│  │   │                                                              │  │  │
│  │   └──────────────────────────────────────────────────────────────┘  │  │
│  │                                                                      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Invocation Patterns: Skill vs Task

Understanding when to use `Skill:` vs `Task:` is critical for proper context management.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                    INVOCATION PATTERNS                                      │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                                                                      │  │
│  │  Skill: skill-name                                                   │  │
│  │  ════════════════                                                    │  │
│  │  • Stays in CALLER'S context                                         │  │
│  │  • Inherits caller's ability to spawn Task agents                    │  │
│  │  • No context isolation                                              │  │
│  │  • Use for: phase skills, domain extensions                          │  │
│  │                                                                      │  │
│  ├──────────────────────────────────────────────────────────────────────┤  │
│  │                                                                      │  │
│  │  Task: agent-name                                                    │  │
│  │  ═══════════════                                                     │  │
│  │  • Creates NEW subagent context                                      │  │
│  │  • CANNOT spawn further Task agents (subagent constraint)            │  │
│  │  • Full context isolation                                            │  │
│  │  • Use for: leaf-level analysis, focused work                        │  │
│  │                                                                      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                                                                      │  │
│  │  KEY CONSTRAINT: Subagents cannot spawn other subagents              │  │
│  │  ═══════════════════════════════════════════════════                 │  │
│  │                                                                      │  │
│  │  Main Conversation                                                   │  │
│  │    → Skill: phase-3-outline      ← STAYS in main context             │  │
│  │      → Skill: ext-outline-plugin ← STAYS in main context             │  │
│  │        → Task: analysis-agent    ← CAN spawn (from main context) ✓   │  │
│  │                                                                      │  │
│  │  Main Conversation                                                   │  │
│  │    → Task: some-agent            ← Creates SUBAGENT context          │  │
│  │      → Skill: some-skill         ← In subagent context               │  │
│  │        → Task: other-agent       ← CANNOT spawn (subagent) ✗         │  │
│  │                                                                      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Decision Guide

| Scenario | Use | Reason |
|----------|-----|--------|
| Phase invocation from orchestrator | `Skill:` | Need to spawn analysis agents |
| Domain extension loading | `Skill:` | Inherits spawning ability |
| Leaf-level file analysis | `Task:` | Isolated, focused work |
| Init phase (no spawning needed) | `Task:` | Simple, isolated execution |
| Plan phase (no spawning needed) | `Task:` | Simple, isolated execution |

---

## Agent Inventory

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                           3 THIN AGENTS (pm-workflow)                       │
│                                                                             │
│  ┌──────────────────────┬────────────────────────────────────────────────┐ │
│  │ AGENT                │ PURPOSE                                        │ │
│  ├──────────────────────┼────────────────────────────────────────────────┤ │
│  │                      │                                                │ │
│  │ plan-init-agent      │ Initialize plan                                │ │
│  │                      │ • Creates status.toon, request.md, references.toon │ │
│  │                      │ • Detects domain                               │ │
│  │                      │                                                │ │
│  ├──────────────────────┼────────────────────────────────────────────────┤ │
│  │                      │                                                │ │
│  │ task-plan-agent      │ Create tasks from deliverables                 │ │
│  │                      │ • Resolves skills for each task                │ │
│  │                      │ • Aggregates/splits deliverables               │ │
│  │                      │                                                │ │
│  ├──────────────────────┼────────────────────────────────────────────────┤ │
│  │                      │                                                │ │
│  │ task-execute-agent   │ Execute single task                            │ │
│  │                      │ • Loads domain skills from task.skills         │ │
│  │                      │ • Routes by profile (implementation/module_testing) │ │
│  │                      │                                                │ │
│  └──────────────────────┴────────────────────────────────────────────────┘ │
│                                                                             │
│  NOTE: Outline phase (3-outline) uses skill-direct invocation instead      │
│  of an agent. This allows the skill to spawn analysis agents.              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                     4 ANALYSIS AGENTS (pm-plugin-development)               │
│                                                                             │
│  ┌──────────────────────┬────────────────────────────────────────────────┐ │
│  │ AGENT                │ PURPOSE                                        │ │
│  ├──────────────────────┼────────────────────────────────────────────────┤ │
│  │                      │                                                │ │
│  │ inventory-           │ Load inventory and assess scope                │ │
│  │ assessment-agent     │ • Runs scan-marketplace-inventory              │ │
│  │                      │ • Determines affected artifacts/bundles        │ │
│  │                      │ • Groups inventory by component type           │ │
│  │                      │                                                │ │
│  ├──────────────────────┼────────────────────────────────────────────────┤ │
│  │                      │                                                │ │
│  │ skill-analysis-      │ Analyze skill files against criteria           │ │
│  │ agent                │ • Reads each SKILL.md                          │ │
│  │                      │ • Applies match/exclude indicators             │ │
│  │                      │ • Returns findings with evidence               │ │
│  │                      │                                                │ │
│  ├──────────────────────┼────────────────────────────────────────────────┤ │
│  │                      │                                                │ │
│  │ command-analysis-    │ Analyze command files against criteria         │ │
│  │ agent                │ • Reads each command .md                       │ │
│  │                      │ • Applies match/exclude indicators             │ │
│  │                      │ • Returns findings with evidence               │ │
│  │                      │                                                │ │
│  ├──────────────────────┼────────────────────────────────────────────────┤ │
│  │                      │                                                │ │
│  │ agent-analysis-      │ Analyze agent files against criteria           │ │
│  │ agent                │ • Reads each agent .md                         │ │
│  │                      │ • Applies match/exclude indicators             │ │
│  │                      │ • Returns findings with evidence               │ │
│  │                      │                                                │ │
│  └──────────────────────┴────────────────────────────────────────────────┘ │
│                                                                             │
│  These agents are spawned by ext-outline-plugin during path-multi          │
│  workflow. They run in PARALLEL for efficient cross-cutting analysis.      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Outline Phase: Skill-Direct Invocation

The outline phase uses skill-direct invocation to enable parallel agent spawning:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                   OUTLINE PHASE FLOW (SKILL-DIRECT)                         │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                                                                      │  │
│  │  /plan-marshall action=outline                                        │  │
│  │         │                                                            │  │
│  │         ▼                                                            │  │
│  │  ┌────────────────────────────────────────────────────────────────┐ │  │
│  │  │ Skill: pm-workflow:phase-3-outline   ← DIRECT (stays in main)  │ │  │
│  │  │                                                                │ │  │
│  │  │  • Loads domain extension                                      │ │  │
│  │  │  • Determines workflow path (simple/complex)                   │ │  │
│  │  │                                                                │ │  │
│  │  │    ┌────────────────────────────────────────────────────────┐ │ │  │
│  │  │    │ Skill: ext-outline-plugin  ← DIRECT (stays in main)    │ │ │  │
│  │  │    │                                                        │ │ │  │
│  │  │    │  • For complex workflow (path-multi):                  │ │ │  │
│  │  │    │                                                        │ │ │  │
│  │  │    │  ┌──────────────────────────────────────────────────┐ │ │ │  │
│  │  │    │  │ Step 1: Task: ext-outline-inventory-agent         │ │ │ │  │
│  │  │    │  │ → Returns grouped inventory                      │ │ │ │  │
│  │  │    │  └──────────────────────────────────────────────────┘ │ │ │  │
│  │  │    │                          │                             │ │ │  │
│  │  │    │                          ▼                             │ │ │  │
│  │  │    │  ┌──────────────────────────────────────────────────┐ │ │ │  │
│  │  │    │  │ Step 3: Parallel Analysis (3 Task agents)        │ │ │ │  │
│  │  │    │  │                                                  │ │ │ │  │
│  │  │    │  │  ┌────────────┐ ┌────────────┐ ┌────────────┐   │ │ │ │  │
│  │  │    │  │  │ ext-out-   │ │ ext-out-   │ │ ext-out-   │   │ │ │ │  │
│  │  │    │  │  │ line-skill │ │ line-cmd   │ │ line-agent │   │ │ │ │  │
│  │  │    │  │  │ -agent     │ │ -agent     │ │ -agent     │   │ │ │ │  │
│  │  │    │  │  └────────────┘ └────────────┘ └────────────┘   │ │ │ │  │
│  │  │    │  │                                                  │ │ │ │  │
│  │  │    │  └──────────────────────────────────────────────────┘ │ │ │  │
│  │  │    │                          │                             │ │ │  │
│  │  │    │                          ▼                             │ │ │  │
│  │  │    │  Aggregate findings → Build deliverables               │ │ │  │
│  │  │    │                                                        │ │ │  │
│  │  │    └────────────────────────────────────────────────────────┘ │ │  │
│  │  │                                                                │ │  │
│  │  └────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  KEY: Skills loaded via Skill: stay in main context, enabling Task spawns  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Agent Structure

Each agent follows the same pattern:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                      AGENT STRUCTURE TEMPLATE                               │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                                                                      │  │
│  │  ---                                                                 │  │
│  │  name: {agent-name}                                                  │  │
│  │  description: {what it does}                                         │  │
│  │  tools: Read, Bash, ...                                              │  │
│  │  model: sonnet                                                       │  │
│  │  ---                                                                 │  │
│  │                                                                      │  │
│  │  # {Agent Name}                                                      │  │
│  │                                                                      │  │
│  │  ## Input                                                            │  │
│  │  - Parameters received from caller                                   │  │
│  │                                                                      │  │
│  │  ## Task                                                             │  │
│  │  - Steps to perform                                                  │  │
│  │                                                                      │  │
│  │  ## Output                                                           │  │
│  │  - TOON format with status field                                     │  │
│  │                                                                      │  │
│  │  ## Critical Rules                                                   │  │
│  │  - Constraints on behavior                                           │  │
│  │                                                                      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Agent Responsibilities

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                      AGENT RESPONSIBILITIES                                 │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                                                                      │  │
│  │  AGENT DOES:                          AGENT DOES NOT:                │  │
│  │  ══════════                           ══════════════                 │  │
│  │                                                                      │  │
│  │  ✓ Load system skills                 ✗ Spawn other agents           │  │
│  │  ✓ Resolve workflow skill             ✗ Cross scope boundaries       │  │
│  │  ✓ Load resolved skill                ✗ Invoke commands              │  │
│  │  ✓ Delegate to skill                  ✗ Make high-level decisions    │  │
│  │  ✓ Return structured result           ✗ Access files outside scope   │  │
│  │  ✓ Provide context isolation                                         │  │
│  │                                                                      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                                                                      │  │
│  │  PHASE SKILL DOES:                    PHASE SKILL DOES NOT:          │  │
│  │  ════════════════                     ═════════════════              │  │
│  │                                                                      │  │
│  │  ✓ Contains workflow logic            ✗ Handle phase transitions     │  │
│  │  ✓ Calls manage-* scripts             ✗ Invoke commands directly     │  │
│  │  ✓ Makes decisions                    ✗ Access files outside scope   │  │
│  │  ✓ Spawns analysis agents (when in    ✗ Duplicate agent logic        │  │
│  │    main context)                                                     │  │
│  │  ✓ Returns structured result                                         │  │
│  │  ✓ Records lessons learned                                           │  │
│  │                                                                      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Agent Constraints

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                       AGENT CONSTRAINTS                                     │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                                                                      │  │
│  │  MUST NOT:                                                           │  │
│  │  ════════                                                            │  │
│  │                                                                      │  │
│  │  ┌────────────────────────────────────────────────────────────────┐ │  │
│  │  │                                                                │ │  │
│  │  │  ✗ Use Read/Write/Edit on .plan/plans/ files                   │ │  │
│  │  │                                                                │ │  │
│  │  │  ✗ Use cat/head/tail/ls on .plan/ directory                    │ │  │
│  │  │                                                                │ │  │
│  │  │  ✗ Spawn other agents (subagent constraint)                    │ │  │
│  │  │                                                                │ │  │
│  │  │  ✗ Invoke commands (commands are user-facing)                  │ │  │
│  │  │                                                                │ │  │
│  │  │  ✗ Hardcode skill names (must resolve from marshal.json)       │ │  │
│  │  │                                                                │ │  │
│  │  │  ✗ Cross scope boundaries (init agent doesn't create tasks)    │ │  │
│  │  │                                                                │ │  │
│  │  └────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                      │  │
│  │  MUST DO:                                                            │  │
│  │  ════════                                                            │  │
│  │                                                                      │  │
│  │  ┌────────────────────────────────────────────────────────────────┐ │  │
│  │  │                                                                │ │  │
│  │  │  ✓ Access .plan/ files ONLY via execute-script.py              │ │  │
│  │  │                                                                │ │  │
│  │  │  ✓ Load system skills (Step 0) before any action               │ │  │
│  │  │                                                                │ │  │
│  │  │  ✓ Resolve workflow skill from marshal.json                    │ │  │
│  │  │                                                                │ │  │
│  │  │  ✓ Delegate to skill for actual work                           │ │  │
│  │  │                                                                │ │  │
│  │  │  ✓ Return structured TOON output                               │ │  │
│  │  │                                                                │ │  │
│  │  │  ✓ Log skill loading decisions                                 │ │  │
│  │  │                                                                │ │  │
│  │  └────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Related Documents

| Document | Purpose |
|----------|---------|
| [skill-loading.md](skill-loading.md) | Two-tier skill loading pattern |
| [phases.md](phases.md) | 7-phase execution model |
| `pm-workflow:workflow-extension-api` | Extension points |
