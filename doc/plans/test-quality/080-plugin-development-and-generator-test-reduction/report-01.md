# Run report — 080-plugin-development-and-generator-test-reduction (run 01)

**Date (UTC):** 2026-08-19    **Branch:** `claude/plugin-dev-generator-tests-v0zvzg`    **PR:** _pending_    **Outcome:** completed

> **Verification loop exit:** _pending_

## Skills loaded

| Skill | Route |
|---|---|
| `cloud-plan-lane` | `.claude/skills/cloud-plan-lane/SKILL.md` — loaded as the first action |

The lane's Step 1 skills were **not** loaded from the plugin notation, which is absent in this cloud
session; the bundle paths were read directly where needed. The plan's surface is `test/**` only — no
production code, no `SKILL.md`, no `.adoc` — so the conditional table resolves to
`pm-dev-python:pytest-testing` as the one domain skill the work touches, and its house rules reach this
run through `doc/plans/test-quality/README.md` § House style (**B1**–**B10**), which was read in full.

## Gating checks (run before D1, all halting)

| Gate | Result |
|---|---|
| Working tree clean at start | Clean |
| Plans `010` and `020` landed | Both present — `def parse_ns` at `test/conftest.py:710`; the 400-line module budget at `persona-module-tester/standards/testing-methodology.md:75` |
| Collision matrix — parties naming `080` (`090`, `110`) | **No open PRs at all** in the repository, and `git branch -r` shows only `origin/main` and this run's branch. No in-flight sibling |
| Partition (§ "The partition, and how a run re-derives it") | **Holds.** All 68 directories and 12 root-level files under `test/plan-marshall/` appear in exactly one of `030`–`070`; every other top-level `test/` entry is `080`'s or one of the four documented exclusions. No entry in two lists, none in none |
| Plan `090` landed (partial dependency) | Landed — `doc/plans/test-quality/090-harness-and-rule-gaps/report-02.md` records `Outcome: completed` |

## Claim labels — re-derived

| Claim | Lead | Re-derived | Verdict |
|---|---|---|---|
| Slice size | ~60,400 lines / 161 modules | **60,667 / 162** | Confirmed |
| `plugin-doctor/` share | ~33,600 / 82 | **32,418 / 77** over this plan's surface — the lead counted the `test_test_conventions_rule*.py` modules this plan excludes | Confirmed once the exclusion is applied |
| `_fixtures.py` is ~1,590 lines and carries the bare basename its own rule forbids | ~1,590 | **1,590**, and the `unique-fixture-basenames` sweep over `test/` reported exactly **1** finding — this file | Confirmed |
| It is the only `unique-fixture-basenames` finding tree-wide | HYPOTHESIS | `unique-fixture-basenames,1` whole-tree, that one file | **Confirmed** |
| **3 of 57 `test_analyze_*.py` import `assert_analyzer_findings`** (gating for D1) | ~3 of 57 | **exactly 3 of 57** | **Confirmed — D1 sized as the plan states, no restatement needed** |
| No module outside `plugin-doctor/` imports `_fixtures` by bare name | HYPOTHESIS | 5 real importers, all inside `plugin-doctor/`. The three other hits are a prose mention in an unrelated helper and two synthetic `_fixtures.py` strings written into scratch trees by plan `010`'s rule tests — not imports | **Confirmed**; blast radius is 5 files |
| ~222 `Namespace(` against zero `parse_ns` | ~222 / 0 | **222 / 0** | Confirmed exactly |
| Plan `090` published a parser seam for every module a conversion would block on | HYPOTHESIS | **Every script probed has a working seam** — see D3 below | **Confirmed, and no site is seam-blocked** |
| Over-budget count | 42, plus a 43rd that is plan `010`'s | **42** in this plan's surface; the doctor reports **43** over the same directories, the extra being `test_test_conventions_rule6.py` | Confirmed, including the split |
| `parse_frontmatter` tested with ~8 hand-picked strings | ~8 | **exactly 8** test functions in `TestParseFrontmatter` | Confirmed |

## Deliverables

