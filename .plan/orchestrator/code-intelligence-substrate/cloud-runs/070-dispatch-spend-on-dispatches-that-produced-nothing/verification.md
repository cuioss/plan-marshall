# Verification — 070-dispatch-spend-on-dispatches-that-produced-nothing

**Audited:** `plan.md`, `report-01.md` (the only two files in the plan directory on arrival)
**Tree state:** `61a43e5` on `claude/code-intelligence-substrate-analysis-kah884`
**Landed as:** squash commit `1565a29` — *"fix(metrics): stamp productive loop-backs; report genuinely-wasted dispatch spend (#1180)"*, 14 files changed
**Overall verdict:** CONFIRMED WITH GAPS

The taxonomy widening (D1 code half), the D2 settlement, the D3 halt and the D4/D5 reader
fields are all present in the tree and behave as the report describes. Four substantive gaps
remain: the two published token figures sum a column whose "no measurement" case is a fabricated
`0` — demonstrated end-to-end here, writer to reader, not inferred; the cause-class partition those
figures are computed over is hand-written and pinned to the enum by nothing; the finalize
classification prose that D1 rerouted is guarded by no test; and the analyst-facing rule document
still asserts the proven-waste claim that the run's own CR-7 disposition removed everywhere else.

## Deliverable verdicts

| # | Deliverable (short) | Report claim | Ground truth | Verdict |
|---|---|---|---|---|
| D1 | Taxonomy member for a productive non-completion + widen the audit rule | DONE | Member present (`manage-metrics.py:102`), finalize 5c table routes `loop_back → returned_with_findings` (`phase-6-finalize/SKILL.md:1100`), rule doc widened (`logging-gap-analysis.md:10,106-115`), all full-enum mirrors in sync and guarded. But the routing prose itself is pinned by no test, and the plan's Verification section demands the routing be shown, not just the writer's acceptance | PARTIAL |
| D2 | Populate or drop the four context-load columns; measured vs unproduced distinguishable | SETTLED by prior `unmeasured` work; no code change | Re-derived: the writer writes the `unmeasured` literal for an omitted flag (`manage-metrics.py:3185-3188`), the retrospective reader reads four ways (`analyze-logs.py:1042-1070`), `test_record_model_representability.py` pins writer + both readers; a repository sweep finds the four flags only in the writer's argparse, `data-format.md`, `SKILL.md` and a test fixture — no producer | CONFIRMED (via a third arm the plan's literal *Done when* does not name) |
| D3 | Re-derive the non-productive population, first-party | BLOCKED on corpus | No sweep/measurement code anywhere in the landed diff; no share figure quoted; the retired "a third of finalize dispatch spend" string appears only in `plan.md:154` labelled RETIRED and in the report's own statement that it is not quoted | CONFIRMED (correctly ships nothing) |
| D4 | Separate RETRYABLE from TERMINAL | code DONE; class shares blocked | `_RETRYABLE_CAUSES` / `_TERMINAL_WASTE_CAUSES` (`analyze-logs.py:1025-1026`), summed and returned separately (`analyze-logs.py:1241-1254`), test proves they never fold. But `retryable_total_tokens` sums `total_tokens`, which the writer defaults to `0` on an omitted flag — the systematic case for a cancelled/restarted dispatch, demonstrated end-to-end below (G1); and the two cause-class tuples are hand-picked strings with no guard tying them to `DISPATCH_TERMINATION_CAUSES`, so a future member falls into neither figure (G13) | PARTIAL |
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
- **Found:** the landed diff contains no sweep, no corpus reader, no share arithmetic. Re-counted
  from `git show --stat 1565a29`: the 14 changed files are the taxonomy (`manage-metrics.py`), the
  two retrospective scripts, four docs, five test files, **and the two plan-directory files**
  (`plan.md`, a pure rename with 0 line changes, and `report-01.md`, +126). Repository-wide
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
  retryable figure has **no path on the timeout sub-case, and no measured value on the others**:
  (a) on the finalize ledger the 5c gate fires "only
  when the step ran as a Task agent and did NOT time out" (`phase-6-finalize/SKILL.md:1093`) while
  its own `blocked_session_restart` row is defined as *"a session restart, harness cancellation, or
  the per-agent timeout budget firing"* (`:1102`), so the **timeout** sub-case can never write a row
  at all — the session-restart and harness-cancellation sub-cases can, and a probe proved a written
  row is accepted (§ Correctness review item 2) — and `harness_cancellation` is absent from the
  finalize value list
  (`:1110`) (G3); and (b) wherever a retryable row *is* written, its `total_tokens` defaults to `0` unless
  the caller measured it — proven end-to-end below — for the very `<usage>` a cancelled dispatch
  never produces (G1); and (c) nothing pins the two cause-class tuples to the enum they partition
  (G13).

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
  re-read at `test_compile_report.py:948` (`| 6-finalize | 0 | 10000 | 16000 | 2 | 0 | 0 |`,
  verbatim) and `test_compile_report_behavior.py:143`
  (`| 5-execute | 2 | 10000 | 16000 | 2 | 1 | 3 |`, verbatim).
