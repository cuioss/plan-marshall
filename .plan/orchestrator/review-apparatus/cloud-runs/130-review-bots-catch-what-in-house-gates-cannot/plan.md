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

# Review bots catch what in-house gates structurally cannot, and nothing quantifies the residual

**Epic:** review-apparatus
**Branch prefix:** feature

## Problem

A full green in-house sweep is not evidence of correctness, and today **nothing quantifies the
residual.**

⭐⭐ **A clean natural experiment makes the shape precise — same diff, same day, two mechanisms, two
essentially disjoint result sets.** On one PR, **self-review** ran three passes and produced six
findings. **Every one is a documentation-consistency finding:** a strictly-narrowing claim that was too
broad; a sentence contradicting an instruction 29 lines above it; three consumer docs asserting a
retired member count; two sites calling a blocking subset seven when it is six; one hard-coded guard
population.

**A review bot's first review of the same diff** produced eight actionable comments, four of them Major,
**of a different kind entirely**:

- a binary read of a fallible observable coercing UNKNOWN into a positive (Major);
- a documented remedy with **no reachable invocation** — no verb, no outcome recording, no timeout
  branch (Major);
- an observable scoped to the head branch when its meaning is per-PR, so a reused branch suppresses the
  remedy (Major);
- a malformed-envelope path collapsing "never read" into "read empty", contradicting the function's own
  docstring;
- a drift pivot shared by **both sides** of a count comparison, so the comparison stays green over a set
  missing a member (Major).

⇒ **Self-review found internal inconsistencies between statements IN the diff. It did not find
behaviours of the code under inputs the diff does not contain.** Those are different search problems,
and this run separates them cleanly.

⛔⛔ **Self-review passing is not evidence the diff is sound.** Three green-ish passes preceded four
Major findings. A run that reads self-review as a proxy for review quality will merge on that proxy
**exactly when a bot is unavailable** — and that is precisely what happened on a later run: **no
external reviewer produced content at all**, and the merge proceeded on in-house evidence alone (CI
green, quality gate, full test suite, structural lint clean, self-review clean after four findings
fixed).

⭐⭐ **The proxy is weakest exactly when it is being leaned on hardest.** That is the sentence this plan
exists to make measurable.

⚠ **And the counter-weight must not be dropped.** On that same reviewer-less run, self-review caught
**four** stale-set instances, including one in a repo-root instruction file that had just been made
load-bearing as the reviewer's own context source. ⇒ The honest finding is **not** "self-review is
weak" — it is that self-review and bot review have **different and complementary reach.** ⛔ **Do not
let this plan be re-framed as an argument against self-review.**

## Goal

Every in-house gate states what its green does not cover, the review-versus-gate delta is a recurring
measured signal rather than an anecdote, and an in-run reviewer commitment survives later steps of the
same run.

## Deliverables

Four. ⚠ **A fifth deliverable was dropped as already shipped** — see Notes.

1. **D0 — GATE, mutates nothing: state what each gate structurally cannot evaluate.** For the gates in
   scope, name the analysis each performs and therefore what each **cannot see**.
   ⛔ **A gate whose green is scope-limited must say so in its verdict.** The defect is not that a gate
   is narrow — it is that **a narrow gate's green reads as whole-tree assurance.**
   *Done when:* each gate's verdict carries its own scope limit, derived from what the gate actually
   analyses rather than from its documentation.

2. **D1 — a same-run reconciliation contract between an automatic-review-committed line and the
   dead-code-removal step.** Honour the in-run reviewer commitment rather than ad-hoc judgement: **if
   the review process committed to a line within a run, a later step in the same run must not silently
   remove it.**
   *Done when:* a line committed to during review survives a later simplify pass in the same run, or the
   removal is surfaced as a conflict rather than performed silently — proven by a test.

