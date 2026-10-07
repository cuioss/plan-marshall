envelope_version=1
sender_type=plan
sender_id=retrospective-completeness-and-phase5-marker
epic=test-suite-quality
kind=candidate-lesson
created=2026-07-28T17:05:30Z

component=plan-marshall:plan-retrospective
category=bug
proposed_bundle=plan-marshall
origin_plan=retrospective-completeness-and-phase5-marker
origin_pr=1036

# D1's registered-implies-rendered guard is directional — a SECTION_SPEC row that NO producer registers is still dead, and one is dead right now

This plan's D1 closed the direction *producer exists, registry row missing*. The opposite
direction — **registry row exists, producer never registers it** — is uncovered, and
`dispatch_boundaries` is sitting in that gap today.

## Evidence from this run

`compile-report` reported:

```
sections_written[15]: … (15 sections)
sections_omitted[1]:
  - Phase Dispatch Boundaries
sections_dropped[0]:
```

`Phase Dispatch Boundaries` is classified **omitted**, i.e. the benign bucket ("the trigger
fragment was absent, so there was nothing to lose"). That classification is wrong here,
because the payload very much exists — `analyze-logs` produced it, richly:

```
dispatch_boundaries:
  4-plan:      1 row   289,886 tokens
  5-execute:   2 rows  322,584 tokens
  6-finalize:  9 rows  1,169,707 tokens   <- larger than phases 2-5 combined
```

The data is emitted **nested inside the `log-analysis` fragment**, under a
`dispatch_boundaries:` key. But `SECTION_SPEC` carries a *separate top-level row*
`('Phase Dispatch Boundaries', 'dispatch_boundaries', 'dispatch_boundaries')`, and
`should_emit` looks for a fragment **registered under that key**. No producer ever calls
`collect-fragments add --aspect dispatch_boundaries` — the plan-retrospective SKILL.md
Step-3 aspect table does not list `dispatch_boundaries` as an aspect at all.

So the section can never render, on any plan, and it fails **quietly into the benign
bucket** rather than the loud one. The finalize-phase token accounting — the single largest
cost centre in the plan, and the number `metrics.md` renders as a blank row — is dropped on
the floor twice over.

## Why the new D1 guard does not catch it

`test_registered_aspects_render.py` is a good test and its docstring is explicit that it
"asserts both directions". The two directions it asserts are:

- **(a) registerable ⇒ renderable** — every `_registerable_aspect_keys()` member has a
  `SECTION_SPEC` row or hits the generic fallback. `dispatch_boundaries` **has** a row, so it
  passes trivially.
- **(b) dispatched ⇒ has a static row** — every key the workflow literally dispatches has a
  row. `dispatch_boundaries` is **never dispatched**, so it is not in the population at all.

Neither direction is **(c) has a row ⇒ some producer registers it**. A row with no producer
is invisible to both.

There is a second, independent blind spot stacked on the first: the producer scanner is

```python
_ASPECT_DISPATCH_RE = re.compile(r'--aspect\s+([a-z][a-z0-9-]*)')
```

`dispatch_boundaries` contains an **underscore**, which `[a-z0-9-]*` cannot match. So even if
a producer were added tomorrow with a literal `add --aspect dispatch_boundaries`, the scan
would silently skip it and direction (b) would stay vacuous for this key. It is the only
underscore-bearing key in `SECTION_SPEC`, which is exactly why nobody noticed.

## Corrective rule

**A render registry and its producer set must be checked in BOTH directions, and the
"nothing to render" bucket must not absorb a row that no producer can ever fill.**

Concretely:

1. Add direction (c) to `test_registered_aspects_render.py`: every non-underscore-prefixed
   `SECTION_SPEC` `fragment_key` must be either in the scanned producer population or on an
   **explicit, justified** exemption list. `dispatch_boundaries` fails this today — either
   give it a producer (split it out of the `log-analysis` fragment, which is the useful fix
   given the payload's value) or drop the row.
2. Widen `_ASPECT_DISPATCH_RE` to `[a-z][a-z0-9_-]*` and add a non-degeneracy anchor pinning
   that an underscore-bearing key is matched — otherwise fixing (1) leaves the scanner
   unable to see the fix.
3. `sections_omitted` must not be a silent bucket for a *structurally unfillable* row.
   Omission is benign only when a producer COULD have registered and legitimately did not.

## Impact

Every retrospective on every plan loses the phase-dispatch-boundary section — the only place
per-step finalize token/duration attribution is rendered. Beyond this one key, the missing
direction means any future `SECTION_SPEC` row added without a matching producer ships dead
and reports itself as benign, which is the exact defect archetype D1 existed to close.

## Note on scope

This is adjacent to but distinct from the already-filed `architecture-refresh` classification
lesson: that one is *two documents disagreeing*, this one is *one registry with no
counterparty*. The shared root is the same recurring shape — a guard that checks one side of
a two-sided contract.
