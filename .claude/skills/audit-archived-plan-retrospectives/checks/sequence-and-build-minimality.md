# Check: sequence-and-build-minimality (cross-plan)

Reconstructs each plan's call sequence from its plan-scoped
`logs/script-execution.log` (the ordered, unambiguous call timeline), buckets
every call into a phase by the `logs/work.log` `[DISPATCH] role=phase-N`
timeline, and studies **build minimality**: the thesis that a build after a
deliverable should be FOCUSED (compile + test-compile + test-run for the CHANGED
module only) and should only run on buildable stuff. The deterministic
computation lives in `scripts/audit.py` (`cross_sequence_build_minimality` /
`_sequence_build_minimality_plan` / `emit_sequence_build_minimality_block`); this
sub-document is the interpretation guide.

This is a cross-plan check: it emits one aggregate block (per-plan rows + corpus
build-class / status / build-verb totals + the duration-band thresholds) rather
than one row per plan in isolation. It builds on the D1 severity infrastructure —
every per-plan row carries the uniform `severity` column and the block carries a
`genuine_signal_count` summary line.

## Build time comes from the change-ledger — the build-time ORACLE

**Build DURATION, the build COUNT, the pass/fail STATUS, and the build-class
bands are derived from the structured change-ledger** (`manage-change-ledger`'s
single append-only `<repo>/.plan/work/change-ledger.jsonl`), **not** by
regex-parsing `(N.NNs)` fragments out of a log. The ledger stamps one `kind=build`
row per build-**executing** dispatch at the executor boundary — for **every**
build system and **every** phase — each carrying a structured `duration_seconds`,
a truthful `status`, and the wrapper-resolved `command`. `_load_build_ledger_index`
reads that one file once and indexes the rows by bare `plan_id`
(`_ledger_plan_key` strips the `{YYYY-MM-DD}-` archive-date prefix from the plan
dir name, because a ledger row carries the bare execution-time id).

This RE-BASE (not an addition — the ledger REPLACES the log as the build-time
source) closes two blindnesses the log derivation carried:

1. **Single build system.** The old log matcher matched only
   `build-pyproject:pyproject_build`; Maven / Gradle / npm builds were invisible.
   The ledger records `command` per build system, so every build system is counted.
2. **Early-phase invisibility.** A build run before the plan-scoped log exists
   never reached it. The ledger is written at the dispatch boundary in every phase,
   so early-phase builds are counted.

The log-derived total is **retained only as the delta baseline**: the block
reports `corpus_build_seconds` (ledger) beside `corpus_build_seconds_log_derived`
(the OLD pyproject-only log total over the SAME ledger-bearing plans) and their
`corpus_build_seconds_delta` — the number that makes "we now see more" evidence
rather than a claim.

**ABSENT IS NOT ZERO.** A plan archived before the ledger existed carries no
`kind=build` rows: its build time is **UNAVAILABLE**, not zero. Such a plan is
counted in `plans_without_ledger` and named in `plans_without_ledger_ids`, and is
EXCLUDED from the delta baseline (folding its log-derived seconds into the delta
would compare the ledger's silence against the log's speech). Its ledger totals
read 0 with `has_ledger: false` — read that as "unmeasurable", never "no builds"
— and its `build_share` is WITHHELD (`n/a`) rather than rendered as a `0%`
derived from that absence (see § "Build time vs plan wall-clock").

**SUSPECT-ZERO rule.** A `kind=build` row whose `duration_seconds` is `0`, absent,
or non-numeric is **SUSPECT**, never data: a zero is indistinguishable from a cache
hit, a no-op, or a build killed at N seconds whose routed status reported
`duration_seconds = 0`. A suspect duration is counted in the `unknown` band
(`build_unknown`) and the `suspect_build_duration` flag, and is **NOT summed into
`total_build_seconds` and NOT averaged in** — a zero silently included is worse
than an absent value, because it drags a total toward a number nobody measured.
A plan carrying suspect builds has a build-time total that is a **floor**.

## Inputs the check reads

For every scanned plan the script joins these structured inputs:

