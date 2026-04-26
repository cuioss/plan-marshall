# Solution Outline Standard

This document defines the complete specification for `solution_outline.md` documents, including document structure, deliverable contract, and diagram patterns.

## Document Structure

### File Location

```
.plan/plans/{plan_id}/solution_outline.md
```

### Required Sections

#### Header

```markdown
# Solution: {title}

plan_id: {plan_id}
created: {timestamp}
compatibility: {value} — {long description}
```

- Title should summarize the solution (not just repeat request title)
- `plan_id` must match directory name
- Timestamp in ISO 8601 format
- `compatibility` is set by phase-2-refine from `marshal.json` configuration. Valid values:
  - `breaking` — Clean-slate approach, no deprecation nor transitionary comments
  - `deprecation` — Add deprecation markers to old code, provide migration path
  - `smart_and_ask` — Assess impact and ask user when backward compatibility is uncertain

#### Solution Metadata (Required)

```markdown
## Solution Metadata

- scope_estimate: {none|surgical|single_module|multi_module|broad}
```

**Purpose**: Solution-level metadata that drives downstream Q-Gate bypass and execution-manifest decisions. Distinct from per-deliverable metadata in the Deliverable Contract — these fields describe the *whole* solution, not any single deliverable.

##### scope_estimate

Classifies the change footprint. Required field; the validator rejects the document when the field is missing or its value is not in the enum below.

| Value | Meaning |
|-------|---------|
| `none` | Pure analysis — no affected files (e.g., a research-only plan that produces no diff) |
| `surgical` | ≤3 files in a single module, no public API surface affected |
| `single_module` | ≤10 files inside one module |
| `multi_module` | Touches more than one module |
| `broad` | Codebase-wide changes (glob-only file lists, sweeping refactors) |

**Derivation helper (rule of thumb)**: Compute `scope_estimate` from the union of `affected_files` across all deliverables.

1. If the union is empty (analysis-only) → `none`.
2. Else if all files map to a single module AND the count is ≤3 AND no file is in a public API surface → `surgical`.
3. Else if all files map to a single module AND the count is ≤10 → `single_module`.
4. Else if files map to >1 module → `multi_module`.
5. Else (codebase-wide or glob-only file lists) → `broad`.

`phase-2-refine` produces the initial estimate from the refined-request `module_mappings`. `phase-3-outline` MAY refine it after deliverables crystalize (e.g., a Simple Track plan whose final deliverable list is ≤3 files in one module is downgraded to `surgical`).

**Example**:

```markdown
## Solution Metadata

- scope_estimate: surgical
```

#### Summary (Required)

```markdown
## Summary

{2-3 sentences describing the approach}
```

**Content Guidelines**:
- What will be built/changed
- Why this approach was chosen
- Expected outcome

**Bad Example**: "Implement the requested feature" (too vague)

**Good Example**: "Implement a JWT token validation service for the authentication module. The service will validate tokens, extract claims, and integrate with the existing security context."

#### Overview (Required)

```markdown
## Overview

```
{ASCII diagram}
```
```

**Requirements**:
- Must contain ASCII diagram
- Diagram shows architecture, components, or flow
- Use box-drawing characters for clarity
- Label new vs existing components

