# Landing Analysis: PLAN-LB-152 — Review-gate single-read cleanup

epic: live-blockers
workstream: WS-05
pr: #1992 (https://github.com/cuioss/plan-marshall/pull/1992)

> Landing record for one shipped plan. Lives at `landings/PLAN-LB-152.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Runbook lane, sender `rb-lb-152-review-gate-single-read-cleanup`, harness `opencode`, model `deepseek-v4.1-flash/high`.
Squash merge `637b5048d8426bb67e5e09f0ca1f3f3c6a003bfc` on base `06e5da77a`, branch
`fix/lb-152-review-gate-single-read-cleanup`, merge-group run `43727419979` `success`. Message
`rb-lb-152-review-gate-single-read-cleanup-001.md` is `complete: false` on `total_tokens` alone (out of scope, no defect).

## Deliverable Fidelity vs Spec

Corroborated with the CI abstraction (`merged`, merge commit as stated), `git diff --stat` over the merge (seven files, 228 insertions,
116 deletions), the lane's progress file, and a `review-gate` re-run. The seven files are the declared surface minus the two
`manage-tasks` scripts, which the spec made read-only hypothesis files and which did not move because the hypothesis was confirmed.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 contract and verdict code describe only the single in-process read | shipped-as-specified | `runbook-lane/SKILL.md:202-221` names no unreachable reason and states the in-process GitHub read; `runbook_lane.py:2758-2771` (the `complete is not True` arm now also takes a missing key); `_required_review_read_failure` and its call gone; pin `test_the_lane_text_names_no_reason_the_verdict_cannot_return` (`test_runbook_lane_review_gate.py:768`) |
| D2 a failing flatten is classified, the import placement is pinned | shipped-as-specified | `runbook_lane.py:2779-2787` guard over `_REVIEW_READ_EXCEPTIONS`; flatten test and import-placement test in `test_runbook_lane_review_gate.py` |
| D3 tests do not depend on the machine and do not leak state | shipped-modified | the provider fixture, `outside_repo_dir`, the `pytest.fail` pin and its companion, the cleaned `_lane_admits` are all in; the sub-clause "`get_default_cwd()` the same before and after the whole module" is **not met as written** and the lane says so (see L1-2) |
| D4 wording is current-state only | shipped-as-specified | the five named docstrings state present behaviour (`github_re_review.py:112-123`, `_github_pr.py:595-597`, the test docstrings); one further docstring, `_match_review`, was edited for the CodeRabbit finding and is accounted for by `4a35735f4` |

## Three-Layer Analysis

The landing was read on three layers — the spec, the deliverable trace, and the merged code — by one read-only leaf, and the orchestrator
re-read the points recorded below as re-read before writing them here. The reading is **by reading, no build, no test run, no write**: what
only a run could show is tagged `not shown by reading`.

- **Dispatch:** one read-only leaf per landing — reason: a full ship, so the merged code is read for the spec premises, the deliverable trace and defects, which is the depth the dispatch rule exists for.
- **Verdict:** layer 1 findings (two refuted spec premises, both authoring faults of this orchestrator); layer 2 findings (one minor: the reason-list pin's reach); layer 3 findings (minors only, no blocker, no major).

Re-read by the orchestrator at the line on the merged tree: `runbook_lane.py:2758-2787`, `github_re_review.py:98-123`, `analyze.md:155`,
`test_runbook_lane_review_gate.py:742-780`, and the spec's Standing Constraints. Leaf-only, not re-read: the `github_ops.py` fetch
postcondition, `ci_base.py:902/915`, the flatten and import tests' bodies, `_lane_admits`, the comment-arm refusal classification, and
the pre-existing history wording.

### Layer 1 — Specified

| Finding | Claim | Verdict | Polarity | Evidence (file:line) |
|---------|-------|---------|----------|----------------------|
| L1-1 | D1 Done-when: a read with no `complete` key already answers `undecidable_read` "and not a traceback" and "holds at `2bf7cd83d`". False: the base carried an explicit `'complete' not in read` branch answering `coverage_unavailable`; so did the Standing Constraint "the only new verdict is `undecidable_read` where there was a traceback". Neither input is reachable by a real read | checked | refutes | `runbook_lane.py:2765-2771` (merged arm); base branch read by the leaf; lane's red run `a13830ee…` agrees |
| L1-2 | D3 Done-when: `ci_base.get_default_cwd()` the same before and after the whole module, "fails at `2bf7cd83d`". It cannot: `test/conftest.py::_reset_ci_default_cwd` is autouse and clears the value around every test | checked | refutes | `test/conftest.py` (`_reset_ci_default_cwd`); lane's green mutation `14a227d5…` |
| L1-3 | Standing Constraint names a `PLAN_MARSHALL_HOME` fixture; no conftest defines one | checked | refutes | leaf search; only `test/plan-marshall/script-shared/test_marketplace_paths.py` matches (leaf-only) |
| L1-4 | Hypothesis: the `manage-tasks` freshness scripts use `coverage_unavailable` as their own reason | checked | confirms | `_freshness_crosscheck.py:1447`, `_cmd_pre_commit_verify_freshness.py:792`; persisted as `corroborated` on claim 5 |
| L1-5 | Hypothesis: `forbid_run` does not trip for a read routed through `ci_base.run_cli` | checked | confirms | `ci_base.py:902, 915`; persisted as `corroborated` on claim 10 |
| L1-6 | Objective "changes no verdict a real read can produce" | checked | confirms | `github_ops.py` fetch always sets `complete` and emits dicts only (leaf-only) |
| L1-7 | The spec's Expected Surface left out `analyze.md`, which still describes the old read | checked | refutes | `analyze.md:155` (re-read) |

**Layer 1 verdict:** findings — 4 refuting (L1-1, L1-2, L1-3, L1-7), 3 confirming. L1-1 to L1-3 are this orchestrator's authoring, the
same class as the PLAN-LB-150 and PLAN-LB-151 entries: a "holds at base" written without reading the base, a Done-when no run can fail,
and a constraint naming a fixture nobody checked.

### Layer 2 — Implemented

| Deliverable | Code trace | Test that can fail | Unexplained file / unborne claim | Verdict |
|-------------|------------|--------------------|---------------------------------|---------|
| D1 | `runbook_lane.py:2758-2771`, `SKILL.md:202-221` | `test_the_lane_text_names_no_reason_the_verdict_cannot_return` (`:768`) fails against the base text; `test_a_read_without_a_coverage_signal_is_undecidable` | none | checked |
| D2 | `runbook_lane.py:2779-2787` | flatten test (a `str` entry raises `TypeError` in the `{**comment}` flatten); `sys.modules['ci_base'] = None` import pin — its mutation outcome is not shown by reading | none | checked |
| D3 | provider fixture, `outside_repo_dir`, `_forbid_cli` | `pytest.fail` escapes `run_cli`'s `except Exception`; the temp-directory run and the red mutations are not shown by reading | none | checked |
| D4 | `github_re_review.py:112-123`, `_github_pr.py:595-597` | documentation pin (existing module) | `_match_review` docstring edit is outside D4's list; the narrative accounts for it (`4a35735f4`) | checked |

- **L2-1 (minor, re-read):** the reason-list pin reads only the paragraph that follows "It answers `merge_allowed: false`"
  (`test_runbook_lane_review_gate.py:752-757`) and only tokens written as ``(`token` ``. The provider paragraph at `SKILL.md:217-221`, where
  the base wrote `coverage_unavailable`, is outside it, so a stale reason there would pass. The Done-when ("the reason list") is met
  literally.

**Layer 2 verdict:** findings — 1 (L2-1). Every file the diff touched is explained, and the lane's narrative holds against the diff,
including its own "not met as written" grading of D3.

### Layer 3 — Correct

| Defect | File:line | Triggering input | Effect | Severity |
|--------|-----------|------------------|--------|----------|
| L3-1 | `github_re_review.py:98-99` | reading the module docstring | still says both discriminators "append every refusal they skip to a per-poll accumulator"; the bounded sentence the CodeRabbit fix added at `:121-123` says a skip ahead of the refusal test is not recorded, and the code agrees with the latter. The overstatement the fix targeted survives two paragraphs above it (re-read) | minor |
| L3-2 | `runbook_lane.py:2770` | an envelope with no `complete` key | the detail reads "truncated: not every connection was drained", a cause that did not happen; the test pins `'truncated'` (`:749`). Fails closed; no real read produces the input (re-read) | minor |
| L3-3 | `analyze.md:155` | a reader of the analyze verb | still says `review-gate` is the parser "from `ci pr comments`"; the gate reads in-process (re-read). Outside the declared surface | minor |
| L3-4 | `github_re_review.py:121` | reading the gate list "authorship, the head reference, or the trigger time" | exact for the review arm only; the comment arm has no head-reference gate, and an enumerative-layer refusal matching an acknowledgment pattern is classified as an acknowledgment, not recorded (leaf-only) | info |
| L3-5 | `runbook_lane.py:6`, `github_re_review.py:128-130`, `test_runbook_lane_review_gate.py:5-22, 976` | reading untouched lines of touched files | pre-existing change-history wording ("used to", "pre-fix policy"), not added by this change (leaf-only) | info |
| L3-6 | `runbook_lane.py:2781` | an exception outside the tuple (`KeyError`, `IndexError`, `RecursionError`) in the flatten | still escapes as a traceback: fails closed, unclassified (leaf-only) | info |

**Layer 3 not shown by reading:** that the module passes from a temporary directory with no `.plan/marshal.json` above it; that each
cited mutation run went red (`assert [] == [7]`, `DID NOT RAISE Failed`, the unreachable-reason message); that `quality-gate`,
`module-tests` and `verify` are green at the merged head. The lane reports all of these with job-log paths; no run was made here.

**Layer 3 verdict:** findings — 6, none above minor. **No blocker and no major.** Stopping is preserved on every input that stopped at base
and no admit path was added: the two inputs whose result changed went from a stop or a traceback to an `undecidable_read` stop (re-read of
`:2758-2787`).

### Conformance to the Project's Own Rules

| Rule source | Rule | Verdict | Evidence |
|-------------|------|---------|----------|
| CLAUDE.md Documentation Standards | No version history, current state only (changed text) | conforms | `SKILL.md:217-221`, `github_re_review.py:112-123`, `_github_pr.py:595-597` |
| CLAUDE.md Documentation Standards | No version history (untouched text in touched files) | deviates | L3-5, pre-existing |
| CLAUDE.md Documentation Standards | No timestamps | conforms | changed text carries none |
| CLAUDE.md Documentation Standards | No duplication | deviates | pre-existing: `runbook_lane.py:2644-2650` and `:2664-2668` restate one rationale |
| CLAUDE.md Commit Trailer | `Co-Authored-By: plan-marshall <noreply@cuioss.de>`, no footer | conforms | the squash commit's trailer |
| `pm-dev-python:python-core` | explicit exception handling, no bare `except` | conforms | one named tuple shared by both guards |
| `pm-dev-python:pytest-testing` | isolation and state restoration | conforms | `monkeypatch`, `restore_default_cwd`, conftest reset |
| `plan-marshall:persona-module-tester` | matched controls; tests that can fail | conforms | shape table keeps admitting and refusing rows; the new pins name a red mutation |
| CLAUDE.md Build Commands | gates green | not_shown_by_reading | only a run shows it |

## Metrics and Anomalies

- Tokens: `unknown` (the runbook lane writes `unknown` rather than a guess; measurement is out of scope under the standing ruling).
- Duration: not carried by the landing.
- Anomalies: five guard-log refusals disclosed (the lane session, R1, a commit message with parentheses; round-2 sub-agent R5 and R1; round-3 sub-agent R1 and R4); the lane counts them as its own. One self-detected shell `grep` on the guard log, re-issued through the file-search tool. The base-sha recipe was not followed (no detached `{plan}-base` worktree): failing runs were taken on the branch before the fix, which for D1 is the base commit exactly and for D2 is base plus D1, with D1 not touching the flatten path. Thirty-one routed builds, all `daemon_longpoll`, no fallback; one `quality-gate` returned `error` for a ruff auto-format and was re-run green. One self-review dispatch was a fresh session because a continue was rejected.

## Routing and Merge Behavior

- Review: CodeRabbit (required) reviewed `7819315da` and raised one inline finding (`Minor · Functional Correctness`: the refusal-record sentence overstated), fixed as wording in `4a35735f4`, thread `PRRT_kwDOQ3xasM63qDEr` replied and resolved; its second review was refused ("Already reviewed the last commit"), which `review_complete_after_handling` covers. Sourcery (optional) refused on quota. Three self-review rounds (nine, three, none open). `review-gate --pr-number 1992` re-run on the merged head: `unresolved_review_threads` 0 and `review_body_findings_total` 1, both **agree** with the landing; `review_body_findings_handled` reads 0 from the provider alone, which is the gate working without the lane's dispositions and not a difference — the lane's progress file carries one `finding:` line, which agrees with the landing's 1.
- CI/merge: green on both pushed heads; merge group `success`; squash merge; no rebase conflicts.
- Sonar: `n/a` (not configured); not re-read.
- Parallelization: no in-flight plan, no collision.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-152 --status shipped`
- [x] row `pr` stamped — `1992`
- [x] row `landing` stamped — `landings/PLAN-LB-152.md`
- [x] row `plan_marshall_plan_id` stamped — `rb-lb-152-review-gate-single-read-cleanup` (from the sender)
- [x] `epic.md` narrative: a Decisions entry and one Watch; the Open Defect for the PR #1988 minors is retired by this landing (see Follow-Ups)
- [x] `corpus set-verdict` on claims 5 and 10 of the PLAN-LB-152 spec (`corroborated`, `live-blockers/analyze`)
- [x] resume anchor updated; `queue-view.md` regenerated and committed
- No executor regeneration is owed (no verb or flag added). A harness sync is owed for the four edited bundle sources.

## Follow-Ups

- **Minors L3-1 to L3-6, L2-1, L1-7** — recorded as one Watch; nothing staged. L3-1, L3-4 and the `_match_review` ordering CodeRabbit found
  belong with the CAUTION-shape parser follow-up, which edits the same two files, and L3-3 and L1-7 are one line in `analyze.md`; whether
  a small plan carries any of them is the operator's word.
- **The HIGH CAUTION-shape review-body parser defect** stays open and unstaged, as the spec said; it is now unblocked by sequencing.
- **Authoring lesson for later specs:** a "holds at `{sha}`" clause is verified against that sha before it is written, a Done-when that no
  run can fail is not written, and a fixture a constraint names is looked up first.
