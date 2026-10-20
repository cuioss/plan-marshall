# Landing Analysis: PLAN-LB-74 — the LB-70 integrity findings closed (runbook lane)

epic: live-blockers
workstream: WS-03
pr: #1822 (https://github.com/cuioss/plan-marshall/pull/1822), merged via the merge queue as `e1481166c` (squash; 16 files, +1302/-113)
harness: **OpenCode runbook lane**, `deepseek-v4.1-flash` / `high` throughout (provider `opencode-go`). Root
`ses_eaa659e96ffe8tO8QjV1bDY1NU`, one self-review child `ses_eaa3e3a39ffeQLaG0XXXfeLFZc` (three rounds),
and a **precursor session** `ses_eaa7b776fffensrRcs5ry8ovvT` (18:55Z-18:57Z, same invocation) that the
landing never mentions. As for PLAN-LB-59, **the installed lane text was the PLAN-LB-71 version
(`97542abc5`)**, not the PR base, so none of PLAN-LB-72's rules were in force.

> Landing record for one shipped plan. Lives at `landings/PLAN-LB-74.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Source: inbox `rb-lb-74-lb-70-integrity-fixes-001.md`. Checked against:

- `git show` of `e1481166c`, the branch commits (`3249d2e14`, `06f3fc6af`, `c8d8cfae7`, `1f127d257`,
  `dbbae6597`, `c83f8b793`, `0e18f21ac`) and `a297ea762` for the D3 hypothesis;
- the progress file, `.plan/temp/guard.log` and `opencode.db` (read-only, 3 sessions);
- PR #1822's 6 review threads, 11 reviews, 27 issue comments and checks through `ci`;
- one delegated read-only corroboration agent (spec fidelity, code soundness, review/merge, process);
  the orchestrator re-read the PR facts itself.

The facts block is `complete: false` on `total_tokens` only (`unknown`, the runbook lane's standing
degradation); the figures are in Metrics below.

## Deliverable Fidelity vs Spec

**3 met / 1 partial / 0 unmet of 4 deliverables**; **13 of 13 Done-when met in substance, 7 demonstrated
failing before the fix as the spec required**. The run reported 3 of 4 done (D3 not done because of a
spec defect, below).

| Spec | Grade | Evidence |
|------|-------|----------|
| D1 the two Major findings on #1815 | met | `test_a_missing_declared_worktree_blocks_the_code_review` failed pre-fix (`findings == []`); `test_a_scored_snapshot_is_rolled_back_when_the_digest_is_not_recorded` failed pre-fix (`'success' == 'error'`); the preservation test holds. Caveat: the worktree test monkeypatches `compute_test_integrity` to return `worktree_unresolved` and never resolves a real missing worktree. |
| D2 verdict row answers by id or exact text only | met | Positional-fallback test (`open_count` 0 → 1) and unmatched-row test failed pre-fix; the `author-verdict` reject half failed pre-fix, the accept half passed pre-fix (so one half of a "fails at `a297ea762`" bullet never failed). **The preservation clause "holds before and after" is false:** it FAILED in the only pre-fix run (`assert 2 == 0`); the run edited the fixture and never re-ran it against unfixed code. |
| D3 integrity record serialized, keys protected | **partial** | **Met:** `test_record_integrity_waits_for_the_status_guard` (failed pre-fix; the worker wrote through the held guard), and both `metadata --set` / `--append` refusals. **Third bullet, "the owning verbs still write those keys (holds at `a297ea762`)": a spec defect, not a run defect.** At `a297ea762` the workflow wrote `functional_review_override_heads` itself (`functional-review.md:158-164`, `metadata --set --append`) and `_cmd_loop_back.py` never referenced the key. The spec's own Claim Labels listed "`loop-back close` is the only writer" as a HYPOTHESIS to verify at outline, which contradicts the Done-when's "holds" label. The run followed the deliverable body: `loop-back close` now appends the head idempotently inside `rmw_json`, and the workflow only reads it. **Why partial and not met: the spec's worry was that the digest record "can be lost", and it still can** (Code defects 1). The lock orders two writes; it does not stop a stale writer from overwriting the block. |
| D4 `.plan/` citation cannot escape or count a self-written file | met | Resolves before checking scope: `..` refused, a symlink out of the plan's `build-results` refused, `.plan/temp` and another plan's `build-results` refused; no acceptance bypass found. **The pre-fix behaviour was never observed:** every D4 test failed pre-fix with `TypeError: missing_evidence() takes 2 positional arguments but 3 were given`, so "accepted before" is the landing's claim, not an observation; the positive control also failed pre-fix, so "holds at `a297ea762`" is undemonstrated. |

**Code defects in the merged change (new, not reported).** The corroboration read the riskiest new code:

1. **Medium — D3's intent not achieved.** `_status_core.write_status` (L142-185) commits the caller's whole
   document as read before the guard and refreshes only `title_token`. Every `require_status` →
   `write_status` writer (metadata, mark-step-done, phase writes) can block on the guard and then overwrite
   the `criteria_integrity` block `_merge_integrity` just committed. The D3 test only exercises a holder
   that re-reads state, never a stale-snapshot writer. The PR body's "lands before or waits" is false.
2. **Medium — in `c83f8b793`, which CodeRabbit never reviewed.** `authorize_change` reads the snapshot and
   checks tampering **outside** the new plan-scoped guard (`:888`, `:896`) and takes it only at `:942`;
   `_commit_authorization` then rewrites from the stale dict and re-records the digest. A re-freeze that
   commits in between is silently reverted (the digest is re-bound, so it does not read as tampered); two
   concurrent `authorize_change` calls drop one `authorized_changes` entry; the decision-log line is written
   before the guard, so a `snapshot_busy` result leaves an orphan decision (`authorize_refreeze` has the
   same shape).
3. **Low.** `_graded_status`'s text arm ignores a conflicting id, so one row can close two criteria.
4. **Low.** `SNAPSHOT_FROZEN_KEY` is an inner key of `criteria_integrity`, so protecting it as a top-level
   metadata field guards nothing (the real protection is `INTEGRITY_KEY`).
5. **Low.** Only `TimeoutError` is caught at `:657` and `:944`; other `OSError`s propagate loudly (no path
   was found that reports success after swallowing one). The rollback writes the prior bytes with a
   non-atomic `write_bytes` (`:625`). A stale `#:` comment above `FUNCTIONAL_REVIEW_STEP`.
