envelope_version=1
sender_type=plan
sender_id=lb-37-functional-review
epic=live-blockers
kind=candidate-lesson
created=2026-10-13T13:52:10Z

component=plan-marshall:automatic-review
category=bug
title=Escalate a required bot's size refusal and ignore other PRs' findings

# Escalate a required bot's size refusal and ignore other PRs' findings

## Context

On PR #1753 CodeRabbit (required) answered with "Review skipped: 198 files exceed the limit of 100". automatic-review filed that reply as an ordinary pr-comment finding (5064d5) and took a plain participation loop_back twice instead of returning `escalate_ask{reason: refusal_structural}`, because the refusal-recovery branch only fires when the bot appears in `rate_limited_bots[]`. Later, on PR #1759, trigger-B treated 5064d5 (reviewed_commit_sha from PR #1753) as evidence that the current reviews were stale and listed CodeRabbit and Sourcery for re-review.

## Root cause

The structural-refusal branch is keyed on the comment wait's rate-limit list, not on the participation check's `refused_structural` state, and CodeRabbit's `refusal_patterns` do not cover the "Review skipped: N files exceed the limit of M" wording. The trigger-B selector reads reviewed_commit_sha from every stored bot finding without filtering by pr_number.

## Proposed action

Route a required bot whose participation state is `refused_structural` into Branch 0 (`refusal_structural`), add the "files exceed the limit" wording to the CodeRabbit registry, and filter trigger-B's staleness input to findings of the current PR.

## Evidence

- aspect: chat_history_analysis - automatic-review loop_back iteration 2 on PR #1753 explained why it did not escalate
- aspect: chat_history_analysis - PR #1759 FIND pass: "trigger-B reads reviewed_commit_sha from any stored bot finding, including one from a different PR"
- aspect: llm_to_script_opportunities - pr_number filter candidate
