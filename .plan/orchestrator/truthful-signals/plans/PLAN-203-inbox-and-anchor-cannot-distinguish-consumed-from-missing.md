# PLAN-203: The inbox and the resume anchor cannot distinguish consumed from missing

epic: truthful-signals
workstream: WS-01

## Objective

`orchestrator inbox validate` returns `file_not_found` for a message that was **consumed and
archived**, identically to one that was **never written**. Combined with a hand-written inbox count in
the resume anchor, this made a healthy epic look like a data-loss incident and cost a plan a full
investigation to disprove. Make consumed, missing, and empty distinguishable, and derive the anchor's
counts instead of narrating them.

⭐ **This is the epic's own theme, in the epic's own tooling, caught by a plan reading the epic's own
ledger.** It is filed here rather than forwarded because the surface is `marshall-orchestrator` — ours.

## What happened (first-party, PLAN-109 retrospective, verbatim)

Running from the main checkout after `branch-cleanup`, three reads looked like data loss:

```
$ orchestrator inbox list --slug truthful-signals
count: 0

$ orchestrator inbox validate --slug truthful-signals --message manage-lessons-mixes-local-time-and-utc-001.md
error: file_not_found

$ orchestrator inbox validate --slug truthful-signals --message code-intelligence-substrate-004.md
error: file_not_found
```

`lessons-capture` had reported 5 messages delivered, and the epic's resume anchor asserted
**"INBOX: 18 queued"** and named `code-intelligence-substrate-004` as **"still queued UNARCHIVED and
undispositioned"**. The obvious hypothesis — messages written into a worktree-scoped store and
destroyed with the worktree — **fit every symptom.**

⭐ **It was wrong, and the disproof is the elegant part.** Writing the next message returned
`manage-lessons-mixes-local-time-and-utc-006.md`. **The allocator issued 006, so it can see 001–005.**
They exist, in `inbox/archive/`. Nothing was lost, the store path was correct, and `count: 0` was
truthful.

## The two defects

**(a) `inbox validate` collapses archived and never-written into one error.** An archived message is a
*consumed* message with a known location; a never-written one is *missing data*. They demand opposite
responses — "this was handled" versus "this was lost".

**(b) The resume anchor's inbox count is hand-written prose that drifted from derived state.** The
anchor claimed 18 queued and named a specific message as unarchived; the derived reader said 0 and
that message was archived.

⛔ **Defect (b) is the orchestrator's own, and it is confirmed.** The anchor was written *before* a
drain and never re-derived after it. The epic's standing rule — *"re-derive counts from status.json,
never from the rendered block"* — **applies one level up and was not applied**: the anchor's own
narrative counts must be re-derived from `inbox list`, not carried forward as prose. ⭐ **The anchor
was stale in the CONFIDENT direction**: it asserted pending work that had already been drained.

## Deliverables

1. **D1 — `inbox validate` resolves the archive.** On a miss in `inbox/`, check `inbox/archive/` and
   return a distinct `status: archived` with `archive_path` — never `file_not_found`. ⚠ Keep
   `file_not_found` meaning *present at neither path*, so the two stay distinguishable.
2. **D2 — `inbox list` states which kind of zero it means.** Report the resolved inbox directory, and
   distinguish `inbox_missing` / `epic_not_found` from a genuinely empty queue. ⭐ Same rule this epic
   has now recorded five times: **a zero meaning "could not look" and a zero meaning "looked, found
   nothing" must not share a representation.**
3. **D3 — `resume-summary` derives the inbox counts.** Render queued/archived counts from the inbox at
   read time, **separately from the operator's narrative anchor**, so a stale sentence cannot outrank a
   live count. ⛔ **Do not solve this by asking the orchestrator to remember to update prose** — that
   is the discipline that already failed. The count must be derived at render time or it will drift
   again.
4. **D4 — GATE (mutates nothing): derive the other narrative-vs-derived divergences.** The inbox count
   is one hand-written number in a generated-adjacent surface. ⛔ **Treat it as a SAMPLE** — enumerate
   what else the anchor and the START-HERE block assert that a reader could instead derive (queue
   counts, launched counts, PR states). Anything derivable is a drift candidate.
5. **D5 — tests, each verified to FAIL pre-fix.** (a) `validate` on an archived message returns
   `archived`, not `file_not_found`. (b) `validate` on a never-written message still returns
   `file_not_found`. (c) `list` distinguishes an empty queue from a missing inbox directory. (d)
   `resume-summary`'s inbox count matches `inbox list` when the narrative anchor disagrees.

## Claim Labels

- OBSERVED (first-party, PLAN-109 retrospective, commands and outputs quoted verbatim): the three
  reads; the `006` allocation that disproved the data-loss hypothesis; `count: 0` being truthful.
- OBSERVED (orchestrator, self-confirmed): the resume anchor asserted 18 queued and named
  `code-intelligence-substrate-004` as unarchived while both were already drained and archived. **The
  orchestrator wrote that anchor before the drain and did not re-derive it after.**
- HYPOTHESIS: the inbox count is the only hand-written count that has drifted — **confirm/refute at
  D4. Assume it is not.**
- ⚠ Establish every site by SYMBOL — `_orchestrator_inbox.py` changed on 2026-07-29 (#1057).

## Expected Surface

- OBSERVED: `marshall-orchestrator/scripts/_orchestrator_inbox.py` (`inbox validate`, `inbox list`)
- HYPOTHESIS: the `resume-summary` renderer (verify-at-outline)
- OBSERVED: `marshall-orchestrator/SKILL.md` § Canonical invocations — the error-code contracts for
  both verbs, updated in lock-step
- OBSERVED: `test/plan-marshall/marshall-orchestrator/**`

## Dependencies and Sequencing

- Depends on: none.
- ⚠ Overlaps with **PLAN-TRUTH-015** (`rename-marshall-orchestrator-to-plan-orchestrator`, staged; was
  PLAN-49) — same bundle, and a rename would collide with every file this touches. **Sequence: this
  first**, or the rename absorbs it.
- Adjacent to: the sibling's PLAN-CIS-011 (ex-PLAN-121) dispatch-observability work — different surface, same
  "artifact must state its own limits" principle.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-203-inbox-and-anchor-cannot-distinguish-consumed-from-missing.md"
```

## Write-Boundary

This plan MUST NOT create or edit any file under `.plan/local/orchestrator/`. Its only channels back
to the epic are its PR and its `inbox/` OUTBOX.
