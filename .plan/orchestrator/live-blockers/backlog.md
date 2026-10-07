# Backlog: the full candidate list this epic was cut from

> The HIGH items of this list are staged as plans `PLAN-LB-01` to `PLAN-LB-21`: §§ 1.1–1.11, 2.1, 2.2, 3.1 and 4.1–4.6. Everything else here is unstaged backlog. The text is the list as it stood when the epic was cut; it is a record, not a live status.

Result of a read-only sweep of all nine active orchestrator epics and the global lessons store, checked against the code at `d42dc6a94`.

An item is listed when at least one of these holds:

- **A** — a defect in plan-marshall at HEAD that breaks or complicates normal use today.
- **B** — work on something the PM-MCP rewrite does not replace (domain skills, consumer repos, org CI, review bots, harness sync, repo docs).
- **C** — the ledger marks it critical, or it is a security or data-loss issue, or it turns `main` red.

Items that are only design input for the rewrite, and refactors, metrics and token-cost work on machinery PM-MCP replaces, are left out.

Each item was found by a sweep agent that read the source ledger and then the code. "Verified" means the agent cited a file and line at HEAD; "unverified" means the claim rests on the ledger or a run report. Epic abbreviations: TS truthful-signals, RA review-apparatus, PC process-compliance, CIS code-intelligence-substrate, PRQ post-run-quality, TQ test-quality, IS instrumentation-substrate, LR lessons-routing, OR orchestrator-refactor, LES the lessons store.

Sizes are guesses: S under a day, M a normal plan, L more than one plan.

---

## 1. Finalize and phase gates that block, mislead or need an override

### 1.1 Push freshness gate rejects the pre-push gate's own green builds — HIGH
The pre-push gate runs quality-gate, test-compile and the tests green on the commit. The freshness check before push only accepts one build record that covers everything, so it reports `build_scope_narrow`. Every finalize pays a second full verify (about 40 minutes) or halts and asks for an override.
- Category A, C. Verified: `manage-tasks/scripts/_freshness_crosscheck.py:257,272,504-539`.
- Sources: TS PLAN-TRUTH-186 (staged), PC PLAN-23 D3 (staged), lesson `2026-09-09-06-002`.
- Spec: `truthful-signals/plans/PLAN-TRUTH-186-…md`, narrow and ready. Size S–M.

### 1.2 Pre-submission self-review does not converge and re-runs settled steps — HIGH
The step has no exit except a clean round or the round ceiling. Recent plans ran 4 to 14 rounds and were stopped by an operator override. Each round re-fires simplify, lessons-housekeeping and plugin-doctor in full, because no step declares which files its verdict depends on. Once the shared counter is spent, real review fixes cannot run. The last commit then ships without the closing gate.
- Category A, C. Verified: `phase-6-finalize/workflow/pre-submission-self-review.md:694`, `phase-6-finalize/scripts/verdict_currency.py:139,200`, `phase-6-finalize/SKILL.md:1475-1502`; no step declares `verdict_inputs`.
- Sources: PC PLAN-20 (staged), PRQ PLAN-PRQ-10 (parked), lessons `2026-09-29-17-001`, `2026-10-02-10-005`, `2026-10-07-07-001`.
- Spec: `process-compliance/plans/PLAN-20-self-review-convergence.md`, ready; minimal cut is D2–D4. Size M–L.

### 1.3 Self-review loops to the ceiling on consumer-repo diffs — HIGH
In a Java or other consumer repo the step picks the plan-marshall surfacer because it resolves. It has no detectors for those files, so the verifier refuses for a reason no further round can change, and the step blocks the push until an operator override (about 28 minutes on one TokenSheriff PR).
- Category A, C. Verified: `phase-6-finalize/workflow/pre-submission-self-review.md:119`; only `ext-self-review-plan-marshall` exists.
- Sources: TS PLAN-TRUTH-181 (staged), PLAN-TRUTH-167, PLAN-TRUTH-173.
- Spec: `truthful-signals/plans/PLAN-TRUTH-181-…md`; D1–D3 are the blocker fix. Size M.

### 1.4 Light-lane plans cannot pass the refine boundary — HIGH
Small plans skip the refine phase, the only place a PR title and a refine record are written. Later boundaries demand both, so every light-lane plan stops with `pr_title_missing` and needs a hand-set title or an undocumented override flag.
- Category A, C. Verified: `plan-marshall/scripts/_invariants.py:1709-1713,1852`, `plan-marshall/workflow/planning.md:253-254`.
- Sources: TS PLAN-TRUTH-172 D2 (staged), PC PLAN-10 D1 (staged), lessons `2026-09-04-12-001`, `2026-09-08-15-001`.
- Spec: PLAN-TRUTH-172 D2, usable as a one-deliverable plan. Size S.