- **Verdict:** PARTIAL — emitted, rendered, tested. Two properties of the published figure fall
  short of the standard this plan itself argues for: the renderer manufactures a `0` from an absent
  key (`compile-report.py:373-375`, and `test_compile_report.py:876` pins that behaviour, under the
  comment at `:875` — *"This fixture carries none of the new figures, so they default to 0"*) — G6;
  and the summed column itself admits fabricated zeros — G2. The owning-module relocation (into
  `plan-retrospective` rather than the hypothesised `manage-metrics`) is sanctioned by the plan's
  *"resolve the owning module at outline"* and is well reasoned in the report; not a finding.

## Correctness review

Read in full: `_parse_dispatch_boundary_file` and `read_dispatch_boundaries_per_phase`
(`analyze-logs.py:1013-1255, 1346-1385`), `render_dispatch_boundaries_body`
(`compile-report.py:336-383`), `cmd_record_dispatch_boundary` (`manage-metrics.py:3120-3230`) and
its argparse block (`:3798-3840`), the finalize 5c step (`phase-6-finalize/SKILL.md:1092-1114`),
and the `DISPATCH_TERMINATION_CAUSE` rule (`logging-gap-analysis.md:105-176`).

Defects found:

1. **A fabricated `0` enters both published cause-class sums — demonstrated end-to-end, not
   inferred.** `manage-metrics.py:3157-3159` — `total_tokens = args.total_tokens if
   args.total_tokens is not None else 0`; `--total-tokens` is optional (`default=None`,
   `manage-metrics.py:3832-3837`), so the coercion is reachable from every call site.
   `error_total_tokens` and `retryable_total_tokens` sum that column
   (`analyze-logs.py:1241-1246`), which parses it as a bare `int(parts[2])` (`:1143`) with no
   unmeasured state.

   **First-party probe (writer → disk → reader, no fixtures; command log in the Adversarial review
   section).** Three rows written into a real `6-finalize` ledger: an `error` with `--total-tokens`
   omitted, an `error` carrying `7000`, and a `blocked_session_restart` with the flag omitted. The
   bytes on disk:

   ```text
   2026-08-18T20:47:19Z,error,0,0,0,unmeasured,unmeasured,unmeasured,unmeasured
   2026-08-18T20:47:20Z,error,7000,3,20000,unmeasured,unmeasured,unmeasured,unmeasured
   2026-08-18T20:47:20Z,blocked_session_restart,0,0,0,unmeasured,unmeasured,unmeasured,unmeasured
   ```

   The reader then returns `error_total_tokens = 7000` and `retryable_total_tokens = 0`. Row 1 is
   the defect in its purest form: **the same row** says `unmeasured` on the four columns D2
   protected and `0` on the one column D4/D5 publish. Row 3 shows the retryable figure reading `0`
   for a dispatch that was genuinely blocked. Nothing downstream can tell either from a measured
   zero.

   The writer's own docstring at `manage-metrics.py:3126-3128` still justifies the default —
   *"The legacy five columns are unchanged: they keep their `0` default, because nothing downstream
   distinguishes an absent from a zero on those"* — which is precisely what this plan made untrue.
   The run's own test suite writes such a row without noticing:
   `test_returned_with_findings_subprocess_accepted_by_argparse`
   (`test_manage_metrics_record_dispatch_boundary.py:572`) invokes the writer with no token flags
   at all.

   **Correction to the earlier reading of the call sites.** There are **four**
   `record-dispatch-boundary` invocations across **three** documents, not two:
   `workflow/execution.md:212` (5-execute, carries *"use `0` when the field is absent"* at `:219`),
   `workflow/execution.md:257` (a synthesised `clean_exit_queue_empty` row that passes
   `--total-tokens 0` deliberately — a licit fabricated zero, reaching **neither** sum),
   `workflow/planning-outline.md:463` (4-plan, same *"use `0`"* instruction at `:468`), and
   `phase-6-finalize/SKILL.md:1109` — which carries **no** `0`-fallback instruction at all, only
   *"Forward the `<usage>` totals captured by 5b"*. So the finalize ledger — the phase this plan
   was written about, and the only one that can carry `blocked_session_restart` — reaches the
   fabricated `0` through the **writer's default alone**. That makes `manage-metrics.py:3157` the
   root cause binding all sites, and a fix confined to the two workflow documents insufficient.

