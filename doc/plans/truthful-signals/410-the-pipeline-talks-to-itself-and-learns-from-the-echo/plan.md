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

# The pipeline's own PR comments enter the preference corpus, so it learns from its own echo

**Epic:** truthful-signals
**Branch prefix:** fix

## Problem

The preference emitter exists to learn recurring **operator** gate-dispositions and generalise them into
durable architecture hints. **Its corpus admits findings the finalize pipeline itself authored**, so the
pipeline's own control traffic becomes evidence about the pipeline's preferences.

Observed on one run: the emitter aggregates `(module, finding-class, disposition)` recurrences and
promotes any tuple reaching a minimum recurrence — **two**, here. Exactly one tuple cleared:

```text
(default, pr-comment, taken_into_account) — count 2
```

**Both contributing findings were written to the PR by the finalize pipeline itself** — not reviewer
feedback, not operator dispositions:

| Finding | What it actually was |
|---|---|
| one | the orchestrator restoring a paragraph that the PR-creation step had **truncated out of the description** |
| the other | the orchestrator's own **review-trigger comment**, posted to re-engage a bot after a head advance |

The ingest verb takes **every** non-noise PR comment as a finding **regardless of author**. Each was then
*necessarily* disposed as taken-into-account — **neither requests a change** — and **two such disposals
are exactly the default threshold.**

## ⭐⭐ Why this is worse than an ordinary false positive: the signal is SELF-REINFORCING

A promoted hint here would encode a **measurement artifact** — *"unattributed PR comments are routinely
taken into account"* — as a standing preference. And it recurs on **any** plan where the pipeline posts
two or more comments of its own.

> **The more the pipeline talks to itself, the stronger the false preference becomes.**

⛔ **There is no natural ceiling**: the corpus grows with pipeline chattiness, not with operator
judgement, and the resulting hint would then influence the pipeline that produces the traffic.

⛔ **And the recurrence is UNATTRIBUTED.** Neither finding carried a component, so both collapsed into
the fallback bucket — **which is where cross-cutting hints are routed, i.e. the widest-blast-radius sink
available.** ⇒ **The least-attributable evidence lands in the most-general slot.**

⭐ **Note the compounding:** one contributing comment exists **only because** the PR-creation step
truncated a section and dropped a paragraph — a separately-reported defect. **One bug manufactured the
corrective comment that became evidence for a false preference.**

⭐ **The guard held on the run that found this.** The reporting step **declined to promote the hint and
filed a finding instead** — which is why this is a plan and not an incident.

## Goal

A finding authored by the pipeline itself cannot contribute to preference learning, and an unattributed
recurrence cannot be promoted into the widest-scope hint bucket by default.

## Deliverables

1. **D0 — GATE: establish the population before designing the filter.** Mutates nothing. **How many
   promoted hints in the existing corpus were minted from self-authored comments?**
   *Done when:* the count is reported **alongside the population scanned**.
   ⛔ **This decides whether the plan is a filter PLUS a corpus repair, or a filter alone.**
   ⚠ **The observation was one tuple on one run, with no history survey. Do not assume the corpus is
   clean, and do not assume it is dirty.**
   ⛔ **A zero here must be a *looked-and-found-nothing*, not a *could-not-look*.**
2. **D1 — Discriminate authorship before a finding contributes to preference learning.** Two seams exist;
   **pick one and record the rationale**:
   - the ingest verb **already classifies bot versus human** — exclude self-authored comments **at
     ingest**; or
   - the **emitter** skips findings with no bot classification and no external author.
   *Done when:* a self-authored comment cannot reach the disposition corpus.
   ⭐ **Prefer the EMITTER arm** — it is **unilaterally shippable**, whereas the ingest arm crosses into
   another epic's surface. ⛔ **Only prefer ingest if D0 shows the corpus is polluted at ingest for other
   consumers too**, and if so, **route through that epic rather than reaching across.**
   > *A PR comment whose author is the plan's own actor is not evidence of a preference about anything.*
3. **D2 — Decide whether a tuple collapsing to the fallback bucket should be promotable AT ALL.** That
   bucket is the sink for **unattributed** findings, not a real cross-cutting judgement.
   *Done when:* the decision is implemented and recorded.
   ⛔ **This is a SEPARATE question from authorship and must not be silently folded into D1.** ⭐ **An
   authorship filter would have blocked *this* instance while leaving the unattributed-to-widest-sink
   path open for any future one.**
