# Solution Outline Skill Contract

Workflow skill for outline phase - transforms requests into solution outlines with deliverables using architecture-driven module selection.

**Implementation**: `pm-workflow:phase-refine-outline`

---

## Purpose

Solution outline skills analyze a request and produce a structured solution outline document containing deliverables. Each deliverable follows the [Deliverable Contract](../../manage-solution-outline/standards/deliverable-contract.md).

**Core constraint**: One deliverable = one module.

**Flow**: Architecture → Request → Module Selection → Deliverables → config.toon.domains

---

## Invocation

**Phase**: `outline`

**Agent invocation**:
```bash
plan-phase-agent plan_id={plan_id} phase=outline
```

**Skill resolution**:
```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall-config:plan-marshall-config \
  resolve-workflow-skill --phase outline
```

Result:
```toon
status: success
domain: system
phase: outline
workflow_skill: pm-workflow:phase-refine-outline
```

---

## Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan_id` | string | Yes | Plan identifier |
| `feedback` | string | No | User feedback from review (for revision iterations) |

---

## Workflow Steps

The workflow skill executes these steps in order:

### Step 1: Load Architecture Context (MANDATORY)

Query project architecture before any codebase exploration. Architecture data is pre-computed and compact (~500 tokens).

```bash
python3 .plan/execute-script.py plan-marshall:analyze-project-architecture:architecture info
```

**If architecture data not found**: Return error `{status: error, message: "Run /marshall-steward first"}` and abort.

### Step 2: Load and Understand Requirements

Load the request document and extract actionable requirements:

```bash
python3 .plan/execute-script.py pm-workflow:manage-plan-documents:manage-plan-documents read \
  --plan-id {plan_id} --type request
```

Parse for:
- Functional requirements (what to build)
- Constraints (technology, patterns, compatibility)
- Explicit test requirements (unit, integration, E2E)
- Acceptance criteria

### Step 3: Assess Complexity (Simple vs Complex)

Determine if task is single-module (simple) or multi-module (complex):

| Scope | Workflow | Action |
|-------|----------|--------|
| Single module affected | **Simple** | Proceed to module selection |
| Multiple modules affected | **Complex** | Decompose first, then simple workflow per sub-task |

For complex tasks, load the complete dependency graph to determine ordering:

```bash
python3 .plan/execute-script.py plan-marshall:analyze-project-architecture:architecture graph
```

Output format: `plan-marshall:analyze-project-architecture/standards/module-graph-format.md`

### Step 4: Select Target Modules

For simple tasks: identify the single affected module. For complex tasks: select module for each sub-task.

Score by responsibility match, purpose fit, and package alignment.

### Step 5: Determine Package Placement

For each module, determine where new code belongs using `--full` to see complete package structure:

```bash
python3 .plan/execute-script.py plan-marshall:analyze-project-architecture:architecture module \
  --name {module} --full
```

### Step 6: Create Deliverables with Skills by Profile

Create deliverables with module context and skills organized by profile. Each deliverable includes:
- Module context (module, package, placement_rationale)
- Skills by Profile block from `module.skills_by_profile`

**Skills by Profile inclusion** (per deliverable):
- `skills-implementation`: Always included
- `skills-testing`: Only if module has test infrastructure (`architecture modules --command module-tests`)

Task-plan will split each deliverable into profile-specific tasks.

### Step 7: Create IT Deliverable (Optional)

If integration tests are needed, create a **separate deliverable** targeting the IT module.

**When to create**:
- Explicit request mentions "integration test", "IT", "E2E"
- Change is external-facing (API, UI, public library API, config)

**Prerequisite**: Project has IT infrastructure:
```bash
python3 .plan/execute-script.py plan-marshall:analyze-project-architecture:architecture modules \
  --command integration-tests
```

If result is empty, skip IT deliverable (no IT module exists).

```
Workflow Steps:
┌──────────────────────────────────────────────────────────────────┐
│ Step 1: Load architecture context (MANDATORY)                    │
│         → architecture info                                      │
│                                                                  │
│ Step 2: Load and understand requirements                         │
│         → manage-plan-documents read --type request              │
│                                                                  │
│ Step 3: Assess complexity (simple vs complex)                    │
│         → Decompose if multi-module                              │
│                                                                  │
│ Step 4: Select target modules                                    │
│         → Score by responsibility, purpose, packages             │
│                                                                  │
│ Step 5: Determine package placement                              │
│         → architecture module --name X --full                    │
│                                                                  │
│ Step 6: Create deliverables with Skills by Profile               │
│         → One deliverable per module                             │
│         → Skills by Profile from module.skills_by_profile        │
│         → Task-plan splits into profile-specific tasks           │
│                                                                  │
│ Step 7: Create IT deliverable (optional)                         │
│         → architecture modules --command integration-tests       │
│         → Separate deliverable targeting IT module               │
└──────────────────────────────────────────────────────────────────┘
```

---

## Architecture Data Loading

Module context comes from `analyze-project-architecture`:

### Project Overview

```bash
python3 .plan/execute-script.py plan-marshall:analyze-project-architecture:architecture info
```

Returns project type, detected domains, and module list.

### Module Details (with full package structure)

```bash
python3 .plan/execute-script.py plan-marshall:analyze-project-architecture:architecture module \
  --name {module} --full
```