### 1.5 Wait procedures the harness cannot run — HIGH
The merge-lock wait, the merge-queue wait and the review-bot poll all prescribe a standalone `sleep`, which the harness blocks. Long builds exceed the 10-minute call ceiling while one document forbids backgrounding them. A CI wait that lapses while checks are still running is filed as a `ci_timeout` finding and costs a loop-back round.
- Category A. Verified: `phase-6-finalize/standards/branch-cleanup.md:373,579,594,608,1572,1590`, `automatic-review/SKILL.md:345,351,579-640`, `manage-locks/SKILL.md:660`, `plan-marshall/workflow/execution.md:373` against `await-long-running.md:13,28`.
- Sources: TS PLAN-TRUTH-169 and -162 (parked), PC PLAN-23 D4 (staged), lesson `2026-10-07-07-007`.
- Spec: PC PLAN-23 D4; the TS specs are stale. Size M.

### 1.6 Triage cannot create or schedule its own fix tasks — HIGH
The triage document tells the agent to create a fix task with `deliverable: 0`, which the validator rejects. A fix task that is created gets no envelope number, and the executor only runs tasks that have one. One failure was then re-triaged once per deliverable (five dispatches and six test runs for a single failure).
- Category A. Verified: `plan-marshall/workflow/triage.md:191` against `manage-tasks/scripts/_tasks_core.py:881-886`; `manage-tasks/scripts/_tasks_crud.py:262-276`.
- Sources: PC PLAN-19 (staged), lessons `2026-09-06-09-002`, `2026-09-13-20-001`.
- Spec: `process-compliance/plans/PLAN-19-execute-verification-loop.md`, ready. Size M.

### 1.7 Scope-creep guard crashes whenever it fires — HIGH by frequency
The guard files a finding of type `scope_creep_warning`, which the findings store rejects, so it exits with an error on every over-threshold call. It also diffs from the plan's creation commit, so everything merged from `main` since counts as the plan's creep. Agents pass thresholds of 1000 or more, which disables it. The tests pin the rejection as intended behaviour.
- Category A. Verified: `phase-5-execute/scripts/scope_creep_check.py:108,180,212`, `tools-file-ops/scripts/constants.py:96-121`.
- Sources: PC PLAN-27 D1 (staged), TS PLAN-TRUTH-178 (parked), lessons `2026-10-02-10-003`, `-004`; named by six sweeps.
- Spec: `process-compliance/plans/PLAN-27-…md` D1, ready. Size S.

### 1.8 Re-running a quality check wipes the triage already done — HIGH
When a checker re-emits a finding that was accepted or fixed, the store resets it to pending and deletes the resolution. Verifying a fix destroys the triage and re-blocks finalize.
- Category A, C (data loss). Verified: `manage-findings/scripts/_findings_core.py:1065-1090`.
- Sources: lessons `2026-09-02-19-001`, `2026-09-05-17-001`.
- Spec: none. Size S.

### 1.9 Pending-findings gate leaks around merge and archive — HIGH
The archive command refuses a plan with a blocking finding, but the finalize step has already marked itself done and logs "Plan archived" without reading the result. Passing `--reason normal_completion`, which the command's help suggests, skips the gate. Before the merge, the findings check is only an instruction; no merge verb enforces it.
- Category A, C. Verified: `phase-6-finalize/standards/archive-plan.md:50-71`, `manage-status/scripts/_cmd_lifecycle.py:598-616,975`, `phase-6-finalize/standards/branch-cleanup.md:735-744`.
- Sources: CIS PLAN-CIS-052 D3 (staged), CIS-054 D5.3.
- Spec: CIS-052 § D3(a) is ready; the merge-side check needs a design. Size S + M.

### 1.10 A retried finalize step cannot record its outcome — HIGH
Recording "done" over an earlier "failed" is refused without `--force`, and so is "failed" over an earlier "done", so a red re-run cannot stop the pipeline. `ci_verify` reports `step_marked_done: true` while the record still says `loop_back`.
- Category A. Verified: `manage-status/scripts/_cmd_mark_step.py:655-666`, `phase-6-finalize/scripts/ci_verify.py:401-417,630-647`.
- Sources: PC PLAN-21 D2 (staged), TS PLAN-TRUTH-170 (parked).
- Spec: PC PLAN-21 D2, ready. Size S–M.