| Input | Field(s) read | Used for |
|-------|---------------|----------|
| `.plan/work/change-ledger.jsonl` (repo-level, once) | `kind=build` rows: `plan_id`, `duration_seconds`, `status`, `command`, `notation`, `timestamp_iso` | **build count, per-build duration, duration-band class, status ratio, per-phase build attribution, churn** — the build-time oracle |
| `work/metrics.toon` | per-phase `duration_seconds` | plan wall-clock denominator (build-vs-wall-clock share + the invariant) |
| `logs/script-execution.log` | per-call `notation subcommand (N.NNs)` lines (timestamp-ordered) | call timeline, per-phase call counts, arch-call count, consecutive-dup, **and the OLD log-derived build seconds kept only as the delta baseline** |
| `logs/work.log` | `[DISPATCH] role=phase-N` markers; `module-tests`/`quality-gate`/`verify`/`coverage`/`compile` verb mentions | phase segmentation, per-role dispatch counts (phase-reentry), build-verb scope mining |
| `references.json` | the realized footprint path set, tier-resolved (`realized_footprint` → `merge_commit_sha` → `modified_files`); the declared `affected_files` list only when no tier resolves | docs-only footprint (`.py` presence) |
| `status.json::metadata` | `change_type` | docs-only classification |
| `artifacts/ci-runs/` | directory count | `ci_runs` (CI re-run signal) |

