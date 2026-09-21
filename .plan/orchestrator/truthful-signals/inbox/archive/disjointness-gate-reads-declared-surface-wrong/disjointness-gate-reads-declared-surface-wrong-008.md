envelope_version=1
sender_type=plan
sender_id=disjointness-gate-reads-declared-surface-wrong
epic=truthful-signals
kind=candidate-lesson
created=2026-08-30T10:37:29Z

component=plan-marshall:plan-retrospective
category=bug
source_plan=disjointness-gate-reads-declared-surface-wrong
source_pr=1366

# The Phase Dispatch Boundaries section can never emit, and its absence is classified benign

## What happened

`compile-report` for this plan returned:

```
sections_written[17]: ...
sections_omitted[3]:
  - Executive Summary
  - Footprint Derivation Coverage
  - Phase Dispatch Boundaries
sections_dropped[0]:
```

The plan has **21 dispatch-boundary rows** across three phases, every one with
`present: true`, carrying `error_total_tokens: 1344170` for `6-finalize`.

## Root cause

The registry row is:

```python
('Phase Dispatch Boundaries', 'dispatch_boundaries', 'dispatch_boundaries'),
```

`should_emit` resolves the trigger against the **top level** of the fragment bundle:

```python
fragment = fragments.get(trigger_key)
if trigger_key == 'dispatch_boundaries':
    return _dispatch_boundaries_has_present_phase(fragment)
```

But nothing registers a top-level `dispatch_boundaries` fragment. `analyze-logs`
emits `dispatch_boundaries:` as a **nested block inside the `log-analysis`
fragment**, and SKILL.md Step 3's aspect table has no row that produces it
standalone. So `fragments.get('dispatch_boundaries')` is `None`,
`_dispatch_boundaries_has_present_phase(None)` returns `False`, and the section is
omitted — on every plan, whatever the data.

The dedicated `render_dispatch_boundaries_body` renderer and its per-phase table are
therefore unreachable. (The key *is* in `valid_aspect_keys()`, so a producer *could*
register it; none does.)

## Why it matters

Two compounding failures.

**1. The dead section is the one that publishes wasted spend.** Its own renderer
docstring says the `error_total_tokens` column is "the strongest proxy for
genuinely-wasted spend". For this plan that column is **1,344,170 tokens** — 24.8% of
the entire plan's dispatched budget, the six failed `pre-submission-self-review`
firings. That is the single most important efficiency figure of the run, and its
dedicated section silently did not render.

**2. The omission is classified as the BENIGN half of the partition.** The contract
defines `sections_omitted` as the case where "the section's trigger fragment was
absent or carried nothing renderable, so there was nothing to lose", against
`sections_dropped` as the LOUD half that forces `status: warning`. Here the payload
existed and was substantial; only the *lookup* failed. So a real loss is reported
under the branch that means no loss, and `compile-report` returns `status: success`.

This is the plan's own subject once more: a could-not-look outcome rendering as a
clean one. Three prior instances in this same run are already filed (rename-blind
footprint derivation; window-dependent ledger reconciliation; unarchived red CI run).

## Remedy shape

Either resolve the trigger where the data actually lives — read
`fragments['log-analysis']['dispatch_boundaries']` — or have `analyze-logs` register
the block as its own aspect. Additionally: a trigger key that resolves to `None` for
a registry row whose producer is expected to exist should be distinguishable from a
producer that ran and had nothing to say. A third state (`sections_untriggered`) or a
warning when a non-`None` trigger key is absent from the bundle would have surfaced
this on the first run instead of silently on every one.
