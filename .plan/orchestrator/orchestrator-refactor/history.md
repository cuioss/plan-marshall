# History: Orchestrator Substrate Refactor

slug: orchestrator-refactor
closed: 2026-10-07

> Frozen record of the epic at close. `epic.md`, the queue rows, the specs, the landings, the
> inbox and the logs stay in this tree untouched; this file is the summary a later reader
> starts from. Close freezes and never deletes.

## Closing rationale

Closed by operator instruction on 2026-10-07. plan-marshall's workflow machinery is being
rewritten as plan-marshall-mcp, which supersedes most of this epic's staged and parked work.
The work that still matters for plan-marshall itself — defects that block or mislead a normal
run today, and high-priority work on things the rewrite does not replace — was cut into the
successor epic `live-blockers` (`.plan/orchestrator/live-blockers/`). Everything else was
left where it stood.

## Vision as pursued

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
> half shipped: PLAN-09 landed the shared ledger worktree, and **`orchestrator.use_worktree` was turned ON
> 2026-10-01** (repository-wide, #1666). Every epic's ledger writes now go to the shared worktree
> (`.plan/local/worktrees/_orchestrator`, branch `chore/orchestrator-ledger`), not to `main`. **Aspect 5 shipped
> 2026-10-03**: PLAN-10 landed the `land` verb (#1690), so that branch is landed by `orchestrator land` rather
> than by hand once the harness installs are synced.

## Final state

The two blocks below are the generated view at close, verbatim.

### Queue view: Orchestrator Substrate Refactor

#### START HERE

**Resume anchor**: 2026-10-05 — PRE-ARCHIVE CLEANUP DONE. Queue terminal: 7 shipped (PLAN-01/02/04/08/09/10/11), 4 superseded by PM-MCP (PLAN-03/05/06/07). All open items transferred (truthful-signals, review-apparatus, lessons-routing — orchestrator-refactor-001.md each) or resolved; settled narrative relocated to settled.md (see Decisions 2026-10-05). Inbox empty; restart verdict ready.

Next action: operator runs /sync-harnesses (retires the last Watch), then /plan-orchestrator close → archive → land. Note for land: remote chore/orchestrator-ledger carries post-run-quality PRQ-15 commits the local worktree lacks (remote_branch_contained=false).

LEDGER LIVES IN THE SHARED WORKTREE (orchestrator.use_worktree ON): take epic_dir/store_checkout from resolve-path; ledger reaches main only through /plan-orchestrator land.
**Phase**: orchestrating
**Queue** (staged, in order):
- (empty)
- PLAN-01 (WS-01) — plan=tracked-orchestrator-store-resolver — PR #1557, #1558, #1561 — landing=landings/PLAN-01.md — status: shipped
- PLAN-02 (WS-01) — plan=ledger-decomposition-and-row-vocabulary — PR #1609 — landing=landings/PLAN-02.md — status: shipped
- PLAN-03 (WS-02) — status: superseded
- PLAN-04 (WS-03) — plan=identifier-vocabulary-decision — PR #1543 — landing=landings/PLAN-04.md — status: shipped
- PLAN-05 (WS-03) — status: superseded
- PLAN-06 (WS-04) — status: superseded
- PLAN-07 (WS-04) — status: superseded
- PLAN-08 (WS-04) — plan=verdict-staleness-scoping — PR #1585 — landing=landings/PLAN-08.md — status: shipped
- PLAN-09 (WS-05) — plan=orchestrator-worktree-substrate — PR #1652 — landing=landings/PLAN-09.md — status: shipped
- PLAN-10 (WS-05) — plan=orchestrator-land-verbs — PR #1690 — landing=landings/PLAN-10.md — status: shipped
- PLAN-11 (WS-04) — plan=cross-check-dated-archive-self-collision — PR #1676 — landing=landings/PLAN-11.md — status: shipped

#### Ordered Queue

| # | Plan | Workstream | Status | Surface (expected) |
|---|------|------------|--------|--------------------|
| — | (empty) | — | — | — |

## Queue outcome

11 plans: 7 shipped, 4 closed unshipped, 0 parked, 0 at another status.

### Shipped

| Plan | Slug | Status | PR |
|---|---|---|---|
| PLAN-01 | tracked-orchestrator-store-resolver | shipped | #1557, #1558, #1561 |
| PLAN-02 | ledger-decomposition-and-row-vocabulary | shipped | #1609 |
| PLAN-04 | identifier-vocabulary-decision | shipped | #1543 |
| PLAN-08 | verdict-staleness-scoping | shipped | #1585 |
| PLAN-09 | orchestrator-worktree-substrate | shipped | #1652 |
| PLAN-10 | orchestrator-land-verbs | shipped | #1690 |
| PLAN-11 | cross-check-dated-archive-self-collision | shipped | #1676 |

### Closed unshipped

| Plan | Slug | Status |
|---|---|---|
| PLAN-03 | self-terminating-layout-migration | superseded |
| PLAN-05 | identifier-rename-execution | superseded |
| PLAN-06 | orchestrator-mechanism-intake | superseded |
| PLAN-07 | orchestrator-script-decomposition | superseded |

### Parked at close

_none_

### Other status at close

_none_

A row still `staged` or `parked` here was live work that did not finish before the close. It
is a lead, not a queue entry: nothing emits it any more.

## Carried into `live-blockers`

- Open item "disjointness gate scope" → `PLAN-LB-14`.
- The `source_id` landing-loss defect (PLAN-06 D5) and the git-config hardening are in `backlog.md` §§ 1.24 and 2.5.

## Leads carried forward, not staged

- The medium- and low-priority items found in this epic are listed with evidence in
  `.plan/orchestrator/live-blockers/backlog.md`. They are unstaged.
- `epic.md` § Open Defects (12 entries) and § Watches (5 entries) are frozen as they
  stood. Entries not named above or in that backlog were judged to be design input for the
  rewrite, refactors or measurements of machinery the rewrite replaces, or already fixed.
- Design input for plan-marshall-mcp lives in that repository's requirements, specification
  and `doc/implementation-watch/` documents. Ledger pointers to
  `plan-marshall-mcp/doc/known-defects/…-carry-over.md` name a path that no longer exists.
- ADR-023 and ADR-024 are still "Proposed"; the naming standard prescribes `--epic` while the code uses `--slug` (`backlog.md` § 4.10).
- Three watches closed with the epic and were never given a disposition: the `2-refine` perfect-score rate and the per-plan argparse-rejection rate (one data point each, from PLAN-04), and the `e79ee5` mis-triage spot-check.
- plan-marshall-mcp contradicts or omits several decisions this epic shipped (verdict staleness from the declared surface, the land resync, branch verification before a ledger commit, per-concern ledger files). That is input for the rewrite and is not carried into `live-blockers`.

### Inbox messages undrained at close

- none

## Decision record

`epic.md` § Decisions is the curated view; `logs/decision.log` is the append-only record. Both
are frozen in this tree.
