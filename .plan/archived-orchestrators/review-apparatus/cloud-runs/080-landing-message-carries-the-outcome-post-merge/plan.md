> ⛔ **FIRST INSTRUCTION — do not skip, do not delete, do not move below the title.**
>
> Before reading the rest of this plan and before any other action, load the working contract that
> governs this run:
>
> ```text
> Skill: cloud-plan-lane
> ```
>
> It owns the branch/PR/review-comment cycle, the build gate, the pre-PR verification sub-agent, the
> run report, and the closing self-check. **Nothing in this plan overrides it** — where this plan and
> the contract disagree, the contract wins, and the disagreement is reported.
>
> If the skill cannot be loaded, **stop and report the run blocked**. Do not reconstruct the workflow
> from this file: the parts that matter most — the merge gate, the verification dispatch, the report
> — are not in here.
>
> This block is part of the plan, not part of the template. It survives into every copy.

# A finalize artifact asserts a claim about PR state and is never regenerated, so it reads as current while describing a superseded world

**Epic:** review-apparatus
**Branch prefix:** fix

## Problem

A plan's `kind: landing` inbox message is emitted **before the merge**, so it names an *intention*
rather than an outcome: no merge state, no commit SHA, no deliverable fidelity, no cost, no operational
residue.

**The mechanism is an ordering, not a missing capability.** The landing message is emitted by
`finalize-step-lessons-capture`, documented there as *unconditional* — and `lessons-capture` runs
**before** `branch-cleanup`, which is the step that merges. ⭐ A post-merge inbox writer already exists
(`plan-retrospective` runs *after* `branch-cleanup`, and on one PR its messages were created 31 minutes
after the landing message), so **the channel already supports post-merge emission; the landing message
is simply on the wrong side of the merge.**

**Three observations widen this from "a missing field" into a class:**

1. ⛔ **The message ASSERTS a landing in its prose while the PR is open.** One message stated *"PR:
   #NNNN"* under a **"What landed"** heading while that PR was open and absent from `origin/main`. ⇒
   **Appending a correct `outcome:` field beside a false sentence leaves the false sentence there.** The
   fix must change the message's **claim**, not only append an outcome — otherwise the plan satisfies
   its own tests and leaves the observed defect live.
2. ⛔⛔ **One plan emitted THREE `landing` messages** as its outcome kept changing — at finalize
   completion (host PR merged, four foreign branches pushed with **no** PRs), then after those PRs were
   opened, then after all five merged. **Only the last can be authoritative, and nothing in the channel
   says so.** A drain consuming the first would reconcile against an outcome in which three of eight
   deliverables shipped nowhere — from a message that is valid, well-formed, and indistinguishable from
   a final one at the envelope layer. ⇒ The message carries *a sequence of outcomes with no supersession
   marker*, and the channel's append-only invariant guarantees all of them survive to the drain.
3. ⭐ **The message asserted its own batch size and was wrong** — it said "two lesson-bearing
   observations in this same batch"; the batch reached eight, because a later step had not run yet.
   **A message's account of its own batch is a snapshot, not an enumeration.**

⭐⭐ **And the class is bigger than the landing message.** A second finalize artifact,
`review-retrospective.md`, was generated mid-run asserting that a reviewer **"never reviewed this
diff."** That was **true when written and false by merge** — that reviewer's review is timestamped
nearly two hours later with five actionable findings, and the step was never regenerated after the
loop-back.

⛔ **The recursion is the point: the artifact whose entire job is to compare the PR's reviewers shipped
a false claim about a reviewer.** ⚠ And the harm is a **mis-scoring**, not a stale sentence: a consumer
trusting it concludes the reviewer was absent ⇒ *no baseline* ⇒ scores the run **"unassessable"**, when
the true verdict is a **5 : 0 deficit against a real baseline**. Opposite conclusions about the required
bot's efficacy.

⭐⭐ **This is the epic's theme running in REVERSE.** Every other instance is a confident **green**
concealing a caveat. This is a confident **red** — emphatic, correctly reasoned — that **became false
while sitting on disk.** The failure mode is not "too confident for its evidence"; it is *"exactly as
confident as its evidence warranted, and then the world moved."*

