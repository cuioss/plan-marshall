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

# A finalize step can run and leave no trace

**Epic:** code-intelligence-substrate
**Branch prefix:** fix

## Problem

The question this plan answers is one: **does a finalize step's execution leave a reliable trace?**
Today it does not, in four distinct ways.

**Emission is wired to first entry, not to the spawn.** A step that loops back spawns repeatedly and
emits **one** dispatch line regardless. On one run the single most expensive step spawned six times
and logged once; on another, roughly a third of all dispatches were unlogged. ⭐⭐ **The gap was
detectable only because a second ledger existed to contradict the first** — on a step with no
boundary rows it would be undetectable. ⛔ **The two ratios differ materially, so do NOT quote either
as "the" undercount**: the loss depends on how many steps looped back and how often. **State the
mechanism and publish the per-run population, never a single headline multiple.**

**Step markers cover only some completed steps, and the population is path-dependent.** Some steps
complete with no marker at all; others carry a completion with no paired start. Emission is
**per-handler rather than driven by the step loop**, and the start/complete pairing is convention
rather than contract. Worse, an operator **resume** after a halt emits no step instrumentation at
all — so whether a step is observable depends on **how the run re-entered**, which is exactly the
dimension no marker-derived count can see. ⛔ **Any count derived from these markers is a FLOOR, not
a count. Marker absence does not mean the step did not run.**

**The completion handshake and the log line are two separate obligations.** The
step-completion invariant is satisfied by the handshake **alone**, while the log line is a separate
instruction living in workflow prose. ⇒ **A step can be fully compliant with the invariant while
leaving no trace in the operational log** — and those two records are precisely the pair a
retrospective or a debugging operator cross-checks against each other.

**One step's mode resolution keys on the wrong signal.** The retrospective step selects its mode by
the presence of an iteration argument, and only that mode emits the completion tail. A dispatch that
omits the argument therefore runs in the wrong mode and leaves its step record unwritten.

**And the roster that says which steps dispatch contradicts itself.** The document declaring itself
the single source of truth carries a closure invariant — *every step carries exactly one
classification* — that **it violates on its own page**. ⛔ **The roster is the side that is wrong on
the merits** for the known instance: the step is correct to run inline, because its documented
interactive mode needs a prompt a dispatched leaf structurally cannot fire. ⇒ **A reader who "fixes"
the audit to agree with the roster would be hard-coding the wrong answer.**

## Goal

A dispatch line is emitted once per **spawn**, not once per step; step markers are driven by the step
loop so their population is structural rather than voluntary; the completion handshake and the log
line cannot diverge; and the roster's classification claims are checked for **correctness**, not only
for completeness.

## Deliverables

1. **D1 — GATE: map the observability seams. Mutates nothing.**
   Confirm each defect at HEAD and pair each signal with the write seam that must co-emit it.
   ⛔ **Derive the divergent set population-wise from the roster**, rather than fixing the sites this
   plan happens to name. ⚠ **Both sides need establishing** — the roster cannot be trusted as the
   baseline either.
   *Done when:* each defect is confirmed or refuted at its own site, and the divergent population is
   derived rather than enumerated.
2. **D2 — emit the dispatch line from the spawn site.** Move the emission (or add one at the loop-back
   re-fire path) so the dispatch count equals the spawn count.
   ⭐ **The line's shape is already specified — only its placement is wrong**, so this is placement
   work, not contract work.
   *Done when:* a step that spawns N times emits N lines, asserted with N > 1.
3. **D3 — drive step markers from the step loop, and fuse the completion marker to the handshake.**
   The completion script already receives the step, the phase and the outcome — **it has everything
   the line needs. Emit the completion marker from the script itself.**
   ⭐ A prose instruction to log, sitting beside a script call that already knows the payload, is a
   duplication that can only ever drift **toward silence**, because nothing reads the log back to
   confirm the emission.
   ⭐ **Generalise to the peer pair in the same pass**: an outcome record that omits the
   head-at-completion field is likewise unverifiable on re-entry — a terminal record well-formed
   enough to pass and thin enough to be useless.
   *Done when:* markers are emitted by the shared path, and a step that completes without any prose
   instruction still produces its pair.
4. **D4 — the resume path emits step instrumentation.** An entire re-entry path currently logs
   nothing, making a resumed run indistinguishable from a run that skipped those steps.
   ⛔ **Any coverage figure this plan reports must state whether its population included a resume.**
   *Done when:* a resumed run emits markers for the steps it executes.
5. **D5 — fix the mode-resolution signal for the retrospective dispatch.** ⚠ **Re-ground before
   scoping**: a later change added payload to the completion tail and rewired several steps, so
   **confirm the current shape rather than the filed one.**
   *Done when:* the dispatch selects the intended mode and its step record is written.
