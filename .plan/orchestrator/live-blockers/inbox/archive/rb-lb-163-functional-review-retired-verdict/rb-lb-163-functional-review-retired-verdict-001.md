envelope_version=1
sender_type=plan
sender_id=rb-lb-163-functional-review-retired-verdict
epic=live-blockers
kind=landing
created=2026-11-19T05:10:51Z

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-163-functional-review-retired-verdict
epic=live-blockers
pr=#2020
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

# PLAN-LB-163 — a deliverable the operator retired closes through a `retired` functional-review verdict

## 1. Deliverables

- **D1 — the validator accepts `retired`** · met · order `test-first`
  - Accept only with every criterion authorized: `test_a_retired_row_with_every_criterion_authorized_is_accepted`; failing at commit `f80a44e81` (job log `ff3fed046b9c48a696e66b727bc47e6d`, `verdict 'retired' is not one of met, met_with_residuals, not_met, superseded`), and again at commit `243d95af9` in a detached base tree (job log `e54c3f78b2784b9ab99ef6f198af935b`).
  - One unauthorized criterion refused, naming it: `test_a_retired_row_with_one_unauthorized_criterion_is_refused_naming_it` — same two failing runs.
  - No criteria to authorize refused: `test_a_retired_row_with_no_criteria_to_authorize_is_refused` — same two failing runs.
  - No blocking `deliverable_not_met` row: asserted in the accepted case; the `not_met` control is `test_a_not_met_row_still_files_its_blocking_deliverable_row`.
  - Existing refusals unchanged: the pre-existing `test_a_self_citation_leaves_the_criteria_open_and_is_named` plus the new `not_met` control.
  - Commits `a196ff1ff`, `dfd51824e`, `18cfe9e42`.
- **D2 — the criteria side closes with the verdict** · met · order `test-first` for the fail-closed half, `none` for the closing half (see Residue)
  - Gate closes a retired deliverable: `test_a_retired_deliverable_is_closed_by_the_completion_gate` (CONTROL — holds at base too).
  - Order-independent: `test_a_criterion_authorized_after_the_retired_verdict_still_closes_it` (CONTROL).
  - Re-opens no graded criterion: `test_a_valid_retirement_does_not_re_open_the_criteria_its_row_graded` (CONTROL).
  - Invalid retirement closes nothing: `test_a_retired_deliverable_with_one_unauthorized_criterion_stays_open`, `test_an_invalid_retirement_closes_nothing_not_even_a_graded_criterion` — the latter failed at commit `243d95af9` (base tree, job log `e54c3f78b2784b9ab99ef6f198af935b`, `assert 1 == 2`).
  - Persistence and the two-write order recorded by the outline: `review-rubric.md` § 2 `retired` row — the sealed `work/functional-review-verdict.json`, read by the gate through `_checked_verdict`, authorization first and verdict second, both read live.
  - Commits `1ce8b2696`, `dfd51824e`, `18cfe9e42`, `732b068cc`.
- **D3 — the two review documents state the verdict** · met · order `none` (prose; covered by the document-contract tests in the same module run)
  - `review-rubric.md` § 2: the `retired` row, the `superseded` row no longer routing through `criteria-authorize`, and the frozen-spec-clause bullet narrowed to what retirement actually closes.
  - `functional-review.md`: the author rule and the verdict schema prose.
  - Commits `914155328`, `dfd51824e`, `732b068cc`.
- **D4 — tests pin D1–D3** · met · order `test-first`
  - Eight tests extend the two named files in their fixture style; the failing runs are the two job logs above; passing at commit `732b068cc` (job log `19fd6fd6f24841458ae9103593192d7c`, 34141 tests).
  - Commits `f80a44e81`, `243d95af9`, `20d7522a9`, `732b068cc`.

Per-head test runs on pushed heads: `34141 tests` at `732b068cc` (job `19fd6fd6f24841458ae9103593192d7c`); `34141 tests` at `18cfe9e42` (job `1c2e3bb9900243ff8a0e27a7ed26434e`); `34141 tests` at `cf2003834` via CI `verify / verify` SUCCESS; `29098 tests` (plan-marshall scope) at `dfd51824e` (job `bab7dec5debf49e7b8b4646eb9a42a5b`).

## 2. Personas and skills

- D1, D2: `persona-implementer`; skills `plan-marshall:ref-code-quality`, `pm-dev-python:python-core`, `plan-marshall:manage-solution-outline`.
- D3: `persona-documenter`; skills `plan-marshall:ref-code-quality`, `pm-plugin-development:plugin-architecture`.
- D4: `persona-module-tester`; skills `plan-marshall:ref-code-quality`, `pm-dev-python:python-core`, `pm-dev-python:pytest-testing`.
- Self-review rounds and PR-comment triage: `persona-code-reviewer`.
- No skill added for surface drift: no module outside the spec's Expected Surface was touched.

## 3. Hypotheses