### 1.11 Finalize commits choose files by prose instruction only — HIGH (security)
Each finalize commit is made by an agent told to "stage the relevant files". No script limits what is staged, so an untracked secret or unrelated file can enter a pushed commit. CodeRabbit rated it Major on #1454; it was accepted, not fixed.
- Category C, A. Verified: `workflow-integration-git/SKILL.md:132`; `git-workflow.py` has no staging verb.
- Sources: lesson `2026-09-08-22-001`, TS PLAN-TRUTH-170 D5 (parked).
- Spec: stale. Size M.

### 1.12 Lessons-housekeeping step opens with a call that always errors — MEDIUM
Step 1 reads the retired `modified_files` field and gets `field_retired` on every run. Each firing improvises a replacement. The step decides which lessons to delete, so it runs on an improvised input.
- Category A, B (project-local skill). Verified: `.claude/skills/finalize-step-lessons-housekeeping/SKILL.md:89-90,318`, `manage-references/scripts/_references_core.py:125`.
- Sources: named by five sweeps; TQ PLAN-184 D2, CIS-052 D6(b), PRQ-05 fold, lesson `2026-09-27-08-001`.
- Spec: TQ PLAN-184 D2, ready. Size S.

### 1.13 Finalize gates scope themselves from a stale file list — MEDIUM
The declared file list is written at outline time and never updated. The plugin-doctor gate scopes from it, so files added during execute or review are never linted (37 declared against 60 realized in one plan).
- Category A. Verified: `.claude/skills/finalize-step-plugin-doctor/SKILL.md:64-65`.
- Sources: lesson `2026-09-29-17-002`, PC PLAN-21 D3.
- Spec: PC PLAN-21, ready. Size M.

### 1.14 Plan keeps pointing at a deleted worktree and is never archived — MEDIUM
`worktree-remove` does not clear `use_worktree` or `worktree_path`. Later steps refuse to run against the missing tree. `plan-pr-078-review-bot-fleet-opt-in` is stuck this way now, with every step done and its archive never run; four consumer checkouts are still on its merged branch.
- Category A, B. Verified: `workflow-integration-git/scripts/git-workflow.py:1598-1611` (set) against `:2000-2295` (never cleared); live `manage-status read` on that plan.
- Sources: TS PLAN-TRUTH-164 and -171 D5a (parked), RA watch 2026-10-07.
- Spec: lift PLAN-TRUTH-171 D5a alone. Size S, plus a one-off cleanup.

### 1.15 Clean-checkout assertions stop a plan on other actors' writes — MEDIUM
After init, refine, outline and plan the workflow demands an empty `git status` on the main checkout and tells the agent to revert what it finds. Sibling plans legitimately write there. Partly eased by the shared ledger worktree; the text is unchanged.
- Category A, C. Verified: `plan-marshall/workflow/planning.md:166-172,442-477`.
- Sources: PC PLAN-17 D1 (staged). Spec ready; re-check the premise. Size M.

### 1.16 Phase handshake reports drift when findings are resolved normally — MEDIUM
Pending-finding counts are compared strictly at each boundary, so resolving a finding at a review gate produces `drift` and needs two override calls the workflow does not mention.
- Category A. Verified: `plan-marshall/scripts/_invariants.py:1845-1851`.
- Sources: lessons `2026-09-02-15-002`, `2026-09-13-21-002`. Spec: none. Size M.

### 1.17 Plans advance past the outline with quality-gate findings pending — MEDIUM
The outline agent transitions the plan itself before the orchestrator's quality gate runs, and only the finalize boundary checks for pending findings. One plan ran two phases with three failed-deliverable findings open.
- Category A. Verified: `phase-3-outline/SKILL.md:694-700`, `plan-marshall/scripts/_invariants.py:1289`.
- Sources: lessons `2026-09-27-07-003`, `2026-10-02-21-003`, PC PLAN-18. Size M.

### 1.18 Planning-lane contracts that cannot be followed as written — MEDIUM
A group of small faults: the rule for skipping a repeated quality check depends on hashes no tool computes; "ask all questions in one prompt" exceeds the four-question limit; two documents disagree on whether outline runs inline; the blocking count can read 1 while every bucket reads 0.
- Category A. Verified at the lines cited in PC PLAN-18 and PLAN-17.
- Spec: `process-compliance/plans/PLAN-18-…md`, ready. Size M–L.

### 1.19 Plan init mis-sizes and mis-labels spec-driven plans — MEDIUM
Scope estimation counts the spec's own path as change surface, domain detection can match the epic's name, the request body is written with a full-file overwrite that loses header fields, and the classify tools take the request only as a one-line argument.
- Category A. Verified: `manage-status/scripts/_cmd_planning_lane.py:268-279,323-368`, `manage-config/scripts/_cmd_domain_detect.py:387-411`.
- Spec: `process-compliance/plans/PLAN-16-init-lane-fidelity.md`, ready. Size M.

