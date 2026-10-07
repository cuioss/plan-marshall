# WS-02: Invocation surfaces that teach their own fix

epic: finalize-machinery

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-02-invocation-surfaces.md` and is tracked in the epic
> `status.json` `workstreams[]` field. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

Owns the argparse-rejection class: nine rejections in one run across four signatures,
several recurring from independent callers, including one hit with the documenting
standard open. Documentation has failed to hold this class; the remedy lives in the
rejection message itself, which must name the offending flag and the sibling verb.

## Scope

- In scope: argparse rejection messages and router-vs-verb flag splits in manage-*
  scripts, tools-integration-ci prepare-body, workflow-integration-github github_pr
  --plan-id, automatic-review measured-diff-size doc contract
- Out of scope: finalize step ordering (WS-01), review-currency semantics (WS-03),
  ledger pipeline (WS-04)

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-02-invocation-surfaces | staged | Make every rejection in the class name its fix at the rejection site |

## Sequencing and Surface Notes

- Single-plan workstream; no internal ordering.
- File-level adjacency with PLAN-03 inside automatic-review (doc wording vs gate
  scripts, different files) — disjoint at file granularity, sequence if either plan
  widens its surface beyond its declared files.
