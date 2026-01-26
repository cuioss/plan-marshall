# CUI Task Workflow

Plan-based task management system that transforms high-level task descriptions into executable action sequences through progressive 7-phase workflow using thin agents and domain-agnostic workflow skills.

## Architecture

**Core Principle**: Thin agents load workflow skills from system domain. Domain knowledge comes from profile-based skill resolution, not hardcoded in agents.

```
User Request → [Thin Agents] → Workflow Skills (from system domain) → Domain Skills (from task.skills) → Result
```

### 7-Phase Execution Model

```
1-init → 2-refine → 3-outline → 4-plan → 5-execute → 6-verify → 7-finalize
```

| Phase | Purpose | Output |
|-------|---------|--------|
| `1-init` | Initialize plan | config.toon, status.toon, request.md |
| `2-refine` | Clarify request | Refined request with confidence score |
| `3-outline` | Create solution outline | solution_outline.md |
| `4-plan` | Decompose into tasks | TASK-*.toon |
| `5-execute` | Run implementation | Modified project files |
| `6-verify` | Quality verification | Build, lint, tests passed |
| `7-finalize` | Commit, PR, shipping | Git commit, PR |

## Commands

### /plan-marshall
Unified plan lifecycle management - create, outline, execute, verify, finalize.

```bash
/plan-marshall                                # List active plans
/plan-marshall action=init task="..."         # Create new plan and outline
/plan-marshall action=outline plan="X"        # Outline specific plan
/plan-marshall action=execute plan="X"        # Execute tasks
/plan-marshall action=verify plan="X"         # Quality verification
/plan-marshall action=finalize plan="X"       # Commit, PR
/plan-marshall plan="X"                       # Auto-detect phase and continue
```

### /pr-doctor
Diagnose and fix PR issues (build, reviews, Sonar).

```bash
/pr-doctor pr=123
/pr-doctor checks=sonar
```

### /task-implement
Quick task implementation (combines create + execute).

```bash
/task-implement task=123              # From GitHub issue
/task-implement task="Add feature"    # From description
```

## Thin Agent Pattern

All agents are domain-agnostic wrappers that load skills via system domain resolution:

| Agent | Skill Resolution | Purpose |
|-------|-----------------|---------|
| `plan-init-agent` | System defaults only | Creates plan, detects domains |
| `request-refine-agent` | `resolve-workflow-skill --phase 2-refine` | Clarifies request until confidence threshold |
| `solution-outline-agent` | `resolve-workflow-skill --phase 3-outline` | Creates deliverables from request |
| `task-plan-agent` | `resolve-workflow-skill --phase 4-plan` | Creates tasks from deliverables |
| `task-execute-agent` | `resolve-workflow-skill --phase 5-execute` + `task.skills` | Executes single task |
| `plan-verify-agent` | `resolve-workflow-skill --phase 6-verify` | Quality verification |
| `plan-finalize-agent` | `resolve-workflow-skill --phase 7-finalize` | Commit, PR, triage |

## Skills

### API Contract Skill

| Skill | Purpose |
|-------|---------|
| `workflow-extension-api` | **Extension points** for domain-specific workflow customization |

### Workflow Skills (System Domain)

Workflow skills are resolved from `system.workflow_skills`:

| Phase | Skill | Purpose |
|-------|-------|---------|
| `1-init` | `pm-workflow:phase-1-init` | Create plan structure |
| `2-refine` | `pm-workflow:phase-2-refine` | Clarify request until confidence threshold |
| `3-outline` | `pm-workflow:phase-3-outline` | Domain-agnostic solution outline creation |
| `4-plan` | `pm-workflow:phase-4-plan` | Domain-agnostic task planning |
| `5-execute` | `pm-workflow:phase-5-execute` | Domain-agnostic task execution |
| `6-verify` | `pm-workflow:phase-6-verify` | Domain-agnostic verification |
| `7-finalize` | `pm-workflow:phase-7-finalize` | Domain-agnostic finalization |

### Workflow Skill Extensions

Domain-specific extensions loaded via `resolve-workflow-skill-extension`:

| Extension Type | Phase | Purpose |
|----------------|-------|---------|
| `outline` | outline | Domain detection, deliverable patterns |
| `triage` | finalize | Finding decision-making (fix/suppress/accept) |

### Support Skills

| Skill | Purpose |
|-------|---------|
| `git-workflow` | Git commit operations |
| `pr-workflow` | PR creation and management |
| `sonar-workflow` | Sonar issue handling |

### Manage Skills (Data/Artifact CRUD)

