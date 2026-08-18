# Gaps — 270-java-skills-route-authors-to-an-anti-pattern-they-never-warn-about

**Source:** verification.md (same directory)   **Open items:** 7

All six deliverables landed and every *Done when:* condition is met; the guidance's two load-bearing
technical claims (accessor propagation of `@Nullable`, and `Optional`'s non-serializability) were
executed against `javac 21.0.10` — twice, the second time by an independent adversarial reviewer
against the real `jspecify-1.0.0` jar — and hold, and the D3 enum `switch` compiles exhaustively with
no `default`. The gaps below are **discoverability, an undischarged verification gate, and declared
residue** — none is a false rule, and none contradicts a *Done when:*.

**Adversarial review outcome:** no gap was refuted. G4 was raised `medium` → `high` (it is a guard
that passes against the defect it names), G1 was lowered `medium` → `low` (its harm story did not
survive checking), G3 gained decisive load-configuration evidence, and G7 was added from a sweep the
original verification ran too narrowly. See § "Refuted during adversarial review" at the end and
verification.md § "Adversarial review".

## G1 — Advertise the static-analysis section in the null-safety skill's Step-2 load list

- **Kind:** incomplete-sweep
- **Severity:** low *(lowered from `medium` in adversarial review — see "Why it matters")*
- **Where:** `marketplace/bundles/pm-dev-java/skills/java-null-safety/SKILL.md:54-59` — § "Step 2: Load
  Implementation Patterns (As Needed)", the "This provides rules for:" list
- **What is wrong:** D4 added § "Static Analysis and Null-Coalescing Helpers" to
  `standards/null-safety-patterns.md:146`, but the SKILL.md index that tells a reader what that file
  contains was not updated — its five bullets still end at "Migration strategy for new and existing
  code". The same commit *did* update the Step-1 index for the two new sections in
  `null-safety-core.md` (`SKILL.md:42-43`), so the omission is an inconsistency within the same diff,
  not a deliberate choice.
- **Why it matters:** index completeness and internal consistency of the same diff. **The original
  harm story was overstated and is corrected here.** It read: "a migrating author reads the SKILL.md
  index to decide whether to load the patterns file; the one section written for them is the one the
  index does not mention, so they load the file for some other reason or not at all." That does not
  hold — the Step-2 *load condition* one line above the list (`SKILL.md:48`, "**Load for
  implementation work** — writing null-safe code, collections, testing, **migration**:") already names
  migration, and D4's target reader is a migrator. The index list describes a file that is read
  whole once the condition fires; it does not gate the read. Residual harm is therefore a reader
  scanning the index and not learning the section exists — real, but low.
- **Fix:** add a bullet to the Step-2 list in `java-null-safety/SKILL.md`, e.g. `- Static analysis and
  null-coalescing helpers — the `Objects.requireNonNullElse` false positive and its alternative`,
  placed after "Unit testing null contracts" to match the file's section order.
- **Done when:** the Step-2 "This provides rules for:" list names the static-analysis /
  null-coalescing section, and its bullet order matches the heading order of
  `standards/null-safety-patterns.md`.
- **Module/topic:** `pm-dev-java` / `java-null-safety`

## G2 — Name the analyser behind the `requireNonNullElse` claim, or scope the claim to what was checked

- **Kind:** omission
- **Severity:** medium
- **Where:** `marketplace/bundles/pm-dev-java/skills/java-null-safety/standards/null-safety-patterns.md:146-166`
  — § "Static Analysis and Null-Coalescing Helpers"
- **What is wrong:** the section attributes the false positive to "Some null-analysis checkers" and
  names none, cites none, and links none. The plan's Claim-labels table required this claim be settled
  by "reproduce against the analyser, or cite its documented behaviour", and made it a precondition of
  D4 ("D4 must name a working alternative, which requires confirming the behaviour first").
  `report-01.md` § D0 records verification of the D1 positions, the three absences, the Lombok
  refutation and the placement decisions — and nothing about the analyser. The gate was never
  discharged. (The mechanism's JDK half is now **executed**, not read: reflection on
  `Objects.class.getMethod("requireNonNullElse", Object.class, Object.class)` under `java 21.0.10`
  prints `public static <T> T java.util.Objects.requireNonNullElse(T,T)` with `getAnnotations()` =
  `[]`, `getAnnotatedReturnType().getAnnotations()` = `[]`, and `[]` on both annotated parameter
  types — so an inference-based checker has nothing but the arguments to infer `T` from, and
  `requireNonNullElse((Duration) null, Duration.ofHours(1))` returns `PT1H` at runtime. What stays
  unchecked is the *checker's* behaviour: no null-analysis tool was run, because none is reachable
  from this repository. Mechanically grounded is still not observed.)
- **Why it matters:** a reader hitting a red gate cannot tell whether this section applies to their
  tool. Worse, the rest of `pm-dev-java` names only SonarQube as a static analyser
  (`java-maintenance/standards/refactoring-triggers.md:5-9`), so a reader will reasonably assume Sonar
  — which is not where this behaviour was observed. Advice to rewrite working code to placate an
  unnamed tool is advice a reader cannot evaluate.
- **Fix:** name the checker the behaviour was observed in (NullAway, Checker Framework, IntelliJ's
  nullability inspection, …) and link its documentation or issue; if no reproduction is available,
  rewrite the opening to state the mechanism rather than an observation — "`requireNonNullElse` is
  declared `static <T> T requireNonNullElse(T, T)` with no nullness annotations, so a checker that
  infers `T` from the arguments infers a `@Nullable` result" — and drop the unattributed "Some
  null-analysis checkers".
- **Done when:** the section either names a specific analyser with a citation, or derives the false
  positive from the JDK signature without attributing it to unnamed tools.
- **Module/topic:** `pm-dev-java` / `java-null-safety`

## G3 — Route the record-component nullability rule from where records are actually taught

- **Kind:** doc-drift
- **Severity:** medium
- **Where:** `marketplace/bundles/pm-dev-java/skills/java-core/standards/java-17-features.md:5-44` —
  § "Records (Java 16)"
- **What is wrong:** this section is the half of the chain the plan's problem statement names ("use
  records for immutable data carriers" — ⭐ correct), and it is where an author is standing when they
  choose a component's type. It contains three worked record examples and a "Records vs Lombok @Value"
  pointer, but no pointer to the new `pm-dev-java:java-null-safety` §§ "Null-Safety by Position" /
  "Records and Null-Safety". The only link between the two skills is the generic Related-Skills line at
  `java-core/SKILL.md:85` (`grep -rn "java-null-safety" .../java-core/` returns exactly one hit —
  re-derived in adversarial review, still exactly one).
- **Why it matters:** the plan diagnosed the defect as two correct-in-isolation rules meeting with
  nothing stated between them. The rule now exists, but only in the skill an author loads for
  null-safety work — not in the skill they load to write a record. An author who loads `java-core`
  alone still reaches `record Foo(Optional<String> bar)` with nothing to stop them, which is the
  original failure path. **That author is the default configuration, not a hypothetical** — evidence
  added in adversarial review: in the java domain's skill registry
  (`marketplace/bundles/pm-dev-java/skills/plan-marshall-plugin/extension.py:29-53`, profile `core`)
  `pm-dev-java:java-core` sits in `defaults`, always loaded, while `pm-dev-java:java-null-safety`
  sits in `optionals`, loaded only when selected. Worse, the always-loaded skill advertises the
  coverage it lacks: its registered description is "Java patterns, conventions, **null-safety**"
  (`marketplace/bundles/plan-marshall/skills/manage-config/standards/skill-domains-operations.md:50`).
- **Fix:** add one line to `java-17-features.md` § "Records (Java 16)", after the code block and beside
  the existing "Records vs Lombok @Value" pointer: a nullable component is `@Nullable T`, never
  `Optional<T>` — see `pm-dev-java:java-null-safety` § "Records and Null-Safety". Do not restate the
  rule or its reasons; cross-reference, per the repository's no-duplication documentation standard.
- **Done when:** `java-core/standards/java-17-features.md` § Records carries a cross-reference to the
  java-null-safety record-component rule, and a reader who loads only `java-core` for record work is
  pointed at it.
- **Module/topic:** `pm-dev-java` / `java-core` ↔ `java-null-safety`

## G4 — Extend the java-maintenance null-safety checklist to the other three positions

- **Kind:** incomplete-sweep
- **Severity:** high *(raised from `medium` in adversarial review — see "Why it matters")*
- **Where:** `marketplace/bundles/pm-dev-java/skills/java-maintenance/standards/compliance-checklist.md:36`
  — § "Null Safety"
- **What is wrong:** the checklist's only `Optional` line is "- No `@Nullable` on return types (use
  `Optional` instead)". It is correct but now covers one of four positions: the widened rule
  (`java-null-safety/SKILL.md:86`) also forbids `Optional<T>` as a field, parameter, or record
  component, and the checklist has no corresponding item. `report-01.md` recorded this as residue and
  dispositioned it out of scope for that run; it is still open at HEAD.
- **Why it matters:** **this is a guard that passes against the defect it names** — the severity
  rubric's `high` clause, and the reason adversarial review raised it. The checklist is the
  `java-maintenance` skill's verification surface, described in its own file table as "Full standards
  compliance verification" (`java-maintenance/SKILL.md:104`) and loaded under "Use when: Verifying
  code meets all Java development standards" (`SKILL.md:47`); `maintenance-prioritization.md:102`
  makes it step 4, "**Verify** using compliance-checklist.md". Its § "Null Safety" declares
  `**Standard**: pm-dev-java:java-null-safety` (`compliance-checklist.md:33`) and then checks **one
  of that standard's four positions**. A project carrying 12 records with `Optional` components — the
  exact population the plan was written about — passes the Null Safety section clean and is told it
  complies with the very skill that forbids them. In an epic about truthful signals, a
  completeness-claiming gate that reports green over the plan's own motivating defect is the defect.
  *(Counter-argument recorded so a third reviewer can weigh it: this is an agent-read Markdown
  checklist, not an automated CI gate, and no checklist is exhaustive. It is nonetheless the only
  verification surface `pm-dev-java` offers for this rule, and it claims completeness.)*
- **Fix:** add one item under § "Null Safety" in `compliance-checklist.md`, mirroring the Quality Rules
  line already in `java-null-safety/SKILL.md:86`: `- No `Optional<T>` for fields, parameters, or record
  components (use `@Nullable T`)`.
- **Done when:** `compliance-checklist.md` § "Null Safety" carries a check for the field / parameter /
  record-component prohibition alongside the existing return-type check.
- **Module/topic:** `pm-dev-java` / `java-maintenance`

## G5 — Correct the xref that points at an "Optional Usage" section in the wrong skill

- **Kind:** stale-statement
- **Severity:** low
- **Where:** `marketplace/bundles/pm-dev-java/skills/java-maintenance/standards/refactoring-triggers.md:48`
  — § "Inconsistent API Contracts"
- **What is wrong:** the line reads `- **See**: `pm-dev-java:java-null-safety` skill, section "Optional
  Usage"`. No such heading exists in either java-null-safety standards file (`grep -n "^#"` over
  `null-safety-core.md` and `null-safety-patterns.md` lists 15 and 12 headings respectively, none named
  "Optional Usage"); the section actually lives at
  `java-core/standards/java-17-features.md:206`. Pre-existing — `git log` shows it predates
  `a75060de` — and recorded as residue by `report-01.md`.
- **Why it matters:** a maintenance pass following the pointer loads the wrong skill and finds no such
  section, then either gives up or improvises. Now that java-null-safety *does* have a positional rule
  worth pointing at, the miss is more costly than before.
- **Fix:** repoint the line. If the intent is `Optional` mechanics (`orElseGet`, `Optional.stream`),
  cite `pm-dev-java:java-core` § "Optional Usage"; if the intent is the contract rule, cite
  `pm-dev-java:java-null-safety` § "Null-Safety by Position" — the enclosing trigger is return-scoped,
  so the latter is the better fit for the "Standards" line at `:49` and the former for `:48`.
- **Done when:** every `**See**:` target in `refactoring-triggers.md` § "Inconsistent API Contracts"
  names a heading that exists in the skill it names.
- **Module/topic:** `pm-dev-java` / `java-maintenance`

## G6 — Make the "reassignment gymnastics" example show reassignment gymnastics

- **Kind:** doc-drift
- **Severity:** low
- **Where:** `marketplace/bundles/pm-dev-java/skills/java-null-safety/standards/null-safety-core.md:231-250`
  — § "Legitimate normalization vs reassignment gymnastics"
- **What is wrong:** the heading and the opening sentence promise a contrast between legitimate
  compact-constructor normalization and unwrapping gymnastics. The code that follows contrasts
  `record Config(Optional<String> name) { }` with `record Config(@Nullable String name) { }` plus
  call-site comments — neither declaration has a compact constructor, so no reassignment of either kind
  appears. Per `report-01.md`, the original example was replaced during CodeRabbit round 1 (the
  replacement is correct; the heading was not adjusted with it).
- **Why it matters:** the prose distinction is stated, so the plan's *Done when:* is met, but a reader
  scanning for the shape they will actually meet in a codebase — a compact constructor doing
  `name = name.orElse("anonymous")` — does not see it rendered. Low: no wrong rule, only an example
  that under-delivers on its heading.
- **Fix:** either add a third snippet showing the gymnastics being condemned (a compact constructor
  that unwraps an `Optional` component, next to the legitimate `Set.copyOf` defensive copy already
  shown in the `TokenConfig` example at `:191-203`), or retitle the section to what the example
  teaches (e.g. "`Optional` component vs `@Nullable` component: what each costs the caller").
- **Done when:** the section's heading and its code examples describe the same contrast.
- **Module/topic:** `pm-dev-java` / `java-null-safety`

## G7 — Extend the java-maintenance switch trigger to the if/else-over-constants shape

- **Kind:** incomplete-sweep
- **Severity:** medium
- **Added by:** adversarial review (the original verification's D3 absence sweep was scoped to
  `.../skills/java-core` and never reached this file)
- **Where:** `marketplace/bundles/pm-dev-java/skills/java-maintenance/standards/refactoring-triggers.md:61-64`
  — § "When to Adopt Modern Java Features", trigger "**Legacy Switch Statements**"
- **What is wrong:** this is the bundle's detection surface for switch modernization, and its
  **Detection** line reads "Switch statements with break keywords, fall-through cases". D3 added a
  second, distinct shape — an `if`/`else` chain over a closed constant set ending in a throw
  (`java-core/standards/java-17-features.md:75`) — and no detection criterion for it was added here.
  The trigger's title ("Legacy Switch **Statements**") also presupposes a `switch` already exists.
  The trigger's `**See**` line does point at `java-17-features.md` § "Switch Expressions", under which
  the new subsection nests, so a reader who *reaches* the trigger will find the new material; the
  hole is upstream of that — nothing routes them to the trigger in the first place.
- **Why it matters:** D3's motivating instance is "three string constants through sequential equality
  checks followed by a throw" — code containing no `switch` at all. A maintenance pass scanning by
  the stated Detection criterion cannot surface it, so the one trigger written to catch it is
  unreachable from the detection step. Note the section's existing worked example (`:66-87`) already
  converts an `if`/`else if` chain — but over **types** (`instanceof`), which is Java-21 pattern
  matching, not the closed-constant-set case; its presence makes the constant-set omission easy to
  mistake for coverage.
- **Fix:** add a sibling trigger under § "When to Adopt Modern Java Features" in
  `refactoring-triggers.md`, immediately after the "Legacy Switch Statements" block (i.e. after
  `:87`), in the file's existing four-line trigger form: `**If/Else Chains Over Constants**:
  Sequential equality checks against a closed set of constants` / `- **Action Required**: Model the
  set as an enum and convert to an exhaustive switch expression` / `- **See**:
  \`pm-dev-java:java-core\` skill, \`standards/java-17-features.md\` section "From an if/else chain
  over a closed constant set"` / `- **Detection**: Chained \`if\`/\`else if\` on \`.equals(...)\` or
  \`==\` against literal constants, ending in a trailing \`throw\``.
- **Done when:** `refactoring-triggers.md` § "When to Adopt Modern Java Features" carries a trigger
  whose **Detection** line matches code that contains no `switch` keyword, and whose **See** line
  names the `java-17-features.md` "From an if/else chain over a closed constant set" section.
- **Module/topic:** `pm-dev-java` / `java-maintenance` ↔ `java-core`

## Refuted during adversarial review

**None.** Every gap G1–G6 was re-checked against the tree by an independent reviewer and survived as a
real finding; two had their severity corrected rather than their substance (G1 `medium` → `low`, G4
`medium` → `high`), and G3 gained load-configuration evidence it had asserted only as a scenario. The
specific clauses that were tested and *did not* survive as written are recorded inline where they
occur, not deleted:

- **G1's harm story** — "a migrating author … loads the file for some other reason or not at all" —
  is refuted by `java-null-safety/SKILL.md:48`, whose Step-2 load condition already names migration.
  The gap survives on index-completeness grounds only; the severity was lowered accordingly.
- **G6's fix text** cited "the legitimate trim/`Set.copyOf` normalization already shown at `:183`".
  The `TokenConfig` example at `:191-203` performs a `Set.copyOf` defensive copy and a blank-check;
  it performs no trim. Corrected in place.

What was checked to reach "none refuted", and what was not, is listed in verification.md
§ "Adversarial review".
