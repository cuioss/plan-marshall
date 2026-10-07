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

# The Java skills route authors to an anti-pattern they never warn about

**Epic:** truthful-signals
**Branch prefix:** chore

## Problem

Four findings on the Java bundle that **only make sense as one chain**. Individually they read as three
documentation gaps and a false alarm; together they explain an observed outcome in a consuming project.

| Rule the skills state | Status |
|---|---|
| "use records for immutable data carriers" | ⭐ **correct** |
| "never `@Nullable` for return types — use `Optional`" | **incomplete** — it says nothing about other positions |
| what a record *component* may be | **stated nowhere** |

⇒ **An author following the skills faithfully arrives at `record Foo(Optional<String> bar)`.**

Measured in the consuming project: **12+ configuration records with `Optional` components**, 10
`Optional` fields across 4 files, ~56 `Optional` parameter occurrences — **while already using
`@Nullable` 112 times and `@NullMarked` in 23 files.**

⭐⭐ **The correct idiom was already in use. The rule that would have directed it to fields, parameters,
and components was never stated.** ⛔ **This is a documentation gap, not an agent-discipline failure —
there was nothing to ignore.** The consuming project's own guidance says only "Optional for nullable
returns", so both layers were silent in the same way.

⛔ **Fixing the `Optional` rule alone does NOT close this.** The **record-component rule is where the two
correct-in-isolation rules meet**, and it is the one that must land.

## ⭐ One reported item is REFUTED, and is carried forward deliberately

The originating report checked the premise *"the Java skills demand the use of Lombok"* and **refuted it
first-party**: the decision table says *"immutable data carrier → Java record (not `@Value`)"*. The
consuming project's records are **compliant, not deviant**, and converting them to Lombok would violate
that table.

⇒ **Carry the refutation forward so the premise does not resurface as a defect.** ⚠ *A findings round
that only confirms suspicions is not doing its job* — this one demonstrated the opposite, and that is
worth preserving.

## Goal

The nullability guidance covers **every position** a type can occupy, records have a stated component
rule, and the two adjacent gaps that made the chain hard to see are documented with their reasons.

## Deliverables

1. **D0 — GATE: derive the positional rule set before writing it.** Mutates nothing.
   *Done when:* every position and every quoted rule is **confirmed against the skills' current text**.
   ⛔ **The proposed table below is the reporter's, not a verified one.** The skill text **has moved**
   since the report was written. **Confirm each position, then write.**
   ⛔ **Also verify the asserted absence:** that **no other skill already states the field/parameter
   rule.** An asserted absence is the higher-risk half — **if some standard already says it, the defect
   is discoverability, not absence, and D1 changes shape entirely.**
2. **D1 — Extend the null-safety guidance to every position, not just returns.**

   | Position | Rule |
   |---|---|
   | Return type | `Optional<T>`; never `@Nullable` |
   | Field | `@Nullable T`; **never `Optional<T>`** |
   | Parameter | `@Nullable T`, or an overload; **never `Optional<T>`** |
   | Record component | `@Nullable T`; **never `Optional<T>`** |

   *Done when:* all four positions are stated **with their reasons**.
   ⚠ **State the reasons — a rule without its reason gets re-litigated.** `Optional` is not
   `Serializable`; it costs an allocation and a dereference per access; and as a parameter it forces
   every caller to wrap.
3. **D2 — Add a Records section.** Component nullability; what belongs in a compact constructor
   (**validate, normalize, defensively copy — assign once**); and defaulting without a builder-default
   annotation.
   *Done when:* the section exists and makes the following distinction **explicit**.
   ⭐ **The distinction that must be explicit:** legitimate normalization, versus **reassignment
   gymnastics that exist only to unwrap an `Optional` the component should never have carried.** That is
   the shape a reader will actually meet, and the one the current text cannot help them with.
4. **D3 — Add the missing `switch` trigger.** Covered today: `switch` statement → `switch` expression.
   **Not covered:** an `if`/`else` chain over a **closed constant set** → `switch`.
   *Done when:* the trigger is stated, with the enum half.
   ⭐ **The enum half is the valuable half** — model the closed set as an enum so the `switch` is
   exhaustive and the unreachable trailing throw **disappears**. The observed instance was three string
   constants through sequential equality checks followed by a throw.
5. **D4 — Record the null-coalescing interaction with static analysis.** The analyser models
   `Objects.requireNonNullElse`'s result as carrying **the nullness of its arguments** — so the idiom
   that exists to *produce* a non-null value is modelled as possibly-null, producing false positives on
   exactly the path a null-annotation migration makes safe.
   *Done when:* it is named **together with the working alternative**, so the next migration does not
   rediscover it against a red gate.
   ⚠ It contributed to a first-pass run of 23 findings with the gate failing.
