envelope_version=1
sender_type=plan
sender_id=a-rule-that-is-green-because-it-examined-nothing
epic=truthful-signals
kind=candidate-lesson
created=2026-08-08T18:51:07Z

component=plan-marshall:manage-adr
category=bug
title=An ADR was cited as "already accepted" while its recorded Status is Proposed
confidence=high
source_plan=a-rule-that-is-green-because-it-examined-nothing
source_signal=qgate-finding 3a5703 (6-finalize, pre-submission-self-review)

# An ADR was cited as "already accepted" while its recorded Status is Proposed

## Context

`arch-gate-fitness-functions.md` line 38 introduced an ADR-014 bullet as "the single-rule form of the anti-vacuity principle **already accepted** in this repository". `doc/adr/014-An_aggregation_over_N_independent_producers….adoc` carries `Status: Proposed`.

The repository maintains a formal two-value ADR status vocabulary, and `manage-adr scan` reports 11 Accepted (ADR-001..011) against 4 Proposed (ADR-012..015). "Already accepted" is therefore a status claim the sole cited record contradicts.

## Root cause

The *substance* the bullet paraphrased was accurate — it matched the ADR-014 metadata summary almost verbatim. Only the acceptance claim was wrong. That is precisely why the sentence read as sound: the citation was correct, the summary was correct, and the one incorrect word rode along unchecked.

Citing an ADR pulls in two independent facts — what it says and what state it is in — and the first being verified creates the impression the second was too. Nothing in the authoring flow separates them.

## Proposed action

- When a document appeals to an ADR's **authority** (not merely its content), read the ADR's `Status` field in the same action and quote a status-accurate phrase. `manage-adr` already exposes the status; the cost is one lookup.
- Prefer status-neutral wording ("already recorded in this repository") unless acceptance is load-bearing; when it *is* load-bearing, cite an Accepted ADR.
- Candidate for a deterministic check: a marketplace doc that names `ADR-NNN` alongside an acceptance-asserting phrase, cross-checked against `doc/adr/NNN-*.adoc` `Status`. This is mechanically decidable and would have caught the defect at edit time.

## Why this belongs to `truthful-signals`

The section this bullet introduced is itself about not treating an unsubstantiated green as evidence. The document argued against vacuous authority while resting on a vacuous authority claim of its own — the recurrence archetype the epic already tracks as *vacuous-authority* (n=5 before this one).

## Resolution in this run

Reworded to "already recorded in this repository" so the claim matches ADR-014's recorded Proposed status. ADR-009 (Accepted), which ADR-014 itself names as its sibling in the fail-closed family, was identified as the citation to use if acceptance is ever needed.

## Evidence

- Q-Gate finding `3a5703`, phase `6-finalize`, source `pm-plugin-development:ext-self-review-plan-marshall`, severity warning, resolution `fixed`.
- File: `marketplace/bundles/plan-marshall/skills/manage-architecture/standards/arch-gate-fitness-functions.md` line 38.
