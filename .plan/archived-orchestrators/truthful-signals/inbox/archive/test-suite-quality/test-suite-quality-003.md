envelope_version=1
sender_type=orchestrator
sender_id=test-suite-quality
epic=truthful-signals
kind=finding
created=2026-07-28T17:42:22Z

# LIVE: `dispatch_boundaries` is a `SECTION_SPEC` row no producer can ever fill — and it fails into the BENIGN bucket

Handed over from epic `test-suite-quality` at its close (2026-07-28). Folded into lesson
`2026-07-27-08-005` as its second instance.

**This is a `truthful-signals` defect by construction**: the report says "omitted — nothing to
render" (benign) about a section whose payload exists, is large, and is being discarded.

## The defect

`compile-report` on PR #1036's run reported:

```text
sections_written[15]: … (15 sections)
sections_omitted[1]:
  - Phase Dispatch Boundaries
sections_dropped[0]:
```

`Phase Dispatch Boundaries` landed in the **benign** bucket — the one meaning "the trigger
fragment was absent, so there was nothing to lose". **That classification is wrong here.** The
payload exists and `analyze-logs` produced it richly:

```text
dispatch_boundaries:
  4-plan:      1 row     289,886 tokens
  5-execute:   2 rows    322,584 tokens
  6-finalize:  9 rows  1,169,707 tokens   <- larger than phases 2-5 combined
```

The data is emitted **nested inside the `log-analysis` fragment** under a `dispatch_boundaries:`
key. But `SECTION_SPEC` carries a *separate top-level row*
`('Phase Dispatch Boundaries', 'dispatch_boundaries', 'dispatch_boundaries')`, and `should_emit`
looks for a fragment **registered under that key**. No producer ever calls
`collect-fragments add --aspect dispatch_boundaries` — the plan-retrospective Step-3 aspect
table does not list `dispatch_boundaries` as an aspect at all.

**So the section can never render, on any plan**, and the finalize-phase token accounting — the
single largest cost centre in a plan, and the number `metrics.md` renders as a blank row — is
dropped on the floor twice over.

## This is the MIRROR of the defect PLAN-10's D1 just closed

- **D1 closed**: producer exists, registry row missing (`direct-gh-glab-usage`,
  `execution-context-dispatch-audit` — both now registered).
- **Still open**: registry row exists, producer never registers it.

D1's new population-derived detector cannot see it. `test_registered_aspects_render.py` asserts
two directions and its docstring is explicit that it "asserts both directions":

- **(a) registerable ⇒ renderable** — `dispatch_boundaries` **has** a row, so it passes trivially.
- **(b) dispatched ⇒ has a static row** — `dispatch_boundaries` is **never dispatched**, so it
  is not in the population at all.

Neither direction is **(c) has a row ⇒ some producer registers it**. A row with no producer is
invisible to both.

## A second, stacked blind spot

```python
_ASPECT_DISPATCH_RE = re.compile(r'--aspect\s+([a-z][a-z0-9-]*)')
```

`dispatch_boundaries` contains an **underscore**, which `[a-z0-9-]*` cannot match. So even if a
producer were added tomorrow with a literal `add --aspect dispatch_boundaries`, the scan would
silently skip it and direction (b) would stay vacuous for this key. **It is the only
underscore-bearing key in `SECTION_SPEC`** — which is precisely why nobody noticed.

## Suggested fix

1. **Add direction (c)** to `test_registered_aspects_render.py`: every non-underscore-prefixed
   `SECTION_SPEC` `fragment_key` must be either in the scanned producer population or on an
   **explicit, justified** exemption list. `dispatch_boundaries` fails this today.
2. **Widen `_ASPECT_DISPATCH_RE`** to `[a-z][a-z0-9_-]*` and add a non-degeneracy anchor pinning
   that an underscore-bearing key is matched — otherwise fixing (1) leaves the scanner unable to
   see the fix.
3. **Give `dispatch_boundaries` a producer** — split it out of the `log-analysis` fragment,
   which is the useful direction given the payload's value — **or drop the row**.
4. **`sections_omitted` must not be a silent bucket for a structurally unfillable row.** Omission
   is benign only when a producer COULD have registered and legitimately did not.

## Sibling residue in the same lesson

`2026-07-27-08-005` also carries the `_executive-summary` row, the original instance of this
same shape: always emitted (`conditional_trigger = None`), no producer, so every compiled report
opens with `_No executive summary provided._`. Both should be settled together — same fix
direction, same guard gap.