6. **D5 — Record the residual from the refuted item.** The Lombok decision table is silent on parameter
   contracts via `@NonNull`, and gives no trigger for auditing utility-class eligibility.
   *Done when:* **a sentence each.** ⛔ **Explicitly NOT a rule change** — these are gaps worth naming,
   not decisions to make without an operator.

⭐ **Split-guard verdict, recorded before hand-over:** six deliverables, **at the threshold**. **Split
evaluated and declined** — D1 and D2 **are the chain** and cannot be separated without reproducing the
defect, and D3–D5 are one-section additions to the same bundle in the same pass. ⭐ **D3 is the split
point if one is ever forced**: it is a different skill from the other five.

## Out of scope

- ⛔ **Converting the consuming project's records to Lombok.** The refuted premise. Those records are
  **compliant**, and converting them would violate the decision table the skills already state.
- **Changing any rule the skills currently get right.** This plan **adds** the positions that were never
  covered; it does not revisit the return-type rule, which is correct.
- **Editing the consuming project.** This is a skills-documentation change. The consuming project's code
  is **evidence**, not surface.
- **Making D5's two gaps into rules.** They are recorded as gaps. Turning them into rules is a decision
  with downstream effects on every Java project, and there is no operator here to make it.

## Expected surface

- `marketplace/bundles/pm-dev-java/skills/java-null-safety/SKILL.md` and
  `.../standards/null-safety-core.md` — D1, D2.
- `marketplace/bundles/pm-dev-java/skills/java-core/standards/java-17-features.md` and
  `.../java-21-features.md` — D3.
- `marketplace/bundles/pm-dev-java/skills/java-lombok/SKILL.md` — D5 only.

⭐ **Disjoint from the entire `plan-marshall` bundle queue** — this is `pm-dev-java` content only. **A
good parallel filler whenever a slot exists.**

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The skills say "use records for immutable data carriers" and "never `@Nullable` for return types" | HYPOTHESIS | the named skills — ⚠ **reported first-party by the filer with line references, but at an older bundle version and NOT re-read since.** *A corrective is a hypothesis until the named site is read.* **D0 re-reads them** |
| Nothing states what a record component may be | HYPOTHESIS | ⛔ an asserted **ABSENCE**, and **the higher-risk half.** Verify it exactly as an asserted presence — **if it exists somewhere, D1 changes shape** |
| The Lombok decision table prefers records over `@Value` | HYPOTHESIS | that table — ⭐ **this is the refutation**; confirm it so the premise cannot resurface |
| The consuming project shows 12+ records with `Optional` components, 10 fields, ~56 parameters, 112 `@Nullable`, 23 `@NullMarked` | HYPOTHESIS | ⚠ **another repository, not reachable from this clone.** **A count in a report is a sample** — these size the problem, they do not bound it, and **no deliverable should depend on them** |
| The analyser models the null-coalescing helper as carrying its arguments' nullness | HYPOTHESIS | reproduce against the analyser, or cite its documented behaviour. ⛔ **D4 must name a working alternative**, which requires confirming the behaviour first |
| The `if`/`else`-over-constants trigger is absent from the current guidance | HYPOTHESIS | the features standards — another asserted **absence** |

An asserted **absence** is verified exactly as an asserted presence, and is the higher-risk half.
Every count above is a **lead** — re-derive it at the moment of the claim.

## Verification

- ⛔ **Every deliverable here is text whose whole value is what a later author does with it, so the
  central check is a COLD READ.** Give the Step 6 verification sub-agent the new guidance with no other
  context, plus the task *"model a configuration value that may be absent, as a record component"*, and
  see what it writes. **The correct answer is `@Nullable T`.** If it writes `Optional<T>`, the guidance
  failed — and it failed in exactly the way the current guidance already fails, which is the whole point
  of the plan.
- **Run the same cold read for the parameter and field positions.** Each is an independent failure mode;
  covering one in prose does not cover the others in a reader's head.
- ⛔ **D0's absence check must be reported explicitly**, with what was searched. "I did not find it" and
  "it is not there" are different claims, and only the second justifies writing a new rule.
- Documentation-only changes are expected, so the build gate will likely take its docs-only path.
  **Confirm from git evidence rather than assuming.**

## Notes

- ⚠ **Not this epic's theme.** It sits here as the default sink under the routing rule, not because it
  fits the charter. **Say so if it is ever re-routed.**
- ⚠ Adjacent to another plan touching the same bundle's architecture gate. **Sequence, do not pair.**
- ⛔ **Do not go looking for the orchestrator spec, the originating report, or the consuming project.**
  The first two live under `.plan/` and the third is a different repository; none is reachable from this
  clone. Everything needed is in this file, and where the evidence lives elsewhere, this file says so.
