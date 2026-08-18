# Verification — 100-canonical-block-diverges-from-argparse-choices

**Verified against:** commit `ac06e4fc94782328f87d1395472a72b7e7a8559d`   **Landed as:** PR #1158, commit `b59f3b93e6d6b4ffb71a523b3599cb2b76384a96`   **Verdict:** implemented-with-gaps

## Method

What was actually done, so an empty finding list is distinguishable from an unexamined one.

**Files read in full:** `plan.md`, `report-01.md`; the landed diff (`git show --stat b59f3b93`, 26 files); both new analyzers
(`_analyze_canonical_enum_drift.py` 727 lines, `_analyze_readme_skill_coverage.py`); both new test files;
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
byte-restored and verified.

## Deliverable-by-deliverable

| # | Deliverable | Done-when condition | Implemented? | As documented? | Correct? | Complete? | Evidence (file:line / symbol / command + result) |
|---|---|---|---|---|---|---|---|
| D1 | GATE: derive the population | divergent count and blocks-examined as two separate numbers; population stated | yes | **partly** | yes | **no** | Re-derived on pre-fix tree: 144 sites / 36 files / 69 resolved / **1** divergent — every figure matches the report. But "36 canonical blocks" is a **file** count; distinct `(file, notation, subcommand)` blocks = 116 (landed) / 118 (HEAD). Both named leads were recorded **refuted**; both are in fact live at the document sites the plan's claim-label named (see G1, G2). |
| D2 | The structural guard | rule ships, population-derived, publishes population size | yes | yes | yes | **partly** | `_analyze_canonical_enum_drift.py::RULE_DESCRIPTOR` (`severity='error'`, `category='structural'`, `scope='corpus-relational'`, `opt_in` defaults False → default-on); registered at `_rule_registry.py:88`, `_runner.py:247` (quality-gate) and `_runner.py:366` (analyze). `details['population_size']` present on every finding. Mutation check 1 fires it live. Authority is `_keyword_value(node,'choices')` only — `description=`/`help=` never read. Blind spots: brace-less `--flag a\|b\|c` (6 live sites) and cross-module parser builders (17 of 50 notations resolve zero authority) — see G7. |
| D3 | README vs `plugin.json` | rule compares each README's enumeration against registration and fails on divergence | yes | yes | yes | yes | `_analyze_readme_skill_coverage.py::derive_readme_population`; `_readme_names_skill` bounded by `(?<![\w-])…(?![\w-])` — verified by `test_longer_sibling_name_is_not_a_match`. Coverage-keyed rather than count-keyed, which the report states plainly. Re-derived: 13 omissions / 5 bundles pre-fix → 0 at HEAD. |
| D4 | Fix what the sweeps confirm | each confirmed divergence fixed; each unconfirmed lead recorded refuted with evidence | yes | **partly** | yes | **no** | Enum fix at `manage-config/SKILL.md:1369` ✓ (live `_RESOLVED_ASK_LANE_VALUES = ('off','standard','full')`, `_cmd_finalize_steps.py:68`). 13 README omissions ✓. Four false *"not registered in plugin.json"* sentences ✓ (re-derived case-insensitively on the pre-fix tree: pm-dev-frontend, pm-dev-oci, pm-dev-python, pm-plugin-development — exactly four). `cui-logging-enforce` → `recipe-cui-logging-enforce` ✓. **Incomplete:** the same `off/auto/full` claim survives at `manage-config/SKILL.md:598` (G3), and a fifth false *"not registered"* sentence survives at `tools-integration-ci/SKILL.md:40` (G4). Two leads mislabelled refuted (G1, G2). |
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
carrying documented enums resolve **zero** authority (59 of 146 sites) — including all four build tools, whose real
`choices=['toon','json']` lives in `script-shared/scripts/build/_build_cli.py:184,275,351,405`. Separately,
`_ENUM_TOKEN_RE` requires braces, so a brace-less `--flag a|b|c` inside a canonical block is invisible; six such sites
exist today. I probed every one of the 76 unresolved sites against every resolvable `choices=` in the marketplace and
found **no** true divergence hiding there, so the report's residue claim survives the test — but the report asserts it
without stating the derivation.

**D4/D5 — the sweeps stopped where the plan pointed.** In each of three cases the run corrected the instance named in
the plan and left an identical claim standing elsewhere: the `off/auto/full` lane enum at `manage-config/SKILL.md:598`,
the false *"not registered in plugin.json"* at `tools-integration-ci/SKILL.md:40` (registered at
`plan-marshall/.claude-plugin/plugin.json:98`), and three of five orphan `standards/` documents. All three predate the
plan (`git log -S` dates the lane text to #1066 and the `tools-integration-ci` sentence to #823, the same commit that
registered the skill).

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
   tree. (→ G6)
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
| "None of the D1 population's 75 unresolved-authority enum sites are defects" | **Holds under test.** 76 unresolved at HEAD (75 at landing, arithmetically consistent). Probed every one against every resolvable `choices=` marketplace-wide; the five candidate mismatches all resolve to a different subcommand's or a different skill's flag. Still **open** as an unguarded surface: 17 of 50 notations resolve no authority at all. |
| "The D3 guard is forward-only; the reverse direction (a README naming a non-existent skill) is not enforced" | **Still open** by design. `derive_readme_population` has no reverse pass. The one known reverse instance stays fixed (`pm-dev-java-cui/README.md` names `recipe-cui-logging-enforce`; no `pm-dev-java-cui:cui-logging-enforce` skill reference survives — the two remaining `cui-logging-enforce` hits are the extension **recipe key** in `plan-marshall-plugin/extension.py:76`, which is a different namespace). |
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
