# Deliverable Contract

Standard structure for deliverables in solution_outline.md that enables task-plan optimization and 5-phase workflow skill routing.

## Purpose

Each deliverable MUST contain sufficient information for:

1. **Grouping analysis**: Can this be aggregated with other deliverables?
2. **Split detection**: Should this be split into multiple tasks?
3. **Domain routing**: Which domain skills should be loaded?
4. **Profile routing**: Which workflow profile (implementation, testing, quality)?
5. **Verification consolidation**: Can verification commands be merged?
6. **Dependency ordering**: What order must deliverables execute in?
7. **Parallelization**: Which deliverables can run concurrently?

## Required Deliverable Structure

All solution-outline skills MUST produce deliverables following this structure:

```markdown
### N. {Deliverable Title}

**Metadata:**
- change_type: {create|modify|refactor|migrate|delete}
- execution_mode: {automated|manual|mixed}
- domain: {java|javascript|plan-marshall-plugin-dev}
- depends: {none | N. Title | N, M}

**Module Context:**
- module: {module-name}
- package: {target-package}
- placement_rationale: {why this module/package}

**Skills by Profile:**
- skills-implementation: [{impl-skill-1}, {impl-skill-2}]
- skills-testing: [{test-skill-1}, {test-skill-2}]  (if module has test infrastructure)

**Affected files:**
- `{path/to/file1}`
- `{path/to/file2}`

**Change per file:** {specific change description}

**Pattern:** (optional, for format changes)
```{format}
{pattern to apply}
```

**Verification:**
- Command: `{verification command}`
- Criteria: {success criteria}

**Success Criteria:**
- {criterion 1}
- {criterion 2}
```

## Field Definitions

| Field | Required | Description | Used For |
|-------|----------|-------------|----------|
| `change_type` | Yes | Type of change | Grouping analysis |
| `execution_mode` | Yes | automated/manual/mixed | Split detection |
| `domain` | Yes | Single domain from config.domains | Domain skill loading |
| `depends` | Yes | Dependencies on other deliverables | Ordering, parallelization |
| `Module Context` | Yes | module, package, placement_rationale | Module/package assignment |
| `Skills by Profile` | Yes | skills-implementation, skills-testing | Task skill inheritance |
| `Affected files` | Yes | Explicit file list | Step generation |
| `Change per file` | Yes | What changes | Task description |
| `Pattern` | Conditional | Code/format pattern | Implementation guide |
| `Verification` | Yes | How to verify | Task verification |

## Domain Values

The `domain` field MUST be a single value from `marshal.json skill_domains`:

| Domain | Description |
|--------|-------------|
| `java` | Java production and test code |
| `javascript` | JavaScript production and test code |
| `plan-marshall-plugin-dev` | Marketplace plugin components |

Multi-domain plans (e.g., fullstack features) have multiple domains in `marshal.json`. Each deliverable selects ONE domain for its work.

> **Note**: The `system` domain is internal-only and must NEVER be assigned to deliverables.

### Domain Validation

Solution outline skills MUST validate domains exist in marshal.json:

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  skill-domains get --domain {domain}
```

Error if domain not found in marshal.json.

## Skills by Profile

Deliverables include ALL applicable skill sets from `module.skills_by_profile`. Task-plan splits these into profile-specific tasks.

| Profile Key | Description | When Included |
|-------------|-------------|---------------|
| `skills-implementation` | Production code skills | Always |
| `skills-testing` | Unit test skills | If module has test infrastructure |

**Note**: Integration tests are separate deliverables (different module), not embedded profiles.

### Profile Values (Task-Level)

When task-plan creates tasks from deliverables, each task has a single profile:

| Profile | Description | Source |
|---------|-------------|--------|
| `implementation` | Production code task | Uses `skills-implementation` |
| `testing` | Unit/integration test task | Uses `skills-testing` |

### Trickle-Down Flow

Skills flow from architecture → deliverable → task (task-plan splits by profile):

```
analyze-project-architecture    solution_outline.md          TASK-*.toon
┌───────────────────────────┐   ┌─────────────────────────┐  ┌─────────────────┐
│ oauth-sheriff-core:       │   │ domain: java            │  │ TASK-001        │
│   skills_by_profile:      │──▶│ Skills by Profile:      │  │ profile: impl   │
│     skills-implementation │   │   skills-implementation │─▶│ skills: [...]   │
│     skills-testing        │   │   skills-testing        │  ├─────────────────┤
└───────────────────────────┘   └─────────────────────────┘  │ TASK-002        │
                                        │                    │ profile: testing│
                                        └───────────────────▶│ skills: [...]   │
                                                             └─────────────────┘
                                task-plan splits deliverable into tasks per profile
