# PLAN-LB-74: The criteria gate's unhandled review findings, matching hazard and unserialised seal are fixed

epic: live-blockers
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-74-lb-70-integrity-fixes.md` and is queued as one row file, `queue/PLAN-LB-74.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged from the adversarial landing analysis of PLAN-LB-70 (#1815, `a297ea762`),
> `landings/PLAN-LB-70.md` § Deliverable Fidelity. Priority is **high**: PLAN-LB-70 merged with two
> unhandled Major CodeRabbit findings in the gate it repaired. **Each deliverable is its own outline
> deliverable, and each Done-when is its own success criterion. Do not merge them.** A Done-when says
> "fails at `a297ea762`" only where the behaviour is new at that sha; a clause that already holds says
> "holds at `a297ea762`". Grade each deliverable against THIS spec's Done-when text; an outline that
> rewrites a Done-when must say so and why.

## Objective

PLAN-LB-70 made the finalize gate refuse only real gaps and bound the verdict and snapshot digests
outside the files they protect. Its merged head still carries two Major findings CodeRabbit raised and
nobody handled: a code review can report `may_close: true` without grading the branch's test changes
when a declared worktree is missing, and a failed snapshot-digest record leaves a frozen snapshot
that nothing binds. The gate's matching can also release a criterion the reviewer graded not met, and
the digest record is written without the status writer's lock, so it can be lost. This plan closes
those, each against a fixture that fails at `a297ea762`.

## Deliverables

1. **The two Major findings CodeRabbit raised on PR #1815 are fixed.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - In `review_support.py` a `worktree_unresolved` error from the test-integrity computation is
     exempt only when the plan does not use a worktree (`plan_uses_worktree(plan_id)` is false); a
     plan that declares a worktree which no longer resolves gets a blocking `test_integrity_not_run`
     finding and `may_close: false` (thread `PRRT_kwDOQ3xasM6uAyYk`).
   - In `_criteria_snapshot.py` (`write_snapshot`, around `:588-595`), when the snapshot digest cannot
     be recorded in the status record, the verb returns an error and the snapshot it wrote is rolled
     back, so no frozen snapshot exists without its outside-the-file binding.

   *Done when:* each of these fails at `a297ea762`:
   - a code review of a plan with `metadata.use_worktree: true` whose worktree is missing returns a
     blocking `test_integrity_not_run` finding and `may_close: false`;
   - when `record_integrity` returns `False` inside `write_snapshot`, the verb returns an error and the
     snapshot file is absent afterwards.

   And this one **holds at** `a297ea762` (a preservation clause, kept as a regression guard): a plan
   with `use_worktree: false` still yields no `test_integrity_not_run` finding from a missing worktree.

2. **A verdict row answers a criterion only by id or by its exact text.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - `_graded_status` (`_criteria_snapshot.py:961-994`) drops the positional fallback. A row matches
     by `criterion_id`, then by exact normalised text; otherwise the criterion is `ungraded`.
   - `criterion_id` becomes part of the verdict authoring schema (`functional-review.md` schema block
     and the `author-verdict` validation in `review_support.py`), so a reviewer who paraphrases a
     criterion keeps it graded by carrying its id.
   - The validator reports a verdict row that matches no frozen criterion by id or text.

   *Done when:* each of these fails at `a297ea762`:
   - frozen criteria `["parser rejects garbage", "parser accepts input"]` with a sealed verdict that
     grades `"parser accepts input"` met (evidenced) and `"junk input is refused"` not met leaves the
     first criterion open: `open_count` is 1, not 0;
   - a verdict row with a paraphrased text and no `criterion_id` leaves its criterion `ungraded` and the
     validator names the unmatched row;
   - `author-verdict` accepts a `criterion_id` on a row and rejects a `criterion_id` that names no
     frozen criterion.

   And this one **holds at** `a297ea762`: a paraphrased row that carries the criterion's `C{n}` id
   grades it (the id arm exists but no producer wrote it).

3. **The integrity record is written under the status writer's lock and its keys are protected.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - `record_integrity` (`_criteria_snapshot.py:134-161`) no longer rewrites `status.json` itself. It
     runs inside the same critical section the `manage-status` writers use, or calls a `manage-status`
     verb; choose at outline and record why. The spec of PLAN-LB-70 asked for "through
     `manage-status`".
   - `manage-status metadata --set` (and `--append`) refuses the keys `criteria_integrity`,
     `snapshot_frozen` and `functional_review_override_heads`; each is written only by its owning verb
     (the writing criteria verbs and `loop-back close`).

   *Done when:*
   - a test that holds the status critical section open shows `record_integrity` blocks until it is
     released or reports a busy lock, where at `a297ea762` it writes immediately (fails at
     `a297ea762`);
   - `manage-status metadata --set --field criteria_integrity` is refused, and so are
     `snapshot_frozen` and `functional_review_override_heads` (fails at `a297ea762`);
   - the owning verbs still write those keys (holds at `a297ea762`).

4. **A `.plan/` citation cannot escape its directory or count a self-written file.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - In `_review_support_validate.py` (`:250-261`) a `.plan/` citation is resolved first and then
     checked against the plan's `build-results` directory, so `.plan/../src/x.py` and any `.plan/temp/*`
     file are refused as evidence.

   *Done when:* each of these fails at `a297ea762`:
   - a citation `.plan/../src/x.py` that exists in the checkout working tree is refused;
   - a citation of a self-written `.plan/temp/note.txt` is refused;
   - a build-log citation under the plan's own `build-results` directory is accepted (this clause
     **holds at** `a297ea762` and is kept as the positive control).

