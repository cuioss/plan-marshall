# Epic: Orchestrator Substrate Refactor

slug: orchestrator-refactor

> Ledger document for one epic under `.plan/local/orchestrator/{slug}/`. The layout and
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

## START HERE

<!-- GENERATED BLOCK — never hand-write or hand-edit this section.
     Regenerate after every queue-touching state change via:
     python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator resume-summary --slug orchestrator-refactor
     Paste the returned `summary` block verbatim between the markers (the same
     invocation also emits `ordered_queue` for the Ordered Queue section below).
     Anything a reader wants to add BY HAND goes in the annotation zone below,
     outside the markers — never inside them. -->

<!-- BEGIN GENERATED: resume-summary -->
**Resume anchor**: PLAN-01 launched, awaiting its landing. parallelization_scope=2 has 1 slot free, but PLAN-02/03/05 all depend on PLAN-01 actually landing (not just launching), so nothing else is emittable yet.
**Phase**: orchestrating
**Inbox (derived)**: 0 queued, 13 archived
**Parked**:
- PLAN-06 (WS-04)
- PLAN-07 (WS-04)
**Queue** (staged, in order):
1. PLAN-02 (WS-01)
2. PLAN-03 (WS-02)
3. PLAN-05 (WS-03)
- PLAN-01 (WS-01) — status: launched
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
| 1 | PLAN-01-tracked-orchestrator-store-resolver | WS-01 | launched | `.gitignore`; `doc/adr/`; `persona-plan-orchestrator/standards/orchestration-model.md`; `plan-orchestrator/scripts/orchestrator.py`; `script-shared/scripts/marketplace_paths.py`; `tools-file-ops/SKILL.md`; `tools-file-ops/scripts/file_ops.py`; tests |
| 2 | PLAN-02-ledger-decomposition-and-row-vocabulary | WS-01 | staged | `manage-status/SKILL.md`; `manage-status/scripts/_status_core.py`; `manage-status/standards/status-lifecycle.md`; `persona-plan-orchestrator/standards/orchestration-model.md`; `plan-orchestrator/SKILL.md`; `plan-orchestrator/scripts/orchestrator.py`; `plan-orchestrator/templates/epic.md`; `plan-orchestrator/workflow/cleanup.md`; `plan-orchestrator/workflow/decompose.md`; tests |
| 3 | PLAN-03-self-terminating-layout-migration | WS-02 | staged | `doc/adr/`; `manage-config/SKILL.md`; `manage-config/scripts/_config_defaults.py`; `marshall-steward/scripts/cache_retention.py`; `script-shared/scripts/marketplace_paths.py`; `plugin-doctor/references/rule-catalog.md`; `plugin-doctor/scripts/_analyze_shim_marker.py`; `plugin-script-architecture/standards/shim-marker-convention.md`; tests |
| 4 | PLAN-05-identifier-rename-execution | WS-03 | staged | `manage-architecture/**`; `manage-logging/**`; `manage-status/**`; `persona-plan-marshall-agent/standards/argument-naming.md`; `persona-plan-orchestrator/**`; `plan-orchestrator/**`; `platform-runtime/**`; `script-shared/scripts/query/query-architecture.py`; `plugin-doctor/scripts/doctor-marketplace.py`; `tools-epic-surface-partition/**`; tests |
| 5 | PLAN-06-orchestrator-mechanism-intake | WS-04 | parked | `phase-1-init/**`; `phase-6-finalize/**`; `plan-orchestrator/scripts/_orchestrator_inbox.py`; `plan-orchestrator/scripts/orchestrator.py`; `plan-orchestrator/standards/inbox-envelope.md`; `plan-orchestrator/standards/landing-payload-spec.md`; `tools-epic-surface-partition/scripts/_epic_partition.py`; `tools-epic-surface-partition/scripts/epic-surface-partition.py`; tests |
| 6 | PLAN-07-orchestrator-script-decomposition | WS-04 | parked | `plan-orchestrator/SKILL.md`; `plan-orchestrator/scripts/`; `plan-orchestrator/scripts/_orchestrator_inbox.py`; `plan-orchestrator/scripts/orchestrator.py`; tests |
<!-- END GENERATED: ordered-queue -->

