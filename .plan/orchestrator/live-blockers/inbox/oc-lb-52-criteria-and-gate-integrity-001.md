envelope_version=1
sender_type=plan
sender_id=oc-lb-52-criteria-and-gate-integrity
epic=live-blockers
kind=landing
created=2026-10-17T18:28:09Z

```landing-facts
schema=landing-facts/1
plan_id=oc-lb-52-criteria-and-gate-integrity
epic=live-blockers
pr=#1798
merge_state=open
cleanup_owed=true
deliverables_total=2
deliverables_done=2
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash
steps=setup:done,implement:done,build-gate:done,self-review:budget-exhausted,pr:done,reviews:pending-coderabbit-quota,merge:open
```

# PLAN-LB-52 — criteria and gate integrity (stopped before the merge)

The plan is implemented, self-reviewed over three rounds, pushed, and green: CI and `verify` pass on the head `5b01f7f38`, and `cuioss-review-bot` has reviewed that head. The run is **blocked on the required reviewer `coderabbit`**, whose free-review quota is exhausted — repeated refusals ("Review limit reached" / "Action not completed — Review rate limited"), including the one-shot `@coderabbitai full review`. No merge was attempted; the required reviewer is never skipped.

## 1. Deliverables

Both deliverables are fully met. Every Done-when has a test that was **seen failing** on the pre-fix tree and passing after; each has a matched negative control.

| Done-when | Verdict | Test | Fail-then-pass |
|---|---|---|---|
| D1 (a) narrowed criterion yields a finding | met | `test_narrowed_criterion_yields_a_blocking_finding` (`test_criteria_integrity_d1.py`) | red at `02dfdf79f` (`ModuleNotFoundError: No module named '_criteria_snapshot'`, log `python-2026-10-17-130410.log`) → green (log `python-2026-10-17-125501.log`) |
| D1 (b) a verdict edited after the reviewer wrote it is refused | met | `test_verdict_edited_after_the_review_wrote_it_is_refused` | same |
| D1 (c) a deleted criterion with no operator decision is refused | met | `test_deleted_criterion_without_an_operator_decision_is_refused` | same |
| D2 (a) a branch deleting an assertion yields a finding | met | `test_branch_deleting_an_assertion_yields_a_finding` | red in the same pre-fix run → green (log `python-2026-10-17-125809.log`) |
| D2 (b) a "fails pre-fix" criterion evidenced only by a HEAD run is `unevidenced` | met | `test_pre_fix_criterion_evidenced_only_by_a_head_run_is_unevidenced` (+ green-mention and HEAD-failure arms) | same |
| D2 (c) a verdict citing a test name absent at the graded head is refused | met | `test_verdict_citing_a_test_name_absent_at_the_graded_head_is_refused` | same |
| D2 (d) a verify-first record after the gated commit is refused | met | `test_verify_first_record_after_the_gated_commit_is_refused` | same |
| D2 (e) finalize with an empty bot queue and one unmet Done-when does not exit | met | `test_finalize_with_an_empty_bot_queue_and_one_unmet_done_when_does_not_exit` | same |

Commits: `a69c3d29f` (D1) and `524593fed` (D2), then corrective commits `50acab439`, `55087f21f`, `fdaab4fad` (test typing and format), `64a1bdbb1` (the reviewer's citation-regex finding), `d411c452c`, `acf69c10c`, `88aef7cbb`, `5b01f7f38`. Test count in the two files: 26.

The pre-fix run used a detached worktree at the branch base (`02dfdf79f`); the four carrier files are byte-identical between the Done-when's named SHAs (`c8adaf178`, `f5d661d87`) and that base, and only `manage-solution-outline.py` differs (by PLAN-LB-42's landed outline Q-Gate work).

## 2. Hypotheses

- `functional-review.md:86-88`'s "freeze" compared the current outline with itself, and no snapshot existed — **confirmed** at `functional-review.md:88`.
- `review-rubric.md:66` counted a bare test identifier as evidence with no existence check — **confirmed** at `review-rubric.md:66`.
- The Done-When triage source was prose only and `_finalize_findings_refusal` read the findings store alone — **confirmed** at `plan-marshall/workflow/triage.md:36-38` and `manage-status/scripts/_cmd_lifecycle.py:895`.
- PLAN-LB-39's root rewrote `work/functional-review-verdict.json` with `python3 -c` (delegated agent's claim, OpenCode DB) — **not independently re-checked**; the mechanism it names is what D1(b) closes.
- PLAN-LB-42's outline held two deliverables for four spec deliverables, and its "fails on the pre-fix tree" criterion was graded `met` on "green in module-tests at HEAD" — **accepted from the spec's OBSERVED labels**; it is the shape the new `spec_criterion_missing` and pre-fix rules address.

## 3. Findings

