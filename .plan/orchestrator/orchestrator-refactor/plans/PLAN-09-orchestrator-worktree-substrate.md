# PLAN-09: A fixed-name, long-lived worktree for each orchestrator epic's own tree

epic: orchestrator-refactor
workstream: WS-05

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-09-orchestrator-worktree-substrate.md` and is queued in the epic
> `status.json` `plans[]` field. The orchestrator EMITS the command below; it never launches
> the plan inline. This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer
> and carries no brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

The orchestrator today reads and writes `.plan/orchestrator/{slug}/` directly against
whatever checkout the session runs in — normally the primary checkout on `main` — with no
dedicated commit/push mechanism at all (confirmed: no `git commit`/`git push` anywhere in
`orchestrator.py` or its workflow docs; it is ad hoc LLM-run `git` under the small-ops
carve-out). Give each epic a FIXED-NAME, long-lived git worktree — created once, reused
forever, never auto-removed — and route the orchestrator's store-resolution seam through it
when an `orchestrator.use_worktree` config knob is on, so an epic's ledger reads/writes land
in a dedicated worktree instead of directly touching the primary checkout. This plan builds
the substrate only; landing the worktree's changes onto `main` is PLAN-10's job.

## Deliverables

1. **D1 — `orchestrator.use_worktree` config knob.** Extend the orchestrator config block's
   CLOSED key-set and validator (`manage-config/standards/data-model.md`, currently
   `{effort, parallelization_scope, auto_emit}` only) with a fourth key, `use_worktree`
   (bool). Decide and document the default at outline — `false` (opt-in rollout, matches how
   `parallelization_scope`/`auto_emit` were introduced) is the safer starting point absent a
   stated reason to default `true`.
2. **D2 — fixed-name per-epic worktree creation/attach, THIN TRIO ONLY.** Extend
   `workflow-integration-git`'s `git-workflow.py worktree-create` / `worktree-path` /
   `worktree-list` (currently hard-required `--plan-id`-only per its own in-source
   assertion) to also address an orchestrator epic — either a sibling
   `--store orchestrator --slug {slug}` addressing mode on the SAME verbs, or a thin
   orchestrator-side wrapper that reuses the same underlying `get_worktree_root() / {key}`
   path-join primitive these three verbs share. **Re-scoped 2026-09-23 (cleanup A1):** the
   ORIGINAL framing ("reuses the same underlying atomic create/attach primitive") pointed at
   `prepare_execute.py`/`integrate_into_main.py`'s move-in/move-back layer, which is
   confirmed plan-shaped by construction (relocates `.plan/local/plans/{plan_id}`, writes a
   plan `status.json`, generates a per-plan executor, takes a `plan_id`-keyed `merge_lock`)
   — an epic tree has none of those, so that layer is explicitly EXCLUDED from this
   deliverable, not merely deferred. Only the thin trio's own path-join logic is generic.
   Decide the addressing-mode question at outline; either way the path convention is fixed
   and deterministic (e.g. `.plan/local/worktrees/orchestrator-{slug}/`), mirroring the
   existing `.plan/local/worktrees/{plan_id}/` convention exactly, one level up.
3. **D3 — idempotent, non-destructive lifecycle.** First use creates the worktree (a fresh
   branch off the epic's current tracking base); every subsequent use reuses it as-is. No
   normal orchestrator operation — including this workstream's own `land` (PLAN-10) — ever
   removes it; only an explicit, separate, operator-invoked teardown (out of THIS plan's
   scope; not designed here) may.
4. **D4 — resolver routing.** When `orchestrator.use_worktree` is on for an epic, route
   `get_store_dir('orchestrator', slug)` / `get_tracked_config_dir()` (`tools-file-ops`, the
   same resolver PLAN-01 introduced) through the worktree's path instead of the primary
   checkout's, for every consumer that reaches it — `manage-status --store orchestrator`,
   `manage-logging --store orchestrator`, `orchestrator.py`'s own file reads/writes
   (`epic.md`, `plans/`, `workstreams/`, `landings/`, `inbox/`), and `corpus`'s reads.
   Falls back to today's primary-checkout path when the knob is off (default, so this
   plan's own landing changes nothing for an epic that hasn't opted in).
5. **D5 — audit the terminal-title/session-binding seam.** `platform_runtime session
   push-title-token --store orchestrator --slug {slug}` (`bind_orchestrator`) is called by
   every epic-scoped verb; confirm/refute whether it depends on the store resolving to the
   PRIMARY checkout's cwd in any way that a worktree-resolved path would break
   (verify-at-outline).

## Non-Goals

- No `land`/`land-all` verb — that is PLAN-10, strictly dependent on this plan.
- No change to the PLAN-lifecycle's own worktree machinery or its `--plan-id` addressing —
  extended/reused, never redesigned.
- No teardown/removal mechanism for the orchestrator worktree — explicitly out of scope per
  D3; "never removed by normal operation" is the whole point.

## Claim Labels

- OBSERVED: no `git commit`/`git push`/`git add` invocation exists anywhere in
  `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py`,
  `_orchestrator_inbox.py`, or any `plan-orchestrator`/`persona-plan-orchestrator` workflow
  doc — the orchestrator's ledger commits today are entirely ad hoc, under the small-ops
  carve-out's "git — read-side commands, and small bounded mutations within the carve-out's
  spirit" clause (`orchestration-model.md` § Small-ops carve-out), never a scripted,
  documented step.
- OBSERVED: `git-workflow.py:886-892` states in-source that every worktree subcommand
  REQUIRES `--plan-id` and operates on `get_worktree_root() / plan_id` — there is currently
  no non-plan-keyed (e.g. epic-keyed) worktree addressing mode.
- OBSERVED: the existing plan-worktree path convention is `.plan/local/worktrees/{plan_id}/`
  (`workflow-integration-git/SKILL.md:530-550`); this plan's fixed-name convention for an
  epic mirrors it one level up in the key space (plan id → epic slug), not the directory
  structure.
- OBSERVED: `manage-config/standards/data-model.md:242-306` — the orchestrator config block
  is validated as a CLOSED shape; `validate_orchestrator_block` (line 306) rejects any
  top-level key outside `{effort, parallelization_scope, auto_emit}`. Adding `use_worktree`
  is a real schema extension (allowed-key set + validator), the same shape of change that
  added `parallelization_scope`/`auto_emit`.
- OBSERVED: the PLAN-tier `use_worktree` knob (`plan.phase-1-init.use_worktree`, bool,
  default `true`, `manage-config/standards/data-model.md:679`, seeded
  `_config_defaults.py:640`) is a DIFFERENT config tier governing a DIFFERENT lifecycle
  (whether a PLAN gets a worktree, consumed at `phase-5-execute` Step 2.5) — this plan's
  knob is net-new at the orchestrator tier, not a reuse of that key.
- OBSERVED: `.plan/orchestrator/` and `.plan/archived-orchestrators/` are git-tracked —
  `.gitignore:45` blankets `.plan/*` but lines 48-51 explicitly negate those two paths
  (only their `logs/` subpaths are re-ignored, lines 57-59) — while `.plan/local/` (where
  worktrees live) carries no negation and stays fully ignored. Live-verified this session:
  `git ls-files .plan/orchestrator/` returns real tracked paths; `git check-ignore
  .plan/local/plans` confirms the blanket rule still applies there. So a worktree checking
  out `.plan/orchestrator/{slug}/`'s branch has real, committable content to work with.
- HYPOTHESIS (re-scoped 2026-09-23, cleanup A1 — the original target `_cmd_prepare` does
  not exist anywhere in the repo): extending `git-workflow.py`'s `worktree-create` /
  `worktree-path` / `worktree-list` with a `--store orchestrator` addressing mode is
  architecturally preferable to a separate thin wrapper in `orchestrator.py` reusing the
  same `get_worktree_root() / {key}` path-join those three verbs share — confirm/refute at
  `git-workflow.py`'s actual verb-dispatch structure (verify-at-outline). The move-in/
  move-back layer (`workflow-integration-git/scripts/prepare_execute.py` §
  `run_prepare_execute`, and `integrate_into_main.py`) is CONFIRMED plan-shaped by
  construction — it relocates `.plan/local/plans/{plan_id}`, writes a plan `status.json`,
  generates a per-plan executor, and takes a `plan_id`-keyed `merge_lock`, none of which an
  epic tree has — and is explicitly OUT of this HYPOTHESIS's scope, not merely unresolved.
  - verdict: contradicted | checked_at: 9588b30b317d0312ede90f1982122aa3145ea871 | by: orchestrator-refactor/cleanup | rescoped: yes | evidence: Refutation re-reproduced, unchanged since prior pass. (1) _cmd_prepare still does not exist anywhere in the repo; real successor is workflow-integration-git/scripts/prepare_execute.py run_prepare_execute :551 (unmoved). (2) move-in/move-back mechanics remain plan-shaped by construction -- prepare_execute.py relocates .plan/local/plans/{plan_id}, writes plan status.json, generates a per-plan executor; integrate_into_main.py resolves via the plan-status channel and takes a plan_id-keyed merge_lock. An epic tree has no plan directory, no executor, no plan-status channel. Only the thin trio (worktree-create/worktree-path/worktree-list) is generic. CORRECTION: the re-scope this verdict calls for is ALREADY absorbed into D2's body (its own 'Re-scoped 2026-09-23 (cleanup A1)' note cites this exact finding) -- verified by re-reading the spec directly. Nothing further owed on the spec body for this claim.
- Verify-first clause: re-derive `git-workflow.py`'s exact verb surface and line numbers
  against HEAD at outline time — this citation is from research conducted 2026-09-23 and
  may have shifted if a sibling plan touched the same file first.
  - verdict: corroborated | checked_at: 9588b30b317d0312ede90f1982122aa3145ea871 | by: orchestrator-refactor/cleanup | rescoped: n/a | evidence: Re-reproduced, unchanged. git-workflow.py is 3054 lines, byte-unchanged since 7d82d5d90 (no sibling plan has shifted it). Cited :886-892 resolves verbatim. Correction the spec should still carry: cmd_worktree_list at :2520 takes no --plan-id despite the in-source comment's blanket claim; real verb surface is SIX not three: worktree-path :1264, branch-sync-state :1369, worktree-create :1511, worktree-remove :1981, worktree-rebase-to :2331, worktree-list :2520, plus locate-plan-checkout :2601.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/standards/data-model.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_config_defaults.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-git/SKILL.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-file-ops/**`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/persona-plan-orchestrator/standards/orchestration-model.md`
- OBSERVED: `test/plan-marshall/manage-config/**`
- OBSERVED: `test/plan-marshall/workflow-integration-git/**`
- OBSERVED: `test/plan-marshall/plan-orchestrator/**`

## Dependencies and Sequencing

- Depends on: none directly (net-new capability).
- Overlaps with: PLAN-02 (also touches `orchestrator.py`'s status/store surface — sequence,
  do not parallelize, since D4's resolver-routing change and PLAN-02's row-vocabulary work
  both touch the same read/write paths), PLAN-06 (also `orchestrator.py`).
- **PLAN-10 strictly depends on this plan** — there is nothing to land until the worktree
  and its resolver routing exist.
- Adjacent to: the PLAN-lifecycle's own `--plan-id`-addressed worktree verbs, which this
  plan extends/reuses rather than redesigns — a behavior change there is explicitly a
  Non-Goal.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/orchestrator-refactor/plans/PLAN-09-orchestrator-worktree-substrate.md"
```

## Write-Boundary

The plan implementing this spec touches only repository source, standards and tests. It
creates and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and
reports its outcome through its PR and its inbox message. The inbox exception's qualifiers
and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
