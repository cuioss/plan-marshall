---
name: default:ci-wait
description: Poll CI to completion and write the completed-CI signal consumed by automated-review
order: 25
---

# CI Wait

Pure executor for the `ci-wait` finalize step. This step polls CI to completion against the freshly-pushed PR branch and writes a completed-CI signal that the downstream `automated-review` step consumes instead of polling CI itself. Splitting CI-wait out of `automated-review` keeps the per-iteration triage budget (900 s / 15 minutes) bounded by comment volume rather than CI queue depth.

This document carries NO step-activation logic. Activation is controlled by the dispatcher in `phase-6-finalize/SKILL.md` Step 3 and is driven solely by presence of `ci-wait` in `manifest.phase_6.steps`. When the dispatcher runs this step, the document executes top to bottom — there is no skip-conditional branching at this layer.

## Timeout Contract

This step runs **inline** in the phase-6-finalize main context — there is no Task agent dispatch and no per-agent timeout wrapper. CI polling is delegated to the `ci wait` script primitive (`plan-marshall:tools-integration-ci:ci`), which carries its own outer `--timeout` ceiling (defaults to 300 s; this step passes an explicit value matching the budget below). The dispatcher invokes the script with a Bash call whose timeout matches the script-side `--timeout` so the host platform per-call ceiling never expires before the script does.

**Budget**: 600 s (10 minutes). CI queue depth, not LLM-side reasoning, dominates wall-clock time during this step — but the dispatcher's inline invocation is bounded by the host platform's maximum Bash timeout, so the budget is the upper bound the host accepts. Most CI runs complete inside 60-180 s; the larger ceiling is defensive for cold-start queues.

**Graceful degradation**: When the `ci wait` script returns `status: timeout`:

1. Log an ERROR entry at `[ERROR] (plan-marshall:phase-6-finalize) Step default:ci-wait timed out after 600s — marking failed and continuing`.
2. Mark this step `failed` via `manage-status mark-step-done … --outcome failed --display-detail "timed out after 600s"`.
3. The dispatcher continues with the next manifest step. Downstream `automated-review` will treat the missing completed-CI signal as a CI-not-ready condition and surface `ci_failure` to the caller for loop-back.
4. On the next Phase 6 entry, the resumable re-entry check sees `outcome=failed` and retries this step from scratch (one fresh attempt per invocation).

There is no Task-agent wrapper or per-agent timeout authority for this step; the `ci wait` script's `--timeout` flag is the only timeout authority. The poll primitive carries short internal poll intervals (default 30 s) which are unrelated to the outer ceiling.

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
  --pr-number {pr_number} --timeout 600
```

Invoke this Bash call with a host-platform timeout of 600000 ms (10 minutes) so the host ceiling matches the script-side `--timeout`. This is the dispatcher-set inline timeout — there is no Task-agent wrapper above it.

| Script Output | Action |
|--------------|--------|
| `final_status: success` | Write the completed-CI signal (next sub-step), then proceed to "Mark Step Complete" Branch A |
| `final_status: failure` | Treat as a CI failure — mark this step `failed` with `display_detail "ci failure"`. Do NOT write the completed-CI signal. Downstream `automated-review` will observe the missing signal and surface `ci_failure` for loop-back. |
| `status: timeout` | The script's own `--timeout` expired — fall through to the timeout contract above and mark `failed`. |

### Write the completed-CI signal

After `ci wait` returns `final_status: success`, persist the completed-CI signal so the downstream `automated-review` step can consume it instead of re-polling CI.

`ci-wait` is one of the four HEAD-dependent steps (alongside `pre-push-quality-gate`, `automated-review`, `sonar-roundtrip`) — see [`phase-6-finalize/SKILL.md`](../SKILL.md) Step 3 "Special case — HEAD-dependent steps". Immediately before invoking `mark-step-done`, resolve the worktree HEAD SHA so the dispatcher can detect a stale completion record after a downstream loop-back commit advances HEAD:

```bash
git -C {worktree_path} rev-parse HEAD
```

The `{worktree_path}` value is the path resolved by `phase-6-finalize` Step 0 (Resolve Worktree and Main Checkout Paths). Capture the stdout as `{sha}` (a 40-character hex SHA) and forward it via `--head-at-completion`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step ci-wait --outcome done \
  --display-detail "CI {final_status} for PR #{pr_number}" \
  --head-at-completion {sha}
```