2. **The finalize 5c gate and the cause it classifies describe different populations.**
   `phase-6-finalize/SKILL.md:1093` gates 5c on the step having *"did NOT time out"*, while
   `:1102` defines `blocked_session_restart` as *"a session restart, harness cancellation, or the
   per-agent timeout budget firing (timeout block at item 5 above)"* — three sub-cases, one of
   which the gate structurally excludes. A timed-out finalize step therefore writes **no boundary
   row at all** (5b/5c are both skipped; the timeout path at item 5 only logs ERROR and marks the
   step `failed` — `:1055-1057`), so the finalize ledger under-counts its own dispatched
   population as well as its retryable spend. `harness_cancellation` is additionally absent from
   the finalize invocation's value list (`:1110`).

   ⚠ **Correction to an earlier reading:** this is a *narrowing and a self-contradiction*, not a
   structural impossibility. The remaining two sub-cases — a session restart or a harness
   cancellation that still returns control to the dispatcher — are not excluded by the gate, and
   the writer imposes **no** phase/cause coupling: the probe above wrote a `blocked_session_restart`
   row onto a `6-finalize` ledger and the writer accepted it (`choices` is the whole 12-member
   enum, checked again in-function at `manage-metrics.py:3147-3155`, with no phase cross-check).
   So `retryable_total_tokens` on the finalize file is reachable in principle and reads `0` in
   practice for the G1 reason, not because no row can exist. The contradiction predates the plan
   (both lines are unchanged in `git show 1565a29 -- …/phase-6-finalize/SKILL.md`), but D4 built a
   reported figure on top of it without noting it.

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

5. **The cause-class partition is unanchored to the enum it partitions.**
   `_TERMINAL_WASTE_CAUSES` / `_RETRYABLE_CAUSES` / `_RETURNED_WITH_FINDINGS_CAUSE`
   (`analyze-logs.py:1025-1027`) are hand-written string literals in a *different bundle* from
   `DISPATCH_TERMINATION_CAUSES` (`manage-metrics.py:79-103`). A repository-wide search for all
   three names returns only their definitions and their three use sites inside `analyze-logs.py`
   — **no test, and no structural relationship to the enum**. The enum's documentation mirrors are
   each guarded by a structural-equality test with an executable negative control
   (`test_manage_metrics.py:3870/3905`, `:4016/4027`, `:4048/4053`); this partition, which decides
   what two *published* figures are computed over, is guarded by nothing. A member added to
   `DISPATCH_TERMINATION_CAUSES` falls into neither class and is silently absent from both figures.
   The plan warned against exactly this shape — D3: *"⛔ **Derive the terminal-state vocabulary from
   the schema**, not from the two names that happened to be observed — they are a sample, not the
   enum"* — and `_RETRYABLE_CAUSES` is literally those two names. Recorded as G13.

