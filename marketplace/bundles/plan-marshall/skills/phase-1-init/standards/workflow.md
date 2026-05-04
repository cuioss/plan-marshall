# Plan Init Workflow

## Init Phase Pattern

The init phase uses a single agent for complete initialization:

```
User Request (description, lesson_id, or issue)
        │
        ▼
┌─────────────────────────────────────────────────────┐
│ PLAN-INIT-AGENT (complete initialization)           │
│                                                     │
│   1. Validate input (exactly one source)            │
│   2. Derive plan_id from input                      │
│   3. Create or reference plan directory             │
│   4. Get task content from source                   │
│   5. Write request.md (preserves original input)    │
│   6. Initialize references.json (branch only)       │
│   7. Detect domain from task analysis               │
│   8. Create status.json with phases                 │
│   9. Store domains in references.json                │
│  10. Transition phase to "refine"                   │
│   OUTPUT: plan_id, domain, next_phase               │
└─────────────────────────────────────────────────────┘
        │
        ▼
    Refine Phase (creates goals and tasks)
```

## Plan Init Responsibilities

| Does | Does NOT |
|------|----------|
| Creates plan directory | Create goals (that's refine phase) |
| Writes request.md | Create tasks (that's refine phase) |
| Initializes references.json (with domains) | Execute implementation |
| Detects domain | Skip to execute phase |
| Creates status.json | |
| Transitions to refine | |

## Input Sources

Plan-init accepts exactly ONE of these inputs:

### Description (Free-form text)
```
description: "Add dark mode toggle to application settings"
```

- Stored verbatim in request.md
- No additional context extraction
- Simplest input type

### Lesson ID
```
lesson_id: "2025-12-02-001"
```

- Fetched via `manage-lessons` skill
- Extracts: title, category, component, detail, related
- Context section populated with lesson metadata
- After ingestion, the lesson file is **moved** out of `lessons-learned/` into the plan directory (Step 5b) — this guarantees the lesson is owned by exactly one plan and prevents duplicate work across re-runs.
- A doc-shaped lesson body triggers the **lesson auto-suggest hook** (Step 5c) which sets `plan_source=recipe` + `recipe_key=lesson_cleanup` in status metadata. See § "Lesson auto-suggest hook" below.

### Issue URL
```
issue: "https://github.com/org/repo/issues/123"
```

- Fetched via `tools-integration-ci:issue-view` operation
- Extracts: title, body, labels, milestone, assignees
- Context section populated with issue metadata

## Lesson auto-suggest hook

**Where**: Step 5c, immediately after Step 5b moves the lesson into the plan directory and immediately before Step 6 initializes references.

**Why**: Most lessons-learned describe small, prescriptive cleanups — fix this wording, add this cross-reference, drop this anti-pattern doc. Routing those through the full refine → outline → Q-Gate → plan pipeline costs minutes of LLM time and produces a heavyweight manifest with `automated-review` and `sonar-roundtrip` steps that are wholly unnecessary for a doc-only change. The auto-suggest hook short-circuits that path by routing doc-shaped lessons through `recipe-lesson-cleanup`, which forces `scope_estimate=surgical` and lets the manifest composer collapse Phase 5 and Phase 6 to the minimum safe set.

**Heuristic** (all three must hold for "doc-shaped"):

1. **No code-touching fences**: body contains no fenced code blocks tagged `python`/`py`/`java`/`js`/`javascript`/`ts`/`typescript`. Markdown, text, bash, and untagged fences are fine.
2. **No primary code-action verb**: the first non-empty line of each `## Directive` (or `## Actions`) section does not start with `test`, `refactor`, `implement`, `add code`, `write code`, or `migrate`.
3. **Has at least one directive**: at least one `## Directive` or `## Actions` heading exists.

**Outcome**:

- **Doc-shaped** → set `plan_source=recipe`, `recipe_key=lesson_cleanup` in status metadata; emit a `Recipe auto-suggested` decision log entry. No prompt — auto-suggest is silent.
- **Code-shaped** → no metadata change; emit an `Auto-suggest declined` decision log entry so the audit trail records the negative result. The plan continues through the normal refine → outline → plan pipeline.

**Override**: The user can override auto-suggest on a subsequent run by passing `--recipe lesson_cleanup` explicitly (which sets the same metadata fields up-front and skips the heuristic), or by editing status metadata directly. The hook never overrides an explicit user choice — when `source == recipe` the hook is skipped entirely.

**Integration with the lesson-conversion path**:

- Step 5b owns the file move (lesson file leaves `lessons-learned/`, lands in `.plan/local/plans/{plan_id}/lesson-{lesson_id}.md`).
- Step 5c owns the routing decision (recipe vs. full pipeline) by reading the file Step 5b just placed.
- Steps 6–11 are unaffected by auto-suggest — they always run regardless of `plan_source`. The recipe routing is consumed downstream by `phase-3-outline` Step 2.5 (loads `recipe-lesson-cleanup` when `recipe_key` is set).

This separation keeps the lesson-conversion mechanics (file ownership) decoupled from the routing policy (which pipeline runs next) — either step can change without breaking the other.

## Plan ID Derivation

| Source | Derivation Rule | Example |
|--------|----------------|---------|
| Description | First 3-5 meaningful words | "add-dark-mode-toggle" |
| Lesson | Prefix + lesson ID | "lesson-2025-12-02-001" |
| Issue | Prefix + issue number | "issue-123" |

Rules:
- Always kebab-case
- Maximum 50 characters
- No special characters except hyphens
- User can override with `--plan-id` parameter

## Existing Plan Handling

When plan directory already exists:

```
AskUserQuestion:
  "Plan 'my-feature' already exists. What would you like to do?"

  Options:
  1. Resume - Continue with existing plan
  2. Replace - Delete and recreate
  3. Rename - Use different plan_id
```

## Validation Criteria

### Input Validation
- Exactly one source provided (description, lesson_id, OR issue)
- If lesson_id: lesson exists and is readable
- If issue: issue URL valid and accessible
- Plan ID format: kebab-case, max 50 chars

### Output Validation
- Plan directory created (via manage-files create-or-reference)
- request.md created with complete original input
- references.json created with branch
- status.json created with phases
- Domains stored in references.json
- Work-log entry written
- Phase transitioned to refine
- plan_id returned

## Error Handling

### Invalid Lesson ID
```toon
status: error
error: invalid_lesson
message: Lesson not found: {lesson_id}
recovery: Check lesson ID with manage-lessons list
```

### Invalid Issue URL
```toon
status: error
error: invalid_issue
message: Issue not found or inaccessible: {issue}
recovery: Verify URL, check permissions
```

### Multiple Sources
```toon
status: error
error: multiple_sources
message: Provide exactly one of: description, lesson_id, issue
recovery: Remove extra parameters
```

### Plan Already Exists (not resumed)
```toon
status: error
error: plan_exists
message: Plan already exists and resume not selected
recovery: Use resume option or provide different plan_id
```

## Integration Points

### Scripts Used

| Script | Purpose |
|--------|---------|
| `plan-marshall:manage-plan-documents` | Write request.md (typed document) |
| `plan-marshall:manage-files` | Create/reference plan directory |
| `plan-marshall:manage-references` | Initialize references |
| `plan-marshall:manage-logging:manage-logging` | Log creation |
| `plan-marshall:manage-lessons` | Read lesson content |

### Complete Initialization

The plan-init agent handles complete initialization:
1. Create plan directory and request.md
2. Initialize references.json with branch
3. Detect domain from task analysis
4. Create status.json with phases
5. Store domains in references.json
6. Transition to refine phase

**Note**: Goals and tasks are NOT created during init. That's the refine phase.
