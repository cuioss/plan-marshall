# PLAN-05: Execute ADR-023 — rename the epic identifier to `--epic`

epic: orchestrator-refactor
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-05-identifier-rename-execution.md` and is queued in the epic
> `status.json` `plans[]` field. The orchestrator EMITS the command below; it never launches
> the plan inline. This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer
> and carries no brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.
>
> **Revision note (2026-09-20):** PLAN-04 landed as PR #1543 and renamed nothing. Its
> decision, ADR-023, is **entity-noun-first with a closed suffix set** — the epic
> identifier becomes `--epic`, NOT `--name` (the epic's own original Vision framing).
> This spec is FOLDED with PLAN-04's D4 execution brief (inbox message
> `identifier-vocabulary-decision-001.md`), which sizes the real surface, derives the
> ordering constraint, and supplies a survivor-sweep method. Everything below reflects
> the folded state; nothing here is the pre-fold guess.

## Objective

Execute ADR-023's decision for the EPIC-NAME half of the rename only: `--slug` (2 scripts,
`orchestrator.py` and `platform_runtime.py`), `--plan-id` carrying the epic name
(`manage-status`, `manage-logging`, `--store orchestrator`), and `--epic` (already correct in
`epic-surface-partition.py`) all become `--epic` — CLI flags, the `status.json`
`plans[].slug` PLAN-ROW field stays a distinct concept and is untouched here (it is the
plan's own kebab key, not the epic's), doc prose, and template placeholders. The
canonical-forms table and the enforcing `ARGUMENT_NAMING_*` rule cluster are kept in
agreement at every commit — never a `rename-then-fix-docs` sequence, which fails the
build-failing `ARGUMENT_NAMING_CANONICAL_FORMS_DRIFT` gate on any partial landing.

Also folded in (same rename decision, different site): three of `--name`'s four occupants
(`architecture enrich module --name`, `query-architecture ... --name`, `doctor-marketplace
analyze|fix --name`) rename to `--module` / `--component` per ADR-023 §(c). The fourth
(`run_config commit-trailer set --name`, a co-author name) is explicitly KEPT — it is not
an entity identity.

The fleet-wide `--plan-id` rename (≥38 scripts declaring the literal, 215 doc files — the
UNCHANGED incumbent surface ADR-023 keeps at all 282 sites) is explicitly NOT in this plan.

## Deliverables

1. **D0 — the reference set**, derived from `git ls-files` (the tracked-and-not-ignored
   universe), partitioned by marshalling family (A: argparse declaration, B:
   Python-marshalled argv/literal/`ns.attr`, C: prose-marshalled), per the sized surface
   in Claim Labels. Re-derive at this plan's own HEAD — the sizing below is PLAN-04's,
   already known to be stale the moment PLAN-04's own diff landed.
2. **D1 — the CLI surfaces renamed together**, one commit per script whose argparse
   changes (the `add_argument` edit, `ns.attr`/argv-literal updates in that script's own
   module, that script's tests, its `## Canonical invocations` block, and any
   canonical-forms row the drift rule cross-checks for it — see D3 for which 30 of 71
   rows that is). `orchestrator queue` is the exception and gets its own commit (D5).
3. **D2 — the `status.json` field**, if this rename touches any stored field (it should
   not — the epic identifier is a path/argument concept, not a stored JSON field; confirm
   this at outline rather than assuming), behind PLAN-03's migration mechanism.
4. **D3 — the canonical-forms table amended in lock-step with D1**, scoped to the 30 of
   71 rows the drift parser actually cross-checks (a lone backticked third cell) — those
   MUST move in the same commit as their script. The other 41 (three `manage-*` rows with
   trailing `(alias: …)` prose, and the three two-column tables — `git-workflow` 9 rows,
   `ci` 22 rows, `doctor-marketplace` 7 rows) are outside the drift parser's row shape and
   may move in a separate commit — but MUST still move, since they rot silently with no
   gate to catch a miss.