6. **The CR-7 relabelling missed three surfaces inside the shipped code and its tests.**
   The rendered header is `error_total_tokens (terminal-error)` (`compile-report.py:357`), but the
   local it feeds is still `wasted = phase_data.get('error_total_tokens', 0)` (`:373`), and three
   test comments still name the quantity by the retired framing —
   `test_compile_report.py:873` and `:943` (*"error_total_tokens (wasted)"*), `:947`
   (*"the genuinely-wasted vs retryable split"*), and
   `test_compile_report_behavior.py:140` (*"the genuinely-wasted vs retryable spend split"*).
   Cosmetic individually; together they are the same overclaim CR-7 removed, surviving beside the
   code that no longer makes it. Recorded as G8.

No other defect was found: the reader's guards (`len(parts) < 5` floor, per-column parsing, the
two-pass zero-provenance gate) all fire on their stated inputs, the cause-class tuples contain no
overlap **with each other** (their gap against the enum is defect 5), the absent-file path returns
every key, and the new member cannot be written without passing both the argparse `choices` and the
in-function membership check (`manage-metrics.py:3147-3155`).

## Test adequacy

| Deliverable | Covering tests | Adequacy |
|---|---|---|
| D1 enum half | `test_manage_metrics.py:2808-2822` (`test_enum_contains_exactly_twelve_values`, `test_enum_contains_returned_with_findings_cause`), `test_manage_metrics_record_dispatch_boundary.py:532-589` | Adequate; the writer test asserts the exact row bytes `,returned_with_findings,73000,21,210000` on the 6-finalize file |
| D1 mirror sync | `test_manage_metrics.py:3870/3905`, `:4016/4027`, `:4048/4053` — each positive guard paired with a negative control that drops one value and requires the guard to raise (line numbers re-taken at the `def`, correcting an earlier off-by-two that cited the docstrings) | Strong; the negative controls are executable, not commentary |
| D1 routing half | *none* | **Gap (G5)** — proven by construction, not only by grep: the sole full-enum doc guard parses manage-metrics' own SKILL.md, the plugin-doctor rule scans `## Canonical invocations` blocks, and no test in `test/plan-marshall/phase-6-finalize/` mentions a termination cause — though that directory does ship `test_loop_back_outcome.py`, a markdown-contract test over this very SKILL.md, so the shape G5 asks for already exists next door |
| D1 rule-scope half | `test_dispatch_waste_and_finalize_scope.py:200-216` | Adequate **for the RED-before regression** — both asserted strings were absent pre-change. Containment-only, however: it asserts the doc *names* `metrics-dispatch-boundaries-{phase}.toon` and `6-finalize`, not that the precondition no longer scopes to execute alone, so a later re-narrowing that left the Inputs line intact would stay green |
| D2 | `test_record_model_representability.py:406,428,455,783,816,899,910` | Strong — writer + both readers + the measured-zero negative control |
| D4/D5 | `test_dispatch_waste_and_finalize_scope.py:78-144`, `test_compile_report.py:901-948`, `test_compile_report_behavior.py:126-144` | Non-vacuous at the reader: the conflation mutation turned 3 of 6 red, reproduced independently (evidence above). Two holes: the renderer test at `:876` *pins* the manufactured-zero default rather than rejecting it (G6), and no test in the set exercises a row whose `total_tokens` was never measured — every fixture row carries a measured value, which is why G1 ships green (G1) |

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
  reported `clean`."* — `dc8e352` was **not** the final head. `pull_request_read get_status` on
  #1180 reports `sha: f45bae2e751a111bc0e27b84347527ce56be93ef`, the report-finalization commit.
  The CI evidence in the report is quoted one commit behind the head the merge gate acted on (G10).
  Re-derived independently here: `get_status` alone is *not* sufficient evidence — it returns
  `total_count: 1`, carrying only CodeRabbit's *"Review rate limited"* commit status. The green
  claim is established instead by `get_check_runs`, which on `f45bae2` returns **7** check runs
  with `verify / conclusion` = `success` (completed 16:36:31Z), alongside `verify / verify`,
  `verify / gate`, `dependency-review / dependency-review` and `generate-check` all success and
  `Sourcery review` / `auto-merge` skipped. So the outcome the report claims was correct on the
  real head. Two details of the sentence are still wrong: the SHA, and `review / review`, which the
  report lists as success but which does not appear among the final head's 7 check runs at all.