The change-ledger is the authoritative build source (see § "Build time comes from
the change-ledger" above). The `script-execution.log` remains the ordered call
timeline and supplies the log-derived delta baseline; the `work.log` supplies the
phase-dispatch timeline and the qualitative build-verb mentions. Best-effort: a
plan with no ledger rows degrades to an unavailable (`has_ledger: false`) row, and
a plan with no logs degrades to an all-zero call row, rather than raising.

### Corpus partition (delivery-cost check)

This check runs over the SHIPPING partition of the corpus, not every scanned
plan: a plan carrying no delivery evidence — no PR record and no footprint — is
excluded before the check sees it, so builds run by a plan that delivered nothing
cannot inflate the corpus build-class totals. See SKILL.md § "Shipping-predicate
corpus partition" for the derived predicate.

## Per-plan computation

### Sequence reconstruction

Each call is bucketed into a phase by the dispatch timeline: a call at time `t`
belongs to the most recent `role=phase-N` marker at or before `t` (defaulting to
`1-init` before the first marker). The script computes, per plan:

| Quantity | Definition |
|----------|------------|
| `calls` | Total parsed script calls. |
| `span_seconds` | Wall-clock span first-call → last-call. |
| per-phase call count | Calls bucketed into each `{1-init … 6-finalize}` phase. |
| `arch_calls` | Calls to `manage-architecture:architecture` (any verb) — the resolution-overhead numerator. |
| `phase_graph` | A compact `phase:calls(b=builds/a=arch)` string per phase, in canonical phase order. |

### Build classification (duration bands)

Every **ledger `kind=build` row** is classified by its `duration_seconds` against
the centralized `THRESHOLDS` bands — **no magic number is re-declared in the
check**:

| Class | Band | Reading |
|-------|------|---------|
| `minimal` | `< build_minimal_seconds` (120s) | compile / small scoped run. |
| `scoped` | `build_minimal_seconds … build_heavy_seconds` (120–400s) | single-module tests. |
| `heavy` | `> build_heavy_seconds` (400s) | whole-tree `verify` / all-modules — **NOT minimal**. |
| `unknown` | duration `0` / absent / non-numeric — **SUSPECT** | classification withheld; counted as `build_unknown` and flagged `suspect_build_duration`, NEVER summed into `total_build_seconds`. |

`max_build_seconds` and `total_build_seconds` carry the worst single build and the
summed build time for the plan, over **valid (`> 0`) durations only** — a suspect
zero contributes to neither (the suspect-zero rule).

### Build-status ratio (killed is SEPARATE from error)

Each `kind=build` row's `status` is tallied into a pass/fail ratio, reported per
plan (`build_success` / `build_error` / `build_timeout` / `build_killed`) and as
corpus totals (`corpus_build_pass` / `_error` / `_timeout` / `_killed`):

| Status | Reading |
|--------|---------|
| `success` (`pass`) | a green build. |
| `error` | a red build — a code problem. |
| `timeout` | the build hit its ceiling. |
| `killed` | an **infrastructure event** (a whole-tree or child kill). ⛔ **NOT folded into `error`** — collapsing a kill into "failed" would report a harness problem as a code problem. It is counted, and rendered, on its own axis so a reader can tell an infrastructure kill from a red build. |

A build whose `status` is `unknown` (or unrecognized) is counted per plan in
`build_status_unknown`, emitted as the per-plan row's `status_unknown` column, and
summed into the emitted `corpus_build_status_unknown` line. The identity holds at
BOTH scopes — `pass + error + timeout + killed + status_unknown == builds` on
every row, and `... == corpus_builds` over the corpus — so the ratio accounts for
every build rather than leaving a silent gap at either scope. An undetermined
outcome is not an absent build: dropping it would make the row's own four-term sum
fall short of its `builds` cell with nothing naming the difference. This is
orthogonal to `build_unknown`, which is the suspect-DURATION band above (a build
can be `status: success` yet duration-suspect, e.g. a cache hit).

### Build time vs plan wall-clock (share + the invariant)

`wall_clock_seconds` is the sum of per-phase `duration_seconds` from
`work/metrics.toon`. `build_share` = `total_build_seconds / wall_clock_seconds` —
the fraction of a plan's elapsed time spent inside builds.

**The share is WITHHELD (`n/a`) when EITHER side is unavailable** — never a
fabricated ratio:

- **Denominator unavailable.** Wall-clock is absent or zero (the metrics
  **absent-file hole** the ratio inherits), so there is nothing to divide by.
- **Numerator unavailable.** The plan carries no `kind=build` ledger rows
  (`has_ledger: false`), so `total_build_seconds` is zero **by absence, not by
  measurement**. Dividing it out yields a `0%` that reads as "this plan spent no
  time building" while the `has_ledger` cell one column away says the build time
  was never measured at all — the two cells of the same row contradicting each
  other. `has_ledger` is the numerator's availability, and absent is not zero on
  either side of a ratio.

A `0%` share is therefore always a real measurement: builds were recorded, and
they occupied a negligible fraction of the plan's elapsed time.

The **invariant** (`build_exceeds_wallclock` flag): summed build time cannot exceed
plan wall-clock. A violation is a **RECORDING defect** — a duration plumbed through
wrongly — not a code problem, and follows the same impossible-values family the
`metrics` check models (`worked > wall`). *Caveat:* builds detached and run
concurrently could in principle sum past wall-clock legitimately; the invariant
treats the common serial case, where a summed build time larger than the whole
plan's elapsed time is impossible.

### Build-verb mining (work.log)

The duration band says *how long* a build ran; the work.log verb mention says
*what scope* it ran with. The script mines `work.log` for the build verbs and
emits a `verbs` summary `smt=…;amt=…;qg=…;vf=…;cov=…;cmp=…`:

| Token | Verb | Scope |
|-------|------|-------|
| `smt` | `module-tests {module}` where `{module}` is a KNOWN module | scoped module-tests. |
| `amt` | `module-tests` with no / unknown argument | all-modules module-tests. |
| `qg` | `quality-gate` | whole-tree static analysis. |
| `vf` | `verify` | whole-tree verify (quality-gate + tests). |
| `cov` | `coverage` | coverage run. |
| `cmp` | `compile` | compile-only — the cheapest, most-minimal verb. |

### Redundancy / anti-pattern flags

Per plan the script emits a `flags` list. Each flag annotates its triggering
value so a flagged row is self-describing:

| Flag | Fires when | Reading |
|------|-----------|---------|
| `build_churn` | a build starts within `build_clustering_minutes` (10m) of the previous build | a re-run loop rather than one focused build per change. |
| `non_minimal_build` | ≥1 heavy (`> build_heavy_seconds`) build ran | a whole-tree verify where a scoped module run sufficed. |
| `docs_only_build` | the plan touched no `.py` file (or `change_type == documentation`) yet ran a build | buildable-stuff violation (the docs-only-build axis). |
| `ci_rerun` | more than one CI run directory under `artifacts/ci-runs/` | the PR round-trip ran CI more than once. **Post-#849/#850 caveat**: a second CI pass is now often the EXPECTED shape — the early baseline-rebase finalize step (`finalize-step-sync-baseline`, #786) and a post-force-push re-review (#742) legitimately re-run CI, and #849's deterministic `ci_verify` + adaptive ci-wait ratchet make that re-verification cheap and intentional. Read ≥2 as a rebase/re-review round-trip vs a genuine red→green churn loop (see the interpretation section). |
| `phase_reentry` | a `phase-N` role was dispatched more than once | a loop-back re-entered a phase. **Post-#849/#850 caveat**: a `5-execute` / `6-finalize` re-entry is the EXPECTED shape of the finalize triage loop-back (the `loop_back_without_asking` inline-replay cycle), not necessarily redundant work — a loop-back that fixed a real finding is correct-by-design. |
| `arch_over_resolution` | `arch_calls ≥ 5 × builds` while builds exist | resolution overhead dwarfing the work it resolves. |
| `consecutive_dup` | ≥1 back-to-back identical `(notation, subcommand)` call | a mechanical double-call (see caveat 3). |
| `suspect_build_duration` | ≥1 ledger build with a zero / absent duration | the plan's build-time total is a **floor** — a killed run reporting 0, a cache hit, or a no-op is indistinguishable, so the missing time is surfaced, never averaged in. |
| `build_exceeds_wallclock` | summed build time > plan wall-clock (+1s) | a **recording defect** (a duration plumbed through wrongly) — the D2 invariant, the check that catches a duration plumbed wrongly. |

## Emitted columns

```
plans_in_corpus: K
build_minimal_seconds: 120
build_heavy_seconds: 400
build_clustering_minutes: 10
corpus_builds: <sum>
corpus_build_minimal: <sum>
corpus_build_scoped: <sum>
corpus_build_heavy: <sum>
corpus_build_unknown: <sum>              # suspect-duration builds
corpus_build_pass: <sum>
corpus_build_error: <sum>
corpus_build_timeout: <sum>
corpus_build_killed: <sum>               # SEPARATE from error
corpus_build_status_unknown: <sum>       # pass+error+timeout+killed+status_unknown == corpus_builds
corpus_build_seconds: <sum>              # ledger total
corpus_build_seconds_log_derived: <sum>  # OLD log total, ledger-bearing plans only
corpus_build_seconds_delta: <ledger - log>   # what the re-base now sees
corpus_build_churn: <sum>
corpus_ci_runs: <sum>
corpus_consecutive_dup: <sum>
corpus_docs_only_build_plans: <count>
plans_without_ledger: <count>            # build time UNAVAILABLE (absent is not zero)
plans_without_ledger_ids: <;-joined ids>
genuine_signal_count: G
rows[K]{plan_id,change_type,calls,span_seconds,has_ledger,builds,build_minimal,build_scoped,build_heavy,build_unknown,pass,error,timeout,killed,status_unknown,total_build_seconds,max_build_seconds,log_build_seconds,wall_clock_seconds,build_share,build_churn,arch_calls,ci_runs,consecutive_dup,phase_reentry,verbs,phase_graph,flags,severity}
```

The `build_share` cell is a percentage or `n/a` (withheld when wall-clock OR the
ledger is absent). `has_ledger: false` marks a plan whose build time is
unavailable — its build columns read 0 by absence, never as a measurement, and
its `build_share` reads `n/a` for exactly that reason.

| Column | Meaning |
|--------|---------|
| `plan_id` | The scanned plan's directory basename (rows sorted by total build seconds, desc). |
| `change_type` | Joined `status.json::metadata` change_type. |
| `calls` / `span_seconds` | Total calls and wall-clock span of the reconstructed sequence. |
| `has_ledger` | `true` when the plan has `kind=build` ledger rows; `false` = build time UNAVAILABLE (absent is not zero). |
| `builds` | Count of `kind=build` ledger rows (every build system, every phase). |
| `build_minimal` / `build_scoped` / `build_heavy` | Duration-band counts. |
| `build_unknown` | Suspect-duration builds (zero / absent) — the suspect-zero band. |
| `pass` / `error` / `timeout` / `killed` | Build-status ratio; `killed` is SEPARATE from `error`. |
| `status_unknown` | Builds whose `status` is absent or unrecognized — the outcome was never DETERMINED, which is not the same as a build that did not run. Present so the five status columns PARTITION the row: `pass + error + timeout + killed + status_unknown == builds`. Without it a four-term sum short of `builds` leaves the remainder unnamed, and an unnamed remainder reads as builds that never happened. Orthogonal to `build_unknown`, which is the suspect-DURATION band. |
| `total_build_seconds` | Summed ledger build time over valid (`> 0`) durations. |
| `max_build_seconds` | Worst single build's duration. |
| `log_build_seconds` | OLD log-derived pyproject-only total — the delta baseline. |
| `wall_clock_seconds` | Plan wall-clock (sum of per-phase metrics durations). |
| `build_share` | `total_build_seconds / wall_clock_seconds`, or `n/a` when **either** side is unavailable — an absent wall-clock (no denominator) or an absent ledger (`has_ledger: false`, so the numerator is zero by absence rather than by measurement). |
| `build_churn` | Clustered-rebuild count. |
| `arch_calls` | architecture-call count (resolution overhead numerator). |
| `ci_runs` | CI run-directory count. |
| `consecutive_dup` | Back-to-back identical-call count (see caveat 3). |
| `phase_reentry` | `;`-joined phase roles dispatched more than once. |
| `verbs` | The build-verb scope summary string. |
| `phase_graph` | Compact per-phase `phase:calls(b=/a=)` string. |
| `flags` | `;`-joined redundancy / non-minimality flags (empty for a minimal plan). |
| `severity` | Uniform D1 severity column: `genuine` when the row carries any flag, else `informational`. |

`genuine_signal_count` equals the number of flagged rows. The threshold and
corpus-total summary lines above the table carry the duration bands and the
corpus build-class totals so each flagged row is self-describing.

### Corpus-partition exclusion columns

Two further block-header lines accompany the block above:

| Line | Meaning |
|------|---------|
| `plans_excluded_non_shipping` | How many scanned plans were excluded from this check's corpus as non-shipping — a number reported SEPARATELY from the examined plan count. |
| `excluded_non_shipping_plan_ids` | The excluded plans, each as `{plan_id}:{archived_reason or unrecorded}`. |

An excluded plan delivered nothing, so it is absent from this check's aggregates
by design; the count is the audit trail proving no row was silently dropped.

## Three caveats (structural — read every flagged row against these)

The check surfaces raw counts; three structural limitations govern how a row is
interpreted. They are intrinsic to the inputs, not bugs, and the orchestrator MUST
apply them before drawing a verdict:

1. **Finalize-fold conflation when no `role=phase-6-finalize` marker exists.** When
   a plan's `work.log` carries no `role=phase-6-finalize` dispatch marker (the
   phase ran inline without a distinct dispatch, or the marker was never written),
   every call that actually belonged to finalize is folded into the preceding
   phase bucket (`5-execute`) by the most-recent-marker rule. The per-phase graph
   for such a plan therefore under-reports finalize and over-reports the preceding
   phase. Treat the phase split as approximate whenever the graph shows no
   `6-finalize` segment: the build/arch counts attributed to `5-execute` may
   include finalize-phase work.

