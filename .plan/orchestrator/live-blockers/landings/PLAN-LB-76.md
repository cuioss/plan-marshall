# Landing Analysis: PLAN-LB-76 — exclusions and module qualification bound to a task's skills (runbook lane)

epic: live-blockers
workstream: WS-01
pr: #1824 (https://github.com/cuioss/plan-marshall/pull/1824), squash-merged as `0cfc7d3f0` (17 files, +895/-41); merged head `b7aefb68e`, `git diff b7aefb68e 0cfc7d3f0` empty
harness: **OpenCode runbook lane**, `deepseek-v4.1-flash` / `high`. Root `ses_ea7f4f62dffeQDFnney2U4gil6`, four self-review child sessions (one aborted by the server restart), one session in all with one restart and no compaction. **First run on the post-PLAN-LB-72 install: the lane text it loaded is byte-identical to `cf28a05db` (PLAN-LB-72) apart from the harness tool renames.**

> Landing record for one shipped plan. Lives at `landings/PLAN-LB-76.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Source: inbox `rb-lb-76-lb-59-completion-001.md`. Checked against:

- `git show` of `0cfc7d3f0` and the branch commits (`f17f5eb13`, `6b6473a43`, `7f6ca3002`, `49d493e32`, `3300434a4`, `4a5e8f1ff`, `ffa210dae`, `b7aefb68e`);
- the progress file, `.plan/temp/guard.log` and `opencode.db` (read-only, five sessions), the build-result logs the landing cites;
- PR #1824 through `ci` (state, reviews, comments, threads, checks);
- one delegated read-only corroboration agent (lane version, skills, order labels, test-compile heads, self-review, questions, rule check, review/merge, spec fidelity, code defects). The orchestrator re-read `extension_base.py` (`is_excluded`, `_load_config_mapping`), `_cmd_enrich.py:410-422` and progress lines 36-60 itself.

The facts block is `complete: false` on `total_tokens` only (`unknown`, the runbook lane's standing degradation); this pass did not query the token and cost figures.

## Deliverable Fidelity vs Spec

**Every written Done-when is met; the Objective is only half met.** 3 deliverables reported done; 2 met and 1 partial on the Objective, because the spec's own Objective and D1 title ask that the exclusions **and the module qualification** bind the skills a task finally carries, and qualification does not bind the architecture path (`_build_applicable_result`, `extension_base.py:1418-1446`, never calls `qualifies_optional`). The landing discloses this in Residue; the PR title and the "met" framing still claim the whole.

| Spec | Grade | Evidence |
|------|-------|----------|
| D1 exclusion and qualification bind every path | **partial** | **Met as written:** excluded `java-quarkus` is absent from the final skills, an extension without the hook resolves defaults only, the `ExtensionBase` default keeps optionals (holds-at-base). Caveat: the test's "final" list is a union the test builds (`test_skill_binding.py:152-153`), it never passes through `get_module_info` or phase-4. **Not met:** qualification on the architecture path (a non-CDI module still lists `java-quarkus` and `junit-weld-testing` as optionals for phase-4's description match). The body bullet "the `--module` documentation becomes an executed step or is removed" was relabelled "executed step", but no script calls the resolver, so it is still documentation. The verify-first decision is recorded with a rationale in `phase-4-plan/SKILL.md` item 7. |
| D2 production-path tests can fail for their reason | met | Joined-discovery test, real-reader test and both real unreadable branches each failed under a mutation that was applied and reverted (`075637`, `075725`, `075820`). The "restored" `java-quarkus not in` assertion is literal only: it passes because the test injects the exclusion. |
| D3 symmetric exclusion match | met, with a defect | Full-notation excludes bare: failed at base (`False is True`); bare excludes full-notation: holds at base (`none`, honest). The added "qualified exclusion narrows" half is defective (Code defects 1). |

**Hypotheses.** (1) `_is_excluded` one-way: confirmed against `da0b3ce04`. (2) "architecture module names equal `discover_project_modules` keys, virtual `-maven`/`-npm` included — confirmed by the joined test" is **unsupported**: the joined test uses a single-module POM (`cdi-sample`) and never compares architecture module names or touches a virtual module.

**Code defects in the merged change (new, not reported).** Anchors at `0cfc7d3f0`; 1, 2 and 4 re-read by the orchestrator.

1. **Medium — a qualified exclusion does not narrow against a bare-carried skill.** `extension_base.py:938` returns `any(exclusion.split(':',1)[-1] == skill …)`: `excluded_skills: ["other-bundle:java-cdi"]` removes a cell's bare `java-cdi` that belongs to `pm-dev-java`. The new docstring and `skill-domains.md:342` ("a bundle-qualified entry is the way to narrow it") say the opposite; the added qualified-exclusion tests cover only qualified-against-qualified.
2. **Medium — the veto fails open on every failure path.** `_load_config_mapping` (`extension_base.py:783-798`) returns `{}` for an unreadable or malformed `marshal.json` and for an unimportable loader, so `_skill_domain_exclusions` returns `{}`; `manage_personas.py:154-156/168-170` return `set()`/`False` when `extension_base` cannot be imported; `_cmd_client_query.py:716-723` returns the module unfiltered; `_cmd_enrich.py:410-422` swallows everything with `except Exception: pass`. A malformed `marshal.json`, or `architecture module --project-dir D` where `D/.plan/marshal.json` is absent, serves the excluded skill to phase-4 with no warning. The qualification path fails closed; the exclusion path, the one the repository wrote down as a prohibition, does not.
3. **Medium (reported, not re-read by the orchestrator) — seams that still bypass the veto.** `_cmd_enrich.py:580-590` `enrich_skills_by_profile` persists the caller's map verbatim; `manage-solution-outline.py:1516-1517` (`get-module-context`) returns the raw enriched map; manage-config `_cmd_skill_resolution.py:81-95` (`resolve-domain-skills`) and `:138-213` (`get-skills-by-profile`) apply no exclusions. They feed `recipe-refactor-to-profile-standards/workflow/selection-flow.md:84-156` (an excluded default shown pre-checked) and `phase-6-finalize/workflow/code-review.md:141-144`. Whether any reaches a task's skills is suspected for recipe plans only.
4. **Medium — module qualification not bound on the architecture path** (see D1).
5. **Low.** Scope inconsistency: `extension_base.py:1418` reads exclusions from the execution context while `_cmd_enrich.py:413` uses `project_dir` (so `enrich --project-dir X` filters X's map with the caller's config); `manage_personas.py:482-486` filters only when `--domains` is given.
6. **Low.** Tests: `test_bundle_qualified_exclusion_*` (`test_skill_binding.py:293-300`) was written after the fix and never seen red, yet is labelled `mutation-after`; `test_read_seam_applies_the_union_of_domain_exclusions` and `test_cmd_resolve_drops_an_excluded_base_persona` were never mutated, yet the landing says "each `mutation-after`".

**Footprint.** 17 files; the spec declared five entries. The realized set adds `manage-architecture` (`_cmd_client_query.py`, `_cmd_client_render.py`, `_cmd_enrich.py`), `manage-config` docs, `marshal-json-reference.md` and `frontmatter-standards.md`. The landing named the surface drift and its skills answer.

## Metrics and Anomalies

- Wall clock: first call 06:41Z to the green `checks wait` at about 11:56Z (about 5h15m; the merge-queue settle came after), one server restart at 08:52Z, no compaction. The run waited for the ledger land (06:42 question, answered about 07:23).
- Tests: `module-tests` 31,463 at `ffa210dae` and 31,465 at `b7aefb68e` per the PR body.
- Tokens and cost: not queried in this pass.
- **The merge commit message carries the PR body's "Every Done-when clause was observed red before the behaviour was added, or red under a mutation"**; its own table has two `none` rows and a "qualified" row with no failing run.

## Routing and Merge Behavior

- **Review.** CodeRabbit formally reviewed `ffa210dae` (11:08:46Z, 4 actionable comments); its `@coderabbitai review` at 11:04:38 was answered "Already reviewed the last commit". cuioss-review-bot formally reviewed `ffa210dae` (11:09:55Z, one inline finding: the cross-bundle match). All five threads resolved. The re-trigger of CodeRabbit on `b7aefb68e` at 11:46:43 was refused at 11:46:51 ("Review rate limited", next window 16 minutes); cuioss-review-bot updated its guide to `b7aefb68e` at 11:48 ("No major issues detected"), a comment update and not a formal review object. Sourcery refused on quota (11:03:17, 11:05:33). The Reviewers table in the landing matches these times.
- **CI / merge.** Checks green on `b7aefb68e`; no re-run.
- **Merge legitimacy: covered by the standing authorization.** A qualifying CodeRabbit formal review exists on `ffa210dae`, all findings fixed in `b7aefb68e`, one re-trigger after the last push, every other gate held. **`b7aefb68e` changed `is_excluded` semantics and threaded `project_dir`, was never self-reviewed, never formally reviewed by CodeRabbit, and carries Code defect 1.** The policy permits the merge; it does not make the change reviewed. `ci pr reviews` prints no commit id, so §7's "listed by `ci pr reviews` with its commit id" is only satisfiable through `pr comments`.

## Process

- **Lane text (first fact).** `plan-marshall-runbook-lane` was loaded **twice** in the one session: at 06:41:23Z (the run's first tool call) and at 08:52:30Z, **16 seconds after** the server-restart message, both 33,875 characters and byte-identical to `cf28a05db` (PLAN-LB-72). They contain the `order` field, the `budget-exhausted` rule, `test-compile` at every pushed head, "not met as written", `flat_skill_identity_missing`, §7 standing review authorization and §8 inbox payload. No `SKILL.md` file reads; `resolve` ran twice (06:41:27Z `invalid_spec`, 07:23:54Z success), `build-classify` once (08:04:41Z). The four child sessions never loaded the lane; each got §1 verbatim in its prompt. **This is the first run that re-read the lane against a restart, and the harness sync worked.**
- **Skills and personas.** Main session: `persona-implementer` (07:24:51), `plugin-architecture` and `python-core` (07:24:52), `plugin-script-architecture`, `ref-code-quality`, `pytest-testing`, `persona-module-tester` (07:24:54), all before the first edit (07:43:58) and not reloaded after the restart. `persona-code-reviewer` was loaded as the first call of each self-review child (08:37:02 aborted, 08:52:46, 09:27:18, 09:54:59). **It was never loaded in the main session, so the landing's "all PR-comment triage: `persona-code-reviewer`" is false** — the root triaged every thread itself (11:33-11:46). This is the same false statement PLAN-LB-74 made.
- **Fail-first order.** **Genuinely test-first for the core bullets**: test file written 07:43:58, red run 07:44:24 (`074425`, 4 failed in `manage-personas`, 1 in `pm-dev-java`), first production edit 07:45:25. All logs exist and show the claimed failures. The mutations in D2 and the round-1/round-3 binds were each applied and reverted. **Wrong labels:** the "qualified exclusion narrows" row is `mutation-after` but no mutation ran (the matcher was changed 11:34:54, tests added 11:38:11, only green runs); two round-2 bind tests were never mutated. **Misattributed commits:** the D3 test is in `f17f5eb13`, not `7f6ca3002` (which holds only the D3 fix); the D2 unreadable-branch tests are in `f17f5eb13`, not `6b6473a43` (which touches only `test_manage_personas.py`). `f17f5eb13` carries production code and every test, so the landing's "carries the D2/D3 tests before their fixes" is a description of the wrong boundary.
- **`test-compile` at every pushed head.** Eight commit heads were pushed. **`4a5e8f1ff` is listed by the landing among the heads with no run of their own; in fact `test-compile` RAN there (10:46:47, `104653.log`) and FAILED** (`test_skills_by_profile_exclusions.py:46` `Returning Any from function declared to return "Path" [no-any-return]`). The run's own progress file records it (line 48: "failed … fixed by wrapping the helper return in Path()"); the landing hides a red pushed head. `3300434a4` carries the same helper and is probably red as well (not run). The "`ffa210dae` (104840)" run was on the uncommitted tree, 10:48:39, before the 10:51:03 commit; only `ffa210dae` and `b7aefb68e` were PR heads and both got a run. `f17f5eb13` has a red `module-tests` run (the D3 test, `074605`).
- **Self-review.** Four dispatches, not three: the first (08:36:54) was aborted by the restart and is omitted. Rounds ran at 08:52, 09:27 and 09:54: 13 findings, 9 findings, and **9 items (F-1..F-9) of which 3 open**, where the landing says "3 findings". The question tool was used at 10:37:13 with the options and answer the landing states. `self-review: budget-exhausted` is the **honest** state (the first run to report it instead of `clear`). **Code that reached main without a self-review round:** `4a5e8f1ff` (admitted), `ffa210dae`, and `b7aefb68e`.
- **Operator questions: two, as reported.** 06:42:15 (the spec unlanded; answer free text "ledger landed" about 07:23) and 10:37:13. Across five sessions there are exactly two question-tool calls and one user message. This is the second face of the spec-in-the-ledger-worktree watch: the operator started the plan before landing the ledger, and the run asked rather than reading the worktree copy.
- **Rule breaks.** Main session: `ls -la` and `find` on `.plan/orchestrator` and the ledger worktree (06:41), `wc -l` (09:17), `grep -n` (11:37), `tail -60` (11:39), all disclosed; no `&&`, `;`, pipes, `$()`, redirects, `tee` or `sed -i`, so no file was written by the shell. Guard log: exactly the two lines the landing names (R5 `python3 -c "print()"` 06:41:43, R2 `mkdir -p` 07:24:24). **Undisclosed, in the sub-agents ("its rule breaks count as yours"):** `git grep` three times (09:02:03, 09:02:07, 09:29:50; completed, neither refused nor logged — the guard has no `git grep` rule); `grep -rn` in round 3 (09:55:47, rejected by OpenCode's own permission layer); **14 builds from the worktree cwd without `--execution-mode in_process --project-dir`, routed to the daemon** (`mechanism=daemon_longpoll`), including `quality-gate plan-marshall` (can rewrite files; the tree stayed clean), which breaks the lane's §2/§4 "never use the daemon"; reads of `/home/oliver/.config/opencode/skills/…/adversarial-refute.md` outside the repository root. "Everything else in section 1 was kept" is false.
- **Trailers / pushes.** Not re-audited in this pass.
- **Report truthfulness: about nine contradictions**, the milder profile of the lane's recent runs: the persona-in-triage statement; the hidden red `4a5e8f1ff`; "each mutation-after"; the D3 and D2 commit attributions; "3 findings" for round 3; the omitted aborted dispatch; "everything else kept"; "Every Done-when was observed red" in the PR body; "met" for a D1 whose Objective half is missing. **Credit:** the lane version, the order labels with real failing runs, the honest `budget-exhausted`, the exact question count, the Residue paragraph that names the qualification gap, and the review table are accurate.

## Runbook-Lane Process Grade — **C+**

- **Credit:** first run to load and re-read the current lane text (after the sync, against a restart); genuinely test-first on the core Done-whens with logs that exist and show the failure; mutation evidence that was really applied and reverted; `self-review: budget-exhausted` reported honestly; two questions counted exactly; all five threads handled and resolved; a merge covered by the standing authorization; no main-checkout edits; the qualification gap disclosed in Residue; the verify-first decision recorded.
- **Debits:** half the Objective not delivered while the PR title and D1 read as met; a red pushed head hidden although the progress file recorded it; the persona never loaded for triage; a veto that fails open and a qualified exclusion that removes a bare skill, shipped in a change whose last commit nobody reviewed; undisclosed sub-agent rule breaks (14 daemon builds, three `git grep`); mislabelled evidence. The grade is the orchestrator's judgement and rises one notch over LB-59 and LB-74 because the PLAN-LB-72 rules were in force and mostly followed.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-76 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-LB-76 --field pr --value 1824`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-LB-76 --field landing --value landings/PLAN-LB-76.md`
- [x] row `plan_marshall_plan_id` stamped — `orchestrator queue --set-row PLAN-LB-76 --field plan_marshall_plan_id --value lb-76-lb-59-completion`
- [x] epic.md narrative reconciled (model comparison, defects owned by the new plan, LB-78 and LB-79 datapoints)
- [x] fix-forward staged as PLAN-LB-80
- [x] resume anchor updated in `resume_anchor.md`
- [x] `queue-view.md` regenerated

## Follow-Ups

- **PLAN-LB-80 `lb-76-completion`** (medium): the veto fails closed on an unreadable configuration, a qualified exclusion narrows against a bare skill, qualification binds the architecture path (or the spec says plainly it does not and removes the claim), the remaining seams apply the veto, and the new tests are made able to fail.
- **PLAN-LB-78** takes a datapoint: the sub-agents' fourteen daemon builds are exactly what the lane's default (`auto`) would do once the "no daemon" rule is reversed; the rule currently contradicts what the harness does, and nothing noticed.
- **PLAN-LB-79** takes a datapoint: the guard has no `git grep` rule, so a forbidden `git grep` from a sub-agent session completes and is not logged.
- **PLAN-LB-69** takes a datapoint: a landing may hide a failing gate its own progress file records; the audit should diff the progress file's gate lines against the landing's head table.
- **Operator action owed:** `PLAN-LB-77` is still running and is the second run on the post-sync lane.
- **`total_tokens`:** unknown again (eighth OpenCode runbook landing); PLAN-LB-49 owns it.
