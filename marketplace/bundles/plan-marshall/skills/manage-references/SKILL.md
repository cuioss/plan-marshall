---
name: manage-references
description: Manage references.json files with field-level access and list management, plus the two plan-footprint surfaces — the realized footprint derived and captured from the worktree git state, and the declared footprint re-derived from the solution outline's structured deliverable data by set union
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
- `affected_files` is written by `sync-affected-files`, which derives it from the outline. Do not hand-compose it through `set-list` / `add-list`: a CSV composed by reading outline prose can only be as complete as that reading, and nothing downstream can audit a reading

## Storage Location

References are stored in the plan directory:

```text
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
| `affected_files` | list | The plan's DECLARED footprint — the paths the solution outline says the plan expects to touch. Derived by `sync-affected-files` from the outline's structured per-deliverable declarations (all three declaration headings, so a survey-scope deliverable's `Files expected to mutate:` paths are included), never composed by reading outline prose. Re-derived by set union at every point a later consumer depends on it being current, so it is not frozen at outline time. Contrast `realized_footprint`, which records what the worktree actually touched. |
| `external_docs` | table | External documentation references |
| `realized_footprint` | list | The realized plan footprint, captured from the worktree by `capture-footprint` (called by `default:branch-cleanup` before worktree removal). The footprint resolver prefers it over any re-derivation. |
| `merge_commit_sha` | string | The landing commit SHA, recorded by `default:branch-cleanup` on the synchronous merge path. Feeds the footprint resolver's merge-commit fallback tier. Absent on the async merge-queue path. |
| `pr_number` | string | The plan's PR/MR number, recorded by `default:create-pr` immediately after the PR is created or an open one is reused. Feeds the footprint resolver's PR-landing tier, which resolves the landing commit through `ci pr view --pr-number N` when `merge_commit_sha` was never written. Present from PR creation onward; absent on a plan that never opened a PR. |

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

### capture-footprint

Compute the live footprint (identical to `compute-footprint`) AND **persist it** into `references.json` under `realized_footprint`. This is the capture-while-true side effect `default:branch-cleanup` performs before it removes the plan's worktree, so a post-merge retrospective or audit resolves the exact realized set from a recorded fact instead of re-deriving it from a substrate that has since changed.

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references capture-footprint \
  --plan-id {plan_id} --worktree-path {worktree_path} \
  [--base-ref {ref}]
```

**Parameters**: same as `compute-footprint` — `--plan-id` and `--worktree-path` required, `--base-ref` optional.

**Output** (TOON): the computed `files` plus `realized_footprint_count` and `persisted: true`. On a compute failure the error is propagated verbatim and nothing is written — the resolver falls through to its lower tiers rather than reading a fabricated empty capture.

---

### sync-affected-files

Re-derive the plan's **declared** footprint from `solution_outline.md` and union it into `references.affected_files`. Where `compute-footprint` / `capture-footprint` answer "what did the worktree touch", this verb answers "what did the outline say the plan expects to touch".

The derivation is structural, not narrative: every path comes from `_plan_parsing.declared_paths_by_intent`, which walks all three declaration headings — `Affected files`, `Files expected to mutate`, `Files to survey` — across every deliverable. A **survey-scope deliverable** declares the latter pair INSTEAD of a flat `Affected files` list, so its expected-to-mutate paths reach the key through this verb and through no other route.

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references sync-affected-files \
  --plan-id {plan_id}
```

**Parameters**:
- `--plan-id` (required): Plan identifier

There is no `--values` argument by design. The outline is the input, so no caller composes a CSV — and therefore no caller can compose one incompletely.

**Output** (TOON):
```toon
status: success
plan_id: my-feature
field: affected_files
added_count: 2
unchanged_count: 7
total: 9
declared_count: 9
added[2]:
  - marketplace/bundles/plan-marshall/skills/manage-references/SKILL.md
  - test/plan-marshall/manage-references/test_manage_references.py
