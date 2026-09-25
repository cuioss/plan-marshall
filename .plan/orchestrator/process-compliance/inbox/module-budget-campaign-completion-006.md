envelope_version=1
sender_type=plan
sender_id=module-budget-campaign-completion
epic=process-compliance
kind=finding
created=2026-09-25T13:55:00Z
revision=1

# Process-rule issue: finalize dispatch templates forward an ABSOLUTE `WORKTREE`, but the execution-context contract mandates repo-relative — every dispatched finalize step is refused

Reporter: plan `module-budget-campaign-completion`, `default:finalize-step-simplify` dispatch.

## Observation

`phase-6-finalize/SKILL.md` Step 0 resolves `{worktree_path}` as an **absolute** path
(`status.metadata.worktree_path`, logged verbatim as
`worktree_path=/home/oliver/git/plan-marshall/.plan/local/worktrees/module-budget-campaign-completion`),
and every dispatch template in the document then forwards it unchanged
(`WORKTREE: {worktree_path}` — Step 3 items 5, and the DISPATCHED project/skill-step template).

The `execution-context` agent contract declares the opposite:

> `WORKTREE` | Yes | Repo-relative working-directory path — the active worktree path when a
> worktree is in use, or the literal `.` for the main checkout. **NEVER absolute.**

Dispatching the absolute value is refused by the agent before any workflow step runs:

```
status: error
display_detail: "execution-context: WORKTREE must be a repo-relative path"
error: contract_violation
component: "plan-marshall:execution-context"
missing_field: "invalid WORKTREE"
```

Re-dispatching the same step with `WORKTREE: .plan/local/worktrees/module-budget-campaign-completion`
ran to completion. So the refusal is real and the absolute form is wrong, not merely
discouraged.

## Why this is a process defect, not a caller slip

The absolute form is not something an orchestrator chose — it is what the
documented sequence produces. Step 0 is the sole resolver, every standards document
inherits `{worktree_path}` from it, and the template interpolates it verbatim. An
orchestrator that follows the workflow verbatim generates a contract-violating prompt on
**every** dispatched step, which is the majority of the pipeline. The defect is the
mismatch between two authoritative surfaces, and it must be closed in the documents —
not worked around per dispatch.

## Sibling (same family, must be closed in the same change)

`plan-marshall/workflow/execution.md` § "Orchestrator cwd-pinning (phase-5+)" asserts the
opposite contract for the same field:

> The dispatched subagent **inherits the orchestrator's pinned cwd** … it does NOT start
> at the repo root and does NOT need a worktree path forwarded for `.plan/` resolution,
> which is cwd-relative; the `WORKTREE` prompt-body field is the never-edit-main-checkout
> salience reminder, not a path-routing mechanism.

The agent contract says the opposite on both counts: `WORKTREE` is **required** (missing →
error TOON) and is **authoritative** ("Bind every Edit/Write/Read tool call against the
`WORKTREE` value verbatim … Do NOT re-resolve"). Both statements cannot hold at once. The
agent contract is the one the runtime enforces, so `execution.md`'s claim is the stale one.

## Consequence if unfixed

- Each dispatched finalize step burns one envelope before failing, or (worse) a caller
  "fixes" it by dropping the field, which trips the missing-field error instead.
- The failure is `status: error` with a `component` name, so it is legible — but it is
  invisible to the quality gate, so it never gets fixed by CI.

## Evidence

- Refusal: the `finalize-step-simplify` dispatch at 2026-09-25T13:47Z.
- Same dispatch with the repo-relative value completed (`status: done`, 2 edits).
- Agent contract: `~/.config/opencode/agents/execution-context-level-5.md:26` (generated
  from the tree source; the clause is identical across all `execution-context-{level}`
  variants and both reader variants).
- Note for reproduction: the first dispatch of the session
  (`project:finalize-step-lessons-housekeeping`, same absolute `WORKTREE`) did **not** trip
  the validation. The validation is therefore not deterministic across steps, which is a
  second-order symptom of the same ambiguity and should be characterised alongside the fix.
