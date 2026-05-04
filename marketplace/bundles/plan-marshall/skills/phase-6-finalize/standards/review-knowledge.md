---
name: default:review-knowledge
description: Review existing lessons-learned against plan changes; propose deletes/updates
order: 80
---

# Review Knowledge

Pure executor for the `review-knowledge` finalize step. Reviews existing lessons-learned against the current plan's diff; proposes deletes/updates.

This document carries NO step-activation logic. Activation is controlled by the dispatcher in `phase-6-finalize/SKILL.md` Step 3 and is driven solely by presence of `review-knowledge` in `manifest.phase_6.steps`. When the dispatcher runs this step, the document executes top to bottom — there is no skip-conditional branching at this layer. The composer in `manage-execution-manifest:compose` decides whether `review-knowledge` is part of the manifest for a given plan; this document does not second-guess that decision.

## Inputs

- `{worktree_path}` and `{main_checkout}` have been resolved at Step 0 of `phase-6-finalize/SKILL.md`. Both paths are required: `{worktree_path}` is the execution root for the running plan, and `{main_checkout}` is the read-only anchor used by `ci`/`git`-style calls that must operate outside the worktree.
- The `AskUserQuestion` gate in sub-step 3g forbids agent-mode dispatch. This step MUST run inline in the finalize main context — it is listed alongside `commit-push`, `branch-cleanup`, `record-metrics`, and `archive-plan` as inline-only.

## Execution

### 3a. Log workflow load

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[SKILL] (plan-marshall:phase-6-finalize) Loading review-knowledge workflow"
```

### 3b. Gather plan context

Read the plan's references snapshot and status to obtain the four fields this step needs: `modified_files`, `domains`, `title`, and `change_type`.

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references \
  get-context --plan-id {plan_id}
```

Extract `modified_files`, `domains`, and `title` from the TOON response. `modified_files` is the authoritative list of files touched by the plan — it drives every match score computed in 3c.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status \
  read --plan-id {plan_id}
```

Extract `metadata.change_type` (one of `feature`, `bug-fix`, `refactor`, `verification`, etc.). This value is passed verbatim into the classification prompt in 3e.

### 3c. List and filter lessons

```bash
python3 .plan/execute-script.py plan-marshall:manage-lessons:manage-lessons list --full
```

The `--full` form returns each lesson's full body plus metadata (`component`, `category`, `title`, absolute `path`). For each entry, compute a match score:

- `component == {bundle}:{skill}` for any component touched by the plan (derived from `modified_files` via `marketplace/bundles/{bundle}/skills/{skill}/` prefix matching), OR
- Body substring hit on any entry of `modified_files` (case-sensitive literal match).

Keep every entry that matches either predicate. Drop the rest.

### 3d. Short-circuit when zero survivors

If the survivors from 3c is empty, skip the classification loop and jump directly to Mark Step Complete **Branch B — nothing to review**. Do NOT spawn any classification agents, do NOT present an `AskUserQuestion` gate, do NOT emit the decision log in 3i.

### 3e. Classification loop

For each surviving lesson candidate from 3c, spawn exactly ONE inline `Task` agent using the templated prompt below. The dispatch MUST route through `plan-marshall:classify-knowledge-agent` so the classification call carries the agent's enforcement envelope (verdict-vocabulary validation and output-contract) — any unscoped agent type is not valid for this call. The prompt body is authoritative — every finalize run uses the same instructions verbatim. `{id}` is the lesson identifier (e.g., `lesson-2026-04-17-004`); `{body}` is the full lesson markdown body.

```
subagent_type: plan-marshall:classify-knowledge-agent
prompt: "Classify whether the plan's changes resolve / partially resolve / supersede the following lesson. Return exactly one verdict word and (only for partially_resolved) a revised body.

PLAN TITLE: {plan.title}
PLAN DIFF (modified files): {modified_files joined by ', '}
CHANGE TYPE: {change_type}

