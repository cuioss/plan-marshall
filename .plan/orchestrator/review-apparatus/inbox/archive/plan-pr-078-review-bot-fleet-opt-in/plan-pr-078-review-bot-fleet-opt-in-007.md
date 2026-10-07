envelope_version=1
sender_type=plan
sender_id=plan-pr-078-review-bot-fleet-opt-in
epic=review-apparatus
kind=candidate-lesson
created=2026-10-06T22:22:12Z

component=plan-marshall:phase-4-plan
category=improvement

# Author release and deploy steps as operator steps, never as leaf steps

## Context

In plan `plan-pr-078-review-bot-fleet-opt-in`, TASK-2 ("Guard the npm release path in cuioss-organization and cut an org release") ended with step 7: bump `release.current-version` in `cuioss-organization/.github/project.yml` from 0.35.0 to 0.36.0 and start `release.yml`. The release fans out pin-bump PRs to 22 consumer repositories. The dispatched leaf merged the guard PR, then had the version-bump edit refused by the harness permission classifier as a production deploy; separately the CI abstraction has no verb to start a `workflow_dispatch` workflow. The task stalled at step 7 of 7. The leaf returned a four-option prompt; the operator answered outside all four ("all is on the cuioss-org (main) so I can cut the release now?"), cut the release himself, and typed "released". A further dispatch then recorded the tag.

## Root cause

The outline and task plan treated "cut a release" as an ordinary implementation step. Nothing at plan time classifies a step as a deploy, so the first place the constraint appears is the harness refusal at execution time, after the preceding steps are already merged.

## Proposed action

- In `phase-4-plan`, classify a step that bumps a release version, tags, publishes, or starts a release workflow as an operator step, and place it at a task boundary so the leaf returns a single "your turn: cut release X" hand-off instead of discovering the refusal.
- Have the outline Q-Gate flag any deliverable whose steps need a CI operation the abstraction does not offer (here: workflow dispatch), so the gap is known before execute.
- Keep the permission refusal as is - it is correct. Do not widen permissions to make this step runnable by a leaf.

## Evidence

- aspect: permission_prompt_analysis - Edit on `cuioss-organization/.github/project.yml` refused by the harness classifier as a production deploy (severity error, confidence high)
- aspect: log_analysis - work log BLOCKED 9ce18b: "Cutting the org release was refused by the harness permission classifier (production deploy) ... release.yml is workflow_dispatch-only with no ci-abstraction dispatch verb ... TASK-2 left in_progress at step 7/7"
- aspect: chat_history_analysis - operator answered the four-option prompt with a free-text question, then "released"
- aspect: logging_gap_analysis - the dispatch ended `voluntary_checkpoint` (269,116 tokens); the tag was recorded by the next dispatch
