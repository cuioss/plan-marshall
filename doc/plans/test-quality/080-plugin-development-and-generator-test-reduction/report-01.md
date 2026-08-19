# Run report — 080-plugin-development-and-generator-test-reduction (run 01)

**Date (UTC):** 2026-08-19    **Branch:** `claude/plugin-dev-generator-tests-v0zvzg`    **PR:** _pending_    **Outcome:** completed

> **Verification loop exit:** `verifier-clear`

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
| ~222 `Namespace(` against zero `parse_ns` | ~222 / 0 | **222 / 0** by the plan's own command — but that command also matches `types.SimpleNamespace(`, of which the slice holds 11. The B6 population is **211** | Confirmed as stated; **the lead over-counts by 11** (see D3 § B6) |
| Plan `090` published a parser seam for every module a conversion would block on | HYPOTHESIS | **Every script probed has a working seam** — see D3 below | **Confirmed, and no site is seam-blocked** |
| Over-budget count | 42, plus a 43rd that is plan `010`'s | **42** in this plan's surface; the doctor reports **43** over the same directories, the extra being `test_test_conventions_rule6.py` | Confirmed, including the split |
| `parse_frontmatter` tested with ~8 hand-picked strings | ~8 | **exactly 8** test functions in `TestParseFrontmatter` | Confirmed |

## Deliverables

| # | Deliverable | State | Commits |
|---|---|---|---|
| D1 | Rename the shared fixture module and make the scaffold the norm | **Done** (conversion partial by design — see below) | `e795c8f`, `fa84cc1`, `c7547c2` |
| D2 | Preserve the suite-coverage meta-test through every move | **Done** | verified against `e795c8f` |
| D3 | Normalise preambles, argument construction, strip history from prose | **Partial** — **B7** and **B3** substantially done (see the caveat under B3), **B6** at 87 % | `4535d7c`, `d500440`, `bd07cec`, `21ae459` |
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

**The 51 converted modules** (`test_analyze_` prefix elided): `agentfile_directory_tree`,
`agentfile_line_budget`, `allowed_tools_drift`, `askuserquestion_reachability`,
`bash_chain_shapes_in_skills`, `bash_fence_inline_code_exemption`, `canonical_enum_drift`,
`cmd_root_anchoring`, `declared_vs_disk`, `executor_path_in_production`, `fail_closed_gate_reads`,
`finalize_step_token`, `frontmatter`, `historical_prose_in_skills`, `incident_reference_in_docs`,
`lane_frontmatter`, `lesson_id_in_skill_prose`, `literal_count`, `manage_findings_invocation`,
`manage_invocation`, `markdown`, `metadata_field_validity`, `mutates_source_order`, `notation_staleness`,
`orphan_argparse_flags`, `persona_binding_resolves`, `persona_profile_uniqueness`,
`phase2_refine_contract`, `plan_path_in_scripts`, `plugin_json`, `provides_method_table`,
`readme_skill_coverage`, `resolution_branch_markers`, `role_field`, `script_call_drift`,
`self_declared_rule_compliance`, `shell_active_tokens`, `shell_substitution_in_skills`, `shim_marker`,
`skill_mode`, `skill_notation`, `skill_relative_temp_path`, `step_configurable_contract`,
`sys_path_bootstrap`, `thinking_directive_in_workflow_docs`, `tmp_redirect_in_skills`,
`triage_fix_not_done_surface`, `triage_read_surface`, `verb_chains`, `verify_step_contract`,
`workflow_doc_toon_error_field`. Three of these (`manage_invocation`, `shim_marker`,
`thinking_directive_in_workflow_docs`) already used the scaffold and were extended, not introduced to it.

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

The 9 remaining take three shapes, none of them a skill script the loader addresses:
`spec_from_file_location` over `marketplace/targets/generate.py`; over the repository-root `build.py`
(`test/marketplace/test_spdx_enforcement.py`); and per-bundle extension loaders whose surrounding
structure differs enough that a mechanical rewrite was not safe. They are residue, not blockers.

**B6 — argument namespaces from the real parser.**