See the [Diagram Patterns](#diagram-patterns) section for diagram patterns.

#### Deliverables (Required)

```markdown
## Deliverables

### 1. {First deliverable title}

{Description}

### 2. {Second deliverable title}

{Description}
```

**Requirements**:
- Uses `###` headings (level 3)
- Sequential numbering starting from 1
- Each deliverable independently achievable
- Concrete titles (not abstract goals)

See the [Deliverable Contract](#deliverable-contract) section for the complete deliverable heading and content specification.

### Optional Sections

#### Approach

```markdown
## Approach

{Execution strategy and order}
```

**When to Include**:
- Complex multi-step implementations
- Specific order matters
- Dependencies between deliverables

#### Dependencies

```markdown
## Dependencies

{External requirements, libraries, services}
```

**When to Include**:
- New dependencies needed
- External service requirements
- Environment prerequisites

#### Risks and Mitigations

```markdown
## Risks and Mitigations

- **Risk**: {description}
  - **Mitigation**: {how to address}
```

**When to Include**:
- Significant technical risks
- Breaking changes
- Performance concerns

### Validation

The `manage-solution-outline validate` command checks:

1. Document exists at expected location
2. Required sections present: Solution Metadata, Summary, Overview, Deliverables
3. Solution Metadata block contains `scope_estimate` with a value in the enum (`none|surgical|single_module|multi_module|broad`)
4. Deliverables section has numbered `### N. Title` items
5. At least one deliverable defined
6. Deliverable contract compliance (Metadata, Profiles, Affected files, Verification)
7. Compatibility extraction from header metadata (if present)

**Validation Command**:
```bash
python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage-solution-outline \
  validate \
  --plan-id {plan_id}
```

**Success Output**:
```toon
status: success
plan_id: my-feature
file: solution_outline.md
validation:
  sections_found: solution_metadata,summary,overview,deliverables,approach,dependencies,risks_and_mitigations
  deliverable_count: 4
  deliverables:
    - 1. Create JwtValidationService class
    - 2. Add configuration properties
    - 3. Implement unit tests
    - 4. Add JavaDoc documentation
  compatibility: breaking — Clean-slate approach, no deprecation nor transitionary comments
  scope_estimate: surgical
```

**Failure Output**:
```toon
status: error
plan_id: my-feature
error: validation_failed
issues:
  - Missing required section: Overview
  - Missing required section: Solution Metadata
  - Missing scope_estimate in Solution Metadata
  - Invalid scope_estimate 'huge' (must be one of: none, surgical, single_module, multi_module, broad)
  - No numbered deliverables found (expected ### N. Title)
```

### Section Order

Sections should appear in this order:

1. Header (# Solution: {title})
2. Metadata (plan_id, created)
3. Summary
4. Overview
5. Deliverables
6. Approach (if present)
7. Dependencies (if present)
8. Risks and Mitigations (if present)

---

## Deliverable Contract

Standard structure for deliverables in solution_outline.md that enables task-plan optimization and 5-phase workflow skill routing.

### Purpose

Each deliverable MUST contain sufficient information for:

1. **Grouping analysis**: Can this be aggregated with other deliverables?
2. **Split detection**: Should this be split into multiple tasks?
3. **Domain routing**: Which domain skills should be loaded?
4. **Profile routing**: Which workflow profiles apply (implementation, module_testing)?
5. **Verification consolidation**: Can verification commands be merged?
6. **Dependency ordering**: What order must deliverables execute in?
7. **Parallelization**: Which deliverables can run concurrently?

### Template

For the exact fill-in-the-blank structure, see:

**Template**: `templates/deliverable-template.md`

### Field Definitions

| Field | Required | Description | Used For |
|-------|----------|-------------|----------|
| `change_type` | Yes | Type of change | Grouping analysis |
| `execution_mode` | Yes | automated/manual/mixed | Split detection |
| `domain` | Yes | Single domain from config.domains | Domain skill loading |
| `module` | Yes | Module name from architecture | Skill resolution |
| `depends` | Yes | Dependencies on other deliverables | Ordering, parallelization |
| `**Profiles:**` | Yes | List of profiles (implementation, module_testing) | Task creation (1:N) |
| `Affected files` | Yes | Explicit file list | Step generation |
| `Change per file` | Yes | What changes | Task description |
| `Pattern` | Conditional | Code/format pattern | Implementation guide |
| `Verification` | Yes | How to verify | Task verification |
| `intent_gloss` | Conditional | One-sentence disambiguation (≤15 words) of compound-word deliverable titles | Anchors task.description generation (phase-4-plan) |

### Intent Gloss

**Purpose**: Disambiguate compound-word deliverable titles whose head morpheme is a planning-domain verb (`review`, `check`, `validate`, `approve`, `merge`, …) to prevent phase-4-plan from re-interpreting the label.

**Format**: A single sentence, max ~15 words, that restates the deliverable's goal using the tail morpheme's meaning.

**When required**: Deliverables whose title contains a compound word whose head morpheme is a common task-planning verb.

**Consumption**: phase-4-plan copies this gloss verbatim into every derived `task.description` header (after the verbatim title quote).

**Example** (for deliverable title `review-knowledge`):

```
**Intent gloss:** Review knowledge captured by prior plans (lessons-learned and memories) against this plan's changes.
```

### Domain Values

The `domain` field MUST be a single value from `marshal.json skill_domains`:

| Domain | Description |
|--------|-------------|
| `java` | Java production and test code |
| `javascript` | JavaScript production and test code |
| `plan-marshall-plugin-dev` | Marketplace plugin components |

Multi-domain plans (e.g., fullstack features) have multiple domains in `marshal.json`. Each deliverable selects ONE domain for its work.

> **Note**: The `system` domain is internal-only and must NEVER be assigned to deliverables.

#### Domain Validation

Solution outline skills MUST validate domains exist in marshal.json:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  skill-domains get --domain {domain}
```

Error if domain not found in marshal.json.

### Profiles Block

Each deliverable has a `**Profiles:**` block listing which profiles apply. Task-plan creates one task per profile (1:N mapping).

> Profiles follow the standard profile model. See [manage-contract.md](../../ref-workflow-architecture/standards/manage-contract.md) for the canonical definition. Architecture source for each profile is `module.skills_by_profile.{profile}` (except `verification` which has no architecture source — runs commands only).

**Note**: Integration tests are separate deliverables (different module), not embedded profiles. Verification profile deliverables may have an empty `Affected files` section.

#### Profile Assignment Rules

Assign profiles based on what the **deliverable itself** creates or modifies — not based on what the module supports:

| Deliverable Content | Profiles |
|---------------------|----------|
| Production code only | `implementation` |
| Production code + test files | `implementation`, `module_testing` |
| Test files only | `module_testing` |
| Markdown components (skills/agents/commands) | `implementation` (plugin-doctor verification) |
| Scripts only (no test files) | `implementation` (compile verification) |
| Scripts + test files | `implementation`, `module_testing` |
| Verification only (no file changes, runs commands) | `verification` |

**Key rule**: `module_testing` is assigned only when the deliverable creates or modifies test files. The existence of test infrastructure in the module is irrelevant — it only matters whether *this deliverable* touches test files.

#### Per-Profile Verification Semantics

Each profile has a distinct verification purpose. Implementation verifies compilability. Module_testing verifies test execution. Running existing tests is NOT the job of the implementation task.

| Profile | Verification Purpose |
|---------|---------------------|
| `implementation` | Compile/build only |
| `module_testing` | Run tests |

Verification commands are resolved during the **outline phase** (phase-3-outline Steps 9-10) using architecture resolution or domain-specific commands. The deliverable's Verification block is the single source of truth — downstream phases copy it verbatim.

#### 1:N Task Creation

Task-plan creates one task per profile in the deliverable:

```
solution_outline.md                        TASK-*.toon (created by task-plan)
┌────────────────────────────┐             ┌────────────────────────┐
│ **Metadata:**              │             │ TASK-001          │
│ - domain: java             │             │ profile: implementation│
│ - module: auth-service     │  ───────►   │ skills: [java-core,    │
│                            │  (1:N)      │          java-cdi]     │
│ **Profiles:**              │             ├────────────────────────┤
│ - implementation           │  ───────►   │ TASK-002          │
│ - module_testing           │             │ profile: module_testing│
│                            │             │ skills: [java-core,    │
└────────────────────────────┘             │          junit-core]   │
                                           │ depends: TASK-001 │
                                           └────────────────────────┘
```

#### Skill Resolution Flow

Task-plan resolves skills from architecture for each profile:

```
For each profile in deliverable.profiles:
  1. Query architecture: module --name {module}
  2. Extract: skills_by_profile.{profile}
  3. Create task with profile + resolved skills
```

**Key principle**: Deliverables specify WHAT profiles apply, task-plan resolves WHICH skills from architecture.

### Dependency Specification

The `depends` field enables task-plan to determine execution order and parallelization.

| Value | Meaning | Example |
|-------|---------|---------|
| `none` | No dependencies, can run in parallel | Independent refactoring |
| `N` | Must complete after deliverable N | `1` |
| `N. Title` | Must complete after deliverable N (with title for clarity) | `1. Create Database Schema` |
| `N, M` | Must complete after ALL numbered deliverables | `1, 2, 4` |

#### Dependency Rules

- Use `none` when the deliverable has no prerequisites
- Reference deliverables by number alone (e.g., `1`) or with title (e.g., `1. Create Schema`)
- Title format improves readability - task-plan parses the number prefix
- Multiple dependencies are comma-separated (numbers only for brevity)
- Circular dependencies are INVALID
- Dependencies should reference earlier deliverable numbers (lower numbers first)

### Change Types

The `change_type` field uses the fixed vocabulary defined in `plan-marshall:ref-workflow-architecture/standards/change-types.md`.

| Key | Priority | Description | Grouping Hint |
|-----|----------|-------------|---------------|
| `analysis` | 1 | Investigate, research, understand | Group by investigation target |
| `feature` | 2 | New functionality or component | Group by component type |
| `enhancement` | 3 | Improve existing functionality | Group by change similarity |
| `bug_fix` | 4 | Fix a defect or issue | Keep separate (minimal fix) |
| `tech_debt` | 5 | Refactoring, cleanup, migration, removal | Group by target format or bundle |
| `verification` | 6 | Validate, check, confirm | Group by verification scope |

#### Agent Resolution

Change types determine which agent handles the outline workflow:
1. Detect change_type from request (detect-change-type-agent)
2. Resolve agent from domain config or use generic fallback
3. Agent creates deliverables appropriate for the change type

### Execution Modes

| Mode | Description | Task-Plan Behavior |
|------|-------------|-------------------|
| `automated` | Can run without human intervention | Can aggregate |
| `manual` | Requires human judgment/action | Must split |
| `mixed` | Contains both auto and manual parts | Must split into separate tasks |

### Validation Rules

Solution outline skills MUST validate that each deliverable contains:

- `change_type` metadata
- `execution_mode` metadata
- `domain` metadata (single value from config.domains)
- `module` metadata (module name from architecture)
- `depends` field (`none` or valid deliverable references)
- `**Profiles:**` block with valid profiles (`implementation`, `module_testing`, `integration_testing`, `verification`)
- Explicit file list (not "all files matching X") — except `verification` profile where affected files can be empty
- Verification command and criteria
- `intent_gloss` — required when deliverable title head morpheme is a planning-domain verb; recommended for every deliverable.

### Deliverable ID Format

| Format | Example | Usage |
|--------|---------|-------|
| Number only | `1`, `2` | `task.deliverable: 1` |
| Full reference | `1. Create CacheConfig` | `depends: 1. Create CacheConfig` |

**Parsing rule**: Extract leading integer, ignore title portion.

### Anti-patterns (INVALID deliverables)

- Missing metadata block
- Missing `domain` field (prevents domain skill loading)
- Missing `module` field (prevents skill resolution from architecture)
- Missing `**Profiles:**` block (prevents task creation)
- Empty `**Profiles:**` block (must have at least one profile)
- Invalid profile (not `implementation`, `module_testing`, `integration_testing`, or `verification`)
- Invalid domain (domain not in marshal.json `skill_domains`)
- System domain (using `system` as deliverable domain - internal only)
- "Update all agents" without file enumeration
- Verification: "manual review" for automatable checks
- Missing `depends` field (prevents parallelization analysis)
- Circular dependencies (D1 depends on D2, D2 depends on D1)
- Forward dependencies (D1 depends on D3, where D3 comes after D1)
- Compound-word deliverable (head morpheme is planning-domain verb) without an `**Intent gloss:**` field.

### Terminology

**Why "Deliverables" not "Goals"?**

Solution outlines contain concrete work items, not abstract goals:
- A goal is an outcome: "Users can authenticate via JWT"
- A deliverable is work product: "Create JwtValidationService class"

Deliverables describe what will be built, not why.

### Parsing Deliverable References

The `manage-solution-outline` script provides functions for parsing and extracting deliverables.

See: `plan-marshall:manage-solution-outline:manage-solution-outline`

**Key functions in script**:
- `validate_deliverable(str) -> (int, str)` - Parse `N. Title` format, return (number, full_reference)
- `extract_deliverables(section) -> list[dict]` - Extract from `### N. Title` headings

### Task Integration

When creating tasks that implement deliverables, use heredoc:

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks add \
  --plan-id {plan_id} <<'EOF'
title: Implement JWT validation service
deliverable: 1
domain: java
steps:
  - Create interface
  - Implement validation
  - Add tests
EOF
```

**Note**: `deliverable` accepts a single integer (1:1 constraint — one deliverable per task).

### Listing Deliverables

To extract deliverables from a solution document:

```bash
python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage-solution-outline \
  list-deliverables \
  --plan-id {plan_id}
```

**Output**:
```toon
status: success
plan_id: my-feature
deliverable_count: 4

deliverables[4]:
- number: 1
  title: Create JwtValidationService class
  reference: 1. Create JwtValidationService class
- number: 2
  title: Add configuration support
  reference: 2. Add configuration support
- number: 3
  title: Implement unit tests
  reference: 3. Implement unit tests
- number: 4
  title: Add JavaDoc documentation
  reference: 4. Add JavaDoc documentation
```

### Ordering and Dependencies

Deliverable numbers indicate **suggested execution order**, not strict dependencies.

**When order matters**: Document in the Approach section:

```markdown
## Approach

1. Start with deliverable 1 (interface definition)
2. Deliverables 2-3 can proceed in parallel
3. Deliverable 4 depends on 1-3 completion
```

**When order doesn't matter**: Keep deliverables logically grouped but note flexibility:

```markdown
## Approach

Deliverables 1-3 can be implemented in any order. Deliverable 4 (documentation) should follow implementation.
```

### Examples

For complete examples and anti-patterns, see:
- `templates/deliverable-template.md` - Template with invalid patterns
- `examples/*.md` - Domain-specific examples (java, javascript, plugin, etc.)

---

## Diagram Patterns

General-purpose ASCII diagram patterns used in Overview sections to give reviewers visual orientation, component relationships, dependency direction, and before/after comparisons.

Use Unicode box-drawing characters (`─`, `│`, `┌`, `┐`, `└`, `┘`, `├`, `┤`, `┬`, `┴`, `┼`, `▶`, `◀`, `▼`, `▲`) for clean diagrams.

Choose the pattern that matches the task type:

- **Component diagram** — feature implementations showing class/component relationships. An outer box carries context (module/package), inner boxes represent components with their properties/methods, arrows show dependencies, existing vs new components are labeled, and a footer lists affected file paths.
- **Before/After comparison** — refactoring tasks. Side-by-side BEFORE and AFTER sections with a transformation arrow (`───▶`) showing method movement from a monolith to multiple services and the new dependency structure.
- **Problem/Solution** — bugfix tasks. A "PROBLEM" header introduces a sequence diagram of the failure scenario (e.g. concurrent thread interactions with a shared store) and a "SOLUTION" header shows the new architecture with the added coordinating component highlighted.
- **File Structure** — documentation tasks. A tree view of the directory hierarchy with annotations explaining each file's purpose, followed by a cross-reference block showing how documents link to each other.
- **Integration Flow** — plugin/integration tasks. Horizontal phase boxes (e.g. `PRE-BUILD → BUILD → POST-BUILD`) with downward data-flow arrows into component boxes and a shared storage/state representation at the bottom.

For straightforward tasks prefer minimal diagrams: a linear flow (`Request → Analyze → Implement → Verify → Done`), a branching flow (`Input ──┬── Path A ──┬── Output` / `└── Path B ──┘`), or a cycle (`Start → Process → Check ─┬─ Pass → Done` / `└─ Fail → Process`).

Tips for clarity: keep consistent fixed-width spacing, label every component, show direction with arrows, distinguish new vs existing components with notes, omit unnecessary detail, use an outer box for visual boundary and context, and add a footer with package/file information for navigation.