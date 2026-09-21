envelope_version=1
sender_type=plan
sender_id=a-rule-that-is-green-because-it-examined-nothing
epic=truthful-signals
kind=candidate-lesson
created=2026-08-08T18:54:00Z

component=pm-dev-java-cui:search-markers
category=anti-pattern
title=A standard described a suppression behaviour without naming where the suppression is enforced
confidence=high
source_plan=a-rule-that-is-green-because-it-examined-nothing
source_signal=pr-comment 55e176 (PR #1115, coderabbitai, resolution=fixed, remediated by TASK-006)

# A standard described a suppression behaviour without naming where the suppression is enforced

## Context

`pm-dev-java-cui/skills/search-markers/standards/marker-detection.md` § Signal A described what the `cui-rewrite:disable` marker does — "scoped to the CUI recipes this bundle defines", "silences the named CUI recipe and nothing else" — without naming **where that silencing is enforced**.

It is not enforced anywhere in this bundle. Signal A only detects and categorises: `auto_suppress` is a categorisation field, not an enforcement switch, and any marker present keeps `cmd_search` exiting `1`. The actual silencing is an external CUI OpenRewrite recipe contract.

## Root cause

The prose was locally scoped ("this bundle defines", "silences") in a document about this bundle's detector, so it read as describing this bundle's behaviour. Every individual statement was true of the *marker*; none was true of the *code the document describes*.

This is a specific, recurring shape: **a document describes a behaviour at a boundary its own component does not own, and the reader attributes the behaviour to the component.** The claim is not false — it is unattributed, which is harder to notice than a false claim because there is nothing to contradict.

## Proposed action

When a standard describes an effect (suppression, retry, rollback, cache invalidation) that is realised outside the component the document covers, name the enforcing party in the same sentence. A one-clause attribution ("honoured by the CUI recipe set and by nothing else, outside this bundle") converts an unattributed claim into a boundary statement.

Note the second-order point the resolution surfaced: naming the boundary **strengthened** the section's load-bearing conclusion rather than weakening it. The reason no local marker reaches AutoFormat is precisely that the marker is honoured externally. Authors avoid boundary attributions fearing they dilute a claim; here it was the opposite.

## Resolution in this run

TASK-006 added the enforcement boundary and left the AutoFormat coverage-boundary conclusion and the no-local-remedy statement intact. Landed as a follow-up commit on the PR branch (`3a9190f8`).

## Evidence

- PR #1115 inline comment `55e176` by `coderabbitai` at `marketplace/bundles/pm-dev-java-cui/skills/search-markers/standards/marker-detection.md:81`, reviewed commit `9f3c4755`, disposition `fixed`.
- Worth recording: CodeRabbit reached this by reading `search_markers.py` and the fixtures, not by reading the prose alone. The finding required cross-checking the document against the implementation — which is why no prose-only review round caught it.
