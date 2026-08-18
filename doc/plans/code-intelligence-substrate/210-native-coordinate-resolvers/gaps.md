# Gaps — 210-native-coordinate-resolvers

The plan's six deliverables all landed and D0's three measurements reproduce exactly at HEAD. What
remains is reach, not construction: the joins this plan built are correct, but the *discoverers* that
feed them cannot see a Poetry-managed Python project at all (G1), silently mangle two ordinary PEP 508
dependency spellings (G2, G3), and read only two of npm's four dependency kinds (G4) — in every case
producing an empty graph that the seam reports as `status: ok, edge_count: 0`, i.e. as a measured
absence rather than a missing capability. Alongside that, two test guards that name a rule cannot fail
(G5, G7), one test docstring misdescribes its own fixture (G6), one live count in shipped user
documentation is wrong (G8, inherited from a later plan), and the run report's build-gate file count is
stale (G9).

## G1 — Read Poetry's own tables so a Poetry-managed Python project derives edges

- **Kind:** incomplete
- **Severity:** high
- **Topic:** lsp/resolvers
- **Where:** `marketplace/bundles/plan-marshall/skills/build-pyproject/scripts/_pyproject_cmd_discover.py:282`
  (`_parse_pyproject_metadata`, `project = data.get('project', {})`)
- **Evidence:** The parser reads the PEP 621 `[project]` table and nothing else. A project declaring
  `[tool.poetry] name` and `[tool.poetry.dependencies]` — still the majority of the Poetry installed
  base, since `[project]` support only arrived in Poetry 2.0 — therefore emits no name and no
  dependencies. Driven end to end over a synthetic three-module Poetry monorepo in which `pkg_app`
  declares `mono-core`:

  ```text
  POETRY MONOREPO modules: ['default', 'pkg_app', 'pkg_core']
     default  metadata= {} deps= []
     pkg_app  metadata= {} deps= []
     pkg_core metadata= {} deps= []
    edges: ([], [])
  ```

- **Why it matters:** This is the plan's own Problem statement, unresolved for a whole class of
  consumer: "every Python … consumer project gets its graph, path, neighbours and impact verbs
  structurally vacuous … while every verb reports success." Worse than silence, the answer actively
  misreports — `client-api.md:110` defines `resolver_count: N` with no edges as "a real, positive
  result … your modules genuinely declare no dependencies on each other", and
  `doc/user/dependency-intelligence.adoc:48` promises that consumer "the graph verbs work on a fresh
  checkout with no configuration".
- **Action:** In `_parse_pyproject_metadata`, fall back to `[tool.poetry]` when `[project]` is absent
  or carries no `name`: read `tool.poetry.name` / `version` / `description` into `metadata`, and read
  `tool.poetry.dependencies` (skipping the `python` key) and `tool.poetry.group.dev.dependencies`
  into the `name:scope` dependency list with the same `runtime` / `dev` scopes. A Poetry dependency
  value may be a version string or a table (`{version = "^1.0"}`, `{path = "../core"}`) — only the
  key is needed, so the value's shape is irrelevant to the join. Add a `poetry-monorepo` fixture
  under `test/plan-marshall/build-pyproject/fixtures/` shaped like the existing
  `multi-module-python` one, and extend `test_pyproject_derivation_resolver.py` to assert its exact
  edge set.
- **Done when:** A fixture whose modules declare their names and inter-module dependencies only under
  `[tool.poetry]` yields a non-empty edge set through `BuildExtension.derive_edges`, and the existing
  PEP 621 fixture's exact 5-edge assertion still passes unchanged.
- **Effort:** M
- **Risk if fixed:** `metadata` and `dependencies` grow for every Poetry consumer, which changes what
  `architecture` emits for consumers of those fields beyond edge derivation — the same widening
  concern the run cited when it declined to widen the `dev`-extra read. Mitigate by making the Poetry
  read a strict fallback that never fires when `[project]` is present.

