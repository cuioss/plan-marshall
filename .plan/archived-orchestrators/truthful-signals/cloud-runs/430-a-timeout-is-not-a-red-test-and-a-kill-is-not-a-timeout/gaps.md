# Gaps — 430-a-timeout-is-not-a-red-test-and-a-kill-is-not-a-timeout

**Source:** verification.md (same directory)   **Open items:** 9

The four deliverables landed. Everything below is residue: one stale comment in a file the
plan itself edited, one vocabulary the plan added but did not carry into the wire-translation
layer (plus the totality test that cannot see the omission), one consuming gate the D0
derivation missed (plus the count that gate silently drops), two mis-stated counts in the run
report, and two low-severity documentation shortfalls.

⚠ **G7 was found by the adversarial review, not by the original verification.** The plan named
"every consuming gate is identified" as its highest-risk asserted-completeness claim; the
original verification checked all eleven rows of the published set and did not re-derive the
set itself. G7 is what re-deriving it found.

## G1 — Delete the stale pre-fix rule from the build-status stamping comment

- **Kind:** stale-statement
- **Severity:** medium
- **Where:** `test/plan-marshall/tools-script-executor/test_executor_runtime.py:604-606` — the module-level comment block above `test_build_boundary_stamps_derived_status`
- **What is wrong:** The comment states the derivation as *"(3) exit 0 => the wrapper's stdout TOON `status` when it is one the WRAPPER is entitled to claim (the timeout fix: the wrapper exits 0 on timeout, the TOON carries the truth; **a stdout `killed` claim at exit 0 stamps `error`, since `killed` is derived-only**)"*. That is the pre-fix rule. This plan reversed it: the parametrisation 130 lines below in the same file now asserts `('status: killed\n', 0, 'killed')`, `_ledger_core.py:62` makes `killed` wrapper-claimable, `_ledger_core.py:74` reduces `DERIVED_ONLY_BUILD_STATUSES` to `{'unknown'}`, and `execute-script.py.template:444-454` documents the opposite. The commit changed the parametrisation and its inline comment but left the header comment untouched (`git show d4ae2e81 -- test/plan-marshall/tools-script-executor/test_executor_runtime.py` shows the header block in neither the `+` nor the `-` set).
- **Why it matters:** It is the only surviving statement in the tree that says a wrapper-claimed `killed` stamps `error` and that `killed` is derived-only — the exact claim the plan's F6/F8/F9 sweep was run to eliminate. A reader who trusts the comment over the assertions 130 lines down will conclude the shipped behaviour is a bug and "fix" it back.
- **Fix:** In that comment, replace clause (3)'s parenthetical so it reads that a stdout `killed` claim at exit 0 is **believed** (it is the wrapper's first-hand observation of the child it reaped, exactly like its `timeout` claim), and that only `unknown` is derived-only. Add clause (5) or extend (4) to note that a stdout `indeterminate` claim at exit 0 stamps `unknown`, matching the case already parametrised at line 737.
- **Done when:** `grep -n "derived-only" test/plan-marshall/tools-script-executor/test_executor_runtime.py` returns no line, and no statement in that file says a stdout `killed` claim stamps `error`. (Re-derived during adversarial review: `grep -rn --binary-files=without-match "derived-only" test/ marketplace/ | grep -i killed` returns exactly two lines — `test_executor_runtime.py:606`, which is this defect, and `ref-code-quality/standards/error-handling.md:435`, which states the CURRENT rule correctly and must not be changed. The sweep found no third instance anywhere in `test/` or `marketplace/`.)
- **Module/topic:** `tools-script-executor` — executor dispatch-boundary tests.

## G2 — Give `indeterminate` an explicit wire row, or refuse to translate it