5. **D4 — the doc sweep** over the ~43 prose-marshalled files (not the originally-cited
   19 — that figure predates the D0 population derivation), with the two-entity
   disambiguation (epic-tier orchestrator vs. plan-lifecycle orchestrator) applied
   wherever the prose says "orchestrator", per ADR-023 §(d).
6. **D5 — `orchestrator queue`'s mode-selector redesign, as its own commit.** `--transition`,
   `--set-row`, `--add-row` are mutually exclusive mode selectors that each currently
   carry a plan id; renaming all three to a single `--plan-id` is a duplicate
   option-string `ArgumentError` at parser construction and would erase the mode.
   Separate identity from mode: promote the mode to a verb (`queue transition` /
   `queue set-row` / `queue add-row`, each taking `--plan-id`), or keep one explicit
   mode flag alongside a single `--plan-id`. This deliverable is NOT part of the
   epic-name rename (`--slug` → `--epic`) — it is the `--transition`/`--set-row`/
   `--add-row` → `--plan-id` collapse ADR-023 §(b) decides, staged here because it sits
   on the same subparser the epic-name rename touches.
7. **D6 — resolve the two-plan-identifier-vocabulary question before D5/D1 touch
   `orchestrator`.** The orchestrator holds two distinct plan identities: the
   epic-local `PLAN-NN` ordinal (`queue --transition/--set-row/--add-row`, and
   `status.json`'s row `id` field) and the plan-marshall kebab id (`inbox write
   --sender-id`, `status.json`'s row `plan_marshall_plan_id` field). ADR-023's suffix set
   covers both as *different values for the same entity kind* but PLAN-04 did not
   enumerate which verb wants which. Decide per-verb, in writing, before any rename
   touches `orchestrator.py` — a blind sweep to `--plan-id` would silently pick the
   wrong identity at half the call sites.
8. **D7 — the survivor sweep**, git-native, per the method in Claim Labels: enumerate the
   whole tracked universe, sweep all three families for every retired spelling, expect
   zero and publish the population read, subtract the two legitimate residues (ADR-023
   and this brief, which both discuss retired spellings by design), and confirm
   `sonar_rest --transition` is excluded as a documented false positive rather than a
   miss.
9. **D8 — self-review point (from `identifier-vocabulary-decision-009`): re-check every
   closed-vocabulary restatement this plan produces** (the canonical-forms rewrite, any
   `ARGUMENT_NAMING_*` plugin-doctor rule text) for the same in-set-vs-out-of-scope
   ambiguity CodeRabbit caught in ADR-023 itself post-push. A rule restated in N places
   can be fixed in one and left wrong in the other N-1.

## Non-Goals

- The fleet-wide `--plan-id` rename (≥38 scripts / 215 doc files, the UNCHANGED
  incumbent surface). Out of scope; successor plan.
- Any behaviour change beyond the mode/identity separation D5 requires on `orchestrator
  queue`. This is a vocabulary change, not a redesign, except at that one site.
- A positional-argument-contract arm (the `ci --plan-id`-after-the-verb class from
  `identifier-vocabulary-decision-010`). Declined: that is a positional defect, not a
  naming one, and adjacent to but outside ADR-023's scope. Promoted to the global
  lessons corpus instead of folded here.
- An argument-value-TYPE convention arm (the `merge_lock --hold-start` epoch-vs-ISO8601
  class from `identifier-vocabulary-decision-011`). Declined for the same reason —
  verified as a convention-inconsistency (not a doc-contract-divergence: both
  `manage-locks/SKILL.md` and `branch-cleanup.md` correctly document `EPOCH`), not a
  naming defect. Promoted to the global lessons corpus instead of folded here.

## Claim Labels

- OBSERVED — ADR-023 (`doc/adr/023-...adoc`, landed at `4804b6976`, read from
  `origin/main`) is the settled decision: entity-noun-first, closed suffix set
  (`none`/`-id`/`-number`/`-slug`). Epic → `--epic`. Plan does NOT collapse (`--plan-id`
  stays at all 282 sites). `--name` kept only at `run_config commit-trailer set --name`.
- OBSERVED — the five declaring sites (pre-rename): `orchestrator.py:4113` (`--slug`,
  required, applied via `_add_slug_arg` to every verb group); `platform_runtime.py:453`
  (`--slug`, validated at `:455` against `--store orchestrator`, on the SAME subparser as
  `--plan-id` at `:439` — the one site where both entities meet); `manage-status`
  (`--plan-id` carrying the epic name under `--store orchestrator`, handlers
  `cmd_orchestrator_*` in `_status_core.py:377-626`); `manage-logging`
  (`manage-logging.py:171-177`, `:226`); `epic-surface-partition.py:768,776,784,798`
  (`--epic`, already correct — cross-bundle, `pm-plugin-development`).
- OBSERVED — the `slug` token is ALSO a `status.json` PLAN ROW field (`plans[].slug`,
  the plan's own kebab key, distinct from the epic name) and a
  `queue --add-row --slug-value` argument. This spec does NOT rename that field — see
  D6 for the separate two-identity question the rename must not conflate with it.
- OBSERVED (from `identifier-vocabulary-decision-001`, PLAN-04's D4 brief, derived from
  `git ls-files` over 3,207 tracked files at PLAN-04's HEAD, zero unreadable) — the sized
  RENAME surface is **31 source files / 43 prose files** (A∪B=31, A∪B∪C=76 total minus
  the 43-only-prose split shown separately). This is the authoritative sizing for THIS
  plan. The previously-cited 38/215 floor is REFUTED as the rename surface: it measures
  the `--plan-id` INCUMBENT surface (32 declaring / 424 mentioning source, 229 doc) —
  the part ADR-023 keeps unchanged, not the part this plan renames.
- OBSERVED (same source) — per-spelling breakdown (declaration sites / Python files /
  prose files): `--slug`→`--epic` (2/18/21, dominant — 286 Python occurrences, 15 of 18
  files are tests under `test/plan-marshall/plan-orchestrator/`); `--slug-value`→
  `--plan-slug` (1/3/4); `--plan`→`--plan-id` (1/5/2); `--target-plan`→`--plan-id`
  (1/1/3); `--transition`/`--set-row`/`--add-row`→`--plan-id` + mode split (1/5/7,
  1/2/5, 1/3/6 respectively, orchestrator-only for the declaration count); `--name`→
  `--module`/`--component` at 4 of 9 sites (5/9/23).
- OBSERVED (same source) — `--transition` is declared on TWO unrelated parsers:
  `plan-orchestrator:orchestrator queue --transition` (in scope) and
  `workflow-integration-sonar:sonar_rest transition --transition
  {accept,falsepositive,wontfix}` (a selector enum naming no entity — NOT in scope,
  renaming it is a defect). Every `--transition` edit must be scoped to `orchestrator.py`
  and its tests specifically.
- OBSERVED (same source) — `ARGUMENT_NAMING_CANONICAL_FORMS_DRIFT`'s own parser
  (`_parse_canonical_forms`), run over the amended `argument-naming.md`: 71 data rows
  under `## Canonical Forms`; the rule cross-checks 30 of them (a lone backticked third
  cell); 41 are excluded by construction (3 `manage-*` alias rows, and the three
  two-column tables — `git-workflow` 9, `ci` 22, `doctor-marketplace` 7 rows).
