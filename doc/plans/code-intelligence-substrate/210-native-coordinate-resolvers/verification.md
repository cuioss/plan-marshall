# Verification — 210-native-coordinate-resolvers

**Audited:** `plan.md`, `report-01.md` (the only two files in the plan directory)
**Tree state:** `2a9aba4` on `claude/code-intelligence-substrate-analysis-kah884`
**Overall verdict:** CONFIRMED WITH GAPS

The plan landed as squash-merge `87c71d3` ("feat(architecture): derive module edges natively for
Python and npm projects (plan 210) (#1238)"). Every deliverable is present, and D0's three
measurements were independently re-derived from scratch — including two fresh shallow clones of the
external repositories the run used. The gaps are not in what was built but in what the join
*cannot* reach: a Poetry-managed Python project, a setuptools project, an unreadable descriptor and
two ordinary PEP 508 dependency spellings all still produce a structurally empty graph, reported as
`status: ok, edge_count: 0` — the exact misreport class this epic exists to remove.

This document has since been through independent adversarial review; see § Adversarial review at the
end for what that round changed.

## Deliverable verdicts

| # | Deliverable (short) | Report claim | Ground truth | Verdict |
|---|---|---|---|---|
| D0 | GATE: measure a real non-Maven project | "Three real projects measured, not one" — 1/0/0/0, 8/11/0/11, 31/83/0/83 | All three rows re-derived exactly at HEAD, two by re-cloning the same repos | CONFIRMED |
| D1 | GATE: verify Gradle explicitly | "The coordinate path WORKS … one narrow form does not" | Confirmed at source: `_extract_gradle_module` publishes `group_id`+`artifact_id`; `_parse_dependencies_output` emits `project:{name}:compile` | CONFIRMED |
| D2 | A Python resolver joining on `[project] name` | Resolver id `pyproject`, PEP 503 normalised | Present, registered on the existing seam, fixture yields 5 edges through the seam | CONFIRMED (Done-when met; see § Correctness review for reach limits — G1/G2/G3/G10/G11) |
| D3 | An npm resolver, workspace members included | Resolver id `npm`, case-folded, workspace members need no special case | Present; fixture yields 5 edges, workspace globs resolved by real discovery | CONFIRMED |
| D4 | Tests proving non-empty edges **and** non-empty impact | "59 new tests across five modules" | 59 collected, 59 pass; per-module 13/16/18/7/5 all match; impact asserted as exact sets | CONFIRMED (two guards vacuous — G5, G7) |
| D5 | Documentation, incl. the extension-architecture page | Five documentation sites | All five present and accurate at HEAD | CONFIRMED |

## Per-deliverable detail

### D0 — GATE: verify the consumer-facing claim against a real consumer project

- **Required (plan):** *"the edge count from at least one real non-Maven project is recorded, **or**
  the run reports it could not reach one."* Plus the ⛔: do not state a consumer-wide claim the run
  could not check.
- **Claimed (report):** three projects measured; `plan-marshall` 1 module / 0 sibling-naming
  dependency strings / 0 edges before / 0 after; `opentelemetry-python` 8 / 11 / **0** / **11**;
  `react-router` 31 / 83 / **0** / **83**. Plus a fourth measurement: the full crawl over
  `plan-marshall` yields 29 edges over 12 modules with **zero** modules carrying a coordinate pair.
- **Found / checks run:** I re-derived every row rather than reading the report's numbers.
  - `plan-marshall`, driven through the real `discover_python_modules` + the real `pyproject` and
    `maven` resolvers: `1 module ['default'], metadata.name='plan-marshall', deps=0,
    dependency strings naming a sibling module: 0, pyproject edges []`. **Exact match.**
  - `open-telemetry/opentelemetry-python`, shallow-cloned fresh into `$TMPDIR`:
    `modules: 8`, `dependency strings naming a sibling module: 11`,
    `maven resolver edges (the BEFORE state): 0`, `pyproject resolver edges: 11`,
    `modules carrying group_id+artifact_id: 0`. **Exact match on all four figures.**
  - `remix-run/react-router`, shallow-cloned fresh: `modules: 31`,
    `dependency strings naming a sibling module: 83`, `maven resolver edges (BEFORE): 0`,
    `npm resolver edges: 83`. **Exact match.**
  - The full-crawl row has drifted with the tree (see § Report accuracy), but its load-bearing half
    holds: `crawl_all_modules('/home/user/plan-marshall')` → 13 modules, **0** carrying
    `group_id`+`artifact_id`, and the `pyproject` resolver sources **0** edges of the graph.
- **Verdict:** CONFIRMED. This is the strongest-evidenced deliverable in the plan directory: the
  three headline measurements are reproducible from scratch by a third party. The report's handling
  of the ⛔ is also correct — it states the generalisation as *structural* (the discoverers emit no
  coordinate pair at all) with the measurements as confirmation, not as an inductive sample.

### D1 — GATE: verify Gradle explicitly

- **Required (plan):** *"Gradle's dependency extraction is read and classified as working or not."*
  Plus the ⛔: if it works, do not "fix" a working path.
- **Claimed (report):** works for the coordinate form; `project :core` extracts as
  `project:core:compile` and derives no edge; deliberately not fixed.
- **Found:**
  - `.../build-gradle/scripts/_gradle_cmd_discover.py:448-453` — every Gradle module publishes
    `metadata.artifact_id` (the module name) and `metadata.group_id`, the same pair Maven publishes.
    This is what lets the `maven` resolver join Gradle unchanged.
  - `.../build-gradle/scripts/_gradle_cmd_discover.py:326-331` — `if 'project :' in line:` →
    `dependencies.append(f'project:{proj_match.group(1)}:compile')`. The literal `project` becomes
    the group segment, so the join key is `project:core`, matching no published coordinate.
  - `test/plan-marshall/build-gradle/test_gradle_rides_the_maven_join.py:103-149` pins both halves
    (7 tests, all pass).
  - Out-of-scope respected: `git show --name-only 87c71d3` lists **no** file under
    `marketplace/bundles/plan-marshall/skills/build-gradle/scripts/`. The working Gradle path was
    not touched.
- **Verdict:** CONFIRMED. One test-adequacy defect (G7) — the premise assertion is tautological.

### D2 — a Python resolver

- **Required (plan):** *"a multi-module Python fixture yields non-empty edges through the seam"*,
  deriving from project names rather than Maven coordinates, registered against the **existing**
  resolver seam.
- **Claimed (report):** `BuildExtension` also subclasses `DerivationResolverBase`, id `pyproject`
  (not `python`), joining `[project] name` on `metadata.name` against `name:scope` strings in PEP 503
  normalised form.
- **Found:**
  - `.../build-pyproject/scripts/extension.py:127` — `class BuildExtension(BuildExtensionBase,
    DerivationResolverBase)`; `:284-297` `derivation_resolver_id() -> 'pyproject'`; `:311-326`
    `_distribution_name` reading `metadata.name` with no fallback; `:328-365` `derive_edges`.
  - `.../script-shared/scripts/extension/_name_edge_join.py:32-42` `normalize_pep503`, `:57-90`
    `scoped_modules`, `:93-148` `build_name_owners` (abstain-and-report on collision), `:151-207`
    `derive_name_edges`.
  - Existing seam, no new extension point: `discover_derivation_resolvers()` at
    `.../extension-api/scripts/extension_discovery.py:533-578` is unchanged by the diff, and
    `git show --name-only 87c71d3` adds no new `ext-point-*.md`.
  - Fixture through the seam: `test_pyproject_derivation_resolver.py:101-108` asserts the exact
    5-edge set from real discovery output; the e2e module reaches the same edges through the real
    `graph` verb.
- **Verdict:** CONFIRMED against the literal *Done when*. The deliverable's broader reach is where
  the gaps are — see § Correctness review and G1/G2/G3/G10/G11. All five sit in one unchanged
  function (`_parse_pyproject_metadata`, which this plan's diff does not touch: the diff adds the
  Axis-C half to `build-pyproject/scripts/extension.py` and leaves `_pyproject_cmd_discover.py`
  alone), so they are the join's *input* reach, not a defect in what was built.

### D3 — an npm resolver

- **Required (plan):** *"a multi-package workspace fixture yields non-empty edges"*, deriving from
  package names, **including workspace members**.
- **Claimed (report):** id `npm`, case-folded; workspace members required no special case because
  discovery already resolves the globs; `metadata.name` added to npm discovery, necessarily.
- **Found:**
  - `.../build-npm/scripts/extension.py:46` multiple inheritance; `:158-164` id `npm`; `:174-187`
    `_package_name`; `:189-225` `derive_edges` → `derive_name_edges(..., normalize_npm)`.
  - `.../build-npm/scripts/_npm_cmd_discover.py:272-284` — the `metadata` block now carries
    `'name': pkg_data.get('name')` with the rationale in-comment. `git show --name-only 87c71d3`
    confirms this file is in the diff (+8 lines).
  - Workspace resolution is pre-existing and real:
    `_npm_cmd_discover.py:128-167` handles the array form, the `{"packages": [...]}` form, and
    `:168-182` `pnpm-workspace.yaml`. The fixture exercises the array form through
    `discover_npm_modules`, and `test_npm_derivation_resolver.py:70-78` asserts the three members
    were discovered before asserting any edge.
  - `test_npm_derivation_resolver.py:116-123` — exact 5-edge set including `('unnamed',
    '@sample/core')` and `('@sample/monorepo', '@sample/core')`.
- **Verdict:** CONFIRMED. One reach gap (G4) and one vacuous guard (G5).

### D4 — tests

- **Required (plan):** *"tests proving both ecosystems yield non-empty graph edges **and** non-empty
  impact"*, with the ⛔ that "edges present, impact empty" must be catchable.
- **Claimed (report):** 59 tests across five modules (13/16/18/7/5); impact asserted as expected
  dependent sets, not non-emptiness; two parametrised anti-vacuity tests.
- **Found / checks run:** re-derived at HEAD with `pytest --collect-only`, per module:
  ```text
  test_pyproject_derivation_resolver.py       -> 13 tests collected
  test_npm_derivation_resolver.py             -> 16 tests collected
  test_native_resolver_graph_impact.py        -> 18 tests collected
  test_gradle_rides_the_maven_join.py         ->  7 tests collected
  test_scoped_module_name_persistence.py      ->  5 tests collected
  ```
  Total 59; `59 passed in 1.43s`. Every figure in the report matches my own measurement exactly.
  - Impact-separate-from-edges: `test_native_resolver_graph_impact.py:249` asserts
    `impact == ['default', 'sample_api', 'sample_cli']` and `:324` asserts
    `impact == ['@sample/api', '@sample/cli', '@sample/monorepo', 'unnamed']` — exact sets, so an
    empty impact beside a non-empty edge set fails them. `:235-241` and `:311-317` are the two
    non-emptiness assertions carrying the failure-mode message.
  - Anti-vacuity: `:145-169`, two parametrised tests re-running the same fixtures with
    `discover_derivation_resolvers` patched to `[]`, asserting `edges == []`, `resolver_count == 0`,
    `impact == []` and `resolvers == []`.
- **Verdict:** CONFIRMED, with two vacuous guards found by mutation (G5, G7).

### D5 — documentation

- **Required (plan):** *"Register the native resolvers alongside the build-system extension
  implementations in the extension-architecture concepts page."* ⭐ the consumer-facing page matters
  most; ⛔ ship docs in this plan.
- **Claimed (report):** five sites — a new `doc/user/dependency-intelligence.adoc`,
  `ext-point-derivation-resolver.md` roster rows plus four new sections,
  `doc/concepts/code-intelligence.adoc`, `doc/concepts/extension-architecture.adoc`,
  `doc/resources/diagrams/extension-topology.svg`.
- **Found:** all five present at HEAD.
  - `doc/concepts/extension-architecture.adoc:28` — the literal deliverable: "Each build skill that
    knows an identity its ecosystem publishes registers the matching join: `build-maven` the
    `groupId:artifactId` coordinate join …, `build-pyproject` the PEP 621 distribution-name join,
    `build-npm` the `package.json` package-name join."
  - `ext-point-derivation-resolver.md:227-228` — the `pyproject` and `npm` roster rows; `:82-91` the
    per-axis registration table with the "Open to" column and the ⚠ that Axis-B registration is
    closed (the N9 fix); `:240` why `python` and `pyproject` are both wanted; `:244-249` the scoping
    rationale; `:255` the no-fallback rationale stated per ecosystem (the N11 fix); `:265-269` Gradle
    rides the Maven join.
  - `doc/user/dependency-intelligence.adoc` (8992 bytes) — registered at `doc/user/README.adoc:21`
    and back-linked from `doc/concepts/code-intelligence.adoc:310`. § "The four verbs" (:15-44) is
    present with `path SOURCE TARGET` positional, the F18 fix.
  - `doc/concepts/code-intelligence.adoc:59` — § "Coordinates are not the only identity", with the
    Gradle caveat at `:67` (the N7 fix).
  - `doc/resources/diagrams/extension-topology.svg` — the derivation-resolver card reads `7 impls`,
    which matches the live roster at HEAD (a later plan added `lsp`).
- **Verdict:** CONFIRMED.

## Correctness review

⚠ This section's coverage of the **Python discoverer** was incomplete on the first pass: it examined
what `_parse_pyproject_metadata` does with the `[project]` table it reads (C1–C3) but not what
happens when the file it reads is the wrong file (C5) or unreadable (C6). Both were found by
adversarial review and are recorded below in their found order.

I read the whole shipped surface: `_name_edge_join.py` (all 207 lines), both `extension.py`
Axis-C halves, `_npm_cmd_discover.py`'s module builder and dependency extractor,
`_pyproject_cmd_discover.py`'s metadata parser, `_gradle_cmd_discover.py`'s dependency parser and
module extractor, the `merge_resolver_edges` call site in `_cmd_client_query.py`, and the
`discover_derivation_resolvers` collector. The join itself is clean — deterministic (`sorted(edges)`,
notes sorted by key), `None`-safe on `metadata`, scoped at both ends, self-edge-free, and it
abstains-and-reports on an ambiguous name. The defects are all upstream of the join, in what the
discoverers hand it.

**C1 — a Poetry-managed Python project derives zero edges, reported as a positive empty answer.**
`marketplace/bundles/plan-marshall/skills/build-pyproject/scripts/_pyproject_cmd_discover.py:282`
reads `project = data.get('project', {})` and nothing else. A project using Poetry's own table
(`[tool.poetry] name`, `[tool.poetry.dependencies]` — still the majority of the Poetry installed
base) therefore yields `metadata == {}` and `dependencies == []` for every module. Driven end to
end over a synthetic three-module Poetry monorepo where `pkg_app` declares `mono-core`:

```text
POETRY MONOREPO modules: ['default', 'pkg_app', 'pkg_core']
   default  metadata= {} deps= []
   pkg_app  metadata= {} deps= []
   pkg_core metadata= {} deps= []
  edges: ([], [])
```

The consequence is precisely the defect class the plan's Problem section names: the graph, path,
neighbours and impact verbs are structurally vacuous while the resolver reports `status: ok,
edge_count: 0`, which `client-api.md:110` defines as "N resolvers ran and found nothing … a real,
positive result". `doc/user/dependency-intelligence.adoc:48` tells that consumer "the graph verbs
work on a fresh checkout with no configuration". → **G1**

**C2 — a PEP 508 direct reference silently produces no edge.**
`_pyproject_cmd_discover.py:295` splits a requirement on `[ < > = ! ~` only. `"m-core @
file:///./core"` contains none of them, so the whole string survives as the dependency name;
`_name_edge_join.py:200` then takes `dependency.split(':', 1)[0]` and gets `m-core @ file`. Driven
end to end where `core/` publishes `m-core` and `app/` depends on it by direct reference:

```text
  app    -> ['m-core @ file:///./core:runtime']
  core   -> []
  edges: ([], [])
```

No note is emitted — `derive_name_edges` treats an unmatched name as an external dependency
(`_name_edge_join.py:170-175`), which is right for a real external and wrong for a mangled one. The
miss is therefore invisible in `notes[]`. → **G2**

**C3 — a PEP 508 environment marker silently produces no edge.** Same parser, same silence.
`"m-core; python_version >= \"3.11\""` → `.split('>')[0].strip()` → `m-core; python_version`:

```text
  marked metadata.name= m-marked -> ['m-core; python_version:runtime']
  edges: ([], [])
```

→ **G3**

**C4 — the npm join reads only two of npm's four dependency kinds, undocumented.**
`_npm_cmd_discover.py:293-307` reads `dependencies` and `devDependencies` and nothing else.
`peerDependencies` is the idiomatic way a plugin package in a workspace declares its dependency on
the workspace's core package, and `optionalDependencies` is common for platform-specific siblings;
both silently produce no edge. The run *did* disclose the analogous Python limitation (only the
`dev` extra is read) in `dependency-intelligence.adoc:86` and in the report's Residue — the npm
specifics section (`:90-98`) carries no equivalent sentence, so the two ecosystems are documented
asymmetrically for the same class of gap. → **G4**

**C5 — a setuptools project derives zero edges, and discovery names the file it never reads.**
*(Added by adversarial review; the original pass missed it.)* `_find_descriptor_file`
(`_pyproject_cmd_discover.py:308-321`) accepts `pyproject.toml`, `setup.cfg` **and** `setup.py`, so a
setuptools module is admitted, stamped `build_systems: ['python']` — which places it inside the
`pyproject` resolver's `scoped_modules` filter — and given its real descriptor path. But
`_parse_pyproject_metadata` opens `pyproject.toml` only (`:269`) and returns early when it is absent
(`:273-274`). Driven end to end over a synthetic three-module setuptools monorepo where `lib_app`
declares `st-core` under `[options] install_requires`:

```text
SETUPTOOLS modules: ['default', 'lib_app', 'lib_core']
   default  | descriptor= setup.py            metadata= {} deps= []
   lib_app  | descriptor= lib_app/setup.cfg   metadata= {} deps= []
   lib_core | descriptor= lib_core/setup.cfg  metadata= {} deps= []
  edges: ([], [])
```

Same misreport as C1, with the extra defect that the module dict asserts a descriptor the parser
never opens. → **G10**

**C6 — an unreadable `pyproject.toml` is swallowed, fail-open.** *(Added by adversarial review.)*
`_pyproject_cmd_discover.py:279-280` is a bare `except Exception` returning the empty metadata /
dependency pair, so a malformed descriptor is indistinguishable from one declaring nothing, and the
loss reaches no channel — not `notes[]`, which only the resolver writes, and not a log. Driven end to
end where the root correctly declares `b-a` and `mod_a/pyproject.toml` has one unbalanced bracket:

```text
MALFORMED TOML modules: ['default', 'mod_a']
   default  metadata= {'name': 'b-root'} deps= ['b-a:runtime']
   mod_a    metadata= {}                 deps= []
  edges: ([], [])
```

The npm side is not symmetric: `_load_package_json` (`_npm_cmd_discover.py:379-392`) catches the same
class but returns `None`, dropping the module rather than admitting an empty one. → **G11**

**Not defects, checked and cleared:**

- The Maven lazy-enrich seam does **not** fire a subprocess for Python/npm modules: `_get_maven_metadata`
  (`build-maven/scripts/_maven_cmd_discover.py:557-559`) returns `None` before any `execute_direct`
  when `pom.xml` is absent.
- `normalize_pep503` (`_name_edge_join.py:42`) is equivalent to the canonical PEP 503 form; the
  substitute-then-strip order changes nothing for any legal distribution name.
- `build_name_owners` skips a module publishing no name without emitting a note
  (`_name_edge_join.py:131-133`) — correct, and documented as deliberate at `:112-116`.
- `count_dispatched` / `_partition_configured_resolvers` fail **open**: an unreadable run-config
  store leaves every resolver dispatched (`_cmd_client_query.py:1001-1002`), and
  `DERIVATION_RESOLVER_ENABLED_DEFAULT = True` (`run_config.py:826`). Verified live: the section is
  `{}` in this clone and all seven resolvers report enabled.

## Test adequacy

**Coverage map.** D2 → `test/plan-marshall/build-pyproject/test_pyproject_derivation_resolver.py`
(13). D3 → `test/plan-marshall/build-npm/test_npm_derivation_resolver.py` (16). D2+D3 end to end
through the real `graph`/`impact` verbs → `test/plan-marshall/manage-architecture/test_native_resolver_graph_impact.py`
(18). D1 → `test/plan-marshall/build-gradle/test_gradle_rides_the_maven_join.py` (7). Residue #4 →
`test/plan-marshall/manage-architecture/test_scoped_module_name_persistence.py` (5).

**Mutation sweep.** I snapshotted the four production files' bytes to
`$TMPDIR/verify-210-mutsweep/`, applied ten single-point mutations one at a time, ran the four
resolver test modules after each, and wrote the original bytes back myself (no `git checkout` /
`restore` / `stash`). Baseline `54 passed`:

| Mutation | Result |
|---|---|
| M1 `normalize_pep503` → identity | CAUGHT — 6 failed |
| M2 `normalize_npm` → no case-fold | CAUGHT — 3 failed |
| M3 `scoped_modules` → unscoped | CAUGHT — 5 failed |
| M4 ambiguous name → pick first alphabetically | CAUGHT — 2 failed |
| M5 self-edge allowed | CAUGHT — 2 failed |
| M6 Python `_distribution_name` falls back to the module name | CAUGHT — 3 failed |
| M7 **npm `_package_name` falls back to the module name** | **SURVIVED — 54 passed** |
| M8 npm discovery drops `metadata.name` | CAUGHT — 13 failed |
| M9 `dependency.rsplit(':', 1)[0]` | SURVIVED — equivalent **over these fixtures**, where every emitted string has exactly one `:` |
| M10 whole `name:scope` string used as the key | CAUGHT — 24 failed |

`git status --porcelain` for all four files is clean afterwards.

⚠ M9's "equivalent mutant" reading holds only for the two fixtures. It is **not** a general property
of the emitted format: C2 above produces `m-core @ file:///./core:runtime`, which carries three
colons, and `split` / `rsplit` disagree on it (`m-core @ file` vs `m-core @ file:///./core`). Both
still fail to join, so the mutant survives either way — but the stated reason, as originally written,
was falsified by this document's own C2. Scoped accordingly.

**M7 is a genuinely vacuous guard**, and the survival is not a weak mutation. The test that names the
rule — `test_npm_derivation_resolver.py:141-143`,
`test_package_without_a_name_is_never_an_edge_target` — cannot fail, because no module in the npm
fixture declares a dependency on the string `unnamed`. Proven directly by running both readings of
`_package_name` over the real discovered fixture:

```text
any module declaring a dependency on the literal string 'unnamed': []
edges with the shipped no-fallback rule: [... 5 edges ...]
edges WITH a directory-name fallback : [... the same 5 edges ...]
--- after adding one dependency on the literal string 'unnamed':
edges with the shipped no-fallback rule: [... the same 5 edges ...]
edges WITH a directory-name fallback : [..., ('@sample/monorepo', 'unnamed'), ...]
```

The Python fixture gets this right — `multi-module-python/pyproject.toml` deliberately depends on
`"toolbox>=1.0.0"` where `toolbox/` publishes no name, which is why M6 was caught. The npm fixture
is missing the equivalent one-line dependency. → **G5**, and the module docstring's account of that
failure mode (`test_npm_derivation_resolver.py:22-24`) is inaccurate as well → **G6**.

**A second tautological guard, found by reading.**
`test_gradle_rides_the_maven_join.py:125-128`,
`test_gradle_modules_carry_the_coordinate_pair_the_maven_join_reads`, is docstringed "The premise of
the whole claim: Gradle publishes what Maven publishes" — but it asserts on the dict the test's own
`_gradle_module()` helper (`:59-76`) hard-codes two lines earlier. It cannot fail no matter what
`_extract_gradle_module` emits. The real function is never called by this module, so D1's founding
premise is the one half of the Gradle claim with no executable pin. (The premise *is* true — I
verified it by reading `_gradle_cmd_discover.py:448-453` — but the test is not the evidence.) → **G7**

## Report accuracy

Every substantive claim I could check held, and several held to the digit. Specifically confirmed:
the 59-test total and all five per-module counts; the `pyproject` / `npm` resolver ids and the
uniqueness rationale; the three D0 measurement rows; the four Out-of-scope bullets; all 18 pass-1
dispositions, all 16 pass-2 dispositions, and all 8 CodeRabbit dispositions that leave a trace in
the tree (spot-checked F3, F4, F5, F8, F9, F10, F11, F12, F13, F14, F15, F16, F17, F18, N7, N8, N9,
N11, N13, N14, N15, N16, C1, C4, C5, C6 — each found at its named site).

Three claims are inaccurate against the tree now:

1. **The build-gate diff verdict is stale — by exactly the defect the report's own Step 9 proposal
   is about.** The report states: *"`git diff --name-only origin/main...HEAD -- '*.py'` → **10
   files** at HEAD, so the gate applied"*, and the same section insists *"the diff verdict MUST be
   re-derived at HEAD"*. The merged PR diff contains **13** `.py` files
   (`git show --name-only --format="" 87c71d3 | grep -c '\.py$'` → `13`; `87c71d3` is a single-parent
   squash, so its diff *is* the three-dot diff). The three uncounted files are the ones added after
   `10` was recorded — `test_scoped_module_name_persistence.py` (pass 3 / C4) and two of the N14
   fixture fixes (`test_cmd_suggest.py`, `test_extension_implementations.py`, both confirmed in the
   diff to carry the `lit:compile` → `lit:runtime` change). That those three arrived *after* `10` was
   recorded is inferred from the report's pass ordering, not observed — the branch was deleted at
   squash-merge. The `./pw verify` figures in the same block are **arithmetically consistent** with
   the N3 correction plus pass 3's additions (`19716 + 5 = 19721`, `740 + 1 = 741`); that is a
   consistency check, not a re-measurement — see § Method, "Not checked", (ii). The omission is
   confined to the file count. → **G9**
2. **The full-crawl figures have drifted — and keep drifting.** The report records "29 edges across
   12 modules … markdown 29, python-import 5, documentation 5". This audit's own re-measurement (13
   modules, 25 edges over 11 nodes, markdown 25 / python 5 / documentation 0) **also no longer
   reproduces**: adversarial review, re-running `crawl_all_modules` + `get_module_graph` over this
   repository a few commits later, measured 13 modules, **32** edges over **13** nodes, and
   markdown 32 / python 5 / documentation 5 / lsp 0 / maven 0 / npm 0 / pyproject 0, at
   `resolver_count: 7`. Every edge-count figure in this row is a snapshot of a tree that other plans
   are still changing, and none of them should be quoted forward. ⛔ **Only the invariant is stable,
   and it is what the row was cited for**: **0** modules carry a `group_id`+`artifact_id` pair, and
   the `pyproject` resolver sources **0** of this repository's edges while reporting
   `status: ok, edge_count: 0`. That invariant reproduced at both measurements. Not raised as a gap.
3. **A residue item no longer reproduces.** See the table below.

Two report claims are **UNVERIFIABLE**, both for structural reasons rather than doubt: the commit
SHAs it cites (`37788dc`, `fc73d6a`, `c820514`, `047eef4`, `0f9f619`) do not resolve in this clone —
`git cat-file -t` returns "Not a valid object name" for all five, because the PR was squash-merged
and the branch deleted; and the reviewer-participation section (`M = 3`, the CodeRabbit re-request
sequence, the merge-gate check states) depends on GitHub API state I did not query.

## Declared residue — current status

| Residue item (from report) | Still open? | Evidence |
|---|---|---|
| Gradle's `project :name` form derives no edge | **Open** — deliberately, and correctly pinned | `_gradle_cmd_discover.py:326-331` still emits `project:{name}:compile`; `build-gradle/scripts/` carries no `DerivationResolverBase`; `test_gradle_rides_the_maven_join.py:136-149` pins both directions and passes. Documented at `ext-point-derivation-resolver.md:265`, `build-maven/SKILL.md:91`, `dependency-intelligence.adoc:103` — the three sites the test docstring names. |
| Python discovery reads only the `dev` extra | **Open** — deliberately | `_pyproject_cmd_discover.py:293-303` reads `[project] dependencies` and `optional-dependencies.dev` only. Disclosed to consumers at `dependency-intelligence.adoc:86`. |
| Serial-pytest module-registration collision (39 failures, 34 pre-existing) | **No longer reproduces** | I ran the exact combination the report names — `test/plan-marshall/manage-architecture`, `build-npm`, `build-pyproject`, `build-gradle`, `build-maven`, `test/pm-plugin-development`, `test/pm-dev-python` — in ONE serial pytest process: **`1 failed, 3974 passed in 501.82s`**. The single failure is `test_doctor_marketplace.py::test_real_marketplace_quality_gate_has_zero_findings`, which fails identically **in isolation** (`1 failed in 29.08s`) and is a whole-tree state check, not a module-registration collision. Zero `_cmd_client_query` collision failures. |
| A scoped npm module cannot round-trip through `save_module_derived` | **Open** — characterized, not fixed | `test_scoped_module_name_persistence.py` (5 tests) passes, including the flat-name control at `:89-94` and the non-npm `group/sub` parametrisation at `:97-104`. The constraint itself is unchanged; the report correctly scopes the risk to the fixture path rather than production. |

## Out-of-scope and collateral

All four Out-of-scope bullets are respected, verified against `git show --name-only 87c71d3`:

- **Changing the Maven derivation path** — `build-maven/scripts/extension.py` is not in the diff.
  Only `build-maven/SKILL.md` changed (+2 lines, the N8 Gradle paragraph), which is documentation.
- **A new extension point** — no new `ext-point-*.md`; `extension_discovery.py` is untouched; both
  resolvers opt in by multiple inheritance on the existing `DerivationResolverBase`.
- **Fixing Gradle** — nothing under `build-gradle/scripts/` is in the diff; only a test was added.
- **Configuring which resolvers run** — `run_config.py` and `manage-run-config/` are not in the diff.

One thing changed without being an explicit deliverable, and it was declared: `_npm_cmd_discover.py`
gained `metadata.name` (+8 lines). The report names it and argues its necessity, and the argument is
correct — without it the npm join has no field that distinguishes a published package from an
unnamed one. Not undeclared collateral.

One inherited defect surfaced during this audit and is **not** attributable to this plan:
`doc/user/dependency-intelligence.adoc:71` says "Three further joins run over cross-references" and
enumerates three. There are now four Axis-A joins (`markdown`, `python`, `documentation`, `lsp`).
The `lsp` resolver landed at `c86de8b` (#1243), *after* this plan's `87c71d3` (#1238), and a later
plan (#1252) edited the same page without correcting the count. Recorded as **G8** because it is a
live false statement in shipped user documentation, with the attribution stated.

## Method and coverage

**What I did.** Read `plan.md` and `report-01.md` in full, then the shipped surface: both build
`extension.py` Axis-C halves, `_name_edge_join.py`, `_npm_cmd_discover.py`,
`_pyproject_cmd_discover.py`, `_gradle_cmd_discover.py`, `extension_discovery.py`, the resolver
dispatch and merge site in `_cmd_client_query.py`, `run_config.py`'s resolver gate, all five test
modules, all six fixture descriptors, and all five documentation sites.

**Executable evidence.** (a) Re-collected and re-ran the 59 tests. (b) A ten-mutation sweep with
byte snapshots I took and restored myself. (c) Re-derived every D0 row from scratch, including two
fresh `git clone --depth 1` of `open-telemetry/opentelemetry-python` and `remix-run/react-router`,
driven through the shipped discoverers and the shipped `maven` / `pyproject` / `npm` resolvers.
(d) Three end-to-end probes on synthetic projects (Poetry layout, PEP 508 direct reference, PEP 508
environment marker) that produced the C1/C2/C3 findings. (e) A 3974-test serial pytest run to test
the third residue item. (f) A live `crawl_all_modules` + `get_module_graph` over this repository.

**Guarding against false negatives.** Before reporting "no coordinate-bearing module in
plan-marshall" I confirmed the same query finds coordinates where they exist — the Gradle fixture
module dict returns a non-empty `group_id`/`artifact_id` pair through the identical accessor.
Before reporting the M7 survival as vacuity I confirmed the mutation is live, by showing it *does*
change the edge set once one dependency string is added.

**Not checked, and why.** (i) The report's commit SHAs and its GitHub-side claims (reviewer
participation, merge-gate check states, the CodeRabbit re-request timeline) — the branch is deleted
and I did not query the API. (ii) `mypy(production) … 400 source files` and the other `./pw verify`
sub-step figures — the brief excludes running the full verify. (iii) The verification agent's
reverse-index injection experiment (`edges: 5, impact: []`) was **not** reproduced: it requires
mutating `_cmd_client_query.py`, which other audit agents were actively modifying in this shared
worktree during my run. I substituted a reading argument plus the two zero-resolver parametrised
tests, which is weaker evidence for that one claim. (iv) `pnpm-workspace.yaml` workspace resolution
is claimed in shipped docs and has no test anywhere in `test/plan-marshall/build-npm/`; it is
pre-existing discovery code that this plan neither added nor was asked to cover, so it is noted here
rather than raised. Adversarial review closed the open question behind that call by driving a
synthetic pnpm workspace (root + `packages/core` + `packages/app`, patterns declared only in
`pnpm-workspace.yaml`) through the real `discover_npm_modules` and the real `npm` resolver: **3
modules, 2 edges**. The shipped claim is therefore true, merely untested — which keeps this out of
the false-documentation class and leaves it a pre-existing test gap, as judged.

**Concurrency caveat.** Other audit agents were mutating files in this worktree throughout. One
early full-crawl reading (all seven resolvers `not_dispatched`) was produced against a transiently
mutated `_cmd_client_query.py` and is discarded; the figures reported above are from a re-run after
`git diff` on that file came back empty. Every number I state was measured with the files it depends
on verified unmodified at the time.
