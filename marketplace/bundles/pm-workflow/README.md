# CUI Task Workflow

Plan-based task management system that transforms high-level task descriptions into executable action sequences through progressive refinement using thin agents and domain-agnostic workflow skills.

## Architecture

**Core Principle**: Thin agents load workflow skills from system domain. Domain knowledge comes from profile-based skill resolution, not hardcoded in agents.

```
User Request → [Thin Agents] → Workflow Skills (from system domain) → Domain Skills (from task.skills) → Result
```

### 5-Phase Execution Model

```
init → outline → plan → execute → finalize
```

| Phase | Purpose | Output |
|-------|---------|--------|
| `init` | Initialize plan | config.toon, status.toon, request.md |
| `outline` | Create solution outline | solution_outline.md |
| `plan` | Decompose into tasks | TASK-*.toon |
| `execute` | Run implementation | Modified project files |
| `finalize` | Commit, PR, quality | Git commit, PR |

## Commands

### /plan-manage
Manage task plans - list, create, refine.

```bash
/plan-manage action=list              # List active plans
/plan-manage action=init task="..."   # Create new plan and refine
/plan-manage action=refine            # Refine specific plan
```

### /plan-execute
Execute task plans - implement, verify, finalize.

```bash
/plan-execute                         # Continue current plan
/plan-execute phase=execute           # Execute specific phase
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
| `solution-outline-agent` | `resolve-workflow-skill --phase outline` | Creates deliverables from request |
| `task-plan-agent` | `resolve-workflow-skill --phase plan` | Creates tasks from deliverables |
| `task-execute-agent` | `resolve-workflow-skill --phase execute` + `task.skills` | Executes single task |
| `plan-finalize-agent` | `resolve-workflow-skill --phase finalize` | Commit, PR, triage |

## Skills

### API Contract Skill

| Skill | Purpose |
|-------|---------|
| `plan-wf-skill-api` | **API contract** for all workflow skills |

### Workflow Skills (System Domain)

Workflow skills are resolved from `system.workflow_skills`:

| Phase | Skill | Purpose |
|-------|-------|---------|
| `init` | `pm-workflow:plan-init` | Create plan structure |
| `outline` | `pm-workflow:phase-refine-outline` | Domain-agnostic solution outline creation |
| `plan` | `pm-workflow:phase-refine-plan` | Domain-agnostic task planning |
| `execute` | `pm-workflow:task-execute` | Domain-agnostic task execution |
| `finalize` | `pm-workflow:plan-finalize` | Domain-agnostic finalization |

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

**Logging**: Work log entries and script execution logging are provided by `plan-marshall:logging` skill.

## Domain Configuration

The system domain contains workflow skills in `marshal.json`:

```json
{
  "skill_domains": {
    "system": {
      "workflow_skills": {
        "init": "pm-workflow:plan-init",
        "outline": "pm-workflow:phase-refine-outline",
        "plan": "pm-workflow:phase-refine-plan",
        "execute": "pm-workflow:task-execute",
        "finalize": "pm-workflow:plan-finalize"
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
        "triage": "pm-dev-java:java-triage"
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
| **Tier 1** | `resolve-workflow-skill --phase execute` | System workflow skill |
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
│   ├── plan-manage.md           # Init + refine phases
│   ├── plan-execute.md          # Execute + finalize phases
│   ├── pr-doctor.md
│   └── task-implement.md
└── skills/
    ├── plan-wf-skill-api/       # API contract for workflow skills
    │   ├── SKILL.md
    │   └── standards/           # Contract documents
    ├── phase-refine-outline/    # Solution outline workflow skill
    ├── phase-refine-plan/       # Task planning workflow skill
    ├── plan-init/               # Init phase skill
    ├── plan-execute/            # Execute phase coordination
    ├── plan-finalize/           # Finalize phase skill
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
