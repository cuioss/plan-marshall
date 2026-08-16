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

# Audit detectors that are structurally incapable of reporting what they claim

**Epic:** code-intelligence-substrate
**Branch prefix:** fix

## Problem

The archived-plan auditor reports per-check counts that consumers treat as findings. Several checks
**cannot produce a true positive at all**: the predicate reads a field live data does not carry, scans
for a marker nothing writes, counts rows that are pending by construction, or attributes an outcome to
the wrong mechanism.

⛔ **This is the epic's flagship archetype located inside the tool that surfaced roughly half the
epic's other plans** — so every clean verdict that tool has produced inherits the doubt until these
are closed. **Absence of findings from this tool has never been evidence of absence.**

⭐ **Scale was the detector.** A small run cannot distinguish *"zero findings"* from *"cannot find"*.
A full-corpus sweep is what made a permanent zero legible as a defect.

### The failure modes are FIVE, not one, and the remedies differ

| Mode | Shape |
|---|---|
| **A — cannot fire** | the predicate's input never occurs, so the check can never produce a positive |
| **B — fires but counts noise** | the positives are structural; the number is untrue in the *opposite* direction |
| **C — fires on an arbitrary population** | neither reliably present nor reliably absent |
| **D — producer starvation** | ⭐ **the detector is written correctly and starves for input.** ⛔ **Load-bearing distinction: fixing the predicate would achieve NOTHING — the producer must emit.** Most recorded vacuous guards are *predicate* defects; this is the first identified as *producer starvation*, and **the two have opposite fixes.** |
| **E — the detector is inside its own population** | it samples before it finishes contributing. ⇒ Its count is a floor **that systematically excludes its own contribution**, so **the one class of failure it can never report is its own.** |

### The confirmed members

**A field that is populated but never read.** The auditor sets a routing key from one metadata field
and **never reads that key from metadata at all** — a search for the read returns **zero hits in the
whole file**. So a plan carrying the key and not the other field is invisible. ⭐ **And an inline
comment asserts the two are "equivalent for matrix purposes"** — the equivalence is **asserted in a
comment and implemented as a one-directional read.**

**A marker no production code writes — and the tests are vacuous too.** A content sweep for the
scanned marker returns hits in **three files, every one a TEST**. **Zero production emitters.**
⇒ ⭐⭐ **The detector scans for a marker nothing writes, AND its suite is green because the tests
synthesise the marker themselves.** That is the vacuous-guard archetype **with its own regression
suite certifying it** — strictly worse than a bare unreachable predicate, because a reader checking
*"is this covered?"* finds passing tests.

**A regex that can never match its emitter.** A removal-cause pattern is written with a different
field order and trailing clause than the emitter's contracted line shape, so the cause always falls
through to a re-evaluation branch and the check fails. ⛔ **This affects every plan under the common
execution posture.** ⭐ **The sharpest vacuous-authority instance recorded**: a comment asserts each
pattern is *"copied verbatim from the emitter contract"*, and the module docstring explains the exact
defect it produces. **The guard documents the defect it causes and asserts a verbatim-copy property
that is false on disk. Nothing observes the copy.**

**A guard whose precondition is its own subject.** Its precondition is *the presence of the marker it
exists to detect the absence of* — ⛔ **so it is vacuous at exactly the value it was written to catch,
and green everywhere else.**

**A warning that fires at every boundary.** ⭐ **A warning that fires at 100% is not a detector — it is
a constant**, and it trains readers to ignore the channel it shares with real warnings. Its remedy is
the **inverse** of the vacuous-guard remedies: **the others never fire and this one never stops.**

**A pending count that cannot reach zero.** A large fraction of rows are pending **by construction**
and no action can resolve them. ⛔ **A pending count that cannot reach zero is not a backlog, it is a
mislabelled population** — and it is worse than a false zero, because **a false zero invites a check
while a large backlog invites resignation.**

## Goal

Every check either **can fire**, or **explicitly reports `unmeasured`** instead of a number that reads
as health — and a detector's output can express *"I did not check"* as a state distinct from *"I
checked and found nothing"*.

## Deliverables

1. **D1 — GATE: verify every claim against the implementing source, then classify. Mutates nothing.**
   ⛔ **Do not fix from the report text.** Confirm or refute each claim at its site and classify it
   into one of the five modes above, **because the remedies differ.**
   **Settle the reporting contract**: a check that cannot substantiate its verdict emits
   **`unmeasured`**, never `0`.
   ⛔ **Re-derive the OTHER members of the removal-cause pattern set against the live emitter in the
   same pass.** One member drifted; **that is a sample of one and says nothing about the other three** —
   this plan's own named-list-is-a-sample rule applied to itself.
   *Done when:* each claim carries a verdict and a mode, and the reporting contract is decided.
2. **D2 — read the field live data actually carries**, so the routing row is reachable. **Correct the
   comment asserting the equivalence** — leaving it is the defending-documentation pattern this epic
   keeps finding.
3. **D3 — measure contention, or say it is unmeasured.** Either scan for a marker the logs actually
   contain, or report the count as `unmeasured` with its reason.
   ⛔ **A zero that cannot be distinguished from "no data" IS the defect** — whichever route is taken,
   the two states must be distinguishable in the output.
   ⛔ **And the tests must be re-pointed at the production emitter**, or they will keep passing over
   the fix. ⚠ **Coordinate on the emission half** — it belongs to the lock skill's surface, not the
   auditor's. **Decide the split rather than absorbing it.**
4. **D4 — exclude structural pendings from the genuine count.** Partition so pending-by-construction
   entries are excluded or reported in their own bucket — **the same partition shape already shipped
   elsewhere in this codebase for omitted-versus-dropped sections, which is the proven pattern.**
   ⭐ **The property to state explicitly: a detector reporting a count must be able to say what would
   make that count zero.**
