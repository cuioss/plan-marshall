# Gaps — 270-java-skills-route-authors-to-an-anti-pattern-they-never-warn-about

**Source:** verification.md (same directory)   **Open items:** 6

All six deliverables landed and every *Done when:* condition is met; the guidance's two load-bearing
technical claims (accessor propagation of `@Nullable`, and `Optional`'s non-serializability) were
executed against `javac 21.0.10` and hold, and the D3 enum `switch` compiles exhaustively with no
`default`. The gaps below are **discoverability, an undischarged verification gate, and declared
residue** — none is a false rule, and none contradicts a *Done when:*.

## G1 — Advertise the static-analysis section in the null-safety skill's Step-2 load list

- **Kind:** incomplete-sweep
- **Severity:** medium
- **Where:** `marketplace/bundles/pm-dev-java/skills/java-null-safety/SKILL.md:54-59` — § "Step 2: Load
  Implementation Patterns (As Needed)", the "This provides rules for:" list
- **What is wrong:** D4 added § "Static Analysis and Null-Coalescing Helpers" to
  `standards/null-safety-patterns.md:146`, but the SKILL.md index that tells a reader what that file
  contains was not updated — its five bullets still end at "Migration strategy for new and existing
  code". The same commit *did* update the Step-1 index for the two new sections in
  `null-safety-core.md` (`SKILL.md:42-43`), so the omission is an inconsistency within the same diff,
  not a deliberate choice.
- **Why it matters:** D4's stated purpose is "so the next migration does not rediscover it against a
  red gate". A migrating author reads the SKILL.md index to decide whether to load the patterns file;
  the one section written for them is the one the index does not mention, so they load the file for
  some other reason or not at all.
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
  discharged. (The mechanism is plausible: `static <T> T requireNonNullElse(T obj, T defaultObj)`
  carries no JDK nullness annotations, so an inference-based checker infers `T` = `@Nullable T` from
  the first argument. Plausible is not checked.)
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
  `java-core/SKILL.md:85` (`grep -rn "java-null-safety" .../java-core/` returns exactly one hit).
- **Why it matters:** the plan diagnosed the defect as two correct-in-isolation rules meeting with
  nothing stated between them. The rule now exists, but only in the skill an author loads for
  null-safety work — not in the skill they load to write a record. An author who loads `java-core`
  alone still reaches `record Foo(Optional<String> bar)` with nothing to stop them, which is the
  original failure path.
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
- **Severity:** medium
- **Where:** `marketplace/bundles/pm-dev-java/skills/java-maintenance/standards/compliance-checklist.md:36`
  — § "Null Safety"
- **What is wrong:** the checklist's only `Optional` line is "- No `@Nullable` on return types (use
  `Optional` instead)". It is correct but now covers one of four positions: the widened rule
  (`java-null-safety/SKILL.md:86`) also forbids `Optional<T>` as a field, parameter, or record
  component, and the checklist has no corresponding item. `report-01.md` recorded this as residue and
  dispositioned it out of scope for that run; it is still open at HEAD.
- **Why it matters:** the checklist is what a compliance/maintenance pass runs against a codebase. A
  project can pass it with 12 records carrying `Optional` components — the exact population the plan
  was written about — because the checklist never asks.
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
  that unwraps an `Optional` component into a field, next to the legitimate trim/`Set.copyOf`
  normalization already shown at `:183`), or retitle the section to what the example teaches
  (e.g. "`Optional` component vs `@Nullable` component: what each costs the caller").
- **Done when:** the section's heading and its code examples describe the same contrast.
- **Module/topic:** `pm-dev-java` / `java-null-safety`