- **H1** ("the Claim-Label line numbers are still current") — **confirmed**: `_review_support_validate.py:474-482` (superseded self-refusal) and `:484-486` (not_met blocking row), `_criteria_snapshot.py:2077` (authorized criterion skipped), `review-rubric.md:32,43`, `functional-review.md:279` were all at the stated lines at `571c01087`.
- **H2** ("a retired orchestrator deliverable always carries at least one criterion") — **refuted**: `build_snapshot` copies `deliverable.get('success_criteria', [])` (`_criteria_snapshot.py:1194`), and the criteria parser returns an empty list for an empty `**Success Criteria:**` block, so a zero-criterion deliverable is possible. It **cannot** be retired — deliverable 1 requires the refusal — and it closes only through `not_met` (blocking, forcing work) or `superseded` by a closing successor; there is no non-blocking closure for one, which is the fail-closed direction the standing constraint demands. A `retired` row on such a deliverable is refused with a reason that says there is nothing to authorize.

## 4. Findings

**Self-review round 1** (`persona-code-reviewer`, sub-agent):
- D4's gate-closing clause is not fail-first — assessed, not a defect to fix; see Residue.
- Stale self-citation guidance (`_superseded_rejection_message`) — fixed in `dfd51824e`.
- Stale docstring (`deliverable_reference_rejection`) — fixed in `dfd51824e`.
- Phantom `retired` row field in both schema examples — fixed in `dfd51824e`.
- `triage.md` "five closing states" — out of the plan's write boundary; follow-up (Residue).

**Self-review round 2** — the sub-agent session errored on a provider weekly usage limit before reporting, so the run verified the five dispositions itself: items 2–4 closed, item 5 a recorded follow-up, item 1 the judgement in Residue. No open defect.

