---
name: manage-references
description: Manage references.json files with field-level access and list management, plus the two plan-footprint surfaces — the realized footprint derived and captured from the worktree git state, and the declared footprint re-derived from the solution outline's structured deliverable data by set union and partitioned by declared intent, so an expected modification and a read-only reference are recorded as separate, disjoint keys — and the read-only three-way reconciliation that compares the recorded declaration, the structured derivation and the realized footprint pairwise by symmetric difference in both directions, so two equal-sized but disjoint sets are reported as fully disagreeing rather than as identical
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
- `affected_files` and `read_intent_files` are written together by `sync-affected-files`, which derives both from the outline. Do not hand-compose either through `set-list` / `add-list`: a CSV composed by reading outline prose can only be as complete as that reading, nothing downstream can audit a reading, and a hand-composed value cannot honour the intent partition that keeps the two keys disjoint

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
  ],
  "read_intent_files": [
    "src/main/java/FooContract.java"
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
| `affected_files` | list | The MUTATION half of the plan's declared footprint — the paths the solution outline says the plan expects to **modify**, and only those. Derived by `sync-affected-files` from the outline's structured per-deliverable declarations (all three declaration headings, so a survey-scope deliverable's `Files expected to mutate:` paths are included), never composed by reading outline prose. A path declared with `read` intent is excluded and carried in `read_intent_files` instead; a path declared both ways is a modification and appears here only. Re-derived by set union at every point a later consumer depends on it being current, so it is not frozen at outline time. Contrast `realized_footprint`, which records what the worktree actually touched. |
| `read_intent_files` | list | The READ half of the declared footprint — paths a deliverable declared it would only consult. Written by `sync-affected-files` alongside `affected_files`, and **disjoint** from it. Kept out of `affected_files` because that key is the denominator of every derived recall figure: the realized footprint is a diff, so a file the plan only read can never appear in it, and counting it as an expected modification caps recall below threshold by construction. Kept *here* rather than dropped so the declaration survives and a genuinely small declared surface stays distinguishable from a filtered one. |
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

Re-derive the plan's **declared** footprint from `solution_outline.md`, partition it by declared intent, and union each half into its own key. Where `compute-footprint` / `capture-footprint` answer "what did the worktree touch", this verb answers "what did the outline say the plan expects to touch, and did it expect to *change* it or merely *read* it".

The derivation is structural, not narrative: every path comes from `_plan_parsing.declared_paths_by_intent`, which walks all three declaration headings — `Affected files`, `Files expected to mutate`, `Files to survey` — across every deliverable. A **survey-scope deliverable** declares the latter pair INSTEAD of a flat `Affected files` list, so its expected-to-mutate paths reach the key through this verb and through no other route.

**The intent partition.** The derived paths are split by the intent they were declared with and written to two keys:

| Half | Key | Members |
|------|-----|---------|
| Mutation | `affected_files` | Every `write-new`, `write-replace`, `delete`, and *unannotated-under-a-modification-heading* path |
| Read | `read_intent_files` | Paths declared `read` — including every marker-less bullet under `Files to survey`, which is analysis-only by definition |

Three rules govern the split:

- **A read-intent path never lands in `affected_files`.** That key is the denominator of every recall figure derived downstream, and the realized footprint is a diff — a file the plan only read can never appear in one. Counted as an expected modification it is a denominator member the numerator cannot ever contain, capping recall below threshold no matter how completely the plan executed.
- **An unannotated bullet under a modification heading counts as a modification.** It stated no intent, and the two readings are not symmetric: over-stating the write-set by one path is recoverable, whereas filing it under `read` subtracts a possibly-changing file from every downstream footprint and manufactures a vacuously small denominator. Its count is published separately so the assumption stays visible.
- **Mutation wins the overlap.** A path one deliverable declares a write and another declares a read is an expected modification, and appears under `affected_files` only. The two halves are therefore disjoint, which is what lets `mutation_count + read_intent_count` reconstruct the distinct declared-path total exactly. The number of read declarations reclassified this way is published as `read_reclassified_count`, so the subtraction is visible rather than silently shrinking `read_intent_count`.

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
added[2]:
  - marketplace/bundles/plan-marshall/skills/manage-references/SKILL.md
  - test/plan-marshall/manage-references/test_manage_references.py
mutation_count: 9
read_intent_count: 3
unannotated_count: 1
read_reclassified_count: 0
declared_count: 12
read_intent_field: read_intent_files
read_intent_added_count: 3
read_intent_total: 3
read_intent_added[3]:
  - marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/_plan_parsing.py
  - marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/_footprint_resolver.py
  - marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/ci_base.py
deliverables_scanned: 5
headings_found: 6
bullets_parsed: 31
```

**Notes**:
- Both writes are a **set union** over the existing value. An already-recorded path always survives a subsequent run, a path that appeared after the outline was first read is added, and a repeat run over an unchanged outline changes nothing — which is what makes the verb safe to call at every point a consumer depends on the value being current.
- Ordering is stable: already-recorded paths keep their position, newly derived ones are appended in sorted order.
- The three partition counts exist so a **filtered** set is never mistaken for a **small** one. `mutation_count + read_intent_count == declared_count` (the halves are disjoint); `unannotated_count` is a SUB-count of `mutation_count`, naming how much of the mutation half arrived by the unmarked-bullet default rather than by an explicit marker.
- `added_count` / `unchanged_count` / `total` / `added` describe `affected_files`; the `read_intent_*` peers describe `read_intent_files`. Each names the key it was computed over, so neither set's figures can be read against the wrong key.
- `deliverables_scanned` / `headings_found` / `bullets_parsed` publish the population the derivation walked, so a small result states what it was derived FROM rather than only what it derived.
- It **refuses rather than reporting a clean zero** when nothing could be derived: a missing or unreadable outline, and an outline whose Deliverables section yielded no deliverable blocks, are `status: error` and write nothing.

**Call sites**: `q-gate-validation` § Step 7 (first write), `phase-4-plan` § Step 7b (before the manifest reads `affected_files_count`), and `phase-6-finalize` (loop-back re-entry refresh). The two later sites exist because a faithful read of a stale value cannot detect its own staleness — re-reading the key returns exactly what was written, so only a re-derivation can tell a current value from a stale one.

---

### reconcile-scope

Compare the plan's file surface as it is asserted in three independent places, and report where they disagree. **Read-only** — it writes no key, persists no finding, and returns no failing status.

The three sides:

| Side | Source | What it is |
|------|--------|------------|
| **A** | `references.affected_files` | The **recorded** declaration — the value every downstream consumer actually reads |
| **B** | `_plan_parsing.declared_paths_by_intent`, mutation half | The **declared** derivation — the outline's structured per-path `intent` data, never scraped from prose |
| **C** | The shared whole-chain footprint resolver | The **realized** footprint — what the landing actually touched |

All three pairs are compared and reported: **A↔B** is the primary comparison (the recorded declaration against the structured derivation it is supposed to equal); **A↔C** and **B↔C** are reported alongside it. B is derived through the same partition rule `sync-affected-files` writes A with, so a difference between them is real drift rather than two readings of the same outline disagreeing about what a declaration means.

**Symmetric difference, never cardinality.** Each pair is compared by set difference in **both directions**, and no code path compares set sizes. Two sets of equal size that share no member are maximally different, and a cardinality check calls them identical — that is the defect this verb exists to detect, and it is not hypothetical: a measured instance had two 29-entry lists disagreeing on 7 members each way, which a size check reported as clean. Both directions are published as named lists with their own sizes, alongside the pair's symmetric-difference size. The intersection is never computed, so no verdict can rest on an overlap.

**A side is established or unmeasured — never "empty" by default.** An empty set is a *measurement*: the plan declared nothing, or the landing touched nothing, and it compares meaningfully. A side that could not be built is not a measurement, and reporting it as an empty set would make every difference against it read as a total disagreement — or, against another empty side, as agreement. Each unmeasured side names its own cause (see the reason table below); the request's three named causes — an unparseable outline, an absent `references.json`, and an unresolvable footprint — are three distinct reasons, never one collapsed state.

**Agreement is admissible only when both sides were established AND at least one carried a member.** Two conditions, because two different things manufacture a false clean:

- One side unbuilt → the pair reports `unmeasured`, naming which sides were unbuilt. It publishes no difference lists and no counts at all; their **absence is the contract**, so a consumer that branches on `{pair}_symmetric_difference_count` finds no key rather than a zero.
- Both sides established but **both empty** → nothing was compared, so the zero symmetric difference certifies nothing. That pair reports `vacuous`, not `agree`.

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references reconcile-scope \
  --plan-id {plan_id}
```

**Parameters**:
- `--plan-id` (required): Plan identifier

There is no value argument by design. All three sides are derived, so there is nothing for a caller to supply — and therefore nothing to supply wrongly.

**Output** (TOON):
```toon
status: success
plan_id: my-feature
primary_pair: a_b
sides[3]:
  - a
  - b
  - c
side_count: 3
pairs[3]:
  - a_b
  - a_c
  - b_c
pair_count: 3
a_source: references.affected_files
a_state: established
a_count: 29
b_source: outline.declared_mutation_intent
b_state: established
b_count: 29
deliverables_scanned: 7
headings_found: 9
bullets_parsed: 41
c_source: realized_footprint
c_state: unmeasured
c_unmeasured_reason: footprint_unresolved
a_b_state: disagree
a_not_b_count: 7
b_not_a_count: 7
a_b_symmetric_difference_count: 14
a_not_b[7]:
  - marketplace/bundles/plan-marshall/skills/manage-references/SKILL.md
a_c_state: unmeasured
a_c_unmeasured_sides[1]:
  - c
b_c_state: unmeasured
b_c_unmeasured_sides[1]:
  - c
established_side_count: 2
measured_pair_count: 1
unmeasured_pair_count: 2
```

**Pair states**:

| State | Meaning |
|-------|---------|
| `agree` | Both sides established, at least one non-empty, and neither difference carries a member |
| `disagree` | Both sides established and at least one difference carries a member |
| `vacuous` | Both sides established and **both empty** — the zero symmetric difference certifies nothing, because nothing was compared |
| `unmeasured` | At least one side could not be built, so no comparison was made. `{pair}_unmeasured_sides` names which; each side's own reason is published once, on the side |

**Unmeasured side reasons**:

| Reason | Side | Cause |
|--------|------|-------|
| `references_absent` | A | `references.json` does not exist |
| `references_unreadable` | A | `references.json` exists but could not be read as a JSON object |
| `affected_files_absent` | A | The key was never written. A **missing** key is not an empty list — nothing was recorded, so there is no recorded declaration to compare. A key present as an empty list *is* a measurement and establishes the side |
| `affected_files_not_a_list` | A | The key exists but is not a list, so no path set can be built from it |
| `outline_not_found` | B | `solution_outline.md` does not exist |
| `outline_unreadable` | B | `solution_outline.md` exists but could not be read |
| `no_deliverables_parsed` | B | The outline was read and yielded no deliverable blocks. The population is still published — the zero is measured |
| `footprint_unresolved` | C | No tier of the shared footprint resolver answered |

**Notes**:
- Every count names the population it was computed from: `a_count` / `b_count` / `c_count` size each side; `deliverables_scanned` / `headings_found` / `bullets_parsed` report the walk side B derived from, and are present whenever the outline was read; `established_side_count` / `side_count` and `measured_pair_count` / `unmeasured_pair_count` / `pair_count` report the coverage of the run itself.
- Exactly one of `{side}_count` and `{side}_unmeasured_reason` is present per side, so a side's state cannot be misread from a placeholder value.
- The `sides` and `pairs` rosters are derived from the verb's own declaration rather than restated, and the pair set is derived from the side set — so the published roster is what was actually compared.

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
| `sync-affected-files` | `--plan-id` | Re-derive the declared footprint from the outline's structured deliverable data and union it, intent-partitioned, into `references.affected_files` (mutation) and `references.read_intent_files` (read) |
| `reconcile-scope` | `--plan-id` | Compare the recorded declaration, the structured derivation and the realized footprint pairwise by symmetric difference in both directions (read-only) |
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

### reconcile-scope

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references reconcile-scope \
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
| `not_a_list` | The target key exists but is not a list, so the union has nothing well-formed to union into. Raised for `references.affected_files` and for `references.read_intent_files` alike; the returned `field` names which one, and nothing is written on either branch (sync-affected-files) |

**`reconcile-scope` contributes no code to the table above, deliberately.** It is an audit, and an audit that could not evaluate something reports *that it could not* — it does not fail. Every condition that would be an error for a writing verb (an absent `references.json`, an unreadable or deliverable-less outline, an unresolvable footprint) is reported instead as an `unmeasured` side carrying its own named reason, under `status: success`, so the pairs that *were* comparable are still reported rather than being lost behind a whole-call failure. That vocabulary is the § `reconcile-scope` "Unmeasured side reasons" table; it is the verb's failure surface, and it is exhaustive. The one condition that does abort the call is a malformed `--plan-id`, which `invalid_plan_id` above already covers for every verb.

**Default values**: Unset fields return `field_not_found` on `get`. The `create` command initializes `branch` and `base_branch` (the latter to `main`). All other fields are optional — only present if explicitly set via `--field` / `set-list` arguments.

---

## Integration

### Producers

| Client | Operation | Purpose |
|--------|-----------|---------|
| `phase-1-init` | create, set, set-list | Initialize references with branch, domains, build system |
| `q-gate-validation` (§ Step 7) | sync-affected-files | First derivation of `affected_files` and `read_intent_files` from the outline's structured deliverable data |
| `phase-4-plan` (§ Step 7b) | sync-affected-files | Refresh before the manifest is composed from `affected_files_count`, so scope added between outline and plan reaches the manifest |
| `phase-6-finalize` | sync-affected-files | Refresh on the loop-back re-entry path, so scope added after phase-3 reaches the finalize-time consumers |
| `phase-6-finalize` (`create-pr`) | set | Record `pr_number` immediately after the PR is created or an open one is reused |

### Consumers

| Client | Operation | Purpose |
|--------|-----------|---------|
| `phase-3-outline` | get, get-context | Read domains and build system for skill routing |
| `phase-5-execute` | get-context | Read build system for task execution |
| `manage-execution-manifest` (via `phase-4-plan` § Step 7b) | get | Read `affected_files` as the declared **modification** surface the compose-time classification is decided from — read-intent paths are excluded by construction, so a deliverable that only consults a file no longer inflates the classification |
| `phase-6-finalize` | compute-footprint | Derive the live plan footprint for commit scope and PR body |
| `phase-6-finalize` (`branch-cleanup`) | capture-footprint, set | Persist `realized_footprint` before worktree removal, and record `merge_commit_sha` after the base pull |
| `plan-retrospective`, `audit-archived-plan-retrospectives` | (reads `realized_footprint` / `merge_commit_sha` / `pr_number` via the shared footprint resolver) | Resolve the realized footprint for recall and mis-prune checks post-merge. `pr_number` backs the PR-landing tier, which is the only tier that resolves a squash / merge-queue landing — the path on which `realized_footprint` and `merge_commit_sha` are both unwritten |

## Related

- `manage-files` — Generic file operations for plan directories
- `manage-plan-documents` — Typed plan document operations (request.md)
