# Plan Finalize Validation Criteria

## Configuration

- Accept `plan_id` parameter (never paths)
- Read the per-plan execution manifest (`execution.toon`) for `phase_6.steps` — the authoritative step list
- Read non-step configuration from `marshal.json`: `plan.phase-6-finalize.review_bot_buffer_seconds`, `plan.phase-6-finalize.max_iterations`, `plan.phase-1-init.branch_strategy`, `plan.phase-5-execute.commit_strategy`
- Read context from references.json: `branch`, `base_branch`, `issue_url`, `build_system`

## Manifest Authority

The validation pass MUST refuse to enforce or report on any step that is NOT present in `manifest.phase_6.steps`. A step listed in `required-steps.md` but absent from the manifest for the running plan is NOT a missing-step violation — it is a manifest pruning decision made at outline time, and validation respects it. Concretely:

- The `phase_steps_complete` handshake invariant only enforces required steps that are also in `manifest.phase_6.steps`.
- The output-template renderer's `[FAILED]` precedence rule only considers manifest steps.
- A validation report enumerating "checks passed" only counts checks whose corresponding step is in the manifest.

Per-step validation criteria below apply when the corresponding step appears in `manifest.phase_6.steps`. When a step is absent from the manifest, the section is not enforced for the current plan.

## Commit Workflow (when `commit-push` is in the manifest)

- Stage all changes in working directory
- Create commit with descriptive message (from request.md summary)
- Use proper commit message format with generated attribution
- Push to remote branch
- Handle commit failures (conflicts, network)
- Handle push failures (remote rejected, authentication)

## PR Creation (when `create-pr` is in the manifest)

- Read issue reference from references.json
- Create PR using template from templates/pr-template.md
- PR body includes: Summary, Changes, Test Plan, Related Issues
- Link PR to issue if present (Closes #N format)
- Set appropriate labels/reviewers if configured

## Automated Review (when `automated-review` is in the manifest)

- Monitor CI status via workflow-integration-github
- Address review comments (iterative - may require looping back to execute)
- Create fix tasks and loop back to 5-execute if issues found (max 3 iterations)
- Per-agent timeout 15 min — on expiry, dispatcher records `outcome=failed` and continues

## Sonar Roundtrip (when `sonar-roundtrip` is in the manifest)

- Handle Sonar quality gate via workflow-integration-sonar
- Per-agent timeout 15 min — on expiry, dispatcher records `outcome=failed` and continues

## Knowledge and Lessons (when `knowledge-capture` / `lessons-capture` are in the manifest)

- Capture significant patterns via manage-memories (advisory, non-blocking)
- Capture lessons learned via manage-lessons (advisory, non-blocking)
- Per-agent timeout 5 min — on expiry, dispatcher records `outcome=failed` and continues

## Archive (when `archive-plan` is in the manifest)

- Archive plan via manage-status archive
- Handle archive failures (missing plan directory, permissions)

## Branch Cleanup (when `branch-cleanup` is in the manifest)

- Gather PR state, branch name, and other open PRs for context
- Present user confirmation dialog with PR link, state, branch, other PRs, and planned actions
- Only proceed with explicit user approval (skip gracefully if declined)
- Abort if other open PRs use this branch as head
- Merge PR if not yet merged (via CI abstraction with `--delete-branch`, which deletes the remote branch only)
- Wait for post-merge CI with 30-minute timeout
- Always switch to base branch, pull latest, and delete the local feature branch — the `--delete-branch` flag does not perform local cleanup, so this sequence runs regardless of prior merge path (freshly merged or already merged)
- Handle merge failures, checkout failures, and pull failures

## Completion

- Mark plan complete via manage-status transition
- Write final work-log entry
- Return completion status with commit hash, PR URL (if created), archive and branch cleanup status

## Error Handling

- Handle git conflicts with user guidance
- Handle network failures with retry
- Handle PR creation failures (duplicate, permissions)
- Handle max iteration limit (3 cycles)
- Support resume after error resolution

## Resumability

Step activation is decided by `manifest.phase_6.steps`; per-step idempotency is decided by the resumable re-entry check in SKILL.md Step 3 (skip if already `done`, retry if `failed`). Standards documents do not contain skip-if-already-applied logic of their own — within an active dispatch, each step records its own outcome and `display_detail`. The dispatcher's re-entry check is the only authority for skipping a previously-completed step.

## Output Format

### Success

```toon
status: success
plan_id: {plan_id}

actions:
  commit: {commit_hash}
  push: success
  pr: {created #{number}|skipped}
  automated_review: {completed|skipped|loop_back}
  sonar: {passed|skipped|loop_back}
  knowledge_capture: {done|skipped}
  lessons_capture: {done|skipped}
  archive: {done|skipped}
  branch_cleanup: {done|skipped|declined}

next_state: complete
```

### Loop Back

```toon
status: loop_back
plan_id: {plan_id}
iteration: {current_iteration}
reason: {ci_failure|review_comments|sonar_issues}
next_phase: 5-execute
fix_tasks_created: {count}
```

### Error

```toon
status: error
plan_id: {plan_id}
step: {commit|push|pr|automated_review|sonar|iteration_limit}
message: {error_description}
recovery: {recovery_suggestion}
```

## Mark Step Complete

This document also serves as the `validation` finalize step entry in `required-steps.md`: it captures the end-of-pipeline validation pass. Before returning control to the finalize pipeline, record that this step ran on the live plan so the `phase_steps_complete` handshake invariant is satisfied at phase transition time.

Pass a `--display-detail` value alongside `--outcome done` so the output-template renderer can surface the validation outcome. The payload differs by whether the validation pass exposed per-check counts:

**Branch A — default** (the handshake invariant confirms all required steps are done; no per-check telemetry is available):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step validation --outcome done \
  --display-detail "all required steps done"
```

**Branch B — per-check counts available** (when the validation pass enumerates individual checks and `{N}` is the count of checks that passed):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step validation --outcome done \
  --display-detail "{N} validation check(s) passed"
```
