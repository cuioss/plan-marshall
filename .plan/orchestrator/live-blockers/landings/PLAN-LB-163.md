# Landing Analysis: PLAN-LB-163 — A deliverable the operator retired with no successor closes through a `retired` functional-review verdict

epic: live-blockers
workstream: WS-01
pr: #2020 (https://github.com/cuioss/plan-marshall/pull/2020)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying claims against ground truth — a landing message is a lead, never a fact. Source message: `rb-lb-163-functional-review-retired-verdict-001.md` (`kind: landing`, drained from the inbox).

## Deliverable Fidelity vs Spec

PR #2020 `merged` through the CI abstraction; merge commit `46d3308ea81814f40641d5d1c894cf96aafc7034` (squash, first parent `60e6a5c46`), on `origin/main`, read with git. The diff is seven files, 413 insertions and 31 deletions.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — the validator accepts `retired` only when every criterion is authorized; refusals name them; no `deliverable_not_met` row | shipped-as-specified | re-read: `_review_support_validate.py` adds `RETIRED` to `FUNCTIONAL_VERDICTS` and a `verdict == RETIRED` branch (hunk at 483-506) that calls `retirement_state(read_snapshot(plan_id), number)`, refuses `unauthorized` naming each text, refuses every other non-`closed` state with the nothing-to-authorize message, and `return`s before `_grade_criteria` and before the `not_met` row. The two existing refusals are unchanged; only the self-citation message text changed. |
| D2 — the criteria side closes with the verdict | shipped-as-specified | re-read: `retirement_state` (`_criteria_snapshot.py`, new, after `_authorization`) is the one predicate; `open_criteria` skips a deliverable whose verdict is `retired` and whose state is `closed`, and otherwise reads every unauthorized criterion of a retired row as `ungraded`, so an invalid retirement closes nothing even where a criterion was graded `met`. Persistence is the sealed verdict file the gate already reads (the rubric records it). |
| D3 — the two review documents state the verdict | shipped-as-specified | `review-rubric.md` (+5) and `functional-review.md` (+11) in the diff stat; their wording is the leaf's reading. No test pins either document's text (leaf reading). |
| D4 — tests pin D1 to D3 | shipped-as-specified | `test_criteria_gate_completion_d1.py` (+139) and `test_superseded_by_names_deliverable_d3.py` (+135) in the diff stat. Which tests fail on the unfixed tree is the lane's and the leaf's reading; the landing itself says three of the gate tests are CONTROLs that pass at base. |

**Surface delta** (declared 6, realized 7): all six declared files are touched. Realized and undeclared: `phase-6-finalize/scripts/review_support.py` (+8 −2, the leaf reads it as a docstring-only change; inside the declared module, and the landing names it). The spec is shipped, so no correction is owed to it; no other staged spec declares a path in `phase-6-finalize` or `manage-solution-outline`.

## Three-Layer Analysis

The landing was read on three layers by one read-only leaf (`execution-context-level-5`, resolved from `orchestrator.analyze`). The orchestrator re-read the points marked "re-read" at their lines; every other point is the leaf's reading and is an unverified lead. The reading is by reading, no build, no test run, no write.

- **Dispatch:** one read-only leaf per landing — reason: reading merged code is the depth the dispatch rule exists for, and this landing's read must not share context with the other two landings of the drain.
- **Verdict:** layer 1 findings (one minor); layer 2 findings (minor); **layer 3 findings — one major**; not shown by reading on layers 1 and 2.

### Layer 1 — Specified

