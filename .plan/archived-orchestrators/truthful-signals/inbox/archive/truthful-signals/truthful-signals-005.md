envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=truthful-signals
kind=finding
created=2026-07-29T12:52:32Z

## An ad-hoc PR is permanently ad-hoc — it can neither maintain itself nor be brought under a plan

### The goal

Close the plan-less PR maintenance gap in the CI abstraction, so that a pull request created outside a plan can be maintained through the sanctioned surface, and so that an existing pull request has a path back into governance.

### Why it belongs to this epic

This is the epic's theme in its structural form. The machinery built today to stop a merge proceeding on an absence of review — the pre-merge participation barrier (#1051) — runs inside `branch-cleanup`, which only executes in a plan flow. **A plan-less PR never reaches it.** So the PRs most likely to carry an unreviewed absence are exactly the ones the absence-detector cannot see, and the only thing holding the line for them is operator discipline.

### The defect, both faces

**Face 1 — a plan-less PR cannot maintain itself.**
`ci pr reply`, `pr thread-reply` and `pr edit` hard-require `--plan-id`. That flag keys the `prepare-body` / `prepare-comment` scratch slot and is guarded by `require_plan_exists` (`tools-integration-ci/scripts/ci_base.py:156`), so a synthetic id returns `plan_not_found`. Only `pr create` carries a `--body-file` escape hatch; its siblings do not.

**Face 2 — an existing PR cannot be adopted into a plan.**
`manage-status create` accepts no branch parameter, and the branch is derived as `feature/{plan_id}` by phase-5-execute as its sole writer. A plan created to govern an existing PR would therefore own a different branch than the PR it governs. There is no adopt verb and no supported binding.

Together these mean an ad-hoc PR stays ad-hoc for its whole life: it cannot fix itself, and it cannot be handed to something that can.

### Observed cost

plan-marshall#1052, 2026-07-29. The PR could not post its own bot re-review trigger and could not correct a body that described two of its three commits — the undescribed one being the change to `required_bots`, i.e. the highest-leverage line in the diff redefining what blocks every future merge. It landed with no review of its final HEAD and no mention of that commit in the merge record. The executing orchestrator identified the blockage correctly, refused to route around it with direct `gh`, and filed it as inbox message 019; the only available unblock was a human acting by hand.

### Candidate remedies — evaluate both, pick with reasons

1. A plan-less body channel for the reply / edit verbs, mirroring `pr create --body-file`.
2. An explicit adopt verb binding a plan to an existing branch and PR.

These are not alternatives to each other by default: remedy 1 makes an ad-hoc PR maintainable, remedy 2 makes it governable. Choosing only the first leaves such PRs permanently outside the ledger and outside the participation barrier.

### Trap to avoid

The router-level `--plan-id` already has a documented escape hatch — `--project-dir` (`tools-integration-ci/SKILL.md:147`). **It does not help.** That flag selects the CHECKOUT the underlying `gh`/`glab` subprocess runs in; the blocking flag selects the prepared-body SLOT. The two share a name and solve different problems. Anyone starting here will find `--project-dir` within a minute and may conclude the gap is already closed.

### Constraint

Do not weaken `require_plan_exists`. Its guard against materialising an orphan plan tree merely to hold a scratch body file is deliberate and documented at the call site.

### Acceptance

A pull request with no plan can post a comment and correct its own body through the abstraction with no direct `gh` use; the behaviour is covered by tests; and the chosen remedy is documented in `tools-integration-ci/standards/pr-review-operations.md`. If remedy 2 is taken, an adopted PR is subsequently governed by the pre-merge participation barrier like any plan-driven one.
