# Aspect: Lessons Proposal

Synthesizes high-confidence signals from all prior aspects into candidate lessons, formatted for `manage-lessons add`. LLM-driven; consumes the TOON fragments of earlier aspects as input.

## Inputs

All aspect fragments produced in earlier workflow steps, especially:
- `script_failure_analysis` — each failure with category `missing_instruction` or `wrong_parameters` is a strong lesson candidate.
- `permission_prompt_analysis` — each prompt suggests a permission or component-declaration lesson.
- `logging_gap_analysis` — persistent sparseness suggests a skill-update lesson.
- `llm_to_script_opportunities` — high-impact candidates become `improvement` lessons.
- `chat_history_analysis` — user pivots suggest refine-phase lessons.

## Lesson Metadata Rules

- `component`: must be a valid skill/agent/command notation (e.g., `plan-marshall:phase-4-plan`). Use `plan-marshall:plan-retrospective` only when the lesson is about the retrospective itself.
- `category`: one of `bug`, `improvement`, `anti-pattern`.
  - `bug` — the source component is broken or produces incorrect output.
  - `improvement` — the component works but should be enhanced.
  - `anti-pattern` — the component is used wrongly or documentation is unclear.
- `title`: ≤80 characters, no trailing period, actionable phrasing (`"Add retry on 5xx in ci pr view"` — not `"ci pr view fails sometimes"`).

## TOON Fragment Shape

```toon
aspect: lessons_proposal
status: success
plan_id: {plan_id}
proposals[*]{component,category,title,body_preview,confidence,source_aspects}:
  "plan-marshall:phase-4-plan",improvement,"Document --file vs --files parameter distinction","When...",high,["script_failure_analysis"]
  "plan-marshall:plan-retrospective",improvement,"Cache aspect fragments across iterations","When...",medium,["logging_gap_analysis"]
```

## Confidence Levels

| Confidence | Meaning | Action |
|-----------|---------|--------|
| `high` | Multi-aspect evidence, clear fix direction | Auto-record in finalize-step mode; pre-selected in user-invocable mode |
| `medium` | Single-aspect evidence, reasonable fix | User prompt in user-invocable mode; skipped in finalize-step mode |
| `low` | Speculative | NOT surfaced — dropped silently |

## Body Template

Each proposal's body follows this template (written to the lesson file via the Write tool after `manage-lessons add` returns a path):

```markdown
# {title}

## Context

{2-4 sentence description of the observed situation}

## Root cause

{1-2 sentence analysis of why it happened}

## Proposed action

{Concrete fix — script edit, config change, doc update}

## Evidence

- aspect: {aspect_name} — {one-line quote or reference}
- ...
```

## Interactive Flow (user-invocable mode)

For each proposal at `confidence: medium` or `high`, use `AskUserQuestion`:

```
question: "Record proposed lesson: {title}?"
options:
  - "Record"
  - "Skip"
  - "Edit title/body first"
```

When `Record`, call `manage-lessons add --component {c} --category {cat} --title "{title}"` and `Write` the body. When `Edit`, let the user revise title/body, then proceed.

## Finalize-step Flow

Only `confidence: high` proposals are auto-recorded. `medium` proposals are included in the report section but not recorded. This preserves the bar: lessons represent findings the retrospective is confident about.

## Out of Scope

- Reviewing existing lessons for overlap (that is `default:review-knowledge` in finalize).
- Updating skill documentation — lessons propose changes; applying them belongs to `plugin-apply-lessons-learned`.
