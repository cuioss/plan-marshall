# Verification — 100-canonical-block-diverges-from-argparse-choices

**Verified against:** commit `ac06e4fc94782328f87d1395472a72b7e7a8559d`   **Landed as:** PR #1158, commit `b59f3b93e6d6b4ffb71a523b3599cb2b76384a96`   **Verdict:** implemented-with-gaps

## Method

What was actually done, so an empty finding list is distinguishable from an unexamined one.

**Files read in full:** `plan.md`, `report-01.md`; the landed diff (`git show --stat b59f3b93`, 26 files); both new analyzers
(`_analyze_canonical_enum_drift.py` 726 lines, `_analyze_readme_skill_coverage.py` 250 lines); both new test files;
`_runner.py` §§ `run_quality_gate` / `run_analyze_marketplace_rules`; `_rule_registry.py::_DESCRIPTOR_MODULES`;
`references/rule-provenance.md` rows 242–243; `references/rule-catalog.md` § "Rule Pack: Manually-maintained-mirror drift";
`plugin-doctor/SKILL.md` lines 370/448; `manage-findings/SKILL.md` §§ Finding Types + Canonical invocations;
`manage-lessons/SKILL.md` §§ Operations + Canonical invocations; `manage-config/SKILL.md` lines 594–600 and 1365–1370;
`AGENTS.md` lines 42/86; `_analyze_bash_chain_shapes_in_skills.py`; `script-shared/scripts/build/_build_cli.py`;
`tools-file-ops/scripts/constants.py` §§ `FINDING_TYPES` / `LESSON_CATEGORIES`.

**Tests run.**

- `uv run python -m pytest test/pm-plugin-development/plugin-doctor/test_analyze_canonical_enum_drift.py
  test/pm-plugin-development/plugin-doctor/test_analyze_readme_skill_coverage.py -o addopts="" -q` → **15 passed** (5.36s).
  Confirms the report's "15 tests" figure exactly (9 + 6).
- `… test_runner.py test_rule_provenance_table.py test_zero_match_suite_coverage.py -o addopts="" -q` → **20 passed**.
  The rule-integration meta-tests the report says it had to satisfy are green.

**Analyzers executed, not merely read.** Both `derive_population()` and `analyze_*()` were run over
(a) today's tree, (b) the exact landed tree (`git archive b59f3b93 marketplace`), and (c) the pre-fix parent tree
(`8f23d7d2`) with the *post-fix* analyzers grafted in, which is what makes the D1/D3 pre-fix numbers re-derivable.

| Tree | enum sites | SKILL.md files | resolved | divergent | bundles | registered | README omissions |
|---|---|---|---|---|---|---|---|
| pre-fix `8f23d7d2` | 144 | 36 | 69 | **1** | 10 | 152 | **13 across 5 bundles** |
| landed `b59f3b93` | 144 | 36 | 69 | 0 | 10 | 152 | 0 |
| HEAD `ac06e4fc` | 146 | 36 | 70 | 0 | 11 | 154 | 0 |

The single pre-fix divergence re-derives as
`plan-marshall/skills/manage-config/SKILL.md:1358 --lane documented ['auto','full','off'] vs choices ['full','off','standard']`,
and the 13 omissions re-derive as exactly the skill names the report lists, bundle for bundle.

**Mutation checks (2), both restored from bytes saved before mutating — never `git checkout`/`restore`/`stash`.**

1. *Does the guard actually catch the class on the real tree?* Re-introduced `--lane {off,auto,full}` at
   `manage-config/SKILL.md:1369`, ran `analyze_canonical_enum_drift(marketplace/bundles)` → **1 finding**, with
   `missing_from_doc=['standard']`, `not_in_choices=['auto']`, `population_size=146`. Restored; `git diff --stat` on the
   file is empty.
2. *Is the D6(c) positive-population assertion load-bearing?* Changed `_skill_md_files`'s glob to `*/skills/*/NOSUCH.md`
   (the "guard examined nothing" failure the plan names as its single most important test) and re-ran the enum test file →
   **4 failed, 5 passed**, `test_positive_population_over_real_tree` among the failures. The assertion is not vacuous.
   Restored; `git diff --stat` on the analyzer is empty.