| # | Deliverable | State | Commits |
|---|---|---|---|
| D1 | Rename the shared fixture module and make the scaffold the norm | **Done** (conversion partial by design — see below) | `e795c8f`, `fa84cc1`, `c7547c2` |
| D2 | Preserve the suite-coverage meta-test through every move | **Done** | verified against `e795c8f` |
| D3 | Normalise preambles, argument construction, strip history from prose | **Partial** — **B7** and **B3** effectively complete, **B6** at 83% | `4535d7c`, `d500440`, `bd07cec`, `21ae459` |
| D4 | Derive the property-based-testing candidate list | **Done** — table below | this report |
| D5 | Report the measured deltas | **Done** | this report |

### D1 — rename plus conversion

The rename is `_fixtures.py` → `_plugin_doctor_fixtures.py`, with all **5** real importers updated. Six
prose sites named the module by its old path and were corrected with it, including the remediation
message inside `test_zero_match_suite_coverage.py` that points a future author at the corpus file — a
prose-bearing string literal, the consumer kind a documentation sweep does not open and a code sweep
does not read.

**The conversion is the deliverable, and it moved from 3 modules to 51.**

| Measure | Before | After |
|---|---|---|
| `test_analyze_*.py` modules asserting through the scaffold | **3 of 57** | **51 of 57** |
| `assert_analyzer_findings` call sites | 20 | **618** (598 converted by this run) |

**The strengthening was proved by mutation, not asserted.** The claim D1 rests on is that
`assert len(findings) == N` passes when the *wrong* rule fires N times, while the scaffold's multiset
comparison does not. With `_analyze_lesson_id_in_skill_prose.py` mutated to emit `some-other-rule` at
its four finding sites:

* the converted assertion **failed** — `analyzer emitted rule codes ['some-other-rule',
  'some-other-rule'], expected ['no-lesson-id-in-skill-prose', 'no-lesson-id-in-skill-prose']`;
* the original assertion **would have passed** — the finding count was still exactly 2, confirmed by
  running the analyzer directly against the same fixture.

27 tests in that module went red under the mutation. The analyzer was restored from a snapshot taken
before the mutation and `git status` confirmed clean afterwards; no `marketplace/bundles/**` change is
in the diff.

**The six unconverted modules, each with its reason** — none is an omission:

| Module | Why it cannot use the scaffold |
|---|---|
| `test_analyze_resolver_matrix_coverage.py` | Its analyzer takes **two** arguments (`marketplace_root, project_root`); the scaffold's signature passes exactly one fixture |
| `test_analyze_argument_naming_workflow_scope.py` | Filters findings by rule and asserts on the **subset**; the scaffold asserts the FULL multiset, so converting would change what is asserted |
| `test_analyze_file_bloat_ack.py` | Calls `analyze_subdocuments`, which returns results rather than a findings list |
| `test_analyze_coverage.py`, `test_analyze_shared.py` | No direct analyzer call at all — different test shape |
| `test_analyze_crossfile.py` | Verifier-echo test; its findings come from `verify_findings` on a crafted claim, not from running an analyzer over a fixture |

**Plan `010`'s four corpus entries still fire after the rename**, each verified individually:
`test-module-line-budget`, `test-helper-module-misnamed`, `test-module-preamble-boilerplate` and
`test-docstring-historical-prose` each return their own rule id from `_run_spec`.

**Count remaining, stated rather than implied:** 6 modules unconverted, all six characterised above;
within the 51 converted modules, 115 `assert len(...) == N` lines remain that are not
analyzer-result counts (list lengths, dictionary sizes, and payload-field counts the scaffold does not
address).

### D2 — the suite-coverage contract

| Set | Before | After |
|---|---|---|
| `registered_rule_ids(MARKETPLACE_ROOT)` | 72 | **72** |
| `fired_rule_ids()` | 116 | **116** |
| `EXEMPT_RULE_IDS` | 4 | **4 — not grown** |
| `registered − fired − exempt` | ∅ | **∅** |
| `FIXTURE_CORPUS` entries | 92 | **92** |

The strongest evidence that the exempt set could not have grown is structural rather than numeric:
`git diff -M origin/main...HEAD` reports the fixture module as `{_fixtures.py => _plugin_doctor_fixtures.py} | 0`
— **zero content lines changed**. It is a pure rename, so neither `EXEMPT_RULE_IDS` nor any corpus entry
was touched at all. The `_EXTRA_FIRED` registry and its recording test (`test_analyze_crossfile.py`)
remain in the same import path; `fired_rule_ids()` is unchanged at 116.

