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

# Agent-facing documentation surfaces state things that are not true

**Epic:** truthful-signals
**Branch prefix:** `chore` — every change is a documentation, standards, or comment correction; no
behaviour changes and no capability is added.

## Problem

Thirty defects, filed by ten earlier runs in this epic, share one shape: a document an **agent or an
operator reads as an oracle** states something the tree does not support. A closed enum is short by
two members, so an agent filing a legitimate `arch-constraint` finding concludes the type is
invented. A configuration table documents a knob that was deleted, so an operator writes a key
nothing reads and is told it succeeded. A compliance checklist claims to verify a four-position rule
and checks one position, so a codebase carrying the exact defect the rule forbids passes clean. A
casing rule says "upper case" four lines above examples reading `gRPC` and `mTLS`. A standard's
closing instruction forbids, without qualification, the backgrounding that a named seam is mandated
to perform.

The mechanism is uniform and is not a code bug: each of these documents was **written correctly once
and then diverged from its subject** — a constant gained members, a knob was retired, a rule was
widened, a section was replaced without adjusting its heading — and nothing recomputes the document
from its subject. The subjects are all readable at HEAD: `FINDING_TYPES` and `LESSON_CATEGORIES` in
`marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts/constants.py`, the `configurable:`
frontmatter of `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md`, the four-position
rule at `marketplace/bundles/pm-dev-java/skills/java-null-safety/SKILL.md:86`, the leaf-dispatch
invariant in `marketplace/bundles/plan-marshall/skills/ref-workflow-architecture/standards/agents.md`.
Each divergence is therefore checkable rather than arguable.

Every gap named below was opened at HEAD during authoring and confirmed still present. None was found
already closed.

## Goal

Every document this plan touches states what its subject actually is, and states it in a way a reader
who has only that document reaches the correct conclusion from. Where a document publishes a
population — a set of finding types, a set of configuration knobs, a set of absent affordances, a set
of statuses — it either equals the population derived from the tree or says explicitly that it is not
a complete enumeration. Where a document publishes a rule, the rule's scope is stated so a reader
cannot apply it to a case it was never true of.

## Deliverables

Eight deliverables, closing thirty gaps. **D1–D3 carry the three `high` gaps and land first**; a run
that has to stop early must have shipped them. Each deliverable is committed and pushed separately —
see `cloud-plan-lane` for the push discipline and why the remote is the only durable store here.

Throughout: **every count, member list, and line number below is a lead, not a fact.** Line numbers
are given so you can find the site quickly; re-derive the content at the moment you change it, and if
a line number is off, the quoted text is the identifier — search for it. If a quoted text is absent
entirely, that is a finding: record it and say so, do not invent a substitute site.

---

1. **D1 — The enum and registration claims in three `plan-marshall` skill documents**
   (closes 100/G1 **high**, 100/G2, 100/G4)

   **Gating derivation, first — halt if it fails.** Parse
   `marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts/constants.py` and recover the
   literal tuples `FINDING_TYPES` and `LESSON_CATEGORIES` — by `ast` parse of the assignment, not by
   eye and not by grep. Record both member lists, in order, in the run report. **If either constant
   cannot be recovered as a literal tuple** (it moved, it became computed, the file is gone),
   **stop this deliverable, report the plan blocked at D1, and do not hand-type a member list** — a
   hand-typed enum is the exact defect this deliverable closes, and reproducing it inside the fix
   would be worse than shipping nothing.

   With the derived sets in hand:

   - **(a)** `marketplace/bundles/plan-marshall/skills/manage-findings/SKILL.md` — the `Types:` line
     in § Finding Types (near `:70`) enumerates twelve types; make it equal `FINDING_TYPES` element
     for element and in `FINDING_TYPES` order. The § Storage file tree (fenced near `:40-62`, rows
     near `:45-56`) lists twelve `{type}.jsonl` files; add the missing rows in the same order —
     `arch-constraint.jsonl` after `sonar-issue.jsonl`, `pr-comment-overflow.jsonl` after
     `pr-comment.jsonl`, matching `manage-findings/standards/jsonl-format.md`. **Do not restate the
     semantics of the added types** — `standards/jsonl-format.md` owns them, and duplication is what
     the repository's documentation standards forbid.
   - **(b)** `marketplace/bundles/plan-marshall/skills/manage-lessons/SKILL.md` — § Operations carries
     two incomplete `--category` enums, at the `update` fenced form (near `:207`) and in the `list`
     parameter list (near `:260`). Make both list all `LESSON_CATEGORIES` members. Write the fenced
     form at `:207` in the brace style the canonical block already uses
     (`[--category {bug|improvement|anti-pattern|arch-constraint}]`) so the canonical-block enum-drift
     analyzer can see it.
   - **(c)** `marketplace/bundles/plan-marshall/skills/tools-integration-ci/SKILL.md` (near `:40`)
     states *"This skill is a script-only library (not registered in plugin.json)."* It **is**
     registered — `marketplace/bundles/plan-marshall/.claude-plugin/plugin.json` carries
     `"./skills/tools-integration-ci"`. Drop the parenthetical. Then sweep for the **class**, not the
     phrasing: `grep -rniE "(not|never|must not be) registered in .?plugin\.json" marketplace/bundles/
     --include=*.md`. For every hit, check whether the named skill is registered in its own bundle's
     `plugin.json`. Fix each that is; leave hits that are about *project* registration with the build
     server, or that name no skill at all, and **name each survivor and its reason in the run report**
     rather than asserting the sweep came back clean.

   *Done when:* the type set on the `Types:` line and the set of `{type}.jsonl` rows in the storage
   tree each equal the `FINDING_TYPES` tuple recovered by the gating derivation, element for element;
   `grep -c "arch-constraint" marketplace/bundles/plan-marshall/skills/manage-findings/SKILL.md` is
   non-zero; every `--category` enum in `manage-lessons/SKILL.md` lists all `LESSON_CATEGORIES`
   members; and the class sweep in (c) returns no file that claims a skill is unregistered while its
   own bundle `plugin.json` registers it, with every remaining hit listed in the report with its
   reason for surviving.

