# Epic: Orchestrator Substrate Refactor

slug: orchestrator-refactor

> Ledger document for one epic under `.plan/orchestrator/{slug}/`. The layout and
> authority contract live in the central standard — see
> `persona-plan-orchestrator/standards/orchestration-model.md`. `status.json` is the
> machine authority; any statement here that conflicts with it is stale prose.

## Vision

The orchestrator refactors its own substrate. Four bound changes: (1) relocate the
persisted ledger from the machine-local `.plan/local/orchestrator/{slug}/` tree to a
SHARED `.plan/orchestrator/{slug}/` tree (git-tracked, cross-machine), decomposing the
current large monolithic files (`status.json`, `epic.md`) into smaller self-contained
per-concern files so two machines can work the same epic in parallel without file-level
collisions; (2) design and land a self-terminating migration mechanism — old-path reads
auto-migrate to the new layout, and a dated/versioned removal task retires the
compatibility shim after a bounded window, generalized so future layout migrations reuse
the same mechanism rather than each inventing its own; (3) rename the `slug` vocabulary
to `name` across the orchestrator's call surface (CLI flags, `status.json` fields, doc
prose), and unify plan-marshall's own top-level `--plan` / `plan_id` naming onto the same
`name` vocabulary, surveying other top-level commands for the same drift; (4) survey
every sibling orchestrator epic (active and archived) for deliverables that are actually
orchestrator-tooling work (not domain work routed through an epic) and fold those into
this epic's workstreams rather than leaving orchestrator-improvement work scattered
across unrelated epics; (5, added 2026-09-23, operator-proposed) confine an epic's own
`.plan/orchestrator/{slug}/` reads/writes to a FIXED-NAME, long-lived, never-removed
per-epic git worktree instead of the primary checkout, and replace today's ad hoc
`git commit`/`git push` with explicit, monitored `land` (this epic) and `land-all` (every
active epic) verbs — landing via branch/PR/CI-wait/merge/pull-both — because frequent
unrelated orchestrator ledger commits landing directly on `main` interfere with
plan-marshall runs that inspect `main`'s state at various lifecycle phases. Done = the
ledger lives at the shared path with no monolithic file, a proven and time-boxed
migration/removal path exists as a reusable pattern, the call surface says `name`
everywhere `slug` used to, no sibling epic still carries an orchestrator-substrate
deliverable this epic did not absorb or explicitly decline, and an epic opted into
`orchestrator.use_worktree` lands its ledger changes through `land`/`land-all` rather than
ad hoc commits directly against `main`.

> **Aspect 1 (address) landed 2026-09-21** via PLAN-01 — the epic's own ledger now lives
> here, at `.plan/orchestrator/orchestrator-refactor/`. **Aspect 3's literal framing was
> corrected by PLAN-04/ADR-023**: the settled spelling is `--epic`, not `--name` — see
> Decisions below. **Aspect 5 staged 2026-09-23** as WS-05 (PLAN-09/PLAN-10) — not yet
> shipped; this epic's OWN ledger writes still land ad hoc on `main` until WS-05 ships and
> `orchestrator.use_worktree` is turned on for this epic, same as every other epic today.

## START HERE

<!-- GENERATED BLOCK — never hand-write or hand-edit this section.
     Regenerate after every queue-touching state change via:
     python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator resume-summary --slug orchestrator-refactor
     Paste the returned `summary` block verbatim between the markers (the same
     invocation also emits `ordered_queue` for the Ordered Queue section below).
     Anything a reader wants to add BY HAND goes in the annotation zone below,
     outside the markers — never inside them. -->

<!-- BEGIN GENERATED: resume-summary -->
**Resume anchor**: WS-05 staged 2026-09-23 (operator-proposed): fixed-name never-removed per-epic worktree (PLAN-09) plus land/land-all verbs (PLAN-10) to stop ad hoc orchestrator ledger commits from dirtying main. Both new, not yet emitted. PLAN-07 dependency updated to include PLAN-09/PLAN-10. Still open from the PLAN-08 landing: git-config-injection hardening routing decision (this epic vs truthful-signals), and a low-urgency mis-triage Watch. Live queue: PLAN-02/03/05/06/09/10 staged, PLAN-07 parked -- all blocked on the unchanged marketplace-wide disjointness gate (candidate_comparison_determinate=false). Next: operator decides the git-config-injection routing and/or resolves the marketplace-wide gate.
**Phase**: orchestrating
**Inbox (derived)**: 0 queued, 24 archived
**Parked**:
- PLAN-07 (WS-04)
**Queue** (staged, in order):
1. PLAN-02 (WS-01)
2. PLAN-03 (WS-02)
3. PLAN-05 (WS-03)
4. PLAN-06 (WS-04)
5. PLAN-09 (WS-05)
6. PLAN-10 (WS-05)
- PLAN-01 (WS-01) — plan=tracked-orchestrator-store-resolver — PR #1557, #1558, #1561 — landing=landings/PLAN-01.md — status: shipped
- PLAN-04 (WS-03) — plan=identifier-vocabulary-decision — PR #1543 — landing=landings/PLAN-04.md — status: shipped
- PLAN-08 (WS-04) — plan=verdict-staleness-scoping — PR #1585 — landing=landings/PLAN-08.md — status: shipped
<!-- END GENERATED: resume-summary -->