### D3 — preambles, argument construction, prose

**B7 — one import preamble.** 44 deep `Path(__file__)` parent chains and 7 skill-root
`spec_from_file_location` preambles replaced.

Every chain was **evaluated against the module's own real path and shown to equal the constant that
replaced it** before being rewritten; the depth was never inferred from the shape of the chain. That
matters here specifically: a directory-counting chain is an environment-derived claim, true only from
the depth it was written at, and the rule exists because such a chain breaks silently when the module
moves.

**One premise in the epic brief is stale, and this run acted on the tree rather than on the document.**
`doc/plans/test-quality/README.md` § "The partition" and this plan's Expected surface both record
`test/pm-code-intelligence/`'s preamble finding as *not fixable here* — the reasoning being that the
module loads a bundle skill's root-level `extension.py`, which `conftest.load_script_module` cannot
address, so the remedy the rule's message names does not apply, and the finding belongs to plan `090`
§ D2. **Plan `090` has since landed `conftest.load_skill_module`** (`test/conftest.py:484`), whose own
docstring names this exact shape: *"The shape this exists for is a bundle's `plan-marshall-plugin`
skill, whose `extension.py` sits at the skill root."* The remedy therefore exists, and 7 such preambles
— `test/pm-code-intelligence/`'s among them — were fixed rather than deferred. The plan's instruction
to *"check by reading whether the modules publish a builder — do not assume from the calendar"* is what
produced this; the same discipline applied to the sibling claim.

| `test-module-preamble-boilerplate` across the slice | Before | After |
|---|---|---|
| findings | **59** | **9** |

The 9 remaining are all one shape — `spec_from_file_location` over a path that is **not** a skill file
(`marketplace/targets/generate.py`), or a per-bundle extension loader whose surrounding structure
differs enough that a mechanical rewrite was not safe. They are residue, not blockers.

**B6 — argument namespaces from the real parser.**

| Measure | Before | After |
|---|---|---|
| hand-built `Namespace(` sites | **222** | **38** |
| sites converted | — | **184 (83%)** |
| `parse_ns` template calls | 0 | **25** |

Each converted module gains one `parse_ns` template per subcommand, **parsed once at module scope**,
plus a small `_ns(template, **overrides)` helper — the plan's explicit hazard is that `parse_ns`
re-executes the script module on every call, so no template is built per test or per assertion. The
converted `test_analyze.py` runs its 106 tests in 1.8 s.

Two shapes needed more than a kwarg-set match, and both are recorded because getting either wrong
would have silently weakened the result:

* **`_fix.py`'s `extract` and `categorize` both take only `--input`.** Matching on the kwarg set alone
  would have folded both onto whichever template it hit first; the single `extract` site was marked
  before conversion and given its own template.
* **`asciidoc.py`'s `validate`/`format` share `(command, path)` and `verify-links`/`classify-links`
  share `(command, file)`.** Those sites are keyed on their own `command=` literal instead. Every
  template was then checked to pair only with its own command value.

`command=` is **dropped** from every overlay rather than restated, because the template already carries
the parser's own value — restating it is precisely the hand-built claim the deliverable removes.

**The `parse_ns` exception list is empty by finding, not by non-attempt.** The epic README warns that an
empty exception list produced by not running the sweep *"tells the operator nothing"*. Every script
behind a remaining site was probed:

| Script | Seam |
|---|---|
| `pm-plugin-development:plugin-doctor:_analyze.py` | **OK** — `{markdown,structure,coverage,cross-file}` |
| `pm-plugin-development:plugin-doctor:_fix.py` | **OK** — `{extract,categorize,apply,verify}` |
| `pm-plugin-development:plugin-doctor:_validate.py` | **OK** — `{references,cross-file,inventory,extension}` |
| `pm-plugin-development:plugin-doctor:doctor-marketplace.py` | **OK** — 7 subcommands |
| `pm-plugin-development:plugin-maintain:maintain.py` | **OK** — `{update,check-duplication,analyze,readme}` |
| `pm-plugin-development:plugin-create:component.py` | **OK** — `{generate,validate}` |
| `pm-documents:ref-asciidoc:asciidoc.py` | **OK** — 5 subcommands |
| `pm-documents:manage-interface:manage-interface.py` | **OK** — 6 subcommands |
| `pm-dev-java:manage-maven-profiles:profiles.py` | **OK** — `{list,unmatched,classify,suggest}` |
| `pm-documents:ref-documentation:docs.py` | **OK** — `{review,analyze-tone}` |
| `pm-dev-frontend:javascript:jsdoc.py` | **OK** — `{analyze}` |

