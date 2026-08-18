# Gaps — 070-dispatch-spend-on-dispatches-that-produced-nothing

The plan's substantive work landed: the taxonomy has its `returned_with_findings` member, the
finalize classification routes a loop-back to it, the audit rule reads every dispatching phase, the
context-load columns were correctly settled without a second writer, D3 halted honestly, and the
terminal-vs-retryable split is emitted, rendered and non-vacuously tested. What remains falls into
four groups: the two *published* token figures sum a column whose "no measurement" case is a
fabricated `0` (G1, G2, G6) — the exact asymmetry D2 exists to prevent, one column over; the
retryable class has no path to a non-zero value on the phase the plan was written about (G3); the
routing prose that D1 rewrote is guarded by no test, so it can silently regress (G5); and the
CR-7 proxy-vs-proof correction was applied to the code and the report but not to the analyst-facing
rule document that the retrospective agent actually follows (G4), nor to three lower-stakes
comment surfaces (G7-G9). Two residue items from the run (D3's finding-yield sweep, D4's class
shares) are still open (G12), and two low-severity record defects round out the list (G10, G11).

## G1 — Represent an unmeasured `total_tokens` instead of writing a fabricated `0`

- **Kind:** bug
- **Severity:** high
- **Topic:** measurement/metrics
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/manage-metrics.py:3157`
  (`cmd_record_dispatch_boundary`); producing call sites
  `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/execution.md:219` and
  `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning-outline.md:468`;
  consumers `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/analyze-logs.py:1241-1246`
- **Evidence:** the writer coerces a missing value —
  `total_tokens = args.total_tokens if args.total_tokens is not None else 0` — and both workflow
  documents instruct the caller to substitute `{n}` with the `<usage>` integer, "(use `0` when the
  field is absent)". `error_total_tokens` and `retryable_total_tokens` sum exactly that column. The
  writer's own docstring still justifies the default with "the legacy five columns … keep their `0`
  default, because nothing downstream distinguishes an absent from a zero on those"
  (`manage-metrics.py:3126-3128`) — no longer true since this plan made two of them the basis of a
  published figure.
- **Why it matters:** a dispatch that terminated without emitting `<usage>` — the systematic case
  for `harness_cancellation` and `blocked_session_restart`, and a real case for `error` — adds `0`
  to a figure the compile-report presents as measured spend. The published waste and retryable
  figures under-report, and a reader cannot tell "no spend" from "never measured" — the precise
  failure D2 was written to prevent for columns 6-9.
- **Action:** give `total_tokens` (and, for consistency of the row, `tool_uses` / `duration_ms`) the
  same `UNMEASURED_COLUMN_TOKEN` treatment the context-load columns already have — an omitted flag
  writes `unmeasured`, never `0` — behind the existing legacy-row floor in
  `_parse_dispatch_boundary_file` so old rows keep parsing; then make the two cause-class sums
  report an accompanying `*_unmeasured_rows` count (or omit the sum when any contributing row is
  unmeasured) rather than silently adding zero. Update `standards/data-format.md`'s column table and
  the two workflow documents to stop instructing callers to fabricate `0`.
- **Done when:** a `record-dispatch-boundary` call that omits `--total-tokens` writes a row whose
  third column is not `0`; `_parse_dispatch_boundary_file` reports that row's spend as unmeasured
  rather than folding it into `error_total_tokens` / `retryable_total_tokens`; and a test asserts a
  measured `0` and an omitted `--total-tokens` are distinguishable in both the file and the reader
  output.
- **Effort:** M
- **Risk if fixed:** every existing ledger row is a nine-column row whose third cell is an int, so
  the reader must keep accepting ints; a strict parse would drop historical rows. The
  `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py` ledger reader
  (`_BC_LEDGER_FIELDS` includes `total_tokens`) parses the same file independently and must be
  updated in lock-step or it will treat the token as unrecognised.

## G2 — Stop presenting `error_total_tokens` as measured when its inputs may be unmeasured

- **Kind:** bug
- **Severity:** medium
- **Topic:** measurement/metrics
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/analyze-logs.py:1241-1243`
  (`error_total_tokens`), rendered at
  `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/compile-report.py:373,377`
