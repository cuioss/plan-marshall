---
name: manage-solution-outline
description: Manage solution outline documents - standards, examples, validation, and deliverable extraction
user-invocable: false
scope: plan
---

# Manage Solution Outline Skill

This skill provides structure guidelines, examples, and operations for `solution_outline.md` documents. Load this skill when creating or modifying solution outlines.

## Enforcement

**Execution mode**: Run scripts exactly as documented; use Write tool for document content, then validate via script.

**Prohibited actions:**
- Do not modify solution_outline.md through the script API write path; use Write tool then validate
- Do not invent script arguments not listed in the Scripts Used table
- Do not skip validation after writing or updating solution content

**Constraints:**
- All commands use `python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage-solution-outline {command} {args}`
- Document creation follows the resolve-path, Write, validate pattern
- Deliverable numbering must be sequential starting from 1

## When to Activate This Skill

Load this skill in Step 1 when:
- Creating a solution outline (via `phase-3-outline` skill)
- Reviewing or updating an existing solution outline
- Validating solution document structure

**First action**: Load `plan-marshall:manage-architecture` skill for module information and architectural context.

**Not needed for**: Creating tasks from deliverables (use manage-tasks skill)

---

## Document Structure

Solution outlines have a fixed structure with required and optional sections:

```markdown
# Solution: {title}

plan_id: {plan_id}
created: {timestamp}
compatibility: {value} — {long description}

## Summary          ← REQUIRED: 2-3 sentences describing the approach

## Overview         ← REQUIRED: ASCII diagram showing architecture/flow

## Deliverables     ← REQUIRED: Numbered ### sections

## Approach         ← OPTIONAL: Execution strategy

## Dependencies     ← OPTIONAL: External requirements

## Risks and Mitigations  ← OPTIONAL: Risk analysis
```

See [standards/structure.md](standards/structure.md) for detailed requirements.

---

## Deliverables Format

Deliverables use numbered `###` headings:

```markdown
## Deliverables

### 1. Create JwtValidationService class

Description of what this deliverable produces.

**Location**: `src/main/java/de/cuioss/auth/jwt/JwtValidationService.java`

**Responsibilities**:
- Validate JWT signature
- Check token expiration

### 2. Add configuration support

Description...
```

**Key Rules**:
- Numbers must be sequential starting from 1
- Titles should be concrete work items (not abstract goals)
- Each deliverable should be independently achievable
- Include location, responsibilities, or success criteria

See [standards/deliverable-contract.md](standards/deliverable-contract.md) for reference format.

---

## Overview Diagrams

The Overview section contains ASCII diagrams showing component relationships. Different task types use different diagram patterns:

| Task Type | Diagram Style |
|-----------|---------------|
| Feature | Component/class relationships with dependencies |
| Refactoring | BEFORE → AFTER transformation comparison |
| Bugfix | Problem sequence + Solution architecture |
| Documentation | File structure with cross-references |
| Plugin | Integration flow with build phases |

See [standards/diagrams.md](standards/diagrams.md) for patterns and examples.

---

## Examples by Task Type

Examples provide starting points for different task categories:

| Example | Use When |
|---------|----------|
| [examples/java-feature.md](examples/java-feature.md) | Java feature implementation |
| [examples/javascript-feature.md](examples/javascript-feature.md) | JavaScript/frontend feature |
| [examples/plugin-feature.md](examples/plugin-feature.md) | Claude Code plugin development |
| [examples/refactoring.md](examples/refactoring.md) | Code refactoring tasks |
| [examples/bugfix.md](examples/bugfix.md) | Bug fix with root cause analysis |
| [examples/documentation-task.md](examples/documentation-task.md) | Documentation creation/updates |

---

## Writing the Solution Document

### Step 1: Load Project Architecture

Load project architecture knowledge via the `plan-marshall:manage-architecture` skill:

```
Skill: plan-marshall:manage-architecture
```

Then query module information:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture info
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture module --name {module-name}
```

Use the returned structure for:

| Section | Use For |
|---------|---------|
| `modules.{name}.responsibility` | Understand what each module does |
| `modules.{name}.purpose` | Understand module classification (library, extension, etc.) |
| `modules.{name}.key_packages` | Identify architecturally significant packages |
| `modules.{name}.skills_by_profile` | Know which skills apply per profile |
| `modules.{name}.tips` | Apply implementation guidance |
| `modules.{name}.insights` | Leverage learned knowledge |
| `internal_dependencies` | Know what depends on what |

### Step 2: Analyze Request

Read the request document to understand:
- What is being requested
- Scope and constraints
- Success criteria

### Step 3: Design Architecture

Before writing, determine:
- Components involved
- Dependencies between components
- Execution order

### Step 4: Create Diagram

Draw ASCII diagram showing:
- New components (boxed)
- Existing components (labeled)
- Dependencies (arrows)
- Package/file structure

### Step 5: Write and Validate Document

Use the resolve-path → Write → validate pattern:

```bash
# 1. Get target path
python3 .plan/execute-script.py \
  plan-marshall:manage-solution-outline:manage-solution-outline resolve-path \
  --plan-id {plan_id}
# Returns: path: .plan/plans/{plan_id}/solution_outline.md

# 2. Write content directly (Write tool — already permitted via Write(.plan/**))
Write({resolved_path}) with solution outline content

# 3. Validate
python3 .plan/execute-script.py \
  plan-marshall:manage-solution-outline:manage-solution-outline write \
  --plan-id {plan_id}
```

**Parameters**:
- `--plan-id` (required): Plan identifier

**Note**: The `write` command validates the file already on disk — it does NOT read from stdin. Checks for required sections (Summary, Overview, Deliverables) and numbered deliverable format (`### N. Title`). Returns `validation_failed` error if validation fails.

