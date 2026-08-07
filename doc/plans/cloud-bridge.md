# Cloud bridge — create, sync, collect

The rule governing the relationship between an **orchestrator plan spec** (machine-local, under
`.plan/local/orchestrator/{epic}/plans/`) and a **cloud plan** (git-tracked, under
`doc/plans/{epic}/`). It applies identically to all three epics — `truthful-signals`,
`review-apparatus`, `code-intelligence-substrate`.

It exists because the two halves cannot see each other. The orchestrator ledger is git-ignored, so a
cloud session never sees it; a cloud session's working state is destroyed when its VM is reclaimed,
so the orchestrator never sees that either. The only shared medium is **git**. Everything below is
about keeping one fact — *where is this plan?* — legible from both sides through that medium alone.

## The two authorities, and which wins

| Question | Authority |
|---|---|
| Is this plan queued, running, shipped, superseded, transferred? | The orchestrator's `status.json` |
| Has a cloud plan been authored, has a run started, did it produce a report? | The `doc/plans/{epic}/` tree itself |
| Did it land, and where? | The PR and its merge commit — read back, never assumed |

Neither authority overwrites the other, and **neither is a stored claim about the other**: the second
is a directory listing and the third is git. That is deliberate. An earlier design kept a written
status column, and the whole class of failure it invited — a row asserting `implemented` for a PR
that never merged — simply cannot be expressed now. **A disagreement between `status.json` and the
tree is a finding**, surfaced at ingest and resolved against ground truth, never by copying one side
onto the other.

## Status vocabulary

**There is no status file. The filesystem is the state**, and it needs no maintenance to stay true:

| What you see under `doc/plans/{epic}/` | State |
|---|---|
| No file for the plan | Not handed to the cloud lane — it is open in the orchestrator only |
| `{cloud-plan}.md`, a flat file | **Authored**, awaiting a run |
| `{cloud-plan}/plan.md` | **A run has started** — Step 3 of the contract moved it into its directory |
| `{cloud-plan}/report-NN.md` alongside it | That run produced a report; the report names its PR |
| Nothing — the directory is gone | **Collected.** The orchestrator has ingested it (§ Path 3) |

This replaced a per-epic `LEDGER.md` that stored the same states as rows. That file was **retired**,
and the reason generalises: **every column it carried was derivable, so it was a cache** — and a
cache of derivable facts drifts the moment someone forgets to regenerate it, in a project whose
recurring defect is a stale artifact read as evidence. Its `open` rows were generated from
`status.json`; its `implemented`/`ingested` columns could not be written honestly by anyone (a run's
branch is merged and deleted by the time it could assert a landing, so the stamp needed a second PR
for a one-word change — one such PR spent scarce bot-review budget on a bookkeeping diff); and its
`PR` and `Report` columns were consequently never filled at all.

The one function it appeared to serve — showing open work where `status.json` is invisible — was
also illusory: **plans are handed to a cloud session, not browsed by it.** The operator picks the
plan on the machine where `status.json` already is.

## Path 1 — Create

Turning an orchestrator plan spec into a cloud plan. Done locally, where both trees are visible.

1. **Pick a staged plan** from the epic's own queue (`orchestrator queue --slug {epic}`), and name the
   cloud plan after **the orchestrator plan's own slug**. Reusing that slug is what keeps the mapping
   stable in both directions without anyone inventing a second name or recording one anywhere.
2. **Read the orchestrator spec** at `.plan/local/orchestrator/{epic}/plans/{ORCH-PLAN-ID}-*.md`.
3. **Author the cloud plan** at `doc/plans/{epic}/{cloud-plan}.md` from
   [`_template/plan.md`](_template/plan.md), carrying across: the problem and its mechanism, the
   deliverables, the out-of-scope boundary, the expected surface, and **every claim label**. A
   `HYPOTHESIS` in the orchestrator spec stays a `HYPOTHESIS` in the cloud plan, with its
   confirm/refute artifact intact — a premise does not become established by being copied.
4. **Do not delete the orchestrator spec.** It stays as the source record; the cloud plan is a derived
   artifact, and the shared slug is what ties them together.
5. **Commit and push it.** The file's existence *is* the `authored` state — there is nothing else to
   record.

The plan must reach `origin/main` before a cloud session can see it — a cloud VM clones from GitHub,
not from the machine that wrote the file.

## Path 2 — Sync

Executing the plan in a cloud session, and recording the outcome where the orchestrator will find it.

The run itself is governed entirely by the `cloud-plan-lane` skill; this section covers only the
bridge obligations layered on top:

**A run records its outcome in exactly one place: its own run report**, inside its own plan
directory. It writes no status anywhere else, and there is no shared file for it to write to. Two
consequences worth stating, because both were bought by removing one:

1. **Two concurrent runs in one epic share no file at all**, so they cannot collide over bookkeeping.
   The earlier design had them editing one row each in a common table, which made collisions rarer
   rather than impossible.
2. **Nothing needs writing at the one moment a run cannot write.** A run could only assert a landing
   after its merge read-back — by which time its branch is merged and deleted — so the write required
   a second PR for a one-word change, and one such PR spent scarce bot-review budget on a bookkeeping
   diff.

What a run owes instead: the report states the PR, the merge commit, and the outcome per deliverable,
including a run that ended **blocked or partial** and why. An overstated outcome is worse than an
understated one — the first is collected as done, the second is picked up again.

## Path 3 — Collect

Reconciling landed cloud plans back into the orchestrator. Done locally, per epic, via that epic's
orchestrator.

1. **Find the landed plans.** List `doc/plans/{epic}/` — every **directory** is a plan a run has
   worked, and the `report-NN.md` inside names its PR. A directory whose PR has merged is ready to
   collect. There is no status marker to read anywhere; see § Status vocabulary.
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
   plan and reports together. That removal *is* the state change; nothing else records it.
   `doc/plans/` is a queue of open work, not an archive: the content stays in git history, and step 5
   holds what a reader actually needs.
7. **Regenerate the epic's START-HERE block** and update `resume_anchor`.

Steps 4–7 are one unit: if the transition fails, nothing is removed.

**That commit is documentation-only, so it carries `--label skip-bot-review` at creation.** Bot review
capacity is contended across this repository, and a bookkeeping diff has nothing to offer a reviewer.
The general rule: **a PR that changes no source gets no bot review.**

## What this bridge deliberately does not do

- **It does not store status anywhere.** Each state is the presence or shape of a file, so it cannot
  go stale and no one has to remember to update it. The states that *cannot* be derived — is this
  plan queued, shipped, superseded? — belong to `status.json` and are not mirrored here.
- **It does not make the orchestrator ledger visible to the cloud.** A cloud session works from the
  plan and this bridge alone; it never reads epic state, and never writes into
  `.plan/local/orchestrator/`. A plan is **handed** to a cloud session, not browsed by it — which is
  why no index of open work is needed on this side.
- **It does not carry the queue.** Ordering, dependencies, surface-disjointness, and parallelization
  remain the orchestrator's, because they are decisions about the epic rather than about one plan.
