envelope_version=1
sender_type=plan
sender_id=rb-lb-170-lb-165-completion-document-rules-and-missing-tests
epic=live-blockers
kind=landing
created=2026-11-20T01:18:54Z

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-170-lb-165-completion-document-rules-and-missing-tests
epic=live-blockers
pr=#2031
merge_state=merged
cleanup_owed=false
deliverables_total=4
deliverables_done=4
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash/high
effort=high
plugin_version=0.1
executor_version=0.1.2155
steps=setup:done,implement:done,build-gate:done,self-review:clear,pr:done,reviews:done,merge:done
unresolved_review_threads=0
review_body_findings_total=10
review_body_findings_handled=10
sonar_open_new_issues=n/a
step.sonar-roundtrip.open_issue_rules=n/a
```

guard: present (tool-call guard active on this harness; see § Rule check)

# PLAN-LB-170 landing — PLAN-LB-165 completion

Merged as `d32af9f8c4f9d21a89c6f026d429efcd1d50cfec` (PR #2031, squash, 12 files, +1239/−40 across five commits).

## 1. Deliverables

Every Done-when's evidence order is `test-first`: the test was written and seen failing against the unfixed code.

### D1 — the false-claim paragraph is head-bound again — met

| Done-when (as written) | Verdict | Test | Order | Failing run | Commit |
|---|---|---|---|---|---|
| The added sentence and the "current state" wording are removed, the head-bound wording restored | met | `test_analyze_false_claim_contract.py::TestFalseClaimIsHeadBound` | test-first | worktree HEAD `b5426d3c5^`, job log `35644b4d0b5b4a09a52d27c2495b4f11` (3 failures) | `b5426d3c5` |
| Only the stale clause is corrected, and only if the parser no longer reads `ci pr comments` | met — HYPOTHESIS confirmed by reading `runbook_lane.py:3009-3056` (one in-process `fetch_pr_comments_data` fetch; no subprocess) | `test_the_review_gate_reads_the_provider_in_process` + `test_the_paragraph_names_the_provider_read_instead_of_the_stale_subcommand` | test-first | same run | `b5426d3c5` |
| A test pins the chosen form | met | the file above (13 tests, 4 planted controls) | test-first | same run | `b5426d3c5`, extended `5bbe3aacf`, `6c95b6916` |

**Form chosen: (a), with the reason.** (b) would keep a post-merge exemption "in a form the drain can decide from observable data". The drain cannot: `review-gate` reports counts, not per-comment timestamps, so a difference cannot be classified as post-merge activity. (a) restores the contract the standard already states and adds no rule. The residual consequence — a thread reopened after the merge now reads as a difference — is real and is recorded in § 9.

### D2 — the Step 6 reopen/supersede sentence is out — met

| Done-when | Verdict | Test | Order | Failing run | Commit |
|---|---|---|---|---|---|
| The reopen clause is removed and the PLAN-LB-165 reword stays | met | `test_handle_open_contract.py::TestStepSixDecisionSemantics` | test-first | `3b6a1f516^`, job log `7ff3d227f9774173bf6e6fb5fd221449` | `3b6a1f516` |
| The item-number ordering is settled (kept as a stand-alone sentence) | met — **kept**: it is true, it clarifies the sequence the re-analysis rule depends on, and with the reopen clause gone it no longer implies a decided item is revisited | `test_the_item_number_ordering_stays_as_a_stand_alone_sentence`; ordering + 2 planted controls | test-first | same run | `3b6a1f516`, scoped `5bbe3aacf` |
| `test_handle_open_contract.py` pins the reworded sentence and the absence of a reopen act | met | same class + `test_the_contract_states_no_reopen_act` (reads the standard's decision-acts bullet) | test-first | same run | `3b6a1f516` |

### D3 — the null-block fix has its tests, and its edge behaviour is settled — met

| Done-when | Verdict | Test | Order | Failing run | Commit |
|---|---|---|---|---|---|
| Null, absent and non-dict tests, in the files that already exercise `get` | met | `test_orchestrator_scope.py` (null / absent / non-dict + a three-state table) and `test_orchestrator_use_worktree.py::TestBlockStates` (null in the caller's file, null in the main-anchored file, absent, unreadable) | test-first | `fced1a4c3^`, job log `57d39b949f764a068f0f3a3e8eeb7f5c` (3 refusals did not name the file) | `fced1a4c3` |
| Written against the unfixed tree first | met | the null-block case needs a tree without the fix: detached base worktree at `a21b19ed7` (the parent of `a3a1907e5`, the merge that shipped the fix), job log `a93bf6c352d7422c90acbd4ee1159ab2` — `a null block was read as success: {'status': 'success', 'value': 90}` | test-first | as recorded | `fced1a4c3` |
| The beyond-spec behaviours are settled with a reason | met — table below | — | none | — | `fced1a4c3` |
| `data-model.md:314` and the handler docstring follow the code | met | `data-model.md:314`, `_cmd_orchestrator.py:32-38,266-276` (+ `5bbe3aacf` scoping fix) | test-first | same runs | `fced1a4c3`, `4bc23010e` |
| The three D1 minors are settled, each reason in this landing message | met — table below | — | none | — | `fced1a4c3` |

**Beyond-spec behaviours.**

| Observation | Disposition and reason |
|---|---|
| The null/non-dict check runs before the `use_worktree` branch, so a malformed block in the caller's own `marshal.json` makes `get use_worktree` error | **Stays.** It is the verb's single precondition for every field; exempting one field would make the same malformed file error for every other knob and pass for this one, and refusing is the fail-closed direction |
| Invalid JSON in the caller's file raises a `ValueError` `main()` does not catch | **Stays.** Pre-existing for every verb and field, and a traceback is not a success. Fixing it needs `manage-config.py`, outside this plan's surface |
| The main-anchored check swallows `OSError`/`ValueError` and answers success `False` | **Stays.** It matches `orchestrator_use_worktree`, which reads the same file the same way; the value answered is the one the store actually uses, so `get` and the seam cannot disagree |
| Both errors carried the same message and named neither file | **Fixed.** Both refusals now name the file (L3-6) |
| The main file is read three times in one branch | **Stays.** Three owners read it (verb validation, the `tools-file-ops` value reader, the `set`-flag reader); collapsing them would duplicate that reader here |

**The three D1 minors.**

| Minor | Disposition and reason |
|---|---|
| The figure `90` repeated in `data-model.md` | **Kept.** `data-model.md` is the canonical restatement location the handle-open contract test names ("the default lives in `DEFAULT_ORCHESTRATOR` and is restated only by the data-model table"); the table row, the seeded-shape example and the validation sentence each serve a different read |
| The "Unreachable" comment | **Kept.** Re-read: all four whitelisted fields are handled above it, so it is accurate |
| The `kinds[]` pin | **Already carried** by the Output contract in `handle-open.md:130-134`, and not test-pinned; nothing to add |

### D4 — `/apply-changes` is operator-only on every harness, with the gap recorded — met

| Done-when | Verdict | Test | Order | Failing run | Commit |
|---|---|---|---|---|---|
| The Claude key stays and its honoured-or-not status is stated in a repository file | met — `SKILL.md:5` + `:24-29`, marked not shown by reading | `test_the_command_is_operator_only_on_every_harness` | test-first | `1759f24e9^`, job log `a90541f03d464d309c18e48467bad1e7` | `1759f24e9` |
| Each other harness records the gap in a repository file, saying what keeps a model from invoking it | met — both entry points name their target's `frontmatter-rules.json` as the authoritative field set and record the mechanism as unconfirmed | same test + `test_each_gap_claiming_harness_has_its_rules_file_to_check_against` | test-first | same run | `1759f24e9`, `5bbe3aacf` |
| "User-invoked by construction" is not assumed for Antigravity | met — the skill-with-invocation-trigger caveat is stated | same | test-first | same run | `1759f24e9` |
| The parity test pins the key and the recorded gap, so the key cannot be removed green | met — the guard also reads the cited metadata and reports a contradiction; 5 controls | `test_apply_changes_command_parity.py` (22 tests) | test-first | same run | `1759f24e9`, `5bbe3aacf`, `6c95b6916` |

**HYPOTHESIS confirmed:** neither `marketplace/targets/opencode/frontmatter-rules.json` nor `marketplace/targets/antigravity/frontmatter-rules.json` publishes a key that withholds a command or skill from model invocation (verified field-by-field, and now checked by the test on every run).

**Per-head test runs:** every pushed head that mattered was tested — `b5426d3c5`, `3b6a1f516`, `fced1a4c3`, `4bc23010e`, `9d050a2d6`, `5bbe3aacf` (targeted module runs), and `1759f24e9`, `bbea09213` (full `verify`, 34,231 and 34,316 tests). Head `6c95b6916` carries targeted runs plus CI's own `verify` (green, job 135986886339).

## 2. Personas and skills

| Step | Persona applied |
|---|---|
| D1, D2 (documents) | `persona-documenter` (declared) |
| D3, D4 (code and tests) | `persona-implementer` (declared) |
| every self-review round, PR-comment triage | `persona-code-reviewer` |

Declared domain skills, loaded as standards before each deliverable: D1/D2 `plan-marshall:ref-code-quality`, `pm-documents:ref-documentation`, `plan-marshall:plan-orchestrator`; D3 `plan-marshall:ref-code-quality`, `pm-dev-python:python-core`, `plan-marshall:manage-config`; D4 `plan-marshall:ref-code-quality`, `pm-plugin-development:plugin-architecture`, `pm-dev-python:pytest-testing`.

**Surface addition (declared):** `test/plan-marshall/plan-orchestrator/test_analyze_false_claim_contract.py` is a 13th path, outside the spec's Expected Surface. D1 requires "A test pins the chosen form" and the surface names no coherent in-surface home for an `analyze` doc test (the only in-surface test file is the handle-open module, and the natural home — `test_analyze_three_layer_contract.py` — is a three-layer contract file and is itself outside the surface). No other file outside the surface was touched.

**Skills added for surface drift:** none.

## 3. Hypotheses

| Hypothesis | Verdict | Evidence |
|---|---|---|
| `runbook_lane review-gate` no longer reads `ci pr comments`, so that clause is stale | **confirmed** | `runbook_lane.py:3009-3056`: `_read_review_surfaces` routes the provider, then calls `fetch_pr_comments_data` in-process; no subprocess, no `pr comments` call. Now pinned by a test that reads the function |
| OpenCode and Antigravity publish no key that withholds a command or skill from model invocation | **confirmed** | both `frontmatter-rules.json` files enumerated; neither carries such a key. Whether either harness honours its frontmatter remains *not shown by reading* and is recorded as unconfirmed in the entry points |

## 4. Findings

### Self-review (3 rounds, sub-agent, persona-code-reviewer)

Round 1 (10 findings): F3 over-broad "unreadable file" sentence, F4 an exception-type pin, F5 a prose-only gap guard, F6 an over-claimed control docstring, F7 a brittle subprocess marker — **fixed**; F1 the out-of-surface test file and F2 two stale sibling docs — **accepted and recorded** (§ 2, § 9); F8/F9/F10 — **recorded here** (form (a) as ordered; "already carried" wording; the D1/D2/D3 rationales above). Round 2 (4 minors): a success-shaped `SystemExit` passing, the narrowed subprocess marker, an unjoined harness map, one detector control — **all fixed**. Round 3: clear.

### PR review (CodeRabbit)

| Finding | Disposition |
|---|---|
| inline-1 — the operator-only paragraphs re-list the target metadata fields | fixed `5bbe3aacf` |
| inline-2 (major) — a thread reopened after the merge reads as a false claim; compare against the merge-gate snapshot instead | **declined**: the spec settles form (a) and forbids the decidable exemption; `runbook_lane.py` is owned by PLAN-LB-167/168; the consequence is recorded as a lead (§ 9). CodeRabbit re-reviewed the merged head and rated the PR **Low** risk with this named as an owner-aware follow-up |
| inline-3 (major) — a later decision that invalidates an earlier decided item has no reconciliation | **declined**: the Standing Constraint forbids a new rule; the act, its Idempotence carve-out and its Output row must land together, which this plan does not take. Recorded as a lead (§ 9) |
| inline-4 — derive the gap-harness key set from `SYNC_TARGETS` | fixed `5bbe3aacf` |
| inline-5 — the key branch skipped the uncertainty check | fixed `5bbe3aacf` |
| inline-6 — the absent-block fields mirrored the scalar whitelist | fixed `5bbe3aacf` |
| inline-7 — the standard check read two of four metric rows | fixed `5bbe3aacf` |
| inline-8 — the graded metric population mirrored `analyze.md` | fixed `6c95b6916` |
| nitpick-1 — the Step 6 pins searched the whole document | fixed `5bbe3aacf` |
| nitpick-2 — the OpenCode gap control could pass on the uncertainty diagnostic | fixed `6c95b6916` |

Sourcery published no review (hard quota: 250k diff characters, next eligible in 1 day and 1 hour). Its refusal carries no findings.

## 5. Reviewers

| Reviewer | Role | Outcome | Heads | History |
|---|---|---|---|---|
| coderabbit | required (`quota_limited`, `review_complete_after_handling`) | **reviewed** | `9d050a2d6` (findings), `bbea09213` (merge head, marker `kind=reviewed`, risk Low) | triggered 18:44:57Z → refused (quota); waited 90 min → triggered 20:44:39Z → refused; escalated `@coderabbitai full review` 20:45:28Z → refused; waited 90 min → triggered 22:17:21Z → **reviewed** (`9d050a2d6`, 8 findings). Re-reviewed the merged head unprompted (2 more findings). Never re-triggered for a later head: the `review_complete_after_handling` exemption applies, its qualifying review is on record, and every finding of it is handled |
| sourcery | optional (`quota_limited`) | refused (hard quota) | — | triggered 18:45:08Z → refused; optional, never gated the merge |

## 6. Operator questions

**None asked.** No blocker, no rule that had to bend, and no required reviewer that had to be obtained by the operator: the coderabbit quota cycle in § 5 was spent in full before any question would have been due. No free-text operator messages arrived during the run.

## 7. Rule check

- **Guard:** present on this harness. Read `{guard_log}` (`.plan/temp/guard.log`) for this run's sessions. Two refusals, both mine, both with no effect:
  - `R2` — `mkdir -p .plan/temp/lb170-base-originals` (a snapshot directory I then did not need; the base-evidence work used an untracked probe file instead).
  - `R5` — a stray `python3 /dev/stdin` invocation, refused before it ran anything; the thread reply was posted through the executor instead.
- **Shell file operations the run issued:** those two refusals are the whole mutation-class count; every other file read and write went through the file tools, and the base tree's cleanup used `git clean` scoped to the one probe path and the owner marker.
- **Restarts / killed sub-agents / re-dispatches:** none. The self-review ran as three rounds in two sub-agent sessions; nothing was re-run on their behalf.
- **Spec read:** `spec_source: ledger_worktree`; no `spec_differ` marker at the setup read or the landing-time re-read (the main checkout's copy and the ledger worktree's copy agreed).
- **Executor skew:** `not_applicable` — a source checkout, where the executor maps the checkout's own scripts. Recorded, and no question raised.
- **Builds:** every one routed (`mechanism=daemon_longpoll`); one CI job re-run (below), which is a CI action, not a build.

## 8. Build server

- Setup preflight: **ready** (`registered: true`). Landing-time resolve: **ready**.
- Builds: **31** routed jobs — 21 targeted `module-tests` runs, 8 `quality-gate` runs, 2 `verify` runs. Every one resolved `mechanism=daemon_longpoll`; **no degraded fallback, no launch-fault retry, no killed job**. Jobs queued behind other plans' builds (up to ~986 s of `queued_seconds`, `PLAN-LB-167`'s worktree) — the per-directory/slot serialization working as designed.
- Five `quality-gate` runs reported `status: error` solely because the gate's own `ruff format --check` found files it then auto-fixed in place; each was followed by a green rerun. Recorded as build results, not as server faults.
- `verify` (the gate canonical) green twice on this branch: 34,231 tests at `1759f24e9`, 34,316 at the merged head `bbea09213` — both green.
- `runtime_stamp_reason`: not present (every stamp fact was measurable).

## 9. Residue

- **A thread reopened after the merge will be recorded as a false claim** (CodeRabbit inline-2). This is the deliberate cost of form (a): the alternative needs a recorded merge-gate snapshot in `runbook_lane.py`, a file owned by PLAN-LB-167/168. Lead for that owner.
- **A later decision that invalidates an already-decided item has no stated reconciliation** (CodeRabbit inline-3). Closing it needs the decision act, its Idempotence carve-out and its Output row in one plan. Lead for the next `handle-open` plan.
- **Two stale sibling docs** still describe `get use_worktree` as the unqualified seam value: `manage-config/SKILL.md:1165` and `manage-config/standards/api-reference.md:187`. The drift predates this plan (the refusal landed in PLAN-LB-165) and both files are outside this plan's declared surface, so they are recorded rather than fixed.
- **CI flake:** the first `verify` on `5bbe3aacf` failed on `test/plan-marshall/tools-script-executor/test_executor_recovery.py::test_the_printed_command_recovers_the_executor` — a `pytest-timeout` at 300 s after a 190 s setup, in a module this PR does not touch. The rerun was green; recorded so the flake is visible.
- **Cleanup:** owed for nothing — the base-evidence worktree was removed with `git worktree remove` after a clean `status --porcelain`, the plan worktree was removed the same way after the merge, and the branch's local and remote refs were pruned.
