# Gaps — 100-canonical-block-diverges-from-argparse-choices

**Source:** verification.md (same directory)   **Open items:** 10

The mechanism (D2/D3) ships and is mutation-verified in the direction it was built for. Every gap below is
either a lead the run recorded as *refuted* that is in fact live, a sweep that stopped at the instance the
plan pointed at, or — G10 — a defect in the shipped guard itself. Gaps G8–G10 were added during adversarial
review; G1–G7 were re-verified against the tree and the clauses that did not survive re-derivation are
recorded under § Refuted during adversarial review.

## G1 — Document all 14 `FINDING_TYPES` in `manage-findings` SKILL.md, and reverse the "refuted" record

- **Kind:** stale-statement (incorrect oracle) + false refutation in the run report
- **Severity:** high
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-findings/SKILL.md:70` (§ Finding Types) and
  `:45-56` (the per-type rows of the § Storage file tree, fenced at `:40-62`)
- **What is wrong:** line 70 enumerates 12 types (`bug`, `improvement`, `anti-pattern`, `triage`, `tip`,
  `insight`, `best-practice`, `build-error`, `test-failure`, `lint-issue`, `sonar-issue`, `pr-comment`) while
  `FINDING_TYPES` (`marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts/constants.py:118`) defines
  **14** — re-derived by `ast.literal_eval` of the assignment, not by eye. `arch-constraint` and
  `pr-comment-overflow` are missing, and neither string occurs **anywhere** in that SKILL.md (`grep -c` = 0 for
  each). The same two are also absent from the storage-layout tree at `:45-56`, which lists twelve
  `{type}.jsonl` files and omits `arch-constraint.jsonl` / `pr-comment-overflow.jsonl` — so the document is
  short by the same two types at two independent sites. `standards/jsonl-format.md:39`, `:41` and `:76` carry
  all 14, so the SKILL.md is the stale mirror on both counts.
  report-01.md § D1 records this lead as *"Refuted: nothing for a canonical-block guard to catch"*, but the
  plan's claim-label names the artifact as *"that SKILL.md versus the `FINDING_TYPES` constant"*, not its
  canonical block.
- **Why it matters:** this is precisely the plan's founding defect — an agent filing an `arch-constraint`
  finding and consulting `manage-findings/SKILL.md` reads a closed list of 12, concludes the type is invented
  under the project's *"never invent script subcommands/flags"* rule, and is wrong. `arch-constraint` is a
  live first-class type with its own producer (`default:verify:arch-gate`) and its own lifecycle. Recording
  the reversal also inoculates the instance against being re-filed.
- **Fix:** (a) add `arch-constraint` and `pr-comment-overflow` to the `Types:` line at `SKILL.md:70`, ordered
  as in `FINDING_TYPES`; (b) add `arch-constraint.jsonl` and `pr-comment-overflow.jsonl` rows to the tree at
  `SKILL.md:45-56`, positioned as in `FINDING_TYPES` (i.e. `arch-constraint.jsonl` after `sonar-issue.jsonl`,
  `pr-comment-overflow.jsonl` after `pr-comment.jsonl`), matching
  `manage-findings/standards/jsonl-format.md:39,41`. Do not restate their semantics —
  `standards/jsonl-format.md` §§ `arch-constraint` / `pr-comment-overflow` already own that.
- **Done when:** the set on `manage-findings/SKILL.md:70` and the set of `{type}.jsonl` rows in the
  `:45-56` tree each equal `FINDING_TYPES` element for element, re-derived by parsing `constants.py` rather
  than by eye, and `grep -c "arch-constraint" manage-findings/SKILL.md` is non-zero.
- **Module/topic:** `plan-marshall:manage-findings`

## G2 — Complete the `--category` enum at the two `manage-lessons` § Operations sites

- **Kind:** stale-statement (incorrect oracle)
- **Severity:** medium — re-severitied down from `high` during adversarial review; see § Refuted for the
  reasoning
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-lessons/SKILL.md:207` (§ Operations → `update`)
  and `:260` (§ Operations → `list` parameter list)