| Finding | Claim | Verdict | Polarity | Evidence (file:line) |
|---------|-------|---------|----------|----------------------|
| L1-1 | D1 defines the precondition as "every criterion authorized". It does not ask for a recorded operator decision to retire, distinct from authorizing a criterion change, so it admits L3-1 by construction | checked (the authorization record shape re-read at `authorize_change`) | refutes (the spec's own Standing Constraint "operator route, not a model shortcut" is not carried by its own precondition) | `_criteria_snapshot.py:1429-1468` of the merge, `authorize_change` (not touched by this landing) |
| L1-2 | The spec premises hold at the base: no `retired` value, a self-citing `superseded` refused, `not_met` filing a blocking row, `criteria-authorize` closing gate criteria | checked (leaf reading) | confirms | `_review_support_validate.py:53` |
| L1-3 | HYPOTHESIS "a retired deliverable always carries at least one criterion" | not_shown_by_reading | none | the landing refutes it from `build_snapshot`; the outline was not read |

**Layer 1 verdict:** findings — 1 (L1-1, minor); not shown by reading — 1

### Layer 2 — Implemented

| Deliverable | Code trace | Test that can fail | Unexplained file / unborne claim | Verdict |
|-------------|------------|--------------------|---------------------------------|---------|
| D1 | `_review_support_validate.py:489-503` (re-read) | the accepted, one-unauthorized and no-criteria tests fail at base (`verdict 'retired' is not one of …`); the `not_met` test is a control (leaf reading) | none | checked |
| D2 | `_criteria_snapshot.py` `retirement_state` and the `open_criteria` hunk (re-read) | only the fail-closed test ("closes nothing, not even a graded criterion") is fail-first; the three closing tests are declared CONTROLs. The retired-closed branch does nothing the per-criterion authorization skip does not already do (leaf reading), so the landing's `order: none` for that half is borne out | none | checked |
| D3 | the two documents | no test asserts the documents name `retired`; the landing's "covered by document-contract tests" does not hold (leaf reading: `test_functional_review_contract.py` pins facts and schema keys only) | the merge commit body says the spec-clause bullet makes the clause "close only through the authorizations a retirement requires"; the leaf reads the bullet and `_spec_clause_drift` as saying the opposite (leaf reading, not re-read) | checked (minor) |
| D4 | the two test files | — | — | checked |
| the narrative's "present" residue | the landing says the unbound-snapshot trust is pre-existing | — | the leaf reads it as half true: the gate already trusted a `present` snapshot, but the validator's `retired` branch newly does (`run_validate` refuses only deleted and tampered). Not re-read | not_shown_by_reading |

**Layer 2 verdict:** findings — 2 (minor); not shown by reading — 1

### Layer 3 — Correct

| Defect | File:line | Triggering input | Effect | Severity |
|--------|-----------|------------------|--------|----------|
| L3-1 | `_review_support_validate.py:489-503`; `_criteria_snapshot.py` `retirement_state` → `_authorization` (re-read); `authorize_change` / `_commit_authorization` (re-read, untouched by this landing) | D1 froze criteria `a` and `b`; the operator authorizes the rewrites `a→a'` and `b→b'` through `criteria-authorize`; the reviewer writes `{number: 1, verdict: retired}` | the authorization entry is keyed on `(deliverable, frozen criterion text)` and carries only a free-text `decision`, so a retirement and a rewrite approval are indistinguishable; the retired branch returns before `_grade_criteria`, so the current criteria `a'` and `b'` are never graded, no `deliverable_not_met` row is filed and the gate closes the deliverable. Before this change `met` and `not_met` forced grading of the current criteria. This breaks the spec's own Standing Constraint that the verdict is an operator route and not a model shortcut | **major** |
| L3-2 | `_criteria_snapshot.py:1586-1588`, `:1638` (leaf reading) | a spec Done-when covered only by the retired deliverable's own outline criterion, with that text left in the outline | coverage is loose text containment, so retiring the deliverable silently retires the spec clause; deleting the text instead raises a blocking `spec_criterion_missing`. The rubric's "does not close such a clause" holds only for deletion | minor |
| L3-3 | `_review_support_validate.py:497-502` (re-read) | a legacy plan with no freeze, or a deliverable added after the freeze | `no_snapshot` and `no_deliverable` reuse the `no_criteria` refusal text, so the message names the wrong cause; no reason code is surfaced although verify-first (b) asked for one | minor |
| L3-4 | `_criteria_snapshot.py:1460`; `:2144` (leaf reading) | a legacy dict-shaped frozen criterion | `retirement_state` normalizes raw entries while `open_criteria` unwraps `{'text': …}` first, so the validator refuses and the gate closes; fails closed | minor |
| L3-5 | `_review_support_validate.py:490` (leaf reading) | a snapshot rewrite between `run_validate`'s state check and the retired branch's second read | not re-checked; narrow window, the gate re-derives the state | info |

**Layer 3 not shown by reading:** L3-6: the end-to-end behaviour of the completion gate's delegation to `open_criteria`, the cited job logs and the "4 of 4 met" figure, and the claims about `triage.md` ("five closing states") and the two landing-payload documents, none of which the leaf read in full.

**Layer 3 verdict:** findings — 5 (1 major, 3 minor, 1 info); not shown by reading — 1

### Conformance to the Project's Own Rules

| Rule source | Rule | Verdict | Evidence |
|-------------|------|---------|----------|
| ref-code-quality | one predicate shared by the validator and the gate | conforms | `retirement_state` is called at `_review_support_validate.py:490` and in `open_criteria` (re-read) |
| ref-code-quality | fail-closed error handling | conforms | every state but `closed` refuses or closes nothing (re-read), apart from L3-1 where the predicate itself is too weak |
| python-core | readable naming, no shadowing | deviates | the generator variable `row` shadows the name being bound inside `retirement_state` (re-read; a nit) |
| CLAUDE.md § Documentation Standards | no duplication | deviates | the retired precondition is restated in the rubric, both workflow lines, the `review_support.py` docstring and two module docstrings (leaf reading) |
| CLAUDE.md § Commit Trailer | exactly the `plan-marshall` trailer | deviates (minor) | the squash also carries a human `Co-authored-by` line and an embedded CodeRabbit summary block; both come from GitHub's squash and the PR body, not from the lane (leaf reading) |
| spec Standing Constraints | `criteria-authorize` not widened; no file outside the two skills and their tests | conforms | `authorize_change` is absent from the diff (re-read); the diff stat lists seven files inside `phase-6-finalize`, `manage-solution-outline` and their tests |

## Metrics and Anomalies

- Tokens: `unknown`; out of scope under the ruling of 2026-10-23, so no defect.
- Duration: not stated.
- Anomalies: the second self-review round's sub-agent session errored on a provider usage limit, and the run performed that round itself (the landing says so). One guard refusal (R2, an `rm` of the evidence owner marker), honoured; `.plan/temp/guard.log` was not re-read here. One routed `verify` hit the daemon bound and the split form ran instead.
- Model: `deepseek-v4.1-flash/high`.

## Routing and Merge Behavior

- Review: the landing claims 0 unresolved threads, 2 body findings, 2 handled. `runbook_lane review-gate --pr-number 2020` returns `unresolved_review_threads: 0` and `review_body_findings_total: 2`, both agreeing. `review_body_findings_handled: 2` is **not re-verified**: the progress file carries prose review lines and a lane gate line (`all_handled … 2/2`) but no `finding:` lines. Sourcery's six findings ride a separate surface (optional reviewer, six replied threads per the landing) and are not in the gate's count.
- CI/merge: merged (`46d3308ea`). per the landing (not checked here), CodeRabbit was refused on quota four times, about six and a half hours, before it reviewed two heads (two findings, then clean).
- Sonar: `sonar_open_new_issues: n/a`; Sonar is not enabled for this project.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-163 --status shipped`
- [x] row `pr` stamped — `2020`
- [x] row `landing` stamped — `landings/PLAN-LB-163.md`
- [x] row `plan_marshall_plan_id` stamped — `rb-lb-163-functional-review-retired-verdict` (from the sender)
- [x] epic.md narrative reconciled: decision 2 closed by this landing; the major L3-1 opened as an Open Defect and reported to the operator
- [x] resume anchor updated in `resume_anchor.md`
- [x] `queue-view.md` regenerated

## Follow-Ups

- **L3-1 (major, REPORTED TO THE OPERATOR, NOT STAGED).** A `retired` verdict is accepted on any `criteria-authorize` entry, including one recorded to approve a rewrite. Staging a fix plan needs the operator's word. A fix would give a retirement its own recorded decision, or require the authorized criterion to be unchanged in the current outline, inside `manage-solution-outline` and `phase-6-finalize`.
- **L1-1, L3-2 to L3-5.** Minor and info; recorded here and not staged.
- **Narrative follow-ups the landing lists** (`triage.md` count, `deliverables_retired` and `deliverables_superseded` missing from the landing-payload documents, `_spec_clause_drift` having no authorization path): recorded here, not staged, outside the focus rule.
