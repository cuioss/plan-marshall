# Landing Analysis: PLAN-LB-132 — refusal escalation, PR-scoped staleness, no credit for an edit, optional bots never ask

epic: live-blockers
workstream: WS-05
pr: #1952 (merge commit `3ed0888ea01abe1aa2d5ea12cd18e0007c259461`, one parent `64907fa3b`)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying claims against ground truth (actual code, artifacts, PR state) — a pasted claim is a lead, never a fact.

## Deliverable Fidelity vs Spec

Corroborated against git: the merge is a merge-queue squash with one parent (`64907fa3b`, the ledger land #1955, read with git before the leaf prompt named it); twenty-two changed paths (read with `git diff --name-only`). The facts block (`pr=#1952`, `merge_state=merged`, `deliverables 4/4`) agrees with git. `landing-check` returns `complete: false` on `total_tokens` alone (out of scope, no defect). `self-review:budget-exhausted` is a lane state: six rounds, every reported finding fixed, no confirming `clear` round.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — a size refusal visible only in `refused_causes` escalates, independent of `review_rate_window_await`, and offers no wait | shipped-as-specified | `_refusal_state` maps `size` to `refused_structural` (`review_completeness.py:728-780`, leaf); `guard_disposition` takes no `review_rate_window_await` argument and `check_completeness` returns it as `guard_action` (leaf); two options, neither waits (`GUARD_STRUCTURAL_OPTIONS`, leaf diff hunk). Tests drive the real functions plus a CLI emitter test (leaf). |
| D2 — stored findings are read for the current PR only | shipped-as-specified | `_scope_findings` (`review_completeness.py:1139-1208`, re-read): same-PR rows join, other-PR rows are dropped, a row with no PR number joins only when the store shows one PR, else it is reported unscoped by hash id. `_read_pr_comment_findings` (`:1211`) and the `cmd_trigger_bot` read (`:2337`) call it. **The spec's premise that `manage-findings` must change is refuted**: the diff touches no `manage-findings` path, and the producer already stamps `pr_number` as the first `detail` line (`github_pr.py:2653-2654`, leaf; stamp introduced in `a063837fb`, leaf pickaxe). The lane records the decision in the PR body (not read). |
| D3 — an edited comment that names no commit credits nothing | shipped-as-specified, broader than the spec wording | `_reviewed_at_merge_candidate` (`github_pr.py:1423-1438`, re-read): with a ledger row the verdict is `recorded_sha == merge_candidate_sha`; the fresh-edit arm and its `require_sha_currency` argument are gone. The coverage-marker, provider-commit-id and body-commit arms (`_evidence_named_verdict`, leaf) still credit a real re-review. The spec asked the arm to require a marker or a commit id; the lane removed the whole edit credit. |
| D4 — an optional bot's decline never escalates | shipped-as-specified, prose only | The filter is SKILL prose at the trigger-B timeout block and the `not_triggered` paragraph; no script changed. Both tests are doc-substring tests (leaf), which is all an LLM-followed document can be tested as. |

**Surface drift, and the lane does not enumerate it.** The re-read path list shows paths outside the spec's Expected Surface: `bot_registry.py`, `coderabbit.md`, `pre_merge_gate.py`, `branch-cleanup.md`, `workflow-integration-github/SKILL.md`, `runbook_lane.py`, four `test_bot_participation_contract_*` files, `test_measured_diff_size_bare_flag_scan.py`, `test_pre_merge_gate.py`, `test_runbook_lane_review_gate.py` and the new `test_optional_bot_decline_no_escalation.py`. And expected paths not changed: `_findings_core.py` and its two test files (explained: the premise was refuted), `test_review_completeness_cli.py` and the `test_re_review_strategy_await.py` pair (not explained; D4 was proved in a new file). The lane explains only `runbook_lane.py` (operator-selected, review-gate returned `undecidable_read`); it has no drift section.

## Three-Layer Analysis

One read-only leaf (`execution-context-level-3`, the resolved default) read the landing at `15aae32c6` with the lane's seven claims passed one by one; the orchestrator re-read the points marked re-read. **By reading, no build, no test run, no write.**

- **Dispatch:** one read-only leaf — reason: reading merged code across ten source files is the depth the dispatch rule exists for.
- **Verdict:** no blocker, no major. Layer 1: 1 minor. Layer 2: 2 minor. Layer 3: 4 minor, 3 watch.

Re-read: `github_pr.py:1405-1438`, `pre_merge_gate.py:1038-1060` and `1222-1244`, `review_completeness.py:1139-1208`, the `manage-findings` verb list, and every consumer of `foreign_stored_findings` (a read-only `grep`, because Grep is unavailable here). **Not re-read** (unverified leads): the test bodies the leaf cites, `automatic-review/SKILL.md` line cites, `_evidence_named_verdict`, `guard_disposition`, `GUARD_STRUCTURAL_OPTIONS`, the build logs, the mutation runs and per-head counts, the six self-review rounds, the reviewers' refusal histories, the operator answers and the PR body.

### Layer 1 — Specified

| Finding | Claim | Verdict | Polarity | Evidence (file:line) |
|---------|-------|---------|----------|----------------------|
| L1-1 | The decline of CodeRabbit's inline-2 ("provide a command to repair unscoped findings") rests on the refusal text naming two actions that clear it: write the stamp into the rows' `detail`, or remove the rows. Neither action has a supported verb: `manage-findings` offers add, list, get, resolve, stamp-fix-commit, promote, ingest, qgate and assessment, none of which edits `detail` or removes a `pr-comment` row. The refusal is `authorizable: False`. So the only clearing path is a hand edit of the git-ignored findings store. | checked (re-read) | refutes | `pre_merge_gate.py:1228-1237`, `manage-findings --help` |

**Layer 1 verdict:** findings — 1 (minor)

### Layer 2 — Implemented

| Deliverable | Code trace | Test that can fail | Unexplained file / unborne claim | Verdict |
|-------------|------------|--------------------|---------------------------------|---------|
| D1 | `review_completeness.py` `guard_disposition`, `check_completeness` | `test_structural_refusal_state.py` (leaf) | none | checked (leaf) |
| D2 | `review_completeness.py:1139-1262, 2337` | `test_trigger_b_stale_set_from_participation.py` (leaf) | `trigger-bot --pr-number` wiring is covered by no new test (`test_review_completeness_cli.py` untouched): a regression that dropped `args.pr_number` at `:2337` would pass | checked, one gap |
| D3 | `github_pr.py:1423-1438` | `test_github_pr_currency.py` (leaf): real `cmd_fetch_findings`, hand-built comment body only | the synthetic `CURRENCY_SUBJECT_BOTS`, because only CodeRabbit declares `participation_requires_update` | checked (leaf) |
| D4 | SKILL prose | doc-substring tests (leaf) | none | checked |

- **L2-1 (minor):** the report's surface-drift disclosure is partial (above). It never says the D3 removal went beyond the spec wording.
- **L2-2 (minor):** the report says Branch 0 (D1c) is "untouched", but the shared `refusal_structural` envelope gained `unproven_bots[N]` and Branch 0's text does not instruct filling it (leaf, not re-read). The count `review_body_findings_total=5` agrees with the `review-gate` re-run; the report's own findings list has six items (five inline and one outside-diff) and its `handled=5` is **not re-verified** (no progress file was passed). Whether that is inline-versus-body counting is not shown by reading.

**Layer 2 verdict:** findings — 2 (minor)

### Layer 3 — Correct

| Defect | File:line | Triggering input | Effect | Severity |
|--------|-----------|------------------|--------|----------|
| L3-1 | `pre_merge_gate.py:1043-1060`; `_scope_findings` `review_completeness.py:1139-1208` | a plan that worked a second PR and holds a pre-stamp (before 2026-05-05) row, resolved or not | `participation_scope_ambiguous` refuses the merge for good, `authorizable: False`, with no supported verb to clear it; the scope function does not filter on resolution, so a resolved legacy row blocks too. Fails closed. The population is the pre-stamp tail of a plan that has since worked another PR | minor |
| L3-2 | `review_completeness.py:1264, 1619` | any run | `foreign_stored_findings` is computed and returned by `check_completeness` and consumed nowhere (a grep over the bundles finds only those two lines), so a pending required finding of an earlier PR of the same plan neither blocks nor is surfaced by this check. A plan-wide pending check elsewhere may cover it (not verified). Low reach: a close-and-reopen happens only when no review existed, so the old PR holds no findings | minor |
| L3-3 | `automatic-review/SKILL.md` (Branch 0 and the `refusal_structural` shape), phase-6-finalize 7a | a structural refusal | the shape lists `unproven_bots[N]` and path 1a says to name every unproven bot in `display_detail`, while the shape's `display_detail` template has no list and Branch 0 does not say to fill the field (leaf, not re-read); whether 7a renders it is not shown | minor |
| L3-4 | `bot-participation-contract.md:416, 597, 604`; `github_pr.py:2160-2162` | — | prose still says the ledger arms decide "unchanged", an edit "proves a fresh review of something", and an unedited comment "fails the test", and a comment still describes the next fetch measuring "a fresh edit against THIS credit" — all contradicted by the removed arm (leaf, not re-read) | minor |

**Watch (not reproduced):**

- **W-1, edit credit and CodeRabbit's in-place summary.** The current finished-review marker `final_review_risk_coverage` names a commit (`coveredCommitId` / `sourceCommitId`, parsed in `_github_pr.py:568-602`, leaf), and the named-commit arm runs before any ledger arm, so the removed arm never mattered for it. Only a body carrying the retired `recent_review_start` wrapper and no commit id loses the edit credit; a re-trigger draws "already reviewed the last commit" and the reply-covered arm lifts the bot. No failing input for the live format.
- **W-2, the review-info span boundary** (`runbook_lane.py:2595-2615`, leaf): a section with no declared count whose rows follow a counted non-finding block would be under-counted; a declared count still wins. CodeRabbit places its review-info blocks after the finding sections. No concrete input found.
- **W-3, `pre_merge_gate.py:986-1076`** (leaf): no fail-open found; the single-PR legacy join can only widen the pending or participated counts, not pass a missing review.

### Conformance to the Project's Own Rules

| Rule source | Rule | Verdict | Evidence |
|-------------|------|---------|----------|
| spec Expected Surface | touched paths within the surface | deviates | fourteen paths outside it, only one explained by the lane (above) |
| spec standing | a fixture answer is one the real verb can give | conforms, one caveat | D2 seeds through the real `add_finding`; the trigger-bot helper re-assembles `cmd_trigger_bot` by hand (leaf) |
| CLAUDE.md § Documentation Standards | current state only | deviates | L3-4 |
| lane rules | files read with the file tools | the lane admits `tail`, `wc -l` and a `grep -n` through Bash (report § 7) | not checkable here |

## Metrics and Anomalies

- Tokens: `unknown`; out of scope. `landing-check` `missing_keys: [total_tokens]` is no defect.
- Anomalies: three guard refusals (R1 twice, R7 once), none worked around; one server restart; eight `verify` runs of which two were red on pre-existing causes. The lane's own review sequence is the evidence behind PLAN-LB-142: CodeRabbit reviewed three heads (three, one and two findings), refused on quota twice after pushes and answered "already reviewed the last commit" once, all after its first review; the standing authorization was available and not needed for the final enqueue.

## Routing and Merge Behavior

- Review: CodeRabbit (required, quota-limited) reviewed `21d85a247`, `6ef306605` and `1a346bb94`; a review ran on the merge head `a66e905e4` with no new findings. Six findings triaged: inline-1, 3, 4 and 5 and the outside-diff finding fixed, inline-2 declined with a reason (L1-1 grades that reason as not sound). Sourcery (optional) refused twice on its diff-size ceiling. Review numbers re-read with `runbook_lane review-gate --pr-number 1952`: `unresolved_review_threads` 0 (agrees) and `review_body_findings_total` 5 (agrees); `review_body_findings_handled` is **not re-verified** (no progress file was passed, so the verb reports 0).
- CI/merge: merge queue, squash with one parent (git); the lane's CI claims were not re-read.
- Sonar: `n/a`.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-132 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-LB-132 --field pr --value 1952`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-LB-132 --field landing --value landings/PLAN-LB-132.md`
- [x] row `plan_marshall_plan_id` stamped — `orchestrator queue --set-row PLAN-LB-132 --field plan_marshall_plan_id --value rb-lb-132-refusal-escalation-and-pr-scoped-staleness`
- [x] epic.md narrative reconciled against the queue rows
- [x] defect/watch opened or retired
- [ ] resume anchor updated in `resume_anchor.md`
- [ ] `queue-view.md` regenerated

(Each box is ticked only after the call it names has returned.)

## Follow-Ups

- No fix plan: no blocker and no major. The minors ride the next plan that touches these surfaces; PLAN-LB-142 reads `review_completeness.py`, `pre_merge_gate.py` and the contract documents and is the next one, so L3-1, L3-3 and L3-4 are carried into its outline as Watch items (the scope-ambiguous refusal sits in the same participation verdict D3 changes).
- **Watch:** L3-1 to L3-4 and W-1 to W-3.
- **Operator-owed, new:** a `manage-findings` verb that stamps a pull request onto a findings row, or removes a row, does not exist; the lane filed it as a follow-up in the findings store (not read).
