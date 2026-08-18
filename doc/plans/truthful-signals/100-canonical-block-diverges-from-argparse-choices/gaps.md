# Gaps — 100-canonical-block-diverges-from-argparse-choices

**Source:** verification.md (same directory)   **Open items:** 7

The mechanism (D2/D3) is sound and mutation-verified. Every gap below is either a lead the run recorded as *refuted*
that is in fact live, or a sweep that stopped at the instance the plan pointed at.

## G1 — Document all 14 `FINDING_TYPES` in `manage-findings` SKILL.md, and reverse the "refuted" record

- **Kind:** stale-statement (incorrect oracle) + false refutation in the run report
- **Severity:** high
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-findings/SKILL.md:70` — § Finding Types
- **What is wrong:** the line enumerates 12 types (`bug`, `improvement`, `anti-pattern`, `triage`, `tip`, `insight`,
  `best-practice`, `build-error`, `test-failure`, `lint-issue`, `sonar-issue`, `pr-comment`) while
  `FINDING_TYPES` (`marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts/constants.py:118`) defines **14** —
  `arch-constraint` and `pr-comment-overflow` are missing, and neither string occurs anywhere in that SKILL.md
  (grep count 0 for each). `standards/jsonl-format.md:76` lists all 14, so the SKILL.md is the stale mirror.
  report-01.md § D1 records this lead as *"Refuted: nothing for a canonical-block guard to catch"*, but the plan's
  claim-label names the artifact as *"that SKILL.md versus the `FINDING_TYPES` constant"*, not its canonical block.
- **Why it matters:** this is precisely the plan's founding defect — an agent filing an `arch-constraint` finding and
  consulting `manage-findings/SKILL.md` reads a closed list of 12, concludes the type is invented under the project's
  *"never invent script subcommands/flags"* rule, and is wrong. The refutation also inoculates the instance against
  being re-filed.
- **Fix:** add `arch-constraint` and `pr-comment-overflow` to the `Types:` line at `SKILL.md:70`, ordered as in
  `FINDING_TYPES`. Do not restate their semantics — `standards/jsonl-format.md` §§ `arch-constraint` /
  `pr-comment-overflow` already own that; the § Finding Types pointer to it is sufficient.
- **Done when:** the set on `manage-findings/SKILL.md:70` equals `FINDING_TYPES` element for element, re-derived by
  parsing `constants.py` rather than by eye.
- **Module/topic:** `plan-marshall:manage-findings`

## G2 — Complete the `--category` enum at the two `manage-lessons` § Operations sites

- **Kind:** stale-statement (incorrect oracle)
- **Severity:** high
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-lessons/SKILL.md:207` (§ Operations → `update`) and
  `:260` (§ Operations → `list` parameter list)
- **What is wrong:** both document `--category bug|improvement|anti-pattern` while
  `LESSON_CATEGORIES` (`tools-file-ops/scripts/constants.py:191`) is
  `('bug','improvement','anti-pattern','arch-constraint')` and `manage-lessons.py:113` binds
  `VALID_CATEGORIES = LESSON_CATEGORIES`. The same file's canonical block at `SKILL.md:746/:758/:772` correctly
  documents all four, so the document contradicts itself. report-01.md records this lead as
  *"Refuted: matches exactly"*, which is true only of the canonical block.
- **Why it matters:** § Operations is the reading path for anyone composing a `manage-lessons update`/`list` call;
  `arch-constraint` is a live, first-class category with its own `--rule` dedup lifecycle, and a reader following the
  § Operations enum would reject it as invented.
- **Fix:** at `:207` change the fenced form to `[--category {bug|improvement|anti-pattern|arch-constraint}]` (brace
  form, matching the canonical block so the D2 guard can see it); at `:260` add `arch-constraint` to the parenthetical
  list. While there, check the adjacent `--status` metavar at `:254` against its live `choices=`.
- **Done when:** every `--category` enum in `manage-lessons/SKILL.md` lists all four `LESSON_CATEGORIES` members, and
  `analyze_canonical_enum_drift` still returns 0 findings.
- **Module/topic:** `plan-marshall:manage-lessons`

## G3 — Fix the surviving `off/auto/full` lane enum in the `manage-config` verb table

