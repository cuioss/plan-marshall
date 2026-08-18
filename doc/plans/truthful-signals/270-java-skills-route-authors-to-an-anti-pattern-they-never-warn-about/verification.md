# Verification — 270-java-skills-route-authors-to-an-anti-pattern-they-never-warn-about

**Verified against:** commit `0e7c5869fd42d73a9d9abe92c41f21b082aa6820`   **Landed as:** PR #1195, commit `a75060de912bfd4310381ea2e88475a61a454f15`   **Verdict:** implemented-with-gaps

## Method

What was actually done, in order:

1. Read `plan.md` and `report-01.md` in full.
2. Located the landed commit: `git log --oneline --all --grep '#1195'` → `a75060de`. Read its full
   diff (`git show --stat`, `git show --name-status`, `git show <sha> -- <path>` for all five source
   files).
3. Confirmed the landed state **is** the HEAD state: `git log --oneline -3 -- <path>` on each of the
   five touched bundle files returns `a75060de` as the newest commit — no later plan or commit has
   modified them, so no supersession question arises for any deliverable.
4. Opened at HEAD, in full or in the relevant range:
   - `marketplace/bundles/pm-dev-java/skills/java-null-safety/SKILL.md`
   - `marketplace/bundles/pm-dev-java/skills/java-null-safety/standards/null-safety-core.md`
   - `marketplace/bundles/pm-dev-java/skills/java-null-safety/standards/null-safety-patterns.md`
   - `marketplace/bundles/pm-dev-java/skills/java-core/standards/java-17-features.md`
   - `marketplace/bundles/pm-dev-java/skills/java-core/standards/java-21-features.md`
   - `marketplace/bundles/pm-dev-java/skills/java-lombok/SKILL.md`
   - `marketplace/bundles/pm-dev-java/skills/java-maintenance/standards/compliance-checklist.md`
   - `marketplace/bundles/pm-dev-java/skills/java-maintenance/standards/refactoring-triggers.md`
   - `.claude/skills/cloud-plan-lane/SKILL.md` (§ Step 8 merge gate, to check the report's gate claims)
5. **Re-ran the report's own D0 absence searches against the pre-change tree** (`a75060de^`), so the
   absence claims are checked at the state the run saw, not at the post-change state:
   - `git grep -n -iE "record component" a75060de^ -- marketplace/bundles` → 3 hits, all Lombok
     `@Builder.Default` limitations, none about nullability. Absence claim holds.
   - `git grep -n -iE "else if|if/else|if-else|closed constant|constant set" a75060de^ -- .../java-core`
     → **zero** hits. Absence claim holds.
6. Re-ran the beyond-diff staleness sweep myself: `grep -rn "Optional" marketplace/bundles/pm-dev-java/`
   (36 hits outside the two edited standards files) and `grep -rn "@Nullable" --include=*.md
   --include=*.adoc --include=*.py .` outside `pm-dev-java` (2 hits, both skill-registry descriptions).
   Read every `Optional` hit in `java-17-features.md`, `java-performance-patterns.md`, `javadoc/**`,
   `refactoring-triggers.md`, `compliance-checklist.md` in context.
7. **Executed the guidance's code.** `javac 21.0.10` is available in this environment. Compiled all
   four Java examples the plan added (D3 enum switch, D2 `TokenConfig` compact constructor, D2
   `RetryPolicy` defaulting, D2 `Config` wrong/correct contrast) with `javac -Xlint:all` and ran them:
   - `-Xlint:all` clean, no warnings, no errors. The D3 enum `switch` expression compiles **without a
     `default`** — the exhaustiveness claim is true, not merely asserted.
   - Ran `Config.class.getMethod("name").getAnnotatedReturnType()` → prints `@Nullable
     java.lang.String`. The claim "`@Nullable` propagates to the generated accessor" is **executed and
     confirmed**, not read.
   - Ran serialization: `Serializable.class.isAssignableFrom(Optional.class)` → `false`;
     `record W(Optional<String> name) implements Serializable` → `NotSerializableException:
     java.util.Optional`; the `@Nullable String` equivalent serializes fine. The D1 "not
     `Serializable`" rationale is **executed and confirmed**.
8. Checked the report's PR-cycle claims against GitHub (MCP `pull_request_read`, methods `get_reviews`
   and `get_comments` on `cuioss/plan-marshall#1195`).
