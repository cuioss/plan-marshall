envelope_version=1
sender_type=plan
sender_id=retrospective-aspects-publish-verdict
epic=post-run-quality
kind=candidate-lesson
created=2026-09-21T09:27:10Z

component=plan-marshall:plan-retrospective
category=improvement
confidence=medium
title=Move the plan-efficiency ratios and the creep set-difference into scripts

# Move the plan-efficiency ratios and the creep set-difference into scripts

## Context

Two retrospective aspects ask an LLM to perform deterministic computation that the
system already has, or could trivially have, in code.

**Plan efficiency.** `references/plan-efficiency.md` Sections 1-2 are four ratios over
denominators already persisted in `work/metrics.toon`, divided against a 35-row static
anchor table that a test already re-derives from its owning enums. Nothing here needs
judgement except the prose message. The reference is forced to spend three separate
warnings on arithmetic hazards an LLM hits and a script cannot: that `_ms` fields are
milliseconds, that plan-level keys round-trip as STRINGS so `max(denominator, 1)`
silently operates on text, and that the numerator must be worked rather than wall time.

**Scope creep.** `request-result-alignment` computes creep as a set difference of the
realized footprint against the union of declared file bullets — this run did it by hand
over ~60 declared and 38 realized paths. `manage-references` ALREADY ships a three-way
reconciliation that compares declaration, structured derivation and realized footprint
by pairwise symmetric difference.

In this very run the hand computation returned 8 creep paths while
`check-manifest-consistency`'s `references_only` returned 10, for a legitimate reason
(the two questions differ on read-intent declarations). Both numbers are correct for
their own question — but having two producers of one comparison is exactly the
second-producer defect `plan-efficiency.md` itself forbids for denominators.

## Root cause

Deterministic work sited in a reference document instead of a script, with the
reference then carrying prose guard-rails against the failure modes that siting causes.

## Proposed action

1. Add a `plan-efficiency compute-ratios` script returning the four ratios, the matched
   anchor row and the tripped column; leave the LLM only the message prose.
2. Route `request-result-alignment`'s creep comparison through the existing
   `manage-references` reconciliation rather than re-deriving it.
3. Extend `check-artifact-consistency` to publish PER-DELIVERABLE recall beside its
   existing global recall, so the 70% fulfilled/partial verdict is read rather than
   recomputed and the read-intent exclusion rule is applied once, in code.

Lower priority, same shape: a `collect-fragments run-deterministic` driver walking
`SECTION_SPEC` would collapse ~18 tool calls (9 script-backed aspects x run+register)
into one and close the silent never-registered-aspect failure mode.

## Evidence

- aspect: llm_to_script_opportunities — four candidates with repetition counts and complexity grades
- aspect: request_result_alignment — `scope_creep_reconciliation` documenting the 8-vs-10 divergence and why both are right
- reference: `references/plan-efficiency.md` Sections 1-2 and their three arithmetic-hazard warnings