- **Kind:** incomplete-sweep
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-config/SKILL.md:598` — the `finalize-steps` row of the
  noun/verb summary table
- **What is wrong:** the row reads *"persist a resolved `off`/`auto`/`full` lane override"*. The live authority is
  `_RESOLVED_ASK_LANE_VALUES = ('off', 'standard', 'full')`
  (`manage-config/scripts/_cmd_finalize_steps.py:68`, consumed at `manage-config.py:749` as
  `choices=list(_RESOLVED_ASK_LANE_VALUES)`). `auto` is rejected at runtime by the guard at `_cmd_finalize_steps.py:314`.
  D4 corrected the identical claim 771 lines below, at `SKILL.md:1369`, and left this one. `git log -S` dates the stale
  text to #1066, so it was present when the plan ran.
- **Why it matters:** the same false oracle the plan's one confirmed divergence was, in the same file — a reader
  consulting the summary table (the natural first stop) is told to pass a value argparse rejects.
- **Fix:** replace ``off`/`auto`/`full`` with ``off`/`standard`/`full`` at `SKILL.md:598`.
- **Done when:** no occurrence of `auto` as a `--lane` value remains under `marketplace/bundles/`; verified by
  `grep -rn "off.*auto.*full" marketplace/bundles/` returning only the `rule-provenance.md:242` narrative row, which
  quotes the historical defect deliberately.
- **Module/topic:** `plan-marshall:manage-config`

## G4 — Remove the fifth false "not registered in plugin.json" claim

- **Kind:** incomplete-sweep (asserted absence that is false)
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/tools-integration-ci/SKILL.md:40`
- **What is wrong:** the line reads *"This skill is a script-only library (not registered in plugin.json)."* The skill
  **is** registered: `marketplace/bundles/plan-marshall/.claude-plugin/plugin.json:98` contains
  `"./skills/tools-integration-ci"`. Both the sentence and the registration were introduced by the same commit
  (#823, `git log -S` on each), so the claim was false from birth. D4 fixed four instances of this exact sentence but
  searched READMEs only.
- **Why it matters:** identical in kind to the four D4 fixed — a reader is told a skill cannot be loaded by
  `Skill: plan-marshall:tools-integration-ci` when it can, and this is the CI abstraction layer every workflow is
  required to route through.
- **Fix:** at `SKILL.md:40`, drop the parenthetical or replace it with the wording D4 standardised on elsewhere —
  *"registered in plugin.json and consumed by …"*. Then re-run the case-insensitive sweep
  `grep -rin "not registered" marketplace/bundles/*/README.md marketplace/bundles/*/skills/*/SKILL.md` and confirm the
  only survivors are the two genuine ones (`build-server-client/SKILL.md:128` and `phase-1-init/SKILL.md:955`, both
  about *project* registration with the build server, not plugin registration).
- **Done when:** no file under `marketplace/bundles/` claims a skill is unregistered while its bundle `plugin.json`
  registers it.
- **Module/topic:** `plan-marshall:tools-integration-ci`

## G5 — Resolve the three orphan `standards/` documents the D5 sweep missed

- **Kind:** incomplete-sweep + stale-statement in the run report
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-config/standards/domain-residency-audit.md`,
  `marketplace/bundles/plan-marshall/skills/manage-config/standards/provisioning-fail-closed-audit.md`,
  `marketplace/bundles/plan-marshall/skills/phase-3-outline/standards/integration-tests.md`
- **What is wrong:** report-01.md § D5 states *"a repo-wide reference scan surfaced **exactly two** true orphans"*. A
  filename-reference sweep over every `.md` and `.py` under `marketplace/bundles` finds **five** unreferenced
  `standards/` documents on the pre-fix tree (`8f23d7d2`) and **three** at HEAD — the two the run handled
  (`adding-document-types.md`, wired in; `script-organisation.md`, removed) plus the three above, which no file
  anywhere references by filename.
- **Why it matters:** the plan's D5 item is *"wire in or remove"*, and the stated count is what stops the remainder
  being re-filed as a fresh finding later. Three shipped documents are unreachable from any skill.
- **Fix:** for each of the three, decide wire-in or delete and act: if the content is current and unique, add an
  explicit link from the owning skill's SKILL.md (the pattern D5 used at `manage-plan-documents/SKILL.md:27`); if it
  duplicates a canonical standard, delete it and point at the canonical one. Note `integration-tests` as a *canonical
  build-target name* appears widely in prose (e.g. `build-maven/SKILL.md:79-83`); that is unrelated to the file
  `phase-3-outline/standards/integration-tests.md`, which is what is unreferenced.
- **Done when:** a filename-reference sweep over `marketplace/bundles/**/*.{md,py}` returns zero `standards/*.md` files
  referenced by nothing, and the derivation (not the number alone) is recorded.
- **Module/topic:** `plan-marshall:manage-config`, `plan-marshall:phase-3-outline`

## G6 — Register both new rules in the plugin-doctor rule catalogue

- **Kind:** doc-drift (a hand-maintained enumeration diverging from the registered set — this plan's own defect class)
- **Severity:** medium
- **Where:** `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/references/rule-catalog.md:1051-1053`
  (§ "Rule Pack: Manually-maintained-mirror drift") and
  `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/SKILL.md:370` and `:448`
- **What is wrong:** `canonical-enum-choices-drift` and `readme-skill-registration-drift` occur **zero** times in
  either file. The catalogue section opens *"**Four** rules that make a hand-maintained documentation mirror of a
  machine-derivable fact machine-checkable … all four are registered in `doctor-marketplace.py::cmd_quality_gate`"* and
  enumerates only `provides-method-table-drift`, `literal-count-drift`, `broken-relative-link`,
  `fenced-code-no-language`. Six such rules are now registered. `references/rule-provenance.md:242-243` *was* updated —
  it is guarded by `test_rule_provenance_table.py`; the catalogue and SKILL.md are not, which is why they drifted.
- **Why it matters:** the catalogue is the reader-facing enumeration of what plugin-doctor enforces; a maintainer
  consulting it will not learn these rules exist, and the literal count "Four" is now false — the precise shape this
  plan was written to make impossible.
- **Fix:** add a `### canonical-enum-choices-drift` and a `### readme-skill-registration-drift` subsection to
  `rule-catalog.md` § "Rule Pack: Manually-maintained-mirror drift" following the shape of the existing four, change
  "Four rules" to "Six rules" and "all four" to "all six", and add both rule IDs to the **Mirror-drift** bullets at
  `plugin-doctor/SKILL.md:370` and `:448`.
- **Done when:** both rule IDs appear in `rule-catalog.md` and `plugin-doctor/SKILL.md`, and the section's stated rule
  count equals the number of rule IDs the section enumerates.
- **Module/topic:** `pm-plugin-development:plugin-doctor`

## G7 — Close or declare the D2 guard's two coverage blind spots

- **Kind:** omission (unguarded surface inside the guard's declared class)
- **Severity:** medium
- **Where:** `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_canonical_enum_drift.py:150`
  (`_ENUM_TOKEN_RE`) and `:528` (`_authority_by_subcommand_flag`, called only on the notation's own script tree via
  `_script_path_for_notation` at `:296`)
- **What is wrong:** two silent-coverage holes, both re-derived at HEAD.
  (a) `_ENUM_TOKEN_RE` requires `{…}`, so a brace-less `--flag a|b|c` inside a canonical block is never collected —
  six such sites exist today (`manage-change-ledger/SKILL.md:215 --kind`,
  `tools-integration-ci/SKILL.md:321 --strategy` and `:344 --error-style`,
  `untrusted-ingestion/SKILL.md:57 --schema`, `workflow-integration-git/SKILL.md:807,810 --mode`).
  (b) the authority is parsed only from the file the notation names, so a skill whose parser is built by a shared
  module resolves nothing: **17 of 50** notations carrying documented enums resolve **zero** authority (59 of 146
  sites), including all four build tools, whose real `choices=['toon','json']` lives in
  `script-shared/scripts/build/_build_cli.py:184,275,351,405`.
  Neither hole hides a live divergence today — I probed all 76 unresolved sites against every resolvable `choices=` in
  the marketplace and every candidate resolved to a different subcommand or a different skill's flag — but neither is
  guarded, and the module docstring's fail-closed section names only per-flag reasons, not these structural ones.
- **Why it matters:** the plan's own standing remedy is *"scope the guard to the directive, or scope the directive to
  the guard — never state a directive the guard cannot see."* Six canonical-block enums are currently outside the
  guard purely because of a notation choice, and a third of the enum-bearing scripts are outside it because of where
  their argparse lives.
- **Fix:** (a) extend `_ENUM_TOKEN_RE` to accept the brace-less pipe form `--flag a|b|c` (require at least one `|` so a
  bare placeholder is not misread), and add a test asserting the six sites above are collected. (b) follow the same
  import-resolution hop `_Resolver.resolve_name` already performs for constants: when the notation's script imports a
  parser-building helper, parse that module's `add_argument` calls too — or, if that is judged too costly, publish the
  unresolved fraction as a named field on the analyzer's output and record the structural reasons in the module
  docstring's fail-closed list so the coverage gap is declared rather than silent.
- **Done when:** `derive_population` collects the six brace-less sites, and either the zero-authority notation count is
  driven below 17 or the analyzer publishes the unresolved fraction with its structural cause.
- **Module/topic:** `pm-plugin-development:plugin-doctor`