## G2 — Strip the PEP 508 direct-reference suffix from a dependency name

- **Kind:** bug
- **Severity:** medium
- **Topic:** lsp/resolvers
- **Where:** `marketplace/bundles/plan-marshall/skills/build-pyproject/scripts/_pyproject_cmd_discover.py:295`
  and `:301` (the `dep.split('[')[0].split('<')[0]…` chain), consumed at
  `marketplace/bundles/plan-marshall/skills/script-shared/scripts/extension/_name_edge_join.py:200`
- **Evidence:** The split chain contains no `@`, so a direct reference survives whole; the join then
  takes `dependency.split(':', 1)[0]` and gets `m-core @ file`. End to end, where `core/` publishes
  `m-core` and `app/` depends on it by direct reference:

  ```text
    app    -> ['m-core @ file:///./core:runtime']
    core   -> []
    edges: ([], [])
  ```

- **Why it matters:** `name @ url` is a legal and common way to wire a sibling in a plain PEP 621
  monorepo without a workspace tool. The edge is lost with no signal at all: `derive_name_edges`
  classifies an unmatched name as an external dependency and deliberately emits no note
  (`_name_edge_join.py:170-175`), so `notes[]` — the seam's own suppression channel — stays empty
  and the loss is invisible to the consumer.
- **Action:** Split the requirement on `@` before the version-specifier chain (PEP 508 requires
  whitespace around the `@` of a URL reference, so `dep.split(' @ ')[0]` is safe and does not touch
  a leading `@` in a name). Add a fixture module whose dependency is a direct reference and assert
  the edge appears.
- **Done when:** A `[project] dependencies` entry of the form `sample-core @ file:///./sample_core`
  yields the same edge as `sample-core>=1.0.0` does, pinned by a test in
  `test_pyproject_derivation_resolver.py`.
- **Effort:** S
- **Risk if fixed:** Low. A name containing ` @ ` is not a legal distribution name, so no currently
  joining dependency changes.

## G3 — Strip the PEP 508 environment marker from a dependency name

- **Kind:** bug
- **Severity:** medium
- **Topic:** lsp/resolvers
- **Where:** `marketplace/bundles/plan-marshall/skills/build-pyproject/scripts/_pyproject_cmd_discover.py:295`
  and `:301`
- **Evidence:** The split chain contains no `;`, so `m-core; python_version >= "3.11"` is truncated
  at the first `>` and strips to `m-core; python_version`:

  ```text
    marked metadata.name= m-marked -> ['m-core; python_version:runtime']
    edges: ([], [])
  ```

  With no marker the same declaration joins correctly, so the marker alone destroys the edge.
- **Why it matters:** A conditionally-required sibling (`sample-core; python_version < "3.12"`) is a
  real internal dependency for impact analysis regardless of the marker's truth on this interpreter
  — changing the depended-upon module can still break the dependent. As with G2 the loss is silent,
  and unlike G2 the mangled key even survives PEP 503 normalisation as a plausible-looking string
  (`sample-core; python-version`), so nothing downstream can spot it either.
- **Action:** Split the requirement on `;` first, before the version-specifier chain. Add a fixture
  module declaring a marked dependency on a sibling and assert the edge appears. Note this is a
  separate instance from G2 in the same function; both splits belong in the same one-line fix but
  need separate assertions.
- **Done when:** A `[project] dependencies` entry of the form `sample-core; python_version >= "3.11"`
  yields the same edge as `sample-core` does, pinned by its own test.
- **Effort:** S
- **Risk if fixed:** Low. `;` is not legal inside a distribution name.

## G4 — Read (or explicitly disclose) npm's `peerDependencies` and `optionalDependencies`

- **Kind:** incomplete
- **Severity:** medium
- **Topic:** lsp/resolvers
- **Where:** `marketplace/bundles/plan-marshall/skills/build-npm/scripts/_npm_cmd_discover.py:293-307`
  (`_extract_dependencies`); documentation site `doc/user/dependency-intelligence.adoc:90-98`
  (§ npm specifics) and `marketplace/bundles/plan-marshall/skills/build-npm/SKILL.md:81`