### 1.20 Dispatch contract faults — MEDIUM
Simplify and self-review are listed as dispatched but tell the sub-agent to dispatch its own sub-agents, which it cannot. The dispatch header passes an absolute worktree path the agent contract forbids, so dispatches are intermittently refused. Execute dispatches return a "checkpoint" with tasks left and the operator restarts them (10 of 14 terminations in one run).
- Category A. Verified: `phase-6-finalize/standards/dispatch-inline-split.md:21,27`, `agents/execution-context.md:27`, `plan-marshall/workflow/execution.md:152,166,203,225-245`.
- Sources: PC PLAN-21 D1, PLAN-27 D2 (ready); CIS-052 D7/D8 (needs design). Size S + S + M.

### 1.21 Steps declared read-only change files, and nobody commits them — MEDIUM
The pre-push gate can rewrite `uv.lock` or a POM and self-review's loop-back can edit source, but both declare they change nothing, so no commit follows. The result is a dirty tree and a halted push.
- Category A. Partly verified: `phase-6-finalize/workflow/pre-submission-self-review.md:8`.
- Sources: lessons `2026-09-08-20-001`, `2026-09-09-06-003`. Size S–M.

### 1.22 Self-review marks findings fixed because upstream touched the file — MEDIUM
After a rebase the diff since the last round includes everything upstream changed, so an earlier blocking finding is auto-closed although the plan never touched it.
- Category A. Verified: `phase-6-finalize/workflow/pre-submission-self-review.md:137-155`.
- Spec: CIS-052 § D5(c)/(d), ready. Size S.

