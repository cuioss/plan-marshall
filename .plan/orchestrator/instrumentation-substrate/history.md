# History: Instrumentation Substrate — a measured instruction fleet

slug: instrumentation-substrate
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

plan-marshall holds its Python to a quality gate, a test suite, and a coverage number. It holds its
**instruction substrate** — 157 components and ~175k lines of markdown under `marketplace/bundles/**`
— to nothing but assertion. Every hard rule, every `⛔`, every workflow step is a claim about model
behaviour that no harness has ever tested, on a fleet of runtimes of which only one is exercised at
all. This epic closes that asymmetry: a documented rule becomes something that can be shown to hold
or fail under adversarial conditions, on more than one model, at a stated cost.

Done, at the epic level, means three things are true that are false today. A workflow rule can be put
under pressure and produce a three-valued verdict with the population it was scored over. A corpus
edit's effect on a non-Claude runtime is a measured regression signal rather than a hope. And the
price of carrying an instruction is a number somebody can read.

## Final state

The two blocks below are the generated view at close, verbatim.

### Queue view: Next Level: measured instruction substrate

#### START HERE

**Resume anchor**: CLEANUP done 2026-09-22: 9 specs re-grounded at HEAD 7d82d5d90 (38 claims: 23 corroborated, 11 contradicted+rescoped in-place, 4 downgraded to spec-internal reasoning for dead inbox citations). Highest-priority re-scope: PLAN-01's leaf-isolation hypothesis is refuted (harness re-supplies CLAUDE.md into dispatched leaves) — spec now splits attribution-isolated vs realistic-context compliance; this gates WS-01. PLAN-02/PLAN-08 share a widened hard-rule population (CLAUDE.md + persona-plan-marshall-agent + tool-usage-patterns.md) — reconcile at outline, do not derive twice. PLAN-05's 4 of 6 numeric figures were corrected in place. PLAN-09's corrections routed to post-run-quality (owns live PLAN-PRQ-05 successor). Ledger compacted (epic_changed=true, ordered-queue regenerated for PLAN-01's narrowed surface). archive_drain=refused (standing, no epic-wide quiescence signal). restart_verdict=NOT_READY — 83 uncommitted paths at HEAD (this session's spec/ledger edits); commit is an operator decision, not auto-applied. NEXT ACTION: review + commit the cleanup edits, then /plan-orchestrator next slug=instrumentation-substrate.
**Phase**: orchestrating
**Parked**:
- PLAN-09 (WS-05)
**Queue** (staged, in order):
1. PLAN-01 (WS-01)
2. PLAN-02 (WS-01)
3. PLAN-03 (WS-02)
4. PLAN-04 (WS-02)
5. PLAN-05 (WS-03)
6. PLAN-06 (WS-03)
7. PLAN-07 (WS-04)
8. PLAN-08 (WS-01)

#### Ordered Queue

| # | Plan | Workstream | Status | Surface (expected) |
|---|------|------------|--------|--------------------|
| 1 | PLAN-01 | WS-01 | staged | marketplace/bundles/pm-plugin-development/skills/instruction-conformance/; test/pm-plugin-development/instruction-conformance/ |
| 2 | PLAN-02 | WS-01 | staged | marketplace/bundles/pm-plugin-development/skills/instruction-conformance/; test/pm-plugin-development/instruction-conformance/ |
| 3 | PLAN-03 | WS-02 | staged | doc/adr/; doc/developer/marketplace-build.adoc |
| 4 | PLAN-04 | WS-02 | staged | doc/developer/; marketplace/bundles/plan-marshall/skills/eval-cross-model/; test/plan-marshall/eval-cross-model/ |
| 5 | PLAN-05 | WS-03 | staged | marketplace/bundles/; marketplace/bundles/pm-plugin-development/skills/plugin-architecture/references/frontmatter-standards.md; marketplace/bundles/pm-plugin-development/skills/plugin-doctor/; test/pm-plugin-development/plugin-doctor/ |
| 6 | PLAN-06 | WS-03 | staged | marketplace/bundles/plan-marshall/skills/manage-status/; marketplace/bundles/plan-marshall/skills/platform-runtime/; test/plan-marshall/platform-runtime/ |
| 7 | PLAN-07 | WS-04 | staged | marketplace/bundles/plan-marshall/skills/persona-module-tester/; marketplace/bundles/pm-dev-python/skills/pytest-testing/; pyproject.toml; test/pm-dev-python/ |
| 8 | PLAN-08 | WS-01 | staged | CLAUDE.md; marketplace/bundles/plan-marshall/skills/platform-runtime/; test/plan-marshall/platform-runtime/ |
| 9 | PLAN-09 | WS-05 | parked | marketplace/bundles/plan-marshall/skills/manage-lessons/; test/plan-marshall/manage-lessons/ |

## Queue outcome

9 plans: 0 shipped, 0 closed unshipped, 1 parked, 8 at another status.

### Shipped

_none_

### Closed unshipped

_none_

### Parked at close

| Plan | Slug | Status |
|---|---|---|
| PLAN-09 | lessons-corpus-provenance-and-quality | parked |

### Other status at close

| Plan | Slug | Status |
|---|---|---|
| PLAN-01 | conformance-harness-seam | staged |
| PLAN-02 | baseline-conformance-corpus | staged |
| PLAN-03 | calibration-axis-decision | staged |
| PLAN-04 | cross-model-eval-signal | staged |
| PLAN-05 | description-surface-economy | staged |
| PLAN-06 | compaction-anchor-pointer | staged |
| PLAN-07 | pbt-standard-liveness | staged |
| PLAN-08 | hard-rule-enforcement-tier-survey | staged |

A row still `staged` or `parked` here was live work that did not finish before the close. It
is a lead, not a queue entry: nothing emits it any more.

## Carried into `live-blockers`

- Nothing from this epic is staged in `live-blockers`.

## Leads carried forward, not staged

- The medium- and low-priority items found in this epic are listed with evidence in
  `.plan/orchestrator/live-blockers/backlog.md`. They are unstaged.
- `epic.md` § Open Defects (3 entries) and § Watches (6 entries) are frozen as they
  stood. Entries not named above or in that backlog were judged to be design input for the
  rewrite, refactors or measurements of machinery the rewrite replaces, or already fixed.
- Design input for plan-marshall-mcp lives in that repository's requirements, specification
  and `doc/implementation-watch/` documents. Ledger pointers to
  `plan-marshall-mcp/doc/known-defects/…-carry-over.md` name a path that no longer exists.
- **The queue below says `staged` for PLAN-01 to PLAN-08, but they were parked as superseded by plan-marshall-mcp in #1643.** #1641 reverted that and the restore was never done. None of them should be emitted.
- `PLAN-07` (property-based-testing standard never adopted) and `PLAN-03` (per-model calibration decision) are ready and concern domain-skill content and the generator; see `backlog.md` §§ 4.9 and 4.10.

### Inbox messages undrained at close

- `inbox/other-approaches-001.md`
- `inbox/process-compliance-001.md`

## Decision record

`epic.md` § Decisions is the curated view; `logs/decision.log` is the append-only record. Both
are frozen in this tree.