4. **D3 — A test that FAILS pre-fix.** Drive the emitter over a synthetic corpus of self-authored
   comments and assert **no promotion** — with ⛔ **a matched negative control: genuine operator
   dispositions at the same count MUST still promote.**
   *Done when:* both halves pass, each seen red first.
   ⛔ **A filter that suppresses both is not a fix.**

Four deliverables, one component.

## Out of scope

- ⛔ **The review-bot taxonomy.** Adjacent, and it belongs to another epic.
- **The PR-description truncation that manufactured one contributing comment.** Separately reported and
  routed. ⚠ **Independent**: fixing the truncation removes one contributing comment **but not the
  mechanism**.
- **Editing the ingest surface unilaterally.** ⛔ If D1 selects that arm, **route it through the owning
  epic and record the hand-off.** ⭐⭐ **An offer is not a transfer** — a plan blocked on an unaccepted
  hand-off waits indefinitely, and one in this project sat six days. **That is the reason to prefer the
  emitter arm.**

## Expected surface

- The preference-emitter finalize step — its aggregation and its minimum-recurrence threshold.
- `marketplace/bundles/plan-marshall/skills/workflow-integration-github/**` — the ingest verb's author
  handling. **Read-only unless D1 selects that arm.**
- `marketplace/bundles/plan-marshall/skills/tools-integration-ci/**` — the comment-preparation verb, as
  the self-authorship signal.
- The architecture-hint store the emitter promotes into — D0's population.
- Tests.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| One tuple cleared at count 2, from two pipeline-authored comments | HYPOTHESIS | ⛔ **first-party to another run, under `.plan/`, NOT reachable here and NOT re-derived.** ⭐ **Re-verify the threshold and the aggregation from SOURCE** — that half is checkable |
| Neither contributing finding carried a component, so both collapsed to the fallback bucket | HYPOTHESIS | same provenance caveat — ⭐ **but the routing rule is checkable from the emitter's source** |
| The ingest verb takes every non-noise PR comment regardless of author | HYPOTHESIS | that verb's implementation and its author handling — ⛔ **D1's whole premise** |
| Self-authored comments are identifiable because they are allocated through a preparation verb | HYPOTHESIS | that verb — ⛔ **if self-authored comments are NOT reliably identifiable, the emitter arm has no discriminator and the plan re-scopes to D2 plus the ingest arm** |
| The ingest verb already classifies bot versus human | HYPOTHESIS | that verb — ⭐ **if true, the discriminator already exists and D1 is small** |
| Any wrong hint was ever actually promoted and acted on | HYPOTHESIS | ⛔ **NOT ESTABLISHED. D0 settles it. Do not report damage taken** |
| The truncation defect caused one of the two contributing comments | HYPOTHESIS | ⚠ recorded to explain the compounding; **no deliverable depends on it** |

An asserted **absence** is verified exactly as an asserted presence, and is the higher-risk half.
Every count above is a **lead** — re-derive it at the moment of the claim.

## Verification

- ⛔ **D3's negative control is the test that matters.** A filter that stops the pipeline's echo **and**
  stops genuine operator dispositions has broken the feature to fix the bug. **Both halves, or the fix is
  unverified.**
- ⛔ **D0's population must be published with the count.** ⭐ **A zero that cannot distinguish
  *looked-and-found-nothing* from *could-not-look* is this epic's namesake defect appearing inside the
  plan that exists to close a self-reinforcing measurement artifact** — which would be a memorable way to
  fail.
- **D1's arm choice and its rationale belong in the report**, including which arm was rejected. The two
  have different owners, and a silent choice makes the ownership question resurface later.
- **D2 must be visibly separate from D1 in the diff.** Folding them is exactly what the deliverable
  forbids, and a merged implementation would leave the wider path open while looking closed.
- Python and test changes are expected, so the build gate takes its full path.

## Notes

- ⭐ **Worth preserving: the guard held.** The step that found this **declined to promote and filed
  instead.** That is the behaviour the fix should make structural rather than dependent on a step
  noticing.
- ⛔ **Do not go looking for the orchestrator spec, the reporting run's artifacts, the inbox message, or
  any landing record.** They live under `.plan/`, which is git-ignored and absent from this clone.
  Everything checkable from source is named above.