**Workflow clarification**: The Write tool creates/updates the file content. The script commands (`write`/`update`) only validate what's on disk. This separation allows the LLM to compose content freely while ensuring structural compliance.

---

## Deliverable References

When tasks reference deliverables, use the full reference format:

```toon
deliverable: "1. Create JwtValidationService class"
```

**Reference Format Rules**:
- Include number and full title
- Format: `N. Title` (number, dot, space, title)
- Title must match exactly what's in solution document

**Validation**:
```bash
python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage-solution-outline \
  list-deliverables \
  --plan-id {plan_id}
```

---

## Error Responses

All errors return TOON with `status: error` and exit code 1.

| Error Code | Cause |
|------------|-------|
| `file_not_found` | solution_outline.md doesn't exist |
| `document_not_found` | Same as file_not_found (used by `update` command) |
| `parse_error` | Failed to parse document structure |
| `validation_failed` | Missing required sections (Summary, Overview, or Deliverables), or deliverable numbering not sequential |
| `deliverable_not_found` | Requested deliverable number doesn't exist (read with `--deliverable-number`) |

```toon
status: error
plan_id: my-plan
error: validation_failed
message: Missing required section: Overview
```

See also [standards/deliverable-contract.md](standards/deliverable-contract.md) for deliverable validation criteria used during task planning.

## Integration

**Loaded by**:
- `plan-marshall:phase-3-outline` skill (loads domain skills from references.json)
- Domain skills: `pm-plugin-development:ext-outline-workflow`, etc.

**Data Sources** (via skills):
- `plan-marshall:manage-architecture` - Project architecture knowledge (modules, responsibilities, packages)
- `marshal.json` - Module domains for skill routing
- Request document - What is being requested

**Scripts Used**:

**Script**: `plan-marshall:manage-solution-outline:manage-solution-outline`

| Command | Parameters | Description |
|---------|------------|-------------|
| `resolve-path` | `--plan-id` | Get target file path (returns `path: .plan/plans/{plan_id}/solution_outline.md`) |
| `write` | `--plan-id` | Validate newly created solution on disk; sets `action: created`. Returns `file_exists` error if file was already validated via `write` before — use `update` instead. |
| `update` | `--plan-id` | Validate updated solution on disk; sets `action: updated`. Returns `document_not_found` if file doesn't exist — use `write` for initial creation. |
| `validate` | `--plan-id` | Validate structure |
| `read` | `--plan-id [--raw] [--deliverable-number N]` | Read solution or specific deliverable |
| `list-deliverables` | `--plan-id` | Extract deliverables list |
| `exists` | `--plan-id` | Check if solution exists |

**Related Skills**:
- `plan-marshall:manage-architecture` - Project architecture knowledge (load in Step 0)
- `plan-marshall:manage-tasks` - Task creation with deliverable references
- `plan-marshall:manage-plan-documents` - Request document operations

---

## Script Output Examples

### write

**Output** (TOON):
```toon
status: success
plan_id: my-feature
file: solution_outline.md
action: created
validation:
  deliverable_count: 3
  sections_found: summary,overview,deliverables
  compatibility: breaking — Clean-slate approach, no deprecation nor transitionary comments
```

### update

**Output** (TOON) — same as `write` but `action` is always `updated`:
```toon
status: success
plan_id: my-feature
file: solution_outline.md
action: updated
validation:
  deliverable_count: 3
  sections_found: summary,overview,deliverables
```

Returns error `document_not_found` if solution outline does not exist (use `write` to create first).

### validate

**Output** (TOON):
```toon
status: success
plan_id: my-feature
file: solution_outline.md
validation:
  sections_found: summary,overview,deliverables
  deliverable_count: 3
  deliverables:
    - 1. Create JwtValidationService class
    - 2. Add configuration support
    - 3. Create unit tests
  compatibility: breaking — Clean-slate approach, no deprecation nor transitionary comments
```

### list-deliverables

**Output** (TOON):
```toon
status: success
plan_id: my-feature
deliverable_count: 3
deliverables:
  - number: 1
    title: Create JwtValidationService class
    reference: 1. Create JwtValidationService class
  - number: 2
    title: Add configuration support
    reference: 2. Add configuration support
```

### read

**Output** (TOON):
```toon
status: success
plan_id: my-feature
file: solution_outline.md
content:
  _header: # Solution: JWT Validation...
  summary: Implement JWT validation service...
  overview: Component architecture diagram...
  deliverables: ### 1. Create JwtValidationService...
```

With `--raw`: Returns raw markdown content.

With `--deliverable-number N`: Returns a specific deliverable by number.

**Example**: Read deliverable 3:
```bash
python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage-solution-outline read \
  --plan-id {plan_id} \
  --deliverable-number 3
```

**Output** (TOON):
```toon
status: success
plan_id: my-feature
deliverable:
  number: 3
  title: Implement unit tests
  reference: 3. Implement unit tests
  metadata:
    change_type: feature
    execution_mode: automated
    domain: java
    module: jwt-service
    depends: 1
  profiles:
    - testing
  affected_files:
    - src/test/java/de/cuioss/jwt/JwtValidationServiceTest.java
```

If deliverable not found, returns error with available numbers:
```toon
status: error
error: deliverable_not_found
plan_id: my-feature
number: 999
available:
  - 1
  - 2
  - 3
```

### exists

**Output** (TOON):
```toon
status: success
plan_id: my-feature
file: solution_outline.md
exists: true
```

Returns exit code 0 if exists, 1 if not.
