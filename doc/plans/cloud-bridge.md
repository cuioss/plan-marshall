# Cloud bridge — create, sync, collect

The rule governing the relationship between an **orchestrator plan spec** (machine-local, under
`.plan/local/orchestrator/{epic}/plans/`) and a **cloud plan** (git-tracked, under
`doc/plans/{epic}/`). It applies identically to all three epics — `truthful-signals`,
`review-apparatus`, `code-intelligence-substrate` — each of which keeps its own row set in
`doc/plans/{epic}/LEDGER.md`.

It exists because the two halves cannot see each other. The orchestrator ledger is git-ignored, so a
cloud session never sees it; a cloud session's working state is destroyed when its VM is reclaimed,
so the orchestrator never sees that either. The only shared medium is **git**. Everything below is
about keeping one fact — *where is this plan?* — legible from both sides through that medium alone.

## The two authorities, and which wins

| Question | Authority |
|---|---|
| Is this plan queued, running, shipped, superseded, transferred? | The orchestrator's `status.json` |
| Has a cloud plan been authored for it, did it land, where is its report? | `doc/plans/{epic}/LEDGER.md` |

Neither overwrites the other. **A disagreement between them is a finding**, surfaced at ingest and
resolved by reading the ground truth (the PR, the merge state, the files on disk) — never by copying
one side onto the other. A row claiming `implemented` whose PR is not merged is a false signal, and
the whole point of this bridge is that such a claim is checkable.

## Status vocabulary

Four states, in order. Each has a derivation that does not depend on the row's own prose:

| Status | Meaning | Derivable from |
|---|---|---|
| `open` | Staged in the orchestrator; no cloud plan authored | No `doc/plans/{epic}/{cloud-plan}/` directory |
| `authored` | A plan exists in the cloud tree, not yet landed | The directory exists with `plan.md` |
| `implemented` | Its PR is merged | PR `state: MERGED` with a real `mergedAt` |
| `ingested` | The orchestrator has reconciled it back into `status.json` | The orchestrator plan row is `shipped` |

`open` and `implemented` are the two that matter operationally — the first says *available to pick
up*, the second says *ready to collect*. The middle and final states exist so a plan in flight and a
plan already absorbed are not both reported as one of those two.

## Path 1 — Create

Turning an orchestrator plan spec into a cloud plan. Done locally, where both trees are visible.

1. **Pick an `open` row** from `doc/plans/{epic}/LEDGER.md`. The `Cloud plan` column already carries
   the intended directory name — it is the orchestrator plan's own slug, so the mapping stays stable
   without anyone inventing a second name.
2. **Read the orchestrator spec** at `.plan/local/orchestrator/{epic}/plans/{ORCH-PLAN-ID}-*.md`.
3. **Author the cloud plan** at `doc/plans/{epic}/{cloud-plan}.md` from
   [`_template/plan.md`](_template/plan.md), carrying across: the problem and its mechanism, the
   deliverables, the out-of-scope boundary, the expected surface, and **every claim label**. A
   `HYPOTHESIS` in the orchestrator spec stays a `HYPOTHESIS` in the cloud plan, with its
   confirm/refute artifact intact — a premise does not become established by being copied.
4. **Do not delete the orchestrator spec.** It stays as the source record. The cloud plan is a
   derived artifact, and the ledger row is what ties them together.
5. **Set the row to `authored`** and commit the plan and the row together, so the tree never shows a
   plan with no row or a row with no plan.

The plan must reach `origin/main` before a cloud session can see it — a cloud VM clones from GitHub,
not from the machine that wrote the file.

## Path 2 — Sync

Executing the plan in a cloud session, and recording the outcome where the orchestrator will find it.

The run itself is governed entirely by the `cloud-plan-lane` skill; this section covers only the
bridge obligations layered on top:

1. **Stamp the row at the start** — status stays `authored`; nothing to change.
2. **On merge, set the row to `implemented`** and fill the `PR` and `Report` columns. Edit **only
   this plan's own row**. The ledger is shared across an epic's plans, so a whole-table rewrite
   turns every concurrent run into a merge conflict; a single-row edit does not.
3. **The stamp is a claim, not the outcome.** It is written after the merge is confirmed by reading
   PR state back (`state: MERGED` with a real `mergedAt`), never after a merge command reports
   success. This repository has seen a merge call report success, delete the branch, and not merge.
4. **A row is never set to `ingested` by a cloud run.** That transition belongs to the orchestrator
   alone, and a run that sets it is asserting something it cannot observe.

If the run ends blocked or partial, leave the row at `authored` and say why in the run report. A row
that overstates progress is worse than one that understates it: the first is collected as done, the
second is picked up again.

## Path 3 — Collect

Reconciling landed cloud plans back into the orchestrator. Done locally, per epic, via that epic's
orchestrator.

1. **Read the ledger** and take every row marked `implemented`.
2. **Corroborate each one before recording it.** For each row: confirm the PR is merged, confirm the
   merge commit is an ancestor of `origin/main`, and read the run report at
   `doc/plans/{epic}/{cloud-plan}/report-NN.md`. A row is a lead until all three agree. A landing
   claim — including a PR number — has been wrong here before.
3. **Read the report's findings section**, not only its outcome line. A run that landed can still
   have surfaced defects, rejected findings with reasons, or contract residue, and those are the
   part the orchestrator would otherwise lose. Route anything not belonging to this epic through the
   normal cross-epic path; do not fold it silently.
4. **Transition the orchestrator plan** to `shipped` and stamp its PR, through the orchestrator's own
   queue verb — never by hand-editing `status.json`.
5. **Set the ledger row to `ingested`.**
6. **Regenerate the epic's START-HERE block** and update `resume_anchor`.

Steps 4–6 are one unit. A row marked `ingested` whose orchestrator plan is still `staged` is exactly
the drift this bridge is meant to make impossible, so if the transition fails, the row does not move.

## Regenerating a ledger

`open` rows are generated from the orchestrator queue rather than maintained by hand, so a newly
staged plan appears without anyone transcribing it. Regeneration **preserves every row carrying
cloud-leg state** (anything past `open`) and rewrites only the `open` ones. A row whose orchestrator
plan has left `staged` drops out of the table — its state lives in `status.json`, which is where a
reader is sent rather than being given a stale copy here.

## What this bridge deliberately does not do

- **It does not sync automatically.** Every transition is written by a party that can observe it:
  the author on create, the run on merge, the orchestrator on ingest.
- **It does not make the orchestrator ledger visible to the cloud.** A cloud session works from the
  plan and this bridge alone; it never reads epic state, and never writes into
  `.plan/local/orchestrator/`.
- **It does not carry the queue.** Ordering, dependencies, surface-disjointness, and parallelization
  remain the orchestrator's, because they are decisions about the epic rather than about one plan.
