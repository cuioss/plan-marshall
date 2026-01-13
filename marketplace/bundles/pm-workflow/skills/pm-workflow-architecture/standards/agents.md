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
│  │   /plan-manage action=refine plan=X                                  │  │
│  │         │                                                            │  │
│  │         ▼                                                            │  │
│  │   ┌──────────────────────────────────────────────────────────────┐  │  │
│  │   │                         AGENT                                │  │  │
│  │   │                         ═════                                │  │  │
│  │   │                                                              │  │  │
│  │   │   1. Load system skills                                      │  │  │
│  │   │   2. Resolve workflow skill (from marshal.json)              │  │  │
│  │   │   3. Load resolved skill                                     │  │  │
│  │   │   4. Delegate to skill                                       │  │  │
│  │   │                                                              │  │  │
│  │   │   ┌────────────────────────────────────────────────────────┐│  │  │
│  │   │   │                      SKILL                             ││  │  │
│  │   │   │                      ═════                             ││  │  │
│  │   │   │                                                        ││  │  │
│  │   │   │   • Contains workflow logic                            ││  │  │
│  │   │   │   • Calls manage-* scripts                             ││  │  │
│  │   │   │   • Returns structured result                          ││  │  │
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

## Agent Inventory

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                           4 THIN AGENTS                                     │
│                                                                             │
│  ┌──────────────────────┬────────────────────────────────────────────────┐ │
│  │ AGENT                │ PURPOSE                                        │ │
│  ├──────────────────────┼────────────────────────────────────────────────┤ │
│  │                      │                                                │ │
│  │ plan-init-agent      │ Initialize plan                                │ │
│  │                      │ • Creates config.toon, status.toon, request.md │ │
│  │                      │ • Detects domain                               │ │
│  │                      │                                                │ │
│  ├──────────────────────┼────────────────────────────────────────────────┤ │
│  │                      │                                                │ │
│  │ solution-outline-    │ Create solution outline                        │ │
│  │ agent                │ • Analyzes codebase                            │ │
│  │                      │ • Creates deliverables with domain/profile     │ │
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
│  │                      │ • Routes by profile (implementation/testing)   │ │
│  │                      │                                                │ │
│  └──────────────────────┴────────────────────────────────────────────────┘ │
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
│  │  tools: Read, Write, Edit, Glob, Grep, Bash, Skill                   │  │
│  │  model: sonnet                                                       │  │
│  │  skills: plan-marshall:general-development-rules                     │  │
│  │  ---                                                                 │  │
│  │                                                                      │  │
│  │  # {Agent Name}                                                      │  │
│  │                                                                      │  │
│  │  ## Step 0: Load System Skills (MANDATORY)                           │  │
│  │                                                                      │  │
│  │  ```                                                                 │  │
│  │  Skill: plan-marshall:general-development-rules                      │  │
│  │  ```                                                                 │  │
│  │                                                                      │  │
│  │  ## Step 1: Resolve Workflow Skill                                   │  │
│  │                                                                      │  │
│  │  ```bash                                                             │  │
│  │  python3 .plan/execute-script.py                                     │  │
│  │    plan-marshall:plan-marshall-config:plan-marshall-config           │  │
│  │    resolve-workflow-skill --domain {domain} --phase {phase}          │  │
│  │  ```                                                                 │  │
│  │                                                                      │  │
│  │  ## Step 2: Load and Execute Skill                                   │  │
│  │                                                                      │  │
│  │  ```                                                                 │  │
│  │  Skill: {resolved_skill}                                             │  │
│  │  ```                                                                 │  │
│  │                                                                      │  │
│  │  ## Return Results                                                   │  │
│  │                                                                      │  │
│  │  Return TOON format with status field.                               │  │
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
│  │  ✓ Load system skills                 ✗ Contain workflow logic       │  │
│  │  ✓ Resolve workflow skill             ✗ Call manage-* scripts        │  │
│  │  ✓ Load resolved skill                ✗ Read/Write .plan/ files      │  │
│  │  ✓ Delegate to skill                  ✗ Spawn other agents           │  │
│  │  ✓ Return structured result           ✗ Invoke commands              │  │
│  │  ✓ Provide context isolation          ✗ Make business decisions      │  │
│  │                                                                      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                                                                      │  │
│  │  SKILL DOES:                          SKILL DOES NOT:                │  │
│  │  ══════════                           ══════════════                 │  │
│  │                                                                      │  │
│  │  ✓ Contains workflow logic            ✗ Spawn agents                 │  │
│  │  ✓ Calls manage-* scripts             ✗ Load other workflow skills   │  │
│  │  ✓ Makes decisions                    ✗ Access files outside scope   │  │
│  │  ✓ Returns structured result          ✗ Handle phase transitions     │  │
│  │  ✓ Records lessons learned            ✗ Invoke commands directly     │  │
│  │                                                                      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Agent Flow: solution-outline-agent

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                   SOLUTION-OUTLINE-AGENT FLOW                               │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                                                                      │  │
│  │  INPUT: plan_id                                                      │  │
│  │                                                                      │  │
│  │  ┌────────────────────────────────────────────────────────────────┐ │  │
│  │  │ Step 0: Load System Skills                                     │ │  │
│  │  │                                                                │ │  │
│  │  │ Skill: plan-marshall:general-development-rules                 │ │  │
│  │  └────────────────────────────────────────────────────────────────┘ │  │
│  │                              │                                       │  │
│  │                              ▼                                       │  │
│  │  ┌────────────────────────────────────────────────────────────────┐ │  │
│  │  │ Step 1a: Get domain from config                                │ │  │
│  │  │                                                                │ │  │
│  │  │ manage-config get --plan-id X --field domains                  │ │  │
│  │  │ → domains: [java]                                              │ │  │
│  │  └────────────────────────────────────────────────────────────────┘ │  │
│  │                              │                                       │  │
│  │                              ▼                                       │  │
│  │  ┌────────────────────────────────────────────────────────────────┐ │  │
│  │  │ Step 1b: Resolve workflow skill                                │ │  │
│  │  │                                                                │ │  │
│  │  │ resolve-workflow-skill --domain java --phase outline           │ │  │
│  │  │ → pm-workflow:phase-refine-outline                                 │ │  │
│  │  └────────────────────────────────────────────────────────────────┘ │  │
│  │                              │                                       │  │
│  │                              ▼                                       │  │
│  │  ┌────────────────────────────────────────────────────────────────┐ │  │
│  │  │ Step 1c: Load resolved skill                                   │ │  │
│  │  │                                                                │ │  │
│  │  │ Skill: pm-workflow:phase-refine-outline                            │ │  │
│  │  └────────────────────────────────────────────────────────────────┘ │  │
│  │                              │                                       │  │
│  │                              ▼                                       │  │
│  │  ┌────────────────────────────────────────────────────────────────┐ │  │
│  │  │ Step 2: Execute Skill Workflow                                 │ │  │
│  │  │                                                                │ │  │
│  │  │ The skill:                                                     │ │  │
│  │  │  • Reads request.md                                            │ │  │
│  │  │  • Analyzes codebase                                           │ │  │
│  │  │  • Creates deliverables                                        │ │  │
│  │  │  • Writes solution_outline.md                                  │ │  │
│  │  └────────────────────────────────────────────────────────────────┘ │  │
│  │                              │                                       │  │
│  │                              ▼                                       │  │
│  │  OUTPUT:                                                             │  │
│  │  status: success                                                     │  │
│  │  plan_id: {plan_id}                                                  │  │
│  │  deliverable_count: 3                                                │  │
│  │                                                                      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Agent Flow: task-execute-agent

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                    TASK-EXECUTE-AGENT FLOW                                  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                                                                      │  │
│  │  INPUT: plan_id, task_number                                         │  │
│  │                                                                      │  │
│  │  ┌────────────────────────────────────────────────────────────────┐ │  │
│  │  │ Step 0: Load System Skills                                     │ │  │
│  │  │                                                                │ │  │
│  │  │ Skill: plan-marshall:general-development-rules                 │ │  │
│  │  └────────────────────────────────────────────────────────────────┘ │  │
│  │                              │                                       │  │
│  │                              ▼                                       │  │
│  │  ┌────────────────────────────────────────────────────────────────┐ │  │
│  │  │ Step 1: Read Task                                              │ │  │
│  │  │                                                                │ │  │
│  │  │ manage-tasks get --plan-id X --task-number 1                   │ │  │
│  │  │ → domain: java                                                 │ │  │
│  │  │ → profile: implementation                                      │ │  │
│  │  │ → skills: [pm-dev-java:java-core, pm-dev-java:junit-core]      │ │  │
│  │  └────────────────────────────────────────────────────────────────┘ │  │
│  │                              │                                       │  │
│  │                              ▼                                       │  │
│  │  ┌────────────────────────────────────────────────────────────────┐ │  │
│  │  │ Step 2: Load Domain Skills (Tier 2)                            │ │  │
│  │  │                                                                │ │  │
│  │  │ Skill: pm-dev-java:java-core                                   │ │  │
│  │  │ Skill: pm-dev-java:junit-core                                  │ │  │
│  │  └────────────────────────────────────────────────────────────────┘ │  │
│  │                              │                                       │  │
│  │                              ▼                                       │  │
│  │  ┌────────────────────────────────────────────────────────────────┐ │  │
│  │  │ Step 3: Resolve Workflow Skill                                 │ │  │
│  │  │                                                                │ │  │
│  │  │ resolve-workflow-skill --domain java --phase implementation    │ │  │
│  │  │ → pm-workflow:task-implementation                     │ │  │
│  │  └────────────────────────────────────────────────────────────────┘ │  │
│  │                              │                                       │  │
│  │                              ▼                                       │  │
│  │  ┌────────────────────────────────────────────────────────────────┐ │  │
│  │  │ Step 4: Load and Execute Workflow Skill                        │ │  │
│  │  │                                                                │ │  │
│  │  │ Skill: pm-workflow:task-implementation                │ │  │
│  │  │                                                                │ │  │
│  │  │ The skill:                                                     │ │  │
│  │  │  • Reads affected files                                        │ │  │
│  │  │  • Applies domain patterns                                     │ │  │
│  │  │  • Implements changes                                          │ │  │
│  │  │  • Runs verification                                           │ │  │
│  │  └────────────────────────────────────────────────────────────────┘ │  │
│  │                              │                                       │  │
│  │                              ▼                                       │  │
│  │  OUTPUT:                                                             │  │
│  │  status: success                                                     │  │
│  │  task_number: 1                                                      │  │
│  │  verification: passed                                                │  │
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
│  │  │  ✗ Spawn other agents (prevents complexity explosion)          │ │  │
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
| [phases.md](phases.md) | 5-phase execution model |
| `pm-workflow:plan-wf-skill-api` | Contract definitions |
