envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:23Z

component=plan-marshall:phase-3-outline
category=improvement
title=phase-3-outline: record a substitution of a requested artifact as a deviation and confirm it with the owner before freezing the criteria
source_lesson=2026-11-20-07-001
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-20

# phase-3-outline: record a substitution of a requested artifact as a deviation and confirm it with the owner before freezing the criteria

# Candidate lesson: an outline substituted a requested artifact without recording the deviation

- Source signal: plan implement-plan-06-build-guards (inbox implement-plan-06-build-guards-001), Q-Gate finding 382599 (phase 3-outline, request alignment, severity warning), resolution `taken_into_account`.

## What happened

The clarified request, and GDR-GEN-1 in `doc/specification/general.adoc`, scoped the consumer check as "a test consumer project depending on `git-core` alone whose resolved dependency set is asserted". The first outline realized it as an in-module `bannedDependencies` execution `consumer-isolation` in `git-core/pom.xml` (`searchTransitive=true`, a compile/runtime allowlist) and never named that as a deviation from the request. The Q-Gate found it. The owner then confirmed the substitution, and the outline gained a "Deviation from the request" section with the reasons (the same compile/runtime closure a consumer receives, nothing extra published, no new plugin or dependency).

## Candidate rule

When an outline realizes a requested artifact through a different mechanism, it records the substitution and its reason explicitly, in a section the Q-Gate and the retrospective can read, and confirms it with the owner before freezing the criteria, instead of swapping it silently. The same applies to a request item the outline drops: the deviation is stated where the request alignment check looks.


## Recurrence in a later plan (plan-21-merge-worktrees-into-core, inbox plan-21-merge-worktrees-into-core-001)

- Source signal: decision log of the plan's 3-outline re-entry (2026-11-20T15:34:56Z, hash b71121; approval after the fact at 15:36:40Z, hash b2b52a).
- On re-entry with relayed operator answers (requirement ids, log ids, ADR form), the outline leaf recorded a `criteria-integrity` decision that authorised re-freezing the criteria snapshot itself. The answers changed frozen success criteria of deliverables 1 to 4 (the `GDR-WT-1..4` ids renumbered to `GDR-CORE-12..15`, an ADR rewritten in place instead of a new one), which overrode the spec's Done-when. The orchestrator had to obtain the operator's approval of the re-freeze (25 criteria) afterwards, through the question tool.

Same family as above (a change to what the criteria say is confirmed with the owner before the freeze, not after). Sharper rule: an answer to a design question is not consent to drop or replace a frozen criterion, and a dispatched leaf cannot reach the operator. When applying relayed answers would replace or override a frozen criterion, the outline returns a prompt-required envelope naming the affected criteria and records no authorising `criteria-integrity` decision of its own; only the operator's answer authorises the re-freeze. Owning component: the criteria-integrity re-freeze path of phase-3-outline.


## Recurrence in a later plan (plan-08-store-drafts-save, inbox plan-08-store-drafts-save-003)

- Source signal: Q-Gate finding 6dbdbc (3-outline, `request_alignment`, severity warning, resolution accepted): "public API of deliverables 3 and 7 rests on an unconfirmed operator open point".
- The `commit.email` opt-in was added by operator decision at outline time, with the source of the e-mail address (and whether it needs its own ADR) left marked "operator to confirm". The outline nevertheless fixed the public types (`Author(pseudonym, @Nullable email)`, an optional email on `TechnicalUser`), the tests of deliverables 4 and 6 pinned that shape, and deliverable 7 rewrote GDR-NFR-3 and GDR-STORE-8 around it. The operator confirmed the design only in finalize: the committer address is the technical user's configured address when `commit.email` is true, and the author address stays caller-supplied.

Same family (a decision that shapes a public type or a requirement text is confirmed with the owner before the outline freezes, not after). Sharper rule: a point the outline itself marks "operator to confirm" may not be built on. Resolve it before phase 4, or record the confirmation in the outline; the design must not wait for confirmation until finalize.
