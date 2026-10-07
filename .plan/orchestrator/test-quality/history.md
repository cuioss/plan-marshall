# History: test-quality — house style and reduction of the Python test corpus

slug: test-quality
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

Bring the repository's ~770-module, ~377,000-line Python test corpus under a stated, enforced house
style (rules **B1**–**B10**) and shrink it **without losing a single assertion**. The epic is too
large for one plan because the corpus partitions into six disjoint reduction slices, each of which
needs its own run, plus a standards plan, a harness plan, a production-gap plan, and a module-budget
campaign that spans all six slices one run at a time. Done at the epic level means: the house style is
written into the owning skills and enforced by `plugin-doctor`'s `test-conventions` scope; every slice
has been through a reduction run; the 400-line module budget (**B1**) is driven to zero honestly; the
suite reports zero unexplained skips and no wall-clock regression; and the epic's own cross-file sets
(partition, collision matrix, per-slice attribution) are **derived and checked** rather than held in
prose.

**This epic was ingested from `doc/plans/test-quality/`**, a standalone `doc/plans/` cloud-lane epic
that ran ten plans to completion outside the orchestrator. The version-controlled directory is now
empty; every plan document, every run report, and the epic's scoping brief live under this tree. See
`## Provenance` below.

## Final state

The two blocks below are the generated view at close, verbatim.

### Queue view: test-quality: house style and reduction of the Python test corpus

#### START HERE

**Resume anchor**: PLAN-184 un-emitted to parked (operator order 2026-09-28): staged row held off the launch path, spec retained. Live queue empty (182/183 shipped, 140 superseded). Next: cleanup + land.
**Phase**: orchestrating
**Parked**:
- PLAN-184 (WS-03)
**Queue** (staged, in order):
- (empty)
- PLAN-140 (WS-04) — PR #1552 — status: superseded
- PLAN-181 (WS-04) — plan=run-3-carve-2-tools-permission-fix — PR #1582 — landing=landings/PLAN-181.md — status: shipped
- PLAN-182 (WS-04) — PR #1640 — landing=landings/PLAN-182-completion.md — status: shipped
- PLAN-183 (WS-03) — plan=carried-defects-and-watches-closure — PR #1602 — landing=landings/PLAN-183.md — status: shipped

#### Ordered Queue

| # | Plan | Workstream | Status | Surface (expected) |
|---|------|------------|--------|--------------------|
| 1 | PLAN-184 | WS-03 | parked | marketplace/bundles/plan-marshall/skills/phase-6-finalize/; marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/; marketplace/bundles/pm-plugin-development/skills/plugin-doctor/; test/_shared/_shared_harness_fixtures.py; test/plan-marshall/script-shared/test_conftest_loader_contract.py |

## Queue outcome

5 plans: 3 shipped, 1 closed unshipped, 1 parked, 0 at another status.

### Shipped

| Plan | Slug | Status | PR |
|---|---|---|---|
| PLAN-181 | run-3-carve-2-tools-permission-fix | shipped | #1582 |
| PLAN-182 | module-budget-campaign-completion | shipped | #1640 |
| PLAN-183 | carried-defects-and-watches-closure | shipped | #1602 |

### Closed unshipped

| Plan | Slug | Status |
|---|---|---|
| PLAN-140 | module-budget-campaign-runs-2-7 | superseded |

### Parked at close

| Plan | Slug | Status |
|---|---|---|
| PLAN-184 | instrument-hardening-backlog | parked |

### Other status at close

_none_

A row still `staged` or `parked` here was live work that did not finish before the close. It
is a lead, not a queue entry: nothing emits it any more.

## Carried into `live-blockers`

- Whole-tree verify outrunning its local budget → `PLAN-LB-12`.
- Scope-creep guard crash (lesson `2026-09-08-22-002`) → `PLAN-LB-07`.

## Leads carried forward, not staged

- The medium- and low-priority items found in this epic are listed with evidence in
  `.plan/orchestrator/live-blockers/backlog.md`. They are unstaged.
- `epic.md` § Open Defects (83 entries) and § Watches (63 entries) are frozen as they
  stood. Entries not named above or in that backlog were judged to be design input for the
  rewrite, refactors or measurements of machinery the rewrite replaces, or already fixed.
- Design input for plan-marshall-mcp lives in that repository's requirements, specification
  and `doc/implementation-watch/` documents. Ledger pointers to
  `plan-marshall-mcp/doc/known-defects/…-carry-over.md` name a path that no longer exists.
- **The recorded "zero over-budget test modules" result of PLAN-182 is false.** 419 test files are over 400 lines at HEAD (412 at the merge commit of #1640). Do not stage the warning-to-error flip of the test-conventions rule from this ledger.
- `PLAN-184` (instrument hardening) is a ready spec; its D2 (lessons-housekeeping retired field), D1 and D4 are in `backlog.md` §§ 1.12 and 2.9.
- #1641 reverted nine paths of this ledger and the restore was never actioned.

### Inbox messages undrained at close

- `inbox/process-compliance-001.md`

## Decision record

`epic.md` § Decisions is the curated view; `logs/decision.log` is the append-only record. Both
are frozen in this tree.