The persisted `head_at_completion` field is consumed by phase-6-finalize Step 3's resumable re-entry check: when the worktree HEAD has advanced past `{sha}` (typically because `automated-review` or `sonar-roundtrip` opened a loop-back fix-task that produced a new commit), the dispatcher re-fires this step against the newer HEAD instead of skipping it on a stale `done` record.

The signal is the `phase_steps["6-finalize"]["ci-wait"].outcome=done` record itself. `automated-review` reads this record (via `manage-status read`) before invoking the producer-stage; the presence of `outcome=done` and a `final_status: success` display detail means CI is green and comment triage may proceed. The absence of the record (or `outcome=failed`) means CI is not ready and `automated-review` should surface `ci_failure` for loop-back without attempting to fetch comments.

## Mark Step Complete

Before returning control to the finalize pipeline, record that this step ran on the live plan so the `phase_steps_complete` handshake invariant is satisfied at phase transition time. The `mark-step-done` call in "Write the completed-CI signal" above IS the step's terminal record on the success path; this section enumerates the alternate branches.

**Branch A — terminal clean pass** (`ci wait` returned `final_status: success`): the `mark-step-done` call in the previous sub-section is the terminal record. Pass the literal `display_detail "CI {final_status} for PR #{pr_number}"` AND `--head-at-completion {sha}` (captured immediately before the call) so the HEAD-dependent resumability check can detect a loop-back commit that advances HEAD past the validated tree.

**Branch B — no PR available** (the dispatcher ran this step but no PR exists for the branch — `ci pr view` returned `status: error`). Resolve the worktree HEAD before marking done so a future loop-back commit re-fires this branch's `done` record instead of skipping it on stale state:

```bash
git -C {worktree_path} rev-parse HEAD
```

Capture the stdout as `{sha}` and forward it via `--head-at-completion`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step ci-wait --outcome done \
  --display-detail "no PR available" \
  --head-at-completion {sha}
```

**Branch C — CI failure** (`ci wait` returned `final_status: failure`): mark this step `failed` and let the dispatcher's general re-entry semantics retry on the next Phase 6 entry. Do NOT record `done` — `automated-review` MUST observe `failed` as the ci-not-ready signal. The `failed` branch does NOT need `--head-at-completion`: the dispatcher unconditionally retries `failed` records on re-entry regardless of HEAD, so the SHA carries no decision value here.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step ci-wait --outcome failed \
  --display-detail "ci failure"
```

`ci-wait` does NOT use `--outcome loop_back`. The step has only two terminal outcomes: `done` (CI green or no PR present) and `failed` (CI failure or wrapper timeout). Re-entry on `failed` is governed by the general resumability table in `phase-6-finalize/SKILL.md` (failed → retry from scratch); re-entry on `done` is governed by the HEAD-dependent table below.

## Resumability

`ci-wait` is one of the four HEAD-dependent steps in `HEAD_DEPENDENT_STEPS` (`pre-push-quality-gate`, `ci-wait`, `automated-review`, `sonar-roundtrip`) — see [`phase-6-finalize/SKILL.md`](../SKILL.md) Step 3 "Special case — HEAD-dependent steps". The HEAD comparison guards against false-clean re-entry after a downstream loop-back commit (typically produced by `automated-review` or `sonar-roundtrip`) advances HEAD past the validated tree:

| Persisted state | Live worktree HEAD | Action |
|-----------------|--------------------|--------|
| `outcome == done` AND `head_at_completion == HEAD` | matches | SKIP (steady-state — CI already observed green for this exact tree) |
| `outcome == done` AND `head_at_completion != HEAD` | differs | RE-FIRE (treat as no record — HEAD has advanced past the validated SHA; re-poll CI against the new tree) |
| `outcome == done` AND `head_at_completion` absent | n/a | RE-FIRE (legacy record from before SHA tracking; safe default is to re-run) |
| `outcome == failed` | n/a | RETRY (unchanged — same as the general rule) |
| no record | n/a | DISPATCH (unchanged — same as the general rule) |

`ci-wait` never records `loop_back`. Downstream loop-back is exclusively the responsibility of `automated-review` (FIX disposition on a `pr-comment` finding) — `ci-wait` only signals CI completion, never plan-level intent to re-execute.