**Zero sites are blocked on a missing parser seam.** The 38 remaining are unconverted for run budget
alone, and are listed under Residue. All templates are hoisted; **none** is per-assertion.

**B3 — docstrings state the invariant, not its history.**

| `test-docstring-historical-prose` across the slice | Before | After |
|---|---|---|
| findings | **49** | **4** |

45 citations were removed across 16 modules — plan and deliverable ids, PR numbers, lesson ids, commit
SHAs, and superseded-behaviour narration. The rationale each docstring carries survives; only the record
of *how* the contract was discovered goes. Where a citation was doing real work the work was kept in
present tense: *"Regression for PR #499 review fc4fa4: the old string heuristic required the line to
contain `def `, `):`, or `,`"* became a statement that detection is structural **because** a line-shape
heuristic cannot see a parameter sitting alone on its own line.

**The four survivors, each characterised per the plan's done-when:**

| Module | Line | Matched | Case |
|---|---|---|---|
| `plugin-doctor/test_test_conventions_rule1.py` | 8 | `Lesson ``2026-04-29-10-001`` ` | **Out of this plan's surface** — plan `010` owns every `test_test_conventions_rule*.py` module |
| `plugin-doctor/test_test_conventions_rule3.py` | 8 | ``Lesson `2026-04-29-22-002` `` | Same — plan `010`'s |
| `pm-dev-java-cui/parse-rewrite-log/test_parse_rewrite_log.py` | 6 | `#118` | **Data, not citation** — the number identifies the **upstream** `cui-open-rewrite` issue that is the provenance of a checked-in WARN corpus, recorded alongside `fixtures/warn-corpus/PROVENANCE.md`. It names the corpus's source, not this repository's history |
| `pm-dev-java-cui/parse-rewrite-log/test_parse_rewrite_log.py` | 192 | `#118` | Same upstream provenance reference |

No finding was worked around by weakening a fixture, and no rule defect was found: every match this run
examined was genuine prose, not a fixture literal. The plan anticipated fixture-literal false positives
(owned by plan `090`); **none occurred in this slice**.

### D4 — property-based-testing candidates for the generator half

**A report deliverable; no code changed.** Derivation, stated so it is reproducible: module-level
functions under `marketplace/targets/**` and
`marketplace/bundles/pm-plugin-development/skills/tools-marketplace-inventory/scripts/**` whose names
match the universal-contract shapes plan `010` § D6 fixed (`parse*`, `validate*`, `normali[sz]e*`,
`encode`/`decode`, `serialize`/`deserialize`, `canonicalize`, `slugify`, `escape`/`unescape`, `coerce`,
`to_toon`/`from_toon`, plus `split`/`resolve`/`sanitize`/`render`), filtered to those a test in this
slice actually exercises. Example-row counts are test functions that call the unit, with a parametrized
case counted per row.

**Result: 9 candidates across 7 production modules, 47 hand-picked example rows.**

