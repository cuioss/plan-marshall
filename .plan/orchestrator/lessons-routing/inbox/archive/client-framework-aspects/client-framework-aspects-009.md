envelope_version=1
sender_type=orchestrator
sender_id=client-framework-aspects
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:04:54Z

> Routed from epic `client-framework-aspects` (repository Token-Sheriff) by its orchestrator on 2026-11-24, at the operator's direction. Original message `plan-15-plan-12-residual-fixes-003.md`, sender plan `plan-15-plan-12-residual-fixes`, created 2026-11-24T11:11:12Z. The lessons store of that repository refuses bundle-prefixed `plan-marshall:*` components (`wrong_store`), so the lesson is handed to this repository, which owns the components.

# Candidate lesson: editing the PR body after the review bots have reviewed reopens a resolved finding and costs an extra pre-merge loop-back

**Source plan:** plan-15-plan-12-residual-fixes (PR #954)
**Signal:** signal_automated_review_count=1 (automatic-review / pre-merge barrier)
**Suggested category:** anti-pattern (finalize process)
**Suggested component:** plan-marshall:phase-6-finalize (PR-body update and pre-merge barrier) or plan-marshall:workflow-integration-github (CodeRabbit comment handling)

## What happened

After the review findings were fixed (inline commit 74e1f9b3) and automatic-review had re-run cleanly on that head, the PR body was edited. CodeRabbit responds to a PR-body edit by re-editing its own walkthrough or summary comment in place. The findings pipeline keys comments by edit term (`edit_term` on each pr-comment record). It therefore saw the edited comment as new and reopened it as pending.

As a result, the first `default:branch-cleanup` run stopped at the pre-merge barrier with `outcome=loop_back` (work log, 10:44:07Z). A further wait-region triage round (10:44:35Z to 10:45:05Z) was needed before the re-fired branch-cleanup could merge (10:45:16Z onward). No new defect was involved; the comment content was unchanged in substance.

## Rule

**Do:** make every PR-body change (summary, residual-follow-up list, disposition notes) before the last push that the review bots review. Alternatively, batch body edits into the same round as a code or doc fix, which needs a re-review anyway.

**Don't:** edit the PR body once automatic-review has completed on the final head. If an edit is unavoidable, expect a CodeRabbit walkthrough re-edit and one more triage pass, and plan for it.

**Possible structural fix (for the orchestrator to judge):** in the pr-comment fetch, a bot's re-edit of its own walkthrough or summary comment (not an inline review comment) with no new actionable content could be classified as non-actionable instead of reopening as pending.