- *"D5 reads `total_tokens` (column 3, produced), not these columns."* — **False**, not merely
  overstated, and it is the report's load-bearing error. Column 3 is produced only when the caller
  forwards `--total-tokens`, an optional flag; the writer coerces a missing value to `0`
  (`manage-metrics.py:3157`). Two of the four call sites instruct *"use `0` when the field is
  absent"* (`execution.md:219`, `planning-outline.md:468`) and the finalize call site
  (`phase-6-finalize/SKILL.md:1109`) states no fallback at all, so the writer's default governs
  there. Proven end-to-end in Correctness review defect 1: a `record-dispatch-boundary` call that
  omits the flag writes `,error,0,0,0,unmeasured,unmeasured,unmeasured,unmeasured` — the same row
  representing "not measured" correctly on columns 6-9 and fabricating a `0` on the column D5
  publishes. The distinction D2 protects does not exist for that column (G1, G2).
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
| Step-9 proposal: name the review-summary-bodies MCP call in the lane's gh↔MCP mapping (to be shipped as a separate `chore/` PR) | **Closed** | Shipped as `4a1936e` *"chore(cloud-plan-lane): map review-summary bodies to get_reviews (#1184)"*; the mapping row is present at `.claude/skills/cloud-plan-lane/SKILL.md:74` and the three-read-methods surface table + requirement at `:1168-1180`, both re-read verbatim |

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
  `grep -rn "termination_cause" --include="*.py" marketplace/` finds no consumer **within
  `marketplace/`** outside `manage-metrics` and `plan-retrospective`. One consumer lives outside that
  scope: `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py:7195` carries
  `termination_cause` in `_BC_LEDGER_FIELDS` and parses the same ledger file independently of
  `plan-retrospective`'s reader — a lock-step surface for any ledger-format change, and one the
  architecture inventory does not crawl (`data-format.md:944`; see `gaps.md` G1 § Risk if fixed).

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
confirmed clean for it. Both readings were reproduced independently during the adversarial review
(same counts, same `assert 26000 == 10000` failure message), and a **first-party writer→disk→reader
probe** was run there in addition — see § Adversarial review.

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

## Adversarial review

Independent review of this document and `gaps.md`. Attacks run: A1 false positives, A2 false
negatives, A3 vacuous evidence, A4 counts and quotes, A5 actionability, A6 severity/topic,
A7 coverage, A8 internal consistency.

Tree state at review: `f9e58e1`. Every `path:line` in both documents was re-opened at that commit;
the only working-tree modifications present were other sessions' `doc/plans/**` audit files, so
none of the production files reasoned about here was in flight.