2. **D2 — Configuration truth on the four consumer-facing `doc/user/` pages**
   (closes 190/G1 **high**, 190/G2, 190/G3, 190/G8, 200/G8)

   - **(a) Delete the dead merge knob.** `doc/user/parallelism-and-locking.adoc` (near `:55`) carries
     a table row for `steps['default:pre-submission-self-review'].drop_review_on_scope_gate` with
     default `false`. The knob does not exist anywhere under `marketplace/bundles/`, and the step-set
     path accepts any `--param` name without checking it, so an operator following this row gets a
     `success` return and a persisted key nothing reads. Delete the row. Nothing else on either page
     references the knob, so no surrounding prose needs adjusting — confirm that rather than assume
     it.
   - **(b) Cover the automatic-review knob population.** *Derivation, then edit.* The declared
     step-owned knob set is the `configurable:` frontmatter block of
     `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md` — a plain YAML block in a
     git-tracked file, with a `key:`, a `default:` and a `description:` per entry. Enumerate its keys.
     Compare against the row set of the `[#automated-review]` table in `doc/user/configuration.adoc`
     (near `:412-425`). At authoring time the table was short by `review_rate_window_await` (default
     `false`) and `review_rate_window_timeout_seconds` (default `3600`) — **re-derive, do not trust
     that pair.** Add one row per missing key, after the `re_review_on_timeout` row, taking the
     wording from that key's `description:` in the frontmatter and pointing onward to
     `automatic-review/SKILL.md` § "Rate-limit refusal recovery (opt-in)" for the escalation contract
     rather than restating it. The table also carries `bot_lists_provenance`, which is **not** a
     frontmatter key — it is written by the steward migration, so it is correctly documented and is
     not an orphan; keep it and say so in the report.
     **If the `configurable:` block cannot be read** (frontmatter restructured, keys moved), do not
     add rows from this plan's text: record that half of (b) as blocked, with what you found instead,
     and complete the rest of D2.
   - **(c) Drop the meta-project claim from `recipes.adoc`.** `doc/user/recipes.adoc` (near `:30`)
     ends its micro-lane "Keeps" bullet with *"Lessons capture and the meta-project derived-state
     steps also stay in."* A consumer project has no meta-project derived-state steps. Drop that
     clause, leaving "Lessons capture also stays in."
   - **(d) Scope the enforcement-hook remedy.** `doc/user/enforcement-hook.adoc` (near `:21`) tells a
     reader whose generated executor is stale to *"Regenerate it via `/sync-plugin-cache` +
     `/marshall-steward`"*. `/sync-plugin-cache` is meta-project-only — it exists only under
     `.claude/skills/`, and no bundle ships it, so a consumer installation does not carry the command.
     The message fires from a hook denial, i.e. at a moment the operator is blocked and following it
     literally. Replace with *"Regenerate it via `/marshall-steward`"*, and add the meta-project half
     back only as an explicitly scoped parenthetical, in the style `doc/user/efforts.adoc` already
     uses for its meta-project-only paragraph.
   - **(e) Complete the `balanced` preset row.** `doc/user/efforts.adoc` (near `:66`) says of the
     `balanced` preset *"triage stays at `level-3`"* and states a summed-level spread of 36; the row
     omits `phase-6-finalize.default: level-3`, so what it describes reconstructs to a different
     total than it states. The `high-end` row directly below shows the table's own convention (it
     names the finalize-default slot explicitly). Mirror that phrasing in the `balanced` row. Verify
     by summing what each of the three rows describes against the spread number that row states —
     re-derive all three totals; do not assume only `balanced` is wrong.

   *Done when:* `grep -rn drop_review_on_scope_gate doc/` returns no hit outside `doc/plans/`; every
   key in the `configurable:` block of `automatic-review/SKILL.md` has a row in the
   `[#automated-review]` table, and every table row that is not such a key has a recorded reason in
   the run report; `grep -n 'meta-project' doc/user/recipes.adoc` returns nothing;
   `grep -n 'sync-plugin-cache' doc/user/enforcement-hook.adoc` returns either nothing or only a hit
   inside a clause explicitly scoped to the meta-project; and each of the three preset rows in
   `efforts.adoc` names every slot whose level differs from that row's stated default, with the
   described levels summing to the spread number the row states.

3. **D3 — The `pm-dev-java` maintenance surfaces that claim to verify what they do not**
   (closes 270/G4 **high**, 270/G5, 270/G7)

   - **(a) Complete the null-safety checklist.**
     `marketplace/bundles/pm-dev-java/skills/java-maintenance/standards/compliance-checklist.md`
     § "Null Safety" declares its standard as `pm-dev-java:java-null-safety` and then checks one of
     that standard's four `Optional` positions — it carries *"No `@Nullable` on return types (use
     `Optional` instead)"* and nothing for fields, parameters, or record components. The checklist is
     `java-maintenance`'s verification surface, so a project carrying records with `Optional`
     components passes its Null Safety section clean while violating the standard the section names.
     Add one item mirroring the rule as `java-null-safety/SKILL.md` already states it (near `:86`):
     *"No `Optional<T>` for fields, parameters, or record components (use `@Nullable T`)"*. Copy the
     wording from that line at the moment of the edit rather than from this plan.
   - **(b) Repoint the broken xref.**
     `marketplace/bundles/pm-dev-java/skills/java-maintenance/standards/refactoring-triggers.md`
     § "Inconsistent API Contracts" (near `:48`) reads
     ``- **See**: `pm-dev-java:java-null-safety` skill, section "Optional Usage"``. No such heading
     exists in either `java-null-safety` standards file; § "Optional Usage" lives in
     `marketplace/bundles/pm-dev-java/skills/java-core/standards/java-17-features.md`. The trigger is
     about `Optional` mechanics, so repoint the `**See**` line at
     `pm-dev-java:java-core` § "Optional Usage". Confirm the heading exists in the file you point at
     before committing.
   - **(c) Add the missing detection trigger.** The same file's
     § "When to Adopt Modern Java Features" carries a "Legacy Switch Statements" trigger whose
     **Detection** line is *"Switch statements with break keywords, fall-through cases"* — it cannot
     surface the shape `java-17-features.md` teaches under "From an if/else chain over a closed
     constant set", which contains no `switch` at all. Its adjacent worked example converts an
     `if`/`else if` chain over **types** (`instanceof`), which makes the constant-set omission look
     like coverage. Add a sibling trigger immediately after the Legacy Switch block, in the file's
     existing four-line trigger form:
     `**If/Else Chains Over Constants**: Sequential equality checks against a closed set of constants`
     / `- **Action Required**: Model the set as an enum and convert to an exhaustive switch expression`
     / ``- **See**: `pm-dev-java:java-core` skill, `standards/java-17-features.md` section "From an if/else chain over a closed constant set"``
     / ``- **Detection**: Chained `if`/`else if` on `.equals(...)` or `==` against literal constants, ending in a trailing `throw` ``.
     Confirm the **See** target heading exists in `java-17-features.md` under § Switch Expressions
     before committing; if it does not, record that and adjust the pointer to the heading that does.

   *Done when:* `compliance-checklist.md` § "Null Safety" carries a check for the field / parameter /
   record-component prohibition alongside the existing return-type check; every `**See**:` target in
   `refactoring-triggers.md` § "Inconsistent API Contracts" names a heading that exists in the skill
   it names, verified by opening that skill; and § "When to Adopt Modern Java Features" carries a
   trigger whose **Detection** line matches code containing no `switch` keyword and whose **See** line
   names an existing heading in `java-17-features.md`.

