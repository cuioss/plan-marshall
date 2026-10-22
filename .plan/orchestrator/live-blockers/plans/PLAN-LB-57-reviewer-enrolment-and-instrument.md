# PLAN-LB-57: Enrol the deferred repositories and make the reviewer measurement reproducible

epic: live-blockers
workstream: WS-05

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-LB-57-reviewer-enrolment-and-instrument.md` and is queued as one row file,
> `queue/PLAN-LB-57.json`, in the epic ledger. The orchestrator EMITS the command below; it never
> launches the plan inline. This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer
> and carries no brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Moved out of PLAN-LB-48 (its former deliverables 6 and 7) on 2026-10-15, when the operator put
> the OpenCode work first. The content is unchanged. These are the unshipped deliverables of
> PLAN-LB-31 (#1771), folded by operator instruction on 2026-10-14; see `landings/PLAN-LB-31.md`.
> Not OpenCode work: sequence it after the OpenCode plans. Former deliverable 5 (efficacy-doc
> corrections) was dropped as medium; if deliverable 2 below persists the tables, the doc's dead
> pointers may be re-pointed at them within this plan's scope.

## Objective

PLAN-LB-31 landed without enrolling the thirteen deferred repositories, and its measurement can
no longer be re-run: its instrument was a set of temp scripts calling raw `gh`. The operator's
question during that run — "why not fixing the script?" — was never answered.

## Deliverables

1. **The thirteen deferred repositories are enrolled and the first reviews observed** (PLAN-LB-31
   spec D6, D7; carried PLAN-LB-20 D4, D5).
   - Ask the operator once — this writes to thirteen foreign repositories — then enrol each per
     the PLAN-LB-31 spec's D6, through the CI abstraction, one PR per repository.
   - Observe the first review on each newly enrolled repository AND on the six enrolled earlier
     (API-Sheriff, TokenSheriff, cui-http, cui-java-module-template, cui-open-rewrite,
     playwright-test-artifacts); the observation of the six does not depend on enrolment.
   - Comments on a foreign repository's PR go through the CI abstraction: add `--repo` to
     `ci pr reply` (it has none, which forced PLAN-LB-31 to raw `gh`).
   - The same selector reaches the other verbs a cross-repository pull request needs: `ci pr view`,
     `ci pr merge` and `ci checks status` take `--repo OWNER/NAME`, so a pull request of a sibling
     repository is read, checked and merged without leaving the abstraction (folded from
     `inbox/pm-mcp-core-m2-m4-004`, where the orchestrator of a consumer epic merged a pull request of
     `plan-marshall-documentation` with raw `gh` because the verbs have no repository selector).

   *Done when:* the PR lists, per repository, the enrolment PR (or the operator's no) and the
   observed first-review outcome; `ci pr reply --repo` has a test; `ci pr view --repo`, `ci pr merge
   --repo` and `ci checks status --repo` each have a test that fails when the option is dropped
   from the parser. At `7474b807` 0 of 13 are enrolled and `ci pr reply --repo` is an argparse
   rejection; at `d7e351419` the same rejection holds for `pr view`, `pr merge` and `checks status`
   (`--repo` is declared only by `repo label list` and `repo file read`).

2. **The measurement instrument is durable and its tables persisted.**
   - The corpus-pass instrument (population with charter split and exclusions, read-only fetch,
     structural classification) becomes committed code that reads through the CI abstraction —
     never raw `gh` — and re-runs deterministically from a stated window.
   - Re-run it once over PLAN-LB-31's window and persist the per-side tables, the fixed-diff rows
     and the experiment comment list in a committed location.

   *Done when:* the instrument runs through the executor in a test against fixture PR data and
   produces the table shape; the persisted tables exist at a committed location; a content search
   finds no `subprocess` call to `gh` in the instrument. At `7474b807` no instrument exists in the
   repository.

Split guard: two deliverables.

## Claim Labels

- OBSERVED: `archived-plans/2026-10-14-plan-lb-31-in-house-reviewer/tasks/TASK-006.json` is `done` after one `ci repo file read` step; its gate "PLAN-LB-30 schema release not evidenced" is refuted by `landings/PLAN-LB-30.md:43,77-78` (`v0.39.0`, `v0.40.0`); the roster decision ("keep required as is") does not block enrolment (PLAN-LB-31 inbox `-001`).
- OBSERVED: `ci pr reply` declares no `--repo` option, so PLAN-LB-31 posted its eight `/review` comments with raw `gh pr comment --repo …`.
- OBSERVED: at `d7e351419` `ci_base.py` declares `--repo` only on `repo label list` and `repo file read`; the `pr view`, `pr merge`, `pr reply` and `checks status` parsers declare none (orchestrator read of `ci_base.py` L1157, L1201, L1314, L1650, L1667).
- HYPOTHESIS: a pull request of a repository other than the routed working tree still needs the provider configured for that repository; the sibling's failure was "CI provider not configured" read from the checkout's own `marshal.json` — confirm whether `--repo` alone removes that dependency or whether the provider must also be resolved from the repository argument (verify-at-outline) (D1).
- OBSERVED: the `task1_*` scripts PLAN-LB-31's doc names (`task1_pop.py`, `task1_fetch.py`, `task1_classify.py`, `task1_final3.py`) no longer exist anywhere.
- HYPOTHESIS: the instrument belongs under `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/` (it measures that skill's reviewers) or `.claude/skills/` (meta-project only) — confirm with the operator at outline (verify-at-outline).
- HYPOTHESIS: the corpus reads the instrument needs (PR list with labels, review comments, check runs per head, workflow runs) are all reachable through existing `ci` verbs — confirm against `tools-integration-ci` `--help`; a missing read becomes a small `ci` verb, never a raw `gh` call (verify-at-outline).

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/ci_base.py` — `pr reply` parser, `--repo` (D1)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_ops.py` and `_github_pr.py` — the provider's reply implementation (verify-at-outline) (D1)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/tools-integration-ci/SKILL.md` — canonical invocation of `pr reply` (verify-at-outline) (D1)
- HYPOTHESIS: `test/plan-marshall/tools-integration-ci/` — `pr reply --repo` test (verify-at-outline) (D1)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/` — the durable corpus instrument (verify-at-outline) (D2)
- HYPOTHESIS: `doc/analysis/` — the persisted measurement tables (verify-at-outline) (D2)
- HYPOTHESIS: `test/plan-marshall/automatic-review/` — instrument tests (verify-at-outline) (D2)

## Dependencies and Sequencing

- Depends on: none. Priority: after the OpenCode plans (operator instruction, 2026-10-15).
- Overlaps with: PLAN-LB-46 (staged) on the `test/plan-marshall/automatic-review/` directory;
  PLAN-LB-41 (staged) only if the doc pointers are re-pointed.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/live-blockers/plans/PLAN-LB-57-reviewer-enrolment-and-instrument.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
