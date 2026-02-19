# 6-Phase Execution Model

The pm-workflow bundle implements a 6-phase execution model for structured task completion.

---

## Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                         6-PHASE EXECUTION MODEL                             │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                                                                      │  │
│  │   ┌────────┐   ┌─────────┐   ┌───────────┐   ┌────────┐              │  │
│  │   │ 1-INIT │──▶│2-REFINE │──▶│ 3-OUTLINE │──▶│ 4-PLAN │──▶          │  │
│  │   └────────┘   └─────────┘   └───────────┘   └────────┘              │  │
│  │       │             │              │              │                  │  │
│  │   ┌───▼───┐    ┌────▼────┐    ┌────▼────┐   ┌────▼────┐             │  │
│  │   │config │    │clarified│    │solution │   │ TASK-*  │             │  │
│  │   │status │    │ request │    │outline  │   │ .toon   │             │  │
│  │   │request│    │         │    │   .md   │   │  files  │             │  │
│  │   └───────┘    └─────────┘    └─────────┘   └─────────┘             │  │
│  │                                                                      │  │
│  │       ┌───────────┐   ┌──────────┐                                  │  │
│  │   ───▶│ 5-EXECUTE │──▶│7-FINALIZE│                                  │  │
│  │       └───────────┘   └──────────┘                                  │  │
│  │            │               │                                        │  │
│  │       ┌────▼────┐    ┌───▼───┐                                      │  │
│  │       │ project │    │commit │                                      │  │
│  │       │  files  │    │  PR   │                                      │  │
│  │       │modified │    │       │                                      │  │
│  │       │+verified│    └───────┘                                      │  │
│  │       └─────────┘                                                    │  │
│  │                                                                      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Phase Details

### Phase 1: 1-INIT

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  PHASE: 1-INIT                                                              │
│  ═══════════                                                                │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                     │   │
│  │  INPUT                           OUTPUT                             │   │
│  │  ═════                           ══════                             │   │
│  │                                                                     │   │
│  │  • description                   .plan/plans/{plan_id}/             │   │
│  │  • lesson_id                       ├── status.toon                  │   │
│  │  • issue URL                       ├── request.md                   │   │
│  │                                    └── references.json              │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  AGENT: plan-init-agent                                                     │
│  SKILL: pm-workflow:phase-1-init                                            │
│                                                                             │
│  STEPS:                                                                     │
│  ──────                                                                     │
│  1. Validate input (exactly one source)                                     │
│  2. Derive plan_id                                                          │
│  3. Create plan directory                                                   │
│  4. Get task content (from description/lesson/issue)                        │
│  5. Write request.md                                                        │
│  6. Initialize references.json                                              │
│  7. Detect domain                                                           │
│  8. Create status.toon (6-phase model)                                      │
│  9. Store domains in references.json                                        │
│  10. Transition to 2-refine phase                                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### Phase 2: 2-REFINE

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  PHASE: 2-REFINE                                                            │
│  ═════════════                                                              │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                     │   │
│  │  INPUT                           OUTPUT                             │   │
│  │  ═════                           ══════                             │   │
│  │                                                                     │   │
│  │  • request.md                    • clarified_request (in request.md)│   │
│  │  • references.json               • clarifications (Q&A pairs)       │   │
│  │  • project-architecture (*)      • module_mapping                   │   │
│  │                                  • scope_estimate                   │   │
│  │                                  • confidence >= threshold          │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  AGENT: request-refine-agent                                                │
│  SKILL: pm-workflow:phase-2-refine                                          │
│                                                                             │
│  STEPS:                                                                     │
│  ──────                                                                     │
│  0. Load confidence threshold from marshal.json (default: 95%)              │
│  1. Load architecture context                                               │
│  2. Load request                                                            │
│  3. Analyze request quality (correctness, completeness, consistency,        │
│     non-duplication, ambiguity)                                             │
│  4. Analyze in architecture context (module mapping, feasibility, scope)    │
│  5. Evaluate confidence                                                     │
│     IF confidence >= threshold → proceed to 3-outline                       │
│     ELSE → Step 6                                                           │
│  6. Clarify with user (AskUserQuestion)                                     │
│  7. Update request with clarifications                                      │
│     Loop back to Step 3                                                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**(*) Project Architecture**: Module context from `plan-marshall:analyze-project-architecture`.

---