- **Evidence:** `error_total_tokens = sum(row['total_tokens'] for row in rows if
  row['termination_cause'] in _TERMINAL_WASTE_CAUSES)` — an unconditional sum with no notion of an
  unmeasured contributor, published in the "Phase Dispatch Boundaries" table under the header
  `error_total_tokens (terminal-error)`.
- **Why it matters:** D5's whole point is "a quantity nobody publishes is a quantity nobody acts
  on". A published quantity that silently mixes measured and fabricated components is worse than an
  unpublished one, because a reader acts on it. This is the same defect as G1 seen from the
  consuming side, and it is worth fixing separately: even after G1 the sum needs a policy for rows
  it cannot cost.
- **Action:** carry the contributing-row count and the unmeasured-row count alongside each sum
  (e.g. `error_total_tokens`, `error_rows`, `error_rows_unmeasured`) and render them together, so
  the table states the population the figure was computed over.
- **Done when:** the compile-report row for a phase whose `error` rows carry no usage shows the
  unmeasured count rather than an unqualified `0`, and a test pins that rendering.
- **Effort:** S
- **Risk if fixed:** the "Phase Dispatch Boundaries" table gains columns; `test_compile_report.py`'s
  exact-row assertions (`:876`, `:945-948`) must be updated together.

## G3 — Make the finalize ledger able to record a retryable termination at all

- **Kind:** bug
- **Severity:** medium
- **Topic:** dispatch/finalize
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md:1093` (the 5c gate),
  `:1102` (the `blocked_session_restart` definition), `:1110` (the five-value invocation)
- **Evidence:** the gate reads "fire only when the step ran as a Task agent and did **NOT** time
  out", while the cause it is supposed to classify reads "cut short by a session restart, harness
  cancellation, or the per-agent timeout budget firing (timeout block at item 5 above)".
  `harness_cancellation` is not even in the invocation's value list. So no row with a retryable
  cause can be written to `metrics-dispatch-boundaries-6-finalize.toon`.
- **Why it matters:** D4 shipped `retryable_total_tokens` specifically so infrastructure spend stays
  separable from deterministic failure — and on the finalize phase, the phase this plan was written
  about and whose spend it calls the majority, that figure is structurally always `0`. A reader
  concludes "no infrastructure waste in finalize" from a column that cannot be populated.
- **Action:** decide and document the intended behaviour: either the timeout path at item 5 records
  a `blocked_session_restart` boundary row before continuing (removing the timed-out carve-out for
  5c specifically, which the report's D4 claim assumes), or the `blocked_session_restart` row is
  redefined to the case 5c can actually observe and the timeout wording removed. Reflect the outcome
  in the invocation's value list.
- **Done when:** the finalize SKILL.md's 5c gate and its cause table describe the same population,
  and either a timed-out finalize step demonstrably produces a boundary row or the documentation
  no longer claims it does.
- **Effort:** M
- **Risk if fixed:** recording a row on the timeout path adds a `record-dispatch-boundary` call in
  an error path where `<usage>` is unavailable — coordinate with G1 so it does not write a
  fabricated `0`.

## G4 — Propagate the CR-7 proxy-vs-proof correction into the logging-gap rule document

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** documentation-surface
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-retrospective/references/logging-gap-analysis.md:160-168`
- **Evidence:** verbatim — "`error_total_tokens` — the spend on dispatches whose terminal state is
  **genuinely non-productive**: they raised a fatal `error` and returned nothing … This is the
  figure a reader acts on: a dispatch that examined nothing and returned nothing cost real tokens
  and bought zero detection." The same claim was softened everywhere else in response to CodeRabbit
  finding CR-7: `analyze-logs.py:1013-1024` and `:1087-1093` now say "the strongest *proxy* … NOT a
  proof of it", and the rendered column is labelled `error_total_tokens (terminal-error)`.
