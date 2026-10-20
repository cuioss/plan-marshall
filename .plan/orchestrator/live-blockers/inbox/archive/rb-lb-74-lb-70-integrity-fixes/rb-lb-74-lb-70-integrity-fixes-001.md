envelope_version=1
sender_type=plan
sender_id=rb-lb-74-lb-70-integrity-fixes
epic=live-blockers
kind=landing
created=2026-10-20T03:26:05Z

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-74-lb-70-integrity-fixes
epic=live-blockers
pr=#1822
merge_state=merged
cleanup_owed=false
deliverables_total=4
deliverables_done=3
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash
steps=setup:done,implement:done,build-gate:done,self-review:clear,pr:done,reviews:done,merge:done
```

guard: present (tool-call guard installed for the opencode harness; `.plan/temp/guard.log` holds no refusal line for this run's sessions)

## Deliverables

**D1 — the two Major findings on PR #1815: met.**
- Done-when "a missing declared worktree returns a blocking `test_integrity_not_run` and `may_close: false`": met —
  `test_a_missing_declared_worktree_blocks_the_code_review`. Before the fix it failed (`findings == []`); after,
  the finding is blocking and `may_close` is false even with a permissive verifier answer. Commit `3249d2e14`.
- Done-when "a failed snapshot-digest record returns an error and leaves no snapshot": met —
  `test_a_scored_snapshot_is_rolled_back_when_the_digest_is_not_recorded`. Before: `status: success` with the
  snapshot on disk; after: `snapshot_integrity_unrecorded` and the file absent. Commit `3249d2e14`, extended by
  `dbbae6597` (re-freeze consumption and byte-level rollback).
- Done-when "a plan with `use_worktree: false` still yields no finding": holds —
  `test_a_plan_without_a_worktree_keeps_the_exemption`.

**D2 — a verdict row answers by id or exact text only: met.**
- `test_a_positional_fallback_no_longer_closes_a_criterion`: before `open_count == 0`, after `1`.
- `test_the_validator_names_an_unmatched_verdict_row`: before no finding; after `unmatched_criterion` names the
  paraphrased row and the criterion stays open.
- `test_author_verdict_refuses_a_criterion_id_that_names_no_frozen_criterion` and
  `test_author_verdict_accepts_a_criterion_id_on_a_row`: reject/accept both proven.
- Preservation clause `test_a_paraphrased_row_carrying_the_id_grades_its_criterion` holds before and after.
- Commits `3249d2e14`, `1f127d257`.

**D3 — the integrity record is serialized and its keys are reserved: two of three Done-when clauses met; the third is a spec defect.**
- "`record_integrity` blocks on the status critical section": met —
  `test_record_integrity_waits_for_the_status_guard` holds the real `rmw_json` critical section and the writer
  stays blocked until release. Before the fix it wrote straight through. Commit `3249d2e14`.
- "`metadata --set` / `--set --append` refuse the three keys": met —
  `test_metadata_set_refuses_every_protected_key`, `test_metadata_append_refuses_every_protected_key`, with an
  unprotected-key control. Commit `3249d2e14`; constants derived from the owning module in `1f127d257`.
- "the owning verbs still write those keys (holds at `a297ea762`)": **not met as written.** It holds for
  `criteria_integrity` / `snapshot_frozen`, but NOT for `functional_review_override_heads`: at `a297ea762` no
  owning verb wrote it — the functional-review workflow appended it by hand
  (`phase-6-finalize/workflow/functional-review.md:161-164`), which is exactly why the key is now protected.
  The deliverable body names `loop-back close` as the owner; the implementation follows the body
  (`_cmd_loop_back.py`, `test_a_close_on_the_functional_review_records_the_override_head`). This clause cannot
  hold at that sha and needs a spec amendment, not a code change.

**D4 — a `.plan/` citation cannot escape or count a self-written file: met.**
- `test_a_citation_escaping_the_plan_directory_is_refused`: before accepted, after refused.
- `test_a_self_written_temp_citation_is_refused`: before accepted, after refused.
- Positive control `test_a_build_log_under_the_plans_own_build_results_is_accepted` holds, plus the negative
  `test_another_plans_build_log_is_refused`. Commit `3249d2e14`.

## Personas and skills

- Persona `plan-marshall:persona-implementer` applied to all four deliverables (production code).
- Domain skills named by the spec, loaded per deliverable: `pm-plugin-development:plugin-architecture`,
  `pm-plugin-development:plugin-script-architecture`, `pm-dev-python:python-core`,
  `plan-marshall:ref-code-quality`, `pm-dev-python:pytest-testing`, `plan-marshall:persona-module-tester`.
- `plan-marshall:persona-code-reviewer` applied to every self-review round and to triaging every PR comment.
- skills added: none (no surface drift; every touched file is in the spec's Expected Surface plus the two doc
  surfaces the D3 behavior necessarily changes, `manage-status/SKILL.md` and the step-1 block of
  `functional-review.md`).

## Hypotheses

- "The status writers' critical section can be entered from the criteria scripts without an upward import
  cycle" — **confirmed.** `manage-status/scripts/_status_query.py:13` already imports `_locks_core`, and
  `_locks_core` imports only `input_validation`, `marketplace_paths` and `plan_logging`; `_criteria_snapshot`
  now imports `held_guard`/`_GUARD_SUFFIX` sideways with no cycle.
- "`loop-back close` is the only writer of `functional_review_override_heads`" — **refuted at `a297ea762`.**
  The writer was `phase-6-finalize/workflow/functional-review.md:161-164` (`metadata --set --append`);
  `_cmd_loop_back.py` did not write it. The run makes the hypothesis true.
- Verify-first clause (shared lock by import vs a `manage-status` verb) — decided: import the shared guard.
  No subprocess, no upward import, and the guard path is the same file by construction. Recorded in
  `_merge_integrity`'s docstring.

## Findings

- Self-review round 1: 12 findings. Fixed: stale positional-fallback docstring; two contradictory workflow
  sentences; the unmatched-row report now mirrors the gate's superseded/current-outline exemptions; deliverable
  qualifier enforced; `authorize_change` rollback; `OSError` handling; causal `may_close` test; real critical
  section in the lock test; override-head idempotency and non-functional-step controls.
- Self-review round 2: 10 items verified; 6 minor new items. Fixed: honest rollback-failure message, tests for
  the authorization rollback and qualifier rejection, doc precision. Residue: see below.
- Self-review round 3: no new defects; "ready to open as a PR". Cosmetic residue listed below.
- PR review — cuioss-review-bot inline (keying `frozen_by_number` by the normalized deliverable number and
  reading dict-shaped criterion text): fixed in `1f127d257`, thread resolved.
- PR review — coderabbit Major (a failed override-head write reported as success): fixed in `1f127d257`,
  thread resolved.
- PR review — coderabbit Minor (hardcoded protected key names): fixed in `1f127d257`, thread resolved.
- PR review — coderabbit outside-diff Minor (a failed verdict-digest record reported as a successful seal):
  fixed in `1f127d257`, answered on the PR.
- PR review — coderabbit Minor (an unbound `snapshot_frozen` marker read as frozen; digest-read `OSError`):
  fixed in `dbbae6597`, threads resolved.
- PR review — coderabbit outside-diff Major (re-freeze authorization not consumed with the digest) and Minor
  (corrupted-snapshot rollback decoded the bytes): fixed in `dbbae6597`, answered on the PR.
- PR review — coderabbit Major (two concurrent re-freezes on one authorization): fixed in `c83f8b793` with a
  plan-scoped snapshot guard; thread resolved.
- Sourcery: quota refusal only; no findings.

## Reviewers

| Reviewer | Required | Outcome | Head reviewed | Trigger / wait history |
|---|---|---|---|---|
| cuioss-review-bot | yes | reviewed | `c8d8cfae7` (formal review 20:55Z); later guides attest `1f127d257`, `dbbae6597`, `c83f8b793`, current `0e18f21ac` (updated 02:34-02:35Z) | triggered 20:53Z, 21:18Z, 00:29Z, 02:09Z, 02:33Z; no refusal |
| coderabbit | yes (quota-limited) | reviewed, then refused | formal reviews on `c8d8cfae7` (20:59Z), `1f127d257` (00:23Z), `dbbae6597` (02:04Z) | refusals 21:15Z, 22:46Z, 00:29Z, 02:10Z, 02:33Z; 90-minute waits observed; re-triggered after the last push and refused at 02:33:57Z; standing authorization applied |
| sourcery | optional (quota-limited) | refused on hard quota, then its check passed on the current head; no findings | `0e18f21ac` (check only) | triggered 20:53Z; refusal names a 14-hour window; optional, does not gate |

Standing review authorization (coderabbit): qualifying review on `dbbae6597`; every finding from it (the
re-freeze race) and from every earlier review fixed in `c83f8b793` / `dbbae6597` / `1f127d257` and every thread
resolved; re-triggered once after the last push and refused; every other gate green on `0e18f21ac`.

## Operator questions

none asked.

Free-text operator messages: none beyond the initial invocation.

## Rule check

- `guard: present`; `.plan/temp/guard.log` contains no line and no refusal for this run's sessions.
- One rule break by the assistant: a single `git -C … grep -n "authorization"` call (git's `grep` subcommand),
  used once while checking for other writers of a constant. The guard did not refuse it and logged nothing.
  No other shell file operation, build-bypass, or CI-CLI call was used.
- The build gate ran through the resolved build commands in-process against the worktree; every test command
  went through `pyproject_build run`.
- All four deliverable tests were written first and seen failing against the unfixed tree before the fix.

## Residue

- **Spec amendment needed:** D3's third Done-when label ("holds at `a297ea762`") is false for
  `functional_review_override_heads` and contradicts the deliverable body; the code implements the body.
- Cosmetic self-review residue, no code impact: `_merge_integrity`'s docstring still names `TimeoutError` where
  the catch is `OSError`; the functional-review "current outline" clause does not say "its own deliverable's";
  the `authorize_change` failed-rollback branch has no forced-failure test; one test name says "scored" where
  "stored" was meant.
- The four deliverables were committed as a small series of coherent commits rather than exactly one commit
  per deliverable, because D1/D2/D3 share two modules and hunks cannot be split without interactive staging
  (which this lane does not use). The PR body and this report name each deliverable and its tests.
