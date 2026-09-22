# Landing Analysis: PLAN-135 — Sweep the Preambles the Shipped Accessors Can Now Reach

epic: test-quality
workstream: WS-02
pr: #1446 (merged as `b64db66713d037b456d3c0c0956c68839208b173`)

> Landing record for one shipped plan. Every figure below was re-derived by this analyze
> at the merge commit itself (`git rev-parse HEAD` == `b64db667`, clean worktree), not
> transcribed from the plan's narrative. Where the plan's claim and the re-derivation
> agree, the agreement is stated; where they diverge, the divergence is recorded.

## Deliverable Fidelity vs Spec

The spec staged **four** deliverables (D1–D4); the plan executed **six**. The expansion is
a split, not scope creep — the spec's D2 carried two distinct shapes and an embedded guard
clause, and the plan separated them into their own deliverables.

| Deliverable (spec) | Plan's | Verdict | Evidence |
|--------------------|--------|---------|----------|
| D1 — derive the live population, classify every member | 1 | shipped-as-specified | Re-derivation at `b64db667` reproduces both counts exactly |
| D2 — convert every reachable preamble (both shapes) | 2 + 3 | shipped-modified (split by shape) | `spec_from_file_location` 61→13, `Path(__file__)` chain 42→0 |
| D2's collision-guard clause | 5 | shipped-modified (promoted to its own deliverable) | `KNOWN_REGISTRATION_COLLISIONS` is 17 names, unchanged; file untouched in the diff |
| D3 — resolve `subprocess-pythonpath` | 4 | shipped-as-specified | 17→5, all 5 residuals error-severity, none suppressed |
| D4 — report the measured deltas | 6 | shipped-as-specified | Landing message carries every figure with its command |

### Independently corroborated at the merge commit

`doctor test-conventions`, whole tree, HEAD = `b64db667`:

| Rule | Plan claimed | This analyze measured | Verdict |
|------|-------------:|----------------------:|---------|
| `test-module-preamble-boilerplate` | 13 | **13** | corroborated |
| — `spec_from_file_location` shape | 13 | **13** (every residual row carries this `kind`) | corroborated |
| — `Path(__file__)` parent-chain shape | 0 | **0** (no row carries this `kind`) | corroborated |
| `subprocess-pythonpath` | 5 | **5** | corroborated |

The 13-row residual decomposes exactly as claimed: **2** in `test/conftest.py` (lines 633
and 1247 at HEAD) and **11** in distinct other files. The plan's own line numbers for the
conftest pair (580, 1178) do not match HEAD — explained by upstream edits to that file
during the run, and immaterial: the plan never edited it, and the count is what the claim
rests on.

Footprint corroborated: **89 files, +689 / −1194 = net −505**, exactly as claimed, and
`b64db667` is an ancestor of `origin/main`.

Both declared spec exclusions **held**: **0** `marketplace/bundles/**` files in the diff,
and `test/conftest.py` untouched. `test_conftest_loader_contract.py` is likewise untouched,
which independently confirms D5's report that it measured both bounds as already correct
and edited nothing.

### A fourth spec-premise error, which the plan did not report

The plan reported three corrections to the spec's premises (structural floor 11-across-4
not 8-across-3; two conftest occurrences not one; five false positives not six). A fourth
stands unreported:

⛔ **The spec's D2 named a "23-name `KNOWN_REGISTRATION_COLLISIONS` baseline". The constant
holds 17 names**, verified by reading it at HEAD. The plan's claim of "unchanged at 17" is
the correct figure and the spec's 23 was wrong on the day it was staged. The guard clause
still did its job — the baseline is unchanged and nothing was relaxed — so nothing shipped
wrong; but a spec premise that is off by six was never caught by the run that quoted it.

The spec's D3 also stated `subprocess-pythonpath` "reports **15** tree-wide"; the true
figure was 17, already corrected in the epic's own re-derivation at `681db9446` before
launch. Two of four spec premises in this plan were numerically stale.

## Metrics and Anomalies

Read from the archived plan's `metrics.md`, not from the narrative.

- **Tokens: 5,802,434** — matches the paste's 5.8M. Against the 3.5M error anchor this is
  **1.66x over**.
- **Duration: 4h42m worked / 11h44m wall** (n=5/6 phases for the worked figure).
- Per-phase: 1-init 37,953 · 2-refine 138,218 · 3-outline 482,676 · 4-plan 472,888 ·
  **5-execute 2,463,442** · **6-finalize 2,207,257**.

**The finalize/execute ratio is 0.90x — a second consecutive sub-1.0** after PLAN-130's
0.91x. The streak of finalize outspending execute is now broken twice running rather than
once. Still two points, still not a demonstrated improvement; the direction is now worth
more than a single sample.

**Anomaly — 296,505 tokens of drift recovery that performed no work.** Two `baseline_drift`
aborts at the phase-5 entry gate, ~23 minutes apart. That is **12.0% of the 5-execute
phase** and 5.1% of the plan total. The second abort was structurally guaranteed, not bad
luck: the documented recovery re-dispatches `2-refine`, which resolves drift as *content*
and never advances the branch, while the gate tests git *ancestry*. Refine cannot change
the predicate the gate evaluates.

⚠ The plan's own lesson computes this waste as 5.7% against a 5.23M total; the archived
metrics give 5,802,434, making it 5.1%. The lesson's percentage was taken against a
mid-run figure. Immaterial to the finding, recorded so the two numbers are not read as a
contradiction.

