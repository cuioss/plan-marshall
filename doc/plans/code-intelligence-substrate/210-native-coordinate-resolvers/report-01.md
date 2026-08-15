# Run report — 210-native-coordinate-resolvers (run 01)

**Date (UTC):** 2026-08-15    **Branch:** `claude/native-coordinate-resolvers-q919yv`    **PR:** _pending_    **Outcome:** _in progress_

## Skills loaded

Loaded via the bundle-source path (`Read: marketplace/bundles/{bundle}/skills/{skill}/SKILL.md`) — the
`plan-marshall` plugin notation was not attempted, since this repository *is* the marketplace and the
path route always works here.

| Skill | Why |
|---|---|
| `cloud-plan-lane` | The lane contract — first action of the run |
| `plan-marshall:ref-code-quality` | Always |
| `pm-plugin-development:plugin-script-architecture` | Always |

Not loaded, with reason: `persona-implementer`, `pm-dev-python:python-core`, `pm-dev-python:pytest-testing`,
`pm-documents:ref-asciidoc`, `plugin-architecture`, `ref-workflow-architecture`, `persona-security-expert`.
The surface was two existing `extension.py` implementors, one new pure-function module, three test modules
and four documentation files; the conditional skills' subject matter (new bundle structure, security-relevant
change, workflow/dispatch topology) was not touched, and the two always-load skills already carry the
code-quality and script-implementation standards this work needed.

## Deliverables

### D0 — GATE: measure a real non-Maven project

**Done. Three real projects measured, not one.** Driven through the shipped discovery + `merge_resolver_edges`
path, no fixtures.

| Project | Modules | Dependency strings naming a sibling module | Edges **before** | Edges **after** |
|---|---|---|---|---|
| `plan-marshall` (this repo, via `build-pyproject`) | 1 | 0 | 0 | 0 |
| `open-telemetry/opentelemetry-python` (shallow clone) | 8 | 11 | **0** | **11** |
| `remix-run/react-router` (shallow clone) | 31 | 83 | **0** | **83** |

The consumer-wide claim the plan labelled **HYPOTHESIS** is therefore now **measured**, and measured on
projects with 11 and 83 genuine internal dependency relations available to find. In every before-case four
resolvers ran and returned zero — the anti-vacuity `resolver_count: N, edges: []` state, i.e. a real positive
answer that the graph was empty.

A fourth measurement explains why this repository's own graph looked healthy and hid the defect: the **full**
architecture crawl over `plan-marshall` yields 29 edges across 12 modules, but **zero** modules carry a
`group_id`+`artifact_id` pair, all 29 edges come from the `component_refs`-based Axis-A resolvers
(markdown 29, python-import 5, documentation 5), and the one module the Python build system discovered
sources **zero** edges. `component_refs` is materialized only by `pm-plugin-development` and `pm-documents`,
so an ordinary Python/npm consumer project has none and falls back to exactly the 0-edge case above.

Commit: measurement only, mutates nothing.

### D1 — GATE: verify Gradle explicitly

**Done. Verdict: the coordinate path WORKS — a second reference implementation, not a third defect.**
One narrow form does not, and is recorded rather than fixed (see Residue).

Driven through the real `_parse_dependencies_output` and the real `maven` resolver. Only the
`gradle dependencies` console text was synthesized, transcribed from the format that parser's own docstring
documents — no JDK/Gradle daemon is available in this environment.

| Gradle dependency form | Extracted as | Edge derived |
|---|---|---|
| `com.example:shared:1.0` (coordinate) | `com.example:shared:compile` | **yes** |
| `project :core` (idiomatic inter-project) | `project:core:compile` | **no** |

Gradle discovery publishes `metadata.group_id` / `metadata.artifact_id` exactly as Maven's does, so the
`maven` resolver joins Gradle modules unchanged. The `project :name` form is extracted with the literal
`project` as its first segment, so the join key becomes `project:core`, which matches no module's published
coordinate. **Not fixed** — the plan excludes fixing Gradle, and its deliverables scope to Python and npm;
widening to a Gradle resolver would be scope the plan did not ask for.

### D2 — Python resolver

**Done.** `build-pyproject`'s `BuildExtension` now also subclasses `DerivationResolverBase`, registering
resolver id **`pyproject`** (not `python` — `pm-dev-python`'s import join owns that id, and ids must be
unique or the discovery collector drops the second claimant). It joins the PEP 621 `[project] name`
(carried on `metadata.name`) against `name:scope` dependency strings, compared in PEP 503 normalised form.

Commit `37788dc`.

### D3 — npm resolver

