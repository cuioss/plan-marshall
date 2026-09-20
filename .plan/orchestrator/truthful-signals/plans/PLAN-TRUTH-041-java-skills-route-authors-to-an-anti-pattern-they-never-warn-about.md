# PLAN-TRUTH-041: the Java skills route authors to an anti-pattern they never warn about

epic: truthful-signals
workstream: WS-01

## Objective

Four reported items on `pm-dev-java` that **only make sense as one chain**. Individually they read as
three doc gaps and a false alarm; together they explain an observed outcome in a consuming project.

| Rule the skills state | Where |
|---|---|
| "use records for immutable data carriers" | `java-lombok/SKILL.md:53`, `java-17-features.md:44` — ⭐ **correct** |
| "never `@Nullable` for return types — use `Optional`" | `java-null-safety/SKILL.md:64,:81`, `null-safety-core.md:119` — **incomplete** |
| what a record *component* may be | **nowhere** |

⇒ An author following the skills **faithfully** arrives at `record Foo(Optional<String> bar)`.
Measured in the consuming project: **12+ configuration records with `Optional` components**, 10
`Optional` fields across 4 files, ~56 `Optional` parameter occurrences — **while already using
`@Nullable` 112 times and `@NullMarked` in 23 files.**

⭐⭐ **The correct idiom was already in use. The rule that would have directed it to fields, parameters
and components was never stated.** ⛔ **This is a documentation gap, not an agent-discipline failure —
there was nothing to ignore.** The consuming project's own `CLAUDE.md` says only "Optional for nullable
returns", so both layers were silent in the same way.

⛔ **Fixing the `Optional` rule alone does NOT close this.** The record-component rule is where the two
correct-in-isolation rules meet, and it is the one that must land.

## ⭐ One reported item is REFUTED and is included deliberately

The originating report checked the operator's premise *"java/java-cui demands the usage of lombok"* and
**refuted it first-party**: `java-lombok/SKILL.md:53` says *"Immutable data carrier → Java record (not
`@Value`)"*. The consuming project's records are **compliant, not deviant**; converting them to Lombok
would violate the decision table. ⇒ **Carry this refutation forward — the premise must not resurface as
a defect.** ⚠ *A findings round that only confirms suspicions is not doing its job* — the filer said so
and demonstrated it.

## Deliverables

1. **D0 — GATE: derive the positional rule set before writing it.** ⛔ The proposed table below is the
   filer's, not a verified one — **confirm each position against the skills' current text**, which has
   moved since bundle 0.1.1276.
2. **D1 — extend `java-null-safety` to every position, not just returns.**

   | Position | Rule |
   |---|---|
   | Return type | `Optional<T>`; never `@Nullable` |
   | Field | `@Nullable T`; **never `Optional<T>`** |
   | Parameter | `@Nullable T`, or an overload; **never `Optional<T>`** |
   | Record component | `@Nullable T`; **never `Optional<T>`** |

   ⚠ **State the reasons** (not `Serializable`; an allocation and a dereference per access; as a
   parameter it forces every caller to wrap) — a rule without its reason gets re-litigated.
3. **D2 — add a Records section**: component nullability, what belongs in a compact constructor
   (**validate, normalize, defensively copy — assign once**), and defaulting without `@Builder.Default`.
   ⭐ **The distinction that must be explicit**: legitimate normalization vs **reassignment gymnastics
   that exist only to unwrap an `Optional` the component should never have carried** (exemplar:
   `config/model/RateLimitConfig.java`).
4. **D3 — add the missing `switch` trigger to `java-core`.** Covered today: `switch` statement →
   `switch` expression. **Not covered**: an `if`/`else` chain over a closed constant set → `switch`.
   ⭐ **The enum half is the valuable half** — model the closed set as an enum so the `switch` is
   exhaustive and the unreachable-default throw disappears. Observed instance:
   `auth/AuthenticationStage.java:112-127`, three `String` constants through sequential
   `if (CONST.equals(x))` blocks then a trailing throw.
5. **D4 — record the `Objects.requireNonNullElse` interaction.** SonarJava models the result as
   carrying the **nullness of its arguments**, so the idiom that exists to produce a non-null value is
   modelled as possibly-null — false positives on exactly the path a JSpecify migration makes safe.
   **Name it with the working alternative** so the next migration does not rediscover it against a red
   gate. ⚠ Contributed to 23 first-pass Sonar findings with the gate FAILED.
6. **D5 — record the residual from the refuted item**: the Lombok table is silent on `@NonNull` for
   parameter contracts and gives no trigger for auditing `@UtilityClass` eligibility. **A sentence
   each — explicitly NOT a rule change.**

⚠ **Six deliverables, at the scope-bloat threshold.** Split evaluated and **declined**: D1 and D2 are
the chain and cannot be separated without reproducing the defect; D3–D5 are one-section additions to
the same bundle in the same pass. ⭐ **D3 is the split point if one is forced** — it is `java-core`, a
different skill from the other five.

## Claim Labels

- **REPORTED, checked first-party by the filer** (skill text read, line-referenced) at bundle
  **0.1.1276**: every quoted line and the refutation. ⚠ **NOT re-read by this orchestrator** — the
  quotes are precise and mutually consistent, but *a corrective is a hypothesis until the named site is
  read*. **D0 re-reads them.**
- **REPORTED**: all consuming-project counts (12+ records, 10 fields, ~56 parameters, 112 `@Nullable`,
  23 `@NullMarked`). ⚠ **A count in a report is a sample** — they size the problem, they do not bound it.
- **HYPOTHESIS**: no other skill states the field/parameter rule elsewhere. ⛔ **An asserted ABSENCE is
  the higher-risk half — verify it exactly as an asserted presence.** If some standard already says it,
  the defect is discoverability, not absence, and D1 changes shape.

## Expected Surface

- **OBSERVED (per the report)**: `pm-dev-java:java-null-safety` SKILL.md + `standards/null-safety-core.md`
- **OBSERVED**: `pm-dev-java:java-lombok/SKILL.md` (D5 only)
- **OBSERVED**: `pm-dev-java:java-core/standards/java-17-features.md`, `java-21-features.md` (D3)

## Dependencies and Sequencing

- ✅ **DISJOINT FROM THE ENTIRE `plan-marshall` QUEUE** — `pm-dev-java` bundle content only, no overlap
  with either running plan. ⭐ **A good parallel filler whenever a slot exists.**
- ⚠ **Not this epic's theme.** Parked here as the default sink under the three-way routing rule, not
  because it fits the charter. **Say so if it is re-routed.**
- ⚠ Adjacent to `PLAN-TRUTH-042` (same bundle, `arch-gate-java`). **Sequence, do not pair.**

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-041-java-skills-route-authors-to-an-anti-pattern-they-never-warn-about.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message. Qualifiers
are in `persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