3. **D2 — the review-versus-gate delta becomes a measured signal.** *"What did review catch that the
   gates did not"* is the only direct read on parity available, and **it arrives free on every PR.**
   ⛔ **Consume the epic's counting rule; do not re-derive it.** Three plans in this epic need
   per-reviewer finding counts and the epic keeps exactly one rule.
   ⛔⛔ **The confound is load-bearing and must be handled IN the measurement, not noted beside it.** The
   bots refuse frequently, so **an absence of review findings is often an absence of *review*, not of
   defects.** ⇒ **A parity metric that does not exclude PRs where the reviewer refused will report
   improving parity as coverage collapses.** That inversion is this epic's named failure mode, so **a
   metric that can produce it must not ship.**
   ⛔ **Partition before computing any rate.** The evidence class is **mixed**: some instances are
   *addable in-house gates* — a lint rule family omitted from the local `select` list, an unsorted
   traversal, a symlink-through copy — where the bot caught what a gate **could** have caught. That is a
   **gate-configuration finding**, not evidence of a structural bot-only class. Others (documentation-
   prose semantics, report-claim consistency) may be genuinely bot-only. **Partition by "could an
   in-house gate have caught this" FIRST.**
   ⛔⛔ **THIS DELIVERABLE HAS A HARD STOP CONDITION, and it is likely to fire in this lane.** The
   fourteen-lesson corpus that would supply the empirical denominator lives in a **machine-local,
   git-ignored directory that is NOT in your clone.** ⇒ Derive the population from something **reachable
   from the clone or the provider** — merged PRs and their review comments, plus gate results visible in
   CI — and **if no such population can be derived, report D2 as blocked on an unavailable population
   and stop.** ⛔ **Do not hand-assemble a corpus to have something to measure**; a rate over a
   hand-picked set is exactly the volume-read-as-coverage defect this plan exists to close.
   *Done when:* the metric excludes refusal-PRs by construction and publishes its population and
   provenance — or the stop condition fires and is reported.

4. **D3 — tests, each verified to FAIL pre-fix**, plus retirement of the two lessons this plan carries.
   ⚠ **Do not carry a lesson this plan does not name.** Only two are in scope: *the completeness guard
   conflates an absent bot with an in-progress one* and *no same-run reconciliation contract exists
   between the simplify step and automatic-review*. The rest returned with the build-gate half.

## Out of scope

- **The build-gate half.** A lint rule family in the local `select=` list, test-compile parity, and gate
  footprint scoping (the zero-scoped-modules branch, the generator-tree root footprint) **went back to a
  sibling epic** and are staged there. ⛔ **Do not scope them here.** If D0 finds the review-side gaps
  are inseparable from the build-side ones, **say so and escalate rather than quietly re-absorbing the
  returned half.**
- **Adding detectors to self-review.** ⚠ Self-review's passes 2 and 3 produced **more of pass 1's
  class** (count prose, then a guard population) rather than reaching the behavioural class. **Whether
  that is a detector-coverage gap or an attention-anchoring effect is worth deciding BEFORE adding
  detectors** — adding them for the wrong one entrenches the anchoring. Another staged plan in this epic
  owns detector additions; this one does not.
- **Arguing that self-review should be trusted less.** See the counter-weight in Problem.
- **A parity claim not supported by the measurement.** If the recurring-signal hypothesis fails, **D2
  ships as a measurement with no parity claim attached.**

## Expected surface

- The `automatic-review` completeness guard and its loop-back decision path — **read-only** for D0.
- `marketplace/bundles/plan-marshall/skills/finalize-step-simplify` and its reconciliation point with
  the automatic-review record — D1's primary surface.
- A governing coverage-parity standard; candidate home
  `phase-6-finalize/standards/pre-push-quality-gate.md`. ⚠ **If the natural home turns out to be the
  build-gate standard that left with the returned half, that is a signal the split needs revisiting —
  escalate rather than editing the returned surface.**
- `manage-metrics` or a retrospective check, for D2's measurement.
- ⛔ **NOT in surface:** `pyproject.toml`'s `select=` list and the gate footprint logic. They went back
  with the build-gate half.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| Self-review and bot review produced essentially disjoint result sets on one diff | OBSERVED — first-party, a controlled same-day comparison | Restated here in full; the finding ledgers are machine-local |
