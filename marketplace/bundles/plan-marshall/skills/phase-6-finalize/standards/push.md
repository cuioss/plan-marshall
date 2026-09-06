---
lane:
  class: core
  cost_size: XS
name: default:push
description: Push the converged branch
order: 11
mutates_source: false
default_on: true
presets:
  - local
  - standard
  - full
implements: plan-marshall:extension-api/standards/ext-point-finalize-step
---

# Push

Pure executor for the `push` finalize step. A **pure push barrier**: it carries NO commit logic. Every deliverable was committed on the feature branch during phase-5-execute, and the dispatcher's commit instrumentation (`phase-6-finalize/SKILL.md` Step 3 item 5f) commits each `mutates_source: true` step's output before this barrier runs — so the steady-state expectation here is a **clean working tree**. This step asserts the tree is clean and pushes the converged branch to remote; it produces NO commit. The squash-merge-at-merge convention is unchanged: per-deliverable feature-branch commits collapse into a single squashed commit on `main` at merge.

## Exit-code convention for `manage-*` script calls

Every `manage-*` script call in this document carries the following exit-code contract unless a step explicitly states otherwise:

- **`exit_code == 0`**: parse the returned TOON and use the value as the step describes.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

This document carries NO step-activation logic. Activation is controlled by the dispatcher in `phase-6-finalize/SKILL.md` Step 3 and is driven solely by presence of `push` in `manifest.phase_6.steps`. When the dispatcher runs this step, the executor always runs to completion and records `outcome=done` — the `display_detail` payload reports the push outcome. The `commit_and_push == false` (local-only) case is handled at composition time by the manifest's `commit_push_disabled` pre-filter (see `manage-execution-manifest/standards/decision-rules.md`), so this step is never dispatched in that case.

## Inputs

- `commit_and_push` from phase-5-execute config (boolean, default `true`). The `false` (local-only) value is filtered out at manifest composition time by the `commit_push_disabled` pre-filter and never reaches this executor — so whenever this step runs, `commit_and_push` is `true` and the converged feature branch is to be pushed.
- `{worktree_path}` has been resolved at finalize entry (see SKILL.md Step 0). All git commands below MUST use `git -C {worktree_path}`.

### Freshness precondition

Before the push runs, invoke the deterministic freshness gate:

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks \
  pre-commit-verify-freshness --plan-id {plan_id}
