# Gaps — 220-resolver-configuration

The plan's five deliverables landed and are covered by non-vacuous tests (two mutations confirmed the
D3 default guard and the roster fail-open guard go red against the defects they name). What remains is
one real behavioural defect the four verification rounds did not reach — with every resolver switched
off, `capabilities` reports `module_edges: not_derivable` on a project whose `graph` verb still returns
declared edges — plus its rendered and documented companions, two still-open residue items the run
declared, and three report-level inaccuracies. The plan's two declared deviations (id-keying instead of
file-pattern keying; no `precedence` knob) were re-checked against the code and are correct
engineering, so they are recorded in `verification.md` rather than filed as gaps here.

## G1 — Stop reporting `module_edges: not_derivable` when declared edges are still returned

- **Kind:** bug
- **Severity:** high
- **Topic:** architecture-core
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_handlers.py:231-234`
  (`cmd_capabilities`, the `module_edges` record); the state is produced by
  `_cmd_client_query.py:966-1031` (`_partition_configured_resolvers`) together with
  `_cmd_client_query.py:1219-1222` (declared-edge stamping) and `:1238-1240` (sibling cross-links)
- **Evidence:** driving the real code with one stub resolver disabled through the machine-local
  binding and one module carrying `internal_dependencies: ['core']` (probe run against a temp
  `PLAN_BASE_DIR` store):

  ```text
  resolver_count: 0
  edge_count: 1
  edges: [{'from': 'core', 'to': 'app', 'producers': ['declared']}]
  capability module_edges: {'status': 'not_derivable', 'producers': [],
                            'producer_count': 0, 'derived_count': 1}
  ```

  `status: not_derivable` beside `derived_count: 1` is the fourth state the handler's own docstring
  (`_cmd_client_handlers.py:172-176`) enumerates as impossible: "`not_derivable` (`producer_count: 0` —
  no producer ran, an absence of capability); `derivable` with `derived_count: 0`; `derivable` with
  `derived_count: N`".
- **Why it matters:** `capabilities` exists so a caller can branch once instead of probing — its
  docstring calls "probe once then branch" the unsound fallback it refuses to enable. An agent that
  reads `module_edges: not_derivable` will skip `graph` / `path` / `neighbors` / `impact` entirely, on a
  project where those verbs return a real, non-empty edge set from declarations and sibling
  cross-links. Before this plan the state needed *zero registered resolvers* (never true on a real tree —
  seven ship); the new menu makes it one operator action away.
- **Action:** make the `module_edges` capability reflect the edge sources that actually answer the
  verbs. Either compute `status` from the full producer population reaching the response (dispatched
  resolvers plus the reserved `declared` / `sibling-cross-link` producers present in
  `graph_result['edges']`), or keep `producer_count` resolver-scoped and add an explicit third status
  value for "no resolver ran, but declared edges are available" — whichever is chosen, `status:
  not_derivable` must never co-occur with `derived_count > 0`.
- **Done when:** a test seeds a project with a declared `internal_dependencies` edge, disables every
  discovered resolver through the `derivation_resolvers` binding, and asserts that `cmd_capabilities`'
  `module_edges` record does not claim `not_derivable` while `derived_count > 0`; and the handler
  docstring's state enumeration matches the states the code can emit.
- **Effort:** M
- **Risk if fixed:** ⛔ **An existing test pins the defective reading and must be revisited in the same
  change.** `test/plan-marshall/manage-architecture/test_derivation_resolver_configuration.py:249-269`
  (`test_capabilities_reports_not_derivable_when_every_resolver_is_disabled`) asserts
  `edges['status'] == 'not_derivable'` for the all-disabled case, and its docstring states the
  generalisation this gap refutes — "Disabling every resolver leaves the envelope genuinely unable to
  derive edges." The assertion is only true because its fixture (`_seed_triple`, `:85-99`) seeds modules
  with no declared `internal_dependencies`; the test must be re-scoped to that precondition rather than
  deleted. Beyond it: `capabilities` is consumed by feasibility/anti-vacuity guards
  (`test_feasibility_underivable_guard.py:93` derives "underivable" from `resolver_count > 0`); widening
  `status` without widening those readers could flip a guard that currently keys on the resolver
  population alone. The `producer_count` field must keep its resolver-scoped meaning or
  `test_capabilities.py` and the four handler docstrings drift again.

## G2 — Reword the all-switched-off provenance footer so it cannot contradict the table above it

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** architecture-core
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_render.py:97-101`
  (`_resolver_provenance_line`, the `not dispatched` branch)
