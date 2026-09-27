# PLAN-12: Worktree-pinned path resolution

epic: truthful-signals
workstream: WS-06

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-12-worktree-paths.md` and is queued in the epic `status.json`
> `plans[]` field. The orchestrator EMITS the command below; it never launches the
> plan inline. This spec is SELF-SUFFICIENT.

## Objective

Resolve every path in the tree the plan runs in: uniform CWD walk-up for plan
directories, worktree-aware prepare/list/consult, localized git output parsed by
structure, argparse rejections that name the notation. G04 + 5 singletons (10 lessons).

## Deliverables

1. Uniform CWD walk-up plan resolution in consult (2026-08-30-16-001).
2. Directory/glob claims rendered and disjointness-checked (2026-08-25-09-016).
3. Invalid-invocation classification from stdout, not stderr alone (2026-09-03-11-003).
4. Idempotent prepare inside the worktree (2026-09-04-14-004).
5. Worktree-resident plan listing without file_not_found (2026-09-04-14-009).
6. Localized merge-tree output never parsed as conflicts (2026-09-04-07-001).
7. Main-anchored consult finding worktree outlines (2026-09-04-07-002).
8. list-deliverables verb named in prose (2026-09-07-15-005).
9. Invocation-quoting workflow steps (2026-09-07-15-010).
10. Argparse/notation rejections classified per notation (2026-09-13-12-005).

## Claim Labels

- OBSERVED: consult returned outline_not_found for a readable worktree outline under CWD-pinned model — read at `lessons-archive/2026-08-30-16-001.md` § Observed + Cause; corroborated at `marketplace/bundles/plan-marshall/skills/manage-lessons/scripts/_lessons_query.py` § outline_not_found.
- OBSERVED: directory/glob claims dropped by renderer and gate, absence reading as disjointness — read at `lessons-archive/2026-08-25-09-016.md` (title triage; body verified at outline).
- HYPOTHESIS: uniform CWD walk-up plus declarative claim rendering closes both — confirm/refute at `marketplace/bundles/plan-marshall/skills/manage-lessons/scripts/` § consult resolver (verify-at-outline).

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-lessons/` — consult, list.
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-architecture/` — content search regexes.
- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-script-executor/` — invocation classification.

## Dependencies and Sequencing

- Depends on: PLAN-10.
- Overlaps with: PLAN-11 (adjacent lifecycle skills, disjoint files) — may pair once PLAN-10 lands.
- Adjacent to: none.
- Landing follow-up (PLAN-01, #1545; folded from ledger-joins-005 as recurrence,
  no new surface): 8 script-failure notations led by argparse rejections from
  invented subcommands/flags — quote invocations verbatim from executor mappings
  or --help output, never extrapolate.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/truthful-signals/plans/PLAN-215-worktree-paths.md"
```

## Write-Boundary

The plan touches only its own repository source and tests. It creates and edits NO
file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}`
message, and reports its outcome through its PR and its inbox message.
