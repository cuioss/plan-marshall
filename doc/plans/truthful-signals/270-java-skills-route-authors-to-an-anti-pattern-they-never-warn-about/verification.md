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
     ⚠ **Corrected in adversarial review: this sweep's scope was too narrow as run.** It was confined
     to `.../skills/java-core`, which is where the report expected the trigger to be, not where a
     trigger could be. Re-run over the whole `pm-dev-java` bundle with a widened pattern
     (`… |chain of if|if chain|switch statement|nested if`) it returns 6 hits, of which one matters:
     `java-maintenance/standards/refactoring-triggers.md:61-87`, a "**Legacy Switch Statements**"
     trigger whose worked example already converts an `if`/`else if` chain — but over **types**
     (`instanceof` → pattern matching), not over a closed constant set. **The absence claim survives
     on the broader basis**, but it was not decisive as originally evidenced, and the near-miss it
     surfaces is a real gap the first pass missed. Filed as **G7**.
6. Re-ran the beyond-diff staleness sweep myself: `grep -rn "Optional" marketplace/bundles/pm-dev-java/`
   and `grep -rn "@Nullable" --include=*.md --include=*.adoc --include=*.py .` outside `pm-dev-java`
   (2 hits, both skill-registry descriptions).
   Read every `Optional` hit in `java-17-features.md`, `java-performance-patterns.md`, `javadoc/**`,
   `refactoring-triggers.md`, `compliance-checklist.md` in context.

   ⚠ **Corrected in adversarial review — the count originally stated here ("36 hits outside the two
   edited standards files") does not re-derive.** At HEAD (and the pm-dev-java files are unchanged
   since `a75060de`, so the figure should be stable) the honest numbers are: **86** total `Optional`
   hits in the bundle; **46** excluding the two edited standards files; **39** excluding all three
   edited `java-null-safety` files; **38** of those in `*.md`. No reading of "outside the two edited
   standards files" yields 36. Worse, the five files named as read account for only **32** hits, so
   **6 were neither counted nor named**: `java-core/SKILL.md:41`, `java-cdi/SKILL.md:32`,
   `java-cdi/standards/basic.md:110`, `java-quarkus/standards/container.md:123`,
   `ext-triage-java/standards/pr-comment-disposition.md:41,67`, and
   `manage-maven-profiles/scripts/profiles.py:154`. All six were opened in adversarial review: three
   are prose uses of the English word "optional", one is CDI's `Instance<T>` idiom (explicitly *not*
   `Optional`), one is a Python docstring, and two are triage phrasings about `Optional.get()` on a
   return value. **None presents an `Optional` field, parameter, or record component as idiomatic —
   the sweep's conclusion survives; only its arithmetic and its stated coverage were wrong.**

   The sweep was also **scoped only to `pm-dev-java`**, which leaves a hole, since
   `plan-marshall:ref-code-quality` is a *default* skill of the java domain. Closed in adversarial
   review: `grep -rn "Optional" .../ref-code-quality/` → 2 hits, `error-handling.md:151` (return-scoped,
   "Throw or use Optional/Result") and `code-organization.md:305` (Python `Optional[...]`). Neither is
   stale. `grep -rInE "record [A-Z][A-Za-z]*\(" marketplace/bundles/ --include=*.md` outside
   `pm-dev-java` → **zero** hits: no Java record is taught anywhere else in the marketplace.
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
| D0 | GATE: derive the positional rule set; verify the asserted absences | Every position and quoted rule confirmed against current text; asserted absence verified and reported | Yes | Yes | Yes | Yes | `report-01.md` § D0 carries the positional table with per-position status + evidence, the explicit absence report with the search terms, and the "I did not find it vs it is not there" statement. I re-ran the two absence searches at `a75060de^`: `record component` → 3 Lombok-only hits; the D3 trigger terms → 0 hits. Both hold. **Adversarial review re-ran both wider:** the field/parameter/component prohibition swept bundle-wide at `a75060de^` with `Optional<T>\|never .{0,20}Optional\|Optional as a (field\|parameter)` — the only pre-existing `Optional` rules anywhere are return-scoped (`refactoring-triggers.md:49`, `java-null-safety/SKILL.md:64`, `null-safety-core.md:102`, `javadoc-core.md:173`), so the absence holds on a much broader basis than originally evidenced. The D3 sweep widened past `java-core` surfaced a near-miss → **G7**; see Method § 5. |
| D1 | Null-safety guidance for every position, with reasons | All four positions stated with their reasons | Yes | Yes | Yes | Yes | `null-safety-core.md:138` § "Null-Safety by Position" (4-row table: return / field / parameter / record component) + `:156` § "Why `Optional` is a return type only" (3 reasons). Mirrored at `java-null-safety/SKILL.md:66-69` (Key Rules) and `:86` (Quality Rules). **Added in adversarial review:** the parameter half also lands in `null-safety-patterns.md:68-70` § "Nullable Parameters" ("**Never accept `Optional<T>` as a parameter.**"), the diff's `@@ -65,6 +65,10 @@` hunk — evidence the original row omitted. All heading line numbers re-derived exactly via `grep -n "^#"`. Serializable reason executed twice → `NotSerializableException: java.util.Optional`. |
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

