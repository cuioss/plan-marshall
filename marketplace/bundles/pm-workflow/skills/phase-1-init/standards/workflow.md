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
│   6. Initialize references.toon (branch only)       │
│   7. Detect domain from task analysis               │
│   8. Create status.toon with phases                 │
│   9. Create config.toon with domain                 │
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
| Initializes references.toon | Execute implementation |
| Detects domain | Skip to execute phase |
| Creates config.toon | |
| Creates status.toon | |
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

- Fetched via `manage-lessons-learned` skill
- Extracts: title, category, component, detail, related
- Context section populated with lesson metadata

### Issue URL
```
issue: "https://github.com/org/repo/issues/123"
```

- Fetched via `gh issue view`
- Extracts: title, body, labels, milestone, assignees
- Context section populated with issue metadata

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
- [ ] Exactly one source provided (description, lesson_id, OR issue)
- [ ] If lesson_id: lesson exists and is readable
- [ ] If issue: issue URL valid and accessible
- [ ] Plan ID format: kebab-case, max 50 chars

### Output Validation
- [ ] Plan directory created (via manage-files create-or-reference)
- [ ] request.md created with complete original input
- [ ] references.toon created with branch
- [ ] status.toon created with phases
- [ ] config.toon created with domain
- [ ] Work-log entry written
- [ ] Phase transitioned to refine
- [ ] plan_id returned

## Error Handling

### Invalid Lesson ID
```toon
status: error
error: invalid_lesson
message: Lesson not found: {lesson_id}
recovery: Check lesson ID with manage-lessons-learned list
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
| `pm-workflow:manage-plan-documents` | Write request.md (typed document) |
| `pm-workflow:manage-files` | Create/reference plan directory |
| `pm-workflow:manage-references` | Initialize references |
| `plan-marshall:manage-logging:manage-log` | Log creation |
| `plan-marshall:manage-lessons` | Read lesson content |

### Complete Initialization

The plan-init agent handles complete initialization:
1. Create plan directory and request.md
2. Initialize references.toon with branch
3. Detect domain from task analysis
4. Create status.toon with phases
5. Create config.toon with domain
6. Transition to refine phase

**Note**: Goals and tasks are NOT created during init. That's the refine phase.