4. **D4 — `java-null-safety` and `java-core`: routing, attribution, and an example that matches its
   heading** (closes 270/G1, 270/G2, 270/G3, 270/G6)

   - **(a) Route the record rule from where records are taught.**
     `marketplace/bundles/pm-dev-java/skills/java-core/standards/java-17-features.md` § "Records
     (Java 16)" is where an author stands when choosing a component's type, and `java-core` is a
     default-loaded skill in the java domain while `java-null-safety` is opt-in — so the author who
     needs the rule is the one least likely to have loaded it. Add **one line** after the section's
     code block, beside the existing "Records vs Lombok @Value" pointer: a nullable component is
     `@Nullable T`, never `Optional<T>` — see `pm-dev-java:java-null-safety` § "Records and
     Null-Safety". **Cross-reference only; do not restate the rule or its reasons.**
   - **(b) Advertise the static-analysis section in the load index.**
     `marketplace/bundles/pm-dev-java/skills/java-null-safety/SKILL.md` § "Step 2: Load Implementation
     Patterns" carries a "This provides rules for:" list whose bullets stop at "Migration strategy for
     new and existing code", while `standards/null-safety-patterns.md` gained a
     § "Static Analysis and Null-Coalescing Helpers". Add a bullet for it, positioned so the bullet
     order matches the heading order of `null-safety-patterns.md` — re-derive that heading order at
     the moment of the edit rather than taking the position from this plan.
   - **(c) Ground the `requireNonNullElse` claim in the signature, not in unnamed tools.**
     `marketplace/bundles/pm-dev-java/skills/java-null-safety/standards/null-safety-patterns.md`
     § "Static Analysis and Null-Coalescing Helpers" attributes a false positive to *"Some
     null-analysis checkers"*, names none, and cites none — so a reader hitting a red gate cannot tell
     whether the section applies to their tool, and the only static analyser the rest of `pm-dev-java`
     names is SonarQube, which is not where the behaviour was seen.
     **No decision is required here and none may be taken:** no null-analysis checker is reachable
     from this repository, so the "name the analyser with a citation" branch is not available to this
     run. Take the mechanism branch: rewrite the opening to derive the false positive from the JDK
     declaration — `Objects.requireNonNullElse` is declared `static <T> T requireNonNullElse(T, T)`
     with no nullness annotations on the method, the return type, or either parameter, so a checker
     that infers `T` from the arguments infers a possibly-null result — and delete the unattributed
     *"Some null-analysis checkers"*. Leave the two code examples and the closing recommendation as
     they are. **Do not add a named analyser you did not run.**
   - **(d) Make the example show what its heading promises.**
     `marketplace/bundles/pm-dev-java/skills/java-null-safety/standards/null-safety-core.md`
     § "Legitimate normalization vs reassignment gymnastics" promises a contrast between legitimate
     compact-constructor normalization and unwrapping gymnastics; the two snippets that follow
     contrast an `Optional` component with a `@Nullable` component and contain no compact constructor
     at all, so neither kind of reassignment appears. Add a third snippet, after the existing pair,
     showing the gymnastics the heading condemns — a compact constructor that unwraps an `Optional`
     component (e.g. `name = name.orElse("anonymous")`) — labelled as the shape to avoid, so the
     section's heading and its code describe the same contrast. Keep the heading; keep both existing
     snippets byte-identical.

   *Done when:* `java-17-features.md` § Records carries a cross-reference to the `java-null-safety`
   record-component rule and restates none of it; the Step-2 "This provides rules for:" list names the
   static-analysis / null-coalescing section with its bullet order matching that file's heading order;
   § "Static Analysis and Null-Coalescing Helpers" derives the false positive from the JDK signature
   and attributes it to no unnamed tool and to no tool this run did not execute; and
   § "Legitimate normalization vs reassignment gymnastics" contains a compact constructor performing
   the unwrap it condemns.

