# PLAN-LB-02: Pre-submission self-review can be closed, cannot starve PR review, and stops re-running settled steps

epic: live-blockers
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-LB-02-self-review-convergence.md` and is queued as one row file, `queue/PLAN-LB-02.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

`default:pre-submission-self-review` has two exits: a clean round the verifier agrees to close, or the
finalize loop-back ceiling. Recent plans ran 4 to 14 rounds and were ended by the operator with moves no
document sanctions — `mark-step-done --force` from `loop_back` to `done`, a hand-resolved finding, and a
hand-edited `loop_back_iteration`. One persisted counter caps every loop-back source, so a self-review that
spends it leaves the first real PR-review fix with no round. The findings the step files for a refused
verdict carry no file path, so nothing can resolve them and they block the pre-merge findings gate. And each
round re-fires `finalize-step-simplify` and `finalize-step-lessons-housekeeping` in full because neither
declares which files its verdict depends on; one run measured six firings of each with zero edits every
time. Give the operator a recorded way to grant rounds or close on named residual findings, budget
loop-backs per source, make the step's own state findings resolvable, and declare `verdict_inputs` on the
two steps so a small fix commit does not re-run them. Carries forward process-compliance PLAN-20
deliverables D2–D4 and post-run-quality PLAN-PRQ-10 deliverable D1 (the `verdict_inputs` route only).

## Deliverables

1. **A logged verb grants further rounds.** A plan-scoped `manage-status` verb grants N additional
   loop-back rounds to a named source, records who granted it and why (reason required), and is the only
   sanctioned way past a ceiling refusal. The ceiling's STOP display in `phase-6-finalize/SKILL.md` Step 3
   item 7b names that verb instead of telling the operator to "re-run finalize", which the persisted counter
   defeats. Setting `loop_back_iteration` through `manage-status metadata --set` stops being the way to do
   it.
   Done when: a test drives the counter to the ceiling, shows the admission gate refusing, runs the grant
   verb with a reason, and shows the next loop-back admitted and the grant present in the plan's status
   record; a grant without a reason is refused.
2. **A recorded operator close on named residual findings.** One sanctioned disposition closes
   `pre-submission-self-review` without a further round: it names the residual findings it accepts (by
   `hash_id`), resolves exactly those as `accepted` with the operator's rationale, and records the step
   `done` with facts that say the close was an operator override and not a verifier `may_close: yes`
   (for example `may_close=operator_override`, plus the accepted count). Head-dependent settle steps the
   operator chooses not to re-fire after the last fix commit are recorded on their own step records as
   skipped with that basis, not as a free-text WARNING. `pre-submission-self-review.md` § "Round-loop
   termination" names this as the *out of budget* close's mechanism.
   Done when: a test closes a step holding a live `loop_back` record through the disposition and reads back
   `outcome: done`, the override fact, and the named findings as `accepted`; an unnamed pending finding
   stays `pending`; the documented flow contains no bare `mark-step-done --force` for this case. A later
   audit can tell the override close from a verifier close by reading the step record alone.
3. **Loop-back budgets are per source.** The single `status.metadata.loop_back_iteration` counter becomes
   one count per requesting step (the `step_ref` that recorded `loop_back`), each compared against
   `phase-6-finalize.max_iterations`. A self-review that has spent its budget no longer causes the
   admission gate to refuse a loop-back requested by `automatic-review`, `sonar-roundtrip` or any other
   step. How a plan already in finalize, whose status still carries the old scalar, is read is decided at
   outline and stated in the SKILL; the scalar is not silently attributed to one source.
   Done when: a test spends `max_iterations` rounds under `default:pre-submission-self-review`, then shows a
   loop-back from a different step admitted at iteration 1 of its own budget, while a further self-review
   loop-back is still refused; `execution.md` and `execution-recovery.md` no longer say the cap is one count
   across both tiers.