```

Parse `status` from the returned TOON. The contract is **fail-closed**: exactly two of the gate's four status members permit the executor to proceed — `fresh` and `exempt` — and they permit **on different bases**, which is why the branch below reads the member rather than treating any non-refusal as a pass. Any other status halts `push` immediately — record `outcome=failed` with a `display_detail` carrying the reason, the current working-tree `worktree_sha`, and the ledger path so the orchestrator's recovery path has the structured signal it needs to dispatch a fresh `verify` run.

The gate reaches its verdict by one of **two disjoint routes**, and the status member names which one ran:

- **The exemption route.** The gate first consults the single build/no-build authority. On a `not_necessary` verdict no `kind=build` entry could legally exist for this footprint, so the gate returns `exempt` carrying the authority's own `reason` **before any ledger row is read**. Nothing about the working tree was examined; the push is permitted because no build was ever owed, not because one was observed.
- **The ledger-scanned route.** Otherwise the gate scans the unified change-ledger for a `kind=build` entry matching the current `worktree_sha`, then cross-checks the `notation` of **every** such row against the build notations this project's architecture resolves (one corroborated row is enough; only a set in which none corroborates is a refusal), and returns `fresh` naming the row it matched; see `marketplace/bundles/plan-marshall/skills/manage-change-ledger/SKILL.md`. The gate is tier-agnostic and build-tool-agnostic on this route.

⛔ **Do not collapse the two permitting members, and do not branch on the absence of a refusal.** A predicate of the shape "`status` is not `stale` and not `undecidable`" admits any future member the gate gains, which is exactly the fail-open ADR-009 forbids. Read the member.

| `status` value | `push` action |
|----------------|---------------|
| `fresh` | Proceed to **Execution** below. A build was observed against this exact working tree. Carry `basis=ledger-verified` into the outcome record (see **Mark Step Complete**). |
| `exempt` | Proceed to **Execution** below. No build was owed, so **nothing was examined** — the push proceeds on the exemption, not on evidence. Carry `basis=exempt-unscanned` and the gate's `reason` into the outcome record, so a reader of the finalize record can tell which basis this push rested on. |
| `stale` | Halt. Record `outcome=failed` with `display_detail` `"stale: {reason} observed_status={observed_status} worktree_sha={worktree_sha} ledger={ledger_path}"` (substitute `-` for `observed_status` when absent). Do NOT push. |
| `undecidable` | Halt. Record `outcome=failed` with `display_detail` `"undecidable: {reason}"` (`reason` is `no_registry` or `head_unresolvable`). Do NOT push. |

**The `stale` `reason` MUST be carried into `display_detail` — it is the only thing that tells the operator what to do next.** The gate reaches `stale` by several routes and they need different responses, so the `reason` is the only field that separates them; a `display_detail` reporting just the sha and ledger path hands one refusal to the operator indistinguishable from another, which is the same discarded-discriminator defect this gate was fixed to stop. The routes and the remedy each one owes are the reason table in `manage-tasks/SKILL.md` § "Pre-Commit Verify Freshness"; read them there rather than from a copy here, so this consumer doc cannot fall behind the vocabulary as it grows.

The freshness gate is **complementary to**, NOT redundant with, the `pre-push-quality-gate` step. The quality-gate verifies *what the code is* (mypy + ruff + tests on the on-disk tree); freshness verifies *that the most recent `verify` run actually observed this version of the code*. A worktree that was modified after the most recent successful build passes neither: the quality-gate may pass against the new tree if the orchestrator re-runs it, but the freshness gate fails because no `kind=build` change-ledger entry carries the current working-tree `worktree_sha`. The two gates together close the gap that `loop-exit-guard` cannot close on its own — `loop-exit-guard` answers "is the queue empty?" while freshness answers "has a `verify` run actually observed this version of the code?"

#### Finalize-internal re-stale reconciliation (documented — replaces the silent `--force`)

This section is scoped to a SINGLE `stale` route: `reason: worktree_mutated`, where no `kind=build` row carries the current sha at all. Read the `reason` first. **Every other `stale` reason is out of scope here**, and the discriminator is what puts it there rather than a list: `worktree_mutated` is the only route on which no row carries the current sha, so on every other route some row already does — the tree has not moved past the build a reconciliation record would reconcile, and none can exist or should be sought. Those routes halt per the table above, each with the remedy the reason table in `manage-tasks/SKILL.md` § "Pre-Commit Verify Freshness" gives for it.

Within `worktree_mutated` there are two distinct causes, and only ONE is a genuine defect:

- **Genuine un-built source drift** — source was edited after the last successful `verify`, and no build observed the current tree. This MUST stay fail-closed (halt per the table above).
- **Finalize-internal re-stale (known-safe)** — a finalize-internal step committed DURING finalize, advancing the working-tree `worktree_sha` past the last `kind=build` ledger entry. The source a `verify` DID observe is unchanged; only a finalize-owned commit moved the currency hash. Overriding this silently with `--force` discards the distinction and the audit trail.

  **Membership is a discriminator, not a list**: a step whose authoritative doc declares `mutates_source: true` **and** whose `order` is greater than `default:pre-push-quality-gate`'s. Both operands are load-bearing. `mutates_source: true` is what makes the step capable of moving the hash at all; the order bound is what makes the move happen *after* the ledger entry this route is measured against, since that entry is written by the pre-push quality gate. A `mutates_source: true` step ordered at or below that gate commits before the ledger row exists, so its commit is already covered by it and produces no re-stale. Resolve both operands from the step docs' own frontmatter rather than from any list here — this bullet deliberately states no membership count, because a count here would go stale the moment a step is added. `default:finalize-step-simplify` and `plan-marshall:automatic-review` are among the members today, named as examples only.

  `default:lessons-capture` is NOT a member and never was: it declares `mutates_source: false`.

Before failing closed on `stale`, the executor MUST determine which cause applies by consulting the **reconciliation record** the dispatcher emits at `phase-6-finalize/SKILL.md` Step 3 item 5f(d) immediately after a finalize-internal `mutates_source` commit. Resolve the current HEAD:

```bash
git -C {worktree_path} rev-parse HEAD
```

Then read the decision log for a freshness-reconcile record naming that HEAD:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  read --plan-id {plan_id} --type decision
```

