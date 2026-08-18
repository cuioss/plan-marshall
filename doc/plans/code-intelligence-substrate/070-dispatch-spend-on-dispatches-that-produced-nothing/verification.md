# Verification — 070-dispatch-spend-on-dispatches-that-produced-nothing

**Audited:** `plan.md`, `report-01.md` (the only two files in the plan directory on arrival)
**Tree state:** `61a43e5` on `claude/code-intelligence-substrate-analysis-kah884`
**Landed as:** squash commit `1565a29` — *"fix(metrics): stamp productive loop-backs; report genuinely-wasted dispatch spend (#1180)"*, 14 files changed
**Overall verdict:** CONFIRMED WITH GAPS

The taxonomy widening (D1 code half), the D2 settlement, the D3 halt and the D4/D5 reader
fields are all present in the tree and behave as the report describes. Three substantive gaps
remain: the two published token figures sum a column whose "no measurement" case is a fabricated
`0`, the finalize classification prose that D1 rerouted is guarded by no test, and the
analyst-facing rule document still asserts the proven-waste claim that the run's own CR-7
disposition removed everywhere else.

## Deliverable verdicts

| # | Deliverable (short) | Report claim | Ground truth | Verdict |
|---|---|---|---|---|
| D1 | Taxonomy member for a productive non-completion + widen the audit rule | DONE | Member present (`manage-metrics.py:102`), finalize 5c table routes `loop_back → returned_with_findings` (`phase-6-finalize/SKILL.md:1100`), rule doc widened (`logging-gap-analysis.md:10,106-115`), all full-enum mirrors in sync and guarded. But the routing prose itself is pinned by no test, and the plan's Verification section demands the routing be shown, not just the writer's acceptance | PARTIAL |
| D2 | Populate or drop the four context-load columns; measured vs unproduced distinguishable | SETTLED by prior `unmeasured` work; no code change | Re-derived: the writer writes the `unmeasured` literal for an omitted flag (`manage-metrics.py:3185-3188`), the retrospective reader reads four ways (`analyze-logs.py:1042-1070`), `test_record_model_representability.py` pins writer + both readers; a repository sweep finds the four flags only in the writer's argparse, `data-format.md`, `SKILL.md` and a test fixture — no producer | CONFIRMED (via a third arm the plan's literal *Done when* does not name) |
| D3 | Re-derive the non-productive population, first-party | BLOCKED on corpus | No sweep/measurement code anywhere in the landed diff; no share figure quoted; the retired "a third of finalize dispatch spend" string appears only in `plan.md:154` labelled RETIRED and in the report's own statement that it is not quoted | CONFIRMED (correctly ships nothing) |
| D4 | Separate RETRYABLE from TERMINAL | code DONE; class shares blocked | `_RETRYABLE_CAUSES` / `_TERMINAL_WASTE_CAUSES` (`analyze-logs.py:1025-1026`), summed and returned separately (`analyze-logs.py:1241-1254`), test proves they never fold. But `retryable_total_tokens` sums `total_tokens`, which callers are instructed to write as `0` when the dispatched agent produced no `<usage>` — the systematic case for a cancelled/restarted dispatch — and the finalize dispatcher's 5c gate excludes timed-out steps entirely, so the finalize ledger cannot carry a retryable row at all | PARTIAL |
| D5 | Make the waste a reported figure | DONE | `error_total_tokens` emitted (`analyze-logs.py:1241-1253`) and rendered (`compile-report.py:357-379`), tested RED-before. But the renderer defaults an absent key to `0` (`compile-report.py:373-375`, pinned by `test_compile_report.py:876`), and the summed column carries fabricated zeros, so a published "0 waste" is not distinguishable from "never measured" | PARTIAL |

## Per-deliverable detail

### D1 — taxonomy member + widened audit rule

- **Required (plan):** *"a loop-back dispatch is stamped with the new member, and the audit rule
  reads the finalize boundary file — both asserted by tests that fail before the change."*
  Verification section adds: *"exercise the loop-back path and assert the new member is what lands
  in the ledger. A unit test over the enum alone does not show the path was rerouted."*
- **Claimed (report):** member added; finalize 5c routed; rule doc widened; all mirror sites in
  lock-step; four RED-before tests.