**Extra sweeps run to test completeness claims** (each a script under the scratchpad, run with `uv run python`):
tree-wide probe of all 76 unresolved-authority sites against every resolvable `add_argument(..., choices=)` in the
marketplace; brace-less-pipe-enum sweep inside canonical blocks; orphan-`standards/`-document sweep on both the pre-fix
and current trees; per-bundle README stated-count vs `plugin.json` registration count; case-insensitive
`"not registered"` sweep across every README **and** every SKILL.md.

⚠ **Concurrency note.** Another session was writing to this working tree during verification
(`plan-marshall/README.md`, `phase-6-finalize/standards/branch-cleanup.md`,
`workflow-integration-git/scripts/git-workflow.py`, and sibling `verification.md` files appeared in
`git status --porcelain` at times I made no such edit). Neither file I mutated appears in `git diff` at exit; both were
byte-restored and verified. The adversarial review saw the same interference directly: one `derive_readme_population`
run reported `plan-marshall` omitting `plan-orchestrator`, and an immediate re-run over an unmodified,
`git status`-clean `plan-marshall/README.md` (which names the skill at `:32` and `:51`) reported **0** omissions. The
HEAD figures below are the reproducible ones — every one was re-derived at least twice.

## Deliverable-by-deliverable

| # | Deliverable | Done-when condition | Implemented? | As documented? | Correct? | Complete? | Evidence (file:line / symbol / command + result) |
|---|---|---|---|---|---|---|---|
| D1 | GATE: derive the population | divergent count and blocks-examined as two separate numbers; population stated | yes | **partly** | yes | **no** | Re-derived on pre-fix tree: 144 sites / 36 files / 69 resolved / **1** divergent — every figure matches the report. But "36 canonical blocks" is a **file** count; distinct `(file, notation, subcommand)` blocks = 116 (landed) / 118 (HEAD). Both named leads were recorded **refuted**; both are in fact live at the document sites the plan's claim-label named (see G1, G2). |
| D2 | The structural guard | rule ships, population-derived, publishes population size | yes | yes | **no** | **partly** | `_analyze_canonical_enum_drift.py::RULE_DESCRIPTOR` (`severity='error'`, `category='structural'`, `scope='corpus-relational'`, `opt_in` defaults False → default-on); registered at `_rule_registry.py:88`/`:115`, `_runner.py:248`/`:255` (quality-gate) and `:366`/`:367` (analyze). `details['population_size']` present on every finding. Mutation check 1 fires it live, and was reproduced independently during adversarial review (same line, same `missing_from_doc`/`not_in_choices`, `population_size=146`). Authority is `_keyword_value(node,'choices')` only — `description=`/`help=` never read. ⛔ **Correctness downgraded during adversarial review:** `_enum_sites_in_skill` latches the notation and subcommand path of a fenced block's FIRST invocation and never updates them, so every enum below a second invocation in the same block is scoped to the wrong subcommand — proven on a synthetic tree to emit a build-failing finding against a *correct* document, and live at 4 sites in `manage-run-config/SKILL.md` (15 multi-invocation blocks exist). See G10. Blind spots: brace-less `--flag a\|b\|c` (6 live sites) and unresolved authority (17 of 50 notations, 60 of 146 sites, three structural causes) — see G7. |
| D3 | README vs `plugin.json` | rule compares each README's enumeration against registration and fails on divergence | yes | yes | yes | yes | `_analyze_readme_skill_coverage.py::derive_readme_population`; `_readme_names_skill` bounded by `(?<![\w-])…(?![\w-])` — verified by `test_longer_sibling_name_is_not_a_match`. Coverage-keyed rather than count-keyed, which the report states plainly. Re-derived: 13 omissions / 5 bundles pre-fix → 0 at HEAD. |
| D4 | Fix what the sweeps confirm | each confirmed divergence fixed; each unconfirmed lead recorded refuted with evidence | yes | **partly** | yes | **no** | Enum fix at `manage-config/SKILL.md:1369` ✓ (live `_RESOLVED_ASK_LANE_VALUES = ('off','standard','full')`, `_cmd_finalize_steps.py:68`). 13 README omissions ✓. Four false *"not registered in plugin.json"* sentences ✓ (re-derived case-insensitively on the pre-fix tree: pm-dev-frontend, pm-dev-oci, pm-dev-python, pm-plugin-development — exactly four). `cui-logging-enforce` → `recipe-cui-logging-enforce` ✓. **Incomplete:** the `off/auto/full` claim survives at **five** further sites — `manage-config/SKILL.md:598`, `manage-config/standards/data-model.md:581`, `manage-config/scripts/_config_defaults.py:939` (G3) and `manage-execution-manifest/standards/decision-rules.md:144`, `:394` (G8) — and the false-registration claim survives twice: `tools-integration-ci/SKILL.md:40` (G4) and, in the variant *"MUST NOT be registered"* that a phrasing-keyed sweep misses, `manage-execution-manifest/SKILL.md:13` (G9). Two leads mislabelled refuted (G1, G2). |
| D5 | Retire the confirmed contradictions | each fixed or explicitly refuted with evidence | yes | **partly** | yes | **no** | (a) `recipe-cui-logging-enforce/SKILL.md:199-200` now qualified `pm-dev-java-cui:cui-logging`; both targets exist under `cui-logging/standards/` ✓. (b) four `ext-outline-workflow/standards/change-*.md` gone; only `change-types.md` remains; the prose-referenced per-type files live in `phase-3-outline/standards/` and are intact ✓ — no dangling reference. (c) `adding-document-types.md` wired in at `manage-plan-documents/SKILL.md:27`; `tools-script-executor/standards/script-organisation.md` deleted with no surviving reference ✓ — but the claim "exactly two true orphans" is contradicted: **five** existed pre-fix, **three** remain (G5). (d) `AGENTS.md:42` and `:86` reconciled ✓; the report's rationale that the enforced set is `&&`/`;`/trailing `&` with a bare `\|` permitted is confirmed at `_analyze_bash_chain_shapes_in_skills.py:24-32,106-109`. |
| D6 | Tests, each verified to FAIL pre-fix | all four hold; report states each was seen to fail before it passed | yes | **partly** | yes | yes | 15 tests, all green. (a) `test_flags_truncated_enum` ✓ (b) `test_passes_correct_enum` ✓ (c) `test_positive_population_over_real_tree` ✓ — proven non-vacuous by mutation check 2 (d) `test_flags_omitted_skill` / `test_passes_complete_enumeration` ✓. **Caveat:** the report's "seen to fail before it passed" evidence is *module-removal → collection error*, which reddens every test uniformly and discriminates nothing. The discrimination claim rests on the Step-6 sub-agent's narrative. I supplied the missing evidence independently (mutation checks 1 and 2); the guard does discriminate, so this is a weakness of the attestation, not of the tests. |