**Done.** `build-npm`'s `BuildExtension` now also subclasses `DerivationResolverBase`, registering resolver
id **`npm`**, joining `package.json` names case-folded. Workspace members required no special case: discovery
already resolves the `workspaces` globs (array form, `{"packages": [...]}` form, and pnpm's
`pnpm-workspace.yaml`) into one module per member, and the `workspace:*` protocol never reaches the join
because only the dependency's name is read.

npm discovery now also carries `metadata.name`. This was necessary, not incidental: a module's own `name`
falls back to the directory (or to `default` for an unnamed root) when `package.json` declares none, so it is
the only field that distinguishes a published package from an unnamed one.

Commit `37788dc`.

### D4 — tests

**Done**, 47 new tests across three modules, all driven through the real discoverers:

- `test/plan-marshall/build-pyproject/test_pyproject_derivation_resolver.py` (14)
- `test/plan-marshall/build-npm/test_npm_derivation_resolver.py` (15)
- `test/plan-marshall/manage-architecture/test_native_resolver_graph_impact.py` (18) — end-to-end through the
  real `graph` and `impact` verbs with the real resolver objects registered

**Impact is asserted separately from edges**, as the plan requires. The impact assertions name the expected
dependent sets (`sample_core` → `['default', 'sample_api', 'sample_cli']`; `@sample/core` →
`['@sample/api', '@sample/cli', '@sample/monorepo', 'unnamed']`) rather than checking non-emptiness, so
"edges present, impact empty" fails them. Two further tests assert impact is non-empty with a message naming
that exact failure mode.

**Non-vacuity is pinned in the suite**, not merely claimed: two parametrised tests re-run the *same* fixtures
with the resolver set emptied and assert zero edges and zero impact. Without them every other assertion in
that module would also pass if the fixtures carried declared `internal_dependencies` or if some other
resolver derived the same pairs.

Two on-disk fixtures were added, each shaped so a specific failure mode is falsifiable rather than merely
absent:

- `build-pyproject/fixtures/multi-module-python/` — `sample_cli` spells its dependencies `Sample_API` and
  `sample.core` (PEP 503-equivalent, textually different); `toolbox` is a discovered module declaring no
  `[project] name` that the root depends on by that string.
- `build-npm/fixtures/workspace-monorepo/` — `@sample/cli` spells its dependency `@SAMPLE/API`;
  `packages/unnamed` declares no `name`; `@sample/cli` reaches `@sample/core` only via `devDependencies`.

Commit `37788dc`.

### D5 — documentation

**Done.** The plan starred the consumer-facing page as mattering most, so that is a new dedicated page rather
than a paragraph appended elsewhere.

- **`doc/user/dependency-intelligence.adoc` (new)** — per-ecosystem table of the identity each build system's
  join keys on; the Python and npm specifics (PEP 503 folding, scoped names, workspace members, dev scopes,
  the no-published-name rule); how to read `resolver_count` so an empty answer is not misread as "no
  dependencies"; what `producers[]` and `notes[]` mean; the Gradle `project(...)` limitation. Registered in
  `doc/user/README.adoc`.
- **`ext-point-derivation-resolver.md`** — roster rows for `pyproject` and `npm`, plus four sections the
  implementation forced: why a name join must be build-system scoped, why neither join falls back to the
  module name, why `python` and `pyproject` are both wanted, and that Gradle rides the Maven join.
- **`doc/concepts/code-intelligence.adoc`** — a "coordinates are not the only identity" section.
- **`doc/concepts/extension-architecture.adoc`** — Axis-C now names each build skill's join.
- **`doc/resources/diagrams/extension-topology.svg`** — the derivation-resolver card read "1 impl", already
  stale at four before this change and six after.

