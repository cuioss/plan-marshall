# Skills by Profile

Profile-based skill organization for granular task execution.

---

## Overview

Skills flow from architecture → deliverable → task (task-plan splits by profile):

```
analyze-project-architecture    solution_outline.md          TASK-*.toon
┌───────────────────────────┐   ┌─────────────────────────┐  ┌─────────────────┐
│ {module}:                 │   │ domain: {domain}        │  │ TASK-001        │
│   skills_by_profile:      │──▶│ Skills by Profile:      │  │ profile: impl   │
│     skills-implementation │   │   skills-implementation │─▶│ skills: [...]   │
│     skills-testing        │   │   skills-testing        │  ├─────────────────┤
└───────────────────────────┘   └─────────────────────────┘  │ TASK-002        │
                                       │                    │ profile: testing│
                                       └───────────────────▶│ skills: [...]   │
                                                            └─────────────────┘
                               task-plan splits deliverable into tasks per profile
```

---

## Skill Source

Skills come from `module.skills_by_profile` in architecture data.

**EXECUTE**:
```bash
python3 .plan/execute-script.py plan-marshall:analyze-project-architecture:architecture module \
  --name {module}
```

Output format: `plan-marshall:analyze-project-architecture/standards/client-api.md`

---

## Profile Definitions

| Profile Key | Description | When Included |
|-------------|-------------|---------------|
| `skills-implementation` | Production code skills | Always |
| `skills-testing` | Unit test skills | If module has test infrastructure |

**Note**: Integration tests are separate deliverables (different module), not embedded profiles.

---

## Profile Inclusion Decision

**EXECUTE**:
```bash
python3 .plan/execute-script.py plan-marshall:analyze-project-architecture:architecture modules \
  --command module-tests
```

Returns list of module names that have unit test infrastructure.

### Decision Logic

```
IF module in (modules --command module-tests):
    Include skills-testing in deliverable
ELSE:
    Only include skills-implementation
```

---

## Skills by Profile Block Format

In deliverables:

```markdown
**Skills by Profile:**
- skills-implementation: [{implementation skills from module.skills_by_profile}]
- skills-testing: [{testing skills from module.skills_by_profile}]
```

---

## Task-Plan Processing

Task-plan reads the deliverable and creates tasks per profile:

```
TASK-{N}.toon (from skills-implementation):
  deliverable: "{N}. {Deliverable Title}"
  profile: implementation
  skills: [{implementation skills from deliverable}]
  steps: [{ClassName}.java]
  verify: {build compile command}

TASK-{N+1}.toon (from skills-testing):
  deliverable: "{N}. {Deliverable Title}"
  profile: testing
  skills: [{testing skills from deliverable}]
  steps: [{ClassName}Test.java]
  verify: {build test command}
  depends: TASK-{N}
```

---

## Profile Values (Task-Level)

When task-plan creates tasks from deliverables, each task has a single profile:

| Profile | Description | Files | Workflow Skill |
|---------|-------------|-------|----------------|
| `implementation` | Production code | `src/main/**/*.java` | `pm-workflow:phase-execute-implementation` |
| `testing` | Unit/integration tests | `*Test.java`, `*IT.java` | `pm-workflow:phase-execute-testing` |

---

## Design Decision: Skill-Profile Assignment

**ONE deliverable = ONE module. ONE task = ONE profile.**

Each deliverable targets a single module and includes ALL applicable skill sets (`Skills by Profile`). Task-plan splits each deliverable into profile-specific tasks. Integration tests are separate deliverables (different module - the IT module).

### Rationale

| Aspect | Multi-profile per deliverable (chosen) |
|--------|----------------------------------------|
| **User review** | Fewer deliverables (concise) |
| **Skill visibility** | All skill sets visible upfront |
| **Task-plan** | Splits by profile (more flexible) |
| **Module constraint** | One module per deliverable |
| **IT handling** | Separate IT deliverable (different module) |

### Key Insight

- Solution-outline creates one deliverable per module with `Skills by Profile`
- Task-plan splits each deliverable into profile-specific tasks
- IT tests are separate deliverables (target different module)

---

## No Runtime Skill Resolution

With skills pre-resolved in deliverables, task-plan becomes simpler:

```
task-plan receives deliverable:
  domain: {domain}
  Skills by Profile:
    skills-implementation: [{implementation skills}]
    skills-testing: [{testing skills}]

For each profile with skills:
  1. Create task with profile name
  2. Copy skills from deliverable's skills-{profile} field
  3. Add profile-specific verification command
```

No runtime skill resolution needed - skills are already computed by architecture analysis.

---

## Example: Full Flow

1. **Architecture** provides module skills:
```toon
{module}:
  skills_by_profile:
    skills-implementation: [{implementation skills}]
    skills-testing: [{testing skills}]
```

2. **Solution-outline** creates deliverable with Skills by Profile:
```markdown
### {N}. {Deliverable Title}

**Module Context:**
- module: {module}

**Skills by Profile:**
- skills-implementation: [{implementation skills}]
- skills-testing: [{testing skills}]
```

3. **Task-plan** splits into tasks:
```
TASK-{N}.toon:
  profile: implementation
  skills: [{implementation skills}]

TASK-{N+1}.toon:
  profile: testing
  skills: [{testing skills}]
  depends_on: TASK-{N}
```

4. **Task-execute** loads skills from task:
```
Load: {skill-1}
Load: {skill-2}
Execute with workflow skill: pm-workflow:phase-execute-implementation
```