**D1 — the two leads.** The plan's claim-label table names the confirm/refute artifact for the `manage-findings` lead as
*"that SKILL.md versus the `FINDING_TYPES` constant"* — the whole document, not its canonical block. `FINDING_TYPES`
(`tools-file-ops/scripts/constants.py:118`) has **14** members, which the report states correctly. But
`manage-findings/SKILL.md:70` § Finding Types enumerates **12**: `arch-constraint` and `pr-comment-overflow` appear
nowhere in that SKILL.md (grep count 0 for each), while `standards/jsonl-format.md:76` lists all 14. The lead is
therefore **confirmed**, not refuted; the report's evidence establishes only the narrower proposition that the *canonical
block* has no enum to compare. The same shape holds for `manage-lessons`: the canonical block does document all four
categories (verified at `SKILL.md:746`, `:758`, `:772`), but `SKILL.md:207` and `:260` in § Operations document
`--category bug|improvement|anti-pattern` — three of the four in `LESSON_CATEGORIES`
(`constants.py:191 = ('bug','improvement','anti-pattern','arch-constraint')`).

**D2 — coverage the report does not quantify.** The authority is resolved only from the AST of the script the notation
names, so a skill whose parser is built by a shared module resolves nothing. Re-derived at HEAD: **17 of 50** notations
carrying documented enums resolve **zero** authority (**60** of 146 sites; 76 unresolved in total) — including all four
build tools, whose real `choices=['toon','json']` lives at `script-shared/scripts/build/_build_cli.py:185,276,352,406`.
The adversarial review found this single-cause framing too narrow: three distinct structural causes produce the 17 (a
shared parser-building module, a declarative dict-spec arg builder that declares no `add_argument` at all, and a
genuine absence of `choices=`). See G7. Separately,
`_ENUM_TOKEN_RE` requires braces, so a brace-less `--flag a|b|c` inside a canonical block is invisible; six such sites
exist today. I probed every one of the 76 unresolved sites against every resolvable `choices=` in the marketplace and
found **no** true divergence hiding there, so the report's residue claim survives the test — but the report asserts it
without stating the derivation.

