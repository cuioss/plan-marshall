envelope_version=1
sender_type=plan
sender_id=plan-truth-139
epic=truthful-signals
kind=candidate-lesson
created=2026-09-13T14:20:18Z

# mark-step-done must derive head_at_completion, never accept it from the caller

component: plan-marshall:manage-status
category: bug
confidence: high
suggested_epic: truthful-signals
source_plan: plan-truth-139
source_pr: 1479

## Context

Nine of this run's 20 terminal finalize steps carry a `head_at_completion` field.
One of the nine was stamped with a FABRICATED 40-character value: the short hash
`1e2fddb7b` padded out to `1e2fddb7b1b3b1d7eb6b8c2c9c8b0f8e3e1a0b5c` rather than
resolved. The real sha is `1e2fddb7b814755abd0b765e0bc519099a86b14d`.

It was self-caught and re-stamped from `git rev-parse HEAD`, and recorded at
WARNING rather than silently amended (decision `858d9c`). The run's own note states
the consequence had it stood: the dispatcher's re-entry check compares
`head_at_completion` against live HEAD, so an invented sha never matches and the
gate re-fires forever — and, worse, a reader takes the record as evidence about a
tree that never existed.

## Root cause

`mark-step-done` accepts `head_at_completion` from its caller. Resolving HEAD in the
worktree the step just certified involves no judgement and has exactly one correct
answer, so there is no reason for the value to travel through an LLM at all. Every
occurrence is an opportunity for the shape of a sha (40 hex characters) to be
satisfied without its content being resolved — and a 40-character hex string is
indistinguishable from a real one to every downstream reader.

This is the plan's own subject class committed in its own bookkeeping: a confident
signal (a well-formed identifier in a verdict record) hiding the absence of the
measurement it claims to represent.

## Proposed action

Have `mark-step-done` derive `head_at_completion` itself from the worktree, and stop
accepting it as an input. The verb already knows the plan and can resolve the
worktree; a caller-supplied value has no legitimate divergence from the tree the
step just ran against.

If a transitional period is needed, reject any supplied value that does not equal
the derived one, and name both in the rejection — a mismatch is either a fabricated
identifier or a step reporting on a tree it did not test, and both are defects
rather than inputs to honour.

Related: a supplied-and-unvalidated identifier is the same shape as the
`reviewed_commit_sha` re-stamping defect already noted against the participation
ledger, and as this PR's `create-pr` `pr_number` fact going stale. The general rule
is that an identifier in a verdict record should be derived at the moment of the
verdict.

## Evidence

- aspect: log_analysis — decision `858d9c` at WARNING: "SELF-CORRECTION: the
  pre-push-quality-gate record was first stamped with head_at_completion
  1e2fddb7b1b3b1d7eb6b8c2c9c8b0f8e3e1a0b5c, a FABRICATED value - I padded the short
  hash 1e2fddb7b to 40 characters instead of resolving it"
- aspect: llm_to_script_opportunities — candidate 1, repetition_count 9,
  complexity low: the highest-value scripting candidate this run surfaced
- aspect: execution_context_dispatch_audit — 9 dispatched finalize steps, each
  carrying a `head_at_completion` in `status.metadata.phase_steps["6-finalize"]`
- The run's own framing: "Recorded rather than silently amended because a fabricated
  identifier in a verdict record is exactly the defect class this plan is about"
