# Lesson-Creation Policy: The Three-Gate Sequence

The canonical, ordered precondition sequence that **every** lesson-creating caller MUST run before allocating a new lesson. Lesson creation is conditional, not unconditional: a new lesson file is allocated only when all three gates clear in order.

## Purpose and Applicability

This standard is the single source of truth for the "should this observation become a *new* lesson?" decision. It applies to **any caller that records a lesson-learned**, not only the finalize step. Concrete callers re-pointed at this policy:

- `plan-marshall:phase-6-finalize` — `lessons-capture` workflow.
- `plan-marshall:phase-6-finalize` — `lessons-integration` conceptual standard.
- `plan-marshall:execute-task` — Record-Lessons step.
- `plan-marshall:plan-retrospective` — lessons-proposal dedup gate.
- `plan-marshall:manage-findings` — Promotion Workflow (finding → lesson).
- `pm-plugin-development:plugin-task-plan` — Record-Issues-as-Lessons step.
- `plan-marshall:phase-4-plan` — Record-Issues-as-Lessons step and the lesson-ID-drift recovery create-path.

A caller running this sequence must execute the gates **in order** and stop at the first gate that resolves the observation without allocating a new lesson. Gate 2 runs only when Gate 1 returns `new`; Gate 3 runs only when Gates 1 and 2 both clear.

```text
observation to record
        │
        ▼
   ┌─────────┐   merge_into / already_closed
   │ GATE 1  │ ─────────────────────────────▶ resolve in the existing lesson, STOP
   │ Dedup   │
   └────┬────┘
        │ new
        ▼
   ┌─────────┐   covering active plan found
   │ GATE 2  │ ─────────────────────────────▶ fold into that plan, STOP
   │ Active  │
   │ plan    │
   └────┬────┘
        │ no covering plan
        ▼
   ┌─────────┐
   │ GATE 3  │ ─────────────────────────────▶ allocate a NEW lesson
   │ Create  │
   └─────────┘
```

## Gate 1 — Dedup Gate

Before anything else, classify the observation against the existing lessons corpus. Load the corpus and classify each candidate using the shared single-candidate classifier — do **not** restate or duplicate its heuristics here:

> See [`../references/dedup-analysis.md`](../references/dedup-analysis.md) for the corpus load (`manage-lessons list --full`), the `new` / `merge_into` / `already_closed` classification rules, the component/root-cause/category heuristics, and the per-candidate output shape.

Act on the classifier's result:

- **`new`** — no existing lesson covers this component + root cause. Proceed to **Gate 2**.
- **`merge_into`** — an existing lesson shares the same component and root cause. Do **not** allocate a new lesson. Extend the target lesson instead:
  - Append a new section to the target file (`.plan/local/lessons-learned/{target_id}.md`) with heading `## Recurrence — YYYY-MM-DD ({plan_id})`, capturing the new evidence.
  - Broaden the target's scope and update its body where the recurrence widens the lesson's applicability.
  - Stop here — no Gate 2, no Gate 3.
- **`already_closed`** — an existing lesson filed the finding and the fix has since landed (positive evidence required; silence is not evidence). Follow the classifier's closed-lesson contract: skip the add and delete the stale lesson file at `.plan/local/lessons-learned/{target_id}.md`, subject to the caller-contract rules below. Stop here.

## Gate 2 — Active-Plan Gate

Runs **only** when Gate 1 returned `new`. The purpose is to avoid filing a standalone lesson for a problem an in-flight plan already exists to solve.

Enumerate the active plans:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status list
```

For each `new`-classified candidate, compare the candidate's **component + root cause** against the request scope of each active plan. When a covering plan exists — an active plan whose request scope already encompasses the candidate's component and root cause — do **not** file a standalone lesson. Instead, fold the observation into that plan (e.g., as additional context, a finding, or a scope note on the covering plan), so the work is addressed inside the plan that already owns it. Stop here.

When no active plan covers the candidate, proceed to **Gate 3**.

## Gate 3 — Create Gate

Runs **only** when Gates 1 and 2 both clear (Gate 1 returned `new` AND Gate 2 found no covering plan). File the lesson using the canonical path-allocate flow:

1. `add` — allocate the lesson file and capture the returned `id` / `path`.
2. `Write {plan_dir}/work/lesson-body-{id}.md` — write the body markdown directly to a plan-scoped staging file with the Write tool (bypasses shell quoting; supports arbitrary markdown).
3. `set-body --lesson-id {id} --file {path}` — apply the staged body to the lesson file.

> See [`../SKILL.md`](../SKILL.md) § "Path-allocate flow (canonical)" and Canonical invocations → `add` / `set-body` for the authoritative command surface and parameters.

## Caller-Contract Note

The gate sequence above defines *what* to check; the existing per-caller contracts in [`../references/dedup-analysis.md`](../references/dedup-analysis.md) § "Caller contracts" define *who confirms* the resulting action. Those contracts are preserved by this policy:

- **Finalize-step mode** (`plan-marshall:plan-retrospective` invoked inside `phase-6-finalize`): executes `new` adds (Gate 3) automatically and `merge_into` appends (Gate 1) automatically.
- **`already_closed` deletion**: always requires the user's confirmation, because deleting a lesson file is destructive — in every mode.
- **User-invocable or archived mode**: asks the user per candidate before any recording, append, or deletion.
