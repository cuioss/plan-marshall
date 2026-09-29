# PLAN-09: A fixed-name, long-lived worktree for each orchestrator epic's own tree

> ✅ **RE-STAGED 2026-09-26 by explicit operator decision** — exempted from the PM-MCP supersession that parked
> the rest of this epic's queue the same day. **RE-SCOPED the same day, operator direction: ONE fixed worktree
> for ALL epic changes**, replacing the earlier one-worktree-per-epic design. Objective, Deliverables and
> Non-Goals below are rewritten for that; Claim Labels are unchanged research (their per-epic phrasing is
> historical). Implementation-independent content is also carried in
> `plan-marshall-mcp/doc/known-defects/orchestrator-refactor-carry-over.md`.

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

The orchestrator today reads and writes `.plan/orchestrator/**` directly against whatever checkout the session
runs in — normally the primary checkout on `main` — with no dedicated commit/push mechanism (no `git
commit`/`git push` in `orchestrator.py` or its workflow docs; ledger commits are ad hoc LLM-run `git`). Every
epic session therefore leaves dirty ledger files on `main`'s working tree, and they accumulate across epics.

Give the orchestrator store ONE fixed-name, long-lived git worktree shared by ALL epics — created once, reused
forever, never auto-removed — and route the single store-resolution seam through it when an
`orchestrator.use_worktree` knob is on, so every epic's ledger reads and writes land in that worktree instead of
the primary checkout. The per-concern ledger layout (one file per row, append-only inbox and landings) already
makes concurrent epic sessions write disjoint files, so one shared working tree is safe for writes; only git
operations need serializing, which is PLAN-10's concern. This plan builds the substrate only; landing the
worktree's changes onto `main` is PLAN-10.

## Deliverables

1. **D1 — `orchestrator.use_worktree` config knob.** Extend the orchestrator config block's CLOSED key-set and
   validator (`manage-config/standards/data-model.md`, currently `{effort, parallelization_scope, auto_emit}`)
   with `use_worktree` (bool). It is REPOSITORY-wide, not per epic: one worktree serves every epic, so a
   per-epic switch would split the ledger across two copies. Default `false` (opt-in rollout) unless the
   outline states a reason for `true`.
2. **D2 — the one fixed worktree.** A single deterministic location under the existing worktree root
   (`get_worktree_root()`), with a key that CANNOT collide with any plan id — choose a key outside the plan-id
   grammar (e.g. a leading underscore or another character the grammar rejects), decided and documented at
   outline. A fixed long-lived branch name within the closed prefix set (`chore/…`), since ledger landings are
   maintenance. Addressing: a non-plan-keyed mode on `git-workflow.py`'s thin worktree trio
   (`worktree-create` / `worktree-path` / `worktree-list`) or a thin orchestrator-side wrapper over the same
   `get_worktree_root() / {key}` path-join — decide at outline. The plan-shaped move-in/move-back layer
   (`prepare_execute.py`, `integrate_into_main.py`) is EXCLUDED (see Claim Labels).
3. **D3 — idempotent, non-destructive lifecycle.** First use creates the worktree on the fixed branch off
   `origin/main`; every later use reuses it as-is. No normal operation — including PLAN-10's `land` — removes
   it; only an explicit, separate operator teardown (out of scope) may. `worktree-list` and any plan-worktree
   sweep must recognise and skip it, never treat it as an orphaned plan worktree.
4. **D4 — one seam, every consumer.** When the knob is on, route `get_store_dir('orchestrator', …)` /
   `get_tracked_config_dir()` (`tools-file-ops`, PLAN-01's resolver) — for BOTH `.plan/orchestrator/` and
   `.plan/archived-orchestrators/` — through the worktree, for every consumer: `manage-status` /
   `manage-logging --store orchestrator`, `orchestrator.py`'s own reads and writes (incl. `archive`, which moves
   a tree between the two roots), `corpus` reads, and the PLAN-SIDE consumers that run from a plan's own
   worktree: `inbox write` (landing / finding messages), `inbox read` (mailbox), `inbox detect`, and
   `phase-1-init`'s read of a spec by `source_id`. A spec staged in the worktree and not yet landed is invisible
   on `main`, so init must resolve it through the same seam or the emit must require the spec landed — decide
   at outline, never silently read a stale `main` copy. Also audit
   `platform_runtime session push-title-token --store orchestrator` (`bind_orchestrator`) for any dependence on
   the primary checkout's cwd. Knob off → today's primary-checkout path unchanged.
5. **D5 — cutover guard.** Enabling the knob while the primary checkout still holds uncommitted or unlanded
   `.plan/orchestrator/**` / `.plan/archived-orchestrators/**` changes would strand them on `main` while every
   reader moves to the worktree. The switch-on path detects that state (naming the dirty paths) and refuses, or
   carries them into the worktree deliberately — decide at outline; never silently leave two diverging copies.

Scope-bloat note: 5 deliverables, below the ~6 split threshold; D4's plan-side consumer list is the widest
surface and is the one to split out if the outline finds it larger than stated.

## Non-Goals

- No `land` verb — that is PLAN-10, strictly dependent on this plan.
- No change to the plan lifecycle's own worktree machinery or its `--plan-id` addressing — extended/reused,
  never redesigned.
- No teardown/removal mechanism for the orchestrator worktree — "never removed by normal operation" is the
  point.
- No per-epic worktree — superseded by the operator's one-shared-worktree direction (2026-09-26).

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
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-1-init/**` — D4's spec-by-`source_id` read (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py` — D4's plan-side `inbox write` / `read` / `detect` (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/platform-runtime/**` — D4's `bind_orchestrator` audit, only if it needs a change (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/phase-1-init/**` (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none directly (net-new capability).
- Overlaps with: PLAN-11 (`orchestrator.py` and `test/plan-marshall/plan-orchestrator/**`) — sequence, do not
  parallelize. PLAN-02 / PLAN-06 overlaps recorded earlier are moot (PLAN-02 shipped, PLAN-06 parked).
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
