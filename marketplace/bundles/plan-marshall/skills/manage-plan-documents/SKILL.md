---
name: manage-plan-documents
description: Manage request documents within plan directories with schema validation and template-based creation
user-invocable: false
mode: script-executor
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

> **No top-level `read` verb.** Every verb below is scoped under a document type
> (`request`) — there is NO standalone `manage-plan-documents read`. To read a
> request document you MUST invoke `manage-plan-documents request read --plan-id ...`.
> Calling `manage-plan-documents read ...` (omitting the `request` document-type
> positional) is an `argparse_rejection` (exit 2): the parser has no top-level
> `read` subcommand. The only top-level subcommand is `list-types`; all CRUD verbs
> (`create`, `read`, `path`, `exists`, `remove`, `mark-clarified`) live under the
> document type. The same rule applies to every verb in the table below — none of
> them exists at the top level.

### Verbs

All verbs below are **document-type-scoped** — invoke them as `manage-plan-documents {document-type} {verb}` (e.g. `request read`), never as a bare top-level subcommand.

| Verb | Description |
|------|-------------|
| `create` | Create document from template |
| `read` | Read document (parsed or raw) — invoked as `request read`, NOT top-level `read` |
| `path` | Return canonical artifact path for direct edit (Step 1 of edit flow) |
| `mark-clarified` | Record clarification transition after direct edit (Step 3 of edit flow) |
| `exists` | Check if document exists |
| `remove` | Delete document |

---

## Editing Flow — Three-Step Path-Allocate Pattern

Edits to existing request documents follow a unified three-step pattern. The script
owns path allocation; the main context writes the file directly with its native
Read/Edit/Write tools; a status-transition subcommand records the outcome. No
multi-line content is ever marshalled through the shell boundary.

```bash
# Step 1: script allocates the canonical artifact path
python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents \
  request path --plan-id {plan_id}
# → returns {status, path, sections}

# Step 2: main context edits the returned path directly with Read/Edit/Write.
# (No shell marshalling, no escaped content. The Edit tool does the work.)

# Step 3: script validates and records the transition
python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents \
  request mark-clarified --plan-id {plan_id}
# → succeeds when the edited file contains a Clarified Request section
```

---

## Operations

Script: `plan-marshall:manage-plan-documents:manage-plan-documents`

### request create

Create a request document. Uses the path-allocate pattern: the script allocates
the canonical artifact path and emits a metadata-only stub. The caller writes
the body content directly with its native `Write` tool using the returned
`path`. No body content ever crosses the shell boundary.

```bash
# Metadata-only: allocates the file and returns its absolute path.
python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents \
  request create \
  --plan-id {plan_id} \
  --title "Feature Title" \
  --source description
# → returns {status, plan_id, document, file, action, path, ...}
# Caller then: Write({path}, "Full task description...")
```

For the narrow case of already-persisted body content, the `--body-file`
shortcut reads a UTF-8 file and inlines its contents during stub rendering:

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents \
  request create \
  --plan-id {plan_id} \
  --title "Feature Title" \
  --source lesson \
  --source-id lesson-2026-04-17-008 \
  --body-file /abs/path/to/body.md
```

**Parameters:**

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--plan-id` | Yes | Plan identifier |
| `--title` | Yes | Document title |
| `--source` | Yes | Source type: `description`, `lesson`, `issue`, or `recipe` |
| `--source-id` | No | Source identifier (lesson ID, issue URL, recipe key) |
| `--body-file` | No | Absolute path to a UTF-8 file whose contents fill the `## Original Input` section. When omitted, the template placeholder paragraph is emitted and the caller writes the body via `Write({path})`. |
| `--force` | No | Overwrite if exists |

**Output:**

