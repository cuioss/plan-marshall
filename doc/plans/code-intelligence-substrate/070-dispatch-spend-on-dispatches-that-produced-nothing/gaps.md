# Gaps — 070-dispatch-spend-on-dispatches-that-produced-nothing

The plan's substantive work landed: the taxonomy has its `returned_with_findings` member, the
finalize classification routes a loop-back to it, the audit rule reads every dispatching phase, the
context-load columns were correctly settled without a second writer, D3 halted honestly, and the
terminal-vs-retryable split is emitted, rendered and non-vacuously tested. What remains falls into
five groups: the two *published* token figures sum a column whose "no measurement" case is a
fabricated `0` (G1, G2, G6) — the exact asymmetry D2 exists to prevent, one column over, and
demonstrated end-to-end from the writer to the reader rather than inferred; the cause-class
partition those figures are computed over is hand-written and pinned to the taxonomy by nothing, so
a future member falls silently out of both (G13); the finalize dispatcher's 5c gate and the cause
table it classifies into describe different populations on the phase the plan was written about
(G3); the routing prose that D1 rewrote is guarded by no test, so it can silently regress (G5); and
the CR-7 proxy-vs-proof correction was applied to the code and the report but not to the
analyst-facing rule document that the retrospective agent actually follows (G4), nor to three
lower-stakes comment surfaces (G7-G9). Two residue items from the run (D3's finding-yield sweep,
D4's class shares) are still open (G12), and two low-severity record defects round out the list
(G10, G11).

**Grouping note.** G4, G7, G8 and G9 are one sweep — the completion of the CR-7 proxy-vs-proof
relabelling across the surfaces the run missed — and are all topiced `measurement/metrics` (G7
stays `tests` because its surface is a test file) so a fix plan picks them up together rather than
in three unrelated passes. G1 is the root cause of G2 and interacts with G3 and G12; fix G1 first.

## G1 — Represent an unmeasured `total_tokens` instead of writing a fabricated `0`

- **Kind:** bug
- **Severity:** high
- **Topic:** measurement/metrics
- **Where:** the root cause is
  `marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/manage-metrics.py:3157`
  (`cmd_record_dispatch_boundary`), reachable from every call site because `--total-tokens` is
  optional (`:3832-3837`, `default=None`). The **four** invocation sites across **three**
  documents:
  `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/execution.md:212` (instruction
  at `:219`), `…/workflow/planning-outline.md:463` (instruction at `:468`), and
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md:1109` — which states **no**
  `0`-fallback, only "Forward the `<usage>` totals captured by 5b", so the writer's default is what
  governs the finalize ledger. (`execution.md:257` is a fourth site that passes `--total-tokens 0`
  **deliberately** for a synthesised `clean_exit_queue_empty` row; it reaches neither sum and must
  not be "fixed".) Consumers:
  `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/analyze-logs.py:1241-1246`,
  which parses the column as a bare `int(parts[2])` (`:1143`) with no unmeasured state.
- **Evidence — first-party, end-to-end (writer → disk → reader, no fixtures).** Three rows written
  into a real `6-finalize` ledger: an `error` with `--total-tokens` omitted, an `error` carrying
  `7000`, a `blocked_session_restart` with the flag omitted. Bytes on disk:

  ```text
  2026-08-18T20:47:19Z,error,0,0,0,unmeasured,unmeasured,unmeasured,unmeasured
  2026-08-18T20:47:20Z,error,7000,3,20000,unmeasured,unmeasured,unmeasured,unmeasured
  2026-08-18T20:47:20Z,blocked_session_restart,0,0,0,unmeasured,unmeasured,unmeasured,unmeasured
  ```

  `_parse_dispatch_boundary_file` then returns `error_total_tokens = 7000` and
  `retryable_total_tokens = 0`. Row 1 is the defect at its sharpest: **one row** correctly says
  `unmeasured` on the four columns D2 protected and fabricates a `0` on the one column D4/D5
  publish. The writer's own docstring still justifies the default — "the legacy five columns …
  keep their `0` default, because nothing downstream distinguishes an absent from a zero on those"
  (`manage-metrics.py:3126-3128`) — which this plan made untrue. The shipped suite already writes
  such a row without noticing: `test_returned_with_findings_subprocess_accepted_by_argparse`
  (`test/plan-marshall/manage-metrics/test_manage_metrics_record_dispatch_boundary.py:572`)
  invokes the writer with no token flags at all.
- **Why it matters:** a dispatch that terminated without emitting `<usage>` — the systematic case
  for `harness_cancellation` and `blocked_session_restart`, and a real case for `error` — adds `0`
  to a figure the compile-report presents as measured spend. `error_total_tokens` therefore
  silently **mixes** measured and fabricated contributions, and `retryable_total_tokens` is worse:
  its two causes are precisely the terminations that produce no `<usage>`, so it reads a
  fabricated `0` systematically rather than occasionally. A reader cannot tell "no spend" from
  "never measured" — the precise failure D2 was written to prevent for columns 6-9, one column
  over.
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
  output. Additionally, `phase-6-finalize/SKILL.md:1109` states what to pass when 5b captured no
  `<usage>`, instead of leaving it to the writer's default.
- **Effort:** M
- **Risk if fixed:** every existing ledger row is a nine-column row whose third cell is an int, so
  the reader must keep accepting ints; a strict parse would drop historical rows. The
  `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py` ledger reader parses the
  same file independently and **must** be updated in lock-step — and its failure mode is worse
  than a parse error: `total_tokens` is in `_BC_LEDGER_FIELDS` (`:7188`) but **not** in
  `_BC_LEDGER_UNMEASURABLE_FIELDS` (`:7224`), so the token would take the
  `totals[ledger_field] += _to_int(cell)` branch (`:7357-7360`), and `_to_int` returns `0` on a
  non-numeric string (`:955-959`) while `measured.add(...)` still fires. The billing-composition
  reconciliation would then report the row as a **measured zero** — silently, with no unrecognised
  signal. That tree is not crawled by the architecture inventory, so a content sweep will not find
  it; `data-format.md:944` names it as a lock-step surface for exactly this reason.

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
  `error_total_tokens (terminal-error)` (`compile-report.py:357`). Demonstrated in G1's probe: over
  a two-`error`-row ledger where one row measured nothing, the reader publishes `7000` — a figure
  indistinguishable from one measured over both rows.
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

## G3 — Reconcile the finalize 5c gate with the cause table it classifies into

- **Kind:** bug
- **Severity:** medium
- **Topic:** dispatch/finalize
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md:1093` (the 5c gate),
  `:1102` (the `blocked_session_restart` definition), `:1110` (the five-value invocation)
- **Evidence:** the gate reads "fire only when the step ran as a Task agent and did **NOT** time
  out" (`:1093`), while the cause it is supposed to classify reads "cut short by a session restart,
  harness cancellation, or the per-agent timeout budget firing (timeout block at item 5 above)"
  (`:1102`) — three sub-cases, one of which the gate structurally excludes. A timed-out finalize
  step therefore writes **no boundary row at all**: 5b and 5c are both skipped, and the item-5
  timeout path only logs ERROR and marks the step `failed` (`:1055-1057`).
  `harness_cancellation` is additionally not in the invocation's value list (`:1110`).
  ⚠ The remaining two sub-cases are **not** blocked: a session restart or a harness cancellation
  that still returns control to the dispatcher passes the gate, and the writer imposes no
  phase/cause coupling — a `blocked_session_restart` row was written onto a real `6-finalize`
  ledger and accepted (`choices` is the whole 12-member enum, re-checked in-function at
  `manage-metrics.py:3147-3155`). So the finalize retryable class is **narrowed and
  self-contradictory**, not structurally impossible.
- **Why it matters:** D4 shipped `retryable_total_tokens` so infrastructure spend stays separable
  from deterministic failure. On the finalize phase — the phase this plan was written about and
  whose spend it calls the majority — the dispatcher's own contract disagrees with itself about
  which terminations that figure covers, and the largest sub-case it names (timeout) is silently
  absent from the ledger entirely, so the phase also under-counts its dispatched **population**,
  not just its spend. Combined with G1 the column reads `0` in practice, and a reader concludes
  "no infrastructure waste in finalize" from a figure that measured almost none of it.
- **Action:** decide and document the intended behaviour: either the timeout path at item 5 records
  a `blocked_session_restart` boundary row before continuing (removing the timed-out carve-out for
  5c specifically, which the report's D4 claim assumes), or the `blocked_session_restart` row is
  redefined to the case 5c can actually observe and the timeout wording at `:1102` removed. Either
  way, reconcile the invocation's value list at `:1110` with the cause table at `:1099-1103`.
- **Done when:** every cause named in `phase-6-finalize/SKILL.md`'s 5c cause table is writable
  under the 5c gate as that gate is worded, no sub-case in a cause's definition names a condition
  the gate excludes, and the brace-form value list at `:1110` contains exactly the causes the table
  at `:1099-1103` defines. If the timeout arm is chosen, a timed-out finalize step produces a
  boundary row; if the redefinition arm is chosen, `:1102` no longer mentions the timeout budget.
- **Effort:** M
- **Risk if fixed:** recording a row on the timeout path adds a `record-dispatch-boundary` call in
  an error path where `<usage>` is unavailable — coordinate with G1 so it does not write a
  fabricated `0`.

## G4 — Propagate the CR-7 proxy-vs-proof correction into the logging-gap rule document

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** measurement/metrics — re-topiced from `documentation-surface`: the defect is a false
  claim about what a published *measurement* asserts, and it belongs in the same fix pass as G7,
  G8 and G9 (see the CR-7 completion-sweep note at the top of this file), not with unrelated doc
  churn
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
- **Done when:** `logging-gap-analysis.md:160-168` contains none of "genuinely non-productive"
  (`:164`), "returned nothing" (`:164`), "genuine terminal waste" (`:166`) or "bought zero
  detection" (`:168`) as assertions about `error` rows, the bullet's own heading at `:160`
  ("**Genuinely-wasted vs retryable dispatch spend**") is restated in the proxy framing, and the
  wording is consistent with `analyze-logs.py:1013-1024`.
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
- **Evidence:** re-derived at HEAD: `grep -rln "returned_with_findings" test/` returns five `.py`
  files (`manage-metrics/test_manage_metrics.py`,
  `manage-metrics/test_manage_metrics_record_dispatch_boundary.py`,
  `plan-retrospective/test_compile_report.py`, `…/test_compile_report_behavior.py`,
  `…/test_dispatch_waste_and_finalize_scope.py`), none of which reads
  `phase-6-finalize/SKILL.md`; `grep -rn "termination.cause\|record-dispatch-boundary"
  test/plan-marshall/phase-6-finalize/*.py` returns nothing across all 28 test files there —
  including `test_loop_back_outcome.py`, which pins the `loop_back` *outcome* end-to-end but says
  nothing about the 5c termination-cause classification it feeds. The one full-enum documentation
  guard
  (`_parse_termination_cause_sites`, `test_manage_metrics.py:3837`) parses manage-metrics' own
  SKILL.md by construction, and the plugin-doctor `canonical-enum-choices-drift` rule scans
  `## Canonical invocations` blocks — line 1110 sits under `## Operation: finalize` and is a
  deliberate subset the rule would reject rather than guard.
- **Why it matters:** D1's *Done when* is "a loop-back dispatch is stamped with the new member", and
  the plan's Verification section warns explicitly that "a unit test over the enum alone does not
  show the path was rerouted". The only shipped assertion is that the writer accepts the string on
  the finalize file. If the 5c table is edited back to route `loop_back → error`, the whole
  deliverable silently reverts with every test still green.
- **Action:** add a document-contract test. The shape is already shipped **in the target directory
  itself**: `test/plan-marshall/phase-6-finalize/test_loop_back_outcome.py` validates markdown
  contracts in this same `phase-6-finalize/SKILL.md` (its invariant 4 asserts the Resumability
  section's table rows), and `test_step_termination_contract.py` in the same directory pairs every
  prose sweep with an executable mutation guard — so the new test has a local precedent to follow
  rather than needing a new pattern. Assert
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
  (`render_dispatch_boundaries_body`); the behaviour is pinned by the assertion at
  `test/plan-marshall/plan-retrospective/test_compile_report.py:876`, under the comment at `:875`
- **Evidence:** `wasted = phase_data.get('error_total_tokens', 0)` (`:373`) /
  `retryable = phase_data.get('retryable_total_tokens', 0)` (`:374`) /
  `returned_with_findings = phase_data.get('returned_with_findings_count', 0)` (`:375`), and the
  test's own comment at `:875`: "This fixture carries none of the new figures, so they default to
  0", asserting `| 5-execute | 0 | 0 | 0 | 0 | 0 | 3 |` at `:876`. The two pre-070 counters
  (`unknown_count`, `clean_exit_queue_empty_count`, `:371-372`) share the same `.get(…, 0)`
  default; they are out of this plan's scope but sit in the same loop and should move with it.
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
  deferred, matching `analyze-logs.py:1013-1024`. Part of the CR-7 completion sweep with G4, G8
  and G9 — do them in one pass.
- **Done when:** the module docstring contains no assertion that `error` rows produced nothing.
- **Effort:** S
- **Risk if fixed:** none — docstring only.

## G8 — Rename the renderer's `wasted` local and the stale "(wasted)" column comments

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** measurement/metrics — re-topiced from `documentation-surface` so it groups with G4,
  G7 and G9 as one CR-7 completion sweep
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/compile-report.py:373`
  (`wasted = phase_data.get('error_total_tokens', 0)`);
  `test/plan-marshall/plan-retrospective/test_compile_report.py:873` and `:943` ("Columns: phase |
  rows | error_total_tokens (wasted) | …") and `:947` ("the genuinely-wasted vs retryable split");
  `test/plan-marshall/plan-retrospective/test_compile_report_behavior.py:140` ("the
  genuinely-wasted vs retryable spend split")
- **Evidence:** the rendered header is `error_total_tokens (terminal-error)`
  (`compile-report.py:357`), but the local variable and **four** comment lines across two test
  files still call the same quantity "wasted" / "genuinely-wasted".
- **Why it matters:** the CR-7 disposition claims the label was corrected; five surfaces still
  carry the old one, so the next reader sees a contradiction between the code and its own comments.
- **Action:** rename the local to `terminal_error` and update the four comment lines.
- **Done when:** across `compile-report.py`, `test_compile_report.py` and
  `test_compile_report_behavior.py`, no occurrence of "wasted" or "genuinely-wasted" refers to
  `error_total_tokens`.
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
- **Evidence:** the report reads "On head `dc8e352` the required `verify / conclusion` check
  concluded **success**; `verify / verify`, `verify / gate`, `review / review`, `dependency-review`,
  and `generate-check` all success". `pull_request_read get_status` on PR #1180 returns
  `sha: f45bae2e751a111bc0e27b84347527ce56be93ef` — the report-finalization commit, which the
  report's own Contract check says was "pushed as the last pre-merge commit", i.e. after
  `dc8e352`. Re-derived here with `get_check_runs`, which is the surface that actually carries the
  verdict (`get_status` returns `total_count: 1`, only CodeRabbit's "Review rate limited" commit
  status): on `f45bae2` there are **7** check runs — `verify / conclusion` success (completed
  16:36:31Z), `verify / verify`, `verify / gate`, `dependency-review / dependency-review` and
  `generate-check` success, `Sourcery review` and `auto-merge` skipped. **`review / review` is not
  among them**, so that clause of the report is wrong independently of the SHA.
- **Why it matters:** the merge gate's condition is "required check green **on head**"; a report
  that evidences an earlier head does not evidence the condition it claims to have met. Here the
  final head was in fact green, so the outcome was right and only the record is wrong.
- **Action:** correct the sentence at `report-01.md:64` to name `f45bae2` as the head the merge
  gate acted on, and to list the checks that actually ran on it (dropping `review / review`).
  Separately, state in the lane's Step-8 evidence which head each check verdict belongs to.
- **Done when:** `report-01.md:64` names `f45bae2` and its check list matches
  `get_check_runs` for that SHA.
- **Effort:** S
- **Risk if fixed:** none — a record correction. Note that editing a landed run report is the same
  lane-contract question G11 raises; prefer an inline correction note over a silent rewrite.

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

## G13 — Anchor the cause-class partition to `DISPATCH_TERMINATION_CAUSES`

- **Kind:** bug
- **Severity:** medium
- **Topic:** measurement/metrics
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/analyze-logs.py:1025-1027`
  (`_TERMINAL_WASTE_CAUSES`, `_RETRYABLE_CAUSES`, `_RETURNED_WITH_FINDINGS_CAUSE`), against
  `marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/manage-metrics.py:79-103`
  (`DISPATCH_TERMINATION_CAUSES`); the test belongs in
  `test/plan-marshall/plan-retrospective/test_dispatch_waste_and_finalize_scope.py`
- **Evidence:** the three constants are hand-written string literals in a **different bundle** from
  the enum they partition. A repository-wide search for all three names across `marketplace/`,
  `test/` and `.claude/` returns only their definitions and their three use sites inside
  `analyze-logs.py` (`:1236`, `:1242`, `:1245`) — no test, and no structural relationship to the
  enum. By contrast every *documentation* mirror of that enum is guarded by a structural-equality
  test with an executable negative control (`test_manage_metrics.py:3870`/`:3905`,
  `:4016`/`:4027`, `:4048`/`:4053`). The partition that decides what two **published** figures are
  computed over is guarded by nothing. Of the 12 enum members, four are classified or counted
  (`error`, `blocked_session_restart`, `harness_cancellation`, `returned_with_findings`), one more
  is counted separately (`clean_exit_queue_empty`), and seven are silently unclassified.
- **Why it matters:** the plan's D3 says in terms: "⛔ **Derive the terminal-state vocabulary from
  the schema**, not from the two names that happened to be observed — they are a sample, not the
  enum." `_RETRYABLE_CAUSES` is literally those two names. A member added to
  `DISPATCH_TERMINATION_CAUSES` later — the taxonomy has been widened twice already, most recently
  by this very plan — lands in neither published figure and in no test, so its spend disappears
  from both without any signal. This is a guard that cannot fire rather than one that fires wrongly,
  which is why grep and the green suite both look clean.
- **Action:** add a test asserting that every member of `DISPATCH_TERMINATION_CAUSES` appears in
  exactly one of a declared set of classes — terminal, retryable, productive, and an explicit
  `_BENIGN_CAUSES` (or `_UNCLASSIFIED_CAUSES`) tuple naming the seven that belong in neither
  spend figure — so the union equals the enum and the intersections are empty. Import the enum
  rather than re-typing it (`test_dispatch_waste_and_finalize_scope.py` already loads scripts via
  `conftest.load_script_module`). Pair it with a negative control that appends a fictitious member
  and requires the assertion to raise.
- **Done when:** appending a member to `DISPATCH_TERMINATION_CAUSES` without adding it to one of
  the `analyze-logs.py` cause-class tuples turns a named test red.
- **Effort:** S
- **Risk if fixed:** the test couples two bundles, so `plan-retrospective`'s test suite gains an
  import of `manage-metrics`' script; that direction already exists in this repository's contract
  tests (`test_logging_gap_analysis_termination_cause_set_matches_the_enum` reads a
  `plan-retrospective` document from a `manage-metrics` test), so the reverse coupling is
  precedented rather than novel.
