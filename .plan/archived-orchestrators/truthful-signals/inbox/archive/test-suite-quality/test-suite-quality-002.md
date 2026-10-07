envelope_version=1
sender_type=orchestrator
sender_id=test-suite-quality
epic=truthful-signals
kind=finding
created=2026-07-28T17:42:14Z

# LIVE: `architecture-refresh` carries TWO classifications, and the runtime obeys the non-authoritative one

Handed over from epic `test-suite-quality` at its close (2026-07-28). Verified live in the
tree at PLAN-10's landing (`6d51ae704`); outside that plan's 10-file footprint, so unfixed.
Filed as lesson `2026-07-28-19-003`.

**This fits `truthful-signals` squarely**: a document that declares itself the single source of
truth is the confident signal; that the runtime ignores it is the caveat.

## The contradiction

`phase-6-finalize/standards/dispatch-inline-split.md` opens by declaring itself

> "the **single source of truth** for which of the default + project finalize steps
> **dispatch** … and which run **inline**"

and carries a closure invariant at `:9`:

> "Every step … carries **exactly one** classification: it appears in either the dispatched
> roster or the inline roster, **never both and never neither**."

At `:23`, under `## Dispatched steps`, it classifies `default:architecture-refresh` as
**dispatched** — "hybrid, classified dispatched … The dispatching tier governs the
classification, so the step carries exactly one roster row."

`phase-6-finalize/SKILL.md` names the same step **inline** at two sites:

- `:889` — "BUILT-IN (**inline-only**: push, ci-verify, **architecture-refresh**,
  branch-cleanup, record-metrics, archive-plan): … follow all steps **in main context**."
- `:992` — "**Inline-only steps** (push, **architecture-refresh**, branch-cleanup,
  record-metrics, archive-plan) skip this call uniformly" (the 5c dispatch-boundary metrics row).

It is **two sites against one**. An earlier brief described it as one against one — that was
wrong.

## The runtime obeys SKILL.md, not the declared SSoT

PLAN-10's own `architecture-refresh` step recorded `outcome=done`,
`display_detail="no module structure changed"`, with **no `[DISPATCH]` line and no 5b/5c
agent-usage row**. So the divergence is not merely documentary: **the side that is NOT the
declared source of truth is the side being executed.**

## Why the guard does not catch it

`test/plan-marshall/phase-6-finalize/test_dispatch_roster_closure.py` derives the registered
step set from `marshal.json` and compares it against `dispatch-inline-split.md`'s two rosters.
`test_roster_lists_are_disjoint` asserts in so many words that no step is classified BOTH
dispatched and inline.

The module **does** open `SKILL.md` (`_SKILL_DOC`) — but only for the count-claim sweep and the
`[DISPATCH]`-emit pairing. **No assertion ever reads SKILL.md for the dispatched/inline
classification.** A step listed dispatched in the roster and inline at two places in SKILL.md
passes every one of these tests green.

**A guard that checks one of two disagreeing documents is a vacuous guard** — here inside the
guard for the very invariant it protects, with the second document already open in the same
test module.

## Why it matters beyond tidiness

Dispatched vs inline decides whether the step gets a `[DISPATCH]` work-log line, an
`execution-context-{level}` envelope, and a 5b/5c agent-usage + dispatch-boundary metrics row.
Classified inline, `architecture-refresh`'s Tier-1 per-module LLM re-enrichment — which the
roster itself calls "the only per-iteration parallel dispatch in the contract" — is
**unattributed in metrics and unaudited in the dispatch chain**. The step reports `done` either
way, so the gap is silent.

`architecture-refresh` is genuinely hybrid (deterministic Tier-0 discover+diff, LLM Tier-1
fan-out). A single boolean classification over a two-tier step is exactly the contract that
gets restated differently in two places — which is why this is the one that drifted.

## ⚠ Sequencing constraint for whoever takes this

**Settle the substantive question FIRST: is `architecture-refresh` dispatched or inline?**
The runtime says inline; the SSoT says dispatched. **The divergence must not be closed by
editing whichever document is easier to reach** — that would ratify whichever answer is
cheapest rather than whichever is correct.

Once settled:

1. Replace both SKILL.md inline-only enumerations (`:889`, `:992`) with a pointer to
   `dispatch-inline-split.md` § "Inline steps". **The fix pattern already exists in the same
   file**: SKILL.md does exactly this for the PROJECT/SKILL branch at `:892-900` ("Look the
   step up in the roster — do NOT infer the class from any example named in this branch").
   The BUILT-IN branch was never given the same treatment.
2. Extend `test_dispatch_roster_closure.py` to parse SKILL.md's inline-only enumerations and
   assert they are absent or roster-derived. The module already holds `_SKILL_DOC`, so this is
   an added assertion, not new plumbing. **The population must be derived from the roster**,
   never a hardcoded step list.

## Generalisable rule

**When a document declares itself the single source of truth for a classification, no other
document may restate that classification — it may only point at it.** Two documents agreeing
today is not safety; it is two things to keep in sync.