- **Evidence:** `render_overview` on the G1 fixture prints an Adjacency table containing `app | core`
  and then, immediately below it:

  ```text
  _Edge provenance: 1 resolver(s) discovered but switched off by the machine-local configuration — alpha. No edges were derived._
  ```

  The rendered edge and the "No edges were derived" claim are two lines apart.
- **Why it matters:** the footer exists precisely so a reader does not misread the adjacency section;
  here it invites the opposite misreading — that the listed dependency is not real. "Derived" is
  defensible as resolver-scoped jargon, but the footer is the surface aimed at a human who does not
  hold that distinction.
- **Action:** in the all-withheld branch (and, for symmetry, the zero-registered branch at `:87`),
  qualify the claim — e.g. "no edges were derived *by a resolver*; any dependency shown above is
  declared" — and assert the wording in the two footer tests at
  `test_derivation_resolver_configuration.py:386-417`.
- **Done when:** a test renders an overview for a project with a declared edge and every resolver
  disabled, and asserts the footer does not state an unqualified "No edges were derived".
- **Effort:** S
- **Risk if fixed:** two existing assertions pin the current substrings
  (`'No edges were derived'`, `'no derivation resolver is registered'`); both must move with the wording.

## G3 — Say in the anti-vacuity tables that declared edges survive a full switch-off

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** documentation-surface
- **Where:** the third-state row of the anti-vacuity table on six surfaces —
  `marketplace/bundles/plan-marshall/skills/manage-architecture/standards/client-api.md:111`,
  `manage-architecture/standards/architecture-persistence.md:611-618`,
  `extension-api/standards/ext-point-derivation-resolver.md:145`,
  `doc/concepts/code-intelligence.adoc:159-160`,
  `doc/user/dependency-intelligence.adoc:122-123`, and
  `doc/adr/014-An_aggregation_over_N_independent_producers_carries_producer_identity_and_no_producer_suppresses_an_element_silently.adoc:97-98`
  — plus two in-code docstrings carrying the same false implication:
  `manage-architecture/scripts/_cmd_client_handlers.py:579-582` (`cmd_path`: "`resolver_count: 0` with
  `path: null` means no resolver ran (**there were no edges to walk**)") and `:638-641` (`cmd_impact`:
  "`resolver_count: 0` with `impact: []` means no resolver ran (**nothing could have depended on the
  module**)"). Eight sites in total.