**D4/D5 — the sweeps stopped where the plan pointed.** In each of three cases the run corrected the instance named in
the plan and left an identical claim standing elsewhere. The adversarial review widened each sweep and found the
residue larger than first recorded: the `off/auto/full` lane enum survives at **five** sites, not one
(`manage-config/SKILL.md:598`, `manage-config/standards/data-model.md:581`,
`manage-config/scripts/_config_defaults.py:939`, `manage-execution-manifest/standards/decision-rules.md:144` and
`:394` — G3, G8); the false-registration claim survives at **two**, not one
(`tools-integration-ci/SKILL.md:40`, registered at `plan-marshall/.claude-plugin/plugin.json:98` — G4; and
`manage-execution-manifest/SKILL.md:13`, registered at `:57`, phrased *"MUST NOT be registered"* — G9); and three of
five orphan `standards/` documents remain. All predate the plan (`git log -S` dates the `SKILL.md:598` lane text to
#1066 / `d04ac98e`, and the `tools-integration-ci` sentence to #823 / `87c677bb`, the same commit that registered the
skill).

## Report accuracy

Re-derived at the moment of writing. **Confirmed exactly:** 144 enum sites; 69 resolved; 1 divergent, at
`manage-config` `finalize-steps set-lane --lane`; `FINDING_TYPES` = 14; `LESSON_CATEGORIES` = 4; 10 bundles /
152 registered skills; 13 README omissions across 5 bundles with the exact skill lists given; "four READMEs" carrying
the false *not registered* sentence (case-insensitively — the fourth, `pm-plugin-development/README.md:47`, is
capitalised); "15 tests"; both rules default-on and registered in both runner passes; the enforced Bash-token set.

**Contradicted:**

1. *"`manage-findings` documents fewer types than `FINDING_TYPES`* … **Refuted**". The document lists 12 of 14 at
   `manage-findings/SKILL.md:70`. The lead is confirmed at the artifact the plan named; only the canonical-block
   sub-claim is refuted. (→ G1)
2. *"`manage-lessons` … Refuted: matches exactly"*. True of the canonical block; false of the document —
   `manage-lessons/SKILL.md:207,260` list three of four categories. (→ G2)
3. *"a repo-wide reference scan surfaced **exactly two** true orphans"*. A filename-reference sweep over every `.md`
   and `.py` in `marketplace/bundles` finds **five** unreferenced `standards/` documents on the pre-fix tree
   (`8f23d7d2`) and **three** at HEAD. (→ G5)
4. *"144 documented enum sites across **36 canonical blocks**"* (report § D1 and the PR body). 36 is the count of
   SKILL.md **files** carrying enum sites; distinct `(file, notation, subcommand)` blocks number 116 on the landed
   tree. This is a report/PR-body figure with no shipped-artifact mirror (no doc under `marketplace/bundles/` restates it), and a run report is a dated record that is not amended, so **no gap is filed**. The 116/118 figures re-derive exactly from `derive_population`.
5. *"**Seen to fail before it passed**: … both test files fail at collection … so every test is red (0 collected)"*.
   The statement is literally true but is not evidence that any individual control discriminates — a collection error
   reddens a tautological test identically. The plan asked for each of (a)–(d) to be *verified* to fail pre-fix.

Not contradicted but not verifiable from the tree: `18913 passed, 14 skipped`; the 8-commit/per-commit-gate history
(squash-merged); the Step-6 sub-agent's cold-read exchange; the reviewer-participation table.

## Out-of-scope compliance

Respected. The landed diff touches no `manage-metrics` file (confirmed against the 26-path file list), and contains no
`--enabled-bots` or `--participated-bots` change. The plan's OBSERVED claim about `manage-metrics` still holds at HEAD
by direct re-derivation: `DISPATCH_TERMINATION_CAUSES` now has **12** members (one added after the plan was written) and
all 12 appear in `manage-metrics/SKILL.md`. The retried-step attempt-identity gap is untouched.

