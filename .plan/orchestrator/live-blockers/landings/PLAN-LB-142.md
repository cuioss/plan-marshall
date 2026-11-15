# Landing Analysis: PLAN-LB-142 — a handled CodeRabbit review is the review

epic: live-blockers
workstream: WS-05
pr: #1959 (merge commit `280e6c4040f1b6120984834a99b76afc137dc697`, merge-group run 43015720042)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying claims against ground truth (actual code, artifacts, PR state) — a pasted claim is a lead, never a fact.

## Deliverable Fidelity vs Spec

Two messages arrived from the runbook lane, both from sender `rb-lb-142-coderabbit-review-done-after-handling`. Message 001 (PR open, `reviews:blocked,merge:blocked`) was a parked-state landing written while CodeRabbit refused on quota; message 002 is the merged state and supersedes it. 001's `merge_state=open` was true when written and is stale now — the PR reads `merged` through the `ci` abstraction (`ci pr view --pr-number 1959`: `state: merged`, `merge_commit_sha 280e6c404…`). Both messages are `complete: false` on `total_tokens` alone (out of scope, as for every runbook landing in this epic); both are drained against the one report.

The facts block of 002 agrees with ground truth: `pr`, `merge_state=merged`, `deliverables 4/4`, `unresolved_review_threads=0`. `review_body_findings_total=17` equals the provider's count from `runbook_lane review-gate --pr-number 1959` (17 ids: `inline-1`…`inline-16`, `nitpick-1`). `review_body_findings_handled=17` was re-read from the run's progress file: every one of those 17 ids carries a `finding:` line with a fix commit or a stated reason (`inline-13` and `inline-14` are the two answered-with-reason). The bare `review-gate` re-run reports `handled: 0` and `merge_allowed: false` because it holds no dispositions input — not a difference. The progress file also carries three `outside-diff` findings the provider count does not include, each with a fix commit. `sonar_open_new_issues=n/a` (the project has no Sonar). No false claim found.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — a flagged bot with a qualifying, handled review is complete at any later head | shipped-as-specified | `bot_registry.review_complete_after_handling`, `classify_bot` done arm (`review_completeness.py:982-988`, re-read), `trigger-bot` withholds the bot, `coderabbit.md:45` sets the flag; tests `test_review_complete_after_handling.py` (leaf) |
| D2 — no path posts or awaits a trigger once the review is on record | shipped-as-specified | `request_fresh_review` refuses `review_on_record_done` before the rate-window guard (`github_re_review.py:1236-1252`, leaf); `resolve_recovery_action` done arm (`:1004-1017`, re-read) |
| D3 — the merge gates accept a done review without a review of the head | shipped-modified | `pre_merge_gate._check_participation` forwards `finished_review_bots[]` (leaf); `runbook_lane.resolve` emits the flag. **Beyond the spec:** `review-gate --required-reviewer` (a per-reviewer evidence check, `runbook_lane.py:2832-2846`, leaf) — see L2-2 |
| D4 — the prose and the pins say the same thing | shipped-modified | 12 documents pinned with mutation controls; but two statements disagree with the code — see L2-1 |

Files no deliverable names: `github_pr.py` / `_github_pr.py` (`finished_review_bots[]`, the producer of D1's and D3's input) are on the spec's Expected Surface under its own "only if the producer must report which bot holds a qualifying review" HYPOTHESIS, which the self-review settled as needed. Two Expected-Surface files were untouched (`planning-workflow.adoc`, `phase-6-finalize/SKILL.md`); the leaf read both for re-trigger/quota wording and found nothing the rule makes wrong.

## Three-Layer Analysis

The landing was read on three layers by one read-only leaf (`execution-context-level-5`, `orchestrator.analyze` surface), and the orchestrator re-read the points marked as re-read. The reading is **by reading, no build, no test run, no write**.