- **A reconciliation record names the current HEAD as a finalize-internal commit** (marker `(plan-marshall:phase-6-finalize:freshness-reconcile)` carrying `commit_sha={HEAD}`, the producing `step_id`, and the prior successful-build `worktree_sha`): the `stale` is the known-safe finalize-internal case. Emit a legible `decision`-level reconciliation confirmation and PROCEED to **Execution** below — the gate is reconciled for a documented reason, NOT silently overridden:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
    decision --plan-id {plan_id} --level INFO \
    --message "(plan-marshall:phase-6-finalize:push) Freshness reconciled — stale worktree_sha={worktree_sha} attributable to finalize-internal commit {commit_sha} from step {step_id}; prior successful-build worktree_sha={prior_build_worktree_sha}. Proceeding to push against a documented reconciliation, not a silent override."
  ```

- **No reconciliation record names the current HEAD**: the `stale` is genuine un-built source drift. Fail closed per the table above — halt, record `outcome=failed`, do NOT push.

The `--force` escape survives only as the orchestrator-only, log-recorded, never-auto-invoked manual override for the genuine-drift case (mirroring phase-5 Step 12a's escape) — it is NOT the mechanism for the finalize-internal re-stale, which is now handled by the reconciliation record above. When the orchestrator drives finalize with `--force` AND the gate returned a refusing status (`stale` or `undecidable`) with NO matching reconciliation record, the dispatcher records a `decision`-level WARNING (`(plan-marshall:phase-6-finalize:push) Worktree-freshness precondition overridden via --force — proceeding with status={status}`) and then allows `push` to proceed.

Append `reason={reason}` to that message on **both** refusing branches — `stale` and `undecidable` alike carry one — and append `observed_status={observed_status}` as well whenever the field is present, substituting `-` when it is not — several refusing routes read no row status at all and omit the field entirely, so test for its presence rather than assuming it. An override is precisely the moment the reason matters most: overriding a `build_killed` refusal (⛔ do NOT blind-retry — establish why it was killed) is a materially different decision from overriding a `worktree_mutated` one (re-dispatch a build), and a decision line that omits which was overridden is not an audit record. This is the same rule the `--force` escape in `phase-5-execute/SKILL.md` § Step 12a states, and the two records state it identically — a `stale` refusal always carries a `reason`, exactly as § "The `stale` `reason` MUST be carried into `display_detail`" above requires of the halting path.

## Execution

### Assert a clean tree

```bash
git -C {worktree_path} status --porcelain
```

A clean tree (empty output) is the contractual expectation — the dispatcher's commit instrumentation committed every `mutates_source: true` step's output upstream of this barrier. A non-empty result indicates an upstream contract violation (a mutating step's edits were not committed before the barrier); STOP and return an error TOON to the orchestrator naming the dirty tree, rather than pushing an inconsistent state.

### Push the converged branch

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[SKILL] (plan-marshall:phase-6-finalize) Loading plan-marshall:workflow-integration-git"
```

```text
Skill: plan-marshall:workflow-integration-git
```

Execute the git_workflow skill's **Workflow: Commit Changes** with `push: true` and NO `message`:
- `push`: true (always push in finalize)
- `worktree_path`: `{worktree_path}` resolved at finalize entry

Against the clean tree this barrier asserts, the Commit Changes workflow's Step 2 reports "No changes to commit" and falls straight through to its Step 6 push — so this barrier creates no commit; it only pushes the already-converged branch.

## Mark Step Complete

Record that this step ran on the live plan. This step's frontmatter declares no `head_dependent` fact, so it is not head-dependent and stamps no `head_at_completion` — it does NOT capture or forward `--head-at-completion`. Its re-entry decision is the dispatcher's `branch-sync-state` parity check (see `phase-6-finalize/SKILL.md` Step 3 item 1's push-specific branch, which branches on the `barrier_action` the verb publishes — a ref-absent verdict never re-fires, so a merged-and-deleted branch is never resurrected; the state→action mapping is owned by `push_barrier_action` and is not restated here), with the explicit post-PR re-invocation after a `mutates_source` step commits (item 5f § "Post-PR re-push") as the fast path.

Resolve `{branch}` — the feature branch just pushed — from the worktree HEAD:

```bash
git -C {worktree_path} rev-parse --abbrev-ref HEAD
```

Pass a `--display-detail` value alongside `--outcome done` so the output-template renderer can surface the push outcome. The detail carries the resolved `{branch}` **and the basis the freshness precondition passed on**, taken from the status member read in § "Freshness precondition" — `ledger-verified` for `fresh`, `exempt-unscanned` for `exempt`. Recording the basis is what makes a completed push auditable: without it the record is identical whether a build observed this tree or nothing was examined at all, and no reader of the finalize record can recover the difference.

On the `fresh` (ledger-verified) route:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step push --outcome done \
  --display-detail "pushed {branch} basis=ledger-verified"
```

On the `exempt` (unscanned) route, carry the gate's own `reason` as well, so the record names why no build was owed:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step push --outcome done \
  --display-detail "pushed {branch} basis=exempt-unscanned reason={reason}"
```

The `display_detail` length ceiling binds **as a caller obligation at this composing site** — the truncation is owed HERE, because nothing downstream performs it. `manage-status mark-step-done` persists whatever `--display-detail` it is handed verbatim (`_build_entry` stores the string unmodified; the handler applies no length validation and no truncation), and the renderer emits the stored value unchanged. So an overlong `reason` is not clipped by anything — it simply violates the ceiling silently, and the only place that can prevent it is the composition of the string above. Compose the detail within the ceiling before passing it: when the gate's `reason` would push the detail past it, truncate the `reason` text — never the `basis=` token, which is the field this record exists to carry. The ceiling's own value is owned by [`../../ref-workflow-architecture/standards/agents.md`](../../ref-workflow-architecture/standards/agents.md) and is not restated here.