5. **D5 — `extension-api` build standards: scope, spellings, vocabulary, and one reachable path**
   (closes 110/G2, 110/G3, 110/G6, 110/G7, 430/G6)

   All five sit in
   `marketplace/bundles/plan-marshall/skills/extension-api/standards/build-systems-common.md`, or in
   the two agent-facing documents that should reach it.

   - **(a) Scope residue (c) to the tier it is true of** (110/G7). The section
     § "Run a long build in the foreground with an explicit 600000 ms Bash timeout" closes *"Do **not**
     background a long build yourself — run it in the foreground at the 600000 ms bound and let the
     harness manage it"*, and the surrounding section asserts its rules hold for every build engine.
     `marketplace/bundles/plan-marshall/skills/ref-workflow-architecture/standards/agents.md` is the
     declared SSOT for build-tier ownership on the leaf boundary and says the opposite in two
     directions: an `execution_tier: orchestrator` build MUST NOT be run by a leaf inline **or**
     backgrounded, and the `await-long-running` seam is the one component permitted to background a
     build, which it does with `run_in_background: true`. Scope the closing instruction: state that it
     governs a build the caller runs itself — an `execution_tier: per_task` build — and that an
     `execution_tier: orchestrator` build is neither foregrounded nor backgrounded by the caller but
     handed to the `await-long-running` seam. Cross-link
     `../../ref-workflow-architecture/standards/agents.md` § "Leaf cannot reap a backgrounded build"
     as the owning contract. **No sentence in the section may forbid the backgrounding
     `await-long-running` mandates.**
   - **(b) Reconcile the two framings of harness auto-backgrounding** (110/G3). The same section
     presents auto-backgrounding as the thing that "preserved the job every time";
     `marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/SKILL.md` presents the same
     event as a loss ("the dispatch will lose the synchronous-return path"). Both are true of
     different halves and both prescribe the same action. Add one clause naming the halves apart —
     auto-backgrounding preserves the *job* and forfeits the *caller's synchronous return*, which is
     why an explicit 600000 ms bound is set to make auto-backgrounding the rare case rather than the
     plan — and cross-link `persona-plan-marshall-agent` § "Bash: Timeout from architecture-resolved
     canonical command" for the caller-side consequence.
   - **(c) Enumerate every help spelling in the stamp predicate** (110/G6). The stamp-predicate bullet
     states the third conjunct as *"no `--help` anywhere in argv"*, but the predicate it names
     (`_mentions_help`, in
     `marketplace/bundles/plan-marshall/skills/tools-script-executor/templates/execute-script.py.template`)
     also fires on `--help=…`, on `-h`, and on `-h` inside a short-flag cluster such as `-vh`. **Read
     `_mentions_help` and re-derive the spellings it matches** — do not take the four from this plan.
     Replace the conjunct with the derived set, and extend the suppression examples so a `run -h`
     probe is named alongside `run --help`. Leave the Enforcement note's citation of `_mentions_help`
     as it stands.
   - **(d) Name `indeterminate` in the three-conditions section** (430/G6). § "The three non-green
     conditions, and every gate that must keep them apart" is framed as *"the list a change to the
     vocabulary must walk"*, names `error` / `timeout` / `killed`, and calls the unresolvable case
     `unknown` — which is the ledger and dispatch-boundary spelling. The wrapper-side spelling for the
     same condition is `indeterminate`, and the two are deliberately distinct: the dispatch boundary
     refuses an `indeterminate` claim and derives `unknown` instead.
     `marketplace/bundles/plan-marshall/skills/extension-api/standards/build-execution.md` § Status
     values already documents all five. Add `indeterminate` to the condition table as the
     wrapper-surface name, state that the boundary's name for the same condition is `unknown` and that
     the boundary derives rather than accepts it, and cross-reference `build-execution.md`. Confirm
     that `build-execution.md` and `build-api-reference.md` agree on the vocabulary size before
     committing; if they do not, record the disagreement rather than silently picking one.
   - **(e) Give the mechanism a path from the surfaces that actually run builds** (110/G2). Nothing in
     `persona-plan-marshall-agent` or in
     `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/await-long-running.md`
     references `build-systems-common.md` at all — verify that absence yourself before adding, since
     an asserted absence is the higher-risk half. Both surfaces already carry the *prohibition*
     ("known-lossy primitive", "Do NOT poll for completion"); what neither reaches is the *diagnosis*
     — that the captured output carries no liveness information in either direction and that the
     `kind=build` change-ledger row's `status` is the substitute oracle. Add **one pointer from each**
     — in `persona-plan-marshall-agent/SKILL.md` immediately after the 600000 ms floor sentence in
     § "Bash: Timeout from architecture-resolved canonical command", and in `await-long-running.md`
     immediately after the known-lossy sentence — to `build-systems-common.md` § "Background build
     execution — reading a long build's completion signal", each naming what the reader gets there.
     **Pointers, not copies:** the rule text stays in one place.

   *Done when:* `grep -rn "build-systems-common"` over
   `marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/` and
   `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/` returns a hit in each that
   reaches the background-execution section; the stamp-predicate bullet enumerates every spelling
   `_mentions_help` matches, as re-derived from that function; the conditions section enumerates five
   statuses and states the `indeterminate`/`unknown` two-layer naming; and the foreground instruction
   names the `execution_tier` it applies to and cross-links `agents.md`, with no sentence in the
   section forbidding the backgrounding `await-long-running.md` mandates.

6. **D6 — The deployment diagram standard and its skeleton**
   (closes 170/G1, 170/G2, 170/G3)

   - **(a) Reconcile the casing rule with its own examples** (170/G1).
     `marketplace/bundles/pm-documents/skills/ref-svg-diagrams/standards/diagram-type-deployment.md`
     § "Protocol and port edge labels" states the format as *"protocol in upper case"*; four lines
     below, its own example block reads `gRPC :9000` and `mTLS :8444`, a later sentence makes `mTLS`
     normative in its own right, and the paired skeleton ships `gRPC :9000` as a worked placeholder.
     An author following the rule literally writes `GRPC :9000`. Reword the casing sentence so it
     matches practice — conventional casing, upper case for the common wire protocols, vendor casing
     where one is established — keeping the single-space and no-space-before-port halves unchanged.
     **Do not change the examples or the skeleton: they are the ground truth here.**
   - **(b) Stop presenting the absent-affordance list as complete** (170/G2). The same file's
     § "Annotated template" says *"The affordances specified above but **absent** from the skeleton —
     the numbered-leg convention and its legend block, the closed-`rect` boundary form, and nesting
     past depth 3 — are authored from this document"*. The em-dash apposition reads as the complete
     set of absences and is not: at least six further affordances specified in the document have no
     placeholder in the skeleton. Make the sentence **non-enumerative** — state that the table below
     is the set the skeleton covers, and that *any* affordance specified in this document but not
     appearing in that table is authored from the document — then either keep the three named items
     introduced by "for example" or drop them. Either wording removes the completeness claim without
     needing a list anyone has to maintain. **Do not replace it with a longer list.**
   - **(c) Bring the skeleton's caption to the shared size** (170/G3).
     `marketplace/bundles/pm-documents/skills/ref-svg-diagrams/templates/deployment-diagram-skeleton.svg`
     defines `.caption { font-size: 12px; … }` while
     `ref-svg-diagrams/standards/visual-language.md` fixes captions at 11 px and
     `diagram-type-deployment.md` fixes no caption size of its own, so nothing authorises the
     override. Change it to `11px`.

     **This half is gated on a rasteriser, and the gate is not a judgement call.** The
     `pm-documents:ref-svg-diagrams` skill makes render-and-read-back MANDATORY and BLOCKING before
     any SVG is committed. So: probe for a rasteriser (`rsvg-convert`, then `inkscape`, then
     `python3 -c "import cairosvg"`). **If one is available**, make the edit, render the file against
     `#ffffff` and `#0d1117`, read both PNGs back with the Read tool, confirm the caption is legible
     on both (re-render the caption strip at higher scale if the 1200 px render cannot resolve it),
     and commit. **If none is available**, do **not** make the edit and do **not** commit an
     unrendered SVG: record 170/G3 in the run report as blocked, naming every command probed and its
     result. Parts (a) and (b) are text-only and proceed either way.

   *Done when:* no example in the protocol-label example block, and no edge label in the deployment
   skeleton, contradicts the casing sentence; § "Annotated template" contains no closed enumeration of
   what the skeleton lacks; and **either** `grep '\.caption' deployment-diagram-skeleton.svg` shows
   `11px` with both re-rendered PNGs read back and the caption confirmed legible on both backgrounds,
   **or** the run report records the rasteriser probe that failed and the edit as not made.

