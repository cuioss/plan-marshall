# Plan Finalize Validation Criteria

## Configuration

- [ ] Accept `plan_id` parameter (never paths)
- [ ] Read finalize config from marshal.json: `plan.phase-7-finalize` (step booleans), `plan.phase-1-init` (branch_strategy)
- [ ] Read context from references.json: `branch`, `base_branch`, `issue_url`, `build_system`

## Commit Workflow (ALWAYS)

- [ ] Stage all changes in working directory
- [ ] Create commit with descriptive message (from request.md summary)
- [ ] Use proper commit message format with generated attribution
- [ ] Push to remote branch
- [ ] Handle commit failures (conflicts, network)
- [ ] Handle push failures (remote rejected, authentication)

## PR Creation (if create_pr == true)

- [ ] Read issue reference from references.json
- [ ] Create PR using template from templates/pr-template.md
- [ ] PR body includes: Summary, Changes, Test Plan, Related Issues
- [ ] Link PR to issue if present (Closes #N format)
- [ ] Set appropriate labels/reviewers if configured

## Automated Review (if PR created)

- [ ] Monitor CI status via workflow-integration-ci
- [ ] Address review comments (iterative - may require looping back to execute)
- [ ] Handle Sonar quality gate via workflow-integration-sonar
- [ ] Create fix tasks and loop back to 5-execute if issues found (max 3 iterations)

## Knowledge and Lessons (Advisory)

- [ ] Capture significant patterns via manage-memories (advisory, non-blocking)
- [ ] Capture lessons learned via manage-lessons (advisory, non-blocking)

## Completion

- [ ] Mark plan complete via manage-lifecycle transition
- [ ] Write final work-log entry
- [ ] Return completion status with commit hash, PR URL (if created)

## Error Handling

- [ ] Handle git conflicts with user guidance
- [ ] Handle network failures with retry
- [ ] Handle PR creation failures (duplicate, permissions)
- [ ] Handle max iteration limit (3 cycles)
- [ ] Support resume after error resolution

## Resumability

The skill checks current state before each step:

- [ ] Are there uncommitted changes? Skip commit if clean
- [ ] Is branch pushed? Skip push if remote is current
- [ ] Does PR exist? Skip creation if PR exists
- [ ] Is automated review complete? Skip if already processed
- [ ] Is Sonar roundtrip complete? Skip if already processed
- [ ] Is plan already complete? Skip if finalize done

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
  knowledge_capture: done
  lessons_capture: done

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