- **Kind:** bug
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_server_protocol.py:150-156` — `_RESULT_STATUS_TO_WIRE`, consumed by `wire_status_from_result:557-572`, reached from `_marshalld_supervisor.run_job:305`
- **What is wrong:** The same commit that added `STATUS_INDETERMINATE` to `_build_result` (`_build_result.py:153`) left it out of the result→wire translation table. Executed against the real module: `wire_status_from_result('indeterminate')` returns `'indeterminate'` via the pass-through fallback, and `'indeterminate' in TERMINAL_STATUSES` is `False` (`TERMINAL_STATUSES` at `:136-139` holds only `success|failure|timeout|killed`). `run_job`'s new narrowing feeds `verdict.status` — an arbitrary string read off the job log by `read_log_verdict`, which parses any column-0 `status:` line — straight into that function, so a status outside the four produces a wire status the daemon never treats as terminal: `marshalld._execute:534` records it, `_is_terminalized:499` reads it as not terminal, `_wait:453` never resolves and returns a running payload, and the client's `_route_to_daemon:600-606` `while True` loop re-polls indefinitely. Before this plan that line was a hard-coded `status = 'failure'`, which is always terminal, so the plan introduced the path. The module's own comment at `:141-149` argues precisely this hazard for `killed` (*"a table that silently omits a status it must translate is one rename away from mapping a kill onto nothing"*) and then omits `indeterminate`. The path is latent today only because the re-entrancy guard (`_build_execute_factory.py:561`) plus `MARSHALLD_JOB_ENV` on the daemon child (`_marshalld_supervisor.py:257`) keep the in-job build in-process, where `indeterminate` is never produced — nothing in the code states or enforces that dependency.
- **Why it matters:** A daemon job whose log carries any column-0 `status:` value outside the four wire statuses terminalizes into a status no consumer recognises: the job never completes for the waiting client, the audit path buckets its fate as `FATE_UNKNOWN` (`_marshalld_audit.py:311`), and the build hangs instead of reporting anything. That is a non-finish that cannot even be classified — the failure mode this plan exists to remove, one layer down.
- **Fix:** Decide the mapping explicitly rather than by fallback. Either (a) add a wire status for the undetermined condition, register it in both `_RESULT_STATUS_TO_WIRE` and `TERMINAL_STATUSES`, and give `_marshalld_supervisor._terminal_payload` an arm for it; or (b) keep the wire vocabulary at four and make `run_job`'s narrowing map any result status without an explicit row onto `STATUS_FAILURE`'s honest peer — a terminal status — rather than passing an untranslatable string through. Whichever is chosen, `wire_status_from_result` must stop silently emitting a non-terminal value: make the pass-through raise, or return a documented terminal fallback. Update the three sites in the same module that still enumerate a four-value `_build_result` vocabulary — the table comment at `:141`, `wire_status_from_result`'s `Args` at `:566-567`, and `LogVerdict.status`'s docstring at `:678-681`.
- **Done when:** For every member of the `_build_result` status vocabulary, `wire_status_from_result(s) in TERMINAL_STATUSES` holds, and a test asserts that property by iterating the vocabulary rather than a hard-coded list (see G3).
- **Module/topic:** `script-shared/build` — daemon wire protocol.

## G3 — Make the vocabulary-totality test derive its population instead of hard-coding it

- **Kind:** vacuous-test
- **Severity:** medium
- **Where:** `test/plan-marshall/script-shared/test_non_finish_discrimination.py:477-517` — `TestVocabularyTranslationIsTotal`
- **What is wrong:** The class docstring says *"Every `_build_result` status has an explicit wire row"* and `test_every_status_translates_explicitly` asserts `result_status in protocol._RESULT_STATUS_TO_WIRE` — but the `parametrize` list is the literal `[('success','success'), ('error','failure'), ('timeout','timeout'), ('killed','killed')]`, and `test_translation_round_trips` iterates the same four literals. `indeterminate` — the status the same commit added — is absent from both, so the test asserting totality is precisely blind to the one omission that exists (G2). It is a completeness claim that samples rather than derives, which is the failure mode the plan's own D0 correction is about.
- **Why it matters:** The test reads as the guard that stops a status from being added without a wire row, and it cannot perform that job. It passed on the very commit that broke the property it names.
- **Fix:** Import the `_build_result` module in the test and derive the population from it — e.g. collect every module attribute matching `STATUS_*` (or an explicit exported tuple added to `_build_result` for the purpose) and assert membership in `_RESULT_STATUS_TO_WIRE` and terminality of the translated value for each. Keep the explicit expected-mapping table as a separate assertion so a wrong mapping still fails, but stop letting the table define the population.
- **Done when:** Adding a new `STATUS_*` constant to `_build_result.py` without a corresponding `_RESULT_STATUS_TO_WIRE` row makes `TestVocabularyTranslationIsTotal` fail, verified by mutation.
- **Module/topic:** `script-shared/build` — non-finish discrimination suite.

## G4 — Correct the `test_non_finish_discrimination.py` case count in report-01.md

- **Kind:** stale-statement
- **Severity:** low
- **Where:** `doc/plans/truthful-signals/430-a-timeout-is-not-a-red-test-and-a-kill-is-not-a-timeout/report-01.md:217` — § D3 opening paragraph
- **What is wrong:** The report states *"`test/plan-marshall/script-shared/test_non_finish_discrimination.py` (44 cases)"*. The file at HEAD is byte-identical to the version landed in `d4ae2e81` (`git show d4ae2e81:… | diff -` → identical) and collects **50** cases — re-derived twice during adversarial review: `pytest … --collect-only` → `50 tests collected`, and `pytest … -q` → `50 passed in 0.23s`. The file holds 35 test functions and 7 `parametrize` decorators.
- **Why it matters:** The report is the plan's durable evidence record and this epic's whole subject is figures that are asserted rather than re-derived. This number is cheap to re-derive and is wrong, which undercuts the report's credibility on the figures that cannot be re-derived (the D2 measurements, the suite totals).
- **Fix:** In `report-01.md:217`, replace "(44 cases)" with "(50 cases)" and name the derivation — `pytest test/plan-marshall/script-shared/test_non_finish_discrimination.py -o addopts="" --collect-only` at `d4ae2e81`.
- **Done when:** `report-01.md:217` states 50, and that figure equals the collected count `pytest --collect-only` reports for the file at `d4ae2e81`.
- **Module/topic:** `doc/plans/truthful-signals` — run report.

## G5 — Stop reporting a genuinely failing build as `undecidable` at classify-outcome

- **Kind:** bug
- **Severity:** low
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-change-ledger/scripts/manage-change-ledger.py:219-233` — `cmd_classify_outcome`'s verdict chain
- **What is wrong:** The verdict chain tests the matched ledger row for `killed` (`:219`, `:222`), then `timeout` (`:225`), then `success` (`:228`), and sends everything else to `undecidable` (`:231-233`) with the message *"no decisive signal — job completed but no conclusive ledger row"*. A row carrying `status: error` — a build that ran and reported failures, the most decisive signal in the vocabulary — therefore lands in the bucket reserved for the unresolvable case, alongside `unknown`. The docstring at `:208-210` enumerates the `undecidable` route as *"anything else, INCLUDING a matching row carrying the derived-only `status: unknown`"* and never mentions `error`. report-01.md's D0 table (`:67`) certifies this gate's discrimination as *"yes — but its killed-row branch was unreachable for an inner kill"* and its D1 table (`:126`) records it as *"unchanged"*, so the `error` direction was never examined on either pass.
- **Why it matters:** It is the inverse of the collapse this plan fixed — a determinate verdict folded into the indeterminate bucket — sitting in a gate the plan enumerated and certified. Severity is low because `plan-marshall/workflow/await-long-running.md:24` records that the daemon's first-class `killed` status **supersedes** this classifier, which *"remains only for any residual detached-build path that is not daemon-served"*.
- **Fix:** Add an `error` arm to the chain returning a distinct verdict (e.g. `failed`) with a message naming the reported failures, and extend the `undecidable` docstring and `manage-change-ledger/SKILL.md` § classify-outcome accordingly. If instead the verb is judged fully dead, retire it rather than leaving a certified-correct gate that mis-reports a red build.
- **Done when:** `classify-outcome` over a ledger whose latest matching row carries `status: error` returns a verdict distinguishable from the one it returns for `status: unknown`, with a test pinning both.
- **Module/topic:** `manage-change-ledger` — classify-outcome.