7. **D7 — Incident narration and a dated snapshot in normative documents**
   (closes 130/G1, 130/G4, 130/G6)

   - **(a) The `#1027` narration in three normative automatic-review documents** (130/G4). The
     sentence *"on #1027 PR-Agent posted its Guide — valid participation — while reporting 'no major
     issues' on a diff in which CodeRabbit found two Major defects"* appears verbatim in
     `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md`,
     `marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md`,
     and the module docstring of
     `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py`. These
     three are a contract document, a standards document, and production code — not bot data sheets —
     and in each the sentence *after* the reference already states the mechanism, so the incident
     reference asks the reader to reason from a PR they cannot open and adds nothing they can act on.
     Replace it in each of the three with a mechanism-only statement of the same fact — e.g. *"a bot
     can post its Guide (valid participation) while reporting no major issues on a diff another
     reviewer found Major defects in"* — and keep every surrounding normative clause **byte-identical**:
     `SKILL.md`'s *"A satisfied quorum MUST NOT be rendered as a reviewed diff"*,
     `bot-participation-contract.md`'s § "Participation is not review quality" heading and its three
     normative obligations, and `review_completeness.py`'s `proves: participation_only` return
     contract. `automatic-review/standards/pr-agent.md` carries the same sentence in a bot data sheet;
     **leave it and record it in the run report as a data-sheet KEEP**, so the disposition is explicit
     rather than an omission.
   - **(b) The `PR #1013` narration one line from a corrected passage** (130/G1).
     `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/SKILL.md` (near
     `:388`) reads *"pins the **PR #1013** pre-fix scanning and post-fix anchored forms end-to-end"*,
     while the very next paragraph in the same section was already edited from "the two **PR #1067**
     defects" to "the two defects" — same document, same construction, opposite treatment. Rewrite the
     line the same way: *"pins the pre-fix scanning and post-fix anchored forms"*. The cross-references
     elsewhere in the file point at `standards/unreachable-guard-detection.md`, which carries the
     worked example, so no meaning is lost. **Leave those cross-references alone** — they are
     referential pointers into a named document, not free narration.
   - **(c) The dated snapshot in a normative standard** (130/G6).
     `marketplace/bundles/plan-marshall/skills/tools-permission-doctor/standards/permission-architecture.md`
     § "Universal Access Pattern" opens with a bare date line (`As of 2025-10-27:`) heading four
     bullets that are already written in the present tense. The repository's documentation standards
     forbid dates in document content. Delete the date line and change nothing else — the four bullets
     stand as the current statement. Then re-derive the family across the bundle tree
     (`git grep -nEi '\b(as of|since|before|after|prior to|until)\s+20[0-9]{2}' -- marketplace/bundles`)
     and report every remaining hit with its reason for surviving; Javadoc/JSDoc `@since` in code
     examples is out of family and stays.

   *Done when:* `git grep -n '#1027' -- marketplace/bundles/plan-marshall/skills/automatic-review/`
   returns at most the single data-sheet hit in `standards/pr-agent.md`, with each of the three
   normative sites still carrying byte-identical the obligations that followed the removed clause;
   the `PR #1013` narration is gone from the `ext-self-review-plan-marshall` regression-test
   paragraph while the two cross-references into `unreachable-guard-detection.md` are untouched; and
   the dated-narration sweep over `marketplace/bundles` returns no hit outside `@since`-style code
   examples, with § "Universal Access Pattern" still listing all four bullets.

   **Note for the build gate:** (a) edits a `.py` file. That is a Python change under the lane's build
   gate even though only a docstring moves, so the gate fires and `./pw verify` runs — see
   `cloud-plan-lane` for the gate's own condition and mechanics.

8. **D8 — Remaining stale statements, and one reusable security rule**
   (closes 280/G5, 390/G3, 170/G4, 170/G5)

   - **(a) The `role` field's Source cell** (280/G5).
     `marketplace/bundles/plan-marshall/skills/ref-workflow-architecture/standards/dispatch-logging.md`
     § "Field semantics" gives the `role` row's Source as *"The `--role` argument the caller passed to
     `effort resolve-target`"*. The implemented seam falls back `--role` → `--phase` → the resolver
     payload's `role` → the literal `default`, and both landed migrated callers rely on that fallback
     by passing only `--phase`. A caller reading the table concludes `--role` is required and may add
     a wrong one, changing the label the dispatch audit rosters on. Restate the Source cell as the
     fallback chain. **Re-derive the chain from the implementing function before writing it** — the
     `emission_role` composition in the effort command module — rather than copying this paragraph.
   - **(b) Codify the shell-interpolation rule where it can travel** (390/G3).
     `marketplace/bundles/plan-marshall/skills/persona-security-expert/standards/dependency-supply-chain.md`
     carries a CI/CD pipeline-hardening bullet list covering SHA-pinning, least privilege, OIDC,
     ephemeral runners, and separation of duties — and says nothing about template injection through a
     context expression inside a `run:` block. Verify that absence yourself across the
     `persona-security-expert` skill before adding, since an asserted absence is the higher-risk half.
     Then add **one bullet** in the list's existing style: never interpolate a GitHub Actions context
     expression into a `run:` block; pass the value through `env:` and reference it as a quoted shell
     variable, because context values such as `github.ref_name`, `github.event.issue.title`, and
     `github.event.pull_request.head.ref` are attacker-influenceable and can carry shell
     metacharacters. **Name both shapes explicitly** — the unsafe one (`${{ … }}` inside `run:`) and
     the safe one (`env:` plus a quoted `"${VAR}"`) — so a reviewer can pattern-match on it.
   - **(c) Two false clauses in a sibling plan's run report** (170/G4, 170/G5). These live in
     `doc/plans/truthful-signals/170-graduate-deployment-diagram-type-from-api-sheriff/report-01.md`
     § Residue. **First check the directory still exists.** It is a git-tracked run report today, but
     a collected plan directory is deleted from `doc/plans/` by the epic's collect step, so it may be
     gone by the time this plan runs. **If the directory is absent, record 170/G4 and 170/G5 as
     not-applicable (collected) in the run report and skip (c) entirely** — do not recreate the file
     and do not go looking for its content elsewhere.
     If it is present:
     - the mount-stem residue row says *"The skeleton centres both stems on their pills; the
       standard's worked example does not, and neither states a rule."* The worked example **does**
       centre at HEAD — a later fix in the same run moved the stem's `x` to the pill's centre — so the
       row's justification is false while its residue (no *rule* fixes the stem's `x`) is still real.
       Recompute the arithmetic from the worked example in `diagram-type-deployment.md` and edit the
       row to say both artifacts centre the stem and that no rule states the convention, so a
       follow-up simply writes down an already-consistent behaviour. **Do not delete the row** — the
       residue is open.
     - the footer-caption residue row, and the finding row that introduced its wording, both assert
       that `block-diagram-skeleton.svg` *"has no footer-caption element at all"*, the second recording
       it as *"verified by element count"*. The file carries three `<text class="col-sub">optional
       footer caption</text>` elements — re-count them rather than trusting that number. Edit both
       rows to say what is actually true and narrower: block defines no `.caption` class and no
       diagram-level footer slot, and carries per-column footer captions at 11 px via `.col-sub`. Drop
       or qualify the *"verified by element count"* claim, which is what made the false absolute look
       checked.

   *Done when:* the `role` row's Source cell in `dispatch-logging.md` matches the fallback chain as
   implemented, verified by reading the implementing function; the CI/CD list in
   `dependency-supply-chain.md` carries a bullet naming both the unsafe and the safe shape; and
   **either** neither cited row in 170's `report-01.md` asserts that `block-diagram-skeleton.svg` has
   no footer-caption element (with the re-counted element count no longer contradicting either row)
   and the mount-stem row's factual clause matches the worked example at HEAD, **or** the run report
   records the 170 directory as absent and both gaps as not-applicable.