9. **No mutation check was performed** — and none was possible. This plan's entire surface is Markdown
   guidance: it adds no production code, no script, and no test. There is no guard to break and no
   test to drive RED. No file in the repository was modified by this verification; the only writes are
   `verification.md` and `gaps.md` in this directory.
10. **No `pytest` run** — the landed diff contains no `*.py` file (see `git show --name-status`), so
    there is no test the plan added to collect.

## Deliverable-by-deliverable

| # | Deliverable | Done-when condition | Implemented? | As documented? | Correct? | Complete? | Evidence (file:line / symbol / command + result) |
|---|---|---|---|---|---|---|---|
| D0 | GATE: derive the positional rule set; verify the asserted absences | Every position and quoted rule confirmed against current text; asserted absence verified and reported | Yes | Yes | Yes | Yes | `report-01.md` § D0 carries the positional table with per-position status + evidence, the explicit absence report with the search terms, and the "I did not find it vs it is not there" statement. I re-ran the two absence searches at `a75060de^`: `record component` → 3 Lombok-only hits; the D3 trigger terms → 0 hits. Both hold. |
| D1 | Null-safety guidance for every position, with reasons | All four positions stated with their reasons | Yes | Yes | Yes | Yes | `null-safety-core.md:138` § "Null-Safety by Position" (4-row table: return / field / parameter / record component) + `:156` § "Why `Optional` is a return type only" (3 reasons). Mirrored at `java-null-safety/SKILL.md:66-69` (Key Rules) and `:86` (Quality Rules). Serializable reason executed → `NotSerializableException: java.util.Optional`. |
| D2 | Records section: component nullability, compact constructor, defaulting | Section exists and makes the normalization-vs-gymnastics distinction explicit | Yes | Yes | Yes | Mostly | `null-safety-core.md:173` § "Records and Null-Safety"; `:183` § "The compact constructor"; `:205` § "Defaulting without a builder-default annotation"; `:231` § "Legitimate normalization vs reassignment gymnastics". Both examples compile `-Xlint:all` clean and run. Accessor propagation executed → `@Nullable java.lang.String`. See G3, G6. |
| D3 | `if`/`else`-over-closed-constants → `switch`, with the enum half | Trigger stated, with the enum half | Yes | Yes | Yes | Yes | `java-17-features.md:75` § "From an if/else chain over a closed constant set", before/after pair, enum-exhaustiveness paragraph, and the "constants must remain `String`" caveat. `javac -Xlint:all` compiles the after-example with no `default` — exhaustive. |
| D4 | Null-coalescing interaction with static analysis | Named together with the working alternative | Yes | Yes | Plausible, unconfirmed | No | `null-safety-patterns.md:146` § "Static Analysis and Null-Coalescing Helpers"; alternative (flow-narrowable ternary) present. But no analyser is named and neither plan nor report records a reproduction or citation. See G1, G2. |
| D5 | Record the two Lombok residuals — a sentence each, NOT rules | A sentence each | Yes | Yes | Yes | Yes | `java-lombok/SKILL.md:60` § "Known gaps in this guidance", two bullets, prefaced "these are **gaps, not rules**". Both statements re-derived: `grep -rn "NonNull" .../java-lombok/` returns only the new bullet itself — the guidance genuinely says nothing else about `@NonNull`; `@UtilityClass` appears at `SKILL.md:33,58` and `lombok-core-annotations.md:135` as a recommendation with no audit trigger. |

**D2 — one weak spot in an otherwise clean pass.** The section titled "Legitimate normalization vs
reassignment gymnastics" (`null-safety-core.md:231`) states the distinction in prose, which satisfies
the Done-when. Its code contrast, however, shows `record Config(Optional<String> name)` against
`record Config(@Nullable String name)` with call-site comments — an Optional-component-vs-nullable-
component contrast, not the promised normalization-code-vs-gymnastics-code contrast. Per `report-01.md`
this shape is the result of a CodeRabbit fix that removed a contrived guard; the replacement is
correct, but the heading now over-promises what the example shows. Cosmetic (G6).