## G6 — Name `indeterminate` in the canonical three-conditions section

- **Kind:** doc-drift
- **Severity:** low
- **Where:** `marketplace/bundles/plan-marshall/skills/extension-api/standards/build-systems-common.md:128-140` — § "The three non-green conditions, and every gate that must keep them apart"
- **What is wrong:** The section is the durable artifact D0 produced and is explicitly framed as *"the list a change to the vocabulary must walk"*. Its condition table names `error`, `timeout`, `killed`, and then says *"An outcome that cannot be resolved to one of those is `unknown`"*. `unknown` is the ledger/dispatch-boundary name; the wrapper-side name for the same condition is `indeterminate` (`_build_result.py:153`, and `DirectCommandResult.status` is a five-value `Literal` at `_build_result.py:112`), and the two are deliberately distinct — `execute-script.py.template` refuses an `indeterminate` claim and derives `unknown` instead, a case pinned at `test_executor_runtime.py:737`. The section never mentions `indeterminate` at all, even though its own table of surfaces includes the wrapper TOON where that is the spelling.
- **Why it matters:** A reader following this page's instruction to walk the consumer set on a vocabulary change starts from four conditions and one spelling for the unresolvable case, and will miss the fifth — which is exactly how G2 arose.
- **Fix:** Add `indeterminate` to the condition table as the wrapper-surface name for the unresolvable outcome, state that the boundary's name for the same condition is `unknown` and why the boundary derives rather than accepts it, and cross-reference `build-execution.md` § Status values, which already documents all five.
- **Done when:** The section enumerates five statuses and states the `indeterminate`/`unknown` two-layer naming, and `build-execution.md`, `build-api-reference.md` and `build-systems-common.md` agree on the vocabulary size.
- **Module/topic:** `extension-api` — build-system standards.

