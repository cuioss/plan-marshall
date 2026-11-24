envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4-v2
epic=lessons-routing
kind=candidate-lesson
created=2026-11-20T17:37:50Z

component=plan-marshall:phase-6-finalize
category=improvement
created=2026-11-20
bundle=plan-marshall
title=Let functional and code review declare their file dependency to survive doc-only commits

# Let functional and code review declare their file dependency to survive doc-only commits

## Context

In PLAN-V2-158 the second CodeRabbit pass found one valid point. It was fixed in 3 files with 12 lines of ADR, developer-guide and Javadoc wording, and no code changed. The new commit (d5f1d6ac) invalidated both closed reviews, because neither the functional review nor the code review declares which files its verdict depends on. The operator had to decide in session whether to re-run both in full or waive the re-run. The waiver is now in status metadata as `refire_waiver` / `functional_review_override_heads`, and branch-cleanup records `head_binding_waived: code-review`. The functional review fired 6 times in total and the code review 2 times.

## Root cause

Review closure is bound to the HEAD SHA alone, so any later commit (even a wording-only fix that answers a review-bot comment) re-opens both reviews or needs an operator waiver.

## Proposed action

Record the reviewed file set (or the deliverable surface) with each closed verdict. A later commit should re-fire a review only when it touches that set with a code change. A documentation-only or Javadoc-only delta inside the set could take a light re-verification instead of a full round. At minimum, offer the waiver as a classified, recommended default for commits that change no code.

## Evidence

- aspect: chat_history_analysis — operator decision "Waive the re-run (Recommended)" for the docs-only commit
- status.metadata.phase_steps.6-finalize.code-review.refire_waiver, branch-cleanup head_binding_waived=code-review
- aspect: invariant-summary / log-analysis — functional-review firing_count 6, loop_back_budgets default:functional-review spent 3