### Phase 3: 3-OUTLINE

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  PHASE: 3-OUTLINE                                                           │
│  ═══════════════                                                            │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                     │   │
│  │  INPUT                           OUTPUT                             │   │
│  │  ═════                           ══════                             │   │
│  │                                                                     │   │
│  │  • clarified_request             solution_outline.md                │   │
│  │  • references.json                  └── Summary                      │   │
│  │  • project-architecture (*)        └── Overview (ASCII diagram)     │   │
│  │                                    └── Deliverables                 │   │
│  │                                        ├── 1. Title                 │   │
│  │                                        │   ├── Metadata             │   │
│  │                                        │   ├── Affected files       │   │
│  │                                        │   └── Verification         │   │
│  │                                        └── 2. Title ...             │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  AGENT: solution-outline-agent                                              │
│  SKILL: pm-workflow:phase-3-outline (or domain-specific extension)          │
│                                                                             │
│  STEPS:                                                                     │
│  ──────                                                                     │
│  1. Load refined request (clarified_request from phase-2-refine)           │
│  2. Load outline extension (if available)                                   │
│  3. Execute workflow:                                                       │
│     • Extension orchestrates (single call):                                 │
│       - Discovery and analysis                                              │
│       - Uncertainty resolution + Synthesize clarified request               │
│       - Call Q-Gate agent (generic, reusable tool)                          │
│       - Build deliverables                                                  │
│       - Return deliverables                                                 │
│     • Generic workflow (if no extension):                                   │
│       - Module selection                                                    │
│       - Package placement                                                   │
│       - Deliverable creation                                                │
│  4. Write solution_outline.md (using deliverables from step 3)              │
│  5. Set domains, record lessons, return results                             │
│  6. ──────────────────────────────────────────────────                      │
│     │  ** USER REVIEW GATE **                                               │
│     │  User must approve before proceeding to 4-plan phase                  │
│     └──────────────────────────────────────────────────                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### Phase 4: 4-PLAN

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  PHASE: 4-PLAN                                                              │
│  ════════════                                                               │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                     │   │
│  │  INPUT                           OUTPUT                             │   │
│  │  ═════                           ══════                             │   │
│  │                                                                     │   │
│  │  solution_outline.md             TASK-001.toon                      │   │
│  │    └── Deliverables              TASK-002.toon                      │   │
│  │        ├── 1. Title              TASK-003.toon                      │   │
│  │        ├── 2. Title              ...                                │   │
│  │        └── 3. Title                                                 │   │
│  │                                  Each task contains:                │   │
│  │                                    • title                          │   │
│  │                                    • deliverable: N                 │   │
│  │                                    • domain                         │   │
│  │                                    • profile                        │   │
│  │                                    • skills: [...]                  │   │
│  │                                    • steps: [file paths]            │   │
│  │                                    • verification                   │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  AGENT: task-plan-agent                                                     │
│  SKILL: pm-workflow:phase-4-plan                                            │
│                                                                             │
│  STEPS:                                                                     │
│  ──────                                                                     │
│  1. Read all deliverables from solution_outline.md                          │
│  2. Build dependency graph                                                  │
│  3. Analyze for aggregation (same domain/profile/change_type)               │
│  4. Analyze for splits (mixed execution_mode)                               │
│  5. Resolve skills from architecture (per profile)                          │
│  6. Create TASK-*.toon files                                                │
│  7. Determine execution order (parallel groups)                             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### Phase 5: 5-EXECUTE

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  PHASE: 5-EXECUTE                                                           │
│  ══════════════                                                             │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                     │   │
│  │  INPUT                           OUTPUT                             │   │
│  │  ═════                           ══════                             │   │
│  │                                                                     │   │
│  │  TASK-001.toon                   Modified project files             │   │
│  │  TASK-002.toon                     • New files created              │   │
│  │  TASK-003.toon                     • Existing files modified        │   │
│  │  ...                               • Tests added/updated            │   │
│  │                                                                     │   │
│  │  For each task:                  Task status updated:               │   │
│  │    • domain                        • pending → in_progress          │   │
│  │    • profile                       • in_progress → completed        │   │
│  │    • skills                                                         │   │
│  │    • steps (file paths)                                             │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  AGENT: task-execute-agent                                                  │
│  SKILL: pm-workflow:task-implementation (or task-module_testing)            │
│                                                                             │
│  EXECUTION LOOP:                                                            │
│  ───────────────                                                            │
│                                                                             │
│     ┌──────────────────────────────────────────────────────────────┐       │
│     │                                                              │       │
│     │  For each task (in dependency order):                        │       │
│     │                                                              │       │
│     │    1. Load task context (manage-tasks get)                   │       │
│     │    2. Load domain skills (from task.skills)                  │       │
│     │    3. Resolve workflow skill (by profile)                    │       │
│     │    4. For each step (file path):                             │       │
│     │       a. Read affected files                                 │       │
│     │       b. Apply domain patterns                               │       │
│     │       c. Implement changes                                   │       │
│     │       d. Mark step complete                                  │       │
│     │    5. Run verification                                       │       │
│     │    6. Mark task complete                                     │       │
│     │                                                              │       │
│     └──────────────────────────────────────────────────────────────┘       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### Phase 7: 7-FINALIZE

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  PHASE: 7-FINALIZE                                                          │
│  ═══════════════                                                            │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                     │   │
│  │  INPUT                           OUTPUT                             │   │
│  │  ═════                           ══════                             │   │
│  │                                                                     │   │
│  │  • marshal.json                   • Git commit                       │   │
│  │    ├── create_pr                 • Branch pushed                    │   │
│  │    └── branch_strategy           • Pull request (if enabled)        │   │
│  │  • references.json               • Plan status: complete            │   │
│  │    ├── branch                                                       │   │
│  │    └── issue_url                                                    │   │
│  │  • Verified project files                                           │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  SKILL: pm-workflow:phase-6-finalize                                        │
│                                                                             │
│  FINALIZE PIPELINE:                                                         │
│  ──────────────────                                                         │
│                                                                             │
│     ┌──────────────────────────────────────────────────────────────┐       │
│     │                                                              │       │
│     │  1. commit_push                                              │       │
│     │     └─▶ Stage, commit, push to remote                        │       │
│     │                                                              │       │
│     │  2. automated_review                                         │       │
│     │     └─▶ Create PR, wait for CI, collect bot feedback         │       │
│     │                                                              │       │
│     │  3. sonar_roundtrip                                          │       │
│     │     └─▶ Wait for analysis, fetch issues, triage              │       │
│     │                                                              │       │
│     │  4. knowledge_capture                                        │       │
│     │     └─▶ Update project-structure.toon (advisory)             │       │
│     │                                                              │       │
│     │  5. lessons_capture                                          │       │
│     │     └─▶ Record notable triage decisions (advisory)           │       │
│     │                                                              │       │
│     │  ON FINDINGS (automated_review/sonar):                       │       │
│     │    → Create fix tasks                                        │       │
│     │    → Loop back to 5-execute                                  │       │
│     │    → Max iterations: 3 (configurable)                        │       │
│     │                                                              │       │
│     │  6. Mark plan complete                                       │       │
│     │     └─▶ transition --completed 6-finalize                    │       │
│     │                                                              │       │
│     └──────────────────────────────────────────────────────────────┘       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Phase Transitions

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                          PHASE TRANSITIONS                                  │
│                                                                             │
│  ┌────────┐    ┌─────────┐    ┌───────────┐    ┌────────┐                  │
│  │ 1-INIT │───▶│2-REFINE │───▶│ 3-OUTLINE │───▶│ 4-PLAN │───▶              │
│  └────────┘    └─────────┘    └───────────┘    └────────┘                  │
│       │             │               │              │                        │
│       │             │          ┌────┴────┐         │                        │
│       │             │          │  USER   │         │                        │
│       │             │          │ REVIEW  │         │                        │
│       │             │          │  GATE   │         │                        │
│       │             │          └────┬────┘         │                        │
│       │             │               │              │                        │
│  auto-continue  threshold met  user-approval  auto-continue                 │
│                                                                             │
│       ┌───────────┐   ┌───────────┐                                        │
│   ───▶│ 5-EXECUTE │──▶│7-FINALIZE │                                        │
│       └───────────┘   └───────────┘                                        │
│            │  ↑              │                                              │
│       auto-continue    pass/fail                                            │
│            │  │              │                                              │
│     [verify+triage]         │                                              │
│       findings? ────────────│──────────┐                                   │
│        (loop)               ▼          │                                   │
│                        ┌──────────┐    │                                   │
│                        │ COMPLETE │    │                                   │
│                        └──────────┘    │                                   │
│                                   5-EXECUTE                                │
│                                  (fix tasks)                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