deliverables_scanned: 5
headings_found: 6
bullets_parsed: 31
```

**Notes**:
- The write is a **set union** over the existing value. A path recorded by an earlier run always survives a later one, a path that appeared after the outline was first read is added, and a repeat run over an unchanged outline changes nothing — which is what makes the verb safe to call at every point a consumer depends on the value being current.
- Ordering is stable: already-recorded paths keep their position, newly derived ones are appended in sorted order.
- `deliverables_scanned` / `headings_found` / `bullets_parsed` publish the population the derivation walked, so a small result states what it was derived FROM rather than only what it derived.
- It **refuses rather than reporting a clean zero** when nothing could be derived: a missing or unreadable outline, and an outline whose Deliverables section yielded no deliverable blocks, are `status: error` and write nothing.

**Call sites**: `q-gate-validation` § Step 7 (first write), `phase-4-plan` § Step 7b (before the manifest reads `affected_files_count`), and `phase-6-finalize` (loop-back re-entry refresh). The two later sites exist because a faithful read of a stale value cannot detect its own staleness — re-reading the key returns exactly what was written, so only a re-derivation can tell a current value from a stale one.

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
| `sync-affected-files` | `--plan-id` | Re-derive `references.affected_files` from the outline's structured deliverable data (set union) |
| `get-context` | `--plan-id` | Get the plan's scalar reference context |
| `compute-footprint` | `--plan-id --worktree-path [--base-ref]` | Derive the live plan footprint from the worktree git state (read-only) |
| `capture-footprint` | `--plan-id --worktree-path [--base-ref]` | Compute the live footprint AND persist it to `references.realized_footprint` |

---

## Canonical invocations

The canonical argparse surface for `manage-references.py`. The plugin-doctor `missing-canonical-block` rule checks that this section is PRESENT,
matching its heading only — the body is never read; `manage-invocation-invalid` derives
its accept-set from a live `--help` walk rather than from this section. Consuming skills xref this
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

### sync-affected-files

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references sync-affected-files \
  --plan-id PLAN_ID
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

### capture-footprint

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references capture-footprint \
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
| `outline_not_found` | `solution_outline.md` does not exist — there is nothing to derive the declared footprint from (sync-affected-files) |
| `outline_unreadable` | `solution_outline.md` exists but could not be read (sync-affected-files) |
| `no_deliverables_parsed` | The outline yielded no deliverable blocks, so nothing was derived and nothing was written. Reported as an error rather than an empty derivation, because an unread outline and a plan that declares nothing are not the same state (sync-affected-files) |
| `not_a_list` | `references.affected_files` exists but is not a list (sync-affected-files) |

**Default values**: Unset fields return `field_not_found` on `get`. The `create` command initializes `branch` and `base_branch` (the latter to `main`). All other fields are optional — only present if explicitly set via `--field` / `set-list` arguments.

---

## Integration

### Producers

| Client | Operation | Purpose |
|--------|-----------|---------|
| `phase-1-init` | create, set, set-list | Initialize references with branch, domains, build system |
| `q-gate-validation` (§ Step 7) | sync-affected-files | First derivation of `affected_files` from the outline's structured deliverable data |
| `phase-4-plan` (§ Step 7b) | sync-affected-files | Refresh before the manifest is composed from `affected_files_count`, so scope added between outline and plan reaches the manifest |
| `phase-6-finalize` | sync-affected-files | Refresh on the loop-back re-entry path, so scope added after phase-3 reaches the finalize-time consumers |
| `phase-6-finalize` (`create-pr`) | set | Record `pr_number` immediately after the PR is created or an open one is reused |

### Consumers

| Client | Operation | Purpose |
|--------|-----------|---------|
| `phase-3-outline` | get, get-context | Read domains and build system for skill routing |
| `phase-5-execute` | get-context | Read build system for task execution |
| `manage-execution-manifest` (via `phase-4-plan` § Step 7b) | get | Read `affected_files` as the declared surface the compose-time classification is decided from |
| `phase-6-finalize` | compute-footprint | Derive the live plan footprint for commit scope and PR body |
| `phase-6-finalize` (`branch-cleanup`) | capture-footprint, set | Persist `realized_footprint` before worktree removal, and record `merge_commit_sha` after the base pull |
| `plan-retrospective`, `audit-archived-plan-retrospectives` | (reads `realized_footprint` / `merge_commit_sha` / `pr_number` via the shared footprint resolver) | Resolve the realized footprint for recall and mis-prune checks post-merge. `pr_number` backs the PR-landing tier, which is the only tier that resolves a squash / merge-queue landing — the path on which `realized_footprint` and `merge_commit_sha` are both unwritten |

## Related

- `manage-files` — Generic file operations for plan directories
- `manage-plan-documents` — Typed plan document operations (request.md)
