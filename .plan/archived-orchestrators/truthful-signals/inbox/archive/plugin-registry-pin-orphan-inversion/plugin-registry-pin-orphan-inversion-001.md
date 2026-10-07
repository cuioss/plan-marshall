envelope_version=1
sender_type=orchestrator
sender_id=plugin-registry-pin-orphan-inversion
epic=truthful-signals
kind=finding
created=2026-08-02T08:34:58Z

# generate_executor preflight reports `fresh` while the skill loader runs three versions stale

component: plan-marshall:tools-script-executor
category: bug
confidence: high
source_plan: none (ad-hoc session, observed at PLAN-TRUTH-010 launch)

## Context

Observed first-party 2026-08-02 while launching `PLAN-TRUTH-010`. `generate_executor preflight` returned:

```
status: success
executor_action: fresh
marshal_status: stale
installed_version: 0.1.1282
executor_version: 0.1.1282
```

`executor_action: fresh` is a **true statement about the executor and a misleading one about the
session**. At that same moment `~/.claude/plugins/installed_plugins.json` pinned all 10
`@plan-marshall` bundles at `0.1.1279`, so the Claude Code skill loader was serving SKILL.md and
workflow bodies three marketplace versions behind the executor the preflight had just blessed. The
skill base directory reported by the running session was `.../plan-marshall/0.1.1279/...` while every
script invocation resolved against 1282.

This is the epic's exact theme: a confident green over the half of the system the check can see, with
no signal at all about the half it cannot.

## Root cause

Two consumers, two oracles — the standing split recorded for this defect class:

- `preflight` compares the executor's embedded `MARSHALL_VERSION` against the dist-manifest. Both were
  1282, so it correctly reported `fresh`.
- Skill loading follows the `installed_plugins.json` registry pin, which `preflight` never reads.

The preflight's success predicate is therefore **structurally incapable** of detecting loader
staleness. It is not a wrong comparison; it is a comparison over the wrong population, reported with a
verdict word (`fresh`) that reads as whole-system.

## New sub-shape observed this run

Prior sightings (2026-07-27, 2026-08-01) were detectable by asserting *exactly one unmarked version
dir per bundle* — the unmarked one being the stale pin. This run returned **zero** unmarked dirs: all
35 version dirs carried `.orphaned_at`, including both the pinned 1279 and the newest 1282 (the GC had
marked its own keep-target). A detector written as "is the newest dir marked?" or "is there exactly one
unmarked dir?" fails on this instance. The correct assertion is `unmarked == [pinned_version]`, with
both `[]` and `[stale_version]` as failure states.

The stale pin was identifiable only because a second marker, `.in_use`, sat on 1279 and no other dir.

## Concrete cost this instance

1279 → 1282 spans `b5477589c` *"feat(build): require plan-id, relocate results, extend ledger (#1075)"*,
which moved the `kind=build` ledger contract — the exact surface `PLAN-TRUTH-010` D1/D2 was about to
design a subcommand discriminator against. Had the preflight's `fresh` been trusted as a whole-system
verdict, the plan would have specified a discriminator against a superseded contract, and the mismatch
would not have surfaced until execution.

Recurrence cadence is now roughly daily: the 08-01 repair installed 1279, and the pin was stale again
against 1282 within 24 hours.

## Proposed action

Two separable items. Neither is a classifier fix, which is why this is filed rather than folded into an
existing plan.

1. **Widen the preflight's population, or narrow its verdict.** Either have `preflight` read the
   registry pin and report loader staleness as its own field, or stop reporting a bare `fresh` that
   reads as whole-system when only the executor half was checked. Fail-closed framing: an unchecked
   half must not be reported as a clean half.
2. **Close the pin-advance gap.** `/sync-plugin-cache` writes new version dirs but does not advance the
   `installed_plugins.json` pin, so the GC re-inverts the markers and the loader drifts. This is
   recorded as long-standing residue (a) on this defect class and has now fired three times.

## Mapping onto existing plans — and what does NOT map

- Item 1 **is** an instance of `PLAN-TRUTH-010`'s D3 clause set (a classifier gating a clean pass on a
  signal that does not cover the claim). If the epic wants it there rather than standalone, it is a
  worked example, not new scope.
- Item 2 does **not** map onto any fail-closed-classifier clause. It is a write-side tool-layer gap in
  the sync/GC pair — no reader discipline recovers a pin that was never advanced. It needs its own
  owner and is the part to check for completeness rather than assume covered.

## Evidence

- `generate_executor preflight` output quoted above, run 2026-08-02 from the main checkout.
- `installed_plugins.json`: all 10 `@plan-marshall` entries at `installPath .../0.1.1279`.
- `diff -rq target/claude/plan-marshall ~/.claude/plugins/cache/plan-marshall/plan-marshall/0.1.1282`
  → identical apart from `__pycache__` and `.orphaned_at`, confirming 1282 as the correct build.
- Marker scan across all 10 bundles: 35/35 version dirs carried `.orphaned_at`; `.in_use` present on
  1279 only.
- Repaired manually (pins → 1282, `.orphaned_at` cleared on the ten 1282 dirs, `.in_use` set);
  post-repair assertion `unmarked == [pinned]` held for all 10 bundles.
