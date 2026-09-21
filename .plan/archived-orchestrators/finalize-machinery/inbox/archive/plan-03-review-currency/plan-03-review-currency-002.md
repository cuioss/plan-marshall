envelope_version=1
sender_type=plan
sender_id=plan-03-review-currency
epic=finalize-machinery
kind=candidate-lesson
created=2026-09-17T11:18:52Z

# Verify single-location after worktree move-in before claiming duplication

Cause class: path-nesting misread of the move-based worktree layout.

Rule: after a `prepare_execute` move-in, assert the plan dir's single location
before reporting a duplication — `git-workflow locate-plan-checkout` must read
`location: worktree`, `manage-files list` from the main cwd must read
`dir_not_found`, and `manage-files list` from the worktree cwd must read the
full listing. Read doubled `.plan/local` segments in a worktree-absolute path
(`.plan/local/worktrees/{id}/.plan/local/plans/{id}`) as expected per-tree
nesting, never as evidence of a copy.

Applies to: any plan-marshall phase-5 move-in (`prepare_execute`,
`action: moved`).
