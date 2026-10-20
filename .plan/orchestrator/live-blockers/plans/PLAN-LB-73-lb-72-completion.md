# PLAN-LB-73: The runbook lane's text is consistent and its qualifying-review signal is reliable

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-73-lb-72-completion.md` and is queued as one row file, `queue/PLAN-LB-73.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged from the adversarial landing analysis of PLAN-LB-72 (#1819, `cf28a05db`),
> `landings/PLAN-LB-72.md` § Deliverable Fidelity. Priority is **low**: nothing here blocks a run.
> **Each deliverable is its own outline deliverable, and each Done-when is its own success
> criterion. Do not merge them.** A Done-when says "fails at `cf28a05db`" only where the behaviour
> is new at that sha; a clause that already holds says "holds at `cf28a05db`". Grade each deliverable
> against THIS spec's Done-when text; an outline that rewrites a Done-when must say so and why.

## Objective

PLAN-LB-72 added the evidence-order rules, the classifier and the flat-identity error to the
runbook lane. Its edits left the lane text contradicting itself in four places, kept a
qualifying-review rule that a clean CodeRabbit review can never satisfy (which cost an unnecessary
91-minute operator question), and left three tests that cannot fail for the reason they name. This
plan closes those, each against a fixture that fails at `cf28a05db`.

## Deliverables

1. **The lane text states each rule once and the qualifying-review signal counts a clean review.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - The branch row (`SKILL.md:80`) states one set: the canonical `feature/`, `fix/` and `chore/`
     plus the project's configured `working_prefixes`, and no sentence in the row makes
     `working_prefixes` the sole set.
   - The §0a progress template carries the `order` slot per Done-when and no longer words a
     `mutation-after` or `none` entry as "failed before fix".
   - One place (§1) states how a Done-when is graded by order: `test-first` is met; `mutation-after`
     is met with the order stated; `none` on a "fails at" clause is `not met as written`. §3 and §6
     refer to it and do not restate it, and §1 and §3 no longer mandate test-first as the only valid
     order.
   - §6 requires the failing run's commit and output identifier only where `order` is not `none`.
   - §4's docs-only branch states whether `test-compile` applies to a docs-only head.
   - §7's "qualifying review" for a quota-limited reviewer counts a formal review AND the reviewer's
     marker-bearing summary comment that names the head with `kind=reviewed`, because CodeRabbit
     publishes a clean review only in that form (`coderabbit.md:311-316`). A reviewer that is not
     quota-limited keeps needing a review of the current head and is not affected.

   *Done when:* each of these fails at `cf28a05db`:
   - a doc test asserts the branch row names one set and does not contain the sentence that makes
     `working_prefixes` the sole source;
   - a doc test asserts the §0a template has an `order` slot and that no template line says "failed
     before fix" without it;
   - a doc test asserts §1 states the grading by order and that §3 and §6 do not restate it;
   - a doc test asserts §6 requires the failing-run identifier only for the orders that have one;
   - a doc test asserts §4 states the docs-only `test-compile` rule;
   - a doc test asserts §7 names the marker-bearing summary comment as a qualifying review for a
     quota-limited reviewer and keeps the current-head rule for a reviewer that is not;
   - a doc test asserts §7 requires the run to re-read the review surfaces (`ci pr comments`,
     `ci pr reviews`, the reviewer's summary comment) in the same step as the merge-gate question and
     again immediately before the enqueue, to put into the question only facts read in that step,
     and to treat a review of the current head that arrived after the question was asked as
     invalidating the answer (folded from `landings/PLAN-LB-70.md`, where a question stated that a
     head had not been reviewed 64 seconds after its review landed);
   - a doc test asserts §7 states that an unresolved review thread or an unhandled outside-diff
     finding on the merge head blocks the standing authorization;
   - the PLAN-LB-72 merge-gate state (both bots clean, `ci pr reviews` empty, CodeRabbit's summary
     comment covering the head) is a fixture a doc-level gate test treats as qualifying.

2. **The tests of the existence check, the timeout and the evidence rule can fail for the reason they name.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - The timeout test makes the real `_cmd_client._augment_resolved` raise (or return no stamp) by
     patching what it reads, not by replacing the function with a stub, so a raising real function
     falls back to 1800 and the test fails. An in-test stub that returns a fixed value is not used.
   - The probed-layout test builds a versioned nested cache fixture (`{cache}/plan-marshall/0.1.0/…`)
     and asserts the versioned probe path, not the unversioned fallback.
   - The `test-compile` evidence test asserts a `test-compile` token beside the sha placeholder in the
     landing template, not the pre-existing `{sha}` text.
   - The glob helper's absence and any non-`ImportError` failure at import both make every path build
     with a named reason, and each has a test.

   *Done when:*
   - mutating the real `_augment_resolved` to raise fails the timeout test; at `cf28a05db` that
     mutation passes it (this Done-when is `mutation-after` by construction);
   - the probed-layout test fails when the versioned nested probe is dropped from the error;
   - the `test-compile` evidence test fails when the `test-compile` token is removed from the landing
     template. This clause **holds at** `cf28a05db` (the token is present and the old test passed on
     the `{sha}` text alone), so it is `mutation-after` by construction;
   - an unavailable glob helper reports `glob helper unavailable: ImportError` and every path builds
     (this behaviour holds at `cf28a05db` and is untested there: the test is new);
   - a non-`ImportError` exception at import reports a named reason and every path builds; at
     `cf28a05db` it propagates.

## Claim Labels

- OBSERVED: the branch row says the prefix set is closed and that `working_prefixes` is "its only extension, never a replacement", and in the same sentence that the prefix "must be one the project's configured `working_prefixes` declares" — `marketplace/bundles/plan-marshall/skills/runbook-lane/SKILL.md` L80.
- OBSERVED: the §0a template line `D{n} test: … — failed before fix ({evidence}), passed after` has no `order` slot — `SKILL.md` L139.
- OBSERVED: §1 and §3 step 2 mandate test-first while §6 and §8 accept `mutation-after` and `none` — `SKILL.md` L162-163, L300-301, L382-386, L515-522 (audit of PLAN-LB-72).
- OBSERVED: §7 excludes a summary comment from "qualifying review", while a clean CodeRabbit review is published only as a marker-bearing summary comment — `SKILL.md` L423-425 and `marketplace/bundles/plan-marshall/skills/automatic-review/standards/coderabbit.md` L311-316.
- OBSERVED: the timeout test replaces `_cmd_client._augment_resolved` with a lambda — `test/plan-marshall/runbook-lane/test_runbook_lane.py` L1363-1367.
- OBSERVED: `ci pr reviews` returned `review_count: 0` on PR #1819 although both required bots reviewed the merge head through comments (orchestrator check, `landings/PLAN-LB-72.md`).
- HYPOTHESIS: the Guide issue comments of cuioss-review-bot are an adequate head-coverage signal for that reviewer and need no change — confirm at `automatic-review/standards/cuioss-review-bot.md` § the reviewer's published artifacts (verify-at-outline).
- Verify-first clause: confirm the marker text CodeRabbit's clean-review summary carries (`<!-- recent_review_start -->` and the `sourceCommitId` / `coveredCommitId` / `kind` fields) against a live comment before D1 names them, and record the source.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/runbook-lane/SKILL.md` — the branch row, §0a, §1, §3, §4, §6, §7 (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/runbook-lane/scripts/runbook_lane.py` — the glob-helper import guard (D2)
- OBSERVED: `test/plan-marshall/runbook-lane/test_runbook_lane.py` — the doc tests of D1 and the tests of D2
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/coderabbit.md` — read only, the marker (verify-at-outline) (D1)

## Dependencies and Sequencing

- Depends on: PLAN-LB-72 (shipped, `cf28a05db`).
- Overlaps with: no running or staged plan on a file.
- Adjacent to:
  - PLAN-LB-69 D4 takes the Done-when authoring rule ("fails at" versus "holds at") on the
    orchestrator side; this plan does not touch it.
  - The classifier's architecture fallback can still say `docs-only` for a path a reusable CI workflow
    would build. That is an operator ruling, not a deliverable here.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-73-lb-72-completion.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