- **Why it matters:** this document is the instruction the retrospective agent follows when emitting
  `DISPATCH_TERMINATION_CAUSE` findings. It tells that agent to report terminal-error spend as
  proven waste — the exact unproven claim the run agreed to stop making, and the claim D3 was
  blocked from establishing.
- **Action:** rewrite the two bullets to match the code's framing: `error_total_tokens` is
  terminal-error spend, the strongest proxy for genuinely-wasted spend now that productive
  loop-backs are stamped `returned_with_findings`, with the finding-yield confirmation still
  outstanding.
- **Done when:** `logging-gap-analysis.md` contains no assertion that `error` rows "returned
  nothing" or "bought zero detection", and its wording is consistent with `analyze-logs.py`'s
  module preamble.
- **Effort:** S
- **Risk if fixed:** none beyond doc churn; the `the accepted causes:` enum set in the same file is
  pinned by `test_logging_gap_analysis_termination_cause_set_matches_the_enum`, so the edit must not
  disturb that enumeration.

## G5 — Pin the finalize 5c classification contract with a document test

- **Kind:** test-gap
- **Severity:** medium
- **Topic:** tests
- **Where:** contract at
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md:1095-1110`; the missing test
  belongs beside `test/plan-marshall/plan-retrospective/test_dispatch_waste_and_finalize_scope.py:200`
  or in `test/plan-marshall/phase-6-finalize/`
- **Evidence:** `grep -rln "returned_with_findings" test/` returns five files, none of which reads
  `phase-6-finalize/SKILL.md`; `grep -rn "termination.cause\|record-dispatch-boundary"
  test/plan-marshall/phase-6-finalize/*.py` returns nothing. The one full-enum documentation guard
  (`_parse_termination_cause_sites`, `test_manage_metrics.py:3837`) parses manage-metrics' own
  SKILL.md by construction, and the plugin-doctor `canonical-enum-choices-drift` rule scans
  `## Canonical invocations` blocks — line 1110 sits under `## Operation: finalize` and is a
  deliberate subset the rule would reject rather than guard.
- **Why it matters:** D1's *Done when* is "a loop-back dispatch is stamped with the new member", and
  the plan's Verification section warns explicitly that "a unit test over the enum alone does not
  show the path was rerouted". The only shipped assertion is that the writer accepts the string on
  the finalize file. If the 5c table is edited back to route `loop_back → error`, the whole
  deliverable silently reverts with every test still green.
- **Action:** add a document-contract test (the shape already used for `logging-gap-analysis.md`)
  asserting that the 5c cause table maps `outcome: loop_back` to `returned_with_findings` and
  `outcome: failed` to `error`, that the table's row count matches the invocation's brace-form value
  list, and that every value in that list is a member of `DISPATCH_TERMINATION_CAUSES` (a subset
  check, not equality). Pair it with a negative control that mutates the parsed text and requires
  the assertion to raise.
- **Done when:** removing `returned_with_findings` from either site in `phase-6-finalize/SKILL.md`
  turns a named test red.
- **Effort:** S
- **Risk if fixed:** a text-parsing test couples to the table's markdown shape; write the parser
  against the `| cause | rule |` row form and the `--termination-cause {…}` brace form, both of
  which are stable across the file's history.

## G6 — Do not render an absent dispatch-boundary figure as `0`

- **Kind:** bug
- **Severity:** medium
- **Topic:** measurement/metrics
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/compile-report.py:371-378`
  (`render_dispatch_boundaries_body`); the behaviour is pinned by
  `test/plan-marshall/plan-retrospective/test_compile_report.py:876`
- **Evidence:** `wasted = phase_data.get('error_total_tokens', 0)` /
  `retryable = phase_data.get('retryable_total_tokens', 0)` /
  `returned_with_findings = phase_data.get('returned_with_findings_count', 0)`, and the test's own
  comment: "This fixture carries none of the new figures, so they default to 0", asserting
  `| 5-execute | 0 | 0 | 0 | 0 | 0 | 3 |`.
- **Why it matters:** a `dispatch_boundaries` fragment produced by a pre-070 `analyze-logs` (any
  archived plan re-compiled later) has no such keys, and the report then publishes zero
  terminal-error spend for a phase where nothing measured it. The repository's own absent-is-not-zero
  rule — stated in this very reader family (`analyze-logs.py:1076-1079`: "A consumer testing for a
  context-load value MUST test for the key's presence — an absent key is never a zero") — is
  violated by its own renderer.
- **Action:** render an explicit non-numeric marker (e.g. `unmeasured`) when the key is absent, and
  change the test to assert that marker rather than `0`.
- **Done when:** a fragment lacking `error_total_tokens` renders a cell that is not `0`, and a test
  asserts the distinction between that cell and a phase whose measured value is `0`.
- **Effort:** S
- **Risk if fixed:** downstream consumers of the rendered table that parse the column as an integer
  would meet a non-numeric cell; the JSON dump appended after the table is unaffected.

## G7 — Correct the stale "returned nothing" framing in the new test file's docstring

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** tests
- **Where:** `test/plan-marshall/plan-retrospective/test_dispatch_waste_and_finalize_scope.py:15-21`
- **Evidence:** "`error_total_tokens` (a dispatch that raised a fatal error and returned nothing —
  the genuinely-wasted spend, a reported figure rather than a derivable one)" — the pre-CR-7
  wording, which the production code no longer uses.
- **Why it matters:** the test file is the executable specification of D4/D5; it now specifies a
  stronger claim than the code makes, and a later reader will reinstate the overclaim from it.
- **Action:** restate as terminal-error spend / strongest proxy, with the finding-yield proof
  deferred, matching `analyze-logs.py:1013-1024`.
- **Done when:** the module docstring contains no assertion that `error` rows produced nothing.
- **Effort:** S
- **Risk if fixed:** none — docstring only.

## G8 — Rename the renderer's `wasted` local and the stale "(wasted)" column comments

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/compile-report.py:373`
  (`wasted = phase_data.get('error_total_tokens', 0)`);
  `test/plan-marshall/plan-retrospective/test_compile_report.py:873,943` ("Columns: phase | rows |
  error_total_tokens (wasted) | …")
- **Evidence:** the rendered header is `error_total_tokens (terminal-error)`
  (`compile-report.py:357`), but the local variable and the two test comments still call the same
  quantity "wasted".
- **Why it matters:** the CR-7 disposition claims the label was corrected; three surfaces still
  carry the old one, so the next reader sees a contradiction between the code and its own comments.
- **Action:** rename the local to `terminal_error` and update the two comment lines.
- **Done when:** `grep -n "wasted" compile-report.py test_compile_report.py` returns nothing that
  refers to `error_total_tokens`.
- **Effort:** S
- **Risk if fixed:** none.

## G9 — Correct the "Genuinely-wasted (terminal)" inline comment in the reader

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** measurement/metrics
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/analyze-logs.py:1238-1240`
- **Evidence:** "# Genuinely-wasted (terminal) vs retryable (infrastructure) dispatch spend, summed
  by cause-class …" — sitting 200 lines below the module preamble at `:1013-1024` that was corrected
  to "the strongest *proxy* … NOT a proof of it".
- **Why it matters:** the two comments in the same file disagree about what the figure asserts;
  the nearer one to the code is the wrong one.
- **Action:** align the inline comment with the preamble's wording. Consider renaming
  `_TERMINAL_WASTE_CAUSES` to `_TERMINAL_ERROR_CAUSES` in the same pass.
- **Done when:** no comment in `analyze-logs.py` describes `error` rows as genuinely wasted without
  the proxy qualification.
- **Effort:** S
- **Risk if fixed:** a constant rename touches `_TERMINAL_WASTE_CAUSES`'s two use sites only
  (`:1242` and the module docstring); no test references the name.

## G10 — Correct the run report's CI head reference

- **Kind:** report-defect
- **Severity:** low
- **Topic:** plan-lane-contract
- **Where:** `doc/plans/code-intelligence-substrate/070-dispatch-spend-on-dispatches-that-produced-nothing/report-01.md:64`
- **Evidence:** "On head `dc8e352` the required `verify / conclusion` check concluded **success**".
  The PR's final head was `f45bae2` — CodeRabbit re-reviewed `f45bae2` at 16:24Z and
  `pull_request_read get_status` for PR #1180 returns `sha: f45bae2e751a111bc0e27b84347527ce56be93ef`
  with overall state `success`. The report's own Contract check says the finalized report was
  "pushed as the last pre-merge commit", i.e. after `dc8e352`.
- **Why it matters:** the merge gate's condition is "required check green **on head**"; a report
  that evidences an earlier head does not evidence the condition it claims to have met. Here the
  final head was in fact green, so the outcome was right and the record is wrong.
- **Action:** in a future lane run, capture the CI verdict after the report-finalization commit, or
  state explicitly which head each check verdict belongs to.
- **Done when:** the lane's Step-8 evidence names the same SHA as the PR's final head.
- **Effort:** S
- **Risk if fixed:** none — a record correction and a lane-contract habit, not a code change.

## G11 — Reconcile `plan.md`'s D2 binary with the shipped three-state contract

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `doc/plans/code-intelligence-substrate/070-dispatch-spend-on-dispatches-that-produced-nothing/plan.md:80-94`
  (D2: "The choice is binary and both arms are acceptable"; "*Done when:* the columns either carry
  real values or are gone")
- **Evidence:** the shipped contract is neither arm: an omitted flag writes the literal `unmeasured`
  (`manage-metrics.py:3185-3188`) and readers implement a four-way read
  (`analyze-logs.py:1042-1070`). The run acknowledged CodeRabbit's CR-6 on exactly this point and
  declined to edit the plan; the correction lives only in `report-01.md:33-35`.
- **Why it matters:** a later plan re-deriving the contract from `plan.md` — the normal way these
  plans are read — would conclude the columns must be populated or dropped and could remove a
  working representation.
- **Action:** add a one-line pointer in `plan.md`'s D2 (or in this directory's records) noting that
  the deliverable was settled by the pre-existing `unmeasured` third state, with the report as the
  authority. Do not rewrite the historical intent.
- **Done when:** a reader of `plan.md` D2 is directed to the settled three-state contract without
  having to open the report.
- **Effort:** S
- **Risk if fixed:** editing a landed plan's text is itself a lane-contract question — prefer an
  additive note over a rewrite.

## G12 — Run D3's finding-yield sweep and D4's class shares where the corpus exists

- **Kind:** omission
- **Severity:** medium
- **Topic:** measurement/metrics
- **Where:** no code exists yet; the consumer surface is
  `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/analyze-logs.py:1030-1255`
  and the archived-record corpus under the machine-local `.plan/local/archived-plans/`
- **Evidence:** `report-01.md:126` records both as blocked; a search across `doc/plans/` for
  `error_total_tokens` / `retryable_total_tokens` returns only this plan's report and
  `truthful-signals/420-…/report-01.md`, which merely classified the fields as safe consumers of a
  reader fix — no plan has measured them since.
- **Why it matters:** the plan's founding question — how much dispatch spend buys nothing — is still
  unanswered. D1 made the population identifiable and D5 made the figure publishable; nobody has
  read it against a real corpus, so the lever remains unsized.
- **Action:** on a machine carrying the archived-record corpus, derive the terminal-state vocabulary
  from `DISPATCH_TERMINATION_CAUSES` (not from observed names), correlate each `error` row against
  finding-yield so `returned_with_findings` rows are excluded by construction, and report count +
  token cost + population size. Compute a share only against a denominator the sibling
  coverage-ratio plan has settled. Fix G1/G3 first, or the retryable half will measure as zero and
  the terminal half will silently omit unmeasured rows.
- **Done when:** a report states the non-productive dispatch count, its token cost, and the
  population size it was measured over, with the unmeasured-row count disclosed alongside.
- **Effort:** L
- **Risk if fixed:** a share computed against an unsettled denominator would reproduce the very
  sample-is-not-a-population error this plan exists to correct — the halt is preferable to a
  premature number.