TRANSITION TRIGGERS:
═══════════════════

┌───────────────┬──────────────┬───────────────────────────────────────────┐
│ From          │ To           │ Trigger                                   │
├───────────────┼──────────────┼───────────────────────────────────────────┤
│ 1-init        │ 2-refine     │ Auto-continue (config/status created)     │
│ 2-refine      │ 3-outline    │ Confidence >= threshold (default 95%)     │
│ 3-outline     │ 4-plan       │ USER APPROVAL of solution outline         │
│ 4-plan        │ 5-execute    │ Auto-continue (tasks created)             │
│ 5-execute     │ 6-finalize   │ All tasks completed + verification passed │
│ 5-execute     │ 5-execute    │ Findings detected → triage + fix tasks    │
│ 6-finalize    │ COMPLETE     │ Commit/PR done (or no findings)           │
│ 6-finalize    │ 5-execute    │ Findings detected → create fix tasks      │
└───────────────┴──────────────┴───────────────────────────────────────────┘
```

---

## Domain Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                           DOMAIN FLOW                                       │
│                                                                             │
│  marshal.json                                                               │
│  ════════════                                                               │
│  skill_domains: [java, javascript, plan-marshall-plugin-dev, ...]           │
│                      │                                                      │
│                      │ all possible domains (project-level)                 │
│                      ▼                                                      │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  REFINE                                                              │  │
│  │  ══════                                                              │  │
│  │  • Loads architecture context                                        │  │
│  │  • Clarifies request until confidence >= threshold                   │  │
│  │  • Maps requirements to modules                                      │  │
│  │  • Updates request.md with clarifications                            │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                      │                                                      │
│                      │ clarified_request                                    │
│                      ▼                                                      │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  OUTLINE                                                             │  │
│  │  ═══════                                                             │  │
│  │  • Analyzes clarified request + architecture context                 │  │
│  │  • Selects modules → determines which profiles apply                 │  │
│  │  • Writes domains + profiles list to deliverables                    │  │
│  │                                                                      │  │
│  │  Example: "Add JWT validation" → module: oauth-sheriff-core          │  │
│  │           → profiles: [implementation, module_testing]               │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                      │                                                      │
│                      │ references.json.domains                                  │
│                      ▼                                                      │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  PLAN                                                                │  │
│  │  ════                                                                │  │
│  │  • Reads deliverable.domain + profiles for each deliverable          │  │
│  │  • Resolves skills from architecture (module.skills_by_profile)      │  │
│  │  • Writes domain + profile + skills to TASK-*.toon                   │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                      │                                                      │
│                      │ task.domain, task.skills                             │
│                      ▼                                                      │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  EXECUTE                                                             │  │
│  │  ═══════                                                             │  │
│  │  • Loads task.skills (domain knowledge)                              │  │
│  │  • Resolves workflow skill for task.profile                          │  │
│  │  • Applies domain patterns during implementation                     │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                      │                                                      │
│                      │ references.json.domains                                  │
│                      ▼                                                      │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  EXECUTE (Verification + Triage Sub-Loop)                            │  │
│  │  ════════════════════════════════════════                            │  │
│  │  • After all tasks complete, runs verification steps                 │  │
│  │  • Reads domains from references.json                                │  │
│  │  • Loads triage extensions for each domain                           │  │
│  │  • On findings: creates fix tasks and loops back                     │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                      │                                                      │
│                      │ verified code                                        │
│                      ▼                                                      │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  FINALIZE                                                            │  │
│  │  ════════                                                            │  │
│  │  • Commits verified code                                             │  │
│  │  • Pushes to remote, creates PR                                      │  │
│  │  • Handles automated review and Sonar feedback                       │  │
│  │  • Captures knowledge and lessons                                    │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Q-Gate Validation Agent

Q-Gate is a GENERIC AGENT TOOL that extensions call during Phase 3 (Outline) to validate assessments.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                        Q-GATE VALIDATION AGENT                              │
│                                                                             │
│  TYPE: Generic agent tool (NOT a workflow step)                             │
│  CALLED BY: Extensions during their workflow                                │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                     │   │
│  │  INPUT                           OUTPUT                             │   │
│  │  ═════                           ══════                             │   │
│  │                                                                     │   │
│  │  • plan_id                       • CONFIRMED assessments            │   │
│  │  • domains                       • FILTERED assessments             │   │
│  │  • CERTAIN_INCLUDE assessments   • affected_files in references.json│   │
│  │                                  • Statistics (confirmed/filtered)  │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  STEPS:                                                                     │
│  ──────                                                                     │
│  1. Load domain skills (via resolve-workflow-skill)                         │
│  2. Read clarified request (or original request)                            │
│  3. Validate each CERTAIN_INCLUDE assessment:                               │
│     • Output Ownership - Component documents another's output               │
│     • Consumer vs Producer - Component consumes, not produces               │
│     • Request Intent Match - Modification fulfills request                  │
│     • Duplicate Detection - Not already covered                             │
│  4. Write CONFIRMED/FILTERED assessments to assessments.jsonl               │
│  5. Persist affected_files to references.json                               │
│  6. Log lifecycle and return statistics                                     │
│                                                                             │
│  WHY GENERIC:                                                               │
│  ───────────                                                                │
│  • Same validation criteria across all domains                              │
│  • Reusable by all domain extensions                                        │
│  • Loads domain skills for context (but validation logic is generic)        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Related Documents

| Document | Purpose |
|----------|---------|
| [agents.md](agents.md) | Thin agent pattern details |
| [skill-loading.md](skill-loading.md) | How skills are resolved |
| [artifacts.md](artifacts.md) | Plan file formats |
| `pm-workflow:workflow-extension-api` | Extension points |
