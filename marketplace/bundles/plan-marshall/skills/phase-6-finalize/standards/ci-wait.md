---
name: default:ci-wait
description: Poll CI to completion and write the completed-CI signal consumed by automated-review
order: 25
---

# CI Wait

Pure executor for the `ci-wait` finalize step. This step polls CI to completion against the freshly-pushed PR branch and writes a completed-CI signal that the downstream `automated-review` step consumes instead of polling CI itself. Splitting CI-wait out of `automated-review` keeps the per-iteration triage budget (900 s / 15 minutes) bounded by comment volume rather than CI queue depth.

This document carries NO step-activation logic. Activation is controlled by the dispatcher in `phase-6-finalize/SKILL.md` Step 3 and is driven solely by presence of `ci-wait` in `manifest.phase_6.steps`. When the dispatcher runs this step, the document executes top to bottom — there is no skip-conditional branching at this layer.

## Timeout Contract

This step runs as a Task agent (`plan-marshall:automated-review-agent`) under a **30-minute (1800 s) per-agent timeout budget** enforced by the SKILL.md Step 3 dispatch loop. The longer budget compared to `automated-review`'s 900 s reflects that CI queue depth — not LLM-side reasoning — dominates wall-clock time during this step. The budget covers the full `ci wait` polling sequence and the signal-write.

**Graceful degradation**: When the wrapper expires:

1. The dispatcher logs an ERROR entry at `[ERROR] (plan-marshall:phase-6-finalize) Step default:ci-wait timed out after 1800s — marking failed and continuing`.
2. The dispatcher marks this step `failed` via `manage-status mark-step-done … --outcome failed --display-detail "timed out after 1800s"`.
3. The dispatcher continues with the next manifest step. Downstream `automated-review` will treat the missing completed-CI signal as a CI-not-ready condition and surface `ci_failure` to the caller for loop-back.
4. On the next Phase 6 entry, the resumable re-entry check sees `outcome=failed` and retries this step from scratch (one fresh attempt per invocation).

There is no internal soft-timeout, polling cap, or partial-progress checkpoint inside this document — the wrapper is the only timeout authority. The `ci wait` polling primitive carries its own short polling intervals but never its own outer ceiling.

## Inputs

- A PR exists (from `create-pr` earlier in the manifest list, or pre-existing on the branch)
- `{worktree_path}` has been resolved at finalize entry (see SKILL.md Step 0). All `ci` and build-script invocations below MUST identify the worktree via either `--plan-id {plan_id}` (preferred — auto-resolves through `manage-status get-worktree-path`) or `--project-dir {worktree_path}` (escape hatch / explicit override). The two flags are mutually exclusive. Examples below use the literal `--project-dir {worktree_path}` form; substitute `--plan-id {plan_id}` to use auto-resolution.

## Execution

### Get PR number

Use the `pr_number` from the create-pr step. If not available:

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci --project-dir {worktree_path} pr view
```

Read `pr_number` from the TOON output. If `ci pr view` returns `status: error` (no PR exists for the branch), this step has nothing to wait on — record `done` with a `display_detail` of `no PR available` (Branch B in "Mark Step Complete" below) and return without writing the signal. Downstream `automated-review` will independently observe the no-PR condition via the same `ci pr view` probe.

### Wait for CI

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci --project-dir {worktree_path} ci wait \
  --pr-number {pr_number}
```

| Script Output | Action |
|--------------|--------|
| `final_status: success` | Write the completed-CI signal (next sub-step), then proceed to "Mark Step Complete" Branch A |
| `final_status: failure` | Treat as a CI failure — mark this step `failed` with `display_detail "ci failure"`. Do NOT write the completed-CI signal. Downstream `automated-review` will observe the missing signal and surface `ci_failure` for loop-back. |
| `status: timeout` | Outer-wrapper timeout territory — fall through to the timeout contract above. Internal polling has no separate ceiling. |

### Write the completed-CI signal

After `ci wait` returns `final_status: success`, persist the completed-CI signal so the downstream `automated-review` step can consume it instead of re-polling CI:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step ci-wait --outcome done \
  --display-detail "CI {final_status} for PR #{pr_number}"
```

The signal is the `phase_steps["6-finalize"]["ci-wait"].outcome=done` record itself. `automated-review` reads this record (via `manage-status read`) before invoking the producer-stage; the presence of `outcome=done` and a `final_status: success` display detail means CI is green and comment triage may proceed. The absence of the record (or `outcome=failed`) means CI is not ready and `automated-review` should surface `ci_failure` for loop-back without attempting to fetch comments.

## Mark Step Complete

Before returning control to the finalize pipeline, record that this step ran on the live plan so the `phase_steps_complete` handshake invariant is satisfied at phase transition time. The `mark-step-done` call in "Write the completed-CI signal" above IS the step's terminal record on the success path; this section enumerates the alternate branches.

**Branch A — terminal clean pass** (`ci wait` returned `final_status: success`): the `mark-step-done` call in the previous sub-section is the terminal record. Pass the literal `display_detail "CI {final_status} for PR #{pr_number}"`.

**Branch B — no PR available** (the dispatcher ran this step but no PR exists for the branch — `ci pr view` returned `status: error`):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step ci-wait --outcome done \
  --display-detail "no PR available"
```

**Branch C — CI failure** (`ci wait` returned `final_status: failure`): mark this step `failed` and let the dispatcher's general re-entry semantics retry on the next Phase 6 entry. Do NOT record `done` — `automated-review` MUST observe `failed` as the ci-not-ready signal.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step ci-wait --outcome failed \
  --display-detail "ci failure"
```

`ci-wait` does NOT use `--outcome loop_back`. The step has only two terminal outcomes: `done` (CI green or no PR present) and `failed` (CI failure or wrapper timeout). Re-entry on `failed` is governed by the general resumability table in `phase-6-finalize/SKILL.md` (failed → retry from scratch).

## Resumability

`ci-wait` follows the general re-entry table in `phase-6-finalize/SKILL.md`:

| Outcome on re-entry | Action |
|---------------------|--------|
| `done` | Skip dispatch entirely. CI was already observed green (or no PR was available); the signal is preserved in the prior record. |
| `failed` | Retry from scratch. CI may have advanced since the previous failure; one fresh attempt per invocation. |
| (no record) | Dispatch as a first-time run. |

`ci-wait` never records `loop_back`. Downstream loop-back is exclusively the responsibility of `automated-review` (FIX disposition on a `pr-comment` finding) — `ci-wait` only signals CI completion, never plan-level intent to re-execute.