Commit `fc73d6a`.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` → **7 files**, so the gate applied.

`./pw verify` (all three sub-steps) — **SUCCESS**:

```
mypy(production)  Success: no issues found in 400 source files
ruff              All checks passed!
SPDX              SPDX-header check passed
plugin-doctor     issues[0]
mypy(test)        Success: no issues found in 739 source files
module-tests      19709 passed, 14 skipped
```

The working tree was clean at the gate, so the diff saw all the work.

Two failures were caught by the gate and fixed before the docs commit — both worth recording because the
narrower commands would have missed them:

1. **`test-compile` only.** Both new resolver test modules returned `Any` out of a file-loaded module
   (`no-any-return`). `quality-gate` and `module-tests` are both green on this; only `./pw verify`'s
   `test-compile` sub-step catches it — exactly the case the lane contract warns about.
2. **A hardcoded roster pin.** `test_graph_family_bundle_project.py`'s `EXPECTED_RESOLVER_IDS` /
   `AXIS_B_RESOLVER_IDS` are deliberate hand-written pins designed to fail when the registry gains a
   resolver. Four tests failed; the pins were updated to the six-resolver roster.

## Findings

Source: the pre-PR verification sub-agent (Step 6), dispatched read-only against the plan. It returned 18
findings plus one non-finding. **17 fixed, 1 rejected.** One finding class it surfaced — a claim this diff
itself falsified — was the most valuable result of the pass and would not have been caught by any gate.

The agent independently re-derived D1 rather than trusting the report, and empirically confirmed the
impact/edge separability requirement by injecting a break into the reverse-index population only, observing
`edges: 5, impact: []` — i.e. the failure mode the plan names is reachable and the impact assertions do catch
it. It also confirmed the four Out-of-scope bullets are clean.

| # | Finding | Disposition |
|---|---|---|
| F1 | Run report absent, making D0 unverifiable | **Rejected — stale.** `report-01.md` was committed at `047eef4`, after the agent was dispatched, so it read a tree that genuinely lacked it. D0's measurement is recorded above. The verdict it drove ("D0 NOT VERIFIABLE") falls with it. |
| F2 | D0's consumer-wide claim stated as fact | **Rejected as stated, for the same reason** — the claim IS measured (11 and 83 edges on two real repos). The Gradle row of that table already points at its own limitation section, so the blanket sentence is qualified where it needs to be. |
| F3 | `dependency-intelligence.adoc` says "Three producer names are not resolvers" and lists two | **Fixed** — corrected to two. My error. |
| F4 | Same page's table claimed the Python join reads all `optional-dependencies`; discovery reads only the `dev` extra | **Fixed** — table corrected, and a paragraph added naming the consequence (a sibling under a `test`/`docs` extra silently produces no edge). Also recorded as residue. |
| F5 | `ext-point-derivation-resolver.md` "One bundle registers at most one resolver … structural, not a convention" — **falsified by this diff** | **Fixed** — Axis-B resolvers are discovered per *build skill* (`discover_build_extensions` keys on `skill_name`), so `plan-marshall` alone now contributes `maven`, `npm` and `pyproject`. Replaced with a per-axis registration-site table and an explicit "do not read this as one-per-bundle". |
| F6 | `build-pyproject/extension.py` restated the same false premise in new prose | **Fixed** — reworded to "each registration site stamps a single resolver id". |
| F7 | `ext-point-derivation-resolver.md:172` leant on the premise (pre-existing) | **Fixed** — scoped to "all three are Axis-A, where the registration site is the bundle". |
| F8 | `build-npm/SKILL.md` documents no Axis-C face, unlike every other resolver-owning skill | **Fixed** — added a "Module-edge derivation (Axis-C derivation resolver)" section matching `build-maven`'s shape. |
| F9 | `build-pyproject/SKILL.md` — same gap | **Fixed** — same treatment. |
| F10 | `module-discovery.md` § Dependency Format omits Python, and my own `_name_edge_join` docstring cites that table for both ecosystems | **Fixed** — Python and Gradle rows added; the npm example scopes corrected from `compile`/`test` to the emitted `runtime`/`dev`. |
| F11 | `architecture-persistence.md` § Dependency Format — identical defect in a second owning standard | **Fixed** — same treatment. |
| F12 | `test_npm_discover_modules.py` module-header roster `metadata: {type, description}` stale | **Fixed** — now `{name, description, version, scripts}`. |
| F13 | Same header's `dependencies: ["npm:name:scope"]` wrong, and load-bearing — a double written from it would join every npm dependency on the literal key `npm` | **Fixed** — corrected to `["name:scope"]` with the scope vocabulary named. |
| F14 | The Gradle claim shipped in three docs with zero test coverage | **Fixed** — new `test/plan-marshall/build-gradle/test_gradle_rides_the_maven_join.py` (7 tests) drives the real `_parse_dependencies_output` into the real Maven resolver, pinning both that the coordinate form yields an edge and that `project:core:compile` does not. The limitation is pinned as current behaviour, so closing it later fails the test and forces the three doc sites to be revisited. |
| F15 | `client-api.md` worked examples show `resolver_count: 1` (pre-existing at four, widened to six here) | **Fixed** — all four examples updated to the real six-resolver roster, plus a normative note that discovery is registry-wide, so `resolver_count` counts resolvers that RAN, never ones that CONTRIBUTED. |
| F16 | `code-intelligence.adoc` § Related linked only `build-maven/SKILL.md` while the body now introduces two more Axis-B joins | **Fixed** — both new skills linked. |
| F17 | No back-link from `code-intelligence.adoc` to the new user page, though the sibling pattern has one | **Fixed** — added. |
| F18 | The ⭐ user page never shows how to invoke any of the four verbs | **Fixed** — added a "The four verbs" section with two runnable invocations and a per-verb table. The `path` row was written with invented `--from/--to` flags on first draft and corrected against the skill's canonical block to positional `SOURCE TARGET`. |

**Non-finding, recorded and not acted on.** Running `test/plan-marshall/manage-architecture` together with
`build-*`, `pm-plugin-development` and `pm-dev-python` in ONE serial pytest process yields 39 failures. The
agent verified this is **pre-existing** — 34 reproduce with the new e2e module excluded — and is caused by
`load_script_module('…_cmd_client.py', '_cmd_client')` re-registering `_cmd_client_query` in `sys.modules`
and orphaning other modules' captured references. The new module follows the identical idiom used by 14
sibling test files, and the canonical xdist run distributes per file, so it does not surface there. Not
attributable to this change; see Residue.

### Gate findings (not from the sub-agent)

| Source | Finding | Disposition |
|---|---|---|
| `./pw verify` test-compile | `no-any-return` in both new resolver test modules — invisible to `quality-gate` and `module-tests` | **Fixed** before the docs commit |
| `./pw verify` module-tests | `test_graph_family_bundle_project.py`'s `EXPECTED_RESOLVER_IDS` / `AXIS_B_RESOLVER_IDS` pins failed (4 tests) — the deliberate hand-written pins, working as designed | **Fixed** — updated to the six-resolver roster |
| `./pw verify` test-compile | `no-any-return` in the new Gradle pin test | **Fixed** |

## Reviewer participation

_Pending — PR not yet opened._

Expected population derived from configuration (the `author_login` of each
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` registry doc):
`coderabbitai`, `cuioss-review-bot`, `sourcery-ai` — M = 3.

