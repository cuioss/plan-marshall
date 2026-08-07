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

**Only two states are ever stored**, because only two can be written by a party at a moment when
writing is appropriate:

| Status | Meaning | Derivable from |
|---|---|---|
| `open` | Staged in the orchestrator; no cloud plan authored | No `doc/plans/{epic}/{cloud-plan}/` directory |
| `authored` | A plan exists in the cloud tree, not yet collected | The directory exists with `plan.md` |

**A collected plan has no row at all** — its row is removed, and its directory with it (§ Path 3).
The ledger is a queue of *open work*, not an archive: the durable record of a landed plan is its PR,
its merge commit, and the orchestrator's landing record.

`implemented` and `ingested` were formerly stored and are now **derived observations only**, made by
the orchestrator at collect time. They were retired as stored values because *nothing could write
them honestly*: this file is git-tracked, so every stamp is a commit and a PR, and the moment a run
could assert `implemented` — after its merge read-back — its branch is already merged and deleted.
The stamp then required a **second PR for a one-word change**, which is how one such PR consumed
scarce bot-review budget on a pure bookkeeping diff. Removing the state removed the PR.

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

**A run never writes to `LEDGER.md` at all.** Its outcome goes in its run report, and the
orchestrator reads the report at collect. This is deliberate:

1. **The stamp was unperformable where it was specified.** A run can only assert `implemented` after
   its merge read-back — and by then its branch is merged and deleted, so the write needs a *second
   PR for a one-word change*. One such PR spent scarce bot-review budget on a pure bookkeeping diff.
2. **It removes the only shared file two concurrent runs both wrote.** With no run touching the
   ledger, an epic's runs cannot collide there at all — better than the single-row-edit discipline it
   replaces, which merely made collisions rarer.
3. **It puts the write where the corroboration is.** The orchestrator is the party that verifies the
   merge, so it is the party that should record it — the same principle the rest of this document
   applies to every other transition.

What a run owes instead: the report states the PR, the merge commit, and the outcome per deliverable,
including a run that ended **blocked or partial** and why. An overstated outcome is worse than an
understated one — the first is collected as done, the second is picked up again.

## Path 3 — Collect

Reconciling landed cloud plans back into the orchestrator. Done locally, per epic, via that epic's
orchestrator.

1. **Find the landed plans.** Every `authored` row whose PR has merged is ready to collect; the run
   report names the PR. There is no `implemented` marker to read — see § Status vocabulary.
2. **Corroborate each one before recording it.** For each: confirm the PR is merged (`state: MERGED`
   with a real `mergedAt`), confirm the merge commit is an **ancestor of `origin/main`**, and read
   the run report at `doc/plans/{epic}/{cloud-plan}/report-NN.md`. It is a lead until all three
   agree. A landing claim — including a PR number — has been wrong here before.
3. **Read the report's findings section**, not only its outcome line. A run that landed can still
   have surfaced defects, rejected findings with reasons, refuted a deliverable, grown beyond its
   stated scope, or left contract residue — that is the part the orchestrator would otherwise lose.
   Route anything not belonging to this epic through the normal cross-epic path; do not fold it
   silently, and record a routing recommendation as a recommendation until the edit exists.
4. **Transition the orchestrator plan** to `shipped` and stamp its PR through the orchestrator's own
   queue verb — never by hand-editing `status.json`.
5. **Write the landing record** at `landings/{ORCH-PLAN-ID}.md` in the epic tree. Once step 6 removes
   the cloud plan and its report, this record plus the PR is the durable account — so it carries the
   outcome per deliverable, any refuted premise, the findings routed out, and any contract gap the
   run exposed.
6. **Remove the cloud plan from the doc path** — delete `doc/plans/{epic}/{cloud-plan}/` entirely,
   plan and reports together, and regenerate the ledger so the row drops out (§ Regenerating a
   ledger). `doc/plans/` is a queue of open work, not an archive; the removed content stays in git
   history, and step 5 holds what a reader actually needs.
7. **Regenerate the epic's START-HERE block** and update `resume_anchor`.

Steps 4–7 are one unit: if the transition fails, nothing is removed. The removal in step 6 and the
ledger regeneration are one commit, so the tree never shows a plan with no row or a row with no plan.

**That commit is documentation-only, so it carries `--label skip-bot-review` at creation.** Bot review
capacity is contended across this repository, and a bookkeeping diff has nothing to offer a reviewer.
The general rule: **a PR that changes no source gets no bot review.**

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