No undeclared collateral change. Every landed path maps to a declared surface: `plugin-doctor/**` (D2/D3),
`marketplace/bundles/*/README.md` (D3/D4), `manage-config/SKILL.md` and `manage-plan-documents/SKILL.md` under the
plan's explicit "Open-ended: whatever additional SKILL.md files D1 surfaces" and D5(c), `pm-dev-java-cui/**` (D4/D5),
`ext-outline-workflow/standards/**` (D5), `AGENTS.md` (D5), `test/**` (D6), plus the plan directory itself. `CLAUDE.md`
was declared in the expected surface but not modified, and the report says why (already correct) — a declared-but-unused
surface, not collateral.

## Residue carried forward

| report-01.md residue item | Status in today's tree |
|---|---|
| "None of the D1 population's 75 unresolved-authority enum sites are defects" | **Holds under test.** 76 unresolved at HEAD (75 at landing, arithmetically consistent). Probed every one against every resolvable `choices=` marketplace-wide; the five candidate mismatches all resolve to a different subcommand's or a different skill's flag. Still **open** as an unguarded surface: 17 of 50 notations (60 of 146 sites) resolve no authority at all, from three distinct structural causes — see G7. |
| "The D3 guard is forward-only; the reverse direction (a README naming a non-existent skill) is not enforced" | **Still open** by design. `derive_readme_population` has no reverse pass. The one known reverse instance stays fixed (`pm-dev-java-cui/README.md` names `recipe-cui-logging-enforce`; no `pm-dev-java-cui:cui-logging-enforce` skill reference survives — the two remaining `cui-logging-enforce` hits are the extension **recipe key** at `pm-dev-java-cui/skills/plan-marshall-plugin/extension.py:76` and its table mirror at `pm-dev-java-cui/skills/plan-marshall-plugin/SKILL.md:43`, which is a different namespace). |
| Merge gate handed off pending CLA + final CI | **Settled** — the work is on `main` as `b59f3b93`. |

## What could NOT be verified

- The `./pw verify` totals (`18913 passed, 14 skipped`) and the two ~400s wall-clock figures — not reproduced here; a
  full verify exceeds the tool budget for this task.
- The eight-commit history and the per-commit quality-gate attestation — the PR was squash-merged, so the individual
  commits are not reachable from `main`.
- The Step-6 verification sub-agent's cold-read dialogue and its "no run report exists" finding — process artifacts with
  no tree residue. I substituted an independent equivalent: `test_description_hand_list_is_not_the_authority` plus a
  direct read of `_authority_by_subcommand_flag`, which together establish the same property from the tree.
- Reviewer participation (0 of 3) — a PR-surface fact, not a tree fact.
- Whether the run genuinely observed each of D6(a)–(d) red *individually* before it went green. The tree preserves only
  the module-removal method the report describes.

## Adversarial review

**Reviewed by:** an independent agent that did not write this document, working from the tree at `ac1618f3`
(35 commits past the `ac06e4fc` this document was written against; `ac06e4fc` confirmed an ancestor of HEAD,
so every finding below was re-checked as live rather than inherited).

**Checked.** Every figure in the § Method table was re-derived by loading both analyzers through
`test/pm-plugin-development/plugin-doctor/conftest.py::load_script_module` and running `derive_population` /
`analyze_*` / `derive_readme_population` over three trees: HEAD, `git archive b59f3b93` (landed) and
`git archive 8f23d7d2` (pre-fix) extracted to a scratch dir. Results, all matching this document exactly:
pre-fix 144 sites / 36 files / 69 resolved / **1** divergent / 10 bundles / 152 registered / **13** omissions
across 5 bundles (skill names bundle-for-bundle identical to report-01.md); landed 144/36/69/**0**/10/152/0;
HEAD 146/36/70/0/11/154/0. Distinct `(file, notation, subcommand)` blocks: **116** landed, **118** HEAD. The
single pre-fix divergence re-derives at `manage-config/SKILL.md:1358`, `finalize-steps set-lane --lane`,
documented `['auto','full','off']` vs choices `['full','off','standard']`.

