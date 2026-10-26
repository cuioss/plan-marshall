# Landing Analysis: PLAN-LB-82 — The integrity carry fails safe, the re-freeze authorization is guarded end to end, and the tests that pin them can fail

epic: live-blockers
workstream: WS-03
pr: #1864 (`931d5847b`, merge queue, base `main`, merged 2026-10-26T10:26:47Z)

> Landing record for one shipped plan. **(re-read)** = read again in git, the CI abstraction, the merged tree, `guard.log`,
> the script execution log or the lane's own build logs. **(store)** = read from the OpenCode session database, read-only
> (counts, tool names, command words, paths, times; no message text). Nothing was executed except the read-only checks named.
> Token usage is out of scope by the 2026-10-23 ruling. The fix was not re-executed here: it rests on the PR's tests, green CI,
> the four cited failing runs and the merged diff of the shared files read in full.

## Verdict

**Grade: B.** Runbook lane, `deepseek-v4.1-flash/high` on all six sessions **(store)** (root plus five self-review sub-agent
sessions), 14 h 39 min wall clock (2026-10-25T20:20Z to 2026-10-26T10:59Z; merged 14 h 06 min in).

All four deliverables are delivered and the code does what the spec asked **(re-read)**: `rmw_json` gains
`require_readable_state` and raises `StateReadFailed` on a missing, unreadable, corrupt or non-object document, `write_status`
takes it whenever the carry is on, `create --force` seeds with `carry_protected_keys=False`, `set-lane` commits through
`rmw_json`, `authorize_refreeze` runs under the snapshot guard with an ownership token, `kept` is retired for `tamper_flagged`,
`verdict_row_matches` reads an id-bearing row as the gate does, and `atomic_write_bytes` fsyncs the file and the directory,
keeps the mode and closes the descriptor when `fdopen` raises. Fourteen files (+1451/-190), CI green, Sonar `0` on the PR, main
clean **(re-read)**. The failing-run evidence is real: all four cited logs exist and their counts match the PR body exactly
(9 of 16, 4 of 11, 8 of 36, 3 of 5) **(re-read, logs)**.

Debits: the landing misreports the required reviewer's state at the final head and says all threads are resolved when one is
open (below); the local full suite never completed at the merge head; the D3 first Done-when is met at a narrower seam than it
reads (disclosed). Credits: every count the lane disclosed is exact (questions 4, sub-agents 5, read-class shell calls 4, guard
refusals 0), the shell-rule deviations were self-reported, no spoofed identity, no main-checkout edit, and the two design
decisions the spec left open were decided and the reason recorded in the code.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|---|---|---|
| D1 the protected-key carry fails safe | shipped-as-specified | `_read_json_state` + `require_readable_state` + `StateReadFailed` (rendered `state_unreadable`, exit 0, by `safe_main`); `create` bypasses the carry and says why; `set-lane` through `rmw_json`. Failing run `python-2026-10-25-204519.log` 9 failed / 7 passed **(re-read, log)** |
| D2 the authorization is guarded end to end, never unlogged | shipped-as-specified | snapshot guard then status guard, token-gated withdrawal (`superseded` / `already_consumed`), `kept` retired for `tamper_flagged`, `AUTHORIZATION_OUTCOMES` held to both docstrings and the rubric by a doc-contract test. `python-2026-10-25-210623.log` 4 failed / 7 passed |
| D3 validator and gate agree; the tests can fail | shipped, narrower than it reads | the `C9` row is unreachable through `run_author_verdict`'s sealing gate, so the test drives `report_unmatched_rows` directly with the predicate asserted alongside and a sealable `D1.C2` row end to end. Disclosed in the landing and the PR body. `python-2026-10-25-213138.log` 8 failed / 28 passed |
| D4 the atomic byte writer is durable | shipped-as-specified | fsync before replace, directory fsync best-effort, prior mode kept, `fdopen` failure closes the descriptor; test-first. `python-2026-10-25-213535.log` 3 failed / 2 passed |

Claimed `deliverables_done=4` of 4; agrees.

**Surface.** The spec declared `_cmd_halt.py`, `orchestrator.py` and `_review_support_validate.py`; the PR edits none of them.
That is correct, not a gap: `_cmd_halt` and the two `orchestrator.py` writers go through the `write_status` seam this PR
changes (the docstring now names them), and the validator's disagreement lives in `verdict_row_matches`, which the PR edits.
No file outside the declared surface was touched.

## Findings by the orchestrator

- **Questions** **(store)**: four `question` calls (20:21Z, 00:55Z, 08:42Z, 10:08Z) = the landing's four. Q1 is the
  `executor-skew` `could_not_check` verdict (the flat-install defect already recorded); Q2 the fourth self-review round; Q3 and
  Q4 the merge with named gaps.
