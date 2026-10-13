envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T06:54:55Z

# Candidate lesson: outline fixed design details that its own survey deliverable was meant to settle

- Component: plan-marshall:phase-3-outline
- Suggested category: improvement
- Signal: plan-retrospective (chat-history-analysis, request-result-alignment)
- Related: workflow-engine-014 (the spec correction got its own deliverable). This one is about what the
  outline asserts before that survey has run.

## Context

Deliverable 2 existed to survey the state catalogue and fix the `retry_counters` key list. The outline
nevertheless wrote both the key list and the clearing rule ("cleared in the transaction that leaves
state_id") into deliverables 2, 3 and 4 and into the task texts. The survey in execute envelope 1 showed
the rule would reset every count, because each retry passes through other states (merge-sync to
merge-gate), and the key list was wrong (re_enter had to split, open_pr was missing). The operator had to
decide a new rule mid-execute; two extra ADRs (core-store 005, 006) followed, and TASK-004 and TASK-006
kept the old key list in their text.

## Root cause

The outline treats a survey deliverable as confirming a design it already wrote down, instead of as the
step that produces the design. Nothing marks the downstream details as provisional.

## Proposed action

When a deliverable's purpose is a survey or a decision, the outline states only the question and the
candidates; the dependent deliverables reference the survey's result instead of restating a value. When the
survey changes a value, the execute phase updates the dependent task texts (or records that they are
superseded) before running them.

## Evidence

- Session transcript, operator decision after envelope 1: "The outline said 'when its state is left', but
  every retry in the state catalogue passes through other states ... that rule would reset the count on
  every retry and no budget would ever stop" - answered "Accept new rule"; second question "Accept list".
- Envelope 1 hand-back: "The text of TASK-4 and TASK-6 still names the old list; the code follows the
  corrected specification."
- work.log 16:34:03 (execute-task): survey result with "Changed vs outline: re_enter split in two ... open_pr
  added".
- request-result-alignment: realized-but-undeclared files include
  pm-core/doc/adr/core-store/005-retry-count-clearing-rule.adoc and 006-retry-counter-key-list.adoc.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `workflow-engine-017.md` from plan workflow-engine (PLAN-13, #45; Claude Code)
