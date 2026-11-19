# Landing Analysis: PLAN-LB-167 — A Sonar read on a head the project's CI never analyses is decided from the last analysed head

epic: live-blockers
workstream: WS-04
pr: #2028 (https://github.com/cuioss/plan-marshall/pull/2028)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying claims against ground truth (the merged code, the PR state through the CI abstraction, the lane's own progress file). The landing message is a lead, not a fact. Merge commit `c35f23c126a7e5e8afa2fc658e67293a252cc5cc` (parent `7e79e2b52`), squash, eight files, 1408+/73-. Landing message: `rb-lb-167-sonar-read-on-a-head-ci-never-analyses-001.md` (runbook lane, harness `opencode`, model `deepseek-v4.1-flash/high`, effort `high`). `landing-check`: `complete: false`, `missing_keys` = `total_tokens` only; per the standing ruling of 2026-10-23 that is no defect. `deliverables_done=3` of `deliverables_total=4`.

## Deliverable Fidelity vs Spec

The lane reports D1's evidence clause "not met as written, by operator decision". The merged code bears that out, and goes further than the lane's words: the motivating case, the one the plan was staged for, is not unblocked. The spec's own verify-first clause said a refutation of premise (a) "loops back to re-scope"; the lane shipped a narrower fix instead.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 decide a `stale_analysis` read from the analysed head when the delta is not built | shipped-modified: the mechanism ships (the verb `sonar-stale-delta`); the motivating consumer stays `undecidable_read` | `runbook_lane.py:1933-1967` (re-read); the rule sources and the fallback at `:1284-1297`, `:1375-1412`, `:1583-1589`, `:1665-1671` (re-read) |
| D2 the carried-forward read is an enumeration, the stop unchanged for every other stale analysis | shipped-modified: the enumeration ships; the licence is self-attested and unbound to the head | `sonar.py:999-1015` (re-read) |
| D3 documents state the rule; landing facts name the analysed revision beside a carried-forward figure | shipped-modified: the rule is stated; "retry the read" still prescribed for a refused stale read; the marking is opt-in, against the spec's "never reads like a measurement of the head" | `runbook-lane/SKILL.md:826-857` (re-read); `runbook_lane.py:2189-2198`, `:2482-2493` (re-read) |
| D4 tests pin D1 to D3, written against the unfixed tree first | shipped-modified: the tests exist; the order is `mutation-after` by the lane's own report, not test-first; two named tests stub the classifier | leaf reading, `test_runbook_lane_sonar.py:525-963`; order not verifiable by reading |

## Three-Layer Analysis