- **Sub-agents** **(store)**: five `subagent` calls (23:48Z, 00:13Z, 00:34Z, 06:32Z, 06:44Z), five child sessions, all completed
  = the landing's five rounds. No restart notice in the tree.
- **Guard** **(re-read)**: `guard.log` holds no line for the six session ids = the landing's "no guard refusal".
- **Shell read-class calls** **(store)**: `grep` 2 and `tail` 2 in the root session, none in the children = the four the landing
  self-reports as deviations. The one call containing a pipe-like character is the `grep -n "…\|…"` regex alternation the
  landing lists, not a shell construct. Exact.
- **Identity** **(store)**: no `CLAUDE_CODE_SESSION_ID` or `OPENCODE` prefix on any executor call. No spoofed identity.
- **Main-checkout edits** **(store)**: 0 tracked-file edits outside the worktree `lb-82-lb-77-completion` (146 worktree edits,
  29 under `.plan/temp`). Main is clean **(re-read)**.
- **Sonar** **(re-read)**: `0` open issues on the PR.
- **Reviewer state misreported (re-read, CI abstraction).** The landing (§5, §9) says CodeRabbit's qualifying review covers
  `a3b6144c8`, that the final head `66c883e51` drew a silent re-trigger, and lists "CodeRabbit's review does not cover the final
  head" as an accepted gap the operator selected twice. The PR's own walkthrough comment says otherwise: its Merge Risk block
  carries `sourceCommitId = coveredCommitId = 66c883e51`, `kind = reviewed`, Low, posted at 09:18Z, nine minutes after the merge
  commit was pushed (09:09Z) and 68 minutes before the merge (10:26Z). The final head WAS reviewed. Q4 (10:08Z) was asked
  fifty minutes after that review existed, with the false premise that the gap was open. No harm followed: the settled rule
  (a valid CodeRabbit review plus a quota-blocked re-review authorizes moving on) applies either way, and the merge was
  correct. Recorded as a note; it is not raised as a question or a finding about the unreviewed head.
- **One thread merged open (re-read).** The landing says CodeRabbit posted four findings and "all four threads resolved". The
  PR has five review threads; the fifth (`PRRT_kwDOQ3xasM6wMufJ`, opened 09:18Z on the final head, Minor, "Functional
  Correctness", `_criteria_snapshot.py` L487) is unresolved and unanswered. Its claim holds on the merged code: when a successor
  reclaims the stale snapshot guard and replaces this call's token, `_line_landed` leaves the pending marker alone but
  `_merge_integrity` still returns true, so `authorize_refreeze` reports `success` for an authorization a newer call replaced.
  It needs a stall longer than the guard's 60 s stale window, the consequence is a refused next re-freeze (the operator
  authorizes again), and nothing unlogged can apply, so it fails closed. CodeRabbit's own risk line calls the merge safe. Not
  staged (focus rule: high and blocking only); the lane's own Residue names the sibling case (two calls failing their decision
  lines inside that window).
- **Routed builds from a worktree (re-read, landing §8).** The routed leg failed again for this worktree (`pwx` unresolvable,
  `exit_code -1`), with `--execution-mode in_process` as the working fallback. This is the third landing after LB-55 and LB-53
  to report it; the Watches entry said to see whether a third run repeats it before staging anything. It does. The fallback
  works, so nothing blocks; the operator decides whether it earns a plan.
- **Local gate**: the whole-tree `verify` could not complete locally (bound at 1411 s; `module-tests` at the merge head timed out
  at 2700 s with no result); CI's `verify` at that head (1721 s) is the authority. The two `test_harness_shape_guards.py`
  scanners time out under local load in five consecutive runs and pass in isolation; CI has never reproduced it. Pre-existing,
  the same pattern the Watches entry already records.
- **Design decisions the spec left open (re-read, code).** Both decided and recorded in the code: the create seed bypasses the
  carry (`carry_protected_keys=False`) rather than clearing keys inside the guard; the `kept` double fault fails closed
  (`tamper_flagged`). A `create --force` still leaves a pre-existing `work/criteria-snapshot.json` standing; the docstring now
  says so.

## Open Items

- Thread `PRRT_kwDOQ3xasM6wMufJ` (Minor): `authorize_refreeze` reports `success` after a successor replaced its token inside the
  stale-guard window. Fail-closed, not staged.
- The fix is source-only here until `/sync-harnesses` runs, as for LB-95.
- Routed-build fallback from a lane worktree: third repeat.

## Reconciliation actions

- Row PLAN-LB-82: `shipped`, pr `1864`, landing `landings/PLAN-LB-82.md`, plan id `rb-lb-82-lb-77-completion`.
- Inbox message `rb-lb-82-lb-77-completion-001.md` archived.
- Epic: queue annotation, Open Defect (PLAN-LB-77 residue) marked fixed, Decisions entry, model-comparison entry, Watches entry
  updated.