```toon
status: success
plan_id: my-feature
document: request
file: request.md
action: created
path: /abs/path/.plan/local/plans/my-feature/request.md

document_info:
  title: Feature Title
  sections: title,metadata,original_input,clarifications,clarified_request
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

### path

Return the canonical artifact path so the main context can edit the file directly.
This is Step 1 of the edit flow — the script owns path allocation; the caller
never invents a path.

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents \
  request path \
  --plan-id {plan_id}
```

**Parameters:**
- `--plan-id` (required): Plan identifier

**Output:**

```toon
status: success
plan_id: my-feature
document: request
file: request.md
path: /abs/path/.plan/local/plans/my-feature/request.md
sections[2]:
  - original_input
  - context
```

After receiving the path, the main context uses its native Read/Edit/Write tools
to modify the file. No content ever crosses the shell boundary.

### mark-clarified

Step 3 of the edit flow for adding clarifications. The caller has already edited
the request document directly; this subcommand validates that a `## Clarified
Request` section is present and records the transition.

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents \
  request mark-clarified \
  --plan-id {plan_id}
```

**Parameters:**
- `--plan-id` (required): Plan identifier

**Output:**

```toon
status: success
plan_id: my-feature
document: request
file: request.md
clarified: true
has_clarifications_section: true
```

If the file is missing a Clarified Request section, returns
`status: error, error: not_clarified` — a signal to the caller that Step 2
(direct edit) has not been performed or did not add the required section.

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

## Canonical invocations

The canonical argparse surface for `manage-plan-documents.py`. The D4 plugin-doctor
analyzer (`_analyze_manage_invocation.py`) reads this section as source-of-truth for
markdown notation occurrences across the marketplace. Consuming skills xref this
section by name (e.g., "see `manage-plan-documents` Canonical invocations →
`request create`") instead of restating the command inline.

The script registers a sub-parser per document type discovered from `documents/*.toon`.
The current registered document type is `request`. Each document type exposes six verbs:
`create`, `read`, `path`, `exists`, `remove`, `mark-clarified`.

### list-types

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents list-types
```

### request create

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents request create \
  --plan-id PLAN_ID --title TEXT --source {description|lesson|issue|recipe} \
  [--source-id ID] [--body-file PATH] [--force]
```

`--title` and `--source` are required. `--source-id` and `--body-file` are optional;
omitting `--body-file` returns a metadata-only stub whose returned `path` is filled
in via the Write tool.

### request read

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents request read \
  --plan-id PLAN_ID [--raw] [--section SECTION]
```

### request path

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents request path \
  --plan-id PLAN_ID
```

### request exists

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents request exists \
  --plan-id PLAN_ID
```

### request remove

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents request remove \
  --plan-id PLAN_ID
```

### request mark-clarified

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents request mark-clarified \
  --plan-id PLAN_ID
```

---

## Error Responses

> See [manage-contract.md](../ref-workflow-architecture/standards/manage-contract.md) for the standard error response format.

| Error Code | Cause |
|------------|-------|
| `document_not_found` | Document doesn't exist (read, path, mark-clarified, remove) |
| `invalid_plan_id` | plan_id format invalid |
| `file_exists` | Document already exists on create (use `--force`) |
| `section_not_found` | Requested section doesn't exist (except `clarified_request` which falls back) |
| `not_clarified` | `mark-clarified` called but document has no Clarified Request section |
| `body_file_not_found` | `--body-file` path does not exist or is not a regular file |
| `validation_error` | Field validation failed on create |

---

## Integration

### Producers

| Client | Operation | Purpose |
|--------|-----------|---------|
| `phase-1-init` | request create | Create initial request document |
| `phase-2-refine` | request path, request mark-clarified | Allocate path, direct-edit file, record clarification transition |

### Consumers

| Client | Operation | Purpose |
|--------|-----------|---------|
| `phase-3-outline` | request read | Read request to design solution |
| `phase-4-plan` | request read | Read request for task planning context |

## Related

- `manage-solution-outline` — Solution outline management (validate, read, list-deliverables)
- `manage-files` — Generic file operations for non-typed plan documents
