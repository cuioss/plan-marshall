# Landing Analysis: PLAN-LB-170 — PLAN-LB-165 completion: two document rules out, null-block tests in, `/apply-changes` operator-only on every harness

epic: live-blockers
workstream: WS-03
pr: #2031 (https://github.com/cuioss/plan-marshall/pull/2031)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying claims against ground truth (the merged code, the PR state through the CI abstraction, the lane's own progress file). The landing message is a lead, not a fact. Merge commit `d32af9f8c4f9d21a89c6f026d429efcd1d50cfec` (parent `f32725159`, PLAN-LB-169's merge), squash, twelve files, 848+/9-. Landing message: `rb-lb-170-lb-165-completion-document-rules-and-missing-tests-001.md` (runbook lane, harness `opencode`, model `deepseek-v4.1-flash/high`, effort `high`). `landing-check`: `complete: false`, `missing_keys` = `total_tokens` only; per the standing ruling of 2026-10-23 that is no defect. `deliverables_done=4` of `deliverables_total=4`.

## Deliverable Fidelity vs Spec

All four deliverables trace to code and to tests that can fail. The plan did what the spec ordered, and the ordered form of D1 turns out to restate a contract the review-gate verb cannot honour. Nine claims of the lane's report are not borne out by the diff, none of them blocking.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 the false-claim paragraph of `analyze.md` is head-bound again (form a or b), with a test | shipped-as-specified, form (a): the post-merge exemption and the "current state" wording are gone and the stale parser clause is corrected; the restored wording asks for a re-read the verb cannot perform (L3-1) | `analyze.md:155` (re-read); `test_analyze_false_claim_contract.py` (336 lines, new) |
| D2 the Step 6 reopen/supersede sentence is removed, the "its" reword stays, a test pins it | shipped-as-specified: the reopen clause is gone, the item-number ordering is kept as a stand-alone sentence | `handle-open.md:72` (re-read); `test_handle_open_contract.py` `TestStepSixDecisionSemantics` (+122) |
| D3 the null-block fix has its tests; the beyond-spec behaviours are settled with reasons; the docs follow the code; the three minors are settled | shipped-modified: tests, file-naming messages and docs landed; two of the lane's stated reasons are not borne out (L2-4, L2-5); the use_worktree file has no non-dict main-anchored test | `_cmd_orchestrator.py:290-323` (re-read); `test_orchestrator_scope.py` (+87), `test_orchestrator_use_worktree.py` (+71) |
| D4 `/apply-changes` operator-only on every harness with the gap stated and pinned | shipped-modified: the gap is now written in each entry point and pinned; the evidence it cites is the generator's metadata and not a harness schema (L3-2) | `.opencode/commands/apply-changes.md:15-22`, `.claude/skills/apply-changes/SKILL.md:24-29` (re-read); `test_apply_changes_command_parity.py` (+190) |

## Three-Layer Analysis

