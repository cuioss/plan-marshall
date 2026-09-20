envelope_version=1
sender_type=plan
sender_id=a-rule-that-is-green-because-it-examined-nothing
epic=truthful-signals
kind=candidate-lesson
created=2026-08-08T18:52:29Z

component=plan-marshall:phase-3-outline
category=anti-pattern
title=Deliverable ordering asserted in Approach prose is not an ordering — phase-4-plan reads only depends metadata
confidence=high
source_plan=a-rule-that-is-green-because-it-examined-nothing
source_signal=qgate-finding c69606 (3-outline)

# Deliverable ordering asserted in Approach prose is not an ordering — phase-4-plan reads only depends metadata

## Context

`solution_outline.md`'s Approach section stated that deliverable 1 is the gate and runs first — the premise deliverables 2 and 3 depend on, and the premise that makes the plan's deliberate absence of a retrofit correct. Deliverable 2's Metadata declared `depends=none`.

Deliverable 3 declared `depends=2`, so the outline author demonstrably knew the mechanism. The ordering was simply stated in the wrong place.

## Root cause

`phase-4-plan` orders tasks from the `depends` metadata, never from Approach prose. An ordering constraint written only in prose is therefore **inert**: deliverable 2 could be scheduled before, or concurrently with, the gate — making deliverable 1 a gate that gates nothing.

The prose reads as a constraint and is consumed by a human reviewer as one, which is exactly why it survives review. The machine that would enforce it never sees it.

## Proposed action

- **Authoring rule**: any ordering claim in an outline's Approach section must be encoded in the corresponding deliverable's `depends` field in the same edit. Prose may explain an ordering; it may never be the only place the ordering exists.
- **Candidate deterministic Q-Gate check** (this instance was caught by an LLM Q-Gate pass, not by a rule): scan the Approach narrative for ordering language ("runs first", "is the gate", "before", "after", "once X is done") that names a deliverable, and cross-check that the named pair has a corresponding `depends` edge. A prose-asserted edge with no metadata counterpart is a finding.

## Why this belongs to `truthful-signals`

The plan's own theme applied to the plan's own ordering: **an ordering constraint that is green because nothing enforced it.** The Q-Gate reviewer named it in exactly those words.

## Resolution in this run

Deliverable 2's Metadata changed from `depends=none` to `depends=1`. A symmetric-peer audit of all four `depends` fields confirmed the rest were correct as authored (1 is the gate and runs first; 3 already declared `depends=2` and inherits transitively; 4 is genuinely independent of the arch-gate chain). No scope, affected-files, verification, or success-criteria change.

## Evidence

- Q-Gate finding `c69606`, phase `3-outline`, type `triage`, severity warning, resolution `taken_into_account`.
- The symmetric-peer audit is itself worth noting as good practice: the fix did not stop at the one flagged field but checked every peer of the same kind.
