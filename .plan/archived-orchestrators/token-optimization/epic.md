# Epic: Token-Optimization Roadmap

slug: token-optimization

> Ledger document for one epic under `.plan/local/orchestrator/{slug}/`. The layout and
> authority contract live in the central standard — see
> `persona-marshall-orchestrator/standards/orchestration-model.md`. `status.json` is the
> machine authority; any statement here that conflicts with it is stale prose.

## Vision

Drive the plan-marshall per-plan token cost down from the audited ~73%-overhead / ~1.0M-token floor to the armed targets (surgical ≤1.2M, single_module ≤1.5M, multi_module ≤2.5M) by fixing dispatch multiplication and finalize-wait cost drivers — then land the bounded post-roadmap tail (finalize integrity, architecture/manifest gaps, tooling/metrics debt, standards folding, and the plan-server/orchestration capability track). The CORE cost-driver roadmap is CLOSED (finale plan-8 #899, 2026-07-15; frozen in `history.md`); this epic now orchestrates the remaining tail as workstreams WS-02 through WS-06.

## START HERE

<!-- GENERATED BLOCK — never hand-write or hand-edit this section.
     Regenerate after every queue-touching state change via:
     python3 .plan/execute-script.py plan-marshall:marshall-orchestrator:orchestrator resume-summary --slug token-optimization
     Paste the returned block verbatim between the markers. -->

<!-- BEGIN GENERATED: resume-summary -->
**Resume anchor**: epic closed - see history.md
**Phase**: orchestrating
**Queue** (staged, in order):
- (empty)
- PLAN-01 (WS-02) — PR 914 — status: shipped
- PLAN-02 (WS-02) — PR 920 — status: shipped
- PLAN-03 (WS-03) — PR 917 — status: shipped
- PLAN-04 (WS-03) — PR 916 — status: shipped
- PLAN-05 (WS-05) — PR 918 — status: shipped
- PLAN-06 (WS-04) — PR 921 — status: shipped
- PLAN-07 (WS-02) — PR 930 — status: resolved
- PLAN-08 (WS-04) — PR 919 — status: shipped
- PLAN-09 (WS-04) — PR 922 — status: shipped
- PLAN-10 (WS-05) — PR 913 — status: shipped
- PLAN-11 (WS-04) — PR 931 — status: resolved
- PLAN-12 (WS-06) — plan=marshall-orchestrator — PR 915 — status: shipped
- PLAN-13 (WS-06) — PR 923 — status: shipped
- PLAN-14 (WS-06) — plan=ci-pr-safe-merge — PR 929 — status: resolved
- PLAN-15 (WS-06) — status: resolved
<!-- END GENERATED: resume-summary -->

## Ordered Queue

Status mirrors status.json (`plans[].status`) — reconcile from status.json to here, never the reverse. Every P-plan spec lives in `.plan/plan-optimization/plans/` (the frozen-doc rule keeps them there); the Notes column carries the launch command.

| # | Plan | Workstream | Status | Surface (expected) | Notes |
|---|------|------------|--------|--------------------|-------|
| 1 | PLAN-01-p1-finalize-commit-integrity | WS-02 | launched | phase-6-finalize steps, workflow-integration-git | `/plan-marshall task="implement .plan/plan-optimization/plans/plan-finalize-commit-integrity.md"` |
| 2 | PLAN-02-p2-unified-finalize-triage | WS-02 | staged | phase-6-finalize triage flow | Serializes AFTER PLAN-01 (shared phase-6 files) — `/plan-marshall task="implement .plan/plan-optimization/plans/plan-unified-finalize-triage.md"` |
| 3 | PLAN-03-p3-architecture-resolution | WS-03 | launched | manage-architecture, build_map, skills_by_profile | `/plan-marshall task="implement .plan/plan-optimization/plans/plan-architecture-resolution.md"` |
| 4 | PLAN-04-p4-execution-manifest-gaps | WS-03 | launched | manage-execution-manifest, compose | `/plan-marshall task="implement .plan/plan-optimization/plans/plan-execution-manifest-gaps.md"` |
| 5 | PLAN-05-p5-consumer-domain-standards | WS-05 | launched | pm-dev-java-cui standards docs | Best parallel candidate (pure docs surface) — `/plan-marshall task="implement .plan/plan-optimization/plans/plan-consumer-domain-standards.md"` |
| 6 | PLAN-06-p6-small-tooling-batch | WS-04 | staged | misc small tooling, manage-lessons store guard | `/plan-marshall task="implement .plan/plan-optimization/plans/plan-small-tooling-batch.md"` |
| 7 | PLAN-07-p7-docs-contract-consistency | WS-02 | staged | concept/config docs | Sequences after PLAN-01/PLAN-02 — `/plan-marshall task="implement .plan/plan-optimization/plans/plan-docs-contract-consistency.md"` |
| 8 | PLAN-08-p8-merge-queue-squash-reconcile | WS-04 | launched | tools-integration-ci merge path | `/plan-marshall task="implement .plan/plan-optimization/plans/plan-merge-queue-squash-reconcile.md"` |
| 9 | PLAN-09-p9-metrics-corpus-integrity | WS-04 | staged | manage-metrics attribution | `/plan-marshall task="implement .plan/plan-optimization/plans/plan-metrics-corpus-integrity.md"` |
| 10 | PLAN-10-ss-survivor-sweep | WS-05 | launched | design-first (ADR on git-native fingerprint substrate) | `/plan-marshall task="implement .plan/plan-optimization/plans/plan-survivor-sweep.md"` |
| 11 | PLAN-11-tt-terminal-title-stale-build-busy | WS-04 | staged | manage-status title_token lifecycle | Re-scope at outline: BK #912 state-gate-first wake may have dissolved the dangling case — `/plan-marshall task="implement .plan/plan-optimization/plans/plan-terminal-title-stale-build-busy.md"` |
| 12 | PLAN-12-marshall-orchestrator-skill | WS-06 | launched | marketplace_paths.py (D0), new skill tree | Running as plan `marshall-orchestrator` (this migration is its D10 dogfood) |
| 13 | PLAN-13-rung1-global-home-root | WS-06 | parked | marketplace_paths.py resolver | Sequenced BEHIND PLAN-12's D0 (same resolver surface); restart contract in `plans/plan-global-home-root.md` — extend D0 with a home-anchored variant |
| 14 | PLAN-14-ci-pr-safe-merge | WS-06 | parked | tools-integration-ci safe-merge | Parked at 3-outline — resume `/plan-marshall plan=ci-pr-safe-merge` |
| 15 | PLAN-15-consumer-upgrade-migrations | WS-06 | parked | consumer repos (not this repo) | Deferred by operator 2026-07-16; order when picked up: API-Sheriff first, nifi LAST (busy at loop-back) |

## Decisions

- 2026-07-16 — Migrated the hand-run roadmap ledger (`.plan/plan-optimization/HANDOVER.md` + `plans/` + `HISTORY.md` + memory landing topics) into this epic as the marshall-orchestrator D10 dogfood. Classification: CLOSED core roadmap → `history.md` (WS-01); the 9 P-plans + SS + TT + the plan-server/orchestration track → workstreams WS-02..WS-06 with the queue above.
- 2026-07-16 — P-plan spec docs stay in `.plan/plan-optimization/plans/` (the source ledger's frozen-doc rule); this epic's `plans/` dir holds no duplicate specs — queue rows point at the canonical docs. Lean over copy.
- 2026-07-16 — Shipped-plan landing analyses are already frozen in `.plan/plan-optimization/HISTORY.md` Snapshots 1-3; no retroactive `landings/` records are synthesized. `landings/` starts fresh with the next ship analyzed under this epic.
- 2026-07-16 — Parallel set honored from the source ledger: P3/P4/P5/P6/P8/P9 disjoint; P1→P2 serialize; P7 after P1/P2; SS independent.

## Open Defects

Un-planned defects carried from HANDOVER §5 (everything that graduated to a P-plan lives in that plan's spec, not here):

- `prepare_execute` re-entry-guard idempotency false negative (nifi live 2026-07-16; lesson 2026-07-16-16-002) — candidate: fold into PLAN-01's re-entry surface at its outline, or own micro-fix.
- Leaf-backgrounding compose-time guard does NOT cover the INITIAL phase-5 envelope call site (#897; recurrence on 2026-06-24-18-001) — extend the plan-6 D6 guard to the initial-envelope dispatch site.
- Dispatched-leaf cannot sub-dispatch its adversarial validator — self-review ran INLINE 6 passes = 1.44M on #893 (52% of plan); align step body/topology docs and give the leaf-hosted validator a sanctioned yield-to-sibling path. Plan candidate.
- Tier-1 recipe floor rejects pre-diagnosed surgical requests (cold post-#875; 2 wrongful rejections) — severity LOW, signal_set covers; recalibrate or retire on more data.
- Self-review surfacer blind to template STRING-CONSTANT pairs (recurrence #3) — plan-worthy on next recurrence.
- Headline finding #3 ("refine is mostly confirm-work") has SIX consecutive counter-examples (#911 definitive) — do NOT act on it without re-deriving against premise-validity rather than confidence.

## Watches

- DATED 2026-07-17 (HARD): Gemini review-bot sunset — decide `enabled_bots` / replacement before then (#899 proved Gemini+CodeRabbit complementary).
- Finalize-wait D6 delta (#899 Cluster B): confirm the before/after reduction is real (not re-shaped waits) on the next few post-#899 landings.
- Consumer upgrade-reminder gap: steward `check-staleness` is pull-only and measures installed-version drift, not upstream availability — no unattended "run upgrade" signal exists (candidate small item, unowned).
- Sibling-collision detector: 1 confirmed same-file miss; armed live test fired clean at #893 — watch stays open.
- CHECK_ERA is a serial conflict point across parallel landings — era-stamp-fill should become append-safe.
- base_branch init-detection gap + silent reconcile heal (LOW) — detect the remote default at init/steward; make the heal loud.
- plan-17 barrier standing check: any merge with unread bot comments is a REGRESSION.
- Worktree staleness (3 graceful observations) — first non-graceful occurrence promotes to a plan.
- Merge lock not released at archive (1x, #879) — recurrence folds as release-on-archive-barrier fix.
- Outline silently drops a spec deliverable (1x, #863) — candidate Q-Gate check.
- Post-remediation re-verify leg falls off the CI abstraction (1x + adjacent consumer class) — plan-worthy on a meta recurrence.
- Run-session bookkeeping drift (1 skip vs 2 full compliance) — wire lifecycle steps into the manifest on a second skip.