| Unit | Production module | Module testing it today | Example rows | Property that would be asserted |
|---|---|---|---|---:|
| `parse_frontmatter` | `targets/opencode/frontmatter.py`, `targets/claude/variant_emitter.py` | `opencode/test_frontmatter.py`, `opencode/test_variant_emitter.py`, `claude/test_variant_emission.py` | **25** | For any frontmatter block, parse-then-re-serialise round-trips; no value containing the `---` fence delimiter truncates the block; an unterminated fence never yields a partial mapping |
| `parse_pack_selection` | `targets/pr_agent/target.py` | `pr_agent/test_pr_agent_target.py` | 6 | For any selection string, the parsed pack set is a subset of the declared packs and is order-insensitive |
| `render_variant` | `targets/claude/variant_emitter.py` | `claude/test_variant_emission.py` | 6 | For any variant input, rendering is idempotent and emits no unresolved placeholder |
| `parse_dep_types` | `tools-marketplace-inventory/scripts/resolve-dependencies.py` | `tools-marketplace-inventory/test_resolve_dependencies.py` | 2 | For any comma-separated type list, parsing yields only registry-declared types, and an unknown token is rejected rather than silently dropped |
| `serialize_output` | `tools-marketplace-inventory/scripts/resolve-dependencies.py` | `tools-marketplace-inventory/test_resolve_dependencies.py` | 2 | For any result structure, serialising then re-parsing preserves the dependency set — a genuine round-trip pair with `parse_dep_types` |
| `_resolve_md_components` | `targets/opencode/emitter.py` | `opencode/test_emitter.py` | 2 | For any component tree, resolution is total: every declared component resolves or is reported, never dropped |
| `_resolve_skill_dirs` | `targets/opencode/emitter.py` | `opencode/test_emitter.py` | 2 | For any bundle layout, the resolved skill-dir set equals the on-disk set |
| `render_variant_frontmatter` | `targets/opencode/variant_emitter.py` | `opencode/test_variant_emitter.py` | 1 | For any frontmatter mapping, rendering then `parse_frontmatter` round-trips |
| `_resolve_version` | `targets/generate.py` | `targets/test_dist_manifest.py` | 1 | For any version-bearing path, resolution is monotone and total over the declared version shapes |

**Relationship to plan `010`'s whole-tree list**, as the plan requires it be stated. Plan `010` § D6
Proposal 1 derived **107 functions across 53 modules** tree-wide, with the column set *call site /
contract kind*. This table refines that list to the generator half and adds the two columns this plan
asks for (the module testing it today, and the example-row count).

* **Refines `010`'s rows:** `parse_frontmatter` — `010` names both the `opencode` and `claude`
  implementations under "Frontmatter parsers"; this run confirms both and measures 25 example rows.
* **New, not in `010`'s named subset:** `parse_pack_selection`, `render_variant`,
  `render_variant_frontmatter`, `parse_dep_types`, `serialize_output`, `_resolve_md_components`,
  `_resolve_skill_dirs`, `_resolve_version`. `010`'s highest-value subset table named no
  `tools-marketplace-inventory` or `pr_agent` call site, so all eight are additions to the named set
  rather than contradictions of the 107-function superset.
* **`010`'s strongest candidate is not in this slice.** The `toon_parser` `parse_toon`/`serialize_toon`
  encode/decode pair lives under `plan-marshall`, which is plan `060`'s surface, not this one. The
  strongest pair *here* is `parse_dep_types`/`serialize_output`.

⚠️ **`parse_frontmatter` remains the worked case and the best first target**: 25 example rows against a
contract that is genuinely universal, and its 8 dedicated cases in `TestParseFrontmatter` are an
enumeration of the shapes the author thought of — unterminated fences, an embedded `---`, list
flattening, a missing trailing newline. That enumeration is the weakness a property closes.

**Adding `hypothesis` is out of scope and remains a standing proposal** (plan `010` § D6 Proposal 1); it
is a third-party dependency and a user-approval step, and no operator is present. This run produces
evidence only.

### D5 — measured deltas

**Line counts.** Population: the 162 `test_*.py` modules in this plan's Expected surface, excluding the
`test_test_conventions_rule*.py` glob. Command: `wc -l $(...)`.

| | Before | After | Delta |
|---|---:|---:|---:|
| Slice total | **60,667** | **60,085** | **−582 (−0.96 %)** |

Per the epic's § "Why there is no line floor", this is **reported, not targeted**. The retired 25 %
floor would have demanded ~15,100 lines against a slice whose entire comment-and-docstring volume is
~13,400. No assertion, rationale, or comment was deleted to move this number: the reduction is
`assert len(...)` / `assert x['rule_id'] == ...` pairs collapsing into one scaffold call, and
`spec_from_file_location` preambles collapsing into one accessor call.

**The five conditions the epic requires of every reduction run.**

