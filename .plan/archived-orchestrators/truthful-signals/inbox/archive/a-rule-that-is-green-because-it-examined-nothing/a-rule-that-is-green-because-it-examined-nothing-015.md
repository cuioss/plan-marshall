envelope_version=1
sender_type=plan
sender_id=a-rule-that-is-green-because-it-examined-nothing
epic=truthful-signals
kind=candidate-lesson
created=2026-08-08T18:52:57Z

component=plan-marshall:phase-3-outline
category=anti-pattern
title=An outline carried two numbering schemes for the same items and never stated the mapping
confidence=high
source_plan=a-rule-that-is-green-because-it-examined-nothing
source_signal=qgate-finding 23de64 (3-outline)

# An outline carried two numbering schemes for the same items and never stated the mapping

## Context

`solution_outline.md` used two numbering schemes for the same four items and never stated the mapping between them:

- The Overview ASCII diagram and the D0 record section used the **request's D-labels**: D0 gate, D1 obligation, D2 polarity trap, D3 retrofit, D4 marker scope.
- The Deliverables section, the Approach section, and the Metadata `depends` fields used **outline ordinals**: 1 gate, 2 obligation, 3 polarity trap, 4 marker scope.

The collision is direct and silent. Diagram label `D2` means the polarity trap, while deliverable `2` is the negative-control obligation. Diagram label `D1` means the obligation, while deliverable `1` is the gate.

## Root cause

Both schemes are individually coherent, so neither reads as wrong in isolation, and the document never places them side by side. The scheme inherited from the source request was carried into the diagram verbatim while the Deliverables section was authored fresh with ordinals.

The concrete downstream hazard: `phase-4-plan` references deliverables by the ordinal-plus-title reference format. A task authored from the *diagram* reading rather than the *Deliverables* reading binds to the wrong deliverable — and the resulting task would look entirely plausible.

## Proposed action

- **One scheme per document.** When a plan document inherits identifiers from a source (request D-labels, issue numbers, spec section ids), pick the local scheme as primary and demote the inherited identifier to a parenthetical annotation, never a competing identifier.
- **Candidate deterministic check**: a plan document containing both `D{n}` tokens and ordinal deliverable references, where the two sequences are not order-isomorphic, is a finding. Order-isomorphism is mechanically decidable and would have caught this exactly.
- The general form is broader than plans: any document that indexes one set under two identifier systems must state the mapping once, adjacent to the first use.

## Resolution in this run

The document now uses one scheme — the ordinal is the primary identifier everywhere it refers to its own deliverables, diagram nodes included. Diagram nodes relabelled 1/2/3/4 with the request D-label carried as a parenthetical annotation (`spec label D1`) for traceability. A Numbering note was added under Overview stating the rule. `D0` keeps its name as the gate *result*, with an explicit statement that it is not a deliverable ordinal. Prose D-label references were converted throughout. Presentation only — no scope, deliverable count, affected files, verification, or success criteria changed.

## Evidence

- Q-Gate finding `23de64`, phase `3-outline`, type `triage`, severity warning, resolution `taken_into_account`.
