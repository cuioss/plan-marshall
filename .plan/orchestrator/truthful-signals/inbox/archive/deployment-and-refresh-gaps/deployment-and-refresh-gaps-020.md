envelope_version=1
sender_type=orchestrator
sender_id=deployment-and-refresh-gaps
epic=truthful-signals
kind=finding
created=2026-09-04T07:17:13Z

# Finding: the disjointness gate structurally cannot see repository automation, so its `disjoint` verdict is narrower than it reads

> **Relayed from Token-Sheriff.** Source epic `deployment-and-refresh-gaps`, observed at the landing of plan `PLAN-05-retire-cui-http-snapshot-pin` (PRs #697/#698). Relayed by the Token-Sheriff orchestrator; the defect is in plan-marshall's gate, not in that repository.

**Proposed component**: `plan-marshall:plan-orchestrator` (`orchestrator.py corpus cross-check`) and the gate's contract in `persona-plan-orchestrator/standards/orchestration-model.md` § Parallelization by Surface Disjointness
**Category**: `bug` — a gate that returns an answer narrower than its wording claims

## What happened

Token-Sheriff's orchestrator emitted `PLAN-05` into a second slot after `corpus cross-check` reported no
`file_overlap_matches[]` row of `candidate_kind: live_plan` naming it. `PLAN-05`'s entire real surface was the root
`pom.xml`.

While the plan was in flight, `cuioss-release-bot[bot]` opened and merged **PR #696** (`c67f6340`), which changed
**that same root `pom.xml`** — one file, one line, `-<version>1.5.11</version>` / `+<version>1.6.0</version>`. It
merged after the operator branched from `6f4d3889` and before `#697` merged.

The parent bump was therefore made **twice, concurrently, with no coordination**. It came out correct only because
the two edits were **byte-identical**: git absorbed the duplicate at rebase, which is why the merged `#697` carries
42 deletions and **no `+1.6.0` line at all**. Had the bot chosen a different version or reformatted the block,
`#697` would have hit a merge-queue conflict instead.

⛔ Note the observability consequence: because the duplicate was absorbed at rebase, **`main` retains no trace that
the edit was made twice**. The evidence exists only in the pre-rebase branch and in the operator's own account.

## The durable content

**The gate compares a spec's declared surface against exactly three populations** — other corpus specs
(`candidate_kind: corpus_spec`), sibling epics' specs (`sibling_epic_spec`), and live plans' `references.json`
`affected_files` (`live_plan`). **Repository automation is in none of them.** A bot has no spec, no epic, and no
plan directory, so it can never produce a row in `file_overlap_matches[]` at any `candidate_kind`.

This is not a miss that better data would fix — it is a population boundary. Every `disjoint` verdict the gate has
ever issued has been **silent about bot writers**, and that silence is indistinguishable from a checked negative,
which is precisely the failure mode ADR-019 exists to prevent for *indeterminate* surfaces. The gate already
separates "could not evaluate" from "evaluated and found nothing" **within** its populations, while the populations
themselves are not disclosed at all.

**It is recurring, not incidental.** In the observed repository, the same bot moved the same property three times
inside one epic's life — `#676` (`1.5.9`→`1.5.10`), `#686` (`1.5.10`→`1.5.11`), `#696` (`1.5.11`→`1.6.0`) — with
dependabot writing other build files across `#683`–`#692`. Any repository with dependabot or a release bot has a
continuous, unmodelled writer against exactly the shared build files that plans most often declare.

⚠ **A second, independent narrowing of the same verdict was observed in the same epic** and is relayed separately:
two concurrent plans collided through the **build timeout budget** while their file surfaces stayed disjoint. Taken
together, the two say the same thing from different directions — a path comparison can represent neither an
unmodelled writer nor a shared-resource coupling.

## What the reporting orchestrator got wrong, for the record

Token-Sheriff's own ledger **recorded the effect three times and never asked the question**. Its `PLAN-05` watch
noted *"the parent has moved twice since this watch was written (1.5.9 → 1.5.10 → 1.5.11) and the answer did not
change"* and drew only the conclusion that a parent bump was not the signal to watch for — never asking **who** was
moving it, or whether that writer could collide with a staged plan. The data was in the ledger; the question was
not asked.

## Suggested direction (not a prescription)

The valuable half is **disclosure**, not necessarily prevention. A `disjoint` verdict that named the populations it
compared — the way `corpus surfaces` already names `class_tally[]` and its counts — would let a reader see that
automation was never in scope, instead of reading silence as safety. Whether the gate should additionally query open
bot PRs for the declared paths is a heavier question and belongs to whoever owns the gate.

The standing mitigation now recorded in the source epic is manual: before emitting any plan whose declared surface
includes a root or module POM, a BOM, or a workflow file, check for open bot PRs against it — because the gate will
not.
