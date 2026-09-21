envelope_version=1
sender_type=plan
sender_id=a-rule-that-is-green-because-it-examined-nothing
epic=truthful-signals
kind=candidate-lesson
created=2026-08-08T18:51:30Z

component=pm-plugin-development:plugin-architecture
category=anti-pattern
title=A skill body gained an authoring-time MUST while its activation description still scoped it to running/interpreting
confidence=high
source_plan=a-rule-that-is-green-because-it-examined-nothing
source_signal=qgate-finding 8ac399 (6-finalize, pre-submission-self-review)

# A skill body gained an authoring-time MUST while its activation description still scoped it to running/interpreting

## Context

This plan added a "Polarity trap in a hand-written `ArchCondition`" section to `pm-dev-java/skills/arch-gate-java/SKILL.md`, closing with a normative pairing requirement: a hand-written condition MUST also be exercised in the positive rule form against the same deliberately non-compliant fixture. The section states itself that the obligation binds **at authoring time**.

The frontmatter `description` (line 3) and the Enforcement activation line (line 16) were untouched and still scoped the skill to "running or interpreting the Java arch-gate".

## Root cause

The `description` field is the activation contract the skill-selection mechanism matches on. A rule author writing a new `ArchCondition` — precisely the reader the MUST governs — matches on neither "running" nor "interpreting", so **the skill is not loaded at the moment its MUST binds**. The obligation is written, correct, and unreachable.

Corroboration that this is drift and not house style: the two sibling per-domain skills, `arch-gate-python` and `arch-gate-js`, carry the byte-identical description template and carry no authoring obligation in their bodies. Java's body had outgrown the shared template and its description was not amended to say so.

The generalisable shape: **when a skill body acquires a new binding moment (authoring, review, migration), its activation description must acquire that moment too, or the obligation is unenforceable by construction.** A body edit and a frontmatter edit are separate actions, and nothing couples them.

## Proposed action

- Add to the skill-authoring checklist: *if the edit introduces a normative obligation that binds at a moment the description does not name, amend the description in the same change.*
- Candidate deterministic detector for `plugin-doctor` / `ext-self-review-plan-marshall`: a diff that adds a MUST/REQUIRED sentence whose surrounding text names an activity verb (authoring, writing, designing, reviewing) absent from the frontmatter `description`. The existing `description_body_drift` self-review candidate class already surfaces this shape — it fired here — so the remaining gap is edit-time rather than pre-submission-time detection.

## Resolution in this run

Amended the line-3 description and the line-16 Enforcement activation sentence to name authoring alongside running and interpreting, and added the fixture-location clause the pairing requirement had left unstated.

## Evidence

- Q-Gate finding `8ac399`, phase `6-finalize`, source `pm-plugin-development:ext-self-review-plan-marshall`, severity warning, resolution `fixed`.
- File: `marketplace/bundles/pm-dev-java/skills/arch-gate-java/SKILL.md` lines 3, 16, and the added polarity-trap section.