4. **The step's own state findings can resolve.** The findings Step 3b files for a non-closing verifier
   state (`verdict_refused`, `further_round_owed`, `verifier_unavailable`) get a resolution path: they are
   filed with a stable key that identifies them as this step's state findings, and the round that closes
   the step — a Branch A close or the Deliverable 2 operator close — resolves every pending one, citing the
   closing HEAD. Where a refusal rationale names a specific file the finding also carries `--file-path`, so
   `qgate resolve-evidenced` can resolve it when a fix touches that file.
   Done when: a test files one of each state finding, closes the step, and `qgate list --phase 6-finalize
   --resolution pending` returns none of them; a state finding filed in a round that did not close stays
   `pending`.
5. **`finalize-step-simplify` and `finalize-step-lessons-housekeeping` declare `verdict_inputs`.** Each
   step's frontmatter declares the fnmatch globs naming the tracked paths its verdict reads, so the existing
   verdict-currency classifier returns `preserved` and the dispatcher skips the step when a loop-back fix
   commit touches none of them. The admissibility bar is the one `ext-point-finalize-step.md` already
   states: the globs must be a superset of everything the verdict reads. If the outline finds that no
   admissible superset narrower than "every file" exists for one of the two steps, that step instead gets
   the recorded refusal-on-evidence paragraph `finalize-step-plugin-doctor` already carries, and the plan
   says so in its PR.
   Done when: for each step that gains a declaration, a test runs `verdict_currency classify` over a
   two-commit fixture whose second commit touches only a path outside the declared globs and gets
   `preserved` / `disjoint_from_verdict_inputs`, and over one whose second commit touches a declared path
   and gets `invalidated` / `verdict_inputs_matched`. A skipped firing is recorded as skipped with its
   basis, never as a firing that ran and found nothing.

## Claim Labels

