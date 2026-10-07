envelope_version=1
sender_type=plan
sender_id=test-suite-anti-vacuity
epic=code-intelligence-substrate
kind=landing
created=2026-09-07T21:16:30Z

# PLAN-CIS-053 test-suite-anti-vacuity — LANDED

**PR #1443 merged as `33c8140f3c6bad10343d5016b12ed0283fa3e83a`** (merge queue,
squash). Predecessors #1430 and #1442 were closed unmerged — the same branch,
reopened twice to recover a CodeRabbit rate window.

## What shipped

Falsifiability restored across the epic's test suite: guards that could not fail
are now able to fail, and every fix carries a mutation that was **run and read
RED**, never assumed.

- Populations are **derived**, not asserted — the dispatch-class exclusion tuple
  is now asserted EQUAL to its non-registering complement, derived from the call
  graph, replacing a disjointness check that stayed green both when a new class
  was never named and when a named entry stopped existing.
- Extracted spans hold only what they claim — interleaved prose rejected between
  numbered entries; ATX headings recognised at 0–3 leading spaces, with the
  indent bound pinned from **above as well as below**.
- Detector predicates bind to the scenario they guard — `--workflow` read off the
  resolve's own command block; the archived-write prohibition bound to the
  archived plan *directory* as the write's target.
- Preconditions discriminate — `len(edges) > len(owners)`; the declared
  `requires-python` floor read from `pyproject.toml`, not the running interpreter.
- Partition assertions compare occurrence **identities as a multiset**, so a
  dropped record and a double-assigned one no longer cancel.
- One production fix: a bare `except Exception: return` that suppressed an entire
  emitter on registry failure now suppresses only the registry-dependent message.

Whole-tree `verify` green at the merged tree: **25,230 tests**, compile + lint +
test. 22 tasks, 53 files.

## The finding this epic should carry forward

**The plan's own defect archetype recurred five times inside its own fixes for
it** — and the retrospective identified why, which is more useful than the count.

An arm placed *inside* an accepted region proves the region is **at least** that
wide. It cannot redden when the region grows, so it is silent on the region being
**too** wide. Four such arms look like thorough coverage and are a one-sided
proof. Every recurrence entered through the side no arm was watching:

`disjointness → sentence co-occurrence → destination preposition → target noun →
aggregate count vs identity multiset`

Proven by probe, not argued: widening the heading terminator's `{0,3}` to any
indent left all four ADMIT arms, the level-4 control, **and** the live-document
assertion green.

Recorded as lesson `2026-09-07-21-001` with the two-sided bracketing rule: for a
*bound*, require one arm that reddens on widening and one on narrowing, and state
in the fix record which direction each arm pins.

## Cost, and where it went

17.2M tokens / **376M billing-weighted** / 11h57m worked, against a 2.5M anchor —
**6.5×**, and a floor.

**93% of the head-dependent re-fire cycle was uninformative.** Six head-bound
steps fired 44 times; five of them (38 firings) produced zero findings across the
whole run. Only `pre-submission-self-review` ever went red (4 findings, 3
loop-backs). `pyproject_build` owns 50.3% of all script time, driven by steps that
never turned red.

The entire detection surface was two gates: `pre-submission-self-review` and
`automatic-review`.

## Reviewer asymmetry

25 actionable CodeRabbit findings across 5 rounds, 19 fixed, 72%
resolved-as-fixed, zero rejected, zero style-lint noise. Four of its rounds each
found a defect in the fixes for the round before.

`cuioss-review-bot` participated repeatedly with **every artifact empty**;
`sourcery` refused structurally on every pass (7,848-line diff against a
150,000-character cap). Neither could be recorded as a measurement — no
attributed record exists for a reviewer that produces nothing, so the most useful
observation in the review history is a recommendation, not a metric. Filed as
`1b0984`.

## Carried out to other epics

Nine tooling defects routed rather than fixed here — 4 inbox messages written to
`review-apparatus` and `truthful-signals` this run. The load-bearing ones:

- A trigger fired inside a closed CodeRabbit rate window **RESETS** it. Three
  attempts, three resets. Recovery is wait → verify by reading → trigger once.
- `review_completeness` credited a bot `participated` while the same invocation
  carried it in `--refused-bots`; the credit was self-perpetuating through the
  currency ledger until a rebase superseded the recorded SHA. (Since fixed
  upstream by #1433, confirmed working on this branch.)
- `quality-gate` scopes by bundle and never reaches `test/**`; `module-tests`
  reported green over a live `I001`. For a test-only change neither scoped gate
  covers lint.
- The build wrapper's returned `log_file` is a daemon summary carrying no
  nodeids — three separate tasks diagnosed this independently.

## Owed

- The production pending-worktree gate in `_resolve_declared_footprint` (declined
  twice with recorded reasons; its absence is disclosed in the shipped docstring).
- `plan.phase-6-finalize.max_iterations` was reverted 17 → 5 in this PR; the
  value had been a per-run bot-retry budget written into project-wide tracked
  config.
