envelope_version=1
sender_type=plan
sender_id=rb-lb-129-review-gate-thread-and-count-truth
epic=live-blockers
kind=landing
created=2026-11-09T21:52:22Z

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-129-review-gate-thread-and-count-truth
epic=live-blockers
pr=#1947
merge_state=merged
cleanup_owed=false
deliverables_total=3
deliverables_done=3
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash/high
effort=high
plugin_version=0.1
executor_version=0.1.2076
steps=setup:done,implement:done,build-gate:done,self-review:clear,pr:done,reviews:done,merge:done
unresolved_review_threads=0
review_body_findings_total=4
review_body_findings_handled=4
sonar_open_new_issues=n/a
step.sonar-roundtrip.open_issue_rules=n/a
```

guard: present (the guard refused one main-checkout edit and the run corrected it; see Rule check).

# Landing — PLAN-LB-129 review-gate thread and count truth

PR #1947 merged into `main` as `d1e4b512850fe81ac08f824098fd6d0eaa8f69da`. Branch `fix/lb-129-review-gate-thread-and-count-truth` pruned locally and remotely; worktree removed; main checkout switched and pulled to the merge commit.

## 1. Deliverables

| Deliverable | Done-when | Verdict | Order | Test | Failing run (commit + output id) | Commit |
|---|---|---|---|---|---|---|
| D1 — a resolved thread is read by its last BOT comment | four-comment thread (`coderabbitai` restatement, `octocat` "done") gives `merge_allowed: false` / `thread_concern_remains` | met | test-first | `test_a_lane_reply_below_the_bot_s_restatement_does_not_discharge_the_concern` | `0eba20d3a`, job `7daf67675b66412980f7c9be3998f57d.log` lines 9-10 (`assert True is False`) | `818508446` |
| D1 | the case joins the `_only_unresolved_threads_stub` parametrization | met | test-first | `test_each_refusing_case_is_red_against_the_unresolved_threads_only_stub[concern-remains-after-lane-reply]` | same run, line 10 | `818508446` |
| D1 | must-keep cases (fifth bot "Addressed in commit def5678."; bot-ack-then-human; bot-confirms-beside-new-concern; single opener refused) | met | none (controls) | `test_a_later_bot_acknowledgement_after_the_restatement_admits_the_merge` and the three existing controls | green at base | `818508446` |
| D2 — count from the declared count | `Nitpick comments: 3` + three row markers → 3 findings | met | test-first | `test_a_colon_counted_section_counts_its_declared_findings` | `818508446`, job `264827a428ea43afa96368045dcd38ce.log` line 9 (`1 == 3`) | `232ac8ba1` |
| D2 | `Nitpick comments: 3` + one disposition keeps the gate closed | met | test-first | `test_one_disposition_does_not_clear_a_colon_counted_section_of_three` | same run, line 10 (`True is False`) | `232ac8ba1` |
| D2 | an undeclared count is not read as one (row markers count) | met | test-first | `test_an_undeclared_section_counts_its_row_markers` | same run, line 11 (`1 == 3`) | `232ac8ba1` |
| D2 | `Potential issues: 2` and `Potential issues (2)` are undecidable | met | test-first | `test_a_counted_title_that_is_neither_a_section_nor_a_label_is_undecidable[2]` | same run; `build-results/plan-marshall/python-2026-11-09-102011.log` lines 28-29, 67-72, 95-96 | `232ac8ba1` |
| D2 | must-keep: clean body reads zero; a recognised `(N)` section counts N | met | none (controls) | `test_a_clean_pull_request_admits_the_merge`, `test_a_nested_file_summary_is_not_read_as_an_unreadable_section` | green at base | `232ac8ba1` |
| D3 — evidence is a real commit or reason | `— TBD`, `— -`, `— n/a` do not dispose | met | test-first | `test_a_placeholder_evidence_does_not_dispose_the_finding[7]` | `232ac8ba1`, job `62311575573d4ad7a049095c16df64f9.log` lines 9-15 (`assert True is False`) | `614432772` |
| D3 | `— fixed in a1b2c3d` and `— declined: …` do dispose | met | none (control) | `test_a_real_commit_or_reason_disposes_the_finding[3]` | green at base | `614432772` |

Per-head test runs: the review-gate module was green at each pushed head during the run (jobs `c279202811d04189a460bf51fc8eafb9`, `52af4c0c76fe41f48eb3ecaa4419c68f`, `0f0b8e9ad1384d52b911865b86782274`, `2785e6617c96423a8582f79ef587647d`, `9521e1f8038b4425be9263aa530f89bc`); full `verify` green at `614432772` (job `6a8c5afdda5449cc852267a25aca4887`), at `7a1eca316` via CI, and at the final head `4593559fc` (local job `6e40e6922da7487c93d0309e8aadb632`; CI "verify / verify" success).

## 2. Personas and skills

- Production code: `persona-implementer`; tests: `persona-module-tester`; every self-review round and the PR-comment triage: `persona-code-reviewer`.
- The spec declares no `Skills:` or `Persona:` lines (`skills: none named`); no skill was added for surface drift.

## 3. Hypotheses

- D1 `outdated` flag: confirmed — no `outdated` key anywhere in `workflow-integration-github/scripts/github_pr.py`, and the captured inline record carries `kind,id,thread_id,author,body,path,line,resolved,created_at,updated_at,commit_id,reply_to_id,thread_reply` only. The rule ignores it either way.
- D2 counted non-finding titles: confirmed for `Files selected for processing: 19` (observed with its count) and for the uncounted `Review info` / `Run configuration` / `Commits`; **refuted for `Additional comments (N)`** — the #1940 capture carries no such block. The shape is therefore counted as an `additional` findings section (fail-closed, no false pass) rather than declared non-finding.

## 4. Findings

Self-review (4 rounds, sub-agent `persona-code-reviewer`):
- round 1: 7 findings — decorated-title counts, `Additional comments` placement, stale docstrings, label provenance, colon location; 7 addressed (one fixture change was forced by D2 and kept its assertions).
- round 2: 9 findings — `Additional comments` wrongly declared non-finding (fail-open) corrected in round 3, count aggregation to `max`, SKILL enumerations, test provenance.
- round 3: 4 open + 1 advisory — `Additional comments` counted; provenance corrected; SKILL text aligned; parametrization split. Operator authorized a fourth round.
- round 4: 5 findings, 0 blocking / 0 false pass — test-docstring provenance, SKILL enumeration and empty-block wording, `review details` provenance fixed; the `Additional comments` capture gap recorded as a stated limitation.
- `self-review: clear` on the final head.

PR review (coderabbit @ `59e4315da`, 4 nitpicks):
- `finding: coderabbit nitpick nitpick-1 — declined` (whole-evidence rule; a per-word check would refuse a stated reason containing a placeholder word; boundary pinned by `test_a_placeholder_embedded_in_a_stated_reason_is_a_stated_reason`).
- `finding: coderabbit nitpick nitpick-2 — declined` (the label list is the verb's observed vocabulary; moving it into `bot_registry` is a separate refactor; a new counted title fails closed).
- `finding: coderabbit nitpick nitpick-3 — 7a1eca316`.
- `finding: coderabbit nitpick nitpick-4 — 7a1eca316`.

`review-gate` on the merge head `4593559fc`: `unresolved_review_threads: 0`, `review_body_findings_total: 4`, `review_body_findings_handled: 4`, `merge_allowed: true`.

## 5. Reviewers

- `coderabbit` (required, `quota_limited: true`): reviewed `59e4315da` (review `PRW…`, 4 nitpicks) and `7a1eca316` as a clean marker-bearing summary (`coveredCommitId: 7a1eca316`, `kind: reviewed`). Re-triggered at 18:33 and again at 19:36 after the final head; refused at 19:36:14 as "Already reviewed the last commit" (the merge commit carried only ledger files). Standing review authorization applied: qualifying review on a PR head, all findings handled, re-trigger after the last push recorded.
- `sourcery` (optional, `quota_limited: true`): refused on hard quota ("2 days and 7 hours", 2026-11-09T17:29:14Z); optional, so no gate impact.

## 6. Operator questions

1. "The self-review hit its 3-round limit… how should I proceed?" — options: Run one more review round / Open the PR now / Stop before the PR. Selected: **Run one more review round**.
2. "Which evaluator should decide this merge?" — options: Merge on the branch's gate verdict / Use the installed pre-fix gate / Stop and report blocked. Selected: **Merge on the branch's gate verdict**.

No free-text operator messages.

## 7. Rule check

- Guard: present. The guard log has one line for this run: `R7` at 2026-11-09T08:55:14Z refused an edit to `test/plan-marshall/runbook-lane/test_runbook_lane_review_gate.py` in the main checkout; the run immediately re-applied it in the worktree (`R7` is the main-checkout write rule). No other guard refusal.
- Shell file operations: none of `cat`/`ls`/`grep`/`find`/`head`/`sed`/`git grep` were issued. One non-file system read was issued outside the repository: `df -h /tmp` (disk usage only, no file content) to confirm the ENOSPC failure was environmental. Reported here as the run's own action.
- Environment/tooling failures (not code): the first full `module-tests` hit the known xdist target-tree race (`target/claude` "Directory not empty", job `7daf67675b66412980f7c9be3998f57d`); a routed `verify` failed 1049 tests on transient `No space left on device` in `/tmp` (job `d9c37b6035754837a0cafddd13e4bb3f`); one targeted build carried a multi-word `--filter` the build wrapper cannot split (job `f915b502593145a387771e120f26c7b8`). None was a failure in a module touched by this plan; each was re-run green.
- Build routing: every build submitted with the default routing and ran `daemon_longpoll`; no degradation and no launch-fault retry.
- Restarts: none. One `worktree-create` shell call exceeded the tool timeout at 120 s; the verb had already created the worktree, and re-running it completed the setup (`worktree_exists` with `executor_in_worktree: present`).
- Spec read: `resolve` read the ledger worktree copy (`spec_source: ledger_worktree`); no `spec_differ` marker was reported, at setup and at landing time.
- `executor-skew`: `not_applicable` (the lane text lives in this source checkout, where the executor maps the checkout's own scripts); answered and recorded, never asked about.

## 8. Build server

Setup preflight: `ready` (project enrolled). Builds by mechanism: `daemon_longpoll` for every build; `in_process_fallback`: 0. Fallbacks/retries: none — every build was submitted, and live results were re-attached with bounded waits. No `killed` job. No `runtime_stamp_reason`.

## 9. Residue

- The merge gate was evaluated with the branch's own (fixed) `review-gate`, per the operator's selection; the main checkout's installed gate ran the pre-fix code during the run (it read this PR's same body as 0 findings — the false pass D2 closes). Future runs on `main` carry the fixed gate.
- `Additional comments (N)` is counted fail-closed because no capture carries it; a capture showing it is boilerplate would let a later plan declare it non-finding.
- Watch item: a combined title such as `Outside diff range and nitpick comments (N)` matches no label and is refused as `undecidable_read` (fail-closed, no false pass).
- Sourcery remains on hard quota for ~2 days (optional reviewer).