The landing was read on three layers by one read-only leaf (`execution-context-level-5`, resolved on `orchestrator.analyze`); the orchestrator re-read the load-bearing points below at the merge commit (the main checkout's `HEAD` is the merge commit). The reading is **by reading, no build, no test run, no write**.

- **Dispatch:** one read-only leaf for this landing — reason: the landing is 1408 added lines across a lane script, a Sonar read verb, two skills and four test files; reading the merged code to test the spec premise, the deliverable trace and the fail-closed property is the depth the Dispatch Decision Rule exists for, and one landing's read does not share context with another's.
- **Verdict:** layer 1 findings (1 major); layer 2 findings (3 majors, 3 minors); layer 3 findings (3 majors, 8 minors). The three layer-3 majors are on the gate side of the contract, not the decision verb, which fails closed on every input read.

### Layer 1 — Specified

| Finding | Claim | Verdict | Polarity | Evidence (file:line) |
|---------|-------|---------|----------|----------------------|
| L1-1 | Premise (a) of the spec ("the lane's classifier made correct for a consumer whose rule it cannot read, the CI check-runs, or both") is refuted on `main` for the motivating consumer: with no readable rule the source is `architecture`, with no architecture the prefixes are `['']` and every path is `buildable`; a delegating workflow yields no `paths-ignore` (`None`); the fallback `_is_project_doc` needs a documentation module (`:1453`). The spec's own clause required a loop-back to re-scope | checked | refutes | `runbook_lane.py:1583-1589`, `:1665-1671`, `:1375-1412`, `:1284-1297`, `:1453` (re-read) |
| L1-2 | This repository opts in with a literal `skip-on-docs-only: true` and no `paths-ignore`, so the carry-forward reaches it only through an architecture documentation surface | checked | confirms | `.github/workflows/python-verify.yml:55` (leaf reading); whether this repository's architecture reports a documentation module is not readable (it lives under `.plan/`) |
| L1-3 | Whether CI check-runs can tell a docs-only skip from a Dependabot or conditional skip depends on a reusable workflow in another repository, so the second alternative of the spec is not shown to be fail-open or fail-closed | not_shown_by_reading | none | `python-verify.yml:43` |

**Layer 1 verdict:** findings — 1 major (L1-1), 2 not shown by reading or confirming (L1-2, L1-3)

### Layer 2 — Implemented

| Deliverable | Code trace | Test that can fail | Unexplained file / unborne claim | Verdict |
|-------------|------------|--------------------|---------------------------------|---------|
| D1 | `runbook_lane.py:1933-1967`; the verb `cmd_sonar_stale_delta` (`:1970`, leaf) | real-git tests `test_the_project_own_rule_decides_a_real_docs_only_delta` (`:610`) and the refusal tests; none runs the motivating case (a delegating workflow with no architecture) through the real classifier | the motivating case stays `undecidable_read` through `delta_buildable` (`:1954-1960`, re-read) | checked (major, L2-1) |
| D2 | `sonar.py:999-1015`, the recheck `:1156-1190` (leaf) | `TestLicensedStaleAnalysis`, `TestRevisionMovingDuringTheRead`: they use the real `_verify_analysis_revision` against a mocked API | the post-enumeration recheck applies to every PR read, beyond D2's described change (hardening no deliverable describes) | checked |
| D3 | `runbook-lane/SKILL.md:826-857`; `workflow-integration-sonar/SKILL.md:202-204` (leaf) | `test_the_lane_text_states_the_carry_forward_rule` | "retry the read" survives for a refused stale read (L2-2); `:828-829` inverts the cause (L2-4) | checked (major) |
| D4 | the four test files | `test_an_unplaceable_path_stays_undecidable` (`:764`) and `test_an_unreadable_footprint_rule_stays_undecidable` stub `_classify_paths`, so they pin the decision's branching and not placement or rule reading | order `mutation-after`, a deviation from the spec (not verifiable by reading) | checked (minor) |

Findings: L2-1 (major) the motivating case is unchanged (see Layer 1); the lane's report says it, and the lane did not loop back to re-scope. L2-2 (major) `runbook-lane/SKILL.md:853-857` still says "retry the read, and if it stays undecidable do not merge" for a `stale_analysis` the carry-forward did not licence, which covers the motivating case, and the merge section repeats "is retried" (`:947`, leaf reading); the retry can never succeed, which is the symptom the plan was staged to remove. L2-3 (major) the squash commit message of `c35f23c12` and the body of PR #2028 describe a different plan's change (see Routing and Merge Behavior), and the message's scope line ("No file outside manage-solution-outline, phase-6-finalize") is false for this commit. L2-4 (minor) `SKILL.md:828-829` says the analysis "stays on a head the CI does not build"; it is the current head that the CI does not build. L2-5 (minor) the missing tests: the motivating case through the real classifier, the architecture source, renames and quoted paths, the gate's short-SHA alias, a licensed read whose head moved, hotspot keys under carry-forward. L2-6 (minor) the flag spellings diverge across the three verbs (`--analysis-revision`, `--carried-forward-analysis-revision`, `--analysed-revision`).

**Layer 2 verdict:** findings — 3 majors, 3 minors

### Layer 3 — Correct

| Defect | File:line | Triggering input | Effect | Severity |
|--------|-----------|------------------|--------|----------|
| L3-1 | `sonar.py:1015` (re-read) | a licensed re-read after a buildable push, where the provider's analysis is still the old revision A | the licence binds the analysed revision only, which the verb's own `undecidable` output discloses, and neither the head nor a `sonar-stale-delta` verdict; so a caller supplying the revision of a stale analysis gets `confirmed` + `carried_forward` for a head whose delta was never classified. The head-moved guard is lane prose only (`SKILL.md:844-847`, re-read), not code. The stop is unchanged only for callers that omit the flag | major |
| L3-2 | `runbook_lane.py:2048-2092` (leaf) | `sonar-gate --carried-forward-analysis-revision A --carried-forward-head-revision B` with any confirmed read | the gate accepts the pair from the caller with no link to a verdict, and its reason asserts "delta not built" unverified | major |
| L3-3 | `runbook_lane.py:2189-2198`, `:2482-2493` (re-read) | `--analysed-revision` omitted, or the gate called without the pair | a carried-forward count reaches the facts and the gate unmarked (`no_open_issues`); the read's own `carried_forward: true` does not travel to either verb. `test_no_analysed_revision_line_rides_without_one` (`test_runbook_lane_sonar_landing.py:263`, leaf) pins that behaviour. This contradicts D3's "never reads like a measurement of the head" as a code property; only lane prose enforces it. The lane records the opt-in as "by operator decision" (progress file, `operator:` line) | major |
| L3-4 | `runbook_lane.py:2072` | a short SHA and the full SHA of one commit | the gate's equality is a string compare, so the alias passes and yields a false "!=" sentence (the lane lists this as accepted residue) | minor |
| L3-5 | `runbook_lane.py:2106` | the empty-delta carry (`:1941`) | the gate reason says "not built" even for an empty delta | minor |
| L3-6 | `runbook_lane.py:1795` | `assume-unchanged` or `skip-worktree` bits, or `status.showUntrackedFiles=no` | `git status --porcelain` misses a modified or untracked workflow file; the footprint rule is read from the working tree and equals the head's only through the three guards (`worktree_not_at_head`, `worktree_dirty`, `worktree_ignored_inputs`) | minor |
| L3-7 | `runbook_lane.py:1281`, `:1358` | a tracked symlink under `.github/workflows` pointing outside the repository | the symlink is followed, so a rule the head does not carry can decide the delta | minor |
| L3-8 | `runbook_lane.py:1815` | an ignored architecture-source input | the ignored-input guard covers `.github/workflows` only | minor |
| L3-9 | `runbook_lane.py:1947` | a head that adds `src/**` to its own `paths-ignore` (and ignores `.github/**`) | the whole delta is classified by the head's rule, so a source change the analysis never saw carries forward; literally the "project's own rule", open with respect to Sonar's new code | minor |
| L3-10 | `runbook_lane.py:1829` | non-ASCII or control-character paths | without `-z` git quotes the path, the quoted path matches nothing, so it reads `buildable`: fail-closed, but a false blocker; `.strip()` at `:1832` alters space-padded names | minor |
| L3-11 | `runbook_lane.py:1835-1967`; `sonar.py:1018-1217` | n/a | `_sonar_stale_delta_verdict` is 133 lines of flat guard clauses; `cmd_read_open_issues` grew to about 200 lines; over the complexity threshold | minor |

Also read: the decision verb fails closed on `not_configured`, a non-`undecidable` read, a missing, unresolvable or equal revision, a checkout not at head, a dirty tree, ignored inputs, a failed diff, an unreadable rule and any buildable path (`runbook_lane.py:1866-1960`, leaf); the delta is a tree-to-tree `git diff --name-only --no-renames` (`:1829`, re-read), so renames list both sides, deletions and mode changes are listed, and a non-ancestor analysed revision compares trees; `_git_in` uses an argv list, `-C`, a timeout and a return-code check, and no new bare `except` appears (`:1741-1761`, leaf); the licence cannot cover a revision other than the one the provider reported (`sonar.py:1013-1015`, re-read), and the recheck after the hotspot fetch (`:1156-1190`, leaf) refuses a changed analysis, a revision missing on recheck and a moved head. No new code writes a file or mutates git (`git status` may take the optional `index.lock`).

**Layer 3 not shown by reading:** whether this repository's architecture reports a documentation module; how the reusable workflow classifies the delta (per push, or the PR against its base); whether check-runs tell skip reasons apart; whether the provider keeps its issue, hotspot and PR endpoints consistent within one analysis; the lane's mutation run ("6 named tests failing") and its "full module-tests green at three heads". Only a run could show these.

**Layer 3 verdict:** findings — 3 majors (L3-1, L3-2, L3-3), 8 minors (L3-4 to L3-11); 1 not shown by reading

### Conformance to the Project's Own Rules

| Rule source | Rule | Verdict | Evidence |
|-------------|------|---------|----------|
| spec | verify-first: a refutation of premise (a) loops back to re-scope | deviates | `runbook_lane.py:1671`, `:1453`; the lane shipped a narrower fix |
| spec | fail closed: carry only when every path is positively not built | conforms | `runbook_lane.py:1933-1967`, within the decision verb |
| spec | D2: the stop unchanged for every other stale analysis | deviates | `sonar.py:1015`: the licence is self-attested and head-unbound |
| spec | D3: a carried-forward figure never reads like a measurement of the head | deviates | `runbook_lane.py:2189-2198`, `:2482-2493` |
| spec | D3: the lane text no longer says retry for a never-refreshed stale analysis | deviates | `runbook-lane/SKILL.md:853-857` |
| spec | never a bare `0`; `--dismissed-keys` stays refused; a project without Sonar unchanged | conforms | leaf reading, `runbook_lane.py:2153-2160`, `:2272-2283`, `:2284-2309` |
| spec | no file outside the lane, the Sonar skill and their tests | conforms | `git show --stat c35f23c12`: exactly the eight Expected Surface files |
| spec | D4 tests written against the unfixed tree first | not_shown_by_reading | the lane reports `mutation-after` |
| python-core | argv-list subprocess, no bare `except` | conforms | `runbook_lane.py:1741-1761` (leaf) |
| ref-code-quality | complexity thresholds | deviates | `runbook_lane.py:1835-1967` |
| CLAUDE.md Commit Trailer | the plan-marshall trailer and nothing else | deviates | the squash message adds `Co-authored-by: cuioss oliver …` (a GitHub squash-generated line) beside the plan-marshall trailer |

Points re-read by the orchestrator at the merge commit: `runbook_lane.py:1284-1297`, `:1375-1412`, `:1440-1459`, `:1568-1589`, `:1660-1675`, `:1822-1832`, `:1930-1967`, `:2182-2198`, `:2478-2506`; `sonar.py:996-1020`; `runbook-lane/SKILL.md:824-859`; the squash message and the bodies of PRs #2027 to #2030. Not re-read, recorded as unverified leads: the guards at `:1795-1931`, `:1341-1365`, `:2048-2092`, the post-enumeration recheck at `sonar.py:1156-1190`, the tests and their counts, `python-verify.yml:43` and `:55`, and every `not_shown_by_reading` point.

The leaf's own slips: it was granted neither Grep nor Glob and used Read, `git show`, `git diff`, `git ls-files` and `git blame -L /regex/` (history reads, not `git grep`); it skipped the dispatcher's `manage-logging` and `resolve-workflow` steps under the read-only instruction; it read its own spilled tool output; four `git blame` calls with several `-L` ranges failed on regex ordering and were re-run one at a time.

## Metrics and Anomalies

- Tokens: `unknown`, an unobserved fact, no defect.
- Duration: the squash commit is dated 2026-11-19 20:26:57 +0000; the landing message was filed at 20:53:28Z.
- Anomalies: (1) **the squash commit message and the PR body of #2028 describe PLAN-LB-169's change** (see Routing and Merge Behavior). (2) The lane's progress file holds the per-deliverable commits and four `finding:` lines (inline-1 to inline-4, each with a commit) but its `self-review round 2` line still reads `pending`, while the landing reports rounds 2 and 3 clean; the progress record lags the landing. (3) The lane self-reports breaks of its own shell rule (`ls` on two test directories, `grep -n -E` on five build logs, `tail -n 20` on one test file, `file` on one skill file) and two guard refusals (`R7`, an edit of `runbook_lane.py` in the main checkout re-issued in the worktree; `R1`, a shell chain using a pipe). (4) One `module-tests` run hit the daemon's learned bound (1137 s) and was re-run split with `--timeout 1705`. (5) `harness=opencode`, `model=deepseek-v4.1-flash/high`: a harness and model other than the Claude lanes of this epic, recorded as a fact with no conclusion drawn.

## Routing and Merge Behavior

- Review: the landing claims 4 review-body findings, 4 handled, 0 unresolved threads; coderabbit required (`quota_limited`, `review_complete_after_handling`; a formal review on `b871434c4`, a marker review on `a7ee50b09`), sourcery optional (refused on quota twice, then skipped). Re-read by `runbook_lane review-gate --pr-number 2028`: `unresolved_review_threads` 0 and `review_body_findings_total` 4 (coderabbit `inline-1` to `inline-4`) both agree with the landing. `review_body_findings_handled`: the gate's own read is `0` and reports `merge_allowed: false` (`body_findings_undisposed`); the number is re-verified from the lane's progress file instead, which holds four `finding:` lines (inline-1 to inline-4, each naming a commit), so 4 agrees. No false claim.
- **PR #2028 carries another plan's body, and so does its squash commit.** The body of PR #2028 (read through the CI abstraction) and the squash message of `c35f23c12` (read from git) describe PLAN-LB-169's change (`criteria-authorize --decision-type`, `manage-solution-outline`, `phase-6-finalize`, a test file `test_retirement_decision_d4.py` that does not exist in the merged tree); PR #2029, which is PLAN-LB-169's own, carries nearly the same text (a later revision: it reports a `verify` run of 1537 s where the #2028 text says 1030 s); only the title and the CodeRabbit summary of #2028 are about the Sonar carry-forward. The lane's progress file says the body was `Summary / per-deliverable Changes / Test evidence table / Residue`. PRs #2027 (this orchestrator's land) and #2030 (PLAN-LB-168) carry their own bodies. **OBSERVED:** the runbook lane's text allocates the PR body with `pr prepare-body --plan-id NO_PLAN` and `pr create --plan-id NO_PLAN` (`runbook-lane/SKILL.md:777-782`, re-read), and the body slot `prepare-body` returns is `.plan/local/plans/NO_PLAN/work/ci-bodies/pr-create-default.md`, the same file the `land` verb writes; with several lanes running at once they share one slot. **HYPOTHESIS (not settled):** PLAN-LB-169's lane wrote its body to that shared slot between PLAN-LB-167's `prepare-body` and `pr create`, so `pr create` consumed the wrong body. Whether `prepare-body` hands every caller the same path, or a path per call, was not read in `ci_base.py`.
- CI/merge: PR `#2028`, state `merged`, merge commit `c35f23c12`, base `main`; the lane reports `settle merged`; `review_decision: none`. Builds reported: 14 `module-tests` and 14 `quality-gate` runs, all `daemon_longpoll`, no `killed` job; none re-run here.
- Collision with PLAN-LB-168 (running; same file `runbook_lane.py`): the merge adds `_classify_paths`, `_CARRY_FORWARD_UNBUILT`, `_git_in`, `_resolve_commit`, `_checkout_revision`, `_worktree_is_clean`, `_ignored_workflow_inputs`, `_delta_paths`, `_sonar_stale_delta_verdict`, `cmd_sonar_stale_delta`, `_carried_forward_revisions`, `_carried_forward` and changes `cmd_build_classify`, `_sonar_gate_verdict`, `cmd_sonar_gate`, `cmd_sonar_facts` and `main`'s argparse block; the review-body parser functions (`_BOLD_SPAN_RE` at 2630, `_owned_blocks` 2659, `_inside_prose` 2813, `_enclosing_sections` 2850, `_heading_section` 3006, `_body_findings` 3084) carry no line attributed to `c35f23c12` (leaf, `git blame`) and no hunk lies in or next to them. A conflict could arise only if PLAN-LB-168 also edits `main`'s argparse block. No unpredicted collision, so no declared surface needs correcting.
- Sonar: the landing's `sonar_open_new_issues` is `n/a` and `step.sonar-roundtrip.open_issue_rules` is `n/a`, the lane's `sonar: not_configured; no read made`; compared as the claim it is.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-167 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-LB-167 --field pr --value 2028`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-LB-167 --field landing --value landings/PLAN-LB-167.md`
- [x] row `plan_marshall_plan_id` stamped — value `rb-lb-167-sonar-read-on-a-head-ci-never-analyses`, taken from the sender
- [x] epic.md narrative reconciled: the Sonar Open Defect is marked SHIPPED IN PART and stays open for the motivating case; one new Open Defect (the PR body and squash message of #2028, the shared body slot); the minors go to the Watch
- [x] resume anchor updated in `resume_anchor.md`
- [x] `queue-view.md` regenerated

## Follow-Ups

- **The motivating case is not fixed (L1-1, L2-1, L2-2).** The Sonar Open Defect stays open: a consumer whose CI delegates to a reusable workflow, with no architecture documentation module, stays `undecidable_read` on a docs-only head, and the lane text still says "retry the read". A fix is a re-scope the spec's own clause required; it is staged only on the operator's word, and the operator chooses between a classifier made correct for that consumer, the CI check-runs of the head, or both. The lane records that the choice to ship the narrower fix was the operator's (two answers in the progress file); I cannot see those answers.
- **The gate side is fail-open in code and fail-closed in prose (L3-1, L3-2, L3-3).** The decision verb fails closed; the licence, the gate's pair and the marking do not bind each other.
- **The body and message of #2028 are wrong (L2-3).** The message is in main's history; the body of the merged PR is editable, and I have not edited it. The cause is a hypothesis; it affects every lane running in parallel and the `land` verb, which share one body slot. It goes to the Open Defects, and a fix plan is staged only on the operator's word.
- The minors (L2-4 to L2-6, L3-4 to L3-11) go to the BACKLOG Watch of `epic.md` under the focus rule.
