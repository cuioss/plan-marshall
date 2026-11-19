envelope_version=1
sender_type=plan
sender_id=rb-lb-166-manifest-no-push-always-wins
epic=live-blockers
kind=landing
created=2026-11-18T23:49:13Z

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-166-manifest-no-push-always-wins
epic=live-blockers
pr=#2018
merge_state=merged
cleanup_owed=false
deliverables_total=2
deliverables_done=2
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash/high
effort=high
plugin_version=0.1
executor_version=0.1.2155
steps=setup:done,implement:done,build-gate:done,self-review:clear,pr:done,reviews:done,merge:done
unresolved_review_threads=0
review_body_findings_total=1
review_body_findings_handled=1
sonar_open_new_issues=n/a
step.sonar-roundtrip.open_issue_rules=n/a
```

guard: present

## Deliverables

Spec: `.plan/orchestrator/live-blockers/plans/PLAN-LB-166-manifest-no-push-always-wins.md`
Branch `fix/lb-166-manifest-no-push-always-wins`, spec read from the shared ledger worktree
(`spec_source: ledger_worktree`, no `spec_differ` marker).

**D1 — the ceremony selection honours `commit_and_push`. MET.** order: `test-first` (the behaviour is
pinned by D2's tests, which were written and seen failing first). Every clause:

- receives `commit_and_push` — `_manifest_rules.py:787-788` (keyword-only, default `True`);
  `manage-execution-manifest.py:2887` forwards the normalised bool.
- never inserts the four when false — `_manifest_rules.py:833-836`; guard is set-membership on
  `_COMMIT_PUSH_DROP_STEPS`, so exactly the push-only steps are covered.
- every other step added as before — the out-of-set `simplify` force-in still happens on a local-only
  plan (test at `…_ceremony_finalize_always.py:260-273`).
- a pushing plan unchanged — three pushing-plan controls green; the default is `True`.
- the outline records the gate values and the map coverage — `decision-rules.md:419,426`,
  `SKILL.md:815`, and the function docstring; see Hypotheses below. order for this clause: `none`
  (nothing to fail).

Commit `8f5b9775e`.

**D2 — the test. MET.** order: `test-first`.
- Authored first and run against the unfixed tree at base `571c01087` with only the test file added:
  7 failed, 4 passed. Failing output:
  `/home/oliver/.plan-marshall/marshalld/job-logs/58f1e8da4fee4b1e906693e4ba76ef97.log`
  (produced by `module-tests plan-marshall --no-parallel --filter CeremonyFinalizeAlwaysRefusedOnLocalOnlyPlan`).
- After moving the class to its final file, the failing run was reproduced from that location with the
  committed guard reverted (guard restored by re-editing, source diff empty afterwards): 7 failed,
  4 passed — `/home/oliver/.plan-marshall/marshalld/job-logs/e6afd6b46b2e4215bf90ebe760e25415.log`.
  This second run is supporting evidence (order `mutation-after`); the Done-when's order stays
  `test-first`, carried by the run above.
- Every required case: one per push-only step the gate map can add (`functional-review`, `code-review`,
  `pre-push-quality-gate`), present-and-dropped and absent-and-insertable; the same gate inserting on a
  pushing plan; `push` (no gate) staying dropped with all gates forced; and a non-push gate still
  inserting on a local-only plan.
- The case set is now DERIVED from `_CEREMONY_FINALIZE_STEP_MAP ∩ _COMMIT_PUSH_DROP_STEPS` (CodeRabbit's
  finding, fixed in `11811e623`), with a non-vacuity test asserting the derivation is non-empty and
  every derived canonical is push-only.
- Commits: `144706237` (tests first authored), `9d252a875` (moved beside the forced-`always` cases),
  `d23f1d67f` (derived case set), `11811e623` (duplicate-case removal).

**Per-head test runs** (each pushed head of the PR):
- `144706237` — module-tests 34143 green (`566bd651d1664d3e80967ea026b662ff.log`), verify green
  (`5717fcea8171444fb9c8b23e5f0d5736.log`).
- `9d252a875` — module-tests 34143 green (`617a33e4b062482285a7eafdee37f84e.log`), verify green
  (`2b35d7827f39426895d05df58c2952b8.log`).
- `11811e623` — module-tests 34144 green (`35960d065bd24617b21d81e69760539d.log`); routed `verify`
  hit the daemon bound, so the split form ran: quality-gate green
  (`8ecdb37297b84551a4fa8a8764d7f2a8.log`).
- `41a6aab02` (base merge #1) — module-tests 34144 green (`0a77e2838837427c94b22c5a322ea0be.log`),
  quality-gate green (`14896ba5e86a40589c71b91282d56731.log`).
- `43a8f8d1e` (base merge #2, the merge head) — module-tests 34144 green
  (`3d32466b93dd476eb1df785028cfe9e7.log`), quality-gate green
  (`eaeb430171bb456ca5495ad1b5ea705e.log`).

`module-tests` is the project's only test part (no `test-compile` published).

## Personas and skills

- D1 — persona-implementer; skills `plan-marshall:ref-code-quality`,
  `pm-dev-python:python-core`, `plan-marshall:manage-execution-manifest`.
- D2 — persona-module-tester; skills `plan-marshall:ref-code-quality`,
  `pm-dev-python:python-core`, `pm-dev-python:pytest-testing`.
- Self-review rounds and the PR-comment triage — persona-code-reviewer.
- No surface drift: every changed file is inside the module the spec's Expected Surface names, or its
  test tree. `skills added: none, reason: no module outside the declared surface was touched`.

## Hypotheses

- HYPOTHESIS "the two functions' order lets the second re-add what the first removed" — **confirmed**:
  `_apply_commit_push_disabled` at `manage-execution-manifest.py:2571` (pre-matrix),
  `_apply_ceremony_finalize_selection` at `manage-execution-manifest.py:2883` (post-matrix).
- HYPOTHESIS "a `minimal` lane can yield `always` for one of the four" — **confirmed for three**:
  `minimal → always` for all five gates (`_manifest_rules.py:658-689` map, `:810-824` transform), and
  the map covers `functional-review`, `code-review`, `pre-push-quality-gate`; `push` owns no gate, so it
  is unreachable through this path (covered by the all-gates case instead).
- OBSERVED lines re-read and confirmed: `_apply_commit_push_disabled` at `_manifest_rules.py:286-319`
  still drops the four when false and was not weakened.

## Findings

- Self-review round 1 (persona-code-reviewer): F1 placement — the forced-`always` class belonged beside
  the forced-`always` cases → **fixed** (moved to `…_ceremony_finalize_always.py`, `9d252a875`); F2 a
  self-contradicting header comment → **fixed** (gone with the move); F3 duplicated monkeypatch helper →
  **fixed** (single copy). F4 keyword-only default `True`, F5 untyped test helper, F6 two docs beyond
  the Expected Surface (inside the permitted subtree, required by D1's record clause), F7 the `push` arm
  being vacuous pre-fix, F9 log line offsets → accepted/recorded as preferences. F8 and F10 → refuted
  (the fixture docstring's "only path" claim is still literally true; the refusal is not silent — the
  pre-filter logs each drop).
- Self-review round 2: residue check clean (the moved-from file is byte-identical to its pre-change
  state); four new findings all refuted or accepted as preferences. `OPEN: 0`.
- CodeRabbit (required): one actionable finding — the new test duplicated the intersection of two
  production registries — **fixed** in `11811e623`, replied on the thread, thread resolved.
  Disposition: `coderabbit inline inline-1 — 11811e623`.
- CodeRabbit re-reviewed `11811e623` incrementally: "No actionable comments were generated in the recent
  review"; its coverage marker names `11811e623` (`kind=reviewed`).
- Sourcery (optional): refused on quota at first trigger, later published "Sourcery assessment.
  **Approved.**" on `d23f1d67f`; re-triggered for the merge head, no further review. Never gated.

## Reviewers

- `coderabbit` (required, `quota_limited: true`, `review_complete_after_handling: true`) — reviewed
  `9d252a875` (one finding) and `11811e623` (clean, marker `kind=reviewed` naming `11811e623`). Under the
  done-exemption its review is the review at any head of this PR once every finding is handled, which it
  is; the later heads (`41a6aab02`, `43a8f8d1e`) carry no re-trigger obligation. Its check-run on
  `43a8f8d1e` was NEUTRAL/skipping (bot-side limit), not a required CI gate.
  Trigger: `@coderabbitai review` at 2026-11-18T19:17:04Z on `9d252a875`.
- `sourcery` (optional, `quota_limited: true`, `review_complete_after_handling: false`) — refused on
  quota (250k diff-char budget) at 2026-11-18T19:16:56Z, reviewed "Approved" at `d23f1d67f`, re-triggered
  for the merge head with no further review. Its outcome never gated the merge.

## Operator questions

None asked. No free-text operator messages.

## Rule check

- **Guard.** `guard: present` (OpenCode). Read `.plan/temp/guard.log` for this run's session
  (`ses_e10a2d311ffeg45KGaT7dtCZ2K`): exactly ONE entry — the R7 refusal at 16:01:52Z, when a first edit
  was aimed at the main checkout's test file instead of the plan worktree. The run immediately re-issued
  the same edit inside the worktree, and every later edit went there. No other guard entry exists for
  this session.
- **Shell file operations.** The run issued none: every file was read and searched with the file tools;
  the whole-tree test logs were opened with the read/grep tools after the build result named them.
- **Executed commands.** Every script went through `python3 .plan/execute-script.py`; every build through
  the resolved `build` commands; every CI action through `plan-marshall:tools-integration-ci:ci`. No
  `gh`/`glab`, no direct wrapper, no `ruff`/`mypy`/`pytest`, no `python3 -c`, no `sleep`. One command per
  shell call throughout.
- **Spec read.** `spec_source: ledger_worktree` — the shared ledger worktree's copy, read as the
  default. No `spec_differ` marker was reported, so the main checkout's copy did not differ at resolve
  time.
- **Executor skew.** `executor-skew: not_applicable` — the lane text lives in this source checkout, so
  the executor maps the checkout's own scripts and cannot lack a verb the text names. Answered and
  recorded, not asked about.
- **Restarts / re-dispatches.** None. The self-review sub-agent was dispatched twice (round 1, round 2)
  plus two clarifying follow-ups in the same session; no sub-agent was killed.
- **Model/effort.** One model and one effort throughout: `deepseek-v4.1-flash/high`.
- Builds: all routed (see Build server). Every routed build, including the two that ended at a bound and
  the one that failed mypy, is counted there.

## Build server

- Setup preflight on the worktree: `ready` (registered `true`), `executor_in_worktree: present`.
- Per-mechanism count: `daemon_longpoll` 25, `in_process_fallback` 0. No `degraded`, no launch-fault
  retry, no `killed` job.
- Two bound expiries, both recorded and never blind-retried:
  - `module-tests` at `144706237` — `timeout_used_seconds: 1168`, `timeout_source: learned`; re-run at
    the resolved `1297`s and green.
  - `verify` at `11811e623` — `timeout_used_seconds: 1297`, `timeout_source: explicit`; the split form
    (quality-gate + module-tests) is the run that was green at that head, per section 4.
- Two submits returned a live status at their bound (`queued` once, `running` once) and were re-attached
  with `build_server wait` on the same job id; neither was backgrounded.
- No `runtime_stamp_reason` was reported by either resolve.

## Residue

- **Delivered mailbox:** `mailbox_state: no_mailbox`, `delivery_state: never_delivered`, `count: 0` at
  all three reads (setup, before self-review, before the merge gate). That is not a read that found no
  mail — the plan was never delivered to — so no disposition lines exist and none were owed.
- **Expected-Surface drift:** `SKILL.md` and `standards/decision-rules.md` were edited although the
  spec's Expected Surface lists only scripts and two test files. Both are inside the permitted
  `manage-execution-manifest` subtree and D1's "records" clause requires them; recorded, not hidden.
- **Test-file placement deviation from D2's literal enumeration:** the spec names
  `test_ceremony_finalize_selection.py` or `…_ceremony_finalize_never.py`, "whichever already holds the
  forced-`always` cases". Neither did — they live in `…_ceremony_finalize_always.py`, where the class now
  sits. A spec amendment was the cleaner path; the deviation is recorded rather than presented as
  conformance.
- Nothing else is open. No base-evidence worktree was created (no Done-when needed a base-sha run), so
  `cleanup_owed=false`; the plan worktree was removed and the branch pruned local and remote.