**D4 — the one deliverable that is not a clean pass.** `null-safety-patterns.md:146-166` states that
"Some null-analysis checkers … model the result's nullness as carrying the nullness of its
**arguments**". The plan's Claim-labels table required this claim be settled by "reproduce against the
analyser, or cite its documented behaviour", and marked it a precondition ("D4 must name a working
alternative, which requires confirming the behaviour first"). `report-01.md` § D0 verifies the D1
positions, the three absences, the refutation and the placements — it says nothing about verifying the
analyser behaviour, and the shipped text names no analyser and carries no citation. The behaviour is
mechanically plausible (`Objects.requireNonNullElse(T, T)` carries no JDK nullness annotations, so a
generic-inference-based checker infers `T` = `@Nullable Duration` from the first argument), and the
prose is honestly hedged with "Some", so nothing false shipped — but the gate the plan set was not
discharged, and a reader cannot tell which tool to expect it from (G2). Separately, the section is
invisible from the skill's own load index (G1).

## Report accuracy

Re-derived every figure `report-01.md` states. **No contradiction found.** Specifically checked:

- **"seven files, all Markdown; the `-- '*.py'` filter returns empty."** `git show a75060de
  --name-status` → 7 paths: 1 rename (`…270-….md` → `…270-…/plan.md`, R100), 1 add (`report-01.md`),
  5 modifies, every one `.md`. No `*.py`, no Java, no other buildable file. **Confirmed.** The
  docs-only build-skip verdict rests on real git evidence, as the plan's Verification section demanded.
- **D0 positional table.** Every "current status" cell re-checked at `a75060de^`: return-type rule
  STATED (`null-safety-core.md` § "CRITICAL RULE: Never Use @Nullable for Return Types", still present
  at HEAD `:117`); field rule ABSENT; parameter rule PARTIAL (`null-safety-patterns.md:45` § "Nullable
  Parameters" pre-existed, the never-`Optional` half did not); record component ABSENT. **Confirmed.**
- **"The only near-match is `refactoring-triggers.md:49`."** Line 49 at HEAD reads "**Standards**: Use
  @NonNull for guaranteed results, Optional<T> for potential absence", under the "Inconsistent API
  Contracts" trigger whose Action/Detection lines are both return-scoped (`:47`, `:50`). The report's
  "not stale — correctly scoped to returns" disposition is **accurate**.
- **"`compliance-checklist.md:36`."** Line 36 at HEAD is exactly "- No `@Nullable` on return types (use
  `Optional` instead)". Line number and text **exact**.
- **"Pre-existing imprecise xref `refactoring-triggers.md:48`."** Line 48 at HEAD points at
  `pm-dev-java:java-null-safety` skill, section "Optional Usage"; `grep -n "^#"` over both
  java-null-safety standards files shows **no** "Optional Usage" heading, while
  `java-core/standards/java-17-features.md:206` has one. The report's characterisation is **exact**,
  and `git log` confirms it predates this commit.
- **"No java-21 edit; its switch content is type-pattern dispatch."** `grep -n -i switch
  java-21-features.md` → 4 hits, all under `## Pattern Matching in Switch` (`:5`), including record
  deconstruction. **Confirmed**, and the file is untouched by `a75060de`.
- **Reviewer participation table.** MCP `get_reviews` on #1195: `sourcery-ai[bot]` posted only
  "you have reached your weekly rate limit of 500000 diff characters"; `coderabbitai[bot]` posted
  "**Actionable comments posted: 7**" on `0d90640` plus a second review carrying the CAUTION block and
  the one comment that **failed to post** (the `plan.md` expected-surface Major). MCP `get_comments`:
  `cuioss-review-bot[bot]` posted "## PR Reviewer Guide 🔍 … No security concerns identified / No major
  issues detected / No relevant tests". Every row of the report's table, including "6 inline + 1 failed
  to post" and the 2-of-3 coverage figure, is **confirmed against GitHub**.
- **"No genuinely-stale consumer."** Re-swept independently. All 36 remaining `Optional` occurrences in
  `pm-dev-java` outside the two edited files are return types, local variables, or stream
  intermediates; none presents an `Optional` field, parameter, or record component as idiomatic. **The
  report's sweep claim holds.**