| # | Condition | Before | After | Verdict |
|---|---|---|---|---|
| 1 | Collected test count does not decrease | **3,404 passed** | **3,404 passed** | **Holds** — unchanged |
| 2 | Coverage does not decrease | 85 % (17,219 stmts, 2,229 missed → **14,990 covered**) | 85 % (17,340 stmts, 2,203 missed → **15,137 covered**) | **Holds** — +147 covered statements |
| 3 | Skipped count does not rise | **13 skipped** | **13 skipped** | **Holds** — unchanged |
| 4 | The suite does not get slower | **252.84 s** | **202.41 s** | **Holds** — 20 % faster |
| 5 | Line delta measured and reported | — | **−582** | Reported above |

**Populations, named.** Conditions 1, 3 and 4 were measured with the **same command and the same scope**
on both sides: `uv run python -m pytest {the slice's 14 directories + 2 root modules} -q -o addopts=""`,
run on this machine, against `origin/main` in a throwaway git worktree for the "before" and against
this branch for the "after". This is a `pytest` wall-clock and is **not** comparable to a `./pw verify`
total, which also runs the quality gate and the test-compile step.

The **3,404** figure counts the slice's directories, which include plan `010`'s
`test_test_conventions_rule*.py` modules; the separate **3,357** collected-item figure counts this
plan's Expected-surface *file list*, which excludes them. Both are unchanged before and after; they are
different populations and are not interchangeable.

Condition 2 was measured with `--cov=marketplace/targets --cov=marketplace/bundles/pm-plugin-development
--cov=marketplace/bundles/pm-documents` over the 10 bundle-test directories the slice exercises,
`-p no:randomly` on both sides. The statement total rises (17,219 → 17,340) because the `parse_ns`
conversion **imports more production code** — the scripts' own parsers — bringing previously unmeasured
modules into the measured set. Coverage did not decrease on either reading.

**The fifth check, which outranks the four above: the doctor must still catch what it caught.** The
whole-tree rule-firing sweep (`doctor-marketplace.py quality-gate`, through the README's exact
`PYTHONPATH` invocation) was captured before the first commit and again after the last:

```text
diff /tmp/doctor-before.txt /tmp/doctor-after.txt  →  IDENTICAL
```

**36 rules run, 0 findings, byte-identical output on both sides.** The rule-id sets match exactly. The
five-directory `PYTHONPATH` prefix in the README ran as documented — no sixth directory was needed, so
the next run inherits it unchanged.

**Order-independence (Verification condition 4).** The slice was run in default directory order and
again with its directories **reversed**: `3,404 passed, 13 skipped` both times, 202.41 s and 203.91 s.
D1's rename and D3's conversions both change `sys.modules` registrations, which is the mechanism plan
`060` found a live order-dependent failure in; none appeared here. Every `parse_ns` template is built
with `register=False`, so building a namespace cannot displace a registration another module imports
plainly.

**Per-rule `test-conventions` counts across the slice.**

| Rule | Before | After |
|---|---:|---:|
| `unique-fixture-basenames` | **1** | **0** |
| `subprocess-pythonpath` | 6 | 6 |
| `identifier-validator-corpus` | 0 | 0 |
| `test-module-line-budget` | 43 | 43 |
| `test-helper-module-misnamed` | 0 | 0 |
| `test-module-preamble-boilerplate` | **59** | **9** |
| `test-docstring-historical-prose` | **49** | **4** |

`test-module-line-budget` is **reported and not acted on**, per this plan's Out of scope: plan `100`
owns the budget campaign. The 43 splits as **42** modules in this plan's surface plus
`test_test_conventions_rule6.py`, which is plan `010`'s and plan `100` run 7's — exactly the split the
plan states. `subprocess-pythonpath` is not a deliverable of this plan and was not touched.

## Findings

_Pending — the verification round is in flight._

## Reviewer participation

_Pending._

## Cost

* **Tokens:** not available to the agent in this session.
* **Wall-clock:** not separately instrumented; the run's measured build and suite time is reported
  above (two full baseline suites, two coverage runs, and repeated `./pw quality-gate` calls dominate).
* **Population:** this single Claude Code cloud session. ⛔ **Not comparable** to a plan-marshall
  `metrics.toon` total, which counts an orchestrator-plus-agent dispatch tree under plan-marshall's own
  per-task billing boundary — a boundary an interactive cloud session does not share.

## Contract check (Step 9)

_Pending._

## What have we learned (Step 9)

_Pending._

## Residue

_Pending._
