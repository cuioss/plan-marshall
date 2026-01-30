# Skill Loading Pattern

The pm-workflow bundle uses a two-tier skill loading pattern for domain-agnostic execution.

---

## Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                      TWO-TIER SKILL LOADING                                 │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                                                                      │  │
│  │   TIER 1: SYSTEM SKILLS                                              │  │
│  │   ═════════════════════                                              │  │
│  │   • Loaded by agent (Step 0)                                         │  │
│  │   • Source: skill_domains.system.defaults                            │  │
│  │   • Example: plan-marshall:ref-development-standards                 │  │
│  │   • Applies to ALL tasks regardless of domain                        │  │
│  │                                                                      │  │
│  │   ─────────────────────────────────────────────────────────────────  │  │
│  │                                                                      │  │
│  │   TIER 2: DOMAIN SKILLS                                              │  │
│  │   ══════════════════════                                             │  │
│  │   • Loaded from task.skills                                          │  │
│  │   • Source: module.skills_by_profile (from architecture)             │  │
│  │   • Example: pm-dev-java:java-core, pm-dev-java:java-cdi             │  │
│  │   • Profiles listed in deliverable, skills resolved by task-plan     │  │
│  │                                                                      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Skill Origin Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                      SKILL ORIGIN FLOW                                      │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                                                                      │  │
│  │  analyze-project-architecture                                        │  │
│  │  ════════════════════════════                                        │  │
│  │                                                                      │  │
│  │  Each module has skills_by_profile:                                  │  │
│  │                                                                      │  │
│  │  modules:                                                            │  │
│  │    oauth-sheriff-core:                                               │  │
│  │      responsibility: "JWT validation logic"                          │  │
│  │      skills_by_profile:                                              │  │
│  │        implementation: [java-core, java-cdi]                         │  │
│  │        module_testing: [java-core, junit-core]                       │  │
│  │                                                                      │  │
│  │    oauth-sheriff-quarkus:                                            │  │
│  │      responsibility: "Quarkus CDI integration"                       │  │
│  │      skills_by_profile:                                              │  │
│  │        implementation: [java-core, java-cdi-quarkus]                 │  │
│  │        module_testing: [java-core, junit-core]                       │  │
│  │                                                                      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                              │                                              │
│                              ▼                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                                                                      │  │
│  │  solution-outline (OUTLINE phase)                                    │  │
│  │  ════════════════════════════════                                    │  │
│  │                                                                      │  │
│  │  1. Query architecture for modules                                   │  │
│  │  2. Select module for each deliverable                               │  │
│  │  3. List profiles that apply (no skills in deliverable)              │  │
│  │                                                                      │  │
│  │  Deliverable output (with Profiles list):                            │  │
│  │  ────────────────────────────────────────────                        │  │
│  │  ### 1. Add IssuerValidator class                                    │  │
│  │  **Metadata:**                                                       │  │
│  │    - module: oauth-sheriff-core                                      │  │
│  │    - domain: java                                                    │  │
│  │  **Profiles:**                                                       │  │
│  │    - implementation                                                  │  │
│  │    - module_testing                                                  │  │
│  │                                                                      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                              │                                              │
│                              ▼                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                                                                      │  │
│  │  task-plan (PLAN phase) - 1:N Task Creation                          │  │
│  │  ══════════════════════════════════════════                          │  │
│  │                                                                      │  │
│  │  For each profile in deliverable.profiles:                           │  │
│  │    1. Query architecture: module --name {module}                     │  │
│  │    2. Extract: skills_by_profile.{profile}                           │  │
│  │    3. Create task with profile + resolved skills                     │  │
│  │                                                                      │  │
│  │  TASK-001.toon (profile: implementation):                            │  │
│  │    deliverable: 1                                                    │  │
│  │    module: oauth-sheriff-core                                        │  │
│  │    domain: java                                                      │  │
│  │    profile: implementation                                           │  │
│  │    skills: ← resolved from architecture                              │  │
│  │      - pm-dev-java:java-core                                         │  │
│  │      - pm-dev-java:java-cdi                                          │  │
│  │                                                                      │  │
│  │  TASK-002.toon (profile: module_testing):                            │  │
│  │    deliverable: 1                                                    │  │
│  │    module: oauth-sheriff-core                                        │  │
│  │    domain: java                                                      │  │
│  │    profile: module_testing                                           │  │
│  │    skills: ← resolved from architecture                              │  │
│  │      - pm-dev-java:java-core                                         │  │
│  │      - pm-dev-java:junit-core                                        │  │
│  │    depends_on: TASK-001                                              │  │
│  │                                                                      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                              │                                              │
│                              ▼                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                                                                      │  │
│  │  task-execute-agent (EXECUTE phase)                                  │  │
│  │  ══════════════════════════════════                                  │  │
│  │                                                                      │  │
│  │  Loads skills from task.skills array (no resolution needed)          │  │
│  │                                                                      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Key Insight**: Skills are associated with modules via `skills_by_profile` in architecture data. Deliverables list which profiles apply (visible to user). Task-plan resolves skills from architecture for each profile, creating one task per profile (1:N mapping).