One thing the report **omits** rather than misstates: after the fix commit `21aa3eb`, CodeRabbit's
walkthrough comment was updated with "**Review limit reached** … Next review available in: 41 minutes",
so no full round-2 review ran on the fix head (CodeRabbit did reply on the individual threads at
22:03). This does not contradict the report — CodeRabbit's Step-7 verdict is correctly `reviewed`, it
did review the diff — and the contract gates on comment handling, not on a re-review. Recorded as an
observation, not a gap.

## Out-of-scope compliance

**Clean.** The landed diff touches exactly five bundle files, all inside `pm-dev-java`, plus this
plan's own directory. Checked against each declared boundary:

- *No consuming-project edit* — impossible from this repository, and nothing outside `marketplace/` and
  `doc/plans/` is touched.
- *No record → Lombok `@Value` conversion* — `java-lombok/SKILL.md:53` still reads "Immutable data
  carrier | Java record (not `@Value`)", unchanged by the diff.
- *Return-type rule not revisited* — `git show` on `null-safety-core.md` is a pure append
  (`@@ -134,3 +134,117 @@`); § "CRITICAL RULE: Never Use @Nullable for Return Types" is byte-identical
  to its pre-change form. The one pre-existing line the diff *replaced* anywhere is
  `java-null-safety/SKILL.md`'s Parameters row, widened from "Use `@Nullable` sparingly; prefer method
  overloads" to add the never-`Optional` half — a widening, not a reversal, exactly what D1 asks for.
- *D5's gaps not turned into rules* — the section is headed "Known gaps in this guidance" and states
  "these are **gaps, not rules**"; neither the Key Decision Guide table nor any standards file gained a
  new recommendation.
- No undeclared collateral change: no `plugin.json`, no registry, no other bundle, no workflow file.

The one place the run knowingly departed from the plan text is D4's and D3's **placement** (D4 →
`null-safety-patterns.md`, which the plan's Expected surface left unassigned; no `java-21-features.md`
edit, which the plan's Expected surface named). The plan itself labels Expected surface as the
reporter's hypothesis and makes D0 re-verify it; the report records and justifies both decisions, and I
confirmed the java-21 rationale. Not a boundary violation.

## Residue carried forward

`report-01.md` § Residue declares three items. Status in today's tree:

1. **`compliance-checklist.md:36` less complete than the widened rule** — **still open.** Line 36 at
   HEAD still checks only "No `@Nullable` on return types"; there is no check for `Optional` fields,
   parameters, or components anywhere in `java-maintenance`. Carried into gaps.md as G4.
2. **Imprecise xref `refactoring-triggers.md:48` → a java-null-safety "Optional Usage" section that
   lives in `java-core/java-17-features.md`** — **still open**, and confirmed pre-existing. Carried
   into gaps.md as G5.
3. **`sourcery-ai` did not review this diff (weekly quota)** — closed by time; the PR is merged and no
   Sourcery pass is retrievable. Not actionable, not carried forward.

The report's Step-9 "what have we learned" item — that the lane contract's report template does not say
a run must list its own `cloud-plan-lane` load — is presented for operator decision and explicitly not
shipped. It remains an operator decision; it is not this plan's gap and is not carried into gaps.md.

## What could NOT be verified

- **The cold read (the plan's central check).** `report-01.md` reports a sub-agent given only the three
  guidance files answering `@Nullable T` in all three positions. That run is not reproducible from the
  tree — no transcript was persisted. I can confirm the *guidance* now says the right thing in all
  three positions (and that its two load-bearing technical claims execute as stated), but not that the
  reported cold read happened as described. Nothing in the tree contradicts it.
- **The consuming project's counts** (12+ records, 10 fields, ~56 parameters, 112 `@Nullable`, 23
  `@NullMarked`). Another repository, unreachable from this clone — exactly as the plan's Claim-labels
  table says. No deliverable depends on them, so this does not weaken any verdict.
- **D4's analyser behaviour**, as an empirical fact. No null-analysis checker (NullAway, Checker
  Framework, IntelliJ inspections) is configured or reachable in this repository, and none is named in
  the guidance. I verified the *mechanism* is plausible from the JDK signature
  (`static <T> T requireNonNullElse(T, T)`, unannotated), but I did not reproduce the false positive.
  See G2.
- **The merge-queue `merge_group` verification run** for this commit. Not inspected; the docs-only
  footprint claim it rests on was verified directly from git instead.