### Annotations

<!-- ANNOTATION ZONE — hand-written, and deliberately OUTSIDE the generated markers.
     A regeneration replaces only what sits BETWEEN the markers, so everything written
     here survives it. This is what makes the block above genuinely regenerable: the
     per-row notes the generator cannot produce (why a row is parked, what a running
     plan is waiting on, an operator caveat on a queue entry) have a home that a
     verbatim paste does not destroy. -->

- (none yet)

## Ordered Queue

<!-- GENERATED BLOCK — never hand-write or hand-edit the table between the markers.
     Regenerated from status.json and the staged specs: emitted as `ordered_queue` by
     orchestrator.py resume-summary --slug orchestrator-refactor (paste it verbatim after a queue change),
     and rewritten in place by the compact stage (orchestrator.py compact --slug orchestrator-refactor) at
     cleanup. Only the LIVE queue is rendered here — a shipped/landed row belongs in its
     landing record, not in the live queue. Per-row notes a reader wants to ADD go in the
     annotation zone below, outside the markers — never inside them. -->

<!-- BEGIN GENERATED: ordered-queue -->
| # | Plan | Workstream | Status | Surface (expected) |
|---|------|------------|--------|--------------------|
| 1 | PLAN-02 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/manage-status/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-status/scripts/_status_core.py; marketplace/bundles/plan-marshall/skills/manage-status/standards/status-lifecycle.md; marketplace/bundles/plan-marshall/skills/persona-plan-orchestrator/standards/orchestration-model.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/SKILL.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py; marketplace/bundles/plan-marshall/skills/plan-orchestrator/templates/epic.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/cleanup.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/decompose.md; test/plan-marshall/manage-status/test_orchestrator_store.py; test/plan-marshall/manage-status/test_orchestrator_store_orchestrator.py; test/plan-marshall/plan-orchestrator/test_orchestrator_compact.py; test/plan-marshall/plan-orchestrator/test_orchestrator_queue_add_row_concurrency.py; test/plan-marshall/plan-orchestrator/test_orchestrator_status_regression.py |
| 2 | PLAN-03 | WS-02 | staged | doc/adr/; marketplace/bundles/plan-marshall/skills/manage-config/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-config/scripts/_config_defaults.py; marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/cache_retention.py; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py; marketplace/bundles/plan-marshall/skills/script-shared/scripts/marketplace_paths.py; marketplace/bundles/pm-plugin-development/skills/plugin-doctor/references/rule-catalog.md; marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_shim_marker.py; marketplace/bundles/pm-plugin-development/skills/plugin-script-architecture/standards/shim-marker-convention.md; test/plan-marshall/marshall-steward/test_cache_retention.py; test/plan-marshall/plan-orchestrator/**; test/pm-plugin-development/plugin-doctor/test_analyze_shim_marker.py |
| 3 | PLAN-05 | WS-03 | staged | marketplace/bundles/plan-marshall/skills/manage-architecture/**; marketplace/bundles/plan-marshall/skills/manage-logging/**; marketplace/bundles/plan-marshall/skills/manage-status/**; marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/standards/argument-naming.md; marketplace/bundles/plan-marshall/skills/persona-plan-orchestrator/**; marketplace/bundles/plan-marshall/skills/plan-orchestrator/**; marketplace/bundles/plan-marshall/skills/platform-runtime/**; marketplace/bundles/plan-marshall/skills/script-shared/scripts/query/query-architecture.py; marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/doctor-marketplace.py; marketplace/bundles/pm-plugin-development/skills/tools-epic-surface-partition/**; test/plan-marshall/manage-logging/**; test/plan-marshall/manage-status/**; test/plan-marshall/plan-orchestrator/**; test/pm-plugin-development/plugin-doctor/test_doctor_marketplace.py; test/pm-plugin-development/tools-epic-surface-partition/** |
| 4 | PLAN-06 | WS-04 | staged | marketplace/bundles/plan-marshall/skills/phase-1-init/**; marketplace/bundles/plan-marshall/skills/phase-6-finalize/**; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py; marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/inbox-envelope.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/landing-payload-spec.md; marketplace/bundles/pm-plugin-development/skills/tools-epic-surface-partition/scripts/_epic_partition.py; marketplace/bundles/pm-plugin-development/skills/tools-epic-surface-partition/scripts/epic-surface-partition.py; test/plan-marshall/phase-1-init/**; test/plan-marshall/phase-6-finalize/**; test/plan-marshall/plan-orchestrator/**; test/pm-plugin-development/tools-epic-surface-partition/** |
| 5 | PLAN-07 | WS-04 | parked | marketplace/bundles/plan-marshall/skills/plan-orchestrator/SKILL.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py; test/plan-marshall/plan-orchestrator/** |
| 6 | PLAN-09 | WS-05 | staged | marketplace/bundles/plan-marshall/skills/manage-config/scripts/_config_defaults.py; marketplace/bundles/plan-marshall/skills/manage-config/standards/data-model.md; marketplace/bundles/plan-marshall/skills/persona-plan-orchestrator/standards/orchestration-model.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py; marketplace/bundles/plan-marshall/skills/tools-file-ops/**; marketplace/bundles/plan-marshall/skills/workflow-integration-git/SKILL.md; marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py; test/plan-marshall/manage-config/**; test/plan-marshall/plan-orchestrator/**; test/plan-marshall/workflow-integration-git/** |
| 7 | PLAN-10 | WS-05 | staged | marketplace/bundles/plan-marshall/skills/manage-locks/**; marketplace/bundles/plan-marshall/skills/plan-orchestrator/SKILL.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py; marketplace/bundles/plan-marshall/skills/tools-integration-ci/**; marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py; test/plan-marshall/plan-orchestrator/**; test/plan-marshall/tools-integration-ci/** |
<!-- END GENERATED: ordered-queue -->

### Queue annotations

<!-- ANNOTATION ZONE — hand-written, and deliberately OUTSIDE the generated table markers.
     A regeneration replaces only the table BETWEEN the markers, so everything written here
     survives it. This is where the per-row narrative the generator cannot derive lives — a
     sequencing caveat, a disjointness note, why a row is parked — keyed by plan id. -->

- PLAN-01 — **SHIPPED 2026-09-21** (#1557/#1558/#1561; #1555 closed unmerged, split
  executed). See `landings/PLAN-01.md`. Landed WITHOUT a redirect — see the new Open Defect
  on `_orchestrator_inbox.py`'s path-prefix gap, folded into PLAN-03.
- PLAN-02 — dependency SATISFIED (PLAN-01 shipped 2026-09-21). Emittable now, subject to
  disjointness/prep-ready checks at `next`-time. ⚠ D2 (row-status vocabulary) is LARGELY
  ALREADY DELIVERED by PLAN-TRUTH-143 (#1539) — shrinks to a doc-reconciliation task.
  D0/D1/D3/D4/D5 unaffected. Sharpest collision in the epic: shares `status.json` schema
  surface with PLAN-05 (WS-03) — do not run concurrently, land PLAN-02 first. Cross-epic
  overlap on `orchestration-model.md` with `truthful-signals` PLAN-TRUTH-151 — still `staged`
  as of 2026-09-21, no live risk yet — check its status before emitting.
- PLAN-03 — dependency SATISFIED (PLAN-01 shipped). Emittable now, subject to
  disjointness/prep-ready checks. ⚠ **Landed without a redirect** — D6 is now a retrofit; its
  most urgent sub-target (`_orchestrator_inbox.py`'s `_SOURCE_ID_RE` path-prefix gap) is
  ACTIVELY breaking orchestration routing right now, not merely a theorised risk — see Claim
  Labels. Overlaps PLAN-04 on `plugin-doctor/references/rule-catalog.md` — not caught by the
  automated matcher; sequence, do not parallelize. Disjoint from PLAN-02 and PLAN-06 — the
  one clean pair in this corpus.
- PLAN-04 — no hard dependency; decision-only. Overlaps PLAN-05 (`argument-naming.md`, PLAN-05
  depends on PLAN-04's decision) and PLAN-03 (`rule-catalog.md`, see above).
- PLAN-05 — PLAN-04 dependency satisfied (shipped #1543, folded with its execution brief
  2026-09-20). Still depends on PLAN-02 (shared `status.json`/`orchestrator.py` surface —
  land PLAN-02 first). Also overlaps PLAN-06 and PLAN-07. **New at `next`-time
  2026-09-20**: collides with a DIFFERENT currently-running live plan
  (`retrospective-aspects-publish-verdict`) on `platform-runtime/standards/contract.md` —
  re-check this plan's own state before PLAN-05 is ever emitted.
- PLAN-06 — **UNBLOCKED and re-staged 2026-09-21** (`cleanup`): PLAN-TRUTH-143 landed as
  PR #1539. Re-grounding found D2/D3 already closed at HEAD (PR #1366, with a corrected
  attribution — the spec's own guess of PR #1370 for the second gate was wrong) and dropped
  them; D5 confirmed still live today (PLAN-04's own row still carries no delivered `kind:
  landing` message) but narrowed to enforcing an existing, already-documented contract rather
  than building new machinery. D1's ownership statement now routes around `truthful-signals`
  PLAN-TRUTH-144, which is `running` as of this pass. No hard dependency; independent of
  PLAN-01's finalize block.
- PLAN-07 — **parked by design**, lowest confidence in the corpus, no external forcing
  function. Depends on PLAN-01/02/05/06/08/09/10 all landing first (all touch
  `orchestrator.py`; PLAN-08 was a behavior FIX to `stale` derivation, PLAN-09/PLAN-10 add
  real new verbs — all three must land before PLAN-07's behavior-PRESERVING split, or the
  split freezes pre-fix/pre-feature state). Operator discretion at `next`-time to keep,
  defer indefinitely, or drop — re-stage to `staged` only once every other plan in this
  epic has shipped, and re-derive its line attribution against the then-current HEAD
  before staging its command.
- PLAN-08 — **SHIPPED 2026-09-22** (#1585, merge `b5d0ef7e6`, verified as `main`'s current
  HEAD). See `landings/PLAN-08.md`. Deliverables D1-D4 shipped-as-specified or better (D2
  exceeds the spec: a full closed 6-member `staleness_basis` vocabulary, not just a named
  fallback). Both of the spec's own re-grounding claims (HYPOTHESIS + Verify-first clause)
  re-grounded and stamped `corroborated` against the merge commit. Landed via merge queue
  under an operator `barrier-ask-override` after CodeRabbit's quota timeout on the final
  loop-back HEAD — see landing record for the review-participation reasoning. Surfaced two
  follow-ups now recorded separately (git-config-injection production hardening — new Open
  Defect below; a mis-triaged review finding — new Watch below) plus 8 promoted lessons.
  Emitted originally on direct operator request ahead of `next`-slot rigor, per its own
  staging note above — that caveat is now moot; the plan shipped clean.
- PLAN-09 — **staged 2026-09-23**, WS-05 foundation. No dependency of its own (net-new
  capability). Overlaps PLAN-02/06 (`orchestrator.py`). PLAN-10 strictly depends on this.
  Carries three verify-at-outline HYPOTHESES: the worktree-verb extension shape, the
  `use_worktree` default, and the terminal-title/session-binding audit — none dictated by
  this staging, all left for outline.
- PLAN-10 — **staged 2026-09-23**, WS-05. Strictly depends on PLAN-09. Overlaps PLAN-07
  (adds real verbs to `orchestrator.py` before PLAN-07's split — PLAN-07 spec updated).
  Carries an open sequencing question for `land-all` (sequential vs bounded-parallel
  against the merge queue) and a HYPOTHESIS on whether `ci pr merge`'s existing sub-verbs
  suffice for D3 — both verify-at-outline, not decided here.

## Decisions

- 2026-09-23 — **New workstream WS-05 (Worktree-Isolated Ledger Landing) staged, PLAN-09 +
  PLAN-10, on operator request.** Operator observed that frequent orchestrator ledger
  commits landing directly on `main` interfere with plan-marshall runs checking `main`'s
  state. Proposed and staged: fixed-name, long-lived, never-removed per-epic worktree
  (PLAN-09) plus `land`/`land-all` verbs replacing ad hoc commit/push with a monitored
  branch/PR/CI-wait/merge/pull-both cycle (PLAN-10). Grounded against a research pass
  confirming: (a) no commit/push mechanism exists today (fully ad hoc); (b) the existing
  plan-worktree lifecycle (`git-workflow.py`) is reusable as a pattern but hard-coupled to
  `--plan-id`; (c) the orchestrator config block is a closed schema needing a real
  extension for `use_worktree`; (d) `phase-6-finalize`'s PR workflow is plan-bound and NOT
  reusable, but the underlying `ci` primitives (`--project-dir` addressing) are generic and
  ARE reusable directly; (e) a bounded, non-foreground CI-wait primitive already exists
  (`ci checks wait`); (f) `corpus epics` is the correct substrate for `land-all`'s sweep.
  Sequenced: PLAN-10 strictly depends on PLAN-09; both must land before PLAN-07 (behavior
  additions before a behavior-preserving split) — PLAN-07's spec updated accordingly.
  Several implementation choices deliberately left as verify-at-outline HYPOTHESES rather
  than dictated here (worktree-verb extension shape, `use_worktree` default,
  `land-all` sequential-vs-parallel) — orchestrating stages the work, not the mechanism.

- 2026-09-19 — parallelization_scope set to 2 (operator choice over the project default
  of 1). Rationale: most staged plans in this epic touch the same shared surface
  (orchestrator.py, the store-path resolver, naming across docs) so true disjoint pairs
  will be rare, but a doc-only or purely-additive plan may run alongside a code plan.
- 2026-09-20 — **PLAN-04 landed (PR #1543) with a result that CORRECTS this epic's own
  Vision.** This epic's Vision (written at `init`) framed aspect 3 as "rename the `slug`
  vocabulary to `name`". PLAN-04's actual, independently-reasoned outcome, landed as
  ADR-023, is different: `--name` is explicitly REJECTED — it names the value's *shape*
  (a form-noun spelling), the exact defect `--slug` already has — and the epic
  identifier is instead spelled `--epic` (entity-noun-first, closed suffix set
  `none`/`-id`/`-number`/`-slug`). The plan identifier is NOT collapsed into the epic's:
  `--plan-id` stays at all its sites, since epic and plan are distinct entities at
  distinct tiers. Alternatives considered and rejected by ADR-023: `--name` (form-noun,
  rejected on the rule), `--slug` (form-noun, incumbent, rejected on the same rule —
  volume favored it 23-to-4 by site count but the rule overrides volume). This
  supersedes the literal "rename to `name`" framing everywhere it appears in this
  epic's own Vision and in PLAN-05's original title; PLAN-05 is corrected to execute
  the ACTUAL decision (`--epic`), not the epic's original guess at what the decision
  would be.
- 2026-09-20 — PLAN-05 folded with PLAN-04's D4 execution brief (message
  `identifier-vocabulary-decision-001.md`): sized rename surface (31 source files / 43
  prose files — NOT the originally-cited 38/215, which the brief shows measures the
  UNCHANGED `--plan-id` incumbent surface, not the rename surface), the same-commit
  ordering constraint from `ARGUMENT_NAMING_CANONICAL_FORMS_DRIFT` (binds only 30 of 71
  canonical-forms rows; the other 41 need a manual sweep), a git-native survivor-sweep
  method, the `orchestrator queue` mode-selector redesign (not a substitution), and the
  "two plan-identifier vocabularies" finding (epic-local `PLAN-NN` ordinal vs
  plan-marshall kebab id, spelled inconsistently across orchestrator verbs — PLAN-05
  must decide per-verb before renaming). Expected Surface updated in the same act:
  added `manage-architecture/**`, `script-shared/scripts/query/query-architecture.py`,
  and `pm-plugin-development/skills/plugin-doctor/scripts/doctor-marketplace.py` (+
  its test) — new `--name`-occupant sites the brief's population derivation surfaced
  that PLAN-04's own (narrower) Expected Surface never declared. Excluded by the same
  same-act rule: `workflow-integration-sonar`'s `sonar_rest --transition` — a false
  member the brief explicitly flags, not a rename target.
- 2026-09-20 — PLAN-06 (parked) folded with `identifier-vocabulary-decision-003`: the
  orchestration-detection reconciliation defect between `phase-1-init` (does not always
  record `source_id`) and `phase-6-finalize`'s terminal-emission gate (drops
  `emit-landing` when the pointer is absent, even when the finalize dispatcher itself
  later resolves `orchestrated: true`). Measured consequence, independently confirmed:
  this epic's `queue_without_landing_count` was `7` of `7` until this reconciliation.
  Expected Surface updated in the same act: added `phase-1-init/**` and
  `phase-6-finalize/**` (the terminal-emission-orchestration-gate surface specifically).
- 2026-09-21 — **`cleanup` re-grounding pass (dispatched, 108 claims across PLAN-02/03/04/
  05/06/07 against HEAD `e8a716501`; PLAN-01 manually excluded — see Open Defects) applied
  material corrections.** PLAN-02's D2 (row-status vocabulary) is largely already delivered
  by PLAN-TRUTH-143 (#1539) — shrinks to doc reconciliation; verdicts stamped on claim-index
  10 (corroborated) and 11 (contradicted, rescoped: yes — population corrected to 509
  rows/13 ledgers). PLAN-06's blocking condition discharged (PLAN-TRUTH-143 shipped); its
  D2/D3 dropped as already-closed at HEAD (PR #1366), with an attribution correction — the
  claim-parsing-gate closure was mis-attributed to PLAN-CIS-051/#1370, actually closed by
  #1366 and #1355; D5 confirmed still live TODAY (not merely historical) but narrowed to
  enforcing an existing, already-documented `source_id` contract rather than building new
  detection machinery; verdicts stamped on claim-index 8 (corroborated), 9 (contradicted,
  rescoped: yes — attribution fix), 10 (contradicted, rescoped: yes — blocker discharged).
  PLAN-06 transitioned `parked` → `staged`. No duplication found beyond an expected
  self-match (PLAN-01's spec ↔ its own launched plan). No ambiguity findings (all 7 specs
  carry Objective/Expected Surface/Claim Labels). No Understated/Unresolvable surface
  corrections needed. Full per-claim corroboration table is the dispatched agent's own
  report, not persisted verbatim here — this entry and the two specs' own edits are the
  durable record.
- 2026-09-21 — **PLAN-01 landed** (#1557/#1558/#1561) via a split from the stuck #1555.
  Reconciled via `analyze` (paste, corroborated against `ci pr view` for all four PR numbers
  plus `git log origin/main`). Two consequential discoveries made and acted on in the same
  pass: (1) `_orchestrator_inbox.py`'s `_SOURCE_ID_RE` now hardcodes the `.plan/orchestrator/`
  prefix, reproduced directly to fail on PLAN-01's own pre-migration `source_id` — folded into
  PLAN-03 as first-party evidence, not theorised risk; (2) this epic's own ledger tree had
  split across the old and new resolver paths (see Open Defects for the corrected root-cause
  account) — reconciled, with `status.json`'s PLAN-06 transition re-applied via script once
  resolution was confirmed correct.

- 2026-09-22 — **Inbox drain: 1 message, `lessons-handling-26-09-22-01-001.md`
  (candidate-lesson, 3 items) dispositioned.** Item `2026-09-19-13-001` (channel
  address grammar mismatch — `--target-plan` mailbox routing keys off the epic-local
  `PLAN-NN` ordinal while a plan's own mailbox read keys off its kebab
  `plan_marshall_plan_id`, so delivery cannot fire in any real epic) **corroborated
  against HEAD and FOLDED into PLAN-05's D6** as first-party evidence, not theorised
  risk — see PLAN-05 Claim Labels. Items `2026-09-21-10-010` and `2026-09-21-10-012`
  **DISCARDED as already-covered**, contradicting the source epic's own
  none-already-covered disposition: -010's cited bug is fixed at
  `_cmd_lifecycle.py:183` (post PLAN-TRUTH-143/#1539); -012's principle is already
  enforced by this epic's own `candidate_comparison_determinate` fail-closed verdict
  (`orchestrate.md` Step 4), landed by the same PR.
- 2026-09-23 — **Inbox drain: `lessons-routing-001.md` (finding) — CONFIRMED, no new action.**
  `lessons-routing` flagged `2026-09-21-10-010`/`-012` as possible duplicates of content
  `truthful-signals` already promoted on 2026-09-21, asking this epic to check before staging
  or acting further. Re-verified: `manage-lessons get` returns `not_found` for both ids in the
  global corpus, and this epic's own 2026-09-22 drain (see entry above) already independently
  discarded both as already-covered — the exact outcome `lessons-routing`'s correction points
  toward. Nothing to retract or re-disposition.
- 2026-09-23 — **Inbox drain: 8 `candidate-lesson` messages from `verdict-staleness-scoping`
  (PLAN-08's own PR #1585 retrospective) — all 8 PROMOTED to the global lessons corpus,
  `2026-09-23-05-001` through `-008`.** None concern this epic's own substrate (`orchestrator.py`,
  the ledger, WS-01..WS-04); all are findings about OTHER marketplace components surfaced
  during PLAN-08's execution — `platform-runtime` (BlockScalar serialization bug in
  `chat extract-signal`, -001), `plan-retrospective` (Tier-1 gating blind to the
  delivered-vs-reduced byte gap, -002; `top_tags[5]` vs the fixed logging-gap vocabulary, -005;
  `Phase Dispatch Boundaries` structurally unrenderable, -008), `phase-6-finalize` (finalize
  cost matched execute's on a 6-file fix, -003; dispatch-audit evidence channel only 27.3%
  populated, -007), `manage-change-ledger` (37 build calls, zero ledger rows, -004), and
  `pm-plugin-development:ext-self-review-plan-marshall` (`self_review surface` exits 1 with
  empty stderr, -006). Promoted rather than folded/staged because no plan in this epic owns
  any of these components — this is the lessons-routing sweep's job to route onward from here. (9 deliverables, D0–D8) —
  no prior rationale was on record.** Verdict: proceed unsplit. D0–D4/D6–D8 are one
  coherent rename (`--slug`→`--epic`) bound by a hard same-commit ordering constraint
  (`ARGUMENT_NAMING_CANONICAL_FORMS_DRIFT`) that a split would not relax — they cannot
  land independently without breaking the gate. D5 (the `orchestrator queue`
  mode-selector collapse) is a genuinely SEPARATE decision, staged here only because it
  sits on the same subparser D1 touches, not because it shares the rename's ordering
  constraint — it is the one candidate for splitting out. Not split now: D5 also depends
  on D6 (settle first, same as D1), so a split plan would still have to sequence tightly
  behind this one, and the corpus's own disjointness gate is currently marketplace-wide
  blocked regardless (see Open Defects) — a split has no throughput benefit while that
  holds. Reconsider at outline time if the executing plan finds D5 adds unwanted coupling.

## Open Defects

- **NEW, discovered 2026-09-22 at `next`-time — the disjointness gate is currently
  MARKETPLACE-WIDE INDETERMINATE, blocking emission for every candidate in this epic
  (and presumptively every epic).** `corpus cross-check` reports
  `candidate_comparison_determinate: false`: 95 of 581 sibling-epic-spec candidates
  across 25 sibling epics, plus 1 `live_plan` entry (`NO_PLAN`), are indeterminate.
  Per the fail-closed rule in `orchestrate.md` Step 4, an indeterminate comparison
  refuses EVERY candidate rather than admitting any on an unexamined population — so
  PLAN-02/03/05/06 all pass prep-readiness (`corpus verdicts blocking_count: 0`) but
  none is emittable. Not this epic's defect to fix (the 95 indeterminate specs belong
  to 25 OTHER epics), but it fully blocks this epic's own `next` progress until either
  those specs gain declarative surfaces or the gate's global-vs-per-candidate scope is
  reconsidered. Not sized or staged — flag for the operator; possibly a
  `truthful-signals` or ecosystem-health item, not orchestrator-refactor's to own.
- **NEW, operator-reported 2026-09-22 — no owner: orchestrator-session UX/mechanism gap.**
  Three related asks surfaced during a live `status` interaction, none cleanly covered by
  an existing staged spec: (a) when already inside a `/plan-marshall:plan-orchestrator
  epic={slug}` session, suggestions should name the bare verb (e.g. "analyze" to drain the
  inbox) rather than restate the full slash-command form — the epic is already bound to the
  session; (b) after a major state change, surface the core next-verb options by name (not
  full syntax), plus any previously-emitted `/plan-marshall` command still `launched` and
  not yet operator-confirmed `running`; (c) candidate mechanism for (b): a single script call
  cross-checking `launched`-status queue rows against live plan-lifecycle state (the same
  `manage-status list`-cross-read pattern already used elsewhere to catch a queue claiming
  `staged` while the live plan has run for a day) to positively detect whether an emitted
  command was actually started, rather than relying on the operator to say so. Not sized or
  staged — none of PLAN-02/03/05/06/07 owns this cleanly (PLAN-06 is ownership consolidation
  of scattered SCHEMA/detection items, not session-presentation UX). Flag for the next
  `decompose`/`cleanup` pass to size and place (new workstream, or fold into WS-04 if the
  running-check script turns out to share surface with `orchestrator.py`'s existing verbs).
- CONFIRMED NOT a new item — operator also flagged residual `slug=` example forms (e.g. the
  `plan-orchestrator` SKILL.md Usage table's `analyze slug={slug}` line). Already inside
  PLAN-05's sized rename surface (D1 CLI-flag rename `--slug`→`--epic`, D4's ~43-file prose
  sweep including `plan-orchestrator/**`) — no separate item created.
> ↪ Relocated to `settled.md` § "PLAN-01 stuck mid-finalize on an unreviewable diff" —
> resolved 2026-09-21 via the #1557/#1558 split.
- **NEW, CRITICAL — the orchestration-detection seam hardcodes the NEW tracked path only,
  so every plan whose `source_id` was captured before PLAN-01 landed now silently fails
  `inbox detect`.** Reproduced directly, 2026-09-21:
  `orchestrator inbox detect --source-id ".plan/local/orchestrator/orchestrator-refactor/plans/PLAN-01-tracked-orchestrator-store-resolver.md"`
  (PLAN-01's OWN actual, correctly-written source_id) returns `orchestrated: false`,
  `detection: unrecognised_id`. The SAME id with the path prefix changed to
  `.plan/orchestrator/...` (the new tracked address) correctly returns `orchestrated: true`
  — isolating the cause precisely to `_orchestrator_inbox.py`'s `_SOURCE_ID_RE`, which now
  requires the `.plan/orchestrator/` prefix literally, with no acceptance of the pre-PLAN-01
  `.plan/local/orchestrator/` form. This is NOT a naming-grammar defect (the digit-suffix
  grammar itself accepts a trailing descriptive slug — `PLAN-01-tracked-orchestrator-store-resolver.md`
  parses fine once the prefix matches) and NOT unique to this epic: `truthful-signals`
  PLAN-TRUTH-144, confirmed `running` as of this epic's own `cleanup` pass, almost certainly
  carries an old-form `source_id` too and will hit the identical failure at its own finalize.
  Folded into PLAN-03 (the migration-mechanism workstream) as first-party reproduced
  evidence, not merely theorised risk — see PLAN-03's Claim Labels.
> ↪ Relocated to `settled.md` § "Epic ledger tree split across two locations" — resolved
> 2026-09-21, both halves reconciled into the tracked tree.
> ↪ Relocated to `settled.md` § "Restart-check worktree signal reported not_ready" —
> resolved 2026-09-21, PR #1566 landed, `restart-check` now reports `ready`.
- **Operator-reported, not yet independently investigated**: `finalize-step-deploy-target` /
  `finalize-step-sync-plugin-cache` were skipped for PLAN-01's own branch, so the local
  `~/.claude/plugins/cache/plan-marshall/` may be stale relative to what just landed
  (including the resolver change itself). Run `/sync-plugin-cache` to refresh — outside this
  orchestrator's carve-out to perform itself.
- (all other defects surfaced by decompose research were folded into a staged plan's Claim
  Labels; see PLAN-01 through PLAN-07)
- **NEW, from PLAN-08's landing (2026-09-23) — unrouted: git-config-injection production
  hardening, ~20 scripts repo-wide.** CodeRabbit finding `5ed953` on PR #1585: the test
  fixture's env scrub was hardened in-plan (TASK-010), but the broader hardening of
  production git seams (`orchestrator.py`'s `_git_read`, `_git_tree_diff`,
  `_resolve_anchor_sha`, and their counterparts across ~20 other scripts repo-wide) was
  deliberately held out of PLAN-08's `bug_fix` scope as a cross-cutting policy change. The
  landing's own residue note names this epic OR `truthful-signals` as candidate homes
  without picking one — `orchestrator.py` is only ONE instance of a repo-wide pattern, so
  staging it here would under-scope it, and dropping it would lose a real security finding.
  Not sized or staged — **operator routing decision needed**: stage a dedicated plan under
  this epic (WS-04, narrowly for `orchestrator.py`'s own three call sites) plus a
  `truthful-signals` item for the other ~17 sites, or route the whole thing to
  `truthful-signals` as one cross-cutting hardening plan.

## Watches

> ↪ Relocated to `settled.md` § "truthful-signals PLAN-TRUTH-143 running, blocking dependents" — resolved 2026-09-20/21, shipped as PR #1539.
- `truthful-signals` PLAN-TRUTH-151 (still `staged` as of 2026-09-21) declares
  `orchestration-model.md`, overlapping PLAN-02 — the disjointness gate cannot see this
  cross-ledger collision. No actual risk yet (nothing running there). — trigger: check before
  staging PLAN-02's emitted command.
- `truthful-signals` PLAN-TRUTH-144 is `running` (as of 2026-09-21 cleanup pass) and declares
  `landing-payload-spec.md` — the same file PLAN-06's D1 takes ownership of. PLAN-06's
  ownership statement must route around it per the running-row exclusion. — trigger: check its
  status before PLAN-06 is ever emitted; once it lands, fold its own claim on the file into
  D1's ownership record.
- `lessons-routing` PLAN-LR-04 (staged) states the same git-ignored-store durability thesis as
  this epic's WS-01 in its own Vision, but its Expected Surface is `prose` (undetectable by
  the gate). — trigger: if PLAN-LR-04 reaches for a durability substrate before WS-01 lands,
  read its spec body by hand rather than trusting the gate.
- **NEW, from PLAN-08's landing (2026-09-23), low urgency.** PLAN-08's own round-2
  verification-feedback triage mis-dispositioned finding `e79ee5` as `accepted` though its
  own `resolution_detail` shows it was a false positive — self-flagged by
  `project:finalize-step-review-retrospective`, not independently re-verified by this
  analysis. — trigger: worth a spot-check if `plan-orchestrator:verification-feedback`
  triage quality is ever audited; no action owed otherwise.
> ↪ Relocated to `settled.md` § "Two orchestrator entities share one word" — resolved by
> PLAN-04/ADR-023, retired 2026-09-20.
- **Cross-plan `2-refine` suspicious-perfect-confidence tracking** (from
  `identifier-vocabulary-decision-008`, promoted to global lessons as `2026-09-20-08-011`).
  PLAN-04 scored 100% on all six weighted refine dimensions and the Q-Gate's
  suspicious-perfect-score flag was resolved `taken_into_account` — the reviewer's own
  rationale is that an orchestrator-authored, claim-labeled staged spec is EXPECTED to score
  100%, not suspiciously so. Whether this holds is a cross-plan question this epic's own
  corpus can answer as more plans land. — trigger: as each subsequent plan in this epic lands,
  record its `2-refine` aggregate score and Q-Gate resolution here; once 3+ data points exist,
  report the rate back to the promoted global lesson.
- **Per-plan argparse-rejection rate** (from `identifier-vocabulary-decision-010`/`-011`/`-012`,
  the latter two promoted individually, `-012` discarded standalone by its own instruction).
  PLAN-04's run produced 3 independent argparse rejections across 3 unrelated notations (`ci`
  router-flag-after-verb, `merge_lock --hold-start` type mismatch, `manage-status metadata`
  missing `--field`) in one plan — denominator unknown (n=1 epic-plan by construction).
  — trigger: as each subsequent plan lands, count its `script_failure`/`argparse_rejection`
  work-log markers here; 3+ data points settle whether PLAN-04's count was high, normal, or low.