5. **D5 — branch on the recorded removal cause.** Re-evaluate a predicate **only when the recorded
   removal was predicate-driven**, and report configuration-driven removals as intentional outcomes
   with no violation verdict.
   ⭐ **This needs no new input — it is a consumption change over data the check already loads.** The
   disproving evidence was **already inside the check's own output**: it loaded the contradicting
   record, rendered it, and did not consult it.
   ⭐ **Preferred remedy, stronger than fixing the pattern: emit the line through a shared formatter
   both sides import**, so the shape has exactly one home. **A hand-written fixture drifts in lock-step
   with the wrong copy and would not have caught this.**
6. **D6 — the class guard.** Surface a detector that has produced **zero positives across a full
   corpus** as *suspect* rather than silently clean. **This is what would have caught all of these
   without a human noticing.** Scope it to reporting, not to blocking.
   ⭐ **And it must distinguish a STRUCTURAL zero (cannot occur) from a DISCIPLINARY zero (does not
   occur yet).** A census whose zero is one un-stubbed sibling away from being non-zero is a different
   claim from one that cannot occur — **the census is the durable deliverable; the number it prints
   today is not.**

Six deliverables with D1 a gate — **at the split guard.** D1 is a gate and D6 is cross-cutting, so the
implementation surface is effectively three. ⚠ **If D1 finds these do not share a reporting seam,
split the counts-noise member out** — it is a different failure direction — rather than proceeding
unsplit.

## Out of scope

- **The auditor's working-directory resolution defect.** ⛔ Excluded deliberately and staged
  separately for exactly this split-guard reason. ⛔ **It collides with this plan on the same file —
  never run concurrently, and run it first.**
- **The documented-versus-accepted vocabulary mismatch** for termination causes. Excluded — a sibling
  plan owns the documentation half. What belongs here is the **third** population: a detector whose
  counted set is narrower than either the documented or the real one.
- **The private bookkeeping-prefix classification defect** and the unreachable rule in the manifest
  cross-check. ⛔ Excluded — **moved to their own plan**; do not re-add them here.
- **Fixing the lock-marker EMISSION.** Excluded unless D3 decides otherwise — it is another skill's
  surface.

## Expected surface

- `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py` — the routing predicate, the
  marker scan, the quality-chain row builder. **OBSERVED**; ⚠ **line numbers have already moved once —
  locate by symbol, and do not pin a test to a line.**
- The auditor's decision-rules document — the refuted parity assertion. **OBSERVED.**
- The routing-decisions check and its removal-cause pattern set. **OBSERVED.**
- The per-check documentation, updated in lock-step with any vocabulary change. **HYPOTHESIS.**
- Tests for this project-local skill — **confirm the test module exists before assuming it.**
  **HYPOTHESIS.**

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The routing key is populated from another field and **never read from metadata** | **OBSERVED, re-verified first-party at HEAD** | The auditor source — a search for the read returns zero hits. ⛔ **Re-derive the location; the line has already moved once.** |
| The scanned marker has **zero production emitters**, and all its occurrences are in tests | **OBSERVED, re-verified first-party at HEAD** | A content search across the inventory. ⭐ **Reproduce it in the clone — it is cheap and it is the finding.** |
| The removal-cause pattern cannot match the emitter's contracted shape | **OBSERVED, verified on both sides** | The pattern and the emitter contract. ⛔ **Read both; the mismatch is in field order and trailing clause.** |
| A guard's precondition is the presence of the marker it exists to detect the absence of | **OBSERVED** | The guard's precondition. |
| A drift warning fired at every boundary | **OBSERVED** | Rescued from a withheld proposal; re-derive. |
| A large fraction of quality-chain rows are pending by construction | **CLAIMED — figures NOT re-derived** | ⚠ **Each figure carries its own unpublished population. Re-derive before citing any of them as a result.** |
| The pending-row predicate still admits those row classes | **HYPOTHESIS** | The findings skill's pending-row predicate. |
| Every remaining claim | **HYPOTHESIS until verified at its own site** | ⛔ **This plan's whole subject is detectors trusted without verification — do not fix from the report text.** |
| The corroborating corpus | **NOT REACHABLE FROM THIS CLONE** | The audit corpus and its report live under machine-local, git-ignored paths ⛔ **— do not go looking for them.** ⚠ **And a re-run against an empty corpus will report zero findings — treat any zero-finding re-run as unverified**, which is itself this plan's subject matter. **Every claim above is settleable from the auditor's SOURCE instead; do it that way.** |

## Verification

- **Every fixture must produce a true positive and be verified to FAIL against the current detector.**
  A detector that has never been observed failing is indistinguishable from a vacuous one.
- **The `unmeasured` state is asserted distinguishable from `0`** — that assertion is the plan's
  central deliverable, not a detail.
- **D3's tests are re-pointed at a production emitter.** ⛔ A suite that synthesises its own marker
  will pass over the fix, which is exactly how this defect survived.
- **D6 is verified against a deliberately-starved detector**: it must be surfaced as suspect, and its
  zero classified structural or disciplinary.
- Full `./pw verify` per the lane contract's build gate.

## Notes

- ⭐ **A method note worth carrying into any detector this plan derives**: a population-derivation
  predicate may need several refinements before it is sound, and a final zero can be *a discipline
  property, not a structural one*. **Report which.**
- **Serialization.** This is a project-local meta skill, disjoint from the bundle plans in this epic —
  **except** the plan that fixes the same file's directory resolution. Sequence behind it.
