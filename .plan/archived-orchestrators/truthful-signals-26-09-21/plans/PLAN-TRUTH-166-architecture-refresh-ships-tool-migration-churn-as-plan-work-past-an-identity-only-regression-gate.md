# PLAN-TRUTH-166: `architecture-refresh` ships tool-migration churn as plan work, past a regression gate that examines only project identity

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

## Provenance

Staged 2026-09-15 from inbox message `api-sheriff-configuration-security-hardening-001.md`, filed from a
consuming repository (`cuioss/API-Sheriff`, plan `configuration-security-hardening`, plan-marshall
`0.1.1670`) during its `default:architecture-refresh` finalize step. The consumer reverted the churn by
hand, so its PR stayed focused — the defect is that the step as documented would have shipped it. The
filer did not read plan-marshall source; the orchestrator re-grounded every claim at `7a028157e` before
staging (see Claim Labels). No staged or live spec in any epic owns this step.

## Objective

**On a consumer (or any project) whose committed architecture descriptors predate a plan-marshall
upgrade, `default:architecture-refresh` commits the upgrade's descriptor migration into whichever plan
finalizes next, attributes it to that plan in the commit subject, and clears it with a regression gate
whose green is narrower than its name.**

The observed run: no module added or removed, no descriptor input changed, yet `discover --force` dirtied
8 files — a `generation: {by: architecture, tree_sha: null}` back-fill on every module, and three curated
`api-sheriff` `key_packages` entries re-keyed from dotted package names to repo-relative paths while every
other entry in the same map stayed dotted. `descriptor-regression-check` returned `regressive: false`
because it examines `name`, `description`, and `description_reasoning` only, and the step's documented
rule — non-empty porcelain plus `regressive: false` means commit — would have shipped the lot as
`chore(architecture): refresh derived data after {plan-title}`.

Both rewrites are **intended** migrations, not bugs in `discover`: the generation back-fill is the
deliberate honest-`unknown` header for content of unrecorded vintage, and the dotted→path re-keying is
the path-is-identity migration. What is wrong is **where they land and what the gate claims about them**:

1. **Attribution.** The commit gate keys on on-disk dirtiness, not on plan-caused change, so a tool
   migration rides an unrelated plan's PR under that plan's name — and collides with consumer policy
   that reverts unrelated churn.
2. **No home for the migration.** Nothing else runs the migration as its own reconcile, so the plan PR is
   the only place it can land at all.
3. **An identity-only gate that does not say so.** `regressive: false` publishes no examined-field
   population, so it reads as whole-descriptor assurance over enrichment data (`key_packages`,
   `responsibility`) it never looked at; a partial key-vocabulary migration is invisible in its output.
4. **A documented cleanup the harness denies.** § 2b prescribes `rm -rf` on the baseline extraction as a
   plain Bash call; the consumer session's permission layer refused it.

## Deliverables

Five deliverables. D0 is a gate. The split guard was considered: all five change one finalize step and
the two scripts it calls, and D1's discriminator is the input D2 and D3 consume, so they cannot ship
apart without leaving the step half-reconciled.

**D0 — GATE: settle the attribution discriminator against the implementing source, and publish it.**
Decide how the step tells a plan-caused descriptor delta from a tool-caused one. The candidate signals
are (a) `added ∪ removed` non-empty, (b) the plan's realized footprint touching a module-discovery input,
and (c) the delta decomposing entirely into known migration classes (generation back-fill, `key_packages`
re-keying). Record which signal is authoritative, what the step does when the classes are MIXED (a
plan-caused and a tool-caused delta in one run), and what it does when the discriminator cannot decide —
which must be a named outcome, never a silent commit.

**D1 — The Tier-0 commit gate commits only the plan-attributable delta.** A tool-migration-only delta is
NOT committed into the plan's branch: the step restores the architecture tree from a snapshot IT took
before `discover --force` (never `git restore` / `git checkout --` over files that may have been dirty
beforehand), records a named outcome in the decision log, and surfaces it in `--display-detail`, naming
the reconcile path D2 provides. The commit subject no longer attributes tool churn to the plan.

**D2 — A migration reconcile path that owns tool-caused descriptor churn.** A sanctioned surface that
runs the descriptor migration as its own commit (`chore(architecture): migrate descriptors to {version}`
or equivalent), for both meta and consumer projects — most naturally a `marshall-steward` `upgrade`
sub-step, since the upgrade flow is the one-flow post-change reconciliation. Outline confirms the host.

**D3 — `descriptor-regression-check` publishes what it examined, and sees enrichment data.** The output
carries its examined-field population so `regressive: false` states which fields it was computed over.
The check additionally compares the per-module `enriched.json` curated fields against the baseline: a
`key_packages` entry lost or a curated description blanked is regressive; a dotted→path re-keying with a
byte-identical description is a reported migration (not regressive); a map left in mixed key vocabulary
reports the unresolved keys. `discover`'s own TOON reports the unresolved-migration count it today emits
only as a WARNING log line.