| # | Attack | What was found | Correction applied |
|---|---|---|---|
| A1 | False positives | **No gap was fabricated.** All twelve entries re-checked at their cited `path:line`; every citation resolves and every quoted line is verbatim. Two claims were **overstated**, one materially: G3 asserted "no row with a retryable cause can be written to the finalize ledger", but the 5c gate excludes only the *timeout* sub-case of `blocked_session_restart` — the session-restart and harness-cancellation sub-cases pass it, and the writer imposes no phase/cause coupling at all (verified by writing a `blocked_session_restart` row onto a real `6-finalize` ledger and having it accepted). G1's Risk claim that `audit.py` "will treat the token as unrecognised" was also wrong | G3 rewritten as a gate-vs-cause-table contradiction plus a narrowing, retitled, with the never-written timed-out row added as the sharper consequence; correctness-review defect 2 rewritten to match. G1's Risk corrected: `total_tokens` is in `_BC_LEDGER_FIELDS` but not `_BC_LEDGER_UNMEASURABLE_FIELDS`, so the token would take the `_to_int` branch and be reported as a **measured zero** — a silent failure, worse than the one claimed |
| A2 | False negatives | **One real defect the audit missed.** The cause-class partition (`_TERMINAL_WASTE_CAUSES` / `_RETRYABLE_CAUSES` / `_RETURNED_WITH_FINDINGS_CAUSE`, `analyze-logs.py:1025-1027`) is three hand-written literals in a different bundle from the enum, with **no test and no structural tie** to `DISPATCH_TERMINATION_CAUSES` — a guard that cannot fire. The audit checked the tuples for *overlap* but not for *coverage*: the bidirectional requirement verified in one direction only. The plan warned against exactly this ("the two names that happened to be observed — they are a sample, not the enum") and `_RETRYABLE_CAUSES` is literally those two names. Also missed: `test_compile_report.py:947` and `test_compile_report_behavior.py:140` carry the same retired framing G8 lists, and `report-01.md:64` is wrong about `review / review` independently of its wrong SHA. D1/D2/D3 re-read against their literal *Done when* — all three verdicts hold | New **G13** filed (medium, `measurement/metrics`) with an executable *Done when*; correctness-review defect 5 added as its trace. G8's Where and Done-when widened to five surfaces; correctness-review defect 6 added as G8's trace (it previously had none — an A8 hole). G10's evidence extended with the `review / review` finding |
| A3 | Vacuous evidence | The audit's one mutation sweep was **re-run independently** and reproduces exactly: `_TERMINAL_WASTE_CAUSES` widened to `('error', 'blocked_session_restart', 'harness_cancellation')` → `3 failed, 3 passed`, failing message `assert 26000 == 10000` / `26000 = int(26000)`. File restored from a byte snapshot at `…/scratchpad/adv-070-mutsweep/analyze-logs.py.orig`; md5 matches the pre-mutation bytes and `git status --porcelain` is clean for that path. The audit's abandoned second mutation (finalize prose) was **not retried** — the by-construction proof was instead re-derived directly, over all 28 files in `test/plan-marshall/phase-6-finalize/`. Separately, the D4/D5 fixture was found to carry a measured `total_tokens` on **every** row, which is precisely why G1 ships green — a vacuity the audit noted as a defect but not as a test-adequacy hole | Test-adequacy row for D4/D5 amended to name that second hole. G5's evidence re-derived and extended with the `test_loop_back_outcome.py` precedent, which lives in the very directory G5 says has no such test — strengthening its actionability |
| A3 | New evidence produced | The audit established G1 by **reading** the writer and the two workflow documents. That is inference, not measurement. A first-party writer→disk→reader probe was run instead: `record-dispatch-boundary` invoked three times against a real ledger (an `error` with `--total-tokens` omitted, an `error` carrying `7000`, a `blocked_session_restart` with the flag omitted), then `_parse_dispatch_boundary_file` run over the result. Row 1 on disk is `,error,0,0,0,unmeasured,unmeasured,unmeasured,unmeasured` — **one row** saying "not measured" on the four columns D2 protected and fabricating a `0` on the column D5 publishes. Reader output: `error_total_tokens = 7000`, `retryable_total_tokens = 0` | G1 and correctness-review defect 1 rebuilt around the probe: the ledger bytes and the reader output are now quoted directly. G2's evidence gains the same demonstration from the consuming side |
| A4 | Counts and quotes | Re-derived at HEAD: 12 enum members with `returned_with_findings` at `manage-metrics.py:102` ✓; 14 changed files in `1565a29` ✓ but the audit's enumeration accounted for only 12 of them; five `grep` hits for `returned_with_findings` under `test/` ✓; two hits for the retired share figure ✓; every mirror line (`SKILL.md:423,442,770`, `data-format.md:946`, `logging-gap-analysis.md:10,124-127`) exact ✓; both *"use `0` when the field is absent"* quotes verbatim at the cited lines ✓; `logging-gap-analysis.md:160-168` verbatim ✓; the two rendered-row strings verbatim ✓. Four citation slips: the mirror-sync negative controls are at `3905/4027/4053` (the audit cited the docstrings, `3907/4029/4055`); `test_compile_report.py`'s comment is at `:875` and its assertion at `:876`; the `test_compile_report_behavior.py` render assertion is at `:143`, not the fixture lines `133-135`; the cloud-plan-lane requirement spans `:1168-1180` | All four corrected. The 14-file enumeration corrected to name `plan.md` and `report-01.md`. `get_status` was **re-derived** rather than trusted: it returns `total_count: 1` carrying only CodeRabbit's status, so it does not evidence a green `verify / conclusion`; `get_check_runs` on `f45bae2` does (7 runs, `verify / conclusion` success at 16:36:31Z) |
| A5 | Actionability | Two entries failed the bar. **G3**'s *Done when* — "the gate and its cause table describe the same population" — is not observable by a run that has read neither the plan nor this audit. **G10**'s action was a future-run habit ("in a future lane run, capture the CI verdict after…") with nothing to execute now, though a concrete correction to `report-01.md:64` was available and unstated. G13 was written to the bar from the start (a named test turns red on a named edit). The other ten entries each name a concrete path, a concrete change and an observable *Done when* | G3's *Done when* rewritten into four checkable conditions over named line ranges. G10 given a concrete first action (correct `report-01.md:64` to name `f45bae2` and drop `review / review`), with the lane-contract habit kept as a secondary item |
| A6 | Severity and topic | Severities hold against the calibration. **G1 = high** is not merely defensible but understated by the audit's own framing: `error_total_tokens` *mixes* measured and fabricated, while `retryable_total_tokens` is systematically fabricated — its two causes are exactly the terminations that emit no `<usage>` — so "a measurement misreports" applies in the strong form. Topics: G4 and G8 sat under `documentation-surface` while G9, the same CR-7 correction in the same file family, sat under `measurement/metrics`; that split would send one correction to three fix plans | G1's *Why it matters* rewritten to state the mix-vs-systematic asymmetry. G4 and G8 re-topiced to `measurement/metrics` with the reason recorded inline; a grouping note added at the top of `gaps.md` binding G4/G7/G8/G9 into one sweep and naming G1 as the root cause to fix before G2/G3/G12 |
| A7 | Coverage | Complete. All five deliverables carry a verdict and a per-deliverable section; out-of-scope compliance, report accuracy (both true and false claims), the residue table and the method/limits section are all present. No deliverable is silently unmentioned. The plan's three exclusions were each checked against the landed stat independently | None needed |
| A8 | Internal consistency | The overall verdict follows from the rows (three PARTIAL, two CONFIRMED → CONFIRMED WITH GAPS). Every verification finding traces to a gap **except G8**, whose subject — the `wasted` local and the stale test comments — appeared nowhere in `verification.md`. Conversely every gap traced back. After the A2 finding, G13 also needed a trace | Correctness-review defect 6 added for G8 and defect 5 for G13; the D4 row, the D4 verdict and the document's opening summary updated so the four substantive gaps named there match the four filed |

**Residual doubt:** the one thing this round could not settle is D1's *behavioural* half — that a real
finalize loop-back is stamped `returned_with_findings` at runtime. The 5c classification is
LLM-executed prose with no code seam, so both the original audit and this review verified it as far
as the tree allows (writer acceptance plus the prose contract) and recorded the residue as G5. A
further round would most likely go after the *rest* of the reader family the same way this one went
after `total_tokens`: `tool_uses` and `duration_ms` share the identical `else 0` coercion
(`manage-metrics.py:3158-3159`) and are not yet summed by anything, so they are a latent repeat of
G1 the moment a future plan publishes them — G1's action names them, but no gap here measures them.
The second likely find is `unknown_count` / `clean_exit_queue_empty_count`, which share G6's
`.get(…, 0)` default and are noted inside G6 rather than filed.

**Verdict on the audit:** SOUND AFTER CORRECTION — every gap it filed is real and no working code
would be changed by acting on it, but its central finding rested on inference where a first-party
probe was available, it overstated G3 into a claim the tree contradicts, and it missed a guard that
cannot fire (G13) by checking the cause-class partition for overlap without checking it for
coverage.