6. **D6 — a correctness assertion over the roster's classifications.**
   ⛔ **Do NOT close this with a second hand-written pin.** The existing test already carries a
   hand-written pin for one step and none for another; **a hand-maintained mirror of a derived set is
   the recurring archetype here (n≥5).**
   ⭐ **The reusable insight**: every assertion in the current test is a **completeness** property —
   coverage, disjointness — and **none is a correctness** property. It can prove each step carries
   exactly one classification and never that the classification is **right**, because it never reads
   the step's own standards document. Add the cross-document check.
   ⚠ **Fix the assertion FIRST and verify it FAILS against the divergent state** before changing
   anything else.
   *Done when:* the check reads both documents, fails against the known divergence, and is derived
   from the roster population rather than pinned.

Six deliverables — **at the split guard**. Proceeding unsplit is deliberate and recorded: all six are
one surface (dispatch and step emission plus the completion handshake), and splitting them would
produce plans that each re-derive the same seam map and race on the same files. **Re-evaluate the
split at outline and record the verdict.**

## Out of scope

- **The dispatch AUDIT and its vacuous check**, the three-state consumer distinction, and the
  channel-completeness report. ⛔ **A sibling plan owns them, and it must run FIRST** — while that
  audit is vacuous, this plan cannot measure its own divergence. Shipping both against the same
  surface would produce two writers for one emitter.
- **The boundary-ledger arithmetic** (a coverage ratio over an undeclared population, missing dispatch
  classes, the equality mislabel). Excluded — moved to its own plan in a documented split.
- **Frozen-manifest-versus-live-config reconciliation**, the simplify prompt's scope clause, and the
  title-token log noise. Excluded — moved to a third plan in the same split.
- **Correcting the roster document's own classification text** and reconciling its enumeration sites.
  Excluded: another epic owns the **doc-correction** half under the routing rule. This plan builds the
  **detector** over it. ⛔ **Sequence behind their correction** — building the test first means
  writing it against the divergent state.

## Expected surface

- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/` — the dispatch and step emission
  sites, and the roster document read by D6. **OBSERVED.**
- The step-completion script — D3's emission home. **HYPOTHESIS**, verify at outline.
- `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/` — the contradictory adjacent
  decision lines for one step selection. **HYPOTHESIS**, verify at outline.
- `test/plan-marshall/` — tests, including the existing classification test D6 replaces.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The dispatch line is emitted on first entry to a step rather than per spawn | **OBSERVED, two independent runs** | ⛔ The run records are machine-local and **not reachable from this clone — do not look for them.** ⭐ **Settle it in the clone from the emission site**: if the emission sits on the entry path rather than the spawn path, the mechanism is confirmed from source. **Do that.** |
| The two observed undercount magnitudes | **LEADS, and deliberately not a headline** | ⛔ **Do not quote either as "the" undercount.** Publish the mechanism and the per-run population instead. |
| Step markers cover only some completed steps, and emission is per-handler rather than loop-driven | **OBSERVED** | Read the emission call sites in the clone: if each handler emits its own, the population is voluntary by construction. |
| A resume path emits no step instrumentation | **OBSERVED** | Read the re-entry path. |
| The completion invariant is satisfied by the handshake alone, while the log line is a separate prose instruction | **OBSERVED, and it is the structural point** | Read the invariant's predicate and the workflow prose side by side — both in the clone. |
| The retrospective's mode resolution keys on an argument the dispatch does not pass | **HYPOTHESIS, and version-stale** | ⚠ A later change added payload to that tail and rewired several steps. ⛔ **Confirm the current shape, not the filed one.** |
| The roster violates its own closure invariant, and the roster is the side that is wrong | **OBSERVED, four independent sightings** | Read the roster's invariant statement and the offending row, plus the step's own standards document carrying the binding mechanism. ⚠ **Four sightings of ONE instance is still not a derived population** — the obligation to derive the full contradicting set stands. |
| The existing classification test asserts completeness but never correctness | **OBSERVED** | Read the test. This is D6's premise and it is cheap to confirm. |

An asserted **absence** ("no correctness assertion exists over the classifications") is verified
exactly as an asserted presence — confirm it in the test before writing a second one.

## Verification

- **D2 is verified with N > 1.** A test where the step spawns once passes against the defect. Force a
  loop-back and assert the line count equals the spawn count.
- **D6's assertion is verified to FAIL against the divergent state before anything else changes.**
  Record that failure. ⛔ A classification test that has never failed is the vacuous guard this plan
  is replacing.
- **D3 is verified by removing the prose instruction**: with the emission moved into the shared path,
  a step whose workflow text no longer tells it to log must still produce its markers.
- **Every coverage figure this plan reports states whether its population included a resume**, per D4.
- Full `./pw verify` per the lane contract's build gate.

## Notes

- **Ordering, and it is a hard constraint.** ⛔ **The sibling audit plan runs FIRST** — this plan
  cannot measure its own divergence while that audit cannot fail. ⛔ **And the other epic's roster
  correction lands before D6** — otherwise the detector is written against the divergent state.
  ⚠ **Re-derive both by naming the actual PRs rather than trusting any statement of their status
  here**; a cross-epic clearance is a snapshot, not a state.
- **Same bundle as the sibling plans from this split — sequence, never run concurrently.**
- ⚠ **If recording anything requires touching effort resolution, stop and coordinate** rather than
  editing that seam from inside this plan.