### Queue annotations

<!-- ANNOTATION ZONE — hand-written, and deliberately OUTSIDE the generated table markers.
     A regeneration replaces only the table BETWEEN the markers, so everything written here
     survives it. This is where the per-row narrative the generator cannot derive lives — a
     sequencing caveat, a disjointness note, why a row is parked — keyed by plan id. -->

- PLAN-01 — must land before PLAN-02 and PLAN-03 (both depend on its resolver tier).
  ~~Blocked by a live collision with running `truthful-signals` PLAN-TRUTH-143~~
  **RESOLVED 2026-09-20**: PLAN-TRUTH-143 landed as PR #1539 (merge commit `1c56734ce`).
  Emitted this round.
- PLAN-02 — depends on PLAN-01. Sharpest collision in the epic: shares `status.json` schema
  surface with PLAN-05 (WS-03) — do not run concurrently, land PLAN-02 first. Cross-epic
  overlap on `orchestration-model.md` with `truthful-signals` PLAN-TRUTH-151 (staged) — check
  its status before emitting.
- PLAN-03 — depends on PLAN-01 (shares `marketplace_paths.py`). Overlaps PLAN-04 on
  `plugin-doctor/references/rule-catalog.md` — not caught by the automated matcher; sequence,
  do not parallelize. Disjoint from PLAN-02 and PLAN-06 — the one clean pair in this corpus.
- PLAN-04 — no hard dependency; decision-only. Overlaps PLAN-05 (`argument-naming.md`, PLAN-05
  depends on PLAN-04's decision) and PLAN-03 (`rule-catalog.md`, see above).
- PLAN-05 — PLAN-04 dependency satisfied (shipped #1543, folded with its execution brief
  2026-09-20). Still depends on PLAN-02 (shared `status.json`/`orchestrator.py` surface —
  land PLAN-02 first). Also overlaps PLAN-06 and PLAN-07. **New at `next`-time
  2026-09-20**: collides with a DIFFERENT currently-running live plan
  (`retrospective-aspects-publish-verdict`) on `platform-runtime/standards/contract.md` —
  re-check this plan's own state before PLAN-05 is ever emitted.
- PLAN-06 — **BLOCKED**, parked rather than staged: `truthful-signals` PLAN-TRUTH-143 (running)
  declares the widest orchestrator surface of any live spec anywhere in the sibling corpus.
  Per the running-row exclusion (orchestration-model.md § Cleanup Contract), do not re-scope
  it. Re-ground PLAN-06 against HEAD once PLAN-TRUTH-143 lands, then re-stage to `staged`.
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

## Open Defects

- (none — every defect surfaced by decompose research was folded into a staged plan's Claim
  Labels; see PLAN-01 through PLAN-07)

## Watches

- `truthful-signals` PLAN-TRUTH-143 is `running` and declares the widest orchestrator surface
  of any live spec in the sibling corpus — PLAN-06 is blocked on it landing, **and (found at
  `next`-time, 2026-09-19) it ALSO collides with PLAN-01**: `corpus cross-check` reports a
  `live_plan` overlap on `orchestration-model.md` and `orchestrator.py`. PLAN-01 is therefore
  sequenced behind PLAN-TRUTH-143 too, not just PLAN-06. — trigger: check its status at every
  `status`/`next` invocation of this epic until it ships, then re-run `next` to unblock PLAN-01.
- `truthful-signals` PLAN-TRUTH-151 (staged) declares `orchestration-model.md`, overlapping
  PLAN-02 — the disjointness gate cannot see this cross-ledger collision. — trigger: check
  before staging PLAN-02's emitted command.
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
