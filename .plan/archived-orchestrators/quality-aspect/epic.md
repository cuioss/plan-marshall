# Epic: Quality-aspect — measurement integrity, gate residuals, and ledger joins

slug: quality-aspect

> Ledger document for one epic under `.plan/orchestrator/quality-aspect/`. The layout
> and authority contract live in the central standard — see
> `persona-plan-orchestrator/standards/orchestration-model.md`. `status.json` is the
> machine authority; any statement here that conflicts with it is stale prose.

## Vision

The finalize-machinery epic retired the defects; the measurements that would prove the
retirement are themselves untrustworthy. Across its seven landings the same structural
gap recurred in four guises: costs summed from ledgers that barely pair, gates deciding
on counts published without their populations, verdicts anchored to trees nobody
re-checks, and reviewer-value signals biased in both directions at once. Each existing
fix is local; none makes the quality instrumentation honest as a whole. This epic makes
every derived number in the finalize lane carry its population, every gate re-verify
what it certifies, and every ledger join on a key instead of a time window. Too large
for one plan: it spans cost attribution, gate residuals, ledger joins, footprint timing,
and reviewer-value signals. Done looks like a retrospective whose every figure states
the population it was computed over, a merge gate that cannot certify a tree it did
not see, and ledgers that pair by construction rather than by audit.

## START HERE

<!-- GENERATED BLOCK — never hand-write or hand-edit this section.
     Regenerate after every queue-touching state change via:
     python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator resume-summary --slug quality-aspect
     Paste the returned `summary` block verbatim between the markers (the same
     invocation also emits `ordered_queue` for the Ordered Queue section below).
     Anything a reader wants to add BY HAND goes in the annotation zone below,
     outside the markers — never inside them. -->

<!-- BEGIN GENERATED: resume-summary -->
**Resume anchor**: epic closed — merged into truthful-signals, see history.md
**Phase**: closed
**Inbox (derived)**: 0 queued, 9 archived
**Queue** (staged, in order):
- (empty)
<!-- END GENERATED: resume-summary -->

### Annotations

<!-- ANNOTATION ZONE — hand-written, and deliberately OUTSIDE the generated markers. -->

- **Scaffolded 2026-09-18, NOT yet decomposed.** Next action is
  `/plan-orchestrator decompose slug=quality-aspect`, working from the inherited
  material below. `parallelization_scope` is 2 (operator overrode the project default
  1 — measurement/ledger surfaces are expected to decompose disjointly).
- **Source of truth for the material below:** the epic-owned copies under
  `finalize-machinery/lessons/{id}.md` (see that epic's `lessons/index.md` for the
  coverage map) plus the corpus originals retained there. Decompose re-verifies every
  claim against the implementing source (verify-first contract) — inherited text is a
  lead, never a premise.
