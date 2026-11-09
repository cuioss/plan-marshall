envelope_version=1
sender_type=plan
sender_id=rb-lb-126-finalize-commit-rows-and-foreign-branch
epic=live-blockers
kind=landing
created=2026-11-08T22:57:19Z

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-126-finalize-commit-rows-and-foreign-branch
epic=live-blockers
pr=#1942
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
steps=setup:done,implement:done,build-gate:done,self-review:budget-exhausted,pr:done,reviews:done,merge:done
unresolved_review_threads=0
review_body_findings_total=0
review_body_findings_handled=0
sonar_open_new_issues=n/a
step.sonar-roundtrip.open_issue_rules=n/a
```

guard: present

# PLAN-LB-126 — landing

Merge commit `f1945737a983d06a3ab19992f2ced93d0661eb05` (PR #1942, merge queue, merge_group run
`42530319936` success).

## 1. Deliverables

Commit map: D1 `c2c2f06` (+ `4e19e8d7`, `82c61541`, `c483ee3b`, `8eeec321` follow-ups), D2 `87dc6cdc`
(+ the same follow-ups), D3 `7e270e15` (+ follow-ups).

### D1 — every finalize commit writes its own `kind=change` row

| Done-when clause | Verdict | order | Test / evidence | Commit |
|---|---|---|---|---|
| a 5f(b) finalize commit, then a loop-back to `5-execute` and a Step 10a fix commit, transition to `6-finalize` (red at HEAD) | met | `mutation-after` | `test_a_finalize_commit_then_a_loop_back_and_a_step_10a_commit_admit_the_boundary` (`test/plan-marshall/workflow-integration-git/test_source_commit_gate_commit_path.py`) — real repo, real verb, real `set-phase`, real ledger append; asserts the boundary predicate is `None` before and after the loop-back. Failing run: with the recording call mutated off at `c2c2f06`, failure at `test_source_commit_gate_commit_path.py:534` (`phase_end_markers_missing`), build job `554c0bd344fa4b639b7c269cd3cce4bf` → log `/home/oliver/.plan-marshall/marshalld/job-logs/554c0bd344fa4b639b7c269cd3cce4bf.log` (exists) | `c2c2f06` |
| a commit with no row is still refused, with every unrecorded SHA in the message (control, two SHAs) | met | `none` | `test_5_execute_end_markers_name_every_unrecorded_sha` (`test/plan-marshall/manage-status/test_manage_status_transition_5_execute_and_finalize.py`) — two unrecorded SHAs, both asserted in `message`, one append invocation each, the retired phase-5 remedy asserted absent, and no newline in `message` | `c2c2f06` |
| the triage inline-fix path leaves a row | met | `none` | `test_the_inline_triage_commit_leaves_a_row_under_the_fixed_prefix` — `section6_record`, no `--step`, row id `finalize-commit` | `c2c2f06` |
| the architecture-refresh path leaves a row | met | `none` | `test_the_architecture_refresh_commit_leaves_a_row` — plan-only commit, row carries `.plan/project-architecture/derived.json` | `c2c2f06` |
| a phase-5 Step 10a commit leaves exactly one row | met | `none` | `test_a_phase_5_commit_leaves_no_row_so_the_settlement_owns_the_only_one` — verb writes nothing outside `6-finalize`; the settlement append leaves exactly one | `c2c2f06` |

### D2 — the foreign-PR gate reads the foreign branch

| Done-when clause | Verdict | order | Test / evidence | Commit |
|---|---|---|---|---|
| a foreign change on a branch not named `feature/{plan_id}` with a merged PR is `clear` (red at HEAD) | met | `mutation-after` | `test_a_foreign_change_on_a_branch_the_plan_id_does_not_name_is_clear` (`test/plan-marshall/phase-6-finalize/test_foreign_pr_gate_gate.py`); the landing resolver answers per branch (`docs/workflow-dsl` merged, `feature/p` pushed_no_pr). Failing run: with the branch selection mutated back to `feature/{plan_id}` at `82c6154`, the verdict is `blocked` and the test fails at `test_foreign_pr_gate_gate.py:386`, build job `6c34f5e625984b038b901b97530bcf17` → log `/home/oliver/.plan-marshall/marshalld/job-logs/6c34f5e625984b038b901b97530bcf17.log` (exists) | `87dc6cdc` |
| the same change pushed with no PR is `blocked` (control) | met | `none` | `test_the_same_change_without_a_pr_is_still_blocked` | `87dc6cdc` |
| an unreadable or disagreeing branch is a named `unresolved` row and `status: error` | met | `none` | `test_an_unreadable_branch_is_a_named_unresolved_row` (`branch_unreadable` + `error: foreign_landing_indeterminate`), `test_a_declared_branch_that_disagrees_with_the_checkout_is_unresolved`, `test_deliverables_declaring_different_branches_for_one_repo_disagree`; the parser-to-gate path is pinned by `test_the_real_parser_carries_the_declared_foreign_branch_to_the_gate` | `87dc6cdc` / `82c61541` |

### D3 — the documents state the row obligation and the branch rule once

| Done-when clause | Verdict | order | Evidence | Commit |
|---|---|---|---|---|
| a read of each cited section shows the one statement and the pointers; no document still says only phase 5 writes a `kind=change` row | met | `none` | row obligation stated once at `workflow-integration-git/SKILL.md` § Commit Changes, pointed to from `phase-6-finalize/SKILL.md` item 5f(b) and 7c(4a), `architecture-refresh.md` § 3d + Tier 1, `manage-change-ledger/SKILL.md` § Entry Shapes + § Integration, `manage-status/SKILL.md`'s 5-execute boundary; corrected in `_ledger_core.py`, `manage-change-ledger.py` (`--kind` help) and `worktree_sha.py`; a content search over `marketplace/` finds no "phase 5 is the writer" claim left | `7e270e15` + follow-ups |
| `archive-plan.md` L37 and the gate docstring state the branch rule | met | `none` | `archive-plan.md` § Pre-Archive Foreign-PR Landing Gate (L37 + the error arm) and `foreign_pr_gate.py`'s module docstring; both state the two sources, the disagreement/unreadable → `unresolved` rule, and the no-fallback rule | `7e270e15` + `c483ee3b` + `8eeec321` |

Per-head test runs (all on the exact content of the head named):

- `82c61541bd4cdcdf4691d52c367b09433f9e533c` — quality-gate success (88 s, log
  `/home/oliver/.plan-marshall/marshalld/job-logs/e6bd6e44e27d4cf28d2b3cd50357b1f6.log`); full
  `module-tests plan-marshall` success (641 s, log
  `/home/oliver/.plan-marshall/marshalld/job-logs/68862aa1e5dc4b469645a72e351920e1.log`).
- `8eeec321a6b299e3eabc42646e5d66bc8a4ef242` — quality-gate success (87 s, log
  `/home/oliver/.plan-marshall/marshalld/job-logs/e2e891a5839842a88562b3391e999977.log`); full
  `module-tests plan-marshall` success (550 s, log
  `/home/oliver/.plan-marshall/marshalld/job-logs/ac24c4c741a34b22b5b310fa16d55ce4.log`).
- `cbccaff7f9054c76b479971d460c2fb04cac3715` (merged head) — quality-gate success (90 s, log
  `/home/oliver/.plan-marshall/marshalld/job-logs/9fd6ef2f0c5a4271b37f39c17337a09c.log`); full
  `module-tests plan-marshall` success (553 s, log
  `/home/oliver/.plan-marshall/marshalld/job-logs/d4e32b8ef0044fbc8eddb96cdf0d5fe2.log`).
- CI on `cbccaff7f`: `verify / verify` success (1117 s), SonarCloud pass, `verify / gate`,
  dependency-review, generate-check.

## 2. Personas and skills

- Production code (D1 row writer, D2 gate): `persona-implementer`.
- Tests (all three deliverables' test files): `persona-module-tester`.
- Documents (D3, plus the D1/D2 doc statements): `persona-documenter`.
- Every self-review round and the PR-comment triage: `persona-code-reviewer`.
- Domain skills: `skills: none named` — the spec's deliverable table declares no `Skills:` or
  `Persona:` line for any of the three deliverables.
- Surface drift: `skills added: none`, and three files were edited beyond the spec's Expected Surface,
  each justified in the code itself:
  - `manage-solution-outline/templates/deliverable-template.md` — the authoring surface where the
    optional `foreign_branch` metadata key must be discoverable (D2's declaration source);
  - `plan-marshall/workflow/execution.md` L479-486 — the dirty-tree attribution map, which the spec
    named as a `kind=change` `deliverable_id` reader;
  - `manage-status/SKILL.md` — the 5-execute boundary description, which the change made false.

## 3. Hypotheses

- "the three writers are the whole population of finalize commits" — **confirmed**; no other
  `git commit` site remains under `phase-6-finalize/standards/` or `plan-marshall/workflow/`
  (`pre-push-quality-gate.md:67` already names the verb).
- "the triage inline commit passes no `step` and is sanctioned by a finding record" — **confirmed** at
  `workflow-integration-git/scripts/git-workflow.py` § `evaluate_source_commit_gate` (settle-band
  step, else open fix task, else section-6 record).
- "the raw architecture-refresh commit is refused by the enforcement guard on the active harness" —
  **confirmed** on OpenCode (`.opencode/plugin/guard.js` R6; `platform-runtime/standards/
  pretooluse-enforcement.md` line 104). It is also the reason the raw commit left no row.
- "the ledger the verb resolves is one the guard reads" — **confirmed**:
  `_ledger_core.resolve_ledger_path` → `{tracked config dir}/work/change-ledger.jsonl`, the same file
  `_cmd_lifecycle._recorded_change_shas` reads, unioned with the plan checkout's own copy by
  `_plan_recorded_change_shas`.
- "no outline field carries a foreign branch" — **refuted as a parser gap**: `**Metadata:**` is a
  free-form key/value block (`_plan_parsing._extract_metadata_block`) that `list-deliverables` emits
  verbatim, so `foreign_branch` needs no parser change. `DECLARATION_FIELDS`
  (`_plan_parsing.py:465`) is only the file-surface record keys. D2's first option therefore needed
  no `_plan_parsing` edit.
- "a foreign branch deleted locally after its merge cannot be tip-resolved" — **confirmed**:
  `_github_pr._branch_tip_sha` runs `git rev-parse {branch}`. Recorded as residue (§9).

## 4. Findings

Self-review rounds (3 dispatched, the limit):

- Round 1 (13 files fixed in `82c61541`): multi-line refusal `message` could not cross the TOON
  boundary (blocking) → one line + pin; a named test had been absorbed by a bad edit (blocking) →
  restored; a main-checkout plan's finalize commit got no row → `--plan-id` in the documented
  invocations; three modules still attributed `kind=change` to phase 5 → corrected; `execution.md`'s
  attribution map; `archive-plan.md`'s error arm; `foreign_branch` undiscoverable at authoring time;
  a sibling test missing its error-code assertion.
- Round 2 (7 files in `c483ee3b`): the `foreign_branch` guidance was inverted and duplicated → the
  template now names the field and points at the one statement; the gate's error `message` now names
  the branch causes; "below" wording and single-line pin coverage; two test refinements.
- Round 3 (3 files in `8eeec321`): the rule statement had dropped the detached-HEAD half of the
  usable-declaration condition → restored; the sibling refusal arm's "below" wording; the git skill's
  Output block now shows the fields the verb returns.
- Operator decision: round 3 reported two text-only findings, both fixed after the round; asked
  whether to spend a fourth round or proceed, the operator selected **proceed**. Reported as
  `self-review:budget-exhausted` because no round reported "nothing open".
- Still open as residue, reported not fixed: the `--step`-derived `deliverable_id` would inherit the
  trailing-digit attribution hazard the constant avoids (no default phase-6 step id ends in a digit);
  `foreign_branch` is not added to the phase-3-outline inline Metadata block or the architecture
  artifact inventory (both are non-authoritative restatements).

PR review surfaces: `review-gate` reports `unresolved_review_threads: 0`,
`review_body_findings_total: 0`, `review_body_findings_handled: 0`, `merge_allowed: true`
(`all_handled`). CodeRabbit's review of `8eeec321a` says "No actionable comments were generated".
Sourcery produced no review (hard quota). No comment required a fix or an answer.

CI: green on `cbccaff7f` (verify, gate, SonarCloud, dependency-review, generate-check).

## 5. Reviewers

| Reviewer | Required? | Outcome | Head reviewed | Trigger / wait history |
|---|---|---|---|---|
| coderabbit | required (`quota_limited: true`) | **reviewed** (summary comment carries `final_review_risk_coverage` with `sourceCommitId` = `coveredCommitId` = `8eeec321a`, `kind=reviewed`, "No actionable comments were generated", Merge Risk Minimal) | `8eeec321a` (a qualifying review on one of this PR's heads) | triggered 20:00:50Z → refused on quota (notice said "30 seconds"); waited the lane's 90 minutes (two `ci pr wait-for-comments` calls, no new comments); re-triggered 21:24:40Z → review finished 21:34; re-triggered again 21:47:14Z on the merged head `cbccaff7f` → refused on quota with no ETA, recorded. **Standing review authorization applies:** qualifying review exists, every finding handled (0 findings), re-triggered once after the last push, all other gates green on the current head |
| sourcery | optional (`quota_limited: true`) | **refused** (hard quota: 250k diff characters per 7 days, next in 3 days 5 hours) | — | triggered 20:01:01Z → refused. Optional, so it does not gate the merge |

## 6. Operator questions

1. Asked: "The self-review budget of 3 rounds is spent. Round 3 reported 2 findings, both
   documentation/text nits, and both are now fixed in commit 8eeec321a (quality-gate and the full
   plan-marshall module-tests are green on that head). Proceed to open the PR, or spend one more
   self-review round first?" — options: "Proceed to the PR (Recommended)" / "Run a 4th self-review
   round". Selected: **"Proceed to the PR"**.

No other question-tool call was made. No free-text operator messages were received. No
surface/naming error required a question.

## 7. Rule check

- **Guard refusals in this run: 2** (guard log `.plan/temp/guard.log`, session
  `ses_e454048b0ffeTlI8aXl0ZftvjH`, both read from the log and attributed by session, not by a time
  window):
  1. `R1` — a shell command carrying a pipe (`grep -rn … | head -20`). Rewritten with the `grep` tool.
  2. `R7` — an `edit` addressed at the MAIN checkout's `git-workflow.py`. Re-issued against the
     worktree path, which is where every source edit in this run landed.
- **Read-class shell file operations the run issued (not refused, counted by the run):** one `ls -la`
  of the worktree root (early, before the worktree's contents were confirmed); eight `tail` reads of
  build logs; five `grep -n` reads of build/guard logs; one `wc -l` of the guard log. All were reads of
  build/guard artefacts, and the lane's counts are taken from the run's own actions, not only from the
  guard log.
- **Routed builds:** every build was submitted with the default routing and ran
  `mechanism=daemon_longpoll`; none was backgrounded. Two bound expiries, both recorded: a
  quality-gate run killed by the daemon's 330 s floor (plugin-doctor is slow), re-submitted once with
  `--timeout 1243`; and a full `module-tests` run killed at an explicit 1243 s because it was run with
  `--no-parallel`, re-run in the split form without that flag and green in 553 s.
- **Operator messages:** one question-tool call (§6). No model or effort switch during the run.
- **Spec read:** `resolve` read the spec from the **ledger worktree**
  (`spec_source: ledger_worktree`); no `spec_differ` marker was reported, so the main checkout's copy
  does not disagree.
- **executor-skew:** `not_applicable` — a source checkout, where the executor maps the checkout's own
  scripts, so the lane text cannot name a verb those scripts lack. Answered and recorded, never asked
  about. (The lane text did change mid-run: the base merge moved `runbook-lane/SKILL.md` by +240 lines,
  and the run re-read it and applied the merged version — the `review-gate` verb, the inbox reads, the
  operator-only Sonar dismissal rule, the evidence-artifact rule and the new landing facts.)
- **`.plan/` writes:** the progress file, the landing file, `.plan/temp/` message files and the two
  `ci` body slots — plus one inbox message. Nothing under `.plan/orchestrator/` was written.
- **Evidence artifacts:** every `mutation-after` claim cites a build job whose log file exists at the
  named path (§1).

## 8. Build server

- Setup preflight: **ready** (project registered, version 1).
- Builds by mechanism: `daemon_longpoll` for every submitted build; **0** `in_process` fallbacks
  (`dependencies: none`).
- Fallbacks/retries: one bound expiry on `quality-gate` (330 s daemon floor → resubmitted once with
  `--timeout 1243`); one bound expiry on `module-tests` (explicit 1243 s with `--no-parallel` →
  re-run in the split form, parallel, 553 s). No `killed` job.
- Queue waits were long (up to ~2 300 s) because other sessions held the machine-global slots; no
  build was submitted in parallel.

## 9. Residue

- **Deleted foreign branch.** A foreign branch deleted after its merge cannot be tip-resolved, so even
  a correct branch name reads `error` (`_github_pr._branch_tip_sha`). The gate now names the branch it
  tried; the read itself is unchanged.
- **Post-cleanup declarations.** A `foreign_branch` declaration is usable only when the foreign
  checkout is on that branch or reports no branch; in the post-cleanup state the plan itself cites
  (tree on `main`) the gate is `error` by design. The operator's remedy is to put the foreign tree on
  the declared branch, or to let the checkout answer.
- **Ambient-branch reads remain a source** (by spec), so a sibling checkout left on an unrelated merged
  branch can clear a foreign deliverable. The declaration is the stated cure.
- **A `--step` id ending in digits** would be read as an outline deliverable number by
  `_review_support_validate.deliverable_number`; no default phase-6 step id ends in a digit.
- **`foreign_branch` discoverability**: the mandated deliverable template names it; the
  phase-3-outline inline Metadata block and `ref-workflow-architecture/standards/artifacts.md` (both
  non-authoritative restatements) do not.
- **No end-to-end CLI test of `commit --plan-id`** for a `use_worktree: false` plan: the plan-context
  resolver shells through a cwd executor a synthetic repo cannot provide. The id-keyed phase lookup is
  pinned in-process instead.
- **Owed outside this plan:** a harness sync after merge, and an executor regeneration only if a verb
  or flag was added (none was — `--plan-id` already existed on the commit verb).
