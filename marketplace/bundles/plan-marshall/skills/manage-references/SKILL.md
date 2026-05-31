---
name: manage-references
description: Manage references.json files with field-level access and list management
user-invocable: false
scope: plan
---

# Manage References Skill

Manage references.json files with field-level access and list management. Tracks files, branches, and external references for a plan.

## Enforcement

> **Base contract**: See [manage-contract.md](../ref-workflow-architecture/standards/manage-contract.md) for shared enforcement rules, TOON output format, and error response patterns.

**Skill-specific constraints:**
- Do not mix `add-list` and `set-list` without understanding their semantics (append vs replace)
- References are plan-scoped; always provide `--plan-id`
- File paths in modified_files and affected_files are always relative to repository root

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
  "modified_files": [
    "src/main/java/Foo.java",
    "src/main/java/Bar.java",
    "src/test/java/FooTest.java"
  ],
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
| `modified_files` | list | Files modified during implementation (collected via git diff on 5-execute completion) |
| `domains` | list | Plan domains (e.g., java, documentation) |
| `affected_files` | list | Files identified during outline phase as potentially needing changes (scope tracking, may be superset of modified_files) |
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
fields[3]:
  - branch
  - base_branch
  - modified_files
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
  modified_files: 3 items
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

### add-file

Add a file to modified_files list.

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references add-file \
  --plan-id {plan_id} \
  --file src/main/java/NewClass.java
```

**Output** (TOON):
```toon
status: success
plan_id: my-feature
section: modified_files
added: src/main/java/NewClass.java
total: 4
```

### remove-file

Remove a file from modified_files list.

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references remove-file \
  --plan-id {plan_id} \
  --file src/main/java/OldClass.java
```

**Output** (TOON):
```toon
status: success
plan_id: my-feature
section: modified_files
removed: src/main/java/OldClass.java
total: 2
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
- `--field` (required): List field name (e.g., `affected_files`, `modified_files`)
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
- `--field` (required): List field name (e.g., `affected_files`, `modified_files`)
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

Get all references in one call, with scalar fields at top level and list fields as counts (or full lists with `--include-files`). More efficient than multiple `get` calls when you need the full picture.

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references get-context \
  --plan-id {plan_id} \
  [--include-files]
```

**Parameters**:
- `--plan-id` (required): Plan identifier
- `--include-files`: Include full file lists in output (default: only counts)

**Output** (TOON):
```toon
status: success
plan_id: my-feature
branch: feature/my-feature
base_branch: main
modified_files_count: 3
issue_url: https://github.com/org/repo/issues/123
build_system: maven
```

With `--include-files`:
```toon
status: success
plan_id: my-feature
branch: feature/my-feature
base_branch: main
modified_files_count: 3
modified_files[3]:
  - src/main/java/Foo.java
  - src/main/java/Bar.java
  - src/main/java/Baz.java
```

---

### diff-files

Intersect the append-only `modified_files` ledger with the live git working-tree state, so consumers operate on "actually-modified-now" paths instead of trusting a potentially stale ledger. **Read-only — never mutates `references.json`.** Its write-back counterpart is `reconcile-files`.

The "live" set is the union of the three-dot `{base_ref}...HEAD` diff name set and the porcelain working-tree state (`git status --porcelain --untracked-files=all`). Both verbs share this primitive (`compute_plan_branch_diff` in `_references_core`).

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references diff-files \
  --plan-id {plan_id} --worktree-path {worktree_path} \
  [--base-ref {ref}]
```

**Parameters**:
- `--plan-id` (required): Plan identifier
- `--worktree-path` (required): Absolute path to the active git worktree
- `--base-ref`: Base ref for the diff (defaults to `references.base_branch`, falling back to `main`)

### reconcile-files

Recompute `references.modified_files` from the plan-branch-only diff and **PERSIST** the reconciled set. This is the write-back counterpart of the read-only `diff-files` verb: both share the same three-dot + porcelain-union primitive, but `reconcile-files` writes the intersected set back to `references.json`.

The reconciliation drops ledger entries that are absent from the live plan-branch-only set — these are the absorbed-upstream files that pollute the ledger after an absorb merge (phase-5-execute self-absorb or `workflow-integration-git` baseline-reconcile focused auto-merge). After this verb runs, downstream finalize consumers (plugin-doctor, regenerate-executor, PR-body, pre-submission-self-review) read a clean footprint that contains only files the plan actually touched.

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references reconcile-files \
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
before_count: 5
after_count: 3
removed[2]:
  - upstream/only/file_a.py
  - upstream/only/file_b.py
modified_files[3]:
  - src/main/java/Foo.java
  - src/main/java/Bar.java
  - src/main/java/Baz.java
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
| `add-file` | `--plan-id --file` | Add file to modified_files |
| `remove-file` | `--plan-id --file` | Remove file from modified_files |
| `add-list` | `--plan-id --field --values` | Add multiple values to a list field |
| `set-list` | `--plan-id --field --values` | Set a list field (replaces existing) |
| `get-context` | `--plan-id [--include-files]` | Get all references context |
| `diff-files` | `--plan-id --worktree-path [--base-ref]` | Intersect modified_files ledger with live git diff (read-only) |
| `reconcile-files` | `--plan-id --worktree-path [--base-ref]` | Recompute and persist modified_files from the plan-branch-only diff (write-back) |

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

### add-file

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references add-file \
  --plan-id PLAN_ID --file PATH
```

### remove-file

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references remove-file \
  --plan-id PLAN_ID --file PATH
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
  --plan-id PLAN_ID [--include-files]
```

### diff-files

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references diff-files \
  --plan-id PLAN_ID --worktree-path ABS_PATH [--base-ref REF]
```

### reconcile-files

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references reconcile-files \
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
| `worktree_not_found` | `--worktree-path` does not exist or is not a directory (diff-files, reconcile-files) |
| `references_not_found` | references.json not found (diff-files, reconcile-files) |
| `not_a_git_worktree` | `--worktree-path` is not inside a git worktree (diff-files, reconcile-files) |

**Default values**: Unset fields return `field_not_found` on `get`. The `create` command initializes `modified_files` and `affected_files` as empty lists and `base_branch` as `main`. All other fields are optional — only present if explicitly set via `--field` arguments.

---

## Integration

### Producers

| Client | Operation | Purpose |
|--------|-----------|---------|
| `phase-1-init` | create, set, set-list | Initialize references with branch, domains, build system |
| `phase-3-outline` | set-list | Set affected_files from solution outline |
| `manage-status/cmd_transition` | set-list (modified_files) | Collect modified files via git diff on 5-execute completion |

### Consumers

| Client | Operation | Purpose |
|--------|-----------|---------|
| `phase-3-outline` | get, get-context | Read domains and build system for skill routing |
| `phase-5-execute` | get-context | Read build system for task execution |
| `phase-6-finalize` | get-context --include-files | Read modified_files for commit scope and PR body |

## Related

- `manage-files` — Generic file operations for plan directories
- `manage-plan-documents` — Typed plan document operations (request.md)
