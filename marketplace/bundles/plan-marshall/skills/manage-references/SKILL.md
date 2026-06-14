---
name: manage-references
description: Manage references.json files with field-level access and list management
user-invocable: false
mode: script-executor
scope: plan
---

# Manage References Skill

Manage references.json files with field-level access and list management. Tracks files, branches, and external references for a plan.

## Enforcement

> **Base contract**: See [manage-contract.md](../ref-workflow-architecture/standards/manage-contract.md) for shared enforcement rules, TOON output format, and error response patterns.

**Skill-specific constraints:**
- Do not mix `add-list` and `set-list` without understanding their semantics (append vs replace)
- References are plan-scoped; always provide `--plan-id`
- File paths in affected_files are always relative to repository root

## Storage Location

References are stored in the plan directory:

```
.plan/plans/{plan_id}/references.json
```

---

## File Format

JSON format for storage:

```json
{
  "branch": "feature/my-feature",
  "base_branch": "main",
  "issue_url": "https://github.com/org/repo/issues/123",
  "build_system": "maven",
  "domains": ["java"],
  "affected_files": [
    "src/main/java/Foo.java"
  ]
}
```

### Schema Fields

| Field | Type | Description |
|-------|------|-------------|
| `branch` | string | Git branch name |
| `base_branch` | string | Base branch for PR (e.g., main) |
| `issue_url` | string | GitHub issue URL |
| `build_system` | string | Build system (maven, gradle, npm, none) |
| `domains` | list | Plan domains (e.g., java, documentation) |
| `affected_files` | list | Files identified during outline phase as potentially needing changes (scope tracking) |
| `external_docs` | table | External documentation references |

---

## Operations

Script: `plan-marshall:manage-references:manage-references`

### create

Create references.json with basic fields.

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references create \
  --plan-id {plan_id} \
  --branch {branch_name} \
  [--issue-url {url}] \
  [--build-system {maven|gradle|npm}] \
  [--domains {java,documentation}]
```

**Parameters**:
- `--plan-id` (required): Plan identifier (kebab-case)
- `--branch` (required): Git branch name
- `--issue-url`: GitHub issue URL
- `--build-system`: Build system (`maven`, `gradle`, `npm`)
- `--domains`: Comma-separated domain list (e.g., `java,documentation`)

**Output** (TOON):
```toon
status: success
plan_id: my-feature
file: references.json
created: true
fields[2]:
  - branch
  - base_branch
```

**Note**: Basic fields are created during plan-init. Additional reference fields are added as needed during execution.

### read

Read entire references.json content.

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references read \
  --plan-id {plan_id}
```

**Output** (TOON):
```toon
status: success
plan_id: my-feature

references:
  branch: feature/my-feature
  issue_url: https://github.com/org/repo/issues/123
  affected_files: 3 items
```

### get

Get a specific field value.

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references get \
  --plan-id {plan_id} \
  --field branch
```

**Output** (TOON):
```toon
status: success
plan_id: my-feature
field: branch
value: feature/my-feature
```

### set

Set a specific field value.

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references set \
  --plan-id {plan_id} \
  --field branch \
  --value feature/new-branch
```

**Output** (TOON):
```toon
status: success
plan_id: my-feature
field: branch
value: feature/new-branch
previous: feature/my-feature
```

### add-list

Add multiple values to a list field.

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references add-list \
  --plan-id {plan_id} \
  --field affected_files \
  --values "path/to/file1.md,path/to/file2.md,path/to/file3.md"
```

**Parameters**:
- `--plan-id` (required): Plan identifier
- `--field` (required): List field name (e.g., `affected_files`)
- `--values` (required): Comma-separated values to add

**Output** (TOON):
```toon
status: success
plan_id: my-feature
field: affected_files
added_count: 3
total: 3
```

**Notes**:
- Creates the field as an empty list if it doesn't exist
- Skips values that already exist in the list (no duplicates)
- Returns error if the field exists but is not a list

### set-list

Set a list field to new values, replacing any existing content.

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references set-list \
  --plan-id {plan_id} \
  --field affected_files \
  --values "path/to/file1.md,path/to/file2.md"
```

**Parameters**:
- `--plan-id` (required): Plan identifier
- `--field` (required): List field name (e.g., `affected_files`)
- `--values` (required): Comma-separated values

**Output** (TOON):
```toon
status: success
plan_id: my-feature
field: affected_files
previous_count: 5
count: 2
```

**Notes**:
- Replaces the entire list (does not append like `add-list`)
- Empty `--values ""` clears the list
- Returns `previous_count` showing how many items were replaced

**When to use `set-list` vs `add-list`**:
- Use `set-list` when you have the complete, authoritative list (e.g., after re-scanning affected files)
- Use `add-list` when incrementally building a list (e.g., adding files as they are modified during execution)

### get-context

Get the plan's scalar reference fields (branch, base_branch, and any present issue_url / build_system) in one call. More efficient than multiple `get` calls when you need the common scalar context.

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references get-context \
  --plan-id {plan_id}
