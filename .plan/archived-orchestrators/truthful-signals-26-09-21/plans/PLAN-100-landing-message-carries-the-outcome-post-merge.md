# PLAN-100: The landing message is emitted pre-merge and carries no outcome, so the epic still needs an operator paste

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> See `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

A plan's `kind: landing` inbox message is emitted **before the merge**, so it names an *intention*
rather than an outcome: no merge state, no commit sha, no deliverable fidelity, no cost, no
operational residue. The orchestrator therefore still depends on an operator pasting the finalize
report to reconcile a landing. Move the landing emission to the post-merge side and give it the
outcome content, so the inbox is a self-sufficient outcome channel — **without letting it become a
trusted one.**

## Mechanism — OBSERVED, orchestrator-verified first-party at HEAD

- The `kind: landing` message is emitted by **`finalize-step-lessons-capture`**
  (`phase-6-finalize/workflow/lessons-capture.md:91`, Branch B4), where it is documented as
  **unconditional** (`:233` — *"the `kind: landing` message is unconditional"*).
- **`lessons-capture` runs BEFORE `branch-cleanup`**, and `branch-cleanup` is the step that merges.
  That ordering is the entire defect: the landing message is written while the PR is still open.
- ⭐ **A post-merge inbox writer already exists.** `plan-retrospective` (which also writes inbox
  messages) runs **after** `branch-cleanup`. On PR #1034 its messages were created **31 minutes
  after** the landing message. **So the channel already supports post-merge emission — the landing
  message is simply on the wrong side of the merge.** This is a re-ordering problem, not a new
  capability.

## Evidence from PR #1034

- Landing message created `14:41:25Z`, naming *"PR #1034"* — **no merge state, no sha.** The merge
  commit `89fd4d1f6` was obtained by the orchestrator from `git log`, not from the channel.
- The message never states the ship's most important fact: that the `archive_conflict` refusal and
  `samefile` inode discrimination were left **byte-for-byte unchanged**. Deliverable fidelity is
  absent from the channel entirely.
- Cost (2.7M tokens / 3h01m, over the error anchor on both axes) — absent.
- The `git worktree remove` timeout and its **non-force** recovery, a third sighting that answers an
  open standard question — absent.
- ⭐ **The message asserted its own batch size and was wrong.** It said *"two lesson-bearing
  observations … in this same batch"*; the batch reached **eight**, because `plan-retrospective` had
  not run yet. **A landing message's account of its own batch is a snapshot, not an enumeration** —
  the sample-read-as-enumeration archetype, inside the channel built to carry findings.

## Deliverables

1. **D1 — GATE (mutates nothing): choose the emission site and settle the split.** Decide whether the
   landing message *moves* post-merge or whether `lessons-capture` keeps a pre-merge message and a new
   post-merge step emits the outcome. ⚠ **Name the failure mode of each:** a moved message is not
   emitted at all if finalize halts before the merge, which may be worse than an early one. Settle
   what the channel should carry when a plan **never merges** — a landing message that can only ever
   describe success is the epic's archetype in the channel itself.
2. **D2 — the landing message carries the outcome.** Merge state and commit sha, deliverable fidelity
   (what shipped versus the spec, including what was deliberately left unchanged), the finalize-step
   outcome set, cost against the anchor, and operational residue (timeouts, repairs, force usage).
   ⚠ **Budget it** — this must not become a transcript. Paths and counts, not prose.
3. **D3 — remove the batch self-description.** The message MUST NOT assert how many sibling messages
   accompany it; it cannot see messages written after it. Replace with nothing — the drain enumerates.
4. **D4 — tests, verified to FAIL pre-fix.** (a) A landing message emitted for a merged PR carries the
   sha. (b) A plan whose finalize halts pre-merge produces the D1-decided behaviour, not a false
   landing. (c) No landing message asserts a sibling count.

Four deliverables, under the split guard.

## ⛔ The constraint that matters most — do not make the channel trusted

**Enriching the landing message must not weaken the orchestrator's corroboration duty.** `analyze.md`
Step 2 and Step 4 are explicit that a message is a **lead, not a fact**, and that PR number, merge
state, and deliverable set are corroborated against `git` and the read-side `ci` abstraction **before**
any ledger write.

A richer, more confident landing message makes skipping that verification *more* tempting and its
absence *less* visible — the failure would look like a smooth reconciliation. **D2 must not add any
field that reads as authoritative**, and the work MUST NOT relax Step 2/Step 4. If anything, the
enriched message should carry its claims **labelled as the plan's own report**.

⚠ Concretely: on PR #1034 the plan's self-report was accurate, **but the epic's standing rule still
required running `ci pr comments` directly — and doing so found that Sourcery has a second refusal
phrasing #1021 does not recognize.** The channel would not have surfaced that. **Automating the paste
must not automate away the check.**

## Claim Labels

- OBSERVED (orchestrator-verified 2026-07-28): the emission site and its unconditional wording at
  `lessons-capture.md:91` / `:233`.
- OBSERVED: `lessons-capture` precedes `branch-cleanup`; `plan-retrospective` follows it — read from
  the PR #1034 finalize step sequence.
- OBSERVED: message 001's creation time, its lack of sha/merge state, and its incorrect batch count —
  read first-party from `inbox/archive/inbox-sequence-reuse-collides-with-the-archive-001.md`.
- HYPOTHESIS: the composed finalize step order is configurable enough to place a post-merge emitter
  without disturbing `branch-cleanup` / `archive-plan` — confirm/refute at the
  `manage-execution-manifest` composed order (verify-at-outline). **If refuted, D1's "new step" arm
  is unavailable and the move arm is forced.**
- HYPOTHESIS: no consumer currently relies on the landing message arriving pre-merge — confirm/refute
  by enumerating readers of `kind: landing` (verify-at-outline). **An asserted absence: verify it.**
- Verify-first clause: re-read `lessons-capture.md` at HEAD before scoping. If a landing has since
  moved the emission, this plan is REFUTED — close it rather than re-implementing.

## Expected Surface

- OBSERVED: `phase-6-finalize/workflow/lessons-capture.md` — Branch B4, `:91`, `:233`, `:253`.
- HYPOTHESIS: a new or relocated finalize step definition + its manifest registration
  (verify-at-outline).
- HYPOTHESIS: `marshall-orchestrator/standards/inbox-envelope.md` — only if the `landing` payload
  shape becomes contractual (verify-at-outline).
- OBSERVED: tests under `test/plan-marshall/phase-6-finalize/**` and
  `test/plan-marshall/marshall-orchestrator/**`.

**Disjointness:** `phase-6-finalize` (+ possibly `marshall-orchestrator` docs).
⚠ **BLOCKED while PLAN-92 runs** — its D8 puts `phase-6-finalize` in an in-flight surface.
⚠ Overlaps **PLAN-64** (finalize step observability) and **PLAN-52**/**PLAN-60** in the same bundle —
sequence, do not pair. ⚠ Touches `marshall-orchestrator`, so **PLAN-49 stays after it**.

## Dependencies and Sequencing

- Depends on: none, but **cannot be emitted while PLAN-92 is in flight**.
- Overlaps with: PLAN-64, PLAN-52, PLAN-60 (same bundle), PLAN-94 (orchestrator docs).
- Adjacent to: PLAN-99 — its cost measurement is a natural source for D2's cost field. **Do not
  duplicate a cost computation; consume whatever PLAN-99 lands, or state plainly that D2 ships a
  placeholder until it does.**

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-100-landing-message-carries-the-outcome-post-merge.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and
edits NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message —
the orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. See `persona-marshall-orchestrator/standards/orchestration-model.md`
§ Ledger Write-Boundary.
