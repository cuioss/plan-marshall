envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-deployment-configurability
epic=truthful-signals
kind=candidate-lesson
created=2026-09-15T18:35:34Z

component=plan-marshall:phase-6-finalize
category=bug

# Finalize residue: tool-authored architecture-refresh commit stales the push freshness gate; branch-cleanup paces with a blocked shell sleep; prune-local-and-remote-ref is not idempotent after worktree-remove

Routed by the API-Sheriff `deployment-configurability` orchestrator on 2026-09-15 while draining PLAN-24's (`release-docs-and-tls-scenario-guide`, PR cuioss/API-Sheriff#305, squash `fb65222`) epic inbox. The originating plan filed these as `candidate-lesson` messages to its API-Sheriff epic; their remedy lives in the plan-marshall bundle, so they are relocated here — the same routing this epic used for `-001`..`-013`. Not re-verified against plan-marshall source by the orchestrator: each is a lead from one plan run. Original message bodies (envelope stripped) are verbatim below.

Origin messages: `release-docs-and-tls-scenario-guide-009`, `release-docs-and-tls-scenario-guide-011`, `release-docs-and-tls-scenario-guide-012`.

⚠ `-009` is adjacent to PLAN-TRUTH-166 (architecture-refresh commits descriptor churn into unrelated PRs), staged from `api-sheriff-configuration-security-hardening-001` — same step, different defect (freshness-gate invalidation rather than churn). Filed as its own item; merge on your side if one fix covers both. `-012` recurs the `orphaned-worktree-prune` shape this operator has hit before.

---

## Original `release-docs-and-tls-scenario-guide-009`

component=plan-marshall:phase-6-finalize
category=bug
source_finding=operational event (orchestrator-reported), plan release-docs-and-tls-scenario-guide

# architecture-refresh self-commit carries no freshness reconciliation record, staling the push gate

## What happened

The finalize architecture-refresh step committed the regenerated `.plan/project-architecture/*` files itself. That commit wrote no freshness reconciliation record, so the push step's freshness gate saw HEAD advanced past the last quality-gate run and reported the gate as stale. A full quality-gate re-run was required even though the only new commit was generated architecture metadata that no Maven build reads.

## Corrective action

A plan-marshall step that authors its own commit must also record the freshness reconciliation for that commit (or the freshness gate must classify a commit whose footprint is solely generated `.plan/project-architecture/**` as not invalidating the prior gate result). Either way, a tool-authored metadata commit should not force a multi-minute gate re-run.

## Evidence

- Plan: release-docs-and-tls-scenario-guide (PR #305)

---

## Original `release-docs-and-tls-scenario-guide-011`

component=plan-marshall:phase-6-finalize
category=bug
source_finding=operational event (orchestrator-reported), plan release-docs-and-tls-scenario-guide

# branch-cleanup paces its poll with a standalone sleep, which the harness blocks

## What happened

The `branch-cleanup` finalize step's polling loop (waiting on merge/CI state) paces itself with a standalone foreground `sleep` Bash call. The Claude Code harness blocks foreground `sleep`, so the documented pacing step cannot execute as written and the orchestrator had to improvise the wait.

## Corrective action

Replace the bare `sleep` pacing in branch-cleanup with a sanctioned bounded wait: a script-side poll with its own timeout (e.g. a `ci pr wait`/`checks wait`-style verb or a `--wait-seconds` option on the status query), so no workflow step depends on a shell `sleep`. Audit other finalize workflows for the same pattern.

## Evidence

- Plan: release-docs-and-tls-scenario-guide (PR #305), finalize branch-cleanup

---

## Original `release-docs-and-tls-scenario-guide-012`

component=plan-marshall:workflow-integration-git
category=bug
source_finding=operational event (orchestrator-reported), plan release-docs-and-tls-scenario-guide

# prune-local-and-remote-ref errors when worktree-remove already deleted the local branch, leaving the tracking ref unpruned

## What happened

In finalize cleanup, `worktree-remove` deleted the plan's local branch along with the worktree. The subsequent `prune-local-and-remote-ref` then tried to delete that local branch, errored because it no longer existed, and stopped before pruning the remote-tracking ref — so the stale `origin/{branch}` tracking ref was left behind.

## Corrective action

`prune-local-and-remote-ref` should be idempotent per ref: an already-absent local branch is a `skipped/already_absent` outcome, not an error, and the verb must still proceed to prune the remote-tracking ref (and report each ref's outcome separately). Alternatively, make the two verbs agree on which one owns local-branch deletion.

## Evidence

- Plan: release-docs-and-tls-scenario-guide (PR #305, squash-merged as fb65222)
- Related memory: orphaned-worktree-prune (manual plain-git prune after worktree-remove dead-ends)
