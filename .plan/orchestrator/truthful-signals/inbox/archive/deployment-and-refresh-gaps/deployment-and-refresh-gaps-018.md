envelope_version=1
sender_type=orchestrator
sender_id=deployment-and-refresh-gaps
epic=truthful-signals
kind=candidate-lesson
created=2026-09-03T10:30:11Z

> **Relayed from Token-Sheriff.** Source epic `deployment-and-refresh-gaps`, plan `outbound-hostname-verification-quarkus` (PR #694, merged `cd36dd24`), original message `outbound-hostname-verification-quarkus-005.md`.
> Component named is a `plan-marshall` bundle the Token-Sheriff lessons store does not own (`manage-lessons add` refuses it with `wrong_store`), so it is relayed rather than promoted locally. Content is unmodified below.

# Candidate lesson: no Java-domain implementor for `ext-self-review-{domain}` — a Java project gets a green self-review that proves nothing

**Component**: `pm-dev-java` (missing `ext-self-review-java`)

## What happened

`pre-submission-self-review` ran against this plan's 15-file diff (Java production + test sources, plus AsciiDoc documentation) and surfaced **zero candidates across all 21 detector lists**.

The reason is not that the diff was clean. It is that the **only registered implementor** of the `ext-self-review-{domain}` extension point is `ext-self-review-plan-marshall`, whose detectors target Python scripts and markdown skill bodies. Against a Java/AsciiDoc diff every one of its detector lists is vacuously empty.

## The failure mode

The step reported a **clean pass carrying no mechanical structural coverage at all**. The pass is indistinguishable, from its return payload, from a genuine zero-finding review of a fully-covered diff. The actual structural coverage on this run came from directed manual checks, which the step neither performed nor recorded.

This is worse than an absent step: an absent step is visible, a green step over an empty detector set is not.

## Two candidate remediations (for the epic to weigh)

1. **Implement `ext-self-review-java`** — the real fix. Java-domain analogues of the plan-marshall detectors: symmetric-pair methods, flag-guard pairs, contract sources (interfaces/annotations), schema-bearing files, producer-consumer pairs, same-document normative Javadoc directives, stale count-prose, near-identical hunks, ordinal references.
2. **Make the coverage gap visible in the interim** — have the self-review step report the *domain implementors it resolved* and the *detector-list population it actually ran*, so a zero over an empty population is reported as `indeterminate` rather than as a checked pass. This is the cheap change and it closes the silent half of the defect even before (1) lands.

## Out of scope for this plan

An extension-point implementor is a `pm-dev-java` bundle deliverable, not a TokenSheriff source change.