```

## Dependency Specification

The `depends` field enables task-plan to determine execution order and parallelization.

| Value | Meaning | Example |
|-------|---------|---------|
| `none` | No dependencies, can run in parallel | Independent refactoring |
| `N` | Must complete after deliverable N | `1` |
| `N. Title` | Must complete after deliverable N (with title for clarity) | `1. Create Database Schema` |
| `N, M` | Must complete after ALL numbered deliverables | `1, 2, 4` |

### Dependency Rules

- Use `none` when the deliverable has no prerequisites
- Reference deliverables by number alone (e.g., `1`) or with title (e.g., `1. Create Schema`)
- Title format improves readability - task-plan parses the number prefix
- Multiple dependencies are comma-separated (numbers only for brevity)
- Circular dependencies are INVALID
- Dependencies should reference earlier deliverable numbers (lower numbers first)

## Change Types

| Type | Description | Grouping Hint |
|------|-------------|---------------|
| `create` | New file/component | Group by component type |
| `modify` | Update existing | Group by change similarity |
| `refactor` | Restructure without behavior change | Keep separate (risky) |
| `migrate` | Format/API migration | Group by target format |
| `delete` | Remove file/component | Group by bundle |

## Execution Modes

| Mode | Description | Task-Plan Behavior |
|------|-------------|-------------------|
| `automated` | Can run without human intervention | Can aggregate |
| `manual` | Requires human judgment/action | Must split |
| `mixed` | Contains both auto and manual parts | Must split into separate tasks |

## Validation Checklist

Solution outline skills MUST validate that each deliverable contains:

- [ ] `change_type` metadata
- [ ] `execution_mode` metadata
- [ ] `domain` metadata (single value from config.domains)
- [ ] `depends` field (`none` or valid deliverable references)
- [ ] Module context (module, package, placement_rationale)
- [ ] Skills by Profile (`skills-implementation` always; `skills-testing` if module has test infra)
- [ ] Explicit file list (not "all files matching X")
- [ ] Verification command and criteria

## Deliverable ID Format

| Format | Example | Usage |
|--------|---------|-------|
| Number only | `1`, `2` | `task.deliverables: [1, 2]` |
| Full reference | `1. Create CacheConfig` | `depends: 1. Create CacheConfig` |

**Parsing rule**: Extract leading integer, ignore title portion.

## Anti-patterns (INVALID deliverables)

- Missing metadata block
- Missing `domain` field (prevents domain skill loading)
- Missing `Skills by Profile` (prevents task skill inheritance)
- Missing `Module Context` (prevents module/package assignment)
- Invalid domain (domain not in marshal.json `skill_domains`)
- System domain (using `system` as deliverable domain - internal only)
- "Update all agents" without file enumeration
- Verification: "manual review" for automatable checks
- Missing `depends` field (prevents parallelization analysis)
- Circular dependencies (D1 depends on D2, D2 depends on D1)
- Forward dependencies (D1 depends on D3, where D3 comes after D1)

## Example Deliverable

```markdown
### 2. Add Auth Endpoint

**Metadata:**
- change_type: create
- execution_mode: automated
- domain: java
- depends: 1. Create Database Schema

**Module Context:**
- module: auth-service
- package: de.cuioss.auth
- placement_rationale: Follows existing controller pattern in auth package

**Skills by Profile:**
- skills-implementation: [pm-dev-java:java-core, pm-dev-java:java-cdi]
- skills-testing: [pm-dev-java:java-core, pm-dev-java:junit-core]

**Affected files:**
- `auth-service/src/main/java/de/cuioss/auth/AuthController.java`
- `auth-service/src/main/java/de/cuioss/auth/dto/AuthRequest.java`
- `auth-service/src/main/java/de/cuioss/auth/dto/AuthResponse.java`

**Change per file:** Create REST endpoint for user authentication with request/response DTOs.

**Pattern:**
```java
@Path("/auth")
@ApplicationScoped
public class AuthController {
    @POST
    public AuthResponse authenticate(AuthRequest request) { ... }
}
```

**Verification:**
- Command: `mvn compile -pl auth-service`
- Criteria: Compilation succeeds

**Success Criteria:**
- REST endpoint accepts POST /auth with username/password
- Returns JWT token on successful authentication
- Returns 401 on invalid credentials
```

## Invalid Examples (Anti-patterns)

### Missing Metadata Block

```markdown
### 1. Update Agent Outputs

Update all agent outputs to use TOON format.

**Verification:** Check manually
```

**Why invalid:**
- No `**Metadata:**` block
- No explicit file list ("all agents" is vague)
- "Check manually" is not an automatable verification

### Vague File References

```markdown
### 2. Update Planning Agents

**Metadata:**
- change_type: modify
- execution_mode: automated
- domain: plan-marshall-plugin-dev
- profile: implementation
- depends: none

**Affected files:**
- All files in marketplace/bundles/planning/agents/

**Verification:**
- Command: `grep -l '```toon' *.md`
- Criteria: All files match
```

**Why invalid:**
- `Affected files` uses "All files in..." instead of explicit paths
- Task-plan cannot generate steps from vague references
- Validation will reject this deliverable