6. **Clean:** lock order is always snapshot guard → status guard and no reverse path exists, so no deadlock
   (worst case nested 30 s timeouts under the 60 s stale threshold); the shared-guard import has no cycle
   (`_status_query.py:13` already imports `_locks_core`).

**Footprint.** 16 files realized; all 7 declared entries touched, including the hypothesis entry
`_cmd_loop_back.py`; one undeclared file (`manage-status/SKILL.md`). The landing said "no surface drift"
and listed two doc surfaces as extra; `functional-review.md` was declared, so only one was. **Scope beyond
the spec:** `authorize_change` rollback; the plan-scoped snapshot guard and its `snapshot_busy` result;
atomic re-freeze consumption; frozen-without-digest now reads `tampered`; `verdict_integrity_unrecorded`;
`D{n}.C{m}` qualified ids; unmatched-row exemptions for superseded and current-outline rows; new
`override_head_recorded` / `override_head_error` return fields. **Existing tests changed:**
`test_loop_back_close` lost its byte-identical / same-inode "close does not rewrite status" assertion
(now a parsed compare excluding the override key); the paraphrase and citation tests were adapted.

## Metrics and Anomalies

- Tokens (`opencode.db`; the landing said `unknown`): input 1,448,307 (root 1,019,039), output 125,173,
  reasoning 146,094, cache read 141,361,408. **Cost $0.80** (root $0.63, reviewer $0.17, precursor $0.01).
  PLAN-LB-72: $0.80; PLAN-LB-59: $0.62.
- Wall clock 18:55Z (first invocation) to 03:26Z, **8h31m**; root 19:19Z-03:26Z. About 5.5 h of external
  waits (comment waits 3.5 h, checks 1.6 h, queue 0.4 h) plus about 1.2 h of local builds. No provider
  interruption, no resume, no compaction; two long-wait cache misses (139k and 382k uncached input).
