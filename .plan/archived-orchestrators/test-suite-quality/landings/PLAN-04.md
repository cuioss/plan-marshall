# Landing Analysis: PLAN-04 — Enforcement Gates & Yardstick Re-Measurement

epic: test-suite-quality
workstream: WS-02
pr: #982 — merged as `4002bedb1` (2026-07-22)

> Landing record. Claims corroborated against the real diff and the real `pyproject.toml`
> before recording. The significant finding is not in the plan's execution — which was
> clean — but in what its measurement revealed about the **epic's own success criterion**.

## Deliverable Fidelity vs Spec

The spec carried 4 deliverables; the plan shipped 3, by **merging spec D1 and D2 into an
ordered pair** (arm the three zero-cost gates, whose verification run doubles as the warning
census; then arm `filterwarnings` only if that census says it lands green). That is a better
decomposition than the spec's, because it makes the census a *product* of the work rather than
a separate prerequisite step. No scope was lost.

| Deliverable | Verdict | Corroboration |
|-------------|---------|---------------|
| Arm the three zero-cost gates + capture census | shipped-as-specified | `addopts` now carries `--strict-markers`, `--strict-config`, `--durations=25` (verified in the diff) |
| Apply-or-defer `filterwarnings` on the measured census | **shipped-as-specified, hypothesis discipline honoured** | `filterwarnings = ["error"]` armed with **zero** per-item ignores, above an 11-line comment recording the census (0 warnings / 14 794 tests) as the justification |
| Re-measure both axes + refresh the stale comment | shipped-as-specified | `:88` comment now reads "~2.5 min (measured 151.69s, warm cache)"; the hang-vs-slow argument was **re-derived**, not silently updated |

**Surface fidelity: exact.** The diff is `pyproject.toml` alone — 1 file, +22/−4. Every
off-limits item verified untouched: `pytest>=8.0,<9` (`:23`), `pytest-xdist>=3.0,<3.8` (`:29`),
`mypy>=1.10,<2` (`:38`), `requires-python` (`:4`), `lock-python-version` (`:12`), and the marker
registry. **This is the first plan in the epic whose actual surface matched its declared surface
exactly** — the third consecutive success for the explicit off-limits section.

**The hypothesis discipline worked, and this is the point.** PLAN-03's landing recorded lesson
`2026-07-21-22-001`'s 5th occurrence against this orchestrator for sizing work on an unverified
count. PLAN-04 was staged with the zero-warnings figure explicitly labelled as a *hypothesis with
its confirming artifact named*. The plan measured first (0 warnings / 14 794 tests, no
warnings-summary section at all), then armed. Had the census come back non-empty, the spec's
record-and-defer instruction was in place. **The corrective action is now demonstrably
load-bearing on the orchestrator side, not just the consumer side.**

Two smaller claims also verified rather than assumed: `--durations=25` reaches
`cmd_module_tests` / `cmd_coverage` because they never override `addopts` (so no `build.py`
change was needed), and the `timeout = 300` rationale was re-checked against the new data
(slowest test 12.84 s — the bound holds by a wider margin than when written, and was
deliberately NOT retightened, since it is a hang detector, not a performance budget).

## Measured Results — and the problem they expose

| Axis | Measured (warm) | Baseline `b591b7d9` | Delta |
|------|-----------------|---------------------|-------|
| Suite duration | **151.69 s** | 137 s | **+14.7 s (worse)** |
| Line coverage | **83.85 %** (43408/51769) | 83.63 % | +0.22 pp |
| Branch coverage | **78.32 %** (16276/20782) | 78.01 % | +0.31 pp |
| Counts | 14 794 pass / 0 fail / 0 skip / 0 warn | 14 423 / 1 fail | — |

### The duration axis is not measurable at the fidelity this epic's success criterion assumes

This is the landing's most important finding, and it is an **epic-level methodology defect, not
a plan failure**.

- The plan measured the same tree at **210.50 s cold → 151.69 s warm**: a **58.8 s cache-state
  swing**, which is **4.5× the entire ~13.2 s saving** PLAN-03 was expected to deliver.
- The `b591b7d9` baseline's own cache state is **unrecorded**, so the 137 s figure is not a
  like-for-like comparator. The +14.7 s delta is bounded, not exact.
