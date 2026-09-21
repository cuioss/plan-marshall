envelope_version=1
sender_type=plan
sender_id=a-rule-that-is-green-because-it-examined-nothing
epic=truthful-signals
kind=candidate-lesson
created=2026-08-08T18:50:39Z

component=plan-marshall:manage-architecture
category=anti-pattern
title=A central standard claimed N sibling skills bind an obligation when only 1 of them did
confidence=high
source_plan=a-rule-that-is-green-because-it-examined-nothing
source_signal=qgate-finding cdf8f4 (6-finalize, pre-submission-self-review)

# A central standard claimed N sibling skills bind an obligation when only 1 of them did

## Context

`manage-architecture/standards/arch-gate-fitness-functions.md` line 42 stated that "the per-domain arch-gate skills bind this obligation to their native tool's rule form and to the tool-specific ways a rule can go vacuous there". The same document's domain table names three: Java (ArchUnit), Python (import-linter), JavaScript (dependency-cruiser).

Only `arch-gate-java` bound it — and only because this plan had just added the binding row. `arch-gate-python` and `arch-gate-js` carry neither a Negative-control binding row nor any tool-specific vacuity note. A content sweep over 4249 inventoried files (0 unreadable, not truncated, 0 elided) returned `arch-gate-java` as the only per-domain hit for the phrase.

## Root cause

The sentence was written from the *intent* of the design (each domain skill binds the central obligation to its own tool) rather than from an enumeration of the skills it names. Because the author had just made the claim true for one skill, the claim read as true. Nothing in the document, and no lint rule, cross-checks a plural claim about a named set against the members of that set.

The failure is invisible at the claim site: a reader of the central doc has no reason to doubt it, and a reader of `arch-gate-python` simply finds none of the guidance the central doc promised exists there — with no signal that anything is missing.

## Proposed action

Treat a **plural claim about a named set of components** the same way the marketplace already treats an index table: it must be verified against every member of the set in the same change that authors it. Concretely:

- When a document names a set (a domain table, a skills list, a bundle enumeration) and then makes a claim about "the X skills", cross-check each member before landing, or narrow the claim to the members that actually satisfy it.
- Prefer the narrow form: name the skill that carries the binding rather than asserting the class does.

This is the set-cardinality sibling of the existing `agent-behavior-rules.md` rule "A newly-authored index/summary table must enumerate every member of the set it indexes" — same obligation (describe the set accurately), different surface (prose claim rather than table).

## Resolution in this run

Line 42 was narrowed: the central doc now states what a per-domain skill adds and names `pm-dev-java:arch-gate-java` as the skill carrying the ArchUnit binding, instead of asserting all three domain skills bind it. Bringing `arch-gate-python` and `arch-gate-js` up to the claim is new work in untouched skills and was correctly deferred.

## Evidence

- Q-Gate finding `cdf8f4`, phase `6-finalize`, source `pm-plugin-development:ext-self-review-plan-marshall`, severity warning, resolution `fixed`.
- File: `marketplace/bundles/plan-marshall/skills/manage-architecture/standards/arch-gate-fitness-functions.md` line 42-43.
- Corroborated post-merge by CodeRabbit on PR #1115 (comment `1f7631`), which reached the same conclusion independently and proposed the same two branches.
