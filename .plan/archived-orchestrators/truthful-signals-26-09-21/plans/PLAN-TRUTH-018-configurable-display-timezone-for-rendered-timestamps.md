# PLAN-TRUTH-018: A configurable DISPLAY timezone for rendered timestamps — storage stays UTC

> Renamed from **PLAN-204** on 2026-07-30 (see `plan-id-rename-map.md`).

epic: truthful-signals
workstream: WS-01

## Objective

Every timestamp this system stores and compares is UTC, and must stay UTC. Every timestamp it
*renders to the operator* is also UTC, and that is the actual pain: the operator reads them in CEST
and converts by hand, or the epic's standing rule forces "run `date` or say nothing".

Add a **display-only** timezone to run configuration, consumed at rendering surfaces exclusively.

## ⛔ The scoping decision, and why the obvious version is refused

The proposal as raised was *"configure the timezone at run-configuration and every time-resolving
should use this."* **The second half is refused, on evidence.** Storage and comparison stay UTC
unconditionally.

**Measured state at HEAD (orchestrator-verified 2026-07-29):** `marketplace/bundles/` contains **32**
time-resolution calls and **all 32 are `datetime.now(UTC)`**. The single bare `datetime.now()` match is
inside `pytest-testing/standards/testing-pytest.md` prose *warning against* wall-clock deadlines. The
tree is fully converged.

Four reasons a configured zone must not reach the write path:

1. **PLAN-109 (#1058) just spent a whole plan converging the last straggler onto UTC.** A configured
   write-zone re-opens exactly the class of defect that plan closed — and that defect was invisible
   until it produced an id whose prefix disagreed with the `created` field beside it.
2. **Cross-record comparison breaks silently.** Retention cutoffs, quiet-window comparisons, and
   ordering all compare records written at different times. Two records written under different
   configured zones are **incomparable, with no error** — the failure mode this epic is named after.
3. **Records cross machines and repos.** Lessons and findings move between this repo and consumer
   repos (API-Sheriff, nifi-extensions, TokenSheriff). A per-project write-zone makes a shared corpus
   internally inconsistent.
4. **DST makes civil-zone arithmetic wrong twice a year.** A configured civil zone has ambiguous and
   non-existent local times. Retention arithmetic across a DST boundary is off by an hour, silently.
   UTC has no such discontinuity.

⭐ **The operator's underlying complaint is real and is fully addressed by the display half.** The
inconvenience is *reading* UTC, not *storing* it.

## Deliverables

1. **D1 — GATE (mutates nothing): DERIVE the rendering surfaces.** Enumerate every place a stored
   timestamp is rendered for a human — landing/retrospective reports, `metrics.md`, the phase
   breakdown, decision/work log rendering, terminal title, operator-facing summaries, `inbox list`
   output. ⛔ **Classify each site as RENDER or STORE/COMPARE.** The knob reaches RENDER sites only,
   and the classification is the deliverable that makes the boundary enforceable.
2. **D2 — the knob.** A `display_timezone` run-config value (IANA name, default `UTC`), settable via
   `marshall-steward`, resolved through the ordinary run-config path. ⚠ **Default `UTC` means the
   unset behaviour is byte-identical to today** — no existing artifact changes unless the operator
   opts in.
3. **D3 — every rendered timestamp carries its zone label.** ⛔ **This is load-bearing, not
   cosmetic.** Converting a rendered timestamp without labelling it makes things *worse* than leaving
   it in UTC: the reader can no longer tell which zone they are looking at, and two artifacts rendered
   under different configs become indistinguishable. **An unlabelled converted timestamp is a
   regression and must fail the test suite.**
4. **D4 — a guard that the knob cannot reach the write path.** A test (or a doctor rule) asserting
   that no `store`/`compare` site consults `display_timezone`, derived over D1's classification rather
   than a hand-written list. ⚠ This is the deliverable that keeps the refusal above true a year from
   now, when the reason has been forgotten.
5. **D5 — tests, each verified to FAIL pre-fix.** (a) With the knob unset, every rendered timestamp is
   byte-identical to today. (b) With it set to a positive-offset zone, a rendered timestamp converts
   AND carries its label. (c) A stored timestamp is unchanged under any knob value. (d) The
   render-site population is derived and asserted non-empty.

## Claim Labels

- OBSERVED (orchestrator-verified at HEAD 2026-07-29): 32 `datetime.now(UTC)` call sites in
  `marketplace/bundles/`, zero live naive calls; the one bare `datetime.now()` is documentation prose
  arguing against it.
- OBSERVED (PLAN-109 landing #1058): the mixed-clock defect and its UTC convergence; the id prefix
  doubles as a sort key.
- HYPOTHESIS: the render/store split is cleanly separable — **confirm/refute at D1**. ⚠ If a single
  value is both stored and rendered from the same site (the lesson-id prefix is the known candidate:
  it is a **sort key** as well as a display string), that site is **STORE** and is out of scope.
  **Confirm/refute artifact**: D1's per-site classification.
- HYPOTHESIS: `marshall-steward` has an existing configuration surface this slots into rather than
  needing a new one (verify-at-outline).

## Expected Surface

- HYPOTHESIS: `manage-run-config` (or the resolved run-config path) for the knob itself
- HYPOTHESIS: `marshall-steward` configuration flow
- HYPOTHESIS: the render sites D1 derives — **deliberately not guessed here**
- OBSERVED: tests for whichever modules D1 identifies

## Dependencies and Sequencing

- Depends on: none. ⚠ **Read `landings/PLAN-109.md` first** — it establishes why the write path is
  UTC and what the mixed-clock failure looked like.
- Overlaps with: ⚠ **PLAN-TRUTH-009** (`surface-every-knob-in-marshal-json`, staged) — adding a knob and
  cataloguing knobs collide. **Sequence, or fold D2's surfacing into PLAN-TRUTH-009.**
- ⚠ Touches `marshall-steward`, which **PLAN-TRUTH-003**'s shim sweep also names. Verify before pairing.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-018-configurable-display-timezone-for-rendered-timestamps.md"
```

## Write-Boundary

This plan MUST NOT create or edit any file under `.plan/local/orchestrator/`. Its only channels back
to the epic are its PR and its `inbox/` OUTBOX.