- **Normalizing per-test does not rescue it.** Baseline 137 s / 14 423 = 9.50 ms per test;
  now 151.69 s / 14 794 = 10.25 ms per test — an ~8 % per-test rise. But both figures are still
  single warm runs against one unrecorded cache state, so the normalization inherits the same
  noise floor. It narrows the confound (the suite has grown +371 tests since baseline, +2.6 %),
  it does not remove it.

**Consequence for the epic.** "Done" is defined in the Vision as *measurable gains in BOTH suite
duration and coverage*. On the evidence, **single warm-run wall-clock cannot demonstrate a
duration gain of the size this campaign produces.** PLAN-05 cannot simply "convert the baseline
into demonstrable gains" using the method the baseline used — it must first fix the measurement
protocol (repeated runs with controlled cache state, or a per-test `--durations` comparison,
which PLAN-04 has now made possible for the first time). This is now the capstone's blocking
prerequisite and is recorded as a decision.

### Coverage attribution — read the +0.22 pp correctly

PLAN-04 changed **no test code and no production code**, so its own coverage contribution is
structurally ~zero. The +0.22 pp / +0.31 pp is the epic's **cumulative** movement since
baseline (83.63 → 83.71 at PLAN-02 → 83.85 now), i.e. it mostly belongs to PLAN-03. Recorded so
the trend table is not misread as attributing coverage to a config-only plan.

## Metrics and Anomalies

- Tokens **1.90 M**; **1 h 23 m worked / 3 h 30 m wall / 2 h 7 m idle**. The most efficient plan
  in the epic by a wide margin (PLAN-02: 3.9 M, PLAN-03: 3.2 M) — consistent with the split
  decision, which is the intended payoff of keeping the cheap half separate.
- Phase outlier: `6-finalize` burned **673 K tokens (35 % of the plan) over 56 m wall with 40 m
  idle** for a 1-file diff — the same finalize-heavy shape PLAN-02's landing flagged
  (1.33 M in finalize). Third consecutive observation; the cost of finalize appears largely
  independent of diff size.
- `3-outline` ran 1 h 27 m wall against 24 m worked (1 h 3 m idle) — again mirroring PLAN-02.

## Routing and Merge Behavior

- Merged clean; main up-to-date, worktree removed, tree clean. Single-file diff, no collision.
- **Build verdicts were taken from the job-log verdict, not the outer status**, because the
  running `marshalld` still executes the pre-fix supervisor from #979 and its outer success was
  treated as untrustworthy throughout. That is the correct posture and matches the standing
  "build wrapper exit code is misleading" rule — recorded as a positive precedent, and as a
  live hazard for the next plan (see Watches).

## Reconciliation Actions

- [x] status.json `plans[]` PLAN-04 → `shipped`
- [x] epic.md queue row reconciled
- [x] Baselines & Trend § — CI row added with the full measured figures
- [x] Watch **retired**: "yardstick unobserved" — both axes are now measured
- [x] Watch **replaced** by: duration axis is below the cache-noise floor (methodology defect)
- [x] Watch added: stale `marshalld` supervisor makes outer build status untrustworthy
- [x] Watch **retired**: "spec surface under-declaration" — declared surface matched exactly
- [x] Decision recorded: PLAN-05 must fix the measurement protocol before claiming gains
- [x] resume_anchor updated; START-HERE regenerated

## Follow-Ups

- **PLAN-05's charter needs amending before emission** — it is staged to "convert the baseline
  into demonstrable duration+coverage gains", which this landing shows is not achievable with
  the baseline's method. Amend at emit: protocol first, then optimization.
- **Per-test hotspot data now exists for the first time** (`--durations=25`, slowest test
  12.84 s). PLAN-05's original targets were derived at module granularity; re-derive them from
  the real per-test table.
- **Operator action owed, now carried twice**: `marshal.json` provisioning stamp stale
  (0.1.1180 → 0.1.1192) — `/marshall-steward` plus a session restart, since the executor
  regenerated.
- Lessons filed by the plan: `2026-07-22-16-001` (read-only path in Affected files flips the
  manifest footprint bucket), `2026-07-22-14-001` (q-gate deliverable-hash segmentation leaves
  the last deliverable's end boundary undefined); one merged into `2026-06-28-17-001`.
