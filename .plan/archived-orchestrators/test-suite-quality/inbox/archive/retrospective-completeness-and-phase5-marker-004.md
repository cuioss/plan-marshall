envelope_version=1
sender_type=plan
sender_id=retrospective-completeness-and-phase5-marker
epic=test-suite-quality
kind=candidate-lesson
created=2026-07-28T16:26:22Z

component=plan-marshall:phase-6-finalize
category=bug
proposed_bundle=plan-marshall
origin_plan=retrospective-completeness-and-phase5-marker
origin_pr=1036

# LIVE, UNRESOLVED: `architecture-refresh` is classified BOTH dispatched and inline, in two documents, one of which declares itself the single source of truth

Verified in the tree at landing time (2026-07-28, at `6d51ae704`). Not fixed by this plan —
out of its 10-file footprint. **This is an open defect, not a historical note.**

## The contradiction

`standards/dispatch-inline-split.md` opens with:

> "This document is **the single source of truth** for which of the default + project
> finalize steps **dispatch** … and which run **inline**."

and carries a **closure invariant** at `:9`:

> "Every step … carries **exactly one** classification: it appears in either the dispatched
> roster or the inline roster, **never both and never neither**."

Under `## Dispatched steps`, `dispatch-inline-split.md:23`:

> `default:architecture-refresh` — hybrid, **classified dispatched** … "The dispatching tier
> governs the classification, so the step carries exactly one roster row."

But `phase-6-finalize/SKILL.md` names it inline at **two** sites:

- `SKILL.md:889` — "BUILT-IN (**inline-only**: push, ci-verify, **architecture-refresh**,
  branch-cleanup, record-metrics, archive-plan): Read the standards document … and follow
  all steps **in main context**."
- `SKILL.md:992` — "**Inline-only steps** (push, **architecture-refresh**, branch-cleanup,
  record-metrics, archive-plan) skip this call uniformly" (the 5c dispatch-boundary
  metrics row).

The pre-dispatch brief described this as one site against one; it is **two against one**.

Corroborating runtime evidence: this plan's `architecture-refresh` step recorded
`outcome=done, display_detail="no module structure changed"` with **no `[DISPATCH]` line and
no 5b/5c agent-usage row** — i.e. the runtime followed SKILL.md's inline classification, not
the declared source of truth. So the divergence is not merely documentary: the declared SSoT
is the side that is **not** being obeyed.

## Why it matters beyond tidiness

1. **The closure invariant is pinned by a test that cannot see the violation.**
   `test/plan-marshall/phase-6-finalize/test_dispatch_roster_closure.py` derives the
   registered step set from `marshal.json` and compares it against
   `dispatch-inline-split.md`'s two rosters — `test_roster_lists_are_disjoint` even asserts
   in so many words that no step is "classified BOTH dispatched and inline". It **does**
   open `SKILL.md` (`_SKILL_DOC`), but only for the count-claim sweep (c) and the
   `[DISPATCH]`-emit pairing (e); **no assertion ever reads SKILL.md for the
   dispatched/inline classification.** So a step listed dispatched in the roster and inline
   at two places in SKILL.md passes every one of these tests green. The guard for
   "exactly one classification" enforces it within one document while the second document
   is already open in the same test module. **A guard that checks one of two disagreeing
   documents is a vacuous guard** — the same archetype this epic has now hit five times,
   here inside the guard for the very invariant it protects.
2. **Real behavioural consequences.** Dispatched vs inline decides whether the step gets a
   `[DISPATCH]` work-log line, an `execution-context-{level}` envelope, and a 5b/5c
   agent-usage + dispatch-boundary metrics row. Classified inline, `architecture-refresh`'s
   Tier-1 per-module LLM re-enrichment — described in the roster as "the only per-iteration
   parallel dispatch in the contract" — is unattributed in metrics and unaudited in the
   dispatch chain.
3. **`architecture-refresh` is the hard case, so it is the one that drifts.** It is genuinely
   hybrid (deterministic Tier-0 discover+diff, LLM Tier-1 fan-out). A single boolean
   classification over a two-tier step is exactly the kind of contract that gets restated
   differently in two places.

## Corrective rule

**When a document declares itself the single source of truth for a classification, no other
document may restate that classification — it may only point at it.** Two documents agreeing
today is not safety; it is two things to keep in sync.

Concretely:
1. Replace both SKILL.md inline-only enumerations (`:889`, `:992`) with a pointer to
   `dispatch-inline-split.md` § "Inline steps". SKILL.md already does exactly this correctly
   for the PROJECT/SKILL branch at `:892-900` ("Look the step up in the roster — do NOT infer
   the class from any example named in this branch"). The BUILT-IN branch was never given
   the same treatment. **The fix pattern already exists in the same file.**
2. Extend `test_dispatch_roster_closure.py` to also parse SKILL.md's inline-only
   enumerations and assert they are either absent or roster-derived — closing the
   vacuous-guard gap in (1) above. The module already holds `_SKILL_DOC`, so this is an
   added assertion, not new plumbing. The population must be **derived from the roster**,
   never a hardcoded step list (the standing epic rule).
3. Settle the substantive question first: is `architecture-refresh` dispatched or inline?
   The runtime says inline; the SSoT says dispatched. **The divergence must not be closed by
   editing whichever document is easier to reach.**

## Impact

Any maintainer routing a finalize step, and any consumer of finalize dispatch metrics. The
`display_detail`/metrics gap is silent — the step reports `done` either way.
