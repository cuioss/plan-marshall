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

# The freshness gate accepts evidence it never cross-checks

**Epic:** code-intelligence-substrate
**Branch prefix:** fix

## Problem

The pre-commit freshness gate was satisfied by a build-kind change-ledger row whose matched notation
named **a build the plan never ran** — in one case a package-manager coverage notation in a plan with
no such build at all, in another a `--help` invocation recorded as a successful build. **The gate
matches on the presence of a stamp without checking that the stamp corresponds to work *this plan*
actually performed.**

⭐ **The verdict was substantively CORRECT on the founding run** — the agent's own verification had
genuinely covered the same tree. ⛔ **That is what makes it dangerous, not what makes it benign**: a
gate that is right for the wrong reason produces **no failure to learn from**, so it can be wrong for
the same reason indefinitely.

## ⛔ A second, independent weakness — the evidence is TIER-BLIND

**This is not the same defect.** In the first, the evidence was *unrelated*. Here the evidence can be
entirely *related* and still insufficient: a build-kind row **does not record which tier ran**, so a
build that compiled but never tested satisfies a gate whose consumers read it as *"tests are fresh"*.
⇒ **The gate's predicate is strictly weaker than the claim its consumers read.**

⭐ **Adopt the reframing: one structural gap, not four bugs.** This is the **fourth** lesson filed
against the same store. Four lessons on one store is the tell that **the store's evidence model is
under-specified**, not that four gates each need a patch. ⇒ **Address the evidence model** — what a
row must record for a consumer to read a claim off it — rather than adding a second special-case check
beside the first. **If two independent checks really are the right answer, record why the model-level
fix was rejected.**

## ⛔ The symmetric risk — do not silence the true positives

A stale verdict at the tail of the execution phase is **structural and correct**: the chain runs
verification and stamps the tree; a subsequent commit changes the tree; the gate compares and
correctly reports stale. ⛔ **The stamp was never wrong — the commit invalidated it, and that commit
is unconditional at the chain tail.**

⛔ **Do NOT "fix" this by re-stamping or by relaxing the comparison.** The gate is doing its job;
weakening it reintroduces exactly the false-green class this plan exists to close. ⇒ **Any remedy
must state which stale verdicts are structural and expected**, or the next reader will silence the
true positives along with the false ones.

## Goal

The gate's match is **auditable** — a reader can see which evidence satisfied it — and **cross-checked**
against what this plan was actually resolved to run, with the evidence model recording enough for a
consumer to read its claim honestly.

## Deliverables

1. **D1 — GATE: establish what the gate currently checks. Mutates nothing.**
   Answer three questions before changing anything: (a) does it compare the matched notation against
   the plan's **resolved canonical commands**, or only assert a row exists? (b) is the matched notation
   **recorded in the decision record**, so a human could see which evidence satisfied it? (c) is there
   any **provenance field** distinguishing a production write from a test write?
   **Then settle the fail-direction**: an uncross-checkable match must not silently pass — choose
   between refusing (fail-closed) and passing-with-a-visible-warning, **and say why**. ⚠ Fail-closed
   can block legitimate work if resolution is imperfect; D1 owns that trade.
   ⛔ **D1 must also state that a doc-only carve-out was considered and REFUSED** — see the claim table.
   An unexplained absence would invite the next author to add it.
   *Done when:* all three questions are answered from the implementing source and the fail-direction is
   recorded with its reasoning.
2. **D2 — GATE: is the producer half owned, or unowned?**
   The plan that was to add a subcommand discriminator to the build-kind stamp belongs to a **retired**
   effort. ⛔ **It is not going to land — it either already did, or it never will.**
   *Done when:* the run establishes first-party whether the stamp now carries a subcommand
   discriminator, because **the answer decides the next deliverable's shape**:

   | If the discriminator EXISTS | If it does NOT |
   |---|---|
   | the producer half is closed and the cross-check can rely on it — **the work narrows** | the producer half is **UNOWNED**. ⛔ **Do not silently absorb it**: record it and stage it, or state explicitly that the gate must defend against bogus rows indefinitely |
3. **D3 — the match becomes auditable.** When the gate is satisfied, the decision record names the
   **matched notation and the evidence row it matched**.
   ⭐ **This alone converts a silent wrong-reason pass into a visible one, and it survives even if the
   cross-check proves impractical.**
   *Done when:* the record contains both, asserted by test.
4. **D4 — the match becomes cross-checked.** Compare the matched notation against the plan's
   **architecture-resolved canonical build commands** — ⛔ **not** against "notations that appear in
   this plan's ledger rows".
   ⭐ **That formulation is deliberate: it does not depend on the producer being fixed**, which is why
   it holds under either branch of D2.
   ⚠ **Precision matters in both directions**: a plan legitimately runs several notations and
   resolution can be partial. **An over-strict check that refuses valid evidence trades one false
   signal for its mirror.**
   *Done when:* an unrelated notation is surfaced per D1's fail-direction, and a legitimate
   multi-notation plan still passes.
