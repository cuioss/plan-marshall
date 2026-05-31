# Plan Finalize Validation Criteria

## Exit-code convention for `manage-*` script calls

Every `manage-*` script call in this document carries the following exit-code contract unless a step explicitly states otherwise:

- **`exit_code == 0`**: parse the returned TOON and use the value as the step describes.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

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

## Lessons (when `lessons-capture` is in the manifest)

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

## Peer-Pattern Consistency Audit

When a source lesson identifies a *missing pattern* in one finalize-standards file (e.g., "`branch-cleanup.md` does not declare its `order: <int>` frontmatter", "`commit-push.md` is missing the `manage-status mark-step-done` termination call"), the Q-Gate audit MUST extend the cleanup beyond the single file the lesson called out. A one-off fix is rarely sufficient — the same drift typically exists across peer files in the same `standards/` directory because they were authored by the same template, edited in the same plan, or copied from one another. Surfacing the divergence at audit time converts a one-off fix into a coverage sweep at marginal cost: the audit is **one grep**, and the fix is the same edit applied to the additional divergent files.

**Audit procedure** (applies whenever a lesson surfaces a peer-pattern claim):

1. **Enumerate siblings** — list every `.md` file in the same `standards/` directory as the file the lesson called out (typically `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/` for finalize standards, but the rule is stated generically and applies to any sibling-standards directory in the bundle):

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
     files --module {bundle:skill} --category standard
   ```

   Glob fallback for sub-module lookup or when the architecture verb returns elision:

   ```
   Glob: marketplace/bundles/{bundle}/skills/{skill}/standards/*.md
   ```

2. **Grep each peer for the pattern claim** — for every peer-pattern claim in the lesson (any sentence of the form "all standards must declare X", "every step terminates with Y", "each standards doc carries frontmatter Z"), grep every sibling for the pattern:

   ```
   Grep: pattern={pattern} path=marketplace/bundles/{bundle}/skills/{skill}/standards/ glob=*.md output_mode=files_with_matches
   ```

   Invert the result: the files NOT in the match set are the divergent siblings.

3. **Add divergent siblings to the cleanup plan as additional deliverables** — NOT as a follow-up plan. Every divergent sibling becomes an additional deliverable (or an additional `Affected files` entry on the originating deliverable) so the fix lands in the same plan as the originating one-off. Following the **Path / Constant Migration Sub-pattern** (see `phase-4-plan/SKILL.md`) is appropriate when the count exceeds the single-task threshold; for ≤ 3 divergent siblings, fold them into the originating deliverable's `Affected files` and let one task agent handle the sweep.

**Why same-plan, not follow-up plan** — splitting the sweep into a follow-up plan loses the audit context: the next planner sees the originating fix in isolation and re-discovers the divergence weeks or months later. A same-plan sweep keeps the rationale (the lesson body that surfaced the original gap) attached to every fix, so a future reader auditing any one of the additional deliverables can trace the rationale back to the originating lesson without archaeology.

**Why "one grep, same edit"** — the audit cost is asymmetric: enumerating siblings is one `architecture files` call, grepping for a pattern is one `Grep` call, and the fix is the same edit pasted into the divergent files. The marginal cost of fixing N additional files is O(N) trivial edits; the marginal cost of NOT fixing them is O(N) future regressions, each of which requires its own lesson → plan → fix cycle. The audit converts an expensive lazy-fix cycle into a cheap eager-fix sweep.

**Generic applicability** — the audit rule is stated generically so it applies to any sibling-standards directory in the bundle (`manage-execution-manifest/standards/`, `phase-4-plan/standards/`, `ref-workflow-architecture/standards/`, etc.), not just `phase-6-finalize/standards/`. The lesson's peer-pattern claim names the target directory; the audit applies the same enumeration + grep + add-to-cleanup-plan flow regardless of which sibling-standards directory is in scope.

**Cross-reference**: the **Path / Constant Migration Sub-pattern** in `phase-4-plan/SKILL.md` codifies the five-task decomposition (code / test / prose / example / verification) when the divergent-sibling count exceeds the single-task threshold or when prose / example sweeps materially extend the work. The two rules compose: the audit identifies the surface, and the migration sub-pattern shapes the task decomposition.

## Mark Step Complete

This document also serves as the `validation` finalize step entry in `required-steps.md`: it captures the end-of-pipeline validation pass. Before returning control to the finalize pipeline, record that this step ran on the live plan so the `phase_steps_complete` handshake invariant is satisfied at phase transition time.

Pass a `--display-detail` value alongside `--outcome done` so the output-template renderer can surface the validation outcome. The payload differs by whether the validation pass exposed per-check counts:

**Branch A — default** (the handshake invariant confirms all required steps are done; no per-check telemetry is available):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step validation --outcome done \
  --display-detail "all required steps done"
```

**Branch B — per-check counts available** (when the validation pass enumerates individual checks and `{N}` is the count of checks that passed):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step validation --outcome done \
  --display-detail "{N} validation check(s) passed"
```