### 1.23 Merge-queue landing gate cannot tell an ejected PR from a queued one — MEDIUM
An ejected PR returns to `open`, the same state as a waiting one. The gate waits its full 1800 seconds and then spends a loop-back round. The queue-state verbs exist (#1690) but finalize does not use them.
- Category A, B. Verified: no `queue-state` or `wait-for-queue-settle` under `phase-6-finalize/`.
- Sources: lesson `2026-10-02-10-002`, OR PLAN-10 landing. Size S–M.

### 1.24 Smaller finalize defects — MEDIUM to LOW
- **Wrong merge commit recorded.** Branch cleanup records local `HEAD` of main as the merge commit; wrong whenever another PR lands first. Verified: `branch-cleanup.md:1746-1756`. Size S.
- **Merge lock released early.** The integrate step takes and releases the same lock inside the outer hold. Partly verified: `integrate_into_main.py:13-24`. PC PLAN-26 D3. Size S–M.
- **First push fails.** The documented push has no upstream on a new branch; the artifact scan lists hundreds of tracked fixtures as "uncertain". Verified: `workflow-integration-git/SKILL.md:174`. PC PLAN-26 D1/D2. Size S.
- **PR record after close-and-reopen names the closed PR.** Verified: `pr-review-operations.md:334-338`. PC PLAN-24 D4. Size S.
- **ADR proposals silently dropped.** The step runs as a sub-agent but must ask the operator. Verified: `adr-propose.md:42,110`. Size S–M.
- **Recomposing the execution manifest erases the step log.** Verified: `manage-execution-manifest.py:2603-2608`. Size S.
- **`bundle:skill` finalize steps are not ordered and the order check passes anyway.** Verified: `_manifest_validation.py:232-240,358-359`. Size S–M.
- **Rebase-time executor refresh reports success over a stale executor.** Verified: `git-workflow.py:984-986,1045-1076`. CIS-052 D4. Size M.
- **Landing report lost for a plan without `source_id`.** Description-sourced plans are classed "not orchestrated" and the landing step is dropped; detection errors on an empty id. Verified: `manage-execution-manifest.py:900-928,976-986`, `orchestrator.py:6464-6468`. Size S.
- **Red-CI triage dead-ends on a producer name.** `ci-verify-build` is not in the accepted list. Verified: `verification-feedback.md:30,59`. Size S.

---

## 2. Build, executor and tooling

### 2.1 Build timeouts leave processes running and local verify outruns its budget — HIGH
When a routed build hits its limit only the top process is killed; pytest workers keep running and the re-run stacks suites. The whole-tree suite takes 6 to 13 minutes quiet and far longer under concurrent plans, so the job is killed, no verify record exists and the push is refused; the recorded way out was `--force`. Overlapping runs can also delete each other's temp directory, and a killed build does not say which budget killed it.
- Category A. Verified: `manage-build-server/scripts/_marshalld_supervisor.py:313-332`, `build.py:133,149,222-262`.
- Sources: TS PLAN-TRUTH-169 (parked), PC PLAN-25 (staged), TQ landings.
- Spec: PC PLAN-25, D2/D3 ready. Size M.

### 2.2 Maven build results are wrong in consumer repos — HIGH
Three defects in the Maven path. The generated `module-tests` command never reaches `package`, so a module using a sibling test-jar fails at discovery. Only the last "Tests run" block is counted, so 724 tests read as 7. The `[deprecation]` pattern is compiled as a regex character class, so Maven's failure epilogue is filed as blocking deprecation findings. PM-MCP lists these parsers as ported, so the defects would carry over.
- Category A, B. Verified: `build-maven/scripts/_maven_cmd_discover.py:787,810`, `_maven_cmd_parse.py:164`, `script-shared/scripts/build/_build_parse.py:487-490,624`, `_build_jvm_patterns.py:54`.
- Sources: TS PLAN-TRUTH-150 (parked), archived PLAN-TRUTH-122.
- Spec: archived `PLAN-TRUTH-122`, line numbers still match. Size M.

### 2.3 A script changed by a plan cannot be called by the same plan — MEDIUM
The generated executor embeds each script's flags at generation time. A plan that adds a flag and uses it later gets `unknown_flag` while `--help` shows the flag, and the task stalls until someone regenerates the executor. Regeneration also has no import check before replacing the old executor.
- Category A. Verified: `tools-script-executor/scripts/generate_executor.py:1344-1465`; no regeneration step in `phase-5-execute/SKILL.md`.
- Sources: lesson `2026-10-07-07-002`. Size M.

### 2.4 Permission checks report clean without looking — MEDIUM (security)
The steward wildcard check reads a `bundles` dict from a descriptor that has a `plugins` array, so it analyses zero bundles and reports success. The suspicious-permission check passes an allow rule with a mid-command wildcard. Both scripts are retired in PM-MCP's inventory.
- Category A, B, C. Verified: `tools-permission-fix/scripts/permission_fix.py:694,816-822`, `tools-permission-doctor/scripts/permission_doctor.py:226-346`.
- Spec: `truthful-signals/plans/PLAN-TRUTH-165-…md`, ready. Size S–M.

### 2.5 Production git calls are not hardened against hostile git config — MEDIUM (security)
About 20 scripts shell out to `git` with the ambient environment. CodeRabbit finding `5ed953` on #1585 hardened only the test fixture.
- Category C. Verified: `plan-orchestrator/scripts/orchestrator.py:2285-2287`.
- Spec: none. Size M–L.

### 2.6 Lessons tooling — MEDIUM
- The duplicate check before filing a lesson cannot see plans in worktrees and suggests creating a document that already exists. Verified: `manage-plan-documents/scripts/_cmd_request.py:153-169`.
- `drain-dedup` groups by component alone and reported five of nine lessons as false recurrences. Verified: `manage-lessons/scripts/_lessons_aggregate.py:278-334`.
- A consumer repo's own namespaced component (`api-sheriff:auth`) is refused as "wrong store". Verified: `manage-lessons/scripts/_lessons_io.py:174-235`.
- Size S each.

### 2.7 CI abstraction gaps — MEDIUM
No way to read CI results for a commit on `main`, no `pr reopen` although the bot-recovery protocol needs it, an "unresolved comments" count that can never reach zero, `ci checks status` omitting a workflow's checks with no completeness signal, and a network blip reported as "not authenticated". Each forces a direct `gh` call the rules forbid.
- Category A, B. Verified: `tools-integration-ci/scripts/ci_base.py:872-874,1287-1291,1314-1317`.
- Sources: TS PLAN-TRUTH-150 folds, lessons `2026-09-28-17-001`, `2026-08-31-08-001`. Size M.

### 2.8 Local green from generated `target/` trees — MEDIUM
A test scans generated harness trees. In a long-lived worktree they exist and the local run is green; on a clean checkout it was red. CI now generates first, but the local gate does not notice and `clean` leaves `target/` in place.
- Category A, B. Verified: `build.py` `cmd_clean`. PC PLAN-23 D1/D2, ready. Size S.

### 2.9 Smaller tooling defects — MEDIUM to LOW
- **Content search has no path filter**, though it is the mandated fallback when Grep is denied; agents invent a flag and are rejected. Verified: `manage-architecture/scripts/architecture.py:305-335`. Size S.
- **Executor gives wrong correction advice** for a mistyped script name. Verified: `execute-script.py.template:1498-1511`. Size S.
- **`architecture diff-modules` reports every module changed** because no `derived.json` is committed. Verified: `_cmd_client_handlers.py:1607-1620`. Size S.
- **Concurrent refines share one temp file** and can swap module mappings. Verified: `refine-workflow-detail.md:752,766`. Size S.
- **`files_exist` plan check** flags predecessor-created files and globs. Verified: `_cmd_qgate_mechanical.py:481`. Size S.
- **Outline parser** can invent a path from an annotated bullet, and keeps only one verification command per deliverable. Verified: `_plan_parsing.py:464,832,836`. Size S–M.
- **"Unknown" file-type deliverables** are promised to block and do not. Verified: `phase-3-outline/SKILL.md:457,484`. Size S.
- **`--plan-id` injection** covers build commands only; its test repeats the wrong list. Verified: `inject_project_dir.py:70,72,164`. CIS-052 D6(a). Size S.
- **Verify-failure classifier** can call a plan's own failures foreign. Verified: `verify_failure_scope.py:97`. Size S.
- **Build-server `wait` without a job id** attaches to the plan's latest job. Verified: `build_server.py:330-356,516`. Size S.
- **Footprint export** can overwrite a plan's state files. Verified: `_cmd_compute_footprint.py:175-197`. TQ PLAN-184 D4. Size S.
- **LSP edit verb** reports success for a declined rename and a clean rollback over changed line endings. Verified: `lsp_client.py:352-362`. Size S.
- **Documented calls that fail as written:** retrospective `--diff-file work/footprint.txt` (nothing writes it), `architecture --package` with a dotted name, `manage-findings` listing 12 of 14 types.
- **Whole-marketplace scan tests** need a 900-second marker and nothing enforces it. TQ PLAN-184 D1. Size S–M.
- **Whole-tree test runs fragment execution**: tasks are closed with their tests unrun and the build is filed under no plan. Verified: `execute-task/SKILL.md:273`, `_build_cli.py:701`. Size M.

---

## 3. The orchestrator itself (the new epic will run on it)

### 3.1 Launch gate refuses every plan — HIGH
The disjointness check refuses all candidates when any sibling spec or live plan has no comparable file list. That is always so (95 of 611 sibling specs at last measure), so `next` emits nothing and every launch since 2026-09-22 needed an override. Archiving nine epics may shrink the set; that is not verified.
- Category A, C. Verified: `plan-orchestrator/workflow/orchestrate.md:107`, `orchestrator.py:4412`.
- Spec: none; two remedies named. Size M.

### 3.2 Steward `.gitignore` setup leaves the ledger ignored — MEDIUM
The block the steward writes ignores `.plan/*` and re-admits three paths, none of them the orchestrator ledger. In a consumer repo `git add` of ledger files does nothing. Found on cui-http.
- Category A, B. Verified: `marshall-steward/scripts/gitignore_setup.py:82-86,94-112`.
- Spec: `truthful-signals/plans/PLAN-TRUTH-187-…md`, fresh and ready. Size S.

### 3.3 Emission and readiness checks — MEDIUM to LOW
- The free-slot count looks only at `launched` rows, the restart check only at `running` rows; each misses the other state. Verified: `orchestrate.md:81`, `orchestrator.py:4688,4704`.
- A `###` sub-heading inside "Expected Surface" hides the entries below it. Verified: `epic_spec_parser.py:464-480`.
- A "sender finished" marker counts as unread mail and blocks readiness; draining it erases the closure. Issue #1697 is open. Verified: `orchestrator.py:4804`. This matters for archiving nine epics.
- `manage-status list` still shows the plan-less sentinel as in progress.
- An unreadable main-checkout config silently falls back to the primary checkout. Verified: `orchestrator_worktree.py:116-138`.
- `worktree-rebase-to` has no reserved-key check for the ledger worktree.
- Size S each.

### 3.4 Ledger state to repair before archiving
- #1641 reverted parked rows to `staged` in instrumentation-substrate, lessons-routing, code-intelligence-substrate and test-quality, and the restore was never done there. A `next` on those epics would emit superseded plans.
- A stale-branch squash merge can silently revert newer ledger content; no guard was found. The `land` verbs narrow this.

---

## 4. Outside PM-MCP's scope

### 4.1 Every harness sync leaves the plugin registry pin behind — HIGH
The sync writes a new cache version and regenerates the executor but never updates Claude Code's plugin registry. Sessions load skill text from the old version while scripts run the new one. Live now: the registry pins `0.1.1837`, the executor is `0.1.1857`, and the newer cache directory is already marked for collection. Repair is an operator script outside the repo plus a restart, after every landing.
- Category A, B, C. Verified live; no `installed_plugins` handling in `marketplace/targets/`.
- Sources: named by five sweeps; TS PLAN-TRUTH-154 (parked, stale). Size M.

### 4.2 Config-only and docs-only PRs skip the test build and red `main` — HIGH
The org footprint gate treats `.plan/**`, `.claude/**` and Markdown as non-building, also in the merge queue. In this repo the tests read exactly those files. Three `marshal.json`-only PRs turned `main` red in one day and stalled a plan for about 18 hours.
- Category A, B, C. Verified: `cuioss-organization/.github/workflows/reusable-pyprojectx-verify.yml:142-156`, consumed at `.github/workflows/python-verify.yml:43-50`.
- Sources: lesson `2026-10-02-10-001`, PC open defect. Spec: none. Size S–M (org repo plus a pin bump).

### 4.3 OpenCode and Antigravity installs ship skills without `workflow/` — HIGH
The generator copies `standards`, `references`, `templates` and `scripts` per skill. The `plan-marshall` skill routes every action to `workflow/*.md`, which is absent in the installed copy on those two harnesses.
- Category A, B. Verified: `marketplace/targets/sync.py:119`, `opencode/emitter.py:80`, `antigravity/emitter.py:51`.
- Spec: none. Size S.

### 4.4 Review-bot recovery and the review gate — HIGH (cluster)
- **Quota wait inside a sub-agent.** A CodeRabbit refusal starts a wait of up to an hour inside an agent with a 15-minute budget that cannot sleep. The operator kills and re-dispatches. Verified: `automatic-review/SKILL.md:180,570-596`.
- **Refusal notices misread.** "Next included review available in N minutes" matches no pattern, so the run waits a fixed 90 minutes (five hours lost against a 21-minute window). Only `@coderabbitai review` exists, which is refused with no new commit; `full review` works and cannot be sent. "Review triggered" is read as a refusal. Verified: `automatic-review/standards/coderabbit.md:37,58-80`, `_github_pr.py:605-640,725`.
- **Stale required bot never re-triggered.** The trigger selects bots from stored findings only, so a bot whose comment was filtered as noise is never chosen. Verified: `automatic-review/SKILL.md:219,230`, `review_completeness.py:382-386`.
- **Merge gate credits a review of an older commit.** Findings are stamped with the PR head at fetch time, a bot's reply in an old thread counts as fresh, Sourcery is exempt from the staleness test, and the SHA guard has no production caller. Verified: `github_pr.py:1644,1712-1759`, `_github_pr.py:318`.
- **"Fixed" posted before the fix exists.** Triage posts the reply and resolves the thread before any commit or build. Verified: `plan-marshall/workflow/verification-feedback.md:7,260-264`.
- **Size limits discovered after the PR exists.** A 151-file PR was refused by both bots after push and CI, then split by hand. Verified: caps exist only as refusal-text patterns in `bot_registry.py`.
- **Smaller:** replies sent twice or never when the resolve call fails (`github_pr.py:2772-2786`); a phrase inside a comment can drop the whole finding (`github_pr.py:469-473`); a slow bot is filed as a CI timeout (`ci_verify.py:193-194`); a reworded refusal from cuioss-review-bot would count as a review.
- Category A, B, C. Sources: RA PLAN-PR-069, -070, -068 (superseded, stale but detailed), PC PLAN-24 (staged, ready), lessons `2026-10-03-18-001`, `2026-10-07-07-007`, `-008`.
- Size: M each for the first four, S–M for the rest.

### 4.5 Review-bot fleet rollout stopped at 7 of 20 repositories — HIGH
Thirteen repos could not be enrolled because their `project.yml` fails the org schema on keys the rollout never touches (`auto-merge-build-timeout`, two-part versions). The three migrated repos carry the same failures. No runnable validator exists.
- Category B, C. Verified: `cuioss-organization/.github/actions/read-project-config/schema.json:161,167,248-259`.
- Sources: RA PLAN-PR-078 landing, lesson `2026-10-06-15-001`. Spec: none; the lesson is a usable directive. Size M.

### 4.6 The required in-house reviewer almost never finds anything — HIGH
In the last measurement 152 of 156 cuioss-review-bot reviews were the same canned "no issues" table. The charter and domain packs changed afterwards and nothing has been measured since, so nobody knows whether the fleet rollout is worth finishing.
- Category B, C. Unverified since 2026-09-15.
- Spec: none; the method is in `review-apparatus/findings/2026-09-15-…md`. Size M.

### 4.7 Required CI check can be green on a PR nothing verified — MEDIUM
A push run skips the heavy verify when an open PR exists and still reports `verify / conclusion` green. If the PR never got a `pull_request` run, nothing tested it. Recorded on two PRs. The merge-queue run still builds, which limits the damage.
- Category B, C. Verified: `reusable-pyprojectx-verify.yml:225-241,399-405`. Size M.

### 4.8 Consumer repos and bot operation — MEDIUM
- nifi-extensions lists the retired `pr-agent`; cui-jsf-test-basic, cui-open-rewrite and cuioss-parent-pom have no `required_bots`, so their review gate passes with nobody required. Nothing rejects an unknown bot name at write time. Size S.
- cuioss-review-bot does not re-review after a push, and a PR whose open event is missed is never reviewed. Size M.
- Six enrolled repos have never been seen running the assembled charter. Size S.
- Review findings on merged PRs were never answered: at least #1433, #1468, #1484, #1066, #1338, plus #1585, which merged on an override. Size M.
- The cross-repo archive gate still clears on a change that was committed locally and never pushed. Verified: `foreign_pr_gate.py:99,269`. Size M.
- Five findings about plan-marshall sit unread in consumer repos' git-ignored lesson directories (Surefire selector, Sonar over http, change-ledger skip in a worktree, empty skill list for doc tasks, the profile-standards recipe). Size S to read.

### 4.9 Domain skill content — MEDIUM
- **pm-dev-java:** the compliance checklist tests one of four positions where `Optional` is forbidden; a cross-reference points at a section that does not exist. Verified: `java-maintenance/standards/compliance-checklist.md:36`. Spec: archived PLAN-TRUTH-091 D3/D4, ready.
- **pm-dev-java:** no warning that narrowing a `catch` can drop the cleanup after it (TokenSheriff shipped a retained credential this way), and none that `allowEmptyShould(true)` keeps an ArchUnit rule passing after it matches nothing.
- **pm-dev-java / build-maven:** no guidance on `failIfNoSpecifiedTests` for scoped test selectors, on `-pl` without `-am`, or on method references in a usage search.
- **pm-dev-python:** Hypothesis property-based testing is prescribed and never used or declared. Verified: `pytest-testing/SKILL.md:3,58,90`. Spec: IS PLAN-07, ready.
- **pm-documents:** the reference checker reports valid anchors with a spaced dash as broken (`doc_references.py:108-109`); the deployment-diagram standard contradicts its own examples.
- **Self-review surfacers** exist only for plan-marshall's own content; none for Java, Python, JavaScript, documents or AsciiDoc. Specs: TS PLAN-TRUTH-182 to -185 (staged). Size L. Operator call, since PM-MCP redesigns the surfacer.
- Size S each unless noted.

### 4.10 Repository documentation and decisions — LOW to MEDIUM
- `CLAUDE.md` does not say which source wins when the harness injects a different commit trailer; agents stop and ask.
- User docs describe a config knob nothing reads (`drop_review_on_scope_gate`), a config example the tool rejects, retired status names, and pre-migration paths for logs and lessons.
- ADR-023 and ADR-024 are still "Proposed"; the naming standard prescribes `--epic` and points at a rename plan that no longer exists, while the code uses `--slug`.
- Whether the generator should vary instruction calibration per model was never decided. Spec: IS PLAN-03, ready.

### 4.11 Smaller items outside PM-MCP — LOW
- Dependabot uses the `pip` ecosystem and can bump `pyproject.toml` without relocking `uv.lock`.
- The Sonar step reports a confirmed zero for PRs Sonar never analysed.
- Release and deploy steps are planned as ordinary agent steps and stall.
- Fifteen tests never run locally; five are excluded through `collect_ignore` and invisible to the skip gate.
- The recorded "zero over-budget test modules" result is false (419 files over 400 lines at HEAD); do not stage the warning-to-error flip from it.
- Open items now belonging to the `plan-marshall-telemetry` repo; unverified, no checkout here.

---

## 5. Housekeeping before the old epics are archived

- **Lessons store:** 35 active lessons with no router. Two describe defects already fixed and should be retired (`2026-09-27-07-001`, `2026-10-02-21-006`); one has no metadata header (`2026-09-27-19-001`).
- **lessons-routing is dormant** and its inbox is undrained; nothing sent there will be read.
- **Transfers from orchestrator-refactor** to truthful-signals and lessons-routing are undrained; their content is covered by sections 1 to 4 above.
- **Rows to close, not carry:** PRQ-12 (shipped via #1646). PRQ-14's premise is overstated.
- **Unlanded:** the orchestrator-refactor cleanup and the review-apparatus PLAN-PR-078 landing exist only on the local ledger branch.
- **Stale notes corrected by this sweep:** the macOS `/proc` skip is fixed; TokenSheriff is no longer merge-blocked; `ci pr merge` re-reads PR state; the mailbox address mismatch is fixed.