## Goal

Every finalize artifact that asserts a claim about PR, review, or merge state either states the HEAD it
describes or is regenerated when that state moves — and the landing message carries a single,
post-merge, outcome-bearing claim that a drain can consume without reconciling a sequence.

## Deliverables

Six. ⚠ **At the split threshold, proceeding unsplit with the rationale recorded**: D0 is a
mutates-nothing derivation that *scopes* D4, and D4's remedy is the same mechanism as D2's (both are
*the artifact must state what is actually true at the moment it is read*). Splitting would put a
population derivation in one plan and its only consumer in another — the coupling the guard exists to
avoid, not the one it exists to break.

0. **D0 — GATE, mutates nothing: DERIVE the population of finalize artifacts that snapshot a
   still-moving fact.** ⛔ **The landing message is a SAMPLE, not the population.** Enumerate every
   finalize-phase artifact that (a) is generated at a fixed step, (b) asserts a claim about PR / review
   / merge state, and (c) is **not regenerated after a loop-back**. For each, record whether its claim
   can go stale between generation and merge.
   Three known members are the **floor, not the list**: the landing message; `review-retrospective.md`;
   and the PR body itself — `create-pr` **silently truncates the Intent section mid-sentence and drops
   the Non-goals paragraph.** ⭐ Those two losses differ in **detectability**, which is what makes the PR
   body a member rather than a formatting bug: a mid-sentence truncation is **visible** to a human
   reader, a dropped Non-goals paragraph is **not** — nothing in the rendered body indicates a section
   was ever there. ⇒ **The reviewer's scope information is the part that vanishes without a trace**, and
   a completeness judgement made against the rendered body is made against a silently truncated
   statement of intent.
   ⛔⛔ **THIS DELIVERABLE CARRIES A HARD SPLIT-AND-STOP CONDITION.** If the derivation returns **more
   than about two additional** staleable artifacts beyond the three named, **STOP, report the derived
   population, and propose the split along artifact boundaries.** At that point the plan is a sweep, not
   a fix, and the split guard applies for real. Do not continue into D1–D5 with a large population.
   *Done when:* the population is derived and published, or the stop condition fires and the split is
   proposed.

1. **D1 — GATE, mutates nothing: choose the emission site and settle the split.** Decide whether the
   landing message *moves* post-merge, or whether `lessons-capture` keeps a pre-merge message and a new
   post-merge step emits the outcome.
   ⚠ **Name the failure mode of each.** A moved message is **not emitted at all** if finalize halts
   before the merge, which may be worse than an early one. Settle what the channel should carry when a
   plan **never merges** — a landing message that can only ever describe success is this project's
   archetype inside the channel itself.
   *Done when:* the choice is made with both failure modes stated, and the never-merges case has a
   defined message.

2. **D2 — the landing message carries the outcome, and its CLAIM changes.** Merge state and commit SHA,
   deliverable fidelity (what shipped versus the spec, **including what was deliberately left
   unchanged**), the finalize-step outcome set, cost against the anchor, and operational residue
   (timeouts, repairs, force usage).
   ⚠ **Budget it — this must not become a transcript.** Paths and counts, not prose.
   ⛔ **Consume the shipped cost measurement; do not duplicate a cost computation.**
   *Done when:* no landing message contains a "What landed" assertion that can be true only if the merge
   happened, unless the merge happened.

3. **D3 — one landing message per landing, and remove the batch self-description.**
   The message MUST NOT assert how many sibling messages accompany it — it cannot see messages written
   after it. Replace with nothing; the drain enumerates.
   ⛔ **Delaying the message until post-merge is necessary but NOT sufficient** — a run that believes it
   finished three times still emits three. The deliverable is **either** explicit supersession in the
   envelope **or** a composition point that cannot fire before the outcome is final. ⚠ **Prefer the
   second**: a supersession marker leaves the drain to reconcile a sequence, which is work this channel
   exists to avoid.
   *Done when:* one landing per landing, proven by a test over the multi-emission shape.