- **What is wrong:** both document `--category bug|improvement|anti-pattern` while
  `LESSON_CATEGORIES` (`tools-file-ops/scripts/constants.py:191`) is
  `('bug','improvement','anti-pattern','arch-constraint')` (re-derived by parsing the assignment) and
  `manage-lessons.py:113` binds `VALID_CATEGORIES = LESSON_CATEGORIES`, consumed at `:1212`, `:1231` and
  `:1242` as `choices=list(VALID_CATEGORIES)`. The same file documents all four at `:104` (the `add`
  parameter list) and at `:746`, `:758`, `:772` (the canonical block), so the document contradicts itself.
  report-01.md records this lead as *"Refuted: matches exactly"*, which is true only of the canonical block.
- **Why it matters:** § Operations is the reading path for anyone composing a `manage-lessons update`/`list`
  call; `arch-constraint` is a live, first-class category with its own `--rule` dedup lifecycle, and a reader
  following the § Operations enum would reject it as invented. It is `medium` rather than `high` because the
  correct four-member set is stated three other times in the same file and argparse accepts `arch-constraint`
  at both flags — no call fails and no behaviour is wrong.
- **Fix:** at `:207` change the fenced form to `[--category {bug|improvement|anti-pattern|arch-constraint}]`
  (brace form, matching the canonical block so the D2 guard can see it); at `:260` add `arch-constraint` to
  the parenthetical list.
- **Done when:** every `--category` enum in `manage-lessons/SKILL.md` lists all four `LESSON_CATEGORIES`
  members, and `analyze_canonical_enum_drift` still returns 0 findings over `marketplace/bundles`.
- **Module/topic:** `plan-marshall:manage-lessons`

## G3 — Fix the three surviving `off`/`auto`/`full` lane restatements in the `manage-config` skill

- **Kind:** incomplete-sweep
- **Severity:** medium
- **Where:** all three under `marketplace/bundles/plan-marshall/skills/manage-config/`:
  - `SKILL.md:598` — the `finalize-steps` row of the noun/verb summary table:
    *"persist a resolved `off`/`auto`/`full` lane override"*
  - `standards/data-model.md:581` — *"`auto`/`full` pin its tier"*, in a sentence whose own enum three
    clauses earlier correctly reads `off`\|`minimal`\|`standard`\|`full`\|`ask`
  - `scripts/_config_defaults.py:939` — the `_LANE_ASK_INFRA_STEPS` comment: *"which persists a resolved
    `off`/`auto`/`full`"*
- **What is wrong:** the live authority is `_RESOLVED_ASK_LANE_VALUES = ('off', 'standard', 'full')`
  (`manage-config/scripts/_cmd_finalize_steps.py:68`, consumed at `manage-config.py:749` as
  `choices=list(_RESOLVED_ASK_LANE_VALUES)`), and the wider reader enum is
  `VALID_LANE_OVERRIDE = ('off', 'minimal', 'standard', 'full', 'ask')` (`_config_defaults.py:481`,
  enforced by `validate_lane_override` at `:484`). `auto` is in neither set: it is rejected at runtime by the
  guard at `_cmd_finalize_steps.py:314`. D4 corrected the identical claim at `SKILL.md:1369` and left these
  three. `git log -S` dates the `SKILL.md:598` text to #1066 (`d04ac98e`), so it was present when the plan ran.
- **Why it matters:** the same false oracle the plan's one confirmed divergence was, in the same skill — a
  reader consulting the summary table (the natural first stop) is told to pass a value argparse rejects, and
  a maintainer reading `_config_defaults.py:939` is told the same thing at the constant that seeds the
  channel.
