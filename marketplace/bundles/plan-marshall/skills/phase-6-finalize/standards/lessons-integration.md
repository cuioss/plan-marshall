# Lessons Integration

Conceptual companion to `lessons-capture.md`. Describes WHY lessons capture exists and the criteria for recording or skipping a lesson. The mechanical executor lives in `standards/lessons-capture.md`; this document carries no dispatch logic of its own.

## Purpose

At plan completion, notable patterns, decisions, and improvements discovered during implementation should be recorded for future reference.

## When to Capture Lessons

Activation is decided by the manifest, not by this document. When `lessons-capture` is in `manifest.phase_6.steps`, the dispatcher runs the `lessons-capture` standards document on every Phase 6 entry. The composer in `manage-execution-manifest:compose` includes `lessons-capture` for every change-type that produces non-trivial work; the only documented exclusion is the rule-1 early-terminate analysis path.

Within an active `lessons-capture` run, the agent applies the criteria below to decide whether to allocate a lesson file or record `no lessons recorded`. This is content judgement, not step activation.

## Lesson Categories

| Category | Description | Examples |
|----------|-------------|----------|
| `bug` | Issues found and fixed | Build failures, edge cases |
| `improvement` | Better approaches discovered | Refactoring patterns, tool usage |
| `anti-pattern` | Patterns to avoid | Code smells, workflow issues |

## Automatic Lesson Detection

Review the plan's work-log for lesson candidates:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  read --plan-id {plan_id} --type work
```

**Look for**:
- `[ERROR]` entries that were resolved
- `[DECISION]` entries with non-obvious choices
- Repeated patterns across multiple tasks

## Recording Lessons

For each notable finding, follow the two-step path-allocate flow (the single supported API — there is no `--detail` inline form):

### Step A — Allocate the lesson file

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons add \
  --component {component_identifier} \
  --category {bug|improvement|anti-pattern} \
  --title "{concise_summary}"
```

### Step B — Write the body to the returned path

Parse `path` from the TOON output of Step A and write the detailed context and resolution directly to that path via the Write tool. Bodies may contain arbitrary markdown (including `##` sections and code fences) because they never pass through a shell argument.

**Component identifier** follows the pattern:
- Skills: `{bundle}:{skill-name}` (e.g., `pm-dev-java:java-core`)
- Scripts: `{bundle}:{skill}:{script}` (e.g., `plan-marshall:manage-tasks:manage-tasks`)
- Build: `{build-system}` (e.g., `maven`, `npm`)

## Recording Criteria

**Record a lesson when**:
- The solution required significant investigation
- The pattern will likely recur in future plans
- Team discussion or external research was needed
- A workaround was applied (document why)

**Don't record when**:
- Standard procedure was followed
- The issue was trivial and obvious
- The finding is project-specific (won't apply elsewhere)

## Example: Recording Bug Lesson

Step A — allocate:

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons add \
  --component "plan-marshall:manage-tasks:manage-tasks" \
  --category bug \
  --title "Shell metacharacters in verification commands need quoting"
```

Step B — Write tool appends the following body to the returned path:

> When verification commands contain pipes or wildcards, they must be quoted in HEREDOC to prevent shell expansion during task creation.

## Example: Recording Improvement

Step A — allocate:

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons add \
  --component "pm-dev-java:java-core" \
  --category improvement \
  --title "Use constructor injection over field injection for CDI beans"
```

Step B — Write tool appends the following body to the returned path:

> Constructor injection makes dependencies explicit and testable. Field injection hides dependencies and makes unit testing harder.

## Advisory Nature

Lessons capture is **advisory only** at the content level:
- Does not require user interaction
- A timeout on the agent (5-minute budget per the SKILL.md Step 3 dispatch wrapper) records `outcome=failed` but does not block subsequent finalize steps

## Logging

Log lesson capture:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[ARTIFACT] (plan-marshall:phase-6-finalize) Captured {count} lessons"
```

## Related

- `plan-marshall:manage-lessons` - Lessons storage and query
