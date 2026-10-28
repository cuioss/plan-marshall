# Landing Analysis: PLAN-LB-93 — Executor, guard and gate fixes (partly delivered)

epic: live-blockers
workstream: WS-04
pr: #1874 (`027351aaa`, merge queue, base `main`, merged 2026-10-27T17:20:34Z)

> Landing record for one shipped plan. **(re-read)** = read again in git, the CI abstraction, the merged tree, `guard.log`,
> the script execution log or the lane's own build logs. **(store)** = read from the OpenCode session database, read-only
> (counts, tool names, command words, paths, times; no message text). Nothing was executed except the read-only checks named.
> Token usage is out of scope by the 2026-10-23 ruling. The fix was not re-run on a real install: it rests on the PR's tests,
> green CI, the cited job logs and the merged diffs of the files named below.

## Verdict

**Grade: C+.** Runbook lane, `deepseek-v4.1-flash/high`, **one session** with no sub-agent **(store)**, 5 h 25 min wall clock
(2026-10-27T12:28Z to 17:53Z; merged 4 h 52 min in).

Four of six deliverables are delivered and verified; D5 is half delivered; D6 was not started; and the self-review round the
lane owes was never run. The headline of the plan ("the gate-truth half ships") did not ship: the required-bot participation
check inside `pre_merge_gate merge` and the whole barrier policy (D6) are still absent, so for the second time the unshipped half
of PLAN-LB-55 is carried forward (LB-55 was graded C+ for the same reason). The delivered four are good work, the lane's account
of its own state is accurate, and the partial landing was the operator's explicit choice at the second question ("Land D1–D5.1,
stage the rest"). The grade follows the outcome against the spec and the skipped self-review, not the quality of what shipped.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|---|---|---|
| D1 the generator starts in a flat install; a missing library is named | shipped-as-specified (the spec's premise corrected) | `skill_bootstrap.py` + a byte-identical stdlib anchor; `test_flat_install_generator_recovery.py`; red log `0e3fa416…` (3 failure lines) for the missing-library report. The lane found the spec was wrong that the start-up part already passed at the base: `marketplace_paths._find_skills_root` was nested-only, so `recover` reported `recovery_generator_missing`; it fixed it and said so **(re-read, job log)** |
| D2 every entry script takes the helper, a guard keeps it | shipped-as-specified | `test_skill_bootstrap_guard.py` fails at the base on `test_every_carrier_routes_through_the_shared_helper` and `test_no_carrier_respells_a_private_fallback` (red log `efba7d3a…`); `permission_fix.py` start-up red log `f70f3660…` **(re-read, job logs)** |
| D3 a cold, green mypy run is not failed for being fast | shipped-as-specified | mechanism (b): the file count mypy prints (`Success: no issues found in N source files`) with the duration heuristic only as the fallback; `compile` without a boundary unchanged; red log `aa0cd9a8…` (ImportError on the not-yet-existing parser: honest `test-first`) |
| D4 a lane run cannot write a tracked file in the main checkout | shipped-as-specified | rule R7 in `guard.js` and the Claude hook, narrow binding (marker + existing worktree); eight cases in `test_guard_lane_main_checkout_write.py` plus a parity test; red log `97b61a40…` names `test_a_lane_run_may_not_edit_a_main_checkout_path` |
| D5 no push or merge of a head the gates did not see | half delivered | the push verb refuses while a merge is armed (`_push_gate.py`, `test_push_while_merge_armed.py`, red log `281811b9…`); `pre_merge_gate merge` does NOT run the participation check |
| D6 the barrier states and enforces the review policy | not delivered | no code, no docs, no tests |

Claimed `deliverables_done=4` of 6; agrees. `steps` carries `implement:partial` and `self-review:not-run`.

**The D1 premise was my spec's.** The spec said the generator's start-up and `recover --help` pass at the base (after LB-97).
The re-grounding I did on 2026-10-27 checked `recover --help` and found exit 0, but not a full `recover` against a flat
checkout, which fails for a second reason. The lane ran the full verb, found it, fixed it and labelled the evidence
accurately. It is the fifth time a lane has corrected a pre-fix statement in one of my specs.

## Findings by the orchestrator

- **Questions** **(store)**: three `question` calls (12:29Z, 14:35Z, 16:21Z) = the landing's three (executor-skew; "Land D1–D5.1,
  stage the rest"; the Sonar override).
- **Sub-agents** **(store)**: none, matching `self-review:not-run`. The lane's own account: "No `persona-code-reviewer`
  sub-agent round was dispatched; the PR review itself and my own re-reads were the only review. This is a rule break." The
  lane did not ask the operator whether to skip it.
- **Guard** **(re-read)**: one line, R1 at 12:58:22Z (`grep -n "error" …python-2026-10-27-125808.log | head -20`) = the landing's one.
- **Shell read-class calls** **(store)**: `tail` 9, `grep` 7, `ls` 2, `find` 1, `wc` 1, `head` 1 = 21. The landing names the
  kinds ("`ls -la` once; `wc -l` once; `head`/`tail` several times; `grep -rn` twice") without totals; the store shows `grep`
  7 against "twice" and `ls` 2 against "once". Understated.
- **Identity** **(store)**: no `CLAUDE_CODE_SESSION_ID` or `OPENCODE` prefix. No spoofed identity.
- **Restarts** **(store)**: none. **Main-checkout edits** **(store)**: 0 (104 worktree edits, 27 under `.plan/temp`). Main is
  clean **(re-read)**. This is the first lane after LB-97 whose run ought to have been tempted by the main checkout, and it
  stayed in its worktree.
- **Executor interference** **(re-read, execution log)**: no `generate_executor generate` call on 2026-10-27 between 12:04Z (my
  regeneration) and the end of the run, so no lane rewrote the shared main executor this time.
- **PR threads** **(re-read)**: ten review threads, 28 inline comments, all resolved. CodeRabbit round 1 (7 actionable, a
  nitpick, an additional) was fixed or answered in `500879135`; round 2 (one actionable) in `5774f179c`. One of its round-1
  findings is worth keeping: with two fresh lane markers `laneWorktree` returned whichever directory `readdirSync` listed
  first and R7 would have sent a call from the other lane there; the lane changed the refusal to name every candidate.
- **Reviewers** **(re-read)**: CodeRabbit (required) reviewed `2adf2258` and `50087913`; the merged head `6288f1622` fixed
  Sourcery's two security findings (answered as false positives: list-argv `subprocess.run` without `shell=True`) and drew a
  rate-limit refusal on the re-trigger at 16:42Z. The standing authorization applies, a note only.
- **Sonar**: never decidable (`analysis_revision_unavailable`). The operator chose "Merge now, accepting the undecidable Sonar
  state". See the Sonar entry in the epic: the cause is a configuration, not this PR.

## Open Items

- **D5 second half and D6 are undelivered** and need a plan: the participation check inside `pre_merge_gate merge`; the
  `step-params` empty-roster error; the stale-bot re-trigger before a barrier question; generated (not authored) barrier options
  with no "make the required bot optional"; the rate-window loop; the merged-under-authorization record; the merge-anyway mutex
  re-acquisition; and removing the two remedies in `branch-cleanup.md` L1041 and L1222.
- GitLab: the push-vs-armed-merge read is GitHub-only (`pr queue-state`), so a GitLab merge train is not observed.
- The self-review round was skipped; the delivered code was reviewed by CodeRabbit (two rounds), Sourcery and the lane's own
  re-reads only.
- The fix is source-only until the next `/sync-harnesses`.

## Reconciliation actions

- Row PLAN-LB-93: `shipped`, pr `1874`, landing `landings/PLAN-LB-93.md`, plan id `rb-lb-93-flat-install-generator-bootstrap`.
- Inbox message `rb-lb-93-flat-install-generator-bootstrap-001.md` archived.
- Epic: queue annotation, the Open Defects it closes or leaves open, Decisions entry, model-comparison entry.
