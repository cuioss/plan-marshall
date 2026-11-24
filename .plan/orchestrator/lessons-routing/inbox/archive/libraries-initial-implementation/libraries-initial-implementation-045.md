envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:29Z

component=plan-marshall:workflow-integration-git
category=improvement
title=phase-5/phase-4: resolve the commit trailer once per plan and hand it to every execute leaf
source_lesson=2026-11-21-12-001
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-21

# phase-5/phase-4: resolve the commit trailer once per plan and hand it to every execute leaf

# Candidate lesson: the commit trailer is resolved per execute leaf from three sources that can disagree

- Source signal: plan-retrospective (chat-history and logging-gap aspects), plan plan-08-store-drafts-save (inbox plan-08-store-drafts-save-022), PR #48. Component `plan-marshall:workflow-integration-git`, confidence high.

## What happened

Four execute leaves (envelopes 1, 2, 4 and 5) each reported the same conflict on their own. The git-workflow trailer resolver gives `Co-Authored-By: plan-marshall <noreply@cuioss.de>`, the session attribution says to end commits with the Claude co-author and session lines, and the orchestrator brief named a different model ("Claude Sonnet 5.5") than the one writing the commits (Opus 5.5). Every leaf chose the session attribution and asked the orchestrator to amend if that was wrong. Nobody resolved it, so all commits on the branch rest on four separate leaf judgements, and the landing records that the trailers on the branch mix Sonnet 5.5 and Opus 5.5 lines.

## Why it matters

The trailer is the commit's authorship statement and is permanent history on `main` once the PR is squashed. Four leaves deciding independently makes the result depend on which leaf committed, and no decision-log entry fixes the trailer for the plan.

## Candidate rule

Resolve the trailer once per plan (in phase-4-plan or at the start of phase 5), record it in the plan status, and hand the resolved trailer to every execute leaf in its brief. When the trailer resolver and the session attribution disagree, surface it once to the operator instead of letting each leaf decide. Owning component: `plan-marshall:workflow-integration-git` (the resolver) with the phase-5 dispatch brief.


## Recurrence in the next plan (plan-12-forms-kinds-schema-layout, inbox plan-12-forms-kinds-schema-layout-003)

- Source signal: plan-retrospective (llm_to_script_opportunities aspect). Plan-12 ran on Sonnet (`status.metadata.model: claude-sonnet-5-5`), early leaf commits carried an Opus co-author trailer, and the trailer was fixed for later commits; the squash merge `8d09629` on `main` still ends with both lines (`Co-Authored-By: Claude Sonnet 5.5` from the PR body and `Co-authored-by: Claude Opus 5.5` collected by GitHub from the earlier branch commits). A squash merge keeps the co-authors of every commit it folds, so the correction on the branch did not reach `main`. The same happened for PLAN-08 (10 Opus and 2 Sonnet trailers on its 12 commits) and PLAN-09.
- Added rules: the commit helper (`git-workflow commit` / `format-commit`) fills the co-author trailer from `status.metadata.model` and refuses a caller-supplied trailer that names a different model; and before the merge the trailers of every branch commit, not only the PR body, are checked against the recorded model and reworded before the squash when they differ. This also settles the root cause named above: the leaf writes the trailer from prose, not from recorded metadata.
