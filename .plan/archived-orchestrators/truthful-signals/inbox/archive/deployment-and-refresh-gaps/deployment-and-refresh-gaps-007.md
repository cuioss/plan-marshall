envelope_version=1
sender_type=orchestrator
sender_id=deployment-and-refresh-gaps
epic=truthful-signals
kind=candidate-lesson
created=2026-09-02T20:14:38Z

> **Relayed from Token-Sheriff.** Source epic `deployment-and-refresh-gaps`, plan `outbound-hostname-verification-core` (PR #689), original message `outbound-hostname-verification-core-009.md`.
> Filed there as a candidate-lesson and refused by `manage-lessons add` with `wrong_store`: the component names a `plan-marshall` bundle that the Token-Sheriff store does not own. Content is unmodified below.

# Candidate lesson: this epic's staged spec carried stale premises — re-ground ordinals and versions against HEAD before launch

**Component:** `plan-marshall:plan-orchestrator` (staged plan specs) / `plan-marshall:phase-2-refine`
**Category:** improvement
**Directly relevant to epic `deployment-and-refresh-gaps`**
**Evidence:** decision log `f31ffd` (WARNING, invalid premise), `0423a9` (stale detail)

## What was stale

`PLAN-03-outbound-hostname-verification-core.md` was staged against `checked_at d922fb0`. By the
time it launched:

1. **Load-bearing:** deliverable 3 and its `expected_surface` cited `doc/adr/0003-*.adoc` as the
   next free ADR ordinal (after `0002-*`). Actual: `doc/adr/` held `0001`-`0007`; ordinals
   `0003`-`0007` had landed via unrelated refresh-path and coverage plans **from this same
   epic**. Next free ordinal was `0008`. Corrected in `clarified_request`.
2. **Non-load-bearing:** the spec cited `cui-java-parent 1.5.9`; HEAD was on `1.5.10` (and moved
   to `1.5.11` mid-flight via #686). `version.cui.http` remained `2.1.0` at the same property
   location, so the mechanism and file/line claims survived.

Both were caught in `2-refine` and cost only the correction. The point is that they were caught
by a human-grade re-read, not by a mechanism.

## Why this is an epic-level lesson, not a plan-level one

The staleness was **self-inflicted by the epic's own throughput**: sibling plans in
`deployment-and-refresh-gaps` consumed the ADR ordinals that PLAN-03's spec had reserved by
assumption. Any epic that stages several specs up front against one HEAD, then lands them
serially, generates exactly this drift — and the later a spec launches, the staler it is.

## Rule

- A staged spec's `checked_at` is a **staleness clock**, not a provenance note. Any spec whose
  `checked_at` predates a sibling landing must be re-grounded before it is emitted as a
  `/plan-marshall` command.
- Never let a spec **reserve a monotonic resource by assumption** — ADR ordinals, migration
  numbers, port allocations. State the selection rule ("the next free ADR ordinal"), not the
  value (`0003`).
- The re-grounding verdict field (`corpus set-verdict` / `corpus verdicts`) is the mechanism
  that exists for this. This spec's premises were repaired by `2-refine` catching them, which
  works but is downstream of where the epic could have caught it.
