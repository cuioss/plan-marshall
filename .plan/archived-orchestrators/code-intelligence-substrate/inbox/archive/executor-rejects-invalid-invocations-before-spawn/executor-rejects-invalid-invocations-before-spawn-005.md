envelope_version=1
sender_type=plan
sender_id=executor-rejects-invalid-invocations-before-spawn
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-09T14:43:19Z

# A required bot resolving participated_but_empty should not alone satisfy the merge gate

component: plan-marshall:phase-6-finalize
category: improvement
confidence: medium
source_plan: executor-rejects-invalid-invocations-before-spawn
source_pr: 1127

## Context

Across three review passes on PR #1127 the gate composition resolved as follows:

- **pr-agent** (`cuioss-review-bot`), the **sole REQUIRED** bot, resolved
  `participated_but_empty` on **all three** passes. It published in its declared shape
  and filed zero findings.
- **coderabbit**, an **OPTIONAL** bot, produced **every** actionable finding: 16 records,
  14 actionable, 11 fixed, 0 rejected — including three Majors that were real defects
  (`93d16a` non-recursive `*.py` glob leaving a stale surface digest; `536c0c` a vacuous
  work-log guard sharing its failure mode with the parse it guards; `5b2668` a dropped
  confidence flag shrinking the accept-set).
- **sourcery**, a second optional bot, resolved `hard_quota` on all three passes — the
  diff exceeded its 150,000-character review limit. It never saw the diff.

The pre-merge review-completeness barrier passed with `participation_complete: true`.

## Root cause

The barrier's required-reviewer predicate is satisfied by participation, and
`participated_but_empty` is participation. So the gate went green on the reviewer that
contributed nothing measurable, while the reviewer that found the defects was one the
gate does not require, and the third was one the gate structurally cannot reach at this
diff size.

A green required-bot signal on this PR therefore carried **no information** about whether
the diff had been substantively reviewed. Note also that Sourcery's exclusion is
deterministic, not intermittent: every plan whose diff exceeds 150,000 characters gets no
Sourcery review, on this PR and on every future PR of comparable size.

## Proposed action

This is one datum, not a verdict, and it explicitly does **not** justify dropping or
demoting pr-agent. The proposal is to make the gate's information content legible rather
than to re-rank bots:

- Surface `participated_but_empty` distinctly at the barrier, so a green participation
  check that rests entirely on empty participation is visible as such rather than
  indistinguishable from a substantive clean review.
- Record the diff-size exclusion as a structural property of the plan (it recurs by size,
  not by chance) rather than as a transient bot failure.
- The required-vs-optional composition question needs a corpus and belongs in the
  cross-plan `audit-archived-plan-retrospectives` quality-chain view, not in a
  single-plan decision.

## Evidence

- `review-retrospective.md` (this plan) — deterministic per-reviewer metrics and the gate-composition observation, stated there as a fact rather than a quality claim.
- decision.log `[2026-08-09T12:05:10Z] [8ff489] (plan-marshall:automatic-review)` — the iteration-2 bot resolution record including sourcery's `hard_quota` refusal text.
- decision.log `[2026-08-09T13:46:27Z] [5bc508]` — the barrier passing with `participation_complete: true`, plus its own recorded caveat that 14 of 60 provider threads remained unresolved while the plan store showed zero pending.
