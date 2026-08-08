---
name: plan-marshall-manage-lessons
description: Manage lessons learned with global scope, including the main-anchored store handle and the fail-closed retirement surface — restore-from-plan's four-state outcome, list-stalled's file-presence-derived population plus its duplication direction, and the store-resolution discriminator that makes every zero state whether the store was actually resolved and scanned
compatibility: Adapted from plan-marshall marketplace (Claude Code native)
---

# Manage Lessons Skill

Manage lessons learned with global scope. Stores lessons as markdown files with key=value metadata headers. A lesson's lifecycle state ("unapplied" vs "applied") is encoded by its on-disk location, not by metadata: unapplied lessons live in `.plan/local/lessons-learned/{id}.md`, and become applied by being moved into a plan directory as `.plan/local/plans/{plan_id}/lesson-{id}.md` via `convert-to-plan`.

## Enforcement

> **Base contract**: See [manage-contract.md](../ref-workflow-architecture/standards/manage-contract.md) for shared enforcement rules, TOON output format, and error response patterns.

**Skill-specific constraints:**
- Only valid category values: `bug`, `improvement`, `anti-pattern`, `arch-constraint`
- `arch-constraint` lessons require `--rule` on `add` (the dedup key) and follow a rule-identity dedup + retire-on-quiet lifecycle (see [Categories](#categories) and `standards/file-format.md`)
- Lessons are global-scoped (not plan-specific); no `--plan-id` parameter
- The `from-error` command expects JSON context as `--context` argument

**Canonical flag names (do not invent aliases):**
- The lesson-selector flag is **`--lesson-id`** on every verb that targets a single lesson (`get`, `update`, `set-body`, `set-title`, `convert-to-plan`, `remove`, `supersede`, and the explicit-ids mode of `cleanup-superseded`). There is **no `--id` flag** — the bare `id` token appears only as an *output* field and as a *metadata* header key (see [Metadata Fields](#metadata-fields)), never as an input argument. Passing `--id` is rejected by argparse (`exit_code: 2`).
- Lifecycle filtering on `list` is done with **`--status {active|superseded|removed|all}`** (default `active`; use `all` to include superseded/removed lessons). There is **no `--include-tombstoned` flag** — `--status all` is the canonical way to surface non-active lessons. Tombstones at `.tombstones/{id}.json` are the audit trail for supersede/remove events and are not listed by any verb; they are never exposed through a list flag.

## Storage Location

Lessons are stored globally:

```text
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
```text

### Metadata Fields

| Field | Description |
|-------|-------------|
| `id` | Unique identifier (date-sequence). Appears as a metadata header key and in command output; the input flag that selects a lesson by this value is **`--lesson-id`**, not `--id`. |
| `component` | Component that lesson applies to |
| `category` | bug, improvement, anti-pattern, arch-constraint |
| `created` | Creation date |
| `bundle` | Optional: bundle that the lesson relates to (e.g., `pm-dev-java`). Used for filtering when applying lessons to specific bundles. |
| `rule` | Conditional (arch-constraint only): the rule identity that is the dedup key |
| `recurrence_count` | Conditional (arch-constraint only): observation count, bumped on each reinforce |
| `last_seen` | Conditional (arch-constraint only): `YYYY-MM-DD` of the latest observation; anchors retire-on-quiet |

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
- `--category` (required): `bug`, `improvement`, `anti-pattern`, or `arch-constraint`
- `--title` (required): Lesson title
- `--bundle`: Optional bundle reference
- `--rule`: Rule identity — required for `--category arch-constraint` (the dedup key). When an active `arch-constraint` lesson already covers the rule, `add` reinforces it (recurrence_count bump + `## Recurrence` section) and returns the existing id with `action: reinforced` instead of allocating a new lesson.
- `--allow-foreign-store`: Bypass the cross-repo wrong-store guard — file the lesson even when the resolved main-anchored store repo does not own the `--component` bundle. The guard applies **only to a component carrying a bundle prefix** (`bundle:skill[:script]`); a prefix-less project-local component (e.g. `integration-tests`) names no bundle, so it files into its own store **without this flag**. Without the flag, a prefixed-bundle mismatch refuses with `error: wrong_store`. A component that does not match the canonical component shape is rejected with `error: invalid_component` — the shape check runs before this flag, so the override cannot launder a malformed value. Skipped under test overrides (`PLAN_BASE_DIR`).

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

```text
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

### consult

Read-only **prospective** query: surface the active lessons that name the components a plan is about to edit. This is the corpus's read side — every other read verb is retrospective (dedup, housekeeping) or referential-integrity. Fired by `phase-3-outline` once `solution_outline.md` has been written and validated, on every authoring lane.

The derivation is entirely script-side — no component notation is supplied by, or inferable from, agent narrative:

1. Resolve `.plan/local/plans/{plan_id}/solution_outline.md`; a missing outline is a structured `error: outline_not_found`, never `status: success` with an empty surfaced set.
2. Extract every deliverable's `**Affected files:**` paths via the shared plan-document parser.
3. Map each path under `marketplace/bundles/{bundle}/skills/{skill}/**` to the component notation `{bundle}:{skill}`. Every path that does not match appears in `unmapped_paths[]`, so narrowing is visible rather than silent.
4. Query active lessons by **exact** `component` string equality — the same predicate `list --component` applies. There is no fuzzy or prefix expansion, so every surfaced lesson genuinely names a component the plan is editing.
5. Union and order deterministically by `(component, lesson_id)`.
6. Apply `--max-per-component`; when the cap binds, report `truncated: true` together with the untruncated `total_matched`. No code path returns a trimmed set that presents itself as complete.
7. Write the machine record to `.plan/local/plans/{plan_id}/work/lessons-consult.toon`.

**Never auto-applies.** The verb mutates no lesson file, alters no deliverable, and emits no Q-Gate finding; its only write is the artifact. The outline author judges the returned set and records one disposition per surfaced lesson in the outline's `## Lessons Consulted` section (see [`phase-3-outline` standards/outline-workflow-detail.md](../phase-3-outline/standards/outline-workflow-detail.md) for the authoritative procedure).

The artifact is deliberately separate from the outline section: a present `work/lessons-consult.toon` with `surfaced_count: 0` means *the consult fired and matched nothing*, while an absent file means *the consult never fired*. A single artifact could not distinguish those.

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons consult \
  --plan-id EXAMPLE-PLAN \
  [--max-per-component 25]
```

**Parameters**:
- `--plan-id` (required): Plan whose `solution_outline.md` supplies the affected-file set
- `--max-per-component` (optional, default `25`): Per-component cap on surfaced lessons. A runaway guard for corpus growth, not a routine trim — when it binds, truncation is always disclosed.

**Output** (TOON):
```toon
status: success
plan_id: EXAMPLE-PLAN
components[2]:
  - plan-marshall:manage-lessons
  - plan-marshall:phase-3-outline
unmapped_paths[1]:
  - test/plan-marshall/manage-lessons/test_consult.py
surfaced[1]{lesson_id,component,category,title}:
  2025-12-02-15-001,plan-marshall:phase-3-outline,improvement,Outline omitted the doc-contract surface
surfaced_count: 1
total_matched: 1
truncated: false
artifact_path: /abs/path/to/.plan/local/plans/EXAMPLE-PLAN/work/lessons-consult.toon
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

### remove

Delete a lesson file and write a tombstone. Interactive confirm by default; `--force` skips the prompt.

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons remove \
  --lesson-id 2025-12-02-001 \
  --reason "guarded failure mode can no longer occur (plan EXAMPLE-PLAN)" \
  --coverage-verdict completely_covered \
  --covering-clause "manage-lessons/SKILL.md Canonical invocations -> remove" \
  --covering-input "remove --coverage-verdict completely_covered with no --covering-clause" \
  --force
```

**Parameters**:

- `--lesson-id` (required): Lesson ID to remove
- `--reason` (required): Free-text removal reason, recorded in the tombstone and the audit log
- `--coverage-verdict` (required, no default): one of `completely_covered`, `redundant`, `superseded`, `obsolete`
- `--covering-clause` (required when the verdict is `completely_covered`): the clause that codifies the rule the lesson taught, named precisely enough to re-read
- `--covering-input` (required when the verdict is `completely_covered`): the concrete input on which that clause's own worked example produces the correct result
- `--force`: Skip the interactive confirmation prompt

#### Retirement evidence: the two-key remove path

Classifying a lesson as retired and deleting it are two separate keys, and the strongest verdict must carry its own evidence:

- **Key 1 — the verdict.** `--coverage-verdict` is required and has no default, so a retirement always states *why*. An omitted verdict is an argparse-level rejection, never a silent default.
- **Key 2 — the evidence pair.** `completely_covered` is the only verdict that asserts the lesson's rule now lives somewhere else, so it alone must name that somewhere: `--covering-clause` (the clause that codifies the rule) and `--covering-input` (the concrete input on which that clause's *own worked example* produces the correct result). Supplying `completely_covered` without BOTH is an argparse-level rejection — exit 2, usage on stderr, and the lesson is left untouched on disk. A whitespace-only value counts as missing.

The evidence is not merely validated, it is **recorded**: the tombstone at `.tombstones/{id}.json` carries `coverage_verdict` always, plus `covering_clause` and `covering_input` when supplied. That is what makes the justification for a deletion outlive the lesson it deleted — the tombstone, not the vanished lesson, is where a later reader checks whether the retirement verdict was sound.

**Tombstone fields written by `remove`**:

| Field | When present | Meaning |
|-------|--------------|---------|
| `lesson_id` | always | The retired lesson's id |
| `removed_at` | always | UTC ISO-8601 instant of the removal |
| `reason` | always | The `--reason` text |
| `status` | always | `removed` |
| `coverage_verdict` | always | The `--coverage-verdict` value |
| `covering_clause` | `completely_covered` | The clause claimed to codify the lesson's rule |
| `covering_input` | `completely_covered` | The input the clause's worked example resolves |

**Output** (TOON):

```toon
status: success
id: 2025-12-02-001
reason: "guarded failure mode can no longer occur (plan EXAMPLE-PLAN)"
tombstone: /abs/path/to/.plan/local/lessons-learned/.tombstones/2025-12-02-001.json
coverage_verdict: completely_covered
covering_clause: "manage-lessons/SKILL.md Canonical invocations -> remove"
covering_input: "remove --coverage-verdict completely_covered with no --covering-clause"
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

### retire-quiet

Retire-on-quiet sibling of `cleanup-superseded` for the `arch-constraint` lifecycle. Walks active `arch-constraint` lessons and retires (tombstone + unlink) every one whose `last_seen` is at least the quiet window old — i.e. the rule has stayed quiet (no recurrence) for that long. Tombstones are preserved exactly as `cleanup-superseded` does. A reinforced lesson's refreshed `last_seen` resets the quiet clock.

```bash
# Default window (marshal.json system.retention.arch_constraint_quiet_days, else hard fallback)
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons retire-quiet

# Explicit window
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons retire-quiet \
  --quiet-days 90

# Dry-run (report only)
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons retire-quiet \
  --quiet-days 90 --dry-run
```

**Parameters**:
- `--quiet-days`: Quiet window in days. Falls back to `system.retention.arch_constraint_quiet_days` from marshal.json, then a hard fallback, when omitted.
- `--dry-run`: Report what would be retired without unlinking anything

**Output** (TOON):
```toon
status: success
dry_run: false
quiet_days: 90
retired[1]{lesson_id,rule,quiet_days_elapsed}:
  2025-12-02-001,java:no-web-in-service,120
retained[0]{lesson_id,rule,quiet_days_elapsed}:
skipped_unparseable_date[0]{lesson_id,last_seen}:
```

Each retirement emits an INFO line to `script-execution.log`:
`(plan-marshall:manage-lessons) Retired quiet arch-constraint lesson {id} (rule {rule}, quiet {N}d >= {window}d)`.

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
- `--allow-foreign-store`: Bypass the cross-repo wrong-store guard — file the lesson even when the resolved main-anchored store repo does not own the context `component` bundle. The guard applies **only to a component carrying a bundle prefix** (`bundle:skill[:script]`); a prefix-less component names no bundle and files without this flag. This includes the documented `unknown` default applied when the context supplies no `component` — `unknown` is prefix-less and therefore local. Only an **absent** `component` defaults: an explicitly-supplied non-string value (`null`, a number, an array) is NOT coerced and is rejected with `error: invalid_component`. Without the flag, a prefixed-bundle mismatch refuses with `error: wrong_store`. Because the context `component` comes from untrusted JSON and bypasses the argparse validator, the guard is also the shape check for this path: a value failing the canonical component shape is rejected with `error: invalid_component`, before this flag is consulted. Skipped under test overrides (`PLAN_BASE_DIR`).

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

Read-only scanner that surfaces plans whose relocated lesson is **stranded** (stalled). When a lesson is moved into a plan directory via `convert-to-plan` (`plans/{plan_id}/lesson-{id}.md`), it leaves the active corpus. If that plan then stalls or is abandoned in `5-execute`/`6-finalize` without running `restore-from-plan`, the lesson stays trapped inside the plan directory and is silently lost. This verb reports every such plan so callers can decide whether to restore or discard. It never mutates lesson files or plan directories.

**The candidate population is the observable file, not a metadata field.** A plan is a candidate exactly when its directory holds a `lesson-*.md`. The population is deliberately NOT filtered by `status.metadata.plan_source`: a gate requiring a lesson-id-shaped `plan_source` excludes every `convert-to-plan`-carried plan (whose `plan_source` is unset), so the verb would report a clean zero over a population that had already discarded the plans it exists to find. A file on disk cannot be argued with; a metadata field that was never written can. `plan_source` is still reported on each row as context; it classifies nothing.

Detection algorithm (deterministic, read-only):

1. Resolve the main-anchored plans root and lessons corpus. **Both are required**, so either one failing is a structured `store_unresolved` error — never a zero. The error names the store that actually failed: `store_resolution: unresolved`, `plans_root_state: unknown`, and `unresolved_store: plans | lessons`. Reporting the sibling store's resolution here would emit a resolved `store_resolution` next to the error, and the documented consumers branch on that field. An absent plans root under a store that DID resolve is the separate, non-faulting `plans_root_state: missing`, which says the scan could not look.
2. Glob `*/lesson-*.md` under the plans root to find plan dirs still holding a relocated lesson; group the matched lesson files by owning plan dir. `scanned_plan_count` reports the size of that population.
3. For each candidate, report both directions. **Absence direction**: read the sibling `status.json` and classify the plan as **stalled** when it is NOT in a terminal state — `current_phase` is one of `5-execute` / `6-finalize` and that phase's row `status != done`. A plan whose current phase has fully completed is NOT stalled (its lesson was, or will be, restored on the normal terminal path). A `status.json` that is missing, unreadable, or not a JSON object yields an `unclassifiable_plans[]` row carrying the reason — it is surfaced, never silently skipped out of the population. **Duplication direction**: every carried lesson id that ALREADY exists in the active corpus is emitted as a `duplicate_lessons[]` row, whatever the plan's stalled classification.
4. Emit each stalled plan with the exact `restore-from-plan --plan-id {plan_id}` invocation in `restore_command`.

`stalled_plans[]` and `duplicate_lessons[]` are independent views over the same scan, correlated by `plan_id`. A plan may legitimately appear in both, and a caller intending to run `restore_command` MUST check the duplicate list first — restoring a duplicate id fails with `destination_exists`.

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons list-stalled
```

**Parameters**: none.

**Output** (TOON) — every field below is emitted on every branch, including the could-not-look ones:
```toon
status: success
store_resolution: main_anchored
plans_root: /abs/path/to/.plan/local/plans
plans_root_state: present
unresolved_store: ""
scanned_plan_count: 2
stalled_count: 1
stalled_plans:
  - plan_id: 2025-12-02-001-example-plan
    plan_source: 2025-12-02-15-001
    current_phase: 5-execute
    phase_status: in_progress
    lesson_ids:
      - 2025-12-02-15-001
    restore_command: "python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons restore-from-plan --plan-id 2025-12-02-001-example-plan"
duplicate_count: 1
duplicate_lessons:
  - plan_id: 2025-12-04-002-other-plan
    lesson_id: 2025-12-04-09-002
    corpus_path: /abs/path/to/.plan/local/lessons-learned/2025-12-04-09-002.md
unclassifiable_count: 0
unclassifiable_plans: []
```

**Every zero states which kind of zero it is.** `stalled_count: 0` is never bare — it always rides with `store_resolution`, `plans_root`, `plans_root_state`, `unresolved_store`, and `scanned_plan_count`. A genuinely clean corpus is `plans_root_state: present` with `scanned_plan_count: 0`; a scan that could not look is `plans_root_state: missing` (still `status: success`, so a sweep is never aborted by it) or a `store_unresolved` error. Read the discriminator, not the count alone.

`plans_root_state` is a closed three-value vocabulary. `present` and `missing` both assert a fact about the resolved plans root — it exists, or it does not. **`unknown` is the third value because neither assertion is available when a store did not resolve**: nothing established whether the plans root exists, so claiming `missing` would report a filesystem fact the verb never observed. `unknown` rides only with the `store_unresolved` error, and `unresolved_store` names which of the two required stores failed.

### restore-from-plan

Inverse of `convert-to-plan`: move every `lesson-*.md` at a plan directory's root back into the active corpus at `.plan/local/lessons-learned/{lesson_id}.md`. Plans that consolidate several lessons carry more than one file; every match is restored.

**Four distinguishable outcomes.** The verb reports which kind of answer it is giving over the closed `action` vocabulary, modelled on `marshall-orchestrator`'s `inbox list` triple — the discriminator rides the payload, and the verb stays non-faulting for the benign zero:

| `action` | `status` | Meaning |
|----------|----------|---------|
| `restored` | `success` | The plan directory resolved, was scanned, carried at least one lesson file, and **every** carried file was moved back. |
| `restore_incomplete` | `error` | The plan directory resolved, was scanned, and carried lesson files, but the move **aborted** on a collision, a traversal guard, or a carried entry that is not a regular file. `restored_count` states how many landed before the abort and is legitimately `0` when the very first file collided. |
| `no_lesson_file` | `success` | The plan directory **genuinely resolved, was scanned, and held no** `lesson-*.md`. The benign zero. |
| `plan_dir_unresolved` | `error` | The plan directory could not be resolved under the main-anchored plans root, so it was **never scanned**. The non-benign zero. |

`action` and `status` pair exactly as the table shows; `restored` never rides with `status: error`. That is what `restore_incomplete` buys: an aborted move used to report `action: restored` with `restored_count: 0`, so a consumer branching on the closed vocabulary — which this contract instructs callers to do rather than re-listing literals — concluded at least one lesson had landed when none had.

An **absent** plan directory is deliberately `plan_dir_unresolved`, not `no_lesson_file`: "the plan never existed" and "I looked in the wrong store" are indistinguishable from inside the verb, and reporting either as a verified-empty plan is exactly the fail-open this contract closes. `store_resolution` sub-discriminates the two ways it happens — `unresolved` means a required store itself was unreachable, while `main_anchored` / `override` means the store resolved but does not hold that plan directory.

The verb needs **both** the plans root and the lessons corpus, so a could-not-look return always reports the resolution of the store that actually **failed**, never a sibling that happened to resolve — and `unresolved_store` names which of the two it was (`plans` / `lessons`, empty when both resolved). The distinction is load-bearing because `store_resolution` is the field this contract tells consumers to branch on: emitting the plans store's resolved value while the *corpus* was the unreachable one reads as "the corpus is fine, the plan is simply absent" to a caller that never reached the corpus at all. `list-stalled` states the same rule for its own `store_unresolved` return; the two surfaces answer it identically.

A pre-existing destination file is never clobbered: the move fails fast with `destination_exists` under `action: restore_incomplete`, and any lessons restored before the collision remain in the corpus and are reported in `restored_lessons`.

Only a **regular, non-symlinked file** is ever moved. Each carried lesson id is derived from the matched filename, never from a resolved path — a symlink resolves out of the plan directory, so an id read off the resolution names the link's *target* rather than the file the plan actually carries. A carried entry that is a symlink or not a regular file fails fast with `unsafe_source` under `action: restore_incomplete`, because moving it would relocate whatever the link points at out of its own location, or plant a directory in the corpus where every later reader expects a markdown file. Testing the resolved parent alone would not catch either: it rejects only entries that escape *out* of the plan directory, while a link or directory resolving back inside it passes untouched — so the entry's **type** is what is tested. `manage-status`'s pre-deletion carry-back applies the identical predicate, reporting it as a `skipped[]` row with `reason: unsafe_source`.

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons restore-from-plan \
  --plan-id EXAMPLE-PLAN
```

**Parameters**:
- `--plan-id` (required): Plan directory under the main-anchored `.plan/local/plans/` to scan

**Output** (TOON) — every field below is emitted on every branch, success and error alike:
```toon
status: success
plan_id: EXAMPLE-PLAN
action: restored
store_resolution: main_anchored
plans_root: /abs/path/to/.plan/local/plans
unresolved_store: ""
restored_count: 1
restored_lessons:
  - lesson_id: 2025-12-02-15-001
    source: /abs/path/to/.plan/local/plans/EXAMPLE-PLAN/lesson-2025-12-02-15-001.md
    destination: /abs/path/to/.plan/local/lessons-learned/2025-12-02-15-001.md
```

#### Stalled-lesson lifecycle gap

`convert-to-plan` is the move that takes a lesson out of the active corpus and into a plan directory; `restore-from-plan` is its inverse, returning the relocated lesson back to `.plan/local/lessons-learned/`. When a plan stalls or is abandoned before reaching a terminal state, the relocated lesson is trapped at the plan-dir root and never resurfaces. `list-stalled` is the detection half of closing that gap — it identifies every trapped lesson; `restore-from-plan` is the remediation half that frees it. The `Action: cleanup` workflow consumes both as a paired scan-and-restore pass.

Closing the gap requires both verbs to distinguish their zeros, because the pass is only as trustworthy as its weakest report: a `list-stalled` that could not read the store, or a `restore-from-plan` that reports an unreachable plan directory as lesson-free, makes the paired pass emit a confident "nothing to do" over a corpus it never saw. Both verbs therefore carry the `store_resolution` discriminator, and the cleanup workflow branches on it rather than on the counts alone. The store-resolution population and its per-site dispositions are enumerated in [`standards/cwd-keyed-store-resolution-audit.md`](standards/cwd-keyed-store-resolution-audit.md).

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
| `add` | `--component --category --title [--bundle] [--rule]` | Allocate a new lesson file and return its absolute `path`. Caller populates body via `set-body`. For `--category arch-constraint`, `--rule` is required and a recurring rule reinforces the existing lesson instead. |
| `set-body` | `--lesson-id (--file PATH \| --content STRING)` | Populate or replace lesson body. `--file` is the canonical form (shell-safe for arbitrary markdown); `--content` is the secondary form for tiny single-line payloads only. |
| `set-title` | `--lesson-id --title` | Rewrite the H1 title in place. Preserves frontmatter and body; idempotent; works on `active` and `superseded` lessons. Fenced-code-block aware. |
| `update` | `--lesson-id [--component] [--category]` | Update lesson metadata |
| `get` | `--lesson-id` | Get single lesson |
| `list` | `[--component] [--category] [--full]` | List with filtering. `--full` includes lesson body content. |
| `consult` | `--plan-id [--max-per-component N]` | Read-only prospective query for `phase-3-outline`: derive the plan's `{bundle}:{skill}` component set from its `solution_outline.md` affected files and surface every active lesson whose `component` exactly equals one of them. Writes the machine record `work/lessons-consult.toon`; mutates no lesson, alters no deliverable, emits no finding. A binding `--max-per-component` (default 25) always discloses `truncated: true` plus the untruncated `total_matched`. |
| `aggregate` | `[--top-n N]` | Read-only classifier: group active lessons that would land in one plan. Returns groups + headline commands. See [`references/aggregate-analysis.md`](references/aggregate-analysis.md). |
| `from-error` | `--context` | Create from JSON error context (programmatic; body synthesized from context) |
| `convert-to-plan` | `--lesson-id --plan-id` | Move lesson into a plan directory as `lesson-{id}.md`. This is the move-semantics replacement for marking a lesson "applied". |
| `remove` | `--lesson-id --reason --coverage-verdict [--covering-clause] [--covering-input] [--force]` | Delete a lesson and write a tombstone. `--coverage-verdict` is required with no default; `completely_covered` additionally requires both evidence flags, and all supplied values are recorded on the tombstone. See [Retirement evidence](#retirement-evidence-the-two-key-remove-path). |
| `supersede` | `--lesson-id --by --reason` | Mark a lesson superseded by a canonical lesson: merge the source body into the canonical, write a tombstone carrying `superseded_by`, and replace the source body with a `[SUPERSEDED]` redirect stub. |
| `restore-from-plan` | `--plan-id` | Inverse of `convert-to-plan`: move the relocated `lesson-*.md` back from a plan directory to the active corpus (`.plan/local/lessons-learned/`). Run on stall/abandon so a stranded lesson resurfaces. Reports a four-value `action` — enumerated in full under [restore-from-plan](#restore-from-plan), the single home for the value set — so an unreachable plan directory is never reported as a lesson-free one, and an aborted move is never reported as a completed one. |
| `cleanup-superseded` | `[--lesson-id ID ...] \| [--retention-days N] [--dry-run]` | Prune superseded `.md` stubs while preserving tombstones. Age-filtered when `--retention-days` (falls back to `system.retention.lessons_superseded_days`, hard fallback 7); explicit when `--lesson-id` is repeated. |
| `retire-quiet` | `[--quiet-days N] [--dry-run]` | Retire-on-quiet for `arch-constraint` lessons: tombstone + unlink every active arch-constraint lesson whose `last_seen` is at least the quiet window old. Window falls back to `system.retention.arch_constraint_quiet_days`, then a hard fallback. |
| `list-stalled` | (none) | Read-only scanner: report plans holding a `lesson-*.md` that is stranded in a non-terminal `5-execute`/`6-finalize` state. Population is derived from the observable lesson file, NOT from `metadata.plan_source`. Returns `stalled_count` with per-plan `restore_command`, the separately-counted `duplicate_lessons` (a carried id already in the corpus), `unclassifiable_plans` (unreadable `status.json`), and the `store_resolution` / `plans_root_state` / `unresolved_store` discriminators that say which kind of zero a zero is — reporting the resolution of the store that actually failed, never a sibling that happened to resolve. Never mutates lesson files or plan dirs. |
| `auto-suggest` | `--plan-id [--max-suggestions N] [--no-emit]` | Recipe-registry matcher for phase-1-init Step 5c. Scans the live recipe registry (`manage-config list-recipes`) and returns up to `--max-suggestions` recipes (default 3) ordered by deterministic confidence — keyword overlap (request narrative ∩ recipe description) + domain alignment + scope alignment. Each suggestion is also written as a plan-scoped `tip` finding (`artifacts/findings/tip.jsonl`) so the orchestrator can surface them in the audit log; pass `--no-emit` to inspect without writing findings. No LLM dispatch — the matcher is pure regex + set algebra. Falls through to the existing Step 5c LLM path when no recipe clears the 0.35 confidence floor. |

---

## Categories

| Category | When to Use |
|----------|-------------|
| `bug` | Script is broken or produces wrong results |
| `improvement` | Script works but could be better |
| `anti-pattern` | Script was misused or documentation unclear |
| `arch-constraint` | Recurring architectural-boundary violation from `arch-gate`. Deduped by `rule` identity (reinforce-on-recurrence); retired on quiet via `retire-quiet`. NOT promote-to-skill. See `standards/file-format.md`. |

---

## Error Responses

> See [manage-contract.md](../ref-workflow-architecture/standards/manage-contract.md) for the standard error response format.

| Error Code | Cause |
|------------|-------|
| `not_found` | Lesson ID doesn't exist (get, update, set-body, convert-to-plan) |
| `plan_dir_unresolved` | `restore-from-plan` **never scanned** for lesson files. Either the named plan directory could not be resolved under the main-anchored plans root, **or** the main-anchored lessons corpus itself did not resolve so there was nowhere to restore into. Deliberately distinct from `action: no_lesson_file`, which asserts the directory WAS scanned and held none — reporting an unreachable directory as lesson-free is the fail-open this code closes. `store_resolution` says which way it happened: `unresolved` (a required store was unreachable) versus a resolved store that does not hold that plan; on the unreachable branch it is always the resolution of the store that **failed**, and `unresolved_store` names which one (`plans` / `lessons`) |
| `store_unresolved` | `list-stalled` could not resolve the main-anchored plans root **or** lessons corpus, so no plan directory was ever scanned. `unresolved_store` names which of the two failed, `store_resolution` is that store's `unresolved` — never a sibling's resolved value — and `plans_root_state` is `unknown`. Distinct from the non-faulting `plans_root_state: missing` (the store resolved, but the plans root does not exist) and from `plans_root_state: present` with `stalled_count: 0` (the scan looked and found nothing) |
| `destination_exists` | `restore-from-plan` refused to clobber an existing corpus file for a restored lesson id; reported under `action: restore_incomplete`, never `restored`. Any lessons moved before the collision remain restored and are reported in `restored_lessons`, so `restored_count` may be `0` (first-file collision) or non-zero. `list-stalled` surfaces the same condition ahead of time as a `duplicate_lessons[]` row |
| `invalid_id` | `restore-from-plan` rejected the supplied `--plan-id` **before any path resolution**: the identifier carries a path separator or a `..` traversal sequence. Nothing was resolved and nothing was scanned, so it rides `action: plan_dir_unresolved` |
| `unsafe_source` | `restore-from-plan` refused to move a carried `lesson-*.md` that is a **symlink or not a regular file** (a directory, FIFO, or device node). Moving a link would relocate whatever it points AT — an arbitrary file outside the plan directory, removed from its own location — and moving a directory would leave a directory where every later reader expects a markdown file, so each subsequent read of that id raises `IsADirectoryError`. Rides `action: restore_incomplete`; lessons moved before the guard fired remain restored and are reported in `restored_lessons`. Distinct from `path_traversal`, which tests where a path *resolves* — this one tests what the entry *is*, and a link resolving back inside the plan directory passes the traversal guard untouched. The `manage-status` pre-deletion carry-back applies the same predicate as a `skipped[]` row with `reason: unsafe_source` |
| `path_traversal` | A resolved path escaped its intended parent directory. Reachable at two points, distinguished by the `action` it rides: **pre-scan** (`action: plan_dir_unresolved`), when the plan directory resolves outside the main-anchored plans root — nothing was scanned; and **mid-loop** (`action: restore_incomplete`), when a carried lesson's derived id or its corpus destination resolves outside its parent — lessons moved before the guard fired remain restored and are reported in `restored_lessons` |
| `copy_failed` | `convert-to-plan` failed to copy the lesson to the plan directory (I/O error or read-back content mismatch); source lesson is left intact, no partial artifact survives |
| `invalid_category` | Category not in: bug, improvement, anti-pattern, arch-constraint |
| `missing_rule` | `add --category arch-constraint` invoked without the required `--rule` dedup key |
| `invalid_context` | JSON context parsing failed (from-error) |
| `invalid_input` | `set-body` invoked without exactly one of `--file` / `--content`, or both supplied |
| `file_not_found` | `set-body --file PATH` points at a non-existent path or a non-regular file (directory, broken symlink, special file) |
| `file_read_error` | `set-body --file PATH` failed with an `OSError` while reading (permission denied, I/O error, etc.) |
| `malformed_lesson` | `set-body` target lesson file is missing its metadata header / title structure |
| `missing_required` | Required parameter missing |
| `missing_coverage_verdict` | `remove` invoked without a valid `--coverage-verdict`. Unreachable from the CLI (argparse rejects an omitted or out-of-vocabulary verdict at parse time); this is the structural backstop for direct programmatic invocation of `cmd_remove`. The lesson is left in place |
| `missing_coverage_evidence` | `remove --coverage-verdict completely_covered` invoked without `--covering-clause` and/or `--covering-input` (a whitespace-only value counts as missing). The CLI rejects this at argparse (exit 2); this code is the handler-side backstop. `missing_flags[]` names the absent flags, and the lesson is left in place |
| `wrong_store` | `add` / `from-error` refused: the component **carries a bundle prefix** and the resolved main-anchored lessons store repo does not own that bundle (the prefix segment of `--component`/context `component` has no `marketplace/bundles/{bundle}` directory in that repo). A prefix-less project-local component names no bundle and never reaches this refusal. Bypass with `--allow-foreign-store`. Skipped under test overrides (`PLAN_BASE_DIR`) |
| `invalid_component` | `add` / `from-error` refused: the component does not match the canonical component shape (`^[a-z0-9-]+(:[a-z0-9-]+)*$`). Distinct from `wrong_store` — the value is not a well-formed component at all, so no ownership claim is made about it. Primarily reachable via `from-error`, whose context `component` comes from untrusted JSON and bypasses the argparse validator. The shape check precedes `--allow-foreign-store`, so the override cannot bypass it |

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
  --component COMPONENT --category {bug|improvement|anti-pattern|arch-constraint} --title TEXT \
  [--bundle BUNDLE] [--rule RULE] [--allow-foreign-store]
```

`--rule` is required when `--category arch-constraint` (the dedup key); ignored for other categories.
`--allow-foreign-store` bypasses the cross-repo wrong-store guard, which applies only to a component carrying a bundle prefix — a prefix-less project-local component files without the flag (see [Error Responses](#error-responses) → `wrong_store`).

### update

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons update \
  --lesson-id LESSON_ID \
  [--component COMPONENT] [--category {bug|improvement|anti-pattern|arch-constraint}]
```

### get

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons get \
  --lesson-id LESSON_ID
```

### list

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons list \
  [--component COMPONENT] [--category {bug|improvement|anti-pattern|arch-constraint}] \
  [--status {active|superseded|removed|all}] [--full]
```

### consult

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons consult \
  --plan-id PLAN_ID [--max-per-component N]
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
  --context JSON [--allow-foreign-store]
```

`--allow-foreign-store` bypasses the cross-repo wrong-store guard, which applies only to a component carrying a bundle prefix — a prefix-less component, including the `unknown` default applied when the context supplies none, files without the flag (see [Error Responses](#error-responses) → `wrong_store`). A context `component` failing the canonical component shape is rejected with `invalid_component` before the flag is consulted.

### remove

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons remove \
  --lesson-id LESSON_ID --reason TEXT \
  --coverage-verdict {completely_covered|redundant|superseded|obsolete} \
  [--covering-clause TEXT] [--covering-input TEXT] [--force]
```

`--coverage-verdict` is **required and has no default** — an unstated verdict is a rejection, never an assumption. `--covering-clause` and `--covering-input` are **required whenever the verdict is `completely_covered`**; supplying that verdict without BOTH is an argparse-level rejection (usage on stderr, exit 2) and the lesson is left in place. The three weaker verdicts (`redundant`, `superseded`, `obsolete`) need no evidence pair. See [Retirement evidence](#retirement-evidence-the-two-key-remove-path) for the contract and [Error Responses](#error-responses) → `missing_coverage_verdict` / `missing_coverage_evidence`.

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

### retire-quiet

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons retire-quiet \
  [--quiet-days N] [--dry-run]
```

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
| `phase-3-outline` | consult | Prospective risk surfacing at outline time — surface the active lessons naming the components the plan is about to edit, for the author to judge |
| `phase-6-finalize` | list | Query unapplied lessons (those still in `.plan/local/lessons-learned/`) for promotion |

## Related

- `manage-findings` — Findings promoted to lessons at 6-finalize
- `manage-run-config` — Complementary global persistence (execution state)