## G7 — The published consumer set omits a twelfth reader of the ledger build status

- **Kind:** missing-implementation
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/extension-api/standards/build-systems-common.md:148-160` — the eleven-row consumer table (header at `:148`, rows `:150-160`); and `report-01.md:60-76` — the D0 table whose published population is *"11 consuming gates. 11 of 11 read a status field"*
- **What is wrong:** `plan-retrospective/scripts/analyze-logs.py` reads the `kind=build` ledger `status` and is in neither list. It imports the exact symbol the derivation named as its closed import set (`from _ledger_core import read_entries`, `:49`), filters on `entry.get('kind') != 'build'` (`:178`), and branches on the status with a hard-coded five-value vocabulary (`status_keys = ('success', 'error', 'timeout', 'killed', 'unknown')`, `:173`). Re-derived during adversarial review: `grep -rn "read_entries" --include=*.py marketplace/` returns four importers outside `_ledger_core.py` itself — `manage-change-ledger.py`, `_cmd_pre_commit_verify_freshness.py`, `build_server.py` (which reads `KIND_JOB`, not `kind=build`), and `analyze-logs.py`. The first two are rows #6 and #7 of the published table; the fourth is absent from it. So the population is **12**, not 11, on the derivation's own stated method.
- **Why it matters:** The plan's own claim-labels table flags *"Every consuming gate is identified"* as the asserted-**completeness** claim and the higher-risk half, and the standard's table is framed as *"the list a change to the vocabulary must walk"*. A reader who walks it on the next vocabulary change will edit eleven consumers and leave the twelfth — which is precisely how G8 below already stands unnoticed. The defect is not that this gate collapses a kill into a red build (it does not — it counts `killed` separately, by design), but that the enumeration D0 published as complete is not.
- **Fix:** Add a row to the consumer table in `build-systems-common.md` for `plan-retrospective analyze-logs` naming its surface (ledger `kind=build` `status`), and correct the population sentence in `report-01.md` § D0 from 11/11 to 12/12. In the same edit, state the derivation command the count came from so the next reader can re-run it rather than trust it.
- **Done when:** `build-systems-common.md`'s consumer table has one row per module that imports `_ledger_core.read_entries` and filters `kind == 'build'`, verified by re-running `grep -rn "read_entries" --include=*.py marketplace/` and matching the result set against the table row-for-row; and the population figure in `report-01.md` equals that row count.
- **Module/topic:** `extension-api` — build-system standards; `plan-retrospective` — log analysis.

## G8 — `analyze-logs` counts an undetermined build and then drops it from its own output

- **Kind:** bug
- **Severity:** low
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/analyze-logs.py:173-197` — the `build_time` block; contract documented at `plan-retrospective/references/log-analysis.md:22-28`
- **What is wrong:** `status_counts` is keyed on five statuses including `unknown` (`:173-174`), and every row whose status is missing or outside the vocabulary is folded into that key (`:183`). The returned dict then emits only four of them — `pass`, `error`, `timeout`, `killed` (`:193-196`) — and `unknown` is discarded. `build_count` still counts the row. So `pass + error + timeout + killed` need not equal `build_count`, and nothing in the block says why: a build whose outcome the boundary could not determine simply vanishes from the retrospective's build-status ratio. The documented TOON shape at `log-analysis.md:22-28` mirrors the same four keys, so the omission is contract, not oversight in one place.
- **Why it matters:** This epic's standing rule is that an unresolvable case is its own answer and is never folded into a neighbour. Dropping it entirely is the same defect one step further: the reader is shown four counts that look exhaustive, cannot reconcile them against `build_count`, and has no signal that any build ended undetermined. The gate that most needs to surface "no verdict was obtained" is the one that reports on how the plan's builds went.
- **Severity rationale:** `low` rather than `medium` because this is a retrospective metrics surface — it degrades no merge decision and gates no transition. It reports a wrong composition, not a wrong outcome.
- **Fix:** Add `unknown: status_counts['unknown']` to the returned dict in `analyze-logs.py`, and add the matching `unknown: N` line to the `build_time` block in `log-analysis.md` with a note that `pass + error + timeout + killed + unknown == build_count`.
- **Done when:** For any ledger, the five returned status counts sum to `build_count`, pinned by a test that feeds a `kind=build` row carrying `status: unknown` (and one carrying a status outside the vocabulary) and asserts the sum identity and a non-zero `unknown`.
- **Module/topic:** `plan-retrospective` — log analysis.

