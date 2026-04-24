# Dedup Analysis: Classify Lessons as Close / Merge / Keep-open

Shared procedure used by two callers:

- `plan-marshall:plan-marshall` Action: lessons → Analyze all lessons (post-hoc corpus sweep).
- `plan-marshall:plan-retrospective` Step 5 Propose Lessons (per-plan proposal dedup).

## Inputs

- One or more candidate lessons to classify. Each candidate has `title`, `component`, `category`, and for the retrospective caller also a `body_preview` plus `source_aspects`.
- The full existing lessons corpus — load via:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons list --full
  ```

## Classification

For each candidate, choose exactly one status:

- **`new`** — no existing lesson covers this component + root cause.
  - Action: caller proceeds with `manage-lessons add` and writes the body.

- **`merge_into`** — one or more existing lessons share the same component and same root cause.
  - Action: caller appends evidence to the target instead of creating, via `Edit` on the target file under `.plan/local/lessons-learned/{target_id}.md`. Append a new section with heading `## Recurrence — YYYY-MM-DD (context)`.
  - Record: `target_id` (the ID being merged into) and the appended section heading.

- **`already_closed`** — an existing lesson filed the finding AND the code fix has since landed.
  - Action: caller skips the add AND deletes the now-stale existing lesson file at `.plan/local/lessons-learned/{target_id}.md`.
  - Record: `target_id` in the retrospective report for audit.

## Heuristics

A candidate is `merge_into` when ALL of the following are true against some existing lesson:

- **Component match**: `component` matches exactly, OR the components name the same skill bundle and overlap in surface (e.g. `plan-marshall:phase-5-execute` merges with `plan-marshall:execute-task` if the root cause is the execute-phase loop).
- **Root cause match**: Root cause (not symptom) is the same. Two lessons with matching symptoms but different root causes are separate — do not merge.
- **Category compatibility**: `bug` + `bug` merge; `bug` + `improvement` merge into whichever target already has more evidence; `anti-pattern` does not merge with `bug`.

A candidate is `already_closed` only when the caller has **positive evidence** the fix landed (a commit, a code grep, a test pass). Silence is NOT evidence of fix — assume `merge_into` when uncertain.

## Output shape (per candidate)

```
{candidate_title}:
  status: new | merge_into | already_closed
  target_id: YYYY-MM-DD-HH-NNN     # omit when status=new
  rationale: one-line explanation
```

## Caller contracts

- **Cleanup-side caller** (`plan-marshall:plan-marshall` Action: lessons → Analyze all lessons) emits the full batch and asks the user once via `AskUserQuestion` before executing close/merge actions.
- **Retrospective-side caller — finalize-step mode** (`plan-marshall:plan-retrospective` invoked inside phase-6-finalize) executes `new` adds automatically and `merge_into` appends automatically; `already_closed` always requires the user's confirmation because deletion is destructive.
- **Retrospective-side caller — user-invocable or archived mode** asks the user per candidate before any recording, append, or deletion.
