# Gaps — 430-a-timeout-is-not-a-red-test-and-a-kill-is-not-a-timeout

**Source:** verification.md (same directory)   **Open items:** 6

The four deliverables landed and the two highest-risk guards were mutation-confirmed to
bite. Everything below is residue: one stale comment in a file the plan itself edited, one
vocabulary the plan added but did not carry into the wire-translation layer (plus the
totality test that cannot see the omission), two mis-stated counts in the run report, and
two low-severity documentation shortfalls.

## G1 — Delete the stale pre-fix rule from the build-status stamping comment

- **Kind:** stale-statement
- **Severity:** medium
- **Where:** `test/plan-marshall/tools-script-executor/test_executor_runtime.py:604-606` — the module-level comment block above `test_build_boundary_stamps_derived_status`
- **What is wrong:** The comment states the derivation as *"(3) exit 0 => the wrapper's stdout TOON `status` when it is one the WRAPPER is entitled to claim (the timeout fix: the wrapper exits 0 on timeout, the TOON carries the truth; **a stdout `killed` claim at exit 0 stamps `error`, since `killed` is derived-only**)"*. That is the pre-fix rule. This plan reversed it: the parametrisation 130 lines below in the same file now asserts `('status: killed\n', 0, 'killed')`, `_ledger_core.py:62` makes `killed` wrapper-claimable, `_ledger_core.py:74` reduces `DERIVED_ONLY_BUILD_STATUSES` to `{'unknown'}`, and `execute-script.py.template:444-454` documents the opposite. The commit changed the parametrisation and its inline comment but left the header comment untouched (`git show d4ae2e81 -- test/plan-marshall/tools-script-executor/test_executor_runtime.py` shows the header block in neither the `+` nor the `-` set).
- **Why it matters:** It is the only surviving statement in the tree that says a wrapper-claimed `killed` stamps `error` and that `killed` is derived-only — the exact claim the plan's F6/F8/F9 sweep was run to eliminate. A reader who trusts the comment over the assertions 130 lines down will conclude the shipped behaviour is a bug and "fix" it back.
- **Fix:** In that comment, replace clause (3)'s parenthetical so it reads that a stdout `killed` claim at exit 0 is **believed** (it is the wrapper's first-hand observation of the child it reaped, exactly like its `timeout` claim), and that only `unknown` is derived-only. Add clause (5) or extend (4) to note that a stdout `indeterminate` claim at exit 0 stamps `unknown`, matching the case already parametrised at line 737.
- **Done when:** No statement in `test_executor_runtime.py` says a stdout `killed` claim stamps `error` or that `killed` is derived-only, and `grep -rn "derived-only" test/ marketplace/ | grep -i killed` returns no line asserting that `killed` is derived-only.
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

## G4 — Correct the two test-count figures in report-01.md

- **Kind:** stale-statement
- **Severity:** low
- **Where:** `doc/plans/truthful-signals/430-a-timeout-is-not-a-red-test-and-a-kill-is-not-a-timeout/report-01.md` — § D1 gate #7 row and § D3 opening paragraph
- **What is wrong:** Two counts are wrong against the tree the report describes. (a) *"`test_non_finish_discrimination.py` (44 cases)"* — the file at HEAD is byte-identical to the version landed in `d4ae2e81` and collects **50** cases (`pytest … -q` → `50 passed`; 35 test functions, 7 `parametrize` decorators). (b) *"12 cases in `test_pre_commit_verify_freshness.py`"* — the landed diff adds 7 test functions, one carrying a 5-way `parametrize`, i.e. **11** cases.
- **Why it matters:** The report is the plan's durable evidence record and this epic's whole subject is figures that are asserted rather than re-derived. Both numbers are cheap to re-derive and both are wrong, which undercuts the report's credibility on the figures that cannot be re-derived (the D2 measurements, the suite totals).
- **Fix:** Replace "44 cases" with the count `pytest --collect-only` reports for that file at the landed commit (50), and "12 cases" with 11, in both places § D3 and § D1 state them. State how each was derived.
- **Done when:** Every test-count figure in report-01.md matches `pytest --collect-only` against `d4ae2e81`.
- **Module/topic:** `doc/plans/truthful-signals` — run report.

## G5 — Stop reporting a genuinely failing build as `undecidable` at classify-outcome

- **Kind:** bug
- **Severity:** low
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-change-ledger/scripts/manage-change-ledger.py:219-235` — `cmd_classify_outcome`
- **What is wrong:** The verdict chain tests the matched ledger row for `killed`, then `timeout`, then `success`, and sends everything else to `undecidable` with the message *"no decisive signal — job completed but no conclusive ledger row"*. A row carrying `status: error` — a build that ran and reported failures, the most decisive signal in the vocabulary — therefore lands in the bucket reserved for the unresolvable case, alongside `unknown`. The docstring at `:207-210` enumerates the `undecidable` route as *"anything else, INCLUDING a matching row carrying the derived-only `status: unknown`"* and never mentions `error`. report-01.md's D0 table certifies this gate as *"yes (already correct)"* and the D1 table records it as *"unchanged"*, so the direction was never examined.
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