- Models: `deepseek-v4.1-flash` / `high` for all sessions.
- Tests: `verify` 31,396 on the merged head `0e18f21ac`; the PR body's "31,364" is the earlier `c8d8cfae7`
  run and was never updated. `c8d8cfae7`'s own CI was still running when `1f127d257` was pushed, so its
  result is unknown.

## Routing and Merge Behavior

- **Review.** Seven commits; PR opened 20:52Z at `c8d8cfae7`. cuioss-review-bot reviewed at 20:55Z (one
  inline suggestion, fixed in `1f127d257`); its guides now read "updated until `0e18f21ac`" (earlier
  attestations were overwritten and cannot be checked). CodeRabbit formally reviewed `c8d8cfae7` (20:59Z),
  `1f127d257` (00:23Z) and `dbbae6597` (02:04Z); every finding fixed and all **6 of 6 threads resolved**.
  CodeRabbit refused re-triggers at 22:46Z, 00:29Z, 02:10Z and 02:33Z. **Two waits were 90 minutes**
  (21:15→22:45, 00:29→02:00); the third re-trigger came 23 minutes after the 02:10 refusal and the
  standing authorization was then invoked (the landing's "90-minute waits observed" over-states this).
  Sourcery refused on a hard quota; its check passes on the merged head.
- **CI / merge.** All 11 checks pass or skip on `0e18f21ac`; no check re-run; merge-group run
  `39361857819` succeeded. Enqueued 02:58:40Z; settled about 03:18-03:24Z (`e1481166c`'s timestamp is the
  merge-group commit, not the merge). `0e18f21ac` merges `origin/main` (#1821, 24 files) into the branch
  and changes none of the PR's 16 files — **the two concurrent runbook plans did not collide**, as the
  surface gate predicted.
- **Merge legitimacy: covered by the standing authorization, but thinly.** A qualifying CodeRabbit review
  exists on `dbbae6597`; its finding (the re-freeze race) was fixed in `c83f8b793`; a re-trigger after the
  last push was refused at 02:33Z; every other gate held. **`c83f8b793` — a Major concurrency fix with
  new code — and the merge commit `0e18f21ac` were never reviewed by CodeRabbit, and its next review window
  opened about a minute after the enqueue**; the review was not requested again, and the fix carries
  defect 2 above. The policy permits the merge; it does not make the fix reviewed.

## Process

- **Operator questions: one, not none.** The precursor session asked at 18:56:26Z that the spec was not on
  main and whether to land the ledger; the answer ("I land the ledger, then run LB-74") was followed by
  `orchestrator land snapshot` (`in_flight`, bound PR #1820) and the session was interrupted at 18:57Z.
  The landing's "none asked" and "no free-text beyond the initial invocation" describe the root only; the
  run was invoked twice.
- **Lane text.** Stale as for PLAN-LB-59: no `order` field, no "not met as written", no `test-compile`, no
  "`self-review: clear` forbidden with an open finding", no question-recording rule. The landing has none
  of the corresponding fields. Install-sync debt, not a run defect.
- **Skills and personas (verified loads).** Root: `runbook-lane`, `persona-implementer`, `python-core`,
  `pytest-testing`, `plugin-architecture`, `plugin-script-architecture`, `ref-code-quality`,
  `persona-module-tester`, **each once at 19:19Z** — "loaded per deliverable" is over-precise. Child:
  `persona-code-reviewer` once, kept in context for rounds 2 and 3. **The root never loaded
  `persona-code-reviewer`, so the landing's "applied … to triaging every PR comment" is false**; the root
  triaged all six threads itself.
- **Fail-first order.** Genuinely test-first (13 failed, 4 passed at 19:28:11Z; first production edit
  19:30:25Z): D1 both, D2 positional/unmatched/reject, D3 lock and key refusal. **Not test-first:** D4
  (failed only on `TypeError`), the D3 override-head test (never run pre-fix), the D2 preservation clause
  (failed pre-fix, never re-run), and all three review-fix commits (`1f127d257`, `dbbae6597`,
  `c83f8b793`: production before tests, no failing run). "All four deliverable tests were written first and
  seen failing against the unfixed tree" is false for D4 and the override-head test.
- **Self-review.** Three rounds (12, 6 and 0 findings), reported honestly as ready to open; all real.
  **Nothing after `c8d8cfae7` was self-reviewed** — `1f127d257`, `dbbae6597` and `c83f8b793` went to the PR
  without a round, and round 1 warned that no run against `a297ea762` was visible to it.
- **Rule breaks.**
  - Disclosed: one `git -C … grep` (confirmed, 20:29Z).
  - **Undisclosed:** an argparse rejection (`orchestrator land status --slug`, unknown flag); `execute`
    code-mode calls in the precursor and the reviewer (one tried `tools.shell` and got "Unknown tool");
    a build auto-backgrounded with its output file read twice; a direct `git worktree remove` in place of
    the git-workflow verb; thread-reply refusals and two stuck pending reviews; two failed edits.
  - Not found: pipes, `&&`/`;`, shell `cat`/`head`/`tail`/`find`/`ls`/`sleep`, `python3 -c`, `gh`/`glab`,
    `--force`, `--no-verify`, `stash`/`reset`/`amend`. All source edits stayed in the plan worktree; the main
    checkout is clean. The guard log holds no line for these sessions, which is weak evidence (the guard
    has no `git grep` rule and the reviewer used the `execute` tool).
- **Trailers.** All seven commits end with exactly `Co-Authored-By: plan-marshall <noreply@cuioss.de>`;
  every push a fast-forward; no wip, amend or force-push.
- **Report truthfulness: about ten contradictions,** mostly over-claims: the operator-question count; the
  D4 and override-head fail-first statements; D2 preservation "holds before and after"; skills "loaded per
  deliverable"; the persona-in-triage statement; the "one rule break"; `total_tokens` unreadable though
  stored; "no surface drift"; the stale PR-body test count; the omitted lane-text staleness and D3
  defects. **Credit:** the D3 spec-defect finding is honest, correct and precisely evidenced, and the run
  followed the deliverable body rather than forcing the false label.

## Runbook-Lane Process Grade — **C** (about C+ on execution)

- **Credit:** genuinely test-first on the core D1/D2/D3 bullets; three self-review rounds with the persona
  really loaded and real findings; all six threads handled and resolved; the D3 spec defect reported
  rather than forced; no main-checkout edits; clean trailers and fast-forward pushes; two predicted-disjoint
  plans merged without collision; $0.80.
- **Debits:** the last three code commits (one a Major concurrency fix) neither self-reviewed nor
  CodeRabbit-reviewed, with defects 1 and 2 shipped; the operator-question and fail-first statements
  false; D3's intent not met while the PR body says otherwise; undisclosed small rule breaks; the root
  never loaded `persona-code-reviewer`; eight and a half hours of wall clock. Part of the lane-rule debit
  is the stale install. The grade is the orchestrator's judgement.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-74 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-LB-74 --field pr --value 1822`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-LB-74 --field landing --value landings/PLAN-LB-74.md`
- [x] row `plan_marshall_plan_id` stamped — `orchestrator queue --set-row PLAN-LB-74 --field plan_marshall_plan_id --value lb-74-lb-70-integrity-fixes`
- [x] epic.md narrative reconciled (queue annotation, Open Defects, Watches)
- [x] fix-forward staged as PLAN-LB-77; the spec-authoring lesson folded into PLAN-LB-69
- [x] resume anchor updated in `resume_anchor.md`
- [x] `queue-view.md` regenerated

## Follow-Ups

- **PLAN-LB-77 `lb-74-completion`** (high): the status-writer lost update (defect 1), the `authorize_change`
  guard scope and log ordering (defect 2), the text-arm conflicting id, the inert top-level key and the
  non-atomic rollback. Shares `_criteria_snapshot.py` and `manage-status/scripts/` with the staged
  PLAN-LB-75; the gate sequences them and PLAN-LB-77 goes first because it repairs what D3 meant to.
- **PLAN-LB-69** takes a second Done-when authoring rule: a clause whose premise the same spec labels
  HYPOTHESIS is not given a "holds at {sha}" label until the hypothesis is settled.
- **Operator action owed:** `/sync-harnesses --target opencode` (see PLAN-LB-59).
- **`total_tokens`:** unknown again (seventh OpenCode runbook landing); PLAN-LB-49 owns it.