- **Evidence:** each table is introduced as *zero-edge disambiguation* ("An empty result MUST be
  readable without inspecting the edge list", `client-api.md:105`) and its third row then reads, verbatim
  at `client-api.md:111`: "`resolver_count: 0` + a **non-empty** `resolvers[]` | **Resolvers exist, but
  this machine switched them off.** Every record carries `status: not_dispatched`. Read the first row as
  "no resolver ran" only when `resolvers[]` is empty too." The row states nothing about `edges[]`, and
  no surface says `graph` can still return a non-empty `edges[]` in that state — which the probe in G1
  demonstrates it does (`edge_count: 1`, `producers: ['declared']`). The two docstring parentheticals
  above assert the absence outright and are simply false. ⚠ Note `client-api.md:105` is where the
  *pre-fix* two-state table sat (`report-01.md` R3-6 cites it); the row moved to `:111` when the third
  row landed — cite `:111`, not the report's number.
- **Why it matters:** an agent reading the table concludes an empty edge set follows from
  `resolver_count: 0`, and will not reconcile a non-empty `edges[]` with a zero count. This is the
  documentation half of G1 and is what let G1 pass four verification rounds.
- **Action:** add one clause to the third row (or a sentence beneath each table) stating that
  declaration-sourced and `sibling-cross-link` edges are unaffected by the binding, so a zero
  `resolver_count` bounds *derivation*, not the response's edge set; and strike or qualify the two
  false parentheticals in `_cmd_client_handlers.py`. Filed as one entry rather than eight because it is
  a single missing caveat with one wording to propagate; the eight sites are enumerated above so a later
  run can sweep them together.
- **Done when:** each of the six table surfaces names the declared/cross-link exception in or beside its
  third-state row; `cmd_path`'s and `cmd_impact`'s docstrings no longer assert that a zero
  `resolver_count` implies an absence of edges; and a grep for `Resolvers exist` plus one for
  `resolver_count: 0` across those files finds no surface without the caveat.
- **Effort:** S
- **Risk if fixed:** low; prose only. The risk is the one this plan hit four times — updating some
  siblings and not others.

## G4 — Reconcile `run-config-standard.md`'s "Full Example" with the sections the document defines

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** documentation-surface
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-run-config/standards/run-config-standard.md:807-859`
- **Evidence:** re-derived from the file. The block titled "Full Example" (json fence `:809-858`)
  contains exactly five top-level keys — `version`, `commands`, `maven`, `architecture_refresh`,
  `ci_durations`. Five documented keys are missing: `language_servers`, `derivation_resolvers` and
  `display_timezone`, each of which has its own `##` section in this document (`:208`, `:267`, `:377`)
  *and* a row in the Optional Sections table (`:69-74`); plus `build` (`build.queue.upper_limit_seconds`)
  and `ci`, which appear in the skill's own schema example at `manage-run-config/SKILL.md:47-58` but not
  in this standard at all. The maintained Schema block (json fence `:19-56`) *does* carry
  `language_servers`, `derivation_resolvers` and `display_timezone`, so the standard's two JSON blocks
  now disagree with each other — and neither carries `build` or `ci`.
- **Why it matters:** a "Full Example" that omits five configured sections is a false claim in shipped
  documentation and is the block a reader copies when hand-authoring a store. This is the run's own
  residue item 2 (finding F8, rejected as pre-existing) — still open, and this plan added the fifth
  omission.
- **Action:** rebuild the example from the sections the document defines, or rename the block to
  "Example" and state which sections it deliberately omits. Decide separately whether `build` and `ci`
  belong in this standard's Schema block, since `SKILL.md` documents them and the standard does not.
- **Done when:** every top-level key the standard's Schema block carries also appears in the example
  block, or the block states its own scope in one sentence; and a reader diffing the two JSON fences
  (`:19-56` and `:809-858`) finds no key in one that is silently absent from the other.
- **Effort:** S
- **Risk if fixed:** none beyond touching a widely-read reference; no code reads this block.

## G5 — Correct the round-1 finding count in `report-01.md`

- **Kind:** report-defect
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `doc/plans/code-intelligence-substrate/220-resolver-configuration/report-01.md:157`
  (row 1 of the per-round table at `:155-160`)
- **Evidence:** re-counted in the file. The paragraph above the table states "the row counts below are
  the tables' own"; row 1 reads verbatim
  `| 1 | 13 | 10 from the sub-agent, 3 self-caught while fixing |`. The round-1 findings table
  (`:170-183`) holds **14** rows — F1, F2, F2b, F3, F4, F5, F6, F7, F8, F9, F10 (11 attributed to the R1
  sub-agent) plus S1, S2, S3. The other three rows re-derive exactly: round 2 has R2-1…R2-10 plus R2-S1
  = **11** (stated 11), round 3 has R3-1…R3-9 plus R3-R = **10** (stated 10), round 4 has R4-1…R4-10 =
  **10** (stated 10). Every one of those counts every suffixed row, so excluding F2b contradicts the
  report's own convention — round 1 is the only row that does not re-derive.
- **Why it matters:** this is the defect class R4-7 recorded as fixed ("replaced with a per-round table
  whose counts are the tables' own"). Leaving it makes the retrospective corpus' finding-density figures
  wrong for this run by one row and undermines the row's stated derivation.
- **Action:** change the round-1 row to
  `| 1 | 14 | 11 from the sub-agent, 3 self-caught while fixing |`, or state explicitly that F2b is
  counted as a sub-row of F2 and apply the same rule to R2-S1 and R3-R.
- **Done when:** each round's stated count equals the number of rows in that round's table under one
  stated counting rule.
- **Effort:** S
- **Risk if fixed:** none.

## G6 — Correct the "a developer's local binding would redden this" rationale, in the report *and* in the shipped test comment

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** tests
- **Where:** two sites carrying the same false rationale —
  `test/pm-plugin-development/plan-marshall-plugin/test_graph_family_bundle_project.py:353-357`
  (the comment justifying the assertion in `test_graph_response_names_every_discovered_resolver`), and
  `doc/plans/code-intelligence-substrate/220-resolver-configuration/report-01.md:222` (row R3-4, the
  disposition that wrote it)
- **Evidence:** the shipped comment reads "It equals the discovered count only while nothing is switched
  off, which is true of a fresh clone and of CI but NOT of a developer machine whose machine-local
  binding disables a resolver. Asserting the equivalence unconditionally would turn this red for that
  developer"; R3-4 states the same — "green only because a fresh clone and CI have no store … A
  developer who disables one resolver through the new menu turns it red". No test can see a developer's
  store: `test/conftest.py:1146-1147` installs an **autouse** `_plan_base_dir_sandbox` fixture
  redirecting `PLAN_BASE_DIR` (and `_config_core.RUN_CONFIG_PATH`) into a per-test tmp sandbox for every
  test not marked `allow_pollution`, and `conftest.py:849-875` locks that marker shut so no test carries
  it. Reproduced independently on the file R3-4 actually names: running
  `test_graph_family_bundle_project.py` with `PLAN_BASE_DIR` pointed at a store disabling all seven
  shipped resolvers gave **29 passed** — the autouse fixture overrode the environment. (The two
  provenance files behave the same way: **49 passed** under a store disabling `maven` and `python`.)
- **Why it matters:** the claim is now in shipped source, not just in the run report. A future author
  reading the comment may add per-test store isolation that already exists, or may believe the suite is
  machine-dependent when it is structurally not. The assertion the comment justifies (compare against
  the dispatched population, not the roster's cardinality) is correct on its own merits and must stay.
- **Action:** rewrite both to state the real reason — `resolver_count` and roster cardinality are
  different quantities once a dispatch control exists, so the assertion names the quantity it means —
  and, where the harness is mentioned at all, say that `test/conftest.py`'s autouse `PLAN_BASE_DIR`
  sandbox (not CI's empty store) is what keeps every test independent of the machine-local binding.
- **Done when:** neither `test_graph_family_bundle_project.py` nor R3-4 claims a developer's local
  binding can redden the suite, and a grep for `developer machine` / `fresh clone and CI` across
  `test/` and this plan directory returns no surviving instance of that rationale.
- **Effort:** S
- **Risk if fixed:** none — comment and report prose only; no assertion changes.

## G7 — Confirm or retire residue item 3 (cross-directory pytest pollution)

- **Kind:** test-gap
- **Severity:** low
- **Topic:** tests
- **Where:** `doc/plans/code-intelligence-substrate/220-resolver-configuration/report-01.md:378-381`
  (Residue 3, re-verified at those lines); the named files are
  `test/plan-marshall/manage-architecture/test_graph_resolver_provenance.py` and
  `test/plan-marshall/manage-architecture/test_native_resolver_graph_impact.py`
- **Evidence:** the residue claims "38 tests fail when several test directories share one ad-hoc
  invocation, on `origin/main` identically". Three multi-directory invocations on this tree were clean
  of that mode: `manage-architecture + extension-api` → **900 passed**; `+ pm-plugin-development/plan-marshall-plugin
  + pm-dev-python` → **1078 passed**; `manage-architecture + script-shared + pm-documents +
  pm-code-intelligence` → **1804 passed, 1 failed**, that one failure being an unrelated live-tree
  characterization over `plan-marshall:manage-metrics:manage-metrics` which fails identically when its
  file is run alone. Independently re-derived here: `manage-architecture + extension-api` → **900
  passed** again, and `test_argparse_surface.py` alone → **1 failed, 47 passed** on the same unrelated
  test, so the single failure is confirmed not to be a cross-directory effect.
- **Why it matters:** a residue item that names a reproduction nobody can reproduce either misdirects a
  future cleanup plan or hides a mode that still fires under a different directory combination. The
  named files still bind `extension_discovery` at module import and patch the attribute on that binding
  (`test_graph_resolver_provenance.py:28` + `:138`, `:144`, `:318`, `:621`;
  `test_feasibility_underivable_guard.py:56`) — the exact pattern the run's own F9/R2-S1 deferral
  replaced in its new files — so the hazard's precondition is still present even though it did not fire
  here.
- **Action:** either record the exact invocation that reproduces the 38 failures (directory set and
  order), or retire the residue item and, if the pattern is judged risky, apply the
  `importlib.import_module` deferral used in the new test files to the two legacy ones.
- **Done when:** the residue item names a reproducible invocation, or is struck and the legacy
  module-level patch targets are deferred like their new siblings.
- **Effort:** M
- **Risk if fixed:** changing the patch target in legacy provenance tests could mask a real staleness
  bug they currently expose; the deferral must be applied per file and each file re-run alone and in a
  sweep.

## G8 — Build the Configuration menu's Page 5 continuation before the next entry needs it

- **Kind:** incomplete
- **Severity:** low
- **Topic:** bundle-docs
- **Where:** `marketplace/bundles/plan-marshall/skills/marshall-steward/references/menu-configuration.md:89-108`
  (Page 4) and `:110-129` (routing table)
- **Evidence:** Page 4 now holds "Derivation Resolvers", "Merge Queue", "Full Reconfigure" and "Back" —
  the `AskUserQuestion` 4-element cap. The plan's Coordination note requires two sibling plans to land
  their language-server settings *inside* this surface; neither
  `doc/plans/code-intelligence-substrate/010-lsp-in-execute-lookup-and-write/` nor `240-skill-lsp-server/`
  has added a menu entry, and no `references/menu-language-servers.md` exists.
- **Why it matters:** the next author adding a Configuration entry must restructure Page 4 (replace
  "Back" with "More...", add Page 5 and a `more-4` routing row) in the same change as their feature —
  which is exactly the kind of adjacent edit that produced this run's cross-surface misses. The run's
  operator decision was to leave it as residue, which is recorded, not disputed.
- **Action:** when the next Configuration entry lands, add Page 5 via the documented "More..."
  continuation and move "Back" onto it, updating the option count in `:24` and the routing table.
- **Done when:** the Configuration submenu's stated option count matches the number of non-navigation
  options across its pages, and no page carries a fifth element.
- **Effort:** S
- **Risk if fixed:** the `:24` count sentence and the routing table must move together; a stale count
  there is a plugin-doctor-invisible inconsistency.

## G9 — Make `configured` mean the same thing in the roster and in the store verb

- **Kind:** bug
- **Severity:** low
- **Topic:** lsp/resolvers
- **Where:** `marketplace/bundles/plan-marshall/skills/extension-api/scripts/extension_api.py:167`
  (`'configured': resolver_id in section`) versus
  `marketplace/bundles/plan-marshall/skills/manage-run-config/scripts/run_config.py:871-877`
  (`configured = isinstance(entry, dict)`)
- **Evidence:** for a malformed entry such as `{"markdown": "yes"}`, the menu roster reports
  `configured: true` while `derivation-resolver get --resolver markdown` reports `configured: false`;
  both report `enabled: true` (fail-open). The menu document instructs the agent to render
  `configured` as the distinction between "left at the default" and "deliberately set"
  (`menu-derivation-resolvers.md:51,60-61`), so the two surfaces tell an operator different things
  about the same store.
- **Why it matters:** the operator sees a resolver marked as deliberately configured, resets it, and the
  store verb had already reported it unconfigured — a small but real inconsistency in the only two
  surfaces that report this field.
- **Action:** pick one definition (an entry counts as configured only when it is a dict) and use it in
  both readers; add a test with a non-dict entry asserting the two agree.
- **Done when:** a malformed entry yields the same `configured` value from
  `extension_api.list_derivation_resolvers()` and `run_config.cmd_derivation_resolver_get`, pinned by a
  test in each file.
- **Effort:** S
- **Risk if fixed:** none beyond the two roster tests that currently assert `configured` on well-formed
  entries.

## G10 — Fix `merge_resolver_edges`' stale statement about how the caller counts

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** architecture-core
- **Where:** `marketplace/bundles/plan-marshall/skills/extension-api/scripts/_derivation_merge.py:105-108`
- **Evidence:** the docstring reads "The caller distinguishes 'no resolver ran' from 'N resolvers ran
  and found nothing' by **the length of the returned report list**." The caller
  (`_cmd_client_query.py:1103-1122`) folds withheld records into that list and then derives
  `resolver_count` from `count_dispatched` (`:412`), never from its length — which is the whole point of
  the R2-1 redesign the same docstring explains 20 lines below at `:126-131`.
- **Why it matters:** this is the one surviving instance of the "length is the discriminator" claim the
  run swept out of five other surfaces, and it sits in the file whose round-1 docstring was the run's own
  1→2 leak. A reader implementing a second caller would reproduce the retired rule.
- **Action:** rewrite the sentence to say the caller distinguishes the two by `count_dispatched` over the
  report list, and that this function's own return contains only resolvers it called.
- **Done when:** no docstring in `_derivation_merge.py` states that the report list's length is the
  anti-vacuity discriminator.
- **Effort:** S
- **Risk if fixed:** none.