- **Self-review round 1** (sub-agent, report-only): all 8 Done-whens met; 4 open — the frozen record's spec clauses were captured and never graded; `names_pre_fix_run` too loose; the rubric said a fabricated citation is "never refused" while the code refuses; the weakened-test wording overclaimed that a relaxed assertion is counted. **Fixed** in `d411c452c` (the spec-clause grading is now implemented, not merely re-worded).
- **Round 2**: 7 open — the finalize-refusal docstring said an unevaluable findings query proceeds; an added sentence named a nonexistent `weakened_test` verdict field; three sibling statements still claimed relaxed assertions are counted; the rubric overclaimed the verb's detection shape; the manage-status refusal table omitted `open_done_when_criteria`; a RED run at HEAD was accepted as pre-fix evidence. **All fixed** in `acf69c10c`. The `triage.md` exit-code-convention section was accepted as a guard-satisfying addition, not a Done-when.
- **Round 3** (the cap): 8 Done-whens met; 3 open — the verdict seal was enforced for `--kind code` while `code-review.md` never seals (it would have refused every code review on a snapshot plan); the rubric placed a dropped negative case in the verb-does-not-detect list; the rubric's unreadable-citation sentence contradicted the code. **All fixed** in `88aef7cbb`. Residue: `authorize_change` writes the decision log before the snapshot, so a crash between the two leaves a logged decision with no authorization.
- **cuioss-review-bot** (reviewed `524593fed`, then `fdaab4fad`, then `88aef7cbb`): finding 1, `EVIDENCE_PATH_RE` swallowed the `::` separator, so a class-scoped citation resolved to the whole string as a path and a valid citation was reported absent — **real, fixed** in `64a1bdbb1` with a segment-by-segment name check and a class-scoped test. Finding 2, a security concern: path traversal in `_referenced_spec_path` (request text) and `missing_evidence` (verdict text) — **real, fixed** in `5b01f7f38`, both readers now confined to the tree they read, with three tests. Its later "No major issues detected" review is on the current head.
- **CI**: red on `524593fed` only, because that head predated the test-typing fix; green on `88aef7f38` and on the current `5b01f7f38`.
- **Comment handling**: every surfaced comment is either fixed and pushed or (the CodeRabbit/Sourcery quota notices) recorded here; no thread was resolved without a fix or a reason. No inline review threads exist on this PR.

## 4. Reviewers

| Reviewer | State | Head | History |
|---|---|---|---|
| `cuioss-review-bot` | **reviewed** | `88aef7cbb` (head before the last fix commit; re-triggered on `5b01f7f38` at 15:50Z, its review of the traversal finding is what `5b01f7f38` answers) | triggered 13:43:40Z, 13:53:18Z, 14:16Z, 14:55Z, 15:50Z; reviewed each pushed head |
| `coderabbit` | **refused (quota)** — no review exists | — | triggered 13:43:59Z, 13:53:02Z (`@coderabbitai review`, both rate-limited), 17:16Z (rate-limited at 17:20:17Z), 18:56Z (`@coderabbitai full review`, once, rate-limited). Next allowed trigger 2026-10-17T18:50:17Z from the 17:20:17Z refusal (already elapsed); the later refusal re-arms the 90-minute clock |
| `sourcery` (optional) | refused (own budget: 250k diff chars / 7 days) | — | triggered 13:43:24Z |

## 5. Operator questions

1. "I edited the MAIN checkout instead of the worktree, and I need a decision on how to clean it up." Options: {Grant a one-time cleanup; Edit-tool restore only; Leave the checkout and record it; Stop the run}. **Selected: "Grant a one-time cleanup".** The grant could not be executed — `git restore` and `git clean` are both permission-denied for me — so the five tracked files were restored by inverting every edit with the Edit tool, and two untracked files remain (see §7).

No other question-tool call was made. Free-text operator messages: none in this session.

## 6. Rule check

- `guard.log` for this run's sessions shows **no line**, so no guard refusal was recorded for this run. Two shell calls were refused at the harness layer rather than by the guard (`git restore`, `git clean` — both `permission.rejected`), which is what forced the Edit-tool restore.
- Rules I did not keep: the main checkout was edited early in the run (the incident in §5 and §7); the two stray untracked files there are its residue.
- Everything else held: executor-only script and build calls, one command per shell call, no `gh`/`glab`, no `sleep`, no forbidden git operation, temp files only under `.plan/temp/` plus the `ci` body slots and this inbox message, and the commit trailer on every commit.

## 7. Residue

1. **CodeRabbit has not reviewed the PR** — the merge gate is not satisfied and no merge was attempted. This is the blocker.
2. **Main-checkout residue (2 untracked files)**: `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/_criteria_snapshot.py` and `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/_review_support_integrity.py`. They are byte-identical in intent to the merged files, but they occupy the paths the merge will deliver, so `switch-and-pull` on the main checkout will refuse until they are removed. No tool available to me can delete them.
3. **`uv.lock` is rewrite-dirty in the worktree** (uv resolved ruff 0.17.1 against the lock's 0.16.10 — environment churn, not part of this change and never staged). A build re-dirties it, so it needs removing after the last build.
4. **Detached probe worktree** `.plan/temp/oc-lb-52-criteria-and-gate-integrity/prefix-tree` (the pre-fix run) is still registered, with a 3-line stub `.plan/execute-script.py` and the two test files inside it.
5. Round-3 minor: `authorize_change` logs the operator decision before writing the snapshot; a crash between the two would leave a logged decision with no authorization recorded.
6. `build_snapshot`'s spec-discovery path (`_referenced_spec_path` + `_spec_deliverables`) has no test of its own; the spec-clause grading it feeds is tested through a hand-written snapshot.
