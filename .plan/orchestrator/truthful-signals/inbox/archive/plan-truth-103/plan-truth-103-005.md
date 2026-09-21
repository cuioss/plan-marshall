envelope_version=1
sender_type=plan
sender_id=plan-truth-103
epic=truthful-signals
kind=candidate-lesson
created=2026-09-13T12:00:44Z

# Self-seeding is not confined to the self-review tier - it crosses the external gate

component: pm-plugin-development:ext-self-review-plan-marshall
category: improvement
confidence: medium
source_plan: plan-truth-103
source_aspects: script_failure_analysis, request_result_alignment, chat_history_analysis

## Context

PLAN-TRUTH-089 already established that finalize self-review **self-seeds**: a
fix for an over-claiming restatement authors the next round's finding, and the
only terminating move is to replace the restatement with a pointer at its
source. plan-truth-103 corroborates that 5-for-5 and adds one thing the earlier
record does not cover.

Inside the self-review tier (6 rounds, 5 real defects, all fixed by deletion):

- Round 1 fixed `c52749` (a repository-wide absence claim) by narrowing the
  claim and routing its bound through a Coverage Split table.
- Round 2 found `9bacd8` **in that table** — the row mixed a git enumeration
  (46 files) with a filesystem-walk partition (43 read + 3 skipped). The finding
  is filed verbatim as "a SELF-SEEDED defect: introduced by the fix for c52749",
  and notes the aggravation that round 1's narrowing "routed the Swept
  Population bound THROUGH this table, so the pointer landed on the unsound
  part."
- Round 3's cohort (`80e378` / `b4d82a` / `82f5bf`) were all stale restatements
  whose fixes were, again, deletions.

## The new observation

**The same archetype crossed the internal/external boundary.**

CodeRabbit's round-1 Major on PR #1475 was a hand-listed caller set. The fix for
it introduced a **mirrored registry** — a second enumeration of the same
population — and CodeRabbit's round-3 review then caught that (`3c3297`).

So: two independent review gates, one operated by this repository's own
structural surfacer and one by an external LLM reviewer, produced the same
defect archetype one layer apart, and in both cases the *fix* for a
completeness-claim finding introduced the next completeness-claim finding.

The existing lesson frames self-seeding as a property of the self-review loop.
It is not. It is a property of **how a completeness claim is repaired**: naming
the members (a list, a table, a mirrored registry) instead of pointing at the
derivation is what re-seeds, regardless of which gate raised the original.

## Proposed action

Generalise the recorded guidance from "self-review self-seeds" to: *any repair
of a set/count/completeness claim that responds by enumerating the members
re-seeds the defect; the terminating repair is a pointer at the derivation.*
Apply it at the CodeRabbit-response site as well as the self-review site — the
disposition-to-fix path for an external reviewer's completeness finding should
carry the same instruction the self-review path already does.

## Evidence

- qgate finding `9bacd8`: "This was a SELF-SEEDED defect: introduced by the fix for c52749."
- qgate findings `80e378`, `b4d82a`, `82f5bf`: cohort of 3, every resolution begins "Deleted ..."
- qgate finding `0892c4` resolution: "Deleted the universal claim rather than rewriting it, as prescribed ... and POINTS at resolve_settings_arg's docstring" — the prescribed form applied verbatim
- external: CodeRabbit round-1 Major (hand-listed caller set) -> fix introduced a mirrored registry -> CodeRabbit round-3 finding `3c3297`
- `status.metadata.phase_steps["6-finalize"]["pre-submission-self-review"].display_detail`: "clean after 6 rounds, 5 findings fixed by deletion"
