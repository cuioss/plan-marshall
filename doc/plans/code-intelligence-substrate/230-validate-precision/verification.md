# Verification — 230-validate-precision

**Audited:** `plan.md`, `report-01.md` (no other files present in the plan directory)
**Tree state:** `0beb095` on `claude/code-intelligence-substrate-analysis-kah884`
**Overall verdict:** CONFIRMED WITH GAPS

The shipped code does what the plan asked, and every headline measurement in the run report is
reproducible — the D0 partition to the row, the residue split, the zero-loss edge diff, the exact
fixture assertion. The gaps are elsewhere: two regression tests are vacuous (one of them the very
test the report cites as the fix for its most dangerous defect), one shipped contract sentence in
`SKILL.md` is false for the population the gate exists to find, and a handful of report figures are
one-off or self-contradictory.

## Deliverable verdicts

| # | Deliverable (short) | Report claim | Ground truth | Verdict |
|---|---|---|---|---|
| D0 | Classify the FULL unresolved set, publish per-class counts | 380 rows, table by shipped guard arm summing to 380 | Replayed the 380-row baseline through the shipped predicates: 145 / 75 / 64 / 46 / 28 (14+14) / 11 / 10 / 1 = 380, exact match | CONFIRMED |
| D1 | Placeholders are not references | `NOTATION_PLACEHOLDER_SEGMENTS`, applied to script *and* skill detectors, asserted by fixture | `_dep_detection.py:147`, applied at `:337`, `:391`, `:412`; mutation of the guard turns 6 tests red | CONFIRMED |
| D2 | A subcommand reference *resolves* | Retarget in the index onto the skill's entry script; 33 citations become edges | `_dep_index.py:481-529`, called at `:556-561`; live corpus: 37 retargets, 33 via the decision-log arm | CONFIRMED |
| D3 | Canonical commands are not script notation | `CANONICAL_COMMAND_PREFIXES` mirrors manage-config's authority | `_dep_detection.py:169` == `_cmd_quality_phases.py:68` byte-for-byte; mutation turns 3 tests red. No test pins the mirror | CONFIRMED (see G10) |
| D4 | Re-baseline; fix or file the residue | 380 → 62; residue 35 in-namespace / 27 unknown-bundle; 10 fixed, 35 filed | At the merge commit: 62 unresolved, split 35/27 exactly; all 10 fixed rows verified gone and their replacements resolve; all 35 filed rows still present | CONFIRMED |
| D5 | Precision fixture asserting **exactly one** finding | 7 non-references + 1 real break, `unresolved_count == 1`, each arm bites | `test_resolve_dependencies.py:1240-1307`; mutation of each of the six arms independently turns `test_exactly_one_finding` red | CONFIRMED |
| D6 | Document the contract; gate-grade verdict | `SKILL.md` gains "What counts as a reference" + "Precision of `validate`"; quality-gates page deliberately unchanged | `SKILL.md:182-215` present; `doc/developer/build.adoc` makes no claim about the validator (grep clean), so the conditional non-edit holds. Two claims in the new text are inaccurate | PARTIAL |

## Per-deliverable detail

### D0 — GATE: classify the FULL unresolved set

- **Required (plan):** every unresolved row carries a class and the per-class counts are published.
- **Claimed (report):** 380 rows classified as an enumeration; table by excluding guard arm summing
  to 380; claim-table figures 55 placeholder / 68 subcommand / 75 canonical / union 198 = 52.1%.