Result includes:
```toon
status: success
module:
  name: oauth-sheriff-core
  path: oauth-sheriff-core
  responsibility: Core JWT validation logic
  purpose: library
  internal_dependencies: [oauth-sheriff-api]
  key_packages:
    - name: de.cuioss.sheriff.oauth.core.pipeline
      description: JWT validation pipeline
  skills_by_profile:
    skills-implementation: [pm-dev-java:java-core, pm-dev-java:java-cdi]
    skills-testing: [pm-dev-java:java-core, pm-dev-java:junit-core]
  tips: [...]
  best_practices: [...]
```

### Module Queries by Command

```bash
# Get modules with unit test infrastructure
python3 .plan/execute-script.py plan-marshall:analyze-project-architecture:architecture modules \
  --command module-tests

# Get modules with IT infrastructure
python3 .plan/execute-script.py plan-marshall:analyze-project-architecture:architecture modules \
  --command integration-tests
```

Returns list of module names that provide the specified command.

### Skill Assignment

When creating deliverables, copy the module's `skills_by_profile` to the deliverable's `Skills by Profile` block:
- `skills-implementation`: Always included
- `skills-testing`: Only if module has test infrastructure

Task-plan will split each deliverable into profile-specific tasks.

---

## config.toon.domains Output

The workflow skill writes detected domains to config.toon:

```bash
python3 .plan/execute-script.py pm-workflow:manage-config:manage-config set-domains \
  --plan-id {plan_id} --domains java,javascript
```

This is an **intelligent decision output** - not a copy of marshal.json domains, but Claude's analysis of which domains are relevant to the specific request.

---

## Knowledge Level

**Source**: `analyze-project-architecture` output

**Knowledge includes**:
- Module names, paths, responsibilities, purposes
- Key packages with descriptions
- Skills by profile (`skills_by_profile`)
- Internal dependencies between modules
- Tips, best practices, and insights per module
- Available commands per module (e.g., `module-tests`, `integration-tests`)

**Knowledge excludes**:
- Implementation patterns (Builder, Factory, etc.)
- Specific annotations (@Inject, @Nullable)
- Testing patterns (mocking, fixtures)
- Error handling patterns

---

## Output Validation

The workflow skill MUST validate that each deliverable contains all required fields from the [Deliverable Contract](../../manage-solution-outline/standards/deliverable-contract.md):

- [ ] `change_type` metadata
- [ ] `execution_mode` metadata
- [ ] `domain` metadata (valid domain from marshal.json)
- [ ] `depends` field (`none` or valid deliverable references)
- [ ] Module context (module, package, placement_rationale)
- [ ] Skills by Profile (`skills-implementation` always; `skills-testing` if module has test infra)
- [ ] Explicit file list (not "all files matching X")
- [ ] Verification command and criteria

---

## Script API Calls

### Architecture Operations

```bash
# Project overview (Step 1)
python3 .plan/execute-script.py plan-marshall:analyze-project-architecture:architecture info

# Module details with full package structure (Steps 4-5)
python3 .plan/execute-script.py plan-marshall:analyze-project-architecture:architecture module \
  --name {module} --full

# Module infrastructure queries (Steps 6-7)
python3 .plan/execute-script.py plan-marshall:analyze-project-architecture:architecture modules \
  --command module-tests
python3 .plan/execute-script.py plan-marshall:analyze-project-architecture:architecture modules \
  --command integration-tests
```

### Request Loading (Step 2)

```bash
python3 .plan/execute-script.py pm-workflow:manage-plan-documents:manage-plan-documents read \
  --plan-id {plan_id} --type request
```

### Solution Outline Operations

```bash
# Write solution outline
python3 .plan/execute-script.py pm-workflow:manage-solution-outline:manage-solution-outline write \
  --plan-id {plan_id} --content "$(cat <<'HEREDOC'
...content...
HEREDOC
)"

# Validate
python3 .plan/execute-script.py pm-workflow:manage-solution-outline:manage-solution-outline validate \
  --plan-id {plan_id}
```

### Config Domains Output

```bash
python3 .plan/execute-script.py pm-workflow:manage-config:manage-config set-domains \
  --plan-id {plan_id} --domains java,javascript
```

---

## Return Structure

```toon
status: success|error
plan_id: {plan_id}
deliverable_count: {N}
domains_detected: [java, javascript]
lessons_recorded: {count}
message: {error message if status=error}
```

---

## Error Handling

| Scenario | Action |
|----------|--------|
| Architecture not found | Return `{status: error, message: "Run /marshall-steward first"}` and abort |
| Request not found | Return `{status: error, message: "Request not found"}` |
| Validation fails | Fix issues or return partial with error list |
| Domain unknown | Return error with valid domains |
| Script execution fails | Record lesson-learned, return error |

---

## Phase Transition

After completion, the orchestrator triggers [User Review Protocol](user-review-protocol.md).

```
outline ──user approval gate──▶ plan
```

---

## Related Documents

- `pm-workflow:phase-init/SKILL.md` - Previous phase (init)
- [phase-plan-contract.md](phase-plan-contract.md) - Next phase (plan)
- [deliverable-contract.md](../../manage-solution-outline/standards/deliverable-contract.md) - Deliverable structure
- [user-review-protocol.md](user-review-protocol.md) - Approval gate after outline
- `plan-marshall:analyze-project-architecture` - Architecture API documentation
