# Lessons Integration

Conceptual companion to `lessons-capture.md`. Describes WHY lessons capture exists and the criteria for recording or skipping a lesson. The mechanical executor lives in `standards/lessons-capture.md`; this document carries no dispatch logic of its own.

## Exit-code convention for `manage-*` script calls

Every `manage-*` script call in this document carries the following exit-code contract unless a step explicitly states otherwise:

- **`exit_code == 0`**: parse the returned TOON and use the value as the step describes.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

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

Before recording any new lesson, run the canonical before-recording gate sequence in [`../../manage-lessons/standards/lesson-creation-policy.md`](../../manage-lessons/standards/lesson-creation-policy.md): Gate 1 (dedup against the existing corpus), Gate 2 (active-plan check), then Gate 3 (create). That standard is authoritative for the gate mechanics; the two-step path-allocate flow below is Gate 3, reached only when Gates 1 and 2 both clear. When Gate 1 returns `merge_into` / `already_closed` or Gate 2 finds a covering active plan, extend the existing lesson or fold into the plan instead of allocating a new one.

For each notable finding that clears the gates, follow the two-step path-allocate flow (the single supported API — there is no `--detail` inline form):

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
- The finding is a durable informational project fact, NOT a defect plus corrective action — a KNOWLEDGE signal, not an ACTIONABLE one. A lesson captures a defect + a "do X instead of Y" rule; a durable fact (an implementation gotcha, a learned observation, an established convention) belongs in the per-module architecture-hints store, not the lessons corpus. Route it to `architecture enrich` (the ACTIONABLE-vs-KNOWLEDGE partition). The routing mechanics — verb selection, `default`-module rule for cross-cutting facts, no-dual-write — live in [`../workflow/lessons-capture.md`](../workflow/lessons-capture.md) § "Classify each candidate signal: ACTIONABLE vs KNOWLEDGE"; do not duplicate them here.
- A similar lesson already exists — extend it instead (Gate 1 `merge_into`; see the shared policy)
- An active plan already covers the issue — fold the observation into that plan instead of filing a standalone lesson (Gate 2; see the shared policy)

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
