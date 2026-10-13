envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T07:34:20Z

# Candidate lesson: define precedence of re-review timeout vs FIND participation credit

Source: plan-retrospective of plan verify-not-resolve. Proposed component: `plan-marshall:automatic-review`. Category: improvement. Confidence: medium.

## Context

At HEAD fdf2268 the coderabbit re-review await ended `timed_out: true` after 625 s, with `answer_withheld_in_progress: true`. A following `bot_completion` check showed its check-run completed, and the next FIND credited coderabbit as `participated`. The leaf therefore skipped the `re_review_on_timeout: ask` branch on its own judgement and asked the orchestrator whether it wanted the strict path. In the same run the producer listed coderabbit in `refused_bots` (cause: quota) because of its `no_unreviewed_commit` replies, even though `participated_bots` took precedence.

## Root cause

The workflow does not say which signal wins when the re-review await times out but later evidence proves participation. The refusal classifier also counts a "nothing new to review" reply as a quota refusal.

## Proposed action

State the precedence in the automatic-review workflow (for example: a later verified participation at the same HEAD clears a timeout without escalating, and this is logged as a decision). Classify `no_unreviewed_commit` replies as their own state, not as a quota refusal.

## Evidence

- aspect: chat-history-analysis — automatic-review leaf at fdf2268: "That skips the `re_review_on_timeout: ask` branch that the timeout would otherwise have triggered. Tell me if you want the strict path instead"; "The producer still lists coderabbit in `refused_bots` (cause: quota)"

Classification is left to the orchestrator.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `verify-not-resolve-023.md` from plan verify-not-resolve (PLAN-18, #43; Claude Code)