4. **D4 — a staleable artifact is REGENERATED after a loop-back, or it declares its as-of point.**
   ⭐⭐ **The governing formulation, which subsumes the weaker "add a timestamp" version:**

   > *A persisted artifact describing external state must carry **the HEAD it describes**, and any
   > consumer must compare that HEAD against the current one before trusting it.*

   `review-retrospective.md` carries **no HEAD stamp at all**, which is precisely why its staleness is
   **invisible on inspection**. A HEAD stamp turns a silent snapshot into a checkable one even when
   regeneration is declined ⇒ **the stamp is the floor for every D0 member; regeneration is the
   additional remedy where the claim is load-bearing.**
   ⚠ **Do not default every member to regeneration** — a full regenerate on each loop-back re-runs
   review-comparison work whose cost this epic has already measured. Choose per member and justify.
   ⭐ **Two stronger correctives, both preferred over per-instance fixes:**
   1. **Derive the metrics from the append-only store, not from live bot state.** Compute reviewer
      counts, total findings, and per-author rows from the stored `pr-comment` findings — a
      deterministic query over an append-only store that **cannot go stale**. ⛔ This removes the
      staleness **class**, not one instance, and is the single highest-value item in this plan.
   2. **Mark artifact-producing finalize steps `loop-back-dirty`.** Any step whose output is a persisted
      document describing PR or review state must re-run when the plan re-enters finalize, even though
      its prior `outcome=done` stands. ⚠ **The step roster currently treats `outcome=done` as terminal —
      correct for idempotent steps, wrong for artifact producers.** That distinction is the fix.
   *Done when:* every D0 member either carries a HEAD stamp or regenerates, with the choice justified
   per member.

5. **D5 — tests, each verified to FAIL pre-fix.** (a) A landing message emitted for a merged PR carries
   the SHA. (b) A plan whose finalize halts pre-merge produces the D1-decided behaviour, **not** a false
   landing. (c) No landing message asserts a sibling count. (d) A regenerated-or-stamped artifact is
   detectably stale to a consumer that checks its HEAD.

## Out of scope

- ⛔⛔ **Making the channel TRUSTED. This is the constraint that matters most.** Enriching the landing
  message must not weaken the orchestrator's corroboration duty: a message is a **lead, not a fact**,
  and PR number, merge state, and deliverable set are corroborated against git and the CI abstraction
  **before** any ledger write. A richer, more confident message makes skipping that verification *more*
  tempting and its absence *less* visible — the failure would look like a smooth reconciliation. ⇒
  **D2 must not add any field that reads as authoritative**, and the enriched message should carry its
  claims **labelled as the plan's own report**. ⚠ Concretely: on one PR the plan's self-report was
  accurate, **and running the comment fetch directly anyway found a second refusal phrasing the
  detector did not recognise.** The channel would not have surfaced that. **Automating the paste must
  not automate away the check.**
- **Re-running review comparison on every loop-back by default.** Cost-bearing; D4 chooses per member.
- **Making the `landing` payload shape contractual** unless D2 forces it. Touching the envelope schema
  widens the blast radius into the drain.
- **Disturbing `branch-cleanup`'s position in the step order.** The step-order change must leave it
  where it is; other staged plans in this epic depend on that.

## Expected surface

- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/lessons-capture.md` — the landing
  emission site and its unconditional wording.
- A new or relocated finalize step definition plus its manifest registration.
- The `finalize-step-review-retrospective` skill — the generator of `review-retrospective.md` — and its
  position relative to the loop-back re-entry point.
- The `create-pr` body composition site — the Intent truncation and the dropped Non-goals paragraph.
- `.../marshall-orchestrator/standards/inbox-envelope.md` — **only if** the `landing` payload shape
  becomes contractual.
- `test/plan-marshall/phase-6-finalize/**` and `test/plan-marshall/marshall-orchestrator/**`.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The landing message is emitted by `lessons-capture` and documented as unconditional | OBSERVED | `lessons-capture.md`, Branch B4 — read the emission site and the unconditional wording |
| `lessons-capture` precedes `branch-cleanup`; a post-merge inbox writer already exists after it | OBSERVED | The composed finalize step order |
| A landing message asserted "PR: #NNNN" under a "What landed" heading while that PR was open | OBSERVED | Restated here; the message itself is machine-local and not in your clone |
| One plan emitted three `landing` messages with no supersession marker | OBSERVED | Restated here; the messages are machine-local |
| `review-retrospective.md` asserted a reviewer never reviewed, and that reviewer's review is timestamped later with five findings | OBSERVED — the refuting timestamp was verified against the provider API | The step's regeneration behaviour: read the implementing source and confirm whether it re-runs after a loop-back |
| `create-pr` truncates Intent and drops Non-goals | HYPOTHESIS — **second-hand, a lead** | The `create-pr` body composition site — read what it renders, and diff a rendered body against its source sections |
| The composed finalize step order is configurable enough to place a post-merge emitter without disturbing `branch-cleanup` / `archive-plan` | HYPOTHESIS | The composed order in the execution manifest. ⛔ **If refuted, D1's "new step" arm is unavailable and the move arm is forced** |
| No consumer relies on the landing message arriving pre-merge (an asserted **absence**) | HYPOTHESIS | Enumerate readers of `kind: landing`. **Verify it — an asserted absence is the higher-risk half** |
| ⛔ **Verify-first, and it can close this plan**: re-read `lessons-capture.md` at HEAD before scoping | — | **If a landing has since moved the emission, this plan is REFUTED — close it rather than re-implementing it.** Report the refutation as the result |

⚠ **Every count and timestamp here is a lead.** Three messages, eight batch items, 31 minutes, 5 : 0.
**Re-derive anything you assert.**

⛔ **Do not go looking for `.plan/`.** The inbox messages, the plan directories, and the artifacts
described above are git-ignored and **absent from your clone**. Everything needed is restated here.

## Verification

- Full verify; read the payload's `status` / `errors[]`, not the exit code.
- **Every D5 test proven discriminating by mutation**, especially (b) — the halted-finalize case, which
  is the one a naive "move the message later" fix silently breaks.
- **Publish D0's derived population and its size** in the run report, with the derivation method. If the
  stop condition fired, that report *is* the deliverable.
- ⭐ **Cold read, and aim it at the message text — this plan is about a false sentence beside a correct
  field.** Have the pre-PR verification sub-agent read a generated landing message **cold**, for two
  scenarios (merged; finalize halted pre-merge), and answer: *did this plan land? how do I know? what
  should I check before believing it?* If the cold reading concludes "landed" in the halted scenario,
  D2/D3 failed. If it concludes "landed, no further checking needed" in the merged scenario, the
  **do-not-make-the-channel-trusted** constraint was breached.

## Notes

- **Why this ranks high: it is infrastructure, and the gap is being paid for by hand right now.** A
  sibling epic forwards PR-related landings to this one, and that routing only works if a landing
  message can carry a post-merge outcome. Until this lands, **the sibling attaches the outcome by hand
  to every forwarded landing.**
- ⭐ **A method rule this plan produced, worth keeping**: it sat for six days marked *"handed over — do
  not start"* against a sibling that had never accepted it. **A row parked on an unaccepted hand-off is
  worse than an unowned one: it reads as owned and is not.** ⇒ **An offer is not a transfer**;
  delegation needs a positive acknowledgement.
- **The contradiction was internal to one plan directory, and the block labelled *authoritative* was the
  wrong one** — a step record said the reviewer reviewed with findings fixed, the retrospective said it
  never reviewed, the findings store held records authored by it, and the retrospective's section headed
  *"Deterministic Metrics (authoritative, not recomputed)"* under-counted both. ⚠ A future auditor
  reading the archived plan takes the authoritative-labelled block at face value.
- **Sequencing.** Nothing blocks it. ⚠ Overlaps `phase-6-finalize` with other staged plans in this epic
  and with a plan retained in a sibling epic — **sequence, never pair, and re-verify by slug** rather
  than by plan id, since ids have been renumbered.