- **Found:**
  - `marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/manage-metrics.py:79-103` —
    `DISPATCH_TERMINATION_CAUSES` now holds 12 members (re-counted from the tuple), the twelfth
    being `returned_with_findings` at line 102, with a comment naming the step-completion
    `loop_back` counterpart.
  - `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md:1095` — *"exactly one of
    the five phase-6-finalize termination causes"*; line 1100 is the `returned_with_findings` row
    (`mark-step-done` recorded `outcome: loop_back`, "Stamp this cause — never `error`"); line 1103
    keeps `error` for `outcome: failed`; line 1110's invocation lists the five-value subset.
  - `marketplace/bundles/plan-marshall/skills/plan-retrospective/references/logging-gap-analysis.md:10`
    (Inputs) and `:106-115` (rule precondition) — both now name
    `work/metrics-dispatch-boundaries-{phase}.toon` and `6-finalize` explicitly. Pre-change state
    confirmed by `git show 1565a29^:…/logging-gap-analysis.md`: Inputs and precondition named
    `work/metrics-dispatch-boundaries-5-execute.toon` only.
  - The report's parenthetical that the *programmatic* reader already globbed every phase is TRUE:
    `git show 1565a29^:…/analyze-logs.py` line 792 already carried
    `work_dir.glob('metrics-dispatch-boundaries-*.toon')`.
  - Mirror sync: `manage-metrics/SKILL.md:423,442,770`, `standards/data-format.md:946`,
    `logging-gap-analysis.md:124-127`, and the argparse `description` now **derived** from the
    tuple (`manage-metrics.py:3802-3820`), which is the CR-2 fix as described.