CANDIDATE (lesson, id={id}):
{body}

Verdict: one of {resolved, partially_resolved, superseded, unaffected}.
For partially_resolved, append a REVISED BODY section with the rewritten content."
```

Capture each agent's response. Parse the first non-empty line as the verdict word (reject any response whose first line is not one of the four allowed verdicts). For `partially_resolved` responses, capture everything after the literal `REVISED BODY` marker as the revised body.

### 3f. Assemble proposed-action list

Build one entry per non-`unaffected` verdict:

```
{id: {id}, path: {absolute_path}, verdict: {verdict}, action: delete|update, revised_body?: {body}}
```

Action mapping:

- `resolved` -> `action: delete`
- `superseded` -> `action: delete`
- `partially_resolved` -> `action: update` (requires `revised_body`)
- `unaffected` -> dropped (no entry)

### 3g. Batch approval gate

Present the assembled proposal set via a single `AskUserQuestion` call with `multiSelect: true`. Each option summarizes exactly one proposed action, so the user can accept, partially accept, or reject the full batch in one interaction.

Option label format:

- `DELETE lesson {id} — {verdict} by plan` (for `action: delete`)
- `UPDATE lesson {id} — {verdict} (revised body)` (for `action: update`)

Semantics:

- Accepted options (checked by the user) -> carry through to 3h.
- Unchecked options -> dropped; the underlying lesson is preserved unchanged.
- Zero selections (user unchecks everything) -> treat as user declined: skip 3h, skip 3i, jump to Mark Step Complete **Branch C — user declined**.

### 3h. Apply accepted actions

For each accepted entry, apply the action:

**Delete action** — direct file removal:

```bash
rm {absolute_path}
```

Where `{absolute_path}` is the `path` field captured in 3c. This matches the existing "Analyze all lessons" close-action pattern in `workflows/planning.md`.

**Update action** — overwrite the markdown file via the `Write` tool. Preserve the existing metadata header (everything up to and including the `# {title}` line) and replace the body below the title with the revised content returned by the classification agent. Do NOT alter the component, category, or title fields.

### 3i. Log each action

For every applied action (not the unaccepted ones), record a decision log entry:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO --message "(plan-marshall:phase-6-finalize:review-knowledge) {action} lesson {id}: {verdict}"
```

Substitute `{action}` (`deleted` / `updated`), `{id}`, and `{verdict}` verbatim.

## Mark Step Complete

Before returning control to the finalize pipeline, record that this step ran on the live plan so the `phase_steps_complete` handshake invariant is satisfied at phase transition time.

Pass a `--display-detail` value alongside `--outcome done` so the output-template renderer can surface the review outcome. All three branch strings MUST be single-line, plain ASCII, <=80 characters, and carry no trailing period (per `output-template.md` contract).

**Branch A — actions applied** (one or more proposed actions were accepted and applied in 3h). `{N_deleted}` is the count of accepted `delete` actions; `{N_updated}` is the count of accepted `update` actions; `{N_kept}` is the count of proposed actions the user explicitly declined (unchecked options from 3g); `{total}` is the size of the proposal set assembled in 3f.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step review-knowledge --outcome done \
  --display-detail "{N_deleted}d/{N_updated}u/{N_kept}k of {total}"
```

Example: `2d/1u/5k of 8` — 2 deletes applied, 1 update applied, 5 proposals declined, out of 8 total proposals.

**Branch B — nothing to review** (zero survivors after the 3c pre-filter, or the lesson pool was empty). `{N_lessons}` is the total returned by the `list` call in 3c (BEFORE filtering), so the detail reports the size of the pool the pre-filter scanned.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step review-knowledge --outcome done \
  --display-detail "nothing to review ({N_lessons} lessons)"
```

**Branch C — user declined** (the `AskUserQuestion` batch gate in 3g returned zero selections).

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step review-knowledge --outcome done \
  --display-detail "user declined review"
```