⛔ **The waste is invisible to retrospective accounting.** `error_total_tokens` counts only
fatal `error` terminations and `retryable_total_tokens` only `blocked_session_restart` +
`harness_cancellation`; a `baseline_drift` row lands in neither, so both read `0` on a run
that burned 296K tokens on nothing.

## Routing and Merge Behavior

- **Review: coverage held for a second consecutive landing.** CodeRabbit reviewed and
  raised **one Major functional-correctness finding no local gate caught**
  (`test_staleness_guard.py:712` — the `_run_python` child was not isolated from the
  repository, weakening a negative control). `cuioss-review-bot` reviewed the same diff
  and reported clean. `sourcery` never reviewed (hard quota, ~7 days).
- **The declined remedy was declined with measurement, not preference.** CodeRabbit's
  stated fix ("assert the package import fails") would have yielded `blocked=marketplace`
  and destroyed the matched negative control it was protecting. The isolation half was
  taken; the assertion half was not. CodeRabbit agreed with that scoping in-thread.
  Re-review at the fix head: no actionable comments, merge risk Moderate → Low.
- **CI/merge:** merged as `b64db667`, 89 files. The PR stayed under the 100-file CodeRabbit
  cap without needing the split PLAN-130 required — the spec's 86-file estimate was close
  and the cap was never approached.

### The gate did NOT go green, and the pre-launch anchor predicted it would

⛔ The resume anchor written at launch stated the whole-tree gate "should go green on this
landing". It did not. `doctor test-conventions` still reports **`status: fail`** at
`b64db667`. The reason is exactly the one the plan documented and is not a shortfall in the
sweep: **all 5 residual `subprocess-pythonpath` findings carry `error` severity**, and they
are the only error-severity findings in the tree (verified: 5 of 5). Every other finding
across all seven rules is a warning.

The plan classified those 5 as confirmed rule false positives and **filed them for WS-03
rather than suppressing them** — the correct call, and consistent with this project's
fix-don't-suppress posture. The consequence is that **the tree-wide gate stays red until
the rule itself is fixed**, which is now WS-03's to own, not a residue of this sweep.

Whole-tree rule state at `b64db667`: `unique-fixture-basenames` 0 · `subprocess-pythonpath`
**5** · `identifier-validator-corpus` 0 · `test-module-line-budget` **354** ·
`test-helper-module-misnamed` 0 · `test-module-preamble-boilerplate` **13** ·
`test-docstring-historical-prose` **3**.

### Declaration form: a fifth measurement, mode 2 for the third time

**89 of 89 realized files fall inside the declared surface** — and, as with PLAN-130's 112
of 112, this tells the gate nothing, because the declaration claims `test/` at ROOT so
nothing *could* have landed outside it. This is the fifth measurement across three modes
and the third in mode 2. The root claim remains the measured reason this epic has run
strictly one plan at a time.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-135 --status shipped`
- [x] row `pr` stamped `#1446`
- [x] row `landing` stamped `landings/PLAN-135.md`
- [x] `plan_marshall_plan_id` already stamped at launch (`sweep-preambles-shipped-accessors`)
- [x] Open Defects: "shipped-accessor gap" and "circular ownership on three preamble sites" retired — both closed by this landing
- [x] Open Defect added: the landing message carried no `landing-facts` block (`complete: false`, all 8 required keys missing)
- [x] Open Defect added: 5 `subprocess-pythonpath` rule false positives keep the tree-wide gate red — handed to WS-03
- [x] Open Defect added: the spec's 23-name collision baseline was wrong (actual 17)
- [x] Watch added: finalize/execute ratio 0.90x, second consecutive sub-1.0
- [x] START-HERE and Ordered Queue blocks regenerated

## Follow-Ups

- **5 `subprocess-pythonpath` false positives** (`462a76`, `c0f4ef`, `02c9ea`, `79bf95`,
  `24970a`) — the rule matches a call *shape* and cannot see a deliberate env scrub, a
  helper-supplied `PYTHONPATH`, or a `-m` stdlib invocation. → WS-03, and they are what
  keeps the gate red.
- **`a073b5`** — no test discriminates whether the `_run_python` isolation holds. Both
  consuming assertions pass under the old and new regimes, so a regression stays green.
  Missing regression protection, not a live defect. → WS-03.
- **The sweep authored a false docstring while retiring false preambles** (inbox 003,
  CodeRabbit `79d281`) — promoted to the lessons corpus. Method-level and applies to
  **every remaining sweep in this epic**: the remedy vocabulary is shape-based
  (`run_script` / explicit `env=`) while the defect is claim-based, so a sweep validated by
  a shape rule is structurally blind to its own defect class. Every internal gate passed
  it; CodeRabbit caught it by running a probe.
- **`baseline-reconcile` locale bug** (lesson `2026-09-07-21-001`) — manufactured 6 phantom
  conflicts out of 2 real ones and drove the entire wasted drift-recovery cycle.
  Already in the corpus; **filed four times under three component spellings**.
- **Drift-recovery gap** (lesson `2026-09-08-01-001`) and **branch-cleanup worktree
  metadata deadlock** (lesson `2026-09-08-01-003`) — both already promoted; both are
  harness defects outside this epic's scope.