**D4 — § 2b's baseline cleanup is an executor-mediated, harness-permitted operation.** Replace the plain
`rm -rf` with a deterministic call that does not depend on a shell deletion being allowed (an executor
verb, a `manage-files`-style cleanup, or a fresh per-run extraction root that needs no clearing). Cross-
reference `PLAN-TRUTH-159`'s D2 lint-time detector, which flags documented Bash invocations an installed
hook denies but is scoped to `.claude/skills/` — note whether this `marketplace/bundles/` site falls
inside its population or outside it.

## Claim Labels

- OBSERVED: the Tier-0 commit gate commits whenever `git status --porcelain .plan/project-architecture` is
  non-empty and `descriptor-regression-check` returns `regressive: false`, with the subject `chore(architecture): refresh derived data after {plan-title}` — `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/architecture-refresh.md` § 3c / 3c.5 / 3d (lines 155–211), read at `7a028157e`.
- OBSERVED: `descriptor-regression-check` examines exactly `name`, `description`, and
  `description_reasoning` of `_project.json`, reads no `enriched.json`, and returns only `status` /
  `regressive` / `violations` with no examined-field population — `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_handlers.py` § `cmd_descriptor_regression_check` (lines 1525–1605), read at `7a028157e`.
- OBSERVED: `discover --force` back-fills `unknown_generation()` (`{by: architecture, tree_sha: None}`)
  onto every existing module document that carries no header, and migrates dotted `key_packages` keys to
  path keys wherever the derived `packages` bridge resolves, keeping unresolved keys dotted and reporting
  them only through a WARNING log entry — `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_manage.py` § `api_discover` (lines 746–757) and § `_migrated_key_packages` (lines 581–639), read at `7a028157e`.
- OBSERVED — a premise of the source message REFUTED at staging: `tree_sha: null` is NOT a confident-but-
  empty stamp. `_architecture_core.py` § `unknown_generation` documents it as the deliberate honest
  header for content of unrecorded vintage, which `derive_freshness` maps to `unknown`, never `fresh`.
  This plan does not change the header; it only stops the back-fill landing under an unrelated plan's
  name (D1/D2).
- OBSERVED: `marshall-steward`'s `upgrade` stage plan carries no architecture or descriptor-migration
  sub-step — `marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/upgrade.py` contains no
  `architecture` or `discover` token, read at `7a028157e`. D2's reconcile path does not exist today.
- OBSERVED: § 2b prescribes `rm -rf {worktree_path}/.plan/temp/architecture-baseline …` as a plain Bash
  call — `architecture-refresh.md` line 93, read at `7a028157e`.
- HYPOTHESIS: the consumer's permission layer denying that `rm -rf` is a general property of consumer
  sessions rather than one session's configuration — confirm/refute at
  `marketplace/bundles/plan-marshall/skills/platform-runtime/standards/pretooluse-enforcement.md` § the
  rule set, and the consumer permission defaults `tools-permission-doctor` seeds (verify-at-outline).
- HYPOTHESIS: the mixed-vocabulary `key_packages` map (3 entries path-keyed, the rest dotted) arises
  because the unmigrated keys had no derived `packages` bridge entry, not from a second defect — confirm/
  refute at `_architecture_core.py` § `migrate_key_packages` against the Java extension's derived
  `packages` map for a multi-package module (verify-at-outline).
- HYPOTHESIS: D0's signal (b), the plan's realized footprint, is available at order 10 — confirm/refute at
  `marketplace/bundles/plan-marshall/skills/manage-references/scripts/manage-references.py` §
  `compute-footprint` and its base-ref resolution after `finalize-step-sync-baseline` (verify-at-outline).

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/architecture-refresh.md` — the commit gate, the regression-gate branch, and § 2b (D1, D3, D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_handlers.py` — `cmd_descriptor_regression_check` (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_manage.py` — `api_discover` unresolved-migration reporting (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-architecture/standards/client-api.md` — the `discover` and `descriptor-regression-check` contracts (D3)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/upgrade.py` and `marketplace/bundles/plan-marshall/skills/marshall-steward/standards/upgrade-flow.md` — the D2 reconcile host (verify-at-outline)
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_architecture_refresh.py` — commit-gate coverage (D1)
- OBSERVED: `test/plan-marshall/manage-architecture/test_descriptor_regression_check.py` — regression-check coverage (D3)
- HYPOTHESIS: `test/plan-marshall/marshall-steward/` — coverage for the D2 sub-step (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none.
- Adjacent, not merged: `PLAN-TRUTH-159` (a documented finalize-step command the repo's hook denies) —
  same archetype as D4 on a different surface (`.claude/skills/`); D4 records the cross-reference rather
  than widening either plan.
- Adjacent, not merged: the same consumer run's sibling message
  `api-sheriff-pro-forma-integration-test-fixes-001.md` (stale local base ref after
  `finalize-step-sync-baseline`) touches the footprint base D0's signal (b) would read; if it is staged
  first, D0 consumes its fix rather than re-deriving the base.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-166-architecture-refresh-ships-tool-migration-churn-as-plan-work-past-an-identity-only-regression-gate.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
