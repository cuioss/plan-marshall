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

# Shipped prose describes the code that shipped

**Epic:** code-intelligence-substrate
**Branch prefix:** chore — maintenance / documentation correction, with one bounded code fix

## Problem

An audit of this epic's landed plans found 156 statements in **shipped prose** that are false, stale,
or overstated. Shipped prose here means the surfaces a reader treats as authority: `SKILL.md` files
an agent loads as contract, `standards/*.md` documents an implementor builds from, `doc/concepts/`
and `doc/user/` pages, module and function docstrings, argparse `help` and `description` strings
that reach an operator through `--help`, and the epic's own plan-directory records. None of these is
covered by a test, so every one of them drifted silently and stayed wrong.

The defects are not one thing. They fall into **three kinds that need different fixes and different
evidence**, and the plan is organised so a fixer always knows which kind is in front of them:

- **(a) True, then stale.** The statement described the code when it was written; the code moved and
  the statement did not. Example: `plan-retrospective/SKILL.md` says *"dispatch the 14 aspect
  references"* while the aspect table beside it has fifteen rows. The fix is to re-derive the fact
  and restate it — or better, to name the source instead of copying a number out of it, so it cannot
  drift again. The evidence is the current source, read at the moment of the fix.
- **(b) Never true — an invented rationale.** The statement was wrong the day it was committed, and
  it usually reads *more* confident than the true statement would. Example: a run report explains why
  a bot reviewed a `skip-bot-review` PR by asserting the registry gates only inline comments — the
  registry records the exact opposite on both halves, so the observation is real and *only the
  explanation is invented* (`020-corpus-residency-admission-control/gaps.md#G10`). This is the worst
  kind, because no sweep finds it: it is internally coherent and contradicts nothing nearby. It is
  caught only by opening the artefact the sentence claims to describe. The fix is to replace the
  rationale with the mechanism actually observed, and the evidence is that observation, cited.
- **(c) Normative, and the inverse of what a landed plan established.** The statement tells a reader
  to do the opposite of a shipped contract. Example:
  `marshall-steward/references/architecture-setup.md` states, in **MUST** form, that per-module
  directories absent from `_project.json["modules"]` *"MUST be ignored — the index is authoritative,
  not the filesystem"*. Plan `150`'s D3 carries its only ⛔ **MUST NOT** on exactly that point, the
  shipped code says the opposite in three places, and a non-vacuous negative-control test pins the
  crawl behaviour. The fix is to retract the instruction at every site, and the evidence is the guard
  that already forbids it.

Four anchor defects show why a per-file fix is not enough and a **mechanism-wide sweep** is:

1. **A normative steward reference instructs the inverse of a landed MUST NOT.** The
   index-is-authoritative claim survives on roughly six `plan-marshall` surfaces and two
   `pm-plugin-development` ones, and one of them attributes the retired contract to `_architecture_core`
   **by name** — so a reader who follows the cross-reference is told the wrong contract about the very
   module that was rewritten to end it.
2. **A commit corrected a false claim at two lines and left a third statement of it nine hundred lines
   above, in the same file.** `manage-config/SKILL.md` explains an `unknown` build verdict by
   "the worktree is not yet materialised" in one section and, after the fix, by "`pending` … or
   `disabled` (it never will)" in another. A reader gets opposite explanations of the same verdict
   depending on where they land.
3. **A contract and its own declared source-of-truth docstring both state a derivation the reference
   suite forbids.** `platform-runtime/standards/contract.md` and
   `Runtime.metrics_normalized_tokens.__doc__` say the recorded `cache_read` is divided in proportion
   to residency weights. Substituting that divisor into `_attribute_cache_read` turns two shipped
   tests red. A target implemented from the normative contract fails the reference suite — and
   `manage-metrics.py` names that docstring as SOURCE OF TRUTH.
4. **Two documents justify a check's cost by per-module build-tool subprocess discovery when the
   crawl issues one child process.** `manage-tasks/SKILL.md` states the freshness crawl shells out to
   "each build tool's own discovery verbs"; instrumented, `resolve_project_build_notations` issues
   exactly one — `git rev-parse --git-common-dir`, from a main-checkout-root resolution for LSP
   configuration, not a build verb and not a worktree-sha computation. An overstated cost is the
   argument a future author reaches for when proposing to weaken the check.

Nothing here is a redesign. Every entry is a sentence, a table row, a docstring paragraph, a help
string, or a heading level — plus **one** code change (§ D1), which exists because the guarantee it
repairs cannot be made true any other way.

## Goal

Every prose surface this plan touches states what the shipped code does. A reader who implements from
a normative contract produces something the reference suite accepts; a reader who follows a steward
reference does not violate a landed MUST NOT; a reader who budgets against a documented cost is not
misled by an order of magnitude; and where a figure could not be re-derived honestly, the figure is
gone and the reader is pointed at the command that produces it. The corrections carry their own
evidence, so a later reader can check them without re-running the audit.

## Deliverables

Six deliverables, grouped by **owning bundle and shared mechanism** rather than by severity: a
deliverable that fixes one wrong mechanism at all its sites is worth more than one per gap. Every
gap in scope is named in § Gap coverage, by source plan and gap id.

⛔ **Three rules bind every deliverable. They are stated once here and are not repeated per entry.**

- **The documentation-only half is always the half this plan takes.** Roughly a dozen gaps are
  written as *"fix the behaviour, or amend the text"*. The behaviour half is owned by a sibling
  `5xx` plan (see § Notes → Sequencing). **This plan always amends the text to describe the shipped
  behaviour**, never changes behaviour to match the text. The single exception is D1's slug fix,
  which is named explicitly and is in this bucket by the audit's own assignment.
- **Every count in this plan is a lead, never a fact.** "Six surfaces", "thirteen sites", "four
  sites", "eight sites", "seventeen verb sections", "fifteen aspect rows" — all were derived when
  the audit ran and the tree has moved since. **Re-derive each population at the moment you act on
  it**, with `Grep`/`Glob`/`Read`, and record the re-derived number in the run report beside the
  number this plan states. A mismatch is a finding, not a reason to stop.
- **Prefer naming the source to copying a number out of it.** Where a corrected sentence would carry
  a count, a duration, or a percentage, replace it with the source that produces it (the table, the
  command, the field) unless the number is itself the point. This is what stops the same gap being
  refiled after the next change.

### D1 — Guarantees the shipped code refutes

The surfaces that publish a **promise** — a divisor, an exit code, a one-directional bias, a
completeness claim, a cost — that the code does not keep. All three high-severity gaps are here.
Kind: mostly (b), never-true; the exit-code family is (c), normative-and-inverted.

