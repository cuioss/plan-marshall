# PLAN-PR-010: The landing message is emitted pre-merge and carries no outcome

epic: review-apparatus
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Provenance — re-issued from `truthful-signals` PLAN-100. ⭐ Now infrastructure.

Released to this epic on 2026-07-30 (row `transferred` there, verified against its live queue). Under
this epic's `PLAN-PR-NNN` rule **no id travels**: this is a re-issue, not a rename.

⭐ **This plan became infrastructure when the dispatcher arrangement was created on 2026-07-30.**
`truthful-signals` is now a dispatcher that forwards PR-related landings to this epic, and that routing
only works if a landing message can carry a post-merge outcome. Until this lands, **the sibling must
attach the outcome BY HAND to every forwarded PR-related landing** — a standing manual tax on the new
arrangement, and the reason this ranks far above its original position.

✅ **Its recorded blocker is DISCHARGED.** The released spec says "BLOCKED while PLAN-92 runs" and lists
PLAN-99 as a source for its cost field. Both have since shipped — PLAN-92 as `#1041`, PLAN-99 as `#1043`
(verified against that epic's live queue, not from its prose). D2 can therefore consume PLAN-99's cost
measurement rather than shipping a placeholder.

## ⛔⛔ THE DELEGATION WAS NOT ACCEPTED — THIS PLAN IS OURS. Verified 2026-08-08.

The epic ledger carried this row as *"HANDED OVER 08-02 — do NOT start"*, delegated to
`truthful-signals` as `review-apparatus-013`, with the note *"retire the row if they accept."*
**They did not accept, and the ledger was never reconciled.** Verified first-party against that epic's
live `status.json`:

- Their `PLAN-100` (`landing-message-carries-the-outcome-post-merge`) still reads **`status:
  transferred`** — i.e. transferred **to us**. It was never re-opened.
- **No `PLAN-TRUTH-*` row owns this subject.** Their 115-row queue was scanned for every adjacent slug
  (`landing`, `finalize-step`, `order`, `capture`, `retrospective`, `stale`); the nearest members are
  `PLAN-TRUTH-066` (the retrospective reads a record not yet written — the 995-before-998 read-order
  defect) and the **superseded** `PLAN-TRUTH-052`. Neither is this.
- Their release message (`truthful-signals-001`) handed PLAN-100 over with *"⭐ **This one is now
  infrastructure for the dispatcher arrangement** … Suggest you rank it early."*

⇒ ⛔ **A row parked on an unaccepted hand-off is worse than an unowned one: it reads as owned and is
not.** For six days nobody was working this, and the ledger said that was fine. ⭐ **The delegation
protocol needs a positive acknowledgement — an offer is not a transfer.** Recorded as an epic-level
method rule, not just a correction to this row.

⚠ **And the cost of the gap is ongoing and paid by the sibling**: until this lands, they must attach the
outcome **by hand** to every forwarded PR-related landing. That tax has been running the whole time the
row said "do not start."

## Objective

A plan's `kind: landing` inbox message is emitted **before the merge**, so it names an *intention* rather
than an outcome: no merge state, no commit sha, no deliverable fidelity, no cost, no operational residue.
The orchestrator therefore still depends on an operator pasting the finalize report to reconcile a
landing. Move the landing emission to the post-merge side and give it the outcome content, so the inbox
is a self-sufficient outcome channel — **without letting it become a trusted one.**

## Mechanism — OBSERVED, orchestrator-verified first-party at HEAD

- The `kind: landing` message is emitted by **`finalize-step-lessons-capture`**
  (`phase-6-finalize/workflow/lessons-capture.md:91`, Branch B4), where it is documented as
  **unconditional** (`:233` — *"the `kind: landing` message is unconditional"*).
- **`lessons-capture` runs BEFORE `branch-cleanup`**, and `branch-cleanup` is the step that merges. That
  ordering is the entire defect: the landing message is written while the PR is still open.
- ⭐ **A post-merge inbox writer already exists.** `plan-retrospective` (which also writes inbox messages)
  runs **after** `branch-cleanup`. On PR `#1034` its messages were created **31 minutes after** the
  landing message. **So the channel already supports post-merge emission — the landing message is simply
  on the wrong side of the merge.** This is a re-ordering problem, not a new capability.

## Evidence from PR #1034

- Landing message created `14:41:25Z`, naming *"PR #1034"* — **no merge state, no sha.** The merge commit
  `89fd4d1f6` was obtained by the orchestrator from `git log`, not from the channel.
- The message never states the ship's most important fact: that the `archive_conflict` refusal and
  `samefile` inode discrimination were left **byte-for-byte unchanged**. Deliverable fidelity is absent
  from the channel entirely.
- Cost (2.7M tokens / 3h01m, over the error anchor on both axes) — absent.
- The `git worktree remove` timeout and its **non-force** recovery, a third sighting that answers an open
  standard question — absent.
- ⭐ **The message asserted its own batch size and was wrong.** It said *"two lesson-bearing observations
  … in this same batch"*; the batch reached **eight**, because `plan-retrospective` had not run yet.
  **A landing message's account of its own batch is a snapshot, not an enumeration** — the
  sample-read-as-enumeration archetype, inside the channel built to carry findings.

## ⚠ ABSORBED 2026-08-09 — a third D0 member, from the PR-body side

Source: `truthful-signals-026` item 1. ⛔ **Second-hand, NOT re-derived — a lead.**

**`create-pr` silently truncates the Intent section mid-sentence and drops the Non-goals paragraph.**

⭐ **Two losses in one step, and they differ in DETECTABILITY** — which is what makes this a D0 member
rather than a formatting bug: a mid-sentence truncation is **visible** to a human reader, while a
dropped Non-goals paragraph is **not** — nothing in the rendered PR body indicates a section was ever
there.

⇒ **The reviewer's scope information is the part that vanishes without a trace.** That bears directly
on whether a review can be judged complete: a reviewer who never saw the Non-goals cannot be faulted
for reviewing outside them, and a completeness judgement made against the rendered body is made against
a silently truncated statement of intent. ⇒ Add `create-pr`'s rendered body to D0's population of
finalize artifacts that assert a claim which can go stale or arrive incomplete.

## Deliverables

0. ⭐ **D0 — GATE (mutates nothing), ADDED 2026-07-30: DERIVE the population of finalize artifacts that
   snapshot a still-moving fact.** ⛔ **The landing message is a SAMPLE, not the population** — a second
   instance surfaced the same day on a different surface (below), so a fix scoped to the landing message
   alone leaves the class open. Enumerate every finalize-phase artifact that (a) is generated at a fixed
   step, (b) asserts a claim about PR/review/merge state, and (c) is **not regenerated after a loop-back**.
   For each, record whether its claim can go stale between generation and merge. Non-empty and derived;
   the two known members are named below and are the floor, not the list.

   **Known member 2 — `review-retrospective.md` (operator-reported on `#1067`, 2026-07-30, and
   corroborated first-party).** Generated at **11:46**, it asserts CodeRabbit **"never reviewed this
   diff."** ⭐ **That was TRUE when written and FALSE by merge**: CodeRabbit's review is timestamped
   **13:35:43Z** with 5 actionable findings (orchestrator-verified via `pulls/1067/reviews`), and the
   step was never regenerated after the loop-back. The operator caught it at finalize step 20/25 and
   regenerated by hand.
   ⛔ **The recursion is the point: `finalize-step-review-retrospective`'s entire job is to compare the
   PR's reviewers — and it shipped a false claim about a reviewer.**
   ⚠ **The concrete harm is a MIS-SCORING, not just a stale sentence.** A consumer trusting that artifact
   would conclude CodeRabbit was absent ⇒ *no baseline* ⇒ score the run **"unassessable"**, when the true
   verdict is a **5 : 0 deficit against a real baseline**. Those are opposite conclusions about the
   required bot's efficacy. ⭐ This epic's own `findings/PR-1067.md` survived only because it was scored
   from the **API**, never from the artifact — which is itself the standing rule (`ci pr comments` /
   provider state is the sole evidence of participation), now shown to protect against our own tooling.

1. **D1 — GATE (mutates nothing): choose the emission site and settle the split.** Decide whether the
   landing message *moves* post-merge or whether `lessons-capture` keeps a pre-merge message and a new
   post-merge step emits the outcome. ⚠ **Name the failure mode of each:** a moved message is not emitted
   at all if finalize halts before the merge, which may be worse than an early one. Settle what the
   channel should carry when a plan **never merges** — a landing message that can only ever describe
   success is this project's archetype in the channel itself.
2. **D2 — the landing message carries the outcome.** Merge state and commit sha, deliverable fidelity
   (what shipped versus the spec, including what was deliberately left unchanged), the finalize-step
   outcome set, cost against the anchor, and operational residue (timeouts, repairs, force usage).
   ⚠ **Budget it** — this must not become a transcript. Paths and counts, not prose. Consume PLAN-99's
   shipped cost measurement (`#1043`); **do not duplicate a cost computation.**
3. **D3 — remove the batch self-description.** The message MUST NOT assert how many sibling messages
   accompany it; it cannot see messages written after it. Replace with nothing — the drain enumerates.
3b. ⭐ **D3b — a staleable finalize artifact is REGENERATED after a loop-back, or it declares its
   as-of point.** For every member D0 derives, exactly one of two remedies, chosen per member and
   justified: **regenerate** after the loop-back (correct when the artifact is cheap and its claim is
   load-bearing — `review-retrospective.md` is the clear case, since a false reviewer claim inverts a
   scoring verdict), or **stamp an explicit as-of** (`generated_at` + the HEAD it describes) when
   regeneration is disproportionate, so a reader can see the claim is a snapshot rather than a verdict.
   ⛔ **A silent snapshot is the defect** — an artifact that reads as current while describing a
   superseded state. ⚠ Do NOT default every member to regeneration: a full regenerate on each loop-back
   re-runs review comparison work whose cost this epic has already measured
   (see PLAN-PR-007's `#1064` figures).

   ⭐⭐ **A SHARPER formulation arrived 2026-07-30 (inbox `code-intelligence-substrate-004` § 2) — adopt it
   over the wording above, which it subsumes:**

   > *A persisted artifact describing external state must carry **the HEAD it describes**, and any
   > consumer must compare that HEAD against the current one before trusting it.*

   `review-retrospective.md` carries **no HEAD stamp at all** — which is precisely why its staleness is
   **invisible on inspection**. A HEAD stamp turns a silent snapshot into a checkable one even when
   regeneration is declined, so it is the floor for every D0 member; regeneration is the additional
   remedy where the claim is load-bearing.

   **Two further correctives from the same source, both stronger than a per-instance fix:**

   1. ⭐ **Derive the metrics from the append-only store, not from live bot state.** Compute
      `reviewer_count` / `total_findings` / per-author rows from
      `manage-findings list --type pr-comment` — a deterministic query over an append-only store that
      **cannot go stale**. ⛔ This removes the staleness **class**, not one instance, and is the single
      highest-value item in this plan.
   2. **Mark artifact-producing finalize steps `loop-back-dirty`.** Any step whose output is a persisted
      document describing PR or review state must re-run when the plan re-enters `6-finalize`, even though
      its prior `outcome=done` stands. ⚠ **The step roster currently treats `outcome=done` as terminal —
      correct for idempotent steps, wrong for artifact producers.** That distinction is the fix.

   ⛔ **The contradiction this produced is internal to ONE plan directory, and the block labelled
   *authoritative* is the one that was wrong:**

   | Source | Claim |
   |---|---|
   | `status.json` → `phase_steps[6-finalize].automatic-review` | coderabbit reviewed, 5 findings fixed |
   | `review-retrospective.md` | coderabbit *"never reviewed this diff … zero signal of any kind"* |
   | `manage-findings list --type pr-comment` | **7 records, 6 authored by `coderabbitai`** |
   | `review-retrospective.md` § *"Deterministic Metrics (**authoritative**, not recomputed)"* | `total_findings: 1`, `reviewer_count: 1` |

   ⭐⭐ **This is the epic's theme running in REVERSE, and it is why the sender handed it over rather than
   keeping it.** Every other instance catalogued here is a confident **GREEN** concealing a caveat. This is
   a confident **RED** — emphatic, bolded, correctly reasoned — that **became false while sitting on
   disk**. The failure mode is not "too confident for its evidence"; it is *"exactly as confident as its
   evidence warranted, and then the world moved."* ⚠ A future auditor reading the archived plan takes it
   at face value.

4. **D4 — tests, verified to FAIL pre-fix.** (a) A landing message emitted for a merged PR carries the
   sha. (b) A plan whose finalize halts pre-merge produces the D1-decided behaviour, not a false landing.
   (c) No landing message asserts a sibling count.

Four deliverables, under the split guard.

## ⛔ The constraint that matters most — do not make the channel trusted

**Enriching the landing message must not weaken the orchestrator's corroboration duty.** `analyze.md`
Step 2 and Step 4 are explicit that a message is a **lead, not a fact**, and that PR number, merge state,
and deliverable set are corroborated against `git` and the read-side `ci` abstraction **before** any
ledger write.

A richer, more confident landing message makes skipping that verification *more* tempting and its absence
*less* visible — the failure would look like a smooth reconciliation. **D2 must not add any field that
reads as authoritative**, and the work MUST NOT relax Step 2 / Step 4. If anything, the enriched message
should carry its claims **labelled as the plan's own report**.

⚠ Concretely: on PR `#1034` the plan's self-report was accurate, **but the standing rule still required
running `ci pr comments` directly — and doing so found that Sourcery has a second refusal phrasing
`#1021` does not recognize.** The channel would not have surfaced that. **Automating the paste must not
automate away the check.**

## ⭐ FOURTH confirmation, and it re-scopes the fix (inbox `truthful-signals-005`, 2026-07-30)

- OBSERVED (sibling-verified against `origin/main`, not from the message): the plan behind **`#1065`**
  emitted a `kind: landing` message asserting **"PR: #1065" under a "What landed" heading** while `#1065`
  is **open** and absent from `origin/main`. They caught it by corroborating rather than trusting, and
  did **not** transition the plan to shipped.
- ⛔ **This is the FOURTH confirmation of the archetype in that epic's ledger** (`PLAN-92`/`#1041` was an
  earlier one). Four sightings is a population, not an anecdote.
- ⭐⭐ **It re-scopes the deliverable, and this is the part to carry:** the message is **not merely missing
  an outcome field — it ASSERTS a landing in its prose while the PR is open.** A consumer reading the
  message *text* rather than the PR state concludes wrongly, and appending a correct `outcome:` field
  beside a false sentence leaves the false sentence there. ⛔ **The fix must change the message's CLAIM,
  not only append an outcome.** A spec that only adds a field would satisfy its own tests and leave the
  observed defect live — the confident-prose-beside-a-correct-field shape this epic is named after.

## ⭐⭐ ABSORBED 2026-08-09 — the FIRST LIVE MULTI-EMISSION INSTANCE, and it is this plan's whole thesis

Source: `orchestrator inbox list --slug review-apparatus`, read first-party by the orchestrator while
analysing PLAN-PR-022's landing. **Not a report claim — the messages are on disk.**

`generic-charter-language-specific-defect` (PLAN-PR-022) emitted **THREE `landing` messages**:

| Message | Written | What had happened by then |
|---|---|---|
| `-006` | 17:04:41Z | finalize completed — host PR merged, **four foreign branches pushed with NO PRs** |
| `-012` | 17:52:24Z | the four foreign PRs had been opened but not merged |
| `-013` | 18:38:03Z | all five merged (last at 18:36:29Z) |

⭐⭐ **Only `-013` can be authoritative, and NOTHING IN THE CHANNEL SAYS SO.** A drain that consumed
`-006` first would reconcile the epic against an outcome in which three of eight deliverables shipped
nowhere — and would do so from a message that is valid, well-formed, and indistinguishable from a
final one at the envelope layer.

⇒ **This is the sharpest possible statement of the defect**: the landing message does not merely carry
a stale outcome, it carries *a sequence of outcomes with no supersession marker*, and the channel's
append-only invariant guarantees all of them survive to the drain.

⛔ **The scope widens accordingly.** "Carry the outcome post-merge" is necessary but not sufficient —
a plan that only delays the message until post-merge still emits three of them if the run believes it
finished three times. The deliverable is **either** explicit supersession in the envelope **or** a
composition point that cannot fire before the outcome is final. ⚠ Prefer the second: a supersession
marker leaves the drain to reconcile a sequence, which is work this channel exists to avoid.

⭐ **DELIVERABLE MOVED IN, 2026-08-09.** The *one landing message per landing* deliverable was drafted
into PLAN-PR-023 and moved here at staging, because this plan already owns the subject. PR-023 keeps
the mechanism that produced the premature outcomes (foreign-task done-ness measured at the commit);
**this plan owns the message.** ⚠ Shared root cause worth carrying in both: *an outcome declared final
before it was.*

## Claim Labels

- OBSERVED (orchestrator-verified 2026-07-28): the emission site and its unconditional wording at
  `lessons-capture.md:91` / `:233`.
- OBSERVED: `lessons-capture` precedes `branch-cleanup`; `plan-retrospective` follows it — read from the
  PR `#1034` finalize step sequence.
- OBSERVED: message 001's creation time, its lack of sha/merge state, and its incorrect batch count —
  read first-party from `inbox/archive/inbox-sequence-reuse-collides-with-the-archive-001.md`.
- OBSERVED (re-verified at this epic's drain): PLAN-92 shipped `#1041` and PLAN-99 shipped `#1043`, so the
  released spec's "BLOCKED while PLAN-92 runs" note is discharged and its cost-field dependency is
  available.
- HYPOTHESIS: the composed finalize step order is configurable enough to place a post-merge emitter
  without disturbing `branch-cleanup` / `archive-plan` — confirm/refute at the `manage-execution-manifest`
  composed order (verify-at-outline). **If refuted, D1's "new step" arm is unavailable and the move arm is
  forced.**
- HYPOTHESIS: no consumer currently relies on the landing message arriving pre-merge — confirm/refute by
  enumerating readers of `kind: landing` (verify-at-outline). **An asserted absence: verify it.**
- Verify-first clause: re-read `lessons-capture.md` at HEAD before scoping. **If a landing has since moved
  the emission, this plan is REFUTED — close it rather than re-implementing.**

## ⚠ Split-guard note (2026-07-30)

This spec now carries **six** deliverables (D0, D1, D2, D3, D3b, D4) and sits at the presumptive split
threshold. **Proceeding unsplit, with the rationale recorded** as the guard requires: D0 is a
mutates-nothing derivation that *scopes* D3b, and D3b's remedy is the same mechanism as D2's (both are
"the artifact must state what is actually true at the moment it is read"). Splitting would put a
population derivation in one plan and its only consumer in another, which is the coupling the guard
exists to avoid, not the coupling it exists to break. ⛔ **If D0's derivation returns more than ~2
additional staleable artifacts, STOP and split along artifact boundaries** — at that point the plan is a
sweep, not a fix, and the split guard applies for real.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/lessons-capture.md` —
  Branch B4, `:91`, `:233`, `:253`.
- HYPOTHESIS: a new or relocated finalize step definition + its manifest registration (verify-at-outline).
- OBSERVED (added 2026-07-30, D0's second member): the `finalize-step-review-retrospective` skill — the
  generator of `review-retrospective.md` — and its position in the finalize step order relative to the
  loop-back re-entry point. ⚠ Re-ground by heading/symbol. ⛔ The orchestrator could NOT read the artifact
  itself (`.plan/local/plans/` is outside its carve-out), so the staleness is the operator's first-party
  report — but **the refuting timestamp is orchestrator-verified**: `pulls/1067/reviews` has CodeRabbit
  `COMMENTED` at 13:35:43Z against an 11:46 generation. Confirm the step's regeneration behaviour against
  the implementing source at outline.
- HYPOTHESIS: `.../marshall-orchestrator/standards/inbox-envelope.md` — only if the `landing` payload
  shape becomes contractual (verify-at-outline).
- OBSERVED: tests under `test/plan-marshall/phase-6-finalize/**` and
  `test/plan-marshall/marshall-orchestrator/**`.

## Dependencies and Sequencing

- Depends on: none. ✅ The released spec's PLAN-92 blocker is discharged (shipped `#1041`).
- ⚠ **Sibling ids renamed 2026-07-30**: `PLAN-113` → **`PLAN-TRUTH-001`**, `PLAN-52` →
  **`PLAN-TRUTH-006`**. Use the TRUTH ids when re-deriving against their live queue; the old ids below
  are retained as the historical reference.
- Overlaps with: ⚠ `truthful-signals` **PLAN-113** (`gates-do-not-refire-over-the-loop-back-diff`) is on
  `phase-6-finalize` and is **retained there deliberately** — `code-intelligence-substrate` has already
  written the PLAN-113 → PLAN-121 sequencing into its ledger as a hard constraint. Do not assume this epic
  can take it. Sequence around it; re-verify at outline by SLUG.
- Overlaps with: ⚠ `truthful-signals` **PLAN-52** (retained) is in the same bundle, different file.
- Overlaps with: ⚠ **PLAN-PR-011** touches `phase-6-finalize` gate standards. Sequence.
- Adjacent to: **PLAN-PR-008** / **PLAN-PR-009**, both on `branch-cleanup.md`. This plan edits
  `lessons-capture.md` and the step order — adjacent, and the step-order change must not disturb
  `branch-cleanup`'s position.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/review-apparatus/plans/PLAN-PR-010-landing-message-carries-the-outcome-post-merge.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/local/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