- **Deliberately excluded:** shipped fixes (PLAN-01..07 remedies — referenced, never
  re-staged); rule-following/process-compliance material (owned by the
  process-compliance epic); the session-identity resolver itself (shipped as PR #1530).

## Ordered Queue

<!-- GENERATED BLOCK — never hand-write or hand-edit the table between the markers.
     Regenerated from status.json and the staged specs: emitted as `ordered_queue` by
     orchestrator.py resume-summary --slug quality-aspect, and rewritten in place by the
     compact stage at cleanup. Only the LIVE queue is rendered here. Per-row notes a reader
     wants to ADD go in the annotation zone below, outside the markers. -->

<!-- BEGIN GENERATED: ordered-queue -->
| # | Plan | Workstream | Status | Surface (expected) |
|---|------|------------|--------|--------------------|
| — | (empty) | — | — | — |
<!-- END GENERATED: ordered-queue -->

### Queue annotations

<!-- ANNOTATION ZONE — hand-written, and deliberately OUTSIDE the generated table markers. -->

- **Standing emit convention (operator direction 2026-09-19).** Every emitted
  `/plan-marshall` command appends the line: "Comply strictly to the process
  rules. All issues with the process rules, file into
  `.plan/orchestrator/process-compliance/inbox`". Applies to all commands
  emitted from this point forward, including re-emits.

- 17 retained staged plans from the 2026-09-19 full-corpus ingestion (18 staged
  minus transferred PLAN-16; see `lessons-disposition.md` for the per-cluster
  record). Sequencing: PLAN-03
  before PLAN-04; PLAN-05 before PLAN-06; PLAN-10 before PLAN-11/12; PLAN-17
  before PLAN-18 and after PLAN-01/03. All surfaces parse declarative
  (corpus surfaces, 18/18 admitting).
- **Transfers out 2026-09-19 (operator direction):** test-fidelity cluster (G19 +
  G29 + 3 singletons, 9 lessons) → test-quality PLAN-180 (WS-01, staged);
  process contracts (8 lessons) → process-compliance PLAN-08 (WS-03, staged).
  PLAN-14 reshaped 8→6, PLAN-15 reshaped 8→2 (config guards; filename kept for
  row continuity), PLAN-16 retired (spec removed, row retired). 17 retained.
  Disposition: `lessons-disposition.md` § Transfers out.
- **Reconsideration 2026-09-19 post-move (cross-check 17/17 declarative, 181
  overlap rows):** no structural changes. WS-09 stays a legitimate single-plan
  workstream (dissolving has no sanctioned row-delete form and config guards fit
  nowhere else cleanly). Sequencing additions: PLAN-13 sequences after live
  test-quality PLAN-177 (`close-the-leftover-gate-gaps`, RUNNING — real overlap
  on plugin-doctor test-conventions files, the one live collision); PLAN-18
  shares tools-integration-ci with process-compliance PLAN-08 (cross-epic
  awareness, no gate impact). All other sibling overlaps are
  terminal-vs-live (inert). Live indeterminates (NO_PLAN, phase-gates) never
  render as disjoint.

## Decisions

- **Epic opened 2026-09-18 at operator direction** ("make a new epic, quality-aspect
  for this and similar open issues"), split out of finalize-machinery at that epic's
  completion. finalize-machinery retires defects; this epic owns what the retirements
  cannot prove — the honesty of the instruments. Scope N=2 per operator answer
  (concurrent, against the project default 1).
- **parallelization_scope=2** (operator answer, 2026-09-18): the cost/gate/ledger
  surfaces are expected to decompose into disjoint contract areas; the `next` gate
  still sequences any pair whose declared surfaces intersect.
- **Full-corpus ingestion 2026-09-19 at operator direction** (all 173 active lessons;
  per-cluster-primary ground truth; remove-in-this-run): charter widened from the
  Inherited Material slice to the whole corpus — the dated-epic convention set
  aside at operator direction. `aggregate` first pass: 31 groups (146 lessons) +
  27 singletons; 0 stale; 2026-09-05-14-002 excluded as superseded. Ground truth:
  DEEP on G04/G09/G30 (+CODE on G15/G30), TRIAGE on the rest with
  verify-at-outline clauses in every spec. Removal was file-level (operator's
  explicit file-ops authorization) rather than per-lesson `remove`: 161 calls was
  disproportionate and 12 YAML-frontmatter lessons are unreachable by id-keyed
  verbs at all — audit trail is `lessons-disposition.md` + `lessons-archive/` +
   decision log, not tombstones. Corpus now holds only the superseded stub.
- **Cross-epic transfers 2026-09-19 at operator direction** (sibling-tree writes
  explicitly authorized): test-fidelity cluster → test-quality PLAN-180 (WS-01,
  staged, with Execution Contract; WS-01 scope names both surfaces verbatim);
  process contracts → process-compliance PLAN-08 (WS-03, staged; basetemp
  single-owned by PLAN-180). Detached here: PLAN-14 reshaped 8→6, PLAN-15
  reshaped 8→2, PLAN-16 spec removed and row retired.
- **Queue-write deviation (logged, no concurrency):** retiring the PLAN-16 row has
  no sanctioned single-row form (queue verbs offer no delete; bulk rewrite is
  reserved for seed-from-nothing), and no closed status fits a moved plan — so
  the row was retired via a whole-array rewrite, twice (second pass fixing a
  PLAN-14 workstream typo my first pass introduced: WS-06→WS-07 restored).
  Justification: single operator session, fresh pre/post reads (18→17 verified),
  no concurrent writer on this epic.   Pre/post row sets verified identical minus
  PLAN-16.
- **Store migration mid-session (#1575, 2026-09-21):** epic trees moved
  `.plan/local/orchestrator/` → tracked `.plan/orchestrator/` (this epic +
  test-quality; archived epics → `.plan/archived-orchestrators/`). All session
  state verified carried over intact (18 queue rows, 173 lessons-archive files,
  2 landings, inbox archives, logs). Scripts resolve the tracked store; all
  subsequent ledger paths use it. The plan-07 inbox message arriving at the new
  path is the migration working, not a write-boundary breach.
- **Cross-machine reconciliation 2026-09-19 (response.09-19.md, truthful-signals
  checkout):** treated as leads, verified against this tree, 9 shipped-in-tree
  deliverables retired (specs + summary.md updated, surfaces re-derived 17/17
  declarative, no plan emptied, queue unchanged): transcript-less policy (P01),
  mutex reclaim (P02), verdict_inputs surface (P04), footprint capture (P07),
  transcript-less log/session/anchor trio (P11), round stamping + metrics re-close
  (P17). Kept — verified absent here: context-load plumbing, VERIFY emission,
  archive receipt, passage re-review, merge-queue proof, re-fire split, churn
  accounting, per-build ledger rows, plan_creation_sha, LC_ALL pinning, per-file
  assessments, freshness verdicts, chat-signal retention. Sibling-only verdicts
  (review-apparatus, code-intelligence-substrate) do not apply to this store.

## Inherited Material — the decompose input

⛔ **This is a hand-off record, not a queue.** Nothing below is staged. Every item is
OBSERVED in a shipped plan's run; each names its evidence in the epic copy. Decompose
turns these into workstreams and specs. Likely workstream cuts: (1) COST ATTRIBUTION —
ledger joins, context-load producers, enrich placement; (2) GATE RESIDUALS — verdict
currency comparison, loop-back accounting, staleness assertions; (3) REVIEWER VALUE —
yield instruments, refusal currency, ETA handling; (4) FOOTPRINT & BARRIER HYGIENE —
capture timing, metadata reconciliation, halt reporting.

### Cost attribution (the numbers don't join)

1. **Ledger rows barely pair** (`02-13-002`, three plans, ~40% pairing): execution-log
   vs dispatch-boundary ledgers share no key (no step_id); equal-size ledgers disagree
   by a third (23 vs 23, union 36). Proposed: step_id join key, render union_rows,
   trace unwritten boundaries.
2. **Context-load producer gap** (`07-13-009`, `08-25-09-004`): optional flags, zero
   callers — measure dark as `unmeasured` (half landed); producer still missing; enrich
   never scheduled (plus session-capture precondition `04-14-006`).
3. **Re-fire cost drivers** (`08-25-09-007`, `13-12-002`, `03-11-007`, `08-13-005`):
   productive vs unproductive re-firing unseparated; no round budget; passage-scope vs
   line-scope fixes; footprint-kind gating unconsumed. (Mechanism half retired by
   PLAN-01 anchor; this is the measurement/policy remainder.)
4. **Build telemetry gaps** (`08-25-09-009`, `04-17-005`, `13-12-004`): daemon path
   writes no rows / attribution lost to NO_PLAN / direct path 1:60; empty-stderr
   failures unclassifiable.

### Gate residuals (verdicts that don't re-verify)

5. **Verdict_inputs comparison** (`04-17-001`): currency classifier invalidates on any
   HEAD advance for lack of a declared surface — opt-in compare-vs-invalidate.
6. **Loop-back accounting** (`06-10-001`, `09-09-01-002`): ceiling counts productive
   with unproductive; out-of-band override skips re-arm; loop-back re-entry drops
   metrics windows (exact 429,730-token gap).
7. **Staleness assertions** (`08-25-09-002` outcome vocabulary; `11-006` halt
   reporting; `08-13-001` archive-plan self-enforcement; `08-13-002`
   mutates_source sync): findings-bearing rounds read as waste; silent halts;
   the one step that destroys its own record store; declarations drifted from behavior.

### Reviewer value (signals biased both ways)

8. **Yield instruments** (`03-07-003`, `08-13-011`, `06-07-001`, `03-16-004`):
   per-source yield unrecorded; sustained zero contribution invisible; 35%
   undercounts; refuted claims bucketed as accepted — no trustworthy reviewer-value
   signal either direction.
9. **Refusal currency** (`08-13-003`, `04-17-002`, `08-25-09-013`): unscoped refusals
   re-assert; size-cap wordings unrecognized at FIND; status bodies block the barrier.
   (Recognition half retired by PLAN-03; this is the currency/scope remainder.)
10. **ETA handling** (`07-13-006`, `09-13-09-001`, `08-13-008`): phrase-bound patterns,
    default overshoot, unpersisted deadlines.

### Footprint & barrier hygiene

11. **Capture timing** (`08-25-09-001`, `08-25-09-010`, `04-14-007`, `07-13-004`,
    `14-05-003`, `04-14-008`, `07-15-004`): post-removal capture, stale-base diffs,
    missing creation SHA, retired-key consumers, empty-excerpt records, worktree-aware
    resolution, stacked-PR rebase discipline.
12. **Three-valued evidence + doc truth** (`09-03-06-001`, `07-13-005`): bool carrying
    three states; worked examples never executed against their runtime.

## Open Defects

{Populated as this epic's own landings surface defects. The inherited set above is decompose
input, not this epic's observations.}

- None from PLAN-01's landing (#1545): 10/10 per PR body + inbox facts; the two
  planning-time process-compliance findings were operator-exempted, not defects.
- **Incomplete inbox landing (plan-09-outline-sweep-001.md, recorded not
  reconciled-as-if-complete):** narrative only, missing all 9 facts-block keys;
  reconciled via the operator paste + landings/PLAN-09.md instead. Corroborates
  (12 deliverables, 9 files). Discrepancy noted: message lists 4
  process-compliance findings, the paste 5 — the 5th (post-archive artifact)
  postdates the message. A manual paste from this plan could still surface a
  required fact the inbox did not.
- **Incomplete inbox landing (plan-07-footprint-surface-001.md, recorded not
  reconciled-as-if-complete):** narrative only, missing all 9 facts-block keys;
  reconciled via landings/PLAN-07.md instead. Corroborates (8 deliverables, 9
  files, verify green). A manual paste from this plan could still surface a
  required fact the inbox did not.

## Watches

- **The inherited set is open by construction.** Every item above is a retained-open
  lesson (corpus originals live; epic copies under finalize-machinery/lessons/). As
  plans ship, their housekeeping retires the covered lessons — the index to watch is
  that epic's `lessons/index.md` plus the corpus tombstone record.
- **Transcript-less token totals unmeasured (from PLAN-01's landing).** Known
  mechanism (gap flag), not a new defect: re-check if a transcript-capable target
  ever reports the same unmeasured totals.
- **Executor runs Claude-cache scripts under opencode (operator-observed
  2026-09-20, analyzed same day).** `.plan/execute-script.py` was generated for
  target=claude: SCRIPTS, PYTHONPATH, bootstrap dirs, and the fallback resolver
  all point at `~/.claude/plugins/cache/plan-marshall/*/`, refreshed only by the
  Claude-pipeline sync. Measured fresh today (0.1.1719 == HEAD, mtime 30 min
  after HEAD), but nothing in opencode runtime refreshes it — repo advances
  without a sync finalize execute stale scripts against current docs. The fresh
  opencode skill tree (`~/.config/opencode/skills/`, verified identical) is
  bypassed entirely. Fix belongs to steward/executor target selection, not to
  any staged plan here.

- **Epic closed 2026-09-21 (orchestrator restructuring pass): merged into
  `truthful-signals`.** Same "confident signal hides a caveat" defect archetype,
  scoped to the finalize lane — lane-scoping alone did not warrant a separate
  ledger. All 18 rows renumbered PLAN-204..221 to avoid id collision with
  truthful-signals' own PLAN-01..19 range; 3 shipped rows archived to
  `truthful-signals-26-09-21`, 15 staged rows joined the live truthful-signals
  queue as workstreams WS-QA-01..09. Full disposition table in `history.md`.
