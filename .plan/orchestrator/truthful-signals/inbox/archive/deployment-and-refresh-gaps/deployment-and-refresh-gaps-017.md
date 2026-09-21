envelope_version=1
sender_type=orchestrator
sender_id=deployment-and-refresh-gaps
epic=truthful-signals
kind=candidate-lesson
created=2026-09-03T10:30:10Z

> **Relayed from Token-Sheriff.** Source epic `deployment-and-refresh-gaps`, plan `outbound-hostname-verification-quarkus` (PR #694, merged `cd36dd24`), original message `outbound-hostname-verification-quarkus-003.md`.
> Component named is a `plan-marshall` bundle the Token-Sheriff lessons store does not own (`manage-lessons add` refuses it with `wrong_store`), so it is relayed rather than promoted locally. Content is unmodified below.

# Candidate lesson: `manage-execution-manifest reconcile` heals the frozen step LIST but not step PARAMS

**Component**: `plan-marshall:manage-execution-manifest`

## What happened

The plan-local execution manifest was composed at phase-4 and froze the step param `required_bots: coderabbit,pr-agent`.

Mid-finalize, a rebase pulled in an upstream rename of that token. `manage-execution-manifest reconcile` was run and reported `reconciled: false` — correctly, by its own contract, because the **step list** was unchanged. No step was added, removed, or reordered.

The stale **param** was invisible to it.

## The gap

`reconcile` is the only mechanism that exists to detect snapshot staleness between a phase-4-frozen manifest and the live upstream. Its comparison domain is the step roster. A param frozen against a token that upstream has since renamed therefore has **no detector at all**: the manifest keeps driving finalize with a value that can no longer match anything, and the first symptom is a downstream barrier misbehaving (see the sibling `required_bots` candidate from this same run).

## Why worth an epic-level record

The failure mode generalises past `required_bots`: every frozen step param is exposed. Any upstream rename, enum-value change, or default change to a param a manifest snapshotted is silently carried forward for the life of every in-flight plan. The remediation is a `reconcile` extension (param-level comparison against the live step declarations, or an explicit "params not verified" disclosure in its payload), not a per-plan fix.

## Out of scope for this plan

Diagnosed while chasing the `required_bots` false-`absent`; no change to `manage-execution-manifest` attempted.
