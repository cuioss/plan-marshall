---
name: manage-plan-documents
description: Manage request documents within plan directories with schema validation and template-based creation
user-invocable: false
scope: plan
---

# Manage Plan Documents Skill

Domain-specific document management for request documents. Provides logical document names, schema validation, and structured read/update operations.

## Enforcement

> **Base contract**: See [manage-contract.md](../ref-workflow-architecture/standards/manage-contract.md) for shared enforcement rules, TOON output format, and error response patterns.

**Skill-specific constraints:**
- Document operations follow the noun-verb pattern (`request {verb}`)
- For solution outlines, use `plan-marshall:manage-solution-outline` instead

## Document Types

| Type | File | Purpose |
|------|------|---------|
| `request` | `request.md` | Original user input (source of truth) |

---

## API: Noun-Verb Pattern

```
manage-plan-documents {document-type} {verb} [options]
```

### Verbs

| Verb | Description |
|------|-------------|
| `create` | Create document from template |
| `read` | Read document (parsed or raw) |
| `update` | Update specific section |
| `exists` | Check if document exists |
| `remove` | Delete document |

---

## Operations

Script: `plan-marshall:manage-plan-documents:manage-plan-documents`

### request create

Create a request document.

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents \
  request create \
  --plan-id {plan_id} \
  --title "Feature Title" \
  --source description \
  --body "Full task description..."
```

**Parameters:**

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--plan-id` | Yes | Plan identifier |
| `--title` | Yes | Document title |
| `--source` | Yes | Source type: `description`, `lesson`, or `issue` |
| `--body` | Yes | Main content |
| `--source-id` | No | Source identifier (lesson ID, issue URL) |
| `--context` | No | Additional context |
| `--force` | No | Overwrite if exists |

**Output:**

```toon
status: success
plan_id: my-feature
document: request
file: request.md
action: created

document_info:
  title: Feature Title
  sections: title,source,source_id,body,context
```

### read

Read a document with parsed sections.

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents \
  request read \
  --plan-id {plan_id}
```

**Output:**

```toon
status: success
plan_id: my-feature
document: request
file: request.md

content:
  _header: # Request: Feature Title...
  original_input: Full task description...
  context: Additional context...
```

**Options:**
- `--raw`: Output raw markdown content
- `--section {section_name}`: Read specific section only (e.g., `clarified_request`)

**Fallback behavior**: When `--section clarified_request` is used but the section doesn't exist, automatically falls back to `original_input`. The response includes both `section` (what was actually returned) and `requested_section` (what was requested). This simplifies callers who want the clarified request if available, otherwise the original input. Other sections do NOT have fallback behavior — requesting a non-existent section returns `status: error, error: section_not_found`.

**Read specific section:**

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents \
  request read \
  --plan-id {plan_id} \
  --section clarified_request
```

**Output:**

```toon
status: success
plan_id: my-feature
document: request
section: original_input          # actual section returned
requested_section: clarified_request  # what was requested
content: Migrate JSON output specifications to TOON format...
```

### update

Update a specific section.

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents \
  request update \
  --plan-id {plan_id} \
  --section context \
  --content "Updated context information..."
```

**Parameters**:
- `--plan-id` (required): Plan identifier
- `--section` (required): Section name to update (e.g., `context`, `original_input`)
- `--content` (required): New content for the section

**Output:**

```toon
status: success
plan_id: my-feature
document: request
section: context
updated: true
```

### clarify

Add clarifications and clarified request sections to a document. Used in the uncertainty resolution flow.

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents \
  request clarify \
  --plan-id {plan_id} \
  --clarifications "**Q: Should JSON in workflow context be included?**
Examples: manage-adr/SKILL.md, workflow-integration-ci/SKILL.md
A: Exclude workflow JSON - Only include explicit ## Output sections" \
  --clarified-request "Migrate JSON output specifications to TOON format in all marketplace bundles.

**Scope:**
- Components with explicit ## Output sections
- All bundles

**Exclusions:**
- JSON in workflow documentation"
```

**Parameters:**

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--plan-id` | Yes | Plan identifier |
| `--clarifications` | No | Q&A clarifications content |
| `--clarified-request` | No | Synthesized clarified request |

At least one of `--clarifications` or `--clarified-request` must be provided. If neither is given, returns `status: error, error: missing_argument`.

**Idempotency**: Calling `clarify` multiple times appends to the Clarifications section and replaces the Clarified Request section. This supports iterative refinement during phase-2-refine.

**Output:**

```toon
status: success
plan_id: my-feature
document: request
sections_added:
  - Clarifications
  - Clarified Request
```

**Resulting request.md structure:**

```markdown
# Request: Migrate JSON to TOON

## Original Input

Migrate agent/command/skill outputs from JSON to TOON format

## Context

...

## Clarifications

**Q: Should files with JSON in workflow context be included?**
Examples: manage-adr/SKILL.md, workflow-integration-ci/SKILL.md
A: Exclude workflow JSON - Only include explicit ## Output sections

## Clarified Request

Migrate JSON output specifications to TOON format in all marketplace bundles.

**Scope:**
- Components with explicit `## Output` sections
- All bundles

**Exclusions (based on clarifications):**
- JSON in workflow documentation
```

### exists

Check if document exists.

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents \
  request exists \
  --plan-id {plan_id}
```

**Output:**

```toon
status: success
plan_id: my-feature
document: request
file: request.md
exists: true
```

Returns exit code 0 if exists, 1 if not.

### remove

Remove a document.

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents \
  request remove \
  --plan-id {plan_id}
```

**Output:**

```toon
status: success
plan_id: my-feature
document: request
file: request.md
action: removed
```

### list-types

List available document types.

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents \
  list-types
```

**Output:**

```toon
status: success
types:
  - name: request
    file: request.md
    fields: 5
```

---

## Error Responses

> See [manage-contract.md](../ref-workflow-architecture/standards/manage-contract.md) for the standard error response format.

| Error Code | Cause |
|------------|-------|
| `document_not_found` | Document doesn't exist (read, update, clarify, remove) |
| `invalid_plan_id` | plan_id format invalid |
| `file_exists` | Document already exists on create (use `--force`) |
| `section_not_found` | Requested section doesn't exist (except `clarified_request` which falls back) |
| `missing_argument` | Required parameter missing (clarify without either flag) |
| `validation_error` | Field validation failed on create |

---

## Integration

### Producers

| Client | Operation | Purpose |
|--------|-----------|---------|
| `phase-1-init` | request create | Create initial request document |
| `phase-2-refine` | request clarify, request update | Add clarifications and update sections |

### Consumers

| Client | Operation | Purpose |
|--------|-----------|---------|
| `phase-3-outline` | request read | Read request to design solution |
| `phase-4-plan` | request read | Read request for task planning context |

## Related Skills

- `manage-solution-outline` — Solution outline management (validate, read, list-deliverables)
- `manage-files` — Generic file operations for non-typed plan documents