2. **The `verify` work.log word-count is an UPPER BOUND while a heavy (`>400s`)
   duration is the FLOOR.** The build-verb mining counts every `verify` mention in
   the work.log text — including mentions inside prose, log lines that name the
   verb without running it, and retries — so the `vf=` count is an UPPER BOUND on
   the number of real whole-tree verify executions. Conversely, a `heavy` build
   classification (`> build_heavy_seconds`) is anchored to a recorded wall-clock
   duration, so it is a FLOOR: a build that took longer than the heavy band
   DEFINITELY ran whole-tree, but the absence of a heavy band does not prove no
   whole-tree verify ran (a fast machine or a cached run can finish a whole-tree
   verify under the band). Read the two together: the verb count bounds intent
   from above, the heavy-duration count anchors realized cost from below.

3. **`consecutive_dup` over-counts same-verb-different-args calls.** The
   consecutive-duplicate primitive keys only on `(notation, subcommand)` — it does
   NOT compare the trailing arguments. Two back-to-back calls to the same
   `notation subcommand` with DIFFERENT arguments (e.g. `manage-tasks read
   --task-number 3` followed by `manage-tasks read --task-number 4`, or two
   `pyproject_build run` calls with different `--command-args` module scopes) are
   counted as a duplicate even though they are legitimately distinct calls. The
   `consecutive_dup` count is therefore an OVER-COUNT of genuine mechanical
   double-calls; a high count is a hint to inspect the sequence, not proof of
   wasted work. Confirm a flagged `consecutive_dup` against the actual
   `script-execution.log` lines before treating it as redundancy.