- OBSERVED: one persisted counter caps every loop-back source — `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md:1475-1502` (item 7b (i): reads `status.metadata.loop_back_iteration`, refuses when `{loop_back_iteration} + 1 > max_iterations`, otherwise persists the increment); no `step_ref` participates in the comparison.
- OBSERVED: the ceiling's STOP display ends "Then re-run finalize when you are ready to give it another round" and names no way to obtain a round — `phase-6-finalize/SKILL.md:1490`; the same section states the count is persisted so a re-run "resumes against it instead of resetting" (`:1631`, `:1635`).
- OBSERVED: `max_iterations` defaults to 3 and both tiers share it — `phase-6-finalize/SKILL.md:109`; `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/execution.md:652` ("counted across both tiers"); `marketplace/bundles/plan-marshall/skills/plan-marshall/standards/execution-recovery.md:77`.
- OBSERVED: `manage-status` has no grant-rounds or waiver verb — the `add_parser(...)` roster in `marketplace/bundles/plan-marshall/skills/manage-status/scripts/manage-status.py` (:117-875) holds `metadata`, `mark-step-done`, `assert-step-recorded`, `merge-authorization grant|check` and no loop-back verb.
- OBSERVED: the self-review has no close other than Branch A (verifier `may_close: yes`) and the ceiling — `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md` § "Step 4" (Branch A preconditions :528-553; Branch B always records `loop_back` :604-647) and § "Round-loop termination" (:694 "no new outcome", :700 *out of budget* closes "on a recorded WARNING DEVIATION").
- OBSERVED: Step 3b files its state findings without a file path — `pre-submission-self-review.md:513-518` (`qgate add ... --title "{state} at pre-submission-self-review" --detail "{rationale}" --component ... --severity warning`, no `--file-path`), while the per-finding call in Branch B does pass `--file-path` (:613-618).
- OBSERVED: a finding with no `file_path` is never resolved by evidence — `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py:1254-1259` (docstring: a finding "that carries no `file_path` at all — is LEFT `pending`") and the test at `:1291` (`if file_path and file_path in changed`).
- OBSERVED: `qgate add` accepts `--rule`, which is folded into the dedup discriminator — `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/manage-findings.py:463`; a candidate carrier for the stable key in Deliverable 4.
- OBSERVED: a head-dependent step that declares no `verdict_inputs` re-fires on every real HEAD advance — `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/verdict_currency.py:139` (`REASON_UNDECLARED`), `:200` (`if not verdict_inputs:` returns invalidated); the dispatcher consults it at `phase-6-finalize/SKILL.md:565-578`.
- OBSERVED: no finalize step declares `verdict_inputs` — a search for a line starting `verdict_inputs` under `marketplace/bundles/` and `.claude/skills/` returns nothing; `finalize-step-plugin-doctor` (`.claude/skills/finalize-step-plugin-doctor/SKILL.md:50`) and `pre-push-quality-gate` (`standards/pre-push-quality-gate.md:445-447`) record a deliberate refusal to declare.
- OBSERVED: both target steps are `head_dependent: true` and `mutates_source: true` — `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/finalize-step-simplify.md:9-10` (order 5) and `.claude/skills/finalize-step-lessons-housekeeping/SKILL.md:13-14` (order 4).
- OBSERVED: `verdict_inputs` is an optional implementor frontmatter key meaningful only with `head_dependent: true` — `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-finalize-step.md:56`.
- HYPOTHESIS: the lessons-housekeeping verdict also reads state outside the tracked tree (the lessons corpus, resolved main-anchored, and the plan outcome), so a path-glob declaration over tracked files may not be a superset of its inputs — confirm/refute at `.claude/skills/finalize-step-lessons-housekeeping/SKILL.md` § Step 3 classification inputs (verify-at-outline).
- HYPOTHESIS: the simplify verdict reads only the plan's changed code files, so a documentation-only fix commit cannot change it — confirm/refute at `phase-6-finalize/standards/finalize-step-simplify.md` § Workflow (what the review reads, and whether it reviews Markdown) (verify-at-outline).
- HYPOTHESIS: `mark-step-done --fact` accepts an arbitrary `may_close` value and the step's `records_facts` obligation admits `operator_override` — confirm at `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_mark_step.py` § fact validation and the `records_facts` frontmatter of `pre-submission-self-review.md` (verify-at-outline).
- HYPOTHESIS: run-reported scale — one plan fired the self-review 13 times with 10 loop-backs and closed by operator override with finalize at 59% of 19.85M tokens; another re-fired lessons-housekeeping, simplify and plugin-doctor six times each with zero edits at 56K–154K tokens per firing. Not reproduced here; the archived plans' `metadata.phase_steps` would confirm (verify-at-outline).
- Verify-first clause: read the contract shipped by PR #1488 ("a self-review that decides its own close") before designing Deliverable 2, so the operator close extends the verifier-owned stop decision instead of bypassing it.
- Verify-first clause: enumerate every reader and writer of `loop_back_iteration` (SKILL.md Step 3 pre-loop read at :701-711, item 7b, the declared-footprint refresh message, archive handling in `manage-status/scripts/_cmd_lifecycle.py`, tests) before changing its shape in Deliverable 3.
- Verify-first clause: for Deliverable 5, list what each step's verdict actually reads before writing a glob; a declaration that is not a superset buys a false skip, which is worse than the re-fire.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` — Step 3 pre-loop counter read and item 7b admission gate, STOP display (D1, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md` — § "Step 3b" state-finding filing, § "Step 4" Branch B and the closing paragraph, § "Round-loop termination" (D2, D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/manage-status.py` — new grant / operator-close verbs (D1, D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_mark_step.py` — override fact and skipped-with-basis record (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/SKILL.md` — verb documentation (D1, D2, D3)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_loop_back.py` — new command module for the per-source counter and grant (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_lifecycle.py` — archive-time handling of the loop-back record, only if the counter's shape change reaches it (verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py` — resolution of the step's state findings (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/manage-findings.py` — CLI surface for that resolution (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-findings/SKILL.md` — documented resolution path (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/execution.md` — "counted across both tiers" (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/standards/execution-recovery.md` — § Loop-back continuation cap (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/finalize-step-simplify.md` — `verdict_inputs` frontmatter and the re-fire paragraph (D5)
- OBSERVED: `.claude/skills/finalize-step-lessons-housekeeping/SKILL.md` — `verdict_inputs` frontmatter or recorded refusal (D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/verdict-currency.md` — adopter list / model text (D5)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/verdict_currency.py` — only if a declared step needs a discovery or matching fix; the classifier is expected to work unchanged (verify-at-outline)
- OBSERVED: `test/plan-marshall/phase-6-finalize/` — ceiling, grant, operator-close and verdict-currency cases beside `test_loop_back_outcome_*.py` and `test_verdict_currency_*.py`
- OBSERVED: `test/plan-marshall/manage-status/` — grant verb, per-source counter, override record
- OBSERVED: `test/plan-marshall/manage-findings/` — state-finding resolution beside `test_findings_store_resolution.py`

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: PLAN-LB-03 (`PLAN-LB-03-self-review-consumer-repos.md`) — both edit `phase-6-finalize/workflow/pre-submission-self-review.md`. Section ownership: THIS plan owns § "Step 3b" from the non-closing state table through the `qgate add` block and the unverified-dispatch paragraph, § "Step 4" Branch B and the paragraph that closes Step 4, and § "Round-loop termination". PLAN-LB-03 owns § "Domain-Aware Candidate Surfacing", § "Step 1" (implementor selection and the zero-generator fallback), the non-finding verdict vocabulary in § "Dispatched-envelope output", the boundary lines of the Step 3b verifier prompt, and the new not-covered branch in § "Step 4". Neither plan edits the other's sections. Sequence the two, never run them together; the second to start rebases onto the first. PLAN-LB-03 is the smaller plan and is suggested first.
- Overlaps with: PLAN-LB-11 (`PLAN-LB-11-finalize-staging-allowlist.md`) — `phase-6-finalize/SKILL.md` (it edits the commit seam, this plan edits Step 3 item 7b). Sequence.
- Overlaps with: PLAN-LB-10 (`PLAN-LB-10-retried-step-outcome.md`) — `manage-status/scripts/_cmd_mark_step.py`. Sequence.
- Overlaps with: PLAN-LB-09 (`PLAN-LB-09-pending-findings-gate.md`) — `manage-status/scripts/manage-status.py` and possibly `_cmd_lifecycle.py`. Sequence. Its pending-findings gate is also the consumer that Deliverable 4's unresolved state findings block today.
- Overlaps with: PLAN-LB-08 (`PLAN-LB-08-triage-survives-recheck.md`) — `manage-findings/scripts/_findings_core.py`. Sequence.
- Overlaps with: PLAN-LB-05 (`PLAN-LB-05-unrunnable-waits.md`) and PLAN-LB-06 (`PLAN-LB-06-triage-fix-task-loop.md`) — `plan-marshall/workflow/execution.md`; this plan changes one sentence there. Sequence or coordinate at the gate.
- Adjacent to: `.claude/skills/finalize-step-plugin-doctor/SKILL.md` — its refusal to declare `verdict_inputs` is recorded on evidence and stays; it keeps re-firing on every HEAD advance.
- Left out on purpose: process-compliance PLAN-20 D1 (naming a fixer for an inline `6-finalize` loop-back, and the per-round convergence measure) and D5 (the verifier's candidate-count contract and a file-reference form for oversized candidate envelopes).
- Left out on purpose: post-run-quality PLAN-PRQ-10 D0 and D2–D5 (corpus re-fire census, retiring `further_round_owed` as a finding, per-class detector coverage, an AsciiDoc detector, their controls), and its D1 shapes other than the `verdict_inputs` declaration. Deliverable 4 here keeps the state findings and makes them resolvable; it does not decide whether they should be findings at all.
- Left out on purpose: the shared surfacing envelope and all detector work.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/live-blockers/plans/PLAN-LB-02-self-review-convergence.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