## G9 — Correct the `test_pre_commit_verify_freshness.py` case count in report-01.md

- **Kind:** stale-statement
- **Severity:** low
- **Where:** `doc/plans/truthful-signals/430-a-timeout-is-not-a-red-test-and-a-kill-is-not-a-timeout/report-01.md:127` (§ D1 gate #7 row) and `:218` (§ D3) — the same figure stated twice
- **What is wrong:** Both sites state *"12 cases in `test_pre_commit_verify_freshness.py`"*. Re-derived during adversarial review from the landed diff: `git show d4ae2e81 -- test/plan-marshall/manage-tasks/test_pre_commit_verify_freshness.py` adds **7** test functions, exactly one of which carries a `parametrize` decorator with **5** tuples (`test_stale_reason_names_the_observed_build_status`) — i.e. 6 + 5 = **11** collected cases, not 12. (The whole file collects 39 at HEAD, but that includes pre-existing cases and the ones `aeab5ab5` added later, so it is not the figure the report is claiming.)
- **Why it matters:** Same as G4 — a stated count that does not re-derive, in the durable record of a plan whose subject is signals that are asserted rather than checked. It is filed separately from G4 because it is a different figure at different sites and either can be corrected without the other.
- **Fix:** In `report-01.md:127` and `:218`, replace "12 cases" with "11 cases" and name the derivation — 7 added test functions, one carrying a 5-way `parametrize`, counted from `git show d4ae2e81 -- test/plan-marshall/manage-tasks/test_pre_commit_verify_freshness.py`.
- **Done when:** Both sites state 11, and that figure equals the number of cases the landed diff's added test functions collect.
- **Module/topic:** `doc/plans/truthful-signals` — run report.

## Refuted during adversarial review

**None.** Every gap G1–G6 was re-checked against the tree by an agent that did not write them, and
all six were upheld — including both `medium` findings, whose asserted mechanisms were confirmed at
the file and symbol they name rather than by re-reading the gap. Three had their supporting text
corrected without their substance changing (G1's Done-when, G4's split into G4 + G9, and G5's quote
and line reference); one supporting citation was challenged and survived:

- **G5** quoted report-01.md's D0 cell as *"yes (already correct)"*. That string does not appear in
  the report — the cell for gate #6 reads *"yes — but its killed-row branch was unreachable for an
  inner kill"* (`report-01.md:67`). The quote has been replaced with the actual cell text. The
  finding itself is unaffected: the `error` → `undecidable` direction is still not examined on
  either the D0 or the D1 pass, and `manage-change-ledger.py:231-233` still routes it there.
  Its docstring reference was also corrected from `:207-210` to `:208-210`.
- **G5**'s severity rationale was challenged and upheld. It cites `await-long-running.md:24`. That citation is exact — the line
  does say `classify-outcome` *"remains only for any residual detached-build path that is not
  daemon-served"*, and `grep -rn "classify-outcome"` finds no remaining call site in any script,
  only the two documentation references and `execution-context.md:38`. `low` is upheld.

The full record of what was and was not re-checked is in verification.md § Adversarial review.