```

**Parameters**:
- `--plan-id` (required): Plan identifier

**Output** (TOON):
```toon
status: success
plan_id: my-feature
branch: feature/my-feature
base_branch: main
issue_url: https://github.com/org/repo/issues/123
build_system: maven
```

---

### compute-footprint

Derive the plan's actual footprint live from the worktree git state — the single source of truth — without consulting any persisted ledger. **Read-only — never mutates `references.json`.** It reads `references.json` only to resolve `base_branch` for the diff range.

The footprint is the union of the three-dot `{base_ref}...HEAD` diff name set and the porcelain working-tree state (`git status --porcelain`). The derivation primitive is `compute_plan_branch_diff` in `_references_core`. Consumers that need to know which files the plan touched (self-review surfacing, pre-commit freshness, the finalize-step scope cap, retrospective consistency checks) call this verb on demand rather than reading a stored array.

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references compute-footprint \
  --plan-id {plan_id} --worktree-path {worktree_path} \
  [--base-ref {ref}]
```

**Parameters**:
- `--plan-id` (required): Plan identifier
- `--worktree-path` (required): Absolute path to the active git worktree
- `--base-ref`: Base ref for the diff (defaults to `references.base_branch`, falling back to `main`)

**Output** (TOON):
```toon
status: success
plan_id: my-feature
base_ref: main
files[3]:
  - src/main/java/Foo.java
  - src/main/java/Bar.java
  - src/main/java/Baz.java
live_count: 3
```

---

## Scripts

**Script**: `plan-marshall:manage-references:manage-references`

| Command | Parameters | Description |
|---------|------------|-------------|
| `create` | `--plan-id --branch [--issue-url] [--build-system] [--domains]` | Create references.json |
| `read` | `--plan-id` | Read entire references |
| `get` | `--plan-id --field` | Get specific field value |
| `set` | `--plan-id --field --value` | Set specific field value |
| `add-list` | `--plan-id --field --values` | Add multiple values to a list field |
| `set-list` | `--plan-id --field --values` | Set a list field (replaces existing) |
| `get-context` | `--plan-id` | Get the plan's scalar reference context |
| `compute-footprint` | `--plan-id --worktree-path [--base-ref]` | Derive the live plan footprint from the worktree git state (read-only) |

---

## Canonical invocations

The canonical argparse surface for `manage-references.py`. The D4 plugin-doctor
analyzer (`_analyze_manage_invocation.py`) reads this section as source-of-truth for
markdown notation occurrences across the marketplace. Consuming skills xref this
section by name (e.g., "see `manage-references` Canonical invocations → `add-list`")
instead of restating the command inline.

### create

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references create \
  --plan-id PLAN_ID --branch BRANCH \
  [--issue-url URL] [--build-system {maven|gradle|npm}] [--domains LIST]
```

### read

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references read \
  --plan-id PLAN_ID
```

### get

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references get \
  --plan-id PLAN_ID --field FIELD
```

### set

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references set \
  --plan-id PLAN_ID --field FIELD --value VALUE
```

### add-list

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references add-list \
  --plan-id PLAN_ID --field FIELD --values CSV
```

### set-list

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references set-list \
  --plan-id PLAN_ID --field FIELD --values CSV
```

### get-context

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references get-context \
  --plan-id PLAN_ID
```

### compute-footprint

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references compute-footprint \
  --plan-id PLAN_ID --worktree-path ABS_PATH [--base-ref REF]
```

---

## Error Responses

> See [manage-contract.md](../ref-workflow-architecture/standards/manage-contract.md) for the standard error response format.

| Error Code | Cause |
|------------|-------|
| `file_not_found` | references.json doesn't exist |
| `invalid_plan_id` | plan_id format invalid |
| `field_not_found` | Requested field doesn't exist (get) |
| `type_mismatch` | Attempting list operation on non-list field (add-list on a string field) |
| `file_exists` | references.json already exists on create |
| `field_not_set` | Field exists but has no value (returns `value: null`, exit 0) |
| `worktree_not_found` | `--worktree-path` does not exist or is not a directory (compute-footprint) |
| `references_not_found` | references.json not found (compute-footprint) |
| `not_a_git_worktree` | `--worktree-path` is not inside a git worktree (compute-footprint) |

**Default values**: Unset fields return `field_not_found` on `get`. The `create` command initializes `branch` and `base_branch` (the latter to `main`). All other fields are optional — only present if explicitly set via `--field` / `set-list` arguments.

---

## Integration

### Producers

| Client | Operation | Purpose |
|--------|-----------|---------|
| `phase-1-init` | create, set, set-list | Initialize references with branch, domains, build system |
| `phase-3-outline` | set-list | Set affected_files from solution outline |

### Consumers

| Client | Operation | Purpose |
|--------|-----------|---------|
| `phase-3-outline` | get, get-context | Read domains and build system for skill routing |
| `phase-5-execute` | get-context | Read build system for task execution |
| `phase-6-finalize` | compute-footprint | Derive the live plan footprint for commit scope and PR body |

## Related

- `manage-files` — Generic file operations for plan directories
- `manage-plan-documents` — Typed plan document operations (request.md)