- **Found / checks run:** I extracted the pre-change tree (`git archive 3d96e40^`) and the merged
  tree (`git archive 3d96e40`) into a scratch dir and ran the validator over each with the pre-change
  and shipped detectors. The pre-change detector over the pre-change tree reproduces
  `total_components: 306`, `unresolved_count: 380`, `circular_dependencies: 294`. I then re-ran the
  shipped detector over that same corpus, captured the `Dependency.exclusion` arm for every detected
  edge, and joined the arms onto the 380 baseline rows:

  ```
  145  script/decision-log      75  script/canonical-command   64  script/none
   46  script/placeholder       28  script/embedded-token      11  import/none
    9  skill/placeholder         1  skill/none                  1  path/none      sum 380
  ```

  The report's two 14-row rows are the `embedded-token` arm split by sub-arm: re-deriving the
  positions gives 11 prefix-only, 14 suffix-only, 3 matching both — and since
  `_is_embedded_in_longer_token` tests the prefix first, the "both" rows attribute to the prefix arm,
  giving exactly 14/14. Applying the shipped predicates row-by-row also reproduces the claim table:
  decision-log **shape** matches 147 while 145 are *attributed* after placeholder precedence
  (the report states both conventions); placeholder 55, canonical 75, subcommand-under-the-shipped-
  rule 68, union 198 = 52.1%, remainder 182 = 47.9%.
- **Verdict:** CONFIRMED — the published partition is re-derivable from the shipped code, which is
  precisely what the plan's Verification asked for.

### D1 — documentation placeholders are no longer references

- **Required (plan):** prose documenting the notation produces no finding, asserted by fixture.
- **Found:** `NOTATION_PLACEHOLDER_SEGMENTS` at `_dep_detection.py:147-162`; consumed by
  `_has_placeholder_segment` (`:172`) at `detect_script_notations` (`:337`) and, as the report
  claims, on the skill detector too — frontmatter branch `:391-395` and `Skill:` branch `:412-414`.
- **Checks run:** mutating `_has_placeholder_segment` to `return False` turns 6 tests red including
  `TestPrecisionRegressionFixture::test_exactly_one_finding`. A synthetic probe confirms both
  directions: `Referenced as \`probe-bundle:real-skill:script\` in docs.` yields no edge, while
  `Run probe-bundle:real-skill:real-skill now.` yields a resolved edge.
- **Verdict:** CONFIRMED.

### D2 — subcommands are no longer misread as scripts

- **Required (plan):** a subcommand reference **resolves** rather than reporting unresolved.
- **Found:** `_entry_script_for_subcommand` at `_dep_index.py:481-529`, invoked from
  `_index_dependencies_from:556-561` **before** the drop, and only for a shape in
  `VERB_BEARING_EXCLUSIONS` (`_dep_detection.py:51`, the single member `DECISION_LOG`).