1. **Cache-read attribution — the divisor** (`030/G1`, `030/G2`, both high).
   `marketplace/bundles/plan-marshall/skills/platform-runtime/standards/contract.md`
   § "Cache-read attribution — turn-weighted residency" states that *the recorded `cache_read` is
   divided in proportion to those weights*. It is not: `_attribute_cache_read` in
   `platform-runtime/scripts/claude_runtime.py` divides only
   `attributable = max(0, cache_read_total - max(0, subagent_cache_read))`, and the subagent-folded
   share reaches the residual through the remainder. The same sentence appears in
   `platform-runtime/scripts/runtime_base.py`, inside `Runtime.metrics_normalized_tokens.__doc__` —
   the docstring `manage-metrics.py` names as SOURCE OF TRUTH — where the trailing "*weight … is NOT
   redistributed*" clause is **not** a rescue, because the defect is about tokens, not weight.
   ⭐ **Do not invent the corrected wording.** `_attribute_cache_read`'s own docstring already states
   the right model in full ("*Only the parent-observed portion is split … subagent_cache_read is
   therefore subtracted before the split and reaches the residual via the remainder*"). Copy that.
   ⛔ **Do not copy the opening sentence of `manage-metrics/standards/data-format.md` § cache-read
   attribution** — it carries the same un-subtracted phrasing and is rescued only by the clause that
   follows it.
   ⛔ **Gating check, and it can halt this item.** Before editing, reproduce the audit's mutation:
   substitute `attributable = cache_read_total` into `_attribute_cache_read` and run
   `test/plan-marshall/platform-runtime/test_metrics_tokens.py -k attribute_cache_read`. The audit and
   its adversarial review both measured **2 failed, 6 passed**. If the mutation now leaves the module
   green, the premise has changed under this plan: **stop this item, restore the file, and report it**
   — do not edit the contract on a premise you could not reproduce. Restore the file from a snapshot
   either way and confirm `git status --porcelain` does not list it.
   *Done when:* neither `contract.md` § Cache-read attribution nor
   `Runtime.metrics_normalized_tokens.__doc__` permits a reader to derive "the recorded `cache_read`
   is divided in proportion to those weights"; both name the subtraction and the zero-weight branch;
   the two texts and `_attribute_cache_read`'s docstring make the same claim; and the mutation
   reproduction is recorded in the run report with its pass/fail counts.

2. **The dangling-reference guarantee — repair, then scope** (`120/G1` high, `120/G2`, `120/G11`).
   `pm-documents/skills/plan-marshall-plugin/SKILL.md` states *"The bias is one-directional — it can
   only make a reference resolve, never falsely fail one."* The shipped engine falsely fails live
   references, because `_heading_anchor_forms` in
   `pm-documents/skills/plan-marshall-plugin/scripts/doc_references.py` collapses hyphen/space runs
   (`re.sub(r'[\s-]+', '-', …)`) where GitHub does not — a heading with an em dash between spaces has
   a **doubled**-hyphen anchor, and the reference to it is reported dangling.
   **This is the one behaviour change in the plan**: add a second, GitHub-exact form in the same
   function — strip non-`[\w\s-]`, then `.replace(' ', '-')` — **keeping** the existing collapsed form
   beside it. Both are additive; the anchor set can only grow. Then scope the SKILL.md sentence to
   what is actually one-directional (the anchor-form over-approximation, not the slug computation),
   name the residual classes, and **mirror the same wording into `doc_references.py`'s engine
   docstring**, which carries the parallel claim. `120/G11` is the third counterexample in the same
   family: `_has_doc_suffix`'s docstring and its body disagree about a dotted bare id — make one match
   the other, changing the docstring unless the body is plainly wrong.
   *Counts are leads:* the audit measured the corpus sweep going from 18 unresolved (10 anchors, 8
   files) to 8 unresolved with zero anchor survivors, and the adversarial review reproduced it by
   substitution. Re-derive both figures; report them.
   *Done when:* a resolution sweep over `doc/**` reports **no unresolved anchor reference** and every
   survivor is a genuine broken file path; `test_doc_references.py` carries a case pinning a heading
   whose title contains an em dash between spaces and asserting the doubled-hyphen slug is among the
   extracted anchors — a case that **fails against the pre-fix function** (run it before the fix and
   record that it failed); and the SKILL.md sentence and the engine docstring say the same true thing.

3. **The refusal does not exit non-zero** (`040/G3`, `040/G4`, `040/G5`, `040/G6`, `040/G7`).
   Four surfaces around `tools-script-executor/scripts/generate_executor.py` claim the fail-open
   refusal "fails loudly (non-zero exit)". Measured: it exits `0` and reports `status: error`, which
   is what `manage-contract.md`'s three-tier model requires. The sharpest instance attributes the
   wrong outcome to a **named contract that says the reverse**: a `cmd_generate` comment credits
   "non-zero exit via the safe_main contract", while `safe_main`'s docstring in
   `tools-file-ops/scripts/file_ops.py` states that `sys.exit(1)` distinguishes a crash (1) from *an
   operation failure (0)*. Correct all four — the `format_surface_stats_line` docstring (the
   deliverable's normative emission contract), the Guard 5 comment, the `cmd_generate` comment, and
   `tools-script-executor/SKILL.md` — to say: `status: error`, nothing written, exit code `0`, and
   **a consumer branches on `status`, never on the exit code**. `040/G7` is the same file family:
   `manage-config/standards/provisioning-fail-closed-audit.md` still justifies the generator with
   **four** deterministic guards and does not list the fifth; the mirroring comment in
   `test/plan-marshall/tools-script-executor/test_generate_executor.py` is correct once **scoped** to
   the four *shape* guards, so scope it rather than renumbering it.
   *Done when:* a whole-tree search for `non-zero exit` in the `tools-script-executor` skill returns
   only statements a live run confirms; `SKILL.md`'s two statements about the refusal agree with each
   other; the fail-closed audit row enumerates five guards and names the fifth as a semantic guard on
   the derivation outcome; and the test comment's "four" is scoped to shape guards.

4. **Three further false guarantees, each retracted or scoped** (`230/G3`, `230/G4`, `260/G2`,
   `160/G8`).
   - `pm-plugin-development/skills/tools-marketplace-inventory/SKILL.md`: *"none of them can hide a
     real reference"* — an excluded shape that names nothing is dropped unreported, which is the
     definition of a broken reference. State **both** directions and add
     broken-reference-in-excluded-shape to the § "Precision of `validate`" limits list.
   - Same file: the unchecked verb registration is credited to the `manage-invocation-invalid`
     plugin-doctor rule, whose extraction regex is anchored on the `python3 .plan/execute-script.py …`
     prefix — a population that contains none of the prose citations and decision-log prefixes the
     claim covers. Replace the attribution with the rule's real scope and name the live example the
     audit found (a `…:classify` citation that resolves onto an entry script although `classify` is
     not a registered verb).
   - `plan-retrospective/references/chat-history-analysis.md`: the residue-classifier is guaranteed to
     fail toward `synthetic` *"for any injection that carries an envelope"*. An envelope-bearing
     injection fails toward `operator`. The behaviour fix is a sibling plan's, so **take the deferred
     branch the gap names**: scope the sentence to envelopes whose body carries no unbalanced token of
     the envelope's own tag name, and add **both** variants (quoted unmatched open, quoted close) to
     the residual-gap section with their error direction and the note that only the second fires
     inside a nested envelope.
   - `marshall-steward/references/skill-domains-setup.md`: enrich-all is said to populate
     `skills_by_profile` *"so that downstream `phase-4-plan` tasks always receive a non-empty skill
     list"*. `enrich_add_domain` skips profiles with no resolved skills. Reword to what enrich-all
     actually guarantees, and name the two dispositions of a profile with none (left absent, or
     declared `"minimal": true`).
   *Done when:* each of the four sentences is either true of the shipped code or names its residual
   class explicitly, and each correction cites in the diff (as a comment, a cross-reference, or the
   sentence itself) the symbol that establishes it.

5. **The crawl-cost rationale** (`300/G2`, `300/G1`).
   `manage-tasks/SKILL.md` § step 7 states the freshness crawl *"shells out: `git` on every project,
   plus each build tool's own discovery verbs on a Maven/Gradle/npm one"*. Instrumented, the crawl
   issues **one** child process. Maven module discovery is explicitly subprocess-free; the
   `help:all-profiles dependency:tree` invocation lives in a function this path never calls; the
   Gradle and npm discovery scripts issue none. Replace the build-tool clause with what the crawl does
   — stdlib parsing of each build file, a filesystem walk, and a single `git rev-parse
   --git-common-dir`.
   ⛔ **Do not describe that `git` call as a worktree-sha computation.** Its captured stack is a
   main-checkout-root resolution for LSP configuration. Writing it the other way would ship a fresh
   invented rationale of exactly kind (b), inside the fix for one.
   `300/G1` is the smaller half and was **re-rated low, with its original claim withdrawn**: the
   adversarial review reproduced nine fresh measurements *inside* the shipped 1–5 s range and showed
   the audit's higher readings were CPU contention in a shared tree, not a host property. ⛔ **Do not
   widen or replace the numeric range.** Add only a qualifier naming the measurement condition (an
   unloaded host) and noting that a contended one can multiply it severalfold.
   *Done when:* the cost paragraph names only subprocesses an instrumented run issues, describes the
   `git` call by the purpose its call stack shows, states the measurement condition beside the range,
   and records — in the paragraph or an adjacent comment — how the subprocess count was established.

### D2 — Retired semantics still stated as normative

Kind (c) throughout: text that instructs a reader to do what a landed plan forbids, or to believe a
model the code retired. This is the deliverable whose value is entirely **what a later reader does**,
so it carries a cold-read check in § Verification.

1. **"The index is authoritative, not the filesystem"** (`150/G18`, `150/G19`, `150/G20`).
   The retired semantic survives across the `plan-marshall` bundle — steward references
   (`architecture-setup.md`, `menu-maintenance.md`, `menu-configuration.md`, `wizard-flow.md`), a
   `determine_mode.py` docstring, and `extension-api/standards/module-discovery.md` — and again in
   `pm-plugin-development` (`plan-marshall-plugin/SKILL.md`, `plugin_discover.py`'s module docstring).
   The strongest instance is normative: *"Per-module directories present on disk but absent from
   `_project.json["modules"]` **MUST be ignored** — the index is authoritative, not the filesystem"*,
   under a heading that reads "Source of Truth".
   ⭐ **The correct formulation is already in the tree — reuse it, do not compose a new one.**
   `_architecture_core.py`'s `load_project_meta` docstring ("*NOT the source of module discovery:
   `iter_modules` crawls the live worktree … not the discovery gatekeeper*"),
   `tools-file-ops/scripts/constants.py` ("*The index is NOT the discovery gatekeeper*"), and
   `manage-architecture/standards/architecture-persistence.md` ("*The index is a denormalized
   pre-flight snapshot; the per-module concept document is authoritative*").
   ⚠ **One row is wording-only.** `determine_mode.py`'s `check_structure` really is index-driven, and
   correctly so for an existence marker. Remove the "source of truth for which modules exist" framing;
   do not change what the function reads.
   `150/G20` needs a different edit from the rest: `manage-solution-outline.py`'s `_read_module_context`
   docstring **attributes** the retired contract to `_architecture_core` by name while its own body
   calls `iter_modules`. Separate the two behaviours the docstring conflates — a `not_found` *guard*
   keyed off `_project.json` existence ("has discovery ever run"), versus module *enumeration* by
   crawl — and drop the attribution.
   *Done when:* no file under `marketplace/bundles/` describes the `modules` index as the source of
   truth for which modules exist or as authoritative over the filesystem; the surviving statements
   match the `constants.py` formulation or cross-reference `architecture-persistence.md`; and
   `test_module_on_disk_absent_from_index_is_still_discovered` (in
   `test/.../test_concept_model.py`) still passes — it is the negative control that pins the crawl.

2. **Package identity is a path, not a dotted name** (`150/G11`, `150/G12`, `150/G13`).
   `manage-architecture/standards/manage-api.md` documents `--package` as "Full package name" and its
   worked example emits a dotted identifier — a form the command now **refuses** with
   `error: non_resolving_package_key`, so the API reference instructs a failing call and shows the
   refused form as a success. `phase-3-outline/standards/module-selection.md` teaches `key_packages` as
   dotted patterns, and the package-selection template repeats "Package name from key_packages".
   ⚠ **Not every dotted name in `manage-api.md` is a defect** — the derived `packages` block is the
   dotted→path bridge and legitimately keeps dotted names. Correct only the `--package` row, its
   worked-example output, and the `key_packages` teaching sites.
   *Done when:* the `--package` row states a repo-relative path (matching the argparse `help`), the
   worked example shows a path, `module-selection.md` contains no dotted-identifier example, and the
   template names the key's real form.

3. **A profile may declare itself minimal** (`160/G7`, `160/G15`).
   `manage-architecture/SKILL.md`'s Step 9 completeness check says every module must carry
   `skills_by_profile` with at least `implementation` and `module_testing`, and sends the operator
   back to Steps 5–8 otherwise — with no mention anywhere in the skill of the `minimal` marker that
   exists precisely for a genuinely-empty profile, documented only in
   `standards/architecture-persistence.md`. Amend the check to accept a declared-minimal profile as
   complete and show the `enrich skills-by-profile` invocation that sets it. `160/G15` is the reader
   half: the `minimal` field and its read-path condition are absent from `standards/client-api.md`,
   the document a consumer reads.
   *Done when:* `manage-architecture/SKILL.md` names the marker and the command that sets it, its
   completeness check no longer treats a declared-minimal profile as incomplete, and `client-api.md`
   documents the field and the condition under which a reader sees it.

4. **The unresolvable footprint has two causes, not one** (`280/G4`, `280/G5`, `280/G13`).
   Six sites — four in the `280/G13` family, two in `280/G4`/`280/G5` — still explain an unresolvable
   footprint, an `unknown` build verdict, or a `worktree_fallback` by pre-materialization
   **alone**: `manage-solution-outline`'s
   `_stamp_read_provenance` docstring and its `SKILL.md`, plus `manage-config/SKILL.md`,
   `manage-config/scripts/_cmd_build_map.py`, `manage-execution-manifest/standards/decision-rules.md`,
   and `phase-6-finalize/standards/finalize-step-security-audit.md`. That is false for a `disabled`
   plan, for which no worktree will **ever** exist — and the corrected sentence is already in the tree
   twice, in `extension_base.py` ("*not merely unhelpful for such a plan but false, since no worktree
   will ever be materialised for it*") and at the other end of `manage-config/SKILL.md` ("*whether
   because the plan's worktree is `pending` … or `disabled` (it never will)*").
   This is anchor defect 2: one of the seven sits in a file whose landing commit changed exactly two
   lines, nine hundred lines below it. Prefer a cross-reference from the consumers to the one
   canonical sentence over seven independent restatements.
   `280/G4`/`280/G5` are the `worktree_fallback` half: the docstring and the `SKILL.md` both say the
   fallback covers the ordinary phase-3 window, while the `WorktreeResolutionError` comment in
   `main()` — same file — says the opposite and a shipped test asserts `worktree_fallback is False` for
   `worktree_state: pending`. Name the genuine-failure causes instead — executor not locatable,
   `manage-status` failure, payload with no recognised state — and adjust the field table's
   `worktree_fallback` row to say resolution *failure*.
   *Done when:* no surface attributes an unresolvable footprint or a `worktree_fallback` to
   pre-materialization alone; every one names both causes or cross-references the canonical sentence;
   and the `manage-solution-outline` docstring and its `main()` comment make the same claim.

5. **Step numbering and the two bypasses** (`350/G13`, `350/G9`).
   Thirteen sites across `manage-execution-manifest`, `extension-api`, `phase-5-execute` and
   `phase-6-finalize` name **phase-4-plan Step 8b** as the execution-manifest composer. The canonical
   numbering is in `phase-4-plan/SKILL.md`: **Step 7b** composes the manifest; Step 8b is the LLM
   Q-Gate dispatch signal. ⚠ A naive search returns more hits than sites — `phase-1-init` has its own
   Step 8b, and one `phase-4-plan` line is already correct. Re-derive the list; edit only the sites
   that name *phase-4-plan's* Step 8b as the composer.
   `350/G9`: the same `phase-4-plan/SKILL.md` says `qgate_validation_required` is `false` *"only on
   the unrecoverable error path"*, while two further paths to `false` — the `q_gate_validation == off`
   opt-out and the surgical-scope bypass — are defined elsewhere in the same file and named on a line
   the landing diff edited. Rewrite to match that line.
   *Done when:* no site outside `phase-4-plan/SKILL.md` names Step 8b as the manifest composer; a
   search for "only on the unrecoverable error path" in `phase-4-plan/SKILL.md` returns nothing; and
   the surviving sentence names both bypasses.

6. **Four remaining normative inversions** (`110/G13`, `320/G10`, `310/G4`, `190/G2`, `190/G7`,
   `220/G8`).
   - `plan-marshall/SKILL.md` documents a `transition --completed 6-finalize` firing site that needs
     qualifying against where the transition actually fires.
   - `tools-file-ops/scripts/file_ops.py` (and its siblings) still carry a blanket *"`.plan/` is
     git-ignored"* premise that a landed plan narrowed; sweep the remaining instances to the narrowed
     statement.
   - `plan-retrospective/references/invariant-check-summary.md` instructs its reader to **open
     `{plan_dir}/handshakes.toon` directly** — the repository's standing rule is that all `.plan/`
     access goes through the `manage-*` script surface, and the same `SKILL.md` forbids the direct
     read six lines from where it mandates it. Route the read through `phase_handshake list`, which
     projects every `HANDSHAKE_FIELD` per row and therefore already returns `captured_at`, `main_sha`
     and `worktree_sha`.
   - `manage-execution-manifest/SKILL.md` does not state that reconcile's scope is built-in steps
     only; `phase-6-finalize/SKILL.md` Step 1.5 does not say what happens to a reconcile error that is
     not `unreconcilable_step`. State both.
   - `marshall-steward/references/menu-configuration.md` carries a Page-5 continuation obligation that
     is recorded nowhere the next Configuration author will read it. Record it there.
   *Done when:* each of the six statements is true of the shipped code and, where it is an
   instruction, is executable by a reader following the repository's standing rules.

### D3 — The `manage-architecture` query contract and the code-intelligence reader pages

The document family a consumer reads before calling a query verb, plus the concepts and user pages
that describe the same surface. Kind: mixed (a) and (b) — several verbs were never contracted at all.

1. **`client-api.md` structure and content** (`135/G1`, `135/G3`, `135/G4`, `135/G5`, `135/G6`,
   `135/G8`, `135/G9`).
   - The Command Summary's `capabilities` row claims `derivable`/`not_derivable` for all three
     capabilities; the handler emits `available`/`unavailable` for `content_search`, and the
     document's own `§ capabilities` says so correctly further down. Name both vocabularies in the
     row. ⛔ Do not change the handler — that is a sibling plan's gap.
   - The heading hierarchy is broken in **two** places, not one: several `### verb` sections render
     as subsections of `## Error Handling`, and four more render under a `## Resolver provenance
     (the graph family)` heading whose prose scopes itself to the four graph-family verbs — two of
     the four are not graph-family verbs at all. Re-close the hierarchy so every verb section sits
     under the heading that owns it.
   - `siblings` and `profiles` are live, registered, `SKILL.md`-invoked verbs with **no response
     contract anywhere**. Add a section for each — arguments table, worked TOON payload, zero-result
     and error semantics — read from the handlers, plus a Command Summary row and a Command Groups
     entry. `descriptor-regression-check` is the mirror case: contracted in `client-api.md`, absent
     from `SKILL.md` entirely; add a canonical-invocation block and a Command Groups row.
   - Two duplications in `§ search` — the `--ignore-case` / `--literal` composition rule and the
     `count` vs `file_count` explanation — each stated twice. Keep one statement of each.
   ⚠ `SKILL.md` is already long; the line-budget analyzer may object to the additions. Run
   plugin-doctor's quality gate (see § Verification) and, if it flags the file, extract rather than
   trim meaning.
   *Done when:* a heading-level parse of `client-api.md` places every verb section under a heading
   that names it; `client-api.md` contains `### siblings` and `### profiles` sections and Command
   Summary rows for both; `manage-architecture/SKILL.md` names `siblings`, `profiles` and
   `descriptor-regression-check`; the `capabilities` row names both status vocabularies; and each of
   the two duplicated rules appears once.

2. **The derivation-resolver mechanism** (`200/G4`, `200/G5`, `200/G7`, `220/G3`).
   `doc/concepts/code-intelligence.adoc` and
   `extension-api/standards/ext-point-derivation-resolver.md` both say the LSP lift to module
   granularity *"goes through the path-attribution seam"*. It does not — the shipped code uses a
   longest-prefix table over the discovered module directories. Name the real mechanism. ⚠ The second
   half of the standard's sentence (drop-and-note rather than guess) is accurate; keep it.
   `200/G7`: `module-discovery.md`'s **normative** "must carry" clause enumerates five `dep_type`
   kinds and omits `lsp`, while the same file's other enumeration was corrected and does list it — so
   an implementor following the normative clause treats a live `lsp` entry as contract-violating.
   `220/G3`: the anti-vacuity table's third-state row appears on roughly six document surfaces plus
   two `_cmd_client_handlers.py` docstrings, and none of them says that **declared edges survive a
   full resolver switch-off**. The two docstring parentheticals assert the absence outright
   (*"there were no edges to walk"*, *"nothing could have depended on the module"*) and are simply
   false: a probe with every resolver off returned a non-empty `edges[]` with `producers: ['declared']`.
   Add the third-state clarification at every site.
   *Done when:* no surface names the path-attribution seam as the LSP lift's mechanism; the normative
   `dep_type` clause lists `lsp`; and every anti-vacuity third-state row, and both handler docstrings,
   state that declared edges can still be present when `resolver_count: 0`.

3. **The reader-facing counts and claims** (`200/G11`, `210/G8`, `240/G13`, `135/G7`, `220/G4`).
   - `doc/concepts/extension-architecture.adoc`: *"every bundle declares its domain identity"* — one
     shipped bundle returns no domains and ships no skills by profile, and two standards already
     record that case correctly. Qualify the sentence to admit it.
   - `doc/user/dependency-intelligence.adoc`: *"Three further joins run over cross-references"* — the
     live roster is four. Correct the count **and** the enumeration, noting the added resolver runs
     only under its enabling condition.
   - `doc/concepts/code-intelligence.adoc`: the Tier 1 paragraph names `info` among the adjacency
     surfaces; `info`'s contract returns no edge, dependency or adjacency field. ⛔ Drop `info` and
     **only** `info` — `overview` and `module` genuinely do carry adjacency. The same page's
     diagnostics paragraph carries a superseded validator characterisation (`240/G13`); restate it
     against the current set or name no number.
   - `manage-run-config/standards/run-config-standard.md`: the block titled "Full Example" omits
     several sections the same document defines and that its own maintained Schema block carries, so
     the document's two JSON fences disagree. Rebuild the example from the Schema block's keys.
     ⚠ Two further keys appear in the skill's schema example but in neither fence of this standard —
     **do not decide** whether they belong here. Record a one-paragraph proposal in the run report
     naming the two keys, the two documents, and the question; make no change on their account.
   *Done when:* each sentence matches its cited source; the two JSON fences in
   `run-config-standard.md` carry the same top-level key set, or the example states its own scope in
   one sentence; and the run report carries the recorded proposal.

### D4 — The measurement and retrospective documentation

`manage-metrics`, `plan-retrospective`, `phase-6-finalize` and `doc/concepts/token-management.adoc`:
the documents that describe what the system measures. Kind: mostly (a), with two unsourced
quantitative claims that are kind (b).

1. **`doc/concepts/token-management.adoc`** (`090/G1`, `090/G2`, `090/G3`, `090/G8`, `090/G9`,
   `090/G10`, `090/G4`).
   - § 6 carries a parenthetical narrating *what the document used to say* ("*The older phrasing that
     a variant's context is 'never additive' …*"). Both `CLAUDE.md` § Documentation Standards and the
     `ref-documentation` organization standard forbid transitional content. Delete it; the preceding
     sentences already state the current position positively.
   - The `~10-15 K tokens of variant context` and `~5-10 dispatches` figures survive in one section
     after being **deleted from another section of the same document** as unverifiable. ⛔ **Delete
     them, keeping the qualitative claim.** Do not attempt to re-derive: the population needed is an
     instrumented corpus run, which this lane cannot perform, and a plan that authored "re-derive it"
     would author a stall.
   - § 6's *"its own cost … is bounded and small against the run-length read cost it removes"* is an
     unsourced quantitative comparison — and the repository's own published billing weights make it
     non-obvious, since a created byte is billed many times a read byte. ⛔ **Restate it as the
     condition rather than the fact** ("isolation pays whenever re-creating an envelope's starting
     context costs less than the residency it removes, which is the property a split must be checked
     against before it is made"). This form is shippable today and preserves the recommendation.
     `090/G9` completes it: connect the section's cost model to the mechanism and to the fields that
     measure it, by name.
   - `090/G10`: carry the currency correction into the `image::` alt text and the SVG `<title>`, which
     still use the superseded wording.
   - `090/G4` is an **omission, not a claim**: the diagram `doc/resources/diagrams/context-isolation.svg`
     was modified without the mandatory rasterise-and-read-back check that
     `pm-documents:ref-svg-diagrams` requires, and the edit replaced short monospace labels with much
     longer prose inside fixed-width boxes. Load that skill, rasterise against both the light and dark
     GitHub backgrounds, read both images back, and fix any clipping or contrast defect.
     ⛔ **If no rasteriser is reachable in the runtime** — none was during the audit — the run report
     MUST say so explicitly and record the gate as an open coverage gap. **A silent skip does not
     discharge this item.**
   *Done when:* the transitional parenthetical and the two unsourced figures are gone; the cost
   sentence is phrased as a condition and names the fields that would measure it; the alt text and
   SVG title match the corrected currency; and the run report either records both rasterisations
   (naming the two background colours) or records the coverage gap.

2. **`plan-retrospective`'s own aspect roster and rules** (`330/G7`, `330/G8`, `330/G10`, `330/G11`,
   `330/G12`, `330/G14`, `290/G12`, `320/G6`, `320/G8`, `320/G1`, `320/G7`).
   - `SKILL.md` says *"dispatch the 14 aspect references"* against a table with a different number of
     rows, and a dispatch-shape heading and body assert two further counts, one of which contradicts
     the list in its own parenthetical. ⭐ **Apply the prefer-naming-to-counting remedy**: replace the
     figures with the named source ("every aspect in the Step-3 aspect table, in the documented
     order"). Where a count is genuinely load-bearing — the `8×` envelope-cost argument beside one of
     them — re-derive it and state which population its denominator is over, rather than leaving it
     orphaned.
   - Remove the historical clause in § Step 4, the attempt narrative in `_fragment_renders_empty`'s
     docstring, and the sweep narrative in the `ZERO_ATTRIBUTION_FIELDS` comment block — all three
     are transitional content the documentation standards forbid — and document the intended consumer
     action for `sections_unattributed_zero`, which is currently emitted with no stated response.
   - `audit-archived-plan-retrospectives/SKILL.md`'s global-log-analysis row does not state the
     `unmeasured` case; state it.
   - `check-manifest-consistency.py`'s `--base-ref` help calls the argument "Required" when it is not
     CLI-enforced, and omitting both diff arguments now yields `indeterminate` for every diff-fed
     rule. Replace the help with the real contract, agreeing with the `SKILL.md` paragraph that
     already documents it. `320/G6`: the documented Aspect 12 capture invocation passes no diff at
     all, while Aspect 13's block beside it does — add the same `--diff-file` argument and state in
     `standards/manifest-crosscheck.md` that an invocation without either produces an all-indeterminate
     aspect. ⚠ Expect this to start producing real findings where the aspect previously produced
     none; that is the point, and the run report should say so. `320/G8`: the LLM interpretation rule
     names one cause of `indeterminate` and there are two — name both, and instruct the renderer to
     surface whichever the message states. `320/G7`: add the field the fragment emits on every success
     but that the documented fragment shape omits.
   *Done when:* no count in `plan-retrospective/SKILL.md` can be contradicted by the table or list
   beside it; no transitional narrative remains in the three named sites; the `--base-ref` help
   contains no "Required" claim and agrees with `SKILL.md`; the Aspect 12 command passes a footprint
   and a run of the documented command on a plan with a captured footprint yields at least one
   non-`indeterminate` diff-fed verdict; and the documented fragment shape lists every key the emitter
   can put in the `diff` block.

3. **`manage-metrics` data-format and help strings** (`060/G7`, `270/G6`, `270/G7`, `340/G1`,
   `340/G7`).
   - `standards/data-format.md` claims a bullet *"states the measure's coverage on every render"*; a
     phase with rows recorded but a zero boundary sum renders no such bullet, and the adjacent
     sentence covers only the file-absent case. Amend the sentence to state the exact condition under
     which the bullet renders. ⛔ Do not change the render guard — that is a sibling plan's gap.
   - Two documented log-analysis shapes disagree with what the code emits: a `ranked[*]{}` header and
     a `script_cost_rollup` key order. Align the documents with the emitted shapes.
   - `reconcile-ledgers`'s subparser `description` restates a claim a later verification round
     refuted, and the corrected wording is already used by the emitter and by `SKILL.md`. ⭐ Copy the
     emitter's wording. This string reaches the operator through `--help` and is captured into the
     generated executor's surface cache, so it is a first-class documentation surface.
   - State that the two `*_population` field families measure different axes, at the point the
     document defines them.
   *Done when:* each sentence is true for every combination of the fields it describes; the two
   documented shapes match the emitted ones field-for-field and in order; and the `reconcile-ledgers`
   description matches the emitter's `detail` string.

4. **The invariant-check rules and the dispatch labels** (`310/G2`, `310/G5`, `170/G12`, `170/G14`).
   - `plan-retrospective/references/invariant-check-summary.md`'s Step 2 rule turns on comparing a
     row's `captured_at` against *"when the main-anchored resolution fix landed in this repository"* —
     and the file names no date, no PR, no commit, and no way to obtain one, while the declared reader
     is an LLM holding only the summariser's output. Give it both halves of a determinable cutoff: the
     landing commit for this repository, named directly, **and** a one-line mechanical derivation for
     a consumer repository (the first commit whose invariants module defines the main-repo-root
     symbol, found with a `git log --diff-filter=A -S…` invocation). `310/G5`: the "Invariants in
     Scope" table is incomplete against the invariants the checker actually evaluates — complete it,
     or re-label it as the subset it is.
   - `170/G12`: one "LLM aspects" site in `phase-6-finalize/standards/dispatch-*.md` was missed when
     its siblings were relabelled; relabel it. `170/G14`: the three relabelled documents assert an
     "eight aspects" count — re-derive it or, preferably, drop it and name the roster.
   *Done when:* a reader holding only a git checkout and the aspect's inputs can reach a verdict on
   the Step 2 rule; the scope table's title matches its contents; and no relabelled document asserts a
   count the roster contradicts.

### D5 — Skill contracts for the phase, tooling and LSP surfaces

The `SKILL.md` and `standards/` documents that publish a payload shape, an outcome set, or an
invocation. Kind: predominantly (a), plus several omissions where a shipped field or outcome was
never published at all.

1. **`lsp-client` and its consumer wiring** (`010/G16`, `010/G8`, `010/G9`, `010/G7`, `010/G10`,
   `010/G12`).
   - A declined rename is a *third* outcome the documented wiring does not name: the verb returns
     `status: success` with `applied: false` and `reason: no_workspace_edit`, while
     `execute-task/SKILL.md` tells a leaf to route only on `failed` and `degraded`. A leaf following
     the wiring reads `success` as "the rename landed" and moves on without renaming anything.
     Publish the third outcome in **both** `lsp-client/SKILL.md` § "The write side" and the
     `execute-task/SKILL.md` wiring paragraph, stating that nothing was changed and what to do
     instead. ⛔ Documentation only — do not change the return shape.
   - `lsp-client/SKILL.md` claims *every* payload carries `boundary_note`; scope it to the payloads
     that do. The write-side contract does not state the re-diagnose's scope limits; state them.
   - `010/G7` is a **cost claim with an unstable magnitude**. Re-measurement showed the first
     `documentSymbol` in a cold session ranging across an order of magnitude between hosts, while two
     things reproduce every time: the **ordering effect** (a `documentSymbol` issued first in a cold
     session costs roughly a second; the same call after a workspace-symbol query and diagnostics
     costs milliseconds) and two **floor-bounded** costs (a settle floor in `wait_until_idle`, and the
     diagnostics wait). ⛔ **State the ordering effect and the floors, which are properties of the
     code; do not quote a per-call magnitude as a constant.** The shipped "cold start is paid once per
     call" sentence rests on warm-path figures and must be replaced, not adjusted.
   - `doc/user/lsp-code-intelligence.adoc`'s state table omits one of the states the verb can report;
     add it. `010/G12`: `lsp-client` is absent from the bundle manifest's `skills[]` array — register
     it, so the manifest and the skill tree agree.
   *Done when:* both wiring surfaces name the declined-rename outcome and its discriminator; the
   `boundary_note` claim is scoped to the payloads that carry it; the cost paragraph names the
   ordering effect and the floors and quotes no per-call constant; the user page's state table lists
   every state the verb reports; and the manifest's `skills[]` contains `lsp-client`.

2. **The corpus language server** (`240/G14`, `240/G15`, `240/G16`, `240/G24`, `240/G17`, `240/G11`,
   `240/G12`, `240/G27`).
   - A gate wording in `tools-corpus-language-server/SKILL.md` and the same justification restated in
     `corpus_lsp.py`'s module docstring and in `active_capabilities()` all rest on a superseded
     characterisation of the validator's unresolved set. Restate all three against what holds now.
   - `_lsp_location`'s docstring describes a range the function does not emit; make it describe what
     it emits.
   - `marketplace/targets/claude/plugin_json_gen.py`'s docstring field list omits a field the
     generator writes; add it.
   - `doc/user/corpus-language-server.adoc` and `doc/developer/corpus-language-server-protocol.adoc`
     both quote a validator measurement that has since moved by roughly an order of magnitude.
     ⭐ **Do not re-quote a fresh number.** Replace the figures with the command that produces them,
     so the reader measures it themselves; the audit's own note is that the run deliberately stated
     ranges to survive drift and the range no longer contains the value. Where the developer page
     records a decision, note that the precision work has since landed, so the constraint is a live
     question rather than a settled one.
   - `240/G27`: `CLAUDE.md` § Repository Overview states component counts that no longer reconcile.
     Re-derive them from the bundle tree and restate, or name the source that produces them.
   *Done when:* no gate justification cites the superseded characterisation; `_lsp_location`'s
   docstring matches its return; the generator docstring lists every field it writes; neither
   reader-facing page quotes a validator figure (each names the command instead); and `CLAUDE.md`'s
   counts match a fresh derivation recorded in the run report.

3. **Tooling invocation surfaces that cannot execute** (`230/G17`, `230/G18`, `230/G21`,
   `120/G4`, `120/G10`, `110/G3`).
   - Roughly thirteen documented `plugin-doctor` invocations across `plan-marshall` and
     `pm-plugin-development` name verbs the entry script does not register. ⚠ **The audit's own first
     enumeration named a verb that does not exist** — the real one is `validate-contracts`, not
     `contracts` — so **re-derive the registered subcommand set from
     `plugin-doctor/scripts/doctor-marketplace.py` before editing anything**, and correct each
     documented invocation to a verb in that set.
   - `tools-integration-ci/standards/github-impl.md` and `gitlab-impl.md` each document an executor
     notation naming a script the skill does not contain. Replace both with the real entry script's
     notation plus whatever argument selects the provider.
   - `230/G21`: dispose of the remaining in-namespace unresolved rows that no other gap covers —
     correct each to an executable notation, or state at the site why it is prose rather than an
     invocation.
   - `120/G4`: an unresolved-reference report currently lacks enough identity to be actionable; give
     each reported reference the identity a reader needs to find it. `120/G10`: the doc-corpus read
     that produces a handful of triples pays a full corpus read on every crawl — record the cost and
     the narrower read that would serve, **as a proposal in the run report**, and make no
     performance change here.
   - `110/G3`: `manage-status`'s `--reason` help advertises `normal_completion` among its examples,
     and the archive gate fires only when `--reason` is **absent** — so the tool's own help documents
     a token that silently disarms a shipped gate. ⛔ **Take the documentation half only**: drop the
     example from the help enumeration. Closing the reason vocabulary is a behaviour change and is
     out of scope (see § Out of scope).
   *Done when:* every documented `plugin-doctor` and `tools-integration-ci` invocation names a
   registered verb; the residue rows are each corrected or annotated; the unresolved-reference report
   carries per-reference identity; `--reason`'s help no longer names `normal_completion`; and the
   corpus-read proposal is recorded in the run report.

4. **Published payload shapes and consumer tables** (`250/G3`, `050/G3`, `050/G6`, `100/G4`,
   `310/G6`, `310/G7`, `350/G17`).
   - `phase-5-execute/SKILL.md`'s `classify` TOON block omits a field the emitter prints on every
     unresolved return and that the module docstring documents — so the token exists in the payload
     and no consumer is told to read it. Add it to the block and name it in the paragraph that tells
     a consumer to read the resolution flag first.
   - `manage-references/SKILL.md`'s consumer table names a skill as a consumer of a key it does not
     read. Remove the row's false half. `050/G6`: a `phase-6-finalize` standard argues from a fallback
     input that is no longer written; drop that half of the argument so the document does not assert a
     dead input.
   - `ext-self-review-plan-marshall/SKILL.md` justifies a check by *"a sibling-`SKILL.md` re-check"*
     while the detector scans every contract source — `SKILL.md` **plus** every `standards/*.md` — and
     the same file says so correctly elsewhere. Correct the rationale to "a contract-source re-check".
   - `script-shared/scripts/marketplace_paths.py` cites a symbol that has moved; correct the citation.
     `310/G7`: `tools-script-executor/standards/cwd-policy.md` claims **one** sanctioned main-anchored
     resolver while a second exists; reconcile the sentence with the resolvers that ship.
   - `350/G17`: a characterization-corpus rule was applied by a landed plan and written down nowhere
     — it exists only in a run record and one test comment, and a rule that lives in a run record binds
     nobody. Write it into the skill that already owns fixture discipline: **determine which of
     `pm-dev-python:pytest-testing` and `plan-marshall:ref-code-quality` currently carries fixture
     guidance and place it there**; if both do or neither does, place it in neither, record a
     one-paragraph placement proposal in the run report, and do not split the rule across two skills.
   *Done when:* the `classify` block's documented field set matches what the emitter can print, field
   for field; every skill named in the `manage-references` consumer table can be shown to reference
   the key the row claims; the self-review rationale names the real file set; the two `script-shared` /
   `cwd-policy` citations match the shipped symbols; and the characterization-corpus rule exists under
   `marketplace/bundles/` or the placement proposal is recorded.

### D6 — The epic's own plan-directory records

Forty-odd defects live in this epic's landed plan directories under
`doc/plans/code-intelligence-substrate/*/` — run reports, plan files, proposal documents. They are
records of past executions, not documentation of current state, and they are corrected under a
different rule from everything above.

⛔ **Gating derivation — run it first, and let it close this deliverable.** List
`doc/plans/code-intelligence-substrate/`. A landed cloud plan's directory is **deleted when the
orchestrator collects it** (`doc/plans/cloud-bridge.md` § Path 3), so some or all of these
directories may be gone from the clone. For every source plan in § Gap coverage → D6 whose directory
is absent, record its gap ids in the run report as **discharged-by-collection**, with the listing as
the evidence, and do not look for the files. If the epic directory is absent entirely, D6 is closed
as not-applicable on that evidence alone. **Do not reconstruct a deleted record from git history.**

⛔ **The correction rule, which admits no mid-run judgement.** A record states what a run observed.
Correct only what was **false when written**, and correct it to what was true then:

- **Arithmetic and internal contradiction** — a stated sum that its own addends refute, a table whose
  row count contradicts its stated count, a duplicated row inflating a total, a disposition of "fixed
  in both" where only one site was fixed, a section heading contradicting the body beneath it. These
  are settled from the record itself; fix them.
- **Mis-citation** — a line number that no longer names the cited text, a dangling relative link to a
  plan file that is now a directory, a mixed 0-/1-based line narrative, a mis-attributed quote, a
  stale symbol or roster name. Replace with the current locator, or with the identifier (the field
  name, the heading) instead of the line number, so it cannot decay again.
- **An invented rationale** — a stated *reason* the cited source refutes. `020/G10` is the exemplar:
  the observation was re-confirmed live and only the explanation was wrong. Replace the explanation
  with what the cited source says, keeping the observation.
- **A count that can only be re-derived against today's tree** — ⛔ **do not substitute a today-number
  into a past record.** Either strike the figure and name the source that produces it, or keep it and
  attach the basis it was measured on. Silently overwriting a past measurement with a present one
  makes the record less true, not more.
- **A plan-file clause the run did not meet** (`100/G8`, `300/G15`, `070/G11`, `020/G9`) — ⛔ **do not
  rewrite the requirement to match what shipped.** Record the divergence: what the clause required,
  what shipped, and why (for `100/G8`, that the shipped construction *publishes* a scope statement
  while the obligation to quote it is prose with no validator; for `070/G11`, that a binary in the
  plan met a three-state contract in the code). The record then tells a later reader the truth about
  both.

*Done when:* the gating listing is recorded in the run report with a per-source-plan present/absent
disposition; for every present directory, each gap id named in § Gap coverage → D6 is either
corrected or carries a one-line reason in the report; no correction introduces a figure measured
against a tree later than the one the record describes; and no plan-file requirement was rewritten to
match what shipped.

## Out of scope

Each exclusion states its reason, because the run has no operator to ask.

- **Every behaviour change except D1's slug fix.** Roughly a dozen gaps read *"fix the code, or amend
  the text"*. The code half is owned by sibling `5xx` plans drawn from the same audit; doing it here
  would collide with them in the same files and could land a behaviour change no test in this plan
  covers. D1's slug fix is the sole exception because the guarantee it repairs cannot be made true by
  any wording — the audit placed it in this bucket for that reason.
- **Closing the `--reason` vocabulary** (`110/G3`'s optional half). Rejecting arbitrary reason strings
  would break any archived plan state or operator runbook already carrying one, and the risk is not
  assessable without an operator. Removing the misleading help example carries no runtime risk and is
  the whole documented defect.
- **Re-deriving the deleted token figures in `token-management.adoc`** (`090/G2`, `090/G3`). The
  population is an instrumented corpus run this lane cannot perform, and a deliverable that required
  it would stall with no one to unblock it. Deletion plus the qualitative claim is the shippable
  correction.
- **Re-quoting a fresh validator measurement** (`240/G11`, `240/G12`). A number measured in this run's
  container drifts again by the next change; the audit's own note is that a range was chosen to
  survive drift and the range no longer contains the value. Naming the command is the fix that does
  not need refiling.
- **The corpus-read performance change behind `120/G10`.** A crawl-time optimisation is a behaviour
  change with its own measurement obligation, and no timing measured in a shared tree is trustworthy
  (see § Claim labels). The cost is recorded as a proposal instead.
- **Deciding where two configuration keys belong** (`220/G4`'s second half) and **where the
  characterization rule lives when neither candidate skill owns fixture discipline** (`350/G17`).
  Both are placement judgements about a contract's ownership; per the lane's no-operator constraint a
  run records a proposal and does not make the call.
- **Adding tests to pin corrected prose.** Except where a deliverable names one (D1's anchor case),
  a text-equality test converts every future rewording into a red build and is the kind of guard this
  epic has repeatedly had to remove. The corrections are verified by the checks in § Verification.
- **Any gap not listed in § Gap coverage.** The bucket is the scope. A defect found in passing is
  recorded in the run report as a lead, not fixed.

## Expected surface

Documentation and prose only, except where noted. Counts of files are leads; re-derive.

- `marketplace/bundles/plan-marshall/skills/*/SKILL.md` and `*/standards/*.md` and `*/references/*.md`
  — the largest share: `platform-runtime`, `manage-architecture`, `manage-metrics`,
  `plan-retrospective`, `manage-config`, `manage-execution-manifest`, `manage-solution-outline`,
  `manage-references`, `manage-run-config`, `manage-status`, `manage-tasks`, `marshall-steward`,
  `extension-api`, `tools-script-executor`, `tools-integration-ci`, `tools-file-ops`, `lsp-client`,
  `execute-task`, `phase-3-outline`, `phase-4-plan`, `phase-5-execute`, `phase-6-finalize`,
  `script-shared`.
- `marketplace/bundles/pm-plugin-development/skills/*` — `plan-marshall-plugin`,
  `tools-marketplace-inventory`, `tools-corpus-language-server`, `ext-self-review-plan-marshall`,
  `plugin-doctor`, `plugin-architecture`, `plugin-script-architecture`.
- `marketplace/bundles/pm-documents/skills/plan-marshall-plugin/` — SKILL.md and `scripts/doc_references.py`.
  **This is the one file with a behaviour change** (D1's `_heading_anchor_forms`).
- Docstrings, comments and argparse `help`/`description` strings inside production Python across those
  bundles — including `runtime_base.py`, `generate_executor.py`, `manage-status.py`,
  `manage-metrics.py`, `check-manifest-consistency.py`, `manage-solution-outline.py`,
  `marketplace_paths.py`, `file_ops.py`, `corpus_lsp.py`, `retro_sections.py`, `compile-report.py`,
  `plugin_discover.py`, `determine_mode.py`, `_cmd_client_handlers.py`, `_cmd_build_map.py`.
- `marketplace/bundles/plan-marshall/.claude-plugin/plugin.json` — one `skills[]` registration.
- `marketplace/targets/claude/plugin_json_gen.py` — one docstring field list.
- `test/plan-marshall/tools-script-executor/test_generate_executor.py` — one comment scoped;
  `test/pm-documents/plan-marshall-plugin/test_doc_references.py` — one added case.
- `doc/concepts/` (`token-management.adoc`, `code-intelligence.adoc`, `extension-architecture.adoc`),
  `doc/user/` (`dependency-intelligence.adoc`, `lsp-code-intelligence.adoc`,
  `corpus-language-server.adoc`), `doc/developer/corpus-language-server-protocol.adoc`,
  `doc/adr/` (one anti-vacuity table), `doc/resources/diagrams/context-isolation.svg`.
- `.claude/skills/audit-archived-plan-retrospectives/SKILL.md` — one row.
- `CLAUDE.md` — § Repository Overview counts.
- `doc/plans/code-intelligence-substrate/*/` — D6 only, and only if the directories are present.

## Claim labels

Every premise this plan's scope rests on. A claim is `OBSERVED` only where the audit **and** its
adversarial review both reproduced it by execution; anything resting on reading alone, on one
unreplicated measurement, or on a timing figure is `HYPOTHESIS` and carries a git-reachable artifact
that settles it.

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| `contract.md` and `runtime_base.py`'s docstring both state a divisor the reference suite refutes | OBSERVED | Substitute `attributable = cache_read_total` into `_attribute_cache_read` (`platform-runtime/scripts/claude_runtime.py`) and run `test/plan-marshall/platform-runtime/test_metrics_tokens.py -k attribute_cache_read`; the audit and its adversarial review both got 2 failed, 6 passed. D1 re-runs it as a gate. |
| The corrected cache-read model is already written in `_attribute_cache_read`'s own docstring | OBSERVED | `platform-runtime/scripts/claude_runtime.py`, `_attribute_cache_read` docstring |
| `_heading_anchor_forms` collapses hyphen runs where GitHub does not, so valid anchored references are reported dangling | OBSERVED | `pm-documents/skills/plan-marshall-plugin/scripts/doc_references.py`, `_heading_anchor_forms`; the adversarial review re-derived the whole sweep by substitution |
| Adding a GitHub-exact form removes every false anchor positive without hiding a genuine one | OBSERVED | Same review's substitution run: unresolved went from 18 to 8 with zero anchor survivors, all survivors genuine broken file paths. D1 re-derives both figures. |
| The generator's fail-open refusal exits `0`, not non-zero | OBSERVED | `tools-file-ops/scripts/file_ops.py`, `safe_main` docstring; `ref-workflow-architecture/standards/manage-contract.md` three-tier model |
| The shipped code contradicts the index-is-authoritative claim, and a non-vacuous test pins the crawl | OBSERVED | `_architecture_core.py` `load_project_meta` docstring; `tools-file-ops/scripts/constants.py`; `test/.../test_concept_model.py::test_module_on_disk_absent_from_index_is_still_discovered` — mutating `iter_modules` to read the index turns it red |
| The freshness crawl issues one child process, and it is a main-checkout-root resolution, not a build verb | OBSERVED | Re-instrumented at adversarial review with all `subprocess` entry points wrapped; corroborated by `build-maven/scripts/_maven_cmd_discover.py`'s explicit "subprocess-free" statement |
| Declared edges survive a full resolver switch-off, so the anti-vacuity third-state row is incomplete | OBSERVED | The sibling gap's probe returned `edge_count: 1` with `producers: ['declared']`; re-confirm by reading `_cmd_client_handlers.py`'s `cmd_path`/`cmd_impact` and the declared-edge path before editing the eight sites |
| The `siblings` and `profiles` verbs are registered and invoked but contracted nowhere | HYPOTHESIS (asserted absence — the highest-risk shape) | Search `manage-architecture/standards/` for each verb name before writing a section. A hit means the contract exists and only the Command Summary row is missing; write the row, not the section. |
| The characterization-corpus rule exists in no skill or standard | HYPOTHESIS (asserted absence) | Search `marketplace/bundles/**/*.md` for the rule's substance (fixture corpora enumerated from the live directory, exclusions justified) before writing it. A hit means the deliverable is a cross-reference, not a new rule. |
| Every count this plan states — surfaces, sites, verb sections, aspect rows, guards | HYPOTHESIS | Each is a lead by construction; the artifact is the re-derivation the run performs at the moment of the edit and records in the report |
| The per-call LSP latency figures, and any duration or throughput in a source gap | HYPOTHESIS | Measured in a shared tree with sibling agents running full suites. The reproducible facts are the *ordering effect* and the two floor-bounded waits in `_lsp_jsonrpc.py`; the magnitudes are not. D5 states only the former. |
| The stated crawl-cost range is correct for an unloaded host | OBSERVED (correcting the source gap) | Nine fresh measurements at adversarial review fell inside the shipped range; the audit's higher readings reproduced only under artificial CPU contention. The original "2× too low" claim is **withdrawn**; `300/G1` is low, not medium. |
| This epic's landed plan directories are still present in the clone | HYPOTHESIS | A listing of `doc/plans/code-intelligence-substrate/`. D6's gating derivation performs it and closes on the result. |

## Verification

⛔ **The build gate proves nothing about this plan's goal.** The lane's Python gate fires only on
production `*.py` change and, when it fires, it proves the tree still compiles and its tests still
pass — not that a corrected sentence is now true. Several deliverables here touch no Python at all.
**Run the gate where the lane requires it, and do not treat a green gate as evidence for any claim
below.** The proof of this plan is per-kind.

**Per-kind proof — every corrected statement is settled by the check that matches its kind.**

- **Kind (a), true-then-stale.** The correction is proved by **re-deriving the fact from its source at
  the moment of the fix and citing that source in the diff**. For a count: the corrected text either
  names the source (the table, the roster, the command) instead of the number, or states the number
  with the derivation recorded in the run report. For a shape or a field set: the documented set and
  the emitted set are compared field-for-field, and the report names the emitter symbol the comparison
  was run against. A kind-(a) fix that leaves a bare number with no recorded derivation is not done.
- **Kind (b), never-true.** A wrong rationale cannot be disproved by reading the sentence — only by
  opening the artefact it claims to describe. **Each kind-(b) correction must name, in the run report,
  the artefact that was opened and what it said**: the docstring, the registry, the instrumented
  count, the mutation result. Where the source gap already recorded that artefact (D1's mutation,
  the subprocess instrumentation, the registry lines behind `020/G10`), the run **re-opens it** and
  reports agreement or disagreement — the audit's word is corroboration, not proof.
- **Kind (c), normative-and-inverted.** The proof is that **the guard which contradicts the text still
  holds after the edit, and the text now agrees with it.** Name the guard per site: for the index
  claim, `test_module_on_disk_absent_from_index_is_still_discovered`; for the exit-code family,
  `safe_main`'s contract and a live run of the refusal; for the `worktree_fallback` family, the
  shipped test asserting `worktree_fallback is False` for a `pending` plan; for the Step-8b family,
  the canonical numbering line in `phase-4-plan/SKILL.md`. Run each named guard; a red guard means the
  correction went the wrong way.

**Cold reads — required, because these texts' whole value is what a later reader does.**
Dispatch the lane's pre-PR verification sub-agent (`cloud-plan-lane` § Step 6) with a reading task,
not a requirements-conformance task. Give it the corrected text and **nothing else** — no gap entry,
no plan section, no commit message — and have it report *which reading it took*:

1. Hand it the rewritten module-index paragraphs (D2.1) and ask: *"A per-module directory exists on
   disk and is absent from `_project.json["modules"]`. Does `architecture discover` see the module?"*
   The required answer is **yes, the crawl finds it**. Any answer that treats the index as a
   gatekeeper means the wording failed, however complete it looks.
2. Hand it the rewritten refusal paragraphs (D1.3) and ask: *"The generator refuses. What does my
   wrapper branch on?"* The required answer is **the `status` field**, with the exit code named as
   `0`. An answer that reaches for the exit code means the wording failed.
3. Hand it the rewritten unresolvable-footprint sentences (D2.4) and ask: *"A plan has
   `use_worktree` disabled. Why is the footprint unresolvable?"* The required answer names **both**
   causes and identifies the `disabled` case as "no worktree will ever exist" — not "not yet".
4. Hand it the rewritten isolation-cost sentence (D4.1) and ask: *"Should I split this dispatch?"*
   The required answer is that it **depends on a comparison the reader must make** — not an
   unconditional yes.

Record each cold read's question, the reading returned, and pass/fail in the run report. A failed
cold read is fixed by rewording and re-read, not by explaining the intended reading in the report.

**Structural and mechanical checks.**

- After every edit under `marketplace/bundles/`, run plugin-doctor's quality gate. ⚠ The lane has no
  generated executor, so invoke the entry script directly by its tracked path
  (`marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/doctor-marketplace.py`),
  scoped to the skills touched. D3.1 adds sections to an already-long `SKILL.md`, so the line-budget
  analyzer is the one most likely to object. **If the gate cannot be run in this runtime, say so in
  the report and record it as an open coverage gap** — do not report it as passing.
- Re-run the reference sweep behind D1.2 and report the unresolved count and the anchor/file split,
  before and after.
- For every "the sweep returns nothing" style *Done when*, run the search and paste the command and
  its result into the report. An empty result is a claim about an absence and is reported as such.
- Confirm no file outside § Expected surface changed, and that the only behaviour change in the diff
  is `_heading_anchor_forms`.

**Self-check before the PR.** Every deliverable's *Done when* is answered with the observation that
settles it, not with "done". Every count stated in this plan appears in the report beside its
re-derived value. Every recorded proposal (D3.3's configuration keys, D5.3's corpus read, D5.4's rule
placement if it triggers) is in the report and **not** acted on. Every HYPOTHESIS in § Claim labels is
resolved or explicitly carried forward with its artifact.

## Notes

**Sequencing — this plan should land last among the `5xx` fix plans, and this is not a preference.**
This plan corrects *descriptions of behaviour*. Its sibling plans (`500` LSP and derivation-resolver
correctness, `510` architecture-store query truthfulness, `520` measurement and cost integrity, `530`
detector and auditor integrity, `540` finalize-dispatch and blocking-boundary observability, `550`
test-suite anti-vacuity, `570` cloud-plan-lane contract proposals) change the behaviour being
described. Every source plan in this epic contributes gaps to four or five different buckets, so file
overlap with the siblings is pervasive and unavoidable — but a *corrected sentence describing
pre-`5xx` behaviour becomes stale the moment its sibling lands*. Running last minimises re-work and is
the only ordering under which this plan's own corrections are true when they merge.

If this plan runs before a sibling anyway, that is survivable but must be handled explicitly: the
run states, in its report, which corrected statements describe behaviour a sibling plan is scheduled
to change, so a later reader can find them. It does **not** anticipate the sibling's change — writing
prose for behaviour that has not landed is how kind (b) defects are created.

Two sibling-overlap hot spots to watch specifically:

- `pm-documents/.../doc_references.py` — this plan changes `_heading_anchor_forms`. Bucket `510`
  draws other gaps from the same source plan. Rebase and re-run the sweep if that plan landed first.
- `manage-architecture/standards/client-api.md` — D3 restructures headings across the whole file,
  which conflicts textually with almost any other edit to it. Take this file's edits in one commit so
  a conflict is resolvable as a unit.

**On the audit that produced these gaps.** Each gap was filed by a ground-truth audit and then
adversarially re-reviewed, with the review appended to each source plan's `verification.md`. **Where
a gap entry and its adversarial review disagree, the review wins** — it was the later, evidence-bearing
pass. Three of its corrections change what this plan does, and each is carried above at the point it
matters: `300/G1`'s original claim is **withdrawn** and its severity re-rated (do not widen the crawl
range); `030/G1`/`030/G2` were re-rated **high** because an implementation built from the contract
text fails the reference suite; and `230/G17`'s original verb enumeration named a verb that does not
exist, which would have sent a fixer to write a second broken notation.

**On timing evidence.** Any figure in a source gap that is a duration or a throughput was measured in
a tree shared with other agents running full suites. Two such figures were shown to be contention
artifacts. This plan therefore treats **every** duration as a lead to re-measure, never as an
established fact, and where a correction would have to quote one it quotes the reproducible property
instead (an ordering effect, a floor, a command to run).

**On `.plan/`.** Several gap entries name `.plan/` paths — plan directories, handshake stores, the
generated executor. `.plan/` is git-ignored and **absent from this run's clone**. Do not go looking
for any of it. Where a deliverable concerns a `.plan/` path (D2.6's handshake-read routing), the work
is entirely in the prose that *instructs* a reader, and needs no access to the store itself.

**On the gap files.** Each gap is cited below as `{source-plan}/gaps.md#{id}` for corroboration. Those
files are git-tracked and should be readable, but a landed cloud plan's directory is deleted at
collect, so **they may be gone**. Everything needed to execute this plan is restated above; treat a
gap file as a bonus, never as required reading, and never block on one.

## Gap coverage

156 gaps: 3 high, 63 medium, 90 low. Every gap in the bucket appears exactly once. Cite as
`doc/plans/code-intelligence-substrate/{source-plan}/gaps.md#{id}`.

| Deliverable | Source plan | Gap ids |
|---|---|---|
| **D1** Guarantees the code refutes | `030-attribution-populations-and-the-cost-decomposition` | G1 **(high)**, G2 **(high)** |
| | `120-documentation-surface-provider` | G1 **(high)**, G2, G11 |
| | `040-generator-fails-open-and-its-fixtures-cannot-see-it` | G3, G4, G5, G6, G7 |
| | `230-validate-precision` | G3, G4 |
| | `260-chat-signal-provenance-filter-under-inclusive` | G2 |
| | `160-empty-skill-resolution-indistinguishable-from-minimal` | G8 |
| | `300-freshness-gate-cannot-distinguish-test-authored-evidence` | G1, G2 |
| **D2** Retired semantics stated as normative | `150-architecture-store-concept-model` | G11, G12, G13, G18, G19, G20 |
| | `160-empty-skill-resolution-indistinguishable-from-minimal` | G7, G15 |
| | `140-project-local-artifact-provider` | G2, G3, G9 |
| | `280-outline-plan-scope-derivation-integrity` | G4, G5, G13 |
| | `350-outline-derived-set-closure-integrity` | G9, G13 |
| | `110-blocking-boundary-arms-on-a-call-not-a-state` | G13 |
| | `320-manifest-cross-check-discards-production-tree` | G10 |
| | `310-main-sha-records-the-pinned-cwd` | G4 |
| | `190-frozen-manifest-diverges-from-live-config` | G2, G7 |
| | `220-resolver-configuration` | G8 |
| **D3** Query contract and reader pages | `135-remove-lsp-query-facade` | G1, G3, G4, G5, G6, G7, G8, G9 |
| | `200-lsp-derivation-resolver` | G4, G5, G7, G11 |
| | `210-native-coordinate-resolvers` | G8 |
| | `220-resolver-configuration` | G3, G4 |
| | `240-skill-lsp-server` | G13 |
| **D4** Measurement and retrospective docs | `090-envelope-length-and-the-isolation-currency` | G1, G2, G3, G4, G8, G9, G10 |
| | `330-retrospective-report-sections-structurally-dead` | G7, G8, G10, G11, G12, G14 |
| | `320-manifest-cross-check-discards-production-tree` | G1, G6, G7, G8 |
| | `270-aggregate-cost-invisible-to-per-call-ceiling` | G6, G7 |
| | `310-main-sha-records-the-pinned-cwd` | G2, G5 |
| | `340-token-ledgers-disagree-and-the-smallest-is-named-actual` | G1, G7 |
| | `170-finalize-dispatch-evidence-is-missing` | G12, G14 |
| | `060-dispatch-boundary-ledger-is-not-a-commensurable-population` | G7 |
| | `290-auditor-detector-integrity` | G12 |
| **D5** Skill contracts: phase, tooling, LSP | `010-lsp-in-execute-lookup-and-write` | G7, G8, G9, G10, G12, G16 |
| | `240-skill-lsp-server` | G11, G12, G14, G15, G16, G17, G24, G27 |
| | `230-validate-precision` | G17, G18, G21 |
| | `120-documentation-surface-provider` | G4, G10 |
| | `310-main-sha-records-the-pinned-cwd` | G6, G7 |
| | `050-post-run-band-contract-and-ordering-residue` | G3, G6 |
| | `100-self-review-surfacing-integrity` | G4 |
| | `110-blocking-boundary-arms-on-a-call-not-a-state` | G3 |
| | `250-footprint-read-outside-its-window` | G3 |
| | `350-outline-derived-set-closure-integrity` | G17 |
| **D6** The epic's plan-directory records | `020-corpus-residency-admission-control` | G3, G4, G5, G6, G7, G8, G9, G10 |
| | `300-freshness-gate-cannot-distinguish-test-authored-evidence` | G10, G11, G12, G13, G14, G15 |
| | `240-skill-lsp-server` | G18, G19, G20, G21, G22, G23 |
| | `290-auditor-detector-integrity` | G13, G14, G15, G16, G17 |
| | `270-aggregate-cost-invisible-to-per-call-ceiling` | G8, G9, G10 |
| | `340-token-ledgers-disagree-and-the-smallest-is-named-actual` | G5, G9, G10 |
| | `100-self-review-surfacing-integrity` | G7, G8 |
| | `120-documentation-surface-provider` | G12, G13 |
| | `170-finalize-dispatch-evidence-is-missing` | G9, G11 |
| | `280-outline-plan-scope-derivation-integrity` | G7, G8 |
| | `320-manifest-cross-check-discards-production-tree` | G4, G5 |
| | `040-generator-fails-open-and-its-fixtures-cannot-see-it` | G8 |
| | `070-dispatch-spend-on-dispatches-that-produced-nothing` | G11 |
| | `090-envelope-length-and-the-isolation-currency` | G7 |
| | `110-blocking-boundary-arms-on-a-call-not-a-state` | G11 |
| | `135-remove-lsp-query-facade` | G11 |
| | `180-finalize-dispatch-manifest-observability` | G10 |
| | `220-resolver-configuration` | G5 |

⛔ **Re-derive the totals from this table before reporting coverage** — the per-deliverable counts
this plan implies (16 / 22 / 16 / 27 / 27 / 48) are a lead like every other count here, and a
transcription slip in a table this size is exactly the defect class the plan exists to close.