5. **D5 — tests.**
   (a) a gate run whose only candidate evidence is an unrelated notation behaves per D1's chosen
   direction — **verified to silently pass against current code**;
   (b) a legitimate multi-notation plan still passes;
   (c) the decision record contains the matched notation.

Five deliverables with two gates — under the split guard.

## Out of scope

- **Test isolation — stopping tests writing into the production store.** ⛔ Excluded: it is the
  **producer** half of a two-owner story and belongs to its own plan. ⚠ **They are NOT independent and
  the ordering matters**: fixing isolation alone removes *this* contamination source but leaves the
  gate unable to distinguish evidence, so the next source reproduces it. **This plan is the durable
  half; isolation is the urgent half. Neither alone closes the problem.** They are source-disjoint
  (gate implementation versus test tree), so **they may run concurrently.**
- **The confirmed pollution source itself** — a specific consumer test that reaches the real store
  with no isolation marker. Read-only evidence here; ⛔ **do not fix it in this plan.**
- **A doc-only freshness exemption.** ⛔ **Excluded on a hard constraint** — see the claim table:
  markdown under the bundle tree **is a build input in this repository**, so exempting a doc-only
  footprint would reintroduce the entire defect class **through the exemption**.
- **Re-stamping or relaxing the staleness comparison** to suppress structural stale verdicts. Excluded
  per the symmetric-risk section.

## Expected surface

- The freshness gate implementation and its decision-record write. **HYPOTHESIS — the exact module was
  not located first-party; verify at outline.**
- `marketplace/bundles/plan-marshall/skills/manage-change-ledger/` — **only if** D1 finds a provenance
  field is the right fix. **HYPOTHESIS.**
- The consumer test that reaches the real store — **read-only evidence, not edited here.** **OBSERVED.**

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The gate was satisfied by a notation the plan never ran — **two independent instances, two different plans, same gate** | **OBSERVED (first-party accounts)** | ⛔ The run records are machine-local and **not reachable from this clone — do not look for them.** ⭐ **Settle it in the clone from the gate's own predicate**: if it asserts row existence without comparing against resolved commands, the defect is structural. |
| Both instances were found **by accident** | **OBSERVED** | ⇒ **The observed rate is a FLOOR.** Scope from that, not from a count of two. |
| The gate performs no notation cross-check at all | **HYPOTHESIS** | ⛔ **Read the implementation.** **If a cross-check already exists and merely failed open, the fix is different — narrow the existing check rather than adding one.** |
| The build-kind row is tier-blind | **OBSERVED** | The row schema in the clone. |
| The pollution source is a **consumer** test, not the ledger's own tests | **OBSERVED, verified first-party** | ⛔ **The originating lesson's directive MIS-LOCATES the offender** — the ledger's own tests are already isolated. **Do not scope against that wording.** |
| Markdown under the bundle tree **is a build input**, because tests parse those bodies | **OBSERVED — the strongest constraint category in the corpus** | ⛔ **This forecloses the remedy D1 is most likely to reach for.** Refuted only if no test reads a bundle markdown body — check that before considering any doc-only carve-out. |
| A stale verdict at the execution-phase tail is structural and the gate is correct | **HYPOTHESIS, internally consistent** | ⚠ The originating account came from a plan that **announced a landing which had not occurred** — ⛔ **re-derive against the implementing source before scoping.** |

## Verification

- **D5(a) must be shown to silently PASS against current code** before the fix. That pre-fix
  observation is the deliverable's proof; without it the test could be pinning the defect.
- **Both directions are asserted**: unrelated evidence is caught, legitimate multi-notation evidence
  is not refused. ⛔ A one-directional fix trades one false signal for its mirror.
- **The structural-stale case is asserted to remain STALE.** If the remedy makes it pass, the gate has
  been weakened and the plan has produced the defect it exists to close.
- **D1's refusal of the doc-only carve-out appears in the shipped reasoning**, not only in the run
  report — an unexplained absence invites its re-introduction.
- Full `./pw verify` per the lane contract's build gate.

## Notes

- ⭐ **A distinct failure class worth naming**: *correct-verdict-wrong-evidence* is not the same as a
  wrong verdict, and it is **strictly harder to detect because nothing ever breaks.** This is at least
  the third instance in this epic of a gate being right by accident.
- ⚠ **A sequencing collision to raise BEFORE starting**: another epic is working on the same ledger
  rows (build-kind rows recording success for timed-out builds, and probe invocations counted as
  builds). **If their fix and this plan's gate work both touch the ledger, they are not disjoint.**
  Raise it at emit time; do not discover it at rebase.
