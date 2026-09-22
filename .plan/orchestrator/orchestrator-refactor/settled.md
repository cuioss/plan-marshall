# Settled: Orchestrator Substrate Refactor

Relocated closed narrative from `epic.md` — the audit record of resolved defects and
retired watches, moved here verbatim by the `cleanup` verb's ledger-compaction stage so
`epic.md` stays focused on live state. A pointer at each origin names the heading here.
See `persona-plan-orchestrator/standards/orchestration-model.md` § Ledger-Compaction Stage.

## PLAN-01 stuck mid-finalize on an unreviewable diff

- ~~PLAN-01 is stuck mid-finalize on an unreviewable diff~~ **RESOLVED 2026-09-21**: the
  split executed — #1557 (code, ~48 files, merged `8c8c7bbf`), #1558 (ledger content, 3,977
  files, `skip-bot-review`, merged `6728b738`), #1555 closed unmerged with a pointer to the
  replacements. A follow-up, #1561, landed a fix for a hardcoded-path finding the split
  missed. See `landings/PLAN-01.md`.

## Epic ledger tree split across two locations

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

## Restart-check worktree signal reported not_ready

- ~~STILL OPEN — restart-check's worktree signal reports not_ready~~ **RESOLVED
  2026-09-21**: operator approved the commit/push/PR/merge sequence. Landed as PR #1566
  (`3d88b24cf`, `skip-bot-review`, merge queue) — see `landings/PLAN-01.md`. `main`
  pulled locally; `restart-check` now reports `ready` on all 5 scored signals. The old
  `.plan/local/orchestrator/orchestrator-refactor/` tree (21 decision-log entries it
  alone held, since `logs/` is git-ignored) was merged into this tree's log before the
  operator deleted it.

## truthful-signals PLAN-TRUTH-143 running, blocking dependents

- ~~`truthful-signals` PLAN-TRUTH-143 is `running`...~~ **RESOLVED 2026-09-20/21**: shipped as
  PR #1539 (merge `1c56734ce`, 2026-09-20T07:11:51Z). Both dependents unblocked: PLAN-01's
  live-plan collision cleared (it was subsequently launched — see the new Open Defect on its
  own stuck finalize, unrelated to this collision); PLAN-06 re-grounded and re-staged this
  cleanup pass (D2/D3 found moot, D5 narrowed).

## Two orchestrator entities share one word

- ~~Two "orchestrator" entities share one word in this codebase...~~ **RESOLVED by PLAN-04 /
  ADR-023 §(d) "Telling the two tiers apart at the caller surface"** — the epic is `--epic`,
  the plan is `--plan-id`; the two are different tokens on the same parser by construction.
  Retired 2026-09-20.