## Out of scope

Each exclusion carries its reason, because with no operator watching, this written boundary is the
only thing holding the line against a tempting adjacent change.

- **Every other gap in the ten source `gaps.md` files.** Those documents carry gaps this plan does not
  name — among them 100/G3, G5, G6, G7, G8, G9, G10; 110/G1, G4, G5; 130/G2, G3, G5; 190/G4, G5, G6,
  G7; 200/G1–G7; 280/G1–G4, G6; 390/G1, G2, G4; 430/G1–G5, G7. They are assigned to other plans in
  this epic and several touch the same files this plan does. Fixing one here produces a conflicting
  diff against a concurrent run and, worse, closes it in a report that the plan actually assigned to
  it will not see. **Read a source `gaps.md` only for the entries this plan names.**
- **The `.caption` 12 px divergence in the other five diagram templates.** D6(c) fixes only the
  deployment skeleton, which is the instance this gap set owns. The others are templates no plan in
  this set touched, each needs its own render-and-read-back verification, and changing them here is
  exactly the unrelated diagram churn plan 170's own out-of-scope forbade.
- **Writing a rule for the mount stem's horizontal position.** D8(c) corrects a false *justification*
  in a residue row; the residue stays open. Writing the rule is new normative text in a diagram-type
  standard, which is a different kind of change from the corrections this plan makes, and it belongs
  to whichever plan takes 170's residue.
- **Adding, extending, or registering any plugin-doctor rule** — including extending the
  `no-incident-references` rule to the narration forms D7 removes by hand. D7 edits three documents;
  a rule change edits the machinery that judges every document, which is a code change with its own
  test obligations and its own reviewers, and the corresponding gaps are assigned elsewhere.
- **Naming a static-analysis tool in D4(c).** No null-analysis checker is reachable from this
  repository, so any named tool would be an assertion this run cannot support — which is the defect
  class this epic exists to close. D4(c) is authored to take the mechanism branch for exactly that
  reason.
- **`/sync-plugin-cache` and any plugin-cache refresh.** Several deliverables edit
  `marketplace/bundles/`. In this lane the sync is inert and is **not** owed: it is a machine-local
  build step reading a git-ignored tree, and the merged bundle source is authoritative. Do not run it
  and do not record it as debt.
- **Amending any governing contract** — `cloud-plan-lane`, the plan template, or the repository's
  documentation standards. Nothing in this plan requires one, and a run may not self-approve a change
  to the contract that governs it. If a deliverable appears to need one, **record the proposal in the
  run report and complete the rest**; do not make the change.

## Expected surface

Twenty-seven files across five bundles plus `doc/user/`. Grouped by deliverable so a concurrency check
against another plan can be made per group.

- `marketplace/bundles/plan-marshall/skills/manage-findings/SKILL.md` — D1(a), the type enum and the
  storage tree.
- `marketplace/bundles/plan-marshall/skills/manage-lessons/SKILL.md` — D1(b), the two § Operations
  `--category` enums.
- `marketplace/bundles/plan-marshall/skills/tools-integration-ci/SKILL.md` — D1(c), the false
  unregistered claim. *(Read-only:
  `marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts/constants.py` and
  `marketplace/bundles/plan-marshall/.claude-plugin/plugin.json` are D1's derivation sources and are
  not edited.)*
- `doc/user/parallelism-and-locking.adoc`, `doc/user/configuration.adoc`, `doc/user/recipes.adoc`,
  `doc/user/enforcement-hook.adoc`, `doc/user/efforts.adoc` — D2.
- `marketplace/bundles/pm-dev-java/skills/java-maintenance/standards/compliance-checklist.md`,
  `.../java-maintenance/standards/refactoring-triggers.md` — D3.
- `marketplace/bundles/pm-dev-java/skills/java-core/standards/java-17-features.md`,
  `.../java-null-safety/SKILL.md`, `.../java-null-safety/standards/null-safety-patterns.md`,
  `.../java-null-safety/standards/null-safety-core.md` — D4.
- `marketplace/bundles/plan-marshall/skills/extension-api/standards/build-systems-common.md`,
  `.../persona-plan-marshall-agent/SKILL.md`,
  `.../plan-marshall/workflow/await-long-running.md` — D5. *(Read-only:
  `.../ref-workflow-architecture/standards/agents.md`,
  `.../extension-api/standards/build-execution.md`,
  `.../tools-script-executor/templates/execute-script.py.template`.)*
