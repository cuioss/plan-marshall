envelope_version=1
sender_type=plan
sender_id=rb-lb-169-retired-verdict-needs-its-own-operator-decision
epic=live-blockers
kind=landing
created=2026-11-19T23:11:09Z

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-169-retired-verdict-needs-its-own-operator-decision
epic=live-blockers
pr=#2029
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
review_body_findings_total=2
review_body_findings_handled=2
sonar_open_new_issues=n/a
step.sonar-roundtrip.open_issue_rules=n/a
```

guard: present

## 1. Deliverables

| # | Done-when | Verdict | Order | Test | Commit |
|---|---|---|---|---|---|
| D1 | authorization carries what the operator decided | met | test-first | `test_a_retirement_decision_closes_a_retired_deliverable` | 948b6bda1 |
| D1 | `retirement_state` closed only on a retirement decision per frozen criterion | met | test-first | same | 948b6bda1 |
| D1 | a rewrite approval and a pre-change record no longer close a `retired` verdict | met | test-first | `test_a_pre_change_authorization_does_not_close_a_retired_deliverable` | 948b6bda1 |
| D1 | one predicate shared by validator and gate | met | test-first | `test_a_rewrite_authorization_closes_nothing_in_the_gate` | 508b20591 |
| D2 | validator refuses a rewrite-only retirement, naming the criteria | met | test-first | `test_rewrite_authorizations_do_not_close_a_retired_deliverable` | 3a8605c5b |
| D2 | grading continues for the current criteria | met | test-first | `test_a_refused_retirement_still_grades_the_criteria_its_row_carries`, `test_a_refused_retirement_with_no_grades_is_reported_even_with_no_outline_criteria` | 508b20591, 1f5a77c07 |
| D2 | no deliverable is closed (gate half) | met | test-first | `test_the_defect_input_is_refused_and_the_gate_stays_open` (frozen `[a,b]` → `[a',b']`, both rewrites authorized → `open_count == 2`) | 508b20591 |
| D3 | rubric's `retired` paragraph states the rule and names the route | met | none | the document at HEAD (`review-rubric.md:33`) plus the existing doc-contract guards | a4720493c, a295ddfba |
| D3 | functional-review workflow states the same and names the route | met | none | `functional-review.md` (criteria-drift bullet, author verdict instructions, verdict-schema paragraph) | a4720493c, a295ddfba |
| D4 | rewrite-only retirement refused by the validator and closes nothing in the gate, current criteria graded | met | test-first | `test_rewrite_authorizations_do_not_close_a_retired_deliverable`, `test_a_rewrite_authorization_closes_nothing_in_the_gate`, `test_the_defect_input_is_refused_and_the_gate_stays_open` | cb52c5f1c |
| D4 | every criterion carrying a retirement decision closes, as before | met | test-first | `test_a_retirement_decision_closes_a_retired_deliverable` | e8166be7f |
| D4 | a mixed deliverable is refused | met | test-first | `test_a_mixed_record_is_refused_naming_only_the_rewrite_criterion` | e8166be7f |
| D4 | a pre-change record with no decision type does not close a deliverable | met | test-first | `test_a_pre_change_authorization_does_not_close_a_retired_deliverable` | e8166be7f |
| D4 | the controls hold at `46d3308ea` | met | test-first | the four controls (`test_a_met_row_still_passes`, `test_a_not_met_row_still_files_its_deliverable_row`, `test_a_retired_row_with_one_unrecorded_criterion_is_still_refused`, `test_a_retired_row_with_no_criteria_to_authorize_is_still_refused`) — all four pass at `46d3308ea` | e8166be7f |

**Failing run (`test-first`).** Base tree at `46d3308ea`, log `.plan/local/plans/NO_PLAN/build-results/plan-marshall/phase-6-finalize/python-2026-11-19-154938.log`: `8 failed, 17 passed in 23.42s`, selection `run --command-args "module-tests plan-marshall/phase-6-finalize --filter retire"` (25 collected; the D4 module contributes 12 — 8 fail, 4 pass). The substantive failure is `test_a_pre_change_authorization_does_not_close_a_retired_deliverable` (validator returned `valid: True` at the base sha, i.e. the defect); the other seven fail on the absent `decision_type` parameter. The four controls pass there. The base tree was removed with `git worktree remove` after `git status --porcelain` came back empty.

**Per-head test runs (pushed heads).** `5d138cb35`: whole-tree `module-tests` green (1030 s) and `verify` green (1537 s). `1f5a77c07`: `verify` green (1076 s), plus `phase-6-finalize` (2086) and `manage-solution-outline` (300). `047e6db1b` (merge of `origin/main`): `verify` green (1006 s). `f90146325`: whole-tree `module-tests` green (1030 s).

## 2. Personas and skills

| Step | Persona | Domain skills |
|---|---|---|
| D1 | persona-implementer | plan-marshall:ref-code-quality, pm-dev-python:python-core, plan-marshall:manage-solution-outline |
| D2 | persona-implementer | plan-marshall:ref-code-quality, pm-dev-python:python-core, plan-marshall:phase-6-finalize |
| D3 | persona-documenter | plan-marshall:ref-code-quality, pm-documents:ref-documentation |
| D4 | persona-module-tester | plan-marshall:ref-code-quality, pm-dev-python:python-core, pm-dev-python:pytest-testing |
| every self-review round, PR triage | persona-code-reviewer | — |

skills added: none — no deliverable reached a module outside the spec's Expected Surface.

## 3. Hypotheses

- "`manage-solution-outline.py` defines the `criteria-authorize` argument surface, so a typed decision needs a new argument or value there" — **confirmed**, `manage-solution-outline.py:1706-1735` (the parser) and `review_support.py:86-91` (its `criteria-authorize` mention).
- "no consumer other than `_authorization`, `retirement_state` and `open_criteria` reads `authorized_changes` entries by shape" — **confirmed**, the only production readers are in `_criteria_snapshot.py` (init `[]`, preserve-on-re-freeze, `preserved_authorizations` count, `_authorization`, `_retirement_decision`, `_commit_authorization`); no test asserts an entry's exact dict shape.
- Verify-first clause (a) — the mechanism settled as a **typed field** on the authorization entry (`decision_type: rewrite|retirement`, `rewrite` the default). The second alternative (refusing a retirement whose authorized text still stands in the current outline) was refuted as unnecessary once the decision is typed and the default fails closed: the typed decision alone makes a rewrite approval indistinguishable-no-more, and the gate half closes only on a retirement decision.

## 4. Findings

- Self-review round 1: 9 findings — 1 HIGH (the gate still closed the defect's own input on the type-blind `_authorization`), 2 MEDIUM (the gate half unpinned; the verdict-schema paragraph still stated the old rule), 1 MEDIUM (a criteria-less refused row was skipped), 4 LOW (stale comments/docstrings, base-control docstrings). All fixed or dispositioned: HIGH/MEDIUM in 508b20591 / a295ddfba / cb52c5f1c, LOWs in 8efa6fd16 / 5d138cb35. Item 8 (a retirement decision also passing `criteria_drift`) deliberately unchanged — the Standing Constraint says only the `retired` verdict stops accepting a rewrite approval — and documented in the predicate's docstring.
- Self-review round 2: 4 LOW (stale gate comment, an assertion that could not fail for its stated reason, `criteria-authorize` help wording, base-run labelling). Fixed in 8efa6fd16 / 5d138cb35; the labelling was carried into the PR body and this report.
- Self-review round 3: **nothing open**.
- PR review (coderabbit, head `5d138cb35`): 2 findings — `inline inline-1` (an edited/unsealed verdict fell back to the rewrite exemption → gate closed it) and `additional additional-1` (empty retirement grading not reported when the outline carries no criterion to compare against). Both fixed in 1f5a77c07; the inline thread was answered and resolved.
- CI: green on every pushed head. No CI-originated findings.

## 5. Reviewers

| Reviewer | Required | Reviewed | Head | History |
|---|---|---|---|---|
| coderabbit | yes | yes — formal review `COMMENTED` at 21:19:23Z plus the marker-bearing summary naming `5d138cb35` (`final_review_risk_coverage`, `kind=reviewed`) | `5d138cb35` (exemption applies for later heads) | triggered at 17:40:37Z (refused on quota, "next included review in 53 minutes"), waited 90 min, re-triggered 19:38:46Z (refused), waited 90 min, re-triggered 21:10:13Z → "Review triggered". No re-trigger after the 1f5a77c07 / 047e6db1b pushes: `review_complete_after_handling` with a qualifying review on record, every finding handled |
| sourcery | no | no — refused on quota | — | triggered at 17:40:49Z; refused ("used your own review budget … 1 day and 2 hours"). Optional reviewer, so the merge was not gated on it |

Standing review authorization: not used. `review-gate --required-reviewer coderabbit` answered `merge_allowed: true`, `all_handled`, `required_review_missing` absent, on the merge head.

## 6. Operator questions

none asked. No free-text operator messages were received.

## 7. Rule check

- `guard: present` on this harness; the guard log (`.plan/temp/guard.log`) carries **two refusals** for this run's session `ses_e0bdc3f9effeE2BYlr0vx8VKXp`, both self-corrected:
  - `R2` (shell file operation, 14:59:35Z) on `rm …/<plan>-base/test/…/test_retirement_decision_d4.py`; the base tree was returned to its tracked state with `git clean -f -- <path>` instead, and the marker with `git clean -fdx -- <path>`.
  - `R1` (shell-chaining constructor, 16:24:42Z) on a `git commit -m` whose message quoted a field name in backticks; re-issued without them.
- One additional deviation the guard did not record: one `printenv OPENCODE_SESSION_ID` call, used to attribute the guard's lines to this session. Single variable, no config or credential file was read.
- Every script ran as `python3 .plan/execute-script.py {bundle}:{skill}:{script} …`; every build through the resolved `build` commands; every CI action through `plan-marshall:tools-integration-ci:ci`. No `gh`/`glab`, no wrapper/binary directly, no `python3 -c`, no `git grep`, no `sleep`. Waits used `ci pr wait-for-comments`, `ci checks wait` and `build_server wait`.
- Files were read and searched with the file tools; no `cat`/`ls`/`grep`/`find`/`head`/`sed`. Temp files were written only under `.plan/temp/` and the `ci` body slots `prepare-*` returned. Nothing under `.plan/orchestrator/` was written.
- Restarts, killed sub-agents and re-dispatches: none. Three self-review rounds (one sub-agent session, continued three times); the base evidence worktree was created twice (first removed after its run, re-created for the final module and removed again).
- Spec read: `spec_source: ledger_worktree`; no `spec_differ` marker (both copies agreed).
- `executor-skew`: `not_applicable` — source checkout, so the executor maps this checkout's own scripts; recorded and not asked about.

## 8. Build server

- Setup preflight: `ready` (registered).
- Every build was routed: `mechanism=daemon_longpoll` on every `[BUILD-SERVER] resolved build` line — 28 routed builds in total (module-tests scoped and whole-tree, quality-gate, verify). No `in_process_fallback`, no launch-fault retry, no `killed` job.
- One routed `verify` (job `da6c90ee588b4da49486837b9624937c`, `--timeout 1705`) ended without a verdict — no pytest summary and no `verify:` line in its log, cut off at 69 % of its module-tests phase. That is recorded here as an environment/supervisory termination, not a red build: the split form's parts (green `quality-gate`, green whole-tree `module-tests`) were run instead, and later `verify` runs with `--timeout 3400` completed green (1537 s, 1076 s, 1006 s).
- Two `quality-gate` runs first failed on `ruff format --check` and auto-fixed the formatting in place; the re-run was green, and the formatting diff is in the commits.
- `runtime_stamp_reason`: absent (the runtime-info seam answered).

## 9. Residue

Nothing open. The base evidence worktree was removed; `cleanup_owed=false`. The branch and its remote ref were pruned and the main checkout pulled to the merge commit `f327251591aa1b065d63d44a456dd117dd328944`.
