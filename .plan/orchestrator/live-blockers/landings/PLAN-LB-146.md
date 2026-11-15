# Landing Analysis: PLAN-LB-146 — a build result names the tree it built, and the freshness gate and the executor hash the same tree

epic: live-blockers
workstream: WS-02
pr: #1971 (squash commit `877a05ac7`, one parent `e81ddd6b10d05baeda22b7ae24c4101255db269d`)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying claims against ground truth (actual code, artifacts, PR state) — a pasted claim is a lead, never a fact.

## Deliverable Fidelity vs Spec

One message from the runbook lane (sender `rb-lb-146-build-result-names-the-tree-built`, revision 0, `merge_state=merged`, deliverables 4/4, `cleanup_owed=true`, self-review `budget-exhausted`). It is `complete: false` on `total_tokens` alone (out of scope under the operator's focus rule). The row was `running` and carried no `pr` or plan id; both are stamped now. The squash commit has one parent, read with `git rev-parse 877a05ac7^` before the leaf prompt named it, and touches 20 paths (read with `git diff --name-only`): 10 under `marketplace/bundles/plan-marshall/skills/`, 10 under `test/`.

Review facts: `review-gate --pr-number 1971` reads 0 unresolved threads and 9 body findings (`inline-1` to `inline-8` and `nitpick-1`); the provider shows 8 review threads. The lane reports 9 of 9 handled, and says the three review bodies carry 10 findings, three of them in "outside diff range" blocks the count does not name; that second figure was not re-derived. **The run's progress file holds no per-finding disposition line at all** (one self-review line for round 1 only), so "9 of 9" cannot be re-read from it; the PR threads and the lane's fix commits are the evidence, and the gate's own 0 unresolved threads agrees. Recorded as partly re-verified, not as false. `sonar_open_new_issues=n/a`.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — the build row and the freshness gate hash the same tree | shipped, with a rollout hazard (F1) and one fail-open route (F2) | the row carries `worktree_root`; the gate compares it (`_cmd_pre_commit_verify_freshness.py:346-399`, re-read); the recorder resolves the root through `resolve_plan_context` (leaf, template L1103-1108) |
| D2 — a rewriting build is named; a mid-build edit cannot fold into one green | shipped-as-specified; stricter than the spec's default (F5) | `worktree_sha_at_dispatch` beside `worktree_sha` (`_ledger_core.py:253-254`, re-read); `worktree_rewritten_by_build` (gate `:283`) |
| D3 — a submit and its wait name the tree they built | shipped-as-specified | leaf read: both replies carry `exec_path`, `project_path`, `plan_id`; plan-less outcomes reach the global work log; the new job-record reads catch `OSError` and `ValueError` |
| D4 — documents and pins | shipped, with a vacuous sweep test (L2-1) and a contradiction between two documents (D-1) | `test_build_tree_naming_doc_contract.py` (leaf) |

The lane's REFUTED hypothesis (the job row "already stores the project path"; it stored a hash) is borne out by the leaf (`_record_job` passed `project_path` only into the hash).

## Three-Layer Analysis

One read-only leaf (`execution-context-level-5`) read the landing; the orchestrator re-read the points marked. By reading: no build, no test run, no write.

- **Verdict:** no blocker as graded; **two majors, both in the freshness path** (F1, F2), one vacuous test (L2-1) and one document contradiction (D-1). F1 is a rollout hazard with a concrete trigger and is the one with an effect today (see the note on the sync below).
- **Leaf rule breaks:** none beyond what it declared (plain `grep` through Bash, no `.plan/` read).

Re-read: `_ledger_core.py:236-257`; `_cmd_pre_commit_verify_freshness.py:340-399`; `execute-script.py.template` by search for the plan-id lines (`:2365-2366`, `:2423`, `:2572`); the squash diff of `runbook_lane.py`; `review-gate` and `ci pr comments`; the changed path list; the surface delta; the progress file. **Not re-read:** the recorder body, the gate's refusal-route table beyond the verdict function, the hash-capture cost claims, the stale-executor import path (the `.plan/execute-script.py` pin is out of bounds and was not read), every test, every document line, `_build_execute_factory.py`.

### Layer 1

| Finding | Claim | Verdict | Evidence |
|---------|-------|---------|----------|
| **F1 (major)** | The gate reads a row as legacy by KEY PRESENCE, but `build_record` always writes both new keys, as `None` when the caller passes nothing. So any writer that has not been updated writes rows the gate refuses for good: (1) an executor generated from the previous template, once it imports the new `_ledger_core`; (2) the documented `manage-change-ledger append --kind build` CLI (`manage-change-ledger.py:141-149`, leaf). The refusal tells the caller to re-dispatch, which writes another refused row, so the push gate halts until the executor is regenerated | checked at code level (re-read: `_ledger_core.py:253-254`, gate `:366-386`); the stale-executor import path is NOT shown | refutes the rollout assumption that regeneration can wait | Concrete state: a plan worktree on `877a05ac7` or later, run through an executor not yet regenerated, runs `verify` green and then reads `stale / worktree_root_unreadable`. The key-presence rule came from a CodeRabbit fix; the docstrings of `build_record` and the CLI still say `None` means "written before the fields existed" |
| **F2 (major, fail-open)** | The recorder takes the plan id from `--audit-plan-id` when `--plan-id` is absent (template `:2365`, re-read), strips that flag before the wrapper runs, and hashes THAT plan's worktree at both dispatch and completion, so `pyproject_build run --audit-plan-id X` from the main checkout, which builds the checkout, records X's worktree hash twice and reads `fresh` for X | checked (plan-id fallback re-read; the hash path is the leaf's, not traced) | refutes the lane's own disclosure ("off-spec combination") as complete | Off-canonical: the resolved executables carry `--plan-id`. Before the change the row hashed the cwd, so this route read stale. The `_ledger_tree_root` docstring says naming X's tree "makes the mismatch visible"; the gate compares X with X |
| F3 (minor) | the CLI writer and `build_record` docstrings say null means "hand-appended / written before the fields existed", which the gate refuses | leaf | refutes | same root cause as F1 |
| F4 (minor) | the dispatch capture runs three untimed git calls before the build, so a hung git now blocks the build from starting; one nested executor run per build resolves the root | leaf | refutes (cost) | `worktree_sha.py:58-75`; non-build calls run no git (leaf) |
| F5 (info) | `worktree_rewritten_by_build` refuses a completion-matching row whenever the build rewrote the tree: stricter than the spec's "match only on the completion hash" default, so a formatter that rewrites a tracked file on every run can never clear the gate | leaf | none | the PR's recorded decision was not read |
| C6 (info) | the `runbook_lane.py` label `files with no reviewable changes` was added under an operator selection, with a test whose fixture has the real block's shape but placeholder icon URLs while its docstring says "captured verbatim" | leaf (squash diff re-read) | confirms (shape) / refutes (docstring) | `test_runbook_lane_review_gate.py:431-451` |

### Layer 2

- **L2-1 (major, vacuous):** `test_no_document_still_describes_the_plan_less_submit_as_silent` searches for `A plan-less build is silent by design.`; the parent document reads `**Plan-less builds are silent by design.**`, so the sweep could not fail at the parent, and two pins borrow the wrong string as their `retired` text (leaf, `e81ddd6b1:build-server-client/SKILL.md`; not re-read).
- L2-2 to L2-5 (minor): a stub raises `TypeError` instead of the intended error; a per-slice count pin was dropped from `test_freshness_exempt_vs_verified_discrimination.py`; no test covers F1, F2 or the real manage-status shell-out; logging isolation of the recorder's `main()` test not checked.
- **Real control:** each doc control ends `assert not _pin_states(pin, planted)`; the leaf grades it mechanically real and substantively weak (it replaces the pinned snippet, so it fails whenever the snippet is removed); not carried as an empty control.
- The recorder test that drives the executor's real `main()` does exec the rendered template and a real child edit in a real git repo (leaf).
- **Surface delta:** declared 12, realized 20, **added 12, missing 4** (`expansion_detected`): added are the manage-change-ledger files, `manage-tasks.py`, `push.md`, `runbook_lane.py` and six tests (new modules the spec said would be named at outline, plus `test_runbook_lane_review_gate.py`, `test_generate_executor_behavior.py`, `test_freshness_exempt_vs_verified_discrimination.py`); missing are the two HYPOTHESIS entries `marshalld.py` and `worktree_sha.py` (correctly untouched) and the two gate test files the spec named OBSERVED (`test_pre_commit_verify_freshness*.py`: the lane put its gate tests in new modules). The lane names the `runbook_lane.py` extension as its one scope extension.
- **Overlap with the running PLAN-LB-148:** `runbook_lane.py` and `test_runbook_lane_review_gate.py` are PLAN-LB-148's surface. This landing already added the label PLAN-LB-148 deliverable 3 adds, so that deliverable is now redundant and may conflict at the list when the lane merges `main`.

### Layer 3

- **D-1 (major, contradiction on a gate):** `manage-change-ledger/SKILL.md` says the two fields are "both optional and `None` for a row written before they existed" and that "the payload-less CLI writer needs no change"; `manage-tasks/SKILL.md` says a legacy row has no key and a `null` is unreadable and never matches; the code follows `manage-tasks` (leaf; code re-read).
- D-2 (minor): `build-server-client/SKILL.md` still says every submit and wait is logged to the plan work log. D-3 (minor): change-history wording in `manage-tasks/SKILL.md`, `build-server-client/SKILL.md`, `build_server.py`, the template and the gate (leaf lists the phrases). D-4 (minor): the `_ledger_tree_root` subdirectory claim holds only when the hashes happen to be equal.

### Conformance

| Rule source | Rule | Verdict | Evidence |
|-------------|------|---------|----------|
| Spec constraint | fail closed: an unresolvable root never reads as the same tree | conforms for the gate; **deviates on the recorder's `--audit-plan-id` route (F2)** | |
| Spec constraint | one reader per concept | conforms (same resolver call) | leaf |
| Spec constraint | docs state current behaviour | deviates (D-3, D-1) | |
| Spec constraint | executor regeneration owed in every project | **conforms in the PR text, but see F1**: the owed regeneration is a blocking prerequisite in a source checkout, not a housekeeping item | |
| CLAUDE.md § No shell file operations | | lane-reported: two guard refusals (R2 on `cp` into the base-evidence tree, R5 on a mistyped interpreter call), neither worked around; `cp` of the committed test files into the base tree is the base-sha recipe's own text defect already on record | message §7 |
| CLAUDE.md § Merge Authorization (Standing) | | **conforms, with three operator questions asked about non-merge matters** (self-review round limit, the CodeRabbit quota, the lane's parser); none asked whether to merge | message §6 |

## Metrics and Anomalies

- Tokens: `unknown` (out of scope). Anomalies: 14 routed builds, one bound expiry (the first `verify`, 720 s) continued with the split form; CodeRabbit refused four triggers on its quota before the operator's "keep retrying" selection and the fifth succeeded (lane-reported, not re-read).
- **Owed cleanup:** `.plan/local/worktrees/lb-146-build-result-names-the-tree-built-base` remains (confirmed by `git worktree list`: detached at `280e6c404`); `git worktree remove` refused because the base-sha recipe's four copied test files are untracked there. The lane did not force it. It holds nothing but those copies (the lane's statement); removing it is an operator action.

## Routing and Merge Behavior

- CodeRabbit (required) reviewed four heads (the lane: `5dee22bad`, `825f4053e`, `27e816ff1`, `9fee6f42e`); every thread resolved with a reply per the lane; sourcery refused on its quota. The merge ran through the lane's own worktree executor because the parser extension that makes the gate decidable was this PR's own change; stated in message §7, so the lane's verdict is not the unpatched gate's.
- CI green on every head after `5dee22bad` (lane-reported); the PR reads merged through the queue as a squash with one parent.
- Sonar: `n/a`; ignored in this project.

## Reconciliation Actions

- [x] row `status` → `shipped`; `pr` 1971; `landing` `landings/PLAN-LB-146.md`; `plan_marshall_plan_id` `rb-lb-146-build-result-names-the-tree-built`
- [x] epic.md annotation and Decisions entry; the resume anchor; `queue-view.md`
- [x] message archived after the persist

## Follow-Ups

- **Residue, one surface (the freshness gate, the ledger writers and their documents) = plan D, now unblocked** because PLAN-LB-146 has shipped: F1 and F2 (the two majors), F3, F4, F5's recorded decision, L2-1 to L2-4, D-1 to D-4, plus the operator's decisions 1 and 2 already settled (a lone Gradle row read as scoped; a deliverable retired with no successor is removed from the outline). A grounding read comes first; F1's fix direction is open (the writer omits the keys unless it has a fact to record, so a writer that cannot record looks legacy by absence and a writer that failed to capture writes an explicit null).
- **The executor regeneration is now urgent in this repository** (F1): see the Decisions entry.
- **PLAN-LB-148 deliverable 3 is redundant** (the title is already on `main`); the lane is running; whether to tell it is the operator's call.