- `marketplace/bundles/pm-documents/skills/ref-svg-diagrams/standards/diagram-type-deployment.md`,
  `.../ref-svg-diagrams/templates/deployment-diagram-skeleton.svg` — D6. *(Read-only:
  `.../ref-svg-diagrams/standards/visual-language.md`.)*
- `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md`,
  `.../automatic-review/standards/bot-participation-contract.md`,
  `.../automatic-review/scripts/review_completeness.py`,
  `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/SKILL.md`,
  `marketplace/bundles/plan-marshall/skills/tools-permission-doctor/standards/permission-architecture.md`
  — D7. **The `.py` file is the plan's only source-code change and is what arms the build gate.**
- `marketplace/bundles/plan-marshall/skills/ref-workflow-architecture/standards/dispatch-logging.md`,
  `marketplace/bundles/plan-marshall/skills/persona-security-expert/standards/dependency-supply-chain.md`,
  `doc/plans/truthful-signals/170-graduate-deployment-diagram-type-from-api-sheriff/report-01.md`
  (conditionally — see D8(c)) — D8.

Anything changed outside this list is collateral and is reported as such.

## Claim labels

Every artifact named below is git-tracked and reachable from a fresh clone. No claim here rests on
anything under `.plan/`.

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| **100/G1 (high) reproduces at HEAD** — `manage-findings/SKILL.md` § Finding Types enumerates twelve types and its storage tree lists twelve `{type}.jsonl` rows, while `FINDING_TYPES` defines fourteen | OBSERVED | `marketplace/bundles/plan-marshall/skills/manage-findings/SKILL.md` § "Finding Types" `Types:` line + the fenced storage tree, against `FINDING_TYPES` in `marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts/constants.py` — both opened during authoring |
| **190/G1 (high) reproduces at HEAD** — `parallelism-and-locking.adoc` documents `drop_review_on_scope_gate`, which exists nowhere under `marketplace/bundles/` | OBSERVED | `doc/user/parallelism-and-locking.adoc` (the table row) plus a tree-wide search for the identifier returning only that row |
| **270/G4 (high) reproduces at HEAD** — `compliance-checklist.md` § "Null Safety" checks one of the four positions the standard it names forbids `Optional` in | OBSERVED | `marketplace/bundles/pm-dev-java/skills/java-maintenance/standards/compliance-checklist.md` § "Null Safety" against the Quality-Rules line in `marketplace/bundles/pm-dev-java/skills/java-null-safety/SKILL.md` |
| **The other twenty-seven gaps reproduce at HEAD** — each cited file and passage was opened during authoring and the quoted text found present | OBSERVED | the file and section named in each deliverable; the source entries are git-tracked at `doc/plans/truthful-signals/{100,110,130,170,190,200,270,280,390,430}-*/gaps.md` |
| **No gap in this set was already closed** — none of the thirty failed to reproduce | OBSERVED | same reads as above; recorded here so the run does not re-litigate the check |
| **Asserted absence: nothing in `persona-plan-marshall-agent/` or `plan-marshall/workflow/` references `build-systems-common.md`** (the premise D5(e) builds on) | OBSERVED, re-verify before acting | a recursive search for `build-systems-common` over both directories returned nothing during authoring. **D5(e) re-runs it**; if a reference now exists, extend it rather than adding a second |
| **Asserted absence: the `persona-security-expert` skill carries no GitHub-Actions template-injection guidance** (the premise D8(b) builds on) | OBSERVED, re-verify before acting | recorded in `doc/plans/truthful-signals/390-ci-and-supply-chain-hardening/gaps.md` § G3, which names both sweeps it ran. **D8(b) re-runs the sweep before adding the bullet** |
| **The 170 plan directory is still present at run time**, so D8(c) has a file to edit | HYPOTHESIS | a listing of `doc/plans/truthful-signals/`. It is git-tracked today, but the epic's collect step deletes a collected plan directory. **D8(c) checks first and records not-applicable if it is gone** |
| **A rasteriser is available in the runtime**, so D6(c)'s mandatory render-and-read-back can be performed | HYPOTHESIS | the probe D6(c) runs (`rsvg-convert`, `inkscape`, `cairosvg`). If all three fail, D6(c) is recorded blocked and the SVG is left unedited |
| **The expected surface is the twenty-seven files listed above** | HYPOTHESIS | `git diff --name-only` against the merge base at the end of the run, compared row for row with § Expected surface |
| **Four gaps carry a severity in this plan different from the assignment list that produced it** — 100/G2 (`high` → `medium`), 110/G2 (`medium` → `low`), 130/G1 (`medium` → `low`), 270/G1 (`medium` → `low`) | OBSERVED | the § "Refuted during adversarial review" and severity lines in each source `gaps.md`. The adversarial-review record governs; none of the four is dropped, only re-ordered within its deliverable |

## Verification

Beyond each deliverable's *Done when:*, the pre-PR verification sub-agent (`cloud-plan-lane` § Step 6)
runs the checks below. **Every deliverable in this plan is text whose value is what a later reader
does with it**, so the interpretation check is the primary verification, not a supplement to it.

### Cold reads — an independent reader takes the text with no context and reports which reading it took

Dispatch a sub-agent that has **not** read this plan and has **not** seen the diff. Give it only the
named file (or the named section), ask the question, and have it answer from that text alone. Record
the answer it gave, verbatim, in the run report next to the required answer. **A wrong or hedged
answer means the wording failed, however complete the change looks** — fix the wording and re-read.

