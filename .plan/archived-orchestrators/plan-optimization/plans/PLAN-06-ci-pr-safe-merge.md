# PLAN-06: ci-pr-safe-merge (provider-agnostic safe-merge verb)

epic: plan-optimization
workstream: WS-02

> Staged plan spec — one shippable unit, ready for `/plan-marshall` hand-off. This spec was
> RE-CONSTITUTED 2026-07-18 after the original parked `ci-pr-safe-merge` plan directory was found
> to have silently vanished from this checkout (not active, not orphaned, not archived — the
> refine/outline state was never persisted here or was later removed). The design below is the
> SETTLED design carried in memory; it is NOT to be re-litigated. This spec exists to persist that
> seed in the epic tree (durable), so a fresh `action=init` converges fast.

## Objective

Provide a provider-agnostic "safe-merge" path so a PR that reaches a stuck/blocked merge state can
be landed deterministically instead of stalling. Today the merge step can hang on a blocked state
with no sanctioned recovery; this plan adds a single readiness-poll-then-merge verb with a bounded,
opt-in admin fallback. Provider-agnostic surface (GitHub + GitLab) with a GitHub-only admin
fallback where the platform supports it.

## Settled Design (do NOT re-litigate — source: memory, operator-confirmed)

1. **New provider-agnostic `ci pr safe-merge` verb** — polls both-provider readiness, then merges.
   (The `ci pr safe-merge` subcommand already exists in the ci surface skeleton — reconcile the
   implementation against the settled design; the verb name is fixed.)
2. **Dedicated `admin_merge_on_stuck_state` knob on `default:branch-cleanup`** — opt-in; governs
   whether the admin fallback may fire. Off by default (safe).
3. **GitHub-only admin fallback on a stuck/blocked state** — when readiness polling confirms a
   genuinely stuck state AND the knob is enabled, use the GitHub admin merge path. GitLab has no
   equivalent fallback (readiness-poll only).
4. **Both-provider readiness polling** — the poll-for-readiness leg is provider-agnostic; only the
   stuck-state fallback is GitHub-specific.

## Deliverables

{Converge the exact deliverable cut at refine/outline against the settled design above. Expected
shape (confirm at outline, do not pre-freeze):}

1. `ci pr safe-merge` verb — readiness poll + merge, provider-agnostic, in `tools-integration-ci`.
2. `admin_merge_on_stuck_state` config knob on `default:branch-cleanup` (schema + defaults + docs).
3. GitHub-only admin fallback on confirmed stuck state, gated by the knob.
4. Wire finalize's merge step to the new verb; retire any ad-hoc stuck-state handling it replaces.
5. Tests: stuck-state repro + fallback-fires-only-when-enabled + GitLab-has-no-fallback.

## Expected Surface

- `plan-marshall:tools-integration-ci:ci` scripts (the `pr safe-merge` verb) + `workflow-integration-github` / `workflow-integration-gitlab` providers
- `default:branch-cleanup` config surface (`manage-config` schema + `_config_defaults` + `configuration.adoc`)
- phase-6-finalize merge-step wiring (small)

## Dependencies and Sequencing

- Depends on: none (design settled; re-init fresh).
- Overlaps with: **PLAN-04 (docs-contract-consistency)** touches the `auto_merge_after_ci` /
  `*_without_asking` config-knob DOCS — adjacent to this plan's `admin_merge_on_stuck_state` knob
  doc, but PLAN-04 is doc-prose and this is code+schema. Mostly disjoint; second finisher rebases
  if both touch `configuration.adoc`. Disjoint from PLAN-05 (terminal-title).

## Hand-Off Command

Original parked plan vanished — this is a FRESH init seeded from the settled design (not a resume):

```text
/plan-marshall action=init task="Implement a provider-agnostic ci pr safe-merge path. SETTLED DESIGN (do not re-litigate): (1) new provider-agnostic `ci pr safe-merge` verb that polls both-provider readiness then merges; (2) dedicated `admin_merge_on_stuck_state` knob on default:branch-cleanup, opt-in/off-by-default; (3) GitHub-only admin merge fallback on a confirmed stuck/blocked state, gated by that knob; (4) both-provider readiness polling, GitLab has readiness-poll only (no admin fallback). The prior parked plan's refine/outline state was lost (directory vanished from checkout); re-converge fast from this seed. Seed spec: .plan/local/orchestrator/plan-optimization/plans/PLAN-06-ci-pr-safe-merge.md"
```

## Status Trail

- plan_marshall_plan_id: {set at launch — will be a fresh feature/{plan_id}, NOT a resume}
- pr: {set when the PR opens}
- landing: {set when landings/PLAN-06.md is recorded}
