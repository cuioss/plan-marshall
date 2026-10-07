# WS-02: Org-side workflow gates

epic: review-apparatus

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-02-org-workflow-gates.md` and is tracked in the epic
> `status.json` `workstreams[]` field. See
> `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

Owns the reusable-workflow layer in `cuioss-organization` that actually invokes PR-Agent — the
event subscriptions, the job-level skip guards, and the fail-closed empty-review gate. Its
outcome is that the gate fails only on the cases it was written to catch (a runner that
produced nothing because every model call failed) and passes the cases the runner legitimately
produces nothing for, so that push-trigger review can be enabled without a wall of false
failures across the org.

## Scope

The org repository only. This workstream is disjoint by construction from every plan-marshall
file, which is what makes it the candidate second stream if `parallelization_scope` is ever
raised above 1.

- In scope: `cuioss-organization/.github/workflows/reusable-pr-agent-review.yml` — the
  empty-`REVIEW_OUTPUT` guard, the job-level `if:` skip guards (which is where
  `ignore_pr_*` semantics actually live for GitHub Action mode), and the consumer release
  fan-out that carries a change to ~21 repos.
- Out of scope: PR-Agent's own settings (`pr-agent-settings` — WS-03); anything inside
  plan-marshall (WS-01); the CodeRabbit config repo (WS-03).

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-PR-002-org-empty-review-guard-too-broad | staged | Narrow the fail-closed guard to the cases it was written for, without weakening it |

## Sequencing and Surface Notes

- ⚠ **No local checkout exists.** `references.json` records `local_checkout: null` for
  `cuioss-organization`. The plan's first act is to obtain one; it cannot assume a tree is present
  the way the other two config repos can.
- The guard must be narrowed BEFORE `handle_push_trigger` is enabled, never after — a broad
  guard plus push triggers means a fan-out of false job failures across ~21 repos.
- ⛔ Do NOT narrow by downgrading empty-review to a warning. The runner exits 0 when every model
  call fails, and this guard is the only thing separating "reviewed, found nothing" from "never
  reviewed" — that ambiguity already cost a real misread on plan-marshall#1024.
- Fully disjoint from WS-01 and WS-03. Held only by `parallelization_scope = 1`.
