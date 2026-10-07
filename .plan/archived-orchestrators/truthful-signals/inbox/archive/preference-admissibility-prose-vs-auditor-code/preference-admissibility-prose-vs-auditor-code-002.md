envelope_version=1
sender_type=plan
sender_id=preference-admissibility-prose-vs-auditor-code
epic=truthful-signals
kind=candidate-lesson
created=2026-09-05T14:10:32Z

component=plan-marshall:persona-code-reviewer
category=anti-pattern
bundle=plan-marshall

# A rationale that refutes a move nobody proposed preserves the defect it claims to justify

## Rule

When a comment or doc paragraph justifies a questionable construct by arguing *against an
alternative*, the falsifier is **the target of the argument**, not its reasoning. Ask: was that
alternative the one actually on the table? A rationale whose target is a move nobody proposed is a
strawman, and it protects the defect precisely by reading as considered.

## Observation

Observed in PLAN `preference-admissibility-prose-vs-auditor-code`: `audit.py` duplicated two
constants. The accompanying rationale argued at length against importing them from
`_findings_core` — a move nobody had proposed. The actual ask was to place them in
`_preference_admissibility`, which **both consumers already import**, so the objection did not
apply to it at all.

The rationale survived several review rounds. It survived *because* it read as considered: reviewers
evaluated whether the argument was sound (it was, about its own target) rather than whether it was
answering the question asked. A bare unjustified duplication would have been caught sooner.

## Why the existing corpus does not cover it

The corpus guards `vacuous-guard`, `vacuous-authority`, and `doc-contract-divergence`. Each of
those is about a claim being *empty* or *unsupported*. This one is different: the claim is
substantive and true — it is simply aimed at the wrong proposition. No existing lesson tests the
TARGET of a justification.

## How to apply

- **Author side**: when justifying a construct by rejecting an alternative, name the alternative
  that was actually proposed, and state why the *proposed* one fails. If no alternative was
  proposed, the rationale is speculative and should say so.
- **Reviewer side**: for every "we do X rather than Y because..." — first check that Y is the
  alternative under discussion. A rationale rebutting an unproposed Y is evidence the real Y was
  never evaluated. Do not grade the argument until its target is confirmed.
- **Signature**: the rationale is longer and better-written than the code it defends, and it names
  a module or approach that appears nowhere in the review thread.
