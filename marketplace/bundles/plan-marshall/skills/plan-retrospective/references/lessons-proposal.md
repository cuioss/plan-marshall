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

## Gate sequence (required before recording)

Before any proposal is recorded, run the canonical three-gate lesson-creation policy in `plan-marshall:manage-lessons:standards/lesson-creation-policy.md` — Gate 1 (dedup), Gate 2 (active-plan check), Gate 3 (create). Do not restate the gate mechanics; this section names the per-candidate flow the policy resolves to.

### Gate 1 — Dedup

Classify each proposal per `plan-marshall:manage-lessons:references/dedup-analysis.md`. Load the full existing lessons corpus via `manage-lessons list --full` and compare each candidate by `component` + root cause.

- **`new`** → proceed to Gate 2.
- **`merge_into`** → skip the add; `Edit` the target lesson file at `.plan/local/lessons-learned/{target_id}.md` to append a `## Recurrence — YYYY-MM-DD ({plan_id})` section with the candidate's body content (Context, Root cause, Evidence at minimum).
- **`already_closed`** → skip both add and append; record the `target_id` in the retrospective report's "Proposed Lessons" section as `"Observed again but already closed by lesson {target_id}"`; delete the stale lesson file at `.plan/local/lessons-learned/{target_id}.md` (requires user confirmation in finalize-step mode because deletion is destructive).

### Gate 2 — Active-plan check

Runs only for candidates Gate 1 classified `new`. Enumerate the active plans via `manage-status list` and compare each `new` candidate's `component` + root cause against each active plan's request scope. When a covering active plan exists, do NOT file a standalone lesson — fold the observation into that plan and record it in the retrospective report's "Proposed Lessons" section as `"Folded into active plan {plan_id}"`. When no active plan covers the candidate, proceed to Gate 3.

### Gate 3 — Create

Runs only when Gates 1 and 2 both clear. Record the lesson via `manage-lessons add --component {c} --category {cat} --title "{title}"` and `Write` the body.

Caller-specific behavior (per `dedup-analysis.md` Caller contracts): finalize-step mode executes `new` adds and `merge_into` appends automatically, but `already_closed` always requires user confirmation because deletion is destructive. User-invocable mode asks per candidate.

## Finalize-step Flow

Only `confidence: high` proposals are auto-recorded. `medium` proposals are included in the report section but not recorded. This preserves the bar: lessons represent findings the retrospective is confident about. All recording is gated by the Gate sequence above — only candidates that clear Gate 1 (`new`) and Gate 2 (no covering active plan) reach `manage-lessons add`.

## Out of Scope

- Updating skill documentation — lessons propose changes; applying them belongs to `plugin-apply-lessons-learned`.

## Persistence

After synthesizing the TOON fragment per the shape documented above, the orchestrator writes the fragment to `work/fragment-lessons-proposal.toon` via the `Write` tool and registers it with the bundle:

```bash
python3 .plan/execute-script.py plan-marshall:plan-retrospective:collect-fragments add \
  --plan-id {plan_id} --aspect lessons-proposal --fragment-file work/fragment-lessons-proposal.toon
```

`compile-report run --fragments-file` consumes the assembled bundle in Step 4 of SKILL.md. The bundle file is auto-deleted on successful report write; on failure it is retained for debugging.
