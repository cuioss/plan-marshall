# Landing Analysis: PLAN-LB-149 — a build row is credited only for the tree it built, no writer's row is refused for a fact it never claimed, and a lone Gradle task row is a scoped row

epic: live-blockers
workstream: WS-02
pr: #1977 (squash commit `f3c9267382b1c0054216ebdf2ada64f7250a3131`, one parent `d1d3ed2b229c8c56dec2689dab31acc2476b1a08`)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying claims against ground truth (actual code, artifacts, PR state) — a pasted claim is a lead, never a fact.

## Deliverable Fidelity vs Spec

One message from the runbook lane (sender `rb-lb-149-build-row-writers-and-freshness-truth`, revision 0, `merge_state=merged`, deliverables 5/5, `cleanup_owed=true`, self-review `clear` after a fourth round the operator authorised). It is `complete: false` on `total_tokens` alone (out of scope under the operator's focus rule). The row was `running` and carried no `pr` or plan id; both are stamped now. The squash commit has one parent, read with `git rev-parse f3c926738^` before the leaf prompt named it, and touches 21 paths (read with `git diff --name-only`): 11 under `marketplace/bundles/plan-marshall/skills/`, 10 under `test/`.

Review facts agree with the provider: `review-gate --pr-number 1977` reads 0 unresolved threads and 8 body findings (`inline-1` to `inline-7` and `additional-1`, all CodeRabbit). `review_body_findings_handled=8` was re-read from the progress file: eight `finding:` lines carry the same eight ids (`progress.md:42-49`; the lane wrote an earlier set of the same eight at `:32-39`); seven were fixed in `32937f4da` and one (`additional-1`, a closing-underscore guard on the `_D2_` regex) was declined with a stated reason that the leaf judged sound. The bare `review-gate` re-run reads `handled: 0` and `merge_allowed: false` only because it holds no dispositions input. `sonar_open_new_issues=n/a`. The PR reads merged through the merge queue, one parent.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — a writer that recorded nothing omits the two tree keys | shipped-as-specified; **F1 CLOSED** | `build_record` writes the pair only when the caller passed a value (`NOT_GIVEN`, `_ledger_core.py:88-98,165-166,273-294`, leaf); the CLI and the seam row pass neither (`manage-change-ledger.py:149-157`, `_build_execute_factory.py:563-574`, leaf); the gate reads presence (`_cmd_pre_commit_verify_freshness.py:369-390`, leaf; the earlier shape re-read in the PLAN-LB-146 analysis); a key-less row is admitted on the completion hash, exactly the reading before PR #1971 |
| D2 — the recorder hashes the tree the build ran in | shipped; **F2 CLOSED in the source, not yet in effect** (stale executors keep the old route until regeneration); two residual routes of the same class (L1-2, L1-3) | `--audit-plan-id` no longer selects the tree (`template:2421-2422`, `_ledger_tree_root` `:1105-1115`, leaf); the template line `_wrapper_plan_id = extract_plan_id(script_args)` at L2421 re-read here, and the row's attribution plan id stays `extract_plan_id(...) or audit_plan_id` at L2411 (re-read) |
| D3 — the pre-build hash is bounded, a failed git call is no hash | shipped-as-specified | `worktree_sha.py:61,79-81,104-110` (leaf); every caller of `compute_worktree_sha` handles `None` as undecidable, an explicit null or an `unknown` (leaf list below) |
| D4 — a lone `:module:task` Gradle row is a scoped row | shipped-as-specified; one new widening (L1-1) | `_gradle_subproject_scope` and `parse_row_scope` (`_freshness_crosscheck.py:735-760,892-897`, re-read) |
| D5 — documents and pins | shipped; minor drift (L3-1 to L3-4) | the doc-contract controls end in `assert not _pin_states(pin, planted)` (leaf, `test_build_tree_naming_doc_contract.py`) |

Spec sub-points: the lane settled every hypothesis: the daemon-routed child reads the same argv tail (confirmed; the leaf adds that its recorder does not read `--resolved-project-dir`, L1-4); the consumer-project self-heal hypothesis is not needed by the fix. The lane's rollout statement holds (an executor from the 877 template passes explicit values, an executor from before #1971 writes key-less rows read as before; leaf, C9).

## Three-Layer Analysis

One read-only leaf (`execution-context-level-5`) read the landing; the orchestrator re-read the points marked. By reading: no build, no test run, no write.

- **Verdict:** **no blocker and no major.** Layer 1: 5 minor, 1 info (one new and one leftover fail-open direction, both off-canonical); layer 2: 4 minor; layer 3: 4 minor. The layer-3 defects are reported to the operator in the same turn; none is fixed inline.
- **Leaf rule breaks:** plain `grep` through Bash (no Grep tool); one `git show --output=` that may have written a scratch copy under the session scratchpad (nothing in the repository); the dispatcher's log calls skipped as instructed.

Re-read: `_freshness_crosscheck.py:735-765,880-905`; the template's plan-id lines by search (`:1065,1165,1260,1421-1427,2406-2421,2604,2637`); the squash path list, the review gate, the progress file (the finding lines), the surface delta, the parent. **Not re-read** (unverified leads): the recorder, the gate and the ledger writer bodies (read in the PLAN-LB-146 analysis, not re-read here); `plan_logging.py:147-156` and `resolve_project_dir.py:111,192-201` (L1-2, L1-3); every test; every document line; the analysis vocabulary; `marshalld.py`; the rendered `.plan/execute-script.py`.

### Layer 1

| Finding | Claim | Verdict | Polarity | Evidence |
|---------|-------|---------|----------|----------|
| L1-1 (minor, fail-open direction, new) | A Gradle row made only of `:`-prefixed ROOT tasks (`:build :test`) now derives an empty scope and returns `None`; at the parent the raw task names read as scope (`('build','test')`), a narrow row for a module-scoped change and refused. Now it is an inability, and for a module-scoped change the gate can answer fresh, though a root task does not build `core` | checked (re-read of the derivation: `:754-756` skips a token with no inner colon, `:895-896` returns `None` on an empty result) | refutes the spec's "the only admission this plan widens is the legacy shape" | Off-canonical: the discoverer never emits a `:`-prefixed root task (leaf, `_gradle_cmd_discover.py:491-498`); no test covers it. A lone `:test` became stricter (refused for a whole-tree change) |
| L1-2 (minor, leftover) | The recorder takes the FIRST `--plan-id`, the wrapper's argparse keeps the LAST, so `run --plan-id X --plan-id Z` builds Z's tree and records X's root and hash under X, which the gate for X can admit as fresh; the lane fixed exactly this first-versus-last mismatch for `--project-dir` and not for `--plan-id` | checked in part (the template takes `extract_plan_id(script_args)`, re-read; the first-wins parse is the leaf's, `plan_logging.py:147-156`) | refutes | off-canonical |
| L1-3 (minor, mostly fail-closed) | An explicit `--project-dir .` is "not supplied" for the wrapper (default `.`), but the recorder hashes `abspath('.')`: from a subdirectory the roots differ and the row is refused (a false refusal); with `--plan-id X --project-dir .` from the main checkout the row names the main checkout while the build ran in X's tree | leaf | refutes | off-canonical |
| L1-4 (info) | The routed child's recorder ignores `--resolved-project-dir` and re-resolves `--plan-id` from the daemon's working directory; in the move-back window it records an explicit null (refused); the parent executor's row names the right tree | leaf (`_build_execute_factory.py:1133-1173,1356`) | none | fail closed |
| L1-5 (minor) | the gate's `undecidable / head_unresolvable` and the CLI `worktree-sha` message now also fire for a failed or timed-out `diff` or `ls-files`; the cause they name is wrong, the answer stays fail-closed | leaf | refutes (message accuracy) | |
| L1-6 (info) | a repository where `git diff HEAD` takes more than 60 s now reads `undecidable` on every run | leaf | none | |