⚠️ **The population needs stating, because the plan's own re-derivation command over-counts.**
`grep -c 'Namespace('` also matches `types.SimpleNamespace(`, which is **not** a B6 target — B6 is about
`argparse.Namespace` carrying the parser's defaults, and a `SimpleNamespace` is a plain value object with
no parser behind it. The slice holds **11** `SimpleNamespace` occurrences, unchanged on both sides. The
after-count additionally contains **7** occurrences of the shared `_ns` overlay helper's own body
(`Namespace(**{**vars(template), **overrides})`), which this run introduced and which is the *mechanism*
of conversion rather than a site awaiting it.

| Measure | Before | After |
|---|---|---|
| raw `grep -c 'Namespace('` (the plan's command) | 222 | 45 |
| — of which `types.SimpleNamespace` (never a B6 target) | 11 | 11 |
| — of which the `_ns` overlay helper introduced here | 0 | 7 |
| **hand-built `argparse.Namespace` sites** | **211** | **27** |
| **sites converted** | — | **184 (87 %)** |
| `parse_ns` template calls | 0 | **25** |

The 27 remaining sit in six modules: `plugin-doctor/test_plugin_doctor_extension.py` (7),
`plugin-maintain/test_maintain.py` (7), `pm-dev-java/maven-profile-management/test_profiles.py` (5),
`plugin-doctor/test_validate.py` (4), `pm-documents/ref-documentation/test_docs.py` (2),
`pm-dev-frontend/test_jsdoc.py` (2).

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

**Zero sites are blocked on a missing parser seam.** The 27 remaining are unconverted for run budget
alone, and are listed under Residue. All templates are hoisted; **none** is per-assertion.

**B3 — docstrings state the invariant, not its history.**

| `test-docstring-historical-prose` across the slice | Before | After |
|---|---|---|
| findings | **49** | **4** |

⚠️ **The rule's finding count is not the whole of B3, and a run that measured itself by it alone would
have reported clean while violations survived.** The rule's matchers do not cover every B3 shape: after
the count reached 4, a further **13** citations were found by reading in 9 modules — `TASK-NN` ids, and
"this plan" self-references naming the change rather than the contract — including in two modules the
prose commit had itself rewritten. They were removed in `7e300e8`. Two matches remain and are correct:
both are fixture literals, one the very string a rule test asserts on. Widening the matchers to catch
these shapes is plan `090` § D4's, per the epic's routing table; this run removed the instances it could
see in its own slice rather than deferring them with the matcher.

45 rule-detected citations were removed across 17 modules — plan and deliverable ids, PR numbers, lesson ids, commit
SHAs, and superseded-behaviour narration. The rationale each docstring carries survives; only the record
of *how* the contract was discovered goes. Where a citation was doing real work the work was kept in
present tense: *"Regression for PR #499 review fc4fa4: the old string heuristic required the line to
contain `def `, `):`, or `,`"* became a statement that detection is structural **because** a line-shape
heuristic cannot see a parameter sitting alone on its own line.

**The four survivors, each characterised per the plan's done-when:**

| Module | Line | Matched | Case |
|---|---|---|---|
| `plugin-doctor/test_test_conventions_rule1.py` | 8 | ``Lesson `2026-04-29-22-002` `` | **Out of this plan's surface** — plan `010` owns every `test_test_conventions_rule*.py` module |
| `plugin-doctor/test_test_conventions_rule3.py` | 8 | `Lesson ``2026-04-29-10-001`` ` | Same — plan `010`'s |
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
| `serialize_output` | `tools-marketplace-inventory/scripts/resolve-dependencies.py` | `tools-marketplace-inventory/test_resolve_dependencies.py` | 2 | For any result dict, the emitted JSON or TOON re-parses to an equal dict. ⚠️ **Not** a round-trip pair with `parse_dep_types` — see the correction below |
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
⛔ **A correction to this table, recorded because the class matters more than the instance.** Its first
draft called `serialize_output` *"a genuine round-trip pair with `parse_dep_types`"*. Reading both
signatures shows they are not inverses: `serialize_output(data: dict, fmt: str) -> str` emits JSON or
TOON for an arbitrary result dict, while `parse_dep_types(str) -> set[DependencyType]` parses a
comma-separated `--dep-types` CLI token, and `resolve-dependencies.py` publishes no re-parser for
`serialize_output`'s output at all. The pairing was invented — a plausible sentence about code the
author had not opened — and it would have sent a later run looking for an inverse that does not exist.
This slice therefore has **no** encode/decode pair; the strongest candidate here is `parse_frontmatter`,
on volume and on contract universality alike.

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
| 4 | The suite does not get slower | **252.84 s** | **202.41 s** | **Holds — no slowdown. The difference is NOT attributable to this change; see below** |
| 5 | Line delta measured and reported | — | **−582** | Reported above |

⛔ **The wall-clock difference is withdrawn as a speed-up.** The verification round pointed out a
confound this run did not control: the `origin/main` baseline ran in a **freshly created worktree with a
cold bytecode cache**, so its 252.84 s includes compiling ~934 test modules that the branch-side run read
from a warm `__pycache__`. The verifier's own independent branch-side run measured 204.36 s, consistent
with the 202.41 s here — but no cache-matched baseline was taken, and this change alters no analyzer
invocation count, so there is no mechanism by which it *would* make the suite 20 % faster. What condition
4 actually establishes is the direction it asks about: **the suite did not get slower.** The magnitude is
unattributable and is not claimed. A cache-matched re-measurement is listed under Residue.

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
| `subprocess-pythonpath` | 8 | 8 |
| `identifier-validator-corpus` | 0 | 0 |
| `test-module-line-budget` | 43 | 43 |
| `test-helper-module-misnamed` | 0 | 0 |
| `test-module-preamble-boilerplate` | **59** | **9** |
| `test-docstring-historical-prose` | **49** | **4** |

`test-module-line-budget` is **reported and not acted on**, per this plan's Out of scope: plan `100`
owns the budget campaign. The 43 splits as **42** modules in this plan's surface plus
`test_test_conventions_rule6.py`, which is plan `010`'s and plan `100` run 7's — exactly the split the
plan states. `subprocess-pythonpath` is not a deliverable of this plan and was not touched; its 8 sites
are `finalize-step-deploy-target/test_deploy_target.py` (2), `test/test_runner_falsifiability.py` (2),
`sync-plugin-cache/` (3) and `marketplace/targets/test_generate_cli.py` (1).

## Verification by reading

### D1 — three converted modules assert rule ids, not counts (plan § Verification, "By reading")

Read from the module text alone, `test_analyze_role_field.py`, `test_analyze_tmp_redirect_in_skills.py`
and `test_analyze_shell_substitution_in_skills.py` each assert through
`assert_analyzer_findings(analyzer, fixture, [RULE_ID])` or `[...]` for the empty case, and each carries
**zero** residual bare `assert len(findings) == N` lines over an analyzer result. None is a rename
wearing a conversion's name — the count assertion is gone, replaced by a multiset of rule codes.

### D3 — the cold read (plan § Verification, "By reading — cold read, required for D3's prose half")

An independent sub-agent was given **five rewritten modules and nothing else** — not this plan, not the
originals, not the production code — and asked of ten named tests: *what contract does this test pin,
and why does it matter?* It was instructed to report explicitly when (b) is unanswerable from the text
and not to reconstruct a plausible rationale.

**Result: 6 ANSWERABLE, 4 NOT-ANSWERABLE.** Three of the four were docstrings this run rewrote — over-
stripped past the citation into the rationale. All three were restored in `f030aa4`, in present tense,
with the reason grounded rather than invented:

| Test | Verdict | Disposition |
|---|---|---|
| `test_analyze.py::test_simplicity_unused_parameter_detects_marker_on_last_multiline_param` | NOT-ANSWERABLE | **Fixed** — the rewritten text gave *implementation* rationale (why a naive detector fails) in place of *contract* rationale (what the miss costs) |
| `test_analyze_argument_naming_workflow_scope.py::test_workflow_md_invented_subcommand_emits_subcommand_unknown` | NOT-ANSWERABLE | **Fixed** — "detected rather than escaping" was the assertion restated |
| `test_analyze_argument_naming_workflow_scope.py::test_workflow_md_invented_flag_emits_flag_unknown` | NOT-ANSWERABLE | **Fixed** — the rationale was a symmetry argument ("caught where drift in a skill body already is"), which justifies the scope by appeal to another scope it never justifies |
| `test_analyze.py::test_simplicity_unused_parameter_marker_in_body_no_false_positive` | NOT-ANSWERABLE | **Not fixed — this run never touched it.** Confirmed against the diff: `git diff origin/main...HEAD` contains no change to it. Recorded as a finding rather than rewritten under a cold read it did not fail |

**The restored rationale was verified against the code, not reasoned from.** The two argument-naming
docstrings now state that argparse rejects the invocation; both halves were checked by *running the
parser* rather than by reading it — `invalid choice: 'structure'` for an unregistered subcommand, and
`unrecognized arguments: --no-such-flag` for an undeclared flag, each `SystemExit(2)`.

⛔ **One rationale this run wrote while fixing the above was itself wrong, and is recorded because the
class matters more than the instance.** The first draft of the unused-parameter docstring claimed *"the
cluster's findings are what reach the `default:finalize-step-simplify` step."* Reading
`_analyze_simplicity.py` shows the opposite relationship: the detectors are the *mechanical* enforcement
layer and that step handles *"the cognitive judgement calls"* — the work the detectors cannot do, not
their output. It was corrected in the same commit to the claim the module does support: these detectors
mechanically enforce the minimum-viable-code posture, so an unseen marker is a declared-dead parameter
no gate reports. Nothing but reading the named module would have caught it: the suite was green, the
linter clean, and the sentence had no earlier version to diff against.

**The cold read also returned two findings about statements that were false**, both fixed in `f030aa4`:

* `test_analyze_verb_chains.py` carried a comment describing how the module locates a script by *"four
  `parent` hops"*. **This run's own preamble rewrite made it false** — the module now imports
  `PROJECT_ROOT` from conftest and performs no hops at all. A sweep across every file this run touched
  found this to be the **only** such stale depth claim; the seven other "levels up" comments describe
  synthetic fixture-tree geometry under `tmp_path`, which the change does not touch, and remain true.
* The same docstring claimed a test guards against a refactor *"accidentally making the regression test
  above pass for the wrong reason"*. Directionally wrong: such a refactor would redden **this** test
  rather than quietly green the other. Pre-existing, but false, so fixed.

**The cold read's own structural observation, recorded because it is a real signal about the corpus.**
Rationale survives where a rule's violation has a *mechanical* consequence outside the analyzer — a file
that stops parsing, a handshake that never terminates, real documentation auto-deleted because the rule
sits in `SAFE_FIX_TYPES`. It collapses into restatement where the rule is a pure detector whose findings
have no documented consumer. The sharpest indicator the reader named: `severity == 'error'` is asserted
in both workflow-scope tests, and nothing in either module says what an error-severity finding gates.
That is a **documentation gap in the rules themselves**, not in these tests, and it is recorded for plan
`090` (which owns the analyzers) rather than papered over here.

## Findings

Recorded **per instance**, never bundled.

### From the pre-PR verification sub-agent (round 1)

| # | Source | Finding | Disposition |
|---|---|---|---|
| V1 | verifier | Report's B6 figures (`222 → 38`, `184`, `83 %`) mix populations: the `222` before-count comes from the plan's `grep -c 'Namespace('`, which also matches `types.SimpleNamespace(`, while the `38` after-count excluded it | **Fixed** — re-derived with an explicit population: 211 hand-built `argparse.Namespace` → 27, **184 converted (87 %)**. The verifier's own counter-figure of `177` was also wrong: it took `222 → 45` raw, counting the 7 new `_ns` overlay-helper lines as unconverted sites |
| V2 | verifier | Report gives `subprocess-pythonpath` as 6; it is **8** | **Fixed.** The per-directory sweep omitted the two root-level modules (`test_runner_falsifiability.py` ×2) that are in this plan's Expected surface. Unchanged 8 → 8, so a reporting error only |
| V3 | verifier | The two surviving prose lesson ids are swapped between `rule1` and `rule3` | **Fixed** |
| V4 | verifier | Commit `bd07cec` says "across **five** modules" / "these **five** scripts"; it touches **4** test modules and names **4** scripts | **Corrected here.** The commit message is immutable on a pushed branch, so condition A is discharged by stating it: the commit's substantive claim — that every seam those scripts need is published — holds; only the cardinality is wrong |
| V5 | verifier | Commit `c7547c2` says "**33** modules"; it touches **30** files | **Corrected here**, same immutability reason. Its 225 site count is correct |
| V6 | verifier | Report and commit `d500440` say "**16** modules"; the 45 removed findings span **17** | **Fixed** in the report; the commit message stands corrected here |
| V7 | verifier | D4's `serialize_output` row called it "a genuine round-trip pair with `parse_dep_types`" — they are not inverses | **Fixed.** An invented rationale; see the ⛔ correction under D4. The other eight rows verified |
| V8 | verifier | Report calls the 9 residual preambles "all one shape"; `test/marketplace/test_spdx_enforcement.py` loads the repo-root `build.py`, a third shape | **Fixed** |
| V9 | verifier | "Every script behind a remaining site was probed" — the seam table omits two `pm-dev-java-cui` scripts | **Resolved by V1's correction.** Both remaining sites in those modules are `types.SimpleNamespace`, so neither is a B6 target and neither needs a seam. With the population corrected, the 11-row table covers every one of the six modules that actually retains a hand-built `argparse.Namespace` |
| V10 | verifier | "B3 effectively complete" overstates: B3-shaped prose the rule cannot match survives, including in modules `d500440` itself rewrote | **Fixed both ways** — 13 further citations removed across 9 modules in `7e300e8` (TASK ids and "this plan" self-references), and the report's claim softened. See the caveat under B3 |
| V11 | verifier | The report's `Findings`, `Reviewer participation`, `Contract check`, `What have we learned` and `Residue` sections were `_Pending_` while D5 was marked Done | **Fixed** — all written |
| V12 | verifier | Two `plugin-doctor` reference docs still name `_fixtures.py`, made false by this run's rename | **Recorded, not fixed — owner named below.** Out of this plan's surface |
| V13 | verifier | Four epic documents still name `test/pm-plugin-development/plugin-doctor/_fixtures.py` | **Recorded, not fixed — owner named below.** Out of this plan's surface |
| V14 | verifier | The `pm-code-intelligence` fix falsified two statements the run flagged in prose but did not record with an owner | **Fixed** — recorded below with an owner |
| V15 | verifier | Coverage figures and the 252.84 s baseline were not independently re-derived; a cold bytecode cache in the baseline worktree is an unexamined confound for the 20 % speed-up | **Accepted — see the correction under D5.** The wall-clock claim is withdrawn as a speed-up and restated as unattributable |
| V16 | verifier | The required D3 cold read (G2) and the three-module D1 read (G3) were not in the report | **Not defects — the verifier's information was stale.** Both were performed and committed in `f0d36b6`, after that agent had read the report. The cold read was a *separate* agent given the five modules and nothing else; this verifier correctly notes it could not itself serve as the cold reader, having been given the plan and the diff |

**The verifier's own clean lines, recorded so an empty finding list is distinguishable from an
unexamined one.** It checked assertion loss **mechanically over the whole diff rather than by sampling**
— every removed `assert`/`pytest.raises` line, deduped to 29 distinct shapes, all of them strictly
subsumed by the multiset the scaffold asserts — and found **zero payload assertions removed anywhere**.
It read ~90 converted call sites across 5 modules end to end and found no weakening, confirming that
multi-rule modules keep their per-site rule ids distinct (`OUTLINE_RULE_ID` / `PLAN_RULE_ID` /
`REFINE_RULE_ID`). It independently confirmed Expected-surface conformance over all 107 changed paths,
the D2 set sizes, plan `010`'s four corpus entries firing, the line delta, the 51/57 and 598 counts, that
all 25 `parse_ns` calls are at module scope, that all 7 `load_skill_module` sites keep a distinct
`module_name`, and — by `git log -S` — that plan `090` shipped `load_skill_module` in `94fd91c` (#1294).

### Findings this plan may NOT fix, each with its owning plan

The epic's § "Where a recorded finding goes" is the routing authority. A `marketplace/bundles/**`
defect is plan `090`'s **exclusively**; a disagreement between epic documents is plan `120`'s.

| # | Finding | Owner |
|---|---|---|
| R1 | `plugin-doctor/references/rule-catalog.md:1347` — *"are in the plugin-doctor tests' `_fixtures.py`"*. Falsified by this run's rename | **`090`** — the only plan that may edit `marketplace/bundles/**` |
| R2 | `plugin-doctor/references/rule-provenance.md:309` — *"live in the plugin-doctor tests' `_fixtures.py`"*. Same cause | **`090`** |
| R3 | `plan-marshall/skills/manage-execution-manifest/scripts/manage-execution-manifest.py:264` names `test/plan-marshall/manage-execution-manifest/_fixtures.py`, which plan `030` renamed to `_execution_manifest_fixtures.py`. **Pre-existing, not this run's** — recorded because it is the identical failure mode one plan earlier and still unowned, and a prose-bearing string literal in production code at that | **`090`** |
| R4 | `doc/plans/test-quality/100-module-budget-campaign.md:161` names `…/plugin-doctor/_fixtures.py` in an **Out-of-scope clause of a plan that has not yet run**. The highest-consequence of these: plan `100` will be executed from that text | **`120`**, or whoever next edits `100` before it runs |
| R5 | `doc/plans/test-quality/README.md:300` and `:438` name the old path | **`120`** |
| R6 | `doc/plans/test-quality/findings-test-corpus-review.md:277` names the old path | **`120`** |
| R7 | `doc/plans/test-quality/README.md:405-410` states `test/pm-code-intelligence/`'s finding *"is plan `090` § D2's"* and is *not fixable* by `080`. **This run fixed it** with `conftest.load_skill_module`, so both statements are now false. This plan's own Expected-surface bullet carries the same claim | **`120`** for the README; the plan file's own copy is corrected by this report standing beside it |
| R8 | `severity == 'error'` is asserted for both `ARGUMENT_NAMING_*` workflow-scope rules, and **no document says what an error-severity finding gates**. Surfaced by the cold read as the reason those two rationales could not be recovered from the module text | **`090`** — it owns the analyzers and their standards |

R1–R7 are all instances of one class: **a path or ownership claim held in prose, with nothing deriving
or checking it.** That is precisely what plan `120` was created to make a red build rather than a
finding, and this run's rename produced six fresh instances of it in a single commit — which is
evidence for `120` landing early, as the epic README already argues.

### Stop record (§ Step 6, "When the loop stops")

* **Exit: `verifier-clear`.** The budget is the default **five** rounds; the plan sets none. **One**
  round ran. No extension was needed or requested.
* **The verifier's own last answer**, quoted rather than paraphrased: *"Condition A forbids leaving what
  I found open — eleven items, all of them false statements, none of them fixed"* and *"**Condition B
  leaves nothing open.** I found no behavioural finding at all."* Every one of those eleven has since
  been fixed or recorded with an owner (V1–V15 above), which is what A requires; A is not satisfied by
  another round of verification but by the repair, and the repair is done.
* **The evidence the clean behavioural verdict rests on is stronger than a read**, and is named: an
  exhaustive enumeration of every removed assertion in the diff (not a sample) reduced to 29 distinct
  shapes and checked for subsumption one by one; a differential `test-conventions` and collected-count
  run against a clean clone at `origin/main` (61a43e5); an in-process execution of the D2 set
  computation; and — for D1's central claim — a mutation experiment that made the pre-conversion
  assertion pass and the post-conversion assertion fail on the same fixture.
* **Were the late findings narrower, or merely fewer?** Only one round ran, so there is no trend to
  report and none is claimed. What the round's *composition* shows is worth stating plainly: **every
  one of its eleven condition-A items was a defect in this run's own reporting — figures, counts,
  swapped ids, an invented rationale — and none was a defect in the shipped test code.** The verifier
  found zero weakened assertions and zero behavioural changes across 107 files.
* **Residue to assume remains.** The deliverables should be read as still carrying defects of the kind
  this round found: **misstated figures and unverified rationales in the report and in commit messages**,
  not weakened tests. A second round would most profitably re-derive every remaining number in this
  document rather than re-read the diff. Two figures are already known-unverified and flagged as such
  (V15): the coverage percentages and the wall-clock baseline.
* **No survivors.** Nothing is left open under B; the one behavioural change beyond pure refactoring is
  characterised in the next paragraph.

**The single B-class item, characterised under (a).** `load_skill_module` registers the seven extension
modules in `sys.modules` where the `spec_from_file_location` preambles it replaced did not. It cannot
change what the deliverable does: each of the seven passes a distinct `module_name` carried over verbatim
from the preamble it replaced, no two are equal, and the only other consumer of that surface
(`test/plan-marshall/script-shared/test_conftest_loader_contract.py:119`) passes `register=False`. The
order-independence run (default and reversed directory order, both `3404 passed, 13 skipped`) is the
executed check of exactly this property.

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

**GitHub access path:** the GitHub MCP server (`mcp__github__*`). No `gh` CLI is present in this session.
**Branch form:** **harness-assigned** — `claude/plugin-dev-generator-tests-v0zvzg`, kept as-is per § Step 2.
**Arrival:** first run; the branch existed locally but **not** on `origin`, and was pushed as the run's
first action before any edit.
A cloud run **never owes** a `/sync-plugin-cache`; none is recorded as owed.

| Step | Verdict | Artifact |
|---|---|---|
| 1 Skills loaded | **Done** | Named in § Skills loaded, with the route used and why the plugin notation was not |
| 2 Branch | **Done** | On `origin`; harness-assigned form, recorded above |
| 3 Plan directory | **Done** | `doc/plans/test-quality/080-…/plan.md` exists and opens with the first-instruction block — checked on the moved file, present and unmodified |
| 4 Implement | **Done** | 10 commits, every one carrying the trailer and no "Generated with" footer; deliverables addressed |
| 4 Per-commit gate | **Done** | Every commit touching `*.py` was preceded by a `./pw quality-gate` reporting `ruff … All checks passed!`, `mypy … Success: no issues found in 415 source files`, and `SPDX-header check passed`. The two exempt points — the initial branch push and the Step 3 `git mv` — changed no source |
| 4 Pushed | **Done** | Pushed after every commit; no unpushed commit remains |
| 5 Build gate | **Done** | Python changed, so the gate ran; results in § D5 |
| 6 Verification sub-agent | **Done** | One round, exit `verifier-clear`, budget 5 with no extension needed. Findings V1–V16 with dispositions; the verifier's last answer quoted; the evidence stronger than a read named; residue-to-assume stated; no survivors, and the one B-class item characterised under (a) |
| 7 PR cycle | _completed below_ | |
| 8 Merge gate | _completed below_ | |
| 8 Bridge | **Done** | No status or bookkeeping write landed under `doc/plans/` outside this plan's own directory. `git diff --name-only origin/main...HEAD -- doc/` shows only this plan's directory |
| 9 This check | **Done** | This table |
| 9 What have we learned | **Done** | Below |

**Re-verified at report time, per § Step 9.** *Tree* claims: the plan directory holds exactly `plan.md`
and `report-01.md`; `.plan/` was never written by this run and no `.plan/` path appears in the diff.
*History* claims: **this run performed no rebase**, so every SHA quoted in this report and in the commit
log is reachable from the branch under review — each was re-derived from `git log` at the moment of
writing rather than carried forward.

## What have we learned (Step 9)

**One contract change is proposed, on evidence this run produced.**

⚠️ **§ Step 6's dispatch checklist does not tell the verifier what the author has already verified, so a
verifier can spend a round re-deriving settled figures and still report a required check as "not
performed" when it was.** This run's verifier returned two findings (G2, G3) asserting the plan's
required cold read and three-module read had not been done. Both **had** been done and committed — by a
*separate* agent, correctly given the five modules and nothing else — but that commit landed while the
verifier was mid-flight, and its snapshot of the report still read `_Pending_`. The verifier reasoned
about this correctly and even noted that it could not itself serve as the cold reader, having been given
the plan and the diff. The cost was real but bounded: two findings that needed refuting rather than
fixing, and a round of doubt about whether a required gate had been skipped.

**The proposed edit** — one clause in § Step 6's dispatch checklist, after "the diff under review":

> * a list of the checks the author has **already** performed and where their results are recorded, so
>   the round is spent on what is unverified rather than on re-deriving what is. The verifier is free to
>   re-derive any of them and should say so when it does — this is a pointer, not a grant of trust.

The last sentence is what keeps this from weakening the gate: the verifier's independence is the point of
the step, and a checklist entry that let an author wave a check through would defeat it. This only stops
the *specific* waste of a verifier reporting an already-satisfied requirement as owed, on a snapshot that
went stale under it.

⛔ **Not proposed, though the run hit it.** The report-is-a-moving-target problem is more general than
this clause fixes — a verifier reading a report mid-write will always risk a stale snapshot. Freezing the
report before dispatch would trade that for a worse failure (the verifier could no longer see the
author's own findings table, which is itself a review surface § Step 6 explicitly names). No edit is
proposed for it; it is recorded so a later run does not mistake the narrow fix above for a complete one.

**Presented to the operator rather than self-approved**, per § Step 9. It is **not** shipped in this PR:
the lane requires a contract amendment to be its own `chore/` branch with its own review audience, and
this run does not self-approve a change to the contract that governs it.

## Residue

Everything left open, and where it goes next.

### Inside this plan's own surface — a follow-up run re-enters this plan

| Item | Size | Note |
|---|---|---|
| **D3 § B6** — 27 hand-built `argparse.Namespace` sites | 6 modules | `plugin_doctor_extension` (7), `plugin-maintain/test_maintain` (7), `maven-profile-management/test_profiles` (5), `plugin-doctor/test_validate` (4), `ref-documentation/test_docs` (2), `pm-dev-frontend/test_jsdoc` (2). **Every one of their scripts has a working parser seam** — probed and tabulated under D3 — so this is budget, not blockage |
| **D3 § B7** — 9 residual preamble findings | 9 modules | Three shapes, none a skill script the loader addresses: `marketplace/targets/generate.py`, the repo-root `build.py`, and per-bundle extension loaders whose surrounding structure resisted a mechanical rewrite |
| **D1** — 6 unconverted `test_analyze_*.py` modules | 6 modules | Each characterised under D1; none is an omission, and at least four are structurally outside the scaffold's single-fixture signature |
| **A cache-matched wall-clock re-measurement** | one run | Condition 4's magnitude is unattributable as measured (V15). A baseline taken with a warmed `__pycache__` would settle it |

### Handed to other plans, with owners

R1–R8 in § Findings. In one line each: two `plugin-doctor` reference docs and one production string
literal name a renamed fixture module (**`090`**); four epic documents name the same old path, one of
them inside a not-yet-executed plan's Out-of-scope clause (**`120`**); the README's `pm-code-intelligence`
ownership note is falsified by this run's fix (**`120`**); and neither the rules nor their standards say
what an error-severity `ARGUMENT_NAMING_*` finding gates, which is why a cold reader could not recover
those two rationales (**`090`**).

### Not residue — deliberately not acted on

**42 over-budget modules** in this slice. Reported, not split: plan `100` owns the budget campaign and
takes this slice after this plan lands, and D1's scaffold conversion is what brings several of them under
budget without a split at all. **8 `subprocess-pythonpath` findings**, unchanged before and after — not a
deliverable of this plan. **`hypothesis`** — D4 produces the evidence; adding the dependency is a
user-approval step with no operator present, and remains plan `010` § D6's standing proposal.
