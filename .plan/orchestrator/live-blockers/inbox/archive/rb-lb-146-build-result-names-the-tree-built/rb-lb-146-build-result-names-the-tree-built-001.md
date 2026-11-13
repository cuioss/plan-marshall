envelope_version=1
sender_type=plan
sender_id=rb-lb-146-build-result-names-the-tree-built
epic=live-blockers
kind=landing
created=2026-11-13T09:23:29Z

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-146-build-result-names-the-tree-built
epic=live-blockers
pr=#1971
merge_state=merged
cleanup_owed=true
deliverables_total=4
deliverables_done=4
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash/high
effort=high
plugin_version=0.1
executor_version=0.1.2076
steps=setup:done,implement:done,build-gate:done,self-review:budget-exhausted,pr:done,reviews:done,merge:done
unresolved_review_threads=0
review_body_findings_total=9
review_body_findings_handled=9
sonar_open_new_issues=n/a
step.sonar-roundtrip.open_issue_rules=n/a
```

guard: present on this harness (`opencode`); two refusals this run, both named in § 7.

## 1. Deliverables

Base-sha evidence is a detached worktree at `280e6c404` (the base-sha recipe: the plan's committed test files copied in, run through the build seam). `order` is the lane's evidence order; the failing run's commit is that base sha.

**D1 — the build row and the freshness gate hash the same tree** (commit `5c33f6978`)

| Done-when | Verdict | order | Test | Failing run |
|---|---|---|---|---|
| main-checkout dispatch + plan `--plan-id` records the worktree hash, gate reads it as matching | met | mutation-after | `test_build_tree_identity_recorder.py::test_a_main_checkout_dispatch_is_read_fresh_against_the_worktree` (two real git trees, different content) | `7fed47733eee4e06ba8b0c351c6c799f.log` @ `280e6c404` — `AttributeError: _capture_dispatch_tree_state` |
| the row carries the root it hashed | met | mutation-after | `…test_the_row_is_hashed_against_the_plans_worktree_root`, `…test_a_plan_less_dispatch_records_the_working_directory`, `…test_an_unresolvable_root_records_no_hash` | same log — `KeyError: 'worktree_root'`, `resolve_plan_context` absent |
| a row hashed against another root reads as a root mismatch | met | mutation-after | `test_freshness_build_tree_identity.py::test_a_row_hashed_against_another_root_is_a_root_mismatch`, `…test_a_root_mismatch_wins_over_a_rewrite` | same log — base reads `fresh`, no `reason` |
| holds: dispatch from the worktree root records the same hash | met | none (hold) | `…test_a_dispatch_from_the_worktree_records_the_same_hash` — passes at base | — |
| holds: plan-less dispatch records the working directory's hash | met | none (hold) | `…test_a_plan_less_dispatch_hashes_the_working_directory` — passes at base | — |

**D2 — a rewriting build is named; a mid-build edit cannot fold into one green** (commits `5c33f6978`, `e6ad02840`, `a48dc07e6`, `19cd43b05`)

| Done-when | Verdict | order | Test | Failing run |
|---|---|---|---|---|
| a rewriting build records both hashes and the gate's reason names the rewrite | met | mutation-after | `test_freshness_build_tree_identity.py::test_a_row_whose_dispatch_hash_differs_names_the_rewrite` (reason + "commit the rewrite and re-run") | `7fed47733eee4e06ba8b0c351c6c799f.log` — base reads `fresh` |
| a build during which a file was edited records differing hashes | met | mutation-after | `test_build_tree_identity_recorder.py::test_main_captures_the_tree_before_the_build_edits_it` — drives the executor's own `main()`; the build child edits a tracked file | `7fed47733eee4e06ba8b0c351c6c799f.log` — `KeyError: 'worktree_root'`, child printed `status: success` |
| holds: nothing changed → equal hashes and a success row reads fresh | met | none (hold) | `…test_a_build_that_changes_nothing_records_equal_hashes` (head) + `…::test_equal_dispatch_and_completion_hashes_read_fresh` (passes at base) | — |
| holds: a re-run on the clean committed tree clears a stale verdict | met | none (hold) | `…::test_a_rerun_on_the_committed_tree_clears_the_rewrite_verdict` — passes at base | — |

One honest nuance: the "records equal hashes" half of the third hold clause is *new* recording (the field did not exist at base), so only its "reads fresh" half can be shown holding at base. Stated rather than glossed.

**D3 — a submit and its wait name the tree they built** (commits `73c3f73f4`, `a29cfff46`, `3b0739361`, `90badc686`)

| Done-when | Verdict | order | Test | Failing run |
|---|---|---|---|---|
| plan-less submit of the main checkout returns `exec_path`, `project_path`, `plan_id: NO_PLAN` | met | mutation-after | `test_build_server_tree_reply.py::test_the_submit_reply_names_the_tree_it_builds`, `…test_a_plan_less_submit_reply_states_the_sentinel` | `7cf7de20e9874c878f5c32a2fb7d7164.log` — `KeyError: 'exec_path'` / `'plan_id'` |
| the matching wait reply carries the same three | met | mutation-after | `…test_the_wait_reply_carries_the_tree_the_submit_named`, `…test_a_plan_less_wait_reply_states_the_sentinel` | same log — `KeyError: 'exec_path'` |
| the work log records the plan-less submission | met | mutation-after | `…test_plan_less_submit_writes_the_global_work_log_as_plan_less`, `…test_an_empty_plan_id_traces_the_same_way`, `…test_a_plan_less_degraded_submit_is_traced_too` | same log — `assert []` (base is silent) |
| holds: a plan-scoped submit keeps today's fields and its work-log line | met | none (hold) | `…test_a_plan_scoped_submit_writes_no_global_line` + pre-existing submit tests — pass at base | — |
| holds: a plan-less submit is still accepted and queued | met | none (hold) | pre-existing `test_plan_less_submit_records_the_sentinel_and_reattaches` | — |

**D4 — the documents and the pins say what the recorder, the gate and the client do** (commit `cf18327d9`, extended in `a48dc07e6`, `19cd43b05`, `5dee22bad`)

| Done-when | Verdict | order | Test | Failing run |
|---|---|---|---|---|
| passes on the changed documents and fails on a planted copy of the old sentence, per pinned document | met | mutation-after | `test_build_tree_naming_doc_contract.py` — 8 pins + 8 planted-copy controls over 3 documents; green at head (`--filter doc_contract`: 51 passed) | `4a5c88b71c2a412ab1df7f1575efd250.log` @ `280e6c404` — 12 failed / 27 passed, every pinned section missing its statement |
| fails at `280e6c404` because no document states a root or two hashes | met | mutation-after | same | same log — "the section opened by 'The row names the tree it hashed' does not carry the tree's hash BEFORE the build ran" |

Per-head test runs: `module-tests` green at `5c33f6978`, `73c3f73f4`, `a29cfff46`, `f95ee9ba0` (full tree, 1142 s), `aff2148c0`, `825f4053e` (merged base), `3b0739361`, `27e816ff1`, `90badc686`, `a05ac1b18`; `quality-gate` green before every commit that touched `*.py`.

## 2. Personas and skills

- D1, D2: persona `implementer`; skills `pm-dev-python:python-core`, `plan-marshall:ref-code-quality`, `pm-plugin-development:plugin-architecture`.
- D3: persona `implementer`; skills `pm-dev-python:python-core`, `plan-marshall:ref-code-quality`.
- D4: persona `documenter`; skill `pm-plugin-development:plugin-architecture`.
- Every self-review round: persona `code-reviewer`.
- Skills added for surface drift: none needed as a declared set — the drift was modules inside already-named skills (`manage-change-ledger`, `runbook-lane`, `phase-6-finalize`), so the same domain skills applied; the review-driven work on `runbook_lane.py` is reported under § 9 as scope beyond the spec, not as a skill gap.

## 3. Hypotheses

- "The executor writes exactly one kind=build row per build-executing dispatch, after the subprocess exits; the submit-time row is kind=job, which the gate ignores" — **confirmed**, template `main()` (one append after dispatch) + `_ledger_core.build_record`/`job_record`.
- "The gate hashes `resolve_plan_context(plan_id, ensure=False).worktree_path`, falling back to cwd" — **confirmed**, `_cmd_pre_commit_verify_freshness.py` root resolution.
- "A build dispatched with a working directory other than the worktree root records the wrong tree's hash and never clears the gate" — **confirmed**, the template hashed `compute_worktree_sha(os.getcwd())`.
- "The same end-state capture allows a false fresh" — **confirmed**: the row carried only the completion hash.
- "Finding 085's mechanism holds only for a non-idempotent rewrite" — **confirmed at the code level**: an idempotent re-run on the clean committed tree records a new hash and clears the verdict; only a re-dirtying gate is unclearable.
- "`run_submit` returns only status/job_status/job_id/attached/queued_behind" — **confirmed**.
- "The wait reply carries only passthrough status fields and no tree" — **confirmed**.
- "The kind=job ledger row already stores the project path" — **REFUTED**: it stored `worktree_sha`, the *hash* of that path, not the paths. Recorded as the D3 premise correction; the row gained `exec_path`/`project_path`.

## 4. Findings

Self-review (persona-code-reviewer, 3 rounds): round 1 — 1 blocker (the D2 ordering was pinned by a comment and nothing drove `main()`), 4 should-fix (a `ValueError` escape out of the gate, an unclearable-route remedy, the template module docstring, two contradictory doc statements), 7 nits; all fixed in `a48dc07e6`. Round 2 — the new unrecorded route's predicate was unscoped over the append-only ledger, vocabulary omissions in three enumerations, a false discriminator in `push.md`, and the `observed_status` contract; all fixed in `19cd43b05`. Round 3 — 0 blocker, 0 should-fix, 4 nits, fixed after the round limit in `5dee22bad` and **not re-reviewed** (operator selected that).

CodeRabbit, four review rounds on this PR (all findings fixed; every thread replied with the fixing commit, then resolved):
- review 1 (head `5dee22bad`), 5 findings → all fixed in `aff2148c0`: plan-less logging routed for every outcome; legacy wait wording; explicit-null dispatch hash refused (the one fail-open in the change); unrecorded-route attribution; doc pins bounded by section.
- review 2 (head `825f4053e`), 4 findings → fixed in `3b0739361` (+ `90badc686`): the routing seam's deliberately hash-less rows excluded; corrupt-ledger reads handled on both re-attach reads; wait audit routing from the job record; the doc-contract sweep widened to `marketplace/`; the newest-row control given the plan under test.
- review 3 (head `27e816ff1`), 1 finding → fixed in `90badc686`: `_latest_job_id_for_plan` catches `ValueError`.
- review 4 (head `9fee6f42e`), 2 findings → fixed in `a05ac1b18`: refusal routing derived from one ordered registry; the census derived from the discovered population.
- CI: green on every head pushed after `5dee22bad`.
- No finding was left unanswered, and none was dismissed.

The review gate's own count (9 body findings, 9 handled) is smaller than the 10 findings those three bodies actually carry: CodeRabbit's "outside diff range comments" blocks are counted under its `inline`/`nitpick` sections, and the run fixed every one of them (see above), including the three the count does not name.

## 5. Reviewers

| Reviewer | Required? | Result | Head reviewed | History |
|---|---|---|---|---|
| `coderabbit` | required, `quota_limited`, `review_complete_after_handling` | **reviewed** (4 reviews) | `5dee22bad`, `825f4053e`, `27e816ff1`, `9fee6f42e` | quota-refused 4× (13:46, 15:21, 16:53 escalated `full review`, 18:24 — each naming a rolling window of 21→39→31 min); after the operator chose to keep retrying, the trigger posted at 19:58 succeeded and review 1 landed at 20:06. Reviews 2–4 were posted automatically on later heads. |
| `sourcery` | optional | refused on quota (7-day diff budget), then reported `SUCCESS` on the final heads without posting findings | — | not gating; no findings to handle |

Standing review authorization: not needed — `coderabbit` holds a qualifying review with its `final_review_risk_coverage` marker naming a covered head of this PR, and every finding of every review is fixed and its thread resolved, so the `review_complete_after_handling` exemption applies at later heads and no further trigger was posted.

## 6. Operator questions

1. "Self-review has reached its 3-round limit. Round 3 reported no blocker and no should-fix, but 4 nits were open; I have fixed all four … How should I proceed?" — options: {Proceed, record budget-exhausted; Run a 4th review round; Stop the run here}; **selected: "Proceed, record budget-exhausted"**.
2. "Required reviewer coderabbit cannot be obtained: quota-refused four times … How should I proceed?" — options: {Stop here, leave PR #1971 open; Keep retrying on the quota loop; Merge now without the review}; **selected: "Keep retrying on the quota loop"**.
3. "The merge gate is blocked by the lane's own parser, not by a finding … How should I proceed?" — options: {Extend the label set, then re-run the gate; Stop with the PR open; Merge on your authority with the gate undecided}; **selected: "Extend the label set, then re-run the gate"**.

No free-text operator messages were received.

## 7. Rule check

- **Guard**: present on this harness. Two refusals, both mine and both recovered without a workaround:
  - R2 (shell file mutation) on `cp` of the plan's committed test files into the base evidence tree — recovered with the Read/Write tools.
  - R5 (direct interpreter call) on a mistyped `python3 .plan/execute-tool.py --help` — the command was a typo, retried as the executor form.
- **Shell file operations**: none issued (no `cat`/`ls`/`grep`/`find`/`head`/`sed`; all reads through Read/Grep/Glob). Every `git` call was read-only or a sanctioned push / merge / `worktree remove`; no `stash`, `restore`, `checkout -- <path>`, `rebase` or forced push. One `git worktree remove` refused (see § 9) and was not forced.
- **`.plan/` writes**: the progress file, the landing file, the `ci` body slots returned by `prepare-*`, and this one inbox message. The spec and `.plan/orchestrator/` were not edited. Note: the final `origin/main` merge brought tracked `.plan/orchestrator/*` ledger changes from `main` into the branch; they are `main`'s own files, not writes of this run.
- **Spec read**: `spec_source=ledger_worktree`; no `spec_differ` marker. `executor-skew`: `not_applicable` (source checkout — the lane text this run read is the checkout the executor maps, so no verb can be missing; answered, recorded, not asked about).
- **Scope**: the spec's four deliverables, plus one operator-authorised extension (`runbook_lane.py`'s non-finding label set, § 9). The review-gate verdicts for the merge were taken through the **worktree's** executor, because the parser extension that makes them decidable is this PR's own change — stated so the verdict is not read as the unpatched gate's.
- **Routed builds**: every build ran through the resolved commands; all reports showed `mechanism=daemon_longpoll`; no `--execution-mode` flag was used, no launch fault occurred, no job was killed. One bound expiry (the first `verify`, `timeout_used_seconds=720`, `timeout_source=learned`) was continued with the split form (`quality-gate` then `module-tests`) rather than re-submitting the same bound; later routed runs passed `--timeout` explicitly.

## 8. Build server

- Setup preflight: `ready` (project registered). Per-mechanism counts: `daemon_longpoll` × 14 builds, `in_process_fallback` × 0. Fallbacks: none; the one bound expiry is not a fallback and is recorded in § 7. No `killed` job. `runtime_stamp_reason`: absent (every stamp fact was measurable).

## 9. Residue

- **Owed cleanup**: `.plan/local/worktrees/lb-146-build-result-names-the-tree-built-base` remains. `git worktree remove` refused (not forced) because the base-sha recipe's copied test files are untracked there: `test/plan-marshall/build-server/test_build_server_tree_reply.py`, `test/plan-marshall/manage-tasks/test_build_tree_naming_doc_contract.py`, `test/plan-marshall/manage-tasks/test_freshness_build_tree_identity.py`, `test/plan-marshall/tools-script-executor/test_build_tree_identity_recorder.py`. Removing it needs those four deleted first (or a forced removal the lane forbids). Hence `cleanup_owed=true`.
- **Scope beyond the spec**: `runbook_lane.py` + its test — the non-finding label extension the operator selected so the review gate could read CodeRabbit's incremental review body at all. Recorded in that commit's message.
- **Carried, disclosed, not fixed**: the row names the PLAN's tree; an off-spec `--audit-plan-id X` with a script-level `--project-dir Y` would record X's tree. Stated in the executor's prose; the canonical resolution path never produces that combination.
- **Self-review** is `budget-exhausted`, not `clear`: the four round-3 nits were fixed after the limit and not re-reviewed, by the operator's selection.
- No token or measurement work. No Sonar work (`not_configured`).
