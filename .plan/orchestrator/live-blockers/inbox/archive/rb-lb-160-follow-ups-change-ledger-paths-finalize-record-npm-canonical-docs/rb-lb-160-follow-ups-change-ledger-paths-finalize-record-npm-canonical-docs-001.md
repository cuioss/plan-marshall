envelope_version=1
sender_type=plan
sender_id=rb-lb-160-follow-ups-change-ledger-paths-finalize-record-npm-canonical-docs
epic=live-blockers
kind=landing
created=2026-11-18T00:23:47Z

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-160-follow-ups-change-ledger-paths-finalize-record-npm-canonical-docs
epic=live-blockers
pr=#2012
merge_state=merged
cleanup_owed=false
deliverables_total=6
deliverables_done=6
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash/high
effort=high
plugin_version=0.1
executor_version=0.1.2152
steps=setup:done,implement:done,build-gate:done,self-review:clear,pr:done,reviews:done,merge:done
unresolved_review_threads=0
review_body_findings_total=1
review_body_findings_handled=1
sonar_open_new_issues=n/a
step.sonar-roundtrip.open_issue_rules=n/a
```

guard: present

## 1. Deliverables

Merge commit `b296b47`; six delivery commits `05880a1`, `c05c3d7`, `36c06f6`, `e21c474`, `369af58`, `686094a`, three review-driven commits `4b65f01`, `fa60436`, `68efebb`, then the base merge `107928a`.

- **D1 — met.** Statements narrowed in `cwd-policy.md`, `marketplace_paths.py` (module docstring, section header, resolver docstring) and `doc/adr/002-…adoc`. Order `none` (documentation; every claim checked against `resolve_plan_context` / `_resolve_worktree_face` / `cwd_checkout_root`, and the hypothesis below). Commit `05880a1`, extended by `4b65f01`, `fa60436`.
- **D2 — met.** `test_a_merge_commit_records_both_paths_of_a_renamed_file` — order `test-first`; failing run at base `6b9a879` with the tests uncommitted, output identifier `plan-marshall/python-2026-11-17-194004.log` (`['src/new_name.py']` only); passed at `686094a`. Commit `c05c3d7`.
- **D3 — met.** `test_append_change_reads_a_nul_separated_path_file_losslessly`, `test_append_change_comma_form_still_stores_what_it_stored`, `test_append_change_refuses_both_path_inputs` — order `test-first`; same failing run (`unrecognized arguments: --changed-paths-file`); passed at `686094a`. Shape chosen: a file of NUL-separated paths, because a repeatable flag would still require the caller to type paths it cannot read back out of a Bash tool that renders NUL as a space, while `git … --output={file}` lets git write the list and the verb read it. Commit `36c06f6`, extended by `68efebb`.
- **D4 — met.** Branch (a), not (b): the boundary guard is gated on `--completed 5-execute` (`_cmd_lifecycle.py:1792`) so it cannot see a `6-finalize` commit made after it, but it DOES re-read those rows after a loop-back, so "no row is owed" would have been false. `test_a_finalize_commit_whose_row_cannot_be_written_reports_it`, `test_the_docstring_no_longer_claims_the_boundary_surfaces_a_finalize_row`, `test_the_commit_changes_flow_tells_the_caller_to_read_ledger_recorded`, `test_a_post_commit_push_refusal_still_reports_the_ledger_outcome` — order `test-first` for the first three (same failing run); the fourth was added against CodeRabbit's finding and failed its own premise before the code was right (log `…-214204.log`). Commit `e21c474`, extended by `68efebb`.
- **D5 — met.** `test_chained_verify_carries_the_canonical_identity_on_every_hop` — order `test-first`; same failing run (`'--canonical verify' not in hop`); passed at `686094a`. Commit `369af58`.
- **D6 — met.** Order `test-first`; the run above failed exactly the 12 new/changed tests and passed 29 076. Stale comment now names the three row owners; the phase-5 doc-contract helper mirrors the `--output` form; every other test still passes (29 088 at `686094a`, 29 089 at `259b39f`, 34 132 in `verify`). Commit `686094a`.

Per-head test runs (`module-tests plan-marshall`): `6b9a879` 12 failed/29 076 passed (intended); `686094a` 29 088 passed; `4b65f01` 29 088; `fa60436` 29 088; `68efebb` 29 089. Full `verify` (34 132 tests, mypy + ruff) green at `68efebb` and at the merge head `107928a`.

## 2. Personas and skills

Personas: D1 `persona-documenter`; D2–D5 `persona-implementer`; D6 `persona-module-tester`; every self-review round `persona-code-reviewer`; PR-comment triage `persona-code-reviewer`.

Skills: each deliverable declared `plan-marshall:ref-code-quality` + `pm-plugin-development:plugin-architecture`, with `pm-documents:ref-documentation` on D1 and `pm-dev-python:python-core` on D2–D6. All loaded as standards.

skills added: none — no deliverable reached a module the Expected Surface did not name. Surface extended instead: `doc/adr/002-…adoc`, reason: it carries the same exclusivity statement D1 names and is the authority both amended documents cite, so narrowing them while leaving the ADR unchanged would have introduced a contradiction.

## 3. Hypotheses

- `cwd-policy` statements contradicted by the `commit` verb's write — **confirmed**. `git-workflow.py:1119` writes `worktree / '.plan' / 'work' / 'change-ledger.jsonl'`, and `worktree` comes from `--project-dir` or the plan record; `cwd-policy.md:34` and `marketplace_paths.py:15` claimed the main-anchored resolver was the only departure from cwd-relativity.
- A `6-finalize` row has no consumer that would refuse on its absence — **confirmed for finalize time, refuted for the branch**: `_cmd_lifecycle.py:1792` gates the guard on `--completed 5-execute`, and the existing `test_a_finalize_commit_then_a_loop_back_…` shows the boundary re-reads a finalize row after a loop-back. That is why branch (a) was taken.
- `test_phase5_change_ledger.py` pins the changed-path command — **confirmed**; its `_diff_tree_paths` helper mirrored the old command and was updated.

## 4. Findings

Self-review round 1 (13 findings): F1 blocker (the surviving "boundary surfaces it" claim) fixed; F2 (resolver exclusivity, ×2) fixed; F3 (over-claimed non-cwd wording) fixed; F4 (recovery step contradicted its own step 1) fixed; F5 (`-z` missing) fixed; F6 (regeneration obligation) fixed; F7–F11 fixed; F12 declined (`branch-cleanup.md:2077`, `_footprint_resolver.py:410` — out of D2's standing constraint, carried as residue); F13 declined (not false). Commit `4b65f01`.

Self-review round 2 (5 findings): N1 (my own "ONLY reader" over-correction) fixed; N2–N5 fixed, including the ADR-002 amendment. Commit `fa60436`. Round 3: **self-review: clear**.

CodeRabbit, inline thread `PRRT_kwDOQ3xasM64qbKi` (`phase-5-execute/SKILL.md:814`): the Step 10a `--output` write fails when `.plan/temp` does not exist — **real** (reproduced: `fatal: could not open … No such file or directory`), fixed by `mkdir -p` and the requirement stated in all five documents that emit the command. Disposition `coderabbit inline inline-1 — 68efebb`; replied naming the commit, then resolved.

CodeRabbit, review-body finding (outside diff, `git-workflow.py:1252`): post-commit refusals discarded `ledger_recorded`/`ledger_error` — **real**, and it defeated D4 exactly where the caller needs the flag. Fixed with one helper on every post-commit return, plus the test above. Disposition `coderabbit inline inline-1 — 68efebb` (the verb reports both CodeRabbit findings under that one id after the thread was resolved).

Sourcery: refused on its own quota ("used your own review budget … request another review in 1 day and 5 hours"), re-triggered on the merge head and refused again. Optional reviewer, so no gating and no quota wait.

## 5. Reviewers

- **coderabbit** (required, `quota_limited: true`, `review_complete_after_handling: true`) — reviewed, one review on `fa60436` with a readable `final_review_risk_coverage` marker (`kind=reviewed`, `coveredCommitId=fa60436`). Both its findings handled, both threads resolved, then re-triggered and answered "already reviewed the last commit"; on the merge head it published a rate-limit notice and no new review. Standing authorization applies: qualifying review on record, every finding handled, re-triggered after the last push, every other gate condition green on the head.
- **sourcery** (optional) — refused on quota twice; not gating.

## 6. Operator questions

1. "The main checkout's executor (version 0.1.2149) refuses the resolve-supplied build command … How should I proceed?" — options: regenerate then continue / run without `--canonical` / stop as blocked. The operator selected **"Regenerate the executor, then continue"**. The regeneration ran through `plan-marshall:tools-script-executor:generate_executor` (342 scripts) and the run continued with the resolve-supplied commands unchanged.

No other question was asked. Free-text operator messages: none.

## 7. Rule check

- `guard: present`; `{guard_log}` has **no line for this run** (the only lines from today belong to session `ses_e170fb5eaffe…`, PLAN-LB-159). Nothing was refused.
- The run's own actions: one shell-file operation outside the allowed set is not present; every build went through the resolved canonicals; every script went through the executor; one command per shell call throughout.
- **Disclosed deviation:** build log files were read from `/home/oliver/.plan-marshall/marshalld/job-logs/` — outside the repository root. They are the builds' own artifacts and the build contract requires opening the `log_file` the result names for the test summary; no credential file, config directory or environment dump was read.
- Spec read: `spec_source: ledger_worktree`, no `spec_differ` marker at either read.
- `executor-skew`: `not_applicable` (source checkout, executor `0.1.2149`), answered and never asked about. A separate, real staleness — the `--canonical` flag missing from the executor's embedded surface — surfaced only when the first build ran, and the operator authorized the regeneration.
- Restarts: none. Killed sub-agents: none. Re-dispatches: the self-review sub-agent three times (rounds 1, 2, 3), each re-reading the diff at the then-current head.

## 8. Build server

Setup preflight `ready`; every build submitted with the default routing and ran `daemon_longpoll` — 16 builds, 0 degraded, 0 launch-fault retries, 0 killed jobs, 0 in-process fallbacks.

Failures, all the run's own and all fixed: one intended test-first run (12 tests); one test with a wrong assertion about the comma split; one `ruff format --check` auto-fix round; one broken relative link found by plugin-doctor; one test premise that asserted a non-zero exit where this CLI reports a business error at exit 0. One build waited 686 s behind another job of this worktree (`queued_seconds`), which is the per-worktree serialization, not a fault.

`runtime_stamp_reason` was absent; the stamp resolved fully.

## 9. Residue

- **Same rename-collapse defect class, out of this plan's surface:** `phase-6-finalize/standards/branch-cleanup.md:2077` and `plan-retrospective/scripts/_footprint_resolver.py:410` still compute a realized path set with a rename-following `git diff {sha}^1 {sha}`.
- `extension-api/standards/canonical-commands.md:162` says "Prefer emitting it — `build_canonical_commands` does"; the chained builder now does too, so the sentence is under-descriptive rather than false.
- **For the operator, per the new obligation:** `--changed-paths-file` is a new flag on the `append` verb's argument surface, so consumer projects must regenerate their executor before the documented Step 10a command works there. This rides the same `/apply-changes` debt the epic already records for `--canonical`.
- The ADR-002 note uses a bare `====` block where the file's other asides are `[NOTE]`-labelled; cosmetic, left as is.
- A known future hazard recorded, not acted on: npm's chained `run build` hop now declares `--canonical verify`, which is semantically the chained canonical's identity rather than the hop's own.
