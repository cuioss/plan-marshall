---
name: manage-lessons
description: Manage lessons learned with global scope
user-invocable: false
mode: script-executor
scope: global
---

# Manage Lessons Skill

Manage lessons learned with global scope. Stores lessons as markdown files with key=value metadata headers. A lesson's lifecycle state ("unapplied" vs "applied") is encoded by its on-disk location, not by metadata: unapplied lessons live in `.plan/local/lessons-learned/{id}.md`, and become applied by being moved into a plan directory as `.plan/local/plans/{plan_id}/lesson-{id}.md` via `convert-to-plan`.

## Enforcement

> **Base contract**: See [manage-contract.md](../ref-workflow-architecture/standards/manage-contract.md) for shared enforcement rules, TOON output format, and error response patterns.

**Skill-specific constraints:**
- Only valid category values: `bug`, `improvement`, `anti-pattern`
- Lessons are global-scoped (not plan-specific); no `--plan-id` parameter
- The `from-error` command expects JSON context as `--context` argument

**Canonical flag names (do not invent aliases):**
- The lesson-selector flag is **`--lesson-id`** on every verb that targets a single lesson (`get`, `update`, `set-body`, `set-title`, `convert-to-plan`, `remove`, `supersede`, and the explicit-ids mode of `cleanup-superseded`). There is **no `--id` flag** — the bare `id` token appears only as an *output* field and as a *metadata* header key (see [Metadata Fields](#metadata-fields)), never as an input argument. Passing `--id` is rejected by argparse (`exit_code: 2`).
- Lifecycle filtering on `list` is done with **`--status {active|superseded|removed|all}`** (default `active`; use `all` to include superseded/removed lessons). There is **no `--include-tombstoned` flag** — `--status all` is the canonical way to surface non-active lessons. Tombstones at `.tombstones/{id}.json` are the audit trail for supersede/remove events and are not listed by any verb; they are never exposed through a list flag.

## Storage Location

Lessons are stored globally:

```
.plan/lessons-learned/
  2025-12-02-001.md
  2025-12-02-002.md
  ...
```

---

## File Format

Markdown with key=value metadata header:

```markdown
id=2025-12-02-001
component=maven-build
category=bug
created=2025-12-02

# Build fails with missing dependency

When running a Maven clean install, the build fails with a missing
dependency error for `jakarta.json-api`.

## Solution

Add the dependency explicitly to pom.xml:

```xml
<dependency>
    <groupId>jakarta.json</groupId>
    <artifactId>jakarta.json-api</artifactId>
</dependency>
```

## Impact

This affects all projects using jakarta.json without explicit dependency.
```

### Metadata Fields

| Field | Description |
|-------|-------------|
| `id` | Unique identifier (date-sequence). Appears as a metadata header key and in command output; the input flag that selects a lesson by this value is **`--lesson-id`**, not `--id`. |
| `component` | Component that lesson applies to |
| `category` | bug, improvement, anti-pattern |
| `created` | Creation date |
| `bundle` | Optional: bundle that the lesson relates to (e.g., `pm-dev-java`). Used for filtering when applying lessons to specific bundles. |

---

## Operations

Script: `plan-marshall:manage-lessons:manage-lessons`

### add

Allocate a new lesson file with metadata header and title (empty body). The call returns the absolute path of the created file; the caller then populates the body via `set-body` (canonical form, see below) — typically by writing a body file under `{plan_dir}/work/lesson-body-{id}.md` and passing it via `--file`.

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons add \
  --component maven-build \
  --category bug \
  --title "Build fails with missing dependency" \
  [--bundle planning]
```

**Parameters**:
- `--component` (required): Component that lesson applies to
- `--category` (required): `bug`, `improvement`, or `anti-pattern`
- `--title` (required): Lesson title
- `--bundle`: Optional bundle reference

**Output** (TOON):
```toon
status: success
id: 2025-12-02-001
path: /abs/path/to/.plan/local/lessons-learned/2025-12-02-001.md
component: maven-build
category: bug
```

### set-body

Populate (or replace) the body of an existing lesson. This is the **canonical** form for writing lesson bodies. Two mutually exclusive input modes are supported: `--file PATH` (preferred, shell-safe for arbitrary markdown) and `--content STRING` (secondary form, suitable only for tiny single-line payloads).

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons set-body \
  --lesson-id 2025-12-02-001 \
  --file /abs/path/to/.plan/local/plans/{plan_id}/work/lesson-body-2025-12-02-001.md
```

**Parameters**:
- `--lesson-id` (required): Lesson ID whose body to set
- `--file` (preferred): Absolute path to a markdown file containing the body. Use this for any non-trivial content — sections with `##` headings, code fences, multi-paragraph prose — because the body never passes through a shell argument.
- `--content` (secondary, tiny payloads only): Inline string body. Use only for single-line or very short content; any payload containing newlines, backticks, quotes, or shell metacharacters MUST use `--file` instead.

`--file` and `--content` are mutually exclusive — exactly one must be provided.

**Output** (TOON):
```toon
status: success
id: 2025-12-02-001
path: /abs/path/to/.plan/local/lessons-learned/2025-12-02-001.md
body_bytes_written: 1234
```

### set-title

Rewrite the H1 title of an existing lesson file in place. The metadata header (`key=value` frontmatter), blank lines, and lesson body are preserved on disk — only the first `# ` line is replaced. Both `active` and `superseded` lifecycle states are rewriteable; only a missing file or a malformed lesson (no H1 line) fail.

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons set-title \
  --lesson-id 2025-12-02-001 \
  --title "Build fails with missing dependency (canonical)"
```

**Parameters**:
- `--lesson-id` (required): Lesson ID whose title to rewrite
- `--title` (required): New title; replaces the H1 line verbatim

**Idempotent**: rewriting with the existing title produces no on-disk change but still returns `status: success` with `old_title == new_title` so callers can re-run safely.

**Fenced-code-block safety**: the rewriter walks the markdown line-by-line tracking ` ``` ` fence state, so a literal `# heading` line inside a code example is not mistaken for the lesson H1.

**Output** (TOON):
```toon
status: success
lesson_id: 2025-12-02-001
old_title: "Build fails with missing dependency"
new_title: "Build fails with missing dependency (canonical)"
file: /abs/path/to/.plan/local/lessons-learned/2025-12-02-001.md
```

**Path-allocate flow (canonical)**:

The standard sequence for creating a lesson with a non-trivial body is:

1. `add` — allocate the lesson file and capture the returned `id`.
2. `Write {plan_dir}/work/lesson-body-{id}.md` — write the body markdown directly to a plan-scoped staging file using the Write tool. This bypasses shell quoting entirely and supports arbitrary markdown content.
3. `set-body --lesson-id {id} --file {path}` — apply the staged body to the lesson file. The script reads the file from disk and replaces the body section while preserving the metadata header and title.

Worked example:

```
# Step 1: allocate
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons add \
  --component maven-build --category bug \
  --title "Build fails with missing dependency"
# → returns id=2025-12-02-001

# Step 2: stage body via Write tool (no shell quoting concerns)
Write("/abs/path/to/.plan/local/plans/EXAMPLE-PLAN/work/lesson-body-2025-12-02-001.md", body_markdown)

# Step 3: apply
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons set-body \
  --lesson-id 2025-12-02-001 \
  --file /abs/path/to/.plan/local/plans/EXAMPLE-PLAN/work/lesson-body-2025-12-02-001.md
```

The inline `--content STRING` form is the secondary path — reserve it for tiny single-line payloads (e.g., a one-sentence note) where staging a file would be overhead. For anything multi-line, code-bearing, or containing shell-significant characters, always use the path-allocate flow above.

### update

Update lesson metadata.

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons update \
  --lesson-id 2025-12-02-001 \
  [--component new-component] \
  [--category bug|improvement|anti-pattern]
```

**Parameters**:
- `--lesson-id` (required): Lesson ID to update
- `--component`: Update component name
- `--category`: Update category

**Output** (TOON):
```toon
status: success
id: 2025-12-02-001
field: component
value: new-component
previous: maven-build
```

### get

Get a single lesson.

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons get \
  --lesson-id 2025-12-02-001
```

**Output** (TOON):
```toon
status: success
id: 2025-12-02-001
component: maven-build
category: bug
created: 2025-12-02
title: Build fails with missing dependency

content: |
  When running a Maven clean install...
```

### list

List lessons with filtering.

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons list \
  [--component maven-build] \
  [--category bug] \
  [--status active|superseded|removed|all] \
  [--full]
```

**Parameters**:
- `--component`: Filter by component name
- `--category`: Filter by category (`bug`, `improvement`, `anti-pattern`)
- `--status`: Filter by lifecycle status — `active` (default), `superseded`, `removed`, or `all`. Use `--status all` to surface superseded/removed lessons; this is the canonical mechanism (there is no `--include-tombstoned` flag).
- `--full`: Include the full lesson body content in each row

**Output** (TOON):
```toon
status: success
total: 5
filtered: 2
lessons:
  - id: 2025-12-02-001
    component: maven-build
    category: bug
    title: Build fails with missing dependency
  - id: 2025-12-02-002
    component: plan-files
    category: improvement
    title: Add validation for plan_id format
```

### convert-to-plan

Move a lesson out of the global lessons-learned directory and into a plan directory as `lesson-{id}.md`. This is how a lesson transitions from "unapplied" to "applied" — the lifecycle state is encoded in the file's location, not in metadata.

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons convert-to-plan \
  --lesson-id 2025-12-02-001 \
  --plan-id EXAMPLE-PLAN
```

**Parameters**:
- `--lesson-id` (required): Lesson ID to move
- `--plan-id` (required): Target plan directory under `.plan/local/plans/`

**Output** (TOON):
```toon
status: success
lesson_id: 2025-12-02-001
plan_id: EXAMPLE-PLAN
source: .plan/local/lessons-learned/2025-12-02-001.md
destination: .plan/local/plans/EXAMPLE-PLAN/lesson-2025-12-02-001.md
```

### cleanup-superseded

Prune the markdown stubs of superseded lessons. Tombstones at
`.tombstones/{id}.json` are NEVER touched — they remain as the audit trail
for the supersede event so historical references resolve by id even after
the redirect stub is gone.

Two mutually exclusive modes:

- **Explicit ids** — `--lesson-id ID` (repeatable). Each id is evaluated
  regardless of file age. Required `metadata.status == 'superseded'` and
  the matching tombstone must exist.
- **Age-filtered** — `--retention-days N`. Walks every `.md` whose
  `metadata.status == 'superseded'` and whose mtime is older than
  `now - N days`. When `--retention-days` is omitted, the value falls back
  to `system.retention.lessons_superseded_days` from `marshal.json`,
  with a hard fallback of `7` if marshal.json is absent or unreadable.

Per-id outcomes:

| Bucket | Condition |
|--------|-----------|
| `removed[]` | Lesson `.md` was unlinked (or, on `--dry-run`, would have been) |
| `already_removed[]` | `.md` already absent and tombstone present (idempotent re-run) |
| `skipped_no_tombstone[]` | Tombstone missing — refused to act because the audit trail would be lost |

```bash
# Age-filtered (uses marshal.json retention or hard fallback 7 days)
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons cleanup-superseded

# Age-filtered with explicit threshold
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons cleanup-superseded \
  --retention-days 30

# Explicit ids
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons cleanup-superseded \
  --lesson-id 2025-12-02-001 \
  --lesson-id 2025-12-02-002

# Dry-run (report only)
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons cleanup-superseded \
  --retention-days 7 --dry-run
```

**Parameters**:
- `--lesson-id`: Repeatable lesson ID; mutually exclusive with `--retention-days`
- `--retention-days`: Age threshold in days; mutually exclusive with `--lesson-id`
- `--dry-run`: Report what would be removed without unlinking anything

**Output** (TOON):
```toon
status: success
dry_run: false
retention_days_effective: 7
removed[1]{lesson_id}:
  2025-12-02-001
already_removed[0]{lesson_id}:
skipped_no_tombstone[0]{lesson_id}:
```

Each successful unlink emits an INFO line to `script-execution.log`:
`(plan-marshall:manage-lessons) Pruned superseded stub {id}`.

### from-error

Create lesson from error context (JSON).

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons from-error \
  --context '{"component":"maven-build","error":"Missing dependency","solution":"Add explicit dep"}'
```

**Parameters**:
- `--context` (required): JSON object with error context
  - `component`: Component name (defaults to "unknown")
  - `error`: Error message (required)
  - `solution`: Optional solution description

**Output** (TOON):
```toon
status: success
id: 2025-12-02-003
created_from: error_context
```

### aggregate

Read-only classifier that groups the active lessons corpus into multi-lesson groups whose work would land in a single plan. Never mutates lesson files — `set-body`, `set-title`, `supersede`, and `cleanup-superseded` are NOT invoked. Use the orchestrator action (`/plan-marshall:plan-marshall` Action: lessons-aggregate) when you want the merge actually applied; use this verb when you want to inspect the classification first.

The classifier rules, signal-priority order, primary-pick tie-breakers, and merged-body-preview template are specified in [`references/aggregate-analysis.md`](references/aggregate-analysis.md).

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons aggregate \
  [--top-n 5]
```

**Parameters**:
- `--top-n` (optional, default `5`): Number of headline `/plan-marshall:plan-marshall lesson={primary_id}` commands to surface in `top_n_commands`. The full `groups[]` list is always returned regardless of this flag.

**Output** (TOON):
```toon
status: success
top_n: 5
groups[N]{primary_id,primary_title,absorb_count,tier,enacted,absorbed,merged_body_preview}:
  ...
top_n_commands[N]:
  - "/plan-marshall:plan-marshall lesson=2025-12-02-001"
  - "/plan-marshall:plan-marshall lesson=2025-12-04-002"
```

Each group carries `tier` (the producing signal: `cross-ref` | `shared-component` | `shared-standards-dir` | `shared-workflow-boundary`) and `enacted` (`true` only for the `cross-ref` tier — weaker tiers are opt-in co-location suggestions, not auto-applied merges). Each `absorbed[]` row carries `{lesson_id, title, reason}` where `reason` names the strongest signal that placed the lesson in the group (e.g., `cross-ref to 2025-12-02-001`, `shared component plan-marshall:phase-5-execute`, `shared standards-dir marketplace/bundles/.../standards/`, `shared workflow-boundary plan-marshall:phase-5-execute`). `merged_body_preview` is the first ~400 characters of the would-be merged body so callers can sanity-check the grouping before invoking the orchestrator action.

Singletons (lessons that match no other lesson at any signal tier) are dropped — only multi-member groups are emitted.

### list-stalled

Read-only scanner that surfaces lesson-sourced plans whose relocated lesson is **stranded** (stalled). When a lesson is moved into a plan directory via `convert-to-plan` (`plans/{plan_id}/lesson-{id}.md`), it leaves the active corpus. If that plan then stalls or is abandoned in `5-execute`/`6-finalize` without running `restore-from-plan`, the lesson stays trapped inside the plan directory and is silently lost. This verb reports every such plan so callers can decide whether to restore or discard. It never mutates lesson files or plan directories.

Detection algorithm (deterministic, read-only):

1. Resolve the plans root and glob `*/lesson-*.md` to find plan dirs still holding a relocated lesson; group the matched lesson files by owning plan dir.
2. For each such plan dir, read the sibling `status.json` (a missing or corrupt `status.json` yields a skipped entry rather than a crash).
3. Classify the plan as **stalled** when `metadata.plan_source` matches the lesson-id pattern (`YYYY-MM-DD-HH-NNN`, i.e. lesson-sourced) AND it is NOT in a terminal state — `current_phase` is one of `5-execute` / `6-finalize` and that phase's row `status != done`. A lesson-sourced plan whose current phase has fully completed is NOT stalled (its lesson was, or will be, restored on the normal terminal path).
4. Emit each stalled plan with the exact `restore-from-plan --plan-id {plan_id}` invocation in `restore_command`.

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons list-stalled
```

**Parameters**: none.

**Output** (TOON):
```toon
status: success
stalled_count: 1
stalled_plans:
  - plan_id: 2025-12-02-001-example-plan
    plan_source: 2025-12-02-15-001
    current_phase: 5-execute
    phase_status: in_progress
    lesson_ids:
      - 2025-12-02-15-001
    restore_command: "python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons restore-from-plan --plan-id 2025-12-02-001-example-plan"
```

An empty corpus (no plans root, or no stalled lesson-sourced plans) returns `stalled_count: 0` with an empty `stalled_plans`.

#### Stalled-lesson lifecycle gap

`convert-to-plan` is the move that takes a lesson out of the active corpus and into a plan directory; `restore-from-plan` is its inverse, returning the relocated lesson back to `.plan/local/lessons-learned/`. When a lesson-sourced plan stalls or is abandoned before reaching a terminal state, the relocated lesson is trapped at the plan-dir root and never resurfaces. `list-stalled` is the detection half of closing that gap — it identifies every trapped lesson; `restore-from-plan` is the remediation half that frees it. The `Action: cleanup` workflow consumes both as a paired scan-and-restore pass.

---

## References

The classification logic for the read-side corpus operations lives under `references/`:

- [`references/dedup-analysis.md`](references/dedup-analysis.md) — single-candidate classifier (new / merge_into / already_closed). Used by the dedup gate before any new lesson is recorded.
- [`references/aggregate-analysis.md`](references/aggregate-analysis.md) — full-corpus classifier. Specifies the signal-priority order (cross-ref > shared-component > shared-standards-dir > shared-workflow-boundary), primary-pick tie-breakers (cross-ref-fan-in → recurrence-count → lesson-id), and the merged-body-preview template consumed by the `aggregate` verb and the `lessons-aggregate` orchestrator action.

---

## Scripts

**Script**: `plan-marshall:manage-lessons:manage-lessons`

| Command | Parameters | Description |
|---------|------------|-------------|
| `add` | `--component --category --title [--bundle]` | Allocate a new lesson file and return its absolute `path`. Caller populates body via `set-body`. |
| `set-body` | `--lesson-id (--file PATH \| --content STRING)` | Populate or replace lesson body. `--file` is the canonical form (shell-safe for arbitrary markdown); `--content` is the secondary form for tiny single-line payloads only. |
| `set-title` | `--lesson-id --title` | Rewrite the H1 title in place. Preserves frontmatter and body; idempotent; works on `active` and `superseded` lessons. Fenced-code-block aware. |
| `update` | `--lesson-id [--component] [--category]` | Update lesson metadata |
| `get` | `--lesson-id` | Get single lesson |
| `list` | `[--component] [--category] [--full]` | List with filtering. `--full` includes lesson body content. |
| `aggregate` | `[--top-n N]` | Read-only classifier: group active lessons that would land in one plan. Returns groups + headline commands. See [`references/aggregate-analysis.md`](references/aggregate-analysis.md). |
| `from-error` | `--context` | Create from JSON error context (programmatic; body synthesized from context) |
| `convert-to-plan` | `--lesson-id --plan-id` | Move lesson into a plan directory as `lesson-{id}.md`. This is the move-semantics replacement for marking a lesson "applied". |
| `restore-from-plan` | `--plan-id` | Inverse of `convert-to-plan`: move the relocated `lesson-*.md` back from a plan directory to the active corpus (`.plan/local/lessons-learned/`). Run on stall/abandon so a stranded lesson resurfaces. |
| `cleanup-superseded` | `[--lesson-id ID ...] \| [--retention-days N] [--dry-run]` | Prune superseded `.md` stubs while preserving tombstones. Age-filtered when `--retention-days` (falls back to `system.retention.lessons_superseded_days`, hard fallback 7); explicit when `--lesson-id` is repeated. |
| `list-stalled` | (none) | Read-only scanner: report lesson-sourced plans whose relocated lesson is stranded in a non-terminal `5-execute`/`6-finalize` state. Returns `stalled_count` and per-plan `restore_command`. Never mutates lesson files or plan dirs. |
| `auto-suggest` | `--plan-id [--max-suggestions N] [--no-emit]` | Recipe-registry matcher for phase-1-init Step 5c. Scans the live recipe registry (`manage-config list-recipes`) and returns up to `--max-suggestions` recipes (default 3) ordered by deterministic confidence — keyword overlap (request narrative ∩ recipe description) + domain alignment + scope alignment. Each suggestion is also written as a plan-scoped `tip` finding (`artifacts/findings/tip.jsonl`) so the orchestrator can surface them in the audit log; pass `--no-emit` to inspect without writing findings. No LLM dispatch — the matcher is pure regex + set algebra. Falls through to the existing Step 5c LLM path when no recipe clears the 0.35 confidence floor. |

---

## Categories

| Category | When to Use |
|----------|-------------|
| `bug` | Script is broken or produces wrong results |
| `improvement` | Script works but could be better |
| `anti-pattern` | Script was misused or documentation unclear |

---

## Error Responses

> See [manage-contract.md](../ref-workflow-architecture/standards/manage-contract.md) for the standard error response format.

| Error Code | Cause |
|------------|-------|
| `not_found` | Lesson ID doesn't exist (get, update, set-body, convert-to-plan) |
| `copy_failed` | `convert-to-plan` failed to copy the lesson to the plan directory (I/O error or read-back content mismatch); source lesson is left intact, no partial artifact survives |
| `invalid_category` | Category not in: bug, improvement, anti-pattern |
| `invalid_context` | JSON context parsing failed (from-error) |
| `invalid_input` | `set-body` invoked without exactly one of `--file` / `--content`, or both supplied |
| `file_not_found` | `set-body --file PATH` points at a non-existent path or a non-regular file (directory, broken symlink, special file) |
| `file_read_error` | `set-body --file PATH` failed with an `OSError` while reading (permission denied, I/O error, etc.) |
| `malformed_lesson` | `set-body` target lesson file is missing its metadata header / title structure |
| `missing_required` | Required parameter missing |

---

## Canonical invocations

The canonical argparse surface for `manage-lessons.py`. The D4 plugin-doctor analyzer
(`_analyze_manage_invocation.py`) reads this section as source-of-truth for markdown
notation occurrences across the marketplace. Consuming skills xref this section by
name (e.g., "see `manage-lessons` Canonical invocations → `add`") instead of
restating the command inline.

### add

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons add \
  --component COMPONENT --category {bug|improvement|anti-pattern} --title TEXT \
  [--bundle BUNDLE]
```

### update

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons update \
  --lesson-id LESSON_ID \
  [--component COMPONENT] [--category {bug|improvement|anti-pattern}]
```

### get

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons get \
  --lesson-id LESSON_ID
```

### list

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons list \
  [--component COMPONENT] [--category {bug|improvement|anti-pattern}] \
  [--status {active|superseded|removed|all}] [--full]
```

### convert-to-plan

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons convert-to-plan \
  --lesson-id LESSON_ID --plan-id PLAN_ID
```

### set-body

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons set-body \
  --lesson-id LESSON_ID (--file PATH | --content TEXT)
```

`--file` and `--content` are mutually exclusive; exactly one is required.

### set-title

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons set-title \
  --lesson-id LESSON_ID --title TEXT
```

### aggregate

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons aggregate \
  [--top-n N]
```

### from-error

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons from-error \
  --context JSON
```

### remove

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons remove \
  --lesson-id LESSON_ID --reason TEXT \
  [--force]
```

### supersede

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons supersede \
  --lesson-id LESSON_ID --by CANONICAL_LESSON_ID --reason TEXT
```

### cleanup-superseded

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons cleanup-superseded \
  [--lesson-id LESSON_ID ...] [--retention-days N] [--dry-run]
```

`--lesson-id` (repeatable) and `--retention-days` are mutually exclusive.

### auto-suggest

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons auto-suggest \
  --plan-id PLAN_ID [--max-suggestions N] [--no-emit]
```

### list-stalled

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons list-stalled
```

### restore-from-plan

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons restore-from-plan \
  --plan-id PLAN_ID
```

---

## Integration

### Producers

| Client | Operation | Purpose |
|--------|-----------|---------|
| `phase-5-execute` | add, from-error | Document errors and solutions during execution |
| `phase-6-finalize` | add | Promote findings to lessons |
| `plugin-doctor` | add | Capture recurring component issues |

### Consumers

| Client | Operation | Purpose |
|--------|-----------|---------|
| `plugin-apply-lessons-learned` | list, convert-to-plan | Apply lessons to marketplace components by moving them into a plan directory |
| `phase-6-finalize` | list | Query unapplied lessons (those still in `.plan/local/lessons-learned/`) for promotion |

## Related

- `manage-findings` — Findings promoted to lessons at 6-finalize
- `manage-run-config` — Complementary global persistence (execution state)