- **Checks run:** instrumenting the live index shows **37** retargets recorded as edges — 33 through
  the decision-log arm (matching the report's re-derived figure), 4 through unexcluded prose — plus
  **24** retargets suppressed as self-edges. Mutating the retarget to always return `None` turns 8
  tests red. `pm-plugin-development:plugin-doctor:validate` is still reported unresolved (6 rows at
  HEAD), so the guard preserves real findings as claimed.
- **Verdict:** CONFIRMED. Note the deliberate recall cost: the retarget never checks that the third
  segment is a registered verb, so `plan-marshall:manage-execution-manifest:classify` (a `[STATUS]`
  label, not an `add_parser` entry) resolves — the report discloses this as F‑1, and I reproduced it
  at `manage-execution-manifest/standards/decision-rules.md:365`.

### D3 — canonical command references are no longer script notation

- **Required (plan):** a build-command reference produces no finding.
- **Found:** `CANONICAL_COMMAND_PREFIXES: tuple[str, ...] = ('default:verify:', 'verify:')` at
  `_dep_detection.py:169`; the named authority `_CANONICAL_VERIFY_PREFIXES` at
  `plan-marshall/skills/manage-config/scripts/_cmd_quality_phases.py:68` holds the identical pair, so
  the R‑5 fix landed.
- **Checks run:** mutating `_is_canonical_command` turns 3 tests red. No test anywhere references
  `CANONICAL_COMMAND_PREFIXES`, so the documented mirror can drift silently (G10).
- **Verdict:** CONFIRMED.

### D4 — re-baseline and report the real unresolved set

- **Required (plan):** the post-fix set is published with its population; genuine breakage fixed or
  filed.
- **Checks run:** at the merge commit the validator reports `306 / 5058 / 4996 / 62 / 294`. The
  report publishes `306 / 5027 / 4965 / 62 / 294`. Unresolved, components and cycles match exactly;
  the two totals sit a constant 31 edges below mine on **both** the baseline and the re-baseline,
  which is corpus drift (main moved under the branch before the squash-merge), and the *deltas* the
  report states reproduce exactly: resolved +44, dependencies −274.
  Splitting the 62 rows by whether the first segment names an indexed bundle gives **35 / 27**,
  the report's split. The Filed table's per-finding counts reproduce row-for-row: `extension_base`
  11, plugin-doctor `validate`/`fix`/`analyze` 6+4+3 = 13, bucket-B 2, `tools-integration-ci` 2,
  `manage_findings` 1, six one-offs — 35 in total (R‑16's missing 35th row is present).
  The 10 fixed rows are verified: no occurrence of
  `plan-marshall:workflow-integration-git:merge_lock`, `plan-marshall:manage-task:manage-task` or
  `plan-marshall:plan-marshall:ref-workflow-architecture` survives anywhere outside this plan's own
  report, and `plan-marshall:manage-locks:merge_lock` names a real script
  (`manage-locks/scripts/merge_lock.py`).
- **Verdict:** CONFIRMED.

### D5 — precision regression test

- **Required (plan):** a fixture with one instance of each false-positive class plus one genuinely
  broken reference, asserting **exactly one** finding — not "at least one".
- **Found:** `_build_precision_graph` at `test_resolve_dependencies.py:1240-1269` (7 excluded
  instances + 1 ghost script) and `TestPrecisionRegressionFixture:1282-1306`, whose first assertion
  is `result['unresolved_count'] == 1` and whose second names the surviving row.
- **Checks run (mutation, each run on the single test file, source restored from a byte snapshot):**

  | Mutation | `test_exactly_one_finding` | Other reds |
  |---|---|---|
  | placeholder guard → False | RED | 5 |
  | canonical guard → False | RED | 1 |
  | decision-log guard → False | RED | 2 |
  | embedded `.`/`:` **prefix** arm off | RED | 2 |
  | embedded `/` **suffix** arm off | RED | 2 |
  | embedded `.`+word arm off | RED | 1 |
  | subcommand retarget → None | RED | 5 |
  | misspelling guard off | green | 1 (`TestMisspelledScriptSegmentIsNotASubcommand`) |
  | verb-bearing gate → always | green | 2 (`TestOnlyVerbBearingShapesRetarget`) |

  Both embedded sub-arms bite separately, so R‑13's fix is real. Rebuilding the shipped fixture with
  all four arms disabled yields **7** unresolved rows, not the 6 the report quotes.
- **Verdict:** CONFIRMED (the assertion is exact and non-vacuous for every documented class).

### D6 — documentation

- **Required (plan):** what it detects, what it deliberately does not treat as a reference, whether
  the output is gate-grade; and if it becomes a gate, the quality-gates page must say so.
- **Found:** `SKILL.md:156-164` (Dependency Types — what it detects), `:182-204` ("What counts as a
  reference", five families with example and reason, the conditional-exclusion contract, the
  subcommand resolution and its two bounds, and the pre-existing fail-open drops), `:206-215`
  ("Precision of `validate`", the two limits, and the explicit "fail-closed report, not a
  zero-tolerance gate" instruction).
- **Checks run:** `doc/developer/build.adoc` contains no mention of `resolve-dependencies` or this
  validator, so the conditional non-edit leaves nothing false — the reasoned non-edit holds. The
  "9 resolvable notations sit unseen behind the comment-line skip" claim re-derives exactly: I
  measured 9 resolvable and 7 non-resolvable notations on skipped comment lines, and none of the 7 is
  genuinely broken, so "no genuinely-broken reference hides there today" also holds.
- **Verdict:** PARTIAL — two claims in the new text do not survive checking; see G3 and G4.

## Correctness review

I read `_dep_detection.py` and `_dep_index.py` in full, and probed the shipped behaviour with
synthetic bundles. The mechanism is sound: the index checks `dep.target.to_notation() not in
index.components` **before** any exclusion logic (`_dep_index.py:547`), so an excluded shape naming a
real component is always kept as an ordinary edge; self-edges are suppressed (`:562-567`); the import
guard (`:502-508`) keeps `PYTHON_IMPORT` targets out of the retarget. Independent regression evidence
at HEAD, running the pre-change detector and the shipped detector over the same corpus:

```
old resolved 4983 / unresolved 377      new resolved 5020 / unresolved 61
LOST (resolved before, absent now): 0   GAINED: 37
old cycles 296, new cycles 296, cycles only in new: 0
```

So the report's zero-loss claim and its "cycle set byte-identical" claim both hold at HEAD, not just
at merge time.

Two defects remain, both about what the gate can no longer see:

1. **A genuinely-broken reference wearing an excluded shape is still dropped silently**
   (`_dep_index.py:569-572`). The exclusion is conditional on the target *existing*, so it protects
   valid references only; a broken one is exactly the case that names no component. Probed on a
   synthetic bundle (each line cites a script that does not exist):

   | Line | Reported? |
   |---|---|
   | `Run probe-bundle:caller:ghost-script now.` (control) | yes — unresolved |
   | `Run probe-bundle:real-skill:ghost-script.py now.` | **no row at all** |
   | `Emitted (probe-bundle:caller:ghost-script) here.` | **no row at all** |
   | `Coordinate x.probe-bundle:caller:ghost-script here.` | **no row at all** |
   | `# Run probe-bundle:caller:ghost-script now.` | **no row at all** |

   This is the *stated* defect of round-2 findings 2 and 3, both marked **Fixed**. The shipped
   `SKILL.md:194` sentence — "Every exclusion in the table above is conditional, so none of them can
   hide a real reference" — is true only under the code's internal definition of "real reference"
   (one that resolves), and false under the reader's (one the gate should have flagged). See G3.

2. **Verb-registration enforcement is attributed to a rule that cannot see this shape.**
   `SKILL.md:204` says the unchecked verb registration "is enforced separately by the
   `manage-invocation-invalid` plugin-doctor rule". That rule's extractor is anchored on the executor
   prefix — `_analyze_manage_invocation.py:375` compiles `python3\s+\.plan/execute-script\.py\s+…` —
   so decision-log prefixes and prose citations, which are the entire population the retarget acts
   on, are outside it. `manage-execution-manifest:classify` is the live instance: it resolves here
   and no rule anywhere raises it. See G4.

Nothing else surfaced: no off-by-one in the arm ordering (placeholder → canonical → decision-log →
embedded, each mutually exclusive by construction of the `elif` chain at `:337-346`), no unguarded
`None` (`parent_skill` is checked at `:509` and `:465`), and `_is_misspelled_script_segment` cannot
fire on a legitimate script because a legitimate script is in `index.components` and never reaches
the retarget.

## Test adequacy

Coverage by deliverable, all in
`test/pm-plugin-development/tools-marketplace-inventory/test_resolve_dependencies.py`:

| Deliverable | Tests | Non-vacuous? |
|---|---|---|
| D1 | `TestNonReferenceColonTriples::test_{documentation,maven}_placeholder…`, `TestPlaceholderSkillReferences` | yes — mutation red |
| D2 | `TestPrecisionRegressionFixture::test_subcommand_resolves…`, `TestSubcommandResolution`, `TestMisspelledScriptSegmentIsNotASubcommand`, `TestOnlyVerbBearingShapesRetarget` | yes — mutation red |
| D3 | `TestNonReferenceColonTriples::test_canonical_verification_step…` | yes — mutation red |
| D5 | `TestPrecisionRegressionFixture` (4 cases) | yes — every one of the six guard arms independently red |
| fail-closed contract | `TestExclusionsAreConditional` (2 fail-open cases + 2 controls), `test_only_the_decision_log_shape_may_carry_a_verb` | yes |

Two shipped behaviours have **no** covering test — proven by mutation, with the whole file staying
green and the live corpus moving:

- Removing the `SCRIPT_NOTATION` restriction at `_dep_index.py:502-508` leaves all 96 tests green,
  while the corpus goes from 61 unresolved / 296 cycles to **50 unresolved / 297 cycles** — the 11
  `extension_base` findings silently resolve. That is exactly the R‑10 defect, and
  `TestRetargetAppliesToWrittenNotationOnly::test_python_import_is_not_retargeted_onto_a_same_named_entry_script`
  is the test the report cites as its regression lock. It cannot fail against it, because its probe
  bundle is named `probe-bundle` while the mapping target is `plan-marshall:ref-toon-format:…`, so
  the entry-script lookup misses on the bundle segment regardless of the guard (G1).
- Removing the self-edge skip at `_dep_index.py:562-567` also leaves all 96 tests green, while the
  corpus goes to **297 cycles** and +24 dependencies — the R‑11 defect, untested (G2).

Test-count claims: the file holds **96** test functions at both the merge commit and HEAD (the two
revisions are byte-identical for this file and directory), against 65 at the merge parent — 31 added,
0 removed. The inventory directory collects **188 passed** today on that unchanged tree.

## Report accuracy

Reproduced and true: the D0 table and every claim-table figure; the residue split and the Filed
table; the zero-loss edge diff and its 37 gains; the 33-row retarget figure; the "zero rows
attributable to this run's own docs" check (0 unresolved rows sourced from the inventory skill at
HEAD); F‑8's "8 rows under the pre-change detector" (the contract table's example triples yield
exactly 8 of the 17 rows the old detector would raise from this skill); the `manage_findings`
restoration; the ADR‑002 fixes at lines 140 and 249; the `tools-fix` test-fixture retarget
(`test_from_notation_command` now names `tools-sync-agents-file`, which exists); and `uv.lock`
untouched by the merged commit.

False, stale, or self-contradictory:

| Quoted claim | Correct value |
|---|---|
| "**30 new test functions**; the file's collected total is **95** (from 65)" | 31 new; 96 collected (measured on the identical file at HEAD) |
| "the inventory suite is **187 passed**" | 188 passed on the unchanged directory |
| "**`20075 passed, 14 skipped`**" (Build gate) vs "20076 passed / 14 skipped" (Contract check § Step 5) | the two contradict each other; the absolute figure is UNVERIFIABLE here (full suite not run) |
| "Twelve commits" (Step 4) vs F‑7 "**Fixed** — nine" vs "before each of eight commits" | the PR carries **13** commits (GitHub API, PR #1254) |
| Round‑2 findings 2 and 3 — "a genuinely-broken reference written parenthetically escaped the gate" / "`bundle:skill:script.py` was dropped" — **Fixed** | not fixed: both shapes still drop a *broken* reference silently (probe evidence above). What the provisional mechanism fixed is the adjacent case of a *valid* reference |
| "all-off gives 6, corroborating the red-before-green claim" | the shipped 7-instance fixture gives **7** with all arms disabled |
| "the retarget does not verify that a verb is registered … Both are stated in `SKILL.md`" | the non-check is stated (`:204`), but the page attributes enforcement to a rule that cannot see the shape, and never records the resulting false resolution |
| Baseline `total_dependencies: 5301` / `resolved: 4921` | not reproducible at any commit named in the report: the merge parent gives 5332 / 4952 (a constant +31 on both the baseline and the re-baseline). The deltas reproduce exactly, so this is main moving under the branch — but no measurement commit is stated, so the population cannot be pinned |

## Declared residue — current status

| Residue item (from report) | Still open? | Evidence |
|---|---|---|
| `_BUCKET_B_NOTATIONS` holds two unresolvable notations (production bug) | **Open** | `execute-task/scripts/inject_project_dir.py:39-50` still lists `plan-marshall:workflow-integration-git:git` and `plan-marshall:workflow-pr-doctor:pr-doctor`; the real scripts are `git-workflow.py` and `pr_doctor.py`, and `cwd-policy.md:68` itself uses `:git-workflow` |
| `extension_base` mapping + nested-script coverage (11 rows) | **Open** | 11 unresolved rows at HEAD for `plan-marshall:extension-api:extension_base`; `discover_components` still globs `scripts/*.py` (`_dep_index.py:290`) |
| plugin-doctor's documented `validate`/`fix`/`analyze` (13 rows) | **Open** | 6+4+3 rows at HEAD; `doctor-marketplace.py` registers `analyze`, `fix`, `report`, `quality-gate`, `list-components`, `test-conventions`, `contracts` — no `validate` |
| `tools-integration-ci` Executor Mapping `github`/`gitlab` (2 rows) | **Open** | 2 rows at HEAD |
| `manage_findings` (1 row) | **Open** | 1 row at HEAD |
| Six one-off references | **Open** | all six present at HEAD |
| The untriaged unknown-bundle rows (27) | **Open**, now 26 | one row (`pm:execute:implement-feature`) disappeared through unrelated corpus drift; nothing was partitioned or triaged |
| Five pre-existing unconditional drops (comment lines, URLs, `http`/digit segments) | **Open**, disclosed | `_dep_detection.py:316-333`; comment-line skip still hides exactly 9 resolvable notations |
| Retarget does not check verb registration (`…:classify`) | **Open**, disclosed | reproduced at `decision-rules.md:365`; `classify` is absent from `manage-execution-manifest.py`'s `add_parser` set |
| `chore/` PR for the § Step 9 contract amendment | Not found | no `uv.lock` guidance matching the proposal appears in `.claude/skills/cloud-plan-lane/SKILL.md`; the proposal remains owed to the operator |
| Sibling editor-facing plan gated on this one | Gate satisfied for in-namespace findings | `doc/plans/code-intelligence-substrate/240-skill-lsp-server/` exists and is the only doc outside this plan referencing `resolve-dependencies` |

## Out-of-scope and collateral

- **"Redesigning the detection layer" — respected.** The change is additive: four predicates, one
  enum, one retarget helper. `detect_script_notations`'s scan, the `DependencyType` set and the
  `validate` output contract are untouched.
- **"Fixing every genuinely-broken reference" — respected.** 10 unambiguous rows fixed, 35 filed
  with reasons.
- **"Building an editor-facing surface" — respected.** The merged commit touches 10 files: the two
  detector modules, the test file, `tools-marketplace-inventory/SKILL.md`, four notation-fix sites
  (`manage-logging/SKILL.md`, `manage-execution-manifest/references/invariant-check-summary.md`,
  `workflow-integration-git/SKILL.md`, ADR‑002) and the plan directory. No LSP or editor code.
- **Collateral, declared:** the ADR‑002 and cross-skill notation edits are outside the inventory
  skill but are named in the report as the D4 fixes and as round‑2 finding 6 / R‑4.

## Method and coverage

- Ran the validator live in-process (bypassing the absent `.plan/` executor) over four corpora: the
  merge parent `3d96e40^`, the merge commit `3d96e40`, and HEAD, each with both the pre-change and
  the shipped detector; instrumented `_index_dependencies_from` to capture the exclusion arm and the
  retarget decision per edge.
- Replayed the 380-row baseline through the shipped predicates row-by-row (no set de-duplication —
  a set-keyed replay silently loses duplicate rows and yields 74/69 instead of 75/68).
- Ran `uv run python -m pytest …test_resolve_dependencies.py -o addopts=""` clean (96 passed) and
  under 11 mutations, restoring both source files from byte snapshots taken beforehand
  (`md5sum` verified identical afterwards; `git status --porcelain` clean for both paths). No
  `git checkout`/`restore`/`stash` was used, and no file I did not mutate was touched.
- **Not checked (UNVERIFIABLE):** the whole-suite figure (`20075`/`20076 passed`), the `mypy`
  file counts, and the marketplace-wide `plugin-doctor total_issues: 0` — running `./pw verify` is
  out of scope for this audit, and the tree has moved since the merge, so the figures are no longer
  measurable as stated. The branch `claude/code-intelligence-validation-azwlva` no longer exists on
  any remote, so per-commit gate claims cannot be re-checked; the commit count was recovered from the
  GitHub API instead.