## Claim Labels

- OBSERVED: CodeRabbit raised an inline Major on `075115bed` at 16:39:37Z (`review_support.py` L215, thread `PRRT_kwDOQ3xasM6uAyYk`, unresolved at merge) and an outside-diff Major on `_criteria_snapshot.py` L588-595 that was never handled — `ci pr comments --pr-number 1815`.
- OBSERVED: `_graded_status` falls back to `criteria[index - 1]` when no id and no exact text match — `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/_criteria_snapshot.py` L961-994 (orchestrator check, `landings/PLAN-LB-70.md`).
- OBSERVED: `criterion_id` is in no verdict schema, so no producer writes it — `phase-6-finalize/workflow/functional-review.md` L326-355 and `phase-6-finalize/scripts/review_support.py` L46-61 (audit of PLAN-LB-70).
- OBSERVED: `record_integrity` does a read-modify-write of `status.json` outside the `rmw_json` critical section and its docstring says so — `_criteria_snapshot.py` L134-161.
- OBSERVED: `manage-status metadata --set` has no protected-key list — `manage-status/scripts/_status_query.py` L301-398 (audit of PLAN-LB-70).
- OBSERVED: the `.plan/` citation arm is constrained to the whole checkout and reads the working tree — `_review_support_validate.py` L250-261.
- HYPOTHESIS: the status writers' critical section can be entered from the criteria scripts without an upward import cycle — confirm at `manage-status/scripts/_status_query.py` § `rmw_json` and the import rules in `_criteria_snapshot.py` § Layering (verify-at-outline).
- HYPOTHESIS: `loop-back close` is the only writer of `functional_review_override_heads` — confirm at `manage-status/scripts/_cmd_loop_back.py` (verify-at-outline).
- Verify-first clause: decide whether the lock is shared by import or the digest goes through a `manage-status` verb, before D3 is scoped; record why.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/_criteria_snapshot.py` — `write_snapshot`, `_graded_status`, `record_integrity` (D1, D2, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/review_support.py` — the `worktree_unresolved` exemption, `author-verdict` schema (D1, D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/_review_support_validate.py` — unmatched rows, the citation arm (D2, D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/functional-review.md` — the verdict schema block (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_status_query.py` — `metadata --set` protected keys (D3)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_loop_back.py` — the owning writer of the override heads (verify-at-outline) (D3)
- OBSERVED: `test/plan-marshall/phase-6-finalize/` and `test/plan-marshall/manage-status/` — the fixtures of D1 to D4

## Dependencies and Sequencing

- Depends on: PLAN-LB-70 (shipped, `a297ea762`).
- Overlaps with: the staged PLAN-LB-53 and PLAN-LB-55 on `manage-status/scripts/` and
  `phase-6-finalize/scripts/`. The emit gate decides; this plan is **high** and goes first, because it
  repairs the gate those plans' finalize steps run through.
- Adjacent to: PLAN-LB-75 (the reach and documentation half of PLAN-LB-70's audit) shares the same
  files and follows this plan.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-74-lb-70-integrity-fixes.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