The landing was read on three layers by one read-only leaf (`execution-context-level-5`, resolved on `orchestrator.analyze`); the orchestrator re-read the load-bearing points below at the merge commit (the main checkout's `HEAD` is the merge commit). The reading is **by reading, no build, no test run, no write**.

- **Dispatch:** one read-only leaf for this landing — reason: the landing completes an earlier landing whose own findings were documents contradicting a standard, a handler and a parity test across three harnesses; testing it means tracing the contract through the review-gate verb and the target metadata, which is the depth the Dispatch Decision Rule exists for; one landing's read does not share context with another's.
- **Verdict:** layer 1 findings (1 major, 1 minor); layer 2 findings (7 minors); layer 3 findings (2 majors, 6 minors). The two majors are the restored contract that the verb cannot realise and the apply-changes gap statement resting on the wrong evidence.

### Layer 1 — Specified

| Finding | Claim | Verdict | Polarity | Evidence (file:line) |
|---------|-------|---------|----------|----------------------|
| L1-1 | The spec's form (a), and the pre-PLAN-LB-165 paragraph it restores, name a re-read "on the merged head" that `review-gate` cannot perform: the verb takes `--pr-number`, `--project-dir`, `--disposition` and `--required-reviewer` and no head, sha or time argument, and reads the PR's current review state through one provider fetch | checked | refutes | `runbook_lane.py:4290-4314` (re-read), `:3671-3699` (re-read, the docstring says the data is fetched once and the verdict flattens its own copy); `github_ops.py:745` (leaf) |
| L1-2 | The spec's Expected Surface was under-declared: D1 required "a test pins the chosen form" and the surface listed no home for an `analyze` test, so the 13th path (`test_analyze_false_claim_contract.py`) is a justified declared addition; no other file outside the surface was touched | checked | confirms | the merge stat: 12 files, 11 of the surface plus the new test, `landing-payload-spec.md` untouched |

**Layer 1 verdict:** findings — 1 major (L1-1), 1 minor (L1-2)

### Layer 2 — Implemented

| Deliverable | Code trace | Test that can fail | Unexplained file / unborne claim | Verdict |
|-------------|------------|--------------------|---------------------------------|---------|
| D1 | `analyze.md:155` | `test_analyze_false_claim_contract.py`: head-bound wording, no exemption, the standard's agreement, the parser clause by reading `_read_review_surfaces`; the planted controls fire through the real detector (leaf) | the lane's citation `runbook_lane.py:3009-3056` is correct on its branch but at the merge commit those lines are `_enclosing_sections`, the function is at `:3671` (leaf); the reason given for rejecting form (b) ("`review-gate` reports counts, not per-comment timestamps") is partly wrong, the provider records carry `created_at`/`updated_at` (`github_ops.py:908`, leaf) and only a later thread resolution has no time | checked (minors, L2-1, L2-2) |
| D2 | `handle-open.md:72` | `TestStepSixDecisionSemantics`, with planted controls | the PR body says `kinds[]` is "already pinned"; the pin regex matches only `^sources[` (`test_handle_open_contract.py:122`, `:489-506`, leaf), so `kinds[]` is not test-pinned; the lane's own landing message says "not test-pinned" | checked (minor, L2-3) |
| D3 | `_cmd_orchestrator.py:290-323`, `data-model.md:314` | the new tests in the two files that exercise `get` | "pre-existing for every verb and field" is false for `use_worktree` (LB-165 moved `load_config` ahead of that branch) and the invalid-JSON path surfaces as a `safe_main` `internal_error` with exit 1, not a traceback (L2-4); "three owners read it" is overstated, two of the three reads sit in the same module (L2-5); no non-dict main-anchored test and none for the `set` message's file name (L2-6) | checked (minors) |
| D4 | the three entry points | `test_the_command_is_operator_only_on_every_harness` and the 22 parity tests; removing the key or a gap sentence turns it red; it cannot pass on an empty population (`_ENTRY_POINTS`, `_HARNESS_RULES_FILES` derive from `SYNC_TARGETS` with a non-empty assert, `:65-68`, `:156-158`, leaf) | the lane's "+1239/−40 across five commits" does not match the squash stat (848+/9−); the four local branch commits sum to 662+/8−; not reproducible (L2-7) | checked |

Findings: L2-1 and L2-2 (minors) are the stale citation and the partly wrong reason for rejecting form (b), above. L2-3 to L2-6 (minors) are the `kinds[]` claim, the "pre-existing" claim, the "three owners" claim and the missing tests, above. L2-7 (info) the stat claim. The squash message and the CodeRabbit summary embedded in it claim guidance on "re-analyzing invalidated decisions without reopening them"; no document says that (leaf).

**Layer 2 verdict:** findings — 7 minors

### Layer 3 — Correct

| Defect | File:line | Triggering input | Effect | Severity |
|--------|-----------|------------------|--------|----------|
| L3-1 | `analyze.md:155` (re-read); `runbook_lane.py:4290-4314`, `:3671` (re-read) | a review thread reopened, or a comment or review posted, after the merge | the paragraph orders the orchestrator to re-read "on the merged head" and to record a difference as a false claim, "not … a stale read"; the verb reads the current state, so a truthful landing is labelled false, and no repository document records this residual or says what the orchestrator does about it; the lane's own "residual consequence" (§ 9 of its landing) is a standing property of the contract and lives only in that landing. The same wording stood before PLAN-LB-165, so this is a latent defect of the contract that PLAN-LB-170 restored and did not create | major |
| L3-2 | `.opencode/commands/apply-changes.md:15-22` (re-read); `.agents/skills/apply-changes/SKILL.md:19-22` (leaf) | an operator or a model reading the entry point | the gap statement ("This harness publishes no key … `frontmatter-rules.json` … is the authoritative field set") cites plan-marshall's generator source-validation config (`opencode/frontmatter.py:97-111`, `antigravity/frontmatter.py:148-151`, leaf), not a harness schema; whether it states a fact about the harness is not shown. The sentence beside it says what keeps a model from invoking the command is "**not shown by reading**", which is honest; the first sentence reads as a fact. The parity guard `_gap_claim_contradicted` (`:332-344`, leaf) only looks for the Claude key name in that file, so it cannot see a real OpenCode or Antigravity key. CLAUDE.md says only Claude Code is tested as a runtime | major |
| L3-3 | `_cmd_orchestrator.py:308-311`, `:320` (re-read); `orchestrator_worktree.py:116-138` (leaf) | an unreadable main-anchored `marshal.json`, or a readable one whose top level is not an object | `get use_worktree` answers `success`, value `False`, `set: false`, indistinguishable from a main file that says false; documented, kept, and consistent with the store seam, but against the plan's own "never turns a failing read into a passing one" and the ref-code-quality rule that an unread input is not an empty one | minor |
| L3-4 | `handle-open.md:72` (re-read) | a later decision in the same run that invalidates an earlier decided item | the item stays decided, neither re-analysed nor recorded; silence is consistent with the closed contract (four acts, `orchestration-model.md:541-543`, leaf) but the gap is written nowhere | minor |
| L3-5 | `test_handle_open_contract.py:86-98`, `:689-697` (leaf) | a reopen act worded without the stems `supersed` or `reopen`, a new `Reopen` bullet after `Presentation`, or an Idempotence carve-out that keeps "is not decided again" | the no-reopen pin scans only Step 6 and the decision-acts bullet for two stems, so it misses these | minor |
| L3-6 | `test_analyze_false_claim_contract.py:76`, `:160`, `:169-170` (leaf) | a refactor of `_read_review_surfaces` (PLAN-LB-171 edits `runbook_lane.py`) | the doc-contract test searches the script text for `def _read_review_surfaces(`, a literal `fetch_pr_comments_data(` inside it and no `subprocess.`/`'pr comments'`; a rename or split turns it red in another plan's build, a docstring that merely mentions `subprocess.` fails it falsely, a fetch moved into a helper that shells out passes it falsely | minor |
| L3-7 | `.claude/skills/apply-changes/SKILL.md:27-28` (re-read) | a reader looking for the support | the sentence cites "a citation of third-party documentation" that is in no repository file the leaf read; whether Claude Code honours `disable-model-invocation: true` is not shown by reading. In this orchestrator session the `Skill` tool's listing includes `apply-changes`, which does not support an inference that the key withholds the skill from a model here; it does not refute one either | minor |
| L3-8 | `test_orchestrator_use_worktree.py:330-398` (leaf) | a temporary directory behind a symlink | the new refusal tests assert `str(path) in error` without `.resolve()`, unlike `:131` and `:156`; only a run on such a host would show it | minor |

Also read: the three documents agree with one another (`analyze.md:155`, `landing-payload-spec.md:108-111` and `:255`, `templates/landing-analysis.md:101-108`) and none carries the removed post-merge exemption (leaf); `handle-open.md:72` has no conflict with the Idempotence rule (`:115`) or the four decision acts, and the kept ordering sentence is a workflow-level rule where the contract's header says workflows xref rather than restate (`orchestration-model.md:536`, leaf), which D2 allowed; the code, the docstrings and `data-model.md:314` agree on null or non-dict refused, absent defaulted, an unreadable main file answering the seam's `False`; "matches `orchestrator_use_worktree`" is borne out (`orchestrator_worktree.py:116-138`, leaf); each new message names the file it actually read; `manage-config/SKILL.md:1165` and `manage-config/standards/api-reference.md:187` are stale as the lane says; no new test shells out (the "subprocess marker" is a text search of `runbook_lane.py`); the squash message's four branch commits end with exactly `Co-Authored-By: plan-marshall <noreply@cuioss.de>`.

**Layer 3 not shown by reading:** whether the lane's test-first red runs happened as stated; whether `verify` was green at the tip; whether Claude Code, OpenCode or Antigravity withhold the command from a model; whether `run_graphql` spawns `gh`; whether the string-path assertions hold behind a symlinked temporary directory; the fifth branch commit's stat. Only a run could show these.

**Layer 3 verdict:** findings — 2 majors (L3-1, L3-2), 6 minors (L3-3 to L3-8); 1 not shown by reading

### Conformance to the Project's Own Rules

| Rule source | Rule | Verdict | Evidence |
|-------------|------|---------|----------|
| spec | no new rule is introduced | conforms | `analyze.md:155` restores the pre-LB-165 text; the ordering sentence of `handle-open.md:72` pre-existed and D2 allowed keeping it |
| spec | `get` never turns a failing read into a passing one | deviates | `_cmd_orchestrator.py:308-311`, `:320` (re-read) with `orchestrator_worktree.py:121-125`; kept and documented |
| spec | no file outside the Expected Surface | deviates | `test_analyze_false_claim_contract.py`, declared and justified (L1-2) |
| spec | tests written against the unfixed tree first | not_shown_by_reading | the lane cites job logs; reading the pre-fix code confirms the null-block test would have failed (leaf) |
| CLAUDE.md Documentation Standards | no timestamps, no version history, current state only | conforms | `analyze.md:155`, `handle-open.md:72`, `data-model.md:314` and the three entry points carry none |
| CLAUDE.md Commit Trailer | exactly the plan-marshall trailer and nothing else by way of attribution | deviates | the four branch commits conform; the GitHub squash message adds `Co-authored-by: cuioss oliver …`, lower-cases the plan-marshall line and embeds the CodeRabbit summary |
| ref-code-quality | an unread input is not treated as a clean value | deviates | `_cmd_orchestrator.py:310`, `:320` |
| ref-code-quality | every refusal branch has a test | deviates | the main-anchored non-dict branch (`:314`) is tested only with null; the `set` message (`:399`) has no file-naming test |
| ref-code-quality | docs that govern code match it | deviates | `manage-config/SKILL.md:1165`, `api-reference.md:187` |
| python-core | no bare or broad `except` | conforms | only narrowed `(OSError, ValueError)` handlers |

Points re-read by the orchestrator at the merge commit: `analyze.md:155`; `handle-open.md:72`; `runbook_lane.py:3664-3708`, `:4288-4318`; `_cmd_orchestrator.py:290-329`; `.opencode/commands/apply-changes.md`, `.claude/skills/apply-changes/SKILL.md:1-36`; the PR body of #2031. Not re-read, recorded as unverified leads: the harness metadata files and their generator loaders, the parity test's guards, the other tests, `orchestration-model.md` lines, `github_ops.py` lines, the diff-stat sums, and every `not_shown_by_reading` point.

The leaf's own slips: it was granted neither Grep nor Glob and used `git ls-files`, `git blame -L /regex/`, `git log -L :func:`, `git show`, `git diff` and Read, and no shell `grep`, `find` or `ls`; it skipped the dispatcher's logging and `resolve-workflow` steps under the read-only instruction. The leaf also reported that `apply-changes` is absent from its own session's skill listing; it is present in this orchestrator session's, so that observation is not used as evidence here.

## Metrics and Anomalies

- Tokens: `unknown`, an unobserved fact, no defect.
- Duration: the squash commit is dated 2026-11-20 00:49:15 +0000; the landing message was filed at 01:18:54Z.
- Anomalies: (1) the lane waited out a long CodeRabbit quota cycle (a refusal at 18:44, a 90-minute wait, a second refusal at 20:44, an escalated `@coderabbitai full review` refused at 20:45, a third wait, a review at 22:17) and CodeRabbit re-reviewed the merged head unprompted with two more findings; Sourcery refused on a hard budget. (2) CI `verify` failed once on `test_executor_recovery.py::test_the_printed_command_recovers_the_executor` (a 300 s `pytest-timeout` after a 190 s setup, in a module the PR does not touch) and the rerun was green; recorded by the lane as a flake. (3) The lane queued behind other plans' builds (up to about 986 s of `queued_seconds`). (4) Five `quality-gate` runs reported `status: error` only because `ruff format --check` found files it then auto-fixed. (5) The lane self-reports two guard refusals of its own (`R2` on a `mkdir -p`, `R5` on a stray `python3 /dev/stdin`), both with no effect. (6) `harness=opencode`, `model=deepseek-v4.1-flash/high`, as for the other lanes of this pass, recorded as a fact with no conclusion drawn.

## Routing and Merge Behavior

- Review: the landing claims 10 review-body findings, 10 handled, 0 unresolved threads; coderabbit required (a review at `9d050a2d6` with eight findings and a re-review of the merge head `bbea09213` rated Low risk with two more), sourcery optional (hard quota refusal). Re-read by `runbook_lane review-gate --pr-number 2031`: `unresolved_review_threads` 0 and `review_body_findings_total` 10 (coderabbit `inline-1` to `inline-8`, `nitpick-1`, `nitpick-2`) both agree with the landing. `review_body_findings_handled`: the gate's own read is `0` (`body_findings_undisposed`); the number is re-verified from the lane's progress file, which holds ten `finding:` lines naming exactly those ten ids, two of them declined with a stated reason (inline-2 and inline-3) and the rest each with a commit, so 10 agrees. No false claim. The two declined findings are the lane's own reading; their substance is L3-1 and L3-4 above, recorded as findings of this analysis and not as the lane's decisions.
- **PR body and squash message are this plan's own.** The body of PR #2031 describes the four deliverables and matches the twelve files; the squash message adds a GitHub-generated co-author line and the CodeRabbit summary (L3 conformance row).
- CI/merge: PR `#2031`, state `merged`, merge commit `d32af9f8c`, base `main`, `review_decision: none`; the lane reports `settle merged`, cleanup done. Builds reported: 31 routed jobs (21 targeted `module-tests`, 8 `quality-gate`, 2 `verify`), all `daemon_longpoll`, no killed job; `verify` green twice (34,231 tests at `1759f24e9`, 34,316 at the merge head `bbea09213`); none re-run here.
- Collision with the running PLAN-LB-171: none observed in the diff; L3-6 is a coupling risk, not a collision (a PLAN-LB-171 refactor of `_read_review_surfaces` would turn a test of this plan red).
- Sonar: `n/a` and `step.sonar-roundtrip.open_issue_rules` `n/a`, the lane's `sonar: not_configured`; compared as the claim it is.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-170 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-LB-170 --field pr --value 2031`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-LB-170 --field landing --value landings/PLAN-LB-170.md`
- [x] row `plan_marshall_plan_id` stamped — value `rb-lb-170-lb-165-completion-document-rules-and-missing-tests`, taken from the sender
- [x] epic.md narrative reconciled: the PLAN-LB-165 landing Open Defect is marked FIX SHIPPED IN PART and stays open for the two majors and the leftovers; one new Open Defect (the analyze contract's re-read, L1-1/L3-1); the minors go to the Watch
- [x] resume anchor updated in `resume_anchor.md`
- [x] `queue-view.md` regenerated

## Follow-Ups

- **The analyze contract's re-read cannot be made on the merged head (L1-1, L3-1).** It was already so before PLAN-LB-165. What a re-read at analyze time can honestly claim is the PR's state at the time of the read; the contract needs a rule for the difference that a post-merge change causes (record it with the read's time, with the provider's per-record times where they decide it, and never as an exemption), and `landing-payload-spec.md` and the landing template carry the same wording. This is a defect of the orchestrator's own contract; a fix plan is staged only on the operator's word. Earlier landing reports of this epic that recorded a difference as a **false claim** under this rule (PLAN-LB-165's review total, 4 against 5) did so against the current state of the PR; whether post-merge activity explains that difference was not settled.
- **The apply-changes gap statement (L3-2, L3-7)** rests on the generator's metadata and on a citation no repository file carries; whether any harness withholds the command from a model is a runtime fact nothing here shows. It goes to the Open Defect with L3-1, since a fix of one is a plan over the same few documents.
- The minors (L1-2, L2-1 to L2-7, L3-3 to L3-8) go to the BACKLOG Watch of `epic.md` under the focus rule; the two stale sibling documents (`manage-config/SKILL.md:1165`, `manage-config/standards/api-reference.md:187`) are the lane's own recorded lead.