Re-derived from source by parsing rather than by eye: `FINDING_TYPES` = **14** and `LESSON_CATEGORIES` = **4**
(`ast.literal_eval` over `tools-file-ops/scripts/constants.py`); `DISPATCH_TERMINATION_CAUSES` = **12** with
**0** members absent from `manage-metrics/SKILL.md` (the out-of-scope claim, re-confirmed); `VALID_LANE_OVERRIDE`
and `_RESOLVED_ASK_LANE_VALUES`; `BUILD_STATUSES`; `LIST_STATUS_CHOICES`; `ARCHITECTURE_REFRESH_TIER_{0,1}_VALUES`;
`VALID_WARNING_CATEGORIES`. Orphan-`standards/` sweep re-run on both trees over 361 documents each: **5** pre-fix,
**3** at HEAD, exactly the named files. `git log -S` re-run for the `#1066` and `#823` provenance claims (both
exact, and `#823` confirmed to have introduced both the sentence and the registration). Landed diff confirmed at
**26** files. Tests re-run: the two new files → **15 passed**; the three meta-tests → **20 passed**.

Sweeps re-run with **broader** patterns than the originals: (i) a fence-aware sweep of every
`## Canonical invocations` section for brace-less pipe enums, filtered to genuine value enums — returns exactly
the **six** sites G7 names, no more; (ii) a case-insensitive sweep for the false-registration **class**
(`not|never|must not be registered in plugin.json`) across every `.md` under `marketplace/bundles/`, which the
original phrasing-keyed sweep could not have caught — surfaced G9; (iii) a sweep for `auto`-as-a-lane-value that
does not assume the `off/auto/full` phrasing — surfaced two further G3 sites and the two G8 sites; (iv) a
whole-tree probe of all **76** unresolved sites against every literal `choices=` set in the marketplace, in
**both** the `add_argument` keyword form and the declarative dict-spec form the original probe did not model;
(v) a README stated-count-vs-registration sweep across all 11 bundles (0 real mismatches; `pm-documents`'
apparent 4/5 are "N workflows" phrases, not skill counts).

Functions executed, not read: `analyze_canonical_enum_drift` and `analyze_readme_skill_coverage` on the real
tree, on both archived trees, and on two purpose-built synthetic trees.

Mutations applied (each preceded by `git diff --quiet -- <path>`, each restored from bytes saved before
mutating, never `git checkout`/`restore`/`stash`; `git status --porcelain` clean for both files at exit):
1. Re-introduced `--lane {off,auto,full}` at `manage-config/SKILL.md:1369` → **1 finding**, line 1369,
   `missing_from_doc=['standard']`, `not_in_choices=['auto']`, `population_size=146`. Mutation check 1 in
   § Method reproduces exactly.
2. Synthetic tree with two invocations of one script in **one** fenced block, both documented **correctly**
   → **1 error-severity finding** against the correct line. This is G10, and it is the most consequential
   result of this review.
3. Synthetic README/`plugin.json` pair: omission flagged with the omitted skill named, clean after the name is
   added, and a README naming a non-existent skill emits nothing — confirming D3 both bites and is forward-only.

