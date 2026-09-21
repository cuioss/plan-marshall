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
across unrelated epics. Done = the ledger lives at the shared path with no monolithic
file, a proven and time-boxed migration/removal path exists as a reusable pattern, the
call surface says `name` everywhere `slug` used to, and no sibling epic still carries an
orchestrator-substrate deliverable this epic did not absorb or explicitly decline.

> **Aspect 1 (address) landed 2026-09-21** via PLAN-01 — the epic's own ledger now lives
> here, at `.plan/orchestrator/orchestrator-refactor/`. **Aspect 3's literal framing was
> corrected by PLAN-04/ADR-023**: the settled spelling is `--epic`, not `--name` — see
> Decisions below.

## START HERE

<!-- GENERATED BLOCK — never hand-write or hand-edit this section.
     Regenerate after every queue-touching state change via:
     python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator resume-summary --slug orchestrator-refactor
     Paste the returned `summary` block verbatim between the markers (the same
     invocation also emits `ordered_queue` for the Ordered Queue section below).
     Anything a reader wants to add BY HAND goes in the annotation zone below,
     outside the markers — never inside them. -->

<!-- BEGIN GENERATED: resume-summary -->
**Resume anchor**: Ledger is clean and internally consistent (corpus, compaction, dedup all pass). The ONE remaining blocker to genuine restart-readiness: 10 uncommitted paths in .plan/orchestrator/orchestrator-refactor/ (this session's tree reconciliation) are not yet committed/pushed - operator action needed, this orchestrator does not commit unprompted. Once committed: run next to emit from PLAN-02/03/06 (all staged, dependencies satisfied).
**Phase**: orchestrating
**Inbox (derived)**: 0 queued, 13 archived
**Parked**:
- PLAN-07 (WS-04)
**Queue** (staged, in order):
1. PLAN-02 (WS-01)
2. PLAN-03 (WS-02)
3. PLAN-05 (WS-03)
4. PLAN-06 (WS-04)
- PLAN-01 (WS-01) — plan=tracked-orchestrator-store-resolver — PR #1557, #1558, #1561 — landing=landings/PLAN-01.md — status: shipped
- PLAN-04 (WS-03) — plan=identifier-vocabulary-decision — PR #1543 — landing=landings/PLAN-04.md — status: shipped
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
  function. Depends on PLAN-01/02/05/06 all landing first (all touch `orchestrator.py`).
  Operator discretion at `next`-time to keep, defer indefinitely, or drop — re-stage to
  `staged` only once every other plan in this epic has shipped, and re-derive its line
  attribution against the then-current HEAD before staging its command.

## Decisions

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

## Open Defects

- ~~PLAN-01 is stuck mid-finalize on an unreviewable diff~~ **RESOLVED 2026-09-21**: the
  split executed — #1557 (code, ~48 files, merged `8c8c7bbf`), #1558 (ledger content, 3,977
  files, `skip-bot-review`, merged `6728b738`), #1555 closed unmerged with a pointer to the
  replacements. A follow-up, #1561, landed a fix for a hardcoded-path finding the split
  missed. See `landings/PLAN-01.md`.
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
- ~~the epic's own ledger tree split across two locations~~ **RESOLVED 2026-09-21, root
  cause corrected.** PLAN-01's #1558 seeded `.plan/orchestrator/orchestrator-refactor/` as a
  ONE-TIME snapshot at merge time (`updated: 2026-09-20T10:23:39Z`), predating this epic's
  own `cleanup` pass. The two trees then diverged for TWO DIFFERENT reasons, not one: (a)
  during `cleanup` (2026-09-21, before PLAN-01 had landed), this orchestrator's script calls
  correctly resolved to the OLD `.plan/local/orchestrator/` tree, since the new resolver code
  did not exist on disk yet; (b) AFTER PLAN-01 merged into local `main` (confirmed:
  `git log HEAD` matches `origin/main` at `441cc46c8`, so the resolver code WAS current, not
  stale as first suspected), this orchestrator's OWN direct `Write`/`Edit` calls kept
  hardcoding the OLD path out of habit for several turns (the PLAN-01 landing report, the
  PLAN-03 fold, this epic.md's own Open-Defects/Watches edits) — while its SCRIPT calls
  (`queue --transition`, `--set-row`) correctly began resolving to the NEW tree the moment
  local `main` advanced, silently splitting `status.json` from everything else. **Both halves
  reconciled**: `epic.md`, `plans/PLAN-02-*.md`, `plans/PLAN-03-*.md`, `plans/PLAN-06-*.md`,
  and `landings/PLAN-01.md` copied forward into `.plan/orchestrator/orchestrator-refactor/`;
  `status.json`'s PLAN-06 transition (`parked`→`staged`) re-applied via script now that it
  resolves correctly. `logs/decision.log` deliberately stays local-only (by #1557's own
  design: `*/logs/` is re-ignored after the tracking negation, to avoid line-churn conflicts)
  — its absence from the tracked tree is expected, not a gap. **The tracked-tree write is an
  UNCOMMITTED change in the actual git working tree** — this orchestrator does not commit or
  push without being asked; flagging for the operator. Going forward, this orchestrator
  writes directly to `.plan/orchestrator/orchestrator-refactor/` only.
- **STILL OPEN as of the 2026-09-21 `cleanup` re-run — `restart-check`'s own `worktree`
  signal reports `not_ready`**: 10 paths in this epic's tracked tree remain uncommitted
  (`epic.md`, all 7 `plans/*.md`, `status.json`, `landings/PLAN-01.md`). This is the
  reconciliation above, not yet turned into a commit. This is the ONE thing standing
  between this epic and genuine restart-readiness — every other signal (`phase`,
  `running_plans`, `corpus_reconciliation`, `inbox`) reports `ready`. Committing and
  pushing is an operator decision this orchestrator does not make unprompted.
- **Operator-reported, not yet independently investigated**: `finalize-step-deploy-target` /
  `finalize-step-sync-plugin-cache` were skipped for PLAN-01's own branch, so the local
  `~/.claude/plugins/cache/plan-marshall/` may be stale relative to what just landed
  (including the resolver change itself). Run `/sync-plugin-cache` to refresh — outside this
  orchestrator's carve-out to perform itself.
- (all other defects surfaced by decompose research were folded into a staged plan's Claim
  Labels; see PLAN-01 through PLAN-07)

## Watches

- ~~`truthful-signals` PLAN-TRUTH-143 is `running`...~~ **RESOLVED 2026-09-20/21**: shipped as
  PR #1539 (merge `1c56734ce`, 2026-09-20T07:11:51Z). Both dependents unblocked: PLAN-01's
  live-plan collision cleared (it was subsequently launched — see the new Open Defect on its
  own stuck finalize, unrelated to this collision); PLAN-06 re-grounded and re-staged this
  cleanup pass (D2/D3 found moot, D5 narrowed).
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
- ~~Two "orchestrator" entities share one word in this codebase...~~ **RESOLVED by PLAN-04 /
  ADR-023 §(d) "Telling the two tiers apart at the caller surface"** — the epic is `--epic`,
  the plan is `--plan-id`; the two are different tokens on the same parser by construction.
  Retired 2026-09-20.
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