| # | Give it | Ask | Required answer |
|---|---|---|---|
| 1 | `manage-findings/SKILL.md` | "List every finding type this skill supports." | The complete `FINDING_TYPES` set, including `arch-constraint` and `pr-comment-overflow` |
| 2 | `doc/user/configuration.adoc` § automated review | "A required review bot refused with a rate limit. Which knob makes the step wait for the window instead of settling, and what is its default?" | `review_rate_window_await`, default `false` |
| 3 | `compliance-checklist.md` § "Null Safety" | "A record declares a component of type `Optional<String>`. Does it pass this section?" | **No** |
| 4 | `null-safety-patterns.md` § "Static Analysis and Null-Coalescing Helpers" | "Which static-analysis tool does this section apply to?" | Any checker that infers the result's nullness from the arguments — **not** a named product, and specifically not SonarQube |
| 5 | `build-systems-common.md` § "Run a long build in the foreground…" | "May the `await-long-running` seam background a build?" and "Does this instruction govern an `execution_tier: orchestrator` build?" | **Yes**, and **no** |
| 6 | `build-systems-common.md` stamp-predicate bullet | "Does `run -h` write a `kind=build` ledger row?" | **No** |
| 7 | `diagram-type-deployment.md` § "Protocol and port edge labels" | "Write the edge label for gRPC on port 9000." | `gRPC :9000` |
| 8 | `diagram-type-deployment.md` § "Annotated template" | "Is the list of affordances the skeleton lacks complete?" | **No** — the table is the positive set; anything specified in the document and not in the table is authored by hand |
| 9 | `dependency-supply-chain.md` CI/CD list | "Is `run: echo ${{ github.ref_name }}` safe? If not, write the safe form." | **Not safe**, plus the `env:` + quoted `"${VAR}"` form |
| 10 | `dispatch-logging.md` § "Field semantics", `role` row | "I am calling `effort resolve-target` with only `--phase`. What will the `role=` label be?" | The phase value — the fallback is named, not "`--role` is required" |
| 11 | `refactoring-triggers.md` § "When to Adopt Modern Java Features" | "I have three string constants compared with `.equals` in an if/else chain ending in a throw, and no `switch`. Does any trigger here fire?" | **Yes**, the if/else-over-constants trigger |
| 12 | `automatic-review/SKILL.md`, the quorum-verdict passage D7(a) edits | "`participation_complete: true` came back. May I describe this diff as reviewed?" | **No** — participation is not review quality; the ceiling must still read as a ceiling with the incident sentence gone |

### Reading checks (no execution)

- **Obligations preserved.** Diff each of D7(a)'s three sites and confirm the normative clause after
  the removed reference is byte-identical to its pre-change form. A removal that also softened an
  obligation is a regression, not a fix.
- **Pointer targets exist.** For every cross-reference added by D3(b), D3(c), D4(a), D4(b), D5(a),
  D5(b), D5(d) and D5(e), open the target file and confirm the named heading is present. A pointer to
  a heading that does not exist is the defect 270/G5 is about, reintroduced.
- **No duplication.** D4(a), D5(e) and D1(a) each add a pointer where the rule already lives
  elsewhere. Confirm each adds a reference and not a copy — the repository's documentation standards
  forbid the copy, and a copy is the next stale mirror.
- **No new dates, versions, or incident numbers** anywhere in the diff. D7 removes three; adding one
  back in a neighbouring edit would be self-defeating.

### Executed checks

- **Every *Done when:* grep and sweep in D1–D8, run and its output recorded** — not asserted. Where a
  sweep is expected to return survivors (D1(c), D7(c)), list each survivor and its reason; a bare
  "clean" is not evidence.
- **The build gate.** D7(a) touches `review_completeness.py`, so the lane's Python-change gate fires
  and `./pw verify` runs — see `cloud-plan-lane` for the gate condition and how the run reports its
  result. The change is a docstring, so a failure is a signal about the tree, not about this diff:
  report it rather than working around it.
- **The SVG render**, if and only if D6(c)'s rasteriser probe succeeded: both PNGs rendered, both read
  back, the caption confirmed legible on both backgrounds. If the probe failed, the report says so and
  the SVG is unchanged.

### What the run report must carry

Beyond the lane's own report contract: the two derived member lists from D1's gating derivation; the
knob set derived in D2(b) and the reason `bot_lists_provenance` is not an orphan; every sweep survivor
from D1(c) and D7(c); every cold-read answer verbatim; the disposition of 170/G3 and of
170/G4+G5 (done, or blocked/not-applicable with the reason); and, per gap id, closed / not-closed. A
run that ends partial says which of the thirty ids it closed — an understated outcome is picked up
again, an overstated one is collected as done.

## Notes

- **The gap set coheres.** All thirty are one mechanism — a document that diverged from a subject
  still readable in the tree — so no gap is excluded for incoherence and this plan needs no split.
  The eight deliverables group by the file or subject a fix lands in, which is also the grouping a
  reviewer can hold in their head.
- **Nothing here needs a decision.** Two gaps arrived with a fork in their fix (270/G2: name an
  analyser *or* derive from the signature; 270/G6: add a snippet *or* retitle the section). Both are
  resolved in the deliverable text — D4(c) takes the signature branch because no checker is reachable
  from this repository, and D4(d) adds the snippet — precisely so no mid-run judgement is required.
  If a deliverable nonetheless turns out to need one, the instruction is to **record the proposal and
  move on**, never to decide.
- **No gap in this set carries Kind `vacuous-test` or `vacuous-guard`**, so no deliverable requires a
  red-first test check. This was checked against every source entry: the Kinds present are
  `stale-statement`, `incomplete-sweep`, `incomplete-statement`, `omission`, `doc-drift`,
  `doc-conflict`, and `false-absence`. 270/G4 is described in its source as *"a guard that passes
  against the defect it names"*, but the guard is an agent-read Markdown checklist, not an automated
  test — there is nothing to drive red, and D3(a)'s *Done when* is the checklist item's presence.
- **Four severities differ from the assignment list.** The source `gaps.md` documents re-severitied
  100/G2 down to `medium`, 110/G2 down to `low`, 130/G1 down to `low`, and 270/G1 down to `low` during
  adversarial review, and raised 270/G4 up to `high`. The adversarial-review record governs. No gap
  was dropped as a result — the re-severities only affected which deliverable a gap sits in and how
  early it lands.
- **Two of the thirty are corrections to a sibling plan's run report** (170/G4, 170/G5). The
  repository's documentation standards exempt a lane run report from the no-timestamps rule as a
  dated record of one execution; that exemption does **not** cover a false statement of fact, which is
  what both rows carry. D8(c) corrects the facts and leaves the dated form alone.
- **The build gate fires once**, on D7(a)'s docstring edit. Every other change in this plan is
  Markdown, AsciiDoc, or SVG.
- **`.plan/` does not exist in the clone this plan runs in.** It is git-ignored, so no orchestrator
  ledger, plan spec, or landing record is reachable — **do not go looking for one**, and do not try to
  route any command through `.plan/execute-script.py`. Nothing in this plan requires either. Where the
  repository's `CLAUDE.md` hard rules mandate the generated executor, the architecture client, or the
  CI abstraction layer, the standalone-plan-lane carve-out in that same file supersedes them for this
  run; `cloud-plan-lane` is the authority on what replaces each.
- **The thirty source entries stay where they are.** `doc/plans/truthful-signals/*/gaps.md` are the
  record other plans in this epic are also working from; this plan reads them and edits none.
