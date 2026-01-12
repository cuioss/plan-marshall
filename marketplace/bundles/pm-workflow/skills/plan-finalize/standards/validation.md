# Plan Finalize Validation Criteria

## Configuration

- [ ] Accept `plan_id` parameter (never paths)
- [ ] Read domain and finalize config from config.toon
- [ ] Finalize config fields: `create_pr`, `verification_required`, `verification_command`, `branch_strategy`
- [ ] Handle all domains: java, javascript, plan-marshall-plugin-dev, generic

## Verification (if verification_required)

- [ ] Run verification command (from config.toon)
- [ ] Handle verification failures with retry option
- [ ] Record lessons-learned on persistent verification failures

## Commit Workflow (ALWAYS)

- [ ] Stage all changes in working directory
- [ ] Create commit with descriptive message (from request.md summary)
- [ ] Use proper commit message format with generated attribution
- [ ] Push to remote branch
- [ ] Handle commit failures (conflicts, network)
- [ ] Handle push failures (remote rejected, authentication)

## PR Creation (if create_pr == true)

- [ ] Read issue reference from references.toon
- [ ] Create PR using template from templates/pr-template.md
- [ ] PR body includes: Summary, Changes, Test Plan, Related Issues
- [ ] Link PR to issue if present (Closes #N format)
- [ ] Set appropriate labels/reviewers if configured

## PR Workflow (if pr_workflow expected)

- [ ] Execute /pm-workflow:pr-doctor command
- [ ] Monitor CI status
- [ ] Address review comments (iterative - may require user intervention)
- [ ] Handle Sonar quality gate

## Completion

- [ ] Verify all tasks marked complete
- [ ] Mark plan complete via manage-lifecycle transition
- [ ] Write final work-log entry
- [ ] Return completion status with commit hash, PR URL (if created)

## Error Handling

- [ ] Handle git conflicts with user guidance
- [ ] Handle network failures with retry
- [ ] Handle PR creation failures (duplicate, permissions)
- [ ] Record lessons-learned on failures
- [ ] Support resume after error resolution

## Resumability

The skill checks current state before each step:

- [ ] Has verification passed? Skip if already verified
- [ ] Are there uncommitted changes? Skip commit if clean
- [ ] Is branch pushed? Skip push if remote is current
- [ ] Does PR exist? Skip creation if PR exists
- [ ] Is plan already complete? Skip if finalize done

## Output Format

### Success

```toon
status: success
plan_id: {plan_id}

actions:
  verification: {passed|skipped}
  commit: {commit_hash}
  push: success
  pr: {created #{number}|skipped}
  pr_workflow: {completed|skipped}

next_state: complete
```

### Error

```toon
status: error
plan_id: {plan_id}
step: {verification|commit|push|pr}
message: {error_description}
recovery: {recovery_suggestion}
```
