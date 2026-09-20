envelope_version=1
sender_type=plan
sender_id=a-rule-that-is-green-because-it-examined-nothing
epic=truthful-signals
kind=candidate-lesson
created=2026-08-08T18:54:30Z

component=pm-dev-java:arch-gate-java
category=anti-pattern
title=A thin-pointer skill violated its own no-duplication prohibition three lines after stating it
confidence=high
source_plan=a-rule-that-is-green-because-it-examined-nothing
source_signal=pr-comment 521b9f (PR #1115, coderabbitai, resolution=fixed, remediated by TASK-005)

# A thin-pointer skill violated its own no-duplication prohibition three lines after stating it

## Context

`pm-dev-java/skills/arch-gate-java/SKILL.md` lines 10-12 and 19 explicitly forbid the skill from duplicating the central execution model and feedback loop owned by `arch-gate-fitness-functions.md`. Line 39 of the same file then restated three things the central standard owns:

- the dedicated-invocation rationale (`arch-gate-fitness-functions.md` line 48),
- the triage routing (its feedback-loop step 2),
- the lesson lifecycle including rule-identity dedup and retire-on-quiet / reinforce-on-recurrence (its step 3).

The Java binding table already carried the only Java-specific facts in that sentence (Rule surface at line 33, Finding type at line 36), so the restatement added nothing.

## Root cause

A self-imposed prohibition stated in a document's own preamble is **not a check** — it is a claim about the document, made by the document, and nothing verifies it. The prohibition being present makes the violation *less* likely to be caught, not more: a reviewer who reads lines 10-12 assumes the rest of the file complies with them, and reads line 39 as the Java-specific content the preamble promised.

Generalising: a document that declares its own invariant needs an external check of that invariant, exactly as a rule needs a negative control. The parallel to this plan's own subject matter is direct — the preamble is an assertion that has never been exercised against a case that would falsify it.

## Proposed action

- **Candidate detector for `ext-self-review-plan-marshall` / `plugin-doctor`**: when a skill body declares a no-duplication / thin-pointer prohibition naming a specific owning document, check the body's remaining prose for statements that also appear in that owning document. Overlap above a threshold is a finding. The owning document is named explicitly in these preambles, so the comparison target is mechanically resolvable.
- **Authoring rule**: a thin-pointer skill's non-table prose should be verifiable as either (a) Java-specific/domain-specific fact, or (b) a link. Sentence 39 was neither.

## Resolution in this run

TASK-005 replaced line 39 with a pointer to the central Findings-to-triage-to-lesson feedback-loop section, keeping the file a thin pointer. Landed as a follow-up commit on the PR branch (`f362638a`).

## Evidence

- PR #1115 inline comment `521b9f` by `coderabbitai` at `marketplace/bundles/pm-dev-java/skills/arch-gate-java/SKILL.md:39`, reviewed commit `9f3c4755`, disposition `fixed`, severity Major.
- The file passed three `pre-submission-self-review` iterations and a scoped `plugin-doctor` quality gate (31 rules, 0 findings) before the bot caught it — so no existing internal check covers this shape.