**CodeRabbit (required)** — 2 findings on `dfd51824e`, both handled:
- `_criteria_snapshot.py:2144` keep every criterion open on an unauthorized retirement — code kept (an authorization is the operator's own per-criterion decision); the wording it contradicted was corrected in `18cfe9e42`; reasoned reply, thread resolved.
- `_review_support_validate.py:103` derive the verdict counters — fixed in `18cfe9e42` (`FUNCTIONAL_FACT_KEYS` now derives `deliverables_{verdict}` from `FUNCTIONAL_VERDICTS`); thread resolved.
- Re-review of `cf2003834`: "no actionable comments were generated".

**Sourcery (optional)** — 6 findings on `cf2003834`:
- Unbound snapshot can authorize retirement — reasoned reply: the `present` (undigested) class is pre-existing and shared by every snapshot reader in the same validator; narrowing it only for retirement would refuse retirement on the legacy shape while leaving `met` grading open on it. Follow-up.
- One authorization closes duplicate criteria — reasoned reply: `authorized_changes` is text-keyed by design; re-keying is out of the plan's scope by its own standing constraint.
- Retired rows accept criterion grades — fixed as a doc wording change in `732b068cc`; the code deliberately ignores the grades (delta rounds carry them forward) and two tests pin both directions.
- Retired spec clauses stay blocking — fixed as a doc claim narrowing in `732b068cc`: retirement closes the deliverable's own criteria and does not close an uncovered frozen spec clause. Follow-up: an authorization path for spec clauses.
- Landing omits retired counts — reasoned reply: the payload contract is outside the write boundary. Follow-up.
- Retirement gate checks remain untested — fixed in `732b068cc`: the three tests are documented as CONTROLs, and the fail-closed pin carries the fail-first evidence.

All 8 threads replied to (each naming a commit or a stated reason) and resolved.

## 5. Reviewers

| Reviewer | Required | Outcome | Head reviewed | History |
|---|---|---|---|---|
| coderabbit | yes | reviewed | `dfd51824e` (2 findings), `cf2003834` (clean) | triggered `20:01`, refused on quota (`Review limit reached`); re-triggered `21:35` and `23:18` (refused), escalated trigger `00:50` (refused, "next included review in 32 minutes"), re-triggered `02:22` — accepted, reviewed `02:31` |
| sourcery | no | reviewed | `cf2003834` (6 findings) | triggered `20:01`, refused (own budget exhausted, 6h07m), re-triggered after `origin/main` moved — reviewed `03:38` |

Standing authorization: not needed — a qualifying review by the required reviewer is on record for the head that mattered, and every one of its findings is handled; `review-gate` confirmed `required_reviewers: coderabbit` with `merge_allowed: true`.

## 6. Operator questions

None asked. The reviewer quota policy forbids asking about a quota before its steps 1–3 are spent, and the review arrived during step 1.

Free-text operator messages: one — "continue", sent after the round-2 self-review sub-agent errored on a provider usage limit. It was read as permission to continue the run, not as permission to merge or to skip anything.

## 7. Rule check

- Guard: present on this harness. `.plan/temp/guard.log` holds exactly one line for this run's session (`ses_e10a34a5bffejS78Tzx4pE23Xb`): `rule=R2` refusing `rm .../lb-163-functional-review-retired-verdict-base/.plan/local/base-evidence-owner`. The refusal was honoured (no retry, no workaround); the marker stayed inside the gitignored `.plan` boundary, the base tree's `status --porcelain` was clean, and `git worktree remove` then succeeded without force.
- Shell file operations issued by the run: one read-class one beyond the guard's scope — `wc -l .plan/temp/guard.log`. No `cat`/`ls`/`grep`/`find`/`head`/`sed` was issued; every file was read and searched with the file tools.
- Every script ran through `python3 .plan/execute-script.py …`; every build through the resolved `build` commands with the default routing; every CI action through `ci`; no build wrapper, test binary or CI CLI was invoked directly; no `python3 -c`, no `sleep`, no `git grep`.
- One command per shell call throughout; no `&&`, `;`, pipes, loops or heredocs.
- `.plan/` writes: the progress file, the landing payload, the CI body slots returned by `prepare-body`/`prepare-comment`, the base tree's owner marker, and the inbox message. No `.plan/orchestrator/` file was edited.
- Git: nothing staged wholesale; no `stash`, `restore`, `checkout --`, `rebase` or forced push. The base branch was brought in by a merge whose commit carries the trailer.
- Restarts: none. Killed sub-agents: none (the round-2 self-review sub-agent errored on a provider usage limit, not a kill). Re-dispatches: two self-review rounds.
- Spec read: `spec_source: ledger_worktree`, and `resolve` reported no `spec_differ`, so the ledger copy and the main-checkout copy agreed.
- Executor skew: `not_applicable` — the lane text lives in a source checkout whose executor maps that checkout's own scripts. Answered, recorded, not asked about.

## 8. Build server

- Setup preflight at the worktree: `ready` (registered, verified handshake).
- Mechanisms: every build resolved `routed` / `daemon_longpoll`; **0** in-process fallbacks, **0** degraded results, **0** launch-fault retries, **0** killed jobs.
- One daemon-bound expiry: the routed `verify` at `dfd51824e` returned `timeout` with `timeout_used_seconds: 1297` and `timeout_source: explicit` (job `27b42c6633a94359bf2e210a60d465be`). Per the split form its parts ran instead: `quality-gate` (job `f564902ac21743b3af4f4d8fd8ec4260`) and `module-tests` (job `1c2e3bb9900243ff8a0e27a7ed26434e`), both green.
- Red builds, for the record: two were the intended test-first evidence runs (`ff3fed046b9c48a696e66b727bc47e6d`, `a4648143083b45f08454863c95a11d29`), two were the intended base-tree runs (`60c1f1db58fb4f8db1b36ea777d27d4a`, `e54c3f78b2784b9ab99ef6f198af935b`), one was the round-2 base control that passed, one was a `quality-gate` that auto-fixed ruff formatting (then green), and one was an invalid multi-word `--filter` that argparse rejected (exit 2, corrected by using a single token).
- No `runtime_stamp_reason` was reported; the stamp is complete.

## 9. Residue

- **The D4 gate-closing clause carries `order: none`.** The completion gate already closes a fully authorized deliverable through its per-criterion authorization skip, so no test can distinguish "the retirement branch closes it" from "each criterion was authorized" — and the base-tree run at `243d95af9` (job log `38b4ab11596a4411a4d6b9abb0473ef7`) shows the three closing tests passing there. They are kept as CONTROLs, documented as such in the file. The retirement branch's own observable effect is the fail-closed direction, and that is pinned fail-first. Self-review round 1 graded the clause "not met"; the run graded the deliverable met, on the reading that the clause demands a test that pins the behaviour and the behaviour is pinned, with the failing-evidence requirement satisfied by the fail-closed test. Either reading is defensible; a reviewer who prefers round 1's should count `deliverables_done` as 3.
- `plan-marshall/workflow/triage.md` still says "five closing states"; a retired deliverable's criteria close through the authorization state it already names, so nothing there is wrong, but the count is now six. Out of this plan's write boundary.
- `phase-6-finalize/standards/emit-landing.md` and `plan-orchestrator/standards/landing-payload-spec.md` transcribe four functional-verdict facts; `deliverables_superseded` and `deliverables_retired` are both omitted. Out of the boundary.
- `snapshot_state`'s `present` class (a snapshot file with no recorded freeze) is trusted by every snapshot reader; hardening it is a shared change to grading for all verdicts, not a retirement-only one.
- `_spec_clause_drift` has no operator-authorization path; a frozen spec clause no outline criterion covers stays blocking even when its deliverable is retired. The rubric now says so instead of implying otherwise.
- The self-review round-2 sub-agent could not run (provider usage limit); round 2 was self-performed, as recorded in § 4.
- The plan's mailbox reported `mailbox_state: no_mailbox`, `delivery_state: never_delivered` on all three reads — it was never deliverable, which is not the same as an empty mailbox, and is recorded here rather than read as "no mail".
- The base worktree used for the evidence was removed; `cleanup_owed=false`.
