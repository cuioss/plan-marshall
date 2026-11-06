envelope_version=1
sender_type=plan
sender_id=rb-lb-107-finalize-gate-waiver-and-step-truth
epic=live-blockers
kind=landing
created=2026-11-06T13:39:30Z

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-107-finalize-gate-waiver-and-step-truth
epic=live-blockers
pr=#1920
merge_state=merged
cleanup_owed=false
deliverables_total=5
deliverables_done=5
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash/high
effort=high
plugin_version=0.1
executor_version=0.1.2062
steps=setup:done,implement:done,build-gate:done,self-review:clear,pr:done,reviews:done,merge:done
step.sonar-roundtrip.open_issue_count=n/a
step.sonar-roundtrip.open_issue_rules=n/a
```

guard: present (`resolve` reported `guard: present` and `guard_log: .plan/temp/guard.log`; no guard-log file exists at that path after the worktree cleanup, so the rule-check below is taken from the run's own actions and is labelled as such).

# PLAN-LB-107 — finalize gate waiver and step truth

Merged as `1d2b559fd1a3f56a1a755788d7e144c4914dbd7f` (PR #1920). The merge gate now reads the re-entry facts the finalize dispatcher reads; the freshness check reads a flag scope as scope.

## 1. Deliverables

**D1 — the merge gate honours the operator's re-fire waiver at the candidate head — met.**
- (a) `test_a_waiver_at_the_candidate_head_is_honoured_and_named_in_the_payload`: met; order `mutation-after`; the waiver row was disabled on the committed fix and the test reported `merge_candidate_not_gated` (job log `7ab0a66c40154033b1b310cd95914a7b`); commit `335358313`.
- (b) matched control `test_a_waiver_at_any_other_head_is_void_and_the_step_is_refused`: met; order `none`; commit `335358313`.
- (c) `test_a_malformed_waiver_is_void_and_the_step_is_refused` (no head / abbreviated / non-dict / null head): met; order `none`; commit `335358313`.
- (d) `test_a_waiver_on_one_step_does_not_admit_a_second_stale_step`: met; order `none`; commit `335358313`.
- Disposition wording + `manage-status` reader sentence: `branch-cleanup.md` / `manage-status/SKILL.md`, commit `335358313`, refined in `b05cfbe59` and `c5878e95d`.

**D2 — head-dependence from the same source as the dispatcher — met.**
- (a) `test_an_undeclared_step_with_a_stale_stamp_is_listed_not_refused`: met; order `mutation-after`; the declared-fact branch was disabled and the test reported `merge_candidate_not_gated` (job log `a1aba2527ae143a08868ea2f95c67359`); commit `335358313`.
- (b) matched control `test_a_declared_step_with_the_same_stale_stamp_refuses`: met; order `none`.
- (c) `test_an_underivable_declaration_falls_back_to_field_presence_and_says_so`: met; order `none`.
- (d) `test_the_classifier_decides_a_stale_declared_step` + `test_the_production_classifier_is_reached_through_the_executor_seam` (`verdict_currency classify … --live-head`): met; order `none`.
- Anti-vacuity: `test_the_production_discovery_path_resolves_the_declared_fact` and `test_the_undeclared_control_step_is_discovered_and_declares_no_fact`.
- **Defect the review found and this plan fixed**: the status read went through the executor's TOON rendering, which splits a `project:step:` line at its first colon, so a namespaced record arrived as a scalar and was skipped. `_read_plan_status` now uses manage-status' JSON resolver. `test_a_project_namespaced_step_record_survives_the_status_read` and `test_a_namespaced_declared_step_is_judged_not_silently_skipped` were red before the change (job log `84e6eaef9ac34010b2a07d281e9ab41e`) and pass at `c50854071`.
- Commits: `335358313`, `b05cfbe59`, `1a61d6826`, `3085d5dd8`, `fab8940ea`, `c50854071`.

**D3 — the operator prompt is built from the labels the grant accepts — met.**
- (a) `test_the_participation_refusal_publishes_the_labels_the_grant_accepts`: met; order `test-first`; at HEAD `29f3b5417` it failed with `KeyError: 'override_options'` (job log `be86483bea2345ccb88e941b769ee621`); commit `335358313`.
- (b) `test_every_override_label_the_documents_name_is_one_the_grant_accepts` (reads `phase-6-finalize/SKILL.md`, never edits it; also checks the prompt `label:` declarations against the grant values): met; order `none`.
- Doc instruction in the ask arm and the structural prompt; commit `335358313`, refined in `b05cfbe59`.

**D4 — a build row is whole-tree only when its recorded scope is whole-tree — met.**
- (a) `test_a_scope_bearing_flag_narrows_the_row_and_is_refused_for_a_whole_tree_change`: met; order `test-first`; at HEAD the scope parsed as `()` instead of `('mod-a',)` (job log `b1d6e39e4c554d18850b5d4176f6d013`); commit `77c6826f5`.
- (b) `test_an_unknown_flag_contributes_no_coverage_and_is_never_labelled_whole_tree`: met; order `test-first`; at HEAD the unknown flag read as a whole-tree `RowScope` (same job log); commit `77c6826f5`.
- (c) matched control `test_the_matched_control_row_with_no_scope_is_still_whole_tree_and_adequate`: met; order `none`.
- PR evidence recorded: the `reactor-test-artifact-project` consumer resolves to `python3 .plan/execute-script.py plan-marshall:build-maven:maven run --command-args "package -pl consumer -am"`; the scope sits inside `--command-args` as the `-pl consumer` value (`_maven_cmd_discover.py` L917, L940-943; fixture assertions `test_discover_modules.py` L690, `test_derive_verification.py` L711-712).
- Commits: `77c6826f5`, `bc80911b8`, `246780e84`, `68afe7605` (CodeRabbit fixes).

**D5 — every producer `ci-verify.md` names is one `verification-feedback` accepts — met.**
- `test_every_producer_the_ci_verify_doc_names_is_accepted` + `test_a_mutated_copy_naming_an_unaccepted_producer_turns_the_guard_red`: met; order `mutation-after` (the mutated copy drives the guard's own assertion red; both `producers: [..]` and `producer=..` shapes, later widened to the spaced and multi-line forms); green at HEAD by construction (the shipped doc names only `ci-verify`).
- Commits: `0d4bd9ac8`, `fd58e49cb`, `68afe7605`.

**Per-head test runs (pushed heads).** `module-tests` green at `fab8940ea` (job `9c5e5ebe25de4a2dbbf8c446a5565924`, 32 779 passed / 11 skipped), at `68afe7605` (job `b6e34ce7…`), at `226417602` (merge commit; job `b2cc3f53…`), and at `c50854071` (job `b757fde0…`). `quality-gate` green on each of those heads (last: job `e7b04771`).

## 2. Personas and skills

- Production code (D1–D4 scripts): `persona-implementer`.
- Unit and module tests (every test file): `persona-module-tester`.
- Documentation (`branch-cleanup.md`, `manage-status/SKILL.md`, `manage-tasks/SKILL.md`): `persona-documenter`.
- Every self-review round and every PR-comment triage: `persona-code-reviewer`.
- Per deliverable: `skills: none named` (the spec declares no `Skills:`/`Persona:` lines). `skills added: none` — no deliverable touched a module outside the Expected Surface; `manage-tasks/SKILL.md` is a doc-consistency edit on the same rule and is recorded in the PR body.

## 3. Hypotheses

- **Maven scopes a module inside `--command-args` with `-pl` — confirmed.** `_maven_cmd_discover.py` L917 (`-pl {relative_path} -am`), L940-943 (package/test ladders). Fixture-resolved consumer: `package -pl consumer -am`.
- **The `whole-tree` label is rendered from empty scope tokens — confirmed in substance, corrected in location.** `row_scopes` renders `canonical + scope`; the literal `whole-tree` comes from `_contributing_row` in `_cmd_pre_commit_verify_freshness.py`, which needed no change.
- **No shipped finalize step declares `verdict_inputs`, so the `preserved` leg is test-only — confirmed** (`verdict_currency.py` requires a resolved non-empty declaration, so a real advance returns `invalidated`).
- **`pre_merge_gate.py` can reach `_derive_head_dependence` and `verdict_currency classify` through its existing seams — confirmed**; the discovery import is in-function and the classifier goes through `_run_verb`.
- **`manage-status/SKILL.md` § Re-fire waiver names only the dispatcher — confirmed before the edit**; one sentence now names the merge gate too.

## 4. Findings and dispositions

- Self-review round 1: 13 findings. Fixed F1 (canonical key), F2 (payload documented + fact wired), F5 (indent), F6 (prompt-label sweep), F7 (real red-at-HEAD cases), F8 (candidate-head ordering), F9 (reason wording), F10 (empty scope), F11 (shared SHA predicate), F12 (guard-driven mutation), F13 (surface recorded); F3 (real Maven row unreadable) fixed in round 2 with the `-am` neutral flag; F4 recorded as the spec-mandated blast radius.
- Self-review round 2: N1–N11. Fixed N1 (docstring precision), N3 (fact wiring), N5 (grounded flags), N6 (guarded derivation), N7 (shared key), N8 (discovery presence), N10 (wording), N11 (lazy import); N2/N4/N9 recorded in the PR body.
- Self-review round 3: 3 findings, all fixed (fact wiring on both record blocks + union + table row, module docstring flags, unused-import collision). Open: none.
- CI: green on every head after the first (`c5878e95d` verify hit the daemon's supervisory bound; the split form was green). One module-tests flake (`test_archive_reason_cli_round_trip_persists_to_archive`, a 30 s subprocess timeout under parallel load) passed in isolation and in the full re-run.
- CodeRabbit review on `fab8940ea`: 2 minor inline findings (neutral flag without scope; deferred import on the non-authorizable path) — both fixed in `68afe7605`, replied to, threads resolved; 1 nitpick (producer regex forms) — addressed by widening the sweep and its mutation cases.
- CodeRabbit review on `226417602`: 1 major outside-diff finding (namespaced step keys lost in the TOON status read) — **confirmed real** and fixed in `c50854071` with two red-then-green tests; 1 trivial note on the spaced-assignment sample — fixed. Disposition posted on the PR.
- No unhandled outside-diff finding and no unresolved review thread remains.

## 5. Reviewers

- **coderabbit** (required, quota-limited): reviewed `fab8940ea` at 2026-11-06T10:59:18Z (2 findings) and `226417602` at 12:12:48Z (1 major, 1 trivial). All findings handled; both threads resolved. Re-triggered after every push; refused on quota at 09:02Z, 11:25:54Z and 12:57:26Z (the last one after the `c50854071` push). **Standing review authorization applied**: a qualifying review exists on a PR head (`226417602`, `coveredCommitId` = that head, `kind=reviewed`), every finding from it is fixed in a pushed commit, it was re-triggered once after the last push with the refusal recorded, and every other gate condition holds on the merged head.
- **sourcery** (optional, non-gating): refused on a 5-day budget at 09:02Z; not re-triggered.

## 6. Operator questions

- None asked via the question tool. One free-text operator message arrived: "retry" after an interruption — it asked to continue the run, and nothing was taken from it beyond resuming.

## 7. Rule check

- `executor-skew` verdict: `not_applicable` (source checkout) — answered, recorded, never asked about.
- Spec read: `spec_source: ledger_worktree`; no `spec_differ` marker.
- No shell file operations were issued (no `ls`/`cat`/`grep`/`find`/`head`/`sed`); every script went through `python3 .plan/execute-script.py`, every build through the resolved `build` commands, every CI action through `ci`. One `date -u` and git plumbing (`status`, `fetch`, `merge`, `push`, `rev-list`, `rev-parse`, `worktree list/remove`, `add`, `commit`) were used as the lane allows.
- One argv mistake: `architecture search --project-dir .` was issued with the router flag after the verb; the executor refused it with `misplaced_router_flag` and named the correct ordering. Re-issued correctly; no source change.
- The first `worktree-create` call exceeded the 120 s shell default and was retried; the verb answered `worktree_exists` with `executor_in_worktree: present`, and the run continued on that worktree.
- No routed build was backgrounded, and no two routed builds ran concurrently from one worktree. Build-server counts in section 8.
- The guard's audit log could not be read (the resolved path holds no file after cleanup), so the guard-refusal count below is taken from the run's own actions: **0 guard refusals** observed; 1 executor surface rejection (the misplaced flag above).

## 8. Build server

- Setup preflight: `ready`.
- Per-mechanism build count: `daemon_longpoll` for every build (no `in_process_fallback`); 36 build jobs submitted.
- Fallbacks/retries: one supervisory-bound expiry on `verify` at `c5878e95d` (`timeout_used_seconds: 1185`, `timeout_source: learned`) — continued with the split form rather than re-submitting the same bound; one module-tests failure that was a load-induced 30 s subprocess timeout (re-ran the failing test in isolation: green; full re-run: green). No launch-fault retries, no `killed` job.
- `runtime_stamp_reason`: absent (the runtime stamp resolved cleanly).

## 9. Residue

- The coverage dimension's canonical vocabulary does not map Maven's `test`/`package` goals, so those rows reach `canonical_outside_vocabulary` (an inability) before scope is judged. Pre-existing; the plan's standing constraint forbids changing `required_coverage`, so it is left as epic residue.
- A trailing executor flag (`--plan-id`, `--timeout`, `--format`, `--mode`) after `--command-args` makes a row unreadable, exactly as D4's rule requires; such rows degrade to `build_scope_unreadable` (which passes with its reason recorded, never with a whole-tree credit). Recorded in the PR body.
- `-am` / `--also-make` is the one place the implementation reads "any other flag" more narrowly than the wording: a known non-narrowing companion is ignored (the `-pl` value beside it still supplies the scope), because the resolved Maven module executable the plan asks this PR to record always carries it. Recorded in the PR body.
- `manage-tasks/SKILL.md` is edited though the plan's Expected Surface names only the script and the test; it is the reader's contract for the rule this plan changes. Recorded in the PR body.