- **Checks run:**
  - `uv run python -m pytest test/plan-marshall/plan-retrospective/test_dispatch_waste_and_finalize_scope.py -o addopts=""` → **6 passed in 5.59s**.
  - Located every named test: `test_enum_contains_returned_with_findings_cause`
    (`test_manage_metrics.py:2814`), `test_returned_with_findings_recorded_on_the_finalize_boundary`
    (`test_manage_metrics_record_dispatch_boundary.py:542`),
    `test_analyze_logs_surfaces_the_finalize_boundary_file`
    (`test_dispatch_waste_and_finalize_scope.py:152`),
    `test_logging_gap_analysis_rule_scope_names_the_finalize_boundary_file` (same file, `:200`).
  - Guard-coverage search for the finalize prose: `grep -rln "returned_with_findings" test/` returns
    five test files (`manage-metrics/test_manage_metrics.py`,
    `manage-metrics/test_manage_metrics_record_dispatch_boundary.py`,
    `plan-retrospective/test_compile_report.py`, `…/test_compile_report_behavior.py`,
    `…/test_dispatch_waste_and_finalize_scope.py`); **none** reads
    `phase-6-finalize/SKILL.md`. `grep -rn "termination.cause\|record-dispatch-boundary\|5c"
    test/plan-marshall/phase-6-finalize/*.py` returns nothing. The one full-enum documentation guard
    (`_parse_termination_cause_sites`, `test_manage_metrics.py:3837-3890`) parses `_SKILL_MD`
    (manage-metrics' own SKILL.md) by construction, and the plugin-doctor
    `canonical-enum-choices-drift` rule scans `## Canonical invocations` blocks
    (`_analyze_canonical_enum_drift.py:4-8`) — line 1110 sits under `## Operation: finalize`, and
    is in any case a deliberate *subset*, which that rule would report as drift rather than accept.
- **Verdict:** PARTIAL — the change is real, complete across every mirror, and the audit-rule half
  is properly tested. The *routing* half is asserted only by writer-acceptance of the string on the
  finalize file; nothing fails if the 5c table is edited back to route `loop_back → error`. The
  run's CR-5 rejection is right that there is no end-to-end code seam, but a document-contract test
  — the same shape as the one it wrote for `logging-gap-analysis.md`, and the same shape used
  elsewhere in this suite for `workflow/execution.md` — was available and not written. See G5.

### D2 — the four per-dispatch token columns

- **Required (plan):** *"the columns either carry real values or are gone, and the
  measured-vs-unproduced distinction is representable and tested"*; the higher-burden asserted
  absence ("no producer") must be re-derived in the clone.
- **Claimed (report):** premise refuted; the pre-existing `unmeasured` infrastructure already
  satisfies the substantive requirement; no producer forwards the flags; no code change warranted.
- **Found / checks run:**
  - Producer sweep re-derived at HEAD:
    `grep -rn -- "--input-tokens|--cache-read-input-tokens|--cache-creation-input-tokens"` over
    `marketplace/` + `test/` yields `manage-metrics/SKILL.md:425,448,772`,
    `standards/data-format.md:73,75,76,905,907,908`, `manage-metrics.py:3851,3870,3879` (argparse)
    and `test/plan-marshall/manage-metrics/_manage_metrics_fixtures.py:158,160,161`. No workflow
    document and no dispatcher call site forwards them — the report's claim holds now.
  - Writer: `manage-metrics.py:3185-3188` — an omitted flag stays `None` and is written as
    `UNMEASURED_COLUMN_TOKEN`, never coerced to `0`.
  - Reader: `analyze-logs.py:1042-1070, 1177-1225` — four-way read (measured / `unmeasured` /
    unrecognised / indeterminate), with a row-level post-token fingerprint deciding a literal `0`.
  - Tests: `test/plan-marshall/manage-metrics/test_record_model_representability.py` carries
    `test_unmeasured_dispatch_columns_are_absent_rather_than_zero:406`,
    `test_measured_zero_dispatch_column_is_present_as_zero:428`,
    `test_composed_boundary_file_reads_three_ways_in_the_retrospective_reader:455`,
    `test_unmeasured_fixture_separates_measured_zeros_from_unmeasured_in_the_audit_ledger_reader:816`
    — writer plus both readers, including the plan's demanded negative control.
  - The landed diff (`git show --stat 1565a29`) touches none of that infrastructure, corroborating
    "no code change".
- **Verdict:** CONFIRMED, with the deviation named: neither literal arm of the plan's binary was
  taken. The columns neither carry real values nor are gone; they carry an explicit third state.
  The substantive clause — representable and tested — is met and independently re-derived here, and
  the plan's own "silence is not acceptable" bar is cleared. Recorded as G11 only because `plan.md`
  still states the binary, so a later reader re-deriving from the plan would reach the wrong
  contract.

### D3 — re-derive the population, first-party

- **Required (plan):** sweep and report count + token cost + population size, or **HALT and report
  blocked on corpus availability**; *"a halt with a clear statement of what was unreachable is a
  success; a share quoted from one run is a failure"*.
- **Claimed (report):** blocked; no share computed; the retired figure not quoted.
- **Found:** the landed diff contains no sweep, no corpus reader, no share arithmetic (the 14
  changed files are the taxonomy, the two scripts, four docs and five test files). Repository-wide
  search for the retired phrase returns exactly two hits — `plan.md:154` (labelled **RETIRED AS
  EVIDENCE**) and `report-01.md:39` (the sentence stating it is not quoted). No `.plan/` search
  artifacts exist in the diff.
- **Verdict:** CONFIRMED — the honesty deliverable is met exactly as specified.

### D4 — separate RETRYABLE from TERMINAL

- **Required (plan):** *"the two classes are reported distinctly."*
- **Claimed (report):** code half DONE via `error_total_tokens` vs `retryable_total_tokens`, never
  summed; class shares blocked on corpus.
- **Found:** `analyze-logs.py:1025-1026` (`_TERMINAL_WASTE_CAUSES = ('error',)`,
  `_RETRYABLE_CAUSES = ('blocked_session_restart', 'harness_cancellation')`), summed separately at
  `:1241-1246` and returned as separate keys at `:1252-1254`; absent-file path returns both keys as
  `0` with `present: False` (`:1099-1121`), and the renderer skips non-present phases
  (`compile-report.py:366-368`).
- **Checks run:** mutation — `_TERMINAL_WASTE_CAUSES` widened to
  `('error', 'blocked_session_restart', 'harness_cancellation')` (i.e. the exact conflation D4
  forbids); `uv run python -m pytest …/test_dispatch_waste_and_finalize_scope.py -o addopts=""` →
  **3 failed, 3 passed** (`test_error_total_tokens_sums_only_terminal_error_rows`,
  `test_returned_with_findings_counted_as_the_productive_population`,
  `test_analyze_logs_surfaces_the_finalize_boundary_file`), with the failure message
  `26000 = int(26000)` against the expected `10000`. File restored from a byte snapshot in
  `/tmp/verify-070-mutsweep/`; `git status --porcelain` clean for it afterwards.
- **Verdict:** PARTIAL — the split is real and non-vacuously tested at the reader, but the
  retryable figure has no path to a real value: (a) the finalize dispatcher's 5c gate fires "only
  when the step ran as a Task agent and did NOT time out" (`phase-6-finalize/SKILL.md:1093`) while
  its own `blocked_session_restart` row is defined as *"a session restart, harness cancellation, or
  the per-agent timeout budget firing"* (`:1102`) — the excluded case (G3); and (b) where a
  retryable row can be written (`workflow/execution.md:213`), the caller is instructed to
  *"use `0` when the field is absent"* (`:217-219`) for the very `<usage>` a cancelled dispatch
  never produces (G1).

### D5 — make the waste a reported figure

- **Required (plan):** *"the field is emitted and covered by a test."*
- **Claimed (report):** `error_total_tokens` emitted, surfaced in the `dispatch_boundaries`
  fragment, rendered in the compile-report table as `error_total_tokens (terminal-error)`, covered
  by `test_error_total_tokens_sums_only_terminal_error_rows` and the render tests; the
  proxy-vs-proof precision tightened per CR-7.
- **Found:** field emitted (`analyze-logs.py:1241-1253`); rendered header and row at
  `compile-report.py:356-379`; the CR-7 softening is present in `analyze-logs.py:1013-1024`
  (module preamble), `:1087-1093` (docstring) and the rendered column label `:357`. Section gating
  is `present: true`-conditional (`report-structure.md:17`).
- **Checks run:** the six-test file above (green at HEAD, red under mutation); render assertions
  re-read at `test_compile_report.py:945-948` (`| 6-finalize | 0 | 10000 | 16000 | 2 | 0 | 0 |`) and
  `test_compile_report_behavior.py:133-135`.
- **Verdict:** PARTIAL — emitted, rendered, tested. Two properties of the published figure fall
  short of the standard this plan itself argues for: the renderer manufactures a `0` from an absent
  key (`compile-report.py:373-375`, and `test_compile_report.py:876` pins that behaviour with the
  comment *"This fixture carries none of the new figures, so they default to 0"*) — G6; and the
  summed column itself admits fabricated zeros — G2. The owning-module relocation (into
  `plan-retrospective` rather than the hypothesised `manage-metrics`) is sanctioned by the plan's
  *"resolve the owning module at outline"* and is well reasoned in the report; not a finding.

## Correctness review

Read in full: `_parse_dispatch_boundary_file` and `read_dispatch_boundaries_per_phase`
(`analyze-logs.py:1013-1255, 1346-1385`), `render_dispatch_boundaries_body`
(`compile-report.py:336-383`), `cmd_record_dispatch_boundary` (`manage-metrics.py:3120-3230`) and
its argparse block (`:3798-3840`), the finalize 5c step (`phase-6-finalize/SKILL.md:1092-1114`),
and the `DISPATCH_TERMINATION_CAUSE` rule (`logging-gap-analysis.md:105-176`).

Defects found:

1. **A fabricated `0` enters both published cause-class sums.**
   `manage-metrics.py:3157-3159` — `total_tokens = args.total_tokens if args.total_tokens is not
   None else 0`; and the two producing call sites instruct the caller to
   *"use `0` when the field is absent"* (`workflow/execution.md:219`,
   `workflow/planning-outline.md:468`). `error_total_tokens` and `retryable_total_tokens` sum that
   column (`analyze-logs.py:1241-1246`). Consequence: a dispatch that terminated without emitting
   `<usage>` — the normal case for `harness_cancellation` / `blocked_session_restart`, and a real
   case for `error` — contributes `0` to a *published* spend figure that is presented as measured.
   This is exactly the measured-zero-vs-unproduced asymmetry D2 exists to prevent, on the two
   columns D4/D5 shipped, and no `unmeasured`-style representation exists for the legacy five
   columns (the writer's own docstring at `manage-metrics.py:3126-3128` says so: *"The legacy five
   columns are unchanged: they keep their `0` default, because nothing downstream distinguishes an
   absent from a zero on those"* — which is no longer true now that D4/D5 sum them).

2. **`retryable_total_tokens` has no populating path on the finalize ledger.**
   `phase-6-finalize/SKILL.md:1093` gates 5c on the step having *"did NOT time out"*, while
   `:1102` defines `blocked_session_restart` as precisely the timeout / restart / cancellation
   case; `harness_cancellation` is not in the finalize invocation's value list at all (`:1110`).
   So on `metrics-dispatch-boundaries-6-finalize.toon` — the file this plan widened the audit rule
   to read, and where the mis-stamping was measured — the retryable class is structurally empty and
   the rendered column will always read `0`. The contradiction predates the plan (both lines are
   unchanged in `git show 1565a29 -- …/phase-6-finalize/SKILL.md`), but D4 built a reported figure
   on top of it without noting it.

3. **The renderer defaults an absent key to `0`.** `compile-report.py:373-375`
   (`phase_data.get('error_total_tokens', 0)` and siblings). A `dispatch_boundaries` fragment
   produced by a pre-070 `analyze-logs` carries no such key, and the table then publishes
   `0` terminal-error spend for a phase where nothing measured it. `test_compile_report.py:876`
   pins this as intended behaviour.

4. **The analyst-facing rule still asserts the claim CR-7 removed.**
   `logging-gap-analysis.md:163-168`: *"`error_total_tokens` — the spend on dispatches whose
   terminal state is **genuinely non-productive**: they raised a fatal `error` and returned
   nothing… This is the figure a reader acts on: a dispatch that examined nothing and returned
   nothing cost real tokens and bought zero detection."* The code preamble, the field docstring, the
   rendered column label and the run report were all softened to "terminal-error spend / strongest
   proxy, finding-yield deferred to D3"; this document — the one the retrospective agent actually
   follows when emitting findings — was not.

No other defect was found: the reader's guards (`len(parts) < 5` floor, per-column parsing, the
two-pass zero-provenance gate) all fire on their stated inputs, the cause-class tuples contain no
overlap, the absent-file path returns every key, and the new member cannot be written without
passing both the argparse `choices` and the in-function membership check
(`manage-metrics.py:3147-3155`).

## Test adequacy

| Deliverable | Covering tests | Adequacy |
|---|---|---|
| D1 enum half | `test_manage_metrics.py:2808-2822` (`test_enum_contains_exactly_twelve_values`, `test_enum_contains_returned_with_findings_cause`), `test_manage_metrics_record_dispatch_boundary.py:532-589` | Adequate; the writer test asserts the exact row bytes `,returned_with_findings,73000,21,210000` on the 6-finalize file |
| D1 mirror sync | `test_manage_metrics.py:3870,3907,4016,4029,4048,4055` — each positive guard paired with a negative control that drops one value and requires the guard to raise | Strong; the negative controls are executable, not commentary |
| D1 routing half | *none* | **Gap (G5)** — proven by construction, not only by grep: the sole full-enum doc guard parses manage-metrics' own SKILL.md, the plugin-doctor rule scans `## Canonical invocations` blocks, and no test in `test/plan-marshall/phase-6-finalize/` mentions a termination cause |
| D1 rule-scope half | `test_dispatch_waste_and_finalize_scope.py:200-216` | Adequate — asserts both the per-phase artifact name and `6-finalize` |
| D2 | `test_record_model_representability.py:406,428,455,783,816,899,910` | Strong — writer + both readers + the measured-zero negative control |
| D4/D5 | `test_dispatch_waste_and_finalize_scope.py:78-144`, `test_compile_report.py:901-948`, `test_compile_report_behavior.py:120-140` | Non-vacuous at the reader: the conflation mutation turned 3 of 6 red (evidence above). The renderer test at `:876` however *pins* the manufactured-zero default rather than rejecting it (G6) |

Vacuity probe performed: one mutation (`_TERMINAL_WASTE_CAUSES` widened to swallow the retryable
causes) → 3 failed / 3 passed, restored from a byte snapshot at
`/tmp/verify-070-mutsweep/analyze-logs.py.orig`, `git status --porcelain` clean for that path
afterwards. A second planned mutation (dropping `returned_with_findings` from the finalize 5c
prose) was **abandoned**: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` is
being written concurrently by another audit session in this same working tree, so a mutation there
could not be attributed. The by-construction proof above stands in its place.

## Report accuracy

Verified true against the tree now:

- *"Added `returned_with_findings` to `DISPATCH_TERMINATION_CAUSES`"* — `manage-metrics.py:102`.
- *"The classification is now five causes, not four"* — `phase-6-finalize/SKILL.md:1095` and the
  five-row table; the pre-change diff confirms it said "four".
- *"its Inputs and precondition covered only `metrics-dispatch-boundaries-5-execute.toon`"* —
  confirmed against `1565a29^`.
- *"The programmatic reader `read_dispatch_boundaries_per_phase` already globbed all phases"* —
  confirmed against `1565a29^` (line 792).
- *"All enum-mirror sites moved in lock-step … and the argparse `description`"* — all five sites
  read; the description is now derived (`manage-metrics.py:3809`), which is the stronger fix CR-2
  asked for.
- *"a repository sweep … finds them only in the writer's argparse definition, the schema doc, and
  the SKILL.md"* — re-derived; the only addition is a test fixture
  (`_manage_metrics_fixtures.py:158-161`), which is not a producer.
- *"the retired figure … is not quoted anywhere"* — re-derived; two hits, both licit.
- CR-2's disposition claim that `data-format.md` and `logging-gap-analysis.md` *"were already
  guarded by structural-equality tests"* — true (`test_manage_metrics.py:4016`, `:4048`), and the
  upstream CodeRabbit comment body (read from the PR) does ask for exactly those two sites.
- Reviewer participation ("2 of 3 reviewed; `sourcery-ai` rate-limited") — corroborated from the PR:
  `get_reviews` on #1180 returns a `sourcery-ai[bot]` review whose entire body is *"you have reached
  your weekly rate limit of 500000 diff characters"*, two `coderabbitai[bot]` reviews stating
  *"Actionable comments posted: 6"*, and one inline thread on `report-01.md` — matching the
  report's 6-actionable-plus-1-inline accounting. The single `cuioss-oliver` "review" is the run's
  own reply posted through the operator account, not a third-party human review.

Inaccurate, stale or overstated:

- *"On head `dc8e352` the required `verify / conclusion` check concluded success … `mergeStateStatus`
  reported `clean`."* — `dc8e352` was **not** the final head. The report-finalization commit
  `f45bae2` followed it (the PR's own review threads show CodeRabbit re-reviewing `f45bae2` at
  16:24Z, and `pull_request_read get_status` reports `sha: f45bae2…`, overall state `success`). The
  CI evidence in the report is quoted one commit behind the head the merge gate actually acted on.
  Low severity — the merge queue re-verified, and the head that merged did carry a green overall
  status — but the quoted head is wrong (G10).
- *"D5 reads `total_tokens` (column 3, produced), not these columns."* — Overstated. Column 3 is
  *produced* only when the caller forwards `--total-tokens`; both producing workflows instruct
  *"use `0` when the field is absent"* and the writer coerces a missing value to `0`
  (`manage-metrics.py:3157`). The distinction D2 protects for columns 6-9 does not exist for the
  column D5 publishes (G1, G2).
- The D4/D5 framing *"they raised a fatal `error` and returned nothing"* survives in the shipped
  rule document (`logging-gap-analysis.md:163-168`) although the report says the precision was
  tightened; the report describes the fix as covering *"the field's docstring/comment, the rendered
  column label, and the report"* — accurate about what it changed, incomplete about where the claim
  lives (G4). The same stale framing survives in the new test file's module docstring
  (`test_dispatch_waste_and_finalize_scope.py:15-21`) and in the internal comment at
  `analyze-logs.py:1238-1240` (G7, G9).
- Build-gate figures (*"16077 passed, 1 skipped"*, *"~6m36s"*) are **UNVERIFIABLE** here — they are
  claims about a historical run, and this audit is explicitly barred from running the full suite.
  Nothing in the tree contradicts them.
- Commit hashes `0499cc7` / `d55d3c6` are **UNVERIFIABLE** — the PR landed as a squash merge
  (`1565a29`) and neither object exists in this clone (`git cat-file -t` → *"Not a valid object
  name"*). This is expected for a squash-merged branch, not a defect.

## Declared residue — current status

| Residue item (from report) | Still open? | Evidence |
|---|---|---|
| **D3 measurement** — the finding-yield sweep over archived records (count, token cost, population size, share only against a settled denominator) | **Still open** | No sweep code and no measurement artifact anywhere in the tree; `grep -rln "error_total_tokens\|retryable_total_tokens" doc/plans/` returns only this plan's report and `truthful-signals/420-…/report-01.md`, whose D3 table records the fields as *"Safe, no change"* consumers — it did not measure them |
| **D4's class shares** over archived records | **Still open** | Same evidence; additionally G1/G3 mean the retryable class would measure as `0` even where a corpus exists, so the corpus sweep alone will not close it |
| Step-9 proposal: name the review-summary-bodies MCP call in the lane's gh↔MCP mapping (to be shipped as a separate `chore/` PR) | **Closed** | Shipped as `4a1936e` *"chore(cloud-plan-lane): map review-summary bodies to get_reviews (#1184)"*; the mapping row is present at `.claude/skills/cloud-plan-lane/SKILL.md:74` and the three-read-methods requirement at `:1171-1178` |

## Out-of-scope and collateral

- The plan's three exclusions ("retry less", the full-surface re-sweep loop, the coverage-ratio
  defect) were respected: the diff contains no retry-budget change, no re-sweep change and no
  coverage-ratio change (`git show --stat 1565a29` — 14 files, all within the taxonomy, the two
  retrospective scripts, four docs and five test files).
- No share figure of any kind is computed or rendered — the plan's hard constraint on an unsettled
  denominator is honoured.
- Collateral changes beyond the deliverables: two docstring-staleness fixes in
  `analyze-logs.py` / `compile-report.py`, declared in the report as sub-agent findings 1 and 2.
  Both are present in the tree (`analyze-logs.py:1353`, `compile-report.py:94` reference
  `_parse_dispatch_boundary_file`'s authoritative shape rather than re-enumerating keys). Declared,
  proportionate, in-surface.
- One writer, one taxonomy: the plan's "do not ship two writers" constraint holds —
  `record-dispatch-boundary` in `manage-metrics.py` remains the only producer of the ledger, and
  `grep -rn "termination_cause" --include="*.py" marketplace/` finds no consumer outside
  `manage-metrics` and `plan-retrospective`.

## Method and coverage

**Checked:** the epic README, `plan.md` and `report-01.md` in full; the landed squash commit and its
stat; the pre-change versions of the rule doc, the reader and the finalize SKILL.md via
`git show 1565a29^:…`; the five production files the plan touched, read around every changed region;
the five test files, read in full or around every relevant assertion; the producer sweep for the
four context-load flags; the consumer sweep for `termination_cause` across `marketplace/`,
`test/` and `.claude/skills/`; PR #1180's reviews and review threads via the GitHub MCP
(`get_reviews`, `get_review_comments`, `get_status`); and the later plan
(`truthful-signals/420-…`) that re-examined the same reader.

**Executed:** `uv run python -m pytest
test/plan-marshall/plan-retrospective/test_dispatch_waste_and_finalize_scope.py -o addopts=""`
green at HEAD (6 passed) and red under a targeted mutation (3 failed / 3 passed), with the file
restored from a byte snapshot under `/tmp/verify-070-mutsweep/` and `git status --porcelain`
confirmed clean for it.

**Not checked / unverifiable:**

- The full `./pw verify` claim (16077 passed) — out of scope for this audit by instruction; the
  figure is a historical run claim.
- Any behaviour of the finalize dispatcher at runtime: the 5c classification is LLM-executed prose
  with no code seam, so "a loop-back dispatch is stamped `returned_with_findings` in a real run"
  cannot be observed from this clone. Verified as far as the tree allows (writer acceptance + the
  prose contract), and the residual risk is recorded as G5.
- D3/D4's corpus measurements — the archived-record corpus lives under the git-ignored `.plan/`
  tree and the plan forbids searching for it. Not searched.
- The individual pre-squash commits (`0499cc7`, `d55d3c6`) — absent from this clone.

**Environment caveat:** this working tree is shared with other concurrently running audit sessions,
and `git status --porcelain` showed unrelated in-flight mutations (e.g. a one-line mutation inside
`cmd_generate` in `manage-metrics.py`, and writes to `phase-6-finalize/standards/record-metrics.md`
and `phase-6-finalize/SKILL.md`). Every file this audit reasons about was checked against `HEAD`
before its verdict was written: the `manage-metrics.py` working-tree diff is confined to
`cmd_generate` (irrelevant to the taxonomy and the boundary writer), and
`plan-retrospective/**`, `phase-6-finalize/SKILL.md`, `manage-metrics/standards/**` and the two
test directories matched `HEAD` exactly at the time of reading. The one mutation attributable to
this audit was restored and verified clean.