## Cost

- **Tokens:** not available to the agent in this session.
- **Wall-clock:** ~1h05m from first commit (`c820514`, 10:45:02Z) to the documentation commit
  (`fc73d6a`, 11:15:36Z) plus the preceding investigation and the verification pass; source is the git
  committer timestamps plus the session's own ordering.
- **Population:** this single Claude Code cloud session's activity. ⛔ **Not comparable to a plan-marshall
  `metrics.toon` total**, which counts an orchestrator-plus-agent dispatch tree under plan-marshall's own
  per-task billing boundary. This run has no such boundary — one interactive session plus one verification
  sub-agent — so no comparable figure can be produced, and none is offered.

## Contract check (Step 9)

_Pending._

## What have we learned (Step 9)

_Pending._

## Residue

- **Gradle's `project :name` form derives no edge** (D1). Real, verified, and deliberately not fixed: the
  plan excludes fixing Gradle and scopes its deliverables to Python and npm. A Gradle build wiring its
  modules with the idiomatic `implementation project(':core')` gets an empty internal graph. The natural fix
  is the same name-join shape this plan built — join `project:{name}` on the module name — which would make
  it a small follow-up rather than new design work. Now **pinned by test** and documented in three places,
  so the follow-up has a failing assertion waiting for it.
- **Python discovery reads only the `dev` extra** (F4). `_parse_pyproject_metadata` reads `[project]
  dependencies` and `optional-dependencies.dev` and nothing else, so a sibling named only under a `test`,
  `docs` or `all` extra produces no edge. Documented rather than changed: widening it alters what discovery
  emits for every consumer of `dependencies`, not just edge derivation, which is beyond this plan's surface.
- **Serial-pytest module-registration collision.** Pre-existing (34 of 39 failures reproduce without this
  plan's e2e module), caused by `load_script_module` re-registering `_cmd_client_query` in `sys.modules`.
  Invisible under the canonical xdist run. Worth its own issue; not attributable to this change.
- **A scoped npm module cannot round-trip through `save_module_derived`.** That writer names its per-module
  directory after the module, so `@sample/core` nests into two directories and the synthetic-project
  fallback that reads them back never finds it. This is why the e2e test copies its fixture into a temp
  project root instead of seeding. The writer documents itself as a snapshot-fixture seam, so production
  reads (which crawl live) are unaffected — but the **enriched** overlay is persisted per module by the same
  naming scheme, and whether a scoped npm package's overlay round-trips was **not verified by this run**.
  Stated as unverified rather than assumed either way.