**Not re-checked.** The `./pw verify` totals and wall-clock figures; the squash-merged eight-commit history and
per-commit gate; the Step-6 sub-agent dialogue; reviewer participation. Also **not** re-run: § Method's mutation
check 2 (blanking `_skill_md_files`' glob), because another session was actively editing this working tree and a
temporarily broken shared analyzer would have poisoned its build — instead `test_positive_population_over_real_tree`
was read in full and found to assert population non-emptiness, the existence of a resolved site, the presence of
the named known-good member, **and** that member's exact resolved choices set, which establishes the same property
without mutating a shared file.

| Item | Original claim | Verdict | Evidence |
|---|---|---|---|
| G1 | `manage-findings/SKILL.md` lists 12 of 14 `FINDING_TYPES`; the "refuted" record is wrong | **upheld, widened** (stays `high`) | `FINDING_TYPES` parsed = 14; `grep -c` = 0 for `arch-constraint` and `pr-comment-overflow` in that file. Second site found: the § Storage tree at `:45-56` lists 12 `{type}.jsonl` rows and omits the same two, while `standards/jsonl-format.md:39,41` carries both. Fix and Done-when extended to cover it |
| G2 | Two § Operations sites list 3 of 4 `LESSON_CATEGORIES` | **upheld, re-severitied** `high` → `medium` | Confirmed at `:207` and `:260`; `LESSON_CATEGORIES` parsed = 4; `VALID_CATEGORIES` bound at `manage-lessons.py:113` and consumed at `:1231`/`:1242`. Downgraded because the same file states all four at `:104` and at `:746`/`:758`/`:772`, and argparse accepts `arch-constraint` at both flags — a self-contradicting document, not wrong behaviour. The trailing "check the `--status` metavar" instruction was resolved (it equals `LIST_STATUS_CHOICES`) and removed as unactionable |
| G3 | One surviving `off/auto/full` lane claim, at `manage-config/SKILL.md:598` | **upheld, widened; its Done-when refuted** | `:598` confirmed against `_RESOLVED_ASK_LANE_VALUES` / `VALID_LANE_OVERRIDE`. Two further manage-config sites found (`standards/data-model.md:581`, `scripts/_config_defaults.py:939`). The prescribed grep returns **eight** rows, not one — Done-when rewritten to a check that terminates |
| G4 | A fifth false *"not registered in plugin.json"* at `tools-integration-ci/SKILL.md:40` | **upheld; its sweep pattern corrected** | `plugin.json:98` registers it; `git log -S` puts both strings in `87c677bb` (#823). The prescribed `"not registered"` pattern is phrasing-keyed and misses the `"MUST NOT be registered"` variant → G9; Done-when replaced with a class-level pattern |
| G5 | Five orphan `standards/` docs pre-fix, three at HEAD, not two | **upheld exactly** | Independent filename-reference sweep over 361 documents on each tree returns 5 and 3, naming exactly the listed files |
| G6 | Neither new rule appears in `rule-catalog.md` or `plugin-doctor/SKILL.md`; the literal "Four" is now false | **upheld** | Zero occurrences of either rule ID in both files; `rule-catalog.md:1053` says "Four rules"; both rules registered at `_rule_registry.py:88`/`:115` and `_runner.py:248`/`:255`/`:366`/`:367`. Severity stays `medium`: `literal-count-drift` is scoped to two other surfaces (`rule-catalog.md:1084`), so no guard passes against this defect |
| G7 | Two blind spots: brace-less enums (6 sites) and 17-of-50 zero-authority notations (59 sites) from shared-module parsers | **upheld in substance; three clauses refuted** | The six brace-less sites re-derive exactly under a broader, fence-aware sweep. But: the site count is **60**, not 59; the `_build_cli.py` `choices=` literals are at `:185,276,352,406`, not `:184,275,351,405`; and the single "shared module" cause is wrong — `manage-change-ledger.py` and `pr_doctor.py` have **zero** `add_argument` calls and declare `'choices'` as a dict key in their own file, while `manage-execution-manifest.py` has no `choices=` at all (a correct fail-closed skip). Rewritten with three named causes and a per-cause fix |
| G8 | *(new)* Two further `off/auto/full` lane restatements in `manage-execution-manifest/standards/decision-rules.md:144,:394` | **added**, `medium` | Neither `auto` is in `VALID_LANE_OVERRIDE`; the same skill states the correct form at `SKILL.md:702`, `decision-rules.md:150` and `manage-execution-manifest.py:1014` |
| G9 | *(new)* `manage-execution-manifest/SKILL.md:13` asserts the skill *"MUST NOT be registered in `plugin.json`"* while `plugin.json:57` registers it | **added**, `medium` | The documented rule is the error, not the registration: `rule-catalog.md:1177` states `user-invocable: false` skills are *exempt*, not forbidden |
| G10 | *(new)* `_enum_sites_in_skill` latches the first invocation's notation **and subcommand path** for the whole fenced block | **added**, `high` | Executed proof: a synthetic block with two correctly-documented invocations yields a build-failing `error` finding against the correct one. Live at `manage-run-config/SKILL.md:399,402,414,419`, where `set-tier-0`/`set-tier-1 --value` are scoped to `get-tier-0` and silently resolve nothing; 15 multi-invocation blocks exist tree-wide. This defeats the very subcommand scoping the run cites as its false-positive protection |
| Method table (3 trees × 7 columns) | pre-fix / landed / HEAD figures | **upheld exactly** | Re-derived on all three trees; every one of the 21 cells matches |
| "Contradicted" #4 (36 blocks vs 116) | the report's "36 canonical blocks" is a file count | **upheld; its gap pointer refuted** | 116/118 re-derive. The pointer read "(→ G6)", but G6 is the rule-catalogue gap — no gap existed for this item. Corrected to state that no gap is filed, because the figure lives only in the run report and PR body and a dated record is not amended |
| D3 clean-pass row | "compares each README's enumeration against registration and fails on divergence" | **upheld behaviourally** | Synthetic mutation: fails on an omitted registered skill (`severity: error`, `population_size: 2`), passes once named, and emits nothing for a README naming an unregistered skill (forward-only, as the residue says). No stated-count mismatch exists at HEAD across all 11 bundles |
| D6 row / positive-population assertion | "proven non-vacuous by mutation check 2" | **upheld by a different means** | Mutation not repeated (concurrent session in the tree); instead the test body was read in full and asserts non-emptiness, a resolved site, the named known-good member, and that member's exact resolved choices set |
| Out-of-scope compliance | `manage-metrics` untouched; all 12 causes documented | **upheld** | Re-derived: 12 members, 0 absent from `manage-metrics/SKILL.md`; the landed 26-file list carries no `manage-metrics`, `--enabled-bots` or `--participated-bots` path |
| Verdict `implemented-with-gaps` | — | **upheld** | Every deliverable D1–D6 shipped; none is unimplemented, so `partially-implemented` does not apply. G10 downgrades D2's *Correct?* to **no** but does not un-ship it |

**Documents corrected.** In `verification.md`: the D2 row's *Correct?* → **no** with G10; the analyzer line
count 727 → **726** (identical at `ac06e4fc`, `b59f3b93` and HEAD); `_runner.py:247` → `:248` (plus the
second registration pair); `_build_cli.py:184,275,351,405` → `:185,276,352,406`; "59 of 146" → **60 of 146**
in both places; the single-cause framing of the 17 zero-authority notations replaced by three named causes;
the D4 row and the D4/D5 narrative widened to five lane sites and two false-registration sites; the broken
"(→ G6)" pointer on Contradicted #4 replaced with the reason no gap is filed; the `cui-logging-enforce`
residue row corrected to name both surviving sites (`extension.py:76` **and**
`plan-marshall-plugin/SKILL.md:43`); the concurrency note extended with a reproduction. In `gaps.md`: open
items 7 → **10**; G1 widened to its second site with corrected line ranges; G2 re-severitied to `medium` and
its unactionable trailing instruction resolved and removed; G3 widened to three sites with a Done-when that
terminates; G4's Done-when replaced with a class-level sweep; G7 rewritten (three causes, corrected figures
and line numbers); G8, G9, G10 added; a `## Refuted during adversarial review` section records the five
clauses that did not survive re-derivation.

**Residual doubt — what a third reviewer should look at first.**
1. **G10's blast radius.** Only the *analyzer* was tested for the first-invocation latch. `_analyze_manage_invocation.py`
   and any other rule that parses `## Canonical invocations` fenced blocks may carry the same assumption; the
   15 multi-invocation blocks are a shared hazard, not a `canonical-enum-choices-drift` one.
2. **The 17 zero-authority notations are the real coverage number.** `population_size: 146` is published on
   every finding, but 60 of those 146 sites are compared against nothing. A guard that reports a population
   without reporting its *resolved fraction* is one restatement away from the false-coverage signal this epic
   is about — G7's fallback (publish the unresolved fraction) may deserve to be the primary fix, not the
   fallback.
3. **Enums declared only in `help=`.** `manage-execution-manifest.py` documents six enums in its canonical
   block that argparse never constrains (`--track`, `--scope-estimate`, `--plan-change-type`, `--phase`,
   `--outcome`, `--commit-and-push`). Nothing in this plan's class covers "the document claims an enum the
   parser does not enforce", and it is the same shape one level down.
4. **Concurrency.** This tree had at least one other session writing to it throughout, including to
   `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py`. Every figure
   here was re-derived at least twice, but a third reviewer should re-run the population derivation on a
   quiescent checkout before treating any count as final.
