envelope_version=1
sender_type=plan
sender_id=orchestrator-worktree-substrate
epic=orchestrator-refactor
kind=candidate-lesson
created=2026-09-28T19:16:53Z

component=plan-marshall:phase-6-finalize
category=improvement

# Grant pre-submission-self-review a content-search path before counting loop-backs

## Context

In orchestrator-worktree-substrate, pre-submission-self-review fired 7 times, 5 of them as loop-backs. On the last round the full-scope sweep examined 263 candidates (222 schema-bearing files plus 41 contract sources). The verifier answered `may_close=no` because the author had not read every file in full and Grep was absent from the envelope. The loop-back ceiling (5/5) was exhausted, and the operator had to close self-review as clean, recording the refusal as finding 5f65bb.

## Root cause

The dispatched leaf did not receive Grep at runtime. The self-review workflow does not route the full-surface sweep through `architecture search --content`, the inventory-backed content search that works without Grep. A coverage-class step therefore cannot complete its own sweep, and the verifier correctly refuses the result.

## Proposed action

Make the self-review full-scope round use `architecture search --content` as its first content-search path, and have it report coverage from that verb's complete-coverage fields. When coverage cannot be established, return a coverage-gap signal instead of spending a loop-back. Do not count a verifier refusal caused by a missing tool as a normal loop-back against the ceiling.

## Evidence

- aspect: chat_history_analysis - operator override after the ceiling was exhausted
- aspect: permission_prompt_analysis - Grep was not granted to dispatched leaves (also observed in this retrospective's own envelope)
- aspect: log_analysis - decision log 15:41:33Z: verifier refused, "Grep absent; refused, gap unswept"