## How the orchestrator interprets the rows

Per Step 3 of `SKILL.md`, every `genuine` row (any flagged plan) is adjudicated
with a stated verdict AND cited evidence; every `informational` (unflagged) row is
dismissed with a one-line cited reason (e.g. "minimal build profile — no
redundancy flag, informational per this sub-doc"). The build-minimality flags map
to the build-minimality lesson axes:

- **`docs_only_build` / `non_minimal_build`** — the headline build-minimality
  signal. A docs-only plan that ran any build, or any plan that ran a heavy
  whole-tree build where a scoped module run sufficed, is the exact defect the
  build-minimality lessons name. Cross-read with the `token-economics` check's
  `5-execute` token share and with `metrics`: a heavy build on a tiny footprint is
  the wasted-wall-time instance.
- **`build_churn` / `ci_rerun`** — re-run loops, but read `ci_rerun` against the
  post-#849/#850 finalize flow before calling it rework. A single extra CI pass
  (`ci_runs == 2`) is now the EXPECTED shape of a plan that hit the early
  baseline-rebase (`finalize-step-sync-baseline`, #786) or a post-force-push
  re-review (#742): the branch was rebased or force-pushed, so CI legitimately
  re-ran, and #849's deterministic `ci_verify` + adaptive ci-wait made that pass
  cheap and intentional. Treat `ci_rerun` as genuine churn only when the count is
  high AND cross-reads with the `quality-chain` check (`build_pending_pile`,
  `loop_back` volume) show the re-runs were chasing an unresolved red build — a
  red→green→red loop, not one rebase/re-review round-trip. `build_churn` (a build
  cluster within the clustering window) remains the local-build rework signal and
  is unaffected by the finalize-flow change.
- **`phase_reentry`** — a loop-back re-entered a phase. Post-#849/#850, a
  `5-execute` / `6-finalize` re-entry is the EXPECTED shape of the finalize triage
  loop-back (the `loop_back_without_asking` inline-replay cycle) — a loop-back that
  fixed a real finding is correct-by-design, not redundant. Read a re-entry against
  the plan's `quality-chain` `loop_back` resolutions before calling it redundant:
  informational when the re-entry corresponds to a resolved loop-back finding; a
  cost signal only when a plan pays many reentries plus heavy builds with no
  corresponding resolved findings (rework, not a productive loop-back).
- **`arch_over_resolution`** — architecture-resolution overhead dwarfing the build
  work it resolves. Surface it as a resolution-cost signal.
- **`consecutive_dup`** — apply caveat 3 before treating it as redundancy; confirm
  against the log lines.

## Adjudication against the build-minimality lessons

This check is the repeatable, corpus-wide form of the build-minimality analysis
captured across the build-minimality lesson cluster:

1. **`docs_only_build` is COVERED by the docs-only-build lesson on a Gate-1 dedup basis.**
   That lesson names the docs-only-build defect (phase-4-plan Step 7 creates
   holistic `quality-gate` / `module-tests` tasks for docs-only plans even when the
   manifest composer correctly suppressed them) and carries the corpus-wide
   build-minimality evidence (whole-tree `>400s` builds dominating; the `compile`
   verb never used). A `docs_only_build` flag here is therefore COVERED — name
   that covering lesson as the reference and do NOT re-file. The
   file-worthy signal is a *drift*: a fresh docs-only-build recurrence on a plan
   created AFTER the Step-7 docs-only guard ships, which extends that lesson
   via Gate-1 `merge_into`.
2. **`non_minimal_build` is the per-deliverable build-minimality axis.** The
   complementary "make the per-deliverable execute-loop build focused (buildable
   stuff only, scoped to the changed module, configurable cadence)" direction is
   the focused-per-deliverable-build axis referenced from the docs-only-build
   lesson's "Additional empirical proof" section. A new `non_minimal_build`
   recurrence after a focused-build remediation ships is the drift worth extending
   that lesson with; the flag itself, pre-remediation, is COVERED by the same
   lesson cluster.
3. **`build_churn` (`module-tests` serial runtime / scope-to-changed-modules) is
   the build-pyproject "make the run cheaper" axis** — the complementary
   build-pyproject cost-reduction lesson cited from the docs-only-build lesson's
   References as the "different component, different fix" lever. A churn flag is
   read against that axis: the fix is to make each run cheaper and scoped, not to
   suppress it.

Per the general lesson-filing rule, any "already covered" drop MUST name the
matching lesson ID (here the docs-only-build lesson and the build-minimality
cluster it cross-references) — assumption is not verification.

## Critical rules

- The script is the single source of truth for every per-plan number, every
  per-phase bucket, every build classification, and every corpus total. Do not
  re-parse `script-execution.log` or re-derive a duration band in chat.
- Every duration band comes from the centralized `THRESHOLDS` table
  (`build_minimal_seconds`, `build_heavy_seconds`, `build_clustering_minutes`) —
  there are NO inline magic numbers in the check. If a band must change, edit
  `scripts/audit.py`'s `THRESHOLDS` entry, not a reading.
- The three caveats above are MANDATORY to apply: the phase split is approximate
  without a `6-finalize` marker; the `verify` verb count is an upper bound while a
  heavy-duration build is a floor; and `consecutive_dup` over-counts
  same-verb/different-args calls.
- This check is read-only; it never edits `.plan/` files.