- **Fix:** replace `` `auto` `` with `` `standard` `` at `SKILL.md:598`, `standards/data-model.md:581` and
  `scripts/_config_defaults.py:939`. The correct wording already exists verbatim at `manage-config/SKILL.md:723`
  (*"every other accepted lane value (`standard`, `full`, `ask`, or an absent override)"*) — copy that form.
- **Done when:** `grep -rn '`auto`' marketplace/bundles/plan-marshall/skills/manage-config/` returns no hit in
  which `auto` is presented as a `lane` value (the surviving hits are the unrelated `gate_mode` enum
  `auto|always|never` at `SKILL.md:713`, `data-model.md:576`, `:605`, `_config_defaults.py:594`, and the
  `lane_selection` enum `ask|auto` at `SKILL.md:738`, `data-model.md:578`), and `validate_lane_override`
  still rejects `auto`.
- **Module/topic:** `plan-marshall:manage-config`

## G4 — Remove the fifth false "not registered in plugin.json" claim

- **Kind:** incomplete-sweep (asserted absence that is false)
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/tools-integration-ci/SKILL.md:40`
- **What is wrong:** the line reads *"This skill is a script-only library (not registered in plugin.json)."*
  The skill **is** registered: `marketplace/bundles/plan-marshall/.claude-plugin/plugin.json:98` contains
  `"./skills/tools-integration-ci"`. Both the sentence and the registration were introduced by the same
  commit — `git log -S` on each string returns `87c677bb` (#823) — so the claim was false from birth. D4
  fixed four instances of this exact sentence (`pm-dev-frontend/README.md:37`, `pm-dev-oci/README.md:33`,
  `pm-dev-python/README.md:19`, `pm-plugin-development/README.md:47`, re-derived case-insensitively on the
  pre-fix tree `8f23d7d2`) but searched READMEs only.
- **Why it matters:** identical in kind to the four D4 fixed — a reader is told a skill cannot be loaded by
  `Skill: plan-marshall:tools-integration-ci` when it can, and this is the CI abstraction layer every workflow
  is required to route through.
- **Fix:** at `SKILL.md:40`, drop the parenthetical or replace it with *"registered in plugin.json and
  consumed by …"*.
- **Done when:** a sweep for the **class**, not the phrasing —
  `grep -rniE "(not|never|must not be) registered in .?plugin\.json" marketplace/bundles/ --include=*.md` —
  returns no file that names a skill its own bundle `plugin.json` registers. Note that the phrasing-only
  pattern `"not registered"` is **insufficient**: it misses the variant recorded as G9. The two surviving
  hits after this fix and G9 are `build-server-client/SKILL.md:128` and `phase-1-init/SKILL.md:955`, both
  about *project* registration with the build server rather than plugin registration, plus the generic
  troubleshooting prose at `pm-plugin-development/skills/verification-mode/standards/resolution-analysis.md:51`
  and `workaround-detection.md:172`, which name no skill.
- **Module/topic:** `plan-marshall:tools-integration-ci`

## G5 — Resolve the three orphan `standards/` documents the D5 sweep missed

- **Kind:** incomplete-sweep + stale-statement in the run report
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-config/standards/domain-residency-audit.md`,
  `marketplace/bundles/plan-marshall/skills/manage-config/standards/provisioning-fail-closed-audit.md`,
  `marketplace/bundles/plan-marshall/skills/phase-3-outline/standards/integration-tests.md`
- **What is wrong:** report-01.md § D5 states *"a repo-wide reference scan surfaced **exactly two** true
  orphans"*. Re-derived independently: a filename-reference sweep over every `.md` and `.py` under
  `marketplace/bundles` (361 `*/skills/*/standards/*.md` documents on both trees) finds **five** unreferenced
  documents on the pre-fix tree (`8f23d7d2`) and **three** at HEAD — the two the run handled
  (`adding-document-types.md`, wired in at `manage-plan-documents/SKILL.md:27`; `script-organisation.md`,
  removed) plus the three above, which no file anywhere references by filename.