| Skill | Script | Purpose |
|-------|--------|---------|
| `manage-plan-documents` | `manage-plan-document.py` | Request/Solution document CRUD |
| `manage-solution-outline` | `manage-solution-outline.py` | Solution outline queries |
| `manage-tasks` | `manage-tasks.py` | Tasks + steps CRUD |
| `manage-files` | `manage-files.py` | Generic file I/O |
| `manage-config` | `manage-config.py` | config.toon domain |
| `manage-references` | `manage-references.py` | references.toon domain |
| `manage-lifecycle` | `manage-lifecycle.py` | status.toon + phases |

**Logging**: Work log entries and script execution logging are provided by `plan-marshall:manage-logging` skill.

## Domain Configuration

The system domain contains workflow skills in `marshal.json`:

```json
{
  "skill_domains": {
    "system": {
      "workflow_skills": {
        "1-init": "pm-workflow:phase-1-init",
        "2-refine": "pm-workflow:phase-2-refine",
        "3-outline": "pm-workflow:phase-3-outline",
        "4-plan": "pm-workflow:phase-4-plan",
        "5-execute": "pm-workflow:phase-5-execute",
        "6-verify": "pm-workflow:phase-6-verify",
        "7-finalize": "pm-workflow:phase-7-finalize"
      }
    }
  }
}
```

Technical domains have profile-based skills and workflow extensions:

```json
{
  "skill_domains": {
    "java": {
      "workflow_skill_extensions": {
        "outline": "pm-dev-java:java-outline-ext",
        "triage": "pm-dev-java:ext-triage-java"
      },
      "core": {
        "defaults": ["pm-dev-java:java-core"],
        "optionals": ["pm-dev-java:java-null-safety"]
      },
      "implementation": { ... },
      "testing": { ... },
      "quality": { ... }
    }
  }
}
```

Plan-level `config.toon` stores domains for the current plan:

```toon
domains: [java]
```

## Two-Tier Skill Loading

Task execution uses two-tier skill loading:

| Tier | Source | Purpose |
|------|--------|---------|
| **Tier 1** | `resolve-workflow-skill --phase 5-execute` | System workflow skill |
| **Tier 2** | `task.skills` array | Domain-specific skills (resolved by task-plan) |

Task-plan inherits skills from deliverables (selected during outline from module.skills_by_profile):
```
Deliverable → task.skills: [pm-dev-java:java-core, pm-dev-java:java-cdi]
```

## File Structure

```
pm-workflow/
├── README.md                    # This file
├── agents/
│   ├── plan-init-agent.md       # Creates plan, detects domains
│   ├── solution-outline-agent.md # Creates deliverables
│   ├── task-plan-agent.md       # Creates tasks
│   └── task-execute-agent.md    # Executes single task
├── commands/
│   ├── pr-doctor.md
│   └── task-implement.md
└── skills/
    ├── workflow-extension-api/  # Extension points for domain customization
    │   ├── SKILL.md
    │   └── standards/           # Extension and profile contracts
    ├── phase-1-init/            # Init phase skill
    ├── phase-2-refine/          # Request refinement workflow skill
    ├── phase-3-outline/         # Solution outline workflow skill
    ├── phase-4-plan/            # Task planning workflow skill
    ├── phase-5-execute/         # Execute phase coordination
    ├── phase-6-verify/          # Verify phase skill
    ├── phase-7-finalize/        # Finalize phase skill
    ├── task-implementation/     # Implementation profile workflow
    ├── task-module_testing/     # Module testing profile workflow
    ├── manage-plan-documents/   # Request/Solution document CRUD
    ├── manage-solution-outline/ # Solution outline queries
    ├── manage-tasks/            # Tasks + steps CRUD
    ├── manage-files/            # Generic file I/O
    ├── manage-config/           # config.toon domain
    ├── manage-references/       # references.toon domain
    ├── manage-lifecycle/        # status.toon + phases
    ├── git-workflow/
    ├── pr-workflow/
    └── sonar-workflow/

.plan/                           # Plan storage (per project)
├── plans/                       # Active plans
│   └── {plan-name}/
│       ├── request.md
│       ├── solution_outline.md
│       ├── config.toon
│       └── tasks/
└── archived-plans/              # Completed plans
```

## Dependencies

- **plan-marshall** - Script runner, file operations base, domain skill configuration
- **pm-plugin-development** - Plugin domain skills (plugin-architecture, plugin-create, plugin-maintain)
- **pm-dev-builder** - Build execution (maven/npm)
- **pm-dev-java** - Java domain skills (java-core, java-cdi, junit-core, etc.)
- **pm-dev-frontend** - JavaScript domain skills (cui-javascript, cui-jsdoc, etc.)

## Installation

```bash
/plugin install pm-workflow
```
