envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=live-blockers
kind=finding
created=2026-10-21T12:58:17Z

# Finding: the runbook lane on opencode edited the main checkout before creating its worktree, and the review bot was silent on the merge head

Source: epic `pm-mcp-core-m2-m4`, PLAN-81 (#114, 2026-10-20), landing `rb-81-unit-frontmatter-hardening-001`, plan-reported and confirmed in its own landing text. Related, already staged here: PLAN-LB-66 (runbook-lane skill), PLAN-LB-67 (standing review authorization), PLAN-LB-46 (review-bot signal gaps).

## Lane contract: edits only in the plan worktree

- The lane edited six files in the main checkout before it created the worktree and corrected it by hand. This repeats the mistake the lane contract forbids. On opencode there is no guard, so nothing stopped it (`guard: none on this harness`). The orchestrator found the main checkout clean afterwards.

## Review bot on the merge head

- `cuioss-review-bot` covered `5ca7772`, not the merged head `ead74de`, which followed a merge of `origin/main` into the branch. The merge went in on the operator's selected "Merge with the gap". The lane's rule is that a required reviewer must cover the head; the lane asked, and the operator chose.

## Same pattern, later

PLAN-64 (#122, 2026-10-21): after the merge of #122 the worktree held one uncommitted build rewrite of a file of another plan; the lane carried it as a separate pull request (#127) on the operator's word and did not fold it into the merged one. That handling was correct; the point is that a rewrite can appear after the merge is enqueued, and whether the lane has a step that looks for such files before the worktree is removed was not checked here.

## Suggestion

A check at the end of the lane run that lists uncommitted files of the plan worktree and of the main checkout, and a rule for a head that moved by a merge of the base branch after the last review.