- **Why it matters:** the plan's D5 item is *"wire in or remove"*, and the stated count is what stops the
  remainder being re-filed as a fresh finding later. Three shipped documents are unreachable from any skill.
- **Fix:** for each of the three, decide wire-in or delete and act: if the content is current and unique, add
  an explicit link from the owning skill's SKILL.md (the pattern D5 used at `manage-plan-documents/SKILL.md:27`);
  if it duplicates a canonical standard, delete it and point at the canonical one. Note that
  `integration-tests` as a *canonical build-target name* appears widely in prose (e.g. `build-maven/SKILL.md:79-83`);
  that is unrelated to the file `phase-3-outline/standards/integration-tests.md`, which is what is unreferenced.
- **Done when:** a filename-reference sweep over `marketplace/bundles/**/*.{md,py}` returns zero
  `*/skills/*/standards/*.md` files referenced by nothing, and the derivation (not the number alone) is
  recorded.
- **Module/topic:** `plan-marshall:manage-config`, `plan-marshall:phase-3-outline`

## G6 — Register both new rules in the plugin-doctor rule catalogue

- **Kind:** doc-drift (a hand-maintained enumeration diverging from the registered set — this plan's own
  defect class)
- **Severity:** medium
- **Where:** `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/references/rule-catalog.md:1051`
  (§ "Rule Pack: Manually-maintained-mirror drift", opening sentence at `:1053`) and
  `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/SKILL.md:370` and `:448`
- **What is wrong:** `canonical-enum-choices-drift` and `readme-skill-registration-drift` occur **zero** times
  in either file. The catalogue section opens *"**Four** rules that make a hand-maintained documentation
  mirror of a machine-derivable fact machine-checkable … all four are registered in
  `doctor-marketplace.py::cmd_quality_gate`"* and enumerates only `provides-method-table-drift`,
  `literal-count-drift`, `broken-relative-link`, `fenced-code-no-language`. Six such rules are now registered:
  both new analyzers appear in `_rule_registry.py:88` and `:115` and in `_runner.py:248`/`:255` (quality-gate)
  and `:366`/`:367` (analyze). `references/rule-provenance.md:242-243` *was* updated — it is guarded by
  `test_rule_provenance_table.py`; the catalogue and SKILL.md are not, which is why they drifted. No existing
  rule covers this literal: `literal-count-drift` is scoped to the `extension-api` "Extension Points" table
  and the `persona-security-expert` standards index only (`rule-catalog.md:1084`).
- **Why it matters:** the catalogue is the reader-facing enumeration of what plugin-doctor enforces; a
  maintainer consulting it will not learn these rules exist, and the literal count "Four" is now false — the
  precise shape this plan was written to make impossible.
- **Fix:** add a `### canonical-enum-choices-drift` and a `### readme-skill-registration-drift` subsection to
  `rule-catalog.md` § "Rule Pack: Manually-maintained-mirror drift" following the shape of the existing four,
  change "Four rules" to "Six rules" and "all four" to "all six" at `:1053`, and add both rule IDs to the
  **Mirror-drift** bullets at `plugin-doctor/SKILL.md:370` and `:448`.
- **Done when:** both rule IDs appear in `rule-catalog.md` and `plugin-doctor/SKILL.md`, and the section's
  stated rule count equals the number of `### ` rule subsections the section enumerates.
- **Module/topic:** `pm-plugin-development:plugin-doctor`

## G7 — Close or declare the D2 guard's two coverage blind spots