- **Evidence:** `_extract_dependencies` iterates `pkg_data.get('dependencies', {})` and
  `pkg_data.get('devDependencies', {})` and nothing else. `peerDependencies` — the idiomatic way a
  plugin package in a workspace declares its dependency on the workspace's core package — and
  `optionalDependencies` therefore produce no edge. The plan's *Done when* for D3 is met by the
  fixture, so this is reach, not a failed deliverable.
- **Why it matters:** The run disclosed the exactly analogous Python limitation — "Other extras are
  *not* read. A sibling named only under a `test`, `docs` or `all` extra produces no edge"
  (`dependency-intelligence.adoc:86`) — and recorded it as residue. The npm section carries no
  equivalent sentence, so the two ecosystems are documented asymmetrically for the same class of
  gap and an npm consumer has no way to learn why a peer-declared sibling is missing from `impact`.
- **Action:** Either extend `_extract_dependencies` with `peer` and `optional` scopes (the join
  ignores the scope segment, so no resolver change is needed) and add the two rows to
  `module-discovery.md` § Dependency Format and `architecture-persistence.md` § Dependency Format;
  **or**, if widening what discovery emits is judged out of budget, add one paragraph to
  `dependency-intelligence.adoc` § npm specifics and to `build-npm/SKILL.md` § Axis-C naming the two
  unread kinds and their consequence, matching the Python paragraph's shape.
- **Done when:** Either a fixture package declaring a sibling only under `peerDependencies` yields an
  edge, or `doc/user/dependency-intelligence.adoc` § npm specifics states in words that
  `peerDependencies` and `optionalDependencies` produce no edge.
- **Effort:** S (documentation route) / M (extraction route)
- **Risk if fixed:** Taking the extraction route grows every npm module's `dependencies` list, which
  is read by consumers beyond edge derivation; the four scope-vocabulary sites listed above must be
  updated in lock-step or they go stale.

## G5 — Make the npm no-fallback rule falsifiable by its own fixture

- **Kind:** test-gap
- **Severity:** medium
- **Topic:** tests
- **Where:** `test/plan-marshall/build-npm/test_npm_derivation_resolver.py:141-143`
  (`test_package_without_a_name_is_never_an_edge_target`), fixture
  `test/plan-marshall/build-npm/fixtures/workspace-monorepo/`
- **Evidence:** Mutating `BuildExtension._package_name`
  (`marketplace/bundles/plan-marshall/skills/build-npm/scripts/extension.py:186`) to fall back to
  the module's own `name` leaves the whole suite green — `54 passed`, identical to baseline — while
  the same mutation on the Python side (`build-pyproject/scripts/extension.py:325`) turns 3 tests
  red. The cause is that no fixture package depends on the string `unnamed`:

  ```text
  any module declaring a dependency on the literal string 'unnamed': []
  edges with the shipped no-fallback rule: [5 edges]
  edges WITH a directory-name fallback : [the same 5 edges]
  --- after adding one dependency on the literal string 'unnamed':
  edges WITH a directory-name fallback : [..., ('@sample/monorepo', 'unnamed'), ...]
  ```

- **Why it matters:** The no-fallback rule is a load-bearing contract obligation, stated normatively
  in three shipped places (`build-npm/SKILL.md:88`,
  `ext-point-derivation-resolver.md:255`, `dependency-intelligence.adoc:98`) and rationalised in the
  code as "a fabricated edge is worse than the missing one it would paper over". A future
  simplification that removes it would ship green.
- **Action:** Add `"unnamed": "^1.0.0"` to the `dependencies` of
  `fixtures/workspace-monorepo/package.json` (mirroring how `multi-module-python/pyproject.toml`
  depends on `"toolbox>=1.0.0"`). The shipped edge set does not change, so
  `test_full_edge_set_is_exactly_the_declared_internal_dependencies` and the e2e impact assertions
  stay as they are — only the mutant dies.
