envelope_version=1
sender_type=plan
sender_id=rb-lb-120-merge-and-push-gate-truth-fixes
epic=live-blockers
kind=landing
created=2026-11-06T23:57:44Z

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-120-merge-and-push-gate-truth-fixes
epic=live-blockers
pr=#1923
merge_state=merged
cleanup_owed=false
deliverables_total=4
deliverables_done=4
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash/high
effort=high
plugin_version=0.1
executor_version=0.1.2062
steps=setup:done,implement:done,build-gate:done,self-review:budget-exhausted,pr:done,reviews:done,merge:done
step.sonar-roundtrip.open_issue_count=n/a
step.sonar-roundtrip.open_issue_rules=n/a
```

guard: present

## 1. Deliverables

Merged as PR #1923, merge commit `b4430a0a6718b6341913b5b413fa2e9931ccf2a3`. All four deliverables are fully met: every Done-when holds as written.

**D1 — the merge gate separates "declares no head-dependence" from "could not be found"** (met)
- absent-from-population stale record refused with the fallback reason — order **test-first**; test `test_a_stale_record_for_a_step_the_discovery_does_not_return_is_refused`; failing run at base `1d2b559fd` (job log `7f10428f5cf347f69723cefcc98d4783`, 3 failures incl. the unreadable-document admission); passed at `ca5fe51ce`. Commit `ca5fe51ce`.
- same record for a discovered undeclared step still listed and admitted (control) — order **test-first**; `test_a_discovered_undeclared_step_is_still_listed_and_admitted`. Commit `ca5fe51ce`.
- project-tier and bundle-tier declared steps pinned through the production reader — order **test-first**; `test_a_bundle_tier_and_a_project_tier_step_resolve_through_the_production_reader` (`automatic-review`, `project:finalize-step-plugin-doctor`). Commit `ca5fe51ce` / `b6f673465`.
- unreadable declared document refused, not listed — order **test-first**; `test_a_declared_document_that_cannot_be_read_is_refused_not_listed`. Commit `ca5fe51ce`.
- `record-merge` records a fact for an unconsulted stamp or a fallback — order **test-first**; `test_record_merge_carries_what_the_head_binding_did_not_validate` + `test_the_head_binding_facts_are_declared_by_the_step_record_contract`. Commit `cd2ff7d45` / `b6f673465`.

**D2 — the push gate does not turn an unreadable build row into a pass** (met)
- whole-tree change + `verify plan-marshall --format json` is not an `UNDETERMINED` pass — order **mutation-after**; `test_a_whole_tree_change_is_not_certified_by_an_unreadable_row`, `test_an_unreadable_row_blocks_a_whole_tree_change_and_names_the_inability`; failing output from mutating the committed fix at `c0e8b00f1` (job log `335407517b274b5bb143cdbbb82a0e7a`, 4 failures); restored clean, green at `c0e8b00f1`. Commit `c0e8b00f1`.
- documented `verify -Ppre-commit -pl core-api` read as `core-api` **or** an inability decided at outline — the outline decision is recorded in the run's progress file (`outline D2`): the executor's flags cannot be told from the payload's, so the inability branch is taken. Order **mutation-after**; `test_the_documented_profile_and_module_row_is_unreadable_and_blocks_a_whole_tree_change`. Commit `c0e8b00f1`.
- each extra-flag shape the documents show is pinned — order **mutation-after**; `test_parse_row_scope_never_reads_an_unreadable_row_as_whole_tree` now carries `verify --format json`, `verify --mode errors --format json`, `verify -Ppre-commit -pl core-api`, `module-tests -k foo`. Commit `bbdacaf1c`.
- each Maven resolver shape judged through `cross_check_candidates` — order **mutation-after**; `test_each_resolved_maven_row_shape_gets_its_own_verdict` (`verify -pl X -am` → NARROW/refused; `package -pl X -am` and `test -pl X -am` → UNDETERMINED/pass, recorded as residue because both canonicals are outside the coverage vocabulary). Commit `c0e8b00f1`.
- control `verify` with no flag still whole-tree and adequate — order **mutation-after**; `test_the_control_row_with_no_extra_flag_is_still_whole_tree_and_adequate`. Commit `c0e8b00f1`.
- the two comments that called an unreadable row "fail-closed" now state the gate effect — `_freshness_crosscheck.py` `parse_row_scope` docstring and the test parametrization comment. Commit `c0e8b00f1`.

**D3 — the gate's tests, bounds and fault reports state what they pin** (met)
- abbreviated waiver uses `HEAD_MERGED[:7]` with a direct predicate assertion — order **mutation-after**; `test_an_abbreviated_waiver_head_is_void_at_the_candidates_own_prefix`; failing output from mutating `_is_full_sha` at `5652f2f97` (job log `f4461632b4974e4d9a8e09eeddf3543a`). Commit `5652f2f97`.
- hand-listed count removed — `test_the_participation_refusal_publishes_the_labels_the_grant_accepts` (list equality kept). Commit `d435144d0`.
- classifier error / timeout / unknown verdict each shown refusing — order **mutation-after**; `test_every_non_preserved_classifier_answer_refuses`; failing output from mutating the gate's admission at `bbdacaf1c` (job log `c48b5c0e808341439c93ed28b7096a99`, `no-verdict` + `unknown-verdict` red). Commits `ca5fe51ce` / `bbdacaf1c`.
- import fault named in the refusal; status-read fault named in the evidence — order **test-first**; `test_an_unimportable_override_label_source_is_named_in_the_refusal`, `test_an_unreadable_status_names_the_fault_in_the_evidence`. Commit `d435144d0`.
- discovery once per merge, bounded reads, classifier calls bounded — order **test-first**; `test_the_gate_discovers_the_population_once_per_merge`, `test_the_classifier_runs_only_for_the_records_the_dispatcher_would_retry`, `test_the_classifier_call_carries_the_modules_finite_bound`. Commits `ca5fe51ce` / `d435144d0`.

**D4 — the documents state what the gate does** (met)
- each cited line's wording corrected — order **none** (wording only, no failing output captured): `branch-cleanup.md` head-binding paragraph now names the three underivable cases and the two dispatcher exceptions; the `PLAN-LB-26` and `PLAN-LB-107 D1–D5` wording is gone from the four test files and the two cited source locations; `manage-status/SKILL.md` § "Re-fire waiver" no longer claims "exactly two readers" and points at the enumerating test. Commit `6a6fb2213`.
- a test enumerates the waiver readers — order **mutation-after**; `test_refire_waiver_readers.py`; failing output from adding an unclassified mention at `6a6fb2213` (job log `55440ec5607b49abbb4a1ed8f0de3240`). Commits `6a6fb2213` / `b6f673465`.

Per-head test runs: `module-tests` green at `93340228b` (32951 tests, job `c467963c3ccf4c5abf6cbf9b993db775`), at `bbdacaf1c` (32955, job `bbd537aaa48f4d2a8c851856915dfc09`), at `b6f673465` (32956, job `f96decc8318a404eadb41d062251da34`) and at the merge head `3312fedcc` (32992, job `eb18f2325c034600a5ee9e250f357c91`). `verify` green at each of those heads (jobs `891462f40d964ec7bf2dc79f172e934c`, `09f1d4cbad42439eb86362db35ccb473`, `387d7ab0968247f2b3a0649fad82865a`, `43fb54aea39a4363b5265acd6ce13682`).

## 2. Personas and skills

No spec deliverable declares `Skills:` or `Persona:` lines — `skills: none named`.

Personas applied as standards: `persona-implementer` and `persona-module-tester` for the production and test work; `persona-code-reviewer` for the self-review rounds and the CodeRabbit triage. No skill was added for surface drift: every changed file is inside the spec's Expected Surface except the new `test/plan-marshall/manage-status/test_refire_waiver_readers.py`, which is the mechanism D4's third bullet asks for.

## 3. Hypotheses

- **Refuted:** a build row records the executor's own flags apart from the payload's, or keeps the column quoting. It does not — `_ledger_core` joins argv unquoted (three+ real `kind=build` rows read); D2 therefore takes the "cannot be told apart" branch.
- **Confirmed and fixed:** `_read_frontmatter_fields` returned `{}` for an unreadable document (`extension_discovery.py:1018-1025` pre-fix); the push gate let an `UNDETERMINED` verdict pass (`_cmd_pre_commit_verify_freshness.py:501-565`); `verdict_currency` reads an absent step as `step_doc_unresolved` (`verdict_currency.py:362`), which is why the refused branch names the fallback and the classifier agrees; a stale record can reach the gate for a step discovery does not return (`pre_merge_gate.py:445-451` pre-fix + `_cmd_mark_step.py:240`); the dispatcher re-fires a declared `done` record with no head and retries `failed`/`loop_back` at the candidate head (`phase-6-finalize/SKILL.md:612-614`); `record-merge` accepts arbitrary fact keys (`pre_merge_gate.py:1299-1411`).
- **Recorded as residue:** Maven `test` and `package` are outside the coverage vocabulary (`_build_examined.py:97-148`), so a narrow Maven row of either stays an inability that passes. `required_coverage` was not changed.

## 4. Findings

**Self-review round 1** (10 findings, all dispositioned in `bbdacaf1c` / a second mutation run): applied 1, 2, 3, 4, 6, 7, 8, 9; finding 5 (classifier evidence) dispositioned with a second mutation (`c48b5c0e…`); finding 10 (PR-body obligations) discharged in the PR body. Nothing was left open at the end of round 1.

**Self-review round 2** was dispatched AFTER the merge and found 10 more items — see § 9. That is the run's process defect: the confirming round should have run before the PR. `self-review` is therefore **not** `clear`.

**CodeRabbit round 1** (on `bbdacaf1c`, 5 inline comments + 2 nitpicks): 4 fixed (`b6f673465`), 1 answered with a reason and accepted by the bot in-thread, both nitpicks applied. All five threads resolved. CodeRabbit itself stamped four of them "Addressed in commit b6f6734".

**CodeRabbit re-triggers:** refused on quota at 20:33 (on `b6f673465`) and at 22:52 (on the merge head `3312fedcc`).

## 5. Reviewers

| Reviewer | Required | Outcome | Head reviewed | History |
|---|---|---|---|---|
| coderabbit (`quota_limited`) | yes | reviewed `bbdacaf1c`; refused on quota for `b6f673465` and `3312fedcc` | `bbdacaf1c`, marker `kind=reviewed` on the summary comment | trigger 19:42 → review 19:49; re-trigger 20:33 → "Review rate limited" (next +8 min); re-trigger 22:51 → "Review rate limited" (next +32 min) |
| sourcery (`quota_limited`, optional) | no | refused on quota | none | trigger 19:42 → "used your own review budget … request another review in 5 days" |

**Standing review authorization** (applies to coderabbit only, which the resolve result marks `quota_limited`): (1) a qualifying review exists on `bbdacaf1c`, one of this PR's heads, with the `final_review_risk_coverage` marker carrying `kind=reviewed` and `sourceCommitId == coveredCommitId == bbdacaf1c`; (2) every finding from that review is handled — four fixed in `b6f673465` and confirmed "Addressed" by the reviewer, one answered and explicitly accepted ("I accept the decision to defer candidate-tree discovery"), both nitpicks applied, and all five threads resolved; (3) it was re-triggered once after the last push and the refusal is recorded; (4) every other gate condition holds on the merge head `3312fedcc` — CI green, `quality-gate`/`module-tests`/`verify` green, every comment handled, Sonar `not_configured`.

## 6. Operator questions

None asked. No rule had to bend, no reviewer had to be skipped, and the merge gate's reviewer condition was satisfied by the standing authorization above (the operator's standing settlement for a CodeRabbit quota refusal alongside a valid review). No free-text operator messages were exchanged during the run.

## 7. Rule check

Spec read: `spec_source: ledger_worktree` (the shared ledger worktree's copy), no `spec_differ`. Executor-skew: `not_applicable` — this is a source checkout, where the executor maps the checkout's own scripts; recorded, never asked about.

Rules I broke (counted by the run's own actions, not only by the guard):
- **Shell file operations, four calls** — two `ls` of `.plan/local/worktrees/_orchestrator/.plan/orchestrator` and `.../plans`, one `wc -l` over three source files, and one `tail -n 40 .plan/temp/guard.log`. Each was a read-class operation the rules reserve for the file tools. No content was changed by any of them.
- **One guard refusal** — `git show … | head -c 200` was refused by the guard's shell-chaining rule (R1). The information was obtained instead by reading the file.

Everything else kept: every script call went through `python3 .plan/execute-script.py …` with the shell in the main checkout; every build went through the resolved `build` commands; every CI action through `plan-marshall:tools-integration-ci:ci`; no `sleep`, no inline Python, no direct `pytest`/`ruff`/`mypy`, no direct `gh`/`glab`; nothing under `.plan/` was written except `.plan/temp/`, the `ci-bodies` slots and the inbox message; the main checkout was never moved by hand (cleanup step 3 did it); no `git stash`/`restore`/`checkout --`/`rebase`/force-push, and no staging of everything at once.

Restarts: none. Killed sub-agents: none. Re-dispatches: the self-review sub-agent was dispatched twice (rounds 1 and 2); every mutation used to capture evidence was restored to a clean working tree before the next step (verified with `git status --porcelain` each time).

## 8. Build server

Setup preflight: `ready` (registered, version 1); worktree executor `present`, `build-routing` answered `auto`.

Every build ran routed: `mechanism=daemon_longpoll`, `serialization=daemon-scheduled`. No build fell back in-process, and no launch-fault retry was needed.

- `quality-gate`: eleven invocations. Four failed on lint/type/format/plugin-doctor findings that were then fixed (not routing faults). One hit the daemon's supervisory bound (`timeout_used_seconds: 330`, `timeout_source: floor`) and was re-run with `--timeout 900`, which succeeded. Two invocations returned the live `running` status at the client's bound and were re-attached with `build_server wait` on `c8766fd63fc841bdacf29fad5f6ef359` and `61d1709bedff44138dd9a4367169b03d`, both of which then succeeded.
- `module-tests`: four whole-tree runs (32951 / 32955 / 32956 / 32992 tests) and thirteen scoped runs; all green at their final state.
- `verify`: four runs (32951 / 32955 / 32956 / 32992 tests) with compile+lint+test, all green.
- `runtime_stamp_reason`: absent.

## 9. Residue

**Open self-review findings from round 2 (dispatched after the merge, so this run cannot fix them):**
1. `manage-tasks/SKILL.md:616` — the new stale-reason table row is outdented by two spaces and would render outside its table. Same class as the split-row defect round 1 caught.
2. `manage-tasks/SKILL.md:477-482` — the new token sits in the `scope_cross_check_reason` table, but it is only a `reason`/`joint_reason`; the coverage dimension keeps `build_scope_unreadable`.
3. `manage-tasks/SKILL.md:583-587` — the `status: stale` cause enumeration does not name the whole-tree-unreadable route.
4. `test_freshness_notation_crosscheck.py:620-622` — the section banner still says "Every scope inability passes" over the now-refusing case.
5. `test_lb55_merge_head_binding.py:83-88,292` — two docstrings still describe the pre-change commit as "HEAD".
6. `branch-cleanup.md:845` — the participation refusal's `override_options[]` is stated unconditionally; the new `override_options_unavailable` degradation is undocumented there.
7. `_cmd_pre_commit_verify_freshness.py:125-127` and `manage-tasks/SKILL.md:593-596` — "`missing_analyses` … is what to run" is wrong for the new route, which deliberately returns an empty list.
8. Pre-existing "used to"/"historically" wording in `_freshness_crosscheck.py:174-180`, `_cmd_pre_commit_verify_freshness.py:167-169`, `pre_merge_gate.py:5,1489`, `_cmd_mark_step.py:433-440` — outside the plan's enumerated sites.
9. Nit: `extension_discovery.py:1032-1034` docstring contrasts two labels that read as synonyms.
10. Nit: `test_freshness_notation_crosscheck.py:635-636` — a test name split across a line break.

**Other residue:**
- Maven `test`/`package` remain outside the coverage vocabulary, so a narrow Maven row of either stays an inability that passes; `required_coverage` untouched.
- The finalize-step population is cwd-anchored by the shared ADR-002 rule, so a merge that runs from a checkout other than `project_dir` can miss a project-tier step and take the fail-closed fallback (answered in-thread on PR #1923; CodeRabbit accepted the deferral and offered to file an issue).
- `pre_merge_gate.py` still carries two pre-existing "used to …" sentences.
- Owed outside this plan, operator-run: a harness sync after merge (`/sync-harnesses`) — no verb or flag was added, so no executor regeneration is owed for the change itself, though the executor version moved during the run (`0.1.2041` → `0.1.2062`, read at landing).