- **Kind:** omission (unguarded surface inside the guard's declared class)
- **Severity:** medium
- **Where:** `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_canonical_enum_drift.py:150`
  (`_ENUM_TOKEN_RE`) and `:528` (`_authority_by_subcommand_flag`, reached only through the notation's own
  script via `_script_path_for_notation` at `:296`)
- **What is wrong:** two silent-coverage holes, both re-derived at HEAD by an independent sweep.
  (a) `_ENUM_TOKEN_RE` requires `{…}`, so a brace-less `--flag a|b|c` inside a canonical block is never
  collected. A fence-aware sweep of every `## Canonical invocations` section, filtered to genuine value
  enums (discarding the `(--a X | --b Y)` mutually-exclusive-group form the analyzer deliberately excludes),
  returns **exactly six** such sites: `manage-change-ledger/SKILL.md:215 --kind build|change|job`,
  `tools-integration-ci/SKILL.md:321 --strategy merge|squash|rebase` and
  `:344 --error-style maven|gradle|npm|generic`,
  `untrusted-ingestion/SKILL.md:57 --schema research|ci-finding|issue-body|finding`, and
  `workflow-integration-git/SKILL.md:807` and `:810 --mode local_and_remote|local_only`.
  (b) the authority is read **only** from `add_argument(..., choices=)` nodes in the file the notation names,
  so **17 of 50** notations carrying documented enums resolve **zero** authority (**60** of 146 sites; 76
  sites are unresolved in total). That number has three distinct structural causes, not one:
  - a *shared parser-building module* — the four build tools, whose real `choices=['toon','json']` lives at
    `script-shared/scripts/build/_build_cli.py:185,276,352,406` and whose `--mode` sets live at `:179` and
    `:273` (`choices=modes`, widened per tool by `parse_extra_modes=['no-openrewrite']` at
    `build-gradle/scripts/gradle.py:93` and `build-maven/scripts/maven.py:107`); and the
    `workflow-integration-github` scripts, built by `tools-integration-ci/scripts/ci_base.py`;
  - a *declarative arg-spec builder* — `manage-change-ledger.py` and `workflow-pr-doctor/scripts/pr_doctor.py`
    contain **zero** `add_argument` calls and declare `'choices': [...]` as a dict key, which the AST walk
    never inspects, even though the parser is in the notation's own file;
  - a *genuine absence of `choices=`* — `manage-execution-manifest.py` has 29 `add_argument` calls and no
    `choices=` at all (e.g. `:3288`, `:3291` put the enum in `help=` and validate in the handler). This third
    class is a correct fail-closed skip and is **not** a guard defect; it is a defect in those scripts.
  Neither hole hides a live divergence today — every one of the 76 unresolved sites was probed against every
  literal `choices=` set in the marketplace (both `add_argument` keyword and dict-spec forms, with constant
  and `list()/sorted()` wrapper resolution) and every candidate mismatch resolved to a different
  subcommand's or a different skill's flag; the four build tools, `manage-change-ledger append --status`
  (`BUILD_STATUSES`, `_ledger_core.py:81`) and the `github_ops` review/merge flags (`ci_base.py:1057`,
  `:963-995`) were each confirmed correct by hand. But none is guarded, and the module docstring's
  fail-closed section names only per-flag reasons, not these structural ones.
- **Why it matters:** the plan's own standing remedy is *"scope the guard to the directive, or scope the
  directive to the guard — never state a directive the guard cannot see."* Six canonical-block enums are
  outside the guard purely because of a notation choice, and a third of the enum-bearing notations are outside
  it because of where or how their argparse is declared.
- **Fix:** (a) extend `_ENUM_TOKEN_RE` to accept the brace-less pipe form `--flag a|b|c` (require at least one
  `|`, and reject a member list in which any member begins with `--`, so the mutually-exclusive-group form
  `(--a X | --b Y)` is not misread), and add a test asserting the six sites above are collected. (b) teach
  `_authority_by_subcommand_flag` the dict-spec form (`{'flags': [...], 'choices': [...]}`) — this is a
  same-file parse and closes `manage-change-ledger` and `pr_doctor` cheaply — and follow the import hop
  `_Resolver.resolve_name` already performs for constants so a parser built in an imported module is parsed
  too. If the import hop is judged too costly, publish the unresolved-notation fraction as a named field on
  the analyzer's output and record the three structural causes in the module docstring's fail-closed list, so
  the coverage gap is declared rather than silent.
- **Done when:** `derive_population` collects the six brace-less sites, and either the zero-authority notation
  count is driven below 17 or the analyzer publishes the unresolved fraction together with its structural
  cause per notation.
- **Module/topic:** `pm-plugin-development:plugin-doctor`

## G8 — Fix the two surviving `off`/`auto`/`full` lane restatements in `manage-execution-manifest`

- **Kind:** incomplete-sweep (same defect class as G3, different owning skill)
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/standards/decision-rules.md:144`
  and `:394`
- **What is wrong:** `:144` reads *"A resolved ask (`off`/`auto`/`full`) and a provider-configured ask both
  survive"*; `:394` reads *"every other value (`auto` / `full` / `ask` / absent) → `auto`"*. Neither `auto`
  is a lane value: the closed set is `VALID_LANE_OVERRIDE = ('off','minimal','standard','full','ask')`
  (`manage-config/scripts/_config_defaults.py:481`, enforced by `validate_lane_override` at `:484`), and the
  resolved-ask subset is `_RESOLVED_ASK_LANE_VALUES = ('off','standard','full')`
  (`manage-config/scripts/_cmd_finalize_steps.py:68`). The same skill states the correct form four times —
  `SKILL.md:702`, `:723`-equivalent prose, `decision-rules.md:150` and
  `scripts/manage-execution-manifest.py:1014` all read `standard`/absent → `auto`. At `:394` the *second*
  `auto` (the `gate_mode` target the transform produces) is correct; only the lane-value list is stale, and
  it additionally omits `standard`.
- **Why it matters:** `decision-rules.md` is the authority document for the ceremony-gate transform; a reader
  composing a per-element override from it is told to write a value `validate_lane_override` rejects, and
  is not told about the one value that actually works.
- **Fix:** at `:144` replace `` `off`/`auto`/`full` `` with `` `off`/`standard`/`full` ``; at `:394` replace
  the lane-value list `(`auto` / `full` / `ask` / absent)` with `(`standard` / `full` / `ask` / absent)`,
  leaving the trailing `→ `auto`` gate-mode target unchanged.
- **Done when:** no line under
  `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/` presents `auto` as a value of the
  per-element `lane` override, and `decision-rules.md:144` and `:394` agree with `decision-rules.md:150`.
- **Module/topic:** `plan-marshall:manage-execution-manifest`

## G9 — Remove the false "MUST NOT be registered in `plugin.json`" claim in `manage-execution-manifest`

- **Kind:** stale-statement (asserted absence that is false) — the variant G4's phrasing-keyed sweep misses
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/SKILL.md:13`
- **What is wrong:** the line ends *"Per the project memory's plugin.json registration rules, it MUST NOT be
  registered in `plugin.json`."* The skill **is** registered:
  `marketplace/bundles/plan-marshall/.claude-plugin/plugin.json:57` contains
  `"./skills/manage-execution-manifest"`. The registration is not the error — the documented rule is. The
  actual convention, stated by the rule that enforces it
  (`plugin-doctor/references/rule-catalog.md:1177`, `plugin-json-orphan-component`), is that
  `user-invocable: true` skills **MUST** register while `user-invocable: false` skills are *"legitimately
  unregistered and therefore exempt"* — **exempt, not forbidden**. This skill carries
  `user-invocable: false`, so registering it is permitted; the sentence invents a prohibition.
- **Why it matters:** it is a cross-document assertion about a site outside itself with nothing checking it —
  the plan's exact class. Acted on literally it would drive a maintainer to *deregister* a skill the D3 guard
  now requires the bundle README to name, and it contradicts the sibling case G4 covers, where the same
  script-only shape is registered without comment.
- **Fix:** at `SKILL.md:13`, delete the final sentence (*"Per the project memory's … `plugin.json`."*). The
  preceding two sentences already state the operative facts — script-only, no user-invocable command, invoked
  through the 3-part notation — and remain true. If a statement about registration is wanted, use the rule's
  own wording: *"`user-invocable: false`, so `plugin-json-orphan-component` exempts it from the registration
  requirement; it is nonetheless registered at `plan-marshall/.claude-plugin/plugin.json:57`."*
- **Done when:** no SKILL.md under `marketplace/bundles/` asserts a registration state its own bundle's
  `plugin.json` contradicts, verified by the class-level sweep in G4's Done-when.
- **Module/topic:** `plan-marshall:manage-execution-manifest`

## G10 — The D2 analyzer mis-attributes every invocation after the first in a shared fenced block

- **Kind:** wrong behaviour in the shipped guard (false positive + silent false negative)
- **Severity:** high
- **Where:** `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_canonical_enum_drift.py:225-277`
  (`_enum_sites_in_skill`), specifically the `if block_notation is None:` latch at `:258`
- **What is wrong:** the parser records the notation **and subcommand path** of the *first* executor
  invocation in a fenced block and never updates them, on the stated assumption *"in practice the notation is
  always the block's first line"* (comment at `:264-265`). That assumption is false: **15** fenced blocks
  inside `## Canonical invocations` sections carry more than one executor invocation today. Every enum below
  the first invocation in such a block is scoped to the wrong subcommand.
  - **Proven false positive.** On a synthetic two-skill tree (`demo alpha --kind choices=['x','y']`,
    `demo beta --kind choices=['p','q']`, both invocations in one fenced block, both documented correctly),
    `analyze_canonical_enum_drift` emits **1 error-severity finding** against the *correct* `beta` line:
    `documented=['p','q'], choices=['x','y'], missing_from_doc=['x','y'], not_in_choices=['p','q']`. The rule
    is registered in `cmd_quality_gate`, so this fails the build on a correctly-written document. This is the
    exact `manage-tasks` `update`-vs-`list --status` hazard the run reports having closed by subcommand
    scoping — the scoping is simply bypassed whenever two invocations share a fence.
  - **Live false negatives.** In `manage-run-config/SKILL.md`, `--value {enabled,disabled}` at `:414`
    (belonging to `architecture-refresh set-tier-0`) and `--value {prompt,auto,disabled}` at `:419`
    (belonging to `architecture-refresh set-tier-1`) are both attributed to `architecture-refresh get-tier-0`,
    which has no `--value` flag. Both therefore resolve no authority and are reported `resolved=False` —
    examined-and-skipped — when their true authorities (`ARCHITECTURE_REFRESH_TIER_0_VALUES` and
    `_TIER_1_VALUES` at `run_config.py:30` and `:32`, used at `:1256` and `:1274`) are fully resolvable. Both
    documents happen to be correct today, so nothing is currently mis-reported as clean; the coverage,
    however, is fictional. Two further sites at `:399` and `:402` (`warning list` / `warning remove
    --category`) are likewise attributed to `warning add`, harmless only because all three share
    `VALID_WARNING_CATEGORIES`.
- **Why it matters:** the deliverable's own correctness argument is *"subcommand-scoped — this is what
  prevents the false positive"*, and a build-failing rule that reddens a correct document is the shipped
  false signal this epic exists to eliminate. The mis-scoped sites also inflate the published
  `population_size` with entries whose recorded `subcommand` is factually wrong, so the population — the
  number the plan requires precisely so a clean result cannot pass for coverage — over-reports.
- **Fix:** in `_enum_sites_in_skill`, re-evaluate the notation on every line rather than only when
  `block_notation is None`: replace the `if block_notation is None:` guard at `:258` with an unconditional
  `_NOTATION_RE.search(raw)`, updating `block_notation` / `block_path` whenever a line matches, and keep the
  previous values for continuation lines that carry no notation. Add two tests: (i) the synthetic
  two-invocation block above must yield **0** findings; (ii) `derive_population` over the real tree must
  report `subcommand == ('architecture-refresh','set-tier-1')` for the `manage-run-config/SKILL.md:419`
  `--value` site, and that site must be `resolved` and non-diverged.
- **Done when:** both tests pass, no site in `derive_population(marketplace/bundles)` carries a subcommand
  path that the invocation line immediately above it does not name, and `analyze_canonical_enum_drift` still
  returns 0 findings over the real tree.
- **Module/topic:** `pm-plugin-development:plugin-doctor`

## Refuted during adversarial review

No gap was refuted in whole — G1–G7 each re-derive at the tree. Three **clauses** did not survive
re-derivation and have been corrected in place; they are recorded here so the corrections are not re-litigated.

- **G3's original Done-when — refuted.** It asserted that
  `grep -rn "off.*auto.*full" marketplace/bundles/` would return *"only the `rule-provenance.md:242` narrative
  row"* once `SKILL.md:598` was fixed. Run as written the pattern returns **eight** rows, of which four are
  further live stale sites (`manage-config/standards/data-model.md:581`,
  `manage-config/scripts/_config_defaults.py:939`,
  `manage-execution-manifest/standards/decision-rules.md:144` and `:394`) and two are correct prose that the
  pattern matches incidentally (`manage-execution-manifest/SKILL.md:723`,
  `extension-api/standards/marshal-json-reference.md:101`). G3 was widened to its three manage-config sites,
  the two `manage-execution-manifest` sites were filed as G8, and the Done-when was rewritten to a check a
  reader can actually run to completion.
- **G7's single-cause attribution for the 17 zero-authority notations — refuted.** The original text
  attributed all 17 to *"a skill whose parser is built by a shared module"*. That holds for the four build
  tools and the `workflow-integration-github` scripts, but `manage-change-ledger.py` and `pr_doctor.py`
  contain **no** `add_argument` calls at all and declare choices as a dict key in the same file, and
  `manage-execution-manifest.py` has no `choices=` anywhere. G7 now names three distinct causes and marks the
  third as a correct fail-closed skip rather than a guard defect.
- **G7's "59 of 146 sites" — refuted.** Re-derived from `derive_population` at HEAD, the 17 zero-authority
  notations cover **60** sites (6+7+6+6+2+9+1+1+1+1+3+1+2+9+1+1+3), of 76 unresolved in total. Corrected to 60
  in G7 and in verification.md.
- **G7's `_build_cli.py:184,275,351,405` — refuted.** Those lines are the `'--format',` argument name; the
  `choices=['toon','json']` literals are at `:185`, `:276`, `:352`, `:406`. Corrected in G7 and in
  verification.md.
- **G2's severity `high` — re-severitied to `medium`, not refuted.** The defect is real at both named lines,
  but `manage-lessons/SKILL.md` states the complete four-member set three other times (`:104`, and the
  canonical block at `:746`/`:758`/`:772`), argparse accepts `arch-constraint` at both flags
  (`manage-lessons.py:1231`, `:1242`), and no call fails. It is a self-contradicting document, not a shipped
  wrong behaviour. G1 stays `high` because `arch-constraint` and `pr-comment-overflow` appear **nowhere** in
  `manage-findings/SKILL.md` — that document is uniformly wrong, with no correct restatement to fall back on.
- **G2's trailing "While there, check the adjacent `--status` metavar at `:254`" — resolved, and removed as
  unactionable.** Checked: `manage-lessons/SKILL.md:254` documents `--status active|superseded|removed|all`,
  which equals `LIST_STATUS_CHOICES = ('active','superseded','removed','all')`
  (`manage-lessons.py:115`, consumed at `:1245`). No divergence; nothing to fix.