- **Done when:** Replacing `_package_name`'s body with
  `return (module_data.get('metadata') or {}).get('name') or module_data.get('name')` makes
  `test_npm_derivation_resolver.py` fail.
- **Effort:** S
- **Risk if fixed:** None expected; verify the e2e module's exact impact lists in
  `test_native_resolver_graph_impact.py:324` are unchanged, since the fixture is shared.

## G6 — Correct the npm resolver test module's account of its own fixture

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** tests
- **Where:** `test/plan-marshall/build-npm/test_npm_derivation_resolver.py:22-24`
- **Evidence:** The module docstring states failure mode 2 as: *"`packages/unnamed` declares no
  `name` while another module depends on the string `@sample/core`; a resolver that fell back to the
  directory name would invent a package identity npm never published."* The clause after the
  semicolon does not describe the fallback failure mode — a dependency on `@sample/core` is joined by
  the *published* name and is unaffected by any fallback. The Python sibling states the same failure
  mode correctly (`test_pyproject_derivation_resolver.py:22-24`: "the fixture root depends on the
  same string").
- **Why it matters:** The docstring is the stated justification for a fixture shape that G5 proves
  does not in fact test what it claims. A reader auditing this module for vacuity is told the guard
  is falsifiable when it is not.
- **Action:** Rewrite the clause to name what actually falsifies the rule — a module depending on the
  literal string `unnamed` — as part of the same change as G5.
- **Done when:** The docstring's failure mode 2 names the dependency on `unnamed` that G5 adds.
- **Effort:** S
- **Risk if fixed:** None.

## G7 — Pin D1's premise against the real Gradle discoverer, not a hand-built dict

- **Kind:** test-gap
- **Severity:** medium
- **Topic:** tests
- **Where:** `test/plan-marshall/build-gradle/test_gradle_rides_the_maven_join.py:125-128`
  (`test_gradle_modules_carry_the_coordinate_pair_the_maven_join_reads`), helper at `:59-76`
- **Evidence:** The test's docstring calls itself "The premise of the whole claim: Gradle publishes
  what Maven publishes", then asserts `metadata['group_id'] and metadata['artifact_id']` on the dict
  that the test's own `_gradle_module()` helper hard-codes two lines above. It cannot fail regardless
  of what `_extract_gradle_module` emits. Every other test in the module correctly drives real code —
  `_parse_dependencies_output` for the extraction half and the real `maven` resolver for the join half
  — so this is the one assertion in the module with no production code behind it.
- **Why it matters:** This test was added specifically to close review finding F14 ("The Gradle claim
  shipped in the docs with zero test coverage"), and the half it was meant to pin — that Gradle
  discovery publishes the coordinate pair — is still uncovered. The claim is asserted in four shipped
  documents (`ext-point-derivation-resolver.md:265`, `build-maven/SKILL.md:91`,
  `code-intelligence.adoc:67`, `dependency-intelligence.adoc:58-60`). The premise is in fact true —
  `_gradle_cmd_discover.py:448-453` returns `'artifact_id': name, 'group_id': group_id` — but nothing
  executable would notice if it stopped being true.
- **Action:** Replace the assertion with one that calls `_extract_gradle_module` (or, if its Gradle
  subprocess dependency makes that impractical without a daemon, `_parse_gradle_properties` plus the
  metadata assembly) and asserts the returned `metadata` carries both keys. Note that
  `_parse_gradle_properties` defaults `group_id` to `None` (`_gradle_cmd_discover.py:272`), so the
  new test should also pin what happens when a Gradle build declares no `group` — currently that
  module publishes no joinable coordinate and derives no edges, which is undocumented.
- **Done when:** Removing `'group_id': group_id` from `_extract_gradle_module`'s returned `metadata`
  dict makes `test_gradle_rides_the_maven_join.py` fail.
- **Effort:** M
- **Risk if fixed:** The replacement must stay hermetic — no JDK or Gradle daemon is available in CI
  for this test module, which is why the current test avoided the real function.

## G8 — Correct the "Three further joins" count in the user-facing dependency page

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** documentation-surface
- **Where:** `doc/user/dependency-intelligence.adoc:71`
- **Evidence:** The line reads *"Three further joins run over cross-references rather than build
  declarations: Python `import` statements, marketplace markdown references, and AsciiDoc
  cross-document references."* The live Axis-A roster is four — `markdown`, `python`, `documentation`
  and `lsp` — enumerated at
  `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-derivation-resolver.md:229-232`,
  and a live `get_module_graph` over this repository returns seven resolver rows. **Not attributable
  to this plan:** the `lsp` resolver landed at `c86de8b` (#1243), after this plan's `87c71d3`
  (#1238); a later plan (#1252) then edited this same page without correcting the count. Recorded
  here because the audit surfaced it.
- **Why it matters:** The sentence exists so a consumer seeing more resolver rows than build systems
  can reconcile them — it is the reconciliation the run added in response to finding N13. With the
  wrong count it fails at exactly its purpose, and the same page's NOTE at `:75` tells the reader to
  expect *every* discovered resolver as a row.
- **Action:** Correct to four and add `lsp` to the enumeration, with a clause noting it is off by
  default (per `ext-point-derivation-resolver.md:231`, it runs only for a language with an enabled
  machine-local `language_servers` entry). Consider replacing the literal count with a reference to
  the roster's single enumeration, which is the fix CodeRabbit's C1 finding forced on
  `client-api.md` for the same drift reason.
- **Done when:** `doc/user/dependency-intelligence.adoc:71` either names four joins including `lsp`,
  or defers the count to `ext-point-derivation-resolver.md` § Current implementations.
- **Effort:** S
- **Risk if fixed:** None.

## G9 — Correct the run report's build-gate `*.py` file count

- **Kind:** report-defect
- **Severity:** low
- **Topic:** plan-lane-contract
- **Where:** `doc/plans/code-intelligence-substrate/210-native-coordinate-resolvers/report-01.md`
  § Build gate, first line
- **Evidence:** The report states *"`git diff --name-only origin/main...HEAD -- '*.py'` → **10
  files** at HEAD, so the gate applied"*, and the same section states that the diff verdict "MUST be
  re-derived at HEAD". The merged squash commit's `.py` diff is **13** files:
  `git show --name-only --format="" 87c71d3 | grep -c '\.py$'` → `13`. `87c71d3` has a single parent
  (`git rev-list --parents -n 1 87c71d3`), so its diff is the three-dot diff the report's command
  computes. The three uncounted files are ones added after `10` was recorded —
  `test_scoped_module_name_persistence.py` (pass 3 / finding C4) plus the two N14 fixture fixes
  (`test_cmd_suggest.py`, `test_extension_implementations.py`). The `./pw verify` figures in the same
  block *were* correctly re-derived (`19716 + 5 = 19721` passed, `740 + 1 = 741` test source files).
- **Why it matters:** It is the one instance of exactly the defect the report's own Step 9 proposal
  is about — a figure observed mid-run and restated at finalization, describing a tree that no longer
  exists. It sits in the section a collector reads to decide whether the build claim covers the
  shipped tree, and it undercuts the proposal's evidence base if the proposal is ever taken up.
- **Action:** Correct `10` to `13` in § Build gate, and note in the Step 9 proposal that the
  re-derivation rule it proposes would have caught this instance in the report that proposes it.
- **Done when:** The report's build-gate file count matches
  `git show --name-only --format="" 87c71d3 | grep -c '\.py$'`.
- **Effort:** S
- **Risk if fixed:** None — the report is a dated record and the correction does not change any
  deliverable verdict.