---

## Execute Phase Skill Loading

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                  EXECUTE PHASE SKILL LOADING                                │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                                                                      │  │
│  │   task-execute-agent                                                 │  │
│  │   ═══════════════════                                                │  │
│  │                                                                      │  │
│  │   ┌────────────────────────────────────────────────────────────┐    │  │
│  │   │  Step 0: Load System Skills (Tier 1)                       │    │  │
│  │   │                                                            │    │  │
│  │   │  Skill: plan-marshall:ref-development-standards            │    │  │
│  │   │                                                            │    │  │
│  │   │  • Always loaded                                           │    │  │
│  │   │  • Agent's skills: field in frontmatter                    │    │  │
│  │   │  • NOT visible in task.skills                              │    │  │
│  │   └────────────────────────────────────────────────────────────┘    │  │
│  │                              │                                       │  │
│  │                              ▼                                       │  │
│  │   ┌────────────────────────────────────────────────────────────┐    │  │
│  │   │  Step 1: Read Task                                         │    │  │
│  │   │                                                            │    │  │
│  │   │  manage-tasks get --plan-id X --number 1                   │    │  │
│  │   │  → module: oauth-sheriff-core                              │    │  │
│  │   │  → domain: java                                            │    │  │
│  │   │  → profile: implementation                                 │    │  │
│  │   │  → skills: [pm-dev-java:java-core, pm-dev-java:java-cdi]   │    │  │
│  │   └────────────────────────────────────────────────────────────┘    │  │
│  │                              │                                       │  │
│  │                              ▼                                       │  │
│  │   ┌────────────────────────────────────────────────────────────┐    │  │
│  │   │  Step 2: Load Domain Skills (Tier 2)                       │    │  │
│  │   │                                                            │    │  │
│  │   │  For each skill in task.skills:                            │    │  │
│  │   │    Skill: pm-dev-java:java-core                            │    │  │
│  │   │    Skill: pm-dev-java:java-cdi                             │    │  │
│  │   │                                                            │    │  │
│  │   │  • Loaded AFTER system skills                              │    │  │
│  │   │  • Already resolved during outline/plan phases             │    │  │
│  │   │  • Listed explicitly in task                               │    │  │
│  │   └────────────────────────────────────────────────────────────┘    │  │
│  │                              │                                       │  │
│  │                              ▼                                       │  │
│  │   ┌────────────────────────────────────────────────────────────┐    │  │
│  │   │  Step 3: Load Workflow Skill                               │    │  │
│  │   │                                                            │    │  │
│  │   │  Based on task.profile:                                    │    │  │
│  │   │    implementation → pm-workflow:task-implementation    │    │  │
│  │   │    module_testing → pm-workflow:task-module_testing    │    │  │
│  │   │                                                            │    │  │
│  │   │  • Determines HOW to execute                               │    │  │
│  │   │  • Applies domain skill patterns                           │    │  │
│  │   └────────────────────────────────────────────────────────────┘    │  │
│  │                              │                                       │  │
│  │                              ▼                                       │  │
│  │   ┌────────────────────────────────────────────────────────────┐    │  │
│  │   │  Step 4: Execute                                           │    │  │
│  │   │                                                            │    │  │
│  │   │  • Implements changes using domain patterns                │    │  │
│  │   │  • Runs verification                                       │    │  │
│  │   │  • Tracks file changes                                     │    │  │
│  │   └────────────────────────────────────────────────────────────┘    │  │
│  │                                                                      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Skill Type Summary

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                       SKILL TYPE SUMMARY                                    │
│                                                                             │
│  ┌───────────────┬────────────────────┬──────────────────────────────────┐ │
│  │ TYPE          │ SOURCE             │ PURPOSE                          │ │
│  ├───────────────┼────────────────────┼──────────────────────────────────┤ │
│  │               │                    │                                  │ │
│  │ SYSTEM        │ Agent frontmatter  │ General rules                    │ │
│  │ (Tier 1)      │ Always first       │ Apply to all tasks               │ │
│  │               │                    │ NOT in task.skills               │ │
│  │               │                    │                                  │ │
│  ├───────────────┼────────────────────┼──────────────────────────────────┤ │
│  │               │                    │                                  │ │
│  │ DOMAIN        │ Architecture →     │ Domain knowledge                 │ │
│  │ (Tier 2)      │ Module →           │ Patterns, conventions            │ │
│  │               │ Task (resolved     │ Listed in task.skills            │ │
│  │               │ by task-plan)      │                                  │ │
│  │               │                    │                                  │ │
│  ├───────────────┼────────────────────┼──────────────────────────────────┤ │
│  │               │                    │                                  │ │
│  │ WORKFLOW      │ task.profile       │ HOW to execute                   │ │
│  │               │ (impl/testing)     │ Workflow logic                   │ │
│  │               │                    │ Calls manage-* scripts           │ │
│  │               │                    │                                  │ │
│  ├───────────────┼────────────────────┼──────────────────────────────────┤ │
│  │               │                    │                                  │ │
│  │ EXTENSION     │ references.json    │ Domain-specific additions        │ │
│  │               │ .domains           │ Triage extensions                │ │
│  │               │                    │                                  │ │
│  └───────────────┴────────────────────┴──────────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Extensions

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                          EXTENSIONS                                         │
│                                                                             │
│  Extensions add domain-specific knowledge without replacing workflow skills │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                                                                      │  │
│  │  EXTENSION TYPES:                                                    │  │
│  │                                                                      │  │
│  │  ┌──────────────┬─────────┬────────────────────────────────────────┐│  │
│  │  │ TYPE         │ PHASE   │ PURPOSE                                ││  │
│  │  ├──────────────┼─────────┼────────────────────────────────────────┤│  │
│  │  │ outline      │ outline │ Domain detection, deliverable patterns ││  │
│  │  │ triage       │ finalize│ Finding decision-making (fix/suppress) ││  │
│  │  └──────────────┴─────────┴────────────────────────────────────────┘│  │
│  │                                                                      │  │
│  │  RESOLUTION:                                                         │  │
│  │                                                                      │  │
│  │  python3 .plan/execute-script.py                                     │  │
│  │    plan-marshall:manage-plan-marshall-config:plan-marshall-config           │  │
│  │    resolve-workflow-skill-extension                                  │  │
│  │    --domain java                                                     │  │
│  │    --type triage                                                     │  │
│  │                                                                      │  │
│  │  → pm-dev-java:ext-triage-java                                           │  │
│  │                                                                      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Related Documents

| Document | Purpose |
|----------|---------|
| [agents.md](agents.md) | Agent skill loading steps |
| [phases.md](phases.md) | When each skill type is used |
| `plan-marshall:analyze-project-architecture` | Source of module.skills_by_profile |
| `pm-workflow:phase-3-outline` | Where module/skills are selected |
| `pm-workflow:workflow-extension-api` | Extension points |