- **Dispatch:** one read-only leaf per landing — reason: reading merged code is the depth the dispatch rule exists for; this is the only full-ship landing of the drain (message 001 is the same plan's interim state).
- **Verdict:** layer 1 clean; layer 2 findings (3: all minor); layer 3 findings (1 major, 5 minor) plus one point not shown by reading. The major is L3-1, reported to the operator at once.

Re-read at `github_re_review.py` 996-1026 and 1876-1946, `github_pr.py` 2196-2228, `review_completeness.py` 978-1038, plus the progress file and the provider through `review-gate` and `ci pr view`. **Not re-read** (unverified leads, recorded as such): `runbook_lane.py` 2669-2718 and 2832-2846, `pre_merge_gate.py` 956-1023, `github_re_review.py` 926-933, 1075, 1236-1252 and the import lines of the module, `workflow-integration-github/SKILL.md` ~1333, `_github_pr.py` 189 and 585, the downstream steps of L3-1's loop (`trigger-bot` listing, the step-done guard, the pre-merge refusal), the test lines the leaf cites, and the conformance wording claims.

### Layer 1 — Specified

| Finding | Claim | Verdict | Polarity | Evidence (file:line) |
|---------|-------|---------|----------|----------------------|
| L1-1 | The premises and Done-when conditions agree with each other and with `main`: a qualifying review is a formal review with a commit or a `kind=reviewed` marker naming one; done stops requests, not handling; no review on record leaves the first trigger and the quota policy | checked (leaf) | confirms | spec; `github_re_review.py:1004-1017` (re-read) |
| L1-2 | The rule goes as far as the spec chose: a done bot settles ahead of a later structural size refusal, so a later diff of any size merges without the bot reading it. A risk the spec accepted, not a defect | checked (leaf; the arm itself re-read) | confirms | `review_completeness.py:982-988`, `github_re_review.py:1004-1017` |

**Layer 1 verdict:** clean. No finding names a corpus claim of a staged spec of this epic, so no re-grounding verdict is persisted.

### Layer 2 — Implemented

| Deliverable | Code trace | Test that can fail | Unexplained file / unborne claim | Verdict |
|-------------|------------|--------------------|---------------------------------|---------|
| D1 | `review_completeness.py:982-988`, `bot_registry.py` | `test_review_complete_after_handling.py` (leaf, with matched negatives) | none | checked |
| D2 | `github_re_review.py:1004-1017, 1236-1252` | `test_review_complete_after_handling_re_review.py` (leaf) | none | checked |
| D3 | `pre_merge_gate.py:1008-1023`, `runbook_lane.py` | `test_review_complete_after_handling_gate.py`, `test_runbook_lane_review_gate.py` (leaf) | `--required-reviewer` (L2-2) | checked |
| D4 | documents, `test_review_complete_after_handling_docs.py` | planted-sentence controls (leaf) | the code/prose disagreement (L2-1) | checked |

- **L2-1 (minor):** D4 says the prose and the pins agree, and they do not on one arm. The code admits `REVIEW_ON_RECORD_UNDECIDABLE` into the done arm (`github_re_review.py:1007`, re-read; a test pins it, leaf), and the done arm runs ahead of every cause, window and budget arm (`:997-1004`, re-read). The `resolve_recovery_action` docstring (item 8, `:926-933`) and the `workflow-integration-github/SKILL.md` prose (~1333 and its table row) say the arm takes credited or stale only, that `undecidable` always resolves `unmeasured`, and put the arm after the window arms (leaf; **docstring and SKILL half not re-read**).
- **L2-2 (minor):** `review-gate --required-reviewer` is on the declared file (`runbook_lane.py`) but no deliverable names it; D3 covers only `resolve` emitting the flag. The lane's report discloses it as a D3 element, so this is an unnamed scope addition rather than an undisclosed one (leaf).
- **L2-3 (minor):** the scoped-join control in `test_trigger_b_stale_set_from_participation.py` (~388) switched its subject from `coderabbit` to `sourcery`, removing CodeRabbit coverage from the PR-scoped join test; the done filter needs `finished_review_bots`, which that helper never passes, so the switch was not required (leaf; not re-read).

**Layer 2 verdict:** findings — 3 (3 minor)

### Layer 3 — Correct

| Defect | File:line | Triggering input | Effect | Severity |
|--------|-----------|------------------|--------|----------|
| L3-1 | `github_re_review.py:1934-1942` against `github_pr.py:2215-2220` (both re-read) | a CodeRabbit `review_body` whose `commit_id` is empty (the GraphQL field is nullable, leaf: `github_ops.py:771-773`), carrying no finished marker, on a pull request whose head has moved on | The post chokepoint's `_qualifying_review_on_record` returns `True` for any `review_body` that is not a refusal (`:1941`: `not _is_refusal_body(...) or review_coverage_names_commit(...)`), with no `commit_id` test. The producer admits the same record to `finished_review_bots` only with a non-empty `commit_id` or a marker naming a commit (`github_pr.py:2219`). So the producer leaves the bot out, `classify_bot` reads it `participated_stale` (`review_completeness.py:1034`, re-read), and `trigger-bot` lists it — while every re-review post is refused with `review_on_record_done`. Leaf: the step-done guard then loops back and the pre-merge gate refuses until an operator authorizes (**the loop-back and the refusal were not re-read**). The leaf also found a test that pins the empty-commit case at `test_review_complete_after_handling_re_review.py:141` (not re-read). The lane's own check and the producer reject this artifact; the chokepoint alone admits it | major |
| L3-2 | `github_pr.py:2205-2222`, `github_re_review.py:1927-1946` (both re-read), `runbook_lane.py:2696-2718` (not re-read) | a `review_body` with a commit that only the enumerative refusal arm reads as a refusal | One concept — a qualifying review — has three readers with different refusal arms and different commit requirements (the producer: `_is_refusal_notice` with a `review_coverage_is_finished` exemption; the chokepoint and the lane: `_is_refusal_body`, which adds the enumerative arm, with a `names_commit` exemption). The producer reports done, the chokepoint still posts, and the lane's `review-gate` answers `required_review_missing`. The docstring's reason for the duplication (`github_re_review.py:1879-1884`, re-read) is that `_is_refusal_notice` lives in a module that imports this one; the leaf reads it as false (`_github_pr.py:189`, already imported at `github_re_review.py:270-292`) — **not re-read**. Breaks "one reader per concept" | minor |
| L3-3 | `review_completeness.py:1027-1034` (re-read) | reading the branch | The comment at 1027-1029 says a refusal or decline on the candidate still outranks this branch; the code does the opposite (the done arm at 982-988 returns before the refusal arms at 991 and 997), and the comment's own next lines (1031-1033) say so | minor |
| L3-4 | `_github_pr.py:~585` (leaf) | a review marker naming a commit outside the pull request, written by the bot's own login | `review_coverage_names_commit` accepts any non-empty `coveredCommitId` / `sourceCommitId`, and a `review_body` `commit_id` is never checked against the PR's heads, while the spec says "on one of this pull request's heads". The lane answers the same question only by presence (the lane's own residue: inline-13, answered with reason). Exposure is limited to what the bot itself writes | minor |
| L3-5 | `runbook_lane.py:~2692` (leaf) | a marker quoted inside a fenced block in a flattened body | The lane re-splits a flattened body by inserting a newline before every `<!--`; flattening has already erased the fence lines, so the fence-aware parser cannot tell a quoted marker from a real claim, and it would count as a qualifying review. The lane also imports the private `_is_refusal_body` of another skill's script | minor |
| L3-6 | `github_re_review.py:~1075` (leaf) | reading the comment | The comment says a flagged bot "never reaches this line"; a flagged bot with no review on record does reach `close_and_reopen`, as the test at `test_review_complete_after_handling_re_review.py:467-478` asserts | info |

**Layer 3 not shown by reading:** L3-7: on the phase-6 path `pre_merge_gate` has no thread check, so whether an open thread with no pending finding blocks the merge (spec point 5) rests on branch protection or the respond pipeline; the lane path blocks it (`runbook_lane.py:2847`, leaf). Only a run could settle it.

**Spec-premise point recorded, not settled:** the spec asserts close-and-reopen changes the pull request number and so resets done. The leaf reads the mechanism as keeping the number and its history, so done is not reset on a same-number reopen, though `close_and_reopen` is only reachable with no review on record (`:1084`, after the done arm at `:1004`), so the two never meet (leaf; **not re-read**). Recorded as a Watch.

**Layer 3 verdict:** findings — 6 (1 major, 4 minor, 1 info) plus 1 not shown by reading

### Conformance to the Project's Own Rules

| Rule source | Rule | Verdict | Evidence |
|-------------|------|---------|----------|
| CLAUDE.md § Documentation Standards | no version history, no timestamps | conforms | leaf: no dates or changelog sections added |
| CLAUDE.md § Documentation Standards | current state only | deviates | leaf: comparative wording — "the behaviour it had before either flag existed" (`bot_registry.py`), "keeps today's behaviour" (`branch-cleanup-rereview.md:15`), "triggered exactly as before" / "posts exactly as before" (`review_completeness.py` `list_bots_for_trigger` docstring, `github_re_review.py:1232-1233`); not re-read |
| CLAUDE.md § Script Execution Convention | scripts via the executor | conforms | leaf: every new prose invocation uses `python3 .plan/execute-script.py` |
| project code rule | fail closed on unreadable state | conforms | the flag is false unless the record sets it; done needs a positive finished-review observation (`review_completeness.py:986`, `github_re_review.py:1006`, re-read); an incomplete fetch is refused (leaf: `pre_merge_gate.py:956-984`) |
| project code rule | one reader per concept | deviates | L3-2 |
| automatic-review registry contract | bot behaviour is registry data, no bot-name literal in code | conforms | leaf: the flag is read only through `bot_registry.review_complete_after_handling` |

## Metrics and Anomalies

- Tokens: `unknown` — the harness measured none (out of scope).
- Duration: not measured by the lane; the guard log's first entry for the run is 21:49Z on 2026-11-10 and the merged landing message is 12:25Z on 2026-11-11. The largest identifiable share is the CodeRabbit quota wait (two 90-minute windows, two refusals at 02:35Z and 04:29Z) and merge-queue waits of up to about fifteen minutes per build submission.
- Anomalies: none beyond the quota wait. The lane recorded three guard refusals, two `R2` (`mv`) and one stray `R5`, none retried; the guard log's other entries belong to other sessions. One operator "retry" was read as a resume signal, not as merge permission.

## Routing and Merge Behavior

- Review: coderabbit (required, `quota_limited`, `review_complete_after_handling`) refused twice on quota, then reviewed `88b6d2695` at 06:34Z; three further automatic reviews followed on later heads under the bot's own configuration. All 17 review-body findings were disposed (15 fixed, 2 answered with a reason), and the two threads were replied to and resolved. Sourcery (optional) refused on `cause: size` and gates nothing. **This plan was its own first test:** it merged on a review of an earlier head with every finding handled and no review of the merge head. `unresolved_review_threads=0` and `review_body_findings_total=17` match the provider's `review-gate` re-read on the merged PR; `handled=17` matches the progress file's 17 dispositions. No false claim.
- CI/merge: `verify / verify` green on each pushed head, merged through the merge queue as a squash commit (`280e6c404`).
- Sonar: `n/a`, the project has no Sonar.

## Reconciliation Actions

- [ ] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-142 --status shipped`
- [x] row `pr` stamped — the row already carries `1959`
- [ ] row `landing` stamped — `orchestrator queue --set-row PLAN-LB-142 --field landing --value landings/PLAN-LB-142.md`
- [x] row `plan_marshall_plan_id` stamped — the row already carries `rb-lb-142-coderabbit-review-done-after-handling`
- [ ] epic.md narrative reconciled: a PLAN-LB-142 annotation, the PLAN-LB-144 hold released, L3-1 and L2-1 as Open Defects, the Watches below
- [ ] resume anchor updated in `resume_anchor.md`
- [ ] `queue-view.md` regenerated and committed with the row change

## Follow-Ups

- L3-1 is a defect in code that has already shipped and can strand a pull request in a loop-back until an operator authorizes; it is reported to the operator and NOT fixed inline, and becomes a staged fix-plan spec only on the operator's word.
- L2-1, L3-2, L3-3, L3-4, L3-5 and L3-6 are minor and cluster on the same three files (`github_re_review.py`, `github_pr.py`, `runbook_lane.py`); they are one candidate follow-up with L3-1, not six.
- The close-and-reopen premise, the phase-6 thread question (L3-7) and the "current state only" wording are Watches.