**C10: F1 and F2 of the PLAN-LB-146 landing.** F1 is closed in the code (the CLI row and a pre-#1971 executor row are key-less and admitted; the new tests drive the real CLI verb and the real gate). F2 is closed in the template for `--audit-plan-id` (the real-`main()` test shows `worktree_root_mismatch`), but a project running an executor generated from the 877 template keeps the F2 route until it regenerates, and L1-2 and L1-3 are two routes of the same class that remain.

### Layer 2

- **The new tests fail at the parent by construction** (leaf): the CLI key tests and the gate-fresh test, the real-`main()` `--audit-plan-id` test, the `--project-dir` tests, the timeout test, the lone-row, `: :` and `:test` tests, the `_D2_` entry and the sweep control. The lane's red-run table (message §1) names a base-evidence run for each; the job logs were not re-read.
- L2-1 (minor): no test covers the multi-root-task widening (L1-1) or a duplicated `--plan-id` (L1-2). L2-2 (minor): `test_every_retired_string_is_parent_text_or_labelled_a_planted_mutation` checks `retired` against a constant inside the test, not against git, so it cannot catch a wrong parent wording (the leaf checked pin 1 by hand); a new pin defaults to `planted`. L2-3 (minor): the docstring of the root-plus-lone-row test says any narrow row refuses the set, while the code returns covered whenever one row covers alone; the test passes because the root `build` row does not cover. L2-4 (minor): `test_freshness_legacy_writer_row.py` isolates the ledger with a `PLAN_BASE_DIR` override and not the `PLAN_MARSHALL_HOME` fixture the spec names (the root conftest was not checked).
- **Surface delta:** declared 21, realized 21, **added 4, missing 4** (`expansion_detected`, read with `inbox landing-check`). Added: `manage-solution-outline/scripts/_criteria_snapshot.py` (the `_D2_` regex; the spec's D5 text allowed "or the regex is", but its Expected Surface named only the rubric documents) and three test files (`test_freshness_legacy_writer_row.py`, `test_freshness_exempt_vs_verified_discrimination.py`, `test_superseded_by_names_deliverable_d3.py`). Missing: `review-rubric.md` and `functional-review.md` (not needed once the regex was changed), `_build_execute_factory.py` and `test_generate_executor.py` (both conditional entries, correctly untouched). The lane names the scope extension in §2.
- **`_criteria_snapshot.py` (outside the declared surface):** the regex accepts `_D2_`, `D2_` and `*D2*`; `D2_notes`, `D2x`, `D2é` and `__D2__` are refused; a self-citation is still `REFERENCE_SELF` and the existence, cycle and successor checks still run after the regex (leaf, `:1921-1944`). The lane's reason for declining the CodeRabbit finding holds.

### Layer 3

- L3-1 (minor): `_freshness_crosscheck.py:449-453` still states the retired reading ("a LONE `:module:`-prefixed task reads as a readable canonical-unknown inability"); D4 asked for this comment to state the new rule. L3-2 (minor): `manage-change-ledger/SKILL.md:395` says every writer and the CLI produce identically-shaped entries, while the CLI now omits keys the executor writes. L3-3 (minor): `manage-change-ledger.py:125-131` says the CLI "is asked about no particular tree" while the verb accepts `--worktree-root`. L3-4 (minor): change-history wording this PR added (template `:1084-1086`, `:2418-2420`, `:2616`; two test docstrings), against the plan's own standing constraint. The three documents no longer contradict each other on the absent-versus-null rule.

### Conformance

| Rule source | Rule | Verdict | Evidence |
|-------------|------|---------|----------|
| Spec constraint | the only admission this plan widens is a row whose writer recorded nothing | deviates, narrowly | L1-1 |
| Spec constraint | docs state current behaviour | deviates (L3-1, L3-4) | |
| Spec constraint | tests use the `PLAN_MARSHALL_HOME` fixture | deviates, nominal (L2-4) | |
| Spec constraint | the PR states executor regeneration is owed | conforms | the lane's report and the template change |
| CLAUDE.md § No shell file operations / `.plan/` scripts only | | **lane-reported deviations**: one `.plan/marshal.json` Read (read-only, disclosed), three guard refusals (R1 heredoc, R2 `rm` of a probe file, R5 mistyped interpreter path), each re-issued the sanctioned way; the R2 refusal is why `cleanup_owed` was true | message §7, not re-read |
| CLAUDE.md § Merge Authorization (Standing) | | conforms: one operator question, about running a fourth self-review round, none about merging | message §6 |

## Metrics and Anomalies

- Tokens: `unknown` (out of scope). About 38 routed builds plus seven in-process base-evidence runs the lane requested on purpose; one run outlived a call and was re-attached; CodeRabbit reviewed once and a later incremental review hit its free-OSS cap, a rate notice and not a review (lane-reported, not re-read).
- **Owed cleanup, now done:** the lane's base-evidence worktree is no longer on disk (it is absent from `git worktree list` and its path does not exist), and the earlier PLAN-LB-146 base worktree, which held only four untracked copies of tests now on `main`, was removed by the orchestrator on the operator's word of 2026-11-14 ("make a full cleanup").

## Routing and Merge Behavior

- CodeRabbit (required) reviewed `1601eea4a`; every finding fixed or declined with a reason, every thread answered then resolved; no re-trigger (done after handling). Sourcery refused on its own quota and gated nothing. The standing authorization was not needed.
- CI green on every pushed head per the lane (`verify` at three heads, 896 to 1073 s); the PR reads merged as a squash with one parent. Sonar `n/a`; ignored here.

## Reconciliation Actions

- [x] row `status` → `shipped`; `pr` 1977; `landing` `landings/PLAN-LB-149.md`; `plan_marshall_plan_id` `rb-lb-149-build-row-writers-and-freshness-truth`
- [x] epic.md annotation and Decisions entry; the resume anchor; `queue-view.md`; message archived after the persist

## Follow-Ups

- **Residue, one surface (the recorder, the gate and their documents):** L1-1 to L1-5, L2-1 to L2-4, L3-1 to L3-4. All minor and off-canonical, so under the operator's rule no plan is staged; if one is, L1-2 (first-versus-last `--plan-id`) and L1-3 (`--project-dir .`) are the two to carry with L1-1.
- **Executor regeneration is still owed, for a different reason than before:** F1 no longer halts the push gate (a stale executor's rows read as before), but F2 stays live in every executor generated from the 877 template until it is regenerated, and the template of this PR carries the fix.
- **Operator decision 2** (a deliverable retired with no successor) is untouched by this landing and still open.
