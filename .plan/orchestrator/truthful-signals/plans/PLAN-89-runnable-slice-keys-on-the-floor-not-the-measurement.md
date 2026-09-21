# PLAN-89: The Runnable-Slice Rule Keys On The FLOOR, Not The Measurement — So A 15-Second Compile Is Orchestrator-Tier

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Raised 2026-07-27 by the PLAN-62 landing (#1022) via inbox message
> `build-timeout-learned-value-truthfulness-006`, read first-party at drain. **The message itself
> recommended staging this rather than folding it, and the orchestrator agrees** — it changes tiering
> policy across all four build engines and every consumer of the resolve stamp.
> ⚠ **This is a CONSEQUENCE of a correct fix, not a regression.** Nothing in #1022 should be reverted.

## Objective

`execution_tier` is derived from the **floored** `bash_timeout_seconds`, so on this repo every
pyprojectx canonical resolves `600 + 30 = 630 > 600` → `orchestrator` **on the floor alone, before any
learned value is consulted** — including `compile` (~15s actual) and `quality-gate` (~16s actual). The
phase-5 leaf's runnable build slice is therefore **EMPTY, not merely narrow**: the orchestrator now
owns every build in this repo, including trivially cheap ones. Decide whether the runnable-slice
question should key on the *measured* value while the enforcement stamp stays floored.

## ⚠ Mechanism — the two questions #1022 collapsed onto one number

- OBSERVED (#1022, `bb27a93b4`): `architecture resolve` computes
  `inner = max(timeout_get(...), config.min_timeout)` then `get_bash_timeout(inner)` (`+
  OUTER_TIMEOUT_BUFFER`), and `execution_tier` is derived from that against
  `HARNESS_BASH_CEILING_SECONDS = 600` (`tools-file-ops/scripts/constants.py`).
- OBSERVED: `PYTEST_OUTER_FLOOR_SECONDS = 600`, `OUTER_TIMEOUT_BUFFER = 30`.
- OBSERVED (this repo, measured): `compile` ~15s, `quality-gate` ~16s, `module-tests` ~640s,
  `verify` ~640s — **all four resolve `execution_tier: orchestrator`**.
- OBSERVED (run log, verbatim): `[BLOCKED] (plan-marshall:phase-5-execute) … All build canonicals
  live-resolve execution_tier=orchestrator (bash_timeout_seconds=630 exceeds the harness ceiling), so
  the whole-tree verification is outside this leaf's runnable slice.`
- **⇒ The load-bearing distinction:** the floor answers *"what bound will be enforced if this run goes
  long?"*; the runnable-slice rule asks *"will this run go long?"*. **Those are different questions**,
  and #1022 collapsed them onto one number. A `compile` with a learned value of ~15s is trivially
  runnable in-leaf and is excluded only by a floor protecting a failure mode it will never reach.
- **⇒ Why the floor itself must NOT be touched.** pyproject's floor exists so the outer kill cannot
  pre-empt pytest's inner per-test backstop — the diagnosable failure. Reporting `per_task` for a
  command whose *enforced* bound is 630s would be exactly the untruthful stamp #1022 eliminated.
  **A test pins this. Do not "fix" the tier by lowering the floor or by un-flooring the stamp.**

## Deliverables

### D1 — GATE: decide whether the runnable-slice rule may key on a different value than enforcement (mutates nothing)

(a) **Confirm the premise at HEAD** — re-verify the four canonicals' resolved tiers and their measured
values against post-#1022 code (verify-first; do not scope from this spec's table).
(b) **Enumerate every consumer of `execution_tier`**, not just phase-5. The stamp is consumed in
several places; a change that fixes the leaf slice while mis-signalling another consumer trades one
defect for another.
(c) **Decide the shape.** The starting point offered by the source message — *keep
`bash_timeout_seconds` floored and truthful (that stamp is about enforcement and must not change), but
derive `execution_tier` from the learned/measured value plus buffer, falling back to the floored value
when no measurement exists* — is **a candidate, not a decision**. ⚠ **The fallback direction is the
whole risk:** an unmeasured-but-slow command would tier `per_task` on first run and get
auto-backgrounded, which is precisely the failure the tier split exists to prevent. D1 must choose the
fallback deliberately and say why. **Fail-closed candidate: no measurement ⇒ orchestrator tier.**
(d) **Decide whether "truthful stamp" and "routing hint" should be separate fields** rather than one
number serving both. If they are separate, say what each consumer reads and why — a second field that
consumers pick arbitrarily is worse than one honest field.

### D2 — implement the D1 decision

Scoped to D1. **Hard constraints:** `bash_timeout_seconds` remains floored and truthful — it is the
enforcement bound and #1022's tests pin it; and no change may make a slow command runnable in-leaf on
its first, unmeasured run.

### D3 — tests

(a) A cheap measured canonical (`compile`) is runnable in-leaf under D1's rule — **verified to FAIL
against current code**, where it resolves `orchestrator`. (b) An unmeasured canonical takes D1's
chosen fallback, asserted explicitly. (c) A genuinely slow canonical (`verify`, ~640s) still resolves
`orchestrator`. (d) `bash_timeout_seconds` remains floored in every case — the #1022 invariant is
untouched.

Three deliverables (D1 a gate) — well under the split guard.

## Claim Labels

- OBSERVED: every claim in § Mechanism above, sourced from #1022's shipped diff, this repo's measured
  wall-clock, and the run's own `[BLOCKED]` log line quoted verbatim.
- HYPOTHESIS: that `execution_tier` has consumers beyond `phase-5-execute` whose behaviour would
  change — confirm/refute by enumerating readers of the resolve stamp at D1(b) (verify-at-outline).
- HYPOTHESIS: that a learned/measured value exists for the cheap canonicals in the common case (the
  proposed rule is worthless if most runs are unmeasured) — confirm/refute against the persisted
  timeout store at D1(a) (verify-at-outline).
- Verify-first clause: **if D1(a) finds the leaf slice is NOT empty at HEAD** — e.g. a later change
  altered the floor or the ceiling — the premise is refuted; loop back and re-scope rather than
  implementing against this spec's table.

## Expected Surface

- OBSERVED: `manage-architecture` — the `resolve` path computing `bash_timeout_seconds` and deriving
  `execution_tier`.
- OBSERVED: `tools-file-ops/scripts/constants.py` — `HARNESS_BASH_CEILING_SECONDS` (read; the single
  declaration #1022 established, do not duplicate it).
- OBSERVED: the four build engines' floor constants — `PYTEST_OUTER_FLOOR_SECONDS` (600) and the
  maven / gradle / npm floors (300). **Read-only** unless D1 explicitly decides otherwise.
- HYPOTHESIS: `phase-5-execute` runnable-slice logic, plus any other `execution_tier` consumer D1(b)
  finds (verify-at-outline).
- OBSERVED: tests under `test/plan-marshall/manage-architecture/**` and
  `test/plan-marshall/phase-5-execute/**`.

**Disjointness:** `manage-architecture` + `phase-5-execute` + build-engine constants (read).
⚠ **OVERLAPS PLAN-86** (`phase-5-execute` persist sites) — different concern, same skill. **Sequence,
do not parallelize.** Adjacent to PLAN-87 (`build-maven/scripts/extension.py` — a different file in
the same skill as the Maven floor constant; file-disjoint).

## Dependencies and Sequencing

- Depends on: **PLAN-62 (#1022) — LANDED**, so the premise is live and re-verifiable at HEAD.
- Overlaps with: **PLAN-86** — sequence; both touch `phase-5-execute`.
- Adjacent to: PLAN-88 / PLAN-58 (`manage-build-server`) — no shared files.
- ⚠ **Operational note:** until this lands, the orchestrator owns EVERY build in this repo, including
  15-second ones. That is working-as-specified, not a fault, but it raises orchestrator-tier build
  traffic and should be weighed when judging build-related throughput complaints.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-89-runnable-slice-keys-on-the-floor-not-the-measurement.md"
```

## Write-Boundary

Repository source + tests only. NO writes to `.plan/local/orchestrator/` **ledger state**
(`status.json`, `epic.md`, `plans/`, `landings/`); the `inbox/` channel is the sanctioned exception
for orchestrated plans. See `persona-marshall-orchestrator/standards/orchestration-model.md`
§ Ledger Write-Boundary.