- OBSERVED (same source) — the whole-tree `test_argument_naming_real_tree_corpus.py`
  corpus, run directly against PLAN-04's head: `markdown_targets: 657`,
  `invocations: 2955`, `registered_notations: 165`, `derivable_surfaces: 117`,
  `non_derivable_omitted: 48`, `blind_spots: 312`, `findings: 0`. That test lives in
  `pm-plugin-development`, not `plan-marshall` (the module `argument-naming.md` is
  attributed to by `which-module`) — a module-scoped gate on the attributed module alone
  would NOT run it. This plan's per-deliverable gate must cover `pm-plugin-development`
  explicitly.
- OBSERVED (same source) — the population coverage gap: 159 registered notations under
  `marketplace/bundles/` (the rename's own scope), 111 derived, 48 `NotDerivable`
  (`help_failed`); of the 48, only one is material —
  `plan-marshall:platform-runtime:platform_runtime`, a hand-rolled dispatcher whose
  top level rejects `--help` and hides 30 long flags including one of the two `--slug`
  sites. Any re-derivation this plan performs inherits that gap; report it as an
  unevaluated cell (ADR-019), never silently folded into a clean count.
- HYPOTHESIS — `epic-surface-partition` is cross-bundle (`pm-plugin-development`) and its
  ownership must be confirmed before editing; `truthful-signals/epic.md:2160-2166`
  records the same caution for the same script. Confirm/refute at that skill's `SKILL.md`
  and its surface-derivation standard (verify-at-outline).
- HYPOTHESIS — an accepted-alias period is unnecessary because every caller is in-repo;
  confirm/refute against the four-condition checklist at
  `phase-3-outline/standards/outline-workflow-detail.md:815-829`, condition by condition,
  and record each answer on the deliverable (verify-at-outline).
- Verify-first clause: ADR-007 records that the deleted-symbol / renamed-identifier
  survivor class has NO whole-surface detector, and that any future detector derives its
  inputs git-natively (`list_tracked_files`/`hash_objects`), never by parsing diff text.
  D7's survivor sweep is this plan's own proof of completeness; do not assume the edit
  set was complete because the build is green.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/**`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/persona-plan-orchestrator/**`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/**`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-logging/**`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/**`
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/tools-epic-surface-partition/**`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/standards/argument-naming.md`
- OBSERVED (added by the D4-brief fold, 2026-09-20): `marketplace/bundles/plan-marshall/skills/manage-architecture/**`
- OBSERVED (added by the D4-brief fold, 2026-09-20): `marketplace/bundles/plan-marshall/skills/script-shared/scripts/query/query-architecture.py`
- OBSERVED (added by the D4-brief fold, 2026-09-20): `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/doctor-marketplace.py`
- OBSERVED: `test/plan-marshall/plan-orchestrator/**`
- OBSERVED: `test/plan-marshall/manage-status/**`
- OBSERVED: `test/plan-marshall/manage-logging/**`
- OBSERVED: `test/pm-plugin-development/tools-epic-surface-partition/**`
- OBSERVED (added by the D4-brief fold, 2026-09-20): `test/pm-plugin-development/plugin-doctor/test_doctor_marketplace.py`

Excluded by the same fold, as a documented false-positive rather than a silent omission:
`marketplace/bundles/plan-marshall/skills/workflow-integration-sonar/**` — its
`sonar_rest transition --transition` is a selector enum naming no entity and must NOT be
touched by the `--transition` sweep.

## Dependencies and Sequencing

- Depends on: **PLAN-04 — LANDED** (PR #1543, merge commit `4804b6976`, on `origin/main`).
  ADR-023 is the settled decision this plan executes. Also depends on PLAN-02 (both touch
  `orchestrator.py`, `plan-orchestrator/SKILL.md`, and `manage-status/**`, including
  `_status_core.py` and `status-lifecycle.md` — the sharpest collision in this epic's
  corpus, since PLAN-02 changes the schema shape and this plan renames CLI flags on the
  same scripts). PLAN-02 lands first.
- Overlaps with: PLAN-06 (`_orchestrator_inbox.py`, `tools-epic-surface-partition/**`,
  and — after PLAN-06's own fold — `phase-1-init/**`/`phase-6-finalize/**`, and its
  tests); PLAN-07 (`plan-orchestrator/**` including `orchestrator.py`).
- Adjacent to: `workflow-integration-sonar` (explicitly excluded, see Expected Surface);
  the fleet-wide `--plan-id` rename (successor plan, not this one).

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/orchestrator-refactor/plans/PLAN-05-identifier-rename-execution.md"
```

## Write-Boundary

The plan implementing this spec touches only repository source, tests, standards and
templates across three bundles (plan-marshall, pm-plugin-development). It creates and
edits NO file under `.plan/local/orchestrator/` (or the migrated tracked address, once
PLAN-01 lands) other than its own `inbox/{sender}-{seq}` message — the orchestrator owns
every other ledger write — and reports its outcome through its PR and its inbox message.
The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