## Adversarial review

**Reviewed by:** an independent agent that did not write this document.

**Checked.** Everything below was re-derived from the tree, not read out of this document or
`report-01.md`.

*Git and provenance.* `git cat-file -t 0e7c5869…` (exists), `git merge-base --is-ancestor` (it is an
ancestor of today's HEAD `45ec01f9`), `git log -1 a75060de…` (the #1195 merge, 2026-08-13),
`git show --name-status` (7 paths: 1 R100 rename, 1 add, 5 modifies, all `.md`, no `*.py`),
`git show --stat` (424 insertions, **1** deletion), and the per-file hunk headers — which confirm
`null-safety-core.md`'s `@@ -134,3 +134,117 @@` pure append and locate the single deletion in
`java-null-safety/SKILL.md`. `git log --oneline -2` on all five touched bundle files plus the three
untouched ones cited (`compliance-checklist.md`, `refactoring-triggers.md`, `java-21-features.md`)
confirms `a75060de` is still newest and the working tree is clean for `pm-dev-java`
(`git diff --quiet` → 0), so nothing here is mid-mutation by another agent.

*Executed, not read.* `javac`/`java 21.0.10` against the real `jspecify-1.0.0` jar found on this
machine. Compiled all four shipped Java examples verbatim with `-Xlint:all` → **exit 0, no warnings**,
including the D3 enum `switch` with **no `default`**. Then ran them:
`ConfigRight.class.getMethod("name").getAnnotatedReturnType()` → `@org.jspecify.annotations.Nullable()
java.lang.String` and `TokenConfig.validity()` likewise → accessor propagation **confirmed by
execution**. `Serializable.class.isAssignableFrom(Optional.class)` → `false`; serializing
`record ConfigWrong(Optional<String> name) implements Serializable` → `NotSerializableException:
java.util.Optional` **for both `Optional.of("x")` and `Optional.empty()`**, while the `@Nullable
String` twin serialized in 70 bytes with the value *and* with `null`. `RetryPolicy.of(3, null)` →
`RetryPolicy[maxAttempts=3, backoff=PT1S]`. Separately, reflection on
`Objects.requireNonNullElse(Object,Object)` → `public static <T> T …(T,T)`, `getAnnotations()` `[]`,
annotated return `[]`, both annotated params `[]`, and the call returns the fallback at runtime — G2's
mechanism clause is now executed rather than asserted.

*Sweeps re-run wider than the originals.* The `Optional` inventory re-counted five ways (86 / 46 / 39 /
38 / 32); the D0 field-parameter-component absence re-swept bundle-wide rather than by the reporter's
phrase; the D3 trigger absence re-swept across all of `pm-dev-java` rather than `java-core`; the
staleness sweep extended outside `pm-dev-java` to `ref-code-quality` (a java-domain **default** skill,
never swept originally) and to a bundle-wide search for Java record teaching. Every unnamed `Optional`
hit was opened.

*Load configuration.* `plan-marshall-plugin/extension.py:29-53` read directly to settle whether G3's
"an author who loads `java-core` alone" is real. It is the default.

*GitHub.* MCP `pull_request_read` `get` and `get_reviews` on `cuioss/plan-marshall#1195` — merged
2026-08-13, head `21aa3eb`, 7 changed files, 424/1, `sourcery-ai[bot]` rate-limited, `coderabbitai[bot]`
"Actionable comments posted: 7" on `0d90640` plus the CAUTION review carrying the one comment that
failed to post. The report's reviewer table and the "6 inline + 1 failed to post" figure hold.

**NOT re-checked.** (a) The cold read — still unreproducible, no transcript; this review adds nothing
to it. (b) The analyser false positive as an empirical fact — no null-checker is installed or
reachable, so G2 stays open on exactly the ground it was filed on. (c) The merge-queue `merge_group`
run. (d) The consuming project's counts — a different repository. (e) `report-01.md`'s narrative of
*how* the run proceeded (step ordering, sub-agent dispatch); only its checkable assertions were
re-derived. (f) No mutation test was attempted — correctly, since the surface is Markdown with no
guard to break. (g) `get_review_comments` bodies for the 6 inline CodeRabbit comments were not
re-read; only the review-level records were.

| Item | Original claim | Verdict | Evidence |
|---|---|---|---|
| **Verdict** | `implemented-with-gaps` | **upheld** | All six deliverables are implemented and every *Done when:* is met at HEAD; none is unimplemented, so `partially-implemented` would be wrong. D4's row ("Complete? No") is a discharged-deliverable-with-an-undischarged-gate, not a missing deliverable. |
| D0 | Absences verified and reported | **upheld, evidence widened** | Both absences survive a much broader sweep than the one originally run — but the original D3 sweep was scoped to `java-core` and would not have caught a counter-example living in `java-maintenance`. Conclusion right, method too narrow. → G7. |
| D1 | Four positions with reasons | **upheld** | Table at `null-safety-core.md:138`, reasons at `:156`, mirrored at `SKILL.md:66-69`/`:86`, parameter half additionally at `null-safety-patterns.md:68-70`. Serializability reason re-executed. |
| D2 | Records section, distinction explicit | **upheld** | Sections at `:173`/`:183`/`:205`/`:231` confirmed by `grep -n "^#"`; both examples recompiled and re-ran. |
| D3 | Trigger with the enum half | **upheld** | `java-17-features.md:75`, enum-exhaustiveness paragraph and `String`-caveat present; the after-example compiles with no `default`. |
| D4 | Named with a working alternative | **upheld** | `null-safety-patterns.md:146-166`; ternary alternative present; gate still undischarged (G2). |
| D5 | A sentence each, not rules | **upheld** | `java-lombok/SKILL.md:60-69`, two bullets under "these are **gaps, not rules**"; `@NonNull` grep re-run case-insensitively across the whole skill returns only the new bullet. |
| G1 | Step-2 index omits the D4 section — `medium` | **re-severitied → `low`** | The omission is real (`SKILL.md:54-59`, five bullets ending at migration strategy). Its harm story is not: `SKILL.md:48`'s load condition already names "migration", which is D4's exact target reader, and the list does not gate the read. |
| G2 | Analyser unnamed, gate undischarged — `medium` | **upheld, strengthened** | Section names no tool; `report-01.md` § D0 records no analyser check. The JDK-signature half of its mechanism is now executed (no annotations anywhere on `requireNonNullElse`). What is missing is a checker run, and none is reachable. `medium` is right — nothing false shipped, the prose is hedged "Some". |
| G3 | `java-core` § Records has no pointer — `medium` | **upheld, evidence upgraded** | The one-hit grep re-derived. New: `java-core` is a **default** skill of the java domain and `java-null-safety` an **optional** (`extension.py:29-53`), and `java-core`'s registered description advertises "null-safety". The failure path is the default path, not a scenario. Kept at `medium`: the rule does exist and is reachable, just not from where records are taught. |
| G4 | Checklist covers 1 of 4 positions — `medium` | **re-severitied → `high`** | Meets the rubric's "a guard that passes against the defect it names". `compliance-checklist.md` is the bundle's verification surface ("Full standards compliance verification", `java-maintenance/SKILL.md:104`; step 4 "**Verify**" in `maintenance-prioritization.md:102`); its § "Null Safety" names `pm-dev-java:java-null-safety` as its standard (`:33`) and checks one of that standard's four positions (`:36`). The plan's motivating population passes it clean. |
| G5 | Xref names a heading that does not exist — `low` | **upheld, figures exact** | `grep -n "^#"` → **15** headings in `null-safety-core.md`, **12** in `null-safety-patterns.md`, none "Optional Usage"; `java-17-features.md:206` **is** `## Optional Usage`. `refactoring-triggers.md:48` reads exactly as quoted. Every stated figure re-derives. |
| G6 | Heading over-promises its example — `low` | **upheld, citation fixed** | `:231-250` read: two record declarations, neither with a compact constructor, so no reassignment of either kind appears. The Fix text's "trim/`Set.copyOf` normalization already shown at `:183`" was imprecise — the `TokenConfig` example (`:191-203`) does a `Set.copyOf` defensive copy and a blank-check, no trim. Corrected. |
| **G7** | *(new)* Switch trigger not extended to the if/else-over-constants shape | **added** | `refactoring-triggers.md:61-64` Detection reads "Switch statements with break keywords, fall-through cases" — it cannot match code containing no `switch`, which is precisely D3's motivating instance. Found only by widening the D0 sweep past `java-core`. |
| Report figures | "seven files, all `.md`, no `*.py`"; "one deleted line"; `compliance-checklist.md:36`; `refactoring-triggers.md:48/49`; java-21 switch content; reviewer table | **upheld, all re-derived** | `--name-status`, `--stat` (1 deletion), exact line reads, `grep -n -i switch java-21-features.md` → 4 hits all under `## Pattern Matching in Switch`, MCP review records. |
| "36 hits outside the two edited standards files" | count | **refuted as a figure** | Does not re-derive under any of five readings (86/46/39/38); the five files named as read account for 32, leaving 6 hits neither counted nor named. All 6 opened; none is stale. Conclusion stands, count replaced. |
| "@Nullable outside `pm-dev-java` → 2 hits" | count | **upheld exactly** | Re-run: exactly 2, both skill-registry descriptions. |
| "No genuinely-stale consumer" | sweep | **upheld, on wider ground** | Re-swept including the 6 unnamed hits, `ref-code-quality`, and a bundle-wide hunt for Java record teaching (zero outside `pm-dev-java`). Nothing presents `Optional` as a field, parameter, or component. |

**Documents corrected.**
*verification.md*: Method § 5 now records that the D3 absence sweep was scoped too narrowly and what
the widened sweep found; Method § 6 replaces the unre-derivable "36" with the five honest counts, names
the 6 hits the sweep never enumerated and their dispositions, and closes the outside-`pm-dev-java`
scope hole; the D0 row records the widened absence sweeps; the D1 row gains the
`null-safety-patterns.md:68-70` parameter evidence it had omitted. The verdict is unchanged.
*gaps.md*: **Open items 6 → 7**; G4 `medium` → `high` with the rubric clause and a recorded
counter-argument; G1 `medium` → `low` with its refuted harm story kept visible rather than deleted;
G3 gains the default-vs-optional load evidence; G2 gains the executed reflection result; G6's `:183`
citation corrected to `:191-203`; **G7 added**; a `## Refuted during adversarial review` section added
recording that nothing was refuted outright and naming the two clauses that were.

**Residual doubt — what a third reviewer should look at first.**
1. **G4's severity.** It is the one judgement call here, and it turns on whether an agent-read Markdown
   checklist counts as a "guard". If it does not, G4 returns to `medium` and this review's headline
   correction goes with it. The counter-argument is recorded in the gap itself; weigh it rather than
   inheriting the verdict.
2. **The cold read remains the plan's central check and remains unverifiable.** Two independent
   reviewers have now confirmed the guidance *says* the right thing; neither has confirmed that a cold
   reader *derives* it. The cheapest way to close this is to re-run it — hand a fresh agent only the
   three guidance files and the task, and persist the transcript this time. Until then the plan's own
   stated success criterion is attested only by the run that had an interest in it passing.
3. **G2's analyser claim.** Still the only shipped sentence in this diff whose truth nobody has
   observed. Someone with NullAway or the Checker Framework available should spend ten minutes on it.
4. **G3 and G7 are the same shape as G4** — a rule that landed in one skill and was never wired into
   the surfaces that route readers to it. If a third reviewer finds a fourth instance, the right
   response is probably one plan about cross-skill routing rather than four separate line edits.
