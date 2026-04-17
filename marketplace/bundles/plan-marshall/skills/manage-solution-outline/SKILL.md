---
name: manage-solution-outline
description: Manage solution outline documents - standards, examples, validation, and deliverable extraction
user-invocable: false
scope: plan
---

# Manage Solution Outline Skill

This skill provides structure guidelines, examples, and operations for `solution_outline.md` documents. Load this skill when creating or modifying solution outlines.

## Enforcement

> **Base contract**: See [manage-contract.md](../ref-workflow-architecture/standards/manage-contract.md) for shared enforcement rules, TOON output format, and error response patterns.

**Skill-specific constraints:**
- Use Write tool for document content, then validate via script (not the script API write path)
- Do not skip validation after writing or updating solution content
- Document creation follows the resolve-path, Write, validate pattern
- Deliverable numbering must be sequential starting from 1

## Document Structure

Required sections: **Summary** (2-3 sentences), **Overview** (ASCII diagram), **Deliverables** (numbered `###` sections). Optional: Approach, Dependencies, Risks and Mitigations.

See [standards/solution-outline-standard.md](standards/solution-outline-standard.md) for the complete section specification, content guidelines, and validation rules.

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

See [standards/solution-outline-standard.md](standards/solution-outline-standard.md) for reference format.

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

See [standards/solution-outline-standard.md](standards/solution-outline-standard.md) for patterns and examples.

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

## Authoring Workflow

See [standards/authoring-guide.md](standards/authoring-guide.md) for the step-by-step workflow for writing a solution document (load architecture, analyze request, design, create diagram, write and validate).

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

> See [manage-contract.md](../ref-workflow-architecture/standards/manage-contract.md) for the standard error response format.

| Error Code | Cause |
|------------|-------|
| `file_not_found` | solution_outline.md doesn't exist |
| `document_not_found` | Same as file_not_found (used by `update` command) |
| `parse_error` | Failed to parse document structure |
| `validation_failed` | Missing required sections (Summary, Overview, or Deliverables), or deliverable numbering not sequential |
| `deliverable_not_found` | Requested deliverable number doesn't exist (read with `--deliverable-number`) |
| `section_not_found` | Requested section doesn't exist (read with `--section`) |

See also [standards/solution-outline-standard.md](standards/solution-outline-standard.md) for deliverable validation criteria used during task planning.

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
| `read` | `--plan-id [--raw] [--deliverable-number N \| --section NAME]` | Read solution, specific deliverable, or a single top-level section |
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

With `--section NAME`: Returns a single top-level `## Section` body. The name is case-insensitive; spaces are normalized to underscores (so `--section "Risks and Mitigations"` matches `## Risks and Mitigations`). Mutually exclusive with `--deliverable-number`. Compatible with `--raw` — when combined, prints just the section body to stdout.

**Example**: Read the Summary section:
```bash
python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage-solution-outline read \
  --plan-id {plan_id} \
  --section summary
```

**Output** (TOON):
```toon
status: success
plan_id: my-feature
file: solution_outline.md
section: summary
requested_section: summary
content: Implement JWT validation service for the authentication module...
```

If the section does not exist, returns:
```toon
status: error
error: section_not_found
plan_id: my-feature
requested_section: nonexistent
message: "Section 'nonexistent' not found in solution_outline.md"
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

---

## Related

- `manage-tasks` — Consumes deliverables from solution outline for task creation
- `manage-architecture` — Provides module placement data used during outline creation
- `manage-references` — Tracks affected_files identified during outline phase
- `manage-plan-documents` — Stores the request document that drives the outline