| Every in-house gate went green on one PR while a bot still found two real defects | OBSERVED | ⚠ Note the self-review figure quoted at the time (*"125 candidates, 1 finding"*) is a **VOLUME, not a coverage number** — do not read it as one |
| The bots refuse frequently, and refusals are often stated only in comment bodies | OBSERVED across several PRs | The refusal states in the completeness classifier, and the comment bodies themselves |
| The absent-versus-in-progress distinction is already shipped | OBSERVED | The check-classification probe functions in `workflow-integration-github/scripts/_github_checks.py`. ⇒ **That deliverable is DROPPED, not re-scoped** |
| The gate-green / bot-finding pairing is **representative** rather than a single instance | HYPOTHESIS | Sample further PRs at D0. ⛔ **D2's whole value depends on this being a recurring signal**; if it is not, D2 ships as a measurement without a parity claim |
| No existing metric already captures the review-versus-gate delta (an asserted **absence**) | HYPOTHESIS | Check `manage-metrics` and the retrospective checks — **several measure adjacent things.** ⛔ An unverified absence here would duplicate a shipped retrospective check |
| Each of the fourteen recorded gaps is still open against current main | HYPOTHESIS — **re-derived by nobody** | Each named gate's own scan scope. ⚠ **The lesson bodies are machine-local and not in your clone** — see D2's stop condition |
| The two carried lessons are still open | OBSERVED at staging | Re-check before retiring either |

⚠ **Every count here is a lead**: six findings, eight comments, four Majors, fourteen lessons, three
passes. **Re-derive anything you assert.** And the fourteen-lesson set is explicitly **a SAMPLE, not an
enumeration** — lessons somebody chose to file, not every occurrence. ⛔ **Any rate derived from it MUST
publish the population and its provenance.**

⛔ **Do not go looking for `.plan/`.** The lesson corpus, the finding ledgers, and the inbox messages
behind this plan are git-ignored and **absent from your clone** — which is exactly why D2 carries a stop
condition rather than an instruction to read them.

## Verification

- Full verify; read the payload's `status` / `errors[]`, not the exit code.
- **Every D3 test proven discriminating by mutation.**
- **D2's metric is tested against the inversion it must not produce**: construct a case where reviewer
  coverage collapses and confirm the metric does **not** report improving parity. ⛔ This is the one
  check that distinguishes a useful metric from a harmful one.
- **Publish the population, its provenance, and the partition** with any rate the run emits — including
  in its own run report.
- ⭐ **Cold read, aimed at the scope-limited verdicts.** D0 makes each gate state what its green does not
  cover. Have the pre-PR verification sub-agent read one changed gate verdict **cold** and answer: *what
  did this gate check, and what could still be wrong despite it passing?* If the cold reader still takes
  the green as whole-tree assurance, D0's wording failed however accurate the scope statement is.

## Notes

- **A deliverable was DROPPED, and saying so is the deliverable.** This plan originally proposed a
  checks-status presence probe to distinguish a structurally-absent bot from an in-progress one. That
  mechanism **shipped in full** in a merged PR, along with a seven-member closed taxonomy stating each
  member's distinct remedy. ⭐ **This epic's named failure mode is staging a plan for an already-landed
  fix** — the drop is the correct outcome, not a shortfall.
- ⚠ **A latent cross-epic collision, deeper than a shared file.** The returned build-gate half is staged
  in a sibling epic, and two couplings exist: the **file** (both may move the same gate standard), and
  ⭐ the **semantics** — a zero-scoped-modules / docs-only branch resolving to a clean pass is **the same
  conflation** as a test-scope resolver returning null for source it cannot resolve. ⛔ ***"No module
  matched"* and *"no tests needed"* are one signal in both places.** The sibling has serialised its two
  plans so it is not fixed twice in two shapes. **Nothing is owed from here** — but if this plan reaches
  that branch, **say so rather than fixing it a third time.** The one-signal-two-meanings archetype is
  now known to live in at least three places.
- **Self-review's own recurring hit is the hard-coded population.** It caught one instance while missing
  two more the bot then found, plus one more found later at finalize — **five instances of one archetype
  in one PR, discovered by three different mechanisms.**
- **Sequencing.** Overlaps other staged plans in this epic on the participation classifier and on the
  finalize phase. ⛔ **Sequence, never pair.** ⚠ If this plan's measurement and the sibling epic's
  build-gate parity plan turn out to be **the same population viewed from two sides**, say so and split
  the surface explicitly rather than shipping both.
