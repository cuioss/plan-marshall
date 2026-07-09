# Check: sequence-and-build-minimality (cross-plan)

Reconstructs each plan's call sequence from its plan-scoped
`logs/script-execution.log` (the ordered, unambiguous call timeline), buckets
every call into a phase by the `logs/work.log` `[DISPATCH] role=phase-N`
timeline, and studies **build minimality**: the thesis that a build after a
deliverable should be FOCUSED (compile + test-compile + test-run for the CHANGED
module only) and should only run on buildable stuff. Operationalizes the two
prototype deep-dives — `.plan/temp/sequence_analysis.py` (per-plan sequence
reconstruction + redundancy detection) and `.plan/temp/build_minimality.py`
(build-duration classification + build-verb mining) — as a single repeatable
cross-plan check. The deterministic computation lives in `scripts/audit.py`
(`cross_sequence_build_minimality` / `_sequence_build_minimality_plan` /
`emit_sequence_build_minimality_block`); this sub-document is the interpretation
guide.

This is a cross-plan check: it emits one aggregate block (per-plan rows + corpus
build-class / build-verb totals + the duration-band thresholds) rather than one
row per plan in isolation. It builds on the D1 severity infrastructure — every
per-plan row carries the uniform `severity` column and the block carries a
`genuine_signal_count` summary line.

## Inputs the check reads

For every scanned plan the script joins four structured inputs:

| Input | Field(s) read | Used for |
|-------|---------------|----------|
| `logs/script-execution.log` | per-call `notation subcommand (N.NNs)` lines (timestamp-ordered) | call timeline, per-phase call counts, build duration, arch-call count, consecutive-dup |
| `logs/work.log` | `[DISPATCH] role=phase-N` markers; `module-tests`/`quality-gate`/`verify`/`coverage`/`compile` verb mentions | phase segmentation, per-role dispatch counts (phase-reentry), build-verb scope mining |
| `references.json` | `modified_files` / `affected_files` list | docs-only footprint (`.py` presence) |
| `status.json::metadata` | `change_type` | docs-only classification |
| `artifacts/ci-runs/` | directory count | `ci_runs` (CI re-run signal) |

The `script-execution.log` is the authoritative ordered source — it records every
script call with its three-segment notation, subcommand, and optional trailing
`(N.NNs)` duration. The `work.log` supplies the phase-dispatch timeline (each
phase-N agent dispatch is a `role=phase-N` marker) and the qualitative build-verb
mentions. Best-effort: a plan with no logs degrades to an all-zero row rather than
raising.

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

Every `build-pyproject:pyproject_build run` call is classified by its recorded
wall-clock duration against the centralized `THRESHOLDS` bands — **no magic number
is re-declared in the check**:

| Class | Band | Reading |
|-------|------|---------|
| `minimal` | `< build_minimal_seconds` (120s) | compile / small scoped run. |
| `scoped` | `build_minimal_seconds … build_heavy_seconds` (120–400s) | single-module tests. |
| `heavy` | `> build_heavy_seconds` (400s) | whole-tree `verify` / all-modules — **NOT minimal**. |
| `unknown` | duration not recorded (0.0) | classification withheld. |

`max_build_seconds` and `total_build_seconds` carry the worst single build and the
summed build time for the plan.

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
corpus_build_seconds: <sum>
corpus_build_churn: <sum>
corpus_ci_runs: <sum>
corpus_consecutive_dup: <sum>
corpus_docs_only_build_plans: <count>
genuine_signal_count: G
rows[K]{plan_id,change_type,calls,span_seconds,builds,build_minimal,build_scoped,build_heavy,max_build_seconds,build_churn,arch_calls,ci_runs,consecutive_dup,phase_reentry,verbs,phase_graph,flags,severity}
```

| Column | Meaning |
|--------|---------|
| `plan_id` | The scanned plan's directory basename (rows sorted by total build seconds, desc). |
| `change_type` | Joined `status.json::metadata` change_type. |
| `calls` / `span_seconds` | Total calls and wall-clock span of the reconstructed sequence. |
| `builds` | Count of `pyproject_build run` calls. |
| `build_minimal` / `build_scoped` / `build_heavy` | Duration-band counts. |
| `max_build_seconds` | Worst single build's duration. |
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
